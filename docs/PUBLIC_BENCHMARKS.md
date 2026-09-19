# Public benchmark pipeline

Semantic Detector keeps third-party PCAP files out of the repository and reconstructs public smoke benchmarks from immutable upstream sources.

## Data flow

```text
pinned upstream PCAP
       ↓
stdlib PCAP / Ethernet / IPv4 / TCP reader
       ↓
per-direction TCP stream reassembly
       ↓
protocol frame extraction
  ├─ Modbus/TCP: MBAP length framing
  └─ DNP3: 0x0564 sync + link length framing
       ↓
messages.jsonl + ground_truth.jsonl
       ↓
Semantic Detector run
       ↓
evaluate
       ↓
metrics + errors + benchmark manifest + report
```

## Why the raw capture is not committed

A public URL is not automatically a sufficient reason to re-host a dataset. The benchmark catalog therefore records the original repository, immutable commit, path, attribution, license/terms, and Git blob identifier, while the workflow downloads the raw capture directly from the upstream project.

This also keeps provenance explicit: an experiment can identify the exact source bytes by pinned commit plus the SHA-256 recorded after download.

## Protocol normalization choices

### Modbus/TCP

Each extracted ADU is represented with six fields:

1. transaction identifier → `identifier`
2. protocol identifier → `constant`
3. length → `length`
4. unit identifier → `identifier`
5. function code → `type_control`
6. PDU data → `payload`

The converter keeps the raw ADU bytes unchanged.

### DNP3

Each extracted raw link frame is represented with seven fields:

1. start bytes → `constant`
2. link length → `length`
3. control → `type_control`
4. destination → `identifier`
5. source → `identifier`
6. header CRC → `unknown`
7. raw remaining link payload (including DNP3 data-block CRC bytes) → `payload`

The current taxonomy has no checksum class, so CRC is intentionally `unknown` instead of being forced into an incorrect semantic label. The raw DNP3 bytes are preserved rather than silently stripping CRC bytes.

## Reassembly limitations

The standard-library converter supports classic PCAP with Ethernet / IPv4 / TCP. It handles retransmission overlap and splits a flow when a TCP sequence gap is observed. It does not currently support PCAPNG, IPv6, IP fragment reassembly, or advanced TCP ambiguity resolution. These limitations are acceptable for the pinned Level-A smoke traces but must be revisited for paper-level benchmarking.

## Reporting level

The automated workflow is **Level A — Smoke** under `docs/BENCHMARKING.md`. A future Level B result requires independent ground-truth review, documented inclusion/exclusion criteria, protocol-specific sample accounting, and an error analysis suitable for publication.
