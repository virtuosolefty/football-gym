"""Combine original SDLC visual evidence with clearly labelled controlled browser checks."""
import html
import importlib.util
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SUITE = "review-practice-2026-10-18"
os.environ["SDLC_VISUAL_SUITE"] = SUITE
spec = importlib.util.spec_from_file_location("visual_report", ROOT / "sdlc/report-visual-five.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.build(["indoor"])
output = ROOT / "test-results" / SUITE / "report"
file = output / "report.html"
document = file.read_text(encoding="utf-8")
document = document.replace("1-collection visual QA", "Review and practice visual QA")
start = document.index('<p class="notice">')
end = document.index('</p>', start)+4
document = document[:start]+ '<p class="notice">Original D:/SDLC visual QA of review tools, two new practice drills and blind-task loading, with one actual indoor detector replay. The five-source blind batch is prepared separately; no independent labels or coach approval are claimed. Raw agent findings and the subsequent readiness fix are distinguished below.</p>'+document[end:]
figures = []
for filename,caption in [("01-practice-desktop.png","Two distinct practice drills: setup and manual session observations"),("02-practice-mobile.png","Practice layout at 390 px"),("03-review-desktop.png","Controlled detector gap and re-seed: navigation, undo and keyboard wiring"),("04-review-mobile.png","Review controls at 390 px"),("05-blind-task.png","Blind task refuses to overwrite existing annotation work"),("06-rest-preserved.png","Follow-up fix: saved Rest choice survives page reload")]:
    assert (output.parent / filename).is_file()
    figures.append(f'<figure><a href="../{filename}"><img src="../{filename}" loading="lazy" alt="{html.escape(caption)}"></a><figcaption>{html.escape(caption)}</figcaption></figure>')
extra='<div class="notice"><h2>Controlled regression and follow-up evidence</h2><p>These direct Playwright screenshots are separate from the original SDLC agent output. The synthetic tracking test uses controlled detections to exercise gaps and re-seeds; it measures UI behavior, not detector accuracy. The readiness fix was verified after the agent identified the problem. Practice observations remain manual notes. Unit checks: 76 Python and 53 JavaScript tests; 11 browser workflows.</p><div class="gallery">'+''.join(figures)+'</div></div>'
document=document.replace('</html>',extra+'</html>')
file.write_text(document,encoding="utf-8")
print(file)
