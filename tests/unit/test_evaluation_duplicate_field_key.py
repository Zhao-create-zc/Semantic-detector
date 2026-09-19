"""R398：规范化后重复 FieldKey 失败测试

复现缺陷：align_predictions_with_truth 在构建 pred_by_key/truth_by_key 字典时，
如果两条 Prediction（或两条 Truth）最终归一到同一 FieldKey，后值会静默覆盖前值，
不产生 duplicate reason_code，评价不失败。

R398 计划要求（修复前测试应真实失败，本轮不修改生产代码）：
- 确保唯一性检查发生在规范化后的完整键上
- 两条 Prediction 最终归一到同一 (layout_id, direction, field_index)
- 两条 Ground Truth 最终归一到同一键
- 评价失败；不允许字典后值覆盖前值；输出 duplicate reason_code

当前缺陷（align_predictions_with_truth 第 125-136 行）：
    pred_by_key: Dict[FieldKey, object] = {}
    for pred in predictions:
        key = _extract_field_key_from_prediction(pred)
        ...
        pred_by_key[key] = pred  # 缺陷：后值静默覆盖前值

    truth_by_key: Dict[FieldKey, GroundTruthRecord] = {}
    for truth in truths:
        truth_by_key[truth.field_key] = truth  # 缺陷：后值静默覆盖前值

R399 修复后：align_predictions_with_truth 应检测 duplicate FieldKey，
抛 ValueError 或返回 duplicate rejection，不静默覆盖。
"""

import pytest

from semantic_detector.contracts import (
    SemanticPrediction,
    DetectorEvidence,
    Direction,
)
from semantic_detector.evaluation.ground_truth import GroundTruthRecord
from semantic_detector.evaluation.metrics import align_predictions_with_truth


def _make_semantic_prediction(
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


def _make_truth_record(
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


class TestEvaluationDuplicateFieldKeyR398:
    """R398：规范化后重复 FieldKey 失败测试

    复现缺陷：align_predictions_with_truth 静默覆盖 duplicate FieldKey。
    修复前：不检测 duplicate，后值覆盖前值，评价不失败。
    修复后（R399）：应检测 duplicate，抛 ValueError 或返回 duplicate rejection。
    """

    def test_r398_duplicate_prediction_field_key_must_fail(self) -> None:
        """R398: 两条 Prediction 归一到同一 FieldKey，评价应失败

        场景：两条 SemanticPrediction 有相同 (layout_id, direction, field_index)
        当前缺陷：pred_by_key[key] = pred 后值覆盖前值，aligned 只有 1 个
        R398 断言：应检测到 duplicate，抛 ValueError
        """
        pred1 = _make_semantic_prediction(run_id="r1", field_index=0)
        pred2 = _make_semantic_prediction(run_id="r2", field_index=0)  # 相同 FieldKey

        # R398 断言：应检测到 duplicate FieldKey，抛 ValueError
        # 当前缺陷：不抛异常，静默覆盖
        with pytest.raises(ValueError, match="duplicate"):
            align_predictions_with_truth([pred1, pred2], [])

    def test_r398_duplicate_truth_field_key_must_fail(self) -> None:
        """R398: 两条 Truth 归一到同一 FieldKey，评价应失败

        场景：两条 GroundTruthRecord 有相同 (layout_id, direction, field_index)
        当前缺陷：truth_by_key[key] = truth 后值覆盖前值
        R398 断言：应检测到 duplicate，抛 ValueError
        """
        truth1 = _make_truth_record(truth_id=1, field_index=0)
        truth2 = _make_truth_record(truth_id=2, field_index=0)  # 相同 FieldKey

        # R398 断言：应检测到 duplicate FieldKey，抛 ValueError
        # 当前缺陷：不抛异常，静默覆盖
        with pytest.raises(ValueError, match="duplicate"):
            align_predictions_with_truth([], [truth1, truth2])

    def test_r398_duplicate_prediction_not_silently_overwritten(self) -> None:
        """R398: 两条 Prediction 归一到同一 FieldKey，不允许字典后值覆盖前值

        当前缺陷：aligned 只有 1 个（后值覆盖前值），unmatched_predictions 为空
        R398 断言：应检测到 duplicate，不静默覆盖
        """
        pred1 = _make_semantic_prediction(run_id="r1", field_index=0, coarse_label="constant")
        pred2 = _make_semantic_prediction(run_id="r2", field_index=0, coarse_label="payload")
        truth = _make_truth_record(truth_id=1, field_index=0)

        # R398 断言：应检测到 duplicate，抛 ValueError
        # 当前缺陷：不抛异常，pred2 覆盖 pred1，aligned=[pred2+truth]
        with pytest.raises(ValueError, match="duplicate"):
            align_predictions_with_truth([pred1, pred2], [truth])

    def test_r398_duplicate_truth_not_silently_overwritten(self) -> None:
        """R398: 两条 Truth 归一到同一 FieldKey，不允许字典后值覆盖前值

        当前缺陷：truth_by_key 后值覆盖前值，aligned 用 truth2
        R398 断言：应检测到 duplicate，抛 ValueError
        """
        pred = _make_semantic_prediction(run_id="r1", field_index=0)
        truth1 = _make_truth_record(truth_id=1, field_index=0, semantic_label="constant")
        truth2 = _make_truth_record(truth_id=2, field_index=0, semantic_label="payload")

        # R398 断言：应检测到 duplicate，抛 ValueError
        # 当前缺陷：不抛异常，truth2 覆盖 truth1
        with pytest.raises(ValueError, match="duplicate"):
            align_predictions_with_truth([pred], [truth1, truth2])

    def test_r398_unique_field_keys_still_aligned(self) -> None:
        """R398 正向对照：不同 FieldKey 正常对齐

        验证修复后不会误伤正常对齐（不同 field_index 不算 duplicate）。
        """
        pred = _make_semantic_prediction(run_id="r1", field_index=0)
        truth = _make_truth_record(truth_id=1, field_index=0)

        # 不同 field_index 不算 duplicate
        pred2 = _make_semantic_prediction(run_id="r2", field_index=1)
        truth2 = _make_truth_record(truth_id=2, field_index=1)

        aligned, unmatched_pred, unmatched_truth = align_predictions_with_truth(
            [pred, pred2], [truth, truth2]
        )

        assert len(aligned) == 2, (
            f"R398 正向对照：2 个不同 FieldKey 应对齐 2 个，"
            f"got {len(aligned)}"
        )
        assert len(unmatched_pred) == 0
        assert len(unmatched_truth) == 0

    def test_r398_duplicate_after_normalization(self) -> None:
        """R398: 规范化后归一到同一 FieldKey 也应失败

        场景：两条 Prediction 的 direction 一个是 Direction.REQUEST，
        另一个也是 Direction.REQUEST（相同枚举），field_index 相同
        当前缺陷：_extract_field_key_from_prediction 返回相同 FieldKey，静默覆盖
        R398 断言：应检测到 duplicate
        """
        pred1 = _make_semantic_prediction(
            run_id="r1", direction=Direction.REQUEST, field_index=0
        )
        pred2 = _make_semantic_prediction(
            run_id="r2", direction=Direction.REQUEST, field_index=0
        )

        # R398 断言：规范化后相同 FieldKey 也应检测到 duplicate
        with pytest.raises(ValueError, match="duplicate"):
            align_predictions_with_truth([pred1, pred2], [])
