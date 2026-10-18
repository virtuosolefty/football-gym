# Screening on six different clips

**October 13, 2026 · `detector-ball-1` and the colour fallback · footage the tracker had never seen**

The first screening ([../real-footage/REPORT-detector.md](../real-footage/REPORT-detector.md)) used three clips that were also used to choose the model. This run uses six clips from a different source, none of which influenced any design choice. It exposed one real failure (a track surviving a hard scene cut and attaching to a traffic cone), which was fixed, and it confirmed the colour fallback is unreliable. It is still a small diagnostic, not a benchmark.

## Footage

Six openly licensed clips from Wikimedia Commons ([sources.json](sources.json): licences, authors, hashes; originals are in `test-results/other-footage/`, excluded from source control). Each is analysed over a 1.7–3 s window with the seed click and radius box recorded in [reference.json](reference.json) *before* any tracker ran on it.

| Clip | What it tests | Window |
|---|---|---|
| `aerial` | Two players in red kit pass a white/orange ball; ball colour is close to the kits | 0.5–3.5 s |
| `training` | Handheld, low quality, several balls in the scene; the target is the ball dribbled by the white-shirted player | 7.4–9.1 s |
| `tennis` | Low-angle close-up with a large ball, then a hard scene cut to a wide shot where the ball is tiny | 5.0–8.0 s |
| `topdown` | 4K drone view; the ball is a ~10 px speck, under 1 px on the tracking canvas | 5.0–8.0 s |
| `improvised` | Children contesting a ball at distance, mostly hidden; no reference position | 50–53 s |
| `tournament` | 320×240 team huddle, no ball visible | 2–5 s |

## Results (real app, Edge, 10 Hz sampling)

| Clip | Detector: coverage, spot checks, audited detections | Colour fallback |
|---|---|---|
| `aerial` | 80.0%; spots 8/10 detected, all correct; **24/24** correct; `UNMEASURABLE` (under the 85% gate) | refused (no ball-shaped patch of one colour) |
| `training` | 94.1%; spots 5/5; **16/16** correct; `UNMEASURABLE` only because the window has 17 samples (rule: 20) | 76.5%; spots 1/5; **1/13** correct, 12 on rooftop/background patches |
| `tennis` | 20.0%; spots 4/6 detected and correct; **6/6** correct (all before the cut), nothing after it; `UNMEASURABLE` | 23.3%; **7/7** correct, nothing after the cut |
| `topdown` | 3.3%; the speck is found at the seed frame (1/1 correct) and then lost; `UNMEASURABLE` | refused |
| `improvised` | refused (no ball found at the click) | refused |
| `tournament` | refused | refused |

Detector total: 47 detections on the four clips that produced any, **47 correct**. No wrong detection, no page error and no measurement record. No clip reached `REVIEW_REQUIRED`, so no contact proposal was released. Details: [results.json](results.json), [runs-detector.json](runs-detector.json), [runs-colour.json](runs-colour.json), [audit.json](audit.json). The audit labels every emitted detection by eye (single reviewer, the AI assistant that implemented the tracker; not independent).

## What the new footage exposed

- **Wrong-object lock after a scene cut (fixed).** Before the fix, the detector run on `tennis` reached 73% coverage: after the cut (0.8 s into the window) the track reacquired an orange-and-white traffic cone at the bottom of the frame (scores 0.25–0.75) and held it for 16 samples, because the search gate only measured distance. The ball it had been following was about 22 px across on the tracking canvas by then, and the cone's box was well outside a factor-of-two window around that. A candidate whose size differs from the ball being followed by more than a factor of two is now rejected, and the track is lost after the usual five misses. The failing run is kept as [runs-detector-without-size-rule.json](runs-detector-without-size-rule.json) (6/22 correct). On the three earlier clips the fix changed nothing except one extra correct detection that appears to be run-to-run variation in frame decoding.
- **Small balls.** Under about 25 px across at native size the detector gives up. In an offline probe with the same model, a tight native crop around the ball in the first frames of the `tennis` and `training` clips (balls about 20 px across) gave no detections even at a 0.05 score threshold, which is why the later, larger-ball windows were used for tracking. The 10 px drone ball is found once, at the click, where the crop is centred on it, and then lost; I did not investigate why it is not found afterwards.
- **Coverage gate vs. correctness.** `aerial` is rejected at 80% coverage even though all 24 detections are right, and `training` is rejected by the 20-sample minimum despite 94% coverage. The gates are doing what they were written to do (they cannot see correctness), but a user would find both outcomes frustrating. Gating on confidence and consistency, not only coverage, remains the right next step.
- **Ground-truth limits.** Spot-check references were read by eye with a few-to-fifteen-pixel uncertainty and judged with a 1.5-radius rule. For tiny balls that is generous; for large balls it is stricter than the first screening's pixel rule.
- **Clips the app could not open (not tracked).** Two of the six downloads (`aerial`, `improvised`) have container timestamps starting near 98,000 s, so the browser reports a ~98,000 s duration and the app (maximum 600 s) cannot analyse them as downloaded. They were re-encoded with timestamps reset (pixels otherwise unchanged; see `derived_files` in [sources.json](sources.json)). A real user uploading such a file would see an error; this is worth handling.

## A mistake in this evaluation, for the record

My first attempt used a static file server without HTTP range support. The browser reported the clips as unseekable, every seek silently failed, and every "frame" I captured was frame 0. I took the clips to be static, wrote a reference file from those frames, and ran the app against it (all six clips refused). The mismatch was caught by comparing the app's own frame at 5.0 s with the frame I had annotated. That reference and run were discarded; everything above comes from frames decoded by the app's own video element.

## What this does and does not show

On footage it had not seen, the detector found the right ball whenever the ball was larger than about 25 px and did not make a wrong detection after the fix; the colour fallback failed on the same multi-ball, cluttered clip in the same way as before. Six clips from one source, four of which have ball-visible windows, annotated by one non-independent reviewer, is far too little to estimate an accuracy or to promise behaviour on other cameras, lighting, ball types or drills. Contact detection was not exercised (no clip has a reference contact count), and foot identification is still not implemented.

## Reproduction

```powershell
# clips and licences are described in sources.json; download them from the Commons pages listed there
python evaluation/other-footage/prepare.py                  # isolated workspace under test-results/other-footage
python app.py --port 8780 --data-dir test-results/other-footage/app-data
node evaluation/other-footage/run.js 8780 detector          # detector installed; writes runs-detector.json
# remove web/models and web/vendor temporarily, then:
node evaluation/other-footage/run.js 8780 colour            # colour fallback; writes runs-colour.json
python evaluation/other-footage/evaluate.py                 # writes results.json
```

`run.js` needs `playwright-core` and a browser that decodes H.264 and VP9 (set `BROWSER_CHANNEL` if not Edge). `ONLY=tennis` limits it to named clips. `evaluate.py` fails if `audit.json` does not cover the recorded runs.
