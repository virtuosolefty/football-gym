# Implementation review and release evidence

Implementation: `843c3d6f844af43e82fba986923683e8c3404c75` on `phase/validation-sdlc`. No merge or deployment was performed.

## Changes reviewed

- Playback errors now remain next to the video, including before the user starts analysis. Upload/reference previews use the same error explanation. Network and interrupted-load errors give retry guidance; unsupported or damaged media gives H.264 re-export guidance. Selecting another clip clears stale action errors, warning text and the old canvas. Valid manual observations can still be saved with an unplayable attachment; the app does not silently convert or discard evidence.
- Mobile saved runs display all five fields as labelled rows, including the full status and Review clip action. The desktop table remains a table.
- `detector-ball-4` adds one intermediate context crop between the existing tight and wide crops for small balls. At most one extra inference is added on that fallback path. It reuses the existing candidate acceptance check. Loss after two misses, edge-exit confirmation, scene-change detection and user reseeding remain unchanged. Earlier saved runs retain their original version.

## Validation

73 Python tests, 51 JavaScript tests and eight local Edge browser workflows passed. The browser suite covers startup/upload races, review/export, cancellation, navigation, scene cuts, pose persistence, blind labelling and the new real decode-failure/recovery/mobile checks. The video module's 23 tests were rerun after correcting an accidental encoding change found during diff review.

The actual-model replay emitted zero detections in the known bottle/cone/floor-ball distractor intervals. Counts were rain 3/30, bottle 21/30, cone 7/30, floor-ball 16/40 and studio 9/50. Rain previously retained 2/30; it still loses the ball at 4.4 seconds and remains UNMEASURABLE. Studio still found no contacts. These are diagnostic replay counts, not identity accuracy scores. That replay ran after the crop change but before the version-label bump, so its raw exports still carry detector-ball-3; the subsequent SDLC runs use detector-ball-4.

The 60-inference crop experiment compared five native crop sizes on six frames from rain and six from the U17 clip. In rain, 128/192/256/384/512 pixel crops produced candidates in 1/2/3/2/0 frames. This motivates an intermediate context fallback, not a new confidence threshold or general preference for one crop size. One inference took roughly 0.25-0.33 seconds at the median in this run; the extra fallback has a cost. See [crop measurements](../../evaluation/priorities-2026-10-18/crop-summary.json).

## Visual QA and provenance

The original `D:\SDLC\src\stages\qa.js` drives the follow-up on indoor, rain and the original mp4v small-ball clip. It uses fresh disposable app data under `test-results/priorities-2026-10-18/`, with separate SDLC run directories. The earlier five-collection baseline and its failed rain attempt remain intact. Source commit and file hashes accompany the raw records. The suite's captured server-file hash predates a text-encoding-only correction to an unrelated reviewed-event count error; [final source hashes](../../evaluation/priorities-2026-10-18/source-files.json) identify the published implementation.

All three SDLC cases completed: indoor and rain returned workflow passes; public-small returned a codec/input warning. No browser console errors were reported. One low-severity agent finding about missing selection guidance was adjudicated against the persistent alert and the passing exact-error browser assertion; the raw finding remains in the report. Linux and Windows CI passed for implementation commit 843c3d6. See the [final evaluation report](../../evaluation/priorities-2026-10-18/REPORT.md) for evidence and limits.

## Limits and remaining work

Rain tracking is still poor. Confidence/correctness thresholds remain uncalibrated, and no independent coach labels were acquired. The mp4v clip remains unsupported in this browser; the improvement is timely guidance, not new codec support. Full natural 30-second windows, extensive night/fast-ball data and independently validated foot/contact accuracy remain future evaluation work. Optional pose was off in the SDLC cases and only exercised in the existing studio diagnostic and regression tests.
