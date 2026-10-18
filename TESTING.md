# Verification

Verified October 18, 2026 on Windows / Python 3.11 / Node / Edge. The Python suite has 73 passing tests; tracker, detector and video orchestration have 47 passing JavaScript tests. Seven isolated browser callbacks passed with zero JavaScript errors. These are software checks, not football accuracy validation.

```powershell
python -m unittest discover -s tests -v
node --test tests/test_tracker.js tests/test_detector.js tests/test_video_lab.js
node --check web/app.js
node --check web/video-lab.js
node --check web/label.js
```

## Automated browser checks

The normal app needs no Node dependencies. For development checks:

```powershell
npm ci
npx playwright install chromium
npm run test:browser
```

`tests/run_browser.js` starts a fresh temporary server on an OS-assigned ephemeral port for each callback, closes its browser context and server, and removes only its own checked temporary directory. It never accesses `.data`. Run from the project root. Set `PYTHON` for another Python executable or `BROWSER_CHANNEL=msedge` to use Edge. The runner returns a model 404 in the synthetic test browser without moving installed assets. `TEST_DETECTOR=1` enables exploratory installed-model runs; these are not deterministic CI checks.

`.github/workflows/test.yml` defines Linux and Windows jobs for backend tests, JavaScript tests, syntax checks and all default browser callbacks on push and pull request, with separate artifact uploads. The remote is [virtuosolefty/football-gym](https://github.com/virtuosolefty/football-gym); inspect the [hosted CI runs](https://github.com/virtuosolefty/football-gym/actions) for the exact commit and results. The counts below record local validation.

- `browser_startup_race.js`: navigate and open profile before the first state response.
- `browser_workflow.js`: 15 groups covering onboarding, plans, feedback/rest, library, fixture WebM uploads/playback, immutable corrections, comparisons, invalid-quality exclusion, five protocols, offline chat, knowledge review, export, mobile layout and deletion.
- `browser_video_workflow.js`: 12 groups covering tracking, cancellation, review, event-derived assessments, immutable history, feedback timestamps, persistence, short-window rejection, mobile layout and deletion. The synthetic fixture yielded 300 samples, 100% coverage, a `SUSPECT` report with unset correctness limits, and 29 provisional turns. Reviewed drops still produced a best run of 17 contacts.
- `browser_tracking_safety.js`: deterministic detector verifies gap confirmation, in-window reseeding, saved segments/hashes, edge-exit abstention, skipping, cancellation during confirmation and navigation cancellation. This checks policy, not ONNX accuracy.
- `browser_label_workflow.js`: blind visible/absent/occluded labels, contacts and feet, provenance, JSON download/resume, no prediction scripts and mobile layout. Its Coach QA identity and synthetic labels are test fixtures, not independent human evidence.

Browser CI uses the committed WebM fixture because headless canvas capture on this host intermittently emitted only a header. Real playback and upload checks remain; camera/MediaRecorder capture is not a CI guarantee.

Screenshots and QA exports are in `test-results/`, excluded from source control. Browser callbacks refuse to set up over an existing player profile.

## Regression coverage and limits

New cases cover the first miss at every frame edge, two misses followed by a confident decoy, motion prediction, tight crops with fallback, forward/backward reseeding, no backfilled gaps, cancellation during inference/decode, correctness limits at 100% coverage, missing scores, implausible jumps, stationary decoys, uncertain gap/boundary contacts, and no proposal spanning a reseed. HTTP tests cover malformed unrelated cookies, duplicate own cookies, stalled uploads and deletion/recreation during upload. The evaluator refuses mismatched hashes/windows and non-independent labels unless explicitly used for diagnostics.

Replaying frozen earlier indoor detections through the new contact finder produced proposals at 1.4, 2.1 and 2.8 seconds, within 0.15 seconds of its three implementer-labelled reference contacts (1.38, 2.02, 2.78). The old finder produced zero. The gap and final boundary proposals remain uncertain. This reuses old detections; it is not a fresh model run or independent benchmark.

Historical screenings are unchanged: [colour tracker](evaluation/real-footage/REPORT.md), [local detector](evaluation/real-footage/REPORT-detector.md), [other footage](evaluation/other-footage/REPORT.md) and [conditions](evaluation/conditions-footage/REPORT.md). Their frozen versions describe earlier behavior. The new [collection workflow](evaluation/README.md) requires several clips per condition, independent blind labels and a held-out split before choosing correctness limits.

The [October 14 additional-data validation](evaluation/validation-2026-10-14/REPORT.md) ran 33 cases through each engine, including 11 new real videos, seven old sources and 12 generated controls. Implementer frame review found a real floor-ball switch after two misses: a longer diagnostic reached 87.5% coverage with 16 wrong-object points. A continuous generated scene-cut decoy reached 100% coverage with 25 wrong points. Bottle/cone regressions stopped before substitution in their replay windows. These results do not establish trustworthy automatic tracking.

The actual-model compute benchmark processed all 300 samples in 50.772 seconds on looped, re-encoded footage; it is not a natural juggling accuracy or original-codec benchmark. Actual-model progress/cancel passed without saving a partial analysis. Run `python evaluation/validation-2026-10-14/check.py` to verify recorded policies, source/code hashes, controlled scores and the complete implementer identity ledger. Independent human labels and correctness calibration remain outstanding.

No calibrated thresholds, verified blind football labels, larger detector model or general decoding speedup are claimed. Optional pose inference is implemented and smoke-tested, not accuracy-validated. Ollama tests mock the provider; live model advice, physical-phone capture and coaching effectiveness remain unverified.

## October 17 changes and checks

Two misses now require confirmation. A 32?18 RGB scene-change alarm pauses before association, even if a plausible ball is still detected. Motion diagnostics cover short gaps. A rejected small-ball detail crop retries the wider motion crop. All contact proposals are uncertain; optional worker-based pose inference supports an anatomical side only for one unambiguous nearby foot and suppresses unsupported turns. Stronger/weaker-foot labels remain separate. The original upload-lock and malformed-cookie fixes remain covered by the HTTP race tests.

Additional browser callbacks: `browser_scene_cut.js` tests the real generated decoy video (15/40 retained samples, zero post-cut emissions); `browser_pose_workflow.js` tests pose persistence, anatomical-side review and cancellation while a worker loads. The runner now allocates its own port, avoiding other local apps. CI includes both callbacks and pose-script syntax checks.

The installed MediaPipe model passed `browser_pose_model.js` on a blank frame with cancellation and no page errors. `TEST_DETECTOR=1 BROWSER_CHANNEL=msedge node tests/run_browser.js browser_real_regressions.js` (set environment variables using your shell syntax) replays the local October 14 footage. Bottle/cone/floor-ball windows emitted no points in their previously identified decoy intervals. The studio replay retained nine frames with real left/right foot landmarks but still produced zero contact proposals because the track was lost early. See [replay evidence and limitations](evaluation/revision-2026-10-17/REPORT.md).

`tools/normalize_video.py` completed a real WebM-to-H.264 encode. Unit checks cover existing-output refusal, failed-encode cleanup and a concurrent output-file creation. No original-codec speed comparison or calibrated contact accuracy is claimed. Contact evaluation now requires explicit `contacts_reviewed: true`; legacy label files do not silently assert zero contacts.
## October 18 SDLC validation phase

The local checks passed: 73 Python tests, 47 JavaScript tests, all seven default browser workflows, 15 isolated SDLC tests, and `node sdlc/smoke.mjs`. The Python suite includes contact-matching counterexamples, side abstentions/body contacts, invalid and duplicate detections, corpus split leakage, review-hash invalidation and SDLC source/data isolation. Review also checked the existing label-tool schema and corrected compatibility issues before the final run.

CI defines Linux and Windows jobs with separate browser artifacts. The October 18 SDLC validation record predates publication to GitHub; local results are not a hosted CI pass. The optional actual-model stage benchmark is outside default CI because its downloaded footage and model files are not committed. See [phase evidence](evaluation/phase-2026-10-18/README.md) and [SDLC validation](sdlc/VALIDATION.md).
