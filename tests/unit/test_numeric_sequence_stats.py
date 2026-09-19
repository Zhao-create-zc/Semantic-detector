"""R074+R075+R076: 序列统计测试"""

from semantic_detector.profiling.numeric import (
    compute_strictly_increasing_ratio,
    compute_nondecreasing_ratio,
    compute_step_one_ratio,
)


class TestComputeStrictlyIncreasingRatio:
    def test_strictly_increasing_sequence(self):
        """严格递增序列"""
        values = [1, 2, 3, 4, 5]
        result = compute_strictly_increasing_ratio(values)
        assert result is not None
        assert result == 1.0
    
    def test_strictly_decreasing_sequence(self):
        """严格递减序列"""
        values = [5, 4, 3, 2, 1]
        result = compute_strictly_increasing_ratio(values)
        assert result is not None
        assert result == 0.0
    
    def test_constant_sequence(self):
        """常量序列"""
        values = [3, 3, 3, 3, 3]
        result = compute_strictly_increasing_ratio(values)
        assert result is not None
        assert result == 0.0
    
    def test_partially_increasing(self):
        """部分递增"""
        values = [1, 3, 2, 4, 5]
        result = compute_strictly_increasing_ratio(values)
        assert result is not None
        assert result == 0.75
    
    def test_single_increase(self):
        """只有一个递增对"""
        values = [5, 4, 3, 2, 10]
        result = compute_strictly_increasing_ratio(values)
        assert result is not None
        assert result == 0.25
    
    def test_two_elements_increasing(self):
        """两个元素递增"""
        values = [1, 2]
        result = compute_strictly_increasing_ratio(values)
        assert result is not None
        assert result == 1.0
    
    def test_two_elements_decreasing(self):
        """两个元素递减"""
        values = [2, 1]
        result = compute_strictly_increasing_ratio(values)
        assert result is not None
        assert result == 0.0
    
    def test_two_elements_equal(self):
        """两个元素相等"""
        values = [1, 1]
        result = compute_strictly_increasing_ratio(values)
        assert result is not None
        assert result == 0.0
    
    def test_single_element_returns_none(self):
        """单元素序列返回 None"""
        values = [42]
        result = compute_strictly_increasing_ratio(values)
        assert result is None
    
    def test_empty_returns_none(self):
        """空序列返回 None"""
        result = compute_strictly_increasing_ratio([])
        assert result is None
    
    def test_with_negative_values(self):
        """包含负值"""
        values = [-5, -3, -1, 1, 3]
        result = compute_strictly_increasing_ratio(values)
        assert result is not None
        assert result == 1.0
    
    def test_mixed_increasing_and_equal(self):
        """混合递增和相等"""
        values = [1, 2, 2, 3, 4]
        result = compute_strictly_increasing_ratio(values)
        assert result is not None
        assert result == 0.75


class TestComputeNondecreasingRatio:
    """R075: nondecreasing_ratio 测试"""
    
    def test_strictly_increasing_sequence(self):
        """严格递增序列"""
        values = [1, 2, 3, 4, 5]
        result = compute_nondecreasing_ratio(values)
        assert result is not None
        assert result == 1.0
    
    def test_constant_sequence(self):
        """常量序列"""
        values = [3, 3, 3, 3, 3]
        result = compute_nondecreasing_ratio(values)
        assert result is not None
        assert result == 1.0
    
    def test_strictly_decreasing_sequence(self):
        """严格递减序列"""
        values = [5, 4, 3, 2, 1]
        result = compute_nondecreasing_ratio(values)
        assert result is not None
        assert result == 0.0
    
    def test_mixed_increasing_and_equal(self):
        """混合递增和相等"""
        values = [1, 2, 2, 3, 4]
        result = compute_nondecreasing_ratio(values)
        assert result is not None
        assert result == 1.0
    
    def test_partially_nondecreasing(self):
        """部分非递减"""
        values = [1, 3, 2, 4, 5]
        result = compute_nondecreasing_ratio(values)
        assert result is not None
        assert result == 0.75
    
    def test_two_elements_equal(self):
        """两个元素相等"""
        values = [1, 1]
        result = compute_nondecreasing_ratio(values)
        assert result is not None
        assert result == 1.0
    
    def test_single_element_returns_none(self):
        """单元素序列返回 None"""
        values = [42]
        result = compute_nondecreasing_ratio(values)
        assert result is None
    
    def test_empty_returns_none(self):
        """空序列返回 None"""
        result = compute_nondecreasing_ratio([])
        assert result is None


class TestComputeStepOneRatio:
    """R076: step_one_ratio 测试"""
    
    def test_step_one_sequence(self):
        """步长为 1 的序列"""
        values = [1, 2, 3, 4, 5]
        result = compute_step_one_ratio(values)
        assert result is not None
        assert result == 1.0
    
    def test_constant_sequence(self):
        """常量序列"""
        values = [3, 3, 3, 3, 3]
        result = compute_step_one_ratio(values)
        assert result is not None
        assert result == 0.0
    
    def test_step_two_sequence(self):
        """步长为 2 的序列"""
        values = [1, 3, 5, 7, 9]
        result = compute_step_one_ratio(values)
        assert result is not None
        assert result == 0.0
    
    def test_partially_step_one(self):
        """部分步长为 1"""
        values = [1, 2, 5, 6, 7]
        result = compute_step_one_ratio(values)
        assert result is not None
        assert result == 0.75
    
    def test_decreasing_sequence(self):
        """递减序列"""
        values = [5, 4, 3, 2, 1]
        result = compute_step_one_ratio(values)
        assert result is not None
        assert result == 0.0
    
    def test_two_elements_step_one(self):
        """两个元素步长为 1"""
        values = [1, 2]
        result = compute_step_one_ratio(values)
        assert result is not None
        assert result == 1.0
    
    def test_two_elements_not_step_one(self):
        """两个元素步长不为 1"""
        values = [1, 3]
        result = compute_step_one_ratio(values)
        assert result is not None
        assert result == 0.0
    
    def test_single_element_returns_none(self):
        """单元素序列返回 None"""
        values = [42]
        result = compute_step_one_ratio(values)
        assert result is None
    
    def test_empty_returns_none(self):
        """空序列返回 None"""
        result = compute_step_one_ratio([])
        assert result is None
