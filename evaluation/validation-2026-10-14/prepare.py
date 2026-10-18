"""Fetch public Pexels variants and prepare isolated media, hashes and reference sheets."""
import hashlib
import json
import re
import subprocess
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
DATA = ROOT / "test-results" / HERE.name
sys.path.insert(0, str(ROOT))
from football import domain
from football.store import Store

SOURCES = [
    ("rain", 14109233, "children-playing-soccer-in-the-rain", "As hik", "football; rain; wet outdoor court"),
    ("night-kick", 3192198, "a-person-kicking-a-soccer-ball", "Pressmaster", "football; floodlit night; kick"),
    ("night-game", 32578915, "children-playing-soccer-on-a-field-at-night", "Usman AbdulrasheedGambo", "football; night; wide field"),
    ("park-juggle", 5552311, "a-man-playing-a-soccer-ball", "Armin Rimoldi", "football; sunny park; juggling"),
    ("urban-juggle", 9517738, "woman-juggling-a-football", "Anastasia Shuraeva", "football; outdoor urban; juggling"),
    ("studio-juggle", 10349006, "a-man-playing-with-a-football", "cottonbro studio", "football; dark indoor; juggling"),
    ("tennis-day", 6219752, "a-man-playing-a-tennis-ball", "Monstera Production", "tennis ball; daylight; hand toss"),
    ("tennis-dark", 10340709, "man-bouncing-tennis-ball-with-racket", "cottonbro studio", "tennis ball; dim court; racket"),
    ("basket-outdoor", 5274906, "basketball-player-dribbling-the-ball", "cottonbro studio", "basketball; strong outdoor shadows; bounce"),
    ("basket-indoor", 6077458, "girl-dribbling-a-basketball", "KoolShooters", "basketball; indoor; bounce"),
    ("volley-dark", 10350513, "volleyball-sportsman-playing-ball-at-net-and-bouncing-it-on-ground", "cottonbro studio", "volleyball; dim indoor; bounce"),
    ("volley-beach", 6179961, "a-man-tossing-a-ball-into-the-air", "Kampus Production", "volleyball; sunny beach; toss"),
]


def hash_file(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def ffmpeg():
    tools = DATA / "tools"
    candidates = list(tools.glob("ffmpeg*.exe"))
    if candidates:
        return candidates[0]
    wheel = next(tools.glob("imageio_ffmpeg-0.6.0-*.whl"))
    with zipfile.ZipFile(wheel) as archive:
        name = next(n for n in archive.namelist() if n.startswith("imageio_ffmpeg/binaries/") and n.endswith(".exe"))
        target = tools / Path(name).name
        target.write_bytes(archive.read(name))
    return target


def fetch(source):
    identifier, pexels_id, slug, author, condition = source
    target = DATA / "footage" / (identifier + ".mp4")
    record = {"id": identifier, "pexels_id": pexels_id, "page": f"https://www.pexels.com/video/{slug}-{pexels_id}/", "author": author,
              "condition": condition, "license_url": "https://www.pexels.com/license/", "retrieved": "2026-10-14", "file": target.name}
    if target.is_file():
        previous = HERE / "sources.json"
        if previous.exists():
            old = next((c for c in json.loads(previous.read_text(encoding="utf-8"))["clips"] if c["id"] == identifier), {})
            if old.get("download"):
                record["download"] = old["download"]
        if identifier == "rain":
            record["download"] = "https://videos.pexels.com/video-files/14109233/14109233-hd_1080_1920_30fps.mp4"
        record.update(bytes=target.stat().st_size, sha256=hash_file(target), reused_download=True)
        return record
    # Pexels publishes dimension/fps variants; only a successful HTTP response is retained as a source URL.
    variants = [f"hd_{w}_{h}_{fps}fps" for w, h in [(1280, 720), (720, 1280), (1366, 720), (720, 1366), (1080, 1920), (1920, 1080)] for fps in [25, 30, 50, 24]]
    for variant in variants:
        url = f"https://videos.pexels.com/video-files/{pexels_id}/{pexels_id}-{variant}.mp4"
        probe = subprocess.run(["curl.exe", "-s", "-I", "--max-time", "10", url], capture_output=True, text=True)
        if not re.search(r"HTTP/\S+ 200", probe.stdout):
            continue
        headers = probe.stdout
        size = re.search(r"(?im)^content-length:\s*(\d+)", headers)
        if size and int(size[1]) > 64_000_000:
            continue
        download = subprocess.run(["curl.exe", "-sS", "-L", "--fail", "--max-time", "90", "--max-filesize", "64000000", "-o", str(target), url], capture_output=True, text=True)
        if download.returncode == 0:
            record.update(download=url, bytes=target.stat().st_size, sha256=hash_file(target))
            print(identifier, "downloaded", record["bytes"], flush=True)
            return record
        target.unlink(missing_ok=True)
    record["error"] = "No downloadable variant under 64 MB found; not included in accuracy results."
    print(identifier, "unavailable", flush=True)
    return record


def main():
    (DATA / "footage").mkdir(parents=True, exist_ok=True)
    binary = ffmpeg()
    sources = list(ThreadPoolExecutor(max_workers=4).map(fetch, SOURCES))
    (HERE / "sources.json").write_text(json.dumps({"clips": sources, "decoder_sha256": hash_file(binary)}, indent=2), encoding="utf-8")
    store = Store(DATA / "app-data")
    if store.get("profile") and store.get("profile")["name"] != "Validation 2026-10-14":
        raise ValueError("Refusing to modify another player's workspace.")
    store.set("profile", domain.profile({"name": "Validation 2026-10-14", "age_band": "18+", "position": "Midfielder", "goal": "juggling", "equipment": ["ball"], "minutes": 15, "consent": True}))
    existing = {m["name"] for m in store.events("media")}
    metadata = []
    for source in sources:
        if "error" in source:
            continue
        clip = DATA / "footage" / source["file"]
        if source["file"] not in existing:
            name = source["sha256"][:32] + ".mp4"
            target = store.media / name
            if not target.exists():
                target.write_bytes(clip.read_bytes())
            store.append("media", {"filename": name, "name": source["file"], "size": source["bytes"], "sha256": source["sha256"], "mime": "video/mp4"})
        info = subprocess.run([str(binary), "-hide_banner", "-i", str(clip)], capture_output=True, text=True).stderr
        metadata.append({"id": source["id"], "ffmpeg_info": info})
        frames = DATA / "preview" / source["id"]
        frames.mkdir(parents=True, exist_ok=True)
        subprocess.run([str(binary), "-y", "-hide_banner", "-loglevel", "error", "-i", str(clip), "-vf", "fps=2,scale=480:-1", "-frames:v", "12", str(frames / "%02d.png")], check=True)
        images = sorted(frames.glob("*.png"))
        sheet = Image.new("RGB", (1440, 4 * 310), "#f4f5ed")
        draw = ImageDraw.Draw(sheet)
        for index, image in enumerate(images):
            tile = Image.open(image).convert("RGB")
            tile.thumbnail((470, 280))
            x, y = (index % 3) * 480, (index // 3) * 310
            sheet.paste(tile, (x, y + 25))
            draw.text((x + 5, y + 5), f"{source['id']} / {index*.5:.1f}s", fill="#133c30")
        sheet.save(DATA / (source["id"] + "-preview.jpg"))
    (HERE / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
