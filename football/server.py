import argparse
import hashlib
import json
import re
import secrets
import sqlite3
import tempfile
import threading
import urllib.parse
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import ai, domain
from .knowledge import DRILLS, PROTOCOLS, SOURCES
from .store import Store

WEB = Path(__file__).resolve().parent.parent / "web"
MAX_VIDEO = 64 * 1024 * 1024
JS, CSS, SVG = "text/javascript; charset=utf-8", "text/css; charset=utf-8", "image/svg+xml"
STATIC = {"/app.js": JS, "/tracker.js": JS, "/detector.js": JS, "/detector-worker.js": JS, "/video-lab.js": JS, "/label.js": JS, "/pose.js": JS, "/pose-worker.js": JS,
          "/label.html": "text/html; charset=utf-8", "/styles.css": CSS, "/video.css": CSS, "/favicon.svg": SVG}
# Installed by tools/fetch_detector.py. Absent files are a plain 404 and the app falls back to colour tracking.
DETECTOR_ASSETS = {"/vendor/ort/ort.wasm.min.js": JS, "/vendor/ort/ort-wasm-simd-threaded.mjs": JS,
                   "/vendor/ort/ort-wasm-simd-threaded.wasm": "application/wasm", "/models/yolox_nano.onnx": "application/octet-stream"}
DETECTOR_ASSETS.update({"/models/pose_landmarker_lite.task": "application/octet-stream",
                        "/vendor/mediapipe/vision_bundle.mjs": JS})
for name in ("vision_wasm_internal", "vision_wasm_nosimd_internal"):
    DETECTOR_ASSETS[f"/vendor/mediapipe/wasm/{name}.js"] = JS
    DETECTOR_ASSETS[f"/vendor/mediapipe/wasm/{name}.wasm"] = "application/wasm"


class LocalServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, store):
        if address[0] != "127.0.0.1":
            raise ValueError("Football Helper binds to loopback only.")
        super().__init__(address, Handler)
        self.store = store
        self.session = secrets.token_urlsafe(32)
        self.mutation_lock = threading.RLock()
        self.workspace_generation = 0


class Handler(BaseHTTPRequestHandler):
    server_version = "FootballHelper/1"

    def setup(self):
        super().setup()
        self.connection.settimeout(15)

    def log_message(self, fmt, *args):
        pass  # Do not log player data, request headers or prompts.

    @property
    def cookie_name(self):
        return f"football_session_{self.server.server_port}"

    @property
    def origin(self):
        return f"http://127.0.0.1:{self.server.server_port}"

    def secure(self):
        if self.headers.get("Host") != self.origin.removeprefix("http://"):
            self.respond(403, {"error": "Invalid localhost host."})
            return False
        if self.headers.get("Sec-Fetch-Site") not in (None, "same-origin", "none") or self.headers.get("Origin") not in (None, self.origin):
            self.respond(403, {"error": "Cross-origin access is forbidden."})
            return False
        return True

    def authorized(self):
        # Other localhost apps share the Cookie header; parse only our opaque token.
        values = [part.partition("=")[2].strip() for part in self.headers.get("Cookie", "").split(";")
                  if part.partition("=")[0].strip() == self.cookie_name]
        return len(values) == 1 and values[0].isascii() and secrets.compare_digest(values[0], self.server.session)

    def respond(self, status, value, content_type="application/json", headers=None, length=None):
        body = json.dumps(value, allow_nan=False).encode() if content_type == "application/json" else value
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body) if length is None else length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self'; img-src 'self' data:; media-src 'self' blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        for key, item in (headers or {}).items():
            self.send_header(key, item)
        self.end_headers()
        try:
            if length is None:
                self.wfile.write(body)
            else:
                remaining = length
                while remaining:
                    chunk = body.read(min(256 * 1024, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def static(self, path):
        try:
            body = (WEB / path[1:]).read_bytes()
        except FileNotFoundError:
            self.respond(404, {"error": "Not found."})
            return
        self.respond(200, body, STATIC.get(path) or DETECTOR_ASSETS[path])

    def do_GET(self):
        if not self.secure():
            return
        path = urllib.parse.urlsplit(self.path).path
        if path in ("/", "/index.html"):
            self.respond(200, (WEB / "index.html").read_bytes(), "text/html; charset=utf-8",
                         {"Set-Cookie": f"{self.cookie_name}={self.server.session}; HttpOnly; SameSite=Strict; Path=/"})
            return
        if not self.authorized():
            self.respond(401, {"error": "Open the app locally to start a session."})
            return
        try:
            if path in STATIC or path in DETECTOR_ASSETS:
                self.static(path)
            elif path == "/api/state":
                store = self.server.store
                records = store.attempts()
                self.respond(200, {"profile": store.get("profile"), "attempts": records, "passport": domain.passport(records),
                                   "protocols": PROTOCOLS, "drills": DRILLS, "sources": SOURCES, "plan": store.get("active_plan"),
                                   "completions": store.events("completion"), "reviews": store.events("review"),
                                   "knowledge_reviews": store.events("knowledge_review"), "chat": store.events("chat"),
                                   "settings": store.get("ai_settings", {"provider": "offline", "model": "gemma4:e4b", "local_only_confirmed": False}),
                                   "media": store.events("media"), "analyses": store.analyses(), "video_annotations": store.events("video_annotation")})
            elif path == "/api/ai/status":
                self.respond(200, ai.status())
            elif path == "/api/export":
                self.export()
            elif re.fullmatch(r"/api/media/[a-f0-9]{32}", path):
                self.video(path.rsplit("/", 1)[1])
            else:
                self.respond(404, {"error": "Not found."})
        except (OSError, sqlite3.Error, domain.ValidationError):
            self.respond(500, {"error": "Could not read local data."})

    def do_POST(self):
        if not self.secure():
            return
        if not self.authorized() or self.headers.get("X-Football-Request") != "1" or self.headers.get("Origin") != self.origin:
            self.respond(403, {"error": "A same-origin app session is required."})
            return
        path = urllib.parse.urlsplit(self.path).path
        try:
            if path == "/api/upload":
                self.upload()
                return
            if self.headers.get("Content-Type") != "application/json":
                raise domain.ValidationError("Use JSON request data.")
            size = self.content_length(1_000_000 if path == "/api/analyses" else 256_000 if path == "/api/video/annotations" else 64_000)
            # The body is read and parsed before taking the lock, so a client that stalls mid-request cannot block every other write.
            data = json.loads(self.rfile.read(size), parse_constant=lambda value: (_ for _ in ()).throw(ValueError("Non-finite JSON")))
            if not isinstance(data, dict):
                raise domain.ValidationError("Request data must be an object.")
            with self.server.mutation_lock:
                store = self.server.store
                if path == "/api/profile":
                    result = domain.profile(data)
                    store.set("profile", result)
                    store.append("consent", {"local_processing": True, "cloud_sharing": False, "ml_training": False, "guardian": result["guardian"]})
                elif path == "/api/attempts":
                    result = store.add_attempt(data)
                elif path == "/api/reviews":
                    result = store.review(data)
                elif path == "/api/analyses":
                    result = store.add_analysis(data)
                elif path == "/api/video/annotations":
                    result = store.annotate_video(data)
                elif path == "/api/video/assessment":
                    result = store.assessment_from_video(data)
                elif path == "/api/knowledge/reviews":
                    result = store.approve_drill(data)
                elif path == "/api/plan":
                    result = store.generate_plan(data)
                elif path == "/api/completions":
                    result = store.complete(data)
                elif path == "/api/ai/settings":
                    result = {"provider": domain.choice(data.get("provider"), ["offline", "ollama"], "provider"),
                              "model": domain.choice(data.get("model"), ai.MODELS, "model"),
                              "local_only_confirmed": domain.flag(data.get("local_only_confirmed", False), "Local-only confirmation")}
                    store.set("ai_settings", result)
                elif path == "/api/chat":
                    result = ai.answer(store, {**data, **store.get("ai_settings", {"provider": "offline"})})
                elif path == "/api/delete":
                    if data.get("confirmation") != "DELETE":
                        raise domain.ValidationError("Type DELETE to erase local records and videos.")
                    store.erase()
                    self.server.workspace_generation += 1
                    result = {"deleted": True}
                else:
                    self.respond(404, {"error": "Not found."})
                    return
                self.respond(200, result)
        except (domain.ValidationError, ValueError, TypeError, KeyError, OverflowError, RecursionError) as error:
            self.respond(400, {"error": str(error) if isinstance(error, domain.ValidationError) else "Invalid request data."})
        except (OSError, sqlite3.Error):
            self.respond(500, {"error": "Local storage is unavailable. Check disk space and permissions."})

    def content_length(self, maximum):
        try:
            size = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise domain.ValidationError("Invalid request length.") from None
        if not 0 < size <= maximum:
            raise domain.ValidationError(f"Request must contain 1–{maximum} bytes.")
        return size

    def upload(self):
        store = self.server.store
        with self.server.mutation_lock:
            store.player()
            generation = self.server.workspace_generation
        if self.headers.get("Content-Type") not in ("video/mp4", "video/webm", "video/quicktime"):
            raise domain.ValidationError("Choose MP4, WebM or MOV video.")
        size = self.content_length(MAX_VIDEO)
        name = domain.text(urllib.parse.unquote(self.headers.get("X-Filename", "")), "Filename", 200)
        suffix = {"video/mp4": ".mp4", "video/webm": ".webm", "video/quicktime": ".mov"}[self.headers["Content-Type"]]
        filename = secrets.token_hex(16) + suffix
        target = store.media / filename
        written = 0
        digest = hashlib.sha256()
        try:
            with target.open("xb") as file:
                while written < size:
                    chunk = self.rfile.read(min(256 * 1024, size - written))
                    if not chunk:
                        raise domain.ValidationError("Video upload was interrupted. Please try again.")
                    if written == 0 and not ((suffix == ".webm" and chunk.startswith(b'\x1a\x45\xdf\xa3')) or
                                            (suffix != ".webm" and len(chunk) >= 12 and chunk[4:8] == b'ftyp')):
                        raise domain.ValidationError("The file does not match the selected video format.")
                    file.write(chunk)
                    digest.update(chunk)
                    written += len(chunk)
            with self.server.mutation_lock:
                if generation != self.server.workspace_generation:
                    raise domain.ValidationError("The workspace was deleted during upload. Upload the video again.")
                store.player()
                result = store.append("media", {"filename": filename, "name": name, "size": size, "mime": self.headers["Content-Type"], "sha256": digest.hexdigest()})
        except Exception:
            target.unlink(missing_ok=True)
            raise
        self.respond(200, result)

    def video(self, media_id):
        record = next((m for m in self.server.store.events("media") if m["id"] == media_id), None)
        if not record:
            self.respond(404, {"error": "Video not found."})
            return
        path = self.server.store.media / record["filename"]
        total = path.stat().st_size
        start, end, status = 0, total - 1, 200
        headers = {"Accept-Ranges": "bytes"}
        if self.headers.get("Range"):
            match = re.fullmatch(r"bytes=(\d*)-(\d*)", self.headers["Range"])
            if not match or not any(match.groups()):
                self.respond(416, b"", record["mime"], {"Content-Range": f"bytes */{total}"})
                return
            left, right = match.groups()
            if left:
                start, end = int(left), min(int(right), total - 1) if right else total - 1
            else:
                start = max(0, total - int(right))
            if start > end or start >= total or (not left and int(right) == 0):
                self.respond(416, b"", record["mime"], {"Content-Range": f"bytes */{total}"})
                return
            headers["Content-Range"] = f"bytes {start}-{end}/{total}"
            status = 206
        with path.open("rb") as file:
            file.seek(start)
            self.respond(status, file, record["mime"], headers, end - start + 1)

    def export(self):
        store = self.server.store
        with self.server.mutation_lock, tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024) as buffer:
            with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("records.json", json.dumps(store.export(), indent=2))
                for media in store.events("media"):
                    archive.write(store.media / media["filename"], "videos/" + media["filename"])
            length = buffer.tell()
            buffer.seek(0)
            self.respond(200, buffer, "application/zip", {"Content-Disposition": 'attachment; filename="football-helper-backup.zip"'}, length)


def main():
    parser = argparse.ArgumentParser(description="Your local football development workspace")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--data-dir", type=Path, default=Path(__file__).resolve().parent.parent / ".data")
    args = parser.parse_args()
    server = LocalServer(("127.0.0.1", args.port), Store(args.data_dir))
    print(f"Football Helper is running at http://127.0.0.1:{server.server_port}", flush=True)
    print("Data stays in " + str(server.store.directory), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
