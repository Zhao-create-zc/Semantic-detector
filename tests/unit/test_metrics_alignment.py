"""预测与 truth 的 FieldKey 对齐测试

R252：新增完整 FieldKey 对齐测试（多 layout、多方向、顺序打乱）。
"""

import pytest
from dataclasses import dataclass
from semantic_detector.contracts import DetectorEvidence, FieldKey, SemanticPrediction, Direction
from semantic_detector.evaluation.ground_truth import GroundTruthRecord
from semantic_detector.evaluation.metrics import (
    AlignedPair,
    align_predictions_with_truth,
    _extract_field_key_from_prediction,
    count_matched_pairs,
    count_unmatched_predictions,
    count_unmatched_truths,
)


class TestAlignPredictionsWithTruth:
    """对齐预测和真值测试"""
    
    def test_empty_lists(self):
        """测试空列表"""
        aligned, unmatched_pred, unmatched_truth = align_predictions_with_truth(
            [], [], "layout_1", "request"
        )
        
        assert len(aligned) == 0
        assert len(unmatched_pred) == 0
        assert len(unmatched_truth) == 0
    
    def test_exact_match(self):
        """测试完全匹配"""
        predictions = [
            DetectorEvidence(
                detector='test',
                coarse_label='constant',
                fine_label='',
                score=1.0,
                is_hard_evidence=True,
                reason_code='test',
                details={'field_index': 0}
            ),
            DetectorEvidence(
                detector='test',
                coarse_label='payload',
                fine_label='',
                score=1.0,
                is_hard_evidence=True,
                reason_code='test',
                details={'field_index': 1}
            ),
        ]
        
        truths = [
            GroundTruthRecord(1, 0, 'constant', 1.0, True),
            GroundTruthRecord(2, 1, 'payload', 1.0, True),
        ]
        
        aligned, unmatched_pred, unmatched_truth = align_predictions_with_truth(
            predictions, truths, "layout_1", "request"
        )
        
        assert len(aligned) == 2
        assert len(unmatched_pred) == 0
        assert len(unmatched_truth) == 0
        
        assert all(pair.is_matched for pair in aligned)
    
    def test_missing_prediction(self):
        """测试缺失预测"""
        predictions = [
            DetectorEvidence(
                detector='test',
                coarse_label='constant',
                fine_label='',
                score=1.0,
                is_hard_evidence=True,
                reason_code='test',
                details={'field_index': 0}
            ),
        ]
        
        truths = [
            GroundTruthRecord(1, 0, 'constant', 1.0, True),
            GroundTruthRecord(2, 1, 'payload', 1.0, True),
        ]
        
        aligned, unmatched_pred, unmatched_truth = align_predictions_with_truth(
            predictions, truths, "layout_1", "request"
        )
        
        assert len(aligned) == 1
        assert len(unmatched_pred) == 0
        assert len(unmatched_truth) == 1
        
        assert aligned[0].is_matched
        assert unmatched_truth[0].field_index == 1
    
    def test_missing_truth(self):
        """测试缺失真值"""
        predictions = [
            DetectorEvidence(
                detector='test',
                coarse_label='constant',
                fine_label='',
                score=1.0,
                is_hard_evidence=True,
                reason_code='test',
                details={'field_index': 0}
            ),
            DetectorEvidence(
                detector='test',
                coarse_label='payload',
                fine_label='',
                score=1.0,
                is_hard_evidence=True,
                reason_code='test',
                details={'field_index': 1}
            ),
        ]
        
        truths = [
            GroundTruthRecord(1, 0, 'constant', 1.0, True),
        ]
        
        aligned, unmatched_pred, unmatched_truth = align_predictions_with_truth(
            predictions, truths, "layout_1", "request"
        )
        
        assert len(aligned) == 1
        assert len(unmatched_pred) == 1
        assert len(unmatched_truth) == 0
        
        assert aligned[0].is_matched
        assert unmatched_pred[0].details['field_index'] == 1


class TestCountFunctions:
    """计数函数测试"""
    
    def test_count_matched_pairs(self):
        """测试匹配对计数"""
        pairs = [
            AlignedPair(FieldKey("l1", "r", 0), None, None, True),
            AlignedPair(FieldKey("l1", "r", 1), None, None, False),
            AlignedPair(FieldKey("l1", "r", 2), None, None, True),
        ]
        
        assert count_matched_pairs(pairs) == 2
    
    def test_count_unmatched_predictions(self):
        """测试未匹配预测计数"""
        preds = [
            DetectorEvidence('test', 'a', '', 1.0, True, 'test'),
            DetectorEvidence('test', 'b', '', 1.0, True, 'test'),
        ]
        
        assert count_unmatched_predictions(preds) == 2
    
    def test_count_unmatched_truths(self):
        """测试未匹配真值计数"""
        truths = [
            GroundTruthRecord(1, 0, 'a', 1.0, True),
            GroundTruthRecord(2, 1, 'b', 1.0, True),
        ]

        assert count_unmatched_truths(truths) == 2


class TestExtractFieldKeyFromPrediction:
    """R252: _extract_field_key_from_prediction 测试

    支持 SemanticPrediction（含完整身份）和旧 DetectorEvidence（从 details 取）。
    """

    def test_extract_from_semantic_prediction(self):
        """从 SemanticPrediction 提取完整 FieldKey。"""
        pred = SemanticPrediction(
            run_id='run-1',
            layout_id='layout_a',
            direction=Direction.RESPONSE,
            field_index=3,
            coarse_label='length',
            fine_label='total_message_length',
            confidence=0.95,
            abstained=False,
            evidence=(),
            alternatives=(),
            prediction_status='confirmed',
        )

        key = _extract_field_key_from_prediction(pred)

        assert isinstance(key, FieldKey)
        assert key.layout_id == 'layout_a'
        assert key.direction == Direction.RESPONSE
        assert key.field_index == 3

    def test_extract_from_detector_evidence_with_details(self):
        """从 DetectorEvidence.details 提取 FieldKey。"""
        pred = DetectorEvidence(
            detector='test',
            coarse_label='constant',
            fine_label='',
            score=1.0,
            is_hard_evidence=True,
            reason_code='test',
            details={'field_index': 5, 'layout_id': 'layout_b', 'direction': 'request'},
        )

        key = _extract_field_key_from_prediction(pred)

        assert isinstance(key, FieldKey)
        assert key.layout_id == 'layout_b'
        assert key.direction == Direction.REQUEST
        assert key.field_index == 5

    def test_extract_from_detector_evidence_missing_field_index_returns_none(self):
        """DetectorEvidence 缺 field_index 时返回 None。"""
        pred = DetectorEvidence(
            detector='test',
            coarse_label='constant',
            fine_label='',
            score=1.0,
            is_hard_evidence=True,
            reason_code='test',
            details={},
        )

        key = _extract_field_key_from_prediction(pred)

        assert key is None

    def test_extract_from_detector_evidence_no_details_returns_none(self):
        """DetectorEvidence 无 details 时返回 None。"""
        pred = DetectorEvidence(
            detector='test',
            coarse_label='constant',
            fine_label='',
            score=1.0,
            is_hard_evidence=True,
            reason_code='test',
            details=None,
        )

        key = _extract_field_key_from_prediction(pred)

        assert key is None


class TestAlignByCompleteFieldKey:
    """R252: 按完整 FieldKey 对齐预测和真值

    03 教程 12.3 / 04 任务表 R252：
    - 多 layout、多方向、顺序打乱
    - 匹配准确，无 default/request
    """

    def _make_semantic_prediction(self, layout_id, direction, field_index, label='length'):
        """合成 SemanticPrediction。"""
        return SemanticPrediction(
            run_id='run-r252',
            layout_id=layout_id,
            direction=direction,
            field_index=field_index,
            coarse_label=label,
            fine_label='',
            confidence=0.95,
            abstained=False,
            evidence=(),
            alternatives=(),
            prediction_status='confirmed',
        )

    def _make_truth(self, layout_id, direction, field_index, label='length', truth_id=1):
        """合成 GroundTruthRecord。"""
        return GroundTruthRecord(
            truth_id=truth_id,
            field_index=field_index,
            semantic_label=label,
            confidence=1.0,
            is_hard_evidence=True,
            layout_id=layout_id,
            direction=direction,
        )

    def test_align_multiple_layouts(self):
        """多 layout 对齐：L1 和 L2 的同 field_index 不冲突。"""
        predictions = [
            self._make_semantic_prediction('L1', Direction.REQUEST, 0, 'length'),
            self._make_semantic_prediction('L2', Direction.REQUEST, 0, 'timestamp'),
        ]
        truths = [
            self._make_truth('L1', 'request', 0, 'length', truth_id=1),
            self._make_truth('L2', 'request', 0, 'timestamp', truth_id=2),
        ]

        aligned, unmatched_pred, unmatched_truth = align_predictions_with_truth(predictions, truths)

        assert len(aligned) == 2
        assert len(unmatched_pred) == 0
        assert len(unmatched_truth) == 0
        # 两个 FieldKey 不同（L1 vs L2）
        keys = {pair.field_key for pair in aligned}
        assert FieldKey('L1', Direction.REQUEST, 0) in keys
        assert FieldKey('L2', Direction.REQUEST, 0) in keys

    def test_align_multiple_directions(self):
        """多方向对齐：同 layout 的 request 和 response 不冲突。"""
        predictions = [
            self._make_semantic_prediction('L1', Direction.REQUEST, 0, 'length'),
            self._make_semantic_prediction('L1', Direction.RESPONSE, 0, 'timestamp'),
        ]
        truths = [
            self._make_truth('L1', 'request', 0, 'length', truth_id=1),
            self._make_truth('L1', 'response', 0, 'timestamp', truth_id=2),
        ]

        aligned, unmatched_pred, unmatched_truth = align_predictions_with_truth(predictions, truths)

        assert len(aligned) == 2
        assert len(unmatched_pred) == 0
        assert len(unmatched_truth) == 0

    def test_align_shuffled_order(self):
        """顺序打乱仍能正确匹配。"""
        predictions = [
            self._make_semantic_prediction('L2', Direction.RESPONSE, 1, 'constant'),
            self._make_semantic_prediction('L1', Direction.REQUEST, 0, 'length'),
            self._make_semantic_prediction('L1', Direction.RESPONSE, 0, 'timestamp'),
        ]
        truths = [
            self._make_truth('L1', 'response', 0, 'timestamp', truth_id=3),
            self._make_truth('L2', 'response', 1, 'constant', truth_id=1),
            self._make_truth('L1', 'request', 0, 'length', truth_id=2),
        ]

        aligned, unmatched_pred, unmatched_truth = align_predictions_with_truth(predictions, truths)

        assert len(aligned) == 3
        assert len(unmatched_pred) == 0
        assert len(unmatched_truth) == 0
        # 验证每对的 FieldKey 匹配
        for pair in aligned:
            pred_key = _extract_field_key_from_prediction(pair.prediction)
            truth_key = pair.truth.field_key
            assert pred_key == truth_key
            assert pair.field_key == pred_key

    def test_align_no_default_request_when_real_fieldkey_present(self):
        """真实 FieldKey 存在时不落入 default/request。"""
        predictions = [
            self._make_semantic_prediction('real_layout', Direction.RESPONSE, 5, 'payload'),
        ]
        truths = [
            self._make_truth('real_layout', 'response', 5, 'payload', truth_id=1),
        ]

        aligned, unmatched_pred, unmatched_truth = align_predictions_with_truth(predictions, truths)

        assert len(aligned) == 1
        assert aligned[0].field_key.layout_id == 'real_layout'
        assert aligned[0].field_key.direction == Direction.RESPONSE
        assert aligned[0].field_key.field_index == 5

    def test_align_mismatched_field_key_separates(self):
        """FieldKey 不匹配的预测和真值分别进入 unmatched。"""
        predictions = [
            self._make_semantic_prediction('L1', Direction.REQUEST, 0, 'length'),
        ]
        truths = [
            self._make_truth('L1', 'response', 0, 'timestamp', truth_id=1),
        ]

        aligned, unmatched_pred, unmatched_truth = align_predictions_with_truth(predictions, truths)

        # L1/request/0 != L1/response/0，不匹配
        assert len(aligned) == 0
        assert len(unmatched_pred) == 1
        assert len(unmatched_truth) == 1

    def test_align_partial_match(self):
        """部分匹配：3 个预测，2 个有对应真值。"""
        predictions = [
            self._make_semantic_prediction('L1', Direction.REQUEST, 0, 'length'),
            self._make_semantic_prediction('L1', Direction.REQUEST, 1, 'constant'),
            self._make_semantic_prediction('L2', Direction.REQUEST, 0, 'payload'),
        ]
        truths = [
            self._make_truth('L1', 'request', 0, 'length', truth_id=1),
            self._make_truth('L1', 'request', 1, 'constant', truth_id=2),
        ]

        aligned, unmatched_pred, unmatched_truth = align_predictions_with_truth(predictions, truths)

        assert len(aligned) == 2
        assert len(unmatched_pred) == 1  # L2/request/0 无真值
        assert len(unmatched_truth) == 0

    def test_align_mixed_semantic_prediction_and_detector_evidence(self):
        """混合 SemanticPrediction 和 DetectorEvidence 仍能对齐。"""
        sem_pred = self._make_semantic_prediction('L1', Direction.REQUEST, 0, 'length')
        det_pred = DetectorEvidence(
            detector='test',
            coarse_label='constant',
            fine_label='',
            score=1.0,
            is_hard_evidence=True,
            reason_code='test',
            details={'field_index': 1, 'layout_id': 'L1', 'direction': 'request'},
        )
        truths = [
            self._make_truth('L1', 'request', 0, 'length', truth_id=1),
            self._make_truth('L1', 'request', 1, 'constant', truth_id=2),
        ]

        aligned, unmatched_pred, unmatched_truth = align_predictions_with_truth(
            [sem_pred, det_pred], truths
        )

        assert len(aligned) == 2
        assert len(unmatched_pred) == 0
        assert len(unmatched_truth) == 0

    def test_align_sorted_by_field_key(self):
        """对齐结果按 (layout_id, direction, field_index) 排序。"""
        predictions = [
            self._make_semantic_prediction('L2', Direction.REQUEST, 0, 'length'),
            self._make_semantic_prediction('L1', Direction.RESPONSE, 1, 'constant'),
            self._make_semantic_prediction('L1', Direction.REQUEST, 0, 'length'),
        ]
        truths = [
            self._make_truth('L2', 'request', 0, 'length', truth_id=1),
            self._make_truth('L1', 'response', 1, 'constant', truth_id=2),
            self._make_truth('L1', 'request', 0, 'length', truth_id=3),
        ]

        aligned, _, _ = align_predictions_with_truth(predictions, truths)

        # 排序顺序：L1/request/0, L1/response/1, L2/request/0
        assert aligned[0].field_key == FieldKey('L1', Direction.REQUEST, 0)
        assert aligned[1].field_key == FieldKey('L1', Direction.RESPONSE, 1)
        assert aligned[2].field_key == FieldKey('L2', Direction.REQUEST, 0)

    def test_align_backward_compatible_without_layout_id_direction_args(self):
        """不传 layout_id/direction 参数仍能工作（向后兼容）。"""
        predictions = [
            self._make_semantic_prediction('L1', Direction.REQUEST, 0, 'length'),
        ]
        truths = [
            self._make_truth('L1', 'request', 0, 'length', truth_id=1),
        ]

        # 不传 layout_id/direction
        aligned, unmatched_pred, unmatched_truth = align_predictions_with_truth(predictions, truths)

        assert len(aligned) == 1
        assert len(unmatched_pred) == 0
        assert len(unmatched_truth) == 0
