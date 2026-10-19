# Review tools, distinct practice and blind-labelling preparation

The durable roadmap is [TODO.md](../../TODO.md). This increment implements its first seven tasks; remaining accuracy, capture, performance, usability and drill tasks stay open with explicit criteria.

## Delivered
- Review playhead and chronological event/missing-detection/re-seed buttons. Missing samples are grouped, and Next uncertain moment wraps. Markers are review prompts, never correctness certification.
- Arrow keys step 0.1 seconds, M marks, N navigates issues and Ctrl/Cmd+Z undoes edits outside form controls. Undo retains up to 50 draft snapshots, resets review confirmation and preserves saved tracking; saving again is explicit. Rapid seeks are serialized and coalesced to the latest requested point; navigation cancels pending review seeking.
- Directional first touch and weaker-foot passing extend the catalog from 25 to 27 drills. Each has a setup sketch, distinct cues and variations, version practice-1, draft status and manual-observation guidance. Existing drill IDs/content versions remain unchanged.
- Practice focus selects either drill for the next session while retaining equipment validation, rest and reduced workload. Outcomes remain manual session notes, visible after completion, not standardized assessment scores. Original assessment protocols are unchanged.
- Five unchanged source videos and empty task metadata are prepared in `test-results/review-practice-2026-10-18/blind-batch/annotator`. All hashes verified. No predictions, seed positions, prior labels or expected contact counts are included. [Handoff instructions](ANNOTATION_HANDOFF.md) and [coordinator manifest](batch-manifest.json) document the work still needed from independent people.
- Blind-task loading checks the video's hash and window, rejects label/reviewer payloads, clears reviewer claims and refuses to overwrite existing labels.

## Validation
76 Python and 53 JavaScript tests pass. All 11 browser workflows passed across the suite and targeted reruns. Two issues in the new test script were fixed: attempting undo beyond available history, and reading saved plan state before the asynchronous UI update completed. No app accuracy claim follows from these checks.

The nine existing browser workflows passed. The new workflows exercise drill selection/rest/score separation, diagrams on desktop/mobile, gap/re-seed navigation, slider and rapid seeks, editing/undo, typing protection, task hash/window validation and preservation of existing labels. Their tracking-gap scenario uses controlled detector responses and is a wiring regression, not a model accuracy test.

Original `D:/SDLC/src/stages/qa.js` run `3dc16417` completed all five flows with a WARNING, using disposable app data and the actual installed detector. It found a readiness-selector reset after reload; that is fixed and covered by a browser regression. A cosmetic missing-favicon request on the label page remains open. The indoor replay produced 30/30 detections and three provisional contacts, but remained SUSPECT. These are model outputs, not independently validated contacts.

The [visual report](../../test-results/review-practice-2026-10-18/report/report.html) retains the raw agent findings and 15 screenshots, with six separately labelled direct-browser screenshots. Its original snapshots predate the final rapid-seek, undecoded-frame and saved-note refinements; direct regression tests cover those changes. Report verification loaded all 21 images and checked local links and layout at 1440 and 390 px without horizontal overflow or page errors. The original SDLC source and player data remain unchanged.

Follow-up tests exposed a rapid-seek race: review requests are now serialized and coalesced, stale seek events during decoding are ignored, and marking an undecoded frame is rejected. The initial implementation passed [Linux and Windows CI](https://github.com/virtuosolefty/football-gym/actions/runs/39185092858); CI for the final follow-up fixes is pending. No merge/deployment.

## Remaining evidence
The corpus audit is still not ready for calibration or held-out accuracy evaluation. Five existing collections do not supply independently labelled, source/player-disjoint coverage of night, rain, small/fast balls and natural full 30-second juggling windows. Coach review of the new drills, independent labels, remaining four drill designs and the rest of the roadmap are open. No messages were sent to annotators and no human identity or approval was fabricated.
