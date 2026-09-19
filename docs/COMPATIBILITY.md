# Compatibility Policy

## Python

The package metadata declares Python `>=3.10`. CI continuously verifies:

| Operating system | Python | Status source |
|---|---:|---|
| Ubuntu | 3.10 | GitHub Actions `tests` |
| Ubuntu | 3.12 | GitHub Actions `tests` |
| Windows | 3.12 | GitHub Actions `tests` |
| macOS | 3.12 | GitHub Actions `tests` |

Python 3.11+ uses the standard-library `tomllib`; Python 3.10 uses the `tomli` compatibility dependency for release-contract tests.

## Compatibility promise

Until 1.0, the project may evolve public structures, but changes to JSONL contracts or canonical semantic labels must be documented in `CHANGELOG.md` and `docs/DATA_CONTRACT.md`. Silent contract changes are not acceptable.

## Platform-specific scripts

PowerShell helper scripts are conveniences rather than the only supported interface. The authoritative cross-platform interface is the Python module/CLI (`python -m semantic_detector...`).
