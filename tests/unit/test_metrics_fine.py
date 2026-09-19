"""Fine-grained metrics 测试"""

import pytest
from semantic_detector.contracts import DetectorEvidence, FieldKey
from semantic_detector.evaluation.ground_truth import GroundTruthRecord
from semantic_detector.evaluation.metrics import (
    AlignedPair,
    calculate_fine_top1_accuracy,
    has_fine_label,
)


class TestCalculateFineTop1Accuracy:
    """Fine top-1 accuracy 测试"""
    
    def test_empty_pairs(self):
        """测试空列表"""
        accuracy = calculate_fine_top1_accuracy([])
        assert accuracy == 0.0
    
    def test_no_fine_labels(self):
        """测试无 fine label"""
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('test', 'constant', '', 1.0, True, 'test'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
        ]
        
        accuracy = calculate_fine_top1_accuracy(pairs)
        assert accuracy == 0.0
    
    def test_all_correct(self):
        """测试全部正确"""
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('test', 'timestamp', 'timestamp_unix_seconds', 1.0, True, 'test'),
                GroundTruthRecord(1, 0, 'timestamp', 1.0, True, fine_label='timestamp_unix_seconds'),
                True
            ),
            AlignedPair(
                FieldKey("l1", "r", 1),
                DetectorEvidence('test', 'timestamp', 'timestamp_unix_milliseconds', 1.0, True, 'test'),
                GroundTruthRecord(2, 1, 'timestamp', 1.0, True, fine_label='timestamp_unix_milliseconds'),
                True
            ),
        ]
        
        accuracy = calculate_fine_top1_accuracy(pairs)
        assert accuracy == 1.0
    
    def test_half_correct(self):
        """测试一半正确"""
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('test', 'timestamp', 'timestamp_unix_seconds', 1.0, True, 'test'),
                GroundTruthRecord(1, 0, 'timestamp', 1.0, True, fine_label='timestamp_unix_seconds'),
                True
            ),
            AlignedPair(
                FieldKey("l1", "r", 1),
                DetectorEvidence('test', 'timestamp', 'timestamp_unix_seconds', 1.0, True, 'test'),
                GroundTruthRecord(2, 1, 'timestamp', 1.0, True, fine_label='timestamp_unix_milliseconds'),
                True
            ),
        ]
        
        accuracy = calculate_fine_top1_accuracy(pairs)
        assert accuracy == 0.5
    
    def test_mixed_with_no_fine(self):
        """测试混合（部分无 fine label）"""
        pairs = [
            # 有 fine label，正确
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('test', 'timestamp', 'timestamp_unix_seconds', 1.0, True, 'test'),
                GroundTruthRecord(1, 0, 'timestamp', 1.0, True, fine_label='timestamp_unix_seconds'),
                True
            ),
            # 无 fine label
            AlignedPair(
                FieldKey("l1", "r", 1),
                DetectorEvidence('test', 'constant', '', 1.0, True, 'test'),
                GroundTruthRecord(2, 1, 'constant', 1.0, True),
                True
            ),
        ]
        
        accuracy = calculate_fine_top1_accuracy(pairs)
        assert accuracy == 1.0  # 只计算有 fine label 的


class TestHasFineLabel:
    """判断 fine label 测试"""
    
    def test_both_have_fine(self):
        """测试都有 fine label"""
        pair = AlignedPair(
            FieldKey("l1", "r", 0),
            DetectorEvidence('test', 'timestamp', 'timestamp_unix_seconds', 1.0, True, 'test'),
            GroundTruthRecord(1, 0, 'timestamp', 1.0, True, fine_label='timestamp_unix_seconds'),
            True
        )
        
        assert has_fine_label(pair) is True
    
    def test_pred_no_fine(self):
        """测试预测无 fine label"""
        pair = AlignedPair(
            FieldKey("l1", "r", 0),
            DetectorEvidence('test', 'constant', '', 1.0, True, 'test'),
            GroundTruthRecord(1, 0, 'timestamp', 1.0, True, fine_label='timestamp_unix_seconds'),
            True
        )
        
        assert has_fine_label(pair) is False
    
    def test_truth_no_fine(self):
        """测试真值无 fine label"""
        pair = AlignedPair(
            FieldKey("l1", "r", 0),
            DetectorEvidence('test', 'timestamp', 'timestamp_unix_seconds', 1.0, True, 'test'),
            GroundTruthRecord(1, 0, 'constant', 1.0, True),
            True
        )
        
        assert has_fine_label(pair) is False
    
    def test_unmatched_pair(self):
        """测试未匹配的对"""
        pair = AlignedPair(
            FieldKey("l1", "r", 0),
            None,
            None,
            False
        )
        
        assert has_fine_label(pair) is False
