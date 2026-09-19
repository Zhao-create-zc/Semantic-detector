"""Tests for the FieldKey contract."""

import pytest
from semantic_detector.contracts import FieldKey, Direction, TypeOpcodeAlignmentKey


def test_field_key_stores_minimal_fields() -> None:
    """测试 FieldKey 存储最小字段"""
    key = FieldKey(
        layout_id="layout_A",
        direction=Direction.REQUEST,
        field_index=0,
    )
    
    assert key.layout_id == "layout_A"
    assert key.direction == Direction.REQUEST
    assert key.field_index == 0


def test_field_key_equality() -> None:
    """测试 FieldKey 相等性"""
    key1 = FieldKey(
        layout_id="layout_A",
        direction=Direction.REQUEST,
        field_index=0,
    )
    key2 = FieldKey(
        layout_id="layout_A",
        direction=Direction.REQUEST,
        field_index=0,
    )
    key3 = FieldKey(
        layout_id="layout_A",
        direction=Direction.RESPONSE,
        field_index=0,
    )
    
    assert key1 == key2
    assert key1 != key3


def test_field_key_hash() -> None:
    """测试 FieldKey 可哈希"""
    key1 = FieldKey(
        layout_id="layout_A",
        direction=Direction.REQUEST,
        field_index=0,
    )
    key2 = FieldKey(
        layout_id="layout_A",
        direction=Direction.REQUEST,
        field_index=0,
    )
    key3 = FieldKey(
        layout_id="layout_A",
        direction=Direction.RESPONSE,
        field_index=0,
    )
    
    assert hash(key1) == hash(key2)
    assert hash(key1) != hash(key3)


def test_field_key_as_dict_key() -> None:
    """测试 FieldKey 可作为 dict key"""
    key1 = FieldKey(
        layout_id="layout_A",
        direction=Direction.REQUEST,
        field_index=0,
    )
    key2 = FieldKey(
        layout_id="layout_A",
        direction=Direction.REQUEST,
        field_index=1,
    )
    
    d = {key1: "value1", key2: "value2"}

    assert d[key1] == "value1"
    assert d[key2] == "value2"
    assert len(d) == 2


class TestFieldKeyStrictValidationR417:
    """R417: FieldKey 严格类型校验（补齐阶段 A 遗漏）

    bool 是 int 子类，hash(True)==hash(1) 且 True==1。
    若 field_index=True 被接受，会与 field_index=1 被误判为同一键，
    导致样本错误合并。
    """

    def test_bool_field_index_rejected(self):
        """field_index=True/False 必须被拒绝（bool 不算 int）。"""
        with pytest.raises(ValueError, match="field_index must be int"):
            FieldKey(layout_id="L", direction=Direction.REQUEST, field_index=True)
        with pytest.raises(ValueError, match="field_index must be int"):
            FieldKey(layout_id="L", direction=Direction.REQUEST, field_index=False)

    def test_float_field_index_rejected(self):
        """field_index=0.0 必须被拒绝（float 不算 int）。"""
        with pytest.raises(ValueError, match="field_index must be int"):
            FieldKey(layout_id="L", direction=Direction.REQUEST, field_index=0.0)

    def test_negative_field_index_rejected(self):
        """field_index=-1 必须被拒绝。"""
        with pytest.raises(ValueError, match="field_index must be >= 0"):
            FieldKey(layout_id="L", direction=Direction.REQUEST, field_index=-1)

    def test_non_str_layout_id_rejected(self):
        """layout_id 非 str 必须被拒绝。"""
        with pytest.raises(ValueError, match="layout_id must be str"):
            FieldKey(layout_id=123, direction=Direction.REQUEST, field_index=0)
        with pytest.raises(ValueError, match="layout_id must be str"):
            FieldKey(layout_id=None, direction=Direction.REQUEST, field_index=0)

    def test_non_direction_direction_rejected(self):
        """direction 非 Direction/str 必须被拒绝（int/None 等非法类型）。"""
        with pytest.raises(ValueError, match="direction must be a Direction or str"):
            FieldKey(layout_id="L", direction=123, field_index=0)
        with pytest.raises(ValueError, match="direction must be a Direction or str"):
            FieldKey(layout_id="L", direction=None, field_index=0)

    def test_bool_field_index_no_hash_collision(self):
        """验证 bool field_index 被拒绝后不会与 int 产生哈希碰撞。"""
        # 正常 int field_index 可构造
        k1 = FieldKey(layout_id="L", direction=Direction.REQUEST, field_index=1)
        assert k1.field_index == 1
        # bool field_index 被拒绝，不会与 k1 碰撞
        with pytest.raises(ValueError):
            FieldKey(layout_id="L", direction=Direction.REQUEST, field_index=True)


class TestTypeOpcodeAlignmentKeyR327:
    """R327: 具名 TypeOpcodeAlignmentKey 测试

    06 计划 R327：
    "消除 Pipeline 与 detector 对裸 tuple 索引含义不一致的问题"

    V2 审计 HIGH-1：旧实现使用裸 tuple，detector 把 alignment_key[3] 当作 width，
    但 Pipeline 放在 [3] 的是 start_mode，导致 start=7 被误判为宽度 7。

    本测试验证具名结构本身正确，尚不改 Pipeline（R328 才接线）。
    """

    def test_normal_construction(self):
        """R327: 正常构造（含 Modbus 风格 start=7, width=1）"""
        key = TypeOpcodeAlignmentKey(
            direction=Direction.REQUEST,
            field_index=4,
            start_mode=7,
            width_mode=1,
        )
        assert key.direction == Direction.REQUEST
        assert key.field_index == 4
        assert key.start_mode == 7
        assert key.width_mode == 1

    def test_negative_field_index_rejected(self):
        """R327: field_index < 0 非法"""
        with pytest.raises(ValueError, match="field_index must be non-negative"):
            TypeOpcodeAlignmentKey(
                direction=Direction.REQUEST,
                field_index=-1,
                start_mode=0,
                width_mode=1,
            )

    def test_negative_start_mode_rejected(self):
        """R327: start_mode < 0 非法"""
        with pytest.raises(ValueError, match="start_mode must be non-negative"):
            TypeOpcodeAlignmentKey(
                direction=Direction.REQUEST,
                field_index=0,
                start_mode=-1,
                width_mode=1,
            )

    def test_zero_width_rejected(self):
        """R327: width_mode=0 非法（必须 > 0）"""
        with pytest.raises(ValueError, match="width_mode must be positive"):
            TypeOpcodeAlignmentKey(
                direction=Direction.REQUEST,
                field_index=0,
                start_mode=0,
                width_mode=0,
            )

    def test_negative_width_rejected(self):
        """R327: width_mode < 0 非法"""
        with pytest.raises(ValueError, match="width_mode must be positive"):
            TypeOpcodeAlignmentKey(
                direction=Direction.REQUEST,
                field_index=0,
                start_mode=0,
                width_mode=-1,
            )

    def test_equal_keys_are_equal(self):
        """R327: 相同值相等（含 start=7, width=1 的 Modbus 场景）"""
        key1 = TypeOpcodeAlignmentKey(
            direction=Direction.REQUEST,
            field_index=4,
            start_mode=7,
            width_mode=1,
        )
        key2 = TypeOpcodeAlignmentKey(
            direction=Direction.REQUEST,
            field_index=4,
            start_mode=7,
            width_mode=1,
        )
        assert key1 == key2
        assert hash(key1) == hash(key2)

    def test_different_direction_not_equal(self):
        """R327: direction 不同不相等"""
        key1 = TypeOpcodeAlignmentKey(
            direction=Direction.REQUEST,
            field_index=4,
            start_mode=7,
            width_mode=1,
        )
        key2 = TypeOpcodeAlignmentKey(
            direction=Direction.RESPONSE,
            field_index=4,
            start_mode=7,
            width_mode=1,
        )
        assert key1 != key2
        assert hash(key1) != hash(key2)

    def test_different_field_index_not_equal(self):
        """R327: field_index 不同不相等"""
        key1 = TypeOpcodeAlignmentKey(
            direction=Direction.REQUEST,
            field_index=4,
            start_mode=7,
            width_mode=1,
        )
        key2 = TypeOpcodeAlignmentKey(
            direction=Direction.REQUEST,
            field_index=5,
            start_mode=7,
            width_mode=1,
        )
        assert key1 != key2

    def test_different_start_mode_not_equal(self):
        """R327: start_mode 不同不相等（位置不一致不对齐）"""
        key1 = TypeOpcodeAlignmentKey(
            direction=Direction.REQUEST,
            field_index=4,
            start_mode=7,
            width_mode=1,
        )
        key2 = TypeOpcodeAlignmentKey(
            direction=Direction.REQUEST,
            field_index=4,
            start_mode=0,
            width_mode=1,
        )
        assert key1 != key2

    def test_different_width_not_equal(self):
        """R327: width_mode 不同不相等（宽度不一致不对齐）"""
        key1 = TypeOpcodeAlignmentKey(
            direction=Direction.REQUEST,
            field_index=4,
            start_mode=7,
            width_mode=1,
        )
        key2 = TypeOpcodeAlignmentKey(
            direction=Direction.REQUEST,
            field_index=4,
            start_mode=7,
            width_mode=2,
        )
        assert key1 != key2

    def test_can_be_dict_key(self):
        """R327: 可作为 dict key（可哈希）"""
        key1 = TypeOpcodeAlignmentKey(
            direction=Direction.REQUEST,
            field_index=4,
            start_mode=7,
            width_mode=1,
        )
        key2 = TypeOpcodeAlignmentKey(
            direction=Direction.REQUEST,
            field_index=4,
            start_mode=7,
            width_mode=1,
        )
        d = {key1: "read_request"}
        assert d[key2] == "read_request"

    def test_position_and_width_not_swapped(self):
        """R327 反例：位置和宽度不得颠倒

        具名结构强制通过字段名构造，start_mode=7 和 width_mode=1 不会混淆。
        验证 start_mode=7, width_mode=1 的键，其 width_mode=1（不是 7），
        start_mode=7（不是 1）。
        """
        key = TypeOpcodeAlignmentKey(
            direction=Direction.REQUEST,
            field_index=4,
            start_mode=7,
            width_mode=1,
        )
        # 关键反例断言：width_mode 是 1（不是 7），start_mode 是 7（不是 1）
        assert key.width_mode == 1, (
            "R327 反例失败：width_mode 应为 1，却变成 7。"
            "这表明 start_mode 和 width_mode 被颠倒，正是 HIGH-1 的根因。"
        )
        assert key.start_mode == 7, (
            "R327 反例失败：start_mode 应为 7，却变成 1。"
            "这表明 start_mode 和 width_mode 被颠倒，正是 HIGH-1 的根因。"
        )

    def test_invalid_direction_type_rejected(self):
        """R327: direction 必须是 Direction 枚举，不接受字符串"""
        with pytest.raises(ValueError, match="direction must be a Direction enum"):
            TypeOpcodeAlignmentKey(
                direction="request",  # 字符串，不是 Direction 枚举
                field_index=0,
                start_mode=0,
                width_mode=1,
            )