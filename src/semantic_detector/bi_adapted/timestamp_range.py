# This file is derived from BinaryInferno (https://github.com/ChandlerChip/BinaryInferno)
# Original file: binaryinferno/tsbyrange.py
# Original function: predictts()
# License: GNU General Public License v3.0 (GPLv3)
# Copyright: Copyright (C) 2023 Jared Chandler (jared.chandler@tufts.edu)
# Modifications: (1) Removed printing; (2) Pure function for support ratio; (3) Field boundary aware; (4) No scanning; (5) Returns support ratio only

"""时间戳范围支持率计算

从已知字段边界计算时间戳候选值在指定时间范围内的支持率。
不扫描其他偏移，只使用 FieldProfile 提供的字段值。
"""

from typing import List, Tuple, Optional
from datetime import datetime, timezone, timedelta
import struct


# 常量：表示时间不可用
TIMESTAMP_UNAVAILABLE = "unavailable"


def is_timestamp_available(capture_times: List[Optional[datetime]]) -> bool:
    """检查是否有可用的时间戳
    
    Args:
        capture_times: 时间戳列表（可能包含 None）
        
    Returns:
        如果至少有一个非 None 时间戳，返回 True
    """
    return any(ct is not None for ct in capture_times)


def get_time_range(
    capture_times: List[Optional[datetime]],
    default_range: Optional[Tuple[datetime, datetime]] = None
) -> Tuple[Optional[datetime], Optional[datetime]]:
    """从时间戳列表获取时间范围
    
    如果所有时间戳都缺失，返回 (None, None) 而不是使用当前时间。
    
    Args:
        capture_times: 时间戳列表（可能包含 None）
        default_range: 默认时间范围（可选）
        
    Returns:
        (low_timestamp, high_timestamp) 元组
        如果所有时间戳都缺失，返回 (None, None)
    """
    # 过滤掉 None 值
    available_times = [ct for ct in capture_times if ct is not None]
    
    if len(available_times) == 0:
        # 所有时间戳都缺失
        if default_range is not None:
            return default_range
        return (None, None)
    
    # 计算时间范围
    low_timestamp = min(available_times)
    high_timestamp = max(available_times)
    
    return (low_timestamp, high_timestamp)


def calculate_timestamp_support(
    field_values: List[int],
    low_timestamp: Optional[datetime],
    high_timestamp: Optional[datetime],
    epoch_offset: int = 0,
    scale: float = 1.0,
    slop_seconds: int = 86400
) -> float:
    """计算字段值在时间范围内的支持率
    
    检查字段值（解释为时间戳）是否落在指定的时间范围内。
    
    Args:
        field_values: 字段值列表（已经解码为整数）
        low_timestamp: 时间范围下界（如果为 None，返回 0.0）
        high_timestamp: 时间范围上界（如果为 None，返回 0.0）
        epoch_offset: 纪元偏移（秒），例如 NTP 纪元偏移为 2208988800
        scale: 缩放因子，例如微秒时间戳需要除以 1000000
        slop_seconds: 容差（秒），允许时间戳在范围外一定量
        
    Returns:
        支持率 (0.0~1.0)
        如果时间范围不可用（low_timestamp 或 high_timestamp 为 None），返回 0.0
    """
    if len(field_values) == 0:
        return 0.0
    
    # 检查时间范围是否可用
    if low_timestamp is None or high_timestamp is None:
        return 0.0
    
    # Unix 纪元
    unix_epoch = datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    
    # 计算时间范围的秒数（相对于 Unix 纪元）
    low_secs = int((low_timestamp - unix_epoch).total_seconds())
    high_secs = int((high_timestamp - unix_epoch).total_seconds())
    
    # 应用容差
    low_secs -= slop_seconds
    high_secs += slop_seconds
    
    # 检查每个字段值
    match_count = 0
    for value in field_values:
        # 缩放并调整纪元偏移
        value_secs = int(value / scale) - epoch_offset
        
        # 检查是否在范围内
        if low_secs <= value_secs <= high_secs:
            match_count += 1
    
    return match_count / len(field_values)


def decode_timestamp_bytes_be(
    field_bytes: bytes,
    byte_width: int = 4
) -> Optional[int]:
    """从字段字节解码大端时间戳值
    
    Args:
        field_bytes: 字段字节值
        byte_width: 字节宽度（4 或 8）
        
    Returns:
        解码后的整数值，如果失败返回 None
    """
    if len(field_bytes) < byte_width:
        return None
    
    try:
        if byte_width == 4:
            value, = struct.unpack(">I", field_bytes[:4])
        elif byte_width == 8:
            value, = struct.unpack(">Q", field_bytes[:8])
        else:
            return None
        return value
    except struct.error:
        return None


def decode_timestamp_bytes_le(
    field_bytes: bytes,
    byte_width: int = 4
) -> Optional[int]:
    """从字段字节解码小端时间戳值
    
    Args:
        field_bytes: 字段字节值
        byte_width: 字节宽度（4 或 8）
        
    Returns:
        解码后的整数值，如果失败返回 None
    """
    if len(field_bytes) < byte_width:
        return None
    
    try:
        if byte_width == 4:
            value, = struct.unpack("<I", field_bytes[:4])
        elif byte_width == 8:
            value, = struct.unpack("<Q", field_bytes[:8])
        else:
            return None
        return value
    except struct.error:
        return None


def calculate_unix_seconds_support(
    field_values: List[int],
    low_timestamp: Optional[datetime],
    high_timestamp: Optional[datetime],
    slop_seconds: int = 86400
) -> float:
    """计算 Unix 秒时间戳支持率
    
    检查字段值是否为 Unix 秒时间戳（从 1970-01-01 开始的秒数）。
    
    Args:
        field_values: 字段值列表
        low_timestamp: 时间范围下界（如果为 None，返回 0.0）
        high_timestamp: 时间范围上界（如果为 None，返回 0.0）
        slop_seconds: 容差（秒）
        
    Returns:
        支持率 (0.0~1.0)
    """
    return calculate_timestamp_support(
        field_values=field_values,
        low_timestamp=low_timestamp,
        high_timestamp=high_timestamp,
        epoch_offset=0,
        scale=1.0,
        slop_seconds=slop_seconds
    )


def calculate_unix_microseconds_support(
    field_values: List[int],
    low_timestamp: Optional[datetime],
    high_timestamp: Optional[datetime],
    slop_seconds: int = 86400
) -> float:
    """计算 Unix 微秒时间戳支持率

    检查字段值是否为 Unix 微秒时间戳（从 1970-01-01 开始的微秒数）。

    Args:
        field_values: 字段值列表
        low_timestamp: 时间范围下界（如果为 None，返回 0.0）
        high_timestamp: 时间范围上界（如果为 None，返回 0.0）
        slop_seconds: 容差（秒）

    Returns:
        支持率 (0.0~1.0)
    """
    return calculate_timestamp_support(
        field_values=field_values,
        low_timestamp=low_timestamp,
        high_timestamp=high_timestamp,
        epoch_offset=0,
        scale=1000000.0,
        slop_seconds=slop_seconds
    )


def calculate_unix_milliseconds_support(
    field_values: List[int],
    low_timestamp: Optional[datetime],
    high_timestamp: Optional[datetime],
    slop_seconds: int = 86400
) -> float:
    """计算 Unix 毫秒时间戳支持率

    检查字段值是否为 Unix 毫秒时间戳（从 1970-01-01 开始的毫秒数）。

    Args:
        field_values: 字段值列表
        low_timestamp: 时间范围下界（如果为 None，返回 0.0）
        high_timestamp: 时间范围上界（如果为 None，返回 0.0）
        slop_seconds: 容差（秒）

    Returns:
        支持率 (0.0~1.0)
    """
    return calculate_timestamp_support(
        field_values=field_values,
        low_timestamp=low_timestamp,
        high_timestamp=high_timestamp,
        epoch_offset=0,
        scale=1000.0,
        slop_seconds=slop_seconds
    )


def calculate_ntp_seconds_support(
    field_values: List[int],
    low_timestamp: Optional[datetime],
    high_timestamp: Optional[datetime],
    slop_seconds: int = 86400
) -> float:
    """计算 NTP 秒时间戳支持率
    
    检查字段值是否为 NTP 秒时间戳（从 1900-01-01 开始的秒数）。
    NTP 纪元偏移为 2208988800 秒。
    
    Args:
        field_values: 字段值列表
        low_timestamp: 时间范围下界（如果为 None，返回 0.0）
        high_timestamp: 时间范围上界（如果为 None，返回 0.0）
        slop_seconds: 容差（秒）
        
    Returns:
        支持率 (0.0~1.0)
    """
    # NTP 纪元偏移：1900-01-01 到 1970-01-01 的秒数
    ntp_epoch_offset = 2208988800
    
    return calculate_timestamp_support(
        field_values=field_values,
        low_timestamp=low_timestamp,
        high_timestamp=high_timestamp,
        epoch_offset=ntp_epoch_offset,
        scale=1.0,
        slop_seconds=slop_seconds
    )


__all__ = [
    'TIMESTAMP_UNAVAILABLE',
    'is_timestamp_available',
    'get_time_range',
    'calculate_timestamp_support',
    'decode_timestamp_bytes_be',
    'decode_timestamp_bytes_le',
    'calculate_unix_seconds_support',
    'calculate_unix_microseconds_support',
    'calculate_unix_milliseconds_support',
    'calculate_ntp_seconds_support'
]
