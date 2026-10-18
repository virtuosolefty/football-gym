"""Versioned video evidence and deterministic summaries; vision proposals never own scores."""
import math
from . import domain
from .knowledge import PROTOCOL

VERSIONS = {"colour": "contrast-ball-4", "detector": "detector-ball-3"}
DETECTOR_MODELS = ["yolox_nano", "yolox_tiny", "yolox_s"]
POSE_MODEL = "mediapipe-pose-lite-1"


def pose_sample(value):
    if not isinstance(value, dict) or set(value) - {"status", "left", "right"}:
        raise domain.ValidationError("Invalid foot pose evidence.")
    result = {"status": domain.choice(value.get("status"), ["single", "multiple", "absent"], "pose status")}
    for side in ("left", "right"):
        if side not in value:
            continue
        foot = value[side]
        if result["status"] != "single" or not isinstance(foot, list) or len(foot) != 3:
            raise domain.ValidationError("Foot evidence needs one person and three landmarks.")
        result[side] = []
        for point in foot:
            if not isinstance(point, list) or len(point) != 3:
                raise domain.ValidationError("A foot landmark needs x, y and visibility.")
            result[side].append([domain.number(n, "Foot landmark", 0, 1) for n in point])
    return result


def foot_evidence(sample, width, height):
    """Proximity supports a trajectory turn; it cannot establish physical contact."""
    pose = sample.get("pose", {})
    if pose.get("status") != "single" or "radius" not in sample:
        return {"side": "unknown", "pose_support": "unavailable"}
    close = []
    for side in ("left", "right"):
        foot = pose.get(side)
        if not foot or min(p[2] for p in foot) < .5:
            continue
        def distance(a, b):
            return math.hypot((a[0]-b[0])*width, (a[1]-b[1])*height)
        ball = (sample["x"], sample["y"])
        heel, toe = foot[1], foot[2]
        # shortcut: two ball radii plus heel-to-toe span is provisional; calibrate with independent contact labels.
        if min(distance(ball, p) for p in foot) <= 2*sample["radius"]*width + distance(heel, toe):
            close.append(side)
    return {"side": close[0] if len(close) == 1 else "unknown",
            "pose_support": "near_foot" if len(close) == 1 else "ambiguous" if close else "no_near_foot"}


def detector_config(data):
    config = data.get("detector")
    if not isinstance(config, dict):
        raise domain.ValidationError("A detector run needs its model configuration.")
    return {"model": domain.choice(config.get("model"), DETECTOR_MODELS, "detector model"),
            "size": domain.number(config.get("size"), "Detector input size", 64, 1280, True),
            "score_threshold": domain.number(config.get("score_threshold"), "Detector score threshold", 0, 1)}


def track_quality(samples, width, height, limits=None):
    """Expose diagnostics without inventing confidence/motion thresholds from a few clips."""
    limits = {} if limits is None else limits
    if not isinstance(limits, dict) or set(limits) - {"min_score", "max_speed", "max_stationary_seconds"}:
        raise domain.ValidationError("Unknown track quality limits.")
    checked = {key: domain.number(value, key, 0, 1 if key == "min_score" else 1000) for key, value in limits.items()}
    found = [s for s in samples if s["found"]]
    scores = [s["score"] for s in found if "score" in s]
    speeds, still_start, stationary = [], None, 0
    for a, b in zip(found, found[1:]):
        if a.get("segment", 0) == b.get("segment", 0) and b["time"] - a["time"] <= .35:
            distance = math.hypot(b["x"] - a["x"], (b["y"] - a["y"]) * height / width)
            speeds.append(distance / (b["time"] - a["time"]))
    for a, b in zip(samples, samples[1:]):
        if not a["found"] or not b["found"] or a.get("segment", 0) != b.get("segment", 0):
            still_start = None
            continue
        distance = math.hypot(b["x"] - a["x"], (b["y"] - a["y"]) * height / width)
        if distance <= 1 / width:
            still_start = a["time"] if still_start is None else still_start
            stationary = max(stationary, b["time"] - still_start)
        else:
            still_start = None
    metrics = {"min_score": min(scores) if scores else None, "mean_score": round(sum(scores) / len(scores), 4) if scores else None,
               "scored_detections": len(scores), "found_detections": len(found),
               "max_speed": round(max(speeds, default=0), 4), "max_stationary_seconds": round(stationary, 3)}
    reasons = []
    if "min_score" in checked and (len(scores) != len(found) or any(score < checked["min_score"] for score in scores)):
        reasons.append("Low or missing detection confidence.")
    if "max_speed" in checked and max(speeds, default=0) > checked["max_speed"]:
        reasons.append("Implausible track motion exceeds the configured limit.")
    if "max_stationary_seconds" in checked and stationary > checked["max_stationary_seconds"]:
        reasons.append("The track stays put longer than the configured limit.")
    # All three limits must be deliberately supplied; coverage alone cannot pass this gate.
    configured = len(checked) == 3
    return {"metrics": metrics, "limits": checked, "configured": configured, "validated": False,
            "reasons": reasons, "status": "SUSPECT" if reasons or not configured else "REVIEW_REQUIRED"}


def analysis(data):
    protocol = domain.choice(data.get("protocol"), list(PROTOCOL), "video protocol")
    duration = domain.number(data.get("duration"), "Decoded clip duration", .1, 600)
    start = domain.number(data.get("start"), "Window start", 0, duration)
    end = domain.number(data.get("end"), "Window end", start + .1, min(duration, start + 60))
    width = domain.number(data.get("width"), "Video width", 16, 7680, True)
    height = domain.number(data.get("height"), "Video height", 16, 4320, True)
    method = domain.choice(data.get("method", "colour"), list(VERSIONS), "tracking method")
    detector = detector_config(data) if method == "detector" else None
    pose_model = domain.choice(data["pose_model"], [POSE_MODEL], "pose model") if data.get("pose_model") is not None else None
    samples = data.get("samples", [])
    if not isinstance(samples, list) or len(samples) > 1200:
        raise domain.ValidationError("Use at most 1,200 track samples.")
    normalized, previous = [], -1
    seed = data.get("seed")
    if seed is not None:
        colour = seed.get("colour") if isinstance(seed, dict) else None
        if not isinstance(seed, dict) or (colour is None and method == "colour") or (colour is not None and (not isinstance(colour, list) or len(colour) != 3)):
            raise domain.ValidationError("A ball seed needs a normalized centre, radius and, for colour tracking, an RGB colour.")
        checked = {"x": domain.number(seed.get("x"), "Seed x", 0, 1), "y": domain.number(seed.get("y"), "Seed y", 0, 1),
                   "radius": domain.number(seed.get("radius"), "Seed radius", 2, 40)}
        if colour is not None:
            checked["colour"] = [domain.number(c, "Seed colour channel", 0, 255, True) for c in colour]
        if "time" in seed:  # The frame the ball was clicked on; tracking runs forward and backward from it.
            checked["time"] = domain.number(seed["time"], "Seed frame time", start, end)
        seed = checked
    reseeds = data.get("reseeds", [])
    if not isinstance(reseeds, list) or len(reseeds) > 1200:
        raise domain.ValidationError("Use at most 1,200 ball confirmations.")
    confirmations = []
    for item in reseeds:
        if not isinstance(item, dict):
            raise domain.ValidationError("Ball confirmations must be objects.")
        confirmations.append({"time": domain.number(item.get("time"), "Confirmation time", start, end),
                              "x": domain.number(item.get("x"), "Confirmation x", 0, 1),
                              "y": domain.number(item.get("y"), "Confirmation y", 0, 1),
                              "radius": domain.number(item.get("radius"), "Confirmation radius", 2, 40),
                              "segment": domain.number(item.get("segment"), "Track segment", 1, 1200, True)})
    if len({item["segment"] for item in confirmations}) != len(confirmations):
        raise domain.ValidationError("Ball confirmation segments must be unique.")
    for sample in samples:
        if not isinstance(sample, dict):
            raise domain.ValidationError("Track samples must be objects.")
        time = domain.number(sample.get("time"), "Frame timestamp", start, end)
        if time <= previous:
            raise domain.ValidationError("Frame timestamps must be strictly increasing.")
        previous = time
        found = domain.flag(sample.get("found"), "Ball detection")
        point = {"time": time, "found": found,
                 "x": domain.number(sample.get("x"), "Ball x", 0, 1) if found else None,
                 "y": domain.number(sample.get("y"), "Ball y", 0, 1) if found else None}
        if found and "score" in sample:
            point["score"] = domain.number(sample["score"], "Detection confidence", 0, 1)
        if found and "radius" in sample:
            point["radius"] = domain.number(sample["radius"], "Normalized ball radius", .00001, 1)
        if "pose" in sample:
            if not pose_model:
                raise domain.ValidationError("Pose evidence requires its model provenance.")
            point["pose"] = pose_sample(sample["pose"])
        if "segment" in sample:
            point["segment"] = domain.number(sample["segment"], "Track segment", 0, 1200, True)
            if point["segment"] and not any(item["segment"] == point["segment"] for item in confirmations):
                raise domain.ValidationError("A new track segment needs a ball confirmation.")
        if "lost_reason" in sample:
            point["lost_reason"] = domain.choice(sample["lost_reason"], ["seed_missing", "edge_exit", "gap", "scene_change"], "track loss reason")
        normalized.append(point)
    coverage = round(sum(s["found"] for s in normalized) / len(normalized), 3) if normalized else 0
    reliable = [s for s in normalized if s["found"]]
    gaps = [reliable[0]["time"] - start, end - reliable[-1]["time"]] if reliable else [end - start]
    gaps += [b["time"] - a["time"] for a, b in zip(reliable, reliable[1:])]
    gap = round(max(gaps), 3)
    reasons = []
    if width < 320 or height < 180:
        reasons.append("Low video resolution; use a closer, clearer view.")
    if len(normalized) < 20:
        reasons.append("Too few sampled frames for track suggestions.")
    if coverage < .85:
        reasons.append("The selected ball was missing or ambiguous in too many frames.")
    if gap > .35:
        reasons.append("Track gaps are too long; review the clip manually.")
    quality = track_quality(normalized, width, height, data.get("quality_limits"))
    quality_reasons = quality["reasons"] + ([] if quality["configured"] or not normalized else ["Correctness limits are unset; confidence, motion and stationary tracks need independent calibration."])
    return {"protocol": protocol, "media_id": domain.text(data.get("media_id"), "Evidence video ID", 32),
            "duration": duration, "start": start, "end": end, "width": width, "height": height,
            "samples": normalized, "version": VERSIONS[method],
            "configuration": {"seed": seed, "reseeds": confirmations, "sample_interval_seconds": .1, "method": method,
                              "max_missed_samples": 2, "edge_loss_requires_confirmation": True,
                              "scene_change": {"channel_delta": 24, "changed_fraction": .65, "validated": False},
                              "pose_model": pose_model,
                              "quality_limits": quality["limits"], **({"detector": detector} if detector else {})},
            "report": {"status": "UNMEASURABLE" if reasons else quality["status"], "coverage": coverage,
                       "max_gap_seconds": gap, "reasons": reasons + quality_reasons, "quality": quality, "sample_count": len(normalized)},
            "candidates": candidates(normalized, width, height, require_pose=bool(pose_model)) if not reasons and not quality["reasons"] and protocol == "juggling" else []}


def candidates(samples, width=320, height=180, require_pose=False):
    """Propose turns across at most two missing samples; never bridge a reseed."""
    result = []
    visible = [(i, s) for i, s in enumerate(samples) if s["found"]]
    for j in range(1, len(visible) - 1):
        indexed = visible[max(0, j-2):min(len(visible), j+3)]
        window = [s for _, s in indexed]
        if indexed[-1][0] - indexed[0][0] - len(indexed) + 1 > 2 or window[-1]["time"] - window[0]["time"] > .65 or len({s.get("segment", 0) for s in window}) != 1:
            continue
        before, point, after = window[0], visible[j][1], window[-1]
        if point["y"] - before["y"] >= .015 and point["y"] - after["y"] >= .015 and (
                point["y"] >= visible[j-1][1]["y"] and point["y"] >= visible[j+1][1]["y"]) and (
                not result or point["time"] - result[-1]["time"] >= .3):
            missing = indexed[-1][0] - indexed[0][0] + 1 > len(indexed)
            boundary = len(indexed) < 5
            support = foot_evidence(point, width, height)
            if require_pose and support["pose_support"] != "near_foot":
                continue
            result.append({"time": point["time"], "kind": "contact", "foot": "unknown", "success": True,
                           **support,
                           "evidence": "trajectory_gap" if missing else "trajectory_boundary" if boundary else "trajectory", "uncertain": True})
    return result


def annotations(data, run):
    if data.get("confirmed") is not True:
        raise domain.ValidationError("Review the entire selected window before confirming its events.")
    events = data.get("events")
    if not isinstance(events, list) or not 1 <= len(events) <= 1000:
        raise domain.ValidationError("Record 1–1,000 reviewed events.")
    kinds = {"juggling": ["contact", "drop"], "wall": ["pass"], "touch": ["pass"], "gates": ["pass"], "slalom": ["start", "finish", "miss"]}[run["protocol"]]
    normalized, seen = [], set()
    for event in events:
        if not isinstance(event, dict):
            raise domain.ValidationError("Events must be objects.")
        time = domain.number(event.get("time"), "Event timestamp", run["start"], run["end"])
        kind = domain.choice(event.get("kind"), kinds, "event type")
        key = (time, kind)
        if key in seen:
            raise domain.ValidationError("Duplicate events at the same timestamp are not allowed.")
        seen.add(key)
        normalized.append({"time": time, "kind": kind, "foot": domain.choice(event.get("foot", "unknown"), ["strong", "weak", "unknown"], "foot"),
                           "side": domain.choice(event.get("side", "unknown"), ["left", "right", "unknown"], "foot side"),
                           "success": domain.flag(event.get("success", True), "Event success")})
    normalized.sort(key=lambda event: (event["time"], event["kind"] == "drop"))
    return {"analysis_id": run["id"], "confirmed": True, "events": normalized,
            "reviewer": domain.text(data.get("reviewer"), "Timeline reviewer", 80), "version": "video-events-2"}


def measurements(protocol, events):
    if protocol == "juggling":
        best = current = 0
        for event in events:
            if event["kind"] == "drop":
                current = 0
            else:
                current += 1
                best = max(best, current)
        return {"contacts": best}
    if protocol == "slalom":
        starts = [e for e in events if e["kind"] == "start"]
        finishes = [e for e in events if e["kind"] == "finish"]
        if len(starts) != 1 or len(finishes) != 1 or finishes[0]["time"] <= starts[0]["time"]:
            raise domain.ValidationError("Mark exactly one start and a later finish for a slalom run.")
        if any(e["time"] < starts[0]["time"] or e["time"] > finishes[0]["time"] for e in events):
            raise domain.ValidationError("Slalom events must be within the timed run.")
        return domain.metrics(protocol, {"seconds": round(finishes[0]["time"] - starts[0]["time"], 3), "missed": sum(e["kind"] == "miss" for e in events)})
    result = {"attempts": len(events), "successes": sum(e["success"] for e in events)}
    if protocol == "wall":
        if any(e["foot"] == "unknown" for e in events):
            raise domain.ValidationError("Label the foot on every wall pass before creating an assessment.")
        result["weak_foot"] = sum(e["foot"] == "weak" for e in events)
    return domain.metrics(protocol, result)


def feedback(run, annotation):
    if not annotation:
        return []
    events = annotation["events"]
    passes = [e for e in events if e["kind"] == "pass"]
    result = []
    failed = [e for e in passes if not e["success"]]
    if failed:
        result.append({"observation": f"{len(failed)} of {len(passes)} labelled passes did not meet the recorded target outcome.",
                       "cue": PROTOCOL[run["protocol"]]["cue"], "times": [e["time"] for e in failed[:5]], "drill_id": run["protocol"] + "-1"})
    known = [e for e in events if e["kind"] in ("pass", "contact") and e["foot"] != "unknown"]
    weak = [e for e in known if e["foot"] == "weak"]
    if len(known) >= 8 and len(weak) / len(known) < .25:
        result.append({"observation": f"{len(weak)} of {len(known)} foot-labelled repetitions used the weaker foot.",
                       "cue": "Try alternating feet at a manageable rhythm. These labels show usage, not the cause of an inconsistency.",
                       "times": [e["time"] for e in known[:3]], "drill_id": run["protocol"] + "-3"})
    drops = [e for e in events if e["kind"] == "drop"]
    if drops:
        result.append({"observation": f"{len(drops)} ball drops were marked in this window.", "cue": PROTOCOL["juggling"]["cue"],
                       "times": [e["time"] for e in drops[:5]], "drill_id": "juggling-1"})
    misses = [e for e in events if e["kind"] == "miss"]
    if misses:
        result.append({"observation": f"{len(misses)} missed cones were marked. This route cannot produce a valid slalom time.",
                       "cue": PROTOCOL["slalom"]["cue"], "times": [e["time"] for e in misses[:5]], "drill_id": "slalom-1"})
    return result[:2]
