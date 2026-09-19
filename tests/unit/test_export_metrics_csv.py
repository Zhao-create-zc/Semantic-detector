"""Metrics CSV export 测试"""

import pytest
import csv
import tempfile
import os
from pathlib import Path
from semantic_detector.io.exporters import (
    export_per_label_metrics_to_csv,
    export_confusion_matrix_to_csv,
    read_per_label_metrics_from_csv,
    read_confusion_matrix_from_csv,
)
from semantic_detector.evaluation.confusion import (
    LabelMetrics,
    LabelStats,
    ConfusionMatrix,
)


class TestExportPerLabelMetricsToCsv:
    """导出每标签指标到 CSV 测试"""
    
    def test_export_single_label(self):
        """测试导出单个标签"""
        label_metrics = {
            'constant': LabelMetrics(label='constant', precision=0.9, recall=0.85, f1=0.87)
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            output_path = f.name
        
        try:
            export_per_label_metrics_to_csv(label_metrics, output_path)
            
            # 读取并验证
            metrics = read_per_label_metrics_from_csv(output_path)
            
            assert len(metrics) == 1
            assert metrics[0]['label'] == 'constant'
            assert metrics[0]['precision'] == 0.9
            assert metrics[0]['recall'] == 0.85
            assert metrics[0]['f1'] == 0.87
        finally:
            os.unlink(output_path)
    
    def test_export_multiple_labels(self):
        """测试导出多个标签"""
        label_metrics = {
            'constant': LabelMetrics(label='constant', precision=0.9, recall=0.85, f1=0.87),
            'payload': LabelMetrics(label='payload', precision=0.8, recall=0.75, f1=0.77),
            'timestamp': LabelMetrics(label='timestamp', precision=0.95, recall=0.9, f1=0.92),
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            output_path = f.name
        
        try:
            export_per_label_metrics_to_csv(label_metrics, output_path)
            
            metrics = read_per_label_metrics_from_csv(output_path)
            
            assert len(metrics) == 3
            labels = [m['label'] for m in metrics]
            assert 'constant' in labels
            assert 'payload' in labels
            assert 'timestamp' in labels
        finally:
            os.unlink(output_path)
    
    def test_csv_header(self):
        """测试 CSV 表头"""
        label_metrics = {
            'constant': LabelMetrics(label='constant', precision=0.9, recall=0.85, f1=0.87)
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            output_path = f.name
        
        try:
            export_per_label_metrics_to_csv(label_metrics, output_path)
            
            with open(output_path, 'r', encoding='utf-8', newline='') as f:
                reader = csv.reader(f)
                header = next(reader)
            
            assert header == ['label', 'precision', 'recall', 'f1']
        finally:
            os.unlink(output_path)


class TestExportConfusionMatrixToCsv:
    """导出混淆矩阵到 CSV 测试"""
    
    def test_export_simple_matrix(self):
        """测试导出简单矩阵"""
        matrix = ConfusionMatrix(
            labels=['constant', 'payload'],
            matrix=[[5, 2], [1, 3]]
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            output_path = f.name
        
        try:
            export_confusion_matrix_to_csv(matrix, output_path)
            
            labels, matrix_data = read_confusion_matrix_from_csv(output_path)
            
            assert labels == ['constant', 'payload']
            assert matrix_data == [[5, 2], [1, 3]]
        finally:
            os.unlink(output_path)
    
    def test_export_larger_matrix(self):
        """测试导出较大矩阵"""
        matrix = ConfusionMatrix(
            labels=['constant', 'payload', 'timestamp'],
            matrix=[[5, 2, 1], [1, 3, 0], [0, 1, 4]]
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            output_path = f.name
        
        try:
            export_confusion_matrix_to_csv(matrix, output_path)
            
            labels, matrix_data = read_confusion_matrix_from_csv(output_path)
            
            assert labels == ['constant', 'payload', 'timestamp']
            assert matrix_data == [[5, 2, 1], [1, 3, 0], [0, 1, 4]]
        finally:
            os.unlink(output_path)
    
    def test_csv_format(self):
        """测试 CSV 格式"""
        matrix = ConfusionMatrix(
            labels=['constant', 'payload'],
            matrix=[[5, 2], [1, 3]]
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            output_path = f.name
        
        try:
            export_confusion_matrix_to_csv(matrix, output_path)
            
            with open(output_path, 'r', encoding='utf-8', newline='') as f:
                reader = csv.reader(f)
                rows = list(reader)
            
            # 第一行：表头
            assert rows[0] == ['', 'constant', 'payload']
            
            # 第二行：constant 行
            assert rows[1] == ['constant', '5', '2']
            
            # 第三行：payload 行
            assert rows[2] == ['payload', '1', '3']
        finally:
            os.unlink(output_path)


class TestReadPerLabelMetricsFromCsv:
    """从 CSV 读取每标签指标测试"""
    
    def test_read_valid_csv(self):
        """测试读取合法 CSV"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            output_path = f.name
            writer = csv.writer(f)
            writer.writerow(['label', 'precision', 'recall', 'f1'])
            writer.writerow(['constant', '0.9', '0.85', '0.87'])
        
        try:
            metrics = read_per_label_metrics_from_csv(output_path)
            
            assert len(metrics) == 1
            assert metrics[0]['label'] == 'constant'
            assert metrics[0]['precision'] == 0.9
        finally:
            os.unlink(output_path)


class TestReadConfusionMatrixFromCsv:
    """从 CSV 读取混淆矩阵测试"""
    
    def test_read_valid_csv(self):
        """测试读取合法 CSV"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            output_path = f.name
            writer = csv.writer(f)
            writer.writerow(['', 'constant', 'payload'])
            writer.writerow(['constant', '5', '2'])
            writer.writerow(['payload', '1', '3'])
        
        try:
            labels, matrix = read_confusion_matrix_from_csv(output_path)

            assert labels == ['constant', 'payload']
            assert matrix == [[5, 2], [1, 3]]
        finally:
            os.unlink(output_path)


class TestExportPerLabelMetricsR260:
    """R260：per_label_metrics.csv 含 tp/fp/fn 计数列测试

    验收：导出再解析，指标和计数一致。
    """

    def test_export_with_label_stats_tp_fp_fn(self):
        """R260：传入 label_stats，CSV 含 tp/fp/fn 列"""
        label_metrics = {
            'constant': LabelMetrics(label='constant', precision=0.9, recall=0.85, f1=0.87),
        }
        label_stats = {
            'constant': LabelStats(label='constant', tp=9, fp=1, fn=2),
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            output_path = f.name

        try:
            export_per_label_metrics_to_csv(label_metrics, output_path, label_stats)

            with open(output_path, 'r', encoding='utf-8', newline='') as f:
                reader = csv.reader(f)
                header = next(reader)
                row = next(reader)

            # 表头含 tp/fp/fn
            assert header == ['label', 'precision', 'recall', 'f1', 'tp', 'fp', 'fn']
            # 数据行含计数
            assert row == ['constant', '0.9', '0.85', '0.87', '9', '1', '2']
        finally:
            os.unlink(output_path)

    def test_export_without_label_stats_backward_compatible(self):
        """R260：不传 label_stats 时向后兼容（4 列）"""
        label_metrics = {
            'constant': LabelMetrics(label='constant', precision=0.9, recall=0.85, f1=0.87),
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            output_path = f.name

        try:
            export_per_label_metrics_to_csv(label_metrics, output_path)

            with open(output_path, 'r', encoding='utf-8', newline='') as f:
                reader = csv.reader(f)
                header = next(reader)

            # 向后兼容：只有 4 列
            assert header == ['label', 'precision', 'recall', 'f1']
        finally:
            os.unlink(output_path)

    def test_roundtrip_with_tp_fp_fn(self):
        """R260：导出再解析，tp/fp/fn 一致"""
        label_metrics = {
            'constant': LabelMetrics(label='constant', precision=0.9, recall=0.85, f1=0.87),
            'payload': LabelMetrics(label='payload', precision=0.8, recall=0.75, f1=0.77),
        }
        label_stats = {
            'constant': LabelStats(label='constant', tp=9, fp=1, fn=2),
            'payload': LabelStats(label='payload', tp=6, fp=2, fn=2),
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            output_path = f.name

        try:
            export_per_label_metrics_to_csv(label_metrics, output_path, label_stats)
            read_metrics = read_per_label_metrics_from_csv(output_path)

            assert len(read_metrics) == 2
            by_label = {m['label']: m for m in read_metrics}

            # constant
            assert by_label['constant']['tp'] == 9
            assert by_label['constant']['fp'] == 1
            assert by_label['constant']['fn'] == 2
            assert by_label['constant']['precision'] == 0.9

            # payload
            assert by_label['payload']['tp'] == 6
            assert by_label['payload']['fp'] == 2
            assert by_label['payload']['fn'] == 2
        finally:
            os.unlink(output_path)

    def test_precision_matches_tp_fp(self):
        """R260：precision = tp/(tp+fp) 与导出的 precision 一致"""
        tp, fp = 9, 1
        expected_precision = tp / (tp + fp)  # 0.9

        label_metrics = {
            'constant': LabelMetrics(
                label='constant', precision=expected_precision, recall=0.85, f1=0.87
            ),
        }
        label_stats = {
            'constant': LabelStats(label='constant', tp=tp, fp=fp, fn=2),
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            output_path = f.name

        try:
            export_per_label_metrics_to_csv(label_metrics, output_path, label_stats)
            read_metrics = read_per_label_metrics_from_csv(output_path)

            m = read_metrics[0]
            # 计数反推 precision 与导出的 precision 一致
            assert abs(m['precision'] - m['tp'] / (m['tp'] + m['fp'])) < 1e-9
        finally:
            os.unlink(output_path)

    def test_label_stats_missing_label_uses_zero(self):
        """R260：label_stats 中缺少某标签时 tp/fp/fn 为 0"""
        label_metrics = {
            'constant': LabelMetrics(label='constant', precision=0.9, recall=0.85, f1=0.87),
            'payload': LabelMetrics(label='payload', precision=0.8, recall=0.75, f1=0.77),
        }
        # label_stats 缺少 'payload'
        label_stats = {
            'constant': LabelStats(label='constant', tp=9, fp=1, fn=2),
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            output_path = f.name

        try:
            export_per_label_metrics_to_csv(label_metrics, output_path, label_stats)
            read_metrics = read_per_label_metrics_from_csv(output_path)

            by_label = {m['label']: m for m in read_metrics}
            # payload 不在 label_stats 中，tp/fp/fn 为 0
            assert by_label['payload']['tp'] == 0
            assert by_label['payload']['fp'] == 0
            assert by_label['payload']['fn'] == 0
        finally:
            os.unlink(output_path)

    def test_read_csv_without_tp_fp_fn_backward_compatible(self):
        """R260：读取不含 tp/fp/fn 的旧 CSV 向后兼容"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as f:
            output_path = f.name
            writer = csv.writer(f)
            writer.writerow(['label', 'precision', 'recall', 'f1'])
            writer.writerow(['constant', '0.9', '0.85', '0.87'])

        try:
            metrics = read_per_label_metrics_from_csv(output_path)

            assert len(metrics) == 1
            assert metrics[0]['label'] == 'constant'
            assert metrics[0]['precision'] == 0.9
            # 旧 CSV 无 tp/fp/fn
            assert 'tp' not in metrics[0]
            assert 'fp' not in metrics[0]
            assert 'fn' not in metrics[0]
        finally:
            os.unlink(output_path)
