# Architecture

Semantic Detector is intentionally split into small stages so that field semantics, evidence, and evaluation can be inspected independently.

## Processing flow

```text
JSONL messages with field boundaries
        |
        v
I/O + strict validation
        |
        v
Field grouping and profiling
        |
        v
Semantic detectors
(constant / length / timestamp / sequence / string /
 identifier / type-control / payload)
        |
        v
Resolver + abstention/conflict handling
        |
        v
SemanticPrediction JSONL + manifest
        |
        v
Optional ground-truth evaluation
```

## Main components

### `io`

Parses JSONL records and enforces strict types. Invalid records are rejected rather than silently coerced.

### `profiling`

Groups equivalent fields across messages and computes statistical/numeric/string features used by detectors.

### `detectors`

Each detector focuses on one semantic hypothesis and returns explicit evidence rather than mutating other detector state.

### `scoring/resolver`

Combines competing evidence, applies ambiguity rules, and may abstain when evidence is insufficient or conflicting.

### `pipeline`

Coordinates validation, profiling, inference, artifact ownership, manifests, and failure behavior.

### `evaluation`

Aligns predictions with ground truth and computes accuracy, coverage, F1, confusion matrices, and categorized error records.

## Design invariants

- Field boundaries are input to the current system; the semantic detector does not silently re-segment messages.
- Invalid or ambiguous data should be visible through rejection/abstention artifacts.
- Detector evidence must remain inspectable so downstream research can explain why a label was proposed.
- Data-contract changes are treated as public interface changes.
- Demo metrics are not protocol-general benchmarks.

## Extension points

New semantic detectors should implement the existing detector interface, produce evidence using canonical taxonomy labels, and add focused unit/integration tests. Upstream boundary-refinement systems should consume exported semantic evidence through an explicit adapter rather than coupling directly to detector internals.
