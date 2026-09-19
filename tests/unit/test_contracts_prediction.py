"""R234: SemanticPrediction prediction_status 校验测试

03 教程 6.3：为 SemanticPrediction 增加 prediction_status 字段，
允许值 confirmed / candidate / abstained，非法值被拒绝，旧字段保留。
"""

import pytest
from semantic_detector.contracts import (
    DetectorEvidence,
    Direction,
    SemanticPrediction,
)


def _make_evidence(is_hard=True, score=0.9, coarse_label="length"):
    return DetectorEvidence(
        detector="test_detector",
        coarse_label=coarse_label,
        fine_label="message_length",
        score=score,
        is_hard_evidence=is_hard,
        reason_code="test_reason",
    )


class TestSemanticPredictionPredictionStatus:
    """R234: prediction_status 字段校验"""

    def _make_prediction(self, **kwargs):
        defaults = dict(
            run_id="run-1",
            layout_id="L1",
            direction=Direction.REQUEST,
            field_index=0,
            coarse_label="length",
            fine_label="message_length",
            confidence=0.9,
            abstained=False,
            evidence=(_make_evidence(),),
            alternatives=(),
            prediction_status="confirmed",
        )
        defaults.update(kwargs)
        return SemanticPrediction(**defaults)

    def test_confirmed_is_valid(self):
        """hard evidence 选中 → prediction_status=confirmed 合法。"""
        pred = self._make_prediction(prediction_status="confirmed")
        assert pred.prediction_status == "confirmed"

    def test_candidate_is_valid(self):
        """soft evidence 选中 → prediction_status=candidate 合法。"""
        pred = self._make_prediction(prediction_status="candidate")
        assert pred.prediction_status == "candidate"

    def test_abstained_is_valid(self):
        """unknown 拒识 → prediction_status=abstained 合法。"""
        pred = self._make_prediction(
            prediction_status="abstained",
            coarse_label="unknown",
            fine_label="unknown",
            confidence=0.0,
            abstained=True,
            evidence=(),
        )
        assert pred.prediction_status == "abstained"

    def test_invalid_status_rejected(self):
        """非法 prediction_status 值被拒绝。"""
        with pytest.raises(ValueError, match="prediction_status must be one of"):
            self._make_prediction(prediction_status="invalid_status")

    def test_empty_status_rejected(self):
        """空字符串 prediction_status 被拒绝。"""
        with pytest.raises(ValueError, match="prediction_status must be one of"):
            self._make_prediction(prediction_status="")

    def test_default_status_is_abstained(self):
        """不传 prediction_status 时默认 abstained（安全默认）。"""
        pred = SemanticPrediction(
            run_id="run-1",
            layout_id="L1",
            direction=Direction.REQUEST,
            field_index=0,
            coarse_label="unknown",
            fine_label="unknown",
            confidence=0.0,
            abstained=True,
            evidence=(),
            alternatives=(),
        )
        assert pred.prediction_status == "abstained"

    def test_old_fields_preserved(self):
        """R234: 新增字段不破坏旧字段。"""
        pred = self._make_prediction()
        # 旧字段全部保留
        assert pred.run_id == "run-1"
        assert pred.layout_id == "L1"
        assert pred.direction == Direction.REQUEST
        assert pred.field_index == 0
        assert pred.coarse_label == "length"
        assert pred.fine_label == "message_length"
        assert pred.confidence == 0.9
        assert pred.abstained is False
        assert len(pred.evidence) == 1
        assert pred.alternatives == ()
        assert pred.config_summary is None

    def test_prediction_status_is_hashable_with_field(self):
        """frozen dataclass 新增字段后仍可哈希。"""
        pred = self._make_prediction(prediction_status="confirmed")
        assert hash(pred) == hash(pred)

    def test_prediction_status_constants_exposed(self):
        """PREDICTION_STATUSES 常量对外暴露，供其他模块引用。"""
        assert SemanticPrediction.PREDICTION_STATUSES == (
            "confirmed",
            "candidate",
            "abstained",
        )
