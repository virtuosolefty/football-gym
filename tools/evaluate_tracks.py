"""Evaluate an exported analysis against blind labels; no inferred labels or tuned thresholds."""
import argparse
import hashlib
import json
import math
from pathlib import Path


def number(value, name, low=0, high=math.inf):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"Invalid {name}.")
    return value


def evaluate(labels, run, video_hash=None, allow_implementer=False):
    if labels.get("format") != "football-evaluation-1":
        raise ValueError("Unsupported evaluation labels.")
    annotator = labels.get("annotator", {})
    independent = annotator.get("independent") is True and annotator.get("role") in ("coach", "second-annotator")
    if not independent and not allow_implementer:
        raise ValueError("Independent blind labels are required. Use --allow-implementer only for diagnostics.")
    clip = labels["clip"]
    if not clip.get("sha256") or (run.get("media_sha256") or video_hash) != clip["sha256"]:
        raise ValueError("Video hash mismatch or missing hash. For a legacy run, supply --video.")
    width, height = number(clip["width"], "width", 16, 7680), number(clip["height"], "height", 16, 4320)
    start, end = number(clip["start"], "start"), number(clip["end"], "end")
    if end <= start or run["start"] != start or run["end"] != end or run["width"] != width or run["height"] != height:
        raise ValueError("Analysis and labels must use the same window and dimensions.")
    frames = labels.get("frames")
    if not isinstance(frames, list) or not 1 <= len(frames) <= 1200:
        raise ValueError("Use 1–1,200 frame labels.")
    seen = set()
    for frame in frames:
        t = number(frame["time"], "label time", start, end)
        if t in seen or frame.get("status") not in ("visible", "absent", "occluded"):
            raise ValueError("Invalid or duplicate frame labels.")
        seen.add(t)
        if frame["status"] == "visible":
            number(frame["x"], "x", 0, 1); number(frame["y"], "y", 0, 1); number(frame["radius"], "radius", 1, 500)
    counts = {key: 0 for key in ("correct", "wrong", "missed_visible", "correct_absent", "occluded", "unlabelled")}
    errors, audited = [], []
    for sample in run["samples"]:
        t = number(sample["time"], "sample time", start, end)
        nearest = min(frames, key=lambda frame: abs(frame["time"] - t))
        # Do not borrow another frame's ground truth, especially around a contact or edge exit.
        if abs(nearest["time"] - t) > .005:
            counts["unlabelled"] += 1
            continue
        status = nearest["status"]
        distance = None
        if status == "occluded":
            outcome = "occluded"
        elif status == "absent":
            outcome = "wrong" if sample["found"] else "correct_absent"
        elif not sample["found"]:
            outcome = "missed_visible"
        else:
            x,y=number(sample["x"], "sample x", 0, 1),number(sample["y"], "sample y", 0, 1)
            distance = math.hypot((x-nearest["x"])*width, (y-nearest["y"])*height)
            errors.append(distance)
            outcome = "correct" if distance <= nearest["radius"] else "wrong"
        counts[outcome] += 1
        audited.append({"time": t, "outcome": outcome, "error_pixels": round(distance, 3) if distance is not None else None, "score": sample.get("score")})
    usable = counts["correct"] + counts["wrong"] + counts["missed_visible"] + counts["correct_absent"]
    emitted = counts["correct"] + counts["wrong"]
    contacts_reviewed = labels.get("contacts_reviewed") is True
    contacts = labels.get("contacts", []) if contacts_reviewed else []
    matched, unmatched = [], list(run.get("candidates", []))
    for contact in contacts:
        t = number(contact["time"], "contact time", start, end)
        proposal = min(unmatched, key=lambda c: abs(c["time"] - t)) if unmatched else None
        if proposal and abs(proposal["time"] - t) <= .15:
            matched.append({"label": t, "proposal": proposal["time"], "offset_seconds": round(proposal["time"] - t, 3)})
            unmatched.remove(proposal)
    return {"clip_id": clip["id"], "annotator": annotator, "independent_self_declared": independent,
            "conditions": labels.get("conditions", []), "version": run.get("version"), "window_seconds": end-start,
            "counts": counts, "labelled_sample_fraction": round((len(audited)/len(run["samples"])), 4) if run["samples"] else 0,
            "correct_detection_precision": round(counts["correct"]/emitted, 4) if emitted else None,
            "correct_sample_fraction": round((counts["correct"]+counts["correct_absent"])/usable, 4) if usable else None,
            "mean_position_error_pixels": round(sum(errors)/len(errors), 3) if errors else None,
            "contact_labels_complete": contacts_reviewed,
            "contact_matches": matched, "missed_contacts": len(contacts)-len(matched) if contacts_reviewed else None,
            "false_contact_proposals": len(unmatched) if contacts_reviewed else None,
            "contact_match_tolerance_seconds": .15, "audit": audited}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels", required=True, type=Path)
    parser.add_argument("--run", required=True, type=Path, help="One exported analysis object, not an entire workspace")
    parser.add_argument("--video", type=Path, help="Original clip, only needed for runs without media_sha256")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--allow-implementer", "--allow-unverified", dest="allow_implementer", action="store_true",
                        help="Diagnostic use only: accept implementer or external labels without verified blind independence")
    args = parser.parse_args()
    try:
        digest = None
        if args.video:
            with args.video.open("rb") as file:
                digest = hashlib.file_digest(file, "sha256").hexdigest()
        result = evaluate(json.loads(args.labels.read_text(encoding="utf-8")), json.loads(args.run.read_text(encoding="utf-8")), digest, args.allow_implementer)
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(1, f"Evaluation refused: {error}\n")
    text = json.dumps(result, indent=2)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    main()
