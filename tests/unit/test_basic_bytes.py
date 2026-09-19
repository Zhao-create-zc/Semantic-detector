"""R058: zero_byte_ratio 测试"""

from semantic_detector.contracts import FieldSample
from semantic_detector.profiling.basic_stats import compute_value_stats
from semantic_detector.profiling.profile_builder import FieldProfile


def _make_samples(field_bytes_list):
    return [
        FieldSample(message_id=f"m{i}", field_key=None, field_bytes=fb,
                     start=0, end=len(fb), message_length=10,
                     remaining_bytes=10 - len(fb))
        for i, fb in enumerate(field_bytes_list)
    ]


class TestZeroByteRatio:
    def test_all_zero_bytes(self):
        samples = _make_samples([b"\x00\x00", b"\x00\x00"])
        profile = FieldProfile()
        compute_value_stats(samples, profile)
        assert abs(profile.zero_byte_ratio - 1.0) < 1e-9

    def test_no_zero_bytes(self):
        samples = _make_samples([b"\x01\x02", b"\x03\x04"])
        profile = FieldProfile()
        compute_value_stats(samples, profile)
        assert profile.zero_byte_ratio == 0.0

    def test_half_zero_bytes(self):
        samples = _make_samples([b"\x00\x01"])
        profile = FieldProfile()
        compute_value_stats(samples, profile)
        assert abs(profile.zero_byte_ratio - 0.5) < 1e-9

    def test_mixed_multi_byte(self):
        samples = _make_samples([b"\x00\x00\x01", b"\x02\x00\x03"])
        profile = FieldProfile()
        compute_value_stats(samples, profile)
        # 6 total bytes, 3 zero bytes
        assert abs(profile.zero_byte_ratio - 0.5) < 1e-9

    def test_empty_samples(self):
        profile = FieldProfile()
        compute_value_stats([], profile)
        assert profile.zero_byte_ratio == 0.0
