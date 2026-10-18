# Responsive analysis and explicit empty reviews

The detector now runs in a dedicated, terminable worker. Cancel works during loading, initial selection and tracking, and navigation closes the worker. Interrupted inference never supplies a partial run. Retry retains usable colour selections; detector cancellation asks for selection again. Detector scoring, association, crop logic and algorithm version are unchanged.

Confirmed empty event lists now persist, reload and export as reviewed zero, visibly distinct from Not reviewed. Reviewer identity and explicit confirmation remain mandatory. A complete reviewed juggling window can measure zero; short windows and incomplete protocol measurements remain rejected. Original tracking and proposed events are preserved.

## Verification

- 74 Python tests, 51 JavaScript tests and all 9 automated browser workflows passed. CI now includes the busy-worker cancellation and empty-review workflow and worker syntax validation.
- A worker deliberately occupied for 15 seconds was cancelled in 99 ms during loading, 118 ms during selection and 117 ms during tracking. No partial analysis was saved; navigation terminated workers. These are local observed timings, not universal latency guarantees.
- Actual installed detector load cancellation and restart passed. Indoor replay: 30/30 detections, 3 provisional contacts, SUSPECT. Five real regression tracks exactly match prior time/found/position/score/radius/segment/loss fields: rain 3/30, bottle 21/30, cone 7/30, floor ball 16/40, studio 9/50. All five remain UNMEASURABLE; none emits points in its known decoy interval.
- A looped 30-second diagnostic ran 300 detector + pose samples in 114.5 seconds. Detector median 210.7 ms, pose median 127.4 ms, decode median 5.0 ms. The 50 ms UI heartbeat ran 2,290 times; maximum observed gap 90.1 ms. Concurrent test activity can affect timings. Fixed crops and looped footage do not measure natural juggling accuracy or end-to-end tracking throughput.
- Five source-collection clip hashes remained unchanged. The original SDLC QA file hash remains `3721210f3b0915e736ad4c56852e69077e2e99594144d5ae67a21e0d0d315382`.

## SDLC visual outcome

Original `D:/SDLC/src/stages/qa.js` was invoked through the isolated integration with the focused [scenario](../../sdlc/reliability-2026-10-18/VISUAL.md). Run `e71ad723` could not execute because the Claude account reached its spending limit. Its raw result is preserved; no SDLC visual pass is claimed.

Direct Playwright fallback used fresh disposable app data and the installed model. Cancellation, restart, explicit empty review, validation, reload/export and desktop/mobile checks passed with no page errors or horizontal overflow. Five actual screenshots were inspected. Empty reviews are simulated UI test input, not independent labels. The local [visual report](../../test-results/reliability-2026-10-18/report/report.html) separates the blocked SDLC attempt from this fallback.

Reproduce: `python -m unittest discover -s tests -v`, `npm test`, `npm run test:browser`. Optional installed-model checks: `TEST_DETECTOR=1`, `BROWSER_CHANNEL=msedge`, `RESULTS_DIR=test-results/reliability-2026-10-18`, then `node tests/run_browser.js browser_worker_benchmark.js browser_real_regressions.js browser_reliability_visual.js` (set environment variables using your shell). `python sdlc/reliability-2026-10-18/report.py` regenerates this phase's local visual report from the retained raw artifacts.

## Remaining priorities

Independent human labels and multiple natural full-window clips per condition are still needed before correctness thresholds can be calibrated. Studio contact misses, rain/small-ball recall and total processing time remain unresolved. This focused phase extends the [prior five-collection evaluation](../priorities-2026-10-18/REPORT.md); it does not claim five complete independently labelled datasets.

Release: development branch only; no merge or deployment. Implementation commit `43caec16132f27297efa4dad90a3d1886488e715` passed both Linux and Windows jobs in [GitHub Actions run 39166942159](https://github.com/virtuosolefty/football-gym/actions/runs/39166942159). The follow-up documentation commit does not change the tested implementation.
