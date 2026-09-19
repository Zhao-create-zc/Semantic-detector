"""R069+R070: 大端和小端 unsigned 数值解码测试"""

from semantic_detector.profiling.numeric import (
    decode_unsigned_be,
    decode_unsigned_le,
    check_numeric_decode_available,
    NumericDecodeUnavailable,
)


class TestDecodeUnsignedBE:
    def test_1_byte(self):
        assert decode_unsigned_be(b'\xff') == 255

    def test_2_bytes(self):
        assert decode_unsigned_be(b'\x01\x00') == 256

    def test_4_bytes(self):
        assert decode_unsigned_be(b'\x00\x00\x01\x00') == 256

    def test_8_bytes(self):
        assert decode_unsigned_be(b'\x00\x00\x00\x00\x00\x00\x01\x00') == 256

    def test_all_ff(self):
        assert decode_unsigned_be(b'\xff\xff') == 65535

    def test_zero(self):
        assert decode_unsigned_be(b'\x00\x00') == 0

    def test_empty_returns_none(self):
        assert decode_unsigned_be(b'') is None

    def test_too_long_returns_none(self):
        assert decode_unsigned_be(b'\x00' * 9) is None


class TestDecodeUnsignedLE:
    def test_1_byte(self):
        assert decode_unsigned_le(b'\xff') == 255

    def test_2_bytes(self):
        assert decode_unsigned_le(b'\x00\x01') == 256

    def test_4_bytes(self):
        assert decode_unsigned_le(b'\x00\x01\x00\x00') == 256

    def test_8_bytes(self):
        assert decode_unsigned_le(b'\x00\x01\x00\x00\x00\x00\x00\x00') == 256

    def test_be_vs_le(self):
        assert decode_unsigned_be(b'\x01\x02') == decode_unsigned_le(b'\x02\x01')

    def test_empty_returns_none(self):
        assert decode_unsigned_le(b'') is None

    def test_too_long_returns_none(self):
        assert decode_unsigned_le(b'\x00' * 9) is None


class TestCheckNumericDecodeAvailable:
    """R071: 变宽字段数值解码必须 abstain"""
    
    def test_variable_width_returns_unavailable(self):
        """宽度 1/2 混合时返回 variable_width"""
        reason = check_numeric_decode_available(
            fixed_width=False,
            width_min=1,
            width_max=2,
            sample_count=10
        )
        assert reason == NumericDecodeUnavailable.VARIABLE_WIDTH
    
    def test_fixed_width_1_byte_available(self):
        """固定宽度 1 字节可用"""
        reason = check_numeric_decode_available(
            fixed_width=True,
            width_min=1,
            width_max=1,
            sample_count=10
        )
        assert reason is None
    
    def test_fixed_width_2_bytes_available(self):
        """固定宽度 2 字节可用"""
        reason = check_numeric_decode_available(
            fixed_width=True,
            width_min=2,
            width_max=2,
            sample_count=10
        )
        assert reason is None
    
    def test_fixed_width_4_bytes_available(self):
        """固定宽度 4 字节可用"""
        reason = check_numeric_decode_available(
            fixed_width=True,
            width_min=4,
            width_max=4,
            sample_count=10
        )
        assert reason is None
    
    def test_fixed_width_8_bytes_available(self):
        """固定宽度 8 字节可用"""
        reason = check_numeric_decode_available(
            fixed_width=True,
            width_min=8,
            width_max=8,
            sample_count=10
        )
        assert reason is None
    
    def test_width_0_unsupported(self):
        """宽度 0 不支持"""
        reason = check_numeric_decode_available(
            fixed_width=True,
            width_min=0,
            width_max=0,
            sample_count=10
        )
        assert reason == NumericDecodeUnavailable.UNSUPPORTED_WIDTH
    
    def test_width_9_unsupported(self):
        """宽度 9 不支持"""
        reason = check_numeric_decode_available(
            fixed_width=True,
            width_min=9,
            width_max=9,
            sample_count=10
        )
        assert reason == NumericDecodeUnavailable.UNSUPPORTED_WIDTH
    
    def test_insufficient_samples(self):
        """样本数不足"""
        reason = check_numeric_decode_available(
            fixed_width=True,
            width_min=2,
            width_max=2,
            sample_count=5,
            min_samples=8
        )
        assert reason == NumericDecodeUnavailable.INSUFFICIENT_SAMPLES
