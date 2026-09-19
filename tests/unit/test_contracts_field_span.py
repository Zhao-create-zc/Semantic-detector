"""Tests for the minimal FieldSpan contract."""

import pytest
from semantic_detector.contracts import FieldSpan


def test_field_span_stores_minimal_fields() -> None:
    span = FieldSpan(field_index=2, start=4, end=8)

    assert span.field_index == 2
    assert span.start == 4
    assert span.end == 8


def test_field_span_supports_zero_based_start() -> None:
    span = FieldSpan(field_index=0, start=0, end=2)

    assert span.field_index == 0
    assert span.start == 0
    assert span.end == 2


def test_field_span_rejects_negative_field_index() -> None:
    with pytest.raises(ValueError) as exc_info:
        FieldSpan(field_index=-1, start=0, end=2)
    assert "field_index must be non-negative" in str(exc_info.value)


def test_field_span_rejects_negative_start() -> None:
    with pytest.raises(ValueError) as exc_info:
        FieldSpan(field_index=0, start=-1, end=2)
    assert "start must be non-negative" in str(exc_info.value)


def test_field_span_rejects_negative_end() -> None:
    with pytest.raises(ValueError) as exc_info:
        FieldSpan(field_index=0, start=0, end=-1)
    assert "end must be non-negative" in str(exc_info.value)


def test_field_span_rejects_empty_interval() -> None:
    with pytest.raises(ValueError) as exc_info:
        FieldSpan(field_index=0, start=2, end=2)
    assert "start must be less than end" in str(exc_info.value)


def test_field_span_rejects_reversed_interval() -> None:
    with pytest.raises(ValueError) as exc_info:
        FieldSpan(field_index=0, start=5, end=2)
    assert "start must be less than end" in str(exc_info.value)


# ---------------------------------------------------------------------------
# R373：严格整数类型校验失败测试（V3 审计 HIGH-1）
#
# 当前 FieldSpan.__post_init__ 只检查 < 0 和 >=，不检查类型。
# JSON 解析后 0.0/1.0 是 float，True/False 是 bool，会被静默接受，
# 随后在 payload[start:end] 切片阶段崩溃（slice indices must be integers）。
#
# 这些测试在 R374 修复前应当失败（FieldSpan 不拒绝非法类型），
# R374 修复后应当通过。本轮不修改生产代码。
# ---------------------------------------------------------------------------


class TestFieldSpanStrictTypeR373:
    """R373：FieldSpan 严格整数类型校验失败测试。

    复现 V3 审计 HIGH-1：field_index/start/end 为浮点或布尔时被静默接受。
    """

    def test_r373_rejects_float_field_index(self) -> None:
        """field_index=0.0（float）必须在构造阶段拒绝，不得进入切片。"""
        with pytest.raises(ValueError) as exc_info:
            FieldSpan(field_index=0.0, start=0, end=1)
        assert "field_index" in str(exc_info.value)

    def test_r373_rejects_float_start(self) -> None:
        """start=0.0（float）必须在构造阶段拒绝。"""
        with pytest.raises(ValueError) as exc_info:
            FieldSpan(field_index=0, start=0.0, end=1)
        assert "start" in str(exc_info.value)

    def test_r373_rejects_float_end(self) -> None:
        """end=1.0（float）必须在构造阶段拒绝。"""
        with pytest.raises(ValueError) as exc_info:
            FieldSpan(field_index=0, start=0, end=1.0)
        assert "end" in str(exc_info.value)

    def test_r373_rejects_bool_field_index(self) -> None:
        """field_index=True（bool）必须在构造阶段拒绝（bool 不算 int）。"""
        with pytest.raises(ValueError) as exc_info:
            FieldSpan(field_index=True, start=0, end=1)
        assert "field_index" in str(exc_info.value)

    def test_r373_rejects_bool_start(self) -> None:
        """start=False（bool）必须在构造阶段拒绝（bool 不算 int）。"""
        with pytest.raises(ValueError) as exc_info:
            FieldSpan(field_index=0, start=False, end=1)
        assert "start" in str(exc_info.value)

    def test_r373_rejects_bool_end(self) -> None:
        """end=True（bool）必须在构造阶段拒绝（bool 不算 int）。"""
        with pytest.raises(ValueError) as exc_info:
            FieldSpan(field_index=0, start=0, end=True)
        assert "end" in str(exc_info.value)

    def test_r373_rejects_string_field_index(self) -> None:
        """field_index="0"（str）必须在构造阶段拒绝。"""
        with pytest.raises(ValueError) as exc_info:
            FieldSpan(field_index="0", start=0, end=1)
        assert "field_index" in str(exc_info.value)

    def test_r373_rejects_string_start(self) -> None:
        """start="0"（str）必须在构造阶段拒绝。"""
        with pytest.raises(ValueError) as exc_info:
            FieldSpan(field_index=0, start="0", end=1)
        assert "start" in str(exc_info.value)

    def test_r373_rejects_none_field_index(self) -> None:
        """field_index=None 必须在构造阶段拒绝。"""
        with pytest.raises(ValueError) as exc_info:
            FieldSpan(field_index=None, start=0, end=1)
        assert "field_index" in str(exc_info.value)

    def test_r373_accepts_strict_int_zero(self) -> None:
        """合法边界：field_index=0, start=0, end=1（严格 int）必须被接受。"""
        span = FieldSpan(field_index=0, start=0, end=1)
        assert span.field_index == 0
        assert span.start == 0
        assert span.end == 1

    def test_r373_accepts_strict_int_positive(self) -> None:
        """合法边界：严格正整数必须被接受。"""
        span = FieldSpan(field_index=2, start=4, end=8)
        assert span.field_index == 2
        assert span.start == 4
        assert span.end == 8

