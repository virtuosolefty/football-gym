"""Install the optional local ball detector: a YOLOX-nano ONNX model and the ONNX Runtime Web wasm runtime.

Run once from the repository root with internet access:  python tools/fetch_detector.py
Every file is pinned by SHA-256 and verified before it is written; TLS certificates are always verified.
After installation the app detects balls entirely on this machine. Without these files it falls back to colour tracking.
"""
import hashlib
import io
import os
import sys
import tarfile
import urllib.request
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent / "web"
MODEL_URL = "https://github.com/Megvii-BaseDetection/YOLOX/releases/download/0.1.1rc0/yolox_nano.onnx"  # Apache-2.0, trained on COCO
RUNTIME_URL = "https://registry.npmjs.org/onnxruntime-web/-/onnxruntime-web-1.30.0.tgz"  # MIT
FILES = {  # destination under web/  ->  (path inside the npm package or None for the model, SHA-256)
    "models/yolox_nano.onnx": (None, "c789161ed43c8269fcd4e67c67eeeb4e80c622da2eb296a20bc6007bd18a0b7d"),
    "vendor/ort/ort.wasm.min.js": ("package/dist/ort.wasm.min.js", "faece07e84faa9001f5104bbe4e5c70861d06cb2376a0dea1fa0ad33a67adc81"),
    "vendor/ort/ort-wasm-simd-threaded.mjs": ("package/dist/ort-wasm-simd-threaded.mjs", "e13f7f94fc51b4ca72b12faeb1ee95f4ace6dfbc8939bc718aabdc0a27c4299b"),
    "vendor/ort/ort-wasm-simd-threaded.wasm": ("package/dist/ort-wasm-simd-threaded.wasm", "3398c10d07d229bd91b364548e130e0e51a8e5704b88c7c083ebbeb78842dee2"),
}


MAX_DOWNLOAD = 100 * 1024 * 1024  # the npm package is ~33 MB; refuse anything wildly larger before decompressing it


def download(url):
    with urllib.request.urlopen(url, timeout=120) as response:
        data = response.read(MAX_DOWNLOAD + 1)
    if len(data) > MAX_DOWNLOAD:
        raise SystemExit(f"Refusing {url}: the download is larger than {MAX_DOWNLOAD // 1024 // 1024} MB.")
    return data


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def store(name, data, expected):
    if sha256(data) != expected:
        raise SystemExit(f"Refusing to install {name}: SHA-256 {sha256(data)} does not match the pinned {expected}.")
    target = WEB / name
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".part")
    partial.write_bytes(data)
    os.replace(partial, target)  # an interrupted install never leaves a truncated file under the real name
    print(f"installed {name} ({len(data) / 1e6:.1f} MB)")


def member(package, inside, name):
    extracted = package.extractfile(inside) if inside in package.getnames() else None
    if extracted is None:
        raise SystemExit(f"Refusing to install {name}: {inside} is missing from the package.")
    return extracted.read()


def main():
    # Existing files are re-hashed, so a truncated or modified file is replaced instead of trusted.
    missing = [name for name in FILES if not (WEB / name).is_file() or sha256((WEB / name).read_bytes()) != FILES[name][1]]
    if not missing:
        print("The local ball detector is already installed and verified.")
        return
    if "models/yolox_nano.onnx" in missing:
        store("models/yolox_nano.onnx", download(MODEL_URL), FILES["models/yolox_nano.onnx"][1])
    runtime = [name for name in missing if name.startswith("vendor/")]
    if runtime:
        with tarfile.open(fileobj=io.BytesIO(download(RUNTIME_URL)), mode="r:gz") as package:
            for name in runtime:
                inside, expected = FILES[name]
                store(name, member(package, inside, name), expected)
    print("Done. Reload the Video feedback page.")


if __name__ == "__main__":
    sys.exit(main())
