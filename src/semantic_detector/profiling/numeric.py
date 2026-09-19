"""R069+R070+R071+R072+R073: 数值解码与统计模块"""

from typing import Optional, List, Tuple
import struct
import math


def decode_unsigned_be(data: bytes) -> Optional[int]:
    """1~8 字节 unsigned 大端解码。

    Args:
        data: 1-8 字节的 bytes

    Returns:
        解码后的整数，或 None（长度不支持时）
    """
    n = len(data)
    if n == 0 or n > 8:
        return None
    return int.from_bytes(data, byteorder='big', signed=False)


def decode_unsigned_le(data: bytes) -> Optional[int]:
    """1~8 字节 unsigned 小端解码。

    Args:
        data: 1-8 字节的 bytes

    Returns:
        解码后的整数，或 None（长度不支持时）
    """
    n = len(data)
    if n == 0 or n > 8:
        return None
    return int.from_bytes(data, byteorder='little', signed=False)


class NumericDecodeUnavailable:
    """数值解码不可用原因"""
    
    VARIABLE_WIDTH = "variable_width"
    UNSUPPORTED_WIDTH = "unsupported_width"
    INSUFFICIENT_SAMPLES = "insufficient_samples"


def check_numeric_decode_available(
    fixed_width: bool,
    width_min: int,
    width_max: int,
    sample_count: int,
    min_samples: int = 1
) -> Optional[str]:
    """检查数值解码是否可用。

    Args:
        fixed_width: 字段是否固定宽度
        width_min: 最小宽度
        width_max: 最大宽度
        sample_count: 样本数量
        min_samples: 最小样本数要求

    Returns:
        None 如果可以解码，否则返回不可用原因代码
    """
    if sample_count < min_samples:
        return NumericDecodeUnavailable.INSUFFICIENT_SAMPLES
    
    if not fixed_width:
        return NumericDecodeUnavailable.VARIABLE_WIDTH
    
    if width_min < 1 or width_max > 8:
        return NumericDecodeUnavailable.UNSUPPORTED_WIDTH
    
    return None


def compute_numeric_min(values: List[int]) -> Optional[int]:
    """计算整数序列的最小值。

    Args:
        values: 整数序列

    Returns:
        最小值，或 None（序列为空时）
    """
    if not values:
        return None
    return min(values)


def compute_numeric_max(values: List[int]) -> Optional[int]:
    """计算整数序列的最大值。

    Args:
        values: 整数序列

    Returns:
        最大值，或 None（序列为空时）
    """
    if not values:
        return None
    return max(values)


def compute_numeric_mean(values: List[int]) -> Optional[float]:
    """计算整数序列的平均值。

    Args:
        values: 整数序列

    Returns:
        平均值，或 None（序列为空时）
    """
    if not values:
        return None
    return sum(values) / len(values)


def compute_numeric_median(values: List[int]) -> Optional[float]:
    """计算整数序列的中位数。

    Args:
        values: 整数序列

    Returns:
        中位数，或 None（序列为空时）
    """
    if not values:
        return None
    
    sorted_values = sorted(values)
    n = len(sorted_values)
    mid = n // 2
    
    if n % 2 == 1:
        return float(sorted_values[mid])
    else:
        return (sorted_values[mid - 1] + sorted_values[mid]) / 2.0


def compute_numeric_stats(values: List[int]) -> Optional[Tuple[int, int, float, float]]:
    """计算整数序列的完整统计。

    Args:
        values: 整数序列

    Returns:
        (min, max, mean, median) 元组，或 None（序列为空时）
    """
    if not values:
        return None
    
    min_val = compute_numeric_min(values)
    max_val = compute_numeric_max(values)
    mean_val = compute_numeric_mean(values)
    median_val = compute_numeric_median(values)
    
    if min_val is None or max_val is None or mean_val is None or median_val is None:
        return None
    
    return (min_val, max_val, mean_val, median_val)


def compute_pearson_correlation(x: List[float], y: List[float]) -> Optional[float]:
    """计算两个序列的 Pearson 相关系数。

    Args:
        x: 第一个数值序列
        y: 第二个数值序列

    Returns:
        Pearson 相关系数 (-1 到 1)，或 None（序列为空、长度不匹配或常量序列时）
    """
    if not x or not y:
        return None
    
    if len(x) != len(y):
        return None
    
    n = len(x)
    if n < 2:
        return None
    
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    
    numerator = 0.0
    sum_sq_x = 0.0
    sum_sq_y = 0.0
    
    for i in range(n):
        dx = x[i] - mean_x
        dy = y[i] - mean_y
        numerator += dx * dy
        sum_sq_x += dx * dx
        sum_sq_y += dy * dy
    
    if sum_sq_x == 0.0 or sum_sq_y == 0.0:
        return None
    
    denominator = math.sqrt(sum_sq_x * sum_sq_y)
    return numerator / denominator


def compute_strictly_increasing_ratio(values: List[int]) -> Optional[float]:
    """计算序列中严格递增相邻对的比例。

    Args:
        values: 整数序列

    Returns:
        严格递增比例 (0 到 1)，或 None（序列少于 2 个元素时）
    """
    if len(values) < 2:
        return None
    
    total_pairs = len(values) - 1
    increasing_count = 0
    
    for i in range(total_pairs):
        if values[i] < values[i + 1]:
            increasing_count += 1
    
    return increasing_count / total_pairs


def compute_nondecreasing_ratio(values: List[int]) -> Optional[float]:
    """计算序列中非递减相邻对的比例。

    Args:
        values: 整数序列

    Returns:
        非递减比例 (0 到 1)，或 None（序列少于 2 个元素时）
    """
    if len(values) < 2:
        return None
    
    total_pairs = len(values) - 1
    nondecreasing_count = 0
    
    for i in range(total_pairs):
        if values[i] <= values[i + 1]:
            nondecreasing_count += 1
    
    return nondecreasing_count / total_pairs


def compute_step_one_ratio(values: List[int]) -> Optional[float]:
    """计算序列中步长为 1 的相邻对的比例。

    Args:
        values: 整数序列

    Returns:
        步长为 1 的比例 (0 到 1)，或 None（序列少于 2 个元素时）
    """
    if len(values) < 2:
        return None
    
    total_pairs = len(values) - 1
    step_one_count = 0
    
    for i in range(total_pairs):
        if values[i + 1] - values[i] == 1:
            step_one_count += 1
    
    return step_one_count / total_pairs


def compute_numeric_message_length_correlation(
    numeric_values: List[int],
    message_lengths: List[int]
) -> Optional[float]:
    """计算数值与消息长度的 Pearson 相关系数。

    Args:
        numeric_values: 数值序列
        message_lengths: 对应的消息长度序列

    Returns:
        Pearson 相关系数，或 None（序列为空、长度不匹配或常量序列时）
    """
    if len(numeric_values) != len(message_lengths):
        return None
    
    x = [float(v) for v in numeric_values]
    y = [float(v) for v in message_lengths]
    
    return compute_pearson_correlation(x, y)


def compute_numeric_remaining_bytes_correlation(
    numeric_values: List[int],
    remaining_bytes: List[int]
) -> Optional[float]:
    """计算数值与剩余字节数的 Pearson 相关系数。

    Args:
        numeric_values: 数值序列
        remaining_bytes: 对应的剩余字节数序列

    Returns:
        Pearson 相关系数，或 None（序列为空、长度不匹配或常量序列时）
    """
    if len(numeric_values) != len(remaining_bytes):
        return None
    
    x = [float(v) for v in numeric_values]
    y = [float(v) for v in remaining_bytes]
    
    return compute_pearson_correlation(x, y)
