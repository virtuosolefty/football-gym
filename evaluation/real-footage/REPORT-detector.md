# Real-footage re-screening with the local ball detector

**October 13, 2026 · `detector-ball-1` (YOLOX-nano + gap-bounded tracker) vs. the `contrast-ball-1` baseline in [REPORT.md](REPORT.md)**

The same three excerpts, seed clicks and 0–3 s windows that the colour tracker failed now track the ball in two of three conditions. A follow-up on six different clips is in [../other-footage/REPORT.md](../other-footage/REPORT.md); it found and fixed one more failure. The third (dark strobe) is still withheld as `UNMEASURABLE`. Contact proposals are still not working on real footage. This is a small diagnostic re-run on the clips that were used to choose the model, not a validated accuracy benchmark, and it must not back a public performance claim.

## What changed

1. **Tracking logic** ([web/tracker.js](../../web/tracker.js)). The track starts at the clicked ball, keeps its last position through short gaps, widens its search gradually (at most five consecutive misses), and is declared lost after that. It never reopens the whole image, and a near-tie between two candidates is an abstention. Tracking runs forward and backward from the frame that was clicked. Selecting a ball whose patch is not ball-shaped is refused up front. After the second screening on different footage, a candidate whose size differs from the ball being followed by more than a factor of two is also rejected.
2. **Learned detector** ([web/detector.js](../../web/detector.js)). A COCO-trained YOLOX-nano ("sports ball" class), run locally with ONNX Runtime Web on a native-resolution crop around the expected ball. The click chooses *which* ball to follow, the detector fits its radius, and the tracker rules above associate detections over time. It is optional: `python tools/fetch_detector.py` installs it, and without it the app uses the colour tracker.

## Results (real app, Edge, detector installed, radius box left at its default of 8)

| Condition | Coverage before → after | Longest gap before → after | Correct detections before → after (full audit) | Status after |
|---|---|---|---|---|
| Diffuse outdoor daylight (ground control, negative control) | 40.0% → **96.7%** (29/30) | 1.3 s → 0.2 s | 0/12 → **29/29** | `REVIEW_REQUIRED` |
| Artificial indoor dome light | 46.7% → **96.7%** (29/30) | 0.7 s → 0.2 s | 1/14 → **29/29** | `REVIEW_REQUIRED` |
| Low-key/strobe studio light | 20.0% → **40.0%** (12/30) | 1.5 s → 0.5 s | 1/5 (+1 unknown) → **10/12** | `UNMEASURABLE` |

All emitted detections: 32 before (2 correct) and 70 after (68 correct). Pre-registered spot checks (the 22 scorable frames in [reference.json](reference.json), same rule as before): **22/22** selected the active ball, with mean centre error under 0.15 ball radii on every clip. See [detector-results.json](detector-results.json), [detector-runs.json](detector-runs.json) and [detector-audit.json](detector-audit.json).

Coverage and correctness are now close on the two lit clips, but they are still different quantities. The strobe clip shows why.

## What is still wrong

- **Distractor lock (strobe).** At 1.6 and 1.7 s the track is on the stationary ball lying on the studio floor, with confidence 0.77 and 0.89, because the active ball was dim and nothing else was within the search gate. The quality gate rejected this run only because coverage was 40%. A clip with the same lock and full coverage would pass the gate. Coverage/gap gates cannot detect "tracking the wrong ball confidently".
- **No usable contact proposals.** The indoor reference has three clear boot contacts (1.38, 2.02, 2.78 s); the app proposed none (0/3). The ball is lowest, blurred and partly hidden at contact, so the detector drops out exactly there, and the contact finder needs five consecutive detections. The daylight negative control also produced none, which is the right outcome there. Contacts need gap-tolerant turning-point logic plus foot/body evidence (recommendation 3 in [REPORT.md](REPORT.md)).
- **Dark frames.** Several lit-then-dark strobe frames have a visible ball and no detection. The tracker abstains, which is the intended behaviour, but it is why the strobe clip stays unmeasurable.
- **Low confidence is stored, not used.** Each detection's score is saved, but nothing gates on it yet (strobe detections range from 0.21 to 0.89).

## How much weight this can bear

- The three clips were also used to compare model sizes, so these numbers are optimistic for new footage. The detector score threshold (0.2) was not tuned.
- The full audit was done by the AI assistant that implemented the detector, from browser-captured frames: one reviewer, not independent of the implementation, and no coach labels. The 22 spot checks pre-date the detector and are the stronger evidence.
- Three clips, three players, three venues. The two lit clips have large, clear balls; nothing here says how it behaves with small, fast, blurred or occluded balls.
- Model choice: YOLOX-nano, -tiny and -s found the active ball on all 22 spot checks in an offline replay (nano 94 ms, tiny 290 ms, s 1.2 s per frame in single-thread WebAssembly under Node). Nano was chosen for size (3.7 MB) and speed, and it caught more dark-strobe frames than tiny. The nano/tiny difference is not statistically meaningful at this sample size, and the full-audit comparison was done on a different frame source than the app run.
- Timing: tracking a 3-second, 30-frame window took 5.8–7.9 s in the app (model loading happens earlier, when the ball is selected), roughly 0.2–0.26 s per frame. A full 30-second assessment window is therefore on the order of a minute. This is not a hardware benchmark.

## Next steps this points to

1. Distractor suppression and confidence gating: reject or flag tracks whose detections are low-confidence, stationary, or jump to a different ball, and report correctness-style evidence next to coverage.
2. Gap-tolerant contact proposals, with foot/body evidence and the ground-control protocol as an explicit negative case.
3. A larger, independently labelled set: several players and venues, standardized drills, small and blurred balls, and a second annotator.

## Reproduction

```powershell
python evaluation/real-footage/prepare.py          # workspace with the three clips (as in REPORT.md)
python tools/fetch_detector.py                     # install the detector (hash-pinned)
python app.py --port 8768 --data-dir test-results/real-footage/app-data
npm install playwright-core                        # in a scratch directory; run with NODE_PATH pointing at it
node evaluation/real-footage/run-detector.js 8768  # writes detector-runs.json
python evaluation/real-footage/evaluate_detector.py
```

`run-detector.js` needs a browser that decodes H.264 (the default is the `msedge` channel; set `BROWSER_CHANNEL` otherwise). The browser-frame audit images were rendered from `test-results/real-footage/frames/`, which are excluded from source control. [evaluate.py](evaluate.py) still describes the frozen `contrast-ball-1` run and now refuses to run against the changed production files, by design.

The detector is [YOLOX](https://github.com/Megvii-BaseDetection/YOLOX) (Apache-2.0, trained on COCO) and the runtime is [ONNX Runtime Web](https://www.npmjs.com/package/onnxruntime-web) (MIT); see [THIRD_PARTY.md](../../THIRD_PARTY.md). No footage was used to train or fine-tune anything.
