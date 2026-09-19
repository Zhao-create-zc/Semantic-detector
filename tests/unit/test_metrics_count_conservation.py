"""R400：评价数量守恒检查测试

验证 verify_count_conservation 函数能正确检测守恒和不守恒场景。

R400 计划要求：
- 在没有 rejected duplicate 的正式评价中必须满足：
  - matched_predictions + unmatched_predictions = total_predictions
  - matched_truths + missing_predictions = total_truths
- 若不满足：valid_for_reporting=false, status=internal_count_inconsistency

R399 修复后 duplicate FieldKey 会抛 ValueError，正常路径下不会出现不守恒。
本测试覆盖 verify_count_conservation 的检测能力（防御性检查）。
"""

import pytest

from semantic_detector.contracts import (
    FieldKey,
    Direction,
    SemanticPrediction,
    DetectorEvidence,
)
from semantic_detector.evaluation.ground_truth import GroundTruthRecord
from semantic_detector.evaluation.metrics import (
    AlignedPair,
    verify_count_conservation,
    align_predictions_with_truth,
)


def _make_prediction(
    run_id: str = "r1",
    layout_id: str = "L1",
    direction: Direction = Direction.REQUEST,
    field_index: int = 0,
    coarse_label: str = "constant",
) -> SemanticPrediction:
    """构造最小 SemanticPrediction 用于测试"""
    evidence = DetectorEvidence(
        detector="constant",
        coarse_label=coarse_label,
        fine_label=coarse_label,
        score=1.0,
        is_hard_evidence=True,
        reason_code="constant",
        details={"field_index": field_index},
    )
    return SemanticPrediction(
        run_id=run_id,
        layout_id=layout_id,
        direction=direction,
        field_index=field_index,
        coarse_label=coarse_label,
        fine_label=coarse_label,
        confidence=1.0,
        abstained=False,
        evidence=(evidence,),
        alternatives=(),
    )


def _make_truth(
    truth_id: int = 1,
    layout_id: str = "L1",
    direction: str = "request",
    field_index: int = 0,
    semantic_label: str = "constant",
) -> GroundTruthRecord:
    """构造最小 GroundTruthRecord 用于测试"""
    return GroundTruthRecord(
        truth_id=truth_id,
        field_index=field_index,
        semantic_label=semantic_label,
        confidence=1.0,
        is_hard_evidence=True,
        layout_id=layout_id,
        direction=direction,
    )


def _make_matched_pair(
    layout_id: str = "L1",
    direction: Direction = Direction.REQUEST,
    field_index: int = 0,
) -> AlignedPair:
    """构造已匹配的 AlignedPair 用于守恒检查测试"""
    pred = _make_prediction(layout_id=layout_id, direction=direction, field_index=field_index)
    truth = _make_truth(
        layout_id=layout_id,
        direction=direction.value,
        field_index=field_index,
    )
    return AlignedPair(
        field_key=FieldKey(layout_id=layout_id, direction=direction, field_index=field_index),
        prediction=pred,
        truth=truth,
        is_matched=True,
    )


class TestCountConservationR400:
    """R400：评价数量守恒检查测试"""

    def test_r400_conserved_when_all_matched(self) -> None:
        """R400: 所有 prediction 和 truth 都匹配——守恒"""
        pred = _make_prediction(field_index=0)
        truth = _make_truth(field_index=0)

        aligned, unmatched_pred, unmatched_truth = align_predictions_with_truth(
            [pred], [truth]
        )

        result = verify_count_conservation(
            aligned, unmatched_pred, unmatched_truth,
            total_predictions=1, total_truths=1,
        )

        assert result.valid_for_reporting is True
        assert result.status == "count_conserved"
        assert result.matched_predictions == 1
        assert result.unmatched_predictions == 0
        assert result.matched_truths == 1
        assert result.missing_predictions == 0
        assert result.message == ""

    def test_r400_conserved_with_unmatched_prediction(self) -> None:
        """R400: 有未匹配 prediction（pred 多于 truth）——守恒"""
        pred1 = _make_prediction(run_id="r1", field_index=0)
        pred2 = _make_prediction(run_id="r2", field_index=1)  # 无对应 truth
        truth = _make_truth(field_index=0)

        aligned, unmatched_pred, unmatched_truth = align_predictions_with_truth(
            [pred1, pred2], [truth]
        )

        result = verify_count_conservation(
            aligned, unmatched_pred, unmatched_truth,
            total_predictions=2, total_truths=1,
        )

        assert result.valid_for_reporting is True
        assert result.status == "count_conserved"
        assert result.matched_predictions == 1
        assert result.unmatched_predictions == 1
        assert result.matched_truths == 1
        assert result.missing_predictions == 0

    def test_r400_conserved_with_missing_prediction(self) -> None:
        """R400: 有 missing prediction（truth 多于 pred）——守恒"""
        pred = _make_prediction(field_index=0)
        truth1 = _make_truth(truth_id=1, field_index=0)
        truth2 = _make_truth(truth_id=2, field_index=1)  # 无对应 pred

        aligned, unmatched_pred, unmatched_truth = align_predictions_with_truth(
            [pred], [truth1, truth2]
        )

        result = verify_count_conservation(
            aligned, unmatched_pred, unmatched_truth,
            total_predictions=1, total_truths=2,
        )

        assert result.valid_for_reporting is True
        assert result.status == "count_conserved"
        assert result.matched_predictions == 1
        assert result.unmatched_predictions == 0
        assert result.matched_truths == 1
        assert result.missing_predictions == 1

    def test_r400_inconsistency_predictions_lost(self) -> None:
        """R400: total_predictions=2 但 matched+unmatched=1（丢失 1 个 prediction）

        模拟 R400 计划描述的不守恒场景：
            total_predictions=2
            matched=1
            unmatched_predictions=0
        这是 R399 修复前 duplicate 静默覆盖导致的典型不守恒。
        """
        # 构造 1 个 matched pair，unmatched_pred 和 unmatched_truth 都为空
        # 但 total_predictions=2，说明 1 个 prediction 丢失了
        aligned = [_make_matched_pair(field_index=0)]
        unmatched_pred: list = []
        unmatched_truth: list = []

        result = verify_count_conservation(
            aligned, unmatched_pred, unmatched_truth,
            total_predictions=2, total_truths=1,
        )

        assert result.valid_for_reporting is False
        assert result.status == "internal_count_inconsistency"
        assert result.matched_predictions == 1
        assert result.unmatched_predictions == 0
        assert "predictions 1+0=1 != total 2" in result.message

    def test_r400_inconsistency_truths_lost(self) -> None:
        """R400: total_truths=2 但 matched+missing=1（丢失 1 个 truth）"""
        aligned = [_make_matched_pair(field_index=0)]
        unmatched_pred: list = []
        unmatched_truth: list = []

        result = verify_count_conservation(
            aligned, unmatched_pred, unmatched_truth,
            total_predictions=1, total_truths=2,
        )

        assert result.valid_for_reporting is False
        assert result.status == "internal_count_inconsistency"
        assert result.matched_truths == 1
        assert result.missing_predictions == 0
        assert "truths 1+0=1 != total 2" in result.message

    def test_r400_inconsistency_both_sides(self) -> None:
        """R400: 双侧都不守恒（predictions 和 truths 都丢失）"""
        aligned = [_make_matched_pair(field_index=0)]
        unmatched_pred: list = []
        unmatched_truth: list = []

        result = verify_count_conservation(
            aligned, unmatched_pred, unmatched_truth,
            total_predictions=3, total_truths=2,
        )

        assert result.valid_for_reporting is False
        assert result.status == "internal_count_inconsistency"
        assert "predictions 1+0=1 != total 3" in result.message
        assert "truths 1+0=1 != total 2" in result.message

    def test_r400_end_to_end_conserved_after_r399_fix(self) -> None:
        """R400 端到端：R399 修复后正常对齐路径应守恒

        R399 修复后 align_predictions_with_truth 不再静默覆盖 duplicate，
        正常路径下守恒检查应通过。
        """
        pred1 = _make_prediction(run_id="r1", field_index=0)
        pred2 = _make_prediction(run_id="r2", field_index=1)
        truth1 = _make_truth(truth_id=1, field_index=0)
        truth2 = _make_truth(truth_id=2, field_index=1)

        aligned, unmatched_pred, unmatched_truth = align_predictions_with_truth(
            [pred1, pred2], [truth1, truth2]
        )

        result = verify_count_conservation(
            aligned, unmatched_pred, unmatched_truth,
            total_predictions=2, total_truths=2,
        )

        assert result.valid_for_reporting is True
        assert result.status == "count_conserved"
        assert len(aligned) == 2
        assert len(unmatched_pred) == 0
        assert len(unmatched_truth) == 0

    def test_r400_duplicate_raises_before_conservation_check(self) -> None:
        """R400: R399 修复后 duplicate 在守恒检查之前就抛 ValueError

        验证 R399 + R400 的协同：duplicate 不再导致不守恒，
        而是在 align 阶段就被拒绝。
        """
        pred1 = _make_prediction(run_id="r1", field_index=0)
        pred2 = _make_prediction(run_id="r2", field_index=0)  # duplicate FieldKey

        with pytest.raises(ValueError, match="duplicate"):
            align_predictions_with_truth([pred1, pred2], [])

    def test_r400_empty_inputs_conserved(self) -> None:
        """R400: 空输入也守恒（边界情况）"""
        result = verify_count_conservation(
            [], [], [],
            total_predictions=0, total_truths=0,
        )

        assert result.valid_for_reporting is True
        assert result.status == "count_conserved"
        assert result.matched_predictions == 0
        assert result.unmatched_predictions == 0
        assert result.matched_truths == 0
        assert result.missing_predictions == 0
