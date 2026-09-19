"""
Tests for SequenceDetector.
"""

import pytest
from datetime import datetime, timezone
from semantic_detector.detectors.sequence import SequenceDetector
from semantic_detector.profiling.profile_builder import FieldProfile
from semantic_detector.config import Config


class TestSequenceDetectorBasic:
    """Basic tests for SequenceDetector."""
    
    def test_detector_name(self):
        """Detector name should be 'sequence'."""
        config = Config()
        detector = SequenceDetector(config)
        assert detector.name == "sequence"
    
    def test_insufficient_samples_returns_abstain(self):
        """Insufficient samples should return abstain evidence."""
        config = Config(min_samples=8)
        detector = SequenceDetector(config)
        
        profile = FieldProfile(
            sample_count=5,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.0,
            unique_ratio=0.9
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) == 1
        assert evidences[0].is_hard_evidence is False
        assert "insufficient_samples" in evidences[0].reason_code
    
    def test_variable_width_returns_empty(self):
        """Variable width field should return empty list."""
        config = Config()
        detector = SequenceDetector(config)
        
        profile = FieldProfile(
            sample_count=10,
            fixed_width=False,
            width_mode=4,
            dominant_value_ratio=0.0,
            unique_ratio=0.9
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) == 0
    
    def test_width_greater_than_8_returns_empty(self):
        """Width > 8 should return empty list."""
        config = Config()
        detector = SequenceDetector(config)
        
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=16,
            dominant_value_ratio=0.0,
            unique_ratio=0.9
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) == 0
    
    def test_constant_field_returns_empty(self):
        """Constant field should return empty list."""
        config = Config()
        detector = SequenceDetector(config)
        
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.99,
            unique_ratio=0.9
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) == 0
    
    def test_low_unique_ratio_returns_empty(self):
        """Low unique ratio field should return empty list."""
        config = Config()
        detector = SequenceDetector(config)
        
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.0,
            unique_ratio=0.3
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) == 0
    
    def test_increasing_illusion_with_low_unique_ratio(self):
        """Increasing illusion with low unique ratio should not be detected.
        
        This tests the case where numeric_be_strictly_increasing_ratio is high,
        but unique_ratio is low (e.g., repeated values like 1,2,1,2,1,2).
        """
        config = Config(sequence_increasing_ratio=0.80)
        detector = SequenceDetector(config)
        
        # 递增假象：numeric_be_strictly_increasing_ratio = 0.9
        # 但唯一率低：unique_ratio = 0.3
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.0,
            unique_ratio=0.3,  # 低唯一率
            numeric_be_strictly_increasing_ratio=0.9,  # 递增假象
            numeric_be_step_one_ratio=None
        )
        
        evidences = detector.detect(profile)
        # 不得命中，因为唯一率低
        assert len(evidences) == 0


class TestSequenceDetectorBE:
    """Tests for SequenceDetector BE detection."""
    
    def test_be_strictly_increasing_sequence(self):
        """BE strictly increasing sequence should be detected."""
        config = Config(sequence_increasing_ratio=0.80)
        detector = SequenceDetector(config)
        
        # 严格递增序列，支持率 1.0
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.0,
            unique_ratio=0.9,
            numeric_be_strictly_increasing_ratio=1.0,
            numeric_be_step_one_ratio=1.0
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) >= 1
        assert evidences[0].coarse_label == "sequence_or_counter"
        assert "be" in evidences[0].fine_label
        assert evidences[0].score >= 0.80
    
    def test_be_partially_increasing_sequence(self):
        """BE partially increasing sequence should be detected if above threshold."""
        config = Config(sequence_increasing_ratio=0.80)
        detector = SequenceDetector(config)
        
        # 部分递增序列，支持率 0.85
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.0,
            unique_ratio=0.9,
            numeric_be_strictly_increasing_ratio=0.85,
            numeric_be_step_one_ratio=None
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) >= 1
        assert evidences[0].coarse_label == "sequence_or_counter"
        assert "be" in evidences[0].fine_label
    
    def test_be_below_threshold_returns_empty(self):
        """BE sequence below threshold should return empty list."""
        config = Config(sequence_increasing_ratio=0.80)
        detector = SequenceDetector(config)
        
        # 支持率 0.75 < 0.80
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.0,
            unique_ratio=0.9,
            numeric_be_strictly_increasing_ratio=0.75,
            numeric_be_step_one_ratio=None
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) == 0
    
    def test_be_step_one_priority(self):
        """BE step-one should have priority over strictly increasing."""
        config = Config(sequence_increasing_ratio=0.80)
        detector = SequenceDetector(config)
        
        # step_one_ratio = 0.9, strictly_increasing_ratio = 0.95
        # 应该返回 step_one_ratio = 0.9（因为 >= 0.7）
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.0,
            unique_ratio=0.9,
            numeric_be_strictly_increasing_ratio=0.95,
            numeric_be_step_one_ratio=0.9
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) >= 1
        # step_one_ratio 优先，所以应该返回 0.9
        assert evidences[0].score == 0.9
    
    def test_be_16bit_sequence(self):
        """BE 16-bit sequence should be detected."""
        config = Config(sequence_increasing_ratio=0.80)
        detector = SequenceDetector(config)
        
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=2,
            dominant_value_ratio=0.0,
            unique_ratio=0.9,
            numeric_be_strictly_increasing_ratio=1.0,
            numeric_be_step_one_ratio=1.0
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) >= 1
        assert "16bit" in evidences[0].fine_label
        assert "be" in evidences[0].fine_label


class TestSequenceDetectorLE:
    """Tests for SequenceDetector LE detection."""
    
    def test_le_strictly_increasing_sequence(self):
        """LE strictly increasing sequence should be detected."""
        config = Config(sequence_increasing_ratio=0.80)
        detector = SequenceDetector(config)
        
        # 严格递增序列，支持率 1.0
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.0,
            unique_ratio=0.9,
            numeric_le_strictly_increasing_ratio=1.0,
            numeric_le_step_one_ratio=1.0
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) >= 1
        assert evidences[0].coarse_label == "sequence_or_counter"
        assert "le" in evidences[0].fine_label
        assert evidences[0].score >= 0.80
    
    def test_le_partially_increasing_sequence(self):
        """LE partially increasing sequence should be detected if above threshold."""
        config = Config(sequence_increasing_ratio=0.80)
        detector = SequenceDetector(config)
        
        # 部分递增序列，支持率 0.85
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.0,
            unique_ratio=0.9,
            numeric_le_strictly_increasing_ratio=0.85,
            numeric_le_step_one_ratio=None
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) >= 1
        assert evidences[0].coarse_label == "sequence_or_counter"
        assert "le" in evidences[0].fine_label
    
    def test_le_below_threshold_returns_empty(self):
        """LE sequence below threshold should return empty list."""
        config = Config(sequence_increasing_ratio=0.80)
        detector = SequenceDetector(config)
        
        # 支持率 0.75 < 0.80
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.0,
            unique_ratio=0.9,
            numeric_le_strictly_increasing_ratio=0.75,
            numeric_le_step_one_ratio=None
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) == 0
    
    def test_le_step_one_priority(self):
        """LE step-one should have priority over strictly increasing."""
        config = Config(sequence_increasing_ratio=0.80)
        detector = SequenceDetector(config)
        
        # step_one_ratio = 0.9, strictly_increasing_ratio = 0.95
        # 应该返回 step_one_ratio = 0.9（因为 >= 0.7）
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.0,
            unique_ratio=0.9,
            numeric_le_strictly_increasing_ratio=0.95,
            numeric_le_step_one_ratio=0.9
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) >= 1
        # step_one_ratio 优先，所以应该返回 0.9
        assert evidences[0].score == 0.9
    
    def test_le_16bit_sequence(self):
        """LE 16-bit sequence should be detected."""
        config = Config(sequence_increasing_ratio=0.80)
        detector = SequenceDetector(config)
        
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=2,
            dominant_value_ratio=0.0,
            unique_ratio=0.9,
            numeric_le_strictly_increasing_ratio=1.0,
            numeric_le_step_one_ratio=1.0
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) >= 1
        assert "16bit" in evidences[0].fine_label
        assert "le" in evidences[0].fine_label
    
    def test_only_le_detected(self):
        """Only LE should be detected if BE fails threshold."""
        config = Config(sequence_increasing_ratio=0.80)
        detector = SequenceDetector(config)
        
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.0,
            unique_ratio=0.9,
            numeric_be_strictly_increasing_ratio=0.70,
            numeric_be_step_one_ratio=None,
            numeric_le_strictly_increasing_ratio=0.90,
            numeric_le_step_one_ratio=None
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) == 1
        assert "le" in evidences[0].fine_label


class TestSequenceDetectorBothEndians:
    """Tests for SequenceDetector with both BE and LE."""
    
    def test_both_be_and_le_detected(self):
        """Both BE and LE should be detected if both pass threshold."""
        config = Config(sequence_increasing_ratio=0.80)
        detector = SequenceDetector(config)
        
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.0,
            unique_ratio=0.9,
            numeric_be_strictly_increasing_ratio=0.90,
            numeric_be_step_one_ratio=None,
            numeric_le_strictly_increasing_ratio=0.85,
            numeric_le_step_one_ratio=None
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) == 2
        # 应该按分数降序排序
        assert evidences[0].score >= evidences[1].score
    
    def test_only_be_detected(self):
        """Only BE should be detected if LE fails threshold."""
        config = Config(sequence_increasing_ratio=0.80)
        detector = SequenceDetector(config)
        
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.0,
            unique_ratio=0.9,
            numeric_be_strictly_increasing_ratio=0.90,
            numeric_be_step_one_ratio=None,
            numeric_le_strictly_increasing_ratio=0.70,
            numeric_le_step_one_ratio=None
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) == 1
        assert "be" in evidences[0].fine_label


class TestSequenceDetectorThresholdBoundary:
    """Tests for SequenceDetector threshold boundary."""
    
    def test_support_below_threshold(self):
        """Support ratio below threshold should not be detected."""
        config = Config(sequence_increasing_ratio=0.80)
        detector = SequenceDetector(config)
        
        # 支持率 0.79 < 0.80
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.0,
            unique_ratio=0.9,
            numeric_be_strictly_increasing_ratio=0.79,
            numeric_be_step_one_ratio=None
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) == 0
    
    def test_support_at_threshold(self):
        """Support ratio at threshold should be detected."""
        config = Config(sequence_increasing_ratio=0.80)
        detector = SequenceDetector(config)
        
        # 支持率 0.80 = 0.80
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.0,
            unique_ratio=0.9,
            numeric_be_strictly_increasing_ratio=0.80,
            numeric_be_step_one_ratio=None
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) >= 1
        assert evidences[0].coarse_label == "sequence_or_counter"
    
    def test_support_above_threshold(self):
        """Support ratio above threshold should be detected."""
        config = Config(sequence_increasing_ratio=0.80)
        detector = SequenceDetector(config)
        
        # 支持率 0.81 > 0.80
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.0,
            unique_ratio=0.9,
            numeric_be_strictly_increasing_ratio=0.81,
            numeric_be_step_one_ratio=None
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) >= 1
        assert evidences[0].coarse_label == "sequence_or_counter"


class TestSequenceDetectorEvidence:
    """Tests for SequenceDetector evidence structure."""
    
    def test_evidence_has_required_fields(self):
        """Evidence should have all required fields."""
        config = Config(sequence_increasing_ratio=0.80)
        detector = SequenceDetector(config)
        
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.0,
            unique_ratio=0.9,
            numeric_be_strictly_increasing_ratio=1.0,
            numeric_be_step_one_ratio=1.0
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) >= 1
        
        evidence = evidences[0]
        assert evidence.detector == "sequence"
        assert evidence.coarse_label == "sequence_or_counter"
        assert evidence.fine_label is not None
        assert evidence.score is not None
        assert evidence.details is not None
        assert "endian" in evidence.details
        assert "byte_width" in evidence.details
        assert "support_ratio" in evidence.details
    
    def test_evidence_is_hard(self):
        """Evidence should be hard evidence."""
        config = Config(sequence_increasing_ratio=0.80)
        detector = SequenceDetector(config)
        
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.0,
            unique_ratio=0.9,
            numeric_be_strictly_increasing_ratio=1.0,
            numeric_be_step_one_ratio=1.0
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) >= 1
        assert evidences[0].is_hard_evidence is True


class TestSequenceDetectorCanonicalLabel:
    """R239: sequence detector coarse_label 统一为标准标签 sequence_or_counter

    03 教程 7.3：coarse_label=sequence_or_counter，fine_label 动态生成
    （含 bit 宽度与 endian），is_hard_evidence=True（hard evidence，区别于
    identifier/payload/type_opcode 的 soft candidate）。
    """

    def _make_detector(self):
        return SequenceDetector(Config(sequence_increasing_ratio=0.80))

    def _make_be_sequence_profile(self):
        return FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.0,
            unique_ratio=0.9,
            numeric_be_strictly_increasing_ratio=1.0,
            numeric_be_step_one_ratio=1.0,
        )

    def test_coarse_label_is_canonical_sequence_or_counter(self):
        """coarse_label 必须是 taxonomy 标准标签 sequence_or_counter。"""
        from semantic_detector.taxonomy import (
            CANONICAL_COARSE_LABELS,
            is_canonical_coarse_label,
        )

        detector = self._make_detector()
        evidences = detector.detect(self._make_be_sequence_profile())
        assert len(evidences) >= 1
        assert evidences[0].coarse_label == "sequence_or_counter"
        assert is_canonical_coarse_label(evidences[0].coarse_label) is True
        assert "sequence_or_counter" in CANONICAL_COARSE_LABELS

    def test_fine_label_dynamic_format_with_bit_width_and_endian(self):
        """fine_label 必须含 sequence_ 前缀、bit 宽度与 endian。

        width_mode=4 -> 32bit，BE 候选 -> fine_label="sequence_32bit_be"。
        不再输出旧标签 sequence 作为 coarse_label。
        """
        detector = self._make_detector()
        evidences = detector.detect(self._make_be_sequence_profile())
        assert len(evidences) >= 1
        fine_label = evidences[0].fine_label
        assert fine_label is not None
        assert fine_label.startswith("sequence_")
        assert "32bit" in fine_label
        assert "be" in fine_label
        # 确保不是旧标签 sequence 作为 coarse_label
        assert evidences[0].coarse_label != "sequence"

    def test_sequence_detector_constants_reference_taxonomy(self):
        """检测器 COARSE_LABEL 常量与 taxonomy 标准标签一致。"""
        from semantic_detector.taxonomy import CANONICAL_COARSE_LABELS

        assert SequenceDetector.COARSE_LABEL == "sequence_or_counter"
        assert SequenceDetector.COARSE_LABEL in CANONICAL_COARSE_LABELS
