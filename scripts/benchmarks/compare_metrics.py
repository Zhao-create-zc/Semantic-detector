"""Compare a benchmark candidate against a committed baseline metrics file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

_METRICS: tuple[tuple[str, str], ...] = (
    ("overall_accuracy", "higher"),
    ("coverage", "higher"),
    ("unknown_rate", "lower"),
    ("covered_accuracy", "higher"),
    ("fine_top1_accuracy", "higher"),
    ("macro_f1", "higher"),
    ("error_count", "lower"),
)


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _metric_value(metrics: dict[str, Any], name: str) -> float:
    if name == "error_count":
        return float(metrics.get("counts", {}).get("error_count", 0))
    return float(metrics[name])


def _status(delta: float, direction: str, tolerance: float) -> str:
    if abs(delta) <= tolerance:
        return "unchanged"
    if direction == "higher":
        return "improved" if delta > 0 else "regressed"
    return "improved" if delta < 0 else "regressed"


def compare_metric_files(baseline_path: Path, candidate_path: Path, *, tolerance: float = 1e-12) -> dict[str, Any]:
    baseline = _read(Path(baseline_path))
    candidate = _read(Path(candidate_path))
    rows: dict[str, dict[str, Any]] = {}
    summary = {"improved": 0, "regressed": 0, "unchanged": 0}
    for name, direction in _METRICS:
        baseline_value = _metric_value(baseline, name)
        candidate_value = _metric_value(candidate, name)
        delta = candidate_value - baseline_value
        status = _status(delta, direction, tolerance)
        summary[status] += 1
        rows[name] = {
            "baseline": baseline_value,
            "candidate": candidate_value,
            "delta": delta,
            "preferred_direction": direction,
            "status": status,
        }
    return {
        "baseline": str(baseline_path),
        "candidate": str(candidate_path),
        "metrics": rows,
        "summary": summary,
    }


def render_markdown(result: dict[str, Any], *, title: str = "Benchmark comparison") -> str:
    lines = [
        f"# {title}",
        "",
        "| Metric | Baseline | Candidate | Delta | Status |",
        "|---|---:|---:|---:|---|",
    ]
    for name, row in result["metrics"].items():
        lines.append(
            f"| `{name}` | {row['baseline']:.6f} | {row['candidate']:.6f} | "
            f"{row['delta']:+.6f} | {row['status']} |"
        )
    s = result["summary"]
    lines += [
        "",
        f"Summary: **{s['improved']} improved**, **{s['regressed']} regressed**, "
        f"**{s['unchanged']} unchanged**.",
        "",
        "> This comparison is descriptive. It does not automatically establish statistical significance or publication-grade improvement.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--markdown-out", type=Path)
    parser.add_argument("--title", default="Benchmark comparison")
    parser.add_argument("--fail-on-regression", action="store_true")
    parser.add_argument("--tolerance", type=float, default=1e-12)
    args = parser.parse_args()

    result = compare_metric_files(args.baseline, args.candidate, tolerance=args.tolerance)
    payload = json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    if args.markdown_out:
        args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_out.write_text(render_markdown(result, title=args.title), encoding="utf-8")
    if args.fail_on_regression and result["summary"]["regressed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
