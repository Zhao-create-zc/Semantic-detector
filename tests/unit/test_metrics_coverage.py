"""Coverage 和 unknown_rate 测试"""

import pytest
from semantic_detector.contracts import DetectorEvidence, FieldKey
from semantic_detector.evaluation.ground_truth import GroundTruthRecord
from semantic_detector.evaluation.metrics import (
    AlignedPair,
    calculate_coverage,
    calculate_unknown_rate,
    is_prediction_unknown,
    calculate_covered_accuracy,
)


class TestCalculateCoverage:
    """Coverage 测试"""
    
    def test_empty_lists(self):
        """测试空列表"""
        coverage = calculate_coverage([], [])
        assert coverage == 0.0
    
    def test_full_coverage(self):
        """测试完全覆盖"""
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('test', 'constant', '', 1.0, True, 'test'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
            AlignedPair(
                FieldKey("l1", "r", 1),
                DetectorEvidence('test', 'payload', '', 1.0, True, 'test'),
                GroundTruthRecord(2, 1, 'payload', 1.0, True),
                True
            ),
        ]
        
        coverage = calculate_coverage(pairs, [])
        assert coverage == 1.0
    
    def test_partial_coverage(self):
        """测试部分覆盖"""
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('test', 'constant', '', 1.0, True, 'test'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
        ]
        
        unmatched_truths = [
            GroundTruthRecord(2, 1, 'payload', 1.0, True),
        ]
        
        coverage = calculate_coverage(pairs, unmatched_truths)
        assert coverage == 0.5
    
    def test_no_coverage(self):
        """测试无覆盖"""
        unmatched_truths = [
            GroundTruthRecord(1, 0, 'constant', 1.0, True),
            GroundTruthRecord(2, 1, 'payload', 1.0, True),
        ]
        
        coverage = calculate_coverage([], unmatched_truths)
        assert coverage == 0.0


class TestCalculateUnknownRate:
    """Unknown rate 测试"""
    
    def test_empty_pairs(self):
        """测试空列表"""
        rate = calculate_unknown_rate([])
        assert rate == 0.0
    
    def test_no_unknown(self):
        """测试无 unknown"""
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('test', 'constant', '', 1.0, True, 'test'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
            AlignedPair(
                FieldKey("l1", "r", 1),
                DetectorEvidence('test', 'payload', '', 1.0, True, 'test'),
                GroundTruthRecord(2, 1, 'payload', 1.0, True),
                True
            ),
        ]
        
        rate = calculate_unknown_rate(pairs)
        assert rate == 0.0
    
    def test_all_unknown(self):
        """测试全部 unknown"""
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('test', 'unknown', '', 1.0, True, 'test'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
            AlignedPair(
                FieldKey("l1", "r", 1),
                DetectorEvidence('test', 'unknown', '', 1.0, True, 'test'),
                GroundTruthRecord(2, 1, 'payload', 1.0, True),
                True
            ),
        ]
        
        rate = calculate_unknown_rate(pairs)
        assert rate == 1.0
    
    def test_half_unknown(self):
        """测试一半 unknown"""
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('test', 'constant', '', 1.0, True, 'test'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
            AlignedPair(
                FieldKey("l1", "r", 1),
                DetectorEvidence('test', 'unknown', '', 1.0, True, 'test'),
                GroundTruthRecord(2, 1, 'payload', 1.0, True),
                True
            ),
        ]
        
        rate = calculate_unknown_rate(pairs)
        assert rate == 0.5


class TestIsPredictionUnknown:
    """预测 unknown 判断测试"""
    
    def test_unknown_prediction(self):
        """测试 unknown 预测"""
        pair = AlignedPair(
            FieldKey("l1", "r", 0),
            DetectorEvidence('test', 'unknown', '', 1.0, True, 'test'),
            GroundTruthRecord(1, 0, 'constant', 1.0, True),
            True
        )
        
        assert is_prediction_unknown(pair) is True
    
    def test_non_unknown_prediction(self):
        """测试非 unknown 预测"""
        pair = AlignedPair(
            FieldKey("l1", "r", 0),
            DetectorEvidence('test', 'constant', '', 1.0, True, 'test'),
            GroundTruthRecord(1, 0, 'constant', 1.0, True),
            True
        )
        
        assert is_prediction_unknown(pair) is False
    
    def test_unmatched_pair(self):
        """测试未匹配的对"""
        pair = AlignedPair(
            FieldKey("l1", "r", 0),
            None,
            None,
            False
        )
        
        assert is_prediction_unknown(pair) is False


class TestCalculateCoveredAccuracy:
    """Covered accuracy 测试"""
    
    def test_empty_pairs(self):
        """测试空列表"""
        accuracy = calculate_covered_accuracy([])
        assert accuracy == 0.0
    
    def test_all_correct(self):
        """测试全部正确"""
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('test', 'constant', '', 1.0, True, 'test'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
            AlignedPair(
                FieldKey("l1", "r", 1),
                DetectorEvidence('test', 'payload', '', 1.0, True, 'test'),
                GroundTruthRecord(2, 1, 'payload', 1.0, True),
                True
            ),
        ]
        
        accuracy = calculate_covered_accuracy(pairs)
        assert accuracy == 1.0
    
    def test_half_correct(self):
        """测试一半正确"""
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('test', 'constant', '', 1.0, True, 'test'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
            AlignedPair(
                FieldKey("l1", "r", 1),
                DetectorEvidence('test', 'constant', '', 1.0, True, 'test'),
                GroundTruthRecord(2, 1, 'payload', 1.0, True),
                True
            ),
        ]
        
        accuracy = calculate_covered_accuracy(pairs)
        assert accuracy == 0.5
    
    def test_none_correct(self):
        """测试全部错误"""
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('test', 'payload', '', 1.0, True, 'test'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
            AlignedPair(
                FieldKey("l1", "r", 1),
                DetectorEvidence('test', 'constant', '', 1.0, True, 'test'),
                GroundTruthRecord(2, 1, 'payload', 1.0, True),
                True
            ),
        ]

        accuracy = calculate_covered_accuracy(pairs)
        assert accuracy == 0.0


class TestCoverageR254:
    """R254：Coverage 仅统计非 unknown，分母为全部 truth

    03 教程 12.4：
    - Coverage = 与 truth 对齐且预测非 unknown 的字段数 / 全部 truth 数量
    - 04 任务表 R254：coverage 仅统计非 unknown
    """

    def test_coverage_excludes_unknown_prediction(self):
        """unknown 预测不计入覆盖（仅统计非 unknown）"""
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('test', 'unknown', '', 0.0, False, 'abstained'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
            AlignedPair(
                FieldKey("l1", "r", 1),
                DetectorEvidence('test', 'constant', '', 1.0, True, 'test'),
                GroundTruthRecord(2, 1, 'constant', 1.0, True),
                True
            ),
        ]

        coverage = calculate_coverage(pairs, [])

        # 分子=1（只有 constant 算覆盖），分母=2，coverage=0.5
        assert coverage == 0.5

    def test_coverage_all_unknown_zero(self):
        """全部预测为 unknown → coverage=0.0"""
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('test', 'unknown', '', 0.0, False, 'abstained'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
            AlignedPair(
                FieldKey("l1", "r", 1),
                DetectorEvidence('test', 'unknown', '', 0.0, False, 'abstained'),
                GroundTruthRecord(2, 1, 'length', 1.0, True),
                True
            ),
        ]

        coverage = calculate_coverage(pairs, [])

        # 分子=0，分母=2，coverage=0.0
        assert coverage == 0.0

    def test_coverage_denominator_includes_unmatched_truths(self):
        """coverage 分母含 unmatched_truths（missing 计入分母）"""
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('test', 'constant', '', 1.0, True, 'test'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
        ]
        unmatched_truths = [
            GroundTruthRecord(2, 1, 'length', 1.0, True),
            GroundTruthRecord(3, 2, 'timestamp', 1.0, True),
        ]

        coverage = calculate_coverage(pairs, unmatched_truths)

        # 分子=1，分母=1+2=3，coverage=1/3
        assert coverage == pytest.approx(1.0 / 3.0)

    def test_coverage_mixed_unknown_and_missing(self):
        """unknown 与 missing 混合：coverage 仅算非 unknown 已对齐"""
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('test', 'constant', '', 1.0, True, 'test'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
            AlignedPair(
                FieldKey("l1", "r", 1),
                DetectorEvidence('test', 'unknown', '', 0.0, False, 'abstained'),
                GroundTruthRecord(2, 1, 'length', 1.0, True),
                True
            ),
        ]
        unmatched_truths = [
            GroundTruthRecord(3, 2, 'timestamp', 1.0, True),
        ]

        coverage = calculate_coverage(pairs, unmatched_truths)

        # 分子=1（只有 constant），分母=2+1=3，coverage=1/3
        assert coverage == pytest.approx(1.0 / 3.0)


class TestUnknownRateR254:
    """R254：Unknown rate 分母为全部 truth（含 unmatched_truths）

    03 教程 12.4：
    - Unknown Rate = 对齐后预测 unknown 的字段数 / 全部 truth 数量
    """

    def test_unknown_rate_denominator_includes_unmatched_truths(self):
        """unknown_rate 分母含 unmatched_truths（missing 计入分母）"""
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('test', 'unknown', '', 0.0, False, 'abstained'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
        ]
        unmatched_truths = [
            GroundTruthRecord(2, 1, 'length', 1.0, True),
        ]

        rate = calculate_unknown_rate(pairs, unmatched_truths)

        # 分子=1（一个 unknown 预测），分母=1+1=2，rate=0.5
        assert rate == 0.5

    def test_unknown_rate_no_unmatched_backward_compatible(self):
        """不传 unmatched_truths 时向后兼容：分母只含匹配的 truth"""
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('test', 'unknown', '', 0.0, False, 'abstained'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
        ]

        rate = calculate_unknown_rate(pairs)

        # 分母=1，分子=1，rate=1.0
        assert rate == 1.0

    def test_unknown_rate_all_missing_zero(self):
        """全部 truth 无匹配预测（全 missing）→ unknown_rate=0.0（无 unknown 预测）"""
        pairs = []
        unmatched_truths = [
            GroundTruthRecord(1, 0, 'constant', 1.0, True),
            GroundTruthRecord(2, 1, 'length', 1.0, True),
        ]

        rate = calculate_unknown_rate(pairs, unmatched_truths)

        # 分子=0（无 unknown 预测），分母=2，rate=0.0
        assert rate == 0.0

    def test_unknown_vs_missing_distinguished(self):
        """unknown 与 missing 区分：unknown 预测算 unknown_rate，missing 不算"""
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('test', 'unknown', '', 0.0, False, 'abstained'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
            AlignedPair(
                FieldKey("l1", "r", 1),
                DetectorEvidence('test', 'constant', '', 1.0, True, 'test'),
                GroundTruthRecord(2, 1, 'constant', 1.0, True),
                True
            ),
        ]
        unmatched_truths = [
            GroundTruthRecord(3, 2, 'timestamp', 1.0, True),
        ]

        rate = calculate_unknown_rate(pairs, unmatched_truths)

        # 分子=1（一个 unknown 预测），分母=2+1=3，rate=1/3
        assert rate == pytest.approx(1.0 / 3.0)


class TestCoveredAccuracyR255:
    """R255：Covered Accuracy 分母不含 unknown

    03 教程 12.4：
    - Covered Accuracy = 非 unknown 且正确的字段数 / 非 unknown 的已对齐预测数
    - 04 任务表 R255：非 unknown 对错混合，分母不含 unknown
    """

    def test_unknown_excluded_from_denominator(self):
        """unknown 预测不计入分母（abstained 不参与 covered accuracy）"""
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('test', 'unknown', '', 0.0, False, 'abstained'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
            AlignedPair(
                FieldKey("l1", "r", 1),
                DetectorEvidence('test', 'constant', '', 1.0, True, 'test'),
                GroundTruthRecord(2, 1, 'constant', 1.0, True),
                True
            ),
        ]

        accuracy = calculate_covered_accuracy(pairs)

        # 分母=1（排除 unknown），分子=1，accuracy=1.0
        assert accuracy == 1.0

    def test_mixed_correct_wrong_non_unknown(self):
        """非 unknown 对错混合：分母只含非 unknown 已对齐预测"""
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('test', 'constant', '', 1.0, True, 'test'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
            AlignedPair(
                FieldKey("l1", "r", 1),
                DetectorEvidence('test', 'payload', '', 1.0, True, 'test'),
                GroundTruthRecord(2, 1, 'constant', 1.0, True),
                True
            ),
            AlignedPair(
                FieldKey("l1", "r", 2),
                DetectorEvidence('test', 'unknown', '', 0.0, False, 'abstained'),
                GroundTruthRecord(3, 2, 'length', 1.0, True),
                True
            ),
        ]

        accuracy = calculate_covered_accuracy(pairs)

        # 分母=2（constant + payload，排除 unknown），分子=1（constant 正确），accuracy=0.5
        assert accuracy == 0.5

    def test_all_unknown_zero_covered_accuracy(self):
        """全部预测为 unknown → covered_count=0 → 0.0"""
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('test', 'unknown', '', 0.0, False, 'abstained'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
            AlignedPair(
                FieldKey("l1", "r", 1),
                DetectorEvidence('test', 'unknown', '', 0.0, False, 'abstained'),
                GroundTruthRecord(2, 1, 'length', 1.0, True),
                True
            ),
        ]

        accuracy = calculate_covered_accuracy(pairs)

        # 分母=0（全 unknown 排除），accuracy=0.0
        assert accuracy == 0.0

    def test_unknown_matching_unknown_truth_excluded(self):
        """unknown 预测即使 truth 也是 unknown 仍不计入分母"""
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('test', 'unknown', '', 0.0, False, 'abstained'),
                GroundTruthRecord(1, 0, 'unknown', 1.0, True),
                True
            ),
        ]

        accuracy = calculate_covered_accuracy(pairs)

        # 分母=0（unknown 排除，即使 truth 也是 unknown），accuracy=0.0
        assert accuracy == 0.0

    def test_all_wrong_non_unknown_zero(self):
        """非 unknown 全错 → 分子=0，accuracy=0.0"""
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('test', 'payload', '', 1.0, True, 'test'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
            AlignedPair(
                FieldKey("l1", "r", 1),
                DetectorEvidence('test', 'constant', '', 1.0, True, 'test'),
                GroundTruthRecord(2, 1, 'payload', 1.0, True),
                True
            ),
        ]

        accuracy = calculate_covered_accuracy(pairs)

        # 分母=2，分子=0，accuracy=0.0
        assert accuracy == 0.0
