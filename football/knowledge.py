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
DRILL = {d["id"]: d for d in DRILLS}
