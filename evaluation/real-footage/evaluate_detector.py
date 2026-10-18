"""Score the recorded detector-ball-1 run: pre-registered spot checks, the full detection audit, and contact proposals.

Reads detector-runs.json (from run-detector.js), reference.json and detector-audit.json; writes detector-results.json.
Unlike evaluate.py this does not pin production file hashes: it describes the run that is recorded in detector-runs.json.
"""
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
CANVAS = {"daylight": (320, 569), "indoor": (320, 180), "strobe": (320, 169)}


def spot_checks(clip, samples, canvas):
    scorable = correct = found = 0
    centre_errors = []
    for index, x, y, radius in clip["points"]:
        if x is None:
            continue
        scorable += 1
        sample = samples[index]
        if not sample["found"]:
            continue
        found += 1
        error = math.hypot(sample["x"] * canvas[0] - x, sample["y"] * canvas[1] - y)
        centre_errors.append(error / radius)
        correct += error <= radius + 4
    return {"scorable_spot_checks": scorable, "spot_detections": found, "correct_spot_detections": correct,
            "mean_centre_error_in_radii": round(sum(centre_errors) / len(centre_errors), 2) if centre_errors else None}


def main():
    reference = {c["id"]: c for c in json.loads((HERE / "reference.json").read_text(encoding="utf-8"))["clips"]}
    audit = {a["id"]: a for a in json.loads((HERE / "detector-audit.json").read_text(encoding="utf-8"))["clips"]}
    runs = json.loads((HERE / "detector-runs.json").read_text(encoding="utf-8"))
    results = []
    for entry in runs["clips"]:
        clip, analysis = reference[entry["id"]], entry["analysis"]
        samples = analysis["samples"]
        decisions = audit[entry["id"]]["detections"]
        if [s["time"] for s in samples if s["found"]] != [d[0] for d in decisions]:
            raise ValueError(f"The detection audit does not cover the recorded {entry['id']} run.")
        labels = [label for _, label in decisions]
        window = clip["contact_window"]
        proposals = [p["time"] for p in analysis["candidates"] if window and window[0] <= p["time"] < window[1]]
        results.append({"clip": entry["id"], "version": analysis["version"], "method": analysis["configuration"]["method"],
                        "detector": analysis["configuration"].get("detector"), "fitted_radius_px": analysis["configuration"]["seed"]["radius"],
                        "sample_count": len(samples), "detected_frames": len(decisions),
                        "coverage_percent": round(analysis["report"]["coverage"] * 100, 1), "max_gap_seconds": analysis["report"]["max_gap_seconds"],
                        "system_status": analysis["report"]["status"], "reasons": analysis["report"]["reasons"],
                        **spot_checks(clip, samples, CANVAS[entry["id"]]),
                        "audited_correct_detections": labels.count("correct"), "audited_wrong_detections": labels.count("wrong"),
                        "audited_precision_percent": round(labels.count("correct") / len(labels) * 100, 1) if labels else None,
                        "min_detection_score": min((s["score"] for s in samples if s["found"]), default=None),
                        "released_contact_proposals": len(analysis["candidates"]), "clear_reference_contacts": len(clip["contacts"]) if clip["contacts"] is not None else None,
                        "matched_contact_proposals": len(proposals) if clip["contacts"] else None,
                        "measurement_records_created": entry["attempts"], "elapsed_ms": entry["elapsed_ms"]})
    (HERE / "detector-results.json").write_text(json.dumps({"page_errors": runs["page_errors"], "clips": results}, indent=2) + "\n")
    for row in results:
        print({k: row[k] for k in ("clip", "coverage_percent", "max_gap_seconds", "system_status", "correct_spot_detections", "scorable_spot_checks",
                                    "audited_correct_detections", "audited_wrong_detections", "released_contact_proposals")})


if __name__ == "__main__":
    main()
