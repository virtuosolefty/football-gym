# Independent evaluation collection

The three existing screenings are implementer-labelled diagnostics. **No independently labelled benchmark has been collected yet.** Their scores must not calibrate the correctness gate or support an accuracy claim.

The [additional-data validation from October 14](validation-2026-10-14/REPORT.md) adds 11 public real videos, old-source regressions, generated controls and a real-model speed/cancellation check. It exposes wrong-object detections despite high coverage. Its identity ledger is implementer-led and uses prediction overlays, so it is not blind or independent and must not be used to choose correctness thresholds.

Open `/label.html` from Video feedback, choose the original local video and label it before looking at any tracker results. Enter a distinct annotator ID, conditions and source/rights notes. Click the same selected ball centre and measure its radius in native pixels; mark absent or occluded rather than guessing. The default grid is 0.1 seconds. Clear contacts can be marked at any paused timestamp with left/right foot or other body-part evidence. Export JSON frequently; import it with the identical video to resume. The video hash prevents labels being applied to a re-encoded or different clip. Identity and independence are self-declared, not verified.

Collect at least three different clips for **each** of daylight, indoor, night, rain, small balls and fast balls. Include at least three complete 30-second juggling windows, ball exits, look-alikes, scene cuts and contact occlusions. Keep failures and missing-ball frames in the set. Record native ball diameters and camera movement in notes. Obtain appropriate consent and rights for footage. Have a coach or second annotator label independently; double-label at least one clip per condition, resolve disagreements, and retain both original label files.

Split calibration and held-out sets by original video/player before running models. Do not put different crops of the same source on both sides. Freeze algorithm versions and chosen limits before evaluating the held-out set. Report correctness among emitted detections, missed visible frames, wrong detections after exits, stationary decoys, label completeness, contact precision/recall with a stated timing tolerance, and elapsed time by condition. Coverage alone is not correctness.

Export one analysis with **Export analysis JSON** in Video feedback, then run:

```powershell
python tools/evaluate_tracks.py --labels labels/clip-coach.json --run runs/clip.json --output results/clip.json
```

For legacy runs lacking a media hash, supply `--video path/to/original.mp4`. The evaluator requires matching dimensions and windows and labels within 5 ms of each sample; unlabelled and occluded frames are reported separately and excluded from accuracy denominators. Match contact proposals within 0.15 seconds, one-to-one. Incomplete labels cannot justify a gate pass. `--allow-implementer` is only for diagnostic data and retains the lack of independence in the report.

The API accepts optional `quality_limits` (`min_score` in 0–1, `max_speed` in frame widths/s, and `max_stationary_seconds`, within one native pixel). **All three are unset by default.** Runs stay `SUSPECT` until deliberately configured, and configured runs remain unvalidated and require human review. Confidence, speed and stationary-duration diagnostics are saved so the independent calibration set can inform the limits. Do not tune them on the held-out clips.

Contact proposals can tolerate up to two absent samples in a seven-sample neighbourhood, spanning at most 0.65 seconds. A shorter neighbourhood near a window boundary allows a turn with only one following detection. Proposals are marked uncertain when a gap or boundary is involved. Optional pose evidence can support these turns with ankle/heel/toe proximity and tentative left/right labels. These rules remain uncalibrated and suppress unsupported turns only when pose is enabled. Gap proposals do not establish foot contact or a precise time; review frame by frame.

New public material is documented in [public-football-2026-10-17](public-football-2026-10-17/README.md). It is a diagnostic collection, not a substitute for blind coach annotation. The evaluator only scores contact proposals when `contacts_reviewed: true`; an unreviewed empty contact list is not negative ground truth. The labelling tool has an explicit full-window contact-review checkbox. `--allow-unverified` is an alias for the diagnostic-only `--allow-implementer` option.
