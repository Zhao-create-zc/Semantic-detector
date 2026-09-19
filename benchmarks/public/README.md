# Public protocol smoke benchmarks

This directory documents reproducible Level-A smoke benchmarks that use public packet captures without vendoring the raw PCAP files into this repository.

The source catalog is `benchmarks/public_sources.json`. Each source is pinned to an immutable upstream Git commit and records the upstream repository, file path, repository-level licensing terms, attribution, and Git blob SHA-1.

## Supported smoke sources

| Source ID | Protocol | Upstream file | Purpose |
|---|---|---|---|
| `iti-modbus-smoke-v1` | Modbus/TCP | `ITI/ICS-Security-Tools/pcaps/ModbusTCP/modbus_test_data_part1.pcap` | Validate Modbus/TCP PCAP extraction → JSONL → inference → evaluation |
| `iti-dnp3-smoke-v1` | DNP3 | `ITI/ICS-Security-Tools/pcaps/bro/dnp3/dnp3.pcap` | Validate DNP3 PCAP extraction → JSONL → inference → evaluation |

The upstream `ITI/ICS-Security-Tools` repository publishes a repository-level CC BY 4.0 license. Semantic Detector still downloads the raw captures at benchmark time instead of redistributing them here.

## Run

```bash
python -m scripts.benchmarks.run_public_benchmark \
  iti-modbus-smoke-v1 \
  --work-dir benchmark-output/iti-modbus-smoke-v1

python -m scripts.benchmarks.run_public_benchmark \
  iti-dnp3-smoke-v1 \
  --work-dir benchmark-output/iti-dnp3-smoke-v1
```

Each run produces:

- `raw/` — downloaded upstream PCAP (ignored by git)
- `prepared/messages.jsonl` — Semantic Detector input
- `prepared/ground_truth.jsonl` — protocol-structure truth keys
- `prepared/config.json` — exact config snapshot
- `run/` — predictions, metrics, confusion matrix, errors, manifests
- `benchmark_manifest.json` — provenance and reproducibility metadata
- `conversion_summary.json` — extraction counts
- `REPORT.md` — human-readable Level-A report

## Scope

These smoke benchmarks are deliberately narrow. Ground truth is generated from protocol structure rules and has not yet undergone independent research annotation. The results therefore validate the toolchain and expose failure modes; they must not be cited as general Modbus/DNP3 performance.
