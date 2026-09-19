"""R136: PayloadDetector 基础逻辑测试"""

import pytest

from semantic_detector.config import Config
from semantic_detector.detectors.payload import PayloadDetector
from semantic_detector.profiling.profile_builder import FieldProfile


class TestPayloadDetectorBasic:
    """Tests for PayloadDetector basic functionality."""
    
    def test_detector_name(self):
        """Detector name should be 'payload'."""
        config = Config()
        detector = PayloadDetector(config)
        assert detector.name == "payload"
    
    def test_insufficient_samples_returns_abstain(self):
        """Insufficient samples should return abstain evidence."""
        config = Config(min_samples=8)
        detector = PayloadDetector(config)
        
        profile = FieldProfile(
            sample_count=7,
            is_last_field_ratio=1.0,
            normalized_entropy=0.95
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) == 1
        assert evidences[0].reason_code == "insufficient_samples"
    
    def test_non_trailing_field_returns_empty(self):
        """Non-trailing field should return empty list."""
        config = Config()
        detector = PayloadDetector(config)
        
        profile = FieldProfile(
            sample_count=10,
            is_last_field_ratio=0.50,
            normalized_entropy=0.95
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) == 0


class TestPayloadDetectorHighEntropy:
    """Tests for PayloadDetector high entropy detection."""
    
    def test_high_entropy_trailing_field_detected(self):
        """High entropy trailing field should be detected."""
        config = Config(payload_entropy_threshold=0.70)
        detector = PayloadDetector(config)
        
        # High entropy, trailing field
        profile = FieldProfile(
            sample_count=10,
            is_last_field_ratio=1.0,
            normalized_entropy=0.95
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) >= 1
        assert evidences[0].coarse_label == "payload"
        assert evidences[0].fine_label == "opaque_payload_candidate"
        assert evidences[0].is_hard_evidence is False  # soft evidence
    
    def test_low_entropy_returns_empty(self):
        """Low entropy should return empty list."""
        config = Config(payload_entropy_threshold=0.70)
        detector = PayloadDetector(config)
        
        profile = FieldProfile(
            sample_count=10,
            is_last_field_ratio=1.0,
            normalized_entropy=0.50
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) == 0


class TestPayloadDetectorEvidence:
    """Tests for PayloadDetector evidence structure."""
    
    def test_evidence_has_required_fields(self):
        """Evidence should have all required fields."""
        config = Config(payload_entropy_threshold=0.70)
        detector = PayloadDetector(config)
        
        profile = FieldProfile(
            sample_count=10,
            is_last_field_ratio=1.0,
            normalized_entropy=0.95
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) >= 1
        
        evidence = evidences[0]
        assert evidence.detector == "payload"
        assert evidence.coarse_label == "payload"
        assert evidence.fine_label == "opaque_payload_candidate"
        assert evidence.score is not None
        assert evidence.details is not None
        assert "normalized_entropy" in evidence.details
        assert "entropy_threshold" in evidence.details
        assert "is_last_field_ratio" in evidence.details
        assert "byte_width" in evidence.details
    
    def test_evidence_is_soft(self):
        """Evidence should be soft evidence."""
        config = Config(payload_entropy_threshold=0.70)
        detector = PayloadDetector(config)
        
        profile = FieldProfile(
            sample_count=10,
            is_last_field_ratio=1.0,
            normalized_entropy=0.95
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) >= 1
        assert evidences[0].is_hard_evidence is False


class TestPayloadDetectorWarning:
    """Tests for PayloadDetector warning field."""
    
    def test_evidence_has_warning_field(self):
        """Evidence should have warning field."""
        config = Config(payload_entropy_threshold=0.70)
        detector = PayloadDetector(config)
        
        profile = FieldProfile(
            sample_count=10,
            is_last_field_ratio=1.0,
            normalized_entropy=0.95
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) >= 1
        assert "warning" in evidences[0].details
        assert evidences[0].details["warning"] == "可能是密文或压缩数据"
    
    def test_warning_content_is_meaningful(self):
        """Warning content should be meaningful."""
        config = Config(payload_entropy_threshold=0.70)
        detector = PayloadDetector(config)
        
        profile = FieldProfile(
            sample_count=10,
            is_last_field_ratio=1.0,
            normalized_entropy=0.95
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) >= 1
        warning = evidences[0].details["warning"]
        assert len(warning) > 0
        assert "密文" in warning or "压缩" in warning


class TestPayloadDetectorThresholdBoundary:
    """Tests for PayloadDetector threshold boundary conditions."""
    
    def test_entropy_below_threshold_returns_empty(self):
        """Entropy below threshold should return empty list."""
        config = Config(payload_entropy_threshold=0.70)
        detector = PayloadDetector(config)
        
        # normalized_entropy = 0.69 (below threshold 0.70)
        profile = FieldProfile(
            sample_count=10,
            is_last_field_ratio=1.0,
            normalized_entropy=0.69
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) == 0
    
    def test_entropy_at_threshold_returns_candidate(self):
        """Entropy at threshold should return candidate."""
        config = Config(payload_entropy_threshold=0.70)
        detector = PayloadDetector(config)
        
        # normalized_entropy = 0.70 (at threshold)
        profile = FieldProfile(
            sample_count=10,
            is_last_field_ratio=1.0,
            normalized_entropy=0.70
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) >= 1
        assert evidences[0].fine_label == "opaque_payload_candidate"
    
    def test_entropy_above_threshold_returns_candidate(self):
        """Entropy above threshold should return candidate."""
        config = Config(payload_entropy_threshold=0.70)
        detector = PayloadDetector(config)
        
        # normalized_entropy = 0.71 (above threshold)
        profile = FieldProfile(
            sample_count=10,
            is_last_field_ratio=1.0,
            normalized_entropy=0.71
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) >= 1
        assert evidences[0].fine_label == "opaque_payload_candidate"
    
    def test_trailing_ratio_below_threshold_returns_empty(self):
        """Trailing ratio below 0.90 should return empty list."""
        config = Config(payload_entropy_threshold=0.70)
        detector = PayloadDetector(config)
        
        # is_last_field_ratio = 0.89 (below 0.90)
        profile = FieldProfile(
            sample_count=10,
            is_last_field_ratio=0.89,
            normalized_entropy=0.95
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) == 0
    
    def test_trailing_ratio_at_threshold_returns_candidate(self):
        """Trailing ratio at 0.90 should return candidate."""
        config = Config(payload_entropy_threshold=0.70)
        detector = PayloadDetector(config)
        
        # is_last_field_ratio = 0.90 (at threshold)
        profile = FieldProfile(
            sample_count=10,
            is_last_field_ratio=0.90,
            normalized_entropy=0.95
        )

        evidences = detector.detect(profile)
        assert len(evidences) >= 1
        assert evidences[0].fine_label == "opaque_payload_candidate"


class TestPayloadDetectorCanonicalLabel:
    """R237: payload detector coarse_label 统一为标准标签 payload

    03 教程 7.3：coarse_label=payload, fine_label=opaque_payload_candidate,
    is_hard_evidence=False。candidate 状态由 fine_label 表达。
    """

    def _make_detector(self):
        from semantic_detector.config import Config
        return PayloadDetector(Config())

    def _make_high_entropy_profile(self):
        return FieldProfile(
            sample_count=10,
            is_last_field_ratio=1.0,
            normalized_entropy=0.95,
        )

    def test_coarse_label_is_canonical_payload(self):
        """coarse_label 必须是 taxonomy 标准标签 payload。"""
        from semantic_detector.taxonomy import (
            CANONICAL_COARSE_LABELS,
            is_canonical_coarse_label,
        )

        detector = self._make_detector()
        evidences = detector.detect(self._make_high_entropy_profile())
        assert len(evidences) >= 1
        assert evidences[0].coarse_label == "payload"
        assert is_canonical_coarse_label(evidences[0].coarse_label) is True
        assert "payload" in CANONICAL_COARSE_LABELS

    def test_fine_label_is_opaque_payload_candidate(self):
        """fine_label 必须是 opaque_payload_candidate。"""
        detector = self._make_detector()
        evidences = detector.detect(self._make_high_entropy_profile())
        assert len(evidences) >= 1
        assert evidences[0].fine_label == "opaque_payload_candidate"

    def test_payload_detector_constants_reference_taxonomy(self):
        """检测器 COARSE_LABEL 常量与 taxonomy 标准标签一致。"""
        from semantic_detector.taxonomy import CANONICAL_COARSE_LABELS

        assert PayloadDetector.COARSE_LABEL == "payload"
        assert PayloadDetector.COARSE_LABEL in CANONICAL_COARSE_LABELS
        assert PayloadDetector.FINE_LABEL == "opaque_payload_candidate"

