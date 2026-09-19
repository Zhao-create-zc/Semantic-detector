# Public benchmark report — iti-modbus-smoke-v1

> Level A smoke benchmark. This report validates reproducibility and the end-to-end pipeline; it is not a paper-level performance claim.

## Provenance

- Protocol: `modbus`
- Dataset: ITI ICS-Security-Tools Modbus test data part 1
- Upstream: https://github.com/ITI/ICS-Security-Tools
- Pinned commit: `9b826091e7ba3fbdd5997d31e116f29e09cbbb48`
- Upstream path: `pcaps/ModbusTCP/modbus_test_data_part1.pcap`
- Upstream blob SHA-1: `ea9238c031e54af97bb45865bb7162d35fa66643`
- Semantic Detector version: `0.1.0`
- Semantic Detector commit: `7ed492ed797f9b7e322909f49b536c7a2448cb05`
- Python: `3.12.14`
- License/terms: CC BY 4.0 (repository-level LICENSE.md)
- Downloaded SHA-256: `94942b3d014810710f50836c95d3faf6df6e6370a6560bae541397c1df50213d`
- Converted messages: 44
- Ground-truth field keys: 12

## Metrics

```json
{
  "counts": {
    "error_count": 9,
    "matched_count": 12,
    "rejected_ground_truth_count": 0,
    "total_predictions": 12,
    "total_truths": 12,
    "unmatched_predictions_count": 0,
    "unmatched_truths_count": 0
  },
  "coverage": 0.75,
  "covered_accuracy": 0.3333333333333333,
  "fine_top1_accuracy": 0.0,
  "macro_f1": 0.24761904761904763,
  "macro_precision": 0.27999999999999997,
  "macro_recall": 0.3,
  "overall_accuracy": 0.25,
  "status": "ok",
  "unknown_rate": 0.25,
  "valid_for_reporting": true
}
```

## Interpretation

This smoke benchmark checks the public-data download, PCAP conversion, Semantic Detector inference, and evaluation chain. Do not generalize these metrics beyond this pinned capture without a larger protocol-specific study and independent ground-truth review.
