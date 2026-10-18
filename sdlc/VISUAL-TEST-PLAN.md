# Five-collection visual QA

User authorization: test five different datasets using `D:\SDLC` for visual testing and reporting.

Use one traceable, unmodified public clip from each of the five existing collections listed in `visual-five.json`: indoor juggling, scene cut, edge exit, rain, and the published small-ball dataset. These are representative samples, not complete collection audits or independent human-labelled benchmarks. Verify five distinct collection names and five distinct video hashes before running.

Invoke the original `D:\SDLC\src\stages\qa.js` visual QA stage with its configured Claude/Playwright/Edge workflow. Keep the source tool unchanged. Each case receives a fresh test-only Football Helper data directory and an in-memory browser profile. Copy only that case's public video into the SDLC run directory so the upload tool can access it without widening file permissions. Preserve per-run screenshots, transcripts, structured verdicts, costs and any errors in Football Helper's isolated SDLC records.

UI flow: onboarding → upload → choose window and ball → tracking or honest manual fallback → loss/skip review → saved status/timeline → JSON export → mobile layout and console inspection. Never confirm provisional contacts as human-reviewed or create an athlete measurement from automated detections. Compare visible markers at selected timestamps only; do not claim exhaustive tracking accuracy.

Acceptance: five case reports with a real verdict or explicit could-not-run reason, actual screenshots where the browser operated, provenance/window details, reported bugs with repro steps, and a combined visual report. Inspect the underlying screenshots and distinguish application defects from model limitations, task wording mismatches and QA-agent/tool failures. Preserve unsuccessful attempts rather than silently replacing them with passes.

No automatic source edits or deployment are part of this test request. Findings should become concrete follow-up work. The previously observed intermittent Windows CI save failure remains a known diagnostic concern; record any recurrence and its network/server evidence.

## Reproduce the local report

From the Football Helper project root, with the isolated runtime provisioned as described in `sdlc/README.md` and the five manifest videos already present:

```powershell
node sdlc/visual-five.mjs
python sdlc/report-visual-five.py
node sdlc/verify-visual-report.cjs
```

For a targeted retry, pass a case ID, for example `node sdlc/visual-five.mjs rain`. Each attempt uses fresh test data; previous reports remain. The visual stage uses the existing authenticated Claude CLI and its configured $3-per-run cap. Its original 30-minute tool timeout still applies. A failed stage may report zero cost despite having used tokens, so reported costs are not a billing total.

Reports and screenshots stay under `test-results/sdlc-visual-five-2026-10-18/report/`; raw SDLC transcripts remain in `sdlc/runtime/data/runs/`. `review.json` in the results parent folder records separate evidence adjudication. The report generator preserves raw agent records and only normalizes known character-encoding artifacts for display. The verifier checks five sections, image loading, local links, JavaScript errors and horizontal overflow at desktop/mobile sizes, then saves report previews for visual inspection.

All windows here are three seconds. This round does not test full 30-second windows, night coverage, pose accuracy, exhaustive ball identity or independently labelled contact accuracy. It complements the automated regression suite; it does not replace it.

For follow-up suites, set `SDLC_VISUAL_SUITE` to a separate folder name (letters, digits and hyphens) and pass case IDs to both the runner and report builder. For example:

```powershell
$env:SDLC_VISUAL_SUITE = 'priorities-2026-10-18'
node sdlc/visual-five.mjs indoor rain public-small
python sdlc/report-visual-five.py indoor rain public-small
node sdlc/verify-visual-report.cjs
```

This preserves the five-case baseline. New records include the source commit and SHA-256 hashes of the application files, so uncommitted preview changes are distinguishable from the commit alone. A focused follow-up is labelled with its actual collection count.
