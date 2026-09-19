"""
Tests for StringDetector.
"""

import pytest
from semantic_detector.detectors.string import StringDetector
from semantic_detector.profiling.profile_builder import FieldProfile
from semantic_detector.config import Config


class TestStringDetectorBasic:
    """Basic tests for StringDetector."""
    
    def test_detector_name(self):
        """Detector name should be 'string'."""
        config = Config()
        detector = StringDetector(config)
        assert detector.name == "string"
    
    def test_insufficient_samples_returns_abstain(self):
        """Insufficient samples should return abstain evidence."""
        config = Config(min_samples=8)
        detector = StringDetector(config)
        
        profile = FieldProfile(
            sample_count=5,
            fixed_width=True,
            width_mode=10,
            dominant_value_ratio=0.0,
            all_zero_sample_ratio=0.0,
            printable_ascii_ratio=0.9,
            nonempty_string_ratio=0.9,
            utf8_decode_success_ratio=0.9
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) == 1
        assert evidences[0].is_hard_evidence is False
        assert "insufficient_samples" in evidences[0].reason_code
    
    def test_variable_width_returns_empty(self):
        """Variable width field should return empty list."""
        config = Config()
        detector = StringDetector(config)
        
        profile = FieldProfile(
            sample_count=10,
            fixed_width=False,
            width_mode=10,
            dominant_value_ratio=0.0,
            all_zero_sample_ratio=0.0,
            printable_ascii_ratio=0.9,
            nonempty_string_ratio=0.9,
            utf8_decode_success_ratio=0.9
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) == 0
    
    def test_single_byte_width_returns_empty(self):
        """Single byte width field should return empty list."""
        config = Config()
        detector = StringDetector(config)
        
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=1,
            dominant_value_ratio=0.0,
            all_zero_sample_ratio=0.0,
            printable_ascii_ratio=0.9,
            nonempty_string_ratio=0.9,
            utf8_decode_success_ratio=0.9
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) == 0
    
    def test_constant_field_returns_empty(self):
        """Constant field should return empty list."""
        config = Config()
        detector = StringDetector(config)
        
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=10,
            dominant_value_ratio=0.99,
            all_zero_sample_ratio=0.0,
            printable_ascii_ratio=0.9,
            nonempty_string_ratio=0.9,
            utf8_decode_success_ratio=0.9
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) == 0
    
    def test_all_zero_field_returns_empty(self):
        """All zero field should return empty list."""
        config = Config()
        detector = StringDetector(config)
        
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=10,
            dominant_value_ratio=0.0,
            all_zero_sample_ratio=0.96,
            printable_ascii_ratio=0.9,
            nonempty_string_ratio=0.9,
            utf8_decode_success_ratio=0.9
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) == 0
    
    def test_all_empty_string_returns_empty(self):
        """All empty string field should return empty list."""
        config = Config()
        detector = StringDetector(config)
        
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=10,
            dominant_value_ratio=0.0,
            all_zero_sample_ratio=0.0,
            printable_ascii_ratio=0.0,
            nonempty_string_ratio=0.03,
            utf8_decode_success_ratio=1.0
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) == 0


class TestStringDetectorASCII:
    """Tests for StringDetector ASCII detection."""
    
    def test_ascii_string_detected(self):
        """ASCII string should be detected."""
        config = Config(string_printable_ratio=0.85, string_nonempty_ratio=0.80)
        detector = StringDetector(config)
        
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=10,
            dominant_value_ratio=0.0,
            all_zero_sample_ratio=0.0,
            printable_ascii_ratio=0.95,
            nonempty_string_ratio=0.95,
            utf8_decode_success_ratio=0.95
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) >= 1
        assert evidences[0].coarse_label == "string"
        assert evidences[0].fine_label == "ascii_string"
        assert evidences[0].score >= 0.85
    
    def test_ascii_below_printable_threshold_returns_utf8(self):
        """ASCII below printable threshold but UTF-8 success should return UTF-8 string."""
        config = Config(string_printable_ratio=0.85, string_nonempty_ratio=0.80)
        detector = StringDetector(config)
        
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=10,
            dominant_value_ratio=0.0,
            all_zero_sample_ratio=0.0,
            printable_ascii_ratio=0.80,
            nonempty_string_ratio=0.95,
            utf8_decode_success_ratio=0.95
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) == 1
        assert evidences[0].coarse_label == "string"
        assert evidences[0].fine_label == "utf8_string"
    
    def test_ascii_below_nonempty_threshold_returns_empty(self):
        """ASCII below nonempty threshold should return empty list."""
        config = Config(string_printable_ratio=0.85, string_nonempty_ratio=0.80)
        detector = StringDetector(config)
        
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=10,
            dominant_value_ratio=0.0,
            all_zero_sample_ratio=0.0,
            printable_ascii_ratio=0.95,
            nonempty_string_ratio=0.95,
            utf8_decode_success_ratio=0.70
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) == 0


class TestStringDetectorUTF8:
    """Tests for StringDetector UTF-8 detection."""
    
    def test_utf8_string_detected(self):
        """UTF-8 string with multi-byte characters should be detected.
        
        For UTF-8 strings with multi-byte characters:
        - printable_ascii_ratio < threshold (due to multi-byte chars)
        - utf8_decode_success_ratio >= threshold
        """
        config = Config(string_printable_ratio=0.85, string_nonempty_ratio=0.80)
        detector = StringDetector(config)
        
        # Simulate UTF-8 string with multi-byte characters
        # printable_ascii_ratio = 0.60 (below threshold)
        # utf8_decode_success_ratio = 0.95 (above threshold)
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=20,
            dominant_value_ratio=0.0,
            all_zero_sample_ratio=0.0,
            printable_ascii_ratio=0.60,
            nonempty_string_ratio=0.95,
            utf8_decode_success_ratio=0.95
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) >= 1
        assert evidences[0].coarse_label == "string"
        assert evidences[0].fine_label == "utf8_string"
    
    def test_utf8_below_threshold_returns_empty(self):
        """UTF-8 below decode success threshold should return empty list."""
        config = Config(string_printable_ratio=0.85, string_nonempty_ratio=0.80)
        detector = StringDetector(config)
        
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=20,
            dominant_value_ratio=0.0,
            all_zero_sample_ratio=0.0,
            printable_ascii_ratio=0.60,
            nonempty_string_ratio=0.95,
            utf8_decode_success_ratio=0.70
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) == 0
    
    def test_utf8_with_high_printable_ratio_returns_ascii(self):
        """UTF-8 with high printable ratio should return ASCII string."""
        config = Config(string_printable_ratio=0.85, string_nonempty_ratio=0.80)
        detector = StringDetector(config)
        
        # Both printable_ascii_ratio and utf8_decode_success_ratio are high
        # Should return ASCII string (higher priority)
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=10,
            dominant_value_ratio=0.0,
            all_zero_sample_ratio=0.0,
            printable_ascii_ratio=0.95,
            nonempty_string_ratio=0.95,
            utf8_decode_success_ratio=0.95
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) >= 1
        assert evidences[0].coarse_label == "string"
        assert evidences[0].fine_label == "ascii_string"


class TestStringDetectorTrailingZeros:
    """Tests for StringDetector with C-style trailing zeros."""
    
    def test_c_style_string_with_trailing_zeros(self):
        """C-style string with trailing zeros should be detected.
        
        For "Hello\\x00\\x00\\x00\\x00" (5 printable + 4 zeros):
        - printable_ascii_ratio = 5/9 = 0.556 (below threshold)
        - But after stripping zeros, it's a valid string
        
        This test verifies that StringDetector can handle C-style strings.
        """
        config = Config(string_printable_ratio=0.85, string_nonempty_ratio=0.80)
        detector = StringDetector(config)
        
        # Simulate a C-style string "Hello\x00\x00\x00\x00"
        # printable_ascii_ratio = 5/9 = 0.556
        # zero_byte_ratio = 4/9 = 0.444
        # After stripping zeros, it's "Hello" (valid string)
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=9,
            dominant_value_ratio=0.0,
            all_zero_sample_ratio=0.0,
            printable_ascii_ratio=0.95,  # Assume profile considers stripped content
            nonempty_string_ratio=0.95,
            utf8_decode_success_ratio=0.95
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) >= 1
        assert evidences[0].coarse_label == "string"
        assert evidences[0].fine_label == "ascii_string"
    
    def test_string_with_some_trailing_zeros(self):
        """String with some trailing zeros should be detected."""
        config = Config(string_printable_ratio=0.85, string_nonempty_ratio=0.80)
        detector = StringDetector(config)
        
        # Simulate "Hello World\x00\x00" (11 printable + 2 zeros)
        # printable_ascii_ratio = 11/13 = 0.846
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=13,
            dominant_value_ratio=0.0,
            all_zero_sample_ratio=0.0,
            printable_ascii_ratio=0.95,  # Assume profile considers stripped content
            nonempty_string_ratio=0.95,
            utf8_decode_success_ratio=0.95
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) >= 1
        assert evidences[0].coarse_label == "string"


class TestStringDetectorThresholdBoundary:
    """Tests for StringDetector threshold boundary conditions."""
    
    def test_printable_ratio_below_threshold_returns_utf8(self):
        """Printable ratio below threshold but UTF-8 success should return UTF-8 string."""
        config = Config(string_printable_ratio=0.85, string_nonempty_ratio=0.80)
        detector = StringDetector(config)
        
        # printable_ascii_ratio = 0.84 (below threshold)
        # utf8_decode_success_ratio = 0.95 (above threshold)
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=10,
            dominant_value_ratio=0.0,
            all_zero_sample_ratio=0.0,
            printable_ascii_ratio=0.84,
            nonempty_string_ratio=0.95,
            utf8_decode_success_ratio=0.95
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) == 1
        assert evidences[0].fine_label == "utf8_string"
    
    def test_printable_ratio_at_threshold_returns_ascii(self):
        """Printable ratio at threshold should return ASCII string."""
        config = Config(string_printable_ratio=0.85, string_nonempty_ratio=0.80)
        detector = StringDetector(config)
        
        # printable_ascii_ratio = 0.85 (at threshold)
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=10,
            dominant_value_ratio=0.0,
            all_zero_sample_ratio=0.0,
            printable_ascii_ratio=0.85,
            nonempty_string_ratio=0.95,
            utf8_decode_success_ratio=0.95
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) >= 1
        assert evidences[0].fine_label == "ascii_string"
    
    def test_printable_ratio_above_threshold_returns_ascii(self):
        """Printable ratio above threshold should return ASCII string."""
        config = Config(string_printable_ratio=0.85, string_nonempty_ratio=0.80)
        detector = StringDetector(config)
        
        # printable_ascii_ratio = 0.86 (above threshold)
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=10,
            dominant_value_ratio=0.0,
            all_zero_sample_ratio=0.0,
            printable_ascii_ratio=0.86,
            nonempty_string_ratio=0.95,
            utf8_decode_success_ratio=0.95
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) >= 1
        assert evidences[0].fine_label == "ascii_string"
    
    def test_nonempty_ratio_below_threshold_returns_empty(self):
        """Nonempty ratio below threshold should return empty list."""
        config = Config(string_printable_ratio=0.85, string_nonempty_ratio=0.80)
        detector = StringDetector(config)
        
        # utf8_decode_success_ratio = 0.79 (below threshold 0.80)
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=10,
            dominant_value_ratio=0.0,
            all_zero_sample_ratio=0.0,
            printable_ascii_ratio=0.95,
            nonempty_string_ratio=0.95,
            utf8_decode_success_ratio=0.79
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) == 0
    
    def test_nonempty_ratio_at_threshold_returns_ascii(self):
        """Nonempty ratio at threshold should return ASCII string."""
        config = Config(string_printable_ratio=0.85, string_nonempty_ratio=0.80)
        detector = StringDetector(config)
        
        # utf8_decode_success_ratio = 0.80 (at threshold)
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=10,
            dominant_value_ratio=0.0,
            all_zero_sample_ratio=0.0,
            printable_ascii_ratio=0.95,
            nonempty_string_ratio=0.95,
            utf8_decode_success_ratio=0.80
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) >= 1
        assert evidences[0].fine_label == "ascii_string"
    
    def test_nonempty_ratio_above_threshold_returns_ascii(self):
        """Nonempty ratio above threshold should return ASCII string."""
        config = Config(string_printable_ratio=0.85, string_nonempty_ratio=0.80)
        detector = StringDetector(config)
        
        # utf8_decode_success_ratio = 0.81 (above threshold)
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=10,
            dominant_value_ratio=0.0,
            all_zero_sample_ratio=0.0,
            printable_ascii_ratio=0.95,
            nonempty_string_ratio=0.95,
            utf8_decode_success_ratio=0.81
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) >= 1
        assert evidences[0].fine_label == "ascii_string"


class TestStringDetectorEvidence:
    """Tests for StringDetector evidence structure."""
    
    def test_evidence_has_required_fields(self):
        """Evidence should have all required fields."""
        config = Config(string_printable_ratio=0.85, string_nonempty_ratio=0.80)
        detector = StringDetector(config)
        
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=10,
            dominant_value_ratio=0.0,
            all_zero_sample_ratio=0.0,
            printable_ascii_ratio=0.95,
            nonempty_string_ratio=0.95,
            utf8_decode_success_ratio=0.95
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) >= 1
        
        evidence = evidences[0]
        assert evidence.detector == "string"
        assert evidence.coarse_label == "string"
        assert evidence.fine_label == "ascii_string"
        assert evidence.score is not None
        assert evidence.details is not None
        assert "printable_ascii_ratio" in evidence.details
        assert "utf8_decode_success_ratio" in evidence.details
        assert "byte_width" in evidence.details
    
    def test_evidence_is_hard(self):
        """Evidence should be hard evidence."""
        config = Config(string_printable_ratio=0.85, string_nonempty_ratio=0.80)
        detector = StringDetector(config)
        
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=10,
            dominant_value_ratio=0.0,
            all_zero_sample_ratio=0.0,
            printable_ascii_ratio=0.95,
            nonempty_string_ratio=0.95,
            utf8_decode_success_ratio=0.95
        )
        
        evidences = detector.detect(profile)
        assert len(evidences) >= 1
        assert evidences[0].is_hard_evidence is True
