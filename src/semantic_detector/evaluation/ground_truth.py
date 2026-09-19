"""Ground truth JSONL 解析与验证"""

import json
from dataclasses import dataclass
from typing import List, Tuple, Optional
from pathlib import Path

from semantic_detector.taxonomy import (
    CANONICAL_COARSE_LABELS,
    normalize_legacy_label,
    is_canonical_coarse_label,
)
from semantic_detector.contracts import (
    FieldKey,
    Direction,
    ALLOWED_DIRECTIONS,
    get_direction_or_raise,
)


@dataclass
class GroundTruthRecord:
    """Ground truth 记录

    R249：新增 layout_id 和 direction 字段，truth 可生成完整 FieldKey。
    semantic_type 改名为 semantic_label（@property semantic_type 向后兼容）。

    完整 FieldKey = (layout_id, direction, field_index)
    """
    truth_id: int
    field_index: int
    semantic_label: str
    confidence: float
    is_hard_evidence: bool
    fine_label: Optional[str] = None
    details: Optional[dict] = None
    # R249: 新增身份字段（有默认值，保持向后兼容）
    # 教程 1.3：direction 缺失时降级为 "unknown"（不兜底 "request"）
    layout_id: str = "default"
    direction: str = "unknown"

    def __post_init__(self):
        """验证字段范围"""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be between 0.0 and 1.0, got {self.confidence}")

        if self.truth_id < 1:
            raise ValueError(f"truth_id must be >= 1, got {self.truth_id}")

        if self.field_index < 0:
            raise ValueError(f"field_index must be >= 0, got {self.field_index}")

        if not self.layout_id:
            raise ValueError("layout_id must not be empty")

        if not self.direction:
            raise ValueError("direction must not be empty")

    @property
    def semantic_type(self) -> str:
        """向后兼容：semantic_type 别名指向 semantic_label

        旧代码（metrics.py/confusion.py）仍可访问 record.semantic_type。
        """
        return self.semantic_label

    @property
    def field_key(self):
        """完整 FieldKey = FieldKey(layout_id, direction, field_index)

        R249：truth 可生成完整 FieldKey，与 SemanticPrediction 对齐。
        R252：返回 FieldKey 对象，direction 转 Direction 枚举。
        R397：严格解析——非法 direction 抛 ValueError，不再降级 UNKNOWN。
        read_ground_truth_jsonl 已在读取阶段拒绝非法 direction，正常不会到达这里。
        """
        direction = get_direction_or_raise(self.direction)
        return FieldKey(
            layout_id=self.layout_id,
            direction=direction,
            field_index=self.field_index,
        )


def read_ground_truth_jsonl(file_path: str) -> Tuple[List[GroundTruthRecord], List[dict]]:
    """读取 ground truth JSONL 文件

    R249：支持新字段 layout_id/direction/semantic_label。
    兼容旧键名 semantic_type（如果 semantic_label 不存在，读 semantic_type）。
    如果 layout_id/direction 缺失，使用默认值 "default"/"request"（过渡兼容）。

    R335：统一拒绝记录结构，至少包含 line_number/stage/reason_code/message/raw_line。
    JSON 解析错误和语义校验错误使用统一可导出的拒绝记录。

    Args:
        file_path: JSONL 文件路径

    Returns:
        (valid_records, rejected_records) 元组

        rejected_records 每项结构（R335 统一）：
        - line_number: 行号（从 1 开始）
        - stage: "read"（读取阶段）
        - reason_code: 拒绝原因代码（invalid_json/missing_required_field/
          invalid_direction/invalid_label/negative_field_index/...）
        - message: 人类可读的错误消息
        - raw_line: 原始行内容
    """
    valid_records: List[GroundTruthRecord] = []
    rejected_records: List[dict] = []

    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            raw_line = line.rstrip('\n').rstrip('\r')
            stripped = raw_line.strip()
            if not stripped:
                continue

            try:
                data = json.loads(stripped)

                # 检查必要字段
                required_fields = ['truth_id', 'field_index', 'confidence', 'is_hard_evidence']
                for field in required_fields:
                    if field not in data:
                        raise ValueError(f"missing_required_field: {field}")

                # R249: semantic_label 优先，兼容旧键名 semantic_type
                semantic_label = data.get('semantic_label')
                if semantic_label is None:
                    semantic_label = data.get('semantic_type')
                if semantic_label is None:
                    raise ValueError("missing_required_field: semantic_label (or semantic_type)")

                # R250: 旧标签兼容读取，normalize 为 9 个标准标签之一
                # 新写出只使用标准标签，旧 fixture 可能含 identifier_candidate/
                # type_opcode/sequence 等旧标签
                semantic_label = normalize_legacy_label(semantic_label)

                # R249: layout_id/direction 缺失时用默认值（过渡兼容旧 fixture）
                # 教程 1.3：direction 缺失时降级为 "unknown"（不兜底 "request"）
                layout_id = data.get('layout_id', 'default')
                direction = data.get('direction', 'unknown')

                # R397: direction 严格校验——非法值进入 rejection，不构造 GroundTruthRecord
                # 计划要求：合法值仅 request/response/unknown；非法字符串 rejected
                # 不自动转小写，不降级为 unknown
                if direction not in ALLOWED_DIRECTIONS:
                    raise ValueError(
                        f"invalid_direction: {direction!r} 不是合法 direction；"
                        f"合法值仅 {sorted(ALLOWED_DIRECTIONS)}"
                    )

                # 创建记录
                record = GroundTruthRecord(
                    truth_id=data['truth_id'],
                    field_index=data['field_index'],
                    semantic_label=semantic_label,
                    confidence=data['confidence'],
                    is_hard_evidence=data['is_hard_evidence'],
                    fine_label=data.get('fine_label'),
                    details=data.get('details'),
                    layout_id=layout_id,
                    direction=direction,
                )

                valid_records.append(record)

            except json.JSONDecodeError as e:
                # R335: 统一拒绝记录结构
                rejected_records.append({
                    'line_number': line_num,
                    'stage': 'read',
                    'reason_code': 'invalid_json',
                    'message': f"JSON 解析失败: {e}",
                    'raw_line': raw_line,
                })
            except ValueError as e:
                # R335: 从异常消息中提取 reason_code（格式 "reason_code: detail"）
                msg = str(e)
                if ':' in msg:
                    reason_code, detail = msg.split(':', 1)
                    reason_code = reason_code.strip()
                    message = detail.strip()
                else:
                    reason_code = 'value_error'
                    message = msg
                rejected_records.append({
                    'line_number': line_num,
                    'stage': 'read',
                    'reason_code': reason_code,
                    'message': message,
                    'raw_line': raw_line,
                })
            except TypeError as e:
                rejected_records.append({
                    'line_number': line_num,
                    'stage': 'read',
                    'reason_code': 'type_error',
                    'message': str(e),
                    'raw_line': raw_line,
                })

    return valid_records, rejected_records


def validate_ground_truth(records: List[GroundTruthRecord]) -> Tuple[List[GroundTruthRecord], List[dict]]:
    """验证 ground truth 记录

    R250：使用 taxonomy.CANONICAL_COARSE_LABELS（9 类标准标签）验证。
    R251：增加重复完整 FieldKey 拒绝（不用 truth_id 代替 FieldKey 唯一性）。
    R335：统一拒绝记录结构，至少包含 stage/reason_code/message/record_summary。

    检查：
    1. truth_id 唯一性
    2. FieldKey (layout_id, direction, field_index) 唯一性
    3. semantic_label 必须是 9 个标准标签之一

    新写出只使用标准标签。旧标签应在 read_ground_truth_jsonl 阶段
    通过 normalize_legacy_label 自动转换。

    Args:
        records: Ground truth 记录列表

    Returns:
        (valid_records, rejected_records) 元组

        rejected_records 每项结构（R335 统一）：
        - stage: "validate"（验证阶段）
        - reason_code: 拒绝原因代码（duplicate_truth_id/duplicate_field_key/
          invalid_label/...）
        - message: 人类可读的错误消息
        - record_summary: 记录摘要（truth_id/layout_id/direction/field_index）
        - errors: 错误列表（向后兼容，可能有多个错误）
    """
    valid_records: List[GroundTruthRecord] = []
    rejected_records: List[dict] = []

    seen_ids = set()
    seen_fieldkeys: set = set()

    for record in records:
        errors = []
        reason_codes = []

        # 检查 truth_id 唯一性
        if record.truth_id in seen_ids:
            errors.append(f"Duplicate truth_id: {record.truth_id}")
            reason_codes.append('duplicate_truth_id')
        else:
            seen_ids.add(record.truth_id)

        # R251: 检查完整 FieldKey 唯一性
        # 不用 truth_id 代替 FieldKey 唯一性
        fieldkey = record.field_key
        if fieldkey in seen_fieldkeys:
            errors.append(
                f"Duplicate FieldKey: (layout_id={record.layout_id}, "
                f"direction={record.direction}, "
                f"field_index={record.field_index})"
            )
            reason_codes.append('duplicate_field_key')
        else:
            seen_fieldkeys.add(fieldkey)

        # R250: 检查 semantic_label 是否为 9 个标准标签之一
        if not is_canonical_coarse_label(record.semantic_label):
            errors.append(
                f"Invalid semantic_label: {record.semantic_label}; "
                f"must be one of {CANONICAL_COARSE_LABELS}"
            )
            reason_codes.append('invalid_label')

        if errors:
            # R335: 统一拒绝记录结构
            rejected_records.append({
                'stage': 'validate',
                'reason_code': reason_codes[0] if reason_codes else 'validation_error',
                'message': '; '.join(errors),
                'record_summary': {
                    'truth_id': record.truth_id,
                    'layout_id': record.layout_id,
                    'direction': record.direction,
                    'field_index': record.field_index,
                },
                'errors': errors,
            })
        else:
            valid_records.append(record)

    return valid_records, rejected_records
