# Football Helper improvement checklist

[x] means implemented and verified. [ ] means open. Software checks do not establish football accuracy. This file tracks every priority agreed with the user; the current increment is review tools, two distinct drills and blind-labelling preparation.

## Current increment
- [x] R1 Seekable review timeline: events, grouped missing detections and re-seeds.
- [x] R2 Next uncertain moment, keyboard controls and undo; preserve typed input and original tracking.
- [x] D1 Directional first-touch drill: setup, diagram, cues, easier/harder variations and manual outcome guidance.
- [x] D2 Weaker-foot passing drill with the same content requirements.
- [x] D3 Select either drill in a session while preserving equipment, rest and workload controls; keep practice notes separate from assessments.
- [x] E1 Prepare a hash-verified, unlabelled batch from the five source collections, without tracker output or expected contact counts.
- [x] E2 Import blind task metadata into the label tool; document annotator handoff and disagreement review.
- [ ] Q1 Unit, API and browser regression checks; desktop/mobile visual evidence in a separate SDLC report; hosted CI.

## Accuracy and independent evidence
- [ ] E3 Obtain independent coach/second-annotator labels and resolve disagreements. A real independent person is required; generated labels cannot satisfy this.
- [ ] E4 Collect at least three eligible distinct videos per condition per split: night, rain, small/fast balls and natural 30-second juggling. Keep source/player groups disjoint. Five diagnostic collections are not a complete evaluation set.
- [ ] E5 Audit corpus readiness; calibrate correctness thresholds only on calibration data; publish held-out wrong-object, missed-ball, contact precision/recall/timing and foot-side results.
- [ ] A1 Diagnose studio contact misses during short losses using independent labels and pose evidence; retain loss-confirmation safeguards.
- [ ] A2 Compare crop strategies and larger models for small/fast balls, moving cameras and continuous lookalikes. Measure accuracy, runtime and confirmation burden together.

## Recording, speed and usability
- [ ] U1 Camera-placement guidance and preview checks for framing, ball size and lighting before analysis.
- [ ] P1 Benchmark less frequent pose inference and decoding changes on natural full-window clips; retain responsive cancel and no partial saves.
- [ ] P2 Test repeated runs for worker/memory leaks, slow devices, mobile uploads, interrupted uploads and long sessions.
- [ ] U2 Improve evidence-source labels in progress views; compare matching setups only and keep practice notes separate.
- [ ] U3 Run a coach/player pilot; measure task completion, review time and confusion.

## Further distinct drills
- [ ] D4 Scan-receive-pass: partner cue, manually reviewed decisions and completed passes.
- [ ] D5 Turn and exit: inside/outside cuts and drag-back; controlled exits by side.
- [ ] D6 Juggling control ladder: touch-and-catch through alternating feet; separate from standard assessment.
- [ ] D7 Pass and move: partner setup, receiving angles and controlled sequences.
- [ ] D8 Qualified coach review of new content and workload; guidance remains draft until its version is reviewed.

## Release discipline
- [x] Q2 Run the original D:/SDLC visual stage; preserve its raw findings separately from direct browser evidence. Run 3dc16417 completed with a warning; its readiness finding is fixed and regression-tested.
- [ ] Q3 Human release review before merge/deployment. Current work stays on the development branch.
- [ ] Q4 Remove the cosmetic missing-favicon request on the label page reported by SDLC.

Current evidence: [phase report](evaluation/review-practice-2026-10-18/REPORT.md) and [annotation handoff](evaluation/review-practice-2026-10-18/ANNOTATION_HANDOFF.md). Unit checks: 76 Python, 53 JavaScript. All 11 browser workflows passed across the full suite and targeted reruns. Final seek changes are verified. The original SDLC visual report is complete; hosted CI for the follow-up fixes is pending.
