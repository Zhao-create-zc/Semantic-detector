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
- Public Modbus/TCP and DNP3 Level-A smoke benchmark pipeline with pinned upstream PCAP sources, provenance manifests, automatic conversion, evaluation, and artifact reports.
- Cross-platform test and package validation workflows, Dependabot, release automation, citation, roadmap, and contributor documentation.

### Fixed
- Python 3.10 release-test compatibility through the `tomli` fallback.

## Versioning policy

- **PATCH**: compatible bug fixes and detector corrections.
- **MINOR**: backward-compatible features, detectors, metrics, or tooling.
- **MAJOR**: incompatible changes to the input/output contract, taxonomy, or public Python/CLI interfaces.
