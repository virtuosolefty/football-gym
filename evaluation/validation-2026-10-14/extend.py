"""Add frozen regression cases and full 30-second real-football windows to the isolated set."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from football.store import Store


def main():
    store = Store(ROOT / "test-results" / HERE.name / "app-data")
    assert store.get("profile")["name"] == "Validation 2026-10-14"
    reference = json.loads((HERE / "reference.json").read_text(encoding="utf-8"))
    existing_cases = {c["id"] for c in reference["clips"]}
    existing_media = {m["name"] for m in store.events("media")}
    cases = []
    for folder, names in [("conditions-footage", ["u17", "beach", "street", "futsal"]), ("other-footage", ["tennis", "aerial", "improvised"])]:
        old = json.loads((ROOT / "evaluation" / folder / "reference.json").read_text(encoding="utf-8"))["clips"]
        for clip in old:
            if clip["id"] not in names:
                continue
            source = ROOT / "test-results" / folder / "footage" / clip["file"]
            with source.open("rb") as file:
                digest = hashlib.file_digest(file, "sha256").hexdigest()
            filename = digest[:32] + source.suffix
            name = "regression-" + clip["file"]
            if name not in existing_media:
                (store.media / filename).write_bytes(source.read_bytes())
                store.append("media", {"filename": filename, "name": name, "size": source.stat().st_size, "sha256": digest, "mime": "video/mp4" if source.suffix == ".mp4" else "video/webm"})
            case = {"id": "regression-" + clip["id"], "file": name, "window": clip["window"], "seed_time": clip["window"][0],
                    "click_normalized": clip["click_normalized"], "radius": clip["radius_hint_canvas_px"], "kind": "old source regression: " + clip.get("condition", clip.get("note", "")), "prior_reference": str(Path("evaluation") / folder / "reference.json")}
            if case["id"] not in existing_cases:
                cases.append(case)
            if clip["id"] in ("aerial", "improvised"):
                full = {**case, "id": clip["id"] + "-30s", "window": [clip["window"][0], clip["window"][0] + 30], "kind": "full 30-second real-football window on existing source; not a new independent source"}
                if full["id"] not in existing_cases:
                    cases.append(full)
    reference["clips"].extend(cases)
    (HERE / "reference.json").write_text(json.dumps(reference, indent=2), encoding="utf-8")
    print("Added", len(cases), "cases")


if __name__ == "__main__":
    main()
