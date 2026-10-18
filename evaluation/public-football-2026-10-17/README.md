# Public football diagnostic material

Downloaded on October 17, 2026 at the user's request. The videos are in `test-results/public-football-2026-10-17/footBall/Videos/`; the raw downloaded label files are under `published-labels/`. The 12 matching app-format files are in this directory's `labels/` folder.

There are **12 videos and 336 published frame labels**, covering a requested 360 samples (the first three seconds of each video at 10 Hz). The other 24 samples have no published file at the requested frame index and remain unlabelled. Empty downloaded files mean an absent ball; missing files never mean absence. Multiple boxes are marked uncertain because they do not identify one selected ball.

Sources:

- Zou and Liu, [A high-quality sport ball dataset annotation based on videos](https://doi.org/10.5061/dryad.3bk3j9m13).
- [Published video repository](https://github.com/Zoutianjian/Videos-For-Sport-Ball-Detection-Dataset), frozen at `7981dcadb2c268808413f5f4d6bdbc25dbfbae75`.
- [Author's public annotation mirror](https://github.com/Zoutianjian/Ball-Yolo-A-Sport-Ball-Dataset), frozen at `c6992050c74d6e3f6992bac0e314e7b378a0f51c`.

The Dryad ZIP download returned HTTP 403. `sources.json` retains that failure; `label-sources.json` records the successful public mirror URLs, hashes and missing files. No authentication or access controls were bypassed. The author's naming map links the original annotation directories to the renamed videos. The zero-based frame indices are converted using the downloaded video's reported frame rate. Alignment still needs a human spot-check before accuracy measurements are trusted.

The downloaded video repository supplies **CC BY-NC-ND 4.0** in `LICENSE.md`. The videos remain unmodified in the local evaluation folder, outside app assets; source README and attribution are retained. This pack is not a grant of commercial redistribution rights.

These are external published labels, **not verified blind coach labels**. Files explicitly retain `independent: false`, `role: external-dataset`, and `contacts_reviewed: false`. Conditions are left blank for review. Match/training scenes, tiny balls, blurred people and moving broadcast cameras differ from the app's fixed-camera juggling setting. The videos do not supply full 30-second juggling windows, a balanced night/rain set, foot-contact labels or reliable pose evidence. Do not use them to calibrate correctness limits or claim an independent benchmark.

Open the blind labelling tool, load a matching downloaded MP4, then import its JSON to inspect or extend the annotation. A reviewer who sees imported labels should not claim to have labelled that clip independently and blindly. For genuine double annotation, start from the video with an empty label file and retain both originals.

Reproduce downloads:

```powershell
python tools/fetch_evaluation.py
python tools/prepare_public_labels.py --ffmpeg path/to/ffmpeg
```

The first command preserves successful downloads even if the Dryad archive remains unavailable. The second uses the public annotation mirror. `--allow-unverified` permits diagnostic comparisons in `tools/evaluate_tracks.py`; normal evaluation refuses these labels. Contact metrics are unavailable until the full window has explicitly been reviewed for contacts.
