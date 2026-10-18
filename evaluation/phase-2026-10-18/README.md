# Validation readiness and performance phase

The downloaded public material is inventoried in `../corpus.json`. All 12 clips remain **diagnostic**, with their historical labels and provenance unchanged. No independent labels, environmental conditions or player identities were invented. The Seven_Air_1 alignment concern remains unresolved.

Run from the project root:

```powershell
python tools/audit_corpus.py evaluation/corpus.json --output evaluation/phase-2026-10-18/readiness.json
```

Exit 0 means the recorded evidence meets collection prerequisites; 2 means evidence is incomplete; 1 means invalid input. This is not an accuracy certification. Current result: zero eligible calibration or held-out clips, and all five condition targets remain unmet. Three distinct videos per condition **per split** is an initial collection target, not a statistically justified sample size or a detector threshold. Larger samples may be needed once uncertainty and failure rates are measured.

To add independently reviewed labels, save their JSON below `evaluation/`, then add a manifest entry with `id`, relative `labels` path, `split` (`calibration` or `held-out`), `source_id` identifying the original recording/session, `player_ids` covering all relevant players, and `alignment_reviewed: true`. Unknown identities must stay diagnostic. Use the same source grouping for edits/excerpts of a recording. Video hashes, sources and players must not cross splits.

The `blind_review` object needs a real reviewer's identifier, a relative `record` path, and the SHA-256 of the exact label file as `labels_sha256`. The record should describe who annotated without predictions, when, how frame alignment and condition tags were checked, and how disagreements were resolved. Do not put private contact details in versioned records. A hash prevents silently changing labels after review; it does not authenticate the human declaration.

Labels need complete 10 Hz frame coverage, at least one visible ball, explicit full-window contact review, and the existing label-tool tags `night`, `rain`, `small`, `fast`, `juggling-30s` as appropriate. Only actual 30-second juggling windows qualify for the last tag. A clip can contribute to several observed conditions; repeated excerpts of one video do not count as distinct videos.

Evaluate analysis exports with `tools/evaluate_tracks.py`. It refuses duplicate/ambiguous samples, invalid coordinates/scores and mismatched media/windows. Contact matching maximizes chronological one-to-one matches within 0.15 seconds, then minimizes total timing error. It reports precision, recall, timing error, side accuracy and side coverage. Unknown predicted sides abstain; body contacts are evaluated for timing but excluded from left/right accuracy. Unreviewed contact sets produce unavailable metrics, not zero-error results. Independent status remains self-declared unless reviewed through the corpus process.

## Optional stage benchmark

```powershell
python tools/normalize_video.py test-results/conditions-footage/footage/u17.webm test-results/phase-2026-10-18/u17-normalized.mp4 --ffmpeg test-results/validation-2026-10-14/tools/ffmpeg-win-x86_64-v7.1.exe
$env:TEST_DETECTOR='1'
$env:BROWSER_CHANNEL='msedge'
node tests/run_browser.js browser_stage_benchmark.js
```

The output folder must exist; normalization refuses to overwrite an existing file. The callback needs the previously downloaded public U17 clip, normalized copy, looped volleyball compute fixture, YOLOX and pose models. It records source hashes, model load time and separate decode/detector/pose totals, median and p95 latencies. Model timing includes frame copying and preprocessing. One fixed native crop is inferred per sample, even when no ball is present, so this measures compute cost rather than tracking accuracy or production app throughput. The 300-sample clip is looped footage, not independent natural juggling evidence. No universal speedup should be inferred from one sequential run.

Existing browser tests cover progress, cancellation and navigation separately. Real-footage regression findings and the unresolved studio zero-contact result remain in `../revision-2026-10-17/REPORT.md`.
