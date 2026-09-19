"""FieldProfile 数据类与构建函数"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional

from semantic_detector.contracts import FieldKey, FieldSample


@dataclass
class FieldProfile:
    """字段画像，保存统一画像数据，不保存无法序列化的对象"""

    # 标识
    layout_id: str = ""
    direction: str = ""
    field_index: int = 0

    # 基础统计
    sample_count: int = 0

    # 宽度与位置
    width_min: int = 0
    width_max: int = 0
    width_mode: int = 0
    fixed_width: bool = False
    start_mode: int = 0
    end_mode: int = 0
    is_first_field_ratio: float = 0.0
    is_last_field_ratio: float = 0.0
    position_ratio_mean: float = 0.0

    # 字节统计
    unique_value_count: int = 0
    unique_ratio: float = 0.0
    dominant_value_ratio: float = 0.0
    dominant_value_hex: Optional[str] = None
    dominant_value_count: int = 0
    all_zero_sample_ratio: float = 0.0
    zero_byte_ratio: float = 0.0
    printable_ascii_ratio: float = 0.0
    nonempty_string_ratio: float = 0.0
    utf8_decode_success_ratio: float = 0.0
    normalized_entropy: float = 0.0

    # 数值统计(大端)
    numeric_be_min: Optional[int] = None
    numeric_be_max: Optional[int] = None
    numeric_be_mean: Optional[float] = None
    numeric_be_median: Optional[float] = None
    numeric_be_strictly_increasing_ratio: Optional[float] = None
    numeric_be_nondecreasing_ratio: Optional[float] = None
    numeric_be_step_one_ratio: Optional[float] = None
    numeric_be_message_length_correlation: Optional[float] = None
    numeric_be_remaining_bytes_correlation: Optional[float] = None
    # R266: BE 精确长度关系支持率（HIGH-7 length 修复铺路）
    numeric_be_message_length_exact_support: Optional[float] = None
    numeric_be_remaining_bytes_exact_support: Optional[float] = None
    numeric_be_message_length_offset_support: Optional[float] = None
    numeric_be_message_length_offset: Optional[int] = None
    numeric_be_remaining_bytes_offset_support: Optional[float] = None
    numeric_be_remaining_bytes_offset: Optional[int] = None

    # 数值统计(小端)
    numeric_le_min: Optional[int] = None
    numeric_le_max: Optional[int] = None
    numeric_le_mean: Optional[float] = None
    numeric_le_median: Optional[float] = None
    numeric_le_strictly_increasing_ratio: Optional[float] = None
    numeric_le_nondecreasing_ratio: Optional[float] = None
    numeric_le_step_one_ratio: Optional[float] = None
    numeric_le_message_length_correlation: Optional[float] = None
    numeric_le_remaining_bytes_correlation: Optional[float] = None
    # R267: LE 精确长度关系支持率（与 BE 对称，端序独立）
    numeric_le_message_length_exact_support: Optional[float] = None
    numeric_le_remaining_bytes_exact_support: Optional[float] = None
    numeric_le_message_length_offset_support: Optional[float] = None
    numeric_le_message_length_offset: Optional[int] = None
    numeric_le_remaining_bytes_offset_support: Optional[float] = None
    numeric_le_remaining_bytes_offset: Optional[int] = None
    
    # 时间戳统计(大端)
    timestamp_be_unix_seconds_support: Optional[float] = None
    timestamp_be_unix_milliseconds_support: Optional[float] = None
    timestamp_be_unix_microseconds_support: Optional[float] = None
    timestamp_be_ntp_seconds_support: Optional[float] = None
    
    # 时间戳统计(小端)
    timestamp_le_unix_seconds_support: Optional[float] = None
    timestamp_le_unix_milliseconds_support: Optional[float] = None
    timestamp_le_unix_microseconds_support: Optional[float] = None
    timestamp_le_ntp_seconds_support: Optional[float] = None

    # R270: capture_time 元数据（HIGH-4 timestamp 铺路）
    # capture_time_count: 有 capture_time 的样本数
    # capture_time_coverage: capture_time_count / sample_count
    # capture_time_min/max: 最早/最晚 capture_time（UTC aware datetime）
    capture_time_count: int = 0
    capture_time_coverage: float = 0.0
    capture_time_min: Optional[Any] = None
    capture_time_max: Optional[Any] = None

    # 元数据
    insufficient_samples: bool = False
    # R266: 数值去重计数（防止常量字段被误判为长度，至少需要 2 个不同值）
    numeric_be_distinct_value_count: Optional[int] = None
    numeric_le_distinct_value_count: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为可 JSON 序列化的字典"""
        return {
            "layout_id": self.layout_id,
            "direction": self.direction,
            "field_index": self.field_index,
            "sample_count": self.sample_count,
            "width_min": self.width_min,
            "width_max": self.width_max,
            "width_mode": self.width_mode,
            "fixed_width": self.fixed_width,
            "start_mode": self.start_mode,
            "end_mode": self.end_mode,
            "is_first_field_ratio": self.is_first_field_ratio,
            "is_last_field_ratio": self.is_last_field_ratio,
            "position_ratio_mean": self.position_ratio_mean,
            "unique_value_count": self.unique_value_count,
            "unique_ratio": self.unique_ratio,
            "dominant_value_ratio": self.dominant_value_ratio,
            "dominant_value_hex": self.dominant_value_hex,
            "dominant_value_count": self.dominant_value_count,
            "all_zero_sample_ratio": self.all_zero_sample_ratio,
            "zero_byte_ratio": self.zero_byte_ratio,
            "printable_ascii_ratio": self.printable_ascii_ratio,
            "nonempty_string_ratio": self.nonempty_string_ratio,
            "utf8_decode_success_ratio": self.utf8_decode_success_ratio,
            "normalized_entropy": self.normalized_entropy,
            "numeric_be_min": self.numeric_be_min,
            "numeric_be_max": self.numeric_be_max,
            "numeric_be_mean": self.numeric_be_mean,
            "numeric_be_median": self.numeric_be_median,
            "numeric_be_strictly_increasing_ratio": self.numeric_be_strictly_increasing_ratio,
            "numeric_be_nondecreasing_ratio": self.numeric_be_nondecreasing_ratio,
            "numeric_be_step_one_ratio": self.numeric_be_step_one_ratio,
            "numeric_be_message_length_correlation": self.numeric_be_message_length_correlation,
            "numeric_be_remaining_bytes_correlation": self.numeric_be_remaining_bytes_correlation,
            "numeric_be_message_length_exact_support": self.numeric_be_message_length_exact_support,
            "numeric_be_remaining_bytes_exact_support": self.numeric_be_remaining_bytes_exact_support,
            "numeric_be_message_length_offset_support": self.numeric_be_message_length_offset_support,
            "numeric_be_message_length_offset": self.numeric_be_message_length_offset,
            "numeric_be_remaining_bytes_offset_support": self.numeric_be_remaining_bytes_offset_support,
            "numeric_be_remaining_bytes_offset": self.numeric_be_remaining_bytes_offset,
            "numeric_le_min": self.numeric_le_min,
            "numeric_le_max": self.numeric_le_max,
            "numeric_le_mean": self.numeric_le_mean,
            "numeric_le_median": self.numeric_le_median,
            "numeric_le_strictly_increasing_ratio": self.numeric_le_strictly_increasing_ratio,
            "numeric_le_nondecreasing_ratio": self.numeric_le_nondecreasing_ratio,
            "numeric_le_step_one_ratio": self.numeric_le_step_one_ratio,
            "numeric_le_message_length_correlation": self.numeric_le_message_length_correlation,
            "numeric_le_remaining_bytes_correlation": self.numeric_le_remaining_bytes_correlation,
            "numeric_le_message_length_exact_support": self.numeric_le_message_length_exact_support,
            "numeric_le_remaining_bytes_exact_support": self.numeric_le_remaining_bytes_exact_support,
            "numeric_le_message_length_offset_support": self.numeric_le_message_length_offset_support,
            "numeric_le_message_length_offset": self.numeric_le_message_length_offset,
            "numeric_le_remaining_bytes_offset_support": self.numeric_le_remaining_bytes_offset_support,
            "numeric_le_remaining_bytes_offset": self.numeric_le_remaining_bytes_offset,
            # R271: timestamp support 字段写入 to_dict（教程 9.3：将现有 timestamp support 真正写入 to_dict）
            "timestamp_be_unix_seconds_support": self.timestamp_be_unix_seconds_support,
            "timestamp_be_unix_milliseconds_support": self.timestamp_be_unix_milliseconds_support,
            "timestamp_be_unix_microseconds_support": self.timestamp_be_unix_microseconds_support,
            "timestamp_be_ntp_seconds_support": self.timestamp_be_ntp_seconds_support,
            "timestamp_le_unix_seconds_support": self.timestamp_le_unix_seconds_support,
            "timestamp_le_unix_milliseconds_support": self.timestamp_le_unix_milliseconds_support,
            "timestamp_le_unix_microseconds_support": self.timestamp_le_unix_microseconds_support,
            "timestamp_le_ntp_seconds_support": self.timestamp_le_ntp_seconds_support,
            "capture_time_count": self.capture_time_count,
            "capture_time_coverage": self.capture_time_coverage,
            # R270: datetime 转 ISO 字符串以便 JSON 化（教程 9.3：UTC 时间可 JSON 化）
            "capture_time_min": self.capture_time_min.isoformat() if hasattr(self.capture_time_min, 'isoformat') else self.capture_time_min,
            "capture_time_max": self.capture_time_max.isoformat() if hasattr(self.capture_time_max, 'isoformat') else self.capture_time_max,
            "insufficient_samples": self.insufficient_samples,
            "numeric_be_distinct_value_count": self.numeric_be_distinct_value_count,
            "numeric_le_distinct_value_count": self.numeric_le_distinct_value_count,
        }


def build_field_profile(
    field_key: FieldKey,
    samples: List[FieldSample],
    slop_seconds: Optional[int] = None,
    min_samples: Optional[int] = None,
) -> FieldProfile:
    """从 FieldKey 和 FieldSample 列表构建完整的 FieldProfile。

    调用所有基础统计函数填充画像。

    R358：slop_seconds 参数让 Config.timestamp_slop_seconds 真正传入
    calculate_*_support 调用，消除"Config 一套 / Detector 硬编码另一套"
    的不一致。None 时用 calculate_*_support 的默认值 86400（向后兼容）。

    R405：min_samples 参数让 Config.min_samples 真正接入画像构建，
    sample_count < min_samples 时标记 insufficient_samples=True。
    None 时不标记（保持向后兼容，insufficient_samples 保持默认 False）。
    不在函数内部构造 Config，由调用方传入 resolved 值。

    Args:
        field_key: 字段标识
        samples: 该字段的 FieldSample 列表
        slop_seconds: 时间戳容差秒数（来自 config.timestamp_slop_seconds）。
            None 时用函数默认值 86400。
        min_samples: 最小样本数阈值（来自 config.min_samples）。
            None 时不标记 insufficient_samples（向后兼容）。
            提供时 sample_count < min_samples → insufficient_samples=True。

    Returns:
        填充完整的 FieldProfile

    Raises:
        ValueError: 当 samples 为空列表时
    """
    if not samples:
        raise ValueError("Cannot build profile from empty samples")

    # R358：将 slop_seconds 统一为有效值（None 时用默认 86400）
    slop = slop_seconds if slop_seconds is not None else 86400

    from semantic_detector.profiling.basic_stats import (
        compute_width_stats,
        compute_position_stats,
        compute_value_stats,
        compute_entropy_stats,
        compute_string_stats,
    )

    profile = FieldProfile(
        layout_id=field_key.layout_id,
        direction=field_key.direction.value,
        field_index=field_key.field_index,
    )

    compute_width_stats(samples, profile)
    compute_position_stats(samples, profile)
    compute_value_stats(samples, profile)
    compute_entropy_stats(samples, profile)
    compute_string_stats(samples, profile)

    # 计算数值统计
    from semantic_detector.profiling.numeric import (
        check_numeric_decode_available,
        decode_unsigned_be,
        decode_unsigned_le,
        compute_numeric_stats,
        compute_strictly_increasing_ratio,
        compute_nondecreasing_ratio,
        compute_step_one_ratio,
        compute_numeric_message_length_correlation,
        compute_numeric_remaining_bytes_correlation,
    )

    # 检查是否可以解码数值
    decode_available = check_numeric_decode_available(
        fixed_width=profile.fixed_width,
        width_min=profile.width_min,
        width_max=profile.width_max,
        sample_count=profile.sample_count,
        min_samples=2
    )

    if decode_available is None:
        # 可以解码,计算数值统计
        be_values = []
        le_values = []
        message_lengths = []
        remaining_bytes_list = []

        for sample in samples:
            be_val = decode_unsigned_be(sample.field_bytes)
            le_val = decode_unsigned_le(sample.field_bytes)
            if be_val is not None and le_val is not None:
                be_values.append(be_val)
                le_values.append(le_val)
                message_lengths.append(sample.message_length)
                remaining_bytes_list.append(sample.remaining_bytes)

        if be_values:
            # 大端统计
            be_stats = compute_numeric_stats(be_values)
            if be_stats:
                profile.numeric_be_min, profile.numeric_be_max, profile.numeric_be_mean, profile.numeric_be_median = be_stats
            
            profile.numeric_be_strictly_increasing_ratio = compute_strictly_increasing_ratio(be_values)
            profile.numeric_be_nondecreasing_ratio = compute_nondecreasing_ratio(be_values)
            profile.numeric_be_step_one_ratio = compute_step_one_ratio(be_values)
            # R268: correlation 仅作画像描述保留，不可作为 length 判定硬证据
            # （correlation=1.0 不代表 value==length，参见教程 8.1）。
            # 长度判定必须看下面的 exact_support / offset_support（来自 bi_adapted.length_relations，
            # 输入为真实 FieldSample 提取的 be_values + message_lengths/remaining_bytes_list）。
            profile.numeric_be_message_length_correlation = compute_numeric_message_length_correlation(be_values, message_lengths)
            profile.numeric_be_remaining_bytes_correlation = compute_numeric_remaining_bytes_correlation(be_values, remaining_bytes_list)

            # R266: BE 精确长度关系支持率（复用 bi_adapted.length_relations，HIGH-7 铺路）
            from semantic_detector.bi_adapted.length_relations import (
                calculate_message_length_support,
                calculate_remaining_bytes_support,
                calculate_offset_message_length_support,
                calculate_offset_remaining_bytes_support,
            )
            profile.numeric_be_message_length_exact_support = calculate_message_length_support(be_values, message_lengths)
            profile.numeric_be_remaining_bytes_exact_support = calculate_remaining_bytes_support(be_values, remaining_bytes_list)
            be_ml_offset_support, be_ml_offset = calculate_offset_message_length_support(be_values, message_lengths)
            be_rb_offset_support, be_rb_offset = calculate_offset_remaining_bytes_support(be_values, remaining_bytes_list)
            profile.numeric_be_message_length_offset_support = be_ml_offset_support
            profile.numeric_be_message_length_offset = be_ml_offset
            profile.numeric_be_remaining_bytes_offset_support = be_rb_offset_support
            profile.numeric_be_remaining_bytes_offset = be_rb_offset
            profile.numeric_be_distinct_value_count = len(set(be_values))

            # 小端统计
            le_stats = compute_numeric_stats(le_values)
            if le_stats:
                profile.numeric_le_min, profile.numeric_le_max, profile.numeric_le_mean, profile.numeric_le_median = le_stats
            
            profile.numeric_le_strictly_increasing_ratio = compute_strictly_increasing_ratio(le_values)
            profile.numeric_le_nondecreasing_ratio = compute_nondecreasing_ratio(le_values)
            profile.numeric_le_step_one_ratio = compute_step_one_ratio(le_values)
            # R268: correlation 仅作画像描述保留，不可作为 length 判定硬证据（同 BE 注释）。
            profile.numeric_le_message_length_correlation = compute_numeric_message_length_correlation(le_values, message_lengths)
            profile.numeric_le_remaining_bytes_correlation = compute_numeric_remaining_bytes_correlation(le_values, remaining_bytes_list)

            # R267: LE 精确长度关系支持率（与 BE 对称，端序独立）
            profile.numeric_le_message_length_exact_support = calculate_message_length_support(le_values, message_lengths)
            profile.numeric_le_remaining_bytes_exact_support = calculate_remaining_bytes_support(le_values, remaining_bytes_list)
            le_ml_offset_support, le_ml_offset = calculate_offset_message_length_support(le_values, message_lengths)
            le_rb_offset_support, le_rb_offset = calculate_offset_remaining_bytes_support(le_values, remaining_bytes_list)
            profile.numeric_le_message_length_offset_support = le_ml_offset_support
            profile.numeric_le_message_length_offset = le_ml_offset
            profile.numeric_le_remaining_bytes_offset_support = le_rb_offset_support
            profile.numeric_le_remaining_bytes_offset = le_rb_offset
            profile.numeric_le_distinct_value_count = len(set(le_values))

    # R270: capture_time 元数据（HIGH-4 timestamp 铺路）
    # 教程 9.3/9.4：从 FieldSample.capture_time 提取统计，
    # 所有 capture_time 缺失时 count=0/coverage=0.0/min/max=None，
    # 不使用当前系统时间兜底（教程 9.4 强制要求）。
    capture_times = [s.capture_time for s in samples if s.capture_time is not None]
    profile.capture_time_count = len(capture_times)
    if profile.sample_count > 0:
        profile.capture_time_coverage = profile.capture_time_count / profile.sample_count
    else:
        profile.capture_time_coverage = 0.0
    if capture_times:
        profile.capture_time_min = min(capture_times)
        profile.capture_time_max = max(capture_times)
    else:
        profile.capture_time_min = None
        profile.capture_time_max = None

    # R271: Unix 秒 BE/LE timestamp support（HIGH-4 timestamp 铺路）
    # R273: NTP 秒 BE/LE timestamp support（NTP 纪元 1900，4 字节秒）
    # 教程 9.4/9.5：
    # - 4 字节固定宽度才计算（decode_timestamp_bytes_be/le 需要 byte_width=4）
    # - 所有 capture_time 缺失时 support=None（不用当前系统时间兜底）
    # - 时间上下界使用 UTC aware datetime（来自 capture_time_min/max）
    # - 复用 bi_adapted.timestamp_range 的 decode + calculate_unix/ntp_seconds_support
    # - 8 字节完整 NTP（高 32 位秒 + 低 32 位小数）暂不实现（教程 9.5：若不能正确实现应暂不输出）
    if (profile.fixed_width
            and profile.width_min == 4
            and profile.width_max == 4
            and profile.capture_time_count > 0):
        from semantic_detector.bi_adapted.timestamp_range import (
            decode_timestamp_bytes_be,
            decode_timestamp_bytes_le,
            calculate_unix_seconds_support,
            calculate_ntp_seconds_support,
        )
        # 解码 4 字节 BE/LE 时间戳值
        be_ts_values = [decode_timestamp_bytes_be(s.field_bytes, 4) for s in samples]
        le_ts_values = [decode_timestamp_bytes_le(s.field_bytes, 4) for s in samples]
        be_ts_values = [v for v in be_ts_values if v is not None]
        le_ts_values = [v for v in le_ts_values if v is not None]
        # R358：slop_seconds 从 config.timestamp_slop_seconds 传入
        if be_ts_values:
            profile.timestamp_be_unix_seconds_support = calculate_unix_seconds_support(
                be_ts_values,
                profile.capture_time_min,
                profile.capture_time_max,
                slop_seconds=slop,
            )
        if le_ts_values:
            profile.timestamp_le_unix_seconds_support = calculate_unix_seconds_support(
                le_ts_values,
                profile.capture_time_min,
                profile.capture_time_max,
                slop_seconds=slop,
            )
        # R273: NTP 秒支持率（NTP 纪元 1900-01-01，epoch_offset=2208988800）
        # 复用同一批 4 字节解码值，与 Unix 秒对称（仅 epoch 不同）
        if be_ts_values:
            profile.timestamp_be_ntp_seconds_support = calculate_ntp_seconds_support(
                be_ts_values,
                profile.capture_time_min,
                profile.capture_time_max,
                slop_seconds=slop,
            )
        if le_ts_values:
            profile.timestamp_le_ntp_seconds_support = calculate_ntp_seconds_support(
                le_ts_values,
                profile.capture_time_min,
                profile.capture_time_max,
                slop_seconds=slop,
            )
    # 否则 support 保持默认 None（capture_time 缺失或非 4 字节固定宽度）

    # R272: Unix ms/us BE/LE timestamp support（8 字节字段，HIGH-4 timestamp 铺路）
    # 教程 9.4：8 字节固定宽度才计算 ms/us（decode_timestamp_bytes_be/le 需要 byte_width=8）
    # - ms: scale=1000.0（Unix 毫秒，从 1970-01-01 开始的毫秒数）
    # - us: scale=1000000.0（Unix 微秒）
    # - capture_time 缺失时 support=None（同 R271 规则）
    # - 复用 bi_adapted.timestamp_range 的 calculate_unix_milliseconds/microseconds_support
    if (profile.fixed_width
            and profile.width_min == 8
            and profile.width_max == 8
            and profile.capture_time_count > 0):
        from semantic_detector.bi_adapted.timestamp_range import (
            decode_timestamp_bytes_be as _decode_be_8,
            decode_timestamp_bytes_le as _decode_le_8,
            calculate_unix_milliseconds_support,
            calculate_unix_microseconds_support,
        )
        # 解码 8 字节 BE/LE 时间戳值
        be_ts_values_8 = [v for v in (_decode_be_8(s.field_bytes, 8) for s in samples) if v is not None]
        le_ts_values_8 = [v for v in (_decode_le_8(s.field_bytes, 8) for s in samples) if v is not None]
        # R358：slop_seconds 从 config.timestamp_slop_seconds 传入
        if be_ts_values_8:
            profile.timestamp_be_unix_milliseconds_support = calculate_unix_milliseconds_support(
                be_ts_values_8,
                profile.capture_time_min,
                profile.capture_time_max,
                slop_seconds=slop,
            )
            profile.timestamp_be_unix_microseconds_support = calculate_unix_microseconds_support(
                be_ts_values_8,
                profile.capture_time_min,
                profile.capture_time_max,
                slop_seconds=slop,
            )
        if le_ts_values_8:
            profile.timestamp_le_unix_milliseconds_support = calculate_unix_milliseconds_support(
                le_ts_values_8,
                profile.capture_time_min,
                profile.capture_time_max,
                slop_seconds=slop,
            )
            profile.timestamp_le_unix_microseconds_support = calculate_unix_microseconds_support(
                le_ts_values_8,
                profile.capture_time_min,
                profile.capture_time_max,
                slop_seconds=slop,
            )
    # 否则 ms/us support 保持默认 None

    # R405：接入 Config.min_samples，sample_count < min_samples 时标记不足
    # None 时不标记（保持向后兼容，insufficient_samples 保持默认 False）
    # 不在函数内部构造 Config，由调用方传入 resolved min_samples 值
    if min_samples is not None:
        profile.insufficient_samples = profile.sample_count < min_samples

    return profile


def build_field_profiles(
    records: List,
    slop_seconds: Optional[int] = None,
    min_samples: Optional[int] = None,
) -> List[FieldProfile]:
    """从记录列表构建字段画像

    统一复用 collector.record_to_field_samples 与 collector.aggregate_by_field_key，
    不在画像构建处重复一套分组与切片逻辑，避免 direction 被破坏。

    实现要点（修复 HIGH-1）：
    - 不使用 str(record.direction) 生成键；
    - 不依赖外层循环残留变量；
    - 不在 profile builder 内手工切片；
    - 不丢弃 capture_time/session_id/pair_id/input_order。

    R358：slop_seconds 参数让 Config.timestamp_slop_seconds 真正传入
    build_field_profile，消除"Config 一套 / Detector 硬编码另一套"的不一致。
    None 时用 build_field_profile 的默认值 86400（向后兼容）。

    R405：min_samples 参数让 Config.min_samples 真正接入画像构建，
    sample_count < min_samples 时标记 insufficient_samples=True。
    None 时不标记（保持向后兼容）。不在函数内部构造 Config，
    由调用方传入 resolved 值（CLI 传 config.min_samples）。

    Args:
        records: MessageRecord 列表
        slop_seconds: 时间戳容差秒数（来自 config.timestamp_slop_seconds）。
            None 时用默认值 86400。
        min_samples: 最小样本数阈值（来自 config.min_samples）。
            None 时不标记 insufficient_samples（向后兼容）。
            提供时 sample_count < min_samples → insufficient_samples=True。

    Returns:
        FieldProfile 列表，按 (layout_id, direction.value, field_index) 稳定排序
    """
    from semantic_detector.profiling.collector import (
        record_to_field_samples,
        aggregate_by_field_key,
    )

    samples: List[FieldSample] = []
    for record in records:
        samples.extend(record_to_field_samples(record))

    grouped = aggregate_by_field_key(samples)

    return [
        build_field_profile(
            field_key,
            field_samples,
            slop_seconds=slop_seconds,
            min_samples=min_samples,
        )
        for field_key, field_samples in grouped.items()
    ]
