# Next-priority implementation and validation

Implemented and pushed on `phase/validation-sdlc`: [843c3d6](https://github.com/virtuosolefty/football-gym/commit/843c3d6f844af43e82fba986923683e8c3404c75). No merge or deployment.

- Playback failures now show persistent, specific guidance beside the video and in upload/reference previews. Switching clips clears stale errors and frames. Unsupported media remains unsupported; the app does not silently transcode it.
- Saved runs stack into labelled mobile rows. Full status, reviewed count and Review clip are visible without sideways scrolling.
- Small-ball tracking tries one intermediate context crop before the wide search. Detector version is now `detector-ball-4`. The existing association, gap, edge-exit, scene-change and manual reseeding safeguards remain in force.

## Evidence

[Open the local visual report with 41 screenshots](../../test-results/priorities-2026-10-18/report/report.html). [SDLC plan](../../sdlc/priorities-2026-10-18/PLAN.md) and [implementation review](../../sdlc/priorities-2026-10-18/REVIEW.md).

| Check | Result |
| --- | --- |
| Python | 73 passed; video module's 23 tests rechecked after text-encoding cleanup |
| JavaScript | 51 passed |
| Local Edge browser workflows | All 8 passed, including playback failure/recovery and complete mobile rows |
| Hosted CI | Linux and Windows passed for implementation commit 843c3d6 |
| Actual-model replays | Zero detections in known bottle/cone/floor-ball distractor intervals |
| SDLC indoor, run 0ac3da2c | Workflow pass; 30/30 samples; SUSPECT; 3 provisional contacts; mobile rows verified |
| SDLC rain, run 5e7442c8 | Workflow pass; 3/30 samples; UNMEASURABLE; zero contacts; poor tracking remains a warning |
| SDLC mp4v clip, run 2f4094a7 | Input/codec warning; early playback guidance verified; no tracking accuracy result |

[Hosted CI run](https://github.com/virtuosolefty/football-gym/actions/runs/39143365465).

Rain increased from 2/30 to 3/30 retained detections in the same three-second window. That is a small diagnostic gain, not a solved rain-tracking problem. The [60-inference crop experiment](crop-summary.json) motivated the bounded fallback; it may add one inference on the fallback path (roughly 0.25-0.33 seconds per inference in this local experiment). Confidence thresholds were not retuned.

All three SDLC reports recorded zero browser console errors. One low-severity agent claim that ball-selection failure had no inline reason was contradicted by its own screenshot (`step-3-select-ball-fail.png`) and the exact-error browser assertions: the codec explanation is visible below the action controls and above the player. The raw finding is retained with adjudication. In rain, the agent's initial y-coordinate correction failed; it restored the original seed before tracking. That deviation is also preserved.

The original D:\SDLC QA source and source-video hashes were verified unchanged. Disposable profiles, screenshots and raw transcripts remain local in separate folders. [Final application hashes](source-files.json) identify the implementation; the SDLC suite-start server hash predates a text-encoding-only correction. The earlier five-collection baseline remains intact.

## Remaining limits

No independent coach labels or calibrated correctness thresholds. Rain tracking remains poor; studio contact detection remains unresolved. These are short-window diagnostics and workflow checks, not proof of full 30-second reliability, night/fast-ball accuracy or validated left/right-foot contacts. The original mp4v clip was not converted, so its detector/contact performance remains untested.
