# Committed public smoke baselines

These directories contain lightweight snapshots from the public `public-benchmark-smoke` workflow. Raw third-party PCAPs and converted message corpora are deliberately **not** committed; they are re-downloaded from the immutable upstream source recorded in each `benchmark_manifest.json`.

| Benchmark | Messages | Overall accuracy | Coverage | Macro F1 | Role |
|---|---:|---:|---:|---:|---|
| `iti-modbus-smoke-v1` | 44 | 0.2500 | 0.7500 | 0.2476 | Level-A smoke baseline |
| `iti-dnp3-smoke-v1` | 115 | 0.3571 | 0.7857 | 0.3611 | Level-A smoke baseline |

These values are intentionally preserved even though they are modest. The purpose of the committed baseline is to expose current failure modes and make future detector improvements measurable. They are **not** paper-level claims and the generated protocol-structure ground truth still requires independent review before publication use.

Each result directory contains:

- `benchmark_manifest.json` — dataset + software provenance
- `conversion_summary.json` — extraction counts
- `metrics.json` — evaluator output
- `per_label_metrics.csv` — label-level statistics
- `confusion_matrix.csv` — truth/prediction matrix
- `errors.jsonl` — concrete wrong-label/abstention cases
- `REPORT.md` — human-readable smoke report
