# Real-protocol smoke baseline — 2026-09-19

This page records the first reproducible public-PCAP baseline produced by the repository's automated benchmark workflow. It is a **Level-A smoke baseline**, not a publication-grade performance claim.

## Inputs

Both traces come from the pinned `ITI/ICS-Security-Tools` repository revision recorded in the result manifests. The upstream repository uses a repository-level CC BY 4.0 license. Semantic Detector does not vendor the raw PCAPs.

| Protocol | Converted messages | Truth field keys | PCAP SHA-256 |
|---|---:|---:|---|
| Modbus/TCP | 44 | 12 | `94942b3d014810710f50836c95d3faf6df6e6370a6560bae541397c1df50213d` |
| DNP3 | 115 | 14 | `7a30496184c93b12ef57fd0877acbead85975b20a8db35d8ac7b5c45e4f9f305` |

Software provenance for this snapshot: Semantic Detector `0.1.0`, commit `7ed492ed797f9b7e322909f49b536c7a2448cb05`, Python `3.12.14`, GitHub Actions run `35421188002`.

## Baseline metrics

| Protocol | Overall accuracy | Coverage | Covered accuracy | Macro F1 | Errors |
|---|---:|---:|---:|---:|---:|
| Modbus/TCP | 0.2500 | 0.7500 | 0.3333 | 0.2476 | 9 |
| DNP3 | 0.3571 | 0.7857 | 0.4545 | 0.3611 | 9 |

The low values are useful: they show that the synthetic/demo success cases did not hide the harder real-protocol behavior.

## Observed failure modes

### 1. Constant evidence dominates structural semantics

A protocol field can be semantically a length, identifier, or control field while being constant within one capture. The current resolver can therefore select `constant` even when the protocol-defined role is different. This appears in Modbus length/unit-id fields and DNP3 control/source fields.

### 2. Short binary identifiers can look like strings

Two-byte or similarly short binary fields may accidentally satisfy printable/UTF-8 heuristics. DNP3 destination addresses and Modbus transaction identifiers demonstrate this failure mode in the smoke baseline.

### 3. DNP3 length semantics are not a simple raw-frame length relation

DNP3 inserts CRC words per data block. The link-layer length byte describes logical link data rather than the final raw TCP payload size including all CRC bytes. A generic `total_message_length` / `remaining_bytes` relation is therefore insufficient without protocol-structure awareness.

### 4. Payload is not always high-entropy opaque data

Real application payloads may be short, structured, printable, or repetitive. In the Modbus trace, payload fields can be classified as strings or rejected rather than `payload`.

### 5. A constant function/control value remains semantically type/control

A single capture may exercise only one operation. Frequency variation alone cannot prove a field is a type/opcode; cross-message-type or cross-layout evidence is needed.

## What this baseline should drive next

1. add semantic precedence that can distinguish **observed value behavior** from **protocol role**;
2. add minimum-width / binary-printability safeguards to string detection;
3. model structured length relations, including protocol framing overhead;
4. make type/opcode inference use cross-layout evidence rather than only within-layout variation;
5. improve payload detection for low-entropy structured payloads;
6. independently review ground truth before promoting any result to Level B.

Raw details are committed under `benchmarks/results/` so future changes can be compared against the same pinned source traces.
