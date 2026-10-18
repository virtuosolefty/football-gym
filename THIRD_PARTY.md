# Third-party components

Both are optional. They are not stored in this repository: `python tools/fetch_detector.py` downloads them from the sources below, verifies a pinned SHA-256 for every file, and writes them to `web/models/` and `web/vendor/` (both excluded from source control). Nothing is fetched at runtime.

| Component | Used for | Licence | Source |
|---|---|---|---|
| YOLOX-nano ONNX weights (`yolox_nano.onnx`) | Local ball detection (COCO "sports ball" class) | Apache-2.0 | [Megvii-BaseDetection/YOLOX release 0.1.1rc0](https://github.com/Megvii-BaseDetection/YOLOX/releases/tag/0.1.1rc0) |
| ONNX Runtime Web 1.30.0 (`ort.wasm.min.js`, `ort-wasm-simd-threaded.mjs`, `.wasm`) | Running the model in the browser through WebAssembly | MIT | [onnxruntime-web on npm](https://www.npmjs.com/package/onnxruntime-web/v/1.30.0) |

Video frames are processed on this machine only. The model was trained by its authors on COCO; this project did not train or fine-tune it, and no user footage is used to train anything. The pinned hashes are in [tools/fetch_detector.py](tools/fetch_detector.py).

## Optional pose evidence

`python tools/fetch_pose.py` installs Google's [MediaPipe Tasks Vision 0.10.32](https://www.npmjs.com/package/@mediapipe/tasks-vision/v/0.10.32) (Apache-2.0) and the official [Pose Landmarker Lite model](https://developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker). Every installed file is SHA-256 pinned in the installer. Assets are local, optional and excluded from source control. Inference runs in a worker using image mode so backward sampling is supported. The app's Content Security Policy restricts worker network connections to this local origin.

Pose landmarks and the app's provisional proximity rules have not been validated for football contacts. No user footage is used for training. The [new evaluation downloads](evaluation/public-football-2026-10-17/README.md) have separate provenance and restrictions and are not distributed as app assets.
