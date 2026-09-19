"""R060: normalized_entropy 归一化统计测试"""

from semantic_detector.contracts import FieldSample
from semantic_detector.profiling.basic_stats import compute_entropy_stats
from semantic_detector.profiling.profile_builder import FieldProfile


def _make_samples(field_bytes_list):
    return [
        FieldSample(message_id=f"m{i}", field_key=None, field_bytes=fb,
                     start=0, end=len(fb), message_length=10,
                     remaining_bytes=10 - len(fb))
        for i, fb in enumerate(field_bytes_list)
    ]


class TestEntropyStats:
    def test_zero_entropy(self):
        """全相同样本：熵 = 0，归一化 = 0"""
        samples = _make_samples([b"\x01", b"\x01", b"\x01", b"\x01"])
        profile = FieldProfile()
        compute_entropy_stats(samples, profile)
        assert abs(profile.normalized_entropy - 0.0) < 1e-9

    def test_max_entropy(self):
        """全不同样本：归一化 = 1.0"""
        samples = _make_samples([b"\x01", b"\x02", b"\x03", b"\x04"])
        profile = FieldProfile()
        compute_entropy_stats(samples, profile)
        assert abs(profile.normalized_entropy - 1.0) < 1e-9

    def test_half_entropy(self):
        """2/2 分布：归一化 = 0.5"""
        samples = _make_samples([b"\x01", b"\x02", b"\x01", b"\x02"])
        profile = FieldProfile()
        compute_entropy_stats(samples, profile)
        assert abs(profile.normalized_entropy - 0.5) < 1e-9

    def test_single_sample(self):
        """单样本：归一化 = 0.0"""
        samples = _make_samples([b"\x01"])
        profile = FieldProfile()
        compute_entropy_stats(samples, profile)
        assert profile.normalized_entropy == 0.0

    def test_empty_samples(self):
        profile = FieldProfile()
        compute_entropy_stats([], profile)
        assert profile.normalized_entropy == 0.0

    def test_result_in_zero_one_range(self):
        """归一化结果始终在 0~1"""
        samples = _make_samples([b"\x01", b"\x01", b"\x02", b"\x03", b"\x04"])
        profile = FieldProfile()
        compute_entropy_stats(samples, profile)
        assert 0.0 <= profile.normalized_entropy <= 1.0

    def test_multi_byte_values(self):
        """多字节值也能计算"""
        samples = _make_samples([b"\x01\x02", b"\x03\x04", b"\x05\x06"])
        profile = FieldProfile()
        compute_entropy_stats(samples, profile)
        assert abs(profile.normalized_entropy - 1.0) < 1e-9
