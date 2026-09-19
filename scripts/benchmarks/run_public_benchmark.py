"""Download, prepare, run, and report a pinned public protocol benchmark."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import urllib.request
from datetime import date
from pathlib import Path

from scripts.benchmarks.pcap_protocol_to_jsonl import convert_pcap

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CATALOG = ROOT / "benchmarks" / "public_sources.json"
DEFAULT_CONFIG = ROOT / "config" / "defaults.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_catalog(path: Path = DEFAULT_CATALOG) -> dict[str, dict[str, object]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data:
        raise ValueError("public benchmark source catalog must be a non-empty object")
    return data


def download_trace(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "SemanticDetectorBenchmark/0.1"})
    with urllib.request.urlopen(request, timeout=60) as response, destination.open("wb") as out:
        shutil.copyfileobj(response, out)


def _run(*cmd: str) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True)


def _jsonl_count(path: Path) -> int:
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _write_report(source_id: str, source: dict[str, object], work_dir: Path, manifest: dict[str, object]) -> None:
    run_dir = work_dir / "run"
    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    report = f"""# Public benchmark report — {source_id}

> Level A smoke benchmark. This report validates reproducibility and the end-to-end pipeline; it is not a paper-level performance claim.

## Provenance

- Protocol: `{source['protocol']}`
- Dataset: {source['dataset_name']}
- Upstream: {source['upstream_home']}
- Pinned commit: `{source['source_commit']}`
- Upstream path: `{source['source_path']}`
- License/terms: {source['license_or_terms']}
- Downloaded SHA-256: `{manifest['dataset']['sha256']}`
- Converted messages: {manifest['input']['message_count']}
- Ground-truth field keys: {manifest['ground_truth']['field_count']}

## Metrics

```json
{json.dumps(metrics, indent=2, sort_keys=True)}
```

## Interpretation

This smoke benchmark checks the public-data download, PCAP conversion, Semantic Detector inference, and evaluation chain. Do not generalize these metrics beyond this pinned capture without a larger protocol-specific study and independent ground-truth review.
"""
    (work_dir / "REPORT.md").write_text(report, encoding="utf-8")


def run_benchmark(source_id: str, work_dir: Path, catalog_path: Path = DEFAULT_CATALOG) -> dict[str, object]:
    catalog = load_catalog(catalog_path)
    if source_id not in catalog:
        raise KeyError(f"unknown public benchmark source: {source_id}")
    source = catalog[source_id]
    protocol = str(source["protocol"])

    work_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = work_dir / "raw"
    prepared_dir = work_dir / "prepared"
    run_dir = work_dir / "run"
    raw_path = raw_dir / Path(str(source["source_path"])).name
    messages_path = prepared_dir / "messages.jsonl"
    truth_path = prepared_dir / "ground_truth.jsonl"
    config_path = prepared_dir / "config.json"

    download_trace(str(source["download_url"]), raw_path)
    source_sha256 = sha256_file(raw_path)
    conversion = convert_pcap(protocol, raw_path, messages_path, truth_path)
    if conversion["message_count"] <= 0:
        raise RuntimeError("public PCAP conversion produced no messages")
    shutil.copy2(DEFAULT_CONFIG, config_path)

    _run(
        sys.executable,
        "-m",
        "semantic_detector.cli",
        "run",
        str(messages_path),
        "--output-dir",
        str(run_dir),
        "--config",
        str(config_path),
    )
    _run(
        sys.executable,
        "-m",
        "semantic_detector.cli",
        "evaluate",
        str(run_dir / "predictions.jsonl"),
        str(truth_path),
    )

    manifest: dict[str, object] = {
        "benchmark_id": source_id,
        "protocol": protocol.upper() if protocol == "dnp3" else "Modbus/TCP",
        "message_type": None,
        "dataset": {
            "name": source["dataset_name"],
            "source": source["download_url"],
            "license_or_terms": source["license_or_terms"],
            "retrieved_at": date.today().isoformat(),
            "sha256": source_sha256,
            "redistributable": False,
            "notes": source["notes"],
        },
        "input": {
            "messages_jsonl": str(messages_path.relative_to(work_dir)),
            "message_count": conversion["message_count"],
        },
        "ground_truth": {
            "file": str(truth_path.relative_to(work_dir)),
            "field_count": _jsonl_count(truth_path),
            "method": "protocol-structure annotation generated by the repository's pinned PCAP converter; requires independent review before paper-level claims",
            "reviewed_by": [],
        },
        "config": {
            "file": str(config_path.relative_to(work_dir)),
            "sha256": sha256_file(config_path),
        },
        "reporting": {
            "required_metrics": [
                "overall_accuracy",
                "coverage",
                "unknown_rate",
                "covered_accuracy",
                "fine_top1_accuracy",
                "macro_f1",
            ],
            "error_analysis": True,
        },
    }
    (work_dir / "benchmark_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (work_dir / "conversion_summary.json").write_text(
        json.dumps(conversion, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    _write_report(source_id, source, work_dir, manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_id", help="source id from benchmarks/public_sources.json")
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    args = parser.parse_args()
    manifest = run_benchmark(args.source_id, args.work_dir, args.catalog)
    print(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
