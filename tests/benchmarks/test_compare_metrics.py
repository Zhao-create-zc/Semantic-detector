from __future__ import annotations

import json
from pathlib import Path

from scripts.benchmarks.compare_metrics import compare_metric_files, render_markdown


def _write(path: Path, *, accuracy: float, coverage: float, macro_f1: float, unknown: float, errors: int) -> None:
    path.write_text(json.dumps({
        "overall_accuracy": accuracy,
        "coverage": coverage,
        "unknown_rate": unknown,
        "covered_accuracy": accuracy,
        "fine_top1_accuracy": 0.0,
        "macro_f1": macro_f1,
        "macro_precision": macro_f1,
        "macro_recall": macro_f1,
        "counts": {"error_count": errors},
    }), encoding="utf-8")


def test_compare_metric_files_classifies_direction(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    _write(baseline, accuracy=0.25, coverage=0.75, macro_f1=0.20, unknown=0.25, errors=9)
    _write(candidate, accuracy=0.40, coverage=0.70, macro_f1=0.30, unknown=0.20, errors=7)

    result = compare_metric_files(baseline, candidate)

    assert result["metrics"]["overall_accuracy"]["status"] == "improved"
    assert result["metrics"]["coverage"]["status"] == "regressed"
    assert result["metrics"]["unknown_rate"]["status"] == "improved"
    assert result["metrics"]["error_count"]["status"] == "improved"
    assert result["summary"] == {"improved": 5, "regressed": 1, "unchanged": 1}


def test_render_markdown_contains_deltas(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"
    _write(baseline, accuracy=0.25, coverage=0.75, macro_f1=0.20, unknown=0.25, errors=9)
    _write(candidate, accuracy=0.30, coverage=0.75, macro_f1=0.20, unknown=0.25, errors=9)

    text = render_markdown(compare_metric_files(baseline, candidate), title="Modbus")
    assert "# Modbus" in text
    assert "overall_accuracy" in text
    assert "+0.050000" in text
    assert "improved" in text
