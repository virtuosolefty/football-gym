# Five-collection SDLC visual test report

Date: 2026-10-18. Application commit: `34d98f21bea0a34c2ed0f79aaad995725cc61ff0`.

The original visual QA stage at `D:\SDLC\src\stages\qa.js` drove Edge against five separate disposable Football Helper profiles. One existing public clip per collection was sampled, each with a three-second window. This is five collection samples, not five independently labelled benchmarks or complete dataset audits.

[Open the local visual report](../../test-results/sdlc-visual-five-2026-10-18/report/report.html) for 68 screenshots, saved-analysis metrics, original agent verdicts and evidence review. [Run plan and commands](../../sdlc/VISUAL-TEST-PLAN.md). [Clip provenance and hashes](../../sdlc/visual-five.json).

| Collection / condition | Saved evidence | Review |
| --- | --- | --- |
| real-footage / indoor | 30/30 detections; SUSPECT; contact proposals at 1.4, 2.1, 2.8 seconds | Workflow completed. Contact timings agree within 0.15 seconds of the implementer reference, but remain unvalidated. |
| other-footage / scene cut | 7/30 detections; UNMEASURABLE; scene-change loss at 5.8 seconds | Skip stopped continuation. Zero detections at or after the prior cone interval boundary. |
| conditions-footage / edge exit | 21/30 detections; UNMEASURABLE; gap loss at 36.3 seconds | Skip stopped continuation. Zero detections at or after the prior bottle interval boundary. |
| validation-2026-10-14 / rain | 2/30 detections; UNMEASURABLE; gap loss at 4.3 seconds | Detector warning: no useful sustained track. Low-confidence seed identity remains uncertain. |
| public-football-2026-10-17 / small ball | Edge rejected the original mp4v video stream; no saved analysis | Playback warning. Tracking and contacts could not be evaluated. |

Raw SDLC verdicts were three warnings and two passes. The passes (edge exit and rain) describe completion of a protective UI workflow, not tracking accuracy. All five completed reports recorded zero browser console errors. The main application page had no horizontal overflow at 390px; the saved-runs table scrolls internally and hides columns without a visible hint.

## Prioritized follow-up work

1. Surface playback failure immediately when a saved clip is selected. Include clear codec/re-encoding guidance; test an mp4v fixture and a playable H.264 control. The QA agent guessed HEVC; direct inspection of the original file confirmed the mp4v sample-entry tag.
2. Improve mobile access to the saved-runs status and Review clip button, using reflow or an obvious scroll cue. Test the complete row at 390px, not only page-level overflow.
3. Investigate rain/small-ball detection using verified seeds and playable footage. Preserve loss confirmation while comparing crop/model/motion alternatives. Do not tune correctness limits from these five samples.
4. Expand to several clips per condition, night and fast balls, complete 30-second windows, and independent blind ball/contact labels. Run pose-on and left/right-foot checks separately; pose was off here. Re-test cancel/progress and the intermittent Windows save failure with captured network/server diagnostics.

## Test-tool failures and evidence preservation

The first rain attempt, `30bb02ac`, saved/exported its analysis but hung while the SDLC browser tool closed a downloads tab. The original 30-minute timeout ended that attempt. Retry `24210cda` left the tab open and completed, reproducing the 2/30 result. Both records and the failed transcript/screenshots remain in the local artifact folders. A failed run can report zero cost despite using tokens, so tool-reported costs are not a billing total.

The indoor agent's missing Juggling goal finding was a prompt mismatch: Ball mastery already stores the juggling value. Its attempted export rename was denied by QA tooling; the generated JSON download succeeded. These are not application defects. The small-ball agent made a read-only media fetch despite its UI-only instructions; this was recorded separately and did not modify app state.

Original video hashes and the original SDLC QA source hash were verified unchanged. Product source and real player data were not modified. Screenshots were inspected by the primary assistant, not an independent coach. The generated report passed actual Edge rendering, all image/local-link checks, no JavaScript page errors and no page-level horizontal overflow at 1440px and 390px.

This testing round does not establish calibrated detection/contact accuracy, full-window reliability, cancellation behavior, or pose accuracy. Existing CI regression results are separate evidence; the full suite was not rerun for these reporting-only changes.
