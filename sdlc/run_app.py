"""SDLC preview/release sandbox. Never opens the player's .data directory."""
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from football.server import main

if __name__ == "__main__":
    port = int(os.environ["PORT"])
    if not 1024 <= port <= 65535:
        raise SystemExit("SDLC PORT must be between 1024 and 65535")
    sys.argv = ["app.py", "--port", str(port), "--data-dir", str(ROOT / "sdlc" / "app-data" / str(port))]
    main()
