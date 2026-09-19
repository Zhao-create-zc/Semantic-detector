"""测试时间戳范围支持率计算"""

import pytest
from datetime import datetime, timezone, timedelta
from semantic_detector.bi_adapted.timestamp_range import (
    TIMESTAMP_UNAVAILABLE,
    is_timestamp_available,
    get_time_range,
    calculate_timestamp_support,
    decode_timestamp_bytes_be,
    decode_timestamp_bytes_le,
    calculate_unix_seconds_support,
    calculate_unix_microseconds_support,
    calculate_ntp_seconds_support
)


class TestDecodeTimestampBytesBE:
    """测试大端时间戳解码"""
    
    def test_4byte_be(self):
        """4 字节大端解码"""
        # 0x12345678
        field_bytes = bytes([0x12, 0x34, 0x56, 0x78])
        value = decode_timestamp_bytes_be(field_bytes, byte_width=4)
        assert value == 0x12345678
    
    def test_8byte_be(self):
        """8 字节大端解码"""
        # 0x123456789ABCDEF0
        field_bytes = bytes([0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0])
        value = decode_timestamp_bytes_be(field_bytes, byte_width=8)
        assert value == 0x123456789ABCDEF0
    
    def test_insufficient_bytes(self):
        """字节不足"""
        field_bytes = bytes([0x12, 0x34])
        value = decode_timestamp_bytes_be(field_bytes, byte_width=4)
        assert value is None


class TestDecodeTimestampBytesLE:
    """测试小端时间戳解码"""
    
    def test_4byte_le(self):
        """4 字节小端解码"""
        # 0x78563412
        field_bytes = bytes([0x12, 0x34, 0x56, 0x78])
        value = decode_timestamp_bytes_le(field_bytes, byte_width=4)
        assert value == 0x78563412
    
    def test_8byte_le(self):
        """8 字节小端解码"""
        # 0xF0DEBC9A78563412
        field_bytes = bytes([0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0])
        value = decode_timestamp_bytes_le(field_bytes, byte_width=8)
        assert value == 0xF0DEBC9A78563412


class TestCalculateTimestampSupport:
    """测试时间戳支持率计算"""
    
    def test_all_in_range(self):
        """所有值都在范围内"""
        # 时间范围：2020-01-01 到 2020-01-02
        low = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        high = datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
        
        # 字段值：2020-01-01 12:00:00 的 Unix 秒
        field_values = [1577880000, 1577883600, 1577887200]
        
        support = calculate_timestamp_support(
            field_values=field_values,
            low_timestamp=low,
            high_timestamp=high,
            epoch_offset=0,
            scale=1.0,
            slop_seconds=0
        )
        
        assert support == 1.0
    
    def test_partial_in_range(self):
        """部分值在范围内"""
        # 时间范围：2020-01-01 到 2020-01-02
        low = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        high = datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
        
        # 字段值：一个在范围内，一个在范围外
        field_values = [1577880000, 1577968000]  # 2020-01-01 12:00:00, 2020-01-02 12:00:00
        
        support = calculate_timestamp_support(
            field_values=field_values,
            low_timestamp=low,
            high_timestamp=high,
            epoch_offset=0,
            scale=1.0,
            slop_seconds=0
        )
        
        assert support == 0.5
    
    def test_none_in_range(self):
        """所有值都不在范围内"""
        # 时间范围：2020-01-01 到 2020-01-02
        low = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        high = datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
        
        # 字段值：2020-01-03
        field_values = [1578076800]
        
        support = calculate_timestamp_support(
            field_values=field_values,
            low_timestamp=low,
            high_timestamp=high,
            epoch_offset=0,
            scale=1.0,
            slop_seconds=0
        )
        
        assert support == 0.0
    
    def test_empty_list(self):
        """空列表"""
        low = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        high = datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
        
        support = calculate_timestamp_support(
            field_values=[],
            low_timestamp=low,
            high_timestamp=high
        )
        
        assert support == 0.0
    
    def test_slop_seconds(self):
        """容差测试"""
        # 时间范围：2020-01-01 到 2020-01-02
        low = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        high = datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
        
        # 字段值：2019-12-31 12:00:00（在范围外，但在容差内）
        field_values = [1577774400]
        
        # 无容差：不在范围内
        support_no_slop = calculate_timestamp_support(
            field_values=field_values,
            low_timestamp=low,
            high_timestamp=high,
            slop_seconds=0
        )
        assert support_no_slop == 0.0
        
        # 有容差：在范围内
        support_with_slop = calculate_timestamp_support(
            field_values=field_values,
            low_timestamp=low,
            high_timestamp=high,
            slop_seconds=86400  # 1 天
        )
        assert support_with_slop == 1.0


class TestUnixSecondsSupport:
    """测试 Unix 秒时间戳支持率"""
    
    def test_unix_seconds(self):
        """Unix 秒时间戳"""
        low = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        high = datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
        
        # 2020-01-01 12:00:00 UTC
        field_values = [1577880000]
        
        support = calculate_unix_seconds_support(
            field_values=field_values,
            low_timestamp=low,
            high_timestamp=high
        )
        
        assert support == 1.0


class TestUnixMicrosecondsSupport:
    """测试 Unix 微秒时间戳支持率"""
    
    def test_unix_microseconds(self):
        """Unix 微秒时间戳"""
        low = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        high = datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
        
        # 2020-01-01 12:00:00 UTC in microseconds
        field_values = [1577880000 * 1000000]
        
        support = calculate_unix_microseconds_support(
            field_values=field_values,
            low_timestamp=low,
            high_timestamp=high
        )
        
        assert support == 1.0


class TestNTPSecondsSupport:
    """测试 NTP 秒时间戳支持率"""
    
    def test_ntp_seconds(self):
        """NTP 秒时间戳"""
        low = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        high = datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
        
        # 2020-01-01 12:00:00 UTC in NTP seconds
        # NTP 纪元：1900-01-01
        # Unix 纪元：1970-01-01
        # NTP 偏移：2208988800 秒
        ntp_offset = 2208988800
        field_values = [1577880000 + ntp_offset]
        
        support = calculate_ntp_seconds_support(
            field_values=field_values,
            low_timestamp=low,
            high_timestamp=high
        )
        
        assert support == 1.0


class TestTimestampUnavailable:
    """测试无 capture_time 时返回 unavailable"""
    
    def test_timestamp_unavailable_constant(self):
        """TIMESTAMP_UNAVAILABLE 常量"""
        assert TIMESTAMP_UNAVAILABLE == "unavailable"
    
    def test_is_timestamp_available_with_times(self):
        """有可用时间戳"""
        capture_times = [
            datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            None,
            datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
        ]
        
        assert is_timestamp_available(capture_times) is True
    
    def test_is_timestamp_available_all_none(self):
        """所有时间戳都缺失"""
        capture_times = [None, None, None]
        
        assert is_timestamp_available(capture_times) is False
    
    def test_is_timestamp_available_empty(self):
        """空列表"""
        capture_times = []
        
        assert is_timestamp_available(capture_times) is False
    
    def test_get_time_range_with_times(self):
        """有可用时间戳：返回时间范围"""
        capture_times = [
            datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            datetime(2020, 1, 3, 0, 0, 0, tzinfo=timezone.utc),
            datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
        ]
        
        low, high = get_time_range(capture_times)
        
        assert low == datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        assert high == datetime(2020, 1, 3, 0, 0, 0, tzinfo=timezone.utc)
    
    def test_get_time_range_all_none(self):
        """所有时间戳都缺失：返回 (None, None)"""
        capture_times = [None, None, None]
        
        low, high = get_time_range(capture_times)
        
        assert low is None
        assert high is None
    
    def test_get_time_range_with_default(self):
        """所有时间戳都缺失：使用默认范围"""
        capture_times = [None, None, None]
        default_range = (
            datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
        )
        
        low, high = get_time_range(capture_times, default_range=default_range)
        
        assert low == datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        assert high == datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
    
    def test_calculate_support_with_none_range(self):
        """时间范围为 None：返回 0.0"""
        field_values = [1577880000, 1577883600]
        
        # low 为 None
        support = calculate_timestamp_support(
            field_values=field_values,
            low_timestamp=None,
            high_timestamp=datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
        )
        assert support == 0.0
        
        # high 为 None
        support = calculate_timestamp_support(
            field_values=field_values,
            low_timestamp=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            high_timestamp=None
        )
        assert support == 0.0
        
        # 两者都为 None
        support = calculate_timestamp_support(
            field_values=field_values,
            low_timestamp=None,
            high_timestamp=None
        )
        assert support == 0.0
    
    def test_unix_seconds_support_with_none_range(self):
        """Unix 秒支持率：时间范围为 None"""
        field_values = [1577880000]
        
        support = calculate_unix_seconds_support(
            field_values=field_values,
            low_timestamp=None,
            high_timestamp=None
        )
        
        assert support == 0.0
    
    def test_unix_microseconds_support_with_none_range(self):
        """Unix 微秒支持率：时间范围为 None"""
        field_values = [1577880000 * 1000000]
        
        support = calculate_unix_microseconds_support(
            field_values=field_values,
            low_timestamp=None,
            high_timestamp=None
        )
        
        assert support == 0.0
    
    def test_ntp_seconds_support_with_none_range(self):
        """NTP 秒支持率：时间范围为 None"""
        ntp_offset = 2208988800
        field_values = [1577880000 + ntp_offset]
        
        support = calculate_ntp_seconds_support(
            field_values=field_values,
            low_timestamp=None,
            high_timestamp=None
        )
        
        assert support == 0.0
    
    def test_no_current_time_used(self):
        """不使用当前时间"""
        # 这个测试确保当时间范围不可用时，不会使用当前时间
        # 而是返回 0.0
        field_values = [1577880000]
        
        # 获取时间范围（所有时间戳都缺失）
        capture_times = [None, None, None]
        low, high = get_time_range(capture_times)
        
        # 验证返回 (None, None) 而不是当前时间
        assert low is None
        assert high is None
        
        # 验证支持率为 0.0
        support = calculate_unix_seconds_support(
            field_values=field_values,
            low_timestamp=low,
            high_timestamp=high
        )
        assert support == 0.0
