"""Install the optional, hash-pinned MediaPipe pose model and local browser runtime."""
import io
import tarfile

from fetch_detector import WEB, download, sha256, store, member

RUNTIME_URL = "https://registry.npmjs.org/@mediapipe/tasks-vision/-/tasks-vision-0.10.32.tgz"
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
FILES = {
    "models/pose_landmarker_lite.task": (None, "59929e1d1ee95287735ddd833b19cf4ac46d29bc7afddbbf6753c459690d574a"),
    "vendor/mediapipe/vision_bundle.mjs": ("package/vision_bundle.mjs", "de83c48ff329717a27aeb528d5ef5f47f077c628a5302dc483aca5b513e7464b"),
    "vendor/mediapipe/wasm/vision_wasm_internal.js": ("package/wasm/vision_wasm_internal.js", "6f6b86509cf9e163ea1cfec7edc8cf53732699c04781e4c21c557c1ba402310e"),
    "vendor/mediapipe/wasm/vision_wasm_internal.wasm": ("package/wasm/vision_wasm_internal.wasm", "cb3ec20026a9aecc2a81a93c25630ceb5389297ddb7a5f0bd61dd09cde606b9b"),
    "vendor/mediapipe/wasm/vision_wasm_nosimd_internal.js": ("package/wasm/vision_wasm_nosimd_internal.js", "9f8fc960e363f0fb2f42f7937b97ae9cf9a5630490f71031fa90caa9bb121938"),
    "vendor/mediapipe/wasm/vision_wasm_nosimd_internal.wasm": ("package/wasm/vision_wasm_nosimd_internal.wasm", "924274fcd5ac8985f6570a8573e7971b7bd2d580ba1b8f3beb0ba8f95db6347c"),
}


def main():
    missing = [name for name, (_, digest) in FILES.items() if not (WEB / name).is_file() or sha256((WEB / name).read_bytes()) != digest]
    model = "models/pose_landmarker_lite.task"
    if model in missing:
        store(model, download(MODEL_URL), FILES[model][1])
    runtime = [name for name in missing if name != model]
    if runtime:
        with tarfile.open(fileobj=io.BytesIO(download(RUNTIME_URL)), mode="r:gz") as package:
            for name in runtime:
                inside, digest = FILES[name]
                store(name, member(package, inside, name), digest)
    print("Optional pose assets verified. Reload Video feedback and enable foot evidence.")


if __name__ == "__main__":
    main()
