"""字段样本收集器：按 layout_id + direction 分组"""

from collections import OrderedDict, Counter
from typing import Dict, List, Tuple

from semantic_detector.contracts import (
    FieldKey,
    FieldSample,
    FieldSpan,
    MessageRecord,
    RejectionRecord,
    REJECTION_REASON_INCONSISTENT_FIELD_COUNT,
)


def group_by_layout_and_direction(records: List[MessageRecord]) -> Dict[Tuple[str, str], List[MessageRecord]]:
    """按 (layout_id, direction.value) 对消息进行稳定分组。

    同组内保持输入顺序，组间按 (layout_id, direction.value) 排序以保证可复现。

    Args:
        records: MessageRecord 列表

    Returns:
        OrderedDict，键为 (layout_id, direction.value) 元组，值为该组的 MessageRecord 列表
    """
    groups: Dict[Tuple[str, str], List[MessageRecord]] = {}
    for record in records:
        key = (record.layout_id, record.direction.value)
        if key not in groups:
            groups[key] = []
        groups[key].append(record)

    sorted_keys = sorted(groups.keys())
    return OrderedDict((k, groups[k]) for k in sorted_keys)


def validate_group_field_count(groups: Dict[Tuple[str, str], List[MessageRecord]]) -> Tuple[Dict[Tuple[str, str], List[MessageRecord]], List[RejectionRecord]]:
    """校验同组内所有消息的字段数量是否一致。

    一旦同一 (layout_id, direction) 组内字段数量不一致，**整组拒绝**：
    该组全部记录进入一个 RejectionRecord，不保留第一条基准子集，不补齐、不截断。
    只有组内所有记录字段数量一致时，整组保留为 valid。

    Args:
        groups: group_by_layout_and_direction 返回的分组字典

    Returns:
        (valid_groups, rejections) 元组
        valid_groups: 字段数量一致的分组（整组保留）
        rejections: 因所在组字段数量不一致被整组拒绝的 RejectionRecord 列表，
            每个包含 group_key / record_count / field_counts / reason_code / records
    """
    valid_groups: Dict[Tuple[str, str], List[MessageRecord]] = OrderedDict()
    rejections: List[RejectionRecord] = []

    for key, records in groups.items():
        if not records:
            valid_groups[key] = []
            continue

        count_dist = Counter(len(r.fields) for r in records)
        if len(count_dist) == 1:
            # 全组字段数一致，整组保留
            valid_groups[key] = list(records)
        else:
            # 字段数不一致，整组拒绝，构造稳定错误结构
            # field_counts 按 field_count 升序排序以保证可复现
            field_counts = tuple(sorted(count_dist.items()))
            rejections.append(
                RejectionRecord(
                    group_key=key,
                    record_count=len(records),
                    field_counts=field_counts,
                    reason_code=REJECTION_REASON_INCONSISTENT_FIELD_COUNT,
                    records=tuple(records),
                )
            )

    return valid_groups, rejections


def prepare_records_for_profiling(
    records: List[MessageRecord],
) -> Tuple[List[MessageRecord], Dict[Tuple[str, str], List[MessageRecord]], List[RejectionRecord]]:
    """统一准备流程：分组 → 字段数校验 → 展平为 valid_records。

    这是 cmd_validate / cmd_profile / cmd_run 共享的单一入口，避免每个 CLI
    命令重复实现分组与校验而漏掉字段数校验（修复 HIGH-2）。

    流程：
        1. group_by_layout_and_direction(records)
        2. validate_group_field_count(groups)  # 整组拒绝不一致组
        3. 将 valid_groups 按 (layout_id, direction.value) 排序展平为 valid_records

    Args:
        records: 原始 MessageRecord 列表

    Returns:
        (valid_records, valid_groups, rejections) 三元组
        valid_records: 通过校验的 MessageRecord 列表（按组顺序展平，组内保持输入顺序）
        valid_groups: 字段数量一致的分组 OrderedDict
        rejections: 因字段数不一致被整组拒绝的 RejectionRecord 列表
    """
    groups = group_by_layout_and_direction(records)
    valid_groups, rejections = validate_group_field_count(groups)

    valid_records: List[MessageRecord] = []
    for _key, recs in valid_groups.items():
        valid_records.extend(recs)

    return valid_records, valid_groups, rejections


def slice_message_fields(record: MessageRecord) -> List[Tuple[int, bytes]]:
    """按字段边界精确切片单条消息的 payload。

    使用 FieldSpan 中的 start/end 直接切片，不重新推断边界。
    变长字段保留真实宽度。

    Args:
        record: MessageRecord 实例

    Returns:
        [(field_index, field_bytes), ...] 列表，按 field_index 排序
    """
    results = []
    for field in record.fields:
        field_bytes = record.payload[field.start:field.end]
        results.append((field.field_index, field_bytes))
    return results


def record_to_field_samples(record: MessageRecord) -> List[FieldSample]:
    """将单条 MessageRecord 转换为 FieldSample 列表。

    每个 FieldSample 可追溯到 message_id，保留原始字段边界，
    不使用 min(message_length)，变长字段保留真实宽度。

    Args:
        record: MessageRecord 实例

    Returns:
        FieldSample 列表，按 field_index 排序
    """
    message_length = len(record.payload)
    samples = []
    for field in record.fields:
        field_bytes = record.payload[field.start:field.end]
        remaining_bytes = message_length - field.end
        field_key = FieldKey(
            layout_id=record.layout_id,
            direction=record.direction,
            field_index=field.field_index,
        )
        sample = FieldSample(
            message_id=record.message_id,
            field_key=field_key,
            field_bytes=field_bytes,
            start=field.start,
            end=field.end,
            message_length=message_length,
            remaining_bytes=remaining_bytes,
            capture_time=record.capture_time,
            session_id=record.session_id,
            pair_id=record.pair_id,
            input_order=record.input_order,
        )
        samples.append(sample)
    return samples


def aggregate_by_field_key(samples: List[FieldSample]) -> Dict[FieldKey, List[FieldSample]]:
    """按 FieldKey 聚合 FieldSample 列表。

    同一 FieldKey（相同 layout_id, direction, field_index）的样本归为一组，
    组内按 input_order 保持稳定顺序，组间按 FieldKey 排序保证可复现。

    Args:
        samples: FieldSample 列表

    Returns:
        OrderedDict，键为 FieldKey，值为该组的 FieldSample 列表
    """
    groups: Dict[FieldKey, List[FieldSample]] = {}
    for sample in samples:
        key = sample.field_key
        if key not in groups:
            groups[key] = []
        groups[key].append(sample)

    sorted_keys = sorted(groups.keys(), key=lambda k: (k.layout_id, k.direction.value, k.field_index))
    return OrderedDict((k, groups[k]) for k in sorted_keys)


def sort_samples_by_capture_time(samples: List[FieldSample]) -> List[FieldSample]:
    """按 capture_time 稳定排序 FieldSample 列表。

    有 capture_time 的样本按时间升序排列。
    缺失 capture_time（None）的样本保持输入顺序，排在有时间的样本之后。

    Args:
        samples: FieldSample 列表

    Returns:
        排序后的新列表（不修改原列表）
    """
    with_time = []
    without_time = []
    for sample in samples:
        if sample.capture_time is not None:
            with_time.append(sample)
        else:
            without_time.append(sample)

    sorted_with_time = sorted(with_time, key=lambda s: s.capture_time)
    return sorted_with_time + without_time


def mark_insufficient_groups(
    groups: Dict[FieldKey, List[FieldSample]],
    min_samples: int = 8,
) -> Tuple[Dict[FieldKey, List[FieldSample]], set]:
    """标记样本数不足的字段组，但不丢弃。

    样本数少于 min_samples 的字段组被标记为 insufficient，但仍保留在返回结果中。

    Args:
        groups: aggregate_by_field_key 返回的分组字典
        min_samples: 最小样本数阈值，默认 8

    Returns:
        (groups, insufficient_keys) 元组
        groups: 与输入相同（所有组保留）
        insufficient_keys: 样本数不足的 FieldKey 集合
    """
    insufficient_keys = set()
    for key, samples in groups.items():
        if len(samples) < min_samples:
            insufficient_keys.add(key)
    return groups, insufficient_keys
