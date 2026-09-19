"""Overall accuracy 测试"""

import pytest
from semantic_detector.contracts import DetectorEvidence, FieldKey
from semantic_detector.evaluation.ground_truth import GroundTruthRecord
from semantic_detector.evaluation.metrics import (
    AlignedPair,
    calculate_overall_accuracy,
    is_prediction_correct,
)


class TestCalculateOverallAccuracy:
    """Overall accuracy 测试"""
    
    def test_empty_pairs(self):
        """测试空列表"""
        accuracy = calculate_overall_accuracy([])
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
        
        accuracy = calculate_overall_accuracy(pairs)
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
        
        accuracy = calculate_overall_accuracy(pairs)
        assert accuracy == 0.5
    
    def test_all_incorrect(self):
        """测试全部错误"""
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('test', 'constant', '', 1.0, True, 'test'),
                GroundTruthRecord(1, 0, 'payload', 1.0, True),
                True
            ),
            AlignedPair(
                FieldKey("l1", "r", 1),
                DetectorEvidence('test', 'constant', '', 1.0, True, 'test'),
                GroundTruthRecord(2, 1, 'payload', 1.0, True),
                True
            ),
        ]
        
        accuracy = calculate_overall_accuracy(pairs)
        assert accuracy == 0.0
    
    def test_unmatched_pairs_ignored(self):
        """测试未匹配的对被忽略"""
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('test', 'constant', '', 1.0, True, 'test'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
            AlignedPair(
                FieldKey("l1", "r", 1),
                None,
                None,
                False
            ),
        ]
        
        accuracy = calculate_overall_accuracy(pairs)
        assert accuracy == 1.0


class TestIsPredictionCorrect:
    """预测正确性判断测试"""
    
    def test_correct_prediction(self):
        """测试正确预测"""
        pair = AlignedPair(
            FieldKey("l1", "r", 0),
            DetectorEvidence('test', 'constant', '', 1.0, True, 'test'),
            GroundTruthRecord(1, 0, 'constant', 1.0, True),
            True
        )
        
        assert is_prediction_correct(pair) is True
    
    def test_incorrect_prediction(self):
        """测试错误预测"""
        pair = AlignedPair(
            FieldKey("l1", "r", 0),
            DetectorEvidence('test', 'constant', '', 1.0, True, 'test'),
            GroundTruthRecord(1, 0, 'payload', 1.0, True),
            True
        )
        
        assert is_prediction_correct(pair) is False
    
    def test_unmatched_pair(self):
        """测试未匹配的对"""
        pair = AlignedPair(
            FieldKey("l1", "r", 0),
            None,
            None,
            False
        )

        assert is_prediction_correct(pair) is False


class TestOverallAccuracyR253:
    """R253：Overall Accuracy 分母为全部 truth，abstained 不从分母中消失

    03 教程 12.4：
    - Overall Accuracy = 标准化预测正确的 truth 数量 / 全部 truth 数量
    - 以下均算错误：预测为 unknown；truth 没有匹配预测；预测标签错误
    - abstained 不从分母中消失
    """

    def test_mixed_correct_unknown_missing_hand_calculated(self):
        """正确/unknown/missing 混合手算

        场景：3 个 truth
        - truth0: semantic_type='constant'，预测 constant（正确）→ 分子+1，分母+1
        - truth1: semantic_type='length'，预测 unknown（abstained）→ 分子+0，分母+1
        - truth2: semantic_type='timestamp'，无预测（missing）→ 分子+0，分母+1
        手算：accuracy = 1 / 3
        """
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

        accuracy = calculate_overall_accuracy(pairs, unmatched_truths)

        # 分子=1（只有 truth0 正确），分母=3（全部 truth），accuracy=1/3
        assert accuracy == pytest.approx(1.0 / 3.0)

    def test_unknown_prediction_not_in_numerator_but_in_denominator(self):
        """预测为 unknown 不计入分子，但仍计入分母"""
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('test', 'unknown', '', 0.0, False, 'abstained'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
        ]

        accuracy = calculate_overall_accuracy(pairs)

        # 分子=0（unknown 不计入），分母=1，accuracy=0.0
        assert accuracy == 0.0

    def test_unknown_prediction_matching_unknown_truth_still_wrong(self):
        """预测为 unknown 即使 truth 也是 unknown 仍算错误（abstained 不贡献正确数）"""
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('test', 'unknown', '', 0.0, False, 'abstained'),
                GroundTruthRecord(1, 0, 'unknown', 1.0, True),
                True
            ),
        ]

        accuracy = calculate_overall_accuracy(pairs)

        # 预测为 unknown 一律算错误，accuracy=0.0
        assert accuracy == 0.0

    def test_all_missing_truths_zero_accuracy(self):
        """全部 truth 无匹配预测（全在 unmatched_truths）→ accuracy=0.0"""
        pairs = []
        unmatched_truths = [
            GroundTruthRecord(1, 0, 'constant', 1.0, True),
            GroundTruthRecord(2, 1, 'length', 1.0, True),
        ]

        accuracy = calculate_overall_accuracy(pairs, unmatched_truths)

        # 分子=0，分母=2，accuracy=0.0
        assert accuracy == 0.0

    def test_no_unmatched_truths_backward_compatible(self):
        """不传 unmatched_truths 时行为兼容：分母只含匹配的 truth"""
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

        accuracy = calculate_overall_accuracy(pairs)

        # 分子=2，分母=2，accuracy=1.0
        assert accuracy == 1.0

    def test_empty_unmatched_truths_list(self):
        """传入空 unmatched_truths 列表不影响分母"""
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('test', 'constant', '', 1.0, True, 'test'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
        ]

        accuracy = calculate_overall_accuracy(pairs, [])

        # 分子=1，分母=1，accuracy=1.0
        assert accuracy == 1.0

    def test_wrong_label_counts_as_error(self):
        """预测标签错误算错误：分子不计入，分母计入"""
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('test', 'constant', '', 1.0, True, 'test'),
                GroundTruthRecord(1, 0, 'payload', 1.0, True),
                True
            ),
            AlignedPair(
                FieldKey("l1", "r", 1),
                DetectorEvidence('test', 'length', '', 1.0, True, 'test'),
                GroundTruthRecord(2, 1, 'length', 1.0, True),
                True
            ),
        ]

        accuracy = calculate_overall_accuracy(pairs)

        # 分子=1（truth1 正确），分母=2，accuracy=0.5
        assert accuracy == 0.5

    def test_mixed_all_three_error_types_hand_calculated(self):
        """三种错误混合手算：正确 + unknown + 错标签 + missing

        - truth0: 预测 constant，truth constant → 正确（分子+1，分母+1）
        - truth1: 预测 unknown，truth length → abstained（分子+0，分母+1）
        - truth2: 预测 string，truth timestamp → 错标签（分子+0，分母+1）
        - truth3: 无预测，truth identifier → missing（分子+0，分母+1）
        手算：accuracy = 1 / 4
        """
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
            AlignedPair(
                FieldKey("l1", "r", 2),
                DetectorEvidence('test', 'string', '', 0.8, True, 'test'),
                GroundTruthRecord(3, 2, 'timestamp', 1.0, True),
                True
            ),
        ]
        unmatched_truths = [
            GroundTruthRecord(4, 3, 'identifier', 1.0, True),
        ]

        accuracy = calculate_overall_accuracy(pairs, unmatched_truths)

        # 分子=1，分母=4，accuracy=0.25
        assert accuracy == pytest.approx(0.25)
