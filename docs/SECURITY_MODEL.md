# Security Model

Semantic Detector processes binary-protocol research data and should treat every input file as untrusted.

## Trust boundaries

1. **Input JSONL** — untrusted structured data. Parsing is strict and rejects malformed payloads, invalid spans, unsupported directions, and inconsistent groups.
2. **Configuration JSON** — untrusted configuration. Invalid values must fail closed rather than silently changing detector behavior.
3. **Output directory** — user-controlled filesystem destination. The tool should write only documented artifacts owned by the active command.
4. **Third-party traces** — may contain sensitive or restricted data even when syntactically valid. Dataset policy and authorization remain the operator's responsibility.

## Security goals

- malformed input must not become arbitrary code execution;
- malformed fields must not escape their declared payload bounds;
- failed runs must not leave stale success artifacts that can be mistaken for current results;
- public examples and benchmarks must not contain credentials, private traffic, or restricted datasets;
- third-party source and license provenance must remain traceable.

## Non-goals

Semantic Detector is not a sandbox for executing protocol implementations, not a malware detonation environment, and not a network intrusion tool. It analyzes supplied data offline and does not provide authorization to capture or inspect third-party traffic.

## Continuous checks

The public repository uses:

- cross-platform pytest CI;
- a 95% coverage gate;
- package build/Twine validation;
- CodeQL static analysis for Python;
- Dependabot for Python and GitHub Actions updates;
- dependency review for high-severity vulnerable dependencies introduced by pull requests.

See `SECURITY.md` for reporting guidance and `docs/DATASET_POLICY.md` for trace-handling rules.
