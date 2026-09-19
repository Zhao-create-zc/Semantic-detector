"""Confusion matrix 测试"""

import pytest
from semantic_detector.contracts import DetectorEvidence, FieldKey, Direction
from semantic_detector.evaluation.ground_truth import GroundTruthRecord
from semantic_detector.evaluation.metrics import AlignedPair
from semantic_detector.evaluation.confusion import (
    ConfusionMatrix,
    build_confusion_matrix,
    get_confusion_matrix_diagonal,
    calculate_accuracy_from_matrix,
)


class TestConfusionMatrix:
    """ConfusionMatrix 数据类测试"""
    
    def test_get_count_valid(self):
        """测试获取有效位置的计数"""
        matrix = ConfusionMatrix(
            labels=['constant', 'payload'],
            matrix=[[5, 2], [1, 3]]
        )
        
        assert matrix.get_count('constant', 'constant') == 5
        assert matrix.get_count('constant', 'payload') == 2
        assert matrix.get_count('payload', 'constant') == 1
        assert matrix.get_count('payload', 'payload') == 3
    
    def test_get_count_invalid_label(self):
        """测试获取无效标签的计数"""
        matrix = ConfusionMatrix(
            labels=['constant', 'payload'],
            matrix=[[5, 2], [1, 3]]
        )
        
        assert matrix.get_count('unknown', 'constant') == 0
        assert matrix.get_count('constant', 'unknown') == 0


class TestBuildConfusionMatrix:
    """构建混淆矩阵测试"""
    
    def test_empty_pairs(self):
        """测试空对列表"""
        labels = ['constant', 'payload']
        
        matrix = build_confusion_matrix([], [], labels)
        
        assert matrix.labels == labels
        assert matrix.matrix == [[0, 0], [0, 0]]
    
    def test_single_correct_prediction(self):
        """测试单个正确预测"""
        pairs = [
            AlignedPair(
                FieldKey("l1", Direction.REQUEST, 0),
                DetectorEvidence('test', 'constant', '', 1.0, True, 'test'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
        ]
        
        labels = ['constant', 'payload']
        matrix = build_confusion_matrix(pairs, [], labels)
        
        assert matrix.matrix == [[1, 0], [0, 0]]
    
    def test_single_incorrect_prediction(self):
        """测试单个错误预测"""
        pairs = [
            AlignedPair(
                FieldKey("l1", Direction.REQUEST, 0),
                DetectorEvidence('test', 'payload', '', 1.0, True, 'test'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
        ]
        
        labels = ['constant', 'payload']
        matrix = build_confusion_matrix(pairs, [], labels)
        
        # 行是预测，列是实际
        # 预测 payload，实际 constant -> matrix[1][0] = 1
        assert matrix.matrix == [[0, 0], [1, 0]]
    
    def test_mixed_predictions(self):
        """测试混合预测"""
        pairs = [
            # 正确预测 constant
            AlignedPair(
                FieldKey("l1", Direction.REQUEST, 0),
                DetectorEvidence('test', 'constant', '', 1.0, True, 'test'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
            # 错误预测：预测 payload，实际 constant
            AlignedPair(
                FieldKey("l1", Direction.REQUEST, 1),
                DetectorEvidence('test', 'payload', '', 1.0, True, 'test'),
                GroundTruthRecord(2, 1, 'constant', 1.0, True),
                True
            ),
            # 正确预测 payload
            AlignedPair(
                FieldKey("l1", Direction.REQUEST, 2),
                DetectorEvidence('test', 'payload', '', 1.0, True, 'test'),
                GroundTruthRecord(3, 2, 'payload', 1.0, True),
                True
            ),
        ]
        
        labels = ['constant', 'payload']
        matrix = build_confusion_matrix(pairs, [], labels)
        
        # constant: 1 TP, 1 FN
        # payload: 1 TP, 1 FP
        # matrix[0][0] = 1 (预测 constant，实际 constant)
        # matrix[1][0] = 1 (预测 payload，实际 constant)
        # matrix[1][1] = 1 (预测 payload，实际 payload)
        assert matrix.matrix == [[1, 0], [1, 1]]
    
    def test_fixed_label_order(self):
        """测试固定标签顺序"""
        pairs = [
            AlignedPair(
                FieldKey("l1", Direction.REQUEST, 0),
                DetectorEvidence('test', 'payload', '', 1.0, True, 'test'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
        ]
        
        # 不同的标签顺序
        labels1 = ['constant', 'payload']
        labels2 = ['payload', 'constant']
        
        matrix1 = build_confusion_matrix(pairs, [], labels1)
        matrix2 = build_confusion_matrix(pairs, [], labels2)
        
        # 矩阵应该不同
        assert matrix1.labels == ['constant', 'payload']
        assert matrix2.labels == ['payload', 'constant']
        
        # matrix1: 预测 payload (index 1), 实际 constant (index 0)
        assert matrix1.matrix == [[0, 0], [1, 0]]
        
        # matrix2: 预测 payload (index 0), 实际 constant (index 1)
        assert matrix2.matrix == [[0, 1], [0, 0]]


class TestGetConfusionMatrixDiagonal:
    """获取对角线测试"""
    
    def test_diagonal(self):
        """测试对角线"""
        matrix = ConfusionMatrix(
            labels=['constant', 'payload', 'timestamp'],
            matrix=[[5, 2, 1], [1, 3, 0], [0, 1, 4]]
        )
        
        diagonal = get_confusion_matrix_diagonal(matrix)
        
        assert diagonal == [5, 3, 4]
    
    def test_zero_diagonal(self):
        """测试零对角线"""
        matrix = ConfusionMatrix(
            labels=['constant', 'payload'],
            matrix=[[0, 5], [3, 0]]
        )
        
        diagonal = get_confusion_matrix_diagonal(matrix)
        
        assert diagonal == [0, 0]


class TestCalculateAccuracyFromMatrix:
    """从矩阵计算准确率测试"""
    
    def test_empty_matrix(self):
        """测试空矩阵"""
        matrix = ConfusionMatrix(
            labels=['constant', 'payload'],
            matrix=[[0, 0], [0, 0]]
        )
        
        accuracy = calculate_accuracy_from_matrix(matrix)
        assert accuracy == 0.0
    
    def test_perfect_accuracy(self):
        """测试完美准确率"""
        matrix = ConfusionMatrix(
            labels=['constant', 'payload'],
            matrix=[[5, 0], [0, 3]]
        )
        
        accuracy = calculate_accuracy_from_matrix(matrix)
        assert accuracy == 1.0
    
    def test_partial_accuracy(self):
        """测试部分准确率"""
        # 总共 10 个，正确 6 个
        matrix = ConfusionMatrix(
            labels=['constant', 'payload'],
            matrix=[[5, 2], [1, 2]]
        )
        
        accuracy = calculate_accuracy_from_matrix(matrix)
        assert accuracy == 0.7  # (5 + 2) / 10
    
    def test_zero_accuracy(self):
        """测试零准确率"""
        matrix = ConfusionMatrix(
            labels=['constant', 'payload'],
            matrix=[[0, 5], [3, 0]]
        )

        accuracy = calculate_accuracy_from_matrix(matrix)
        assert accuracy == 0.0


class TestBuildConfusionMatrixR258:
    """R258：混淆矩阵 unknown 列与多 layout 行为修复测试

    验收：固定矩阵，行为可复现。
    - 旧标签经 normalize_legacy_label 归一化后计入矩阵（不丢弃）
    - unknown 预测/truth 正确计入 unknown 行/列
    - 多 layout、多方向的对聚合到同一矩阵
    - missing prediction（unmatched_truths）计入 unknown 行
    - 相同输入产生相同矩阵（行为可复现）
    """

    def test_legacy_predicted_label_normalized(self):
        """R258：旧标签 'sequence' 预测归一化为 'sequence_or_counter' 后计入矩阵"""
        pairs = [
            AlignedPair(
                FieldKey("l1", Direction.REQUEST, 0),
                DetectorEvidence('test', 'sequence', '', 1.0, True, 'test'),
                GroundTruthRecord(1, 0, 'sequence_or_counter', 1.0, True),
                True
            ),
        ]

        labels = ['constant', 'payload', 'sequence_or_counter', 'unknown']
        matrix = build_confusion_matrix(pairs, [], labels)

        # 预测 'sequence' -> 归一化 'sequence_or_counter' (idx 2)
        # truth 'sequence_or_counter' (idx 2)
        # matrix[2][2] = 1
        assert matrix.matrix[2][2] == 1
        # 其他位置全为 0
        assert matrix.matrix == [
            [0, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 0],
        ]

    def test_legacy_truth_label_normalized(self):
        """R258：truth 旧标签 'type_opcode' 归一化为 'type_control' 后计入矩阵"""
        pairs = [
            AlignedPair(
                FieldKey("l1", Direction.REQUEST, 0),
                DetectorEvidence('test', 'constant', '', 1.0, True, 'test'),
                GroundTruthRecord(1, 0, 'type_opcode', 1.0, True),
                True
            ),
        ]

        labels = ['constant', 'type_control']
        matrix = build_confusion_matrix(pairs, [], labels)

        # 预测 'constant' (idx 0)
        # truth 'type_opcode' -> 归一化 'type_control' (idx 1)
        # matrix[0][1] = 1
        assert matrix.matrix == [[0, 1], [0, 0]]

    def test_unknown_prediction_in_unknown_row(self):
        """R258：预测为 unknown 计入 unknown 行"""
        pairs = [
            AlignedPair(
                FieldKey("l1", Direction.REQUEST, 0),
                DetectorEvidence('test', 'unknown', '', 1.0, True, 'test'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
        ]

        labels = ['constant', 'unknown']
        matrix = build_confusion_matrix(pairs, [], labels)

        # 预测 unknown (idx 1), truth constant (idx 0)
        # matrix[1][0] = 1
        assert matrix.matrix == [[0, 0], [1, 0]]

    def test_unknown_truth_in_unknown_column(self):
        """R258：truth 为 unknown 计入 unknown 列"""
        pairs = [
            AlignedPair(
                FieldKey("l1", Direction.REQUEST, 0),
                DetectorEvidence('test', 'constant', '', 1.0, True, 'test'),
                GroundTruthRecord(1, 0, 'unknown', 1.0, True),
                True
            ),
        ]

        labels = ['constant', 'unknown']
        matrix = build_confusion_matrix(pairs, [], labels)

        # 预测 constant (idx 0), truth unknown (idx 1)
        # matrix[0][1] = 1
        assert matrix.matrix == [[0, 1], [0, 0]]

    def test_multi_layout_aggregated(self):
        """R258：多 layout、多方向的对聚合到同一矩阵"""
        pairs = [
            # layout l1, request, field 0
            AlignedPair(
                FieldKey("l1", Direction.REQUEST, 0),
                DetectorEvidence('test', 'constant', '', 1.0, True, 'test'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
            # layout l2, request, field 0
            AlignedPair(
                FieldKey("l2", Direction.REQUEST, 0),
                DetectorEvidence('test', 'constant', '', 1.0, True, 'test'),
                GroundTruthRecord(2, 0, 'constant', 1.0, True),
                True
            ),
            # layout l1, response, field 1
            AlignedPair(
                FieldKey("l1", Direction.RESPONSE, 1),
                DetectorEvidence('test', 'payload', '', 1.0, True, 'test'),
                GroundTruthRecord(1, 1, 'payload', 1.0, True),
                True
            ),
        ]

        labels = ['constant', 'payload']
        matrix = build_confusion_matrix(pairs, [], labels)

        # 两个 constant 正确 + 一个 payload 正确
        # matrix[0][0] = 2, matrix[1][1] = 1
        assert matrix.matrix == [[2, 0], [0, 1]]

    def test_unmatched_truths_counted_in_unknown_row(self):
        """R258：missing prediction（unmatched_truths）计入 unknown 行

        使矩阵列总和等于 truth 总数，与 Overall Accuracy 分母一致。
        """
        pairs = [
            # 匹配：预测 constant，实际 constant
            AlignedPair(
                FieldKey("l1", Direction.REQUEST, 0),
                DetectorEvidence('test', 'constant', '', 1.0, True, 'test'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
        ]
        # missing prediction：truth 是 payload 但无预测
        unmatched_truths = [
            GroundTruthRecord(2, 1, 'payload', 1.0, True),
        ]

        labels = ['constant', 'payload', 'unknown']
        matrix = build_confusion_matrix(pairs, unmatched_truths, labels)

        # matched: matrix[0][0] = 1 (constant, constant)
        # unmatched: matrix[unknown_idx=2][payload_idx=1] = 1
        assert matrix.matrix == [
            [1, 0, 0],
            [0, 0, 0],
            [0, 1, 0],
        ]

    def test_unmatched_truths_skipped_when_unknown_not_in_labels(self):
        """R258：unknown 不在 labels 时 unmatched_truths 被跳过（向后兼容）"""
        pairs = [
            AlignedPair(
                FieldKey("l1", Direction.REQUEST, 0),
                DetectorEvidence('test', 'constant', '', 1.0, True, 'test'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
        ]
        unmatched_truths = [
            GroundTruthRecord(2, 1, 'payload', 1.0, True),
        ]

        # labels 不含 unknown
        labels = ['constant', 'payload']
        matrix = build_confusion_matrix(pairs, unmatched_truths, labels)

        # unmatched_truths 被跳过，矩阵只统计 matched 对
        assert matrix.matrix == [[1, 0], [0, 0]]

    def test_legacy_label_not_dropped(self):
        """R258：旧标签预测与 truth 在归一化后均计入矩阵，不被丢弃

        场景：预测 'opaque_payload'（旧），truth 'payload'（标准）
        归一化后 predicted='payload', true='payload'，计入对角线。
        """
        pairs = [
            AlignedPair(
                FieldKey("l1", Direction.REQUEST, 0),
                DetectorEvidence('test', 'opaque_payload', '', 1.0, True, 'test'),
                GroundTruthRecord(1, 0, 'payload', 1.0, True),
                True
            ),
        ]

        labels = ['constant', 'payload']
        matrix = build_confusion_matrix(pairs, [], labels)

        # 预测 'opaque_payload' -> 归一化 'payload' (idx 1)
        # truth 'payload' (idx 1)
        # matrix[1][1] = 1
        assert matrix.matrix == [[0, 0], [0, 1]]

    def test_fixed_matrix_reproducible(self):
        """R258：相同输入产生相同矩阵（行为可复现）"""
        pairs = [
            AlignedPair(
                FieldKey("l1", Direction.REQUEST, 0),
                DetectorEvidence('test', 'sequence', '', 1.0, True, 'test'),
                GroundTruthRecord(1, 0, 'sequence_or_counter', 1.0, True),
                True
            ),
            AlignedPair(
                FieldKey("l2", Direction.RESPONSE, 1),
                DetectorEvidence('test', 'unknown', '', 1.0, True, 'test'),
                GroundTruthRecord(2, 1, 'constant', 1.0, True),
                True
            ),
        ]
        unmatched_truths = [
            GroundTruthRecord(3, 2, 'payload', 1.0, True),
        ]

        labels = ['constant', 'payload', 'sequence_or_counter', 'unknown']

        # 构建两次，矩阵应完全一致
        matrix1 = build_confusion_matrix(pairs, unmatched_truths, labels)
        matrix2 = build_confusion_matrix(pairs, unmatched_truths, labels)

        assert matrix1.labels == matrix2.labels
        assert matrix1.matrix == matrix2.matrix

        # 手算验证：
        # pair 1: 预测 'sequence'->'sequence_or_counter' (idx 2), truth 'sequence_or_counter' (idx 2)
        #   matrix[2][2] += 1
        # pair 2: 预测 'unknown' (idx 3), truth 'constant' (idx 0)
        #   matrix[3][0] += 1
        # unmatched: truth 'payload' (idx 1), 计入 unknown 行 (idx 3)
        #   matrix[3][1] += 1
        assert matrix1.matrix == [
            [0, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 1, 0],
            [1, 1, 0, 0],
        ]

    def test_column_sum_equals_truth_count(self):
        """R258：矩阵列总和等于 truth 总数（matched truth + unmatched truth）"""
        pairs = [
            AlignedPair(
                FieldKey("l1", Direction.REQUEST, 0),
                DetectorEvidence('test', 'constant', '', 1.0, True, 'test'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
            AlignedPair(
                FieldKey("l1", Direction.REQUEST, 1),
                DetectorEvidence('test', 'unknown', '', 1.0, True, 'test'),
                GroundTruthRecord(1, 1, 'payload', 1.0, True),
                True
            ),
        ]
        unmatched_truths = [
            GroundTruthRecord(2, 2, 'constant', 1.0, True),
        ]

        labels = ['constant', 'payload', 'unknown']
        matrix = build_confusion_matrix(pairs, unmatched_truths, labels)

        # 列总和：每列的 truth 数量
        # constant 列: pair1 (matched, truth constant) + unmatched (truth constant) = 2
        # payload 列: pair2 (matched, truth payload) = 1
        # unknown 列: 0
        column_sums = [sum(row[i] for row in matrix.matrix) for i in range(len(labels))]
        assert column_sums == [2, 1, 0]
        # 总 truth = 2 (matched) + 1 (unmatched) = 3
        assert sum(column_sums) == 3
