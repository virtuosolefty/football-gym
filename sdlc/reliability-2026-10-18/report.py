"""Report the real SDLC attempt separately from direct browser fallback evidence."""
import hashlib
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "test-results/reliability-2026-10-18"
REPORT = OUT / "report"
REPORT.mkdir(exist_ok=True)
record = json.loads((OUT / "indoor-e71ad723.json").read_text(encoding="utf-8"))
benchmark = json.loads((OUT / "worker-benchmark.json").read_text(encoding="utf-8"))["results"][0]
rows = []
for name in ["rain-context", "bottle", "cone", "floor-ball", "studio-pose", "indoor-worker-analysis"]:
    run = json.loads((OUT / (name + ".json")).read_text(encoding="utf-8"))
    rows.append({"clip": name, "found": sum(s["found"] for s in run["samples"]), "samples": len(run["samples"]), "status": run["report"]["status"], "contacts": [e["time"] for e in run["candidates"]]})
summary = {"sdlc": {"id": record["result"]["id"], "verdict": "couldnt_run", "reason": record["result"]["couldntRunReason"]},
           "fallback": "direct Playwright, visually inspected by implementer; not independent labels",
           "checks": {"python": 74, "javascript": 51, "browser_workflows": 9}, "replays": rows, "benchmark": benchmark,
           "sourceFiles": {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in ["web/detector.js", "web/detector-worker.js", "web/video-lab.js", "football/video.py"]}}
(REPORT / "results.json").write_text(json.dumps([summary], indent=2) + "\n", encoding="utf-8")
escape = html.escape
parts = ["""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Football Helper reliability QA</title>
<style>body{font:16px/1.6 system-ui;background:#f5f6ef;color:#143e32;margin:auto;padding:24px;max-width:1050px}h1,h2{line-height:1.2}section,.card{background:white;padding:20px;margin:20px 0;border:1px solid #d5dfd6;border-radius:12px}img{max-width:100%;height:auto}a{color:#176850;overflow-wrap:anywhere}pre{white-space:pre-wrap;overflow-wrap:anywhere}.scroll{overflow:auto}table{border-collapse:collapse}td,th{padding:10px;text-align:left;border-bottom:1px solid #ddd}.notice{background:#fff2d9;padding:14px}figure{margin:24px 0}</style>
<h1>Responsive analysis and explicit empty reviews</h1><p>October 18, 2026. Separate test data; original videos and D:\SDLC unchanged.</p><section>
<h2>Original SDLC visual QA: could not run</h2><p class="notice">""", escape(summary["sdlc"]["reason"]), "</p><p>No SDLC agent visual pass is claimed. Raw attempt: <a href='../indoor-e71ad723.json'>e71ad723</a>.</p>",
"<h2>Direct browser fallback: passed</h2><p>Actual installed model cancellation and restart; reviewed-empty validation, reload and export; desktop and mobile layout with no horizontal overflow or browser errors. The empty review is simulated test input, not independent contact labels.</p>",
"<p>74 Python tests, 51 JavaScript tests and 9 automated browser workflows pass. Busy-worker cancellation measured 99 / 118 / 117 ms for loading / selection / tracking. No partial runs were saved; navigation terminated workers.</p>",
"<h2>Installed-model replay evidence</h2><p>All five pre-existing regression tracks match their prior time, found, position, score, radius, segment and loss-reason fields exactly. This verifies preservation on these samples, not general accuracy.</p><div class='scroll'><table><tr><th>Clip</th><th>Found</th><th>Status</th><th>Provisional contacts (s)</th></tr>"]
for row in rows:
    parts.append(f"<tr><td><a href='../{row['clip']}.json'>{row['clip']}</a></td><td>{row['found']}/{row['samples']}</td><td>{row['status']}</td><td>{escape(str(row['contacts']))}</td></tr>")
parts += ["</table></div><h2>300-sample compute diagnostic</h2>", f"<p>Looped 30-second clip with detector and pose: {benchmark['elapsed_ms']/1000:.1f} seconds; {benchmark['heartbeat_ticks']} UI heartbeat ticks, longest gap {benchmark['max_heartbeat_gap_ms']:.1f} ms. One run, other test activity on this machine; fixed crops do not measure app tracking throughput or natural juggling accuracy.</p>", "<p><a href='../worker-benchmark.json'>Raw timing report</a></p><h2>Visual evidence</h2>"]
for file, caption in [("01-cancelled.png", "Real model loading cancelled; no saved run"), ("02-real-tracking.png", "Restart succeeds: 30/30 indoor detections, three provisional contacts; still suspect"), ("03-review-required.png", "An empty timeline still requires explicit review confirmation"), ("04-empty-reviewed-desktop.png", "Reloaded reviewed-zero state is distinct from not reviewed"), ("05-empty-reviewed-mobile.png", "390 px mobile layout: readable warnings, stacked saved-run fields")]:
    assert (OUT / file).is_file()
    parts.append(f"<figure><figcaption>{escape(caption)}</figcaption><a href='../{file}'><img src='../{file}' alt='{escape(caption, quote=True)}' loading='lazy'></a></figure>")
parts += ["<p><a href='../empty-reviewed-analysis.json'>Empty-reviewed export</a> (test fixture only). See the prior five-collection evaluation for broader coverage. Studio contact misses, rain/small-ball recall, independently labelled natural 30-second windows and threshold calibration remain open.</p></section></html>"]
(REPORT / "report.html").write_text("".join(parts), encoding="utf-8")
print(REPORT / "report.html")
