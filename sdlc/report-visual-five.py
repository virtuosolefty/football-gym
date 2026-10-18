"""Build a local HTML/Markdown report from the five SDLC visual QA records."""
import html
import json
import os
import sys
from pathlib import Path
import re
import shutil
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
SUITE = os.environ.get("SDLC_VISUAL_SUITE", "sdlc-visual-five-2026-10-18")
assert re.fullmatch(r"[a-z0-9-]+", SUITE), "Invalid suite folder"
RESULTS = ROOT / "test-results" / SUITE


def display_text(value):
    """Repair known agent-output encoding artifacts for display; retain raw JSON."""
    text = str(value)
    for character in "→–—·’":
        text = text.replace(character.encode("utf-8").decode("cp1252"), character)
    return text


def summarize(record):
    directory = Path(record["appData"]).resolve()
    assert directory.is_relative_to(RESULTS.resolve()), "Only test data may be read"
    database = directory / "football.sqlite3"
    with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as db:
        events = db.execute("SELECT payload FROM events WHERE kind='analysis' ORDER BY rowid").fetchall()
    if not events:
        return None
    run = json.loads(events[-1][0])
    samples = run.get("samples", [])
    result = {"method": run.get("configuration", {}).get("method"), "window": [run["start"], run["end"]],
              "samples": len(samples), "found": sum(s["found"] for s in samples),
              "coverage": run["report"]["coverage"], "status": run["report"]["status"],
              "provisional_contacts": [p["time"] for p in run.get("candidates", [])],
              "losses": [{"time": s["time"], "reason": s["lost_reason"]} for s in samples if s.get("lost_reason")],
              "validated": run["report"].get("quality", {}).get("validated", False)}
    boundary = {"scene-cut": 5.8, "edge-exit": 36.3}.get(record["case"]["id"])
    if boundary is not None:
        result["emissions_in_prior_decoy_interval"] = sum(s["found"] and s["time"] >= boundary for s in samples)
    return result


def build(selected=()):
    cases = json.loads((ROOT / "sdlc/visual-five.json").read_text(encoding="utf-8"))
    assert set(selected) <= {c["id"] for c in cases}, "Unknown case"
    if selected:
        cases = [c for c in cases if c["id"] in selected]
    records = []
    for file in RESULTS.glob("*.json"):
        item = json.loads(file.read_text(encoding="utf-8"))
        if "case" in item and "result" in item:
            records.append(item)
    assert {r["case"]["id"] for r in records} == {c["id"] for c in cases}, "Need an actual attempt for every selected case"
    output = RESULTS / "report"
    output.mkdir(exist_ok=True)
    escape = lambda value: html.escape(display_text(value), quote=True)
    review_file = RESULTS / "review.json"
    review = json.loads(review_file.read_text(encoding="utf-8")) if review_file.exists() else {}
    cards, rows, combined = [], [], []
    lines = [f"# {len(cases)}-collection SDLC visual QA", "", "Original engine: D:\\SDLC\\src\\stages\\qa.js. Representative public clips; not whole-dataset accuracy evaluation or independent human labelling.", "", "| Case / collection | SDLC verdict | Saved tracking result |", "| --- | --- | --- |"]
    for case in cases:
        attempts = sorted((r for r in records if r["case"]["id"] == case["id"]), key=lambda r: r["result"]["createdAt"])
        record = attempts[-1]
        result = record["result"]
        run_id = result["id"]
        assert re.fullmatch(r"[a-f0-9]{8}", run_id)
        metrics = summarize(record)
        run_dir = ROOT / "sdlc/runtime/data/runs" / run_id
        assets = output / case["id"]
        assets.mkdir(exist_ok=True)
        figures = []
        for name in result.get("screenshots", []):
            assert Path(name).name == name and name.endswith(".png")
            source = run_dir / name
            assert source.is_file(), f"Missing screenshot: {source}"
            if source.is_file():
                shutil.copy2(source, assets / name)
                relative = f"{case['id']}/{name}"
                figures.append(f'<figure><a href="{escape(relative)}"><img loading="lazy" src="{escape(relative)}" alt="{escape(case["id"] + ": " + name)}"></a><figcaption>{escape(name)}</figcaption></figure>')
        raw = {**record, "saved_analysis": metrics, "review": review.get(case["id"], {})}
        raw["attempts"] = [{"id": r["result"]["id"], "status": r["result"]["status"],
                            "verdict": r["result"].get("verdict"),
                            "reason": r["result"].get("couldntRunReason")} for r in attempts]
        (assets / "report.json").write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
        downloads = sorted(run_dir.glob("analysis-*.json"))
        if downloads:
            shutil.copy2(downloads[-1], assets / "analysis.json")
        verdict = result.get("verdict") or "could not run"
        saved = f"{metrics['status']}, {metrics['found']}/{metrics['samples']} samples, {len(metrics['provisional_contacts'])} proposals" if metrics else "No saved analysis"
        rows.append(f'<tr><td><a href="#{case["id"]}">{escape(case["id"])}</a><br>{escape(case["collection"])}</td><td>{escape(verdict)}</td><td>{escape(saved)}</td></tr>')
        lines.append(f"| {case['id']} / {case['collection']} | {verdict} | {saved} |")
        steps = ''.join(f'<li><strong>{escape(s.get("title", "Step"))}</strong> — {escape(s.get("status", ""))}<p>{escape(s.get("observation", ""))}</p></li>' for s in result.get("steps", []))
        bugs = ''.join(f'<li><strong>{escape(b.get("title", "Finding"))}</strong> ({escape(b.get("severity", ""))})<p>{escape(b.get("reproSteps", ""))}</p><p>Expected: {escape(b.get("expected", ""))}<br>Observed: {escape(b.get("actual", ""))}</p></li>' for b in result.get("bugs", []))
        review_note = review.get(case["id"], {}).get("note", "No separate adjudication recorded.")
        cards.append(f'<section id="{case["id"]}"><h2>{escape(case["id"])} · {escape(verdict)}</h2><p>{escape(case["collection"])} · {case["start"]}–{case["end"]} seconds · SDLC run {run_id}</p><p><a href="{escape(case["source"])}">Original source</a> · {escape(case["license"])}</p><h3>Review of evidence</h3><p>{escape(review_note)}</p><pre>{escape(json.dumps(metrics, indent=2))}</pre><details><summary>SDLC agent report and raw findings</summary><p>{escape(result.get("summary") or result.get("couldntRunReason", "No summary"))}</p><ol>{steps}</ol><ul>{bugs}</ul><p>Console errors: {escape(result.get("consoleErrors", []))}</p><p>Attempts retained: {len(attempts)} · Reported cost: ${result.get("costUsd", 0):.3f}</p><a href="{case["id"]}/report.json">Structured report</a></details><div class="gallery">{"".join(figures)}</div></section>')
        combined.append(raw)
    lines += ["", "## Evidence and limitations", "", "Open report.html for screenshots, raw SDLC findings and review notes. Each case's report.json contains the structured run and saved-analysis verification. Earlier unsuccessful attempts remain in the parent folder and SDLC records. The raw agent verdict is preserved separately from evidence review; an edge-exit workflow pass is not an accuracy pass.", "", "Coverage is not correctness. The indoor contact reference is implementer-labelled. Public dataset label alignment and independence remain unverified. Pose is off in these runs. No real player records were used, and provisional tracks were not converted to athlete measurements."]
    for record in combined:
        lines += ["", f"## {record['case']['id']}", "", record["result"].get("summary") or record["result"].get("couldntRunReason", "No report"), "", review.get(record["case"]["id"], {}).get("note", "No separate adjudication recorded.")]
    (output / "REPORT.md").write_text(display_text("\n".join(lines)) + "\n", encoding="utf-8")
    (output / "results.json").write_text(json.dumps(combined, indent=2) + "\n", encoding="utf-8")
    document = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Football Helper · Five-collection visual QA</title><style>body{font:16px/1.55 system-ui,sans-serif;max-width:1180px;margin:40px auto;padding:0 22px;color:#173b32;background:#f5f7f3}h1,h2{line-height:1.2}section{margin:32px 0;padding:24px;background:white;border:1px solid #ccd8d0;border-radius:12px}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:12px;border-bottom:1px solid #ccd8d0}a{color:#216a52}pre{white-space:pre-wrap;background:#eef2ed;padding:16px;border-radius:8px;font-size:13px}.gallery{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:16px;margin-top:20px}figure{margin:0}img{width:100%;max-height:420px;object-fit:contain;object-position:top;border:1px solid #ccd8d0;background:#eef2ed}figcaption{font-size:12px;overflow-wrap:anywhere}.notice{padding:16px;background:#fff2cf;border-radius:8px}details{padding:12px 0}li{margin-bottom:12px}@media(max-width:600px){body{padding:0 12px;margin:20px auto}section{padding:14px}td,th{padding:7px;font-size:13px}}</style><h1>Football Helper<br>Five-collection visual QA</h1><p>Actual visual QA stage from D:\\SDLC · Edge browser · isolated test data</p><p class="notice">Five representative clips, one per existing collection. These are visual workflow checks, not exhaustive dataset evaluation or independent football accuracy certification. Raw agent passes describe workflow completion, not accuracy; rain remains a detector warning. Model warnings and QA-agent/tool failures are reported separately.</p><table><thead><tr><th>Case / collection</th><th>SDLC verdict</th><th>Saved tracking result</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table>' + ''.join(cards) + '<p>Original videos and SDLC source are unchanged. Provisional contacts remain unvalidated; no real athlete assessments were created.</p></html>'
    assert '&lt;script&gt;' == escape('<script>')
    assert display_text('\u00e2\u2020\u2019') == '\u2192'
    document = document.replace('Five-collection visual QA', f'{len(cases)}-collection visual QA').replace('Five representative clips', f'{len(cases)} representative clips')
    (output / "report.html").write_text(document, encoding="utf-8")
    print(output / "report.html")


if __name__ == "__main__":
    build(sys.argv[1:])
