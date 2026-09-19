"""Tests for the DetectorEvidence contract."""

import pytest
from semantic_detector.contracts import DetectorEvidence


def test_detector_evidence_stores_minimal_fields() -> None:
    """测试 DetectorEvidence 存储最小字段"""
    evidence = DetectorEvidence(
        detector="constant",
        coarse_label="constant",
        fine_label="constant",
        score=0.98,
        is_hard_evidence=True,
        reason_code="dominant_value_ratio_high",
    )
    
    assert evidence.detector == "constant"
    assert evidence.coarse_label == "constant"
    assert evidence.fine_label == "constant"
    assert evidence.score == 0.98
    assert evidence.is_hard_evidence is True
    assert evidence.reason_code == "dominant_value_ratio_high"


def test_detector_evidence_with_optional_details() -> None:
    """测试 DetectorEvidence 包含可选 details"""
    evidence = DetectorEvidence(
        detector="constant",
        coarse_label="constant",
        fine_label="constant",
        score=0.98,
        is_hard_evidence=True,
        reason_code="dominant_value_ratio_high",
        details={"dominant_value": b'\x00\x01'},
    )
    
    assert evidence.details == {"dominant_value": b'\x00\x01'}


def test_detector_evidence_score_boundary_zero() -> None:
    """测试分数边界 0.0"""
    evidence = DetectorEvidence(
        detector="test",
        coarse_label="test",
        fine_label="test",
        score=0.0,
        is_hard_evidence=False,
        reason_code="test",
    )
    
    assert evidence.score == 0.0


def test_detector_evidence_score_boundary_one() -> None:
    """测试分数边界 1.0"""
    evidence = DetectorEvidence(
        detector="test",
        coarse_label="test",
        fine_label="test",
        score=1.0,
        is_hard_evidence=True,
        reason_code="test",
    )
    
    assert evidence.score == 1.0


def test_detector_evidence_rejects_negative_score() -> None:
    """测试拒绝负数分数"""
    with pytest.raises(ValueError) as exc_info:
        DetectorEvidence(
            detector="test",
            coarse_label="test",
            fine_label="test",
            score=-0.1,
            is_hard_evidence=False,
            reason_code="test",
        )
    assert "score must be between 0.0 and 1.0" in str(exc_info.value)


def test_detector_evidence_rejects_score_above_one() -> None:
    """测试拒绝超过 1.0 的分数"""
    with pytest.raises(ValueError) as exc_info:
        DetectorEvidence(
            detector="test",
            coarse_label="test",
            fine_label="test",
            score=1.1,
            is_hard_evidence=False,
            reason_code="test",
        )
    assert "score must be between 0.0 and 1.0" in str(exc_info.value)