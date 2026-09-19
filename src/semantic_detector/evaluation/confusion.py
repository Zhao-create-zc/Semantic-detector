"""Confusion matrix 和每标签统计"""

from typing import Dict, List, Optional
from dataclasses import dataclass

from semantic_detector.evaluation.ground_truth import GroundTruthRecord
from semantic_detector.evaluation.metrics import AlignedPair
from semantic_detector.taxonomy import normalize_legacy_label


@dataclass
class LabelStats:
    """单个标签的统计"""
    label: str
    tp: int = 0
    fp: int = 0
    fn: int = 0


def calculate_per_label_stats(
    aligned_pairs: List[AlignedPair],
    unmatched_truths: List[GroundTruthRecord]
) -> Dict[str, LabelStats]:
    """计算每个标签的 TP/FP/FN

    R256：以标准 coarse label 计算（对预测和真值标签应用 normalize_legacy_label），
    missing prediction（unmatched_truths）计 FN。

    Args:
        aligned_pairs: 对齐的对列表
        unmatched_truths: 未匹配的真值列表

    Returns:
        标签到统计的字典
    """
    stats: Dict[str, LabelStats] = {}

    # 处理匹配的对
    for pair in aligned_pairs:
        if not pair.is_matched or not pair.prediction or not pair.truth:
            continue

        # R256: 以标准 coarse label 计算（防御性归一化旧标签）
        predicted_label = normalize_legacy_label(pair.prediction.coarse_label)
        true_label = normalize_legacy_label(pair.truth.semantic_type)

        # 确保标签存在于统计中
        if predicted_label not in stats:
            stats[predicted_label] = LabelStats(label=predicted_label)
        if true_label not in stats:
            stats[true_label] = LabelStats(label=true_label)

        # R417（R259 一致性）：pred=unknown 一律算错误（abstained error），
        # 不计 TP，即使 truth 也是 unknown。与 calculate_overall_accuracy /
        # is_prediction_correct / collect_errors 保持一致。
        if predicted_label == 'unknown':
            # pred=unknown：计为 true_label 的 FN（漏检）
            stats[true_label].fn += 1
            # 不计 unknown 的 FP（abstain 不算误报，与 errors.jsonl 的 abstained 分类一致）
        elif predicted_label == true_label:
            # TP: 预测正确
            stats[true_label].tp += 1
        else:
            # FP: 预测为该标签但实际不是
            stats[predicted_label].fp += 1
            # FN: 实际是该标签但预测不是
            stats[true_label].fn += 1

    # 处理未匹配的真值（missing prediction 计 FN）
    for truth in unmatched_truths:
        true_label = normalize_legacy_label(truth.semantic_type)

        if true_label not in stats:
            stats[true_label] = LabelStats(label=true_label)

        stats[true_label].fn += 1

    return stats


def get_all_labels(
    aligned_pairs: List[AlignedPair],
    unmatched_truths: List[GroundTruthRecord]
) -> List[str]:
    """获取所有出现的标签

    Args:
        aligned_pairs: 对齐的对列表
        unmatched_truths: 未匹配的真值列表

    Returns:
        标签列表（排序后）
    """
    labels = set()

    for pair in aligned_pairs:
        if pair.is_matched and pair.prediction:
            labels.add(normalize_legacy_label(pair.prediction.coarse_label))
        if pair.is_matched and pair.truth:
            labels.add(normalize_legacy_label(pair.truth.semantic_type))

    for truth in unmatched_truths:
        labels.add(normalize_legacy_label(truth.semantic_type))

    return sorted(labels)


def get_truth_labels(
    aligned_pairs: List[AlignedPair],
    unmatched_truths: List[GroundTruthRecord]
) -> List[str]:
    """R257：获取 truth 中出现的标签（用于 macro 等权平均）

    03 教程 12.4 Macro-F1：truth 中出现的每个类别等权。
    只收集 truth 标签（含 unmatched_truths），不含仅预测出现的标签。

    Args:
        aligned_pairs: 对齐的对列表
        unmatched_truths: 未匹配的真值列表

    Returns:
        truth 中出现的标签列表（标准化、去重、排序后）
    """
    labels = set()

    for pair in aligned_pairs:
        if pair.is_matched and pair.truth:
            labels.add(normalize_legacy_label(pair.truth.semantic_type))

    for truth in unmatched_truths:
        labels.add(normalize_legacy_label(truth.semantic_type))

    return sorted(labels)


def calculate_precision(stats: LabelStats) -> float:
    """计算 precision
    
    Precision = TP / (TP + FP)
    
    Args:
        stats: 标签统计
        
    Returns:
        Precision (0.0 到 1.0)
    """
    denominator = stats.tp + stats.fp
    
    if denominator == 0:
        return 0.0
    
    return stats.tp / denominator


def calculate_recall(stats: LabelStats) -> float:
    """计算 recall
    
    Recall = TP / (TP + FN)
    
    Args:
        stats: 标签统计
        
    Returns:
        Recall (0.0 到 1.0)
    """
    denominator = stats.tp + stats.fn
    
    if denominator == 0:
        return 0.0
    
    return stats.tp / denominator


def calculate_f1(stats: LabelStats) -> float:
    """计算 F1 score
    
    F1 = 2 * (precision * recall) / (precision + recall)
    
    Args:
        stats: 标签统计
        
    Returns:
        F1 score (0.0 到 1.0)
    """
    precision = calculate_precision(stats)
    recall = calculate_recall(stats)
    
    if precision + recall == 0:
        return 0.0
    
    return 2 * (precision * recall) / (precision + recall)


@dataclass
class LabelMetrics:
    """单个标签的评估指标"""
    label: str
    precision: float
    recall: float
    f1: float


def calculate_per_label_metrics(
    stats: Dict[str, LabelStats]
) -> Dict[str, LabelMetrics]:
    """计算每个标签的 precision/recall/F1
    
    Args:
        stats: 标签统计字典
        
    Returns:
        标签到指标的字典
    """
    metrics: Dict[str, LabelMetrics] = {}
    
    for label, label_stats in stats.items():
        metrics[label] = LabelMetrics(
            label=label,
            precision=calculate_precision(label_stats),
            recall=calculate_recall(label_stats),
            f1=calculate_f1(label_stats)
        )
    
    return metrics


def calculate_macro_f1(
    metrics: Dict[str, LabelMetrics],
    truth_labels: Optional[List[str]] = None
) -> float:
    """计算 macro F1

    R257：仅按 truth 出现的标签等权（不含只有 FP 的预测标签）。

    Macro F1 = 指定标签 F1 的平均值

    Args:
        metrics: 标签指标字典
        truth_labels: truth 中出现的标签列表（R257 新增）。
            传入时只对这些标签（且在 metrics 中存在）等权平均；
            不传时向后兼容，对所有 metrics 标签平均。

    Returns:
        Macro F1 (0.0 到 1.0)
    """
    if not metrics:
        return 0.0

    if truth_labels is not None:
        labels = [l for l in truth_labels if l in metrics]
    else:
        labels = list(metrics.keys())

    if not labels:
        return 0.0

    total_f1 = sum(metrics[l].f1 for l in labels)

    return total_f1 / len(labels)


def calculate_macro_precision(
    metrics: Dict[str, LabelMetrics],
    truth_labels: Optional[List[str]] = None
) -> float:
    """计算 macro precision

    R257：仅按 truth 出现的标签等权。

    Args:
        metrics: 标签指标字典
        truth_labels: truth 中出现的标签列表（R257 新增）

    Returns:
        Macro precision (0.0 到 1.0)
    """
    if not metrics:
        return 0.0

    if truth_labels is not None:
        labels = [l for l in truth_labels if l in metrics]
    else:
        labels = list(metrics.keys())

    if not labels:
        return 0.0

    total_precision = sum(metrics[l].precision for l in labels)

    return total_precision / len(labels)


def calculate_macro_recall(
    metrics: Dict[str, LabelMetrics],
    truth_labels: Optional[List[str]] = None
) -> float:
    """计算 macro recall

    R257：仅按 truth 出现的标签等权。

    Args:
        metrics: 标签指标字典
        truth_labels: truth 中出现的标签列表（R257 新增）

    Returns:
        Macro recall (0.0 到 1.0)
    """
    if not metrics:
        return 0.0

    if truth_labels is not None:
        labels = [l for l in truth_labels if l in metrics]
    else:
        labels = list(metrics.keys())

    if not labels:
        return 0.0

    total_recall = sum(metrics[l].recall for l in labels)

    return total_recall / len(labels)


@dataclass
class ConfusionMatrix:
    """混淆矩阵"""
    labels: List[str]
    matrix: List[List[int]]
    
    def get_count(self, predicted: str, actual: str) -> int:
        """获取指定位置的计数
        
        Args:
            predicted: 预测标签
            actual: 实际标签
            
        Returns:
            计数
        """
        if predicted not in self.labels or actual not in self.labels:
            return 0
        
        pred_idx = self.labels.index(predicted)
        actual_idx = self.labels.index(actual)
        
        return self.matrix[pred_idx][actual_idx]


def build_confusion_matrix(
    aligned_pairs: List[AlignedPair],
    unmatched_truths: List[GroundTruthRecord],
    labels: List[str]
) -> ConfusionMatrix:
    """构建混淆矩阵

    R258：对 predicted_label 和 true_label 应用 normalize_legacy_label
    （与 calculate_per_label_stats 保持一致），修复 unknown 列和多 layout 行为。
    旧标签（如 'sequence'/'type_opcode'/'opaque_payload'）归一化后正确计入矩阵，
    避免因标签未归一化而被丢弃；多 layout、多方向的对聚合到同一矩阵，行为可复现。

    missing prediction（unmatched_truths）计入 unknown 行（若 unknown 在 labels 中），
    表示"未给出明确预测"，使矩阵列总和等于 truth 总数，与 Overall Accuracy 分母一致。
    若 unknown 不在 labels 中则跳过（向后兼容）。

    混淆矩阵的行表示预测标签，列表示实际标签。

    Args:
        aligned_pairs: 对齐的对列表
        unmatched_truths: 未匹配的真值列表（missing prediction）
        labels: 标签列表（固定顺序，应为已归一化的标准标签）

    Returns:
        混淆矩阵
    """
    n = len(labels)
    matrix = [[0] * n for _ in range(n)]

    label_to_idx = {label: i for i, label in enumerate(labels)}
    unknown_idx = label_to_idx.get('unknown')

    # 处理匹配的对
    for pair in aligned_pairs:
        if not pair.is_matched or not pair.prediction or not pair.truth:
            continue

        # R258: 以标准 coarse label 计算（与 calculate_per_label_stats 一致）
        predicted_label = normalize_legacy_label(pair.prediction.coarse_label)
        true_label = normalize_legacy_label(pair.truth.semantic_type)

        if predicted_label in label_to_idx and true_label in label_to_idx:
            pred_idx = label_to_idx[predicted_label]
            true_idx = label_to_idx[true_label]
            matrix[pred_idx][true_idx] += 1

    # R258: 处理 unmatched_truths（missing prediction 计入 unknown 行）
    # 若 unknown 不在 labels 中则跳过（向后兼容）
    if unknown_idx is not None:
        for truth in unmatched_truths:
            true_label = normalize_legacy_label(truth.semantic_type)
            if true_label in label_to_idx:
                true_idx = label_to_idx[true_label]
                matrix[unknown_idx][true_idx] += 1

    return ConfusionMatrix(labels=labels, matrix=matrix)


def get_confusion_matrix_diagonal(confusion_matrix: ConfusionMatrix) -> List[int]:
    """获取混淆矩阵对角线
    
    对角线元素表示正确预测的数量
    
    Args:
        confusion_matrix: 混淆矩阵
        
    Returns:
        对角线元素列表
    """
    n = len(confusion_matrix.labels)
    return [confusion_matrix.matrix[i][i] for i in range(n)]


def calculate_accuracy_from_matrix(confusion_matrix: ConfusionMatrix) -> float:
    """从混淆矩阵计算准确率

    R417（R259 一致性）：pred=unknown + truth=unknown 不计为正确（abstained error）。
    对角线中 unknown-unknown 格不计入 correct，但计入 total（分母为全部 truth）。

    Args:
        confusion_matrix: 混淆矩阵

    Returns:
        准确率 (0.0 到 1.0)
    """
    total = 0
    correct = 0

    labels = confusion_matrix.labels
    n = len(labels)
    unknown_idx = labels.index('unknown') if 'unknown' in labels else -1

    for i in range(n):
        for j in range(n):
            total += confusion_matrix.matrix[i][j]

    # 对角线之和，但排除 unknown-unknown 格（R259：abstained error 不计正确）
    for i in range(n):
        if i == unknown_idx:
            continue  # unknown-unknown 不计 correct
        correct += confusion_matrix.matrix[i][i]

    if total == 0:
        return 0.0

    return correct / total
