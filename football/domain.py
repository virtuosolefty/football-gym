import math
from .knowledge import PROTOCOL, DRILLS


class ValidationError(ValueError):
    pass


def text(value, name, maximum=1000, required=True):
    if not isinstance(value, str) or len(value.strip()) > maximum or (required and not value.strip()):
        raise ValidationError(f"{name} must be text of 1–{maximum} characters.")
    return value.strip()


def number(value, name, low, high, integer=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high or (integer and int(value) != value):
        raise ValidationError(f"{name} must be {'a whole number' if integer else 'a number'} between {low} and {high}.")
    return int(value) if integer else value


def choice(value, choices, name):
    if value not in choices:
        raise ValidationError(f"Choose a valid {name}.")
    return value


def flag(value, name):
    if not isinstance(value, bool):
        raise ValidationError(f"{name} must be true or false.")
    return value


def profile(data):
    equipment = data.get("equipment")
    if not isinstance(equipment, list) or any(e not in ["ball", "wall", "markers", "cones"] for e in equipment) or "ball" not in equipment:
        raise ValidationError("Select your equipment, including a ball.")
    if data.get("consent") is not True:
        raise ValidationError("Local data processing consent is required.")
    age = choice(data.get("age_band"), ["16–17", "18+"], "age band")
    guardian = flag(data.get("guardian", False), "Guardian permission")
    if age == "16–17" and not guardian:
        raise ValidationError("Guardian permission is required for this pilot's under-18 players.")
    return {"name": text(data.get("name"), "Name", 60), "age_band": age, "guardian": guardian,
            "position": choice(data.get("position"), ["Goalkeeper", "Defender", "Midfielder", "Forward"], "position"),
            "goal": choice(data.get("goal"), list(PROTOCOL), "goal"), "equipment": sorted(set(equipment)),
            "minutes": number(data.get("minutes"), "Session minutes", 5, 60, True), "consent": True}


def metrics(protocol, data):
    if not isinstance(data, dict):
        raise ValidationError("Measurements must be an object.")
    if protocol == "juggling":
        return {"contacts": number(data.get("contacts"), "Consecutive contacts", 0, 10000, True)}
    if protocol == "slalom":
        return {"seconds": number(data.get("seconds"), "Elapsed seconds", .1, 600),
                "missed": number(data.get("missed"), "Missed cones", 0, 10, True)}
    attempts = number(data.get("attempts"), "Attempts", 1, 1000, True)
    if protocol in ("touch", "gates") and attempts != 20:
        raise ValidationError("This protocol requires exactly 20 attempts.")
    result = {"attempts": attempts, "successes": number(data.get("successes"), "Successful outcomes", 0, attempts, True)}
    if protocol == "wall":
        result["weak_foot"] = number(data.get("weak_foot"), "Weak-foot passes", 0, attempts, True)
    return result


def attempt(data):
    protocol = choice(data.get("protocol"), list(PROTOCOL), "assessment")
    conditions = data.get("conditions")
    quality = data.get("quality")
    if not isinstance(conditions, dict) or not isinstance(quality, dict):
        raise ValidationError("Setup and quality checks are required.")
    condition = {"distance": number(conditions.get("distance"), "Distance / cone spacing", .1, 30),
                 "width": number(conditions.get("width"), "Target width", .1, 10),
                 "surface": choice(conditions.get("surface"), ["Grass", "Turf", "Hard court", "Indoor"], "surface"),
                 "duration": PROTOCOL[protocol]["duration"], "protocol_version": "1"}
    if conditions.get("duration") != condition["duration"]:
        raise ValidationError(f"Use the protocol's {condition['duration']}-second observation window.")
    checks = {name: flag(quality.get(name), name) for name in ("visible", "fixed_camera", "setup_valid")}
    return {"protocol": protocol, "conditions": condition, "quality": checks, "metrics": metrics(protocol, data.get("metrics")),
            "notes": text(data.get("notes", ""), "Notes", 1000, False), "media_id": data.get("media_id")}


def evaluate(record):
    result = dict(record)
    result["status"] = "MEASURED" if all(record["quality"].values()) else "UNMEASURABLE"
    m = record["metrics"]
    if record["protocol"] == "slalom" and m["missed"]:
        result["status"] = "UNMEASURABLE"
    result["value"] = None if result["status"] == "UNMEASURABLE" else (
        m["contacts"] if record["protocol"] == "juggling" else
        m["seconds"] if record["protocol"] == "slalom" else round(m["successes"] / m["attempts"] * 100, 1))
    result["unit"] = PROTOCOL[record["protocol"]]["unit"]
    result["confidence"] = "Coach-reviewed manual measurement" if record.get("review") else "Self-reported · unverified"
    if record.get("evidence"):
        result["confidence"] = "Coach-reviewed video annotation" if record.get("review") else "Video-annotated · self-reviewed"
    result["cue"] = PROTOCOL[record["protocol"]]["cue"] if result["value"] is not None else "Repeat the assessment with a complete route, visible ball and valid, fixed setup."
    result["version"] = "manual-rules-1"
    if record.get("evidence"):
        result["version"] = "video-annotation-rules-1"
    return result


def passport(records):
    result = []
    for key, protocol in PROTOCOL.items():
        valid = [r for r in records if r["protocol"] == key and r["value"] is not None]
        latest = valid[-1] if valid else None
        comparable = [r for r in valid if latest and r["conditions"] == latest["conditions"]]
        baseline = comparable[0] if comparable else None
        delta = round(latest["value"] - baseline["value"], 1) if len(comparable) > 1 else None
        result.append({"protocol": key, "name": protocol["skill"], "latest": latest, "baseline": baseline,
                       "delta": delta, "improved": delta is not None and (delta < 0 if key == "slalom" else delta > 0),
                       "comparable_count": len(comparable), "history": valid})
    return result


def plan(player, records, completions, readiness):
    choice(readiness, ["Ready", "Tired", "Rest"], "readiness")
    if readiness == "Rest":
        return {"reason": "You chose rest. Recover today and return when ready.", "minutes": 0, "assignments": []}
    recent = completions[-2:]
    reduced = readiness == "Tired" or any(c["effort"] >= 4 for c in recent)
    budget = max(5, int(player["minutes"] * .6)) if reduced else player["minutes"]
    priority = {p["protocol"]: p for p in passport(records)}
    goal = player["goal"]
    secondary = {"Goalkeeper": "touch", "Defender": "gates", "Midfielder": "wall", "Forward": "slalom"}[player["position"]]

    def rank(drill):
        p = priority[drill["protocol"]]
        latest = p["latest"]
        gap = (100 - latest["value"]) / 100 if latest and drill["protocol"] not in ("juggling", "slalom") else .5
        return (drill["protocol"] != goal, drill["protocol"] != secondary, -gap, drill["difficulty"])

    eligible = [d for d in DRILLS if set(d["equipment"]) <= set(player["equipment"])]
    eligible.sort(key=rank)
    selected, seen = [], set()
    for d in eligible:
        if d["protocol"] in seen:
            continue
        p = priority[d["protocol"]]
        history = [r for r in p["history"] if p["latest"] and r["conditions"] == p["latest"]["conditions"]]
        practiced = [c for c in completions if c["protocol"] == d["protocol"]][-2:]
        progress = not reduced and len(history) >= 2 and all(r["review"] for r in history[-2:]) and (
            all(r["value"] >= 85 for r in history[-2:]) if d["protocol"] not in ("juggling", "slalom") else p["improved"])
        progress = progress and len(practiced) >= 2 and all(c["effort"] <= 2 and c["completed"] for c in practiced)
        selected_drill = next((x for x in eligible if x["protocol"] == d["protocol"] and x["difficulty"] == (2 if progress else 1)), d)
        if (len(selected) + 1) * 5 > budget:
            break
        selected.append({"drill_id": selected_drill["id"], "protocol": d["protocol"], "minutes": 5,
                         "reason": "Goal priority" if d["protocol"] == goal else "Position relevance" if d["protocol"] == secondary else "Build a repeatable baseline",
                         "adaptation": "Progress one practice constraint" if progress else "Reduce pace and take longer breaks" if reduced else "Build consistency"})
        seen.add(d["protocol"])
    return {"reason": "Reduced workload based on readiness or recent effort." if reduced else "Chosen for your goals, position, equipment and comparable evidence.",
            "minutes": len(selected) * 5, "assignments": selected}


def retrieve(question, player):
    words = set(question.lower().replace("-", " ").split())
    eligible = [d for d in DRILLS if set(d["equipment"]) <= set(player["equipment"])]
    return sorted(eligible, key=lambda d: (-(len(words & set((d["name"] + " " + d["skill"] + " " + d["cue"]).lower().split())) + (2 if d["protocol"] == player["goal"] else 0)), d["difficulty"]))[:3]
