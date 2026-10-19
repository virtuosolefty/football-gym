"""Original starter guidance; source links are research references, not endorsements."""

VERSION = "starter-1"
PROTOCOLS = [
    {"id": "juggling", "name": "Juggling", "skill": "Ball mastery", "unit": "contacts", "duration": 30,
     "equipment": ["ball"], "instructions": "In a clear area, count consecutive contacts before the ball drops. Record your best run in 30 seconds.",
     "cue": "Start with a manageable number of touches. Reset calmly after a drop."},
    {"id": "wall", "name": "Alternating-foot wall passing", "skill": "Short passing", "unit": "%", "duration": 30,
     "equipment": ["ball", "wall", "markers"], "instructions": "Mark a 3 m wall distance and a 1 m receiving zone. Alternate feet for 30 seconds. Count passes, controlled returns, and weak-foot passes.",
     "cue": "Receive inside the marked zone before your next pass. Slow the rhythm if control drops."},
    {"id": "touch", "name": "First-touch receiving zone", "skill": "First touch", "unit": "%", "duration": 60,
     "equipment": ["ball", "wall", "markers"], "instructions": "At 3 m from a safe wall, make 20 returns into a marked 1 m receiving zone. Count first touches that stay in the zone.",
     "cue": "Observe where the first touch ends. Try a gentler touch before increasing the pace."},
    {"id": "slalom", "name": "Slalom dribble", "skill": "Dribbling", "unit": "seconds", "duration": 60,
     "equipment": ["ball", "cones"], "instructions": "Place five cones 2 m apart. Time one outward-and-return run. Record missed cones. Keep the layout identical for retests.",
     "cue": "Keep touches close enough to change direction around each cone. Prioritize a complete route."},
    {"id": "gates", "name": "Passing through gates", "skill": "Passing accuracy", "unit": "%", "duration": 60,
     "equipment": ["ball", "cones"], "instructions": "Make 20 passes from 5 m through a 1 m gate. Count successful passes. Use the same distance and gate width each time.",
     "cue": "Choose a consistent approach and aim through the centre of the gate."},
]
PROTOCOL = {p["id"]: p for p in PROTOCOLS}

SOURCES = [
    {"id": "original", "name": "Football Helper starter pack", "url": "", "rights": "Original project text; no external media reproduced", "review": "Draft — requires qualified coach review", "version": VERSION},
    {"id": "fifa", "name": "FIFA Training Centre", "url": "https://www.fifatrainingcentre.com/", "rights": "Research reference only; content not imported", "review": "External source; verify rights before ingestion"},
    {"id": "fa", "name": "England Football Learning", "url": "https://learn.englandfootball.com/", "rights": "Research reference only; content not imported", "review": "External source; verify rights before ingestion"},
]

VARIANTS = [
    ("Reset & repeat", "Begin with short, comfortable repetitions and reset between attempts.", 1),
    ("Build consistency", "Repeat at an even rhythm and record successful outcomes.", 1),
    ("Alternate feet", "Give each foot an equal number of repetitions at a comfortable pace.", 2),
    ("Change the rhythm", "Alternate a slower set with a slightly quicker set while retaining control.", 2),
    ("Retest rehearsal", "Practice the assessment setup exactly; do not change the comparison conditions.", 3),
]
DRILLS = [
    {"id": f"{p['id']}-{i+1}", "name": f"{p['name']} · {title}", "protocol": p["id"], "skill": p["skill"],
     "difficulty": difficulty, "equipment": p["equipment"], "minutes": 5,
     "steps": [p["instructions"], step, "Work for 45 seconds, then take 45 seconds to recover. Repeat up to three times; stop if uncomfortable."],
     "cue": p["cue"], "progression": "After two comparable successful retests and comfortable completed sessions, change one practice constraint. Keep assessment conditions fixed.",
     "regression": "Reduce pace and repetitions; preserve control and take longer breaks.", "source": "original", "version": VERSION,
     "observable_error": {"juggling": "Frequent drops", "wall": "Returns leave the receiving zone", "touch": "First touch leaves the receiving zone", "slalom": "Missed cones", "gates": "Passes miss the gate"}[p["id"]]}
    for p in PROTOCOLS for i, (title, step, difficulty) in enumerate(VARIANTS)
]
# Distinct practice variants retain their own version and never redefine assessment protocols.
DRILLS += [
    {"id": "touch-directional", "name": "Directional first touch", "protocol": "touch", "skill": "First touch",
     "difficulty": 1, "equipment": ["ball", "wall", "markers"], "minutes": 5, "practice_only": True,
     "diagram": "directional", "version": "practice-1", "source": "original",
     "steps": ["Stand about 3 m from a safe wall. Mark two 1 m exit gates, one to each side of your receiving position, with clear space beyond them.",
               "Pass to the wall. As the ball returns, use the first touch to guide it through the chosen gate, then follow under control. Reset before the next repetition.",
               "Try a short set towards each side at a comfortable pace. Record the receiving foot and successful first touches for each direction; recover between sets within the five-minute practice."],
     "cue": "Choose your exit before the return arrives. Guide the first touch into space you can reach.",
     "observable_error": "The first touch misses the chosen gate or needs an extra touch before crossing it.",
     "progression": "Once control is consistent and practice feels comfortable, narrow one gate or vary the return angle. Change one constraint at a time; keep assessment conditions fixed.",
     "regression": "Widen the gates, soften the wall pass and reset after each attempt.",
     "recording": "In session feedback, note left-gate successes/attempts, right-gate successes/attempts, receiving foot and gate width. These are self-reported practice observations, not first-touch assessment scores."},
    {"id": "wall-weaker-foot", "name": "Weaker-foot passing block", "protocol": "wall", "skill": "Short passing",
     "difficulty": 1, "equipment": ["ball", "wall", "markers"], "minutes": 5, "practice_only": True,
     "diagram": "weaker-foot", "version": "practice-1", "source": "original",
     "steps": ["Use a safe wall, mark a 1 m target and a receiving zone, and start about 3 m away. Leave space around you.",
               "Pass with your weaker foot and receive the return under control in the zone. Reset when the ball leaves the zone rather than chasing the next pass.",
               "Use short comfortable sets with recovery between them, up to five minutes. Count target passes and controlled returns separately, and record which foot you used."],
     "cue": "Keep the pass comfortable enough to control the return. Aim through the middle of the target.",
     "observable_error": "The pass misses the wall target or the return leaves the receiving zone.",
     "progression": "After consistent, comfortable sets, slightly increase distance or narrow the target, one change at a time. Retest using the original alternating-foot protocol.",
     "regression": "Move closer, widen the target and pause between passes.",
     "recording": "In session feedback, note foot used, target passes/attempts, controlled returns/attempts and distance. This single-foot practice does not replace the alternating-foot wall assessment."},
]
DRILL = {d["id"]: d for d in DRILLS}
