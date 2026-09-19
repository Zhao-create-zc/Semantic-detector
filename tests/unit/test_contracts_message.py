"""Tests for the MessageRecord contract."""

import pytest
from semantic_detector.contracts import FieldSpan, Direction, MessageRecord


def test_message_record_stores_minimal_fields() -> None:
    """测试 MessageRecord 存储最小字段"""
    span = FieldSpan(field_index=0, start=0, end=2)
    record = MessageRecord(
        message_id="msg_0001",
        layout_id="layout_A",
        direction=Direction.REQUEST,
        payload=b'\x00\x01\x00\x00\x00\x06\x01\x03\x00\x00\x00\x02',
        fields=(span,),
    )
    
    assert record.message_id == "msg_0001"
    assert record.layout_id == "layout_A"
    assert record.direction == Direction.REQUEST
    assert record.payload == b'\x00\x01\x00\x00\x00\x06\x01\x03\x00\x00\x00\x02'
    assert record.fields == (span,)


def test_message_record_with_multiple_fields() -> None:
    """测试 MessageRecord 包含多个字段"""
    span1 = FieldSpan(field_index=0, start=0, end=2)
    span2 = FieldSpan(field_index=1, start=2, end=4)
    span3 = FieldSpan(field_index=2, start=4, end=6)
    
    record = MessageRecord(
        message_id="msg_0002",
        layout_id="layout_B",
        direction=Direction.RESPONSE,
        payload=b'\x00\x01\x00\x02\x00\x03',
        fields=(span1, span2, span3),
    )
    
    assert len(record.fields) == 3
    assert record.fields[0].start == 0
    assert record.fields[1].start == 2
    assert record.fields[2].start == 4


def test_message_record_with_optional_fields() -> None:
    """测试 MessageRecord 包含可选字段"""
    span = FieldSpan(field_index=0, start=0, end=2)
    record = MessageRecord(
        message_id="msg_0003",
        layout_id="layout_C",
        direction=Direction.UNKNOWN,
        payload=b'\x00\x01',
        fields=(span,),
        capture_time="2026-06-24T00:00:01Z",
        session_id="session_01",
        pair_id="pair_0001",
        metadata={"key": "value"},
        input_order=5,
    )
    
    assert record.capture_time == "2026-06-24T00:00:01Z"
    assert record.session_id == "session_01"
    assert record.pair_id == "pair_0001"
    assert record.metadata == {"key": "value"}
    assert record.input_order == 5


def test_message_record_payload_is_bytes() -> None:
    """测试 payload 保存为 bytes"""
    span = FieldSpan(field_index=0, start=0, end=2)
    record = MessageRecord(
        message_id="msg_0004",
        layout_id="layout_D",
        direction=Direction.REQUEST,
        payload=b'\x00\x01\x00\x00\x00\x06\x01\x03\x00\x00\x00\x02',
        fields=(span,),
    )
    
    assert isinstance(record.payload, bytes)


def test_message_record_rejects_empty_message_id() -> None:
    """测试拒绝空 message_id"""
    span = FieldSpan(field_index=0, start=0, end=2)
    with pytest.raises(ValueError) as exc_info:
        MessageRecord(
            message_id="",
            layout_id="layout_A",
            direction=Direction.REQUEST,
            payload=b'\x00\x01',
            fields=(span,),
        )
    assert "message_id must not be empty" in str(exc_info.value)


def test_message_record_rejects_empty_layout_id() -> None:
    """测试拒绝空 layout_id"""
    span = FieldSpan(field_index=0, start=0, end=2)
    with pytest.raises(ValueError) as exc_info:
        MessageRecord(
            message_id="msg_0001",
            layout_id="",
            direction=Direction.REQUEST,
            payload=b'\x00\x01',
            fields=(span,),
        )
    assert "layout_id must not be empty" in str(exc_info.value)


def test_message_record_rejects_invalid_direction() -> None:
    """测试拒绝非法 direction"""
    span = FieldSpan(field_index=0, start=0, end=2)
    with pytest.raises(ValueError) as exc_info:
        MessageRecord(
            message_id="msg_0001",
            layout_id="layout_A",
            direction="invalid",
            payload=b'\x00\x01',
            fields=(span,),
        )
    assert "direction must be a Direction enum" in str(exc_info.value)


def test_message_record_rejects_field_end_exceeds_payload() -> None:
    """测试拒绝字段 end 超过 payload 长度"""
    span = FieldSpan(field_index=0, start=0, end=5)  # end=5 但 payload 只有 2 字节
    with pytest.raises(ValueError) as exc_info:
        MessageRecord(
            message_id="msg_0001",
            layout_id="layout_A",
            direction=Direction.REQUEST,
            payload=b'\x00\x01',
            fields=(span,),
        )
    assert "exceeds payload length" in str(exc_info.value)
    assert "Field 0 end (5)" in str(exc_info.value)


def test_message_record_rejects_overlapping_fields() -> None:
    """测试拒绝重叠字段"""
    span1 = FieldSpan(field_index=0, start=0, end=3)  # 0-3
    span2 = FieldSpan(field_index=1, start=2, end=5)  # 2-5，与 span1 重叠
    with pytest.raises(ValueError) as exc_info:
        MessageRecord(
            message_id="msg_0001",
            layout_id="layout_A",
            direction=Direction.REQUEST,
            payload=b'\x00\x01\x02\x03\x04',
            fields=(span1, span2),
        )
    assert "Fields overlap" in str(exc_info.value)
    assert "field 0 end (3)" in str(exc_info.value)
    assert "field 1 start (2)" in str(exc_info.value)


def test_message_record_rejects_non_contiguous_field_index() -> None:
    """测试拒绝非连续 field_index"""
    span0 = FieldSpan(field_index=0, start=0, end=2)
    span2 = FieldSpan(field_index=2, start=2, end=4)  # 缺少 index=1
    with pytest.raises(ValueError) as exc_info:
        MessageRecord(
            message_id="msg_0001",
            layout_id="layout_A",
            direction=Direction.REQUEST,
            payload=b'\x00\x01\x02\x03',
            fields=(span0, span2),
        )
    assert "field_index must be contiguous from 0" in str(exc_info.value)
    assert "[0, 2]" in str(exc_info.value)


# ---------------------------------------------------------------------------
# R375：MessageRecord 标识字段严格类型校验失败测试（V3 审计 HIGH-1）
#
# 当前 MessageRecord.__post_init__ 只检查 not message_id / not layout_id，
# 不检查类型。整数 message_id=123 / layout_id=456 / session_id=789 /
# input_order="1" / metadata=[] 会被静默接受。
#
# 这些测试在 R376 修复前应当失败，R376 修复后应当通过。
# 本轮不修改生产代码。
# ---------------------------------------------------------------------------

_VALID_SPAN = FieldSpan(field_index=0, start=0, end=2)
_VALID_PAYLOAD = b'\x00\x01'


class TestMessageRecordStrictTypeR375:
    """R375：MessageRecord 标识字段严格类型校验失败测试。

    复现 V3 审计 HIGH-1：message_id/layout_id 为整数、session_id/pair_id 为
    整数、input_order 为字符串、metadata 为列表时被静默接受。
    """

    def test_r375_rejects_integer_message_id(self) -> None:
        """message_id=123（int）必须在构造阶段拒绝，不得静默字符串化。"""
        with pytest.raises(ValueError) as exc_info:
            MessageRecord(
                message_id=123,
                layout_id="L",
                direction=Direction.REQUEST,
                payload=_VALID_PAYLOAD,
                fields=(_VALID_SPAN,),
            )
        assert "message_id" in str(exc_info.value)

    def test_r375_rejects_integer_layout_id(self) -> None:
        """layout_id=456（int）必须在构造阶段拒绝。"""
        with pytest.raises(ValueError) as exc_info:
            MessageRecord(
                message_id="m1",
                layout_id=456,
                direction=Direction.REQUEST,
                payload=_VALID_PAYLOAD,
                fields=(_VALID_SPAN,),
            )
        assert "layout_id" in str(exc_info.value)

    def test_r375_rejects_integer_session_id(self) -> None:
        """session_id=789（int）必须在构造阶段拒绝（必须是 str 或 None）。"""
        with pytest.raises(ValueError) as exc_info:
            MessageRecord(
                message_id="m1",
                layout_id="L",
                direction=Direction.REQUEST,
                payload=_VALID_PAYLOAD,
                fields=(_VALID_SPAN,),
                session_id=789,
            )
        assert "session_id" in str(exc_info.value)

    def test_r375_rejects_integer_pair_id(self) -> None:
        """pair_id=999（int）必须在构造阶段拒绝（必须是 str 或 None）。"""
        with pytest.raises(ValueError) as exc_info:
            MessageRecord(
                message_id="m1",
                layout_id="L",
                direction=Direction.REQUEST,
                payload=_VALID_PAYLOAD,
                fields=(_VALID_SPAN,),
                pair_id=999,
            )
        assert "pair_id" in str(exc_info.value)

    def test_r375_rejects_string_input_order(self) -> None:
        """input_order="1"（str）必须在构造阶段拒绝（必须是 int）。"""
        with pytest.raises(ValueError) as exc_info:
            MessageRecord(
                message_id="m1",
                layout_id="L",
                direction=Direction.REQUEST,
                payload=_VALID_PAYLOAD,
                fields=(_VALID_SPAN,),
                input_order="1",
            )
        assert "input_order" in str(exc_info.value)

    def test_r375_rejects_bool_input_order(self) -> None:
        """input_order=True（bool）必须在构造阶段拒绝（bool 不算 int）。"""
        with pytest.raises(ValueError) as exc_info:
            MessageRecord(
                message_id="m1",
                layout_id="L",
                direction=Direction.REQUEST,
                payload=_VALID_PAYLOAD,
                fields=(_VALID_SPAN,),
                input_order=True,
            )
        assert "input_order" in str(exc_info.value)

    def test_r375_rejects_list_metadata(self) -> None:
        """metadata=[]（list）必须在构造阶段拒绝（必须是 dict 或 None）。"""
        with pytest.raises(ValueError) as exc_info:
            MessageRecord(
                message_id="m1",
                layout_id="L",
                direction=Direction.REQUEST,
                payload=_VALID_PAYLOAD,
                fields=(_VALID_SPAN,),
                metadata=[],
            )
        assert "metadata" in str(exc_info.value)

    def test_r375_rejects_whitespace_only_message_id(self) -> None:
        """message_id='   '（纯空白）必须在构造阶段拒绝（strip 后非空）。"""
        with pytest.raises(ValueError) as exc_info:
            MessageRecord(
                message_id="   ",
                layout_id="L",
                direction=Direction.REQUEST,
                payload=_VALID_PAYLOAD,
                fields=(_VALID_SPAN,),
            )
        assert "message_id" in str(exc_info.value)

    def test_r375_rejects_whitespace_only_layout_id(self) -> None:
        """layout_id='   '（纯空白）必须在构造阶段拒绝（strip 后非空）。"""
        with pytest.raises(ValueError) as exc_info:
            MessageRecord(
                message_id="m1",
                layout_id="   ",
                direction=Direction.REQUEST,
                payload=_VALID_PAYLOAD,
                fields=(_VALID_SPAN,),
            )
        assert "layout_id" in str(exc_info.value)

    def test_r375_accepts_none_session_id(self) -> None:
        """合法边界：session_id=None 必须被接受。"""
        record = MessageRecord(
            message_id="m1",
            layout_id="L",
            direction=Direction.REQUEST,
            payload=_VALID_PAYLOAD,
            fields=(_VALID_SPAN,),
            session_id=None,
        )
        assert record.session_id is None

    def test_r375_accepts_none_metadata(self) -> None:
        """合法边界：metadata=None 必须被接受。"""
        record = MessageRecord(
            message_id="m1",
            layout_id="L",
            direction=Direction.REQUEST,
            payload=_VALID_PAYLOAD,
            fields=(_VALID_SPAN,),
            metadata=None,
        )
        assert record.metadata is None

    def test_r375_accepts_dict_metadata(self) -> None:
        """合法边界：metadata={'k':'v'} 必须被接受。"""
        record = MessageRecord(
            message_id="m1",
            layout_id="L",
            direction=Direction.REQUEST,
            payload=_VALID_PAYLOAD,
            fields=(_VALID_SPAN,),
            metadata={"k": "v"},
        )
        assert record.metadata == {"k": "v"}
