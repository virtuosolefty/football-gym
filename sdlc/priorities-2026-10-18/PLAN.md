# Next priorities: plan and review

User authorization: work on the next priorities identified by five-collection visual QA. Follow D:\SDLC lifecycle with local implementation and actual visual QA, keeping the original SDLC tool and player data unchanged.

## Scope and acceptance

1. Playback: persistent, actionable error beside the selected video; distinguish unsupported/decoding errors from network/aborted loading. Show upload preview errors before saving. Preserve valid manual observations; do not silently transcode or discard evidence. Selecting a playable clip clears stale warnings and markers. Exercise real browser media failure and recovery, including saved runs and reload.
2. Mobile saved runs: reflow full status, counts and Review clip action into labelled rows at narrow widths. Preserve desktop table and keyboard access. Test the actual full row at 390px and normal desktop width.
3. Small/rain ball: measure current detector at multiple native crop scales on existing real clips. Only adopt a bounded crop change if evidence supports it without weakening association, scene-cut, two-miss or edge-exit safeguards. No new confidence thresholds, blanket accuracy claims or automatic reacquisition. Record failures and runtime tradeoffs.

## Connected code and review

VideoLab render/bind/selection/process/seek, Record preview handlers, saved-run CSS, detector near/pick callers, unit/browser tests, CI default browser list, saved detector configuration and visual QA harness/report provenance. Reuse existing normalization guidance and original D:\SDLC visual stage. Use separate disposable server data. Existing uncommitted five-case report assets remain intact.

Risks checked before implementation: stale media errors after switching sources; failed selection overwriting the useful error; stale canvas markers; disabled controls remaining stuck after cancellation; detector crop changes masking ambiguous candidates or changing persisted provenance. Regression checks must cover these paths. No database migration is needed for playback/layout changes. Release review follows tests; no deployment or merge is part of this task.
