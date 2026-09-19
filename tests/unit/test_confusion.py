"""Confusion matrix 测试"""

import pytest
from semantic_detector.contracts import DetectorEvidence, FieldKey
from semantic_detector.evaluation.ground_truth import GroundTruthRecord
from semantic_detector.evaluation.metrics import AlignedPair
from semantic_detector.evaluation.confusion import (
    LabelStats,
    calculate_per_label_stats,
    get_all_labels,
    get_truth_labels,
    calculate_precision,
    calculate_recall,
    calculate_f1,
    LabelMetrics,
    calculate_per_label_metrics,
    calculate_macro_f1,
    calculate_macro_precision,
    calculate_macro_recall,
)


class TestCalculatePerLabelStats:
    """每标签统计测试"""
    
    def test_empty_lists(self):
        """测试空列表"""
        stats = calculate_per_label_stats([], [])
        assert stats == {}
    
    def test_single_tp(self):
        """测试单个 TP"""
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('test', 'constant', '', 1.0, True, 'test'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
        ]
        
        stats = calculate_per_label_stats(pairs, [])
        
        assert 'constant' in stats
        assert stats['constant'].tp == 1
        assert stats['constant'].fp == 0
        assert stats['constant'].fn == 0
    
    def test_single_fp(self):
        """测试单个 FP"""
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('test', 'constant', '', 1.0, True, 'test'),
                GroundTruthRecord(1, 0, 'payload', 1.0, True),
                True
            ),
        ]
        
        stats = calculate_per_label_stats(pairs, [])
        
        assert 'constant' in stats
        assert stats['constant'].tp == 0
        assert stats['constant'].fp == 1
        assert stats['constant'].fn == 0
        
        assert 'payload' in stats
        assert stats['payload'].tp == 0
        assert stats['payload'].fp == 0
        assert stats['payload'].fn == 1
    
    def test_single_fn_from_unmatched(self):
        """测试从未匹配真值产生的 FN"""
        unmatched_truths = [
            GroundTruthRecord(1, 0, 'constant', 1.0, True),
        ]
        
        stats = calculate_per_label_stats([], unmatched_truths)
        
        assert 'constant' in stats
        assert stats['constant'].tp == 0
        assert stats['constant'].fp == 0
        assert stats['constant'].fn == 1
    
    def test_mixed_stats(self):
        """测试混合统计"""
        pairs = [
            # TP for constant
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('test', 'constant', '', 1.0, True, 'test'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
            # FP for payload (predicted payload, actual constant)
            AlignedPair(
                FieldKey("l1", "r", 1),
                DetectorEvidence('test', 'payload', '', 1.0, True, 'test'),
                GroundTruthRecord(2, 1, 'constant', 1.0, True),
                True
            ),
        ]
        
        unmatched_truths = [
            # FN for timestamp
            GroundTruthRecord(3, 2, 'timestamp', 1.0, True),
        ]
        
        stats = calculate_per_label_stats(pairs, unmatched_truths)
        
        # constant: 1 TP, 1 FN
        assert stats['constant'].tp == 1
        assert stats['constant'].fp == 0
        assert stats['constant'].fn == 1
        
        # payload: 1 FP
        assert stats['payload'].tp == 0
        assert stats['payload'].fp == 1
        assert stats['payload'].fn == 0
        
        # timestamp: 1 FN
        assert stats['timestamp'].tp == 0
        assert stats['timestamp'].fp == 0
        assert stats['timestamp'].fn == 1


class TestGetAllLabels:
    """获取所有标签测试"""
    
    def test_empty_lists(self):
        """测试空列表"""
        labels = get_all_labels([], [])
        assert labels == []
    
    def test_from_predictions(self):
        """测试从预测获取标签"""
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('test', 'constant', '', 1.0, True, 'test'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
        ]
        
        labels = get_all_labels(pairs, [])
        
        assert 'constant' in labels
    
    def test_from_truths(self):
        """测试从真值获取标签"""
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('test', 'constant', '', 1.0, True, 'test'),
                GroundTruthRecord(1, 0, 'payload', 1.0, True),
                True
            ),
        ]
        
        labels = get_all_labels(pairs, [])
        
        assert 'constant' in labels
        assert 'payload' in labels
    
    def test_from_unmatched_truths(self):
        """测试从未匹配真值获取标签"""
        unmatched_truths = [
            GroundTruthRecord(1, 0, 'timestamp', 1.0, True),
        ]
        
        labels = get_all_labels([], unmatched_truths)
        
        assert 'timestamp' in labels
    
    def test_sorted_labels(self):
        """测试标签排序"""
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('test', 'payload', '', 1.0, True, 'test'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
        ]
        
        labels = get_all_labels(pairs, [])
        
        assert labels == ['constant', 'payload']


class TestCalculatePrecision:
    """Precision 测试"""
    
    def test_zero_denominator(self):
        """测试分母为零"""
        stats = LabelStats(label='test', tp=0, fp=0, fn=0)
        precision = calculate_precision(stats)
        assert precision == 0.0
    
    def test_perfect_precision(self):
        """测试完美 precision"""
        stats = LabelStats(label='test', tp=10, fp=0, fn=5)
        precision = calculate_precision(stats)
        assert precision == 1.0
    
    def test_half_precision(self):
        """测试一半 precision"""
        stats = LabelStats(label='test', tp=5, fp=5, fn=0)
        precision = calculate_precision(stats)
        assert precision == 0.5


class TestCalculateRecall:
    """Recall 测试"""
    
    def test_zero_denominator(self):
        """测试分母为零"""
        stats = LabelStats(label='test', tp=0, fp=0, fn=0)
        recall = calculate_recall(stats)
        assert recall == 0.0
    
    def test_perfect_recall(self):
        """测试完美 recall"""
        stats = LabelStats(label='test', tp=10, fp=5, fn=0)
        recall = calculate_recall(stats)
        assert recall == 1.0
    
    def test_half_recall(self):
        """测试一半 recall"""
        stats = LabelStats(label='test', tp=5, fp=0, fn=5)
        recall = calculate_recall(stats)
        assert recall == 0.5


class TestCalculateF1:
    """F1 测试"""
    
    def test_zero_precision_and_recall(self):
        """测试 precision 和 recall 都为零"""
        stats = LabelStats(label='test', tp=0, fp=5, fn=5)
        f1 = calculate_f1(stats)
        assert f1 == 0.0
    
    def test_perfect_f1(self):
        """测试完美 F1"""
        stats = LabelStats(label='test', tp=10, fp=0, fn=0)
        f1 = calculate_f1(stats)
        assert f1 == 1.0
    
    def test_balanced_f1(self):
        """测试平衡 F1"""
        # precision = 0.5, recall = 0.5
        # F1 = 2 * 0.5 * 0.5 / (0.5 + 0.5) = 0.5
        stats = LabelStats(label='test', tp=5, fp=5, fn=5)
        f1 = calculate_f1(stats)
        assert f1 == 0.5


class TestCalculatePerLabelMetrics:
    """每标签指标测试"""
    
    def test_empty_stats(self):
        """测试空统计"""
        metrics = calculate_per_label_metrics({})
        assert metrics == {}
    
    def test_single_label(self):
        """测试单个标签"""
        stats = {
            'constant': LabelStats(label='constant', tp=10, fp=0, fn=0)
        }
        
        metrics = calculate_per_label_metrics(stats)
        
        assert 'constant' in metrics
        assert metrics['constant'].precision == 1.0
        assert metrics['constant'].recall == 1.0
        assert metrics['constant'].f1 == 1.0
    
    def test_multiple_labels(self):
        """测试多个标签"""
        stats = {
            'constant': LabelStats(label='constant', tp=8, fp=2, fn=2),
            'payload': LabelStats(label='payload', tp=5, fp=5, fn=5),
        }
        
        metrics = calculate_per_label_metrics(stats)
        
        assert 'constant' in metrics
        assert 'payload' in metrics
        
        # constant: precision = 8/10 = 0.8, recall = 8/10 = 0.8
        assert metrics['constant'].precision == 0.8
        assert metrics['constant'].recall == 0.8
        
        # payload: precision = 5/10 = 0.5, recall = 5/10 = 0.5
        assert metrics['payload'].precision == 0.5
        assert metrics['payload'].recall == 0.5


class TestCalculateMacroF1:
    """Macro F1 测试"""
    
    def test_empty_metrics(self):
        """测试空指标"""
        f1 = calculate_macro_f1({})
        assert f1 == 0.0
    
    def test_single_label(self):
        """测试单个标签"""
        metrics = {
            'constant': LabelMetrics(label='constant', precision=1.0, recall=1.0, f1=1.0)
        }
        
        f1 = calculate_macro_f1(metrics)
        assert f1 == 1.0
    
    def test_multiple_labels(self):
        """测试多个标签"""
        metrics = {
            'constant': LabelMetrics(label='constant', precision=0.8, recall=0.8, f1=0.8),
            'payload': LabelMetrics(label='payload', precision=0.5, recall=0.5, f1=0.5),
        }
        
        f1 = calculate_macro_f1(metrics)
        assert f1 == 0.65  # (0.8 + 0.5) / 2


class TestCalculateMacroPrecision:
    """Macro precision 测试"""
    
    def test_empty_metrics(self):
        """测试空指标"""
        precision = calculate_macro_precision({})
        assert precision == 0.0
    
    def test_multiple_labels(self):
        """测试多个标签"""
        metrics = {
            'constant': LabelMetrics(label='constant', precision=0.8, recall=0.8, f1=0.8),
            'payload': LabelMetrics(label='payload', precision=0.6, recall=0.6, f1=0.6),
        }
        
        precision = calculate_macro_precision(metrics)
        assert precision == 0.7  # (0.8 + 0.6) / 2


class TestCalculateMacroRecall:
    """Macro recall 测试"""
    
    def test_empty_metrics(self):
        """测试空指标"""
        recall = calculate_macro_recall({})
        assert recall == 0.0
    
    def test_multiple_labels(self):
        """测试多个标签"""
        metrics = {
            'constant': LabelMetrics(label='constant', precision=0.8, recall=0.9, f1=0.84),
            'payload': LabelMetrics(label='payload', precision=0.6, recall=0.7, f1=0.64),
        }
        
        recall = calculate_macro_recall(metrics)
        assert recall == 0.8  # (0.9 + 0.7) / 2


class TestPerLabelStatsR256:
    """R256：per-label TP/FP/FN 处理 missing truth，以标准 coarse label 计算

    03 教程 12.4 Macro-F1：
    - 以标准 coarse label 计算
    - unmatched truth 相当于该类别 FN（missing prediction 计 FN）
    - 04 任务表 R256：手算例子，missing prediction 计 FN
    """

    def test_hand_calculated_full_scenario(self):
        """手算例子：TP/FP/FN/missing 全场景

        - pair0: pred=constant, truth=constant → TP for constant
        - pair1: pred=length, truth=timestamp → FP for length, FN for timestamp
        - pair2: pred=sequence(旧标签), truth=sequence_or_counter →
          normalize 后均为 sequence_or_counter → TP for sequence_or_counter
        - unmatched truth3: identifier → FN for identifier (missing prediction)

        手算 stats:
        - constant: TP=1, FP=0, FN=0
        - length: TP=0, FP=1, FN=0
        - timestamp: TP=0, FP=0, FN=1
        - sequence_or_counter: TP=1, FP=0, FN=0
        - identifier: TP=0, FP=0, FN=1
        """
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('test', 'constant', '', 1.0, True, 'test'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
            AlignedPair(
                FieldKey("l1", "r", 1),
                DetectorEvidence('test', 'length', '', 1.0, True, 'test'),
                GroundTruthRecord(2, 1, 'timestamp', 1.0, True),
                True
            ),
            AlignedPair(
                FieldKey("l1", "r", 2),
                DetectorEvidence('test', 'sequence', '', 1.0, True, 'test'),
                GroundTruthRecord(3, 2, 'sequence_or_counter', 1.0, True),
                True
            ),
        ]
        unmatched_truths = [
            GroundTruthRecord(4, 3, 'identifier', 1.0, True),
        ]

        stats = calculate_per_label_stats(pairs, unmatched_truths)

        # constant: TP=1, FP=0, FN=0
        assert stats['constant'].tp == 1
        assert stats['constant'].fp == 0
        assert stats['constant'].fn == 0

        # length: TP=0, FP=1, FN=0
        assert stats['length'].tp == 0
        assert stats['length'].fp == 1
        assert stats['length'].fn == 0

        # timestamp: TP=0, FP=0, FN=1
        assert stats['timestamp'].tp == 0
        assert stats['timestamp'].fp == 0
        assert stats['timestamp'].fn == 1

        # sequence_or_counter: TP=1, FP=0, FN=0
        assert stats['sequence_or_counter'].tp == 1
        assert stats['sequence_or_counter'].fp == 0
        assert stats['sequence_or_counter'].fn == 0

        # identifier: TP=0, FP=0, FN=1 (missing prediction)
        assert stats['identifier'].tp == 0
        assert stats['identifier'].fp == 0
        assert stats['identifier'].fn == 1

    def test_missing_prediction_counts_as_fn(self):
        """missing prediction（unmatched truth）计 FN"""
        pairs = []
        unmatched_truths = [
            GroundTruthRecord(1, 0, 'constant', 1.0, True),
            GroundTruthRecord(2, 1, 'constant', 1.0, True),
            GroundTruthRecord(3, 2, 'length', 1.0, True),
        ]

        stats = calculate_per_label_stats(pairs, unmatched_truths)

        # constant: 2 个 missing → FN=2
        assert stats['constant'].tp == 0
        assert stats['constant'].fp == 0
        assert stats['constant'].fn == 2

        # length: 1 个 missing → FN=1
        assert stats['length'].tp == 0
        assert stats['length'].fp == 0
        assert stats['length'].fn == 1

    def test_normalize_legacy_prediction_label_matches_standard_truth(self):
        """旧预测标签 normalize 后与标准 truth 标签匹配算 TP

        pred='type_opcode'（旧）, truth='type_control'（标准）
        normalize('type_opcode')='type_control' → TP
        """
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('test', 'type_opcode', '', 1.0, True, 'test'),
                GroundTruthRecord(1, 0, 'type_control', 1.0, True),
                True
            ),
        ]

        stats = calculate_per_label_stats(pairs, [])

        # type_control: TP=1（旧标签 type_opcode 归一化后匹配）
        assert 'type_control' in stats
        assert stats['type_control'].tp == 1
        assert stats['type_control'].fp == 0
        assert stats['type_control'].fn == 0
        # 不应出现 type_opcode 这个旧标签键
        assert 'type_opcode' not in stats

    def test_normalize_legacy_truth_label(self):
        """旧 truth 标签 normalize 后参与统计"""
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('test', 'payload', '', 1.0, True, 'test'),
                GroundTruthRecord(1, 0, 'opaque_payload', 1.0, True),
                True
            ),
        ]

        stats = calculate_per_label_stats(pairs, [])

        # opaque_payload → payload
        assert 'payload' in stats
        assert stats['payload'].tp == 1
        assert 'opaque_payload' not in stats

    def test_hand_calculated_macro_f1(self):
        """手算 macro-F1：truth 中出现的类别等权

        场景：
        - pair0: pred=constant, truth=constant → TP for constant
        - pair1: pred=length, truth=length → TP for length
        - unmatched truth2: timestamp → FN for timestamp

        stats:
        - constant: TP=1, FP=0, FN=0 → P=1.0, R=1.0, F1=1.0
        - length: TP=1, FP=0, FN=0 → P=1.0, R=1.0, F1=1.0
        - timestamp: TP=0, FP=0, FN=1 → P=0.0, R=0.0, F1=0.0

        macro_f1 = (1.0 + 1.0 + 0.0) / 3 = 2/3
        """
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('test', 'constant', '', 1.0, True, 'test'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
            AlignedPair(
                FieldKey("l1", "r", 1),
                DetectorEvidence('test', 'length', '', 1.0, True, 'test'),
                GroundTruthRecord(2, 1, 'length', 1.0, True),
                True
            ),
        ]
        unmatched_truths = [
            GroundTruthRecord(3, 2, 'timestamp', 1.0, True),
        ]

        stats = calculate_per_label_stats(pairs, unmatched_truths)
        metrics = calculate_per_label_metrics(stats)
        macro_f1 = calculate_macro_f1(metrics)

        # macro_f1 = (1.0 + 1.0 + 0.0) / 3
        assert macro_f1 == pytest.approx(2.0 / 3.0)


class TestMacroF1R257:
    """R257：Macro-F1 仅按 truth 出现的标签等权

    03 教程 12.4 Macro-F1：
    - truth 中出现的每个类别等权
    - 04 任务表 R257：类别不均衡，仅按 truth 出现标签等权
    """

    def test_get_truth_labels_excludes_prediction_only_labels(self):
        """get_truth_labels 只返回 truth 标签（不含仅预测出现的标签）"""
        pairs = [
            # truth=constant, pred=constant
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('test', 'constant', '', 1.0, True, 'test'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
            # truth=constant, pred=payload（payload 只在预测中出现）
            AlignedPair(
                FieldKey("l1", "r", 1),
                DetectorEvidence('test', 'payload', '', 1.0, True, 'test'),
                GroundTruthRecord(2, 1, 'constant', 1.0, True),
                True
            ),
        ]

        truth_labels = get_truth_labels(pairs, [])

        # truth 中只有 constant
        assert truth_labels == ['constant']

    def test_get_truth_labels_includes_unmatched_truths(self):
        """get_truth_labels 含 unmatched_truths 的标签"""
        pairs = []
        unmatched_truths = [
            GroundTruthRecord(1, 0, 'constant', 1.0, True),
            GroundTruthRecord(2, 1, 'timestamp', 1.0, True),
        ]

        truth_labels = get_truth_labels(pairs, unmatched_truths)

        assert truth_labels == ['constant', 'timestamp']

    def test_macro_f1_only_truth_labels_equal_weight(self):
        """macro_f1 传入 truth_labels 时只对 truth 标签平均（排除只有 FP 的预测标签）

        场景：
        - pair0: pred=constant, truth=constant → TP for constant
        - pair1: pred=payload, truth=constant → FP for payload, FN for constant

        stats:
        - constant: TP=1, FP=0, FN=1 → P=1.0, R=0.5, F1=2/3
        - payload: TP=0, FP=1, FN=0 → P=0.0, R=0.0, F1=0.0（只有 FP，truth 中没出现）

        truth_labels = ['constant']
        旧 macro_f1（不传）= (2/3 + 0.0) / 2 = 1/3
        新 macro_f1（传 truth_labels）= 2/3 / 1 = 2/3
        """
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('test', 'constant', '', 1.0, True, 'test'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
            AlignedPair(
                FieldKey("l1", "r", 1),
                DetectorEvidence('test', 'payload', '', 1.0, True, 'test'),
                GroundTruthRecord(2, 1, 'constant', 1.0, True),
                True
            ),
        ]

        stats = calculate_per_label_stats(pairs, [])
        metrics = calculate_per_label_metrics(stats)
        truth_labels = get_truth_labels(pairs, [])

        # 旧逻辑（不传 truth_labels）：对 constant + payload 平均
        old_macro_f1 = calculate_macro_f1(metrics)
        assert old_macro_f1 == pytest.approx((2.0 / 3.0 + 0.0) / 2)

        # 新逻辑（传 truth_labels）：只对 constant 平均
        new_macro_f1 = calculate_macro_f1(metrics, truth_labels)
        assert new_macro_f1 == pytest.approx(2.0 / 3.0)

    def test_macro_f1_backward_compatible_without_truth_labels(self):
        """不传 truth_labels 时向后兼容：对所有 metrics 标签平均"""
        metrics = {
            'constant': LabelMetrics(label='constant', precision=0.8, recall=0.8, f1=0.8),
            'payload': LabelMetrics(label='payload', precision=0.6, recall=0.6, f1=0.6),
        }

        f1 = calculate_macro_f1(metrics)

        # (0.8 + 0.6) / 2 = 0.7
        assert f1 == 0.7

    def test_macro_precision_only_truth_labels(self):
        """macro_precision 传入 truth_labels 时只对 truth 标签平均"""
        metrics = {
            'constant': LabelMetrics(label='constant', precision=1.0, recall=0.5, f1=0.667),
            'payload': LabelMetrics(label='payload', precision=0.0, recall=0.0, f1=0.0),
        }
        truth_labels = ['constant']

        precision = calculate_macro_precision(metrics, truth_labels)

        # 只对 constant 平均 = 1.0
        assert precision == 1.0

    def test_macro_recall_only_truth_labels(self):
        """macro_recall 传入 truth_labels 时只对 truth 标签平均"""
        metrics = {
            'constant': LabelMetrics(label='constant', precision=1.0, recall=0.5, f1=0.667),
            'payload': LabelMetrics(label='payload', precision=0.0, recall=0.0, f1=0.0),
        }
        truth_labels = ['constant']

        recall = calculate_macro_recall(metrics, truth_labels)

        # 只对 constant 平均 = 0.5
        assert recall == 0.5

    def test_class_imbalance_scenario(self):
        """类别不均衡场景：truth 中 3 个类别，预测引入额外 FP 类别

        - pair0: pred=constant, truth=constant → TP for constant
        - pair1: pred=length, truth=length → TP for length
        - pair2: pred=payload, truth=timestamp → FP for payload, FN for timestamp
        - unmatched truth3: identifier → FN for identifier

        stats:
        - constant: TP=1, FP=0, FN=0 → F1=1.0
        - length: TP=1, FP=0, FN=0 → F1=1.0
        - timestamp: TP=0, FP=0, FN=1 → F1=0.0
        - identifier: TP=0, FP=0, FN=1 → F1=0.0
        - payload: TP=0, FP=1, FN=0 → F1=0.0（只有 FP，truth 中没出现）

        truth_labels = ['constant', 'identifier', 'length', 'timestamp']
        新 macro_f1 = (1.0 + 1.0 + 0.0 + 0.0) / 4 = 0.5
        旧 macro_f1（含 payload）= (1.0+1.0+0.0+0.0+0.0)/5 = 0.4
        """
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('test', 'constant', '', 1.0, True, 'test'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
            AlignedPair(
                FieldKey("l1", "r", 1),
                DetectorEvidence('test', 'length', '', 1.0, True, 'test'),
                GroundTruthRecord(2, 1, 'length', 1.0, True),
                True
            ),
            AlignedPair(
                FieldKey("l1", "r", 2),
                DetectorEvidence('test', 'payload', '', 1.0, True, 'test'),
                GroundTruthRecord(3, 2, 'timestamp', 1.0, True),
                True
            ),
        ]
        unmatched_truths = [
            GroundTruthRecord(4, 3, 'identifier', 1.0, True),
        ]

        stats = calculate_per_label_stats(pairs, unmatched_truths)
        metrics = calculate_per_label_metrics(stats)
        truth_labels = get_truth_labels(pairs, unmatched_truths)

        # truth_labels 不含 payload
        assert 'payload' not in truth_labels
        assert set(truth_labels) == {'constant', 'length', 'timestamp', 'identifier'}

        new_macro_f1 = calculate_macro_f1(metrics, truth_labels)
        assert new_macro_f1 == 0.5

        # 旧逻辑（不传 truth_labels）含 payload，= 0.4
        old_macro_f1 = calculate_macro_f1(metrics)
        assert old_macro_f1 == pytest.approx(0.4)


class TestPerLabelStatsR259ConsistencyR417:
    """R417：calculate_per_label_stats R259 一致性

    R259 约束：pred=unknown 一律算错误（abstained error），不计 TP，
    即使 truth 也是 unknown。与 calculate_overall_accuracy / is_prediction_correct /
    collect_errors 保持一致。
    """

    def test_unknown_unknown_not_counted_as_tp(self):
        """pred=unknown + truth=unknown 不计 TP（R259）"""
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('det', 'unknown', '', 0.5, True, 'abstain'),
                GroundTruthRecord(1, 0, 'unknown', 1.0, True),
                True
            ),
        ]
        stats = calculate_per_label_stats(pairs, [])
        # unknown 标签不应有 TP
        assert stats['unknown'].tp == 0
        # truth=unknown 的 FN 应 +1（漏检）
        assert stats['unknown'].fn == 1

    def test_unknown_pred_with_nonunknown_truth_counts_fn(self):
        """pred=unknown + truth=constant → constant 的 FN +1（不计 unknown FP）"""
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('det', 'unknown', '', 0.5, True, 'abstain'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
        ]
        stats = calculate_per_label_stats(pairs, [])
        # constant 标签的 FN 应 +1（漏检）
        assert stats['constant'].fn == 1
        # unknown 不计 FP（abstain 不算误报）
        assert stats['unknown'].fp == 0

    def test_correct_prediction_still_counts_tp(self):
        """对照测试：pred=constant + truth=constant → TP +1（正常路径）"""
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('det', 'constant', '', 1.0, True, 'rc'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
        ]
        stats = calculate_per_label_stats(pairs, [])
        assert stats['constant'].tp == 1
        assert stats['constant'].fn == 0
        assert stats['constant'].fp == 0
