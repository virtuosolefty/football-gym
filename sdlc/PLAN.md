# Football Helper: validation phase

Approved scope: the user's October 18 instruction to continue the next build phase using `D:\SDLC`, keeping projects separate.

## Requirements and design

1. Preserve `D:\SDLC` and its demo project, records, configuration and worktrees. Bootstrap a project-specific runtime under `sdlc/runtime/`. Keep runtime state out of version control; keep reproducible configuration and lifecycle records here.
2. Preserve the player's `.data/`. Preview and local release instances must use separate disposable data directories. Use the football server's accepted loopback host and require successful HTTP readiness, not a 403 response.
3. Establish local source control and retain the existing CI workflow. No external repository or deployment destination is known; do not claim hosted CI has run.
4. Repair evaluation before tuning the tracker: reject ambiguous sample records; match contacts one-to-one in chronological order with maximum matches and minimum timing error; report precision, recall, timing error and foot-side accuracy separately.
5. Audit a corpus manifest for independently reviewed labels, complete contact review, condition coverage, full 30-second windows, and separation by source, player and video hash. Unknown provenance and public imported labels must not qualify for calibration or held-out validation.
6. Inventory the downloaded clips as diagnostic material, retaining their original labels and provenance. Record the unresolved Seven_Air_1 alignment issue. Never manufacture coach labels, climate conditions or successful validation.

## Acceptance checks

- Unit tests cover the evaluator's greedy-matching failure, duplicates, invalid detections, unknown foot sides, source/player leakage and empty/unverified corpora.
- Existing Python, JavaScript and browser workflow/race suites pass.
- Isolated SDLC runtime passes its own tests; its dashboard and preview start against this project without reading or writing player records.
- Produce a readiness report that lists actual missing evidence. Correctness thresholds remain uncalibrated until those requirements are met.

## Review and release

Review scope: evaluator callers, label schema, corpus manifest, test runner, CI, SDLC configuration and startup. Keep application tracking behavior unchanged while establishing trustworthy evaluation.

After implementation: record test evidence and review findings in `sdlc/VALIDATION.md`. A local tested build is not an independent football validation or a production deployment. The SDLC dashboard retains its explicit merge/deploy gate. Human annotation and usability sessions remain external work; automated agents cannot supply independent human labels.

## Following builds

- Analyze the indoor three-contact and studio zero-contact clips using frame-aligned independent labels. Compare misses at contact, identity changes, pose abstentions and contact logic separately.
- Add continuous-lookalike, one-frame dropout and moving-camera footage to the held-out set; report false tracks, misses and confirmation interruptions together.
- Benchmark original and normalized footage with per-stage decode/detector/pose timing, 30-second windows, cancellation during each stage, and repeat-run leakage checks.
- Run CI on an actual hosted repository, then conduct a coach/player usability pilot. No pass claims until those runs exist.
