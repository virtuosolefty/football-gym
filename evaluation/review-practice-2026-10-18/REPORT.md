# Review tools, distinct practice and blind-labelling preparation

The durable roadmap is [TODO.md](../../TODO.md). This increment implements its first seven tasks; remaining accuracy, capture, performance, usability and drill tasks stay open with explicit criteria.

## Delivered
- Review playhead and chronological event/missing-detection/re-seed buttons. Missing samples are grouped, and Next uncertain moment wraps. Markers are review prompts, never correctness certification.
- Arrow keys step 0.1 seconds, M marks, N navigates issues and Ctrl/Cmd+Z undoes edits outside form controls. Undo retains up to 50 draft snapshots, resets review confirmation and preserves saved tracking; saving again is explicit. Rapid seeks cancel stale seek requests.
- Directional first touch and weaker-foot passing extend the catalog from 25 to 27 drills. Each has a setup sketch, distinct cues and variations, version practice-1, draft status and manual-observation guidance. Existing drill IDs/content versions remain unchanged.
- Practice focus selects either drill for the next session while retaining equipment validation, rest and reduced workload. Outcomes remain manual session notes, visible after completion, not standardized assessment scores. Original assessment protocols are unchanged.
- Five unchanged source videos and empty task metadata are prepared in `test-results/review-practice-2026-10-18/blind-batch/annotator`. All hashes verified. No predictions, seed positions, prior labels or expected contact counts are included. [Handoff instructions](ANNOTATION_HANDOFF.md) and [coordinator manifest](batch-manifest.json) document the work still needed from independent people.
- Blind-task loading checks the video's hash and window, rejects label/reviewer payloads, clears reviewer claims and refuses to overwrite existing labels.

## Validation
76 Python and 52 JavaScript tests pass. All 11 browser workflows passed across the suite and targeted reruns. Two issues in the new test script were fixed: attempting undo beyond available history, and reading saved plan state before the asynchronous UI update completed. No app accuracy claim follows from these checks.

The nine existing browser workflows passed. The new workflows exercise drill selection/rest/score separation, diagrams on desktop/mobile, gap/re-seed navigation, slider and rapid seeks, editing/undo, typing protection, task hash/window validation and preservation of existing labels. Their tracking-gap scenario uses controlled detector responses and is a wiring regression, not a model accuracy test.

Original `D:/SDLC/src/stages/qa.js` run `3dc16417` is in progress using disposable app data and the actual installed detector. Its snapshot predates the final rapid-seek cancellation and saved-note display refinements; the final direct browser tests cover those. Raw verdict and screenshots will be recorded without altering agent findings. Hosted CI pending the implementation push. No merge/deployment.

## Remaining evidence
The corpus audit is still not ready for calibration or held-out accuracy evaluation. Five existing collections do not supply independently labelled, source/player-disjoint coverage of night, rain, small/fast balls and natural full 30-second juggling windows. Coach review of the new drills, independent labels, remaining four drill designs and the rest of the roadmap are open. No messages were sent to annotators and no human identity or approval was fabricated.
