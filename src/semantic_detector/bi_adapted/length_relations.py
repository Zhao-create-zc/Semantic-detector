# This file is derived from BinaryInferno (https://github.com/ChandlerChip/BinaryInferno)
# Original files: binaryinferno/lv.py, lv2.py, lv3.py, lv4.py
# Original functions: Length-Value pair detection
# License: GNU General Public License v3.0 (GPLv3)
# Copyright: Copyright (C) 2023 Jared Chandler (jared.chandler@tufts.edu)
# Modifications: Unified 1~4 byte length extraction, fixed-endian support, field boundary aware

"""长度关系检测

从已知字段边界提取长度候选值，支持 1~4 字节的大端和小端解码。
不扫描其他偏移，只使用 FieldProfile 提供的字段值。
"""

from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class LengthCandidate:
    """长度候选值
    
    表示一个可能的长度值及其解码方式。
    """
    value: int
    byte_width: int
    endian: str  # 'be' or 'le'
    source: str  # 'field_value' or other


def extract_length_candidates_be(
    field_bytes: bytes,
    max_width: int = 4
) -> List[LengthCandidate]:
    """从字段字节提取大端长度候选值
    
    Args:
        field_bytes: 字段字节值
        max_width: 最大字节宽度（1~4）
        
    Returns:
        长度候选值列表
    """
    candidates = []
    
    # 限制宽度
    width = min(len(field_bytes), max_width)
    if width == 0:
        return candidates
    
    # 提取 1~width 字节的大端值
    for byte_count in range(1, width + 1):
        # 取前 byte_count 个字节
        value_bytes = field_bytes[:byte_count]
        
        # 大端解码
        value = int.from_bytes(value_bytes, byteorder='big', signed=False)
        
        candidates.append(LengthCandidate(
            value=value,
            byte_width=byte_count,
            endian='be',
            source='field_value'
        ))
    
    return candidates


def extract_length_candidates_le(
    field_bytes: bytes,
    max_width: int = 4
) -> List[LengthCandidate]:
    """从字段字节提取小端长度候选值
    
    Args:
        field_bytes: 字段字节值
        max_width: 最大字节宽度（1~4）
        
    Returns:
        长度候选值列表
    """
    candidates = []
    
    # 限制宽度
    width = min(len(field_bytes), max_width)
    if width == 0:
        return candidates
    
    # 提取 1~width 字节的小端值
    for byte_count in range(1, width + 1):
        # 取前 byte_count 个字节
        value_bytes = field_bytes[:byte_count]
        
        # 小端解码
        value = int.from_bytes(value_bytes, byteorder='little', signed=False)
        
        candidates.append(LengthCandidate(
            value=value,
            byte_width=byte_count,
            endian='le',
            source='field_value'
        ))
    
    return candidates


def extract_length_candidates(
    field_bytes: bytes,
    max_width: int = 4,
    endian: str = 'both'
) -> List[LengthCandidate]:
    """从字段字节提取长度候选值
    
    Args:
        field_bytes: 字段字节值
        max_width: 最大字节宽度（1~4）
        endian: 字节序 ('be', 'le', 'both')
        
    Returns:
        长度候选值列表
    """
    candidates = []
    
    if endian == 'be':
        candidates.extend(extract_length_candidates_be(field_bytes, max_width))
    elif endian == 'le':
        candidates.extend(extract_length_candidates_le(field_bytes, max_width))
    elif endian == 'both':
        candidates.extend(extract_length_candidates_be(field_bytes, max_width))
        candidates.extend(extract_length_candidates_le(field_bytes, max_width))
    
    return candidates


def calculate_message_length_support(
    field_values: List[int],
    message_lengths: List[int]
) -> float:
    """计算 value == message_length 的支持率
    
    Args:
        field_values: 字段值列表
        message_lengths: 消息长度列表
        
    Returns:
        支持率 (0.0~1.0)
    """
    if len(field_values) == 0 or len(message_lengths) == 0:
        return 0.0
    
    if len(field_values) != len(message_lengths):
        raise ValueError("field_values and message_lengths must have the same length")
    
    match_count = 0
    for value, length in zip(field_values, message_lengths):
        if value == length:
            match_count += 1
    
    return match_count / len(field_values)


def calculate_remaining_bytes_support(
    field_values: List[int],
    remaining_bytes: List[int]
) -> float:
    """计算 value == remaining_bytes 的支持率
    
    Args:
        field_values: 字段值列表
        remaining_bytes: 剩余字节数列表
        
    Returns:
        支持率 (0.0~1.0)
    """
    if len(field_values) == 0 or len(remaining_bytes) == 0:
        return 0.0
    
    if len(field_values) != len(remaining_bytes):
        raise ValueError("field_values and remaining_bytes must have the same length")
    
    match_count = 0
    for value, remaining in zip(field_values, remaining_bytes):
        if value == remaining:
            match_count += 1
    
    return match_count / len(field_values)


def calculate_offset_message_length_support(
    field_values: List[int],
    message_lengths: List[int]
) -> Tuple[float, Optional[int]]:
    """计算 value + offset == message_length 的支持率

    优先接受统一偏移（所有样本使用相同的偏移，返回支持率 1.0）。
    若无统一偏移，则返回最常见偏移的支持率（允许部分支持）。

    Args:
        field_values: 字段值列表
        message_lengths: 消息长度列表

    Returns:
        (支持率, 偏移值) 元组
        - 统一偏移：返回 (1.0, 偏移值)
        - 最常见偏移：返回 (该偏移出现率, 最常见偏移值)
        - 无数据：返回 (0.0, None)
    """
    if len(field_values) == 0 or len(message_lengths) == 0:
        return (0.0, None)
    
    if len(field_values) != len(message_lengths):
        raise ValueError("field_values and message_lengths must have the same length")
    
    # 计算每个样本的偏移
    offsets = []
    for value, length in zip(field_values, message_lengths):
        offset = length - value
        offsets.append(offset)
    
    # 检查是否所有偏移相同
    if len(set(offsets)) == 1:
        # 统一偏移
        offset = offsets[0]
        return (1.0, offset)
    
    # 没有统一偏移，计算最常见的偏移的支持率
    from collections import Counter
    offset_counts = Counter(offsets)
    most_common_offset, count = offset_counts.most_common(1)[0]
    support = count / len(field_values)
    
    return (support, most_common_offset)


def calculate_offset_remaining_bytes_support(
    field_values: List[int],
    remaining_bytes: List[int]
) -> Tuple[float, Optional[int]]:
    """计算 value + offset == remaining_bytes 的支持率

    优先接受统一偏移（所有样本使用相同的偏移，返回支持率 1.0）。
    若无统一偏移，则返回最常见偏移的支持率（允许部分支持）。

    Args:
        field_values: 字段值列表
        remaining_bytes: 剩余字节数列表

    Returns:
        (支持率, 偏移值) 元组
        - 统一偏移：返回 (1.0, 偏移值)
        - 最常见偏移：返回 (该偏移出现率, 最常见偏移值)
        - 无数据：返回 (0.0, None)
    """
    if len(field_values) == 0 or len(remaining_bytes) == 0:
        return (0.0, None)
    
    if len(field_values) != len(remaining_bytes):
        raise ValueError("field_values and remaining_bytes must have the same length")
    
    # 计算每个样本的偏移
    offsets = []
    for value, remaining in zip(field_values, remaining_bytes):
        offset = remaining - value
        offsets.append(offset)
    
    # 检查是否所有偏移相同
    if len(set(offsets)) == 1:
        # 统一偏移
        offset = offsets[0]
        return (1.0, offset)
    
    # 没有统一偏移，计算最常见的偏移的支持率
    from collections import Counter
    offset_counts = Counter(offsets)
    most_common_offset, count = offset_counts.most_common(1)[0]
    support = count / len(field_values)
    
    return (support, most_common_offset)


__all__ = [
    'LengthCandidate',
    'extract_length_candidates_be',
    'extract_length_candidates_le',
    'extract_length_candidates',
    'calculate_message_length_support',
    'calculate_remaining_bytes_support',
    'calculate_offset_message_length_support',
    'calculate_offset_remaining_bytes_support',
]
