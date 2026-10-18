"""Prepare a separate evaluation workspace, preserving all normal app data."""
import json
import shutil
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from football import domain
from football.store import Store


def main():
    store = Store(ROOT / "test-results" / "real-footage" / "app-data")
    if store.get("profile") and store.get("profile")["name"] != "Footage evaluation":
        raise ValueError("Refusing to modify a workspace belonging to someone else.")
    store.set("profile", domain.profile({"name": "Footage evaluation", "age_band": "18+", "position": "Midfielder", "goal": "juggling",
                                         "equipment": ["ball", "wall", "markers", "cones"], "minutes": 15, "consent": True}))
    existing = {m["name"] for m in store.events("media")}
    for clip in json.loads((Path(__file__).parent / "sources.json").read_text())["clips"]:
        if clip["file"] in existing:
            continue
        source = ROOT / "test-results" / "real-footage" / "footage" / clip["file"]
        name = uuid.uuid4().hex + ".mp4"
        shutil.copyfile(source, store.media / name)
        store.append("media", {"name": clip["file"], "filename": name, "mime": "video/mp4", "size": source.stat().st_size,
                               "source_url": clip["page"], "license_url": "https://www.pexels.com/license/"})
    print(json.dumps({"profile": "Footage evaluation", "media": len(store.events("media")), "data_directory": str(store.directory)}))


if __name__ == "__main__":
    main()
