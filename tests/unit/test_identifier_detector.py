"""R133: IdentifierDetector 基础逻辑测试"""

import pytest

from semantic_detector.config import Config
from semantic_detector.detectors.identifier import IdentifierDetector
from semantic_detector.profiling.profile_builder import FieldProfile


class TestIdentifierDetectorBasic:
    """Tests for IdentifierDetector basic functionality."""
    
    def test_detector_name(self):
        """Detector name should be 'identifier'."""
        config = Config()
        detector = IdentifierDetector(config)
        assert detector.name == "identifier"
    
    def test_insufficient_samples_returns_abstain(self):
        """Insufficient samples should return abstain evidence."""
        config = Config(min_samples=8)
        detector = IdentifierDetector(config)
        
        profile = FieldProfile(
            sample_count=7,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.0,
            unique_ratio=0.95
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) == 1
        assert evidences[0].reason_code == "insufficient_samples"
    
    def test_variable_width_returns_empty(self):
        """Variable width field should return empty list."""
        config = Config()
        detector = IdentifierDetector(config)
        
        profile = FieldProfile(
            sample_count=10,
            fixed_width=False,
            width_mode=4,
            dominant_value_ratio=0.0,
            unique_ratio=0.95
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) == 0
    
    def test_constant_field_returns_empty(self):
        """Constant field should return empty list."""
        config = Config()
        detector = IdentifierDetector(config)
        
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.99,
            unique_ratio=0.95
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) == 0


class TestIdentifierDetectorHighUnique:
    """Tests for IdentifierDetector high unique ratio detection."""
    
    def test_high_unique_non_increasing_detected(self):
        """High unique ratio non-increasing data should be detected."""
        config = Config(identifier_unique_ratio=0.80, identifier_score_cap=0.70)
        detector = IdentifierDetector(config)
        
        # High unique ratio, non-increasing
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.0,
            unique_ratio=0.95,
            numeric_be_strictly_increasing_ratio=0.10,
            numeric_le_strictly_increasing_ratio=0.10
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) >= 1
        assert evidences[0].coarse_label == "identifier"
        assert evidences[0].fine_label == "identifier_candidate"
        assert evidences[0].is_hard_evidence is False  # soft evidence
        assert evidences[0].score <= 0.70  # score cap
    
    def test_low_unique_ratio_returns_empty(self):
        """Low unique ratio should return empty list."""
        config = Config(identifier_unique_ratio=0.80)
        detector = IdentifierDetector(config)
        
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.0,
            unique_ratio=0.70,
            numeric_be_strictly_increasing_ratio=0.10,
            numeric_le_strictly_increasing_ratio=0.10
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) == 0
    
    def test_increasing_sequence_returns_empty(self):
        """Increasing sequence should return empty list."""
        config = Config()
        detector = IdentifierDetector(config)
        
        # High unique ratio but increasing
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.0,
            unique_ratio=0.95,
            numeric_be_strictly_increasing_ratio=0.95,
            numeric_le_strictly_increasing_ratio=0.0
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) == 0


class TestIdentifierDetectorScoreCap:
    """Tests for IdentifierDetector score cap."""
    
    def test_score_capped_at_config_value(self):
        """Score should be capped at config value."""
        config = Config(identifier_unique_ratio=0.80, identifier_score_cap=0.70)
        detector = IdentifierDetector(config)
        
        # Very high unique ratio
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.0,
            unique_ratio=0.99,
            numeric_be_strictly_increasing_ratio=0.10,
            numeric_le_strictly_increasing_ratio=0.10
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) >= 1
        assert evidences[0].score == 0.70  # capped at 0.70
    
    def test_score_not_capped_when_below_cap(self):
        """Score should not be capped when below cap."""
        config = Config(identifier_unique_ratio=0.80, identifier_score_cap=0.90)
        detector = IdentifierDetector(config)
        
        # Unique ratio below cap
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.0,
            unique_ratio=0.85,
            numeric_be_strictly_increasing_ratio=0.10,
            numeric_le_strictly_increasing_ratio=0.10
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) >= 1
        assert evidences[0].score == 0.85  # not capped


class TestIdentifierDetectorThresholdBoundary:
    """Tests for IdentifierDetector threshold boundary conditions."""
    
    def test_unique_ratio_below_threshold_returns_empty(self):
        """Unique ratio below threshold should return empty list."""
        config = Config(identifier_unique_ratio=0.80)
        detector = IdentifierDetector(config)
        
        # unique_ratio = 0.79 (below threshold 0.80)
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.0,
            unique_ratio=0.79,
            numeric_be_strictly_increasing_ratio=0.10,
            numeric_le_strictly_increasing_ratio=0.10
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) == 0
    
    def test_unique_ratio_at_threshold_returns_candidate(self):
        """Unique ratio at threshold should return candidate."""
        config = Config(identifier_unique_ratio=0.80, identifier_score_cap=0.90)
        detector = IdentifierDetector(config)
        
        # unique_ratio = 0.80 (at threshold)
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.0,
            unique_ratio=0.80,
            numeric_be_strictly_increasing_ratio=0.10,
            numeric_le_strictly_increasing_ratio=0.10
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) >= 1
        assert evidences[0].fine_label == "identifier_candidate"
    
    def test_unique_ratio_above_threshold_returns_candidate(self):
        """Unique ratio above threshold should return candidate."""
        config = Config(identifier_unique_ratio=0.80, identifier_score_cap=0.90)
        detector = IdentifierDetector(config)
        
        # unique_ratio = 0.81 (above threshold)
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.0,
            unique_ratio=0.81,
            numeric_be_strictly_increasing_ratio=0.10,
            numeric_le_strictly_increasing_ratio=0.10
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) >= 1
        assert evidences[0].fine_label == "identifier_candidate"


class TestIdentifierDetectorExcludeHardEvidence:
    """Tests for IdentifierDetector excluding when hard evidence exists."""
    
    def test_exclude_when_length_hard_evidence_exists(self):
        """Should not output identifier when length hard evidence exists."""
        config = Config(identifier_unique_ratio=0.80, identifier_score_cap=0.70)
        detector = IdentifierDetector(config)
        
        # Create a profile that would normally be detected as identifier
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.0,
            unique_ratio=0.95,
            numeric_be_strictly_increasing_ratio=0.10,
            numeric_le_strictly_increasing_ratio=0.10
        )
        
        # Create a hard evidence from length detector
        from semantic_detector.contracts import DetectorEvidence
        length_evidence = DetectorEvidence(
            detector="length",
            coarse_label="length",
            fine_label="total_length",
            score=0.95,
            is_hard_evidence=True,
            reason_code="length_detected",
            details={"byte_width": 4}
        )
        
        # Should not output identifier when hard evidence exists
        evidences = detector.detect(profile, existing_evidences=[length_evidence])
        assert len(evidences) == 0
    
    def test_output_when_soft_evidence_exists(self):
        """Should still output identifier when only soft evidence exists."""
        config = Config(identifier_unique_ratio=0.80, identifier_score_cap=0.70)
        detector = IdentifierDetector(config)
        
        # Create a profile that would normally be detected as identifier
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.0,
            unique_ratio=0.95,
            numeric_be_strictly_increasing_ratio=0.10,
            numeric_le_strictly_increasing_ratio=0.10
        )
        
        # Create a soft evidence from another detector
        from semantic_detector.contracts import DetectorEvidence
        soft_evidence = DetectorEvidence(
            detector="other",
            coarse_label="other",
            fine_label="other_candidate",
            score=0.50,
            is_hard_evidence=False,
            reason_code="soft_detected",
            details={}
        )
        
        # Should still output identifier when only soft evidence exists
        evidences = detector.detect(profile, existing_evidences=[soft_evidence])
        assert len(evidences) >= 1
        assert evidences[0].fine_label == "identifier_candidate"
    
    def test_output_when_no_existing_evidences(self):
        """Should output identifier when no existing evidences."""
        config = Config(identifier_unique_ratio=0.80, identifier_score_cap=0.70)
        detector = IdentifierDetector(config)
        
        # Create a profile that would normally be detected as identifier
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.0,
            unique_ratio=0.95,
            numeric_be_strictly_increasing_ratio=0.10,
            numeric_le_strictly_increasing_ratio=0.10
        )
        
        # Should output identifier when no existing evidences
        evidences = detector.detect(profile, existing_evidences=None)
        assert len(evidences) >= 1
        assert evidences[0].fine_label == "identifier_candidate"
        
        # Also test with empty list
        evidences = detector.detect(profile, existing_evidences=[])
        assert len(evidences) >= 1
        assert evidences[0].fine_label == "identifier_candidate"


class TestIdentifierDetectorEvidence:
    """Tests for IdentifierDetector evidence structure."""
    
    def test_evidence_has_required_fields(self):
        """Evidence should have all required fields."""
        config = Config(identifier_unique_ratio=0.80, identifier_score_cap=0.70)
        detector = IdentifierDetector(config)
        
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.0,
            unique_ratio=0.95,
            numeric_be_strictly_increasing_ratio=0.10,
            numeric_le_strictly_increasing_ratio=0.10
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) >= 1
        
        evidence = evidences[0]
        assert evidence.detector == "identifier"
        assert evidence.coarse_label == "identifier"
        assert evidence.fine_label == "identifier_candidate"
        assert evidence.score is not None
        assert evidence.details is not None
        assert "unique_ratio" in evidence.details
        assert "score_cap" in evidence.details
        assert "byte_width" in evidence.details
    
    def test_evidence_is_soft(self):
        """Evidence should be soft evidence."""
        config = Config(identifier_unique_ratio=0.80, identifier_score_cap=0.70)
        detector = IdentifierDetector(config)
        
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.0,
            unique_ratio=0.95,
            numeric_be_strictly_increasing_ratio=0.10,
            numeric_le_strictly_increasing_ratio=0.10
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) >= 1
        assert evidences[0].is_hard_evidence is False


class TestIdentifierDetectorCanonicalLabel:
    """R236: identifier detector coarse_label 统一为标准标签 identifier

    03 教程 7.3：coarse_label=identifier, fine_label=identifier_candidate,
    is_hard_evidence=False。candidate 状态由 fine_label 表达，不混入 coarse_label。
    """

    def test_coarse_label_is_canonical_identifier(self):
        """coarse_label 必须是 taxonomy 标准标签 identifier。"""
        from semantic_detector.taxonomy import (
            CANONICAL_COARSE_LABELS,
            is_canonical_coarse_label,
        )

        config = Config(identifier_unique_ratio=0.80, identifier_score_cap=0.70)
        detector = IdentifierDetector(config)

        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.0,
            unique_ratio=0.95,
            numeric_be_strictly_increasing_ratio=0.10,
            numeric_le_strictly_increasing_ratio=0.10,
        )

        evidences = detector.detect(profile)
        assert len(evidences) >= 1
        assert evidences[0].coarse_label == "identifier"
        assert is_canonical_coarse_label(evidences[0].coarse_label) is True
        assert "identifier" in CANONICAL_COARSE_LABELS

    def test_candidate_status_in_fine_label_not_coarse(self):
        """candidate 状态由 fine_label 表达，coarse_label 不含 candidate。"""
        config = Config(identifier_unique_ratio=0.80, identifier_score_cap=0.70)
        detector = IdentifierDetector(config)

        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.0,
            unique_ratio=0.95,
            numeric_be_strictly_increasing_ratio=0.10,
            numeric_le_strictly_increasing_ratio=0.10,
        )

        evidences = detector.detect(profile)
        assert len(evidences) >= 1
        # coarse_label 是纯语义类别，不含 candidate
        assert evidences[0].coarse_label == "identifier"
        assert "candidate" not in evidences[0].coarse_label
        # candidate 状态在 fine_label
        assert evidences[0].fine_label == "identifier_candidate"

    def test_identifier_detector_constants_reference_taxonomy(self):
        """检测器 COARSE_LABEL 常量与 taxonomy 标准标签一致。"""
        from semantic_detector.taxonomy import CANONICAL_COARSE_LABELS

        assert IdentifierDetector.COARSE_LABEL == "identifier"
        assert IdentifierDetector.COARSE_LABEL in CANONICAL_COARSE_LABELS
        assert IdentifierDetector.FINE_LABEL == "identifier_candidate"
