# Roadmap

This roadmap describes intended directions, not promised dates. Items may change as protocol samples and research results reveal better priorities.

## 0.1.x — Public baseline and reproducibility

- Keep Python 3.10+ CI green across supported platforms.
- Improve packaging, examples, documentation, and release reproducibility.
- Expand sanitized test fixtures for current semantic detectors.
- Clarify confidence, abstention, and error-reporting behavior.

## 0.2.x — Benchmark and protocol coverage

- Add a reusable benchmark harness for public protocol datasets.
- Report per-protocol and cross-protocol metrics instead of relying on synthetic demo results.
- Add reproducible experiments for representative protocols such as Modbus, DNP3, and other publicly redistributable samples where licensing permits.
- Record dataset provenance and preprocessing assumptions alongside results.

## 0.3.x — Semantic feedback for boundary refinement

- Define a stable interface that exposes semantic evidence to upstream field-boundary algorithms.
- Add constrained merge/split/shift candidate evaluation rather than unconstrained re-segmentation.
- Measure whether semantic feedback improves boundary accuracy without degrading already-correct boundaries.

## Toward 1.0

A 1.0 release should have a stable data contract, documented extension interfaces, reproducible public benchmarks, cross-platform packaging, and enough real-protocol evidence to distinguish demonstrated behavior from research hypotheses.
