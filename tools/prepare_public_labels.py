"""Fetch a 3-second, 10 Hz diagnostic subset from the dataset author's public label mirror.

Requires FFmpeg for video metadata. Does not claim blind independent annotation.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import urllib.request
import urllib.error

if __package__:
    from .fetch_evaluation import ROOT, DEST, CLIPS, fetch
else:
    from fetch_evaluation import ROOT, DEST, CLIPS, fetch

REVISION = "c6992050c74d6e3f6992bac0e314e7b378a0f51c"
BASE = "https://raw.githubusercontent.com/Zoutianjian/Ball-Yolo-A-Sport-Ball-Dataset/" + REVISION + "/"
NAMES = {"Game_1_1": "Game_Juven_Udinese_Boardcast_1", "Game_2_1": "Game_Livepool_Wolf_Boardcast_1",
         "Game_3_1": "Game_Real_Mardrid_ManCity_Boardcast_1", "Game_4_1": "Game_Torino_ACMilan_Boardcast_1"}


def parse_boxes(text):
    boxes = []
    for line in text.splitlines():
        fields = [float(value) for value in line.split()]
        if len(fields) != 5 or not all(math.isfinite(n) for n in fields) or any(not 0 <= n <= 1 for n in fields[1:]):
            raise ValueError("Invalid published YOLO label")
        boxes.append(fields)
    return boxes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    args = parser.parse_args()
    manifest = {"label_revision": REVISION, "source": BASE, "contacts_reviewed": False,
                "independent_blind_labels": False, "files": [], "clips": []}
    for name in CLIPS:
        video = DEST / "footBall" / "Videos" / (name + ".mp4")
        metadata = subprocess.run([args.ffmpeg, "-hide_banner", "-i", str(video)], capture_output=True, text=True).stderr
        stream = next(line for line in metadata.splitlines() if "Video:" in line)
        width, height = map(int, re.search(r"\b(\d{2,5})x(\d{2,5})\b", stream).groups())
        fps = float(re.search(r"(\d+(?:\.\d+)?) fps", stream).group(1))
        original = NAMES.get(name, name)
        requests = [(i/10, int(math.floor(i/10*fps + 1e-7))) for i in range(30)]
        def get_label(item):
            time, index = item
            path = f"footBall/Labels/{original}/{original}_{index}.txt"
            provenance = {"path": path, "frame_index": index, "sample_time": time, "url": BASE + path}
            try:
                data = fetch(BASE + path, DEST / "published-labels" / path, 100_000)
            except urllib.error.HTTPError as error:
                if error.code != 404:
                    raise
                return None, {**provenance, "status": "missing_label"}
            boxes = parse_boxes(data.decode("utf-8-sig"))
            label = {"time": time, "status": "absent" if not boxes else "occluded"}
            if len(boxes) == 1:
                _, x, y, w, h = boxes[0]
                label.update(status="visible", x=x, y=y, radius=max(1, min(w*width, h*height)/2))
            return label, {**provenance, "sha256": hashlib.sha256(data).hexdigest()}
        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(get_label, requests))
        digest = hashlib.sha256(video.read_bytes()).hexdigest()
        labels = {"format": "football-evaluation-1", "clip": {"id": name, "filename": video.name, "sha256": digest,
                  "width": width, "height": height, "start": 0, "end": 3},
                  "annotator": {"id": "Zou-Liu-public-dataset", "role": "external-dataset", "independent": False},
                  "conditions": [], "notes": "Published external ball boxes, mapped by the author's naming guide. Blind annotation protocol unverified; condition review and alignment spot-check required. Multiple boxes are marked uncertain. Blurred people prevent pose validation.",
                  "sample_interval": .1, "frames": [r[0] for r in results if r[0] is not None], "contacts": [], "contacts_reviewed": False,
                  "source": {"url": BASE, "revision": REVISION, "fps": fps}}
        output = ROOT / "evaluation" / "public-football-2026-10-17" / "labels"
        output.mkdir(parents=True, exist_ok=True)
        (output / (name + ".json")).write_text(json.dumps(labels, indent=2) + "\n", encoding="utf-8")
        manifest["files"].extend(r[1] for r in results)
        count = sum(r[0] is not None for r in results)
        manifest["clips"].append({"id": name, "fps": fps, "frames": count, "visible": sum(r[0] is not None and r[0]["status"] == "visible" for r in results)})
        print(name, count, "published frame labels downloaded;", 30-count, "unlabelled", flush=True)
        (output.parent / "label-sources.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
