# Changelog

All notable user-visible changes to Semantic Detector are documented here. The project follows semantic versioning for public releases.

## [Unreleased]

### Added
- Machine-readable JSON Schemas for messages, ground truth, predictions, and benchmark manifests.
- Reproducible benchmark/dataset policies and experiment report template.
- Coverage workflow with a 95% project-wide gate.
- `scripts/dev_check.py` for a single local verification entry point.
- Maintainer/CODEOWNERS and compatibility policy files.
- Standalone JSONL schema validation utility.
- CodeQL and pull-request dependency review workflows plus a documented security model.

### Added

- Public open-source repository structure and contribution guidance.
- GitHub Actions test and package validation workflows.
- Reproducibility, architecture, citation, roadmap, and release documentation.
- Dependabot configuration for Python and GitHub Actions dependencies.

### Fixed

- Python 3.10 release-test compatibility through the `tomli` fallback.

## Versioning policy

- **PATCH**: compatible bug fixes and detector corrections.
- **MINOR**: backward-compatible features, detectors, metrics, or tooling.
- **MAJOR**: incompatible changes to the input/output contract, taxonomy, or public Python/CLI interfaces.
