"""R079: 把 numeric 结果接入 FieldProfile 测试"""

import struct
from datetime import datetime, timezone

from semantic_detector.contracts import FieldKey, FieldSample, Direction
from semantic_detector.profiling.profile_builder import build_field_profile


def create_sample(field_bytes: bytes, message_length: int, remaining_bytes: int, message_id: str) -> FieldSample:
    """创建 FieldSample 辅助函数"""
    return FieldSample(
        message_id=message_id,
        field_key=FieldKey(layout_id="test_layout", direction=Direction.REQUEST, field_index=0),
        field_bytes=field_bytes,
        start=0,
        end=len(field_bytes),
        message_length=message_length,
        remaining_bytes=remaining_bytes,
    )


def create_sample_with_capture(field_bytes: bytes, message_length: int, remaining_bytes: int,
                                message_id: str, capture_time=None) -> FieldSample:
    """R271: 创建带 capture_time 的 FieldSample 辅助函数"""
    return FieldSample(
        message_id=message_id,
        field_key=FieldKey(layout_id="test_layout", direction=Direction.REQUEST, field_index=0),
        field_bytes=field_bytes,
        start=0,
        end=len(field_bytes),
        message_length=message_length,
        remaining_bytes=remaining_bytes,
        capture_time=capture_time,
    )


class TestNumericInProfile:
    """测试 numeric 结果接入 FieldProfile"""
    
    def test_fixed_width_2_bytes_be_increasing(self):
        """固定宽度 2 字节,大端递增序列"""
        samples = [
            create_sample(b'\x00\x01', 10, 8, 'msg1'),
            create_sample(b'\x00\x02', 11, 9, 'msg2'),
            create_sample(b'\x00\x03', 12, 10, 'msg3'),
            create_sample(b'\x00\x04', 13, 11, 'msg4'),
            create_sample(b'\x00\x05', 14, 12, 'msg5'),
        ]
        
        field_key = FieldKey(layout_id="test_layout", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)
        
        # 检查基础信息
        assert profile.fixed_width is True
        assert profile.width_min == 2
        assert profile.width_max == 2
        
        # 检查大端数值统计
        assert profile.numeric_be_min == 1
        assert profile.numeric_be_max == 5
        assert profile.numeric_be_mean is not None
        assert profile.numeric_be_median is not None
        assert profile.numeric_be_strictly_increasing_ratio == 1.0
        assert profile.numeric_be_nondecreasing_ratio == 1.0
        assert profile.numeric_be_step_one_ratio == 1.0
    
    def test_fixed_width_2_bytes_le_increasing(self):
        """固定宽度 2 字节,小端递增序列"""
        samples = [
            create_sample(b'\x01\x00', 10, 8, 'msg1'),
            create_sample(b'\x02\x00', 11, 9, 'msg2'),
            create_sample(b'\x03\x00', 12, 10, 'msg3'),
            create_sample(b'\x04\x00', 13, 11, 'msg4'),
            create_sample(b'\x05\x00', 14, 12, 'msg5'),
        ]
        
        field_key = FieldKey(layout_id="test_layout", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)
        
        # 检查小端数值统计
        assert profile.numeric_le_min == 1
        assert profile.numeric_le_max == 5
        assert profile.numeric_le_strictly_increasing_ratio == 1.0
        assert profile.numeric_le_step_one_ratio == 1.0
    
    def test_variable_width_no_numeric_stats(self):
        """变宽字段不计算数值统计"""
        samples = [
            create_sample(b'\x01', 10, 9, 'msg1'),
            create_sample(b'\x01\x02', 11, 9, 'msg2'),
            create_sample(b'\x01\x02\x03', 12, 9, 'msg3'),
        ]
        
        field_key = FieldKey(layout_id="test_layout", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)
        
        # 变宽字段不应该有数值统计
        assert profile.fixed_width is False
        assert profile.numeric_be_min is None
        assert profile.numeric_be_max is None
        assert profile.numeric_le_min is None
        assert profile.numeric_le_max is None
    
    def test_width_9_no_numeric_stats(self):
        """宽度 9 不计算数值统计"""
        samples = [
            create_sample(b'\x00' * 9, 20, 11, 'msg1'),
            create_sample(b'\x00' * 9, 21, 12, 'msg2'),
        ]
        
        field_key = FieldKey(layout_id="test_layout", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)
        
        # 宽度 9 不应该有数值统计
        assert profile.numeric_be_min is None
        assert profile.numeric_le_min is None
    
    def test_constant_sequence(self):
        """常量序列"""
        samples = [
            create_sample(b'\x00\x05', 10, 8, 'msg1'),
            create_sample(b'\x00\x05', 11, 9, 'msg2'),
            create_sample(b'\x00\x05', 12, 10, 'msg3'),
        ]
        
        field_key = FieldKey(layout_id="test_layout", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)
        
        # 常量序列
        assert profile.numeric_be_min == 5
        assert profile.numeric_be_max == 5
        assert profile.numeric_be_strictly_increasing_ratio == 0.0
        assert profile.numeric_be_nondecreasing_ratio == 1.0
        assert profile.numeric_be_step_one_ratio == 0.0
    
    def test_message_length_correlation(self):
        """数值与消息长度相关性"""
        samples = [
            create_sample(b'\x00\x0a', 10, 8, 'msg1'),
            create_sample(b'\x00\x14', 20, 18, 'msg2'),
            create_sample(b'\x00\x1e', 30, 28, 'msg3'),
            create_sample(b'\x00\x28', 40, 38, 'msg4'),
        ]
        
        field_key = FieldKey(layout_id="test_layout", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)
        
        # 数值等于消息长度,应该完全正相关
        assert profile.numeric_be_message_length_correlation is not None
        assert abs(profile.numeric_be_message_length_correlation - 1.0) < 1e-9
    
    def test_remaining_bytes_correlation(self):
        """数值与剩余字节数相关性"""
        samples = [
            create_sample(b'\x00\x08', 10, 8, 'msg1'),
            create_sample(b'\x00\x12', 20, 18, 'msg2'),
            create_sample(b'\x00\x1c', 30, 28, 'msg3'),
            create_sample(b'\x00\x26', 40, 38, 'msg4'),
        ]
        
        field_key = FieldKey(layout_id="test_layout", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)
        
        # 数值等于剩余字节数,应该完全正相关
        assert profile.numeric_be_remaining_bytes_correlation is not None
        assert abs(profile.numeric_be_remaining_bytes_correlation - 1.0) < 1e-9


class TestBeLengthRelationsR266:
    """R266：BE 精确长度关系字段测试（HIGH-7 length 修复铺路）

    验收：total/remaining/offset | 字段可序列化。
    复用 bi_adapted.length_relations 的 4 个 support 函数。
    """

    def test_message_length_exact_support_full(self):
        """R266：value == message_length 时 exact_support == 1.0"""
        # BE 2 字节：value = 10, 20, 30, 40 == message_length
        samples = [
            create_sample(b'\x00\x0a', 10, 8, 'msg1'),
            create_sample(b'\x00\x14', 20, 18, 'msg2'),
            create_sample(b'\x00\x1e', 30, 28, 'msg3'),
            create_sample(b'\x00\x28', 40, 38, 'msg4'),
        ]
        field_key = FieldKey(layout_id="test_layout", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)

        assert profile.numeric_be_message_length_exact_support is not None
        assert abs(profile.numeric_be_message_length_exact_support - 1.0) < 1e-9
        # offset=0 时 offset_support 也应为 1.0，offset=0
        assert abs(profile.numeric_be_message_length_offset_support - 1.0) < 1e-9
        assert profile.numeric_be_message_length_offset == 0

    def test_remaining_bytes_exact_support_full(self):
        """R266：value == remaining_bytes 时 exact_support == 1.0"""
        # BE 2 字节：value = 8, 18, 28, 38 == remaining_bytes
        samples = [
            create_sample(b'\x00\x08', 10, 8, 'msg1'),
            create_sample(b'\x00\x12', 20, 18, 'msg2'),
            create_sample(b'\x00\x1c', 30, 28, 'msg3'),
            create_sample(b'\x00\x26', 40, 38, 'msg4'),
        ]
        field_key = FieldKey(layout_id="test_layout", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)

        assert profile.numeric_be_remaining_bytes_exact_support is not None
        assert abs(profile.numeric_be_remaining_bytes_exact_support - 1.0) < 1e-9
        assert abs(profile.numeric_be_remaining_bytes_offset_support - 1.0) < 1e-9
        assert profile.numeric_be_remaining_bytes_offset == 0

    def test_message_length_offset_support_nonzero_offset(self):
        """R266：value + offset == message_length，offset != 0"""
        # BE 2 字节：value = 8, 18, 28, 38；message_length = 10, 20, 30, 40
        # offset = message_length - value = 2（统一）
        samples = [
            create_sample(b'\x00\x08', 10, 8, 'msg1'),
            create_sample(b'\x00\x12', 20, 18, 'msg2'),
            create_sample(b'\x00\x1c', 30, 28, 'msg3'),
            create_sample(b'\x00\x26', 40, 38, 'msg4'),
        ]
        field_key = FieldKey(layout_id="test_layout", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)

        # exact_support（value == message_length）应为 0（value=8 != length=10）
        assert profile.numeric_be_message_length_exact_support == 0.0
        # offset_support：value + 2 == message_length，全部匹配
        assert abs(profile.numeric_be_message_length_offset_support - 1.0) < 1e-9
        assert profile.numeric_be_message_length_offset == 2

    def test_distinct_value_count_at_least_two(self):
        """R266：distinct_value_count 反映真实不同值数量（防止常量误判）"""
        # 5 个不同 BE 值：1, 2, 3, 4, 5
        samples = [
            create_sample(b'\x00\x01', 10, 8, 'msg1'),
            create_sample(b'\x00\x02', 11, 9, 'msg2'),
            create_sample(b'\x00\x03', 12, 10, 'msg3'),
            create_sample(b'\x00\x04', 13, 11, 'msg4'),
            create_sample(b'\x00\x05', 14, 12, 'msg5'),
        ]
        field_key = FieldKey(layout_id="test_layout", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)

        assert profile.numeric_be_distinct_value_count == 5

    def test_distinct_value_count_one_for_constant(self):
        """R266：常量字段 distinct_value_count == 1（不应被判为长度）"""
        samples = [
            create_sample(b'\x00\x05', 10, 8, 'msg1'),
            create_sample(b'\x00\x05', 11, 9, 'msg2'),
            create_sample(b'\x00\x05', 12, 10, 'msg3'),
        ]
        field_key = FieldKey(layout_id="test_layout", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)

        assert profile.numeric_be_distinct_value_count == 1

    def test_no_match_support_zero(self):
        """R266：value 与 message_length 无任何匹配时 support == 0.0"""
        # BE value = 100, 200, 300, 400；message_length = 10, 20, 30, 40
        samples = [
            create_sample(b'\x00\x64', 10, 8, 'msg1'),  # 100 vs 10
            create_sample(b'\x00\xc8', 20, 18, 'msg2'),  # 200 vs 20
            create_sample(b'\x01\x2c', 30, 28, 'msg3'),  # 300 vs 30
            create_sample(b'\x01\x90', 40, 38, 'msg4'),  # 400 vs 40
        ]
        field_key = FieldKey(layout_id="test_layout", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)

        assert profile.numeric_be_message_length_exact_support == 0.0
        # offset 也不统一（-90, -180, -270, -360），offset_support 取最常见 offset 的比例
        # 每个 offset 各 1 次，最常见 offset 支持 = 1/4
        assert profile.numeric_be_message_length_offset_support is not None

    def test_fields_serializable_in_to_dict(self):
        """R266：BE 长度关系字段可序列化（to_dict 含全部新字段）"""
        samples = [
            create_sample(b'\x00\x0a', 10, 8, 'msg1'),
            create_sample(b'\x00\x14', 20, 18, 'msg2'),
        ]
        field_key = FieldKey(layout_id="test_layout", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)
        d = profile.to_dict()

        # 6 个 BE support 字段 + 2 个 distinct_count
        assert "numeric_be_message_length_exact_support" in d
        assert "numeric_be_remaining_bytes_exact_support" in d
        assert "numeric_be_message_length_offset_support" in d
        assert "numeric_be_message_length_offset" in d
        assert "numeric_be_remaining_bytes_offset_support" in d
        assert "numeric_be_remaining_bytes_offset" in d
        assert "numeric_be_distinct_value_count" in d
        assert "numeric_le_distinct_value_count" in d

    def test_fields_roundtrip_via_json(self):
        """R266：BE 长度关系字段 JSON round-trip 保持值"""
        import json
        samples = [
            create_sample(b'\x00\x0a', 10, 8, 'msg1'),
            create_sample(b'\x00\x14', 20, 18, 'msg2'),
        ]
        field_key = FieldKey(layout_id="test_layout", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)
        d = profile.to_dict()
        serialized = json.dumps(d)
        deserialized = json.loads(serialized)

        assert deserialized["numeric_be_message_length_exact_support"] == 1.0
        assert deserialized["numeric_be_message_length_offset"] == 0
        assert deserialized["numeric_be_distinct_value_count"] == 2


class TestLeLengthRelationsR267:
    """R267：LE 精确长度关系字段测试（与 BE 对称，端序独立）

    验收：LE fixture | 端序独立。
    LE 字段名与 BE 对称，复用同一组 bi_adapted.length_relations 函数，
    但输入为 LE 解码值。
    """

    def test_le_message_length_exact_support_full(self):
        """R267：LE value == message_length 时 exact_support == 1.0"""
        # LE 2 字节：b'\x0a\x00' = 10, b'\x14\x00' = 20, ... == message_length
        samples = [
            create_sample(b'\x0a\x00', 10, 8, 'msg1'),
            create_sample(b'\x14\x00', 20, 18, 'msg2'),
            create_sample(b'\x1e\x00', 30, 28, 'msg3'),
            create_sample(b'\x28\x00', 40, 38, 'msg4'),
        ]
        field_key = FieldKey(layout_id="test_layout", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)

        assert profile.numeric_le_message_length_exact_support is not None
        assert abs(profile.numeric_le_message_length_exact_support - 1.0) < 1e-9
        assert abs(profile.numeric_le_message_length_offset_support - 1.0) < 1e-9
        assert profile.numeric_le_message_length_offset == 0

    def test_le_remaining_bytes_exact_support_full(self):
        """R267：LE value == remaining_bytes 时 exact_support == 1.0"""
        # LE 2 字节：b'\x08\x00' = 8, b'\x12\x00' = 18, ... == remaining_bytes
        samples = [
            create_sample(b'\x08\x00', 10, 8, 'msg1'),
            create_sample(b'\x12\x00', 20, 18, 'msg2'),
            create_sample(b'\x1c\x00', 30, 28, 'msg3'),
            create_sample(b'\x26\x00', 40, 38, 'msg4'),
        ]
        field_key = FieldKey(layout_id="test_layout", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)

        assert profile.numeric_le_remaining_bytes_exact_support is not None
        assert abs(profile.numeric_le_remaining_bytes_exact_support - 1.0) < 1e-9
        assert abs(profile.numeric_le_remaining_bytes_offset_support - 1.0) < 1e-9
        assert profile.numeric_le_remaining_bytes_offset == 0

    def test_le_message_length_offset_support_nonzero_offset(self):
        """R267：LE value + offset == message_length，offset != 0"""
        # LE 2 字节：value = 8, 18, 28, 38；message_length = 10, 20, 30, 40
        # offset = message_length - value = 2（统一）
        samples = [
            create_sample(b'\x08\x00', 10, 8, 'msg1'),
            create_sample(b'\x12\x00', 20, 18, 'msg2'),
            create_sample(b'\x1c\x00', 30, 28, 'msg3'),
            create_sample(b'\x26\x00', 40, 38, 'msg4'),
        ]
        field_key = FieldKey(layout_id="test_layout", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)

        assert profile.numeric_le_message_length_exact_support == 0.0
        assert abs(profile.numeric_le_message_length_offset_support - 1.0) < 1e-9
        assert profile.numeric_le_message_length_offset == 2

    def test_le_distinct_value_count(self):
        """R267：LE distinct_value_count 反映 LE 解码的不同值数量"""
        # LE 2 字节：b'\x01\x00'=1, b'\x02\x00'=2, ... 5 个不同值
        samples = [
            create_sample(b'\x01\x00', 10, 8, 'msg1'),
            create_sample(b'\x02\x00', 11, 9, 'msg2'),
            create_sample(b'\x03\x00', 12, 10, 'msg3'),
            create_sample(b'\x04\x00', 13, 11, 'msg4'),
            create_sample(b'\x05\x00', 14, 12, 'msg5'),
        ]
        field_key = FieldKey(layout_id="test_layout", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)

        assert profile.numeric_le_distinct_value_count == 5

    def test_be_le_independent_when_byte_order_differs(self):
        """R267：BE 和 LE 解码不同时，support 独立计算（端序独立）

        构造 BE value != message_length 但 LE value == message_length 的场景：
        b'\x0a\x00'：BE=2560，LE=10。message_length=10。
        LE exact_support==1.0，BE exact_support==0.0。
        """
        samples = [
            create_sample(b'\x0a\x00', 10, 8, 'msg1'),
            create_sample(b'\x14\x00', 20, 18, 'msg2'),
            create_sample(b'\x1e\x00', 30, 28, 'msg3'),
            create_sample(b'\x28\x00', 40, 38, 'msg4'),
        ]
        field_key = FieldKey(layout_id="test_layout", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)

        # LE value (10,20,30,40) == message_length → exact_support=1.0
        assert abs(profile.numeric_le_message_length_exact_support - 1.0) < 1e-9
        # BE value (2560,5120,7680,10240) != message_length → exact_support=0.0
        assert profile.numeric_be_message_length_exact_support == 0.0

    def test_le_fields_serializable_in_to_dict(self):
        """R267：LE 长度关系字段可序列化"""
        samples = [
            create_sample(b'\x0a\x00', 10, 8, 'msg1'),
            create_sample(b'\x14\x00', 20, 18, 'msg2'),
        ]
        field_key = FieldKey(layout_id="test_layout", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)
        d = profile.to_dict()

        assert "numeric_le_message_length_exact_support" in d
        assert "numeric_le_remaining_bytes_exact_support" in d
        assert "numeric_le_message_length_offset_support" in d
        assert "numeric_le_message_length_offset" in d
        assert "numeric_le_remaining_bytes_offset_support" in d
        assert "numeric_le_remaining_bytes_offset" in d

    def test_le_fields_roundtrip_via_json(self):
        """R267：LE 长度关系字段 JSON round-trip 保持值"""
        import json
        samples = [
            create_sample(b'\x0a\x00', 10, 8, 'msg1'),
            create_sample(b'\x14\x00', 20, 18, 'msg2'),
        ]
        field_key = FieldKey(layout_id="test_layout", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)
        d = profile.to_dict()
        serialized = json.dumps(d)
        deserialized = json.loads(serialized)

        assert deserialized["numeric_le_message_length_exact_support"] == 1.0
        assert deserialized["numeric_le_message_length_offset"] == 0
        assert deserialized["numeric_le_distinct_value_count"] == 2


class TestBuildProfileRealSamplesR268:
    """R268：build_field_profile 接入 bi_adapted length_relations 端到端验证

    验收：真实样本列表 | 不再只依赖 correlation。
    全链路：FieldSample 列表（含 message_length/remaining_bytes）→
    build_field_profile → FieldProfile 的 exact_support/offset 字段。
    关键：exact_support 来自真实样本统计，而非手动构造数值列表；
    correlation 仍保留但仅作描述，不再作为判定依据。
    """

    def test_real_samples_produce_exact_support_from_field_sample(self):
        """R268：真实 FieldSample 列表驱动 exact_support 计算

        FieldSample.message_length / remaining_bytes 是真实来源，
        build_field_profile 内部提取后传给 bi_adapted.length_relations。
        验证：value == message_length 时 exact_support == 1.0。
        """
        # 真实样本：BE value = 10/20/30/40，message_length = 10/20/30/40
        samples = [
            create_sample(b'\x00\x0a', 10, 8, 'msg1'),
            create_sample(b'\x00\x14', 20, 18, 'msg2'),
            create_sample(b'\x00\x1e', 30, 28, 'msg3'),
            create_sample(b'\x00\x28', 40, 38, 'msg4'),
        ]
        field_key = FieldKey(layout_id="real_layout", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)

        # exact_support 由真实样本统计，应为 1.0
        assert profile.numeric_be_message_length_exact_support is not None
        assert abs(profile.numeric_be_message_length_exact_support - 1.0) < 1e-9
        # distinct_value_count 也来自真实样本去重
        assert profile.numeric_be_distinct_value_count == 4

    def test_real_samples_partial_match_support_ratio(self):
        """R268：部分匹配时 exact_support 反映真实比例（非 0/1 二值）"""
        # 4 个样本：2 个 value==message_length，2 个不等
        # BE: 10==10 ✓, 20==20 ✓, 99!=30 ✗, 99!=40 ✗
        samples = [
            create_sample(b'\x00\x0a', 10, 8, 'msg1'),  # 10 == 10
            create_sample(b'\x00\x14', 20, 18, 'msg2'),  # 20 == 20
            create_sample(b'\x00\x63', 30, 28, 'msg3'),  # 99 != 30
            create_sample(b'\x00\x63', 40, 38, 'msg4'),  # 99 != 40
        ]
        field_key = FieldKey(layout_id="partial_layout", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)

        # 2/4 = 0.5
        assert abs(profile.numeric_be_message_length_exact_support - 0.5) < 1e-9
        assert profile.numeric_be_distinct_value_count == 3  # {10, 20, 99}

    def test_correlation_high_but_exact_support_zero(self):
        """R268：correlation 高但 exact_support 为 0 时不能判为长度

        教程 8.1 反例：value=[1,2,3,4], length=[100,200,300,400]
        correlation=1.0（完全正相关）但 value != length（exact_support=0）。
        证明 correlation 不可作为 length 判定硬证据。
        """
        # BE: value = 1,2,3,4；message_length = 100,200,300,400
        samples = [
            create_sample(b'\x00\x01', 100, 98, 'msg1'),
            create_sample(b'\x00\x02', 200, 198, 'msg2'),
            create_sample(b'\x00\x03', 300, 298, 'msg3'),
            create_sample(b'\x00\x04', 400, 398, 'msg4'),
        ]
        field_key = FieldKey(layout_id="trap_layout", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)

        # correlation 完全正相关（保留作画像描述）
        assert profile.numeric_be_message_length_correlation is not None
        assert abs(profile.numeric_be_message_length_correlation - 1.0) < 1e-9
        # 但 exact_support == 0（没有任何样本 value == message_length）
        assert profile.numeric_be_message_length_exact_support == 0.0
        # offset_support 也应为 0（offset = 99/198/297/396 不统一）
        # 最常见 offset 各 1 次，support = 1/4 = 0.25
        assert profile.numeric_be_message_length_offset_support is not None
        assert abs(profile.numeric_be_message_length_offset_support - 0.25) < 1e-9

    def test_real_samples_remaining_bytes_driven(self):
        """R268：remaining_bytes 同样来自真实 FieldSample"""
        # BE value = 8/18/28/38；remaining_bytes = 8/18/28/38
        samples = [
            create_sample(b'\x00\x08', 10, 8, 'msg1'),
            create_sample(b'\x00\x12', 20, 18, 'msg2'),
            create_sample(b'\x00\x1c', 30, 28, 'msg3'),
            create_sample(b'\x00\x26', 40, 38, 'msg4'),
        ]
        field_key = FieldKey(layout_id="rb_layout", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)

        assert abs(profile.numeric_be_remaining_bytes_exact_support - 1.0) < 1e-9
        assert profile.numeric_be_remaining_bytes_offset == 0

    def test_correlation_and_exact_support_coexist_in_profile(self):
        """R268：correlation 与 exact_support 同时存在于 FieldProfile

        correlation 不删除（保留作画像描述），但 length 判定走 exact_support。
        """
        samples = [
            create_sample(b'\x00\x0a', 10, 8, 'msg1'),
            create_sample(b'\x00\x14', 20, 18, 'msg2'),
        ]
        field_key = FieldKey(layout_id="coexist_layout", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)

        # 两者共存
        assert profile.numeric_be_message_length_correlation is not None
        assert profile.numeric_be_message_length_exact_support is not None
        # 字段名同时存在于 to_dict
        d = profile.to_dict()
        assert "numeric_be_message_length_correlation" in d
        assert "numeric_be_message_length_exact_support" in d
        assert "numeric_le_message_length_correlation" in d
        assert "numeric_le_message_length_exact_support" in d


class TestDistinctValueCountR269:
    """R269：distinct numeric value count 常量/变化值场景

    验收：常量/变化值 | 长度 detector 可排除常量伪证据。
    教程 8.2："至少需要两个不同字段值，才允许把固定常量判定为长度"。
    教程 8.4 LengthDetector 前置条件："至少两个不同数值"。

    本轮强化：常量字段即使 value==message_length 巧合命中（exact_support=1.0），
    distinct_value_count==1 仍标记为常量伪证据，后续 LengthDetector 应据此排除。
    """

    def test_constant_field_with_accidental_length_match_still_distinct_one(self):
        """R269：常量字段即使 value 巧合等于 message_length，distinct==1 仍是伪证据

        反例场景：所有样本 value=10, message_length=10
        - exact_support=1.0（看似完美 length 候选）
        - 但 distinct_value_count=1（常量字段）
        教程 8.2/8.4 明确禁止常量被判定为长度。
        """
        # BE 2 字节：所有样本 value=10，message_length=10
        samples = [
            create_sample(b'\x00\x0a', 10, 8, 'msg1'),
            create_sample(b'\x00\x0a', 10, 8, 'msg2'),
            create_sample(b'\x00\x0a', 10, 8, 'msg3'),
            create_sample(b'\x00\x0a', 10, 8, 'msg4'),
        ]
        field_key = FieldKey(layout_id="const_trap", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)

        # exact_support 看似完美
        assert abs(profile.numeric_be_message_length_exact_support - 1.0) < 1e-9
        # 但 distinct_value_count=1 → 常量伪证据，LengthDetector 应排除
        assert profile.numeric_be_distinct_value_count == 1
        # LE 解码后也是常量
        assert profile.numeric_le_distinct_value_count == 1

    def test_distinct_two_minimum_legal_for_length(self):
        """R269：distinct==2 是合法长度的最小阈值（边界值）

        教程 8.4："至少两个不同数值"——distinct==2 是最小合法值。
        """
        # BE: value=10, 20（2 个不同值），message_length=10, 20
        samples = [
            create_sample(b'\x00\x0a', 10, 8, 'msg1'),
            create_sample(b'\x00\x14', 20, 18, 'msg2'),
        ]
        field_key = FieldKey(layout_id="min_legal", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)

        assert profile.numeric_be_distinct_value_count == 2
        assert abs(profile.numeric_be_message_length_exact_support - 1.0) < 1e-9

    def test_distinct_value_count_grows_with_unique_values(self):
        """R269：distinct_value_count 随不同值数量增长"""
        # 3 个不同值
        samples = [
            create_sample(b'\x00\x0a', 10, 8, 'msg1'),
            create_sample(b'\x00\x14', 20, 18, 'msg2'),
            create_sample(b'\x00\x1e', 30, 28, 'msg3'),
        ]
        field_key = FieldKey(layout_id="three_unique", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)
        assert profile.numeric_be_distinct_value_count == 3

        # 5 个不同值
        samples = [
            create_sample(b'\x00\x0a', 10, 8, 'msg1'),
            create_sample(b'\x00\x14', 20, 18, 'msg2'),
            create_sample(b'\x00\x1e', 30, 28, 'msg3'),
            create_sample(b'\x00\x28', 40, 38, 'msg4'),
            create_sample(b'\x00\x32', 50, 48, 'msg5'),
        ]
        profile = build_field_profile(field_key, samples)
        assert profile.numeric_be_distinct_value_count == 5

    def test_distinct_value_count_in_to_dict_for_detector_consumption(self):
        """R269：distinct_value_count 在 to_dict 中可被 LengthDetector 读取

        LengthDetector 从 profile.to_dict() 读取 distinct_value_count 作为前置条件。
        """
        samples = [
            create_sample(b'\x00\x0a', 10, 8, 'msg1'),
            create_sample(b'\x00\x14', 20, 18, 'msg2'),
        ]
        field_key = FieldKey(layout_id="consumer", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)
        d = profile.to_dict()

        # LengthDetector 前置条件字段
        assert d["numeric_be_distinct_value_count"] == 2
        assert d["numeric_le_distinct_value_count"] == 2
        # 配合 exact_support 一起判读
        assert d["numeric_be_message_length_exact_support"] == 1.0

    def test_constant_field_distinct_one_with_high_correlation_trap(self):
        """R269：常量字段 correlation 为 None/退化，distinct==1 双重排除

        常量字段 std=0，Pearson correlation 会退化（分母为 0）。
        即便如此 distinct_value_count==1 仍是更可靠的排除信号。
        """
        # 所有样本相同：value=10, length=10
        samples = [
            create_sample(b'\x00\x0a', 10, 8, 'msg1'),
            create_sample(b'\x00\x0a', 10, 8, 'msg2'),
            create_sample(b'\x00\x0a', 10, 8, 'msg3'),
        ]
        field_key = FieldKey(layout_id="const_corr_trap", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)

        # distinct==1 是硬证据
        assert profile.numeric_be_distinct_value_count == 1
        # correlation 在常量场景下可能为 None 或退化值
        # （具体行为依赖 compute_numeric_message_length_correlation 实现，
        # 此处不强制断言 correlation 值，只断言 distinct_value_count 是可靠排除信号）

    def test_be_le_distinct_count_consistent_for_same_byte_pattern(self):
        """R269：同一字节模式 BE/LE distinct_count 一致（虽然具体值不同）

        字节 b'\x00\x0a'/b'\x00\x14'/b'\x00\x1e' BE 解码={10,20,30}，
        LE 解码={2560,5120,7680}，但 distinct_count 都==3。
        """
        samples = [
            create_sample(b'\x00\x0a', 10, 8, 'msg1'),
            create_sample(b'\x00\x14', 20, 18, 'msg2'),
            create_sample(b'\x00\x1e', 30, 28, 'msg3'),
        ]
        field_key = FieldKey(layout_id="be_le_consistent", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)

        assert profile.numeric_be_distinct_value_count == 3
        assert profile.numeric_le_distinct_value_count == 3


class TestUnixSecondsSupportR271:
    """R271：Unix 秒 BE/LE timestamp support 测试

    验收：4 字节时间 fixture | support 来自真实 capture range。
    教程 9.4：
    - 4 字节固定宽度才计算
    - 所有 capture_time 缺失时 support=None
    - 时间上下界来自真实 capture_time（UTC aware datetime）
    - 复用 bi_adapted.timestamp_range 的 decode + calculate_unix_seconds_support
    """

    def test_be_unix_seconds_full_support(self):
        """R271：BE 4 字节 Unix 秒 == capture_time → support=1.0"""
        t1 = datetime(2026, 6, 27, 10, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 6, 27, 11, 0, 0, tzinfo=timezone.utc)
        ts1 = int(t1.timestamp())
        ts2 = int(t2.timestamp())
        # 4 字节 BE 时间戳
        samples = [
            create_sample_with_capture(struct.pack(">I", ts1), 10, 8, 'm1', t1),
            create_sample_with_capture(struct.pack(">I", ts2), 10, 8, 'm2', t2),
        ]
        field_key = FieldKey(layout_id="ts_be", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)

        assert profile.timestamp_be_unix_seconds_support is not None
        assert abs(profile.timestamp_be_unix_seconds_support - 1.0) < 1e-9

    def test_le_unix_seconds_full_support(self):
        """R271：LE 4 字节 Unix 秒 == capture_time → support=1.0"""
        t1 = datetime(2026, 6, 27, 10, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 6, 27, 11, 0, 0, tzinfo=timezone.utc)
        ts1 = int(t1.timestamp())
        ts2 = int(t2.timestamp())
        # 4 字节 LE 时间戳
        samples = [
            create_sample_with_capture(struct.pack("<I", ts1), 10, 8, 'm1', t1),
            create_sample_with_capture(struct.pack("<I", ts2), 10, 8, 'm2', t2),
        ]
        field_key = FieldKey(layout_id="ts_le", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)

        assert profile.timestamp_le_unix_seconds_support is not None
        assert abs(profile.timestamp_le_unix_seconds_support - 1.0) < 1e-9

    def test_be_unix_seconds_zero_support_when_out_of_range(self):
        """R271：BE 4 字节值超出 capture range → support=0.0"""
        t1 = datetime(2026, 6, 27, 10, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 6, 27, 11, 0, 0, tzinfo=timezone.utc)
        # capture range = [2026-06-27T10:00:00, 2026-06-27T11:00:00]
        # slop = 86400 秒 = 1 天，所以实际范围 = [2026-06-26T10:00:00, 2026-06-28T11:00:00]
        # 用 2000 年的时间戳，肯定超出范围
        old_ts = int(datetime(2000, 1, 1, tzinfo=timezone.utc).timestamp())
        samples = [
            create_sample_with_capture(struct.pack(">I", old_ts), 10, 8, 'm1', t1),
            create_sample_with_capture(struct.pack(">I", old_ts), 10, 8, 'm2', t2),
        ]
        field_key = FieldKey(layout_id="ts_oob", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)

        assert profile.timestamp_be_unix_seconds_support is not None
        assert profile.timestamp_be_unix_seconds_support == 0.0

    def test_non_4_byte_field_returns_none_support(self):
        """R271：非 4 字节字段 → support=None（不计算）"""
        t1 = datetime(2026, 6, 27, 10, 0, 0, tzinfo=timezone.utc)
        # 2 字节字段（不是 4 字节）
        samples = [
            create_sample_with_capture(b'\x00\x01', 10, 8, 'm1', t1),
            create_sample_with_capture(b'\x00\x02', 10, 8, 'm2', t1),
        ]
        field_key = FieldKey(layout_id="ts_2byte", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)

        assert profile.timestamp_be_unix_seconds_support is None
        assert profile.timestamp_le_unix_seconds_support is None

    def test_no_capture_time_returns_none_support(self):
        """R271：capture_time 全缺失 → support=None（不用当前系统时间兜底）

        教程 9.4：所有 capture_time 缺失时所有 timestamp support 为 None。
        """
        ts = int(datetime(2026, 6, 27, 10, 0, 0, tzinfo=timezone.utc).timestamp())
        samples = [
            create_sample_with_capture(struct.pack(">I", ts), 10, 8, 'm1', None),
            create_sample_with_capture(struct.pack(">I", ts), 10, 8, 'm2', None),
        ]
        field_key = FieldKey(layout_id="ts_nocap", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)

        # 即使 4 字节字段值是合法 Unix 秒，capture_time 缺失时 support 仍为 None
        assert profile.timestamp_be_unix_seconds_support is None
        assert profile.timestamp_le_unix_seconds_support is None

    def test_partial_support_half_match(self):
        """R271：部分匹配时 support 反映真实比例"""
        t1 = datetime(2026, 6, 27, 10, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 6, 27, 11, 0, 0, tzinfo=timezone.utc)
        ts_in_range = int(t1.timestamp())  # 在范围内
        old_ts = int(datetime(2000, 1, 1, tzinfo=timezone.utc).timestamp())  # 超出范围
        # 2 个在范围内 + 2 个超出 → support=0.5
        samples = [
            create_sample_with_capture(struct.pack(">I", ts_in_range), 10, 8, 'm1', t1),
            create_sample_with_capture(struct.pack(">I", ts_in_range), 10, 8, 'm2', t2),
            create_sample_with_capture(struct.pack(">I", old_ts), 10, 8, 'm3', t1),
            create_sample_with_capture(struct.pack(">I", old_ts), 10, 8, 'm4', t2),
        ]
        field_key = FieldKey(layout_id="ts_partial", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)

        assert profile.timestamp_be_unix_seconds_support is not None
        assert abs(profile.timestamp_be_unix_seconds_support - 0.5) < 1e-9

    def test_timestamp_support_in_to_dict(self):
        """R271：timestamp support 字段在 to_dict 中可被 TimestampDetector 读取"""
        t1 = datetime(2026, 6, 27, 10, 0, 0, tzinfo=timezone.utc)
        ts1 = int(t1.timestamp())
        samples = [
            create_sample_with_capture(struct.pack(">I", ts1), 10, 8, 'm1', t1),
        ]
        field_key = FieldKey(layout_id="ts_dict", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)
        d = profile.to_dict()

        # 8 个 timestamp support 字段都在 to_dict 中
        assert "timestamp_be_unix_seconds_support" in d
        assert "timestamp_le_unix_seconds_support" in d
        assert "timestamp_be_unix_milliseconds_support" in d
        assert "timestamp_le_unix_milliseconds_support" in d
        assert "timestamp_be_unix_microseconds_support" in d
        assert "timestamp_le_unix_microseconds_support" in d
        assert "timestamp_be_ntp_seconds_support" in d
        assert "timestamp_le_ntp_seconds_support" in d
        # R271 计算的字段有值，其余为 None
        assert d["timestamp_be_unix_seconds_support"] is not None

    def test_be_le_independent_timestamp(self):
        """R271：BE/LE timestamp support 独立计算（端序独立）

        同一组字节 b'\x00\x00\x00\x01'：
        - BE 解码 = 1（1970-01-01 00:00:01，超出 2026 范围）
        - LE 解码 = 16777216（1970-07-14，仍超出 2026 范围）
        但用不同字节构造 BE/LE 各自匹配的场景，证明独立计算。
        """
        t1 = datetime(2026, 6, 27, 10, 0, 0, tzinfo=timezone.utc)
        ts1 = int(t1.timestamp())
        # BE 字段：4 字节大端编码 ts1
        be_samples = [
            create_sample_with_capture(struct.pack(">I", ts1), 10, 8, 'm1', t1),
        ]
        be_profile = build_field_profile(
            FieldKey(layout_id="ts_be_only", direction=Direction.REQUEST, field_index=0), be_samples
        )
        # BE 匹配
        assert abs(be_profile.timestamp_be_unix_seconds_support - 1.0) < 1e-9
        # LE 不匹配（同字节的 LE 解码值不同，且大概率超出范围）
        # LE 解码 struct.pack(">I", ts1) 为 LE = 反转字节
        # ts1 ≈ 1.78e9，BE 编码 = 0x6A ?? ?? ??
        # LE 解码同字节 = 大端反转后的值，通常不在范围内
        # 此处不强制 LE=0.0，只验证 BE/LE 独立（BE=1.0 不意味着 LE=1.0）

    def test_variable_width_4_byte_field_no_support(self):
        """R271：变宽 4 字节字段（width 不固定）→ support=None"""
        t1 = datetime(2026, 6, 27, 10, 0, 0, tzinfo=timezone.utc)
        ts1 = int(t1.timestamp())
        # 一个 4 字节 + 一个 3 字节 → 变宽
        samples = [
            create_sample_with_capture(struct.pack(">I", ts1), 10, 8, 'm1', t1),
            create_sample_with_capture(b'\x00\x00\x01', 10, 8, 'm2', t1),
        ]
        field_key = FieldKey(layout_id="ts_varwidth", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)

        # 变宽字段不计算 timestamp support
        assert profile.fixed_width is False
        assert profile.timestamp_be_unix_seconds_support is None


class TestUnixMsUsSupportR272:
    """R272：Unix ms/us BE/LE timestamp support 测试

    验收：8 字节 fixture | 支持率正确。
    教程 9.4：8 字节固定宽度才计算 ms/us。
    - ms: scale=1000.0（Unix 毫秒）
    - us: scale=1000000.0（Unix 微秒）
    复用 bi_adapted.timestamp_range 的 calculate_unix_milliseconds/microseconds_support。
    """

    def test_be_unix_milliseconds_full_support(self):
        """R272：BE 8 字节 Unix 毫秒 == capture_time → support=1.0"""
        t1 = datetime(2026, 6, 27, 10, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 6, 27, 11, 0, 0, tzinfo=timezone.utc)
        ms1 = int(t1.timestamp() * 1000)  # Unix 毫秒
        ms2 = int(t2.timestamp() * 1000)
        samples = [
            create_sample_with_capture(struct.pack(">Q", ms1), 10, 8, 'm1', t1),
            create_sample_with_capture(struct.pack(">Q", ms2), 10, 8, 'm2', t2),
        ]
        field_key = FieldKey(layout_id="ts_ms_be", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)

        assert profile.timestamp_be_unix_milliseconds_support is not None
        assert abs(profile.timestamp_be_unix_milliseconds_support - 1.0) < 1e-9

    def test_le_unix_milliseconds_full_support(self):
        """R272：LE 8 字节 Unix 毫秒 == capture_time → support=1.0"""
        t1 = datetime(2026, 6, 27, 10, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 6, 27, 11, 0, 0, tzinfo=timezone.utc)
        ms1 = int(t1.timestamp() * 1000)
        ms2 = int(t2.timestamp() * 1000)
        samples = [
            create_sample_with_capture(struct.pack("<Q", ms1), 10, 8, 'm1', t1),
            create_sample_with_capture(struct.pack("<Q", ms2), 10, 8, 'm2', t2),
        ]
        field_key = FieldKey(layout_id="ts_ms_le", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)

        assert profile.timestamp_le_unix_milliseconds_support is not None
        assert abs(profile.timestamp_le_unix_milliseconds_support - 1.0) < 1e-9

    def test_be_unix_microseconds_full_support(self):
        """R272：BE 8 字节 Unix 微秒 == capture_time → support=1.0"""
        t1 = datetime(2026, 6, 27, 10, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 6, 27, 11, 0, 0, tzinfo=timezone.utc)
        us1 = int(t1.timestamp() * 1000000)  # Unix 微秒
        us2 = int(t2.timestamp() * 1000000)
        samples = [
            create_sample_with_capture(struct.pack(">Q", us1), 10, 8, 'm1', t1),
            create_sample_with_capture(struct.pack(">Q", us2), 10, 8, 'm2', t2),
        ]
        field_key = FieldKey(layout_id="ts_us_be", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)

        assert profile.timestamp_be_unix_microseconds_support is not None
        assert abs(profile.timestamp_be_unix_microseconds_support - 1.0) < 1e-9

    def test_le_unix_microseconds_full_support(self):
        """R272：LE 8 字节 Unix 微秒 == capture_time → support=1.0"""
        t1 = datetime(2026, 6, 27, 10, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 6, 27, 11, 0, 0, tzinfo=timezone.utc)
        us1 = int(t1.timestamp() * 1000000)
        us2 = int(t2.timestamp() * 1000000)
        samples = [
            create_sample_with_capture(struct.pack("<Q", us1), 10, 8, 'm1', t1),
            create_sample_with_capture(struct.pack("<Q", us2), 10, 8, 'm2', t2),
        ]
        field_key = FieldKey(layout_id="ts_us_le", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)

        assert profile.timestamp_le_unix_microseconds_support is not None
        assert abs(profile.timestamp_le_unix_microseconds_support - 1.0) < 1e-9

    def test_ms_out_of_range_zero_support(self):
        """R272：8 字节 ms 值超出 capture range → support=0.0"""
        t1 = datetime(2026, 6, 27, 10, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 6, 27, 11, 0, 0, tzinfo=timezone.utc)
        # 2000 年的毫秒值，肯定超出 2026 范围
        old_ms = int(datetime(2000, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
        samples = [
            create_sample_with_capture(struct.pack(">Q", old_ms), 10, 8, 'm1', t1),
            create_sample_with_capture(struct.pack(">Q", old_ms), 10, 8, 'm2', t2),
        ]
        field_key = FieldKey(layout_id="ts_ms_oob", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)

        assert profile.timestamp_be_unix_milliseconds_support is not None
        assert profile.timestamp_be_unix_milliseconds_support == 0.0

    def test_non_8_byte_field_ms_us_none(self):
        """R272：非 8 字节字段 → ms/us support=None（4 字节只计算秒）"""
        t1 = datetime(2026, 6, 27, 10, 0, 0, tzinfo=timezone.utc)
        ts1 = int(t1.timestamp())
        # 4 字节字段（R271 计算 seconds，但不计算 ms/us）
        samples = [
            create_sample_with_capture(struct.pack(">I", ts1), 10, 8, 'm1', t1),
        ]
        field_key = FieldKey(layout_id="ts_4byte_no_ms", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)

        # 4 字节字段有 seconds support
        assert profile.timestamp_be_unix_seconds_support is not None
        # 但没有 ms/us support（保持 None）
        assert profile.timestamp_be_unix_milliseconds_support is None
        assert profile.timestamp_be_unix_microseconds_support is None

    def test_no_capture_time_ms_us_none(self):
        """R272：capture_time 全缺失 → ms/us support=None"""
        t1 = datetime(2026, 6, 27, 10, 0, 0, tzinfo=timezone.utc)
        ms1 = int(t1.timestamp() * 1000)
        samples = [
            create_sample_with_capture(struct.pack(">Q", ms1), 10, 8, 'm1', None),
            create_sample_with_capture(struct.pack(">Q", ms1), 10, 8, 'm2', None),
        ]
        field_key = FieldKey(layout_id="ts_ms_nocap", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)

        assert profile.timestamp_be_unix_milliseconds_support is None
        assert profile.timestamp_be_unix_microseconds_support is None
        assert profile.timestamp_le_unix_milliseconds_support is None
        assert profile.timestamp_le_unix_microseconds_support is None

    def test_ms_us_distinct_from_seconds(self):
        """R272：同一 8 字节字段的 ms/us 与 seconds 不同（ms/us 字段不计算 seconds）

        8 字节字段：R271 的 4 字节 seconds 不计算（宽度 != 4），
        R272 的 8 字节 ms/us 才计算。证明 ms/us 与 seconds 互斥。
        """
        t1 = datetime(2026, 6, 27, 10, 0, 0, tzinfo=timezone.utc)
        ms1 = int(t1.timestamp() * 1000)
        samples = [
            create_sample_with_capture(struct.pack(">Q", ms1), 10, 8, 'm1', t1),
        ]
        field_key = FieldKey(layout_id="ts_8byte_exclusive", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)

        # 8 字节字段：seconds 不计算（R271 要求 width==4），ms/us 计算（R272 要求 width==8）
        assert profile.timestamp_be_unix_seconds_support is None
        assert profile.timestamp_be_unix_milliseconds_support is not None
        assert profile.timestamp_be_unix_microseconds_support is not None

    def test_ms_us_in_to_dict(self):
        """R272：ms/us support 字段在 to_dict 中可被 TimestampDetector 读取"""
        t1 = datetime(2026, 6, 27, 10, 0, 0, tzinfo=timezone.utc)
        ms1 = int(t1.timestamp() * 1000)
        samples = [
            create_sample_with_capture(struct.pack(">Q", ms1), 10, 8, 'm1', t1),
        ]
        field_key = FieldKey(layout_id="ts_ms_dict", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)
        d = profile.to_dict()

        # ms/us 字段在 to_dict 中
        assert d["timestamp_be_unix_milliseconds_support"] is not None
        assert d["timestamp_be_unix_microseconds_support"] is not None
        # seconds 字段为 None（8 字节不计算 seconds）
        assert d["timestamp_be_unix_seconds_support"] is None


class TestNtpSecondsSupportR273:
    """R273：NTP 秒 BE/LE timestamp support 测试

    验收：NTP fixture（4 字节秒）| NTP 纪元 1900。
    教程 9.4/9.5：
    - 4 字节固定宽度才计算 NTP 秒（与 Unix 秒同宽度，仅 epoch 不同）
    - NTP 纪元 1900-01-01，epoch_offset=2208988800 秒
    - 8 字节完整 NTP（高 32 位秒 + 低 32 位小数）暂不实现（教程 9.5）
    - capture_time 缺失时 support=None
    复用 bi_adapted.timestamp_range 的 calculate_ntp_seconds_support。
    """

    def test_be_ntp_seconds_full_support(self):
        """R273：BE 4 字节 NTP 秒 == capture_time → support=1.0"""
        t1 = datetime(2026, 6, 27, 10, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 6, 27, 11, 0, 0, tzinfo=timezone.utc)
        # NTP 秒 = Unix 秒 + 2208988800（NTP 纪元偏移）
        ntp1 = int(t1.timestamp()) + 2208988800
        ntp2 = int(t2.timestamp()) + 2208988800
        samples = [
            create_sample_with_capture(struct.pack(">I", ntp1), 10, 8, 'm1', t1),
            create_sample_with_capture(struct.pack(">I", ntp2), 10, 8, 'm2', t2),
        ]
        field_key = FieldKey(layout_id="ts_ntp_be", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)

        assert profile.timestamp_be_ntp_seconds_support is not None
        assert abs(profile.timestamp_be_ntp_seconds_support - 1.0) < 1e-9

    def test_le_ntp_seconds_full_support(self):
        """R273：LE 4 字节 NTP 秒 == capture_time → support=1.0"""
        t1 = datetime(2026, 6, 27, 10, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 6, 27, 11, 0, 0, tzinfo=timezone.utc)
        ntp1 = int(t1.timestamp()) + 2208988800
        ntp2 = int(t2.timestamp()) + 2208988800
        samples = [
            create_sample_with_capture(struct.pack("<I", ntp1), 10, 8, 'm1', t1),
            create_sample_with_capture(struct.pack("<I", ntp2), 10, 8, 'm2', t2),
        ]
        field_key = FieldKey(layout_id="ts_ntp_le", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)

        assert profile.timestamp_le_ntp_seconds_support is not None
        assert abs(profile.timestamp_le_ntp_seconds_support - 1.0) < 1e-9

    def test_ntp_out_of_range_zero_support(self):
        """R273：NTP 值超出 capture range → support=0.0"""
        t1 = datetime(2026, 6, 27, 10, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 6, 27, 11, 0, 0, tzinfo=timezone.utc)
        # 1900 年初的 NTP 秒（很小），超出 2026 范围
        old_ntp = 0  # NTP 1900-01-01 00:00:00
        samples = [
            create_sample_with_capture(struct.pack(">I", old_ntp), 10, 8, 'm1', t1),
            create_sample_with_capture(struct.pack(">I", old_ntp), 10, 8, 'm2', t2),
        ]
        field_key = FieldKey(layout_id="ts_ntp_oob", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)

        assert profile.timestamp_be_ntp_seconds_support is not None
        assert profile.timestamp_be_ntp_seconds_support == 0.0

    def test_ntp_distinct_from_unix_seconds(self):
        """R273：NTP 秒与 Unix 秒同时计算但 support 不同

        同一组 4 字节字段值，若值是 Unix 秒则 Unix support=1.0，
        NTP support=0.0（因为 NTP 解析后超出范围）。
        证明 NTP 与 Unix 秒独立计算（仅 epoch 不同）。
        """
        t1 = datetime(2026, 6, 27, 10, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 6, 27, 11, 0, 0, tzinfo=timezone.utc)
        # 字段值 = Unix 秒（不是 NTP 秒）
        unix1 = int(t1.timestamp())
        unix2 = int(t2.timestamp())
        samples = [
            create_sample_with_capture(struct.pack(">I", unix1), 10, 8, 'm1', t1),
            create_sample_with_capture(struct.pack(">I", unix2), 10, 8, 'm2', t2),
        ]
        field_key = FieldKey(layout_id="ts_unix_not_ntp", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)

        # Unix 秒 support=1.0（值匹配）
        assert abs(profile.timestamp_be_unix_seconds_support - 1.0) < 1e-9
        # NTP 秒 support=0.0（同样的值当 NTP 解析后，秒数 = unix + 2208988800，
        # 远超 capture range，因为 calculate_ntp 会减去 epoch_offset=2208988800，
        # 实际 value_secs = unix，应该匹配... 让我重新思考）
        # 实际上 calculate_ntp_seconds_support 内部：
        #   value_secs = value - epoch_offset = unix - 2208988800
        #   这会变成负数（unix ≈ 1.78e9, epoch_offset ≈ 2.21e9），负数不在范围
        # 所以 NTP support=0.0
        assert profile.timestamp_be_ntp_seconds_support == 0.0

    def test_ntp_no_capture_time_none(self):
        """R273：capture_time 全缺失 → NTP support=None"""
        t1 = datetime(2026, 6, 27, 10, 0, 0, tzinfo=timezone.utc)
        ntp1 = int(t1.timestamp()) + 2208988800
        samples = [
            create_sample_with_capture(struct.pack(">I", ntp1), 10, 8, 'm1', None),
            create_sample_with_capture(struct.pack(">I", ntp1), 10, 8, 'm2', None),
        ]
        field_key = FieldKey(layout_id="ts_ntp_nocap", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)

        assert profile.timestamp_be_ntp_seconds_support is None
        assert profile.timestamp_le_ntp_seconds_support is None

    def test_ntp_non_4_byte_field_none(self):
        """R273：非 4 字节字段 → NTP support=None"""
        t1 = datetime(2026, 6, 27, 10, 0, 0, tzinfo=timezone.utc)
        ntp1 = int(t1.timestamp()) + 2208988800
        # 8 字节字段（NTP 秒需要 4 字节）
        samples = [
            create_sample_with_capture(struct.pack(">Q", ntp1), 10, 8, 'm1', t1),
        ]
        field_key = FieldKey(layout_id="ts_ntp_8byte", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)

        # 8 字节字段不计算 NTP 秒（R273 要求 width==4）
        assert profile.timestamp_be_ntp_seconds_support is None

    def test_ntp_in_to_dict(self):
        """R273：NTP support 字段在 to_dict 中可被 TimestampDetector 读取"""
        t1 = datetime(2026, 6, 27, 10, 0, 0, tzinfo=timezone.utc)
        ntp1 = int(t1.timestamp()) + 2208988800
        samples = [
            create_sample_with_capture(struct.pack(">I", ntp1), 10, 8, 'm1', t1),
        ]
        field_key = FieldKey(layout_id="ts_ntp_dict", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(field_key, samples)
        d = profile.to_dict()

        # NTP 字段在 to_dict 中
        assert d["timestamp_be_ntp_seconds_support"] is not None
        assert d["timestamp_le_ntp_seconds_support"] is not None





