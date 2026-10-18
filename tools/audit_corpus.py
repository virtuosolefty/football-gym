"""Check whether a corpus has the evidence needed for calibration and held-out evaluation."""
import argparse
import hashlib
import json
import math
from pathlib import Path

try:
    from .evaluate_tracks import evaluate
except ImportError:
    from evaluate_tracks import evaluate

CONDITIONS = ("night", "rain", "small", "fast", "juggling-30s")
SPLITS = ("calibration", "held-out")


def local_file(root, name):
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Missing evidence path.")
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError(f"Evidence must be an existing file inside the manifest folder: {name}")
    return path


def audit(manifest, root):
    if manifest.get("format") != "football-corpus-1" or not isinstance(manifest.get("clips"), list):
        raise ValueError("Unsupported corpus manifest.")
    rows, ids, problems = [], set(), []
    groups = {key: {} for key in ("sha256", "source_id", "player_id")}
    coverage = {split: {condition: set() for condition in CONDITIONS} for split in SPLITS}
    for entry in manifest["clips"]:
        clip_id = entry.get("id")
        if not isinstance(clip_id, str) or not clip_id.strip() or clip_id in ids:
            raise ValueError("Missing or duplicate clip id.")
        ids.add(clip_id)
        split = entry.get("split")
        if split not in (*SPLITS, "diagnostic"):
            raise ValueError(f"Invalid split: {clip_id}")
        reasons = []
        labels_path = local_file(root, entry.get("labels"))
        labels = json.loads(labels_path.read_text(encoding="utf-8"))
        clip = labels["clip"]
        if clip["id"] != clip_id:
            raise ValueError(f"Clip id does not match labels: {clip_id}")
        # Reuse the evaluator's frame/contact validation, without inventing detections.
        run = {**clip, "media_sha256": clip["sha256"], "samples": [{"time": f["time"], "found": False} for f in labels["frames"]]}
        result = evaluate(labels, run, allow_implementer=True)
        if not result["independent_self_declared"] or not labels.get("annotator", {}).get("id"):
            reasons.append("No independent coach/second-annotator declaration")
        if labels.get("contacts_reviewed") is not True:
            reasons.append("Contacts not reviewed over the full window")
        if entry.get("alignment_reviewed") is not True:
            reasons.append("Frame/label alignment not reviewed")
        review = entry.get("blind_review", {})
        if not isinstance(review, dict):
            raise ValueError(f"Invalid blind review: {clip_id}")
        if not review.get("reviewer") or not review.get("record"):
            reasons.append("No recorded blind annotation review")
        else:
            local_file(root, review["record"])
            if review.get("labels_sha256") != hashlib.sha256(labels_path.read_bytes()).hexdigest():
                reasons.append("Blind review does not bind to the current labels hash")
        source = entry.get("source_id")
        players = entry.get("player_ids")
        if not isinstance(source, str) or not source.strip():
            reasons.append("Unknown source grouping")
        if not isinstance(players, list) or not players or any(not isinstance(p, str) or not p.strip() for p in players):
            reasons.append("Unknown player grouping")
            players = []
        digest = clip["sha256"]
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError(f"Invalid video SHA-256: {clip_id}")
        expected = [round(clip["start"] + i / 10, 6) for i in range(math.ceil((clip["end"]-clip["start"]) * 10 - 1e-7))]
        times = [f["time"] for f in labels["frames"]]
        if any(not any(abs(t - f) <= .005 for f in times) for t in expected):
            reasons.append("Incomplete 10 Hz frame labels")
        if not any(f["status"] == "visible" for f in labels["frames"]):
            reasons.append("No visible ball labels")
        conditions = labels.get("conditions", [])
        if not isinstance(conditions, list) or any(not isinstance(c, str) for c in conditions):
            raise ValueError(f"Invalid conditions: {clip_id}")
        if "juggling-30s" in conditions and clip["end"]-clip["start"] < 29.95:
            reasons.append("Full-window juggling label is shorter than 30 seconds")
        if split in SPLITS:
            for key, values in (("sha256", [digest]), ("source_id", [source] if source else []), ("player_id", players)):
                for value in values:
                    groups[key].setdefault(value, set()).add(split)
            if not reasons:
                for condition in CONDITIONS:
                    if condition in conditions:
                        coverage[split][condition].add(digest)
        rows.append({"id": clip_id, "split": split, "eligible": split in SPLITS and not reasons, "issues": reasons})
    for key, values in groups.items():
        for value, splits in values.items():
            if len(splits) > 1:
                problems.append(f"Split leakage: {key} {value}")
    for row in rows:
        if row["split"] in SPLITS:
            problems.extend(f"{row['id']}: {reason}" for reason in row["issues"])
    counts = {split: {condition: len(hashes) for condition, hashes in values.items()} for split, values in coverage.items()}
    for split, values in counts.items():
        for condition, count in values.items():
            if count < 3:
                problems.append(f"{split}: {condition} needs {3-count} more eligible distinct videos (minimum 3)")
    return {"ready_for_calibration_and_validation": not problems,
            "note": "Evidence readiness only; not an accuracy certification. Review records and identities require human verification.",
            "required_distinct_videos_per_condition_per_split": 3, "coverage": counts, "blockers": problems, "clips": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = audit(json.loads(args.manifest.read_text(encoding="utf-8")), args.manifest.parent)
        text = json.dumps(result, indent=2) + "\n"
        if args.output:
            args.output.write_text(text, encoding="utf-8")
        else:
            print(text, end="")
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(1, f"Corpus audit refused: {error}\n")
    raise SystemExit(0 if result["ready_for_calibration_and_validation"] else 2)


if __name__ == "__main__":
    main()
