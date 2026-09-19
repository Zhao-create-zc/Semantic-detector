"""测试长度关系检测"""

import pytest
from semantic_detector.bi_adapted.length_relations import (
    LengthCandidate,
    extract_length_candidates_be,
    extract_length_candidates_le,
    extract_length_candidates,
    calculate_message_length_support,
    calculate_remaining_bytes_support,
    calculate_offset_message_length_support,
    calculate_offset_remaining_bytes_support,
)


class TestLengthCandidatesBE:
    """测试大端长度候选值提取"""
    
    def test_single_byte(self):
        """单字节大端解码"""
        field_bytes = bytes([0x12])
        candidates = extract_length_candidates_be(field_bytes)
        
        assert len(candidates) == 1
        assert candidates[0].value == 0x12
        assert candidates[0].byte_width == 1
        assert candidates[0].endian == 'be'
    
    def test_two_bytes(self):
        """双字节大端解码"""
        field_bytes = bytes([0x12, 0x34])
        candidates = extract_length_candidates_be(field_bytes)
        
        assert len(candidates) == 2
        
        # 1 字节
        assert candidates[0].value == 0x12
        assert candidates[0].byte_width == 1
        
        # 2 字节
        assert candidates[1].value == 0x1234
        assert candidates[1].byte_width == 2
    
    def test_three_bytes(self):
        """三字节大端解码"""
        field_bytes = bytes([0x12, 0x34, 0x56])
        candidates = extract_length_candidates_be(field_bytes)
        
        assert len(candidates) == 3
        
        assert candidates[0].value == 0x12
        assert candidates[1].value == 0x1234
        assert candidates[2].value == 0x123456
    
    def test_four_bytes(self):
        """四字节大端解码"""
        field_bytes = bytes([0x12, 0x34, 0x56, 0x78])
        candidates = extract_length_candidates_be(field_bytes)
        
        assert len(candidates) == 4
        
        assert candidates[0].value == 0x12
        assert candidates[1].value == 0x1234
        assert candidates[2].value == 0x123456
        assert candidates[3].value == 0x12345678
    
    def test_max_width_limit(self):
        """最大宽度限制"""
        field_bytes = bytes([0x12, 0x34, 0x56, 0x78, 0x9A])
        candidates = extract_length_candidates_be(field_bytes, max_width=2)
        
        # 只提取 1~2 字节
        assert len(candidates) == 2
        assert candidates[0].byte_width == 1
        assert candidates[1].byte_width == 2


class TestLengthCandidatesLE:
    """测试小端长度候选值提取"""
    
    def test_single_byte(self):
        """单字节小端解码"""
        field_bytes = bytes([0x12])
        candidates = extract_length_candidates_le(field_bytes)
        
        assert len(candidates) == 1
        assert candidates[0].value == 0x12
        assert candidates[0].byte_width == 1
        assert candidates[0].endian == 'le'
    
    def test_two_bytes(self):
        """双字节小端解码"""
        field_bytes = bytes([0x12, 0x34])
        candidates = extract_length_candidates_le(field_bytes)
        
        assert len(candidates) == 2
        
        # 1 字节
        assert candidates[0].value == 0x12
        assert candidates[0].byte_width == 1
        
        # 2 字节（小端：0x3412）
        assert candidates[1].value == 0x3412
        assert candidates[1].byte_width == 2
    
    def test_three_bytes(self):
        """三字节小端解码"""
        field_bytes = bytes([0x12, 0x34, 0x56])
        candidates = extract_length_candidates_le(field_bytes)
        
        assert len(candidates) == 3
        
        assert candidates[0].value == 0x12
        assert candidates[1].value == 0x3412
        assert candidates[2].value == 0x563412
    
    def test_four_bytes(self):
        """四字节小端解码"""
        field_bytes = bytes([0x12, 0x34, 0x56, 0x78])
        candidates = extract_length_candidates_le(field_bytes)
        
        assert len(candidates) == 4
        
        assert candidates[0].value == 0x12
        assert candidates[1].value == 0x3412
        assert candidates[2].value == 0x563412
        assert candidates[3].value == 0x78563412


class TestLengthCandidatesBoth:
    """测试双端长度候选值提取"""
    
    def test_both_endian(self):
        """同时提取大端和小端"""
        field_bytes = bytes([0x12, 0x34])
        candidates = extract_length_candidates(field_bytes, endian='both')
        
        # 2 个大端 + 2 个小端 = 4 个候选
        assert len(candidates) == 4
        
        # 大端
        assert candidates[0].endian == 'be'
        assert candidates[1].endian == 'be'
        
        # 小端
        assert candidates[2].endian == 'le'
        assert candidates[3].endian == 'le'
    
    def test_be_only(self):
        """只提取大端"""
        field_bytes = bytes([0x12, 0x34])
        candidates = extract_length_candidates(field_bytes, endian='be')
        
        assert len(candidates) == 2
        assert all(c.endian == 'be' for c in candidates)
    
    def test_le_only(self):
        """只提取小端"""
        field_bytes = bytes([0x12, 0x34])
        candidates = extract_length_candidates(field_bytes, endian='le')
        
        assert len(candidates) == 2
        assert all(c.endian == 'le' for c in candidates)


class TestEdgeCases:
    """测试边缘情况"""
    
    def test_empty_bytes(self):
        """空字节"""
        field_bytes = bytes()
        candidates = extract_length_candidates_be(field_bytes)
        
        assert len(candidates) == 0
    
    def test_zero_value(self):
        """零值"""
        field_bytes = bytes([0x00, 0x00])
        candidates = extract_length_candidates_be(field_bytes)
        
        assert len(candidates) == 2
        assert candidates[0].value == 0
        assert candidates[1].value == 0
    
    def test_max_value(self):
        """最大值"""
        field_bytes = bytes([0xFF, 0xFF, 0xFF, 0xFF])
        candidates = extract_length_candidates_be(field_bytes)
        
        assert len(candidates) == 4
        assert candidates[0].value == 0xFF
        assert candidates[1].value == 0xFFFF
        assert candidates[2].value == 0xFFFFFF
        assert candidates[3].value == 0xFFFFFFFF


class TestMessageLengthSupport:
    """测试 value == message_length 支持率"""
    
    def test_full_support(self):
        """全支持：所有样本都满足"""
        field_values = [100, 100, 100, 100, 100]
        message_lengths = [100, 100, 100, 100, 100]
        
        support = calculate_message_length_support(field_values, message_lengths)
        
        assert support == 1.0
    
    def test_partial_support(self):
        """部分支持：部分样本满足"""
        field_values = [100, 100, 100, 200, 200]
        message_lengths = [100, 100, 100, 150, 150]
        
        support = calculate_message_length_support(field_values, message_lengths)
        
        # 3/5 = 0.6
        assert support == 0.6
    
    def test_no_support(self):
        """无支持：没有样本满足"""
        field_values = [100, 100, 100]
        message_lengths = [200, 200, 200]
        
        support = calculate_message_length_support(field_values, message_lengths)
        
        assert support == 0.0
    
    def test_single_match(self):
        """单个匹配"""
        field_values = [100, 200, 300]
        message_lengths = [100, 250, 350]
        
        support = calculate_message_length_support(field_values, message_lengths)
        
        # 1/3
        assert support == pytest.approx(1/3)
    
    def test_empty_lists(self):
        """空列表"""
        field_values = []
        message_lengths = []
        
        support = calculate_message_length_support(field_values, message_lengths)
        
        assert support == 0.0
    
    def test_length_mismatch_raises(self):
        """长度不匹配抛出异常"""
        field_values = [100, 200]
        message_lengths = [100, 200, 300]
        
        with pytest.raises(ValueError, match="must have the same length"):
            calculate_message_length_support(field_values, message_lengths)


class TestRemainingBytesSupport:
    """测试 value == remaining_bytes 支持率"""
    
    def test_full_support(self):
        """全支持"""
        field_values = [50, 50, 50]
        remaining_bytes = [50, 50, 50]
        
        support = calculate_remaining_bytes_support(field_values, remaining_bytes)
        
        assert support == 1.0
    
    def test_partial_support(self):
        """部分支持"""
        field_values = [50, 50, 100]
        remaining_bytes = [50, 60, 100]
        
        support = calculate_remaining_bytes_support(field_values, remaining_bytes)
        
        # 2/3
        assert support == pytest.approx(2/3)
    
    def test_no_support(self):
        """无支持"""
        field_values = [50, 50, 50]
        remaining_bytes = [100, 100, 100]
        
        support = calculate_remaining_bytes_support(field_values, remaining_bytes)
        
        assert support == 0.0


class TestModbusStyleSupport:
    """测试 Modbus 风格的 remaining_bytes 支持"""
    
    def test_modbus_style_full_support(self):
        """Modbus 风格：全支持"""
        # Modbus 风格：字段值等于剩余字节数
        # 例如：字段值 5 表示后面还有 5 个字节
        field_values = [5, 10, 3, 8]
        remaining_bytes = [5, 10, 3, 8]
        
        support = calculate_remaining_bytes_support(field_values, remaining_bytes)
        
        assert support == 1.0
    
    def test_modbus_style_partial_support(self):
        """Modbus 风格：部分支持"""
        # 有些样本符合 Modbus 风格，有些不符合
        field_values = [5, 10, 3, 8]
        remaining_bytes = [5, 10, 7, 8]  # 第三个不符合
        
        support = calculate_remaining_bytes_support(field_values, remaining_bytes)
        
        # 3/4 = 0.75
        assert support == 0.75
    
    def test_modbus_style_with_offset(self):
        """Modbus 风格：带偏移"""
        # 有些协议中，字段值 + 偏移 = 剩余字节数
        # 例如：字段值 5，偏移 2，剩余字节 7
        field_values = [5, 8, 3]
        remaining_bytes = [7, 10, 5]  # 都有偏移 2
        
        # 直接比较不支持
        support = calculate_remaining_bytes_support(field_values, remaining_bytes)
        
        assert support == 0.0
    
    def test_modbus_style_variable_remaining(self):
        """Modbus 风格：变长剩余字节"""
        # 不同消息的剩余字节数不同
        field_values = [10, 20, 15, 25]
        remaining_bytes = [10, 20, 15, 25]
        
        support = calculate_remaining_bytes_support(field_values, remaining_bytes)
        
        assert support == 1.0
    
    def test_modbus_style_zero_remaining(self):
        """Modbus 风格：零剩余字节"""
        # 字段值为 0，表示没有剩余字节
        field_values = [0, 0, 0]
        remaining_bytes = [0, 0, 0]
        
        support = calculate_remaining_bytes_support(field_values, remaining_bytes)
        
        assert support == 1.0
    
    def test_modbus_style_mixed_samples(self):
        """Modbus 风格：混合样本"""
        # 混合符合和不符合的样本
        field_values = [5, 10, 3, 8, 12, 7]
        remaining_bytes = [5, 10, 7, 8, 15, 7]  # 第 3 和第 5 个不符合
        
        support = calculate_remaining_bytes_support(field_values, remaining_bytes)
        
        # 4/6 = 2/3
        assert support == pytest.approx(2/3)


class TestOffsetMessageLengthSupport:
    """测试 value + offset == message_length 支持率"""
    
    def test_fixed_offset_full_support(self):
        """固定偏移：全支持"""
        # 所有样本：value + 2 = message_length
        field_values = [10, 20, 15, 25]
        message_lengths = [12, 22, 17, 27]
        
        support, offset = calculate_offset_message_length_support(field_values, message_lengths)
        
        assert support == 1.0
        assert offset == 2
    
    def test_fixed_offset_zero(self):
        """偏移为 0（即 value == message_length）"""
        field_values = [100, 100, 100]
        message_lengths = [100, 100, 100]
        
        support, offset = calculate_offset_message_length_support(field_values, message_lengths)
        
        assert support == 1.0
        assert offset == 0
    
    def test_fixed_offset_negative(self):
        """负偏移"""
        # value - 5 = message_length
        field_values = [105, 110, 115]
        message_lengths = [100, 105, 110]
        
        support, offset = calculate_offset_message_length_support(field_values, message_lengths)
        
        assert support == 1.0
        assert offset == -5
    
    def test_non_fixed_offset(self):
        """非固定偏移：不同样本使用不同偏移"""
        field_values = [10, 20, 15]
        message_lengths = [12, 25, 17]  # 偏移分别为 2, 5, 2
        
        support, offset = calculate_offset_message_length_support(field_values, message_lengths)
        
        # 最常见偏移是 2（2/3 支持）
        assert support == pytest.approx(2/3)
        assert offset == 2
    
    def test_all_different_offsets(self):
        """所有偏移都不同"""
        field_values = [10, 20, 30]
        message_lengths = [11, 23, 35]  # 偏移分别为 1, 3, 5
        
        support, offset = calculate_offset_message_length_support(field_values, message_lengths)
        
        # 每个偏移只出现一次，支持率为 1/3
        assert support == pytest.approx(1/3)
    
    def test_empty_lists(self):
        """空列表"""
        field_values = []
        message_lengths = []
        
        support, offset = calculate_offset_message_length_support(field_values, message_lengths)
        
        assert support == 0.0
        assert offset is None
    
    def test_length_mismatch_raises(self):
        """长度不匹配抛出异常"""
        field_values = [10, 20]
        message_lengths = [12, 22, 32]
        
        with pytest.raises(ValueError, match="must have the same length"):
            calculate_offset_message_length_support(field_values, message_lengths)


class TestOffsetRemainingBytesSupport:
    """测试 value + offset == remaining_bytes 支持率"""
    
    def test_fixed_offset_full_support(self):
        """固定偏移：全支持"""
        # 所有样本：value + 3 = remaining_bytes
        field_values = [5, 10, 8, 12]
        remaining_bytes = [8, 13, 11, 15]
        
        support, offset = calculate_offset_remaining_bytes_support(field_values, remaining_bytes)
        
        assert support == 1.0
        assert offset == 3
    
    def test_fixed_offset_zero(self):
        """偏移为 0（即 value == remaining_bytes）"""
        field_values = [50, 50, 50]
        remaining_bytes = [50, 50, 50]
        
        support, offset = calculate_offset_remaining_bytes_support(field_values, remaining_bytes)
        
        assert support == 1.0
        assert offset == 0
    
    def test_fixed_offset_negative(self):
        """负偏移"""
        # value - 2 = remaining_bytes
        field_values = [52, 57, 62]
        remaining_bytes = [50, 55, 60]
        
        support, offset = calculate_offset_remaining_bytes_support(field_values, remaining_bytes)
        
        assert support == 1.0
        assert offset == -2
    
    def test_non_fixed_offset(self):
        """非固定偏移：不同样本使用不同偏移"""
        field_values = [5, 10, 8]
        remaining_bytes = [8, 16, 11]  # 偏移分别为 3, 6, 3
        
        support, offset = calculate_offset_remaining_bytes_support(field_values, remaining_bytes)
        
        # 最常见偏移是 3（2/3 支持）
        assert support == pytest.approx(2/3)
        assert offset == 3
    
    def test_all_different_offsets(self):
        """所有偏移都不同"""
        field_values = [5, 10, 15]
        remaining_bytes = [7, 14, 21]  # 偏移分别为 2, 4, 6
        
        support, offset = calculate_offset_remaining_bytes_support(field_values, remaining_bytes)
        
        # 每个偏移只出现一次，支持率为 1/3
        assert support == pytest.approx(1/3)
    
    def test_empty_lists(self):
        """空列表"""
        field_values = []
        remaining_bytes = []
        
        support, offset = calculate_offset_remaining_bytes_support(field_values, remaining_bytes)
        
        assert support == 0.0
        assert offset is None
    
    def test_length_mismatch_raises(self):
        """长度不匹配抛出异常"""
        field_values = [5, 10]
        remaining_bytes = [8, 13, 18]
        
        with pytest.raises(ValueError, match="must have the same length"):
            calculate_offset_remaining_bytes_support(field_values, remaining_bytes)
