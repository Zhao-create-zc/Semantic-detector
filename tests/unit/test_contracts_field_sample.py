"""Tests for the FieldSample contract."""

from semantic_detector.contracts import FieldKey, FieldSample, Direction


def test_field_sample_stores_minimal_fields() -> None:
    """测试 FieldSample 存储最小字段"""
    key = FieldKey(
        layout_id="layout_A",
        direction=Direction.REQUEST,
        field_index=0,
    )
    sample = FieldSample(
        message_id="msg_0001",
        field_key=key,
        field_bytes=b'\x00\x01',
        start=0,
        end=2,
        message_length=12,
        remaining_bytes=10,
    )
    
    assert sample.message_id == "msg_0001"
    assert sample.field_key == key
    assert sample.field_bytes == b'\x00\x01'
    assert sample.start == 0
    assert sample.end == 2
    assert sample.message_length == 12
    assert sample.remaining_bytes == 10


def test_field_sample_with_optional_fields() -> None:
    """测试 FieldSample 包含可选字段"""
    key = FieldKey(
        layout_id="layout_A",
        direction=Direction.REQUEST,
        field_index=0,
    )
    sample = FieldSample(
        message_id="msg_0001",
        field_key=key,
        field_bytes=b'\x00\x01',
        start=0,
        end=2,
        message_length=12,
        remaining_bytes=10,
        capture_time="2026-06-24T00:00:01Z",
        session_id="session_01",
        pair_id="pair_0001",
        input_order=5,
    )
    
    assert sample.capture_time == "2026-06-24T00:00:01Z"
    assert sample.session_id == "session_01"
    assert sample.pair_id == "pair_0001"
    assert sample.input_order == 5


def test_field_sample_remaining_bytes_calculation() -> None:
    """测试 remaining_bytes 计算"""
    key = FieldKey(
        layout_id="layout_A",
        direction=Direction.REQUEST,
        field_index=0,
    )
    sample = FieldSample(
        message_id="msg_0001",
        field_key=key,
        field_bytes=b'\x00\x01',
        start=0,
        end=2,
        message_length=12,
        remaining_bytes=10,  # 12 - 2 = 10
    )
    
    assert sample.remaining_bytes == sample.message_length - sample.end