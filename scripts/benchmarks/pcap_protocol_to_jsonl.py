"""Convert public Modbus/TCP or DNP3 PCAPs into Semantic Detector JSONL inputs.

The converter intentionally uses only the Python standard library so that public
benchmark preparation does not add runtime dependencies to Semantic Detector.
It supports classic PCAP files containing Ethernet / IPv4 / TCP traffic.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import math
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator


@dataclass(frozen=True)
class TcpSegment:
    timestamp: float
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    seq: int
    payload: bytes

    @property
    def flow_key(self) -> tuple[str, str, int, int]:
        return (self.src_ip, self.dst_ip, self.src_port, self.dst_port)


@dataclass(frozen=True)
class ReassembledChunk:
    flow_key: tuple[str, str, int, int]
    timestamp: float
    payload: bytes


_PCAP_MAGIC = {
    b"\xd4\xc3\xb2\xa1": ("<", 1_000_000),
    b"\xa1\xb2\xc3\xd4": (">", 1_000_000),
    b"\x4d\x3c\xb2\xa1": ("<", 1_000_000_000),
    b"\xa1\xb2\x3c\x4d": (">", 1_000_000_000),
}


def _iter_pcap_frames(path: Path) -> Iterator[tuple[float, int, bytes]]:
    with path.open("rb") as f:
        global_header = f.read(24)
        if len(global_header) != 24:
            raise ValueError("PCAP global header is incomplete")
        magic = global_header[:4]
        try:
            endian, ts_scale = _PCAP_MAGIC[magic]
        except KeyError as exc:
            raise ValueError("unsupported capture format: expected classic PCAP") from exc
        _major, _minor, _zone, _sigfigs, _snaplen, linktype = struct.unpack(
            endian + "HHIIII", global_header[4:]
        )
        while True:
            packet_header = f.read(16)
            if not packet_header:
                return
            if len(packet_header) != 16:
                raise ValueError("PCAP packet header is incomplete")
            ts_sec, ts_frac, incl_len, _orig_len = struct.unpack(endian + "IIII", packet_header)
            frame = f.read(incl_len)
            if len(frame) != incl_len:
                raise ValueError("PCAP packet data is truncated")
            yield ts_sec + ts_frac / ts_scale, linktype, frame


def _parse_ethernet_ipv4_tcp(timestamp: float, linktype: int, frame: bytes) -> TcpSegment | None:
    if linktype != 1 or len(frame) < 14:  # DLT_EN10MB
        return None
    offset = 14
    ether_type = int.from_bytes(frame[12:14], "big")
    while ether_type in {0x8100, 0x88A8}:
        if len(frame) < offset + 4:
            return None
        ether_type = int.from_bytes(frame[offset + 2 : offset + 4], "big")
        offset += 4
    if ether_type != 0x0800 or len(frame) < offset + 20:
        return None

    ip = frame[offset:]
    version = ip[0] >> 4
    ihl = (ip[0] & 0x0F) * 4
    if version != 4 or ihl < 20 or len(ip) < ihl:
        return None
    total_length = int.from_bytes(ip[2:4], "big")
    if total_length < ihl or len(ip) < min(total_length, len(ip)):
        return None
    flags_fragment = int.from_bytes(ip[6:8], "big")
    fragment_offset = flags_fragment & 0x1FFF
    more_fragments = bool(flags_fragment & 0x2000)
    if fragment_offset or more_fragments:
        return None
    if ip[9] != 6:
        return None

    src_ip = str(ipaddress.IPv4Address(ip[12:16]))
    dst_ip = str(ipaddress.IPv4Address(ip[16:20]))
    tcp = ip[ihl:total_length]
    if len(tcp) < 20:
        return None
    src_port, dst_port = struct.unpack("!HH", tcp[:4])
    seq = int.from_bytes(tcp[4:8], "big")
    data_offset = (tcp[12] >> 4) * 4
    if data_offset < 20 or len(tcp) < data_offset:
        return None
    payload = tcp[data_offset:]
    if not payload:
        return None
    return TcpSegment(timestamp, src_ip, dst_ip, src_port, dst_port, seq, payload)


def read_tcp_segments(path: Path) -> list[TcpSegment]:
    segments: list[TcpSegment] = []
    for timestamp, linktype, frame in _iter_pcap_frames(path):
        segment = _parse_ethernet_ipv4_tcp(timestamp, linktype, frame)
        if segment is not None:
            segments.append(segment)
    return segments


def reassemble_tcp_streams(segments: Iterable[TcpSegment]) -> list[ReassembledChunk]:
    grouped: dict[tuple[str, str, int, int], list[TcpSegment]] = {}
    for segment in segments:
        grouped.setdefault(segment.flow_key, []).append(segment)

    chunks: list[ReassembledChunk] = []
    for flow_key, flow_segments in grouped.items():
        ordered = sorted(flow_segments, key=lambda seg: (seg.seq, seg.timestamp))
        current = bytearray()
        current_timestamp = ordered[0].timestamp
        next_seq: int | None = None
        for segment in ordered:
            if next_seq is None:
                current.extend(segment.payload)
                next_seq = segment.seq + len(segment.payload)
                current_timestamp = segment.timestamp
                continue
            if segment.seq > next_seq:
                if current:
                    chunks.append(ReassembledChunk(flow_key, current_timestamp, bytes(current)))
                current = bytearray(segment.payload)
                next_seq = segment.seq + len(segment.payload)
                current_timestamp = segment.timestamp
                continue
            overlap = next_seq - segment.seq
            if overlap < len(segment.payload):
                current.extend(segment.payload[overlap:])
                next_seq += len(segment.payload) - overlap
        if current:
            chunks.append(ReassembledChunk(flow_key, current_timestamp, bytes(current)))
    return chunks


def _modbus_direction(flow_key: tuple[str, str, int, int]) -> str | None:
    _src_ip, _dst_ip, src_port, dst_port = flow_key
    if dst_port == 502:
        return "request"
    if src_port == 502:
        return "response"
    return None


def _dnp3_direction(flow_key: tuple[str, str, int, int]) -> str | None:
    _src_ip, _dst_ip, src_port, dst_port = flow_key
    if dst_port == 20000:
        return "request"
    if src_port == 20000:
        return "response"
    return None


def _split_modbus(stream: bytes) -> Iterator[bytes]:
    cursor = 0
    while cursor + 8 <= len(stream):
        protocol_id = int.from_bytes(stream[cursor + 2 : cursor + 4], "big")
        length = int.from_bytes(stream[cursor + 4 : cursor + 6], "big")
        total = 6 + length
        if protocol_id != 0 or length < 2 or total > 260:
            cursor += 1
            continue
        if cursor + total > len(stream):
            break
        frame = stream[cursor : cursor + total]
        if len(frame) > 8:  # keep a stable sixth data field
            yield frame
        cursor += total


def _split_dnp3(stream: bytes) -> Iterator[bytes]:
    cursor = 0
    while cursor + 10 <= len(stream):
        start = stream.find(b"\x05\x64", cursor)
        if start < 0 or start + 10 > len(stream):
            return
        length = stream[start + 2]
        if length < 5:
            cursor = start + 1
            continue
        user_data_length = length - 5
        crc_blocks = math.ceil(user_data_length / 16) if user_data_length else 0
        total = 10 + user_data_length + 2 * crc_blocks
        if start + total > len(stream):
            return
        frame = stream[start : start + total]
        if total > 10:  # keep a stable seventh user-data field
            yield frame
        cursor = start + total


def _field(index: int, start: int, end: int) -> dict[str, int]:
    return {"field_index": index, "start": start, "end": end}


def _modbus_fields(frame: bytes) -> list[dict[str, int]]:
    return [
        _field(0, 0, 2),
        _field(1, 2, 4),
        _field(2, 4, 6),
        _field(3, 6, 7),
        _field(4, 7, 8),
        _field(5, 8, len(frame)),
    ]


def _dnp3_fields(frame: bytes) -> list[dict[str, int]]:
    return [
        _field(0, 0, 2),
        _field(1, 2, 3),
        _field(2, 3, 4),
        _field(3, 4, 6),
        _field(4, 6, 8),
        _field(5, 8, 10),
        _field(6, 10, len(frame)),
    ]


_TRUTH = {
    "modbus": [
        ("identifier", False),
        ("constant", True),
        ("length", True),
        ("identifier", True),
        ("type_control", True),
        ("payload", True),
    ],
    "dnp3": [
        ("constant", True),
        ("length", True),
        ("type_control", True),
        ("identifier", True),
        ("identifier", True),
        ("unknown", False),  # CRC is intentionally outside the current taxonomy.
        ("payload", True),
    ],
}


def _write_ground_truth(protocol: str, directions: list[str], output: Path) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)
    layout_id = "modbus_tcp_adu" if protocol == "modbus" else "dnp3_link_frame"
    truth_id = 1
    with output.open("w", encoding="utf-8", newline="\n") as f:
        for direction in sorted(set(directions)):
            for field_index, (semantic_label, hard) in enumerate(_TRUTH[protocol]):
                row = {
                    "truth_id": truth_id,
                    "layout_id": layout_id,
                    "direction": direction,
                    "field_index": field_index,
                    "semantic_label": semantic_label,
                    "confidence": 1.0 if semantic_label != "unknown" else 0.0,
                    "is_hard_evidence": hard,
                }
                f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
                truth_id += 1
    return truth_id - 1


def convert_pcap(protocol: str, input_path: Path, messages_path: Path, ground_truth_path: Path) -> dict[str, int]:
    protocol = protocol.lower()
    if protocol not in {"modbus", "dnp3"}:
        raise ValueError("protocol must be 'modbus' or 'dnp3'")

    segments = read_tcp_segments(Path(input_path))
    chunks = reassemble_tcp_streams(segments)
    messages_path.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, object]] = []
    directions: list[str] = []
    for chunk in chunks:
        if protocol == "modbus":
            direction = _modbus_direction(chunk.flow_key)
            frames = _split_modbus(chunk.payload)
            layout_id = "modbus_tcp_adu"
            field_builder = _modbus_fields
        else:
            direction = _dnp3_direction(chunk.flow_key)
            frames = _split_dnp3(chunk.payload)
            layout_id = "dnp3_link_frame"
            field_builder = _dnp3_fields
        if direction is None:
            continue
        for frame in frames:
            rows.append(
                {
                    "message_id": f"{protocol}-{len(rows) + 1:06d}",
                    "layout_id": layout_id,
                    "direction": direction,
                    "payload_hex": frame.hex(),
                    "fields": field_builder(frame),
                }
            )
            directions.append(direction)

    with messages_path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    truth_count = _write_ground_truth(protocol, directions, Path(ground_truth_path)) if rows else 0
    return {
        "message_count": len(rows),
        "ground_truth_count": truth_count,
        "tcp_segment_count": len(segments),
        "stream_chunk_count": len(chunks),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", required=True, choices=["modbus", "dnp3"])
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--messages", required=True, type=Path)
    parser.add_argument("--ground-truth", required=True, type=Path)
    args = parser.parse_args()
    summary = convert_pcap(args.protocol, args.input, args.messages, args.ground_truth)
    print(json.dumps(summary, indent=2, sort_keys=True))
    if summary["message_count"] == 0:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
