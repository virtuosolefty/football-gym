"""Prepare an isolated workspace holding the downloaded clips (run tools/fetch first; see REPORT.md). Normal app data is never touched."""
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
    store = Store(ROOT / "test-results" / "other-footage" / "app-data")
    if store.get("profile") and store.get("profile")["name"] != "Other footage evaluation":
        raise ValueError("Refusing to modify a workspace belonging to someone else.")
    store.set("profile", domain.profile({"name": "Other footage evaluation", "age_band": "18+", "position": "Midfielder", "goal": "juggling",
                                         "equipment": ["ball"], "minutes": 15, "consent": True}))
    existing = {m["name"] for m in store.events("media")}
    for clip in json.loads((Path(__file__).parent / "reference.json").read_text(encoding="utf-8"))["clips"]:
        if clip["file"] in existing:
            continue
        source = ROOT / "test-results" / "other-footage" / "footage" / clip["file"]
        suffix = source.suffix
        name = uuid.uuid4().hex + suffix
        shutil.copyfile(source, store.media / name)
        store.append("media", {"name": clip["file"], "filename": name, "mime": "video/mp4" if suffix == ".mp4" else "video/webm", "size": source.stat().st_size})
    print(json.dumps({"media": len(store.events("media")), "data_directory": str(store.directory)}))


if __name__ == "__main__":
    main()
