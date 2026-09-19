"""预测导出与读回

提供预测结果的 JSONL 导出和读回功能。
"""

import json
import hashlib
import tempfile
import os
from typing import List, Optional
from pathlib import Path
from semantic_detector.contracts import (
    DetectorEvidence,
    MessageRecord,
    Direction,
    SemanticPrediction,
    ALLOWED_DIRECTIONS,
    RejectedRecord,
    get_direction_or_raise,
    REASON_CODE_DUPLICATE_MESSAGE_ID,
    REASON_CODE_INVALID_JSON,
    REASON_CODE_MISSING_REQUIRED_FIELD,
    REASON_CODE_VALUE_ERROR,
    REASON_CODE_TYPE_ERROR,
)


def _serialize_detector_evidence(evidence: DetectorEvidence) -> dict:
    """将 DetectorEvidence 序列化为 JSON-safe 字典

    Args:
        evidence: 证据对象

    Returns:
        JSON-safe 字典
    """
    return {
        "detector": evidence.detector,
        "coarse_label": evidence.coarse_label,
        "fine_label": evidence.fine_label,
        "is_hard_evidence": evidence.is_hard_evidence,
        "score": evidence.score,
        "reason_code": evidence.reason_code,
        "details": evidence.details,
    }


def _serialize_semantic_prediction(prediction: SemanticPrediction) -> dict:
    """将 SemanticPrediction 序列化为完整 JSON-safe 字典

    R243：导出完整身份和证据字段，符合 03 教程 HIGH-3 要求。
    每行 JSONL 含：run_id/layout_id/direction/field_index/coarse_label/
    fine_label/confidence/abstained/prediction_status/evidence/alternatives。

    Args:
        prediction: SemanticPrediction 对象

    Returns:
        JSON-safe 字典（含完整身份和证据）
    """
    # direction 是 Direction(str, Enum)，直接取 .value 得到 "request" 等字符串
    direction_value = prediction.direction.value if isinstance(prediction.direction, Direction) else str(prediction.direction)

    # evidence 元组中每个 DetectorEvidence 序列化为 dict
    evidence_list = [_serialize_detector_evidence(e) for e in prediction.evidence]

    # alternatives 已经是 dict 元组（由 resolver.serialize_evidence 生成）
    alternatives_list = [dict(alt) for alt in prediction.alternatives]

    return {
        "run_id": prediction.run_id,
        "layout_id": prediction.layout_id,
        "direction": direction_value,
        "field_index": prediction.field_index,
        "coarse_label": prediction.coarse_label,
        "fine_label": prediction.fine_label,
        "confidence": prediction.confidence,
        "abstained": prediction.abstained,
        "prediction_status": prediction.prediction_status,
        "evidence": evidence_list,
        "alternatives": alternatives_list,
    }


def export_predictions_to_jsonl(
    predictions: List,
    output_path: Path | str
) -> None:
    """导出预测到 JSONL 文件

    R243：导出完整 SemanticPrediction 全字段（run_id/layout_id/direction/
    field_index/coarse_label/fine_label/confidence/abstained/prediction_status/
    evidence/alternatives）。每行 JSONL 含完整身份和证据。

    向后兼容：如果传入 DetectorEvidence，仍导出旧格式（detector/score/
    is_hard_evidence/reason_code/details）。

    Args:
        predictions: 预测列表（SemanticPrediction 或 DetectorEvidence）
        output_path: 输出文件路径
    """
    output_path = Path(output_path)

    with open(output_path, 'w', encoding='utf-8') as f:
        for prediction in predictions:
            if isinstance(prediction, SemanticPrediction):
                prediction_dict = _serialize_semantic_prediction(prediction)
            else:
                # 向后兼容：DetectorEvidence 旧格式
                prediction_dict = {
                    'detector': prediction.detector,
                    'coarse_label': prediction.coarse_label,
                    'fine_label': prediction.fine_label,
                    'score': prediction.score,
                    'is_hard_evidence': prediction.is_hard_evidence,
                    'reason_code': prediction.reason_code,
                    'details': prediction.details
                }
            f.write(json.dumps(prediction_dict, ensure_ascii=False) + '\n')


def read_predictions_from_jsonl(
    input_path: Path | str
) -> List[DetectorEvidence]:
    """从 JSONL 文件读回预测

    自动检测格式：
    - SemanticPrediction JSONL（含 ``run_id`` 键）：调用
      :func:`read_semantic_predictions_from_jsonl` 读回，并取每条的
      ``evidence[0]`` 作为 primary DetectorEvidence。
    - 旧 DetectorEvidence JSONL（含 ``detector`` 键）：按旧格式直读。

    Args:
        input_path: 输入文件路径

    Returns:
        预测列表（DetectorEvidence）
    """
    input_path = Path(input_path)
    predictions: List[DetectorEvidence] = []

    with open(input_path, 'r', encoding='utf-8') as f:
        first_line = ""
        for line in f:
            if line.strip():
                first_line = line
                break

    # 检测格式：SemanticPrediction 含 run_id 键
    if first_line:
        sample = json.loads(first_line)
        if "run_id" in sample:
            # SemanticPrediction 格式：用严格读回函数，取 primary evidence
            semantic_preds = read_semantic_predictions_from_jsonl(input_path)
            for sp in semantic_preds:
                if sp.evidence:
                    predictions.append(sp.evidence[0])
                else:
                    # 无证据时构造 unknown 占位（保持向后兼容）
                    predictions.append(DetectorEvidence(
                        detector="unknown",
                        coarse_label=sp.coarse_label,
                        fine_label=sp.fine_label,
                        score=sp.confidence,
                        is_hard_evidence=False,
                        reason_code="no_evidence_in_prediction",
                        details=None,
                    ))
            return predictions

    # 旧 DetectorEvidence 格式
    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                prediction_dict = json.loads(line)
                prediction = DetectorEvidence(
                    detector=prediction_dict['detector'],
                    coarse_label=prediction_dict['coarse_label'],
                    fine_label=prediction_dict['fine_label'],
                    score=prediction_dict['score'],
                    is_hard_evidence=prediction_dict['is_hard_evidence'],
                    reason_code=prediction_dict['reason_code'],
                    details=prediction_dict.get('details')
                )
                predictions.append(prediction)

    return predictions


def _deserialize_detector_evidence(d: dict) -> DetectorEvidence:
    """从 dict 重建 DetectorEvidence

    R244：与 _serialize_detector_evidence 互逆，用于 round-trip 读回。

    Args:
        d: JSON-safe 字典

    Returns:
        DetectorEvidence 对象
    """
    return DetectorEvidence(
        detector=d["detector"],
        coarse_label=d["coarse_label"],
        fine_label=d["fine_label"],
        is_hard_evidence=d["is_hard_evidence"],
        score=d["score"],
        reason_code=d["reason_code"],
        details=d.get("details"),
    )


def read_semantic_predictions_from_jsonl(
    input_path: Path | str
) -> List[SemanticPrediction]:
    """从 JSONL 文件严格读回 SemanticPrediction

    R244：与 export_predictions_to_jsonl（SemanticPrediction 路径）互逆。
    round-trip 等价：导入对象与导出对象在身份和证据字段上等价。

    R247：拒绝重复 FieldKey（layout_id + direction + field_index）。
    遇到重复时抛出 ValueError，明确错误，不静默覆盖。

    R397：direction 严格解析。非法 direction（如 "foo"/"bar"）抛出 ValueError，
    不再降级为 Direction.UNKNOWN。合法值仅 request/response/unknown。

    - evidence: list of dict -> tuple of DetectorEvidence
    - alternatives: list of dict -> tuple of dict
    - direction: 字符串值 -> Direction 枚举（严格解析，非法值抛 ValueError）
    - prediction_status: 缺省 "abstained"
    - config_summary: 缺省 None

    Args:
        input_path: 输入文件路径

    Returns:
        SemanticPrediction 列表

    Raises:
        ValueError: 遇到重复 FieldKey（layout_id + direction + field_index）
            或非法 direction 值
    """
    input_path = Path(input_path)
    predictions: List[SemanticPrediction] = []
    seen_fieldkeys: set = set()

    with open(input_path, 'r', encoding='utf-8') as f:
        for line_no, line in enumerate(f, start=1):
            if not line.strip():
                continue
            d = json.loads(line)

            # R397: direction 严格解析——非法值抛 ValueError，不再降级为 UNKNOWN
            # 计划要求：未知但合法的方向必须明确写 "unknown"；非法字符串 rejected
            direction_value = d.get("direction", "unknown")
            direction = get_direction_or_raise(direction_value)

            # R247: 重复 FieldKey 检测
            fieldkey = (d["layout_id"], direction_value, d["field_index"])
            if fieldkey in seen_fieldkeys:
                raise ValueError(
                    f"重复 FieldKey (layout_id={d['layout_id']}, "
                    f"direction={direction_value}, "
                    f"field_index={d['field_index']}) 在第 {line_no} 行；"
                    f"predictions 不得有重复 FieldKey"
                )
            seen_fieldkeys.add(fieldkey)

            # evidence 重建为 DetectorEvidence 元组
            evidence_list = d.get("evidence", [])
            evidence_tuple = tuple(
                _deserialize_detector_evidence(e) for e in evidence_list
            )

            # alternatives 重建为 dict 元组
            alternatives_list = d.get("alternatives", [])
            alternatives_tuple = tuple(dict(alt) for alt in alternatives_list)

            prediction = SemanticPrediction(
                run_id=d["run_id"],
                layout_id=d["layout_id"],
                direction=direction,
                field_index=d["field_index"],
                coarse_label=d["coarse_label"],
                fine_label=d["fine_label"],
                confidence=d["confidence"],
                abstained=d["abstained"],
                evidence=evidence_tuple,
                alternatives=alternatives_tuple,
                config_summary=d.get("config_summary"),
                prediction_status=d.get("prediction_status", "abstained"),
            )
            predictions.append(prediction)

    return predictions


def hash_file_sha256(file_path: str) -> str:
    """计算文件的 SHA-256 哈希值
    
    Args:
        file_path: 文件路径
        
    Returns:
        SHA-256 哈希值（十六进制字符串）
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def atomic_write_file(file_path: str, content: str) -> None:
    """原子写入文件
    
    Args:
        file_path: 文件路径
        content: 文件内容
    """
    dir_path = os.path.dirname(file_path)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)
    
    # 写入临时文件
    with tempfile.NamedTemporaryFile(
        mode='w',
        dir=dir_path if dir_path else None,
        delete=False,
        encoding='utf-8'
    ) as tmp_file:
        tmp_file.write(content)
        tmp_path = tmp_file.name
    
    # 原子重命名
    os.replace(tmp_path, file_path)


def export_validated_records(
    records: List[MessageRecord],
    output_path: str
) -> None:
    """导出验证后的记录到 JSONL 文件
    
    Args:
        records: 记录列表
        output_path: 输出文件路径
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        for record in records:
            # 获取 direction 字符串
            direction_str = str(record.direction)
            if direction_str.startswith('Direction.'):
                direction_str = direction_str.split('.')[-1].lower()
            
            record_dict = {
                'message_id': record.message_id,
                'layout_id': record.layout_id,
                'direction': direction_str,
                'payload_hex': record.payload.hex(),
                'fields': [
                    {
                        'field_index': field.field_index,
                        'start': field.start,
                        'end': field.end
                    }
                    for field in record.fields
                ],
                'input_order': record.input_order
            }
            
            # 添加可选字段
            if record.capture_time is not None:
                record_dict['capture_time'] = record.capture_time.isoformat()
            if record.session_id is not None:
                record_dict['session_id'] = record.session_id
            if record.pair_id is not None:
                record_dict['pair_id'] = record.pair_id
            if record.metadata is not None:
                record_dict['metadata'] = record.metadata
            
            f.write(json.dumps(record_dict, ensure_ascii=False) + '\n')


def export_rejected_records(
    rejected: List[dict],
    output_path: str
) -> None:
    """导出被拒绝的记录到 JSONL 文件

    Args:
        rejected: 被拒绝的记录列表（包含 line_number 和 error/reason）
        output_path: 输出文件路径
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        for item in rejected:
            # 处理 MessageRecord 对象
            export_item = {}
            for key, value in item.items():
                if key == 'record' and isinstance(value, MessageRecord):
                    # 将 MessageRecord 转换为可序列化的 dict
                    direction_str = str(value.direction)
                    if direction_str.startswith('Direction.'):
                        direction_str = direction_str.split('.')[-1].lower()

                    export_item[key] = {
                        'message_id': value.message_id,
                        'layout_id': value.layout_id,
                        'direction': direction_str,
                        'payload_hex': value.payload.hex(),
                        'fields': [
                            {
                                'field_index': field.field_index,
                                'start': field.start,
                                'end': field.end
                            }
                            for field in value.fields
                        ],
                        'input_order': value.input_order
                    }
                else:
                    export_item[key] = value

            # 添加 'code' 字段（如果没有）
            if 'code' not in export_item:
                if 'error' in export_item:
                    export_item['code'] = 'parse_error'
                elif 'reason' in export_item:
                    export_item['code'] = 'validation_error'

            f.write(json.dumps(export_item, ensure_ascii=False) + '\n')


def _classify_rejection_error(error_msg: str) -> tuple:
    """根据 error 消息内容分类拒绝阶段和 reason_code

    R383：read_jsonl_file 返回的拒绝 dict 中 'error' 键混合了 parse 和
    contract 两类错误。本函数根据错误消息前缀/关键词识别阶段和稳定
    reason_code，用于构造 RejectedRecord。

    read_jsonl_file 的 try 块同时捕获两类 ValueError：
    1. json.loads 抛 JSONDecodeError（ValueError 子类），消息形如
       "Expecting ',' delimiter: line 1 column 22 (char 21)"，
       不以 "Invalid JSON:" 开头
    2. parse_json_record 抛 ValueError，消息以 "Invalid JSON:" /
       "Missing required field" / "must be int" 等开头

    Args:
        error_msg: read_jsonl_file 返回的 error 字符串

    Returns:
        (stage, reason_code) 元组：
        - stage: "parse" 或 "contract"
        - reason_code: REASON_CODE_* 常量之一
    """
    # parse_json_record 包装的 JSON 解析错误
    if error_msg.startswith("Invalid JSON:"):
        return ("parse", REASON_CODE_INVALID_JSON)

    # json.loads 直接抛的 JSONDecodeError：含 "Expecting"/"Extra data"/
    # "Unterminated" 等特征关键词（不以 "Invalid JSON:" 开头）
    json_parse_keywords = (
        "Expecting",
        "Extra data",
        "Unterminated string",
        "delimiter",
        "property name",
    )
    if any(kw in error_msg for kw in json_parse_keywords):
        return ("parse", REASON_CODE_INVALID_JSON)

    # 缺少必填字段：contract 阶段
    if error_msg.startswith("Missing required field"):
        return ("contract", REASON_CODE_MISSING_REQUIRED_FIELD)

    # 类型错误：contract 阶段（FieldSpan/MessageRecord 的 must be int/str 等）
    if "must be int" in error_msg or "must be str" in error_msg:
        return ("contract", REASON_CODE_TYPE_ERROR)

    # 其他 ValueError：contract 阶段（start>=end、字段越界、非法 direction 等）
    return ("contract", REASON_CODE_VALUE_ERROR)


def _build_record_summary(record: MessageRecord) -> dict:
    """从 MessageRecord 构造可序列化的 record_summary 摘要

    R383：RejectedRecord 不保存 MessageRecord 对象，用摘要 dict 替代。
    摘要含字段数、payload 长度、input_order，不含 payload 全量内容。

    Args:
        record: MessageRecord 对象

    Returns:
        摘要 dict，所有值为 JSON 基本类型
    """
    return {
        "field_count": len(record.fields),
        "payload_length": len(record.payload),
        "input_order": record.input_order,
    }


def convert_rejection_dict_to_record(rej_dict: dict) -> RejectedRecord:
    """将 read_jsonl_file 返回的拒绝 dict 转换为 RejectedRecord

    R383：统一拒绝结构。read_jsonl_file 返回两种形式的拒绝 dict：
    1. {'line_number': N, 'error': 'msg'} — parse/contract 阶段
    2. {'line_number': N, 'record': MessageRecord, 'reason': 'Duplicate ...'} — duplicate 阶段

    本函数识别形式并构造 RejectedRecord，移除 MessageRecord 对象，
    提取 message_id/layout_id/direction/record_summary 摘要字段。

    Args:
        rej_dict: read_jsonl_file 返回的拒绝 dict

    Returns:
        RejectedRecord 实例（所有字段可 JSON 序列化）
    """
    line_number = rej_dict.get("line_number")

    # 形式 2：duplicate 阶段（含 'record' MessageRecord 和 'reason'）
    if "record" in rej_dict and isinstance(rej_dict["record"], MessageRecord):
        mr = rej_dict["record"]
        reason_str = rej_dict.get("reason", "")
        # duplicate 阶段的 reason 格式: "Duplicate message_id: X"
        return RejectedRecord(
            line_number=line_number,
            stage="duplicate",
            reason_code=REASON_CODE_DUPLICATE_MESSAGE_ID,
            message=reason_str,
            message_id=mr.message_id,
            layout_id=mr.layout_id,
            direction=mr.direction.value if isinstance(mr.direction, Direction) else str(mr.direction),
            record_summary=_build_record_summary(mr),
            raw_line=None,
        )

    # 形式 1：parse/contract 阶段（含 'error'）
    error_msg = rej_dict.get("error", "")
    stage, reason_code = _classify_rejection_error(error_msg)
    return RejectedRecord(
        line_number=line_number,
        stage=stage,
        reason_code=reason_code,
        message=error_msg,
        message_id=None,
        layout_id=None,
        direction=None,
        record_summary=None,
        raw_line=None,
    )


def export_rejected_records_unified(
    rejected: List[dict],
    output_path: str,
) -> List[RejectedRecord]:
    """统一导出拒绝记录到 JSONL 文件（R383 HIGH-2 修复）

    将 read_jsonl_file 返回的拒绝 dict 列表转换为 RejectedRecord，
    使用 RejectedRecord.to_dict() 写入 JSONL。所有字段可 JSON 序列化，
    不直接 json.dumps(MessageRecord)。

    无 rejection 时写空文件，避免旧文件残留。

    Args:
        rejected: read_jsonl_file 返回的拒绝 dict 列表
        output_path: 输出文件路径

    Returns:
        转换后的 RejectedRecord 列表（供调用方计数/上报）
    """
    records = [convert_rejection_dict_to_record(r) for r in rejected]
    with open(output_path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec.to_dict(), ensure_ascii=False) + "\n")
    return records


def export_field_profiles(
    profiles: List,
    output_path: str
) -> None:
    """导出字段画像到 JSONL 文件

    R274：改用 profile.to_dict() 替代 dataclasses.asdict()。
    原因：FieldProfile.capture_time_min/max 可能是 datetime 对象，
    asdict 不会转 ISO 字符串，json.dumps 会抛
    "TypeError: Object of type datetime is not JSON serializable"。
    to_dict() 已在 R270 处理 datetime → ISO 字符串，可安全 JSON 化。
    同时 to_dict() 输出 R264-R273 全部新增字段（dominant_value_hex/count、
    BE/LE exact_support/offset_support/offset、distinct_value_count、
    capture_time 4 个、8 个 timestamp support），确保 round-trip 不丢证据。

    Args:
        profiles: 字段画像列表
        output_path: 输出文件路径
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        for profile in profiles:
            profile_dict = profile.to_dict()
            f.write(json.dumps(profile_dict, ensure_ascii=False) + '\n')


def import_field_profiles(
    input_path: str
) -> List:
    """从 JSONL 文件导入字段画像

    R274：与 export_field_profiles（使用 to_dict）互逆。
    - datetime 字段（capture_time_min/max）从 ISO 字符串解析回 datetime
      （to_dict 输出 ISO 字符串，导入需还原为 datetime 才能等价）
    - 其他字段直接 FieldProfile(**profile_dict)
    - round-trip 等价：导入对象与导出对象在所有字段上等价
    - None 值保持 None（capture_time 缺失场景）

    Args:
        input_path: 输入文件路径

    Returns:
        字段画像列表
    """
    from semantic_detector.profiling.profile_builder import FieldProfile
    from datetime import datetime

    profiles = []
    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                profile_dict = json.loads(line)
                # R274: capture_time_min/max 从 ISO 字符串解析回 datetime
                # to_dict 输出 .isoformat()（如 '2026-06-27T10:00:00+00:00'）
                # Python 3.11+ fromisoformat 支持 'Z' 后缀，但为兼容性统一替换
                for key in ('capture_time_min', 'capture_time_max'):
                    val = profile_dict.get(key)
                    if isinstance(val, str):
                        iso_val = val.replace('Z', '+00:00') if val.endswith('Z') else val
                        profile_dict[key] = datetime.fromisoformat(iso_val)
                profile = FieldProfile(**profile_dict)
                profiles.append(profile)

    return profiles


def export_metrics_to_json(
    metrics: dict,
    output_path: str
) -> None:
    """导出评估指标到 JSON 文件
    
    Args:
        metrics: 指标字典
        output_path: 输出文件路径
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)


def read_metrics_from_json(
    input_path: str
) -> dict:
    """从 JSON 文件读取评估指标
    
    Args:
        input_path: 输入文件路径
        
    Returns:
        指标字典
    """
    with open(input_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def build_metrics_dict(
    overall_accuracy: float,
    coverage: float,
    unknown_rate: float,
    covered_accuracy: float,
    fine_top1_accuracy: float = None,
    macro_f1: float = None,
    macro_precision: float = None,
    macro_recall: float = None,
    counts: Optional[dict] = None
) -> dict:
    """构建指标字典

    R260：新增 counts 字段，使 metrics.json 包含计数，
    导出再解析后可验证指标与计数一致（如 accuracy 与 correct/total 对应）。

    Args:
        overall_accuracy: 总体准确率
        coverage: 覆盖率
        unknown_rate: unknown 比率
        covered_accuracy: 覆盖准确率
        fine_top1_accuracy: fine top-1 准确率（可选）
        macro_f1: macro F1（可选）
        macro_precision: macro precision（可选）
        macro_recall: macro recall（可选）
        counts: 计数字典（R260 新增，可选），可包含：
            total_predictions, total_truths, matched_count,
            unmatched_truths_count, unmatched_predictions_count, error_count

    Returns:
        指标字典
    """
    metrics = {
        'overall_accuracy': overall_accuracy,
        'coverage': coverage,
        'unknown_rate': unknown_rate,
        'covered_accuracy': covered_accuracy
    }

    if fine_top1_accuracy is not None:
        metrics['fine_top1_accuracy'] = fine_top1_accuracy

    if macro_f1 is not None:
        metrics['macro_f1'] = macro_f1

    if macro_precision is not None:
        metrics['macro_precision'] = macro_precision

    if macro_recall is not None:
        metrics['macro_recall'] = macro_recall

    if counts is not None:
        metrics['counts'] = counts

    return metrics


def export_per_label_metrics_to_csv(
    label_metrics: dict,
    output_path: str,
    label_stats: Optional[dict] = None
) -> None:
    """导出每标签指标到 CSV 文件

    R260：新增 label_stats 参数，传入时追加 tp/fp/fn 计数列，
    使 CSV 导出再解析后可验证 precision/recall/f1 与计数一致。

    Args:
        label_metrics: 标签指标字典（label -> LabelMetrics）
        output_path: 输出文件路径
        label_stats: 标签统计字典（label -> LabelStats，R260 新增，可选）。
            传入时表头追加 tp/fp/fn 列；不传时向后兼容（只导出 4 列）。
    """
    import csv

    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)

        if label_stats is not None:
            # R260: 含 tp/fp/fn 计数列
            writer.writerow(['label', 'precision', 'recall', 'f1', 'tp', 'fp', 'fn'])
            for label, metrics in label_metrics.items():
                stats = label_stats.get(label)
                tp = stats.tp if stats is not None else 0
                fp = stats.fp if stats is not None else 0
                fn = stats.fn if stats is not None else 0
                writer.writerow([
                    label,
                    metrics.precision,
                    metrics.recall,
                    metrics.f1,
                    tp,
                    fp,
                    fn
                ])
        else:
            # 向后兼容：只导出 4 列
            writer.writerow(['label', 'precision', 'recall', 'f1'])
            for label, metrics in label_metrics.items():
                writer.writerow([
                    label,
                    metrics.precision,
                    metrics.recall,
                    metrics.f1
                ])


def export_confusion_matrix_to_csv(
    confusion_matrix,
    output_path: str
) -> None:
    """导出混淆矩阵到 CSV 文件
    
    Args:
        confusion_matrix: ConfusionMatrix 对象
        output_path: 输出文件路径
    """
    import csv
    
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        
        # 写表头（第一行：空 + 标签列表）
        writer.writerow([''] + confusion_matrix.labels)
        
        # 写数据（每行：标签 + 该行数据）
        for i, label in enumerate(confusion_matrix.labels):
            row = [label] + confusion_matrix.matrix[i]
            writer.writerow(row)


def read_per_label_metrics_from_csv(
    input_path: str
) -> list:
    """从 CSV 文件读取每标签指标

    R260：若 CSV 含 tp/fp/fn 列则一并读取，使导出再解析后计数可验证。

    Args:
        input_path: 输入文件路径

    Returns:
        指标列表 [{'label': ..., 'precision': ..., 'recall': ..., 'f1': ...,
                  'tp': ..., 'fp': ..., 'fn': ...}, ...]
        tp/fp/fn 仅在 CSV 含这些列时出现。
    """
    import csv

    metrics = []

    with open(input_path, 'r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)

        for row in reader:
            entry = {
                'label': row['label'],
                'precision': float(row['precision']),
                'recall': float(row['recall']),
                'f1': float(row['f1'])
            }
            # R260: 读取 tp/fp/fn 计数列（若存在）
            if 'tp' in row and row['tp'] != '':
                entry['tp'] = int(row['tp'])
            if 'fp' in row and row['fp'] != '':
                entry['fp'] = int(row['fp'])
            if 'fn' in row and row['fn'] != '':
                entry['fn'] = int(row['fn'])
            metrics.append(entry)

    return metrics


def read_confusion_matrix_from_csv(
    input_path: str
) -> tuple:
    """从 CSV 文件读取混淆矩阵

    Args:
        input_path: 输入文件路径

    Returns:
        (labels, matrix) 元组
    """
    import csv

    labels = []
    matrix = []

    with open(input_path, 'r', encoding='utf-8', newline='') as f:
        reader = csv.reader(f)

        # 读取表头
        header = next(reader)
        labels = header[1:]  # 跳过第一个空列

        # 读取数据
        for row in reader:
            matrix.append([int(x) for x in row[1:]])

    return labels, matrix


def build_failed_run_manifest(
    run_id: str,
    status: str,
    exit_code: int,
    started_at: str,
    finished_at: str,
    input_path: str,
    input_sha256: str,
    resolved_config: dict,
    valid_records: int,
    rejected_records: int,
    error_stage: str,
    error_message: str,
    error_type: str = "",
    config_source: str = "default",
    config_sha256: str = "",
    input_line_count: int = 0,
    partial_artifacts_present: bool = False,
) -> dict:
    """R390/R421：构建失败 Run 的 Manifest

    失败运行不能没有 Manifest，也不能留下旧成功 Manifest。
    本函数构建失败 Manifest，包含 R390 的 14 个基础字段 + R421 扩展字段。

    R390 基础字段（14 个，向后兼容）：
    - run_id：本次失败运行的新 run_id（禁止复用旧 run_id）
    - status：失败状态（failed 或 invalid_input）
    - exit_code：退出码（失败恒为 1）
    - started_at：命令开始时间（ISO 8601）
    - finished_at：命令结束时间（ISO 8601）
    - input_path：输入文件路径
    - input_sha256：输入文件 SHA-256（无法读取时为空串）
    - resolved_config：解析后的配置字典
    - valid_records：进入失败阶段时的有效记录数
    - rejected_records：进入失败阶段时的拒绝记录数
    - field_profiles：恒为 0（失败时不产生画像）
    - predictions：恒为 0（失败时不产生预测）
    - error_stage：失败阶段名（read_jsonl / build_field_profiles 等）
    - error_message：错误消息字符串

    R421 扩展字段：
    - valid_for_reporting：恒为 False（失败运行不可用于报表）
    - failure_stage：与 error_stage 同值（计划要求字段名，向后兼容用 error_stage）
    - error_type：异常类型名（如 "RuntimeError"）
    - config_source：配置来源（"default" 或用户配置路径）
    - config_sha256：配置文件 SHA-256（默认配置或无配置时为空串）
    - partial_artifacts_present：是否保留了诊断用半成品（如 profiles 已成功后 detect 失败）
    - counts：嵌套计数对象（input_line_count/validated_records/rejected_records/
      field_profiles/predictions），同时保留平铺字段以向后兼容

    Args:
        run_id: 新生成的 run_id（UUID 字符串）
        status: 失败状态（"failed" 或 "invalid_input"）
        exit_code: 退出码（失败恒为 1）
        started_at: 命令开始时间 ISO 8601 字符串
        finished_at: 命令结束时间 ISO 8601 字符串
        input_path: 输入文件路径
        input_sha256: 输入文件 SHA-256 十六进制摘要
        resolved_config: 解析后的配置字典（Config.to_dict()）
        valid_records: 进入失败阶段时的有效记录数
        rejected_records: 进入失败阶段时的拒绝记录数
        error_stage: 失败阶段名
        error_message: 错误消息字符串
        error_type: 异常类型名（如 "RuntimeError"），R421 扩展
        config_source: 配置来源（"default" 或用户配置路径），R421 扩展
        config_sha256: 配置文件 SHA-256，R421 扩展
        input_line_count: 输入文件总行数，R421 扩展
        partial_artifacts_present: 是否保留诊断用半成品，R421 扩展

    Returns:
        失败 Manifest 字典（14 基础 + 7 扩展 = 21 字段）
    """
    return {
        # R390 基础字段（向后兼容）
        "run_id": run_id,
        "status": status,
        "exit_code": exit_code,
        "started_at": started_at,
        "finished_at": finished_at,
        "input_path": input_path,
        "input_sha256": input_sha256,
        "resolved_config": resolved_config,
        "valid_records": valid_records,
        "rejected_records": rejected_records,
        "field_profiles": 0,
        "predictions": 0,
        "error_stage": error_stage,
        "error_message": error_message,
        # R421 扩展字段
        "valid_for_reporting": False,
        "failure_stage": error_stage,
        "error_type": error_type,
        "config_source": config_source,
        "config_sha256": config_sha256,
        "partial_artifacts_present": partial_artifacts_present,
        "counts": {
            "input_line_count": input_line_count,
            "validated_records": valid_records,
            "rejected_records": rejected_records,
            "field_profiles": 0,
            "predictions": 0,
        },
    }
