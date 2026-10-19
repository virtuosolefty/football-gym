import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from . import domain, video
from .knowledge import DRILL, PROTOCOL


def now():
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, directory):
        self.directory = Path(directory).resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.media = self.directory / "videos"
        self.media.mkdir(exist_ok=True)
        with self.db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY, kind TEXT NOT NULL, created TEXT NOT NULL, payload TEXT NOT NULL);
            """)

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.directory / "football.sqlite3", timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA secure_delete=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    def get(self, key, default=None):
        with self.db() as db:
            row = db.execute("SELECT payload FROM settings WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def set(self, key, value):
        with self.db() as db:
            db.execute("INSERT OR REPLACE INTO settings VALUES (?,?)", (key, json.dumps(value)))

    def append(self, kind, payload):
        event = {"id": uuid.uuid4().hex, "created": now(), **payload}
        with self.db() as db:
            db.execute("INSERT INTO events VALUES (?,?,?,?)", (event["id"], kind, event["created"], json.dumps(payload)))
        return event

    def events(self, kind=None):
        with self.db() as db:
            rows = db.execute("SELECT * FROM events" + (" WHERE kind=?" if kind else "") + " ORDER BY rowid", (kind,) if kind else ()).fetchall()
        return [{"id": r["id"], "created": r["created"], "kind": r["kind"], **json.loads(r["payload"])} for r in rows]

    def player(self):
        result = self.get("profile")
        if not result:
            raise domain.ValidationError("Create your player profile first.")
        return result

    def attempts(self):
        reviews = {r["attempt_id"]: r for r in self.events("review")}
        analyses = {r["id"]: r for r in self.events("analysis")}
        annotations = {r["id"]: r for r in self.events("video_annotation")}
        results = []
        for record in self.events("attempt"):
            review = reviews.get(record["id"])
            record["original_metrics"] = record["metrics"]
            if review and review["metrics"]:
                record["metrics"] = review["metrics"]
            record["review"] = review
            evidence = record.get("evidence")
            record["feedback"] = video.feedback(analyses[evidence["analysis_id"]], annotations[evidence["annotation_id"]]) if evidence else []
            results.append(domain.evaluate(record))
        return results

    def add_attempt(self, data):
        self.player()
        record = domain.attempt(data)
        if record["media_id"] is not None and not any(m["id"] == record["media_id"] for m in self.events("media")):
            raise domain.ValidationError("The evidence video does not exist.")
        return self.append("attempt", record)

    def analyses(self):
        labels = {r["analysis_id"]: r for r in self.events("video_annotation")}
        return [{**run, "annotation": labels.get(run["id"]), "feedback": video.feedback(run, labels.get(run["id"]))}
                for run in self.events("analysis")]

    def add_analysis(self, data):
        self.player()
        run = video.analysis(data)
        media = next((m for m in self.events("media") if m["id"] == run["media_id"]), None)
        if not media:
            raise domain.ValidationError("Upload or select an existing evidence video first.")
        if media.get("sha256"):
            run["media_sha256"] = media["sha256"]
        return self.append("analysis", run)

    def annotate_video(self, data):
        run = next((r for r in self.events("analysis") if r["id"] == data.get("analysis_id")), None)
        if not run:
            raise domain.ValidationError("Video analysis not found.")
        return self.append("video_annotation", video.annotations(data, run))

    def assessment_from_video(self, data):
        run = next((r for r in self.analyses() if r["id"] == data.get("analysis_id")), None)
        if not run or not run["annotation"]:
            raise domain.ValidationError("Save a confirmed event timeline first.")
        annotation = run["annotation"]
        if data.get("annotation_id") != annotation["id"]:
            raise domain.ValidationError("The event timeline changed. Reload it before creating an assessment.")
        if run["end"] - run["start"] < PROTOCOL[run["protocol"]]["duration"] - .01:
            raise domain.ValidationError("The selected video window must cover the full assessment observation window.")
        if any(r.get("evidence", {}).get("annotation_id") == annotation["id"] for r in self.events("attempt")):
            raise domain.ValidationError("This timeline version already has an assessment.")
        record = domain.attempt({**data, "protocol": run["protocol"], "media_id": run["media_id"],
                                 "metrics": video.measurements(run["protocol"], annotation["events"])})
        record["evidence"] = {"source": "video-annotated", "analysis_id": run["id"], "annotation_id": annotation["id"],
                              "tracker_version": run["version"], "annotation_version": annotation["version"]}
        return self.append("attempt", record)

    def review(self, data):
        attempt = next((r for r in self.attempts() if r["id"] == data.get("attempt_id")), None)
        if not attempt:
            raise domain.ValidationError("Assessment not found.")
        correction = domain.metrics(attempt["protocol"], data["metrics"]) if data.get("metrics") is not None else None
        return self.append("review", {"attempt_id": attempt["id"], "coach": domain.text(data.get("coach"), "Reviewer name", 80),
                                      "note": domain.text(data.get("note"), "Review note", 2000), "metrics": correction,
                                      "clip_seconds": domain.number(data.get("clip_seconds", 0), "Clip timestamp", 0, 600),
                                      "original_metrics": attempt["metrics"], "version": "manual-review-1"})

    def generate_plan(self, data):
        result = domain.plan(self.player(), self.attempts(), self.events("completion"), data.get("readiness"), data.get("focus_drill_id"))
        for assignment in result["assignments"]:
            assignment["id"] = uuid.uuid4().hex
        result["readiness"] = data["readiness"]
        result["engine_version"] = "adaptive-rules-2"
        event = self.append("plan", result)
        self.set("active_plan", event)
        return event

    def complete(self, data):
        assignment = next((a for p in self.events("plan") for a in p["assignments"] if a["id"] == data.get("assignment_id")), None)
        if not assignment:
            raise domain.ValidationError("Assignment not found.")
        if any(c["assignment_id"] == assignment["id"] for c in self.events("completion")):
            raise domain.ValidationError("This assignment already has feedback.")
        return self.append("completion", {"assignment_id": assignment["id"], "protocol": assignment["protocol"],
                                          "completed": domain.flag(data.get("completed"), "Completion"),
                                          "effort": domain.number(data.get("effort"), "Effort", 1, 5, True),
                                          "note": domain.text(data.get("note", ""), "Feedback", 1000, False)})

    def approve_drill(self, data):
        if data.get("drill_id") not in DRILL:
            raise domain.ValidationError("Drill not found.")
        if data.get("qualified") is not True:
            raise domain.ValidationError("Confirm that a qualified coach reviewed the guidance.")
        return self.append("knowledge_review", {"drill_id": data["drill_id"], "reviewer": domain.text(data.get("reviewer"), "Reviewer", 80),
                                                 "note": domain.text(data.get("note"), "Review note", 1000), "version": DRILL[data["drill_id"]]["version"]})

    def export(self):
        with self.db() as db:
            settings = {r["key"]: json.loads(r["payload"]) for r in db.execute("SELECT * FROM settings")}
        return {"format": "football-helper-1", "exported": now(), "settings": settings, "events": self.events()}

    def erase(self):
        for record in self.events("media"):
            path = self.media / record["filename"]
            if path.parent.resolve() != self.media.resolve():
                raise domain.ValidationError("Unsafe media path.")
            path.unlink(missing_ok=True)
        with self.db() as db:
            db.execute("DELETE FROM events")
            db.execute("DELETE FROM settings")
        with self.db() as db:
            db.execute("VACUUM")
