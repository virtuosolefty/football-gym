# Football Helper lifecycle

This project follows the plan → review → build → regression QA → release-review workflow in `D:\SDLC`. The October 18 phase was implemented and reviewed in this coding session; it did **not** run the SDLC tool's automated Claude planning/build/browser-QA agents. Those remain available in the isolated dashboard, with their existing approval gates.

## Separate folders

| Location | Purpose |
| --- | --- |
| `D:\SDLC` | Original tool and demo; unchanged |
| `sdlc/` | Versioned integration, approved plan, validation record and backlog |
| `sdlc/runtime/` | Ignored copy of tool code, dependencies, dashboard records and `.worktrees/` |
| `sdlc/app-data/<port>/` | Ignored preview/local-release data; never the player's `.data/` |
| `evaluation/phase-2026-10-18/` | Versioned findings and benchmark reports |
| `test-results/phase-2026-10-18/` | Ignored generated video copies and raw test artifacts |

Local source control has a frozen `main` baseline and development branch `phase/validation-sdlc`. The isolated dashboard uses this development branch as its base, so future task worktrees include the tested integration. `AV_digitalTwin`, player data, model binaries and runtime records are excluded from commits. The remote is [virtuosolefty/football-gym](https://github.com/virtuosolefty/football-gym); see [GitHub Actions](https://github.com/virtuosolefty/football-gym/actions) for hosted CI results.

## Run the isolated tool

Already installed on this machine. From the project root:

```powershell
npm start --prefix sdlc/runtime
```

Open `http://127.0.0.1:8870`. The backlog contains three next-phase tasks. Preview is port 8871; the dashboard's “production” instance is a **local release sandbox** on port 8872. It uses separate data and is not the player's live app. Stop with Ctrl+C.

For a fresh installation:

```powershell
python sdlc/bootstrap.py --source D:\SDLC
npm ci --prefix sdlc/runtime --ignore-scripts --no-audit --no-fund
npm test --prefix sdlc/runtime
node sdlc/smoke.mjs
```

Bootstrap refuses an existing runtime to preserve its task history. Upgrade by reviewing upstream changes and retaining the existing records; do not overwrite the original tool. The checked-in config is a template copied into `runtime/`: its relative repository path is resolved there. Three explicit adaptations exist only in the copy: IPv4 loopback for Football Helper's host checks, 2xx-only readiness, and Python commands in the builder tool list. Source hashes are recorded in `runtime/source-provenance.json`.

The smoke check starts/stops its own dashboard and preview, verifies reference source hashes and rejects HTTP 403 as readiness. It also seeds missing backlog tasks. Do not run it while the dashboard or preview port is occupied. Automated model stages require Claude CLI authentication and use that account's model allowance. The current phase's evidence is in [VALIDATION.md](VALIDATION.md), not a fabricated automated-agent report.

Before merging/deploying a dashboard task: review its actual diff, run Python/JS/browser checks, and inspect any model/footage diagnostics. Optional model weights are ignored by git; install them separately in a task worktree before actual-model QA. Hardware and football accuracy evidence cannot be replaced by passing mocked browser tests.
