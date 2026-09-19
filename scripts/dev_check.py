"""Run the repository's standard local verification checks."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*cmd: str) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True)


def check_json_files() -> None:
    candidates = [ROOT / "config" / "defaults.json", ROOT / "examples" / "config.json"]
    candidates.extend(sorted((ROOT / "schemas").glob("*.json")))
    candidates.extend(sorted((ROOT / "benchmarks").glob("*.json")))
    for path in candidates:
        json.loads(path.read_text(encoding="utf-8"))
        print(f"json ok: {path.relative_to(ROOT)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coverage", action="store_true", help="run pytest with the 95% coverage gate")
    args = parser.parse_args()

    check_json_files()
    run(sys.executable, "-m", "compileall", "-q", "src", "scripts")
    if args.coverage:
        run(
            sys.executable, "-m", "pytest", "-q",
            "--cov=semantic_detector", "--cov-report=term-missing", "--cov-fail-under=95",
        )
    else:
        run(sys.executable, "-m", "pytest", "-q")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
