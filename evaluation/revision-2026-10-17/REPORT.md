# October 17 tracking revision

The first two priorities were identity loss and correctness gating. This revision stops after two consecutive misses (previously three) and retains first-miss edge abstention. A whole-frame thumbnail change now pauses the window before ball association. The cut alarm's RGB threshold is provisional and may reject camera/lighting changes; it does not establish identity through every cut or close look-alike.

The correctness gate stays uncalibrated and suspect by default. Motion diagnostics now span short detection gaps. No confidence, speed or stationary-duration limits were selected from the available implementer or public data.

## Actual installed-model replays

The October 14 source clips and seeds were replayed through the app in an isolated temporary workspace. Loss prompts were skipped, never automatically reseeded. These are regressions against previously observed failure windows, not new independent accuracy measurements. `regressions.json` records analysis/video hashes; `code-version.json` identifies the implementation. Full analysis JSON is in `test-results/revision-2026-10-17/`.

| Case | Retained detections | Coverage | First loss | Result |
|---|---:|---:|---|---|
| Bottle / u17 | 21/30 | 70% | 36.3 s, gap | No emissions in the known decoy interval |
| Cone / scene cut | 7/30 | 23.3% | 5.8 s, scene change | No post-cut emissions |
| Floor-ball switch | 16/40 | 40% | 2.8 s, gap | No emissions at 3.4–4.9 s, where the prior run emitted 16 wrong points |
| Studio with pose | 9/50 | 18% | 1.0 s, gap | Nine single-person pose samples with left/right foot landmarks; zero contact proposals |

All four runs are `UNMEASURABLE`, with unset correctness limits and no browser errors. The floor-ball case deliberately loses coverage: stopping before substitution is preferable to retaining the old 87.5%-coverage wrong track. The studio failure is **not solved**: pose evidence cannot recover a ball that has already been lost, and no foot-contact accuracy claim follows from these samples.

The deterministic scene-cut fixture additionally retains 15/40 samples, then pauses at exactly 1.5 s. Skipping emits zero decoy points, where the frozen old control emitted 25. The frame-edge and reseeding browser workflow passes, including cancellation during confirmation and navigation.

## Contacts and operation

Gap-tolerant trajectory proposals remain available for manual review and are always uncertain. Optional MediaPipe Pose Landmarker Lite runs locally in a worker; with it enabled, a proposal also needs one unambiguous nearby foot. The provisional proximity/visibility rules are not calibrated, and body contacts or multiple people still require manual labels. Anatomical left/right is stored separately from stronger/weaker foot.

Installed-model smoke checks exercised inference and cancellation. The normal automated browser suite tests worker wiring with deterministic outputs, preserving model-free CI. Seven browser callbacks, 61 Python tests and 47 JavaScript tests passed. Hosted CI was configured but cannot be claimed as run from this workspace, which has no Git repository.

Progress continues showing elapsed time during decode/model waits. A separate normalization helper creates frequent-keyframe H.264 copies, refuses overwrite and cleans up on cancellation or failure; a real encode succeeded. This is not a measured universal decoding speedup.

## Evaluation still needed

[Twelve additional public clips and 336 published frame labels](../public-football-2026-10-17/README.md) are downloaded with hashes and source provenance. They do not supply independent blind coach labelling, contact truth, a balanced night/rain set or full 30-second juggling windows. An implementer spot-check sheet is at `test-results/revision-2026-10-17/public-label-spot-checks.png`; blurring sometimes obscures the ball, and the Seven_Air crop suggests alignment needs correction. Do not calibrate or report benchmark accuracy from this pack without review.

Remaining work is independent collection and calibration, reliable natural 30-second tracking, recovery of the studio/indoor contact failures, and measured small/fast-ball improvements. No larger detector was added; the implementation uses motion prediction and detail crops with wider-crop fallback.
