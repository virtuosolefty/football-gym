"""Download a bounded public football evaluation pack, preserving external provenance.

These are public third-party detection annotations, not our blind coach labels.
The videos have blurred people and do not validate foot-contact inference.
"""
import hashlib
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "test-results" / "public-football-2026-10-17"
REVISION = "7981dcadb2c268808413f5f4d6bdbc25dbfbae75"
BASE = "https://raw.githubusercontent.com/Zoutianjian/Videos-For-Sport-Ball-Detection-Dataset/" + REVISION + "/"
CLIPS = ["Game_1_1", "Game_2_1", "Game_3_1", "Game_4_1", "Pass_Training_1_1", "Pass_Training_2_1",
         "Seven_Air_1", "Seven_Audience_1_1", "Seven_Audience_2_1", "dribble_Top_10_1", "dribble_Training_2_1", "shot_Training_1_1"]


def fetch(url, path, limit):
    if path.exists():
        return path.read_bytes()
    with urllib.request.urlopen(url, timeout=60) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError("Download exceeds the declared size limit: " + url)
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + ".part")
    partial.write_bytes(data)
    partial.replace(path)
    return data


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    manifest = {"source": "https://doi.org/10.5061/dryad.3bk3j9m13", "video_revision": REVISION,
                "annotation_provenance": "External published ball boxes; independence and blind protocol not verified. No contact labels.",
                "limitations": "Blurred people; match/training footage, not a representative juggling benchmark. Conditions need human review.",
                "files": [], "errors": []}
    urls = [(BASE + name, name, 100_000) for name in ["README.md", "LICENSE.md", "footBall/README.md", "footBall/Videos/README.MD"]]
    urls += [(BASE + f"footBall/Videos/{name}.mp4", f"footBall/Videos/{name}.mp4", 64*1024*1024) for name in CLIPS]
    urls += [("https://datadryad.org/downloads/file_stream/4736298", "footBall-labels.zip", 10*1024*1024)]
    for url, name, limit in urls:
        try:
            data = fetch(url, DEST / name, limit)
            if name.endswith(".zip") and not data.startswith(b"PK"):
                raise ValueError("The annotation response was not a ZIP archive.")
            manifest["files"].append({"path": name, "url": url, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
            print(f"Downloaded {name}: {len(data):,} bytes", flush=True)
        except (OSError, ValueError) as error:
            manifest["errors"].append({"path": name, "error": str(error)})
            print(f"Unavailable {name}: {error}", flush=True)
        target = ROOT / "evaluation" / "public-football-2026-10-17" / "sources.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    if manifest["errors"]:
        raise SystemExit("Some files could not be downloaded; see sources.json. Existing successful downloads are preserved.")


if __name__ == "__main__":
    main()
