"""Tests for JSON record parsing."""

import json
import pytest
from semantic_detector.io.jsonl import parse_json_record
from semantic_detector.contracts import Direction


def test_parse_json_record_minimal() -> None:
    """测试最小合法 JSON"""
    json_str = json.dumps({
        "message_id": "msg_0001",
        "layout_id": "layout_A",
        "direction": "request",
        "payload_hex": "00010203",
        "fields": [
            {"field_index": 0, "start": 0, "end": 2}
        ]
    })
    record = parse_json_record(json_str)
    
    assert record.message_id == "msg_0001"
    assert record.layout_id == "layout_A"
    assert record.direction == Direction.REQUEST
    assert record.payload == b'\x00\x01\x02\x03'
    assert len(record.fields) == 1
    assert record.fields[0].field_index == 0
    assert record.fields[0].start == 0
    assert record.fields[0].end == 2


def test_parse_json_record_with_optional_fields() -> None:
    """测试包含可选字段的 JSON"""
    json_str = json.dumps({
        "message_id": "msg_0002",
        "layout_id": "layout_B",
        "direction": "response",
        "payload_hex": "0A1B2C3D",
        "fields": [
            {"field_index": 0, "start": 0, "end": 2},
            {"field_index": 1, "start": 2, "end": 4}
        ],
        "capture_time": "2026-06-24T00:00:01Z",
        "session_id": "session_01",
        "pair_id": "pair_0001",
        "metadata": {"key": "value"},
        "input_order": 5
    })
    record = parse_json_record(json_str)
    
    assert record.message_id == "msg_0002"
    assert record.layout_id == "layout_B"
    assert record.direction == Direction.RESPONSE
    assert record.payload == b'\x0a\x1b\x2c\x3d'
    assert len(record.fields) == 2
    assert record.capture_time is not None
    assert record.session_id == "session_01"
    assert record.pair_id == "pair_0001"
    assert record.metadata == {"key": "value"}
    assert record.input_order == 5


def test_parse_json_record_invalid_json() -> None:
    """测试非法 JSON"""
    with pytest.raises(ValueError) as exc_info:
        parse_json_record("invalid json")
    assert "Invalid JSON" in str(exc_info.value)


def test_parse_json_record_missing_field() -> None:
    """测试缺少必要字段"""
    json_str = json.dumps({
        "message_id": "msg_0003",
        "layout_id": "layout_C",
        "direction": "request"
    })
    with pytest.raises(ValueError) as exc_info:
        parse_json_record(json_str)
    assert "Missing required field" in str(exc_info.value)


def test_parse_json_record_invalid_direction() -> None:
    """测试非法方向"""
    json_str = json.dumps({
        "message_id": "msg_0004",
        "layout_id": "layout_D",
        "direction": "invalid",
        "payload_hex": "0001",
        "fields": [{"field_index": 0, "start": 0, "end": 2}]
    })
    with pytest.raises(ValueError) as exc_info:
        parse_json_record(json_str)
    assert "Invalid direction" in str(exc_info.value)


def test_parse_json_record_invalid_payload_hex() -> None:
    """测试非法 payload_hex"""
    json_str = json.dumps({
        "message_id": "msg_0005",
        "layout_id": "layout_E",
        "direction": "request",
        "payload_hex": "000G0102",
        "fields": [{"field_index": 0, "start": 0, "end": 2}]
    })
    with pytest.raises(ValueError) as exc_info:
        parse_json_record(json_str)
    assert "Invalid hex character" in str(exc_info.value)


def test_parse_json_record_fields_not_list() -> None:
    """测试 fields 不是列表"""
    json_str = json.dumps({
        "message_id": "msg_0006",
        "layout_id": "layout_F",
        "direction": "request",
        "payload_hex": "0001",
        "fields": "not a list"
    })
    with pytest.raises(ValueError) as exc_info:
        parse_json_record(json_str)
    assert "fields must be a list" in str(exc_info.value)


def test_parse_json_record_field_missing_key() -> None:
    """测试字段缺少必要 key"""
    json_str = json.dumps({
        "message_id": "msg_0007",
        "layout_id": "layout_G",
        "direction": "request",
        "payload_hex": "0001",
        "fields": [{"field_index": 0, "start": 0}]
    })
    with pytest.raises(ValueError) as exc_info:
        parse_json_record(json_str)
    assert "Missing required field key" in str(exc_info.value)


def test_parse_json_record_metadata_not_object() -> None:
    """测试 metadata 不是对象"""
    json_str = json.dumps({
        "message_id": "msg_0008",
        "layout_id": "layout_H",
        "direction": "request",
        "payload_hex": "0001",
        "fields": [{"field_index": 0, "start": 0, "end": 2}],
        "metadata": "not an object"
    })
    with pytest.raises(ValueError) as exc_info:
        parse_json_record(json_str)
    assert "metadata must be an object" in str(exc_info.value)