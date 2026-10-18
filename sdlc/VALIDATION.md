# Validation record — October 18, 2026

Historical record of the initial integration phase. Later remote CI and visual QA supersede its release-status paragraph: see the [priorities report](../evaluation/priorities-2026-10-18/REPORT.md) and [latest reliability report](../evaluation/reliability-2026-10-18/REPORT.md).

Scope and authorization: [PLAN.md](PLAN.md). Reference process: `D:\SDLC\README.md`. This record covers a manually executed plan/review/build/test cycle in this coding session. No separate model reviewer, independent human reviewer or automated SDLC plan/build/QA stage is claimed.

## Delivered

- Isolated SDLC runtime, reproducible bootstrap, source hashes, project config, disposable preview/release data, actual dashboard/preview smoke check and three next-phase backlog tasks. Original `D:\SDLC` source hashes remained unchanged.
- Local git baseline `c42e14e`, development branch `phase/validation-sdlc`. Runtime data, player data, model/download binaries and unrelated `AV_digitalTwin` remain ignored.
- Contact evaluator fixes: maximum one-to-one chronological matches, minimum-error tie-breaking, timing/precision/recall and separate side accuracy/coverage. Body contacts remain supported. Invalid detections, duplicate sample timestamps and repeated use of one frame label are refused.
- Corpus readiness audit: review-file hash binding, full frame/contact review, known source/player grouping, condition/window requirements and cross-split leakage detection. Twelve downloaded public clips inventoried as diagnostic only.
- Stage benchmark on public footage and looped compute fixture, with original/normalized comparison and code/model hashes. Linux and Windows CI jobs with distinct artifacts; no hosted run claimed.

## Checks actually run

| Check | Result |
| --- | --- |
| `python -m unittest discover -s tests -q` | 73 passed |
| `npm test` | 47 passed |
| Default Edge browser suite | All 7 callbacks passed, no page errors |
| `npm test --prefix sdlc/runtime` | 15 passed, including worktree/commit/merge and conflict cleanup |
| `node sdlc/smoke.mjs` | Dashboard, preview, isolated data and 403 readiness rejection passed |
| Corpus audit | Correctly returned not-ready; 0 eligible clips in either split |
| Actual-model stage benchmark | 3 clips / 360 samples completed, no page errors |
| JS syntax / `git diff --check` | Passed |

The browser suite covers onboarding, uploads, assessments, review/export, mobile layout, startup race, loss/reseed/edge exit, cancellation/navigation, blind labeling, scene-cut decoy and pose persistence/cancellation. Tests use disposable data; they do not validate real football accuracy.

## Performance evidence

Single sequential run, headless Edge, local YOLOX nano and optional MediaPipe pose. Fixed 300-native-pixel centre crops; one detector inference per sample. Load time excluded from the totals below. See `evaluation/phase-2026-10-18/stage-benchmark.json` and `code-version.json`.

| Input | Samples | Decode | Detector | Pose | Total |
| --- | ---: | ---: | ---: | ---: | ---: |
| Original 720p VP9 U17, seconds 34–37 | 30 | 2.40 s | 6.89 s | Off | 9.29 s |
| Same window, normalized H.264 copy | 30 | 0.20 s | 5.64 s | Off | 5.84 s |
| Looped 30-second compute fixture | 300 | 1.70 s | 62.57 s | 42.32 s | 106.60 s |

Inference remains the main cost after normalization. Pose on every sampled frame adds material cost. These are compute diagnostics, not production tracking throughput: they do not stop on ball loss, use a fixed crop and run pose even when no ball is found. The full-window fixture repeats short footage. The first video loads the detector; later videos reuse it. Encoding cost, natural full-window juggling and hardware variability prevent generalizing a universal speedup.

## Review findings and disposition

- Original SDLC readiness treated a 403 as success and used `localhost`; the isolated adaptation uses `127.0.0.1` and requires 2xx. The original tool is unchanged.
- Original SDLC data location was fixed beside its code; copying only code/public/tests/package files into a separate runtime prevents mixing its demo records with Football Helper.
- Greedy contact scoring could lose a valid match; the regression counterexample now yields both matches regardless of input ordering.
- Label-tool schema includes body contacts and `juggling-30s`; compatibility was checked and corrected before the final Python run.
- Duplicate/near-duplicate detections could inflate scoring by reusing a label; evaluation now rejects them.
- Public labels lack blind review and player grouping, and some lack full sample coverage. The readiness report exposes these gaps instead of treating downloads as independent validation.

## Release disposition and remaining evidence

Ready for local development use. No remote push, hosted CI, production deployment or calibration is claimed. Dashboard model stages were not started; its existing approval gates remain enabled. The runtime and smoke-test servers have been stopped.

Still required: independent coach/second-annotator labels; source/player-disjoint calibration and held-out clips across all conditions; resolution of Seven_Air_1 label alignment; real indoor/studio contact evaluation (the studio replay still had zero proposals); continuous-lookalike/moving-camera tests; natural 30-second performance/accuracy runs; a coach/player usability pilot; and an actual repository destination for hosted CI. Correctness limits remain unset. These are tracked in `backlog.json` and the isolated dashboard.
