from __future__ import annotations

import json
import struct
from pathlib import Path

from scripts.benchmarks.pcap_protocol_to_jsonl import convert_pcap


def _ipv4_tcp_packet(*, src_port: int, dst_port: int, seq: int, payload: bytes) -> bytes:
    eth = b"\x00" * 12 + b"\x08\x00"
    src_ip = b"\x0a\x00\x00\x01"
    dst_ip = b"\x0a\x00\x00\x02"
    total_len = 20 + 20 + len(payload)
    ip = struct.pack(
        "!BBHHHBBH4s4s",
        0x45,
        0,
        total_len,
        1,
        0,
        64,
        6,
        0,
        src_ip,
        dst_ip,
    )
    tcp = struct.pack(
        "!HHIIHHHH",
        src_port,
        dst_port,
        seq,
        0,
        5 << 12,
        65535,
        0,
        0,
    )
    return eth + ip + tcp + payload


def _write_pcap(path: Path, frames: list[bytes]) -> None:
    with path.open("wb") as f:
        f.write(struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1))
        for index, frame in enumerate(frames, 1):
            f.write(struct.pack("<IIII", index, 0, len(frame), len(frame)))
            f.write(frame)


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_convert_modbus_tcp_pcap(tmp_path: Path) -> None:
    # transaction=1, protocol=0, length=6, unit=1, function=3, data=00000002
    adu = bytes.fromhex("000100000006010300000002")
    pcap = tmp_path / "modbus.pcap"
    _write_pcap(pcap, [_ipv4_tcp_packet(src_port=12000, dst_port=502, seq=100, payload=adu)])

    messages = tmp_path / "messages.jsonl"
    truth = tmp_path / "ground_truth.jsonl"
    summary = convert_pcap("modbus", pcap, messages, truth)

    assert summary["message_count"] == 1
    rows = _read_jsonl(messages)
    assert rows[0]["direction"] == "request"
    assert rows[0]["layout_id"] == "modbus_tcp_adu"
    assert rows[0]["payload_hex"] == adu.hex()
    assert rows[0]["fields"] == [
        {"field_index": 0, "start": 0, "end": 2},
        {"field_index": 1, "start": 2, "end": 4},
        {"field_index": 2, "start": 4, "end": 6},
        {"field_index": 3, "start": 6, "end": 7},
        {"field_index": 4, "start": 7, "end": 8},
        {"field_index": 5, "start": 8, "end": 12},
    ]
    truth_rows = _read_jsonl(truth)
    assert [x["semantic_label"] for x in truth_rows] == [
        "identifier", "constant", "length", "identifier", "type_control", "payload"
    ]


def test_convert_dnp3_pcap(tmp_path: Path) -> None:
    # DNP3 length=6 => 5 link bytes + 1 byte user data.
    # Total raw frame: 10-byte header (incl. CRC) + 1 data byte + 2 data CRC bytes.
    frame = bytes.fromhex("056406c4010002000000aa0000")
    pcap = tmp_path / "dnp3.pcap"
    _write_pcap(pcap, [_ipv4_tcp_packet(src_port=13000, dst_port=20000, seq=200, payload=frame)])

    messages = tmp_path / "messages.jsonl"
    truth = tmp_path / "ground_truth.jsonl"
    summary = convert_pcap("dnp3", pcap, messages, truth)

    assert summary["message_count"] == 1
    rows = _read_jsonl(messages)
    assert rows[0]["direction"] == "request"
    assert rows[0]["layout_id"] == "dnp3_link_frame"
    assert rows[0]["payload_hex"] == frame.hex()
    assert rows[0]["fields"] == [
        {"field_index": 0, "start": 0, "end": 2},
        {"field_index": 1, "start": 2, "end": 3},
        {"field_index": 2, "start": 3, "end": 4},
        {"field_index": 3, "start": 4, "end": 6},
        {"field_index": 4, "start": 6, "end": 8},
        {"field_index": 5, "start": 8, "end": 10},
        {"field_index": 6, "start": 10, "end": 13},
    ]
    truth_rows = _read_jsonl(truth)
    assert [x["semantic_label"] for x in truth_rows] == [
        "constant", "length", "type_control", "identifier", "identifier", "unknown", "payload"
    ]
