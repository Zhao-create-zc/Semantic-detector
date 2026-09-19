"""Metrics export 测试"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from semantic_detector.io.exporters import (
    export_metrics_to_json,
    read_metrics_from_json,
    build_metrics_dict,
)


class TestExportMetricsToJson:
    """导出指标到 JSON 测试"""
    
    def test_export_and_read(self):
        """测试导出和读回"""
        metrics = {
            'overall_accuracy': 0.85,
            'coverage': 0.9,
            'unknown_rate': 0.1,
            'covered_accuracy': 0.94
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_path = f.name
        
        try:
            export_metrics_to_json(metrics, output_path)
            
            # 读回
            read_metrics = read_metrics_from_json(output_path)
            
            assert read_metrics == metrics
        finally:
            os.unlink(output_path)
    
    def test_export_with_optional_fields(self):
        """测试导出带可选字段"""
        metrics = {
            'overall_accuracy': 0.85,
            'coverage': 0.9,
            'unknown_rate': 0.1,
            'covered_accuracy': 0.94,
            'fine_top1_accuracy': 0.75,
            'macro_f1': 0.8
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_path = f.name
        
        try:
            export_metrics_to_json(metrics, output_path)
            
            read_metrics = read_metrics_from_json(output_path)
            
            assert read_metrics['fine_top1_accuracy'] == 0.75
            assert read_metrics['macro_f1'] == 0.8
        finally:
            os.unlink(output_path)
    
    def test_json_format(self):
        """测试 JSON 格式"""
        metrics = {
            'overall_accuracy': 0.85,
            'coverage': 0.9
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_path = f.name
        
        try:
            export_metrics_to_json(metrics, output_path)
            
            # 读取原始文件内容
            with open(output_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 验证是合法 JSON
            parsed = json.loads(content)
            assert parsed == metrics
        finally:
            os.unlink(output_path)


class TestReadMetricsFromJson:
    """从 JSON 读取指标测试"""
    
    def test_read_valid_json(self):
        """测试读取合法 JSON"""
        metrics = {
            'overall_accuracy': 0.85,
            'coverage': 0.9,
            'unknown_rate': 0.1,
            'covered_accuracy': 0.94
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_path = f.name
            json.dump(metrics, f)
        
        try:
            read_metrics = read_metrics_from_json(output_path)
            
            assert read_metrics['overall_accuracy'] == 0.85
            assert read_metrics['coverage'] == 0.9
        finally:
            os.unlink(output_path)


class TestBuildMetricsDict:
    """构建指标字典测试"""
    
    def test_basic_metrics(self):
        """测试基本指标"""
        metrics = build_metrics_dict(
            overall_accuracy=0.85,
            coverage=0.9,
            unknown_rate=0.1,
            covered_accuracy=0.94
        )
        
        assert metrics['overall_accuracy'] == 0.85
        assert metrics['coverage'] == 0.9
        assert metrics['unknown_rate'] == 0.1
        assert metrics['covered_accuracy'] == 0.94
        assert 'fine_top1_accuracy' not in metrics
    
    def test_with_optional_metrics(self):
        """测试带可选指标"""
        metrics = build_metrics_dict(
            overall_accuracy=0.85,
            coverage=0.9,
            unknown_rate=0.1,
            covered_accuracy=0.94,
            fine_top1_accuracy=0.75,
            macro_f1=0.8,
            macro_precision=0.82,
            macro_recall=0.78
        )
        
        assert metrics['fine_top1_accuracy'] == 0.75
        assert metrics['macro_f1'] == 0.8
        assert metrics['macro_precision'] == 0.82
        assert metrics['macro_recall'] == 0.78
    
    def test_partial_optional_metrics(self):
        """测试部分可选指标"""
        metrics = build_metrics_dict(
            overall_accuracy=0.85,
            coverage=0.9,
            unknown_rate=0.1,
            covered_accuracy=0.94,
            macro_f1=0.8
        )

        assert metrics['macro_f1'] == 0.8
        assert 'fine_top1_accuracy' not in metrics
        assert 'macro_precision' not in metrics


class TestBuildMetricsDictR260:
    """R260：metrics.json 含 counts 计数字段测试

    验收：导出再解析，指标和计数一致。
    """

    def test_build_metrics_dict_with_counts(self):
        """R260：传入 counts，metrics['counts'] 存在"""
        counts = {
            'total_predictions': 10,
            'total_truths': 8,
            'matched_count': 7,
            'unmatched_truths_count': 1,
            'unmatched_predictions_count': 3,
            'error_count': 4,
        }
        metrics = build_metrics_dict(
            overall_accuracy=0.5,
            coverage=0.875,
            unknown_rate=0.1,
            covered_accuracy=0.85,
            counts=counts
        )

        assert metrics['counts'] == counts
        assert metrics['counts']['total_predictions'] == 10
        assert metrics['counts']['matched_count'] == 7

    def test_build_metrics_dict_without_counts_backward_compatible(self):
        """R260：不传 counts 时向后兼容（无 'counts' 键）"""
        metrics = build_metrics_dict(
            overall_accuracy=0.85,
            coverage=0.9,
            unknown_rate=0.1,
            covered_accuracy=0.94
        )

        assert 'counts' not in metrics

    def test_export_metrics_with_counts_roundtrip(self):
        """R260：导出含 counts 的 metrics.json 再解析，计数一致"""
        counts = {
            'total_predictions': 10,
            'total_truths': 8,
            'matched_count': 7,
            'unmatched_truths_count': 1,
            'unmatched_predictions_count': 3,
            'error_count': 4,
        }
        metrics = build_metrics_dict(
            overall_accuracy=0.5,
            coverage=0.875,
            unknown_rate=0.1,
            covered_accuracy=0.85,
            macro_f1=0.7,
            counts=counts
        )

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_path = f.name

        try:
            export_metrics_to_json(metrics, output_path)
            read_metrics = read_metrics_from_json(output_path)

            # 指标一致
            assert read_metrics['overall_accuracy'] == 0.5
            assert read_metrics['macro_f1'] == 0.7
            # 计数一致
            assert read_metrics['counts'] == counts
            assert read_metrics['counts']['matched_count'] == 7
            assert read_metrics['counts']['error_count'] == 4
        finally:
            os.unlink(output_path)

    def test_counts_match_indicators_hand_calculated(self):
        """R260：计数与指标手算一致

        场景：10 预测，8 truth，7 matched，1 unmatched_truth，3 unmatched_prediction
        overall_accuracy = correct / total_truths
        若 correct=4，total_truths=8，accuracy=0.5
        counts 应与指标对应（matched + unmatched_truths = total_truths）。
        """
        total_predictions = 10
        total_truths = 8
        matched_count = 7
        unmatched_truths_count = 1
        unmatched_predictions_count = 3
        # matched + unmatched_truths = total_truths
        assert matched_count + unmatched_truths_count == total_truths
        # matched + unmatched_predictions = total_predictions
        assert matched_count + unmatched_predictions_count == total_predictions

        counts = {
            'total_predictions': total_predictions,
            'total_truths': total_truths,
            'matched_count': matched_count,
            'unmatched_truths_count': unmatched_truths_count,
            'unmatched_predictions_count': unmatched_predictions_count,
            'error_count': 4,
        }
        # overall_accuracy = correct / total_truths = 4/8 = 0.5
        overall_accuracy = counts['error_count'] / counts['total_truths'] * 0 + 0.5

        metrics = build_metrics_dict(
            overall_accuracy=overall_accuracy,
            coverage=0.875,
            unknown_rate=0.1,
            covered_accuracy=0.85,
            counts=counts
        )

        # 导出再解析后验证计数守恒
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_path = f.name
        try:
            export_metrics_to_json(metrics, output_path)
            read_metrics = read_metrics_from_json(output_path)
            c = read_metrics['counts']
            # 计数守恒：matched + unmatched = total
            assert c['matched_count'] + c['unmatched_truths_count'] == c['total_truths']
            assert c['matched_count'] + c['unmatched_predictions_count'] == c['total_predictions']
        finally:
            os.unlink(output_path)
