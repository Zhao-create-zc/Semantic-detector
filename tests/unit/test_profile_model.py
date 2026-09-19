"""R053: FieldProfile dataclass 骨架测试"""

import json

from semantic_detector.profiling.profile_builder import FieldProfile


def test_minimal_instance():
    """最小实例可创建"""
    profile = FieldProfile()
    assert profile.sample_count == 0
    assert profile.layout_id == ""


def test_to_dict_serializable():
    """to_dict 输出可 JSON 化"""
    profile = FieldProfile(
        layout_id="L1",
        direction="request",
        field_index=0,
        sample_count=10,
        width_min=2,
        width_max=4,
        width_mode=2,
        fixed_width=False,
        start_mode=0,
        end_mode=2,
        is_first_field_ratio=1.0,
        is_last_field_ratio=0.0,
        position_ratio_mean=0.1,
        unique_value_count=5,
        unique_ratio=0.5,
        dominant_value_ratio=0.3,
        dominant_value_hex="aabb",
        dominant_value_count=3,
        all_zero_sample_ratio=0.0,
        zero_byte_ratio=0.0,
        printable_ascii_ratio=0.8,
        nonempty_string_ratio=0.9,
        utf8_decode_success_ratio=0.9,
        normalized_entropy=0.7,
        insufficient_samples=False,
    )
    d = profile.to_dict()
    serialized = json.dumps(d)
    deserialized = json.loads(serialized)
    assert deserialized["layout_id"] == "L1"
    assert deserialized["sample_count"] == 10
    assert deserialized["fixed_width"] is False
    assert len(deserialized) == 69


def test_all_fields_present():
    """to_dict 包含所有字段"""
    profile = FieldProfile()
    d = profile.to_dict()
    expected_keys = {
        "layout_id", "direction", "field_index", "sample_count",
        "width_min", "width_max", "width_mode", "fixed_width",
        "start_mode", "end_mode", "is_first_field_ratio", "is_last_field_ratio",
        "position_ratio_mean", "unique_value_count", "unique_ratio",
        "dominant_value_ratio", "dominant_value_hex", "dominant_value_count",
        "all_zero_sample_ratio", "zero_byte_ratio",
        "printable_ascii_ratio", "nonempty_string_ratio", "utf8_decode_success_ratio",
        "normalized_entropy", "insufficient_samples",
        "numeric_be_min", "numeric_be_max", "numeric_be_mean", "numeric_be_median",
        "numeric_be_strictly_increasing_ratio", "numeric_be_nondecreasing_ratio",
        "numeric_be_step_one_ratio", "numeric_be_message_length_correlation",
        "numeric_be_remaining_bytes_correlation",
        "numeric_be_message_length_exact_support", "numeric_be_remaining_bytes_exact_support",
        "numeric_be_message_length_offset_support", "numeric_be_message_length_offset",
        "numeric_be_remaining_bytes_offset_support", "numeric_be_remaining_bytes_offset",
        "numeric_le_min", "numeric_le_max", "numeric_le_mean", "numeric_le_median",
        "numeric_le_strictly_increasing_ratio", "numeric_le_nondecreasing_ratio",
        "numeric_le_step_one_ratio", "numeric_le_message_length_correlation",
        "numeric_le_remaining_bytes_correlation",
        "numeric_le_message_length_exact_support", "numeric_le_remaining_bytes_exact_support",
        "numeric_le_message_length_offset_support", "numeric_le_message_length_offset",
        "numeric_le_remaining_bytes_offset_support", "numeric_le_remaining_bytes_offset",
        "numeric_be_distinct_value_count", "numeric_le_distinct_value_count",
        "capture_time_count", "capture_time_coverage",
        "capture_time_min", "capture_time_max",
        "timestamp_be_unix_seconds_support", "timestamp_be_unix_milliseconds_support",
        "timestamp_be_unix_microseconds_support", "timestamp_be_ntp_seconds_support",
        "timestamp_le_unix_seconds_support", "timestamp_le_unix_milliseconds_support",
        "timestamp_le_unix_microseconds_support", "timestamp_le_ntp_seconds_support",
    }
    assert set(d.keys()) == expected_keys


def test_insufficient_flag():
    """insufficient_samples 标志可设置"""
    profile = FieldProfile(insufficient_samples=True)
    d = profile.to_dict()
    assert d["insufficient_samples"] is True
