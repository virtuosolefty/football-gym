"""Compare frozen production outputs with independently recorded visual spot checks."""
import csv
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from football import video


def matched_events(predictions, reference, tolerance=.15):
    available = list(reference)
    matched = 0
    for time in sorted(predictions):
        if not available:
            break
        nearest = min(available, key=lambda other: abs(time-other))
        if abs(nearest-time) <= tolerance:
            available.remove(nearest)
            matched += 1
    return matched


def main():
    reference = json.loads((HERE / "reference.json").read_text())
    for file, key in [(ROOT / "web/tracker.js", "frozen_tracker_sha256"), (ROOT / "football/video.py", "frozen_video_rules_sha256")]:
        if hashlib.sha256(file.read_bytes()).hexdigest() != reference[key]:
            raise ValueError("Production code changed; the recorded evaluation would no longer describe this version.")
    runs = {r["id"]: r for r in json.loads((HERE / "runs.json").read_text())}
    metadata = {m["id"]: m for m in json.loads((HERE / "capture-metadata.json").read_text())}
    detection_audit = {a["id"]: a for a in json.loads((HERE / "detection-audit.json").read_text())["clips"]}
    results = []
    audit = []
    for clip in reference["clips"]:
        run = runs[clip["id"]]
        analysis = run["analysis"]
        canvas = metadata[clip["id"]]["canvas"]
        correct = found = scorable = 0
        for index, x, y, radius in clip["points"]:
            sample = analysis["samples"][index]
            row = {"clip": clip["id"], "time": index/10, "reference_x": x, "reference_y": y, "reference_radius": radius,
                   "found": sample["found"], "predicted_x": sample["x"] * canvas["width"] if sample["found"] else None,
                   "predicted_y": sample["y"] * canvas["height"] if sample["found"] else None,
                   "scorable": x is not None, "correct_ball": None, "error_px": None}
            if x is not None:
                scorable += 1
                if sample["found"]:
                    found += 1
                    error = math.hypot(row["predicted_x"]-x, row["predicted_y"]-y)
                    row["error_px"] = round(error, 2)
                    row["correct_ball"] = error <= radius + 4
                    correct += row["correct_ball"]
                else:
                    row["correct_ball"] = False
            audit.append(row)
        window = clip["contact_window"]
        candidates = [p["time"] for p in analysis["candidates"] if window and window[0] <= p["time"] < window[1]]
        reference_contacts = clip["contacts"]
        matches = matched_events(candidates, reference_contacts) if reference_contacts is not None else None
        detected_times = [s["time"] for s in analysis["samples"] if s["found"]]
        decisions = detection_audit[clip["id"]]["detections"]
        if detected_times != [d[0] for d in decisions]:
            raise ValueError("The detection audit does not cover the current run.")
        correct_audit = sum(label == "correct" for _, label in decisions)
        wrong_audit = sum(label == "wrong" for _, label in decisions)
        unknown_audit = sum(label == "unknown" for _, label in decisions)
        results.append({"clip": clip["id"], "condition": clip["condition"], "activity": clip["activity"],
                        "sample_count": len(analysis["samples"]), "detected_frames": sum(s["found"] for s in analysis["samples"]),
                        "coverage_percent": round(analysis["report"]["coverage"]*100, 1), "max_gap_seconds": analysis["report"]["max_gap_seconds"],
                        "system_status": analysis["report"]["status"], "reasons": analysis["report"]["reasons"],
                        "spot_checks": len(clip["points"]), "scorable_spot_checks": scorable, "spot_detections": found, "correct_spot_detections": correct,
                        "correct_ball_recall_percent": round(correct/scorable*100, 1) if scorable else None,
                        "detected_ball_precision_percent": round(correct/found*100, 1) if found else None,
                        "audited_correct_detections": correct_audit, "audited_wrong_detections": wrong_audit, "audited_unknown_detections": unknown_audit,
                        "audited_detection_precision_percent": round(correct_audit/(correct_audit+wrong_audit)*100, 1) if correct_audit+wrong_audit else None,
                        "released_contact_proposals": len(analysis["candidates"]), "clear_reference_contacts": len(reference_contacts) if reference_contacts is not None else None,
                        "matched_contact_proposals": matches, "contact_recall_percent": round(matches/len(reference_contacts)*100, 1) if reference_contacts else None,
                        "diagnostic_ungated_turns": [p["time"] for p in video.candidates(analysis["samples"])],
                        "measurement_records_created": run["attempts"], "elapsed_ms_including_screenshot": run["elapsed_ms"]})
    (HERE / "results.json").write_text(json.dumps({"reference_method": reference["method"], "clips": results}, indent=2)+"\n")
    for name, rows in [("summary.csv", results), ("spot-checks.csv", audit)]:
        with (HERE / name).open("w", newline="", encoding="utf-8") as output:
            writer = csv.DictWriter(output, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
