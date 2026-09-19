# Public benchmark report — iti-dnp3-smoke-v1

> Level A smoke benchmark. This report validates reproducibility and the end-to-end pipeline; it is not a paper-level performance claim.

## Provenance

- Protocol: `dnp3`
- Dataset: ITI ICS-Security-Tools DNP3 sample capture
- Upstream: https://github.com/ITI/ICS-Security-Tools
- Pinned commit: `9b826091e7ba3fbdd5997d31e116f29e09cbbb48`
- Upstream path: `pcaps/bro/dnp3/dnp3.pcap`
- Upstream blob SHA-1: `8ee8d3ec6129aa7730a0e967d955d347f0722c10`
- Semantic Detector version: `0.1.0`
- Semantic Detector commit: `7ed492ed797f9b7e322909f49b536c7a2448cb05`
- Python: `3.12.14`
- License/terms: CC BY 4.0 (repository-level LICENSE.md)
- Downloaded SHA-256: `7a30496184c93b12ef57fd0877acbead85975b20a8db35d8ac7b5c45e4f9f305`
- Converted messages: 115
- Ground-truth field keys: 14

## Metrics

```json
{
  "counts": {
    "error_count": 9,
    "matched_count": 14,
    "rejected_ground_truth_count": 0,
    "total_predictions": 14,
    "total_truths": 14,
    "unmatched_predictions_count": 0,
    "unmatched_truths_count": 0
  },
  "coverage": 0.7857142857142857,
  "covered_accuracy": 0.45454545454545453,
  "fine_top1_accuracy": 0.0,
  "macro_f1": 0.3611111111111111,
  "macro_precision": 0.3888888888888889,
  "macro_recall": 0.4166666666666667,
  "overall_accuracy": 0.35714285714285715,
  "status": "ok",
  "unknown_rate": 0.21428571428571427,
  "valid_for_reporting": true
}
```

## Interpretation

This smoke benchmark checks the public-data download, PCAP conversion, Semantic Detector inference, and evaluation chain. Do not generalize these metrics beyond this pinned capture without a larger protocol-specific study and independent ground-truth review.
