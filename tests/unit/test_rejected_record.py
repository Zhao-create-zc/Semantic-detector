"""R382：统一 RejectedRecord 数据模型测试

验证 contracts.py 新增的 RejectedRecord dataclass：
- 所有字段可 JSON 序列化
- 不保存 Python 对象实例（MessageRecord/Direction/FieldSpan）
- 严格类型校验（line_number 用 type is int 拒绝 bool）
- to_dict() 返回可序列化 dict
- reason_code 常量正确性
"""

import json
from dataclasses import FrozenInstanceError

import pytest

from semantic_detector.contracts import (
    Direction,
    FieldSpan,
    MessageRecord,
    RejectedRecord,
    REASON_CODE_DUPLICATE_MESSAGE_ID,
    REASON_CODE_INVALID_JSON,
    REASON_CODE_MISSING_REQUIRED_FIELD,
    REASON_CODE_VALUE_ERROR,
    REASON_CODE_TYPE_ERROR,
)


def _make_valid_rejected_record(**overrides) -> RejectedRecord:
    """构造一个合法的 RejectedRecord（参数可覆盖）"""
    defaults = {
        "line_number": 5,
        "stage": "duplicate",
        "reason_code": REASON_CODE_DUPLICATE_MESSAGE_ID,
        "message": "Duplicate message_id: m1",
        "message_id": "m1",
        "layout_id": "L",
        "direction": "request",
        "record_summary": {"field_count": 1, "payload_length": 2},
        "raw_line": '{"message_id": "m1", ...}',
    }
    defaults.update(overrides)
    return RejectedRecord(**defaults)


class TestRejectedRecordR382Construction:
    """R382：RejectedRecord 基本构造测试"""

    def test_r382_valid_construction_all_fields(self) -> None:
        """R382: 所有字段构造成功"""
        rec = _make_valid_rejected_record()
        assert rec.line_number == 5
        assert rec.stage == "duplicate"
        assert rec.reason_code == REASON_CODE_DUPLICATE_MESSAGE_ID
        assert rec.message == "Duplicate message_id: m1"
        assert rec.message_id == "m1"
        assert rec.layout_id == "L"
        assert rec.direction == "request"
        assert rec.record_summary == {"field_count": 1, "payload_length": 2}
        assert rec.raw_line == '{"message_id": "m1", ...}'

    def test_r382_valid_construction_minimal_fields(self) -> None:
        """R382: 仅必填字段构造成功，可选字段默认为 None"""
        rec = RejectedRecord(
            line_number=1,
            stage="parse",
            reason_code=REASON_CODE_INVALID_JSON,
            message="Invalid JSON",
        )
        assert rec.line_number == 1
        assert rec.stage == "parse"
        assert rec.reason_code == REASON_CODE_INVALID_JSON
        assert rec.message == "Invalid JSON"
        assert rec.message_id is None
        assert rec.layout_id is None
        assert rec.direction is None
        assert rec.record_summary is None
        assert rec.raw_line is None

    def test_r382_line_number_none_allowed(self) -> None:
        """R382: line_number=None 允许（非文件来源的拒绝）"""
        rec = RejectedRecord(
            line_number=None,
            stage="contract",
            reason_code=REASON_CODE_VALUE_ERROR,
            message="contract violation",
        )
        assert rec.line_number is None

    def test_r382_frozen_dataclass(self) -> None:
        """R382: RejectedRecord 是 frozen dataclass，不可变"""
        rec = _make_valid_rejected_record()
        with pytest.raises(FrozenInstanceError):
            rec.reason_code = "other"  # type: ignore[misc]


class TestRejectedRecordR382TypeValidation:
    """R382：RejectedRecord 严格类型校验"""

    def test_r382_line_number_bool_rejected(self) -> None:
        """R382: line_number 不接受 bool（bool 是 int 子类，但 type is int 拒绝）"""
        with pytest.raises(ValueError, match="line_number must be int or None"):
            RejectedRecord(
                line_number=True,  # bool 不是 int
                stage="parse",
                reason_code=REASON_CODE_INVALID_JSON,
                message="x",
            )

    def test_r382_line_number_float_rejected(self) -> None:
        """R382: line_number 不接受 float"""
        with pytest.raises(ValueError, match="line_number must be int or None"):
            RejectedRecord(
                line_number=1.0,
                stage="parse",
                reason_code=REASON_CODE_INVALID_JSON,
                message="x",
            )

    def test_r382_line_number_str_rejected(self) -> None:
        """R382: line_number 不接受 str"""
        with pytest.raises(ValueError, match="line_number must be int or None"):
            RejectedRecord(
                line_number="5",
                stage="parse",
                reason_code=REASON_CODE_INVALID_JSON,
                message="x",
            )

    def test_r382_stage_empty_rejected(self) -> None:
        """R382: stage 不接受空字符串"""
        with pytest.raises(ValueError, match="stage must be a non-empty string"):
            RejectedRecord(
                line_number=1, stage="", reason_code="x", message="y"
            )

    def test_r382_stage_whitespace_rejected(self) -> None:
        """R382: stage 不接受纯空白字符串"""
        with pytest.raises(ValueError, match="stage must be a non-empty string"):
            RejectedRecord(
                line_number=1, stage="   ", reason_code="x", message="y"
            )

    def test_r382_stage_non_string_rejected(self) -> None:
        """R382: stage 不接受非字符串"""
        with pytest.raises(ValueError, match="stage must be a non-empty string"):
            RejectedRecord(
                line_number=1, stage=123, reason_code="x", message="y"  # type: ignore[arg-type]
            )

    def test_r382_reason_code_empty_rejected(self) -> None:
        """R382: reason_code 不接受空字符串"""
        with pytest.raises(ValueError, match="reason_code must be a non-empty string"):
            RejectedRecord(
                line_number=1, stage="parse", reason_code="", message="y"
            )

    def test_r382_reason_code_whitespace_rejected(self) -> None:
        """R382: reason_code 不接受纯空白字符串"""
        with pytest.raises(ValueError, match="reason_code must be a non-empty string"):
            RejectedRecord(
                line_number=1, stage="parse", reason_code="  ", message="y"
            )

    def test_r382_message_non_string_rejected(self) -> None:
        """R382: message 不接受非字符串（但允许空字符串）"""
        with pytest.raises(ValueError, match="message must be str"):
            RejectedRecord(
                line_number=1, stage="parse", reason_code="x", message=123  # type: ignore[arg-type]
            )

    def test_r382_message_empty_allowed(self) -> None:
        """R382: message 允许空字符串（reason_code 已足够说明时）"""
        rec = RejectedRecord(
            line_number=1, stage="parse", reason_code="x", message=""
        )
        assert rec.message == ""

    def test_r382_message_id_int_rejected(self) -> None:
        """R382: message_id 不接受整数（必须 str 或 None）"""
        with pytest.raises(ValueError, match="message_id must be str or None"):
            RejectedRecord(
                line_number=1,
                stage="parse",
                reason_code="x",
                message="y",
                message_id=123,  # type: ignore[arg-type]
            )

    def test_r382_layout_id_int_rejected(self) -> None:
        """R382: layout_id 不接受整数"""
        with pytest.raises(ValueError, match="layout_id must be str or None"):
            RejectedRecord(
                line_number=1,
                stage="parse",
                reason_code="x",
                message="y",
                layout_id=1,  # type: ignore[arg-type]
            )

    def test_r382_direction_int_rejected(self) -> None:
        """R382: direction 不接受整数（必须 str 或 None，不接受 Direction 枚举）"""
        with pytest.raises(ValueError, match="direction must be str or None"):
            RejectedRecord(
                line_number=1,
                stage="parse",
                reason_code="x",
                message="y",
                direction=1,  # type: ignore[arg-type]
            )

    def test_r382_direction_enum_accepted_as_str_subclass(self) -> None:
        """R382: direction 接受 Direction 枚举（str 子类，可 JSON 序列化）

        Direction 继承 str（class Direction(str, Enum)），所以 isinstance
        校验通过。json.dumps(Direction.REQUEST) 输出 "request"（str 子类的
        枚举值会被序列化为字符串值），满足"可 JSON 序列化"要求。
        """
        rec = RejectedRecord(
            line_number=1,
            stage="duplicate",
            reason_code=REASON_CODE_DUPLICATE_MESSAGE_ID,
            message="x",
            direction=Direction.REQUEST,
        )
        # to_dict() 可 JSON 序列化
        d = rec.to_dict()
        s = json.dumps(d, ensure_ascii=False)
        parsed = json.loads(s)
        assert parsed["direction"] == "request"

    def test_r382_record_summary_list_rejected(self) -> None:
        """R382: record_summary 不接受 list（必须是 dict 或 None）"""
        with pytest.raises(ValueError, match="record_summary must be dict or None"):
            RejectedRecord(
                line_number=1,
                stage="parse",
                reason_code="x",
                message="y",
                record_summary=["a", "b"],  # type: ignore[arg-type]
            )

    def test_r382_record_summary_str_rejected(self) -> None:
        """R382: record_summary 不接受 str"""
        with pytest.raises(ValueError, match="record_summary must be dict or None"):
            RejectedRecord(
                line_number=1,
                stage="parse",
                reason_code="x",
                message="y",
                record_summary="summary",  # type: ignore[arg-type]
            )

    def test_r382_raw_line_int_rejected(self) -> None:
        """R382: raw_line 不接受整数"""
        with pytest.raises(ValueError, match="raw_line must be str or None"):
            RejectedRecord(
                line_number=1,
                stage="parse",
                reason_code="x",
                message="y",
                raw_line=123,  # type: ignore[arg-type]
            )


class TestRejectedRecordR382NoPyObject:
    """R382：RejectedRecord 禁止保存 Python 对象实例

    HIGH-2 根因：rejected 结构含 MessageRecord 对象导致 json.dumps 崩溃。
    RejectedRecord 通过类型校验拒绝任何 Python 对象实例。
    """

    def test_r382_no_message_record_in_fields(self) -> None:
        """R382: RejectedRecord 字段不包含 MessageRecord 对象

        RejectedRecord 没有 'record' 字段（旧 rejected_records 字典的 'record' 键），
        只有 message_id/layout_id/direction 字符串和 record_summary dict。
        """
        rec = _make_valid_rejected_record()
        # 不存在 'record' 字段
        assert not hasattr(rec, "record")
        # 字段值都是基本类型
        assert isinstance(rec.line_number, int) or rec.line_number is None
        assert isinstance(rec.stage, str)
        assert isinstance(rec.reason_code, str)
        assert isinstance(rec.message, str)
        assert isinstance(rec.message_id, str) or rec.message_id is None
        assert isinstance(rec.layout_id, str) or rec.layout_id is None
        assert isinstance(rec.direction, str) or rec.direction is None
        assert isinstance(rec.record_summary, dict) or rec.record_summary is None
        assert isinstance(rec.raw_line, str) or rec.raw_line is None

    def test_r382_record_summary_must_not_contain_message_record(self) -> None:
        """R382: record_summary 不能含 MessageRecord 对象

        虽然 record_summary 是 dict 类型，但若含 MessageRecord 会导致序列化失败。
        R382 仅校验 dict 类型；R383 在写出时会用 to_dict() 保证字段为基本类型。
        本测试验证构造时不直接接受 MessageRecord 作为字段值。
        """
        # 构造一个 MessageRecord
        mr = MessageRecord(
            message_id="m1",
            layout_id="L",
            direction=Direction.REQUEST,
            payload=b"\x00\x01",
            fields=(FieldSpan(field_index=0, start=0, end=2),),
        )
        # RejectedRecord 不接受 MessageRecord 作为任何字段的值
        with pytest.raises(ValueError, match="message_id must be str or None"):
            RejectedRecord(
                line_number=1,
                stage="duplicate",
                reason_code=REASON_CODE_DUPLICATE_MESSAGE_ID,
                message="x",
                message_id=mr,  # type: ignore[arg-type]
            )


class TestRejectedRecordR382ToDict:
    """R382：RejectedRecord.to_dict() 方法测试"""

    def test_r382_to_dict_returns_dict(self) -> None:
        """R382: to_dict() 返回 dict"""
        rec = _make_valid_rejected_record()
        d = rec.to_dict()
        assert isinstance(d, dict)

    def test_r382_to_dict_all_fields_present(self) -> None:
        """R382: to_dict() 包含所有字段"""
        rec = _make_valid_rejected_record()
        d = rec.to_dict()
        assert set(d.keys()) == {
            "line_number", "stage", "reason_code", "message",
            "message_id", "layout_id", "direction",
            "record_summary", "raw_line",
        }

    def test_r382_to_dict_field_values_correct(self) -> None:
        """R382: to_dict() 字段值正确"""
        rec = _make_valid_rejected_record()
        d = rec.to_dict()
        assert d["line_number"] == 5
        assert d["stage"] == "duplicate"
        assert d["reason_code"] == REASON_CODE_DUPLICATE_MESSAGE_ID
        assert d["message"] == "Duplicate message_id: m1"
        assert d["message_id"] == "m1"
        assert d["layout_id"] == "L"
        assert d["direction"] == "request"
        assert d["record_summary"] == {"field_count": 1, "payload_length": 2}
        assert d["raw_line"] == '{"message_id": "m1", ...}'

    def test_r382_to_dict_json_serializable(self) -> None:
        """R382: to_dict() 结果可 json.dumps 序列化（HIGH-2 核心要求）"""
        rec = _make_valid_rejected_record()
        d = rec.to_dict()
        # 不应抛 TypeError
        s = json.dumps(d, ensure_ascii=False)
        assert isinstance(s, str)
        # 反序列化后字段一致
        parsed = json.loads(s)
        assert parsed["reason_code"] == REASON_CODE_DUPLICATE_MESSAGE_ID
        assert parsed["message_id"] == "m1"

    def test_r382_to_dict_minimal_fields_json_serializable(self) -> None:
        """R382: 仅必填字段的 RejectedRecord 也可序列化"""
        rec = RejectedRecord(
            line_number=1,
            stage="parse",
            reason_code=REASON_CODE_INVALID_JSON,
            message="bad json",
        )
        d = rec.to_dict()
        s = json.dumps(d, ensure_ascii=False)
        parsed = json.loads(s)
        assert parsed["line_number"] == 1
        assert parsed["message_id"] is None
        assert parsed["record_summary"] is None

    def test_r382_to_dict_none_line_number_serializable(self) -> None:
        """R382: line_number=None 时可序列化"""
        rec = RejectedRecord(
            line_number=None,
            stage="contract",
            reason_code=REASON_CODE_VALUE_ERROR,
            message="x",
        )
        d = rec.to_dict()
        s = json.dumps(d, ensure_ascii=False)
        parsed = json.loads(s)
        assert parsed["line_number"] is None

    def test_r382_to_dict_does_not_contain_message_record(self) -> None:
        """R382: to_dict() 结果不含 MessageRecord 对象

        HIGH-2 根因：旧 rejected_records 字典含 'record': MessageRecord。
        RejectedRecord.to_dict() 不含 'record' 键，也不含任何 MessageRecord。
        """
        rec = _make_valid_rejected_record()
        d = rec.to_dict()
        assert "record" not in d
        # 检查所有值都不是 MessageRecord
        for k, v in d.items():
            assert not isinstance(v, MessageRecord), (
                f"字段 {k} 含 MessageRecord 对象: {v!r}"
            )


class TestRejectedRecordR382ReasonCodeConstants:
    """R382：reason_code 常量正确性"""

    def test_r382_duplicate_message_id_constant(self) -> None:
        """R382: REASON_CODE_DUPLICATE_MESSAGE_ID 常量值正确"""
        assert REASON_CODE_DUPLICATE_MESSAGE_ID == "duplicate_message_id"

    def test_r382_invalid_json_constant(self) -> None:
        """R382: REASON_CODE_INVALID_JSON 常量值正确"""
        assert REASON_CODE_INVALID_JSON == "invalid_json"

    def test_r382_missing_required_field_constant(self) -> None:
        """R382: REASON_CODE_MISSING_REQUIRED_FIELD 常量值正确"""
        assert REASON_CODE_MISSING_REQUIRED_FIELD == "missing_required_field"

    def test_r382_value_error_constant(self) -> None:
        """R382: REASON_CODE_VALUE_ERROR 常量值正确"""
        assert REASON_CODE_VALUE_ERROR == "value_error"

    def test_r382_type_error_constant(self) -> None:
        """R382: REASON_CODE_TYPE_ERROR 常量值正确"""
        assert REASON_CODE_TYPE_ERROR == "type_error"

    def test_r382_constants_distinct(self) -> None:
        """R382: 所有 reason_code 常量互不相同"""
        codes = {
            REASON_CODE_DUPLICATE_MESSAGE_ID,
            REASON_CODE_INVALID_JSON,
            REASON_CODE_MISSING_REQUIRED_FIELD,
            REASON_CODE_VALUE_ERROR,
            REASON_CODE_TYPE_ERROR,
        }
        assert len(codes) == 5

    def test_r382_constants_are_strings(self) -> None:
        """R382: 所有 reason_code 常量都是字符串"""
        for code in [
            REASON_CODE_DUPLICATE_MESSAGE_ID,
            REASON_CODE_INVALID_JSON,
            REASON_CODE_MISSING_REQUIRED_FIELD,
            REASON_CODE_VALUE_ERROR,
            REASON_CODE_TYPE_ERROR,
        ]:
            assert isinstance(code, str)
            assert code.strip() == code  # 无首尾空白
            assert code  # 非空


class TestRejectedRecordR382StageUsage:
    """R382：RejectedRecord 用于不同阶段的场景测试"""

    def test_r382_stage_parse_invalid_json(self) -> None:
        """R382: parse 阶段（JSON 解析失败）场景"""
        rec = RejectedRecord(
            line_number=3,
            stage="parse",
            reason_code=REASON_CODE_INVALID_JSON,
            message="Expecting ',' delimiter at line 3",
            raw_line='{"message_id": "m1"',
        )
        assert rec.stage == "parse"
        assert rec.reason_code == REASON_CODE_INVALID_JSON
        d = rec.to_dict()
        json.dumps(d)  # 可序列化

    def test_r382_stage_contract_missing_field(self) -> None:
        """R382: contract 阶段（缺少必填字段）场景"""
        rec = RejectedRecord(
            line_number=7,
            stage="contract",
            reason_code=REASON_CODE_MISSING_REQUIRED_FIELD,
            message="Missing required field: payload_hex",
            raw_line='{"message_id": "m1", "layout_id": "L"}',
        )
        assert rec.stage == "contract"
        d = rec.to_dict()
        json.dumps(d)

    def test_r382_stage_duplicate_message_id(self) -> None:
        """R382: duplicate 阶段（重复 message_id）场景"""
        rec = RejectedRecord(
            line_number=5,
            stage="duplicate",
            reason_code=REASON_CODE_DUPLICATE_MESSAGE_ID,
            message="Duplicate message_id: m1",
            message_id="m1",
            layout_id="L",
            direction="request",
            record_summary={"field_count": 1, "payload_length": 2},
        )
        assert rec.stage == "duplicate"
        d = rec.to_dict()
        json.dumps(d)

    def test_r382_stage_contract_value_error(self) -> None:
        """R382: contract 阶段（值错误，如 start>=end）场景"""
        rec = RejectedRecord(
            line_number=2,
            stage="contract",
            reason_code=REASON_CODE_VALUE_ERROR,
            message="start must be less than end, got start=5, end=3",
            message_id="m2",
            layout_id="L",
        )
        assert rec.stage == "contract"
        assert rec.reason_code == REASON_CODE_VALUE_ERROR
        d = rec.to_dict()
        json.dumps(d)

    def test_r382_stage_contract_type_error(self) -> None:
        """R382: contract 阶段（类型错误，如 bool field_index）场景"""
        rec = RejectedRecord(
            line_number=4,
            stage="contract",
            reason_code=REASON_CODE_TYPE_ERROR,
            message="field_index must be int, got bool: True",
            message_id="m3",
        )
        assert rec.stage == "contract"
        assert rec.reason_code == REASON_CODE_TYPE_ERROR
        d = rec.to_dict()
        json.dumps(d)
