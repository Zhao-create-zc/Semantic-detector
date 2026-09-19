"""R056+R057: unique count/ratio 和 dominant/all_zero 统计测试"""

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


class TestValueStats:
    def test_all_unique(self):
        samples = _make_samples([b"\x01", b"\x02", b"\x03", b"\x04"])
        profile = FieldProfile()
        compute_value_stats(samples, profile)
        assert profile.unique_value_count == 4
        assert profile.unique_ratio == 1.0

    def test_all_same(self):
        samples = _make_samples([b"\xaa", b"\xaa", b"\xaa"])
        profile = FieldProfile()
        compute_value_stats(samples, profile)
        assert profile.unique_value_count == 1
        assert abs(profile.unique_ratio - 1 / 3) < 1e-9

    def test_repeated_values(self):
        samples = _make_samples([b"\x01", b"\x02", b"\x01", b"\x02", b"\x01"])
        profile = FieldProfile()
        compute_value_stats(samples, profile)
        assert profile.unique_value_count == 2
        assert profile.unique_ratio == 2 / 5

    def test_single_sample(self):
        samples = _make_samples([b"\xff"])
        profile = FieldProfile()
        compute_value_stats(samples, profile)
        assert profile.unique_value_count == 1
        assert profile.unique_ratio == 1.0

    def test_empty_samples(self):
        profile = FieldProfile()
        compute_value_stats([], profile)
        assert profile.unique_value_count == 0
        assert profile.unique_ratio == 0.0

    def test_multi_byte_unique(self):
        samples = _make_samples([b"\x01\x02", b"\x01\x03", b"\x01\x02"])
        profile = FieldProfile()
        compute_value_stats(samples, profile)
        assert profile.unique_value_count == 2
        assert abs(profile.unique_ratio - 2 / 3) < 1e-9


class TestDominantAndZeroStats:
    def test_dominant_value_ratio(self):
        samples = _make_samples([b"\x01", b"\x01", b"\x01", b"\x02"])
        profile = FieldProfile()
        compute_value_stats(samples, profile)
        assert abs(profile.dominant_value_ratio - 3 / 4) < 1e-9

    def test_dominant_all_same(self):
        samples = _make_samples([b"\xaa", b"\xaa", b"\xaa"])
        profile = FieldProfile()
        compute_value_stats(samples, profile)
        assert abs(profile.dominant_value_ratio - 1.0) < 1e-9

    def test_all_zero_sample_ratio(self):
        samples = _make_samples([b"\x00", b"\x00", b"\x01", b"\x02"])
        profile = FieldProfile()
        compute_value_stats(samples, profile)
        assert abs(profile.all_zero_sample_ratio - 2 / 4) < 1e-9

    def test_no_zero_samples(self):
        samples = _make_samples([b"\x01", b"\x02", b"\x03"])
        profile = FieldProfile()
        compute_value_stats(samples, profile)
        assert profile.all_zero_sample_ratio == 0.0

    def test_all_zero_samples(self):
        samples = _make_samples([b"\x00", b"\x00", b"\x00"])
        profile = FieldProfile()
        compute_value_stats(samples, profile)
        assert abs(profile.all_zero_sample_ratio - 1.0) < 1e-9


class TestDominantValueR265:
    """R265：多值计数场景，ratio/count/hex 一致性测试

    验收：多值计数 | ratio/count/hex 一致。
    """

    def test_dominant_count_matches_ratio(self):
        """R265：dominant_value_count 与 dominant_value_ratio 一致（count/total=ratio）"""
        samples = _make_samples([b"\x01", b"\x01", b"\x01", b"\x02", b"\x03"])
        profile = FieldProfile()
        compute_value_stats(samples, profile)
        # 主值 b"\x01" 出现 3 次，共 5 个样本
        assert profile.dominant_value_count == 3
        assert abs(profile.dominant_value_ratio - 3 / 5) < 1e-9
        # count / total == ratio
        assert abs(profile.dominant_value_count / len(samples) - profile.dominant_value_ratio) < 1e-9

    def test_dominant_hex_matches_real_value(self):
        """R265：dominant_value_hex 与真实主值字节一致"""
        samples = _make_samples([b"\xab\xcd", b"\xab\xcd", b"\x12\x34"])
        profile = FieldProfile()
        compute_value_stats(samples, profile)
        # 主值 b"\xab\xcd" → hex "abcd"
        assert profile.dominant_value_hex == "abcd"
        assert profile.dominant_value_count == 2

    def test_multi_value_dominant_still_correct(self):
        """R265：多值计数场景，主值仍正确识别"""
        # 5 个不同值，b"\xff" 出现 3 次为主值
        samples = _make_samples([
            b"\xff", b"\xff", b"\xff", b"\x01", b"\x02"
        ])
        profile = FieldProfile()
        compute_value_stats(samples, profile)
        assert profile.unique_value_count == 3
        assert profile.dominant_value_count == 3
        assert profile.dominant_value_hex == "ff"
        assert abs(profile.dominant_value_ratio - 3 / 5) < 1e-9

    def test_tie_dominant_hex_null_but_count_correct(self):
        """R265：并列时 hex 为 None，但 count/ratio 仍正确"""
        # b"\x01" 和 b"\x02" 各 2 次，并列
        samples = _make_samples([b"\x01", b"\x01", b"\x02", b"\x02"])
        profile = FieldProfile()
        compute_value_stats(samples, profile)
        assert profile.dominant_value_hex is None
        assert profile.dominant_value_count == 2
        assert abs(profile.dominant_value_ratio - 0.5) < 1e-9

    def test_three_way_tie_dominant_hex_null(self):
        """R265：三方并列时 hex 仍为 None"""
        samples = _make_samples([b"\x01", b"\x02", b"\x03"])
        profile = FieldProfile()
        compute_value_stats(samples, profile)
        # 三个值各 1 次，三方并列
        assert profile.dominant_value_hex is None
        assert profile.dominant_value_count == 1
        assert abs(profile.dominant_value_ratio - 1 / 3) < 1e-9

    def test_single_sample_dominant(self):
        """R265：单样本时主值即该样本，hex/count/ratio 一致"""
        samples = _make_samples([b"\xab\xcd\xef"])
        profile = FieldProfile()
        compute_value_stats(samples, profile)
        assert profile.dominant_value_hex == "abcdef"
        assert profile.dominant_value_count == 1
        assert abs(profile.dominant_value_ratio - 1.0) < 1e-9

    def test_empty_samples_dominant_defaults(self):
        """R265：空样本时 dominant_value_hex/count 为默认值"""
        profile = FieldProfile()
        compute_value_stats([], profile)
        assert profile.dominant_value_hex is None
        assert profile.dominant_value_count == 0
        assert profile.dominant_value_ratio == 0.0

    def test_ratio_count_hex_all_consistent(self):
        """R265：ratio/count/hex 三者完全一致的综合场景"""
        # 7 个样本：b"\xaa" 4 次，b"\xbb" 2 次，b"\xcc" 1 次
        samples = _make_samples([
            b"\xaa", b"\xaa", b"\xaa", b"\xaa", b"\xbb", b"\xbb", b"\xcc"
        ])
        profile = FieldProfile()
        compute_value_stats(samples, profile)
        # 主值 b"\xaa"
        assert profile.dominant_value_hex == "aa"
        assert profile.dominant_value_count == 4
        # ratio = count / total
        expected_ratio = 4 / 7
        assert abs(profile.dominant_value_ratio - expected_ratio) < 1e-9
        # count = ratio * total
        assert abs(profile.dominant_value_count - profile.dominant_value_ratio * len(samples)) < 1e-9
        # unique 一致
        assert profile.unique_value_count == 3
