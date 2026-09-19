"""R055: 字段 start/end 众数和首尾字段比例测试"""

from semantic_detector.contracts import Direction, FieldSample, FieldSpan, MessageRecord
from semantic_detector.profiling.basic_stats import compute_position_stats
from semantic_detector.profiling.profile_builder import FieldProfile
from semantic_detector.profiling.collector import record_to_field_samples


def _make_first_field_samples(starts, message_lengths):
    """构造第一个字段的 FieldSample 列表（用于首字段比例测试）"""
    samples = []
    for i, (st, ml) in enumerate(zip(starts, message_lengths)):
        end = st + 2
        remaining = ml - end
        samples.append(FieldSample(
            message_id=f"m{i}",
            field_key=None,
            field_bytes=b"\x00\x00",
            start=st, end=end,
            message_length=ml,
            remaining_bytes=remaining,
        ))
    return samples


class TestPositionStats:
    def test_start_end_mode(self):
        """start/end 众数正确"""
        samples = _make_first_field_samples(
            starts=[0, 0, 2, 0],
            message_lengths=[10, 10, 10, 10],
        )
        profile = FieldProfile()
        compute_position_stats(samples, profile)
        assert profile.start_mode == 0

    def test_first_field_ratio(self):
        """首字段比例正确"""
        samples = _make_first_field_samples(
            starts=[0, 0, 2, 4],
            message_lengths=[10, 10, 10, 10],
        )
        profile = FieldProfile()
        compute_position_stats(samples, profile)
        assert profile.is_first_field_ratio == 2 / 4

    def test_last_field_ratio(self):
        """末字段比例正确（remaining_bytes == 0）"""
        samples = [
            FieldSample(message_id="m0", field_key=None, field_bytes=b"\x00\x00",
                        start=0, end=2, message_length=10, remaining_bytes=8),
            FieldSample(message_id="m1", field_key=None, field_bytes=b"\x00\x00",
                        start=0, end=10, message_length=10, remaining_bytes=0),
            FieldSample(message_id="m2", field_key=None, field_bytes=b"\x00\x00",
                        start=0, end=10, message_length=10, remaining_bytes=0),
        ]
        profile = FieldProfile()
        compute_position_stats(samples, profile)
        assert profile.is_last_field_ratio == 2 / 3

    def test_position_ratio_mean(self):
        """position_ratio_mean = start / message_length 的均值"""
        samples = _make_first_field_samples(
            starts=[0, 2, 4],
            message_lengths=[10, 10, 10],
        )
        profile = FieldProfile()
        compute_position_stats(samples, profile)
        expected = (0 / 10 + 2 / 10 + 4 / 10) / 3
        assert abs(profile.position_ratio_mean - expected) < 1e-9

    def test_empty_samples(self):
        profile = FieldProfile()
        compute_position_stats([], profile)
        assert profile.start_mode == 0

    def test_all_same_position(self):
        samples = _make_first_field_samples(
            starts=[5, 5, 5],
            message_lengths=[20, 20, 20],
        )
        profile = FieldProfile()
        compute_position_stats(samples, profile)
        assert profile.start_mode == 5
        assert profile.is_first_field_ratio == 0.0
        assert profile.position_ratio_mean == 5 / 20

    def test_position_ratio_mean_different_message_lengths(self):
        """R064: 不同消息长度下的 position_ratio_mean"""
        samples = [
            FieldSample(message_id="m0", field_key=None, field_bytes=b"\x00",
                        start=0, end=1, message_length=10, remaining_bytes=9),
            FieldSample(message_id="m1", field_key=None, field_bytes=b"\x00",
                        start=5, end=6, message_length=20, remaining_bytes=14),
            FieldSample(message_id="m2", field_key=None, field_bytes=b"\x00",
                        start=2, end=3, message_length=4, remaining_bytes=1),
        ]
        profile = FieldProfile()
        compute_position_stats(samples, profile)
        expected = (0 / 10 + 5 / 20 + 2 / 4) / 3
        assert abs(profile.position_ratio_mean - expected) < 1e-9
