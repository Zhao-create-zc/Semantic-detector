"""基础画像统计函数"""

import math
from collections import Counter
from typing import List

from semantic_detector.contracts import FieldSample
from semantic_detector.profiling.profile_builder import FieldProfile
from semantic_detector.bi_adapted.entropy import H


def compute_width_stats(samples: List[FieldSample], profile: FieldProfile) -> FieldProfile:
    """计算宽度 min/max/mode/fixed 统计并填充到 profile。

    Args:
        samples: 同一 FieldKey 的 FieldSample 列表
        profile: 要填充的 FieldProfile

    Returns:
        填充后的 FieldProfile
    """
    if not samples:
        return profile

    widths = [s.end - s.start for s in samples]
    profile.sample_count = len(samples)
    profile.width_min = min(widths)
    profile.width_max = max(widths)

    counter = Counter(widths)
    profile.width_mode = counter.most_common(1)[0][0]
    profile.fixed_width = profile.width_min == profile.width_max

    return profile


def compute_position_stats(samples: List[FieldSample], profile: FieldProfile) -> FieldProfile:
    """计算 start/end 众数和首尾字段比例。

    Args:
        samples: 同一 FieldKey 的 FieldSample 列表
        profile: 要填充的 FieldProfile

    Returns:
        填充后的 FieldProfile
    """
    if not samples:
        return profile

    starts = [s.start for s in samples]
    ends = [s.end for s in samples]

    start_counter = Counter(starts)
    end_counter = Counter(ends)
    profile.start_mode = start_counter.most_common(1)[0][0]
    profile.end_mode = end_counter.most_common(1)[0][0]

    total = len(samples)
    first_count = sum(1 for s in samples if s.start == 0)
    last_count = sum(1 for s in samples if s.remaining_bytes == 0)

    profile.is_first_field_ratio = first_count / total
    profile.is_last_field_ratio = last_count / total

    msg_lengths = [s.message_length for s in samples]
    if any(ml > 0 for ml in msg_lengths):
        position_ratios = [s.start / s.message_length for s in samples if s.message_length > 0]
        profile.position_ratio_mean = sum(position_ratios) / len(position_ratios) if position_ratios else 0.0

    return profile


def compute_value_stats(samples: List[FieldSample], profile: FieldProfile) -> FieldProfile:
    """计算 unique_value_count 和 unique_ratio。

    Args:
        samples: 同一 FieldKey 的 FieldSample 列表
        profile: 要填充的 FieldProfile

    Returns:
        填充后的 FieldProfile
    """
    if not samples:
        return profile

    unique_values = set()
    for s in samples:
        unique_values.add(s.field_bytes)

    profile.unique_value_count = len(unique_values)
    profile.unique_ratio = len(unique_values) / len(samples)

    value_counts = Counter(s.field_bytes for s in samples)
    most_common = value_counts.most_common()
    dominant_count = most_common[0][1]
    profile.dominant_value_ratio = dominant_count / len(samples)
    profile.dominant_value_count = dominant_count
    # R264: 主值 hex 来自真实样本统计；并列（tie）时为 None，不伪造稳定主值
    tie_count = sum(1 for _, c in most_common if c == dominant_count)
    if tie_count > 1:
        profile.dominant_value_hex = None
    else:
        profile.dominant_value_hex = most_common[0][0].hex()

    all_zero_count = sum(1 for s in samples if s.field_bytes == b'\x00' * len(s.field_bytes))
    profile.all_zero_sample_ratio = all_zero_count / len(samples)

    total_bytes = sum(len(s.field_bytes) for s in samples)
    if total_bytes > 0:
        zero_bytes = sum(b.count(0) for s in samples for b in [s.field_bytes])
        profile.zero_byte_ratio = zero_bytes / total_bytes

    return profile


def compute_entropy_stats(samples: List[FieldSample], profile: FieldProfile) -> FieldProfile:
    """计算字段总体 normalized_entropy。

    使用适配自 BI 的 H() 函数计算 Shannon entropy，
    然后除以 log2(n) 归一化到 [0, 1] 范围。

    Args:
        samples: 同一 FieldKey 的 FieldSample 列表
        profile: 要填充的 FieldProfile

    Returns:
        填充后的 FieldProfile
    """
    if not samples:
        return profile

    raw_entropy = H([s.field_bytes for s in samples])
    n = len(samples)
    if n <= 1:
        profile.normalized_entropy = 0.0
    else:
        max_entropy = math.log2(n)
        profile.normalized_entropy = raw_entropy / max_entropy if max_entropy > 0 else 0.0

    return profile


def compute_string_stats(samples: List[FieldSample], profile: FieldProfile) -> FieldProfile:
    """计算 printable_ascii_ratio 和 nonempty_string_ratio。

    printable_ascii_ratio: 可打印 ASCII 字节（0x20-0x7E）占总字节数的比例。
    nonempty_string_ratio: 去尾零后非空字符串占样本数的比例。

    Args:
        samples: 同一 FieldKey 的 FieldSample 列表
        profile: 要填充的 FieldProfile

    Returns:
        填充后的 FieldProfile
    """
    if not samples:
        return profile

    total_bytes = 0
    printable_count = 0
    nonempty_count = 0
    for s in samples:
        for b in s.field_bytes:
            total_bytes += 1
            if 0x20 <= b <= 0x7E:
                printable_count += 1
        stripped = s.field_bytes.rstrip(b'\x00')
        if len(stripped) > 0:
            nonempty_count += 1

    if total_bytes > 0:
        profile.printable_ascii_ratio = printable_count / total_bytes

    profile.nonempty_string_ratio = nonempty_count / len(samples)

    utf8_success_count = 0
    for s in samples:
        try:
            s.field_bytes.decode('utf-8')
            utf8_success_count += 1
        except UnicodeDecodeError:
            pass
    profile.utf8_decode_success_ratio = utf8_success_count / len(samples)

    return profile
