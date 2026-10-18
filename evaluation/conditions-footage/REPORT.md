# Screening across playing conditions

**October 13, 2026 · `detector-ball-1` and the colour tracker · six clips chosen for variety of conditions**

Earlier screenings used ordinary training footage. This one deliberately varies conditions: bright sand, an indoor reflective floor, a daylight stadium broadcast, handheld pick-up football on a dusty pitch, a night match in stadium smoke, and an overhead broadcast. The detector did well on sand, indoors and on the stadium pitch while the ball was in view, gave up on balls near or below ~25 px, and **adopted a ball-like object after the real ball left the view**. The colour tracker was fooled by a round logo. One of these two failures was fixed; the other is documented below. This is a small diagnostic, not a benchmark.

## Footage

Six openly licensed clips from Wikimedia Commons ([sources.json](sources.json): licences, authors, hashes; originals in `test-results/conditions-footage/`, excluded from source control). Three further clips (`children`, `penalty`, `samsun`) kept failing their hash check on download and were dropped. Seed click, radius box and ball positions were recorded in [reference.json](reference.json) before any tracker ran on a clip.

| Clip | Condition | Window |
|---|---|---|
| `beach` | Bright sun, sand, panning broadcast camera; a beach-soccer penalty (static ball, kick, ball in the net) | 0.5–3.5 s |
| `futsal` | Indoor lighting, reflective wooden floor; two identical static balls beside a bench | 57–60 s |
| `u17` | Daylight stadium broadcast; a ball lies on the grass, the camera pans, then the ball leaves the view | 34–37 s |
| `street` | Overcast, handheld phone video, dusty pitch, motion blur; ball ~20–28 px at 1280 px wide | 10–13 s |
| `latvia` | Night, stadium smoke and haze, handheld from the stands; ball not identifiable. Decoy: the club crest (contains a stylised football) | 11–14 s |
| `wc2022` | Overhead floodlit broadcast; at most a few pixels of ball, a bright dot of unknown identity | 5–8 s |

## Results (real app, Edge, 10 Hz sampling)

| Clip | Detector (installed) | Colour tracker (detector not installed) |
|---|---|---|
| `beach` | 43.3% coverage; spots 5/10, all 13 detections correct; `UNMEASURABLE` (ball lost once it is in flight: a 1.8 s gap to the end of the window, no wrong detection) | identical: same 13 frames, all correct |
| `futsal` | **100%**; spots 4/4; **30/30** correct on the left of two identical balls; `REVIEW_REQUIRED` | refused |
| `u17` | 93.3%; spots 6/6; **21/28 correct, 7 wrong**; `REVIEW_REQUIRED` | 70.0%; **21/21 correct**, none after the ball left; `UNMEASURABLE` |
| `street` | refused (no ball found at the click) | refused |
| `latvia` | refused (no ball found at the crest) | **tracked the crest for 30/30 samples, `REVIEW_REQUIRED`**: 0/30 correct |
| `wc2022` | refused | refused |

Totals: detector 71 detections, 64 correct; colour tracker 64 detections, 34 correct (30 of the wrong ones are the logo). No page errors, no measurement records, no contact proposals. Details: [results.json](results.json), [runs-detector.json](runs-detector.json), [runs-colour.json](runs-colour.json), [audit.json](audit.json). The audit labels every emitted detection by eye (single reviewer, the AI assistant that implemented the tracker; not independent).

## What these conditions exposed

- **Colour fallback accepted a decoy (fixed).** On `latvia` the detector found nothing at the crest, so the app fell back to colour tracking, which tracked the round crest for the whole window and reported `REVIEW_REQUIRED`. A colour patch will track any round, uniformly coloured object. With the detector installed, a click it does not recognise is now refused ([runs-detector-before-refusal-fix.json](runs-detector-before-refusal-fix.json) is the failing run). With **no** detector installed, the colour tracker still behaves this way, which is why the app labels it experimental and why the detector is the recommended path.
- **A ball-like object adopted after the ball leaves (not fixed).** On `u17` the ball leaves the frame after ~2.1 s. From 2.3 s the track attached to a pale-blue water bottle on the touchline, with confidence 0.40–0.66 (the real ball scored 0.7–0.9 but 0.56 at the frame edge), for 7 samples, and the run was still `REVIEW_REQUIRED` at 93% coverage. The bottle is within the search gate of the last ball position and within the size rule. This is the same class of failure as the cone in the previous screening and the stationary floor ball in the first, so it is now seen on three clips. The colour tracker did not make this error on `u17`.
- **Appearance continuity does not separate them cleanly.** I measured the chromaticity change between consecutive accepted detections (table [below](#appearance-measurement); an ad-hoc script on the captured frames, not kept in the repository). Correct balls change by up to 0.091 (tennis close-up) and the bottle differs from the ball by 0.105–0.110, so a colour-continuity rule would need a threshold inside a margin of 0.014 chosen from these examples. I did not build one. Confidence gating fails too, because the true ball's edge-of-frame score (0.56) overlaps the bottle's (0.40–0.66).
- **Ball in flight.** On `beach` the ball is detected while still, then lost during the kick (motion blur, ~110 canvas px of travel over three samples) and never recovered in the net, because a track lost after five misses never reacquires. That is the designed abstention, and a limitation for fast play.
- **Small balls.** `street` (about 20–28 px) was refused by the detector, consistent with the earlier finding that balls around 20 px are not detected; `wc2022` (a few px) was refused.
- **Two identical balls.** On `futsal` the tracker stayed on the clicked ball for all 30 samples, with a position error of about 4 px against my reference.
- **Slow decoding.** The colour run on `latvia` took 86 s for 30 samples; seeking in 1080p VP9 without frequent keyframes is slow. A 30-second assessment window on such footage would take several minutes.

### Appearance measurement

Mean RGB over the central 60% of the detection circle, chromaticity = RGB / sum, distance between consecutive accepted detections:

| Clip | Max step between correct detections | Look-alike vs last ball |
|---|---|---|
| aerial / training / beach / futsal / u17 | 0.029 / 0.045 / 0.012 / 0.001 / 0.016 | – |
| tennis (pre-cut close-up) | 0.091 | cone after the cut: 0.062–0.166 |
| u17 | 0.016 | bottle: 0.105–0.110 |

## What this does and does not show

Across sand, an indoor floor and a stadium pitch the detector followed the right ball whenever the ball was big enough and in view, including picking one of two identical balls. It does not yet know when the ball has gone: after a ball leaves, the tracker can latch onto the nearest ball-like object and the run can still pass the coverage gate. Until there is a confidence-and-consistency gate that works across more footage, a `REVIEW_REQUIRED` track must be checked by a person, which is what the app already asks. Six clips from one source, ball-visible windows in four of them, annotated by one non-independent reviewer, cannot estimate accuracy. Contact detection, foot identification and night-time or rainy conditions with a visible ball were not tested (no clip had one that I could find).

## Reproduction

```powershell
# clips and licences are described in sources.json; download them from the Commons pages listed there
python evaluation/conditions-footage/prepare.py            # isolated workspace under test-results/conditions-footage
python app.py --port 8782 --data-dir test-results/conditions-footage/app-data
node evaluation/conditions-footage/run.js 8782 detector    # detector installed; writes runs-detector.json
# remove web/models and web/vendor temporarily, then:
node evaluation/conditions-footage/run.js 8782 colour      # writes runs-colour.json
python evaluation/conditions-footage/evaluate.py           # writes results.json
```

`run.js` needs `playwright-core` and a browser that decodes VP9. `evaluate.py` fails if `audit.json` does not cover the recorded runs.
