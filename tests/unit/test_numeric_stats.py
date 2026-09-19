"""R072: numeric min/max/mean/median 统计测试"""

from semantic_detector.profiling.numeric import (
    compute_numeric_min,
    compute_numeric_max,
    compute_numeric_mean,
    compute_numeric_median,
    compute_numeric_stats,
)


class TestComputeNumericMin:
    def test_basic_sequence(self):
        """已知整数序列的最小值"""
        values = [10, 20, 30, 40, 50]
        assert compute_numeric_min(values) == 10
    
    def test_unsorted_sequence(self):
        """乱序序列的最小值"""
        values = [50, 10, 40, 20, 30]
        assert compute_numeric_min(values) == 10
    
    def test_single_value(self):
        """单元素序列"""
        values = [42]
        assert compute_numeric_min(values) == 42
    
    def test_with_negatives(self):
        """包含负数的序列"""
        values = [-10, 0, 10, 20]
        assert compute_numeric_min(values) == -10
    
    def test_all_same(self):
        """所有值相同"""
        values = [5, 5, 5, 5]
        assert compute_numeric_min(values) == 5
    
    def test_empty_returns_none(self):
        """空序列返回 None"""
        assert compute_numeric_min([]) is None


class TestComputeNumericMax:
    def test_basic_sequence(self):
        """已知整数序列的最大值"""
        values = [10, 20, 30, 40, 50]
        assert compute_numeric_max(values) == 50
    
    def test_unsorted_sequence(self):
        """乱序序列的最大值"""
        values = [50, 10, 40, 20, 30]
        assert compute_numeric_max(values) == 50
    
    def test_single_value(self):
        """单元素序列"""
        values = [42]
        assert compute_numeric_max(values) == 42
    
    def test_with_negatives(self):
        """包含负数的序列"""
        values = [-10, 0, 10, 20]
        assert compute_numeric_max(values) == 20
    
    def test_all_same(self):
        """所有值相同"""
        values = [5, 5, 5, 5]
        assert compute_numeric_max(values) == 5
    
    def test_empty_returns_none(self):
        """空序列返回 None"""
        assert compute_numeric_max([]) is None


class TestComputeNumericMean:
    def test_basic_sequence(self):
        """已知整数序列的平均值"""
        values = [10, 20, 30, 40, 50]
        assert compute_numeric_mean(values) == 30.0
    
    def test_unsorted_sequence(self):
        """乱序序列的平均值"""
        values = [50, 10, 40, 20, 30]
        assert compute_numeric_mean(values) == 30.0
    
    def test_single_value(self):
        """单元素序列"""
        values = [42]
        assert compute_numeric_mean(values) == 42.0
    
    def test_with_negatives(self):
        """包含负数的序列"""
        values = [-10, 0, 10]
        assert compute_numeric_mean(values) == 0.0
    
    def test_fractional_result(self):
        """结果为分数"""
        values = [1, 2, 3, 4]
        assert compute_numeric_mean(values) == 2.5
    
    def test_empty_returns_none(self):
        """空序列返回 None"""
        assert compute_numeric_mean([]) is None


class TestComputeNumericMedian:
    def test_odd_count(self):
        """奇数个元素的中位数"""
        values = [10, 20, 30, 40, 50]
        assert compute_numeric_median(values) == 30.0
    
    def test_even_count(self):
        """偶数个元素的中位数"""
        values = [10, 20, 30, 40]
        assert compute_numeric_median(values) == 25.0
    
    def test_unsorted_sequence(self):
        """乱序序列的中位数"""
        values = [50, 10, 40, 20, 30]
        assert compute_numeric_median(values) == 30.0
    
    def test_single_value(self):
        """单元素序列"""
        values = [42]
        assert compute_numeric_median(values) == 42.0
    
    def test_two_values(self):
        """两个元素的中位数"""
        values = [10, 20]
        assert compute_numeric_median(values) == 15.0
    
    def test_with_negatives(self):
        """包含负数的序列"""
        values = [-10, 0, 10]
        assert compute_numeric_median(values) == 0.0
    
    def test_empty_returns_none(self):
        """空序列返回 None"""
        assert compute_numeric_median([]) is None


class TestComputeNumericStats:
    def test_basic_sequence(self):
        """已知整数序列的完整统计"""
        values = [10, 20, 30, 40, 50]
        result = compute_numeric_stats(values)
        assert result is not None
        min_val, max_val, mean_val, median_val = result
        assert min_val == 10
        assert max_val == 50
        assert mean_val == 30.0
        assert median_val == 30.0
    
    def test_even_count_sequence(self):
        """偶数个元素的完整统计"""
        values = [1, 2, 3, 4]
        result = compute_numeric_stats(values)
        assert result is not None
        min_val, max_val, mean_val, median_val = result
        assert min_val == 1
        assert max_val == 4
        assert mean_val == 2.5
        assert median_val == 2.5
    
    def test_single_value(self):
        """单元素序列"""
        values = [42]
        result = compute_numeric_stats(values)
        assert result is not None
        min_val, max_val, mean_val, median_val = result
        assert min_val == 42
        assert max_val == 42
        assert mean_val == 42.0
        assert median_val == 42.0
    
    def test_empty_returns_none(self):
        """空序列返回 None"""
        assert compute_numeric_stats([]) is None
