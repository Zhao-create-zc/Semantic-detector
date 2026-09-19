"""Evaluation metrics for semantic detector"""

import json
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
from semantic_detector.contracts import (
    FieldKey,
    DetectorEvidence,
    SemanticPrediction,
    Direction,
    get_direction_or_raise,
)
from semantic_detector.evaluation.ground_truth import GroundTruthRecord
from semantic_detector.taxonomy import normalize_legacy_label


@dataclass
class AlignedPair:
    """对齐的预测和真值对"""
    field_key: FieldKey
    prediction: Optional[DetectorEvidence]
    truth: Optional[GroundTruthRecord]
    is_matched: bool


def _extract_field_key_from_prediction(pred) -> Optional[FieldKey]:
    """从预测对象提取完整 FieldKey

    R252：支持 SemanticPrediction（含完整身份字段）和旧 DetectorEvidence
    （从 details 取 field_index，layout_id/direction 缺失时返回 None）。

    R399：严格规范化——旧 DetectorEvidence 的 direction 也用 get_direction_or_raise
    严格解析，非法值抛 ValueError（不再降级 UNKNOWN）。direction 缺失时（None 或空）
    默认 "unknown"（合法值），不兜底 "request"。这确保 _extract_field_key_from_prediction
    与 R397 修复后的 Prediction/Ground Truth 使用同一严格解析函数，规范化后的 FieldKey
    可安全用于 align_predictions_with_truth 的唯一性检查。

    Args:
        pred: SemanticPrediction 或 DetectorEvidence

    Returns:
        FieldKey 或 None（无法提取身份时）

    Raises:
        ValueError: 当旧 DetectorEvidence 的 direction 非法时（R399 严格规范化）
    """
    if isinstance(pred, SemanticPrediction):
        # SemanticPrediction 含完整身份字段，direction 已是 Direction 枚举
        return FieldKey(
            layout_id=pred.layout_id,
            direction=pred.direction,
            field_index=pred.field_index,
        )
    # 旧 DetectorEvidence：从 details 取 field_index
    if pred.details and 'field_index' in pred.details:
        # R399: 严格规范化——direction 用 get_direction_or_raise 解析
        # direction 缺失时（None 或空字符串）默认 "unknown"（合法值），不兜底 "request"
        direction_value = pred.details.get('direction') or 'unknown'
        direction = get_direction_or_raise(direction_value)
        return FieldKey(
            layout_id=pred.details.get('layout_id', 'default'),
            direction=direction,
            field_index=pred.details['field_index'],
        )
    return None


def _extract_evidence_fields_from_prediction(pred) -> dict:
    """从预测对象提取证据字段（detector/reason_code/score/fine_label）

    R261：兼容 SemanticPrediction（confidence + evidence 元组）和
    旧 DetectorEvidence（score + 直接字段）。使 collect_errors 可处理
    真实 SemanticPrediction importer 读回的对象。

    Args:
        pred: SemanticPrediction 或 DetectorEvidence

    Returns:
        含 detector/reason_code/score/fine_label 的字典
    """
    if isinstance(pred, SemanticPrediction):
        score = pred.confidence
        if pred.evidence:
            ev = pred.evidence[0]
            detector = ev.detector
            reason_code = ev.reason_code
        else:
            detector = 'unknown'
            reason_code = ''
        return {
            'detector': detector,
            'reason_code': reason_code,
            'score': score,
            'fine_label': pred.fine_label,
        }
    # 旧 DetectorEvidence
    return {
        'detector': pred.detector,
        'reason_code': pred.reason_code,
        'score': pred.score,
        'fine_label': pred.fine_label,
    }


def align_predictions_with_truth(
    predictions: List,
    truths: List[GroundTruthRecord],
    layout_id: Optional[str] = None,
    direction: Optional[str] = None
) -> Tuple[List[AlignedPair], List, List[GroundTruthRecord]]:
    """对齐预测和真值

    R252：按完整 FieldKey (layout_id, direction, field_index) 对齐。
    - 支持多 layout、多方向、顺序打乱
    - 匹配准确，不依赖外部传入 layout_id/direction
    - 兼容旧 DetectorEvidence（从 details 取身份，缺失时用 default/unknown）

    R399：先规范化，再检查重复。
    - Prediction/Truth 在生成 FieldKey 后立即检查 duplicate，不静默覆盖
    - duplicate FieldKey 抛 ValueError，消息包含 "duplicate" 标识
    - 规范化由 _extract_field_key_from_prediction（Prediction 侧）和
      GroundTruthRecord.field_key（Truth 侧，R397 严格解析）完成
    - 正确顺序：读取原始记录 → 严格字段校验 → 规范化合法字段 → 生成 FieldKey
      → 检查重复 → 构建字典

    Args:
        predictions: 预测列表（SemanticPrediction 或 DetectorEvidence）
        truths: 真值列表
        layout_id: 可选，旧调用方兼容（未使用，R252 改为从预测对象提取）
        direction: 可选，旧调用方兼容（未使用）

    Returns:
        (aligned_pairs, unmatched_predictions, unmatched_truths) 元组

    Raises:
        ValueError: 当 Prediction 或 Truth 出现 duplicate FieldKey 时（R399）
    """
    aligned_pairs: List[AlignedPair] = []
    unmatched_predictions: List = []
    unmatched_truths: List[GroundTruthRecord] = []

    # R252: 用完整 FieldKey 做映射
    # R399: 先规范化，再检查重复——duplicate FieldKey 抛 ValueError
    # 计划要求：读取原始记录 → 严格字段校验 → 规范化合法字段 → 生成 FieldKey
    #           → 检查重复 → 构建字典
    # 禁止：先用原始字符串判断不重复 → 后归一化成同一键 → 静默覆盖
    pred_by_key: Dict[FieldKey, object] = {}
    for pred in predictions:
        key = _extract_field_key_from_prediction(pred)
        if key is None:
            unmatched_predictions.append(pred)
            continue
        if key in pred_by_key:
            raise ValueError(
                f"duplicate FieldKey in predictions: "
                f"layout_id={key.layout_id!r}, direction={key.direction.value!r}, "
                f"field_index={key.field_index!r}"
            )
        pred_by_key[key] = pred

    # GroundTruthRecord.field_key 属性（R249）
    # R399: 同样检查 duplicate FieldKey，truth.field_key 已规范化（R397 严格解析）
    truth_by_key: Dict[FieldKey, GroundTruthRecord] = {}
    for truth in truths:
        key = truth.field_key
        if key in truth_by_key:
            raise ValueError(
                f"duplicate FieldKey in ground truth: "
                f"layout_id={key.layout_id!r}, direction={key.direction.value!r}, "
                f"field_index={key.field_index!r}"
            )
        truth_by_key[key] = truth

    # 收集所有 FieldKey（按 (layout_id, direction, field_index) 排序保证稳定顺序）
    all_keys = set(pred_by_key.keys()) | set(truth_by_key.keys())
    sorted_keys = sorted(all_keys, key=lambda k: (k.layout_id, k.direction, k.field_index))

    # 对齐
    for key in sorted_keys:
        pred = pred_by_key.get(key)
        truth = truth_by_key.get(key)

        if pred is not None and truth is not None:
            # 匹配
            aligned_pairs.append(AlignedPair(
                field_key=key,
                prediction=pred,
                truth=truth,
                is_matched=True
            ))
        elif pred is not None:
            # 只有预测，没有真值
            unmatched_predictions.append(pred)
        elif truth is not None:
            # 只有真值，没有预测
            unmatched_truths.append(truth)

    return aligned_pairs, unmatched_predictions, unmatched_truths


@dataclass
class CountConservationResult:
    """评价数量守恒检查结果（R400）

    R400：防止 total_predictions=2, matched=1, unmatched_predictions=0 这种不守恒结果。

    在没有 rejected duplicate 的正式评价中必须满足：
    - matched_predictions + unmatched_predictions = total_predictions
    - matched_truths + missing_predictions = total_truths

    其中 missing_predictions = unmatched_truths（有 truth 没 pred，相当于 missing prediction）。

    若不满足：valid_for_reporting=false, status=internal_count_inconsistency。
    R399 修复后 duplicate FieldKey 会抛 ValueError，正常路径下不会出现不守恒。
    本结果作为额外防御，确保即使有内部 bug 也能检测到不守恒并标记不可上报。

    Attributes:
        valid_for_reporting: 是否可上报（守恒时 True）
        status: 状态码（count_conserved / internal_count_inconsistency）
        total_predictions: 输入的总预测数
        total_truths: 输入的总真值数
        matched_predictions: 匹配且有 prediction 的对数
        unmatched_predictions: 未匹配的预测数（含 key is None 的 prediction）
        matched_truths: 匹配且有 truth 的对数
        missing_predictions: 未匹配的真值数（= unmatched_truths，有 truth 没 pred）
        message: 不守恒时的详细消息
    """
    valid_for_reporting: bool
    status: str
    total_predictions: int
    total_truths: int
    matched_predictions: int
    unmatched_predictions: int
    matched_truths: int
    missing_predictions: int
    message: str = ""


def verify_count_conservation(
    aligned_pairs: List[AlignedPair],
    unmatched_predictions: List,
    unmatched_truths: List[GroundTruthRecord],
    total_predictions: int,
    total_truths: int,
) -> CountConservationResult:
    """验证评价数量守恒（R400）

    在没有 rejected duplicate 的正式评价中必须满足：
    - matched_predictions + unmatched_predictions = total_predictions
    - matched_truths + missing_predictions = total_truths

    其中 missing_predictions = unmatched_truths（有 truth 没 pred）。

    R399 修复后 duplicate FieldKey 会抛 ValueError，正常路径下不会出现不守恒。
    本函数作为额外防御，确保即使有内部 bug 也能检测到不守恒并标记
    valid_for_reporting=false。

    Args:
        aligned_pairs: 对齐的对列表
        unmatched_predictions: 未匹配的预测列表
        unmatched_truths: 未匹配的真值列表（= missing_predictions）
        total_predictions: 输入的总预测数
        total_truths: 输入的总真值数

    Returns:
        CountConservationResult：valid_for_reporting + status + 详细计数
    """
    matched_predictions = sum(
        1 for p in aligned_pairs if p.is_matched and p.prediction is not None
    )
    matched_truths = sum(
        1 for p in aligned_pairs if p.is_matched and p.truth is not None
    )
    actual_unmatched_predictions = len(unmatched_predictions)
    actual_missing_predictions = len(unmatched_truths)

    pred_conserved = (
        matched_predictions + actual_unmatched_predictions == total_predictions
    )
    truth_conserved = (
        matched_truths + actual_missing_predictions == total_truths
    )

    if pred_conserved and truth_conserved:
        return CountConservationResult(
            valid_for_reporting=True,
            status="count_conserved",
            total_predictions=total_predictions,
            total_truths=total_truths,
            matched_predictions=matched_predictions,
            unmatched_predictions=actual_unmatched_predictions,
            matched_truths=matched_truths,
            missing_predictions=actual_missing_predictions,
        )

    return CountConservationResult(
        valid_for_reporting=False,
        status="internal_count_inconsistency",
        total_predictions=total_predictions,
        total_truths=total_truths,
        matched_predictions=matched_predictions,
        unmatched_predictions=actual_unmatched_predictions,
        matched_truths=matched_truths,
        missing_predictions=actual_missing_predictions,
        message=(
            f"count inconsistency: "
            f"predictions {matched_predictions}+{actual_unmatched_predictions}="
            f"{matched_predictions + actual_unmatched_predictions} != total {total_predictions}; "
            f"truths {matched_truths}+{actual_missing_predictions}="
            f"{matched_truths + actual_missing_predictions} != total {total_truths}"
        ),
    )


def count_matched_pairs(aligned_pairs: List[AlignedPair]) -> int:
    """统计匹配的对数
    
    Args:
        aligned_pairs: 对齐的对列表
        
    Returns:
        匹配的对数
    """
    return sum(1 for pair in aligned_pairs if pair.is_matched)


def count_unmatched_predictions(unmatched_predictions: List[DetectorEvidence]) -> int:
    """统计未匹配的预测数
    
    Args:
        unmatched_predictions: 未匹配的预测列表
        
    Returns:
        未匹配的预测数
    """
    return len(unmatched_predictions)


def count_unmatched_truths(unmatched_truths: List[GroundTruthRecord]) -> int:
    """统计未匹配的真值数
    
    Args:
        unmatched_truths: 未匹配的真值列表
        
    Returns:
        未匹配的真值数
    """
    return len(unmatched_truths)


def calculate_overall_accuracy(
    aligned_pairs: List[AlignedPair],
    unmatched_truths: Optional[List[GroundTruthRecord]] = None
) -> float:
    """计算 overall accuracy

    R253：分母为全部 truth 数量（含 unmatched_truths），abstained 不从分母中消失。

    Overall Accuracy = 标准化预测正确的 truth 数量 / 全部 truth 数量

    以下均算错误（不计入分子，但计入分母）：
    - 预测为 unknown（abstained）；
    - truth 没有匹配预测（unmatched_truths）；
    - 预测标签错误。

    Args:
        aligned_pairs: 对齐的对列表
        unmatched_truths: 未匹配的真值列表（R253 新增，计入分母）

    Returns:
        Overall accuracy (0.0 到 1.0)
    """
    correct_count = 0
    total_count = 0

    for pair in aligned_pairs:
        if pair.is_matched and pair.prediction and pair.truth:
            total_count += 1

            # 预测为 unknown 算错误（abstained 不计入分子，但仍在分母）
            if pair.prediction.coarse_label == 'unknown':
                continue

            # 检查 coarse_label 是否匹配 semantic_type（归一化旧标签）
            if normalize_legacy_label(pair.prediction.coarse_label) == \
                    normalize_legacy_label(pair.truth.semantic_type):
                correct_count += 1

    # unmatched_truths 计入分母（truth 没有匹配预测算错误）
    if unmatched_truths:
        total_count += len(unmatched_truths)

    if total_count == 0:
        return 0.0

    return correct_count / total_count


def is_prediction_correct(pair: AlignedPair) -> bool:
    """判断预测是否正确

    与 :func:`calculate_overall_accuracy` 保持一致：
    - pred=unknown 一律算错误（即使 truth 也是 unknown，R259 设计决策）
    - 标签比较前应用 :func:`normalize_legacy_label` 归一化旧标签

    Args:
        pair: 对齐的对

    Returns:
        是否正确
    """
    if not pair.is_matched or not pair.prediction or not pair.truth:
        return False

    # pred=unknown 一律算错误（与 calculate_overall_accuracy 一致）
    if pair.prediction.coarse_label == 'unknown':
        return False

    return normalize_legacy_label(pair.prediction.coarse_label) == \
        normalize_legacy_label(pair.truth.semantic_type)


def calculate_coverage(
    aligned_pairs: List[AlignedPair],
    unmatched_truths: List[GroundTruthRecord]
) -> float:
    """计算 coverage

    R254：Coverage = 与 truth 对齐且预测非 unknown 的字段数 / 全部 truth 数量

    - 分子：匹配且 prediction 非空且 coarse_label != 'unknown' 的对数
    - 分母：匹配且 truth 非空的对数 + unmatched_truths 数量 = 全部 truth 数量

    Args:
        aligned_pairs: 对齐的对列表
        unmatched_truths: 未匹配的真值列表

    Returns:
        Coverage (0.0 到 1.0)
    """
    # 分母 = 全部 truth 数量（匹配的 truth + 未匹配的 truth）
    matched_truth_count = sum(1 for pair in aligned_pairs if pair.is_matched and pair.truth)
    total_truths = matched_truth_count + len(unmatched_truths)

    if total_truths == 0:
        return 0.0

    # 分子 = 与 truth 对齐且预测非 unknown 的字段数
    covered_count = sum(
        1 for pair in aligned_pairs
        if pair.is_matched and pair.prediction and pair.truth
        and pair.prediction.coarse_label != 'unknown'
    )

    return covered_count / total_truths


def calculate_unknown_rate(
    aligned_pairs: List[AlignedPair],
    unmatched_truths: Optional[List[GroundTruthRecord]] = None
) -> float:
    """计算 unknown rate

    R254：Unknown rate = 对齐后预测 unknown 的字段数 / 全部 truth 数量

    - 分子：匹配且 prediction 非空且 coarse_label == 'unknown' 的对数
    - 分母：匹配且 truth 非空的对数 + unmatched_truths 数量 = 全部 truth 数量

    Args:
        aligned_pairs: 对齐的对列表
        unmatched_truths: 未匹配的真值列表（R254 新增，计入分母）

    Returns:
        Unknown rate (0.0 到 1.0)
    """
    # 分母 = 全部 truth 数量
    matched_truth_count = sum(1 for pair in aligned_pairs if pair.is_matched and pair.truth)
    if unmatched_truths:
        matched_truth_count += len(unmatched_truths)

    if matched_truth_count == 0:
        return 0.0

    # 分子 = 对齐后预测 unknown 的字段数
    unknown_count = sum(
        1 for pair in aligned_pairs
        if pair.is_matched and pair.prediction
        and pair.prediction.coarse_label == 'unknown'
    )

    return unknown_count / matched_truth_count


def is_prediction_unknown(pair: AlignedPair) -> bool:
    """判断预测是否为 unknown
    
    Args:
        pair: 对齐的对
        
    Returns:
        是否为 unknown
    """
    if not pair.is_matched or not pair.prediction:
        return False
    
    return pair.prediction.coarse_label == 'unknown'


def calculate_covered_accuracy(aligned_pairs: List[AlignedPair]) -> float:
    """计算 covered accuracy

    R255：Covered Accuracy = 非 unknown 且正确的字段数 / 非 unknown 的已对齐预测数

    - 分母：匹配且 prediction/truth 非空且 coarse_label != 'unknown' 的对数
      （非 unknown 的已对齐预测数，abstained 不计入分母）
    - 分子：上述对中 coarse_label == semantic_type 的对数（非 unknown 且正确）

    Args:
        aligned_pairs: 对齐的对列表

    Returns:
        Covered accuracy (0.0 到 1.0)
    """
    correct_count = 0
    covered_count = 0

    for pair in aligned_pairs:
        if not (pair.is_matched and pair.prediction and pair.truth):
            continue
        # abstained（unknown 预测）不计入分母
        if pair.prediction.coarse_label == 'unknown':
            continue
        covered_count += 1
        # 检查 coarse_label 是否匹配 semantic_type（归一化旧标签）
        if normalize_legacy_label(pair.prediction.coarse_label) == \
                normalize_legacy_label(pair.truth.semantic_type):
            correct_count += 1

    if covered_count == 0:
        return 0.0

    return correct_count / covered_count


def calculate_fine_top1_accuracy(aligned_pairs: List[AlignedPair]) -> float:
    """计算 fine-grained top-1 accuracy
    
    Fine top-1 accuracy = fine_label 匹配的数量 / 有 fine_label 的总数
    
    只在预测和真值都有 fine_label 时计算
    
    Args:
        aligned_pairs: 对齐的对列表
        
    Returns:
        Fine top-1 accuracy (0.0 到 1.0)
    """
    if not aligned_pairs:
        return 0.0
    
    correct_count = 0
    total_count = 0
    
    for pair in aligned_pairs:
        if not pair.is_matched or not pair.prediction or not pair.truth:
            continue
        
        # 检查是否都有 fine_label
        pred_fine = pair.prediction.fine_label
        truth_fine = pair.truth.fine_label
        
        if pred_fine and truth_fine:
            total_count += 1
            
            if pred_fine == truth_fine:
                correct_count += 1
    
    if total_count == 0:
        return 0.0
    
    return correct_count / total_count


def has_fine_label(pair: AlignedPair) -> bool:
    """判断对是否包含 fine label
    
    Args:
        pair: 对齐的对
        
    Returns:
        是否包含 fine label
    """
    if not pair.is_matched or not pair.prediction or not pair.truth:
        return False
    
    return bool(pair.prediction.fine_label and pair.truth.fine_label)


@dataclass
class EvaluationError:
    """评估错误记录"""
    field_key: FieldKey
    error_type: str
    predicted_label: str
    true_label: str
    confidence: float
    details: Optional[dict] = None


def collect_errors(
    aligned_pairs: List[AlignedPair],
    unmatched_truths: List[GroundTruthRecord],
    unmatched_predictions: Optional[List] = None
) -> List[EvaluationError]:
    """收集评估错误

    R259：重写 errors.jsonl 分类，四类错误，每条带 FieldKey 与 evidence。

    错误类型：
    1. wrong_label：matched 且预测非 unknown 且归一化后标签 != truth 标签
    2. abstained：matched 且预测为 unknown（弃权）
    3. missing_prediction：unmatched_truths（有 truth 无预测）
    4. unexpected_prediction：unmatched_predictions（有预测无 truth）

    标签比较应用 normalize_legacy_label（与 R256/R258 一致）。
    每条错误带 FieldKey 与 evidence（预测证据或 truth 信息）。

    Args:
        aligned_pairs: 对齐的对列表
        unmatched_truths: 未匹配的真值列表（missing prediction）
        unmatched_predictions: 未匹配的预测列表（unexpected prediction，R259 新增）。
            不传时向后兼容（不收集 unexpected_prediction）。

    Returns:
        错误记录列表
    """
    errors = []

    # 处理匹配的对
    for pair in aligned_pairs:
        if not pair.is_matched or not pair.prediction or not pair.truth:
            continue

        # R259: 以标准 coarse label 比较（与 R256/R258 一致）
        predicted_label = normalize_legacy_label(pair.prediction.coarse_label)
        true_label = normalize_legacy_label(pair.truth.semantic_type)

        # abstained：预测为 unknown（弃权）
        if predicted_label == 'unknown':
            ev_fields = _extract_evidence_fields_from_prediction(pair.prediction)
            error = EvaluationError(
                field_key=pair.field_key,
                error_type='abstained',
                predicted_label='unknown',
                true_label=true_label,
                confidence=ev_fields['score'],
                details={
                    'evidence': {
                        'detector': ev_fields['detector'],
                        'reason_code': ev_fields['reason_code'],
                        'score': ev_fields['score'],
                        'fine_label': ev_fields['fine_label'],
                    },
                    'truth': {
                        'semantic_label': pair.truth.semantic_label,
                        'confidence': pair.truth.confidence,
                        'fine_label': pair.truth.fine_label,
                    }
                }
            )
            errors.append(error)
            continue

        # wrong_label：预测非 unknown 但标签错误
        if predicted_label != true_label:
            ev_fields = _extract_evidence_fields_from_prediction(pair.prediction)
            error = EvaluationError(
                field_key=pair.field_key,
                error_type='wrong_label',
                predicted_label=predicted_label,
                true_label=true_label,
                confidence=ev_fields['score'],
                details={
                    'evidence': {
                        'detector': ev_fields['detector'],
                        'reason_code': ev_fields['reason_code'],
                        'score': ev_fields['score'],
                        'fine_label': ev_fields['fine_label'],
                    },
                    'truth': {
                        'semantic_label': pair.truth.semantic_label,
                        'confidence': pair.truth.confidence,
                        'fine_label': pair.truth.fine_label,
                    }
                }
            )
            errors.append(error)

    # missing_prediction：有 truth 无预测（用 truth 完整 FieldKey，R249）
    for truth in unmatched_truths:
        error = EvaluationError(
            field_key=truth.field_key,
            error_type='missing_prediction',
            predicted_label='none',
            true_label=normalize_legacy_label(truth.semantic_type),
            confidence=0.0,
            details={
                'evidence': None,
                'truth': {
                    'semantic_label': truth.semantic_label,
                    'confidence': truth.confidence,
                    'truth_id': truth.truth_id,
                    'fine_label': truth.fine_label,
                }
            }
        )
        errors.append(error)

    # unexpected_prediction：有预测无 truth（R259 新增）
    if unmatched_predictions:
        for pred in unmatched_predictions:
            key = _extract_field_key_from_prediction(pred)
            if key is None:
                # 无法提取身份的预测（边缘情况）
                # R417：field_index 必须 >= 0（FieldKey 校验），用 layout_id='unknown' 区分
                key = FieldKey(
                    layout_id='unknown',
                    direction=Direction.UNKNOWN,
                    field_index=0
                )
            predicted_label = normalize_legacy_label(pred.coarse_label)
            ev_fields = _extract_evidence_fields_from_prediction(pred)
            error = EvaluationError(
                field_key=key,
                error_type='unexpected_prediction',
                predicted_label=predicted_label,
                true_label='none',
                confidence=ev_fields['score'],
                details={
                    'evidence': {
                        'detector': ev_fields['detector'],
                        'reason_code': ev_fields['reason_code'],
                        'score': ev_fields['score'],
                        'fine_label': ev_fields['fine_label'],
                    },
                    'truth': None
                }
            )
            errors.append(error)

    return errors


def export_errors_to_jsonl(
    errors: List[EvaluationError],
    output_path: str
) -> None:
    """导出错误到 JSONL 文件
    
    Args:
        errors: 错误记录列表
        output_path: 输出文件路径
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        for error in errors:
            error_dict = {
                'field_key': {
                    'layout_id': error.field_key.layout_id,
                    'direction': error.field_key.direction,
                    'field_index': error.field_key.field_index
                },
                'error_type': error.error_type,
                'predicted_label': error.predicted_label,
                'true_label': error.true_label,
                'confidence': error.confidence,
                'details': error.details
            }
            f.write(json.dumps(error_dict, ensure_ascii=False) + '\n')
