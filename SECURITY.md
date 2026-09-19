# Security Policy

## Supported versions

The project is currently pre-1.0. Security fixes are applied to the latest `main` branch and, after tagged releases begin, to the latest supported release line when practical.

| Version | Supported |
|---|---|
| `main` | Yes |
| older untagged snapshots | No guaranteed backport |

## Reporting a vulnerability

Do not paste real credentials, private PCAP contents, tokens, private keys, or sensitive customer/project data into a public issue.

A useful report includes:

- affected commit/version;
- minimal reproducible input with sensitive data removed;
- expected vs actual behavior;
- impact and affected component;
- reproduction steps;
- suggested mitigation, if known.

If GitHub private vulnerability reporting is available for this repository, prefer that channel. Otherwise, open a minimal public issue that describes the affected component without publishing exploit secrets or sensitive payloads, so the maintainer can coordinate the next step.

## Scope

Examples of security-relevant issues include arbitrary code execution, path traversal, unsafe artifact overwrite, sensitive information disclosure, malicious input bypassing validation, dependency vulnerabilities, and license/provenance regressions that can cause unsafe redistribution.

This project is intended for authorized protocol-analysis research and defensive engineering. Only process data and systems you are permitted to analyze.

For trust boundaries and continuous checks, see [docs/SECURITY_MODEL.md](docs/SECURITY_MODEL.md).
