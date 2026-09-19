"""R073: Pearson 相关系数测试"""

from semantic_detector.profiling.numeric import compute_pearson_correlation


class TestComputePearsonCorrelation:
    def test_perfect_positive_correlation(self):
        """完全正相关"""
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [2.0, 4.0, 6.0, 8.0, 10.0]
        result = compute_pearson_correlation(x, y)
        assert result is not None
        assert abs(result - 1.0) < 1e-9
    
    def test_perfect_negative_correlation(self):
        """完全负相关"""
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [10.0, 8.0, 6.0, 4.0, 2.0]
        result = compute_pearson_correlation(x, y)
        assert result is not None
        assert abs(result - (-1.0)) < 1e-9
    
    def test_no_correlation(self):
        """无相关"""
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [2.0, 2.0, 2.0, 2.0, 2.0]
        result = compute_pearson_correlation(x, y)
        assert result is None
    
    def test_constant_x_returns_none(self):
        """常量 x 序列返回 None"""
        x = [5.0, 5.0, 5.0, 5.0]
        y = [1.0, 2.0, 3.0, 4.0]
        result = compute_pearson_correlation(x, y)
        assert result is None
    
    def test_constant_y_returns_none(self):
        """常量 y 序列返回 None"""
        x = [1.0, 2.0, 3.0, 4.0]
        y = [5.0, 5.0, 5.0, 5.0]
        result = compute_pearson_correlation(x, y)
        assert result is None
    
    def test_both_constant_returns_none(self):
        """两个都是常量序列返回 None"""
        x = [5.0, 5.0, 5.0, 5.0]
        y = [3.0, 3.0, 3.0, 3.0]
        result = compute_pearson_correlation(x, y)
        assert result is None
    
    def test_partial_positive_correlation(self):
        """部分正相关"""
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [1.0, 2.0, 2.5, 4.0, 5.0]
        result = compute_pearson_correlation(x, y)
        assert result is not None
        assert 0.9 < result < 1.0
    
    def test_partial_negative_correlation(self):
        """部分负相关"""
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [5.0, 4.0, 3.5, 2.0, 1.0]
        result = compute_pearson_correlation(x, y)
        assert result is not None
        assert -1.0 < result < -0.9
    
    def test_empty_x_returns_none(self):
        """空 x 序列返回 None"""
        result = compute_pearson_correlation([], [1.0, 2.0])
        assert result is None
    
    def test_empty_y_returns_none(self):
        """空 y 序列返回 None"""
        result = compute_pearson_correlation([1.0, 2.0], [])
        assert result is None
    
    def test_mismatched_lengths_returns_none(self):
        """长度不匹配返回 None"""
        x = [1.0, 2.0, 3.0]
        y = [1.0, 2.0]
        result = compute_pearson_correlation(x, y)
        assert result is None
    
    def test_single_element_returns_none(self):
        """单元素序列返回 None"""
        x = [1.0]
        y = [2.0]
        result = compute_pearson_correlation(x, y)
        assert result is None
    
    def test_two_elements(self):
        """两个元素的相关系数"""
        x = [1.0, 2.0]
        y = [3.0, 6.0]
        result = compute_pearson_correlation(x, y)
        assert result is not None
        assert abs(result - 1.0) < 1e-9
    
    def test_with_negative_values(self):
        """包含负值"""
        x = [-2.0, -1.0, 0.0, 1.0, 2.0]
        y = [-4.0, -2.0, 0.0, 2.0, 4.0]
        result = compute_pearson_correlation(x, y)
        assert result is not None
        assert abs(result - 1.0) < 1e-9
    
    def test_integer_input(self):
        """整数输入(自动转换为 float)"""
        x = [1, 2, 3, 4, 5]
        y = [2, 4, 6, 8, 10]
        result = compute_pearson_correlation(x, y)
        assert result is not None
        assert abs(result - 1.0) < 1e-9
