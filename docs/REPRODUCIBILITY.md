# Reproducibility Guide

This document describes how to record enough context to reproduce a Semantic Detector run.

## 1. Record the exact code version

Prefer a tagged release. For development runs, record the Git commit SHA.

```bash
git rev-parse HEAD
```

## 2. Record the environment

At minimum record Python and operating-system versions.

```bash
python --version
python -m pip freeze > environment.txt
```

## 3. Preserve inputs and configuration

Keep the sanitized input JSONL, the configuration file used, and generated manifest files together. The pipeline manifest records resolved configuration information and a stable configuration hash so accidental configuration drift can be detected.

Do not publish private captures, credentials, proprietary payloads, or datasets whose licenses prohibit redistribution.

## 4. Run the pipeline

```bash
python -m semantic_detector.cli run messages.jsonl \
  --output-dir out \
  --config config/defaults.json
```

For evaluation, preserve the exact ground-truth file as well:

```bash
python -m semantic_detector.cli evaluate \
  out/predictions.jsonl \
  ground_truth.jsonl
```

## 5. Report results conservatively

Report the protocol/dataset, sample count, preprocessing, configuration, coverage, abstention rate, accuracy/F1 metrics, and error categories. Synthetic-demo results must not be presented as real-protocol performance.

## Determinism

The current detector pipeline is rule/statistics based rather than stochastic model training. Reproducibility therefore depends primarily on identical code, inputs, ordering/contract behavior, and resolved configuration. The integration test suite includes determinism checks for supported flows.
