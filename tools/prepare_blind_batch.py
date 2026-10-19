"""Copy unchanged clips and empty task metadata for independent blind annotation."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def prepare(cases, root, output):
    root, output = Path(root).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError("Choose a new output folder; existing review work is never overwritten.")
    checked = []
    for index, case in enumerate(cases, 1):
        source = (root / case["file"]).resolve()
        if not source.is_relative_to(root) or not source.is_file() or source.suffix.lower() not in (".mp4", ".webm", ".mov"):
            raise ValueError("Every source must be a local video inside the project.")
        start, end = case["start"], case["end"]
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in (start, end)) or not 0 <= start < end <= 600 or end-start > 60:
            raise ValueError("Invalid annotation window.")
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        if digest != case["sha256"]:
            raise ValueError("Source hash changed; review the manifest before preparing a batch.")
        identity = f"review-{index:03d}"
        task = {"format": "football-labelling-task-1", "clip": {"id": identity, "filename": identity+source.suffix.lower(), "sha256": digest, "start": start, "end": end}, "conditions": []}
        checked.append((source, task, case))
    if not checked:
        raise ValueError("Choose at least one clip.")
    blind = output / "annotator"
    blind.mkdir(parents=True)
    coordinator = []
    for source, task, case in checked:
        shutil.copyfile(source, blind / task["clip"]["filename"])
        (blind / (task["clip"]["id"]+".task.json")).write_text(json.dumps(task, indent=2)+"\n", encoding="utf-8")
        coordinator.append({"task": task["clip"]["id"], "collection": case.get("collection"), "original_file": case["file"], "sha256": case["sha256"], "source": case.get("source"), "license": case.get("license"), "split": "diagnostic", "player_ids": [], "independent_labels_received": False})
    (output / "coordinator.json").write_text(json.dumps(coordinator, indent=2)+"\n", encoding="utf-8")
    rights = "\n".join(f"- {c['task']}: {c['license']} | {c['source']}" for c in coordinator)
    (blind / "README.md").write_text("""# Blind annotation handoff

Open Football Helper's blind evaluation labelling tool. Load a local video, then its matching .task.json using Load blind task. The task supplies only identity and window, never predictions or expected contacts. Select conditions from the footage yourself. Enter your own annotator identity and role; declare independence only if true.

Watch the window before labelling. Follow the same ball; label every 0.1-second sample as visible, absent, or occluded/uncertain. Mark clear contacts while inspecting intermediate frames; do not infer them from trajectory alone. Label the body part only when visible. Review the entire contact window even if there are no contacts. Export labels often; keep the video and task unchanged. Resume with Resume exported labels. Browser decode failures must be reported to the coordinator, not labelled absent.

Return the exported JSON and note any ambiguous frames. Do not view tracker output before finishing. Each annotator should work separately. The coordinator compares independent labels, records disagreements and adjudication, binds the review record to the final labels hash, verifies source/player grouping and audits corpus readiness before calibration. These initial short windows do not meet natural 30-second coverage requirements.

Source attribution (videos copied unchanged; respect each source's license):
"""+rights+"\n", encoding="utf-8")
    return coordinator


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "sdlc/visual-five.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        records = prepare(json.loads(args.manifest.read_text(encoding="utf-8")), ROOT, args.output)
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(1, str(error)+"\n")
    print(json.dumps({"clips": len(records), "collections": len({r["collection"] for r in records}), "output": str(args.output), "independent_labels_received": False}))
