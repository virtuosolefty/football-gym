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


def contact_metrics(contacts, proposals, start, end):
    """Maximum chronological one-to-one matches, then minimum total timing error."""
    for name, events in (("contacts", contacts), ("proposals", proposals)):
        if not isinstance(events, list) or len(events) > 1200:
            raise ValueError(f"Invalid {name}.")
        seen = set()
        for event in events:
            t = number(event["time"], f"{name} time", start, end)
            allowed_sides = ("left", "right", "body", "unknown") if name == "contacts" else ("left", "right", "unknown")
            if t in seen or event.get("side", event.get("foot", "unknown")) not in allowed_sides:
                raise ValueError(f"Duplicate time or invalid side in {name}.")
            seen.add(t)
    contacts = sorted(contacts, key=lambda c: c["time"])
    proposals = sorted(proposals, key=lambda c: c["time"])
    # A chronological optimal match exists for this absolute-time distance metric.
    choices = [bytearray(len(proposals) + 1) for _ in range(len(contacts) + 1)]
    previous = [(0, 0)] * (len(proposals) + 1)
    for i, contact in enumerate(contacts, 1):
        current = [(0, 0)]
        for j, proposal in enumerate(proposals, 1):
            best, action = previous[j], 1
            if current[j-1] > best:
                best, action = current[j-1], 2
            distance = abs(contact["time"] - proposal["time"])
            if distance <= .15 + 1e-9:
                candidate = (previous[j-1][0] + 1, previous[j-1][1] - distance)
                if candidate > best:
                    best, action = candidate, 3
            current.append(best)
            choices[i][j] = action
        previous = current
    matches = []
    i, j = len(contacts), len(proposals)
    while i and j:
        action = choices[i][j]
        if action == 3:
            contact, proposal = contacts[i-1], proposals[j-1]
            matches.append({"label": contact["time"], "proposal": proposal["time"],
                            "offset_seconds": round(proposal["time"] - contact["time"], 6),
                            "label_side": contact.get("side", contact.get("foot", "unknown")),
                            "proposal_side": proposal.get("side", "unknown")})
            i -= 1
            j -= 1
        elif action == 1:
            i -= 1
        else:
            j -= 1
    matches.reverse()
    labelled_sides = [m for m in matches if m["label_side"] in ("left", "right")]
    predicted_sides = [m for m in labelled_sides if m["proposal_side"] != "unknown"]
    correct_sides = sum(m["label_side"] == m["proposal_side"] for m in predicted_sides)
    return {"contact_matches": matches, "missed_contacts": len(contacts)-len(matches),
            "false_contact_proposals": len(proposals)-len(matches),
            "contact_precision": round(len(matches)/len(proposals), 4) if proposals else None,
            "contact_recall": round(len(matches)/len(contacts), 4) if contacts else None,
            "contact_mean_absolute_error_seconds": round(sum(abs(m["offset_seconds"]) for m in matches)/len(matches), 6) if matches else None,
            "contact_side_accuracy": round(correct_sides/len(predicted_sides), 4) if predicted_sides else None,
            "contact_side_coverage": round(len(predicted_sides)/len(labelled_sides), 4) if labelled_sides else None,
            "contact_match_tolerance_seconds": .15}


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
    if not 0 < end-start <= 60 or run["start"] != start or run["end"] != end or run["width"] != width or run["height"] != height:
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
    samples = run["samples"]
    if not isinstance(samples, list) or not 1 <= len(samples) <= 1200:
        raise ValueError("Use 1–1,200 analysis samples.")
    sample_times, used_labels = set(), set()
    for sample in samples:
        t = number(sample["time"], "sample time", start, end)
        if t in sample_times or not isinstance(sample.get("found"), bool):
            raise ValueError("Duplicate sample time or invalid found flag.")
        sample_times.add(t)
        if sample["found"]:
            number(sample["x"], "sample x", 0, 1)
            number(sample["y"], "sample y", 0, 1)
        if sample.get("score") is not None:
            number(sample["score"], "sample score", 0, 1)
        nearest = min(frames, key=lambda frame: abs(frame["time"] - t))
        # Do not borrow another frame's ground truth, especially around a contact or edge exit.
        if abs(nearest["time"] - t) > .005:
            counts["unlabelled"] += 1
            continue
        if nearest["time"] in used_labels:
            raise ValueError("Multiple analysis samples would reuse the same frame label.")
        used_labels.add(nearest["time"])
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
    metrics = contact_metrics(labels.get("contacts", []), run.get("candidates", []), start, end)
    if not contacts_reviewed:
        metrics = {key: ([] if key == "contact_matches" else .15 if key == "contact_match_tolerance_seconds" else None) for key in metrics}
    return {"clip_id": clip["id"], "annotator": annotator, "independent_self_declared": independent,
            "conditions": labels.get("conditions", []), "version": run.get("version"), "window_seconds": end-start,
            "counts": counts, "labelled_sample_fraction": round((len(audited)/len(run["samples"])), 4) if run["samples"] else 0,
            "correct_detection_precision": round(counts["correct"]/emitted, 4) if emitted else None,
            "correct_sample_fraction": round((counts["correct"]+counts["correct_absent"])/usable, 4) if usable else None,
            "mean_position_error_pixels": round(sum(errors)/len(errors), 3) if errors else None,
            "contact_labels_complete": contacts_reviewed,
            **metrics, "audit": audited}


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
