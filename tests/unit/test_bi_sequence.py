"""
Tests for BI-adapted sequence_heuristic functions.
"""

import pytest
from semantic_detector.bi_adapted.sequence_heuristic import (
    calculate_strictly_increasing_ratio,
    calculate_nondecreasing_ratio,
    calculate_step_one_ratio,
    detect_sequence_pattern,
)


class TestCalculateStrictlyIncreasingRatio:
    """Tests for calculate_strictly_increasing_ratio."""
    
    def test_empty_list_returns_none(self):
        """Empty list should return None."""
        result = calculate_strictly_increasing_ratio([])
        assert result is None
    
    def test_single_element_returns_none(self):
        """Single element list should return None."""
        result = calculate_strictly_increasing_ratio([42])
        assert result is None
    
    def test_two_elements_increasing(self):
        """Two increasing elements should return 1.0."""
        result = calculate_strictly_increasing_ratio([1, 2])
        assert result == 1.0
    
    def test_two_elements_decreasing(self):
        """Two decreasing elements should return 0.0."""
        result = calculate_strictly_increasing_ratio([2, 1])
        assert result == 0.0
    
    def test_two_elements_equal(self):
        """Two equal elements should return 0.0."""
        result = calculate_strictly_increasing_ratio([5, 5])
        assert result == 0.0
    
    def test_strictly_increasing_sequence(self):
        """Strictly increasing sequence should return 1.0."""
        result = calculate_strictly_increasing_ratio([1, 2, 3, 4, 5])
        assert result == 1.0
    
    def test_strictly_decreasing_sequence(self):
        """Strictly decreasing sequence should return 0.0."""
        result = calculate_strictly_increasing_ratio([5, 4, 3, 2, 1])
        assert result == 0.0
    
    def test_mixed_sequence(self):
        """Mixed sequence should return correct ratio."""
        # [1,2,3,1,2,0,1,10,20,30]
        # Increasing: 1<2, 2<3, 1<2, 0<1, 1<10, 10<20, 20<30 = 7
        # Total pairs: 9
        # Ratio: 7/9 ≈ 0.778
        result = calculate_strictly_increasing_ratio([1, 2, 3, 1, 2, 0, 1, 10, 20, 30])
        assert result is not None
        assert abs(result - 7/9) < 0.001
    
    def test_all_equal(self):
        """All equal values should return 0.0."""
        result = calculate_strictly_increasing_ratio([5, 5, 5, 5])
        assert result == 0.0


class TestCalculateNondecreasingRatio:
    """Tests for calculate_nondecreasing_ratio."""
    
    def test_empty_list_returns_none(self):
        """Empty list should return None."""
        result = calculate_nondecreasing_ratio([])
        assert result is None
    
    def test_single_element_returns_none(self):
        """Single element list should return None."""
        result = calculate_nondecreasing_ratio([42])
        assert result is None
    
    def test_strictly_increasing_sequence(self):
        """Strictly increasing sequence should return 1.0."""
        result = calculate_nondecreasing_ratio([1, 2, 3, 4, 5])
        assert result == 1.0
    
    def test_all_equal(self):
        """All equal values should return 1.0."""
        result = calculate_nondecreasing_ratio([5, 5, 5, 5])
        assert result == 1.0
    
    def test_mixed_sequence(self):
        """Mixed sequence should return correct ratio."""
        # [1,2,2,3,1,2]
        # Non-decreasing: 1<=2, 2<=2, 2<=3, 3>1, 1<=2 = 4
        # Total pairs: 5
        # Ratio: 4/5 = 0.8
        result = calculate_nondecreasing_ratio([1, 2, 2, 3, 1, 2])
        assert result == 0.8


class TestCalculateStepOneRatio:
    """Tests for calculate_step_one_ratio."""
    
    def test_empty_list_returns_none(self):
        """Empty list should return None."""
        result = calculate_step_one_ratio([])
        assert result is None
    
    def test_single_element_returns_none(self):
        """Single element list should return None."""
        result = calculate_step_one_ratio([42])
        assert result is None
    
    def test_step_one_sequence(self):
        """Step-one sequence should return 1.0."""
        result = calculate_step_one_ratio([1, 2, 3, 4, 5])
        assert result == 1.0
    
    def test_no_step_one(self):
        """No step-one pairs should return 0.0."""
        result = calculate_step_one_ratio([1, 3, 5, 7, 9])
        assert result == 0.0
    
    def test_mixed_sequence(self):
        """Mixed sequence should return correct ratio."""
        # [1,2,3,5,6,10]
        # Step-one: 2-1=1, 3-2=1, 6-5=1 = 3
        # Total pairs: 5
        # Ratio: 3/5 = 0.6
        result = calculate_step_one_ratio([1, 2, 3, 5, 6, 10])
        assert result == 0.6


class TestDetectSequencePattern:
    """Tests for detect_sequence_pattern."""
    
    def test_empty_list_returns_none(self):
        """Empty list should return None."""
        result = detect_sequence_pattern([])
        assert result is None
    
    def test_single_element_returns_none(self):
        """Single element list should return None."""
        result = detect_sequence_pattern([42])
        assert result is None
    
    def test_step_one_pattern(self):
        """Step-one sequence should be detected."""
        result = detect_sequence_pattern([1, 2, 3, 4, 5])
        assert result == 'step_one'
    
    def test_strictly_increasing_pattern(self):
        """Strictly increasing (but not step-one) should be detected."""
        result = detect_sequence_pattern([1, 3, 5, 7, 9])
        assert result == 'strictly_increasing'
    
    def test_nondecreasing_pattern(self):
        """Non-decreasing (with equals) should be detected."""
        # [1, 2, 2, 3, 3] - has equals but no step-one majority
        # step-one: 2-1=1, 3-2=1 = 2/4 = 0.5
        # strictly_inc: 1<2, 2<2(no), 2<3, 3<3(no) = 2/4 = 0.5
        # nondecreasing: 1<=2, 2<=2, 2<=3, 3<=3 = 4/4 = 1.0
        result = detect_sequence_pattern([1, 2, 2, 3, 3])
        assert result == 'nondecreasing'
    
    def test_no_pattern(self):
        """Random sequence should return None."""
        result = detect_sequence_pattern([5, 1, 9, 2, 8, 3])
        assert result is None
    
    def test_custom_threshold(self):
        """Custom threshold should affect detection."""
        # [1,3,5,7,2] - strictly increasing but not step-one
        # step-one: 0/4 = 0.0
        # strictly_inc: 1<3, 3<5, 5<7, 7>2 = 3/4 = 0.75
        result = detect_sequence_pattern([1, 3, 5, 7, 2], threshold=0.8)
        assert result is None  # 0.75 < 0.8
        
        result = detect_sequence_pattern([1, 3, 5, 7, 2], threshold=0.7)
        assert result == 'strictly_increasing'  # 0.75 >= 0.7


class TestSafetyNoDivisionByZero:
    """Tests to ensure no division by zero."""
    
    def test_empty_list_no_crash(self):
        """Empty list should not crash."""
        try:
            calculate_strictly_increasing_ratio([])
            calculate_nondecreasing_ratio([])
            calculate_step_one_ratio([])
            detect_sequence_pattern([])
        except ZeroDivisionError:
            pytest.fail("ZeroDivisionError raised for empty list")
    
    def test_single_element_no_crash(self):
        """Single element should not crash."""
        try:
            calculate_strictly_increasing_ratio([1])
            calculate_nondecreasing_ratio([1])
            calculate_step_one_ratio([1])
            detect_sequence_pattern([1])
        except ZeroDivisionError:
            pytest.fail("ZeroDivisionError raised for single element")
