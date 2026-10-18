"""Copy the local SDLC tool into an isolated, reproducible project runtime."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def bootstrap(source, target):
    source, target = source.resolve(), target.resolve()
    if target.exists():
        raise ValueError("Runtime already exists; preserve its records and use a new target for upgrades.")
    if target == source or target.is_relative_to(source) or source.is_relative_to(target):
        raise ValueError("SDLC source and runtime must be separate directories.")
    names = ("src", "public", "test", "package.json", "package-lock.json", "README.md")
    for name in names:
        if not (source / name).exists():
            raise ValueError(f"Missing SDLC source: {name}")
    original = {}
    for name in names:
        item = source / name
        for file in item.rglob("*") if item.is_dir() else [item]:
            if file.is_file():
                original[str(file.relative_to(source))] = hashlib.sha256(file.read_bytes()).hexdigest()
    # Fail before copying if the upstream integration points changed.
    runner = (source / "src/appRunner.js").read_text(encoding="utf-8")
    builder = (source / "src/stages/build.js").read_text(encoding="utf-8")
    if runner.count("http://localhost:${port}") != 1 or runner.count("if (res.status < 500)") != 1 or builder.count("['node', 'npm', 'npx'") != 1:
        raise ValueError("SDLC source changed; review the loopback/readiness/Python adaptations before upgrading.")
    target.mkdir(parents=True)
    for name in names:
        item = source / name
        if item.is_dir():
            shutil.copytree(item, target / name)
        else:
            shutil.copy2(item, target / name)
    (target / "src/appRunner.js").write_text(runner.replace("http://localhost:${port}", "http://127.0.0.1:${port}").replace("if (res.status < 500)", "if (res.status >= 200 && res.status < 300)"), encoding="utf-8")
    (target / "src/stages/build.js").write_text(builder.replace("['node', 'npm', 'npx'", "['python', 'node', 'npm', 'npx'"), encoding="utf-8")
    shutil.copy2(Path(__file__).with_name("sdlc.config.json"), target / "sdlc.config.json")
    (target / "source-provenance.json").write_text(json.dumps({"source": str(source), "sha256": original,
        "adaptations": ["IPv4 loopback host", "2xx readiness required", "Python build/test command allowed"]}, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("D:/SDLC"))
    args = parser.parse_args()
    try:
        bootstrap(args.source, Path(__file__).with_name("runtime"))
    except (ValueError, OSError) as error:
        parser.exit(1, f"SDLC bootstrap refused: {error}\n")
    print("Runtime prepared in sdlc/runtime. Next: npm ci --prefix sdlc/runtime")
