# Synthetic video fixture

`contrast-ball.webm` is an original generated test video (320 × 180, approximately 30.48 seconds). It shows an 8-pixel-radius yellow disc centred at x=160, moving vertically around y=90 with a 50-pixel amplitude and approximately one cycle per second, against a uniform dark green background. Frames were drawn on a browser canvas and encoded with MediaRecorder at about 20 fps.

There is no player, foot, target or real football movement in this fixture. It verifies local decoding, seeded colour tracking, track-quality reports, contact-proposal review and persistence. Turning points are not ground-truth football contacts. A representative grassroots dataset and independent labels are still required for football accuracy validation.

`scene-cut-decoy.mp4` is the original generated control from `evaluation/validation-2026-10-14/controlled.py`: a 16-pixel-radius marker at (160,90), replaced at 1.5 seconds by an identical marker at (170,90) against a different background. The 4-second browser regression must pause at the cut and emit no post-cut decoy points after skipping. It contains no real people or third-party footage.
