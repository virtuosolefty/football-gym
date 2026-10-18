"""Score the recorded runs on the conditions screening against reference.json and audit.json.

Spot checks use the size-independent rule from reference.json (centre within 1.5 reference radii). The audit labels every emitted
detection, judged by eye on frames from the app's own video decoder; refusals and abstentions are reported, not scored as errors.
"""
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = ("detector", "colour", "detector-before-refusal-fix")


def spot_checks(clip, analysis):
    scale = clip["canvas_scale"]
    height_scale = clip["video_size"][1] / clip["video_size"][0]
    if height_scale > 2:  # the app narrows the tracking canvas for very tall video, which would shift these coordinates
        raise ValueError(f"{clip['id']}: portrait video taller than 2:1 is not supported by this scorer.")
    checked = detected = correct = 0
    for spot in clip["spots"]:
        checked += 1
        if spot["frame"] >= len(analysis["samples"]):
            continue
        sample = analysis["samples"][spot["frame"]]
        if not sample["found"]:
            continue
        detected += 1
        x, y = sample["x"] * 320 * scale, sample["y"] * 320 * height_scale * scale
        correct += math.hypot(x - spot["x"], y - spot["y"]) <= 1.5 * spot["radius"]
    return {"spot_checks": checked, "spot_detections": detected, "correct_spot_detections": correct}


def main():
    reference = {c["id"]: c for c in json.loads((HERE / "reference.json").read_text(encoding="utf-8"))["clips"]}
    audit = json.loads((HERE / "audit.json").read_text(encoding="utf-8"))["runs"]
    output = {}
    for label in RUNS:
        runs = json.loads((HERE / f"runs-{label}.json").read_text(encoding="utf-8"))
        rows = []
        for entry in runs["clips"]:
            clip = reference[entry["id"]]
            row = {"clip": entry["id"], "kind": clip["kind"], "window": clip["window"]}
            analysis = entry["analysis"]
            if analysis is None:
                rows.append({**row, "outcome": "refused", "message": entry["selection"]["error"]})
                continue
            found = [i for i, s in enumerate(analysis["samples"]) if s["found"]]
            labels = audit[label][entry["id"]]
            if found != labels["frames"]:
                raise ValueError(f"The audit does not cover the recorded {label}/{entry['id']} run.")
            wrong = set(labels["wrong_frames"])
            if not wrong <= set(found):
                raise ValueError(f"The audit marks frames wrong that {label}/{entry['id']} did not detect: {sorted(wrong - set(found))}.")
            rows.append({**row, "outcome": "tracked", "method": analysis["configuration"]["method"], "version": analysis["version"],
                         "samples": len(analysis["samples"]), "detected_frames": len(found), "coverage_percent": round(analysis["report"]["coverage"] * 100, 1),
                         "max_gap_seconds": analysis["report"]["max_gap_seconds"], "status": analysis["report"]["status"], "reasons": analysis["report"]["reasons"],
                         **spot_checks(clip, analysis), "audited_correct": len(found) - len(wrong), "audited_wrong": len(wrong),
                         "contact_proposals": len(analysis["candidates"]), "elapsed_ms": entry["elapsed_ms"]})
        output[label] = {"page_errors": runs["page_errors"], "clips": rows}
    (HERE / "results.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    for label, data in output.items():
        print(f"== {label} (page errors: {len(data['page_errors'])})")
        for r in data["clips"]:
            if r["outcome"] == "refused":
                print(f"  {r['clip']:11s} refused")
            else:
                print(f"  {r['clip']:11s} {r['status']:14s} cov {r['coverage_percent']:5.1f}%  spots {r['correct_spot_detections']}/{r['spot_checks']}  audited {r['audited_correct']}/{r['audited_correct'] + r['audited_wrong']} correct")


if __name__ == "__main__":
    main()
