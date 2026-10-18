import io
import json
import socket
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from unittest import mock

from football import server
from football.server import LocalServer
from football.store import Store
from test_domain import player, attempt


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(self.tmp.name)
        self.server = LocalServer(("127.0.0.1", 0), self.store)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        self.client = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        self.cookie = None
        self.addCleanup(self.cleanup)

    def cleanup(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.tmp.cleanup()

    def request(self, path, data=None, headers=None, raw=None):
        h = {"Origin": self.url, "X-Football-Request": "1"}
        if self.cookie:
            h["Cookie"] = self.cookie
        if data is not None:
            h["Content-Type"] = "application/json"
        h.update(headers or {})
        request = urllib.request.Request(self.url + path, data=raw if raw is not None else json.dumps(data).encode() if data is not None else None, headers=h)
        try:
            response = self.client.open(request)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return response.status, response.read(), response.headers

    def login(self):
        status, body, headers = self.request("/")
        self.assertEqual(status, 200)
        self.cookie = headers["Set-Cookie"].split(";")[0]
        self.assertIn("HttpOnly", headers["Set-Cookie"])
        self.assertIn("SameSite=Strict", headers["Set-Cookie"])

    def test_anonymous_cross_origin_and_rebinding_are_blocked(self):
        self.assertEqual(self.request("/api/state")[0], 401)
        self.assertEqual(self.request("/", headers={"Host": "evil.example"})[0], 403)
        self.assertEqual(self.request("/", headers={"Origin": "https://evil.example"})[0], 403)
        self.login()
        self.assertEqual(self.request("/api/profile", player(), {"X-Football-Request": ""})[0], 403)
        self.assertEqual(self.request("/api/profile", player(), {"Origin": "https://evil.example"})[0], 403)
        self.assertEqual(self.request("/api/state", headers={"Sec-Fetch-Site": "cross-site"})[0], 403)

    def test_complete_assessment_plan_review_and_export_flow(self):
        self.login()
        self.assertEqual(self.request("/api/profile", player())[0], 200)
        status, body, _ = self.request("/api/attempts", attempt())
        self.assertEqual(status, 200)
        a = json.loads(body)
        self.assertEqual(self.request("/api/reviews", {"attempt_id": a["id"], "coach": "Coach", "note": "Verified."})[0], 200)
        status, body, _ = self.request("/api/plan", {"readiness": "Ready"})
        self.assertEqual(status, 200)
        assignment = json.loads(body)["assignments"][0]
        self.assertEqual(self.request("/api/completions", {"assignment_id": assignment["id"], "completed": True, "effort": 2})[0], 200)
        status, body, _ = self.request("/api/export")
        self.assertEqual(status, 200)
        with zipfile.ZipFile(io.BytesIO(body)) as z:
            exported = json.loads(z.read("records.json"))
        self.assertEqual(exported["settings"]["profile"]["name"], "Test Player")
        self.assertNotIn("football_session", json.dumps(exported))

    def test_upload_magic_bytes_range_privacy_and_deletion(self):
        self.login()
        self.request("/api/profile", player())
        upload_headers = {"Content-Type": "video/webm", "X-Filename": "../../outside.webm"}
        self.assertEqual(self.request("/api/upload", headers=upload_headers, raw=b"not a video")[0], 400)
        video = b'\x1a\x45\xdf\xa3' + bytes(range(100))
        status, body, _ = self.request("/api/upload", headers=upload_headers, raw=video)
        self.assertEqual(status, 200)
        media = json.loads(body)
        self.assertEqual((self.store.media / media["filename"]).parent, self.store.media)
        status, body, headers = self.request("/api/media/"+media["id"], headers={"Range":"bytes=4-9"})
        self.assertEqual(status, 206)
        self.assertEqual(body, video[4:10])
        self.assertEqual(headers["Content-Range"], "bytes 4-9/104")
        self.assertEqual(self.request("/api/media/"+media["id"], headers={"Range":"bytes=1000-"})[0], 416)
        self.assertEqual(self.request("/api/media/"+media["id"], headers={"Range":"bytes=-4"})[1], video[-4:])
        self.assertEqual(self.request("/api/delete", {"confirmation":"wrong"})[0], 400)
        self.assertEqual(self.request("/api/delete", {"confirmation":"DELETE"})[0], 200)
        self.assertEqual(list(self.store.media.iterdir()), [])
        self.assertEqual(self.store.events(), [])

    def test_video_routes_validate_and_persist(self):
        self.login()
        self.request("/api/profile", player())
        status, body, _ = self.request("/api/upload", headers={"Content-Type": "video/webm", "X-Filename": "qa.webm"}, raw=b'\x1a\x45\xdf\xa3'+bytes(20))
        self.assertEqual(status, 200)
        media_id = json.loads(body)["id"]
        status, body, _ = self.request("/api/analyses", {"media_id": media_id, "protocol": "juggling", "duration": 30.1, "start": 0, "end": 30, "width": 640, "height": 360, "samples": []})
        self.assertEqual(status, 200)
        run = json.loads(body)
        labels = {"analysis_id": run["id"], "reviewer": "QA", "confirmed": True, "events": [{"time": 1, "kind": "contact"}]}
        status, body, _ = self.request("/api/video/annotations", labels)
        self.assertEqual(status, 200)
        annotation = json.loads(body)
        status, body, _ = self.request("/api/video/assessment", {"analysis_id": run["id"], "annotation_id": annotation["id"],
            "conditions": {"distance": 1, "width": 1, "surface": "Grass", "duration": 30},
            "quality": {"visible": True, "fixed_camera": True, "setup_valid": True}})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["metrics"], {"contacts": 1})
        state = json.loads(self.request("/api/state")[1])
        self.assertEqual(len(state["analyses"]), 1)
        self.assertEqual(len(state["attempts"]), 1)

    def test_invalid_json_and_arbitrary_paths(self):
        self.login()
        self.assertEqual(self.request("/api/profile", headers={"Content-Type":"application/json"}, raw=b'{"minutes":NaN}')[0], 400)
        self.assertEqual(self.request("/api/profile", [1,2,3])[0], 400)
        for path in ["/.data/football.sqlite3", "/../app.py", "/api/media/../../app.py", "/football/store.py"]:
            self.assertEqual(self.request(path)[0], 404)

    def test_hostile_json_bodies_are_rejected_with_400_and_never_kill_the_server(self):
        self.login()
        bodies = {"deep arrays": b"[" * 60_000, "deep objects": b'{"a":' * 12_000, "deep then valid": b"[" * 5_000 + b"]" * 5_000,
                  "huge integer": b'{"minutes":' + b"9" * 6_000 + b"}", "overflowing integer": b'{"minutes":' + b"9" * 400 + b"}", "invalid utf-8": b'{"name":"\xff\xfe"}', "truncated": b'{"name":"x"',
                  "bare null": b"null", "bare string": b'"x"', "NaN constant": b'{"minutes":NaN}', "Infinity": b'{"minutes":-Infinity}',
                  "BOM prefix": b'\xef\xbb\xbf{"name":"x"}', "empty object": b"{}"}
        for path in ("/api/profile", "/api/analyses", "/api/video/annotations", "/api/attempts", "/api/reviews", "/api/plan", "/api/completions", "/api/chat", "/api/knowledge/reviews", "/api/ai/settings", "/api/video/assessment"):
            for label, raw in bodies.items():
                with self.subTest(path=path, body=label):
                    status, body, _ = self.request(path, headers={"Content-Type": "application/json"}, raw=raw)
                    self.assertEqual(status, 400, (path, label, body[:80]))
        self.assertEqual(self.request("/api/state")[0], 200, "the server is still serving after hostile bodies")

    def test_a_stalled_client_does_not_block_other_requests(self):
        self.login()
        port = self.server.server_port
        stalled = socket.create_connection(("127.0.0.1", port), timeout=5)
        self.addCleanup(stalled.close)
        # Promise a body and never send it: the handler must wait for it without holding the global mutation lock.
        headers = [f"POST /api/profile HTTP/1.1", f"Host: 127.0.0.1:{port}", f"Origin: {self.url}", f"Cookie: {self.cookie}",
                   "X-Football-Request: 1", "Content-Type: application/json", "Content-Length: 500"]
        stalled.sendall(("\r\n".join(headers) + "\r\n\r\n").encode())
        time.sleep(.3)
        started = time.monotonic()
        self.assertEqual(self.request("/api/profile", player())[0], 200)
        self.assertLess(time.monotonic() - started, 5, "a normal write waited behind the stalled upload")

    def test_session_cookie_is_scoped_to_its_own_port(self):
        self.login()
        name = self.cookie.split("=")[0]
        self.assertEqual(name, f"football_session_{self.server.server_port}")
        other_dir = tempfile.TemporaryDirectory()
        other = LocalServer(("127.0.0.1", 0), Store(other_dir.name))
        thread = threading.Thread(target=other.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(lambda: (other.shutdown(), other.server_close(), thread.join(), other_dir.cleanup()))
        other_url = f"http://127.0.0.1:{other.server_port}"
        request = urllib.request.Request(other_url + "/", headers={"Origin": other_url, "X-Football-Request": "1"})
        with self.client.open(request) as response:
            other_cookie = response.headers["Set-Cookie"].split(";")[0]
        self.assertNotEqual(other_cookie.split("=")[0], name, "two local instances must not overwrite each other's cookie")
        # A browser sends both cookies to both ports; each server accepts only its own.
        both = f"{self.cookie}; {other_cookie}"
        self.assertEqual(self.request("/api/state", headers={"Cookie": both})[0], 200)
        self.assertEqual(self.request("/api/state", headers={"Cookie": other_cookie})[0], 401)

    def test_same_site_requests_from_other_local_ports_are_refused(self):
        self.login()
        for site, expected in {"same-origin": 200, "none": 200, "same-site": 403, "cross-site": 403}.items():
            with self.subTest(site=site):
                self.assertEqual(self.request("/api/state", headers={"Sec-Fetch-Site": site})[0], expected)

    def test_detector_assets_are_optional_allowlisted_and_typed(self):
        with tempfile.TemporaryDirectory() as web:
            root = Path(web)
            (root / "index.html").write_text("<!doctype html>")
            (root / "detector.js").write_text("// detector")
            (root / "models").mkdir()
            (root / "models" / "yolox_nano.onnx").write_bytes(b"onnx")
            (root / "models" / "other.onnx").write_bytes(b"x")
            (root / "vendor" / "ort").mkdir(parents=True)
            (root / "vendor" / "ort" / "ort-wasm-simd-threaded.wasm").write_bytes(b"\0asm")
            with mock.patch.object(server, "WEB", root):
                self.assertEqual(self.request("/models/yolox_nano.onnx")[0], 401)
                self.login()
                status, body, headers = self.request("/detector.js")
                self.assertEqual((status, headers["Content-Type"]), (200, "text/javascript; charset=utf-8"))
                status, body, headers = self.request("/models/yolox_nano.onnx")
                self.assertEqual((status, body, headers["Content-Type"]), (200, b"onnx", "application/octet-stream"))
                status, body, headers = self.request("/vendor/ort/ort-wasm-simd-threaded.wasm")
                self.assertEqual((status, headers["Content-Type"]), (200, "application/wasm"))
                self.assertEqual(self.request("/vendor/ort/ort.wasm.min.js")[0], 404, "files that are not installed are simply absent")
                for path in ["/models/other.onnx", "/models/", "/vendor/ort/../../app.js", "/vendor/ort/ort-wasm-simd-threaded.mjs.map"]:
                    self.assertEqual(self.request(path)[0], 404, path)

    def test_content_security_policy_allows_wasm_but_not_eval(self):
        _, _, headers = self.request("/")
        policy = {part.split()[0]: part.split()[1:] for part in headers["Content-Security-Policy"].split(";") if part.strip()}
        self.assertEqual(policy["script-src"], ["'self'", "'wasm-unsafe-eval'"])
        self.assertNotIn("'unsafe-eval'", policy["script-src"])
        self.assertNotIn("'unsafe-inline'", policy["script-src"])

    def test_unrelated_malformed_cookies_cannot_block_or_authorize_our_session(self):
        self.login()
        for cookie in (f"broken=\"unfinished; {self.cookie}", f"not-a-cookie; {self.cookie}", f"bad[]={{}}; {self.cookie}", f"{self.cookie}; bad=\"unfinished"):
            self.assertEqual(self.request("/api/state", headers={"Cookie": cookie})[0], 200, cookie)
        for cookie in ("broken=\"unfinished", self.cookie + "; " + self.cookie, self.cookie + "wrong"):
            self.assertEqual(self.request("/api/state", headers={"Cookie": cookie})[0], 401)

    def test_stalled_upload_does_not_hold_lock_and_cannot_resurrect_deleted_workspace(self):
        self.login()
        self.request("/api/profile", player())
        port = self.server.server_port
        stalled = socket.create_connection(("127.0.0.1", port), timeout=5)
        self.addCleanup(stalled.close)
        started = threading.Event()
        original = self.store.player
        def check_player():
            result = original()
            started.set()
            return result
        with mock.patch.object(self.store, "player", side_effect=check_player):
            headers = ["POST /api/upload HTTP/1.0", f"Host: 127.0.0.1:{port}", f"Origin: {self.url}", f"Cookie: {self.cookie}",
                       "X-Football-Request: 1", "X-Filename: race.webm", "Content-Type: video/webm", "Content-Length: 16"]
            stalled.sendall(("\r\n".join(headers) + "\r\n\r\n").encode() + b'\x1a\x45\xdf\xa3')
            self.assertTrue(started.wait(3))
            self.assertEqual(self.request("/api/delete", {"confirmation": "DELETE"})[0], 200)
            self.assertEqual(self.request("/api/profile", player())[0], 200)
            stalled.sendall(bytes(12))
            response = b""
            while True:
                chunk = stalled.recv(4096)
                if not chunk:
                    break
                response += chunk
        self.assertIn(b"400", response.split(b"\r\n", 1)[0])
        self.assertIn(b"deleted during upload", response)
        self.assertEqual(self.store.events("media"), [])
        self.assertEqual(list(self.store.media.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
