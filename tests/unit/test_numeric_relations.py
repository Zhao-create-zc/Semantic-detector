"""R077+R078: 数值与消息长度/剩余字节数相关性测试"""

from semantic_detector.profiling.numeric import (
    compute_numeric_message_length_correlation,
    compute_numeric_remaining_bytes_correlation,
)


class TestComputeNumericMessageLengthCorrelation:
    """R077: 数值与消息长度相关性测试"""
    
    def test_perfect_positive_correlation(self):
        """完全正相关：数值等于消息长度"""
        numeric_values = [10, 20, 30, 40, 50]
        message_lengths = [10, 20, 30, 40, 50]
        result = compute_numeric_message_length_correlation(numeric_values, message_lengths)
        assert result is not None
        assert abs(result - 1.0) < 1e-9
    
    def test_perfect_negative_correlation(self):
        """完全负相关"""
        numeric_values = [10, 20, 30, 40, 50]
        message_lengths = [50, 40, 30, 20, 10]
        result = compute_numeric_message_length_correlation(numeric_values, message_lengths)
        assert result is not None
        assert abs(result - (-1.0)) < 1e-9
    
    def test_no_correlation(self):
        """无相关：消息长度为常量"""
        numeric_values = [10, 20, 30, 40, 50]
        message_lengths = [100, 100, 100, 100, 100]
        result = compute_numeric_message_length_correlation(numeric_values, message_lengths)
        assert result is None
    
    def test_constant_numeric_returns_none(self):
        """数值为常量返回 None"""
        numeric_values = [50, 50, 50, 50]
        message_lengths = [10, 20, 30, 40]
        result = compute_numeric_message_length_correlation(numeric_values, message_lengths)
        assert result is None
    
    def test_partial_correlation(self):
        """部分相关"""
        numeric_values = [10, 20, 30, 40, 50]
        message_lengths = [10, 20, 25, 40, 50]
        result = compute_numeric_message_length_correlation(numeric_values, message_lengths)
        assert result is not None
        assert 0.9 < result < 1.0
    
    def test_empty_returns_none(self):
        """空序列返回 None"""
        result = compute_numeric_message_length_correlation([], [])
        assert result is None
    
    def test_mismatched_lengths_returns_none(self):
        """长度不匹配返回 None"""
        numeric_values = [10, 20, 30]
        message_lengths = [10, 20]
        result = compute_numeric_message_length_correlation(numeric_values, message_lengths)
        assert result is None
    
    def test_linear_relationship(self):
        """线性关系：数值 = 2 * 消息长度"""
        numeric_values = [20, 40, 60, 80, 100]
        message_lengths = [10, 20, 30, 40, 50]
        result = compute_numeric_message_length_correlation(numeric_values, message_lengths)
        assert result is not None
        assert abs(result - 1.0) < 1e-9


class TestComputeNumericRemainingBytesCorrelation:
    """R078: 数值与剩余字节数相关性测试"""
    
    def test_perfect_positive_correlation(self):
        """完全正相关：数值等于剩余字节数"""
        numeric_values = [10, 20, 30, 40, 50]
        remaining_bytes = [10, 20, 30, 40, 50]
        result = compute_numeric_remaining_bytes_correlation(numeric_values, remaining_bytes)
        assert result is not None
        assert abs(result - 1.0) < 1e-9
    
    def test_perfect_negative_correlation(self):
        """完全负相关"""
        numeric_values = [10, 20, 30, 40, 50]
        remaining_bytes = [50, 40, 30, 20, 10]
        result = compute_numeric_remaining_bytes_correlation(numeric_values, remaining_bytes)
        assert result is not None
        assert abs(result - (-1.0)) < 1e-9
    
    def test_no_correlation(self):
        """无相关：剩余字节数为常量"""
        numeric_values = [10, 20, 30, 40, 50]
        remaining_bytes = [100, 100, 100, 100, 100]
        result = compute_numeric_remaining_bytes_correlation(numeric_values, remaining_bytes)
        assert result is None
    
    def test_constant_numeric_returns_none(self):
        """数值为常量返回 None"""
        numeric_values = [50, 50, 50, 50]
        remaining_bytes = [10, 20, 30, 40]
        result = compute_numeric_remaining_bytes_correlation(numeric_values, remaining_bytes)
        assert result is None
    
    def test_partial_correlation(self):
        """部分相关"""
        numeric_values = [10, 20, 30, 40, 50]
        remaining_bytes = [10, 20, 25, 40, 50]
        result = compute_numeric_remaining_bytes_correlation(numeric_values, remaining_bytes)
        assert result is not None
        assert 0.9 < result < 1.0
    
    def test_empty_returns_none(self):
        """空序列返回 None"""
        result = compute_numeric_remaining_bytes_correlation([], [])
        assert result is None
    
    def test_mismatched_lengths_returns_none(self):
        """长度不匹配返回 None"""
        numeric_values = [10, 20, 30]
        remaining_bytes = [10, 20]
        result = compute_numeric_remaining_bytes_correlation(numeric_values, remaining_bytes)
        assert result is None
    
    def test_modbus_style(self):
        """Modbus 风格：数值等于剩余字节数"""
        numeric_values = [5, 10, 15, 20, 25]
        remaining_bytes = [5, 10, 15, 20, 25]
        result = compute_numeric_remaining_bytes_correlation(numeric_values, remaining_bytes)
        assert result is not None
        assert abs(result - 1.0) < 1e-9
