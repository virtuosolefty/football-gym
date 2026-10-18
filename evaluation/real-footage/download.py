"""Download only the three public source URLs in sources.json for this evaluation."""
import hashlib
import json
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DESTINATION = ROOT / "test-results" / "real-footage" / "footage"


def main():
    manifest = json.loads((Path(__file__).parent / "sources.json").read_text())
    DESTINATION.mkdir(parents=True, exist_ok=True)
    records = []
    for clip in manifest["clips"]:
        url = clip["download"]
        if urllib.parse.urlparse(url).hostname != "videos.pexels.com":
            raise ValueError("Only the reviewed public Pexels video URLs are allowed.")
        target = DESTINATION / clip["file"]
        if not target.exists():
            request = urllib.request.Request(url, headers={"User-Agent": "FootballHelperEvaluation/1"})
            temporary = target.with_suffix(".part")
            try:
                with urllib.request.urlopen(request, timeout=45) as response, temporary.open("wb") as output:
                    if response.headers.get("Content-Type", "").split(";")[0] != "video/mp4":
                        raise ValueError("Source did not return an MP4 video.")
                    size = 0
                    while chunk := response.read(256 * 1024):
                        size += len(chunk)
                        if size > 64 * 1024 * 1024:
                            raise ValueError("Source exceeded the app's 64 MB file limit.")
                        output.write(chunk)
                temporary.replace(target)
            finally:
                temporary.unlink(missing_ok=True)
        records.append({"id": clip["id"], "file": str(target.relative_to(ROOT)), "bytes": target.stat().st_size,
                        "sha256": hashlib.sha256(target.read_bytes()).hexdigest()})
        print(json.dumps(records[-1]), flush=True)
    (Path(__file__).parent / "downloads.json").write_text(json.dumps(records, indent=2) + "\n")


if __name__ == "__main__":
    main()
