"""R061+R062+R063: 字符串统计测试（printable_ascii_ratio 等）"""

from semantic_detector.contracts import FieldSample
from semantic_detector.profiling.basic_stats import compute_string_stats
from semantic_detector.profiling.profile_builder import FieldProfile


def _make_samples(field_bytes_list):
    return [
        FieldSample(message_id=f"m{i}", field_key=None, field_bytes=fb,
                     start=0, end=len(fb), message_length=10,
                     remaining_bytes=10 - len(fb))
        for i, fb in enumerate(field_bytes_list)
    ]


class TestPrintableAsciiRatio:
    def test_all_printable(self):
        samples = _make_samples([b"hello", b"world"])
        profile = FieldProfile()
        compute_string_stats(samples, profile)
        assert abs(profile.printable_ascii_ratio - 1.0) < 1e-9

    def test_no_printable(self):
        samples = _make_samples([b"\x00\x01\x02", b"\xff\xfe"])
        profile = FieldProfile()
        compute_string_stats(samples, profile)
        assert profile.printable_ascii_ratio == 0.0

    def test_half_printable(self):
        samples = _make_samples([b"\x00\x41"])  # 0x00 non-printable, 0x41 = 'A'
        profile = FieldProfile()
        compute_string_stats(samples, profile)
        assert abs(profile.printable_ascii_ratio - 0.5) < 1e-9

    def test_space_is_printable(self):
        samples = _make_samples([b" a "])
        profile = FieldProfile()
        compute_string_stats(samples, profile)
        assert abs(profile.printable_ascii_ratio - 1.0) < 1e-9

    def test_tilde_is_printable(self):
        samples = _make_samples([b"\x7e"])  # 0x7E = '~'
        profile = FieldProfile()
        compute_string_stats(samples, profile)
        assert abs(profile.printable_ascii_ratio - 1.0) < 1e-9

    def test_mixed_binary_and_ascii(self):
        samples = _make_samples([b"\x00AB\x80C"])
        profile = FieldProfile()
        compute_string_stats(samples, profile)
        # 5 bytes: A(0x41), B(0x42), C(0x43) = 3 printable
        assert abs(profile.printable_ascii_ratio - 3 / 5) < 1e-9

    def test_empty_samples(self):
        profile = FieldProfile()
        compute_string_stats([], profile)
        assert profile.printable_ascii_ratio == 0.0


class TestNonemptyStringRatio:
    def test_all_nonempty(self):
        samples = _make_samples([b"hello", b"world"])
        profile = FieldProfile()
        compute_string_stats(samples, profile)
        assert abs(profile.nonempty_string_ratio - 1.0) < 1e-9

    def test_all_trailing_zeros(self):
        samples = _make_samples([b"\x00\x00", b"\x00"])
        profile = FieldProfile()
        compute_string_stats(samples, profile)
        assert profile.nonempty_string_ratio == 0.0

    def test_mixed(self):
        samples = _make_samples([b"abc", b"\x00", b"def\x00"])
        profile = FieldProfile()
        compute_string_stats(samples, profile)
        # b"abc" → nonempty, b"\x00" → empty, b"def\x00" → stripped "def" nonempty
        assert abs(profile.nonempty_string_ratio - 2 / 3) < 1e-9

    def test_single_nonempty(self):
        samples = _make_samples([b"A"])
        profile = FieldProfile()
        compute_string_stats(samples, profile)
        assert profile.nonempty_string_ratio == 1.0

    def test_single_empty(self):
        samples = _make_samples([b"\x00\x00\x00"])
        profile = FieldProfile()
        compute_string_stats(samples, profile)
        assert profile.nonempty_string_ratio == 0.0

    def test_empty_bytes(self):
        samples = _make_samples([b""])
        profile = FieldProfile()
        compute_string_stats(samples, profile)
        assert profile.nonempty_string_ratio == 0.0


class TestUtf8DecodeSuccessRatio:
    def test_all_valid_utf8(self):
        samples = _make_samples([b"hello", b"world"])
        profile = FieldProfile()
        compute_string_stats(samples, profile)
        assert abs(profile.utf8_decode_success_ratio - 1.0) < 1e-9

    def test_all_invalid_utf8(self):
        samples = _make_samples([b"\xff\xfe", b"\x80\x81"])
        profile = FieldProfile()
        compute_string_stats(samples, profile)
        assert profile.utf8_decode_success_ratio == 0.0

    def test_mixed_valid_invalid(self):
        samples = _make_samples([b"abc", b"\xff\xfe", b"def"])
        profile = FieldProfile()
        compute_string_stats(samples, profile)
        assert abs(profile.utf8_decode_success_ratio - 2 / 3) < 1e-9

    def test_empty_bytes_valid(self):
        samples = _make_samples([b""])
        profile = FieldProfile()
        compute_string_stats(samples, profile)
        assert profile.utf8_decode_success_ratio == 1.0

    def test_empty_samples(self):
        profile = FieldProfile()
        compute_string_stats([], profile)
        assert profile.utf8_decode_success_ratio == 0.0
