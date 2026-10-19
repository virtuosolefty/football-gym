# Independent annotation handoff

Prepared batch: `test-results/review-practice-2026-10-18/blind-batch/annotator/`.
Coordinator mapping: sibling `coordinator.json`. Five unmodified videos from five existing collections, neutral IDs review-001 through review-005, matching SHA-256 task files and source/license attribution. No tracker output, seed, prior labels or expected contact count is in the annotator tasks. Nobody has been contacted or recorded as an independent annotator.

Give each reviewer a separate copy of the annotator folder. They load the video and matching task into /label.html, label every 10 Hz sample and inspect contacts at intermediate frames, then export. Their own identity, role and independence declaration must be entered; the tool never fills these from a task. Report decoding problems to the coordinator; do not mark unplayable footage as absent. If normalization is necessary, create a separately hashed task and verify time alignment.

Keep first-pass exports unchanged. Compare annotators' ball status, position/radius, contact time and anatomical side. Record disagreements, the adjudicator's reasoning and final label hash in a separate review record. Never resolve a disagreement by looking at the tracker prediction first. The readiness manifest requires labels, source_id, player_ids, alignment_reviewed and a blind_review object containing reviewer, record path and labels_sha256. Verify these claims with the people involved.

Run tools/audit_corpus.py before calibration. This initial batch is diagnostic: independent labels, source/player grouping and multiple clips per condition are outstanding; it supplies neither night coverage nor natural 30-second juggling coverage. Collect at least three eligible distinct videos per condition in each source/player-disjoint split. A readiness audit is not an accuracy certification.
