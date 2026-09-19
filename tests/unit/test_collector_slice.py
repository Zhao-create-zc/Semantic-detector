"""R043+R044: 单条消息精确字段切片测试"""

from semantic_detector.contracts import Direction, FieldSpan, MessageRecord
from semantic_detector.profiling.collector import slice_message_fields


def test_basic_slicing():
    record = MessageRecord(
        message_id="m1",
        layout_id="L1",
        direction=Direction.REQUEST,
        payload=bytes.fromhex("aabbccddeeff"),
        fields=(
            FieldSpan(field_index=0, start=0, end=2),
            FieldSpan(field_index=1, start=2, end=4),
            FieldSpan(field_index=2, start=4, end=6),
        ),
    )
    result = slice_message_fields(record)
    assert len(result) == 3
    assert result[0] == (0, b"\xaa\xbb")
    assert result[1] == (1, b"\xcc\xdd")
    assert result[2] == (2, b"\xee\xff")


def test_single_field():
    record = MessageRecord(
        message_id="m1",
        layout_id="L1",
        direction=Direction.REQUEST,
        payload=bytes.fromhex("deadbeef"),
        fields=(FieldSpan(field_index=0, start=0, end=4),),
    )
    result = slice_message_fields(record)
    assert result == [(0, b"\xde\xad\xbe\xef")]


def test_non_contiguous_fields():
    record = MessageRecord(
        message_id="m1",
        layout_id="L1",
        direction=Direction.REQUEST,
        payload=bytes.fromhex("aabbccddeeff0011"),
        fields=(
            FieldSpan(field_index=0, start=0, end=2),
            FieldSpan(field_index=1, start=4, end=6),
        ),
    )
    result = slice_message_fields(record)
    assert result == [(0, b"\xaa\xbb"), (1, b"\xee\xff")]


def test_empty_payload_no_fields():
    record = MessageRecord(
        message_id="m1",
        layout_id="L1",
        direction=Direction.REQUEST,
        payload=b"",
        fields=(),
    )
    result = slice_message_fields(record)
    assert result == []


def test_field_index_preserved():
    record = MessageRecord(
        message_id="m1",
        layout_id="L1",
        direction=Direction.REQUEST,
        payload=bytes.fromhex("aabbccdd"),
        fields=(
            FieldSpan(field_index=0, start=0, end=2),
            FieldSpan(field_index=1, start=2, end=4),
        ),
    )
    result = slice_message_fields(record)
    indices = [idx for idx, _ in result]
    assert indices == [0, 1]


def test_varied_width_fields():
    record = MessageRecord(
        message_id="m1",
        layout_id="L1",
        direction=Direction.REQUEST,
        payload=bytes.fromhex("aabbccddeeff"),
        fields=(
            FieldSpan(field_index=0, start=0, end=1),
            FieldSpan(field_index=1, start=1, end=4),
            FieldSpan(field_index=2, start=4, end=6),
        ),
    )
    result = slice_message_fields(record)
    assert result[0] == (0, b"\xaa")
    assert result[1] == (1, b"\xbb\xcc\xdd")
    assert result[2] == (2, b"\xee\xff")


def test_two_messages_different_lengths_tail_preserved():
    """变长消息：长消息尾字段完整保留，不被截断为最短长度"""
    short_record = MessageRecord(
        message_id="m-short",
        layout_id="L1",
        direction=Direction.REQUEST,
        payload=bytes.fromhex("aabbccdd"),
        fields=(
            FieldSpan(field_index=0, start=0, end=2),
            FieldSpan(field_index=1, start=2, end=4),
        ),
    )
    long_record = MessageRecord(
        message_id="m-long",
        layout_id="L1",
        direction=Direction.REQUEST,
        payload=bytes.fromhex("aabbccddeeff00112233"),
        fields=(
            FieldSpan(field_index=0, start=0, end=2),
            FieldSpan(field_index=1, start=2, end=10),
        ),
    )

    short_result = slice_message_fields(short_record)
    long_result = slice_message_fields(long_record)

    # 短消息的 field 1 只有 2 字节
    assert short_result[1] == (1, b"\xcc\xdd")

    # 长消息的 field 1 有 8 字节，完整保留
    assert long_result[1] == (1, b"\xcc\xdd\xee\xff\x00\x11\x22\x33")

    # 长消息 field 1 不被截断为短消息的宽度
    assert len(long_result[1][1]) > len(short_result[1][1])
