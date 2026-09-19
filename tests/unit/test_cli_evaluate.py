"""CLI evaluate 测试"""

import pytest
import tempfile
import os
import json
import csv
from pathlib import Path
from semantic_detector.cli import main
from semantic_detector.contracts import DetectorEvidence, SemanticPrediction, Direction
from semantic_detector.io.exporters import export_predictions_to_jsonl
from semantic_detector.evaluation.ground_truth import GroundTruthRecord


class TestCliEvaluate:
    """CLI evaluate 测试"""
    
    def test_evaluate_basic(self):
        """测试基本评估"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建预测文件
            predictions = [
                DetectorEvidence('test', 'constant', '', 1.0, True, 'test', details={'field_index': 0}),
                DetectorEvidence('test', 'payload', '', 1.0, True, 'test', details={'field_index': 1}),
            ]
            predictions_path = os.path.join(tmpdir, 'predictions.jsonl')
            export_predictions_to_jsonl(predictions, predictions_path)
            
            # 创建真值文件
            truths = [
                {'truth_id': 1, 'field_index': 0, 'semantic_type': 'constant', 'confidence': 1.0, 'is_hard_evidence': True},
                {'truth_id': 2, 'field_index': 1, 'semantic_type': 'payload', 'confidence': 1.0, 'is_hard_evidence': True},
            ]
            truth_path = os.path.join(tmpdir, 'truth.jsonl')
            with open(truth_path, 'w', encoding='utf-8') as f:
                for truth in truths:
                    f.write(json.dumps(truth) + '\n')
            
            # 运行 evaluate
            exit_code = main(['evaluate', predictions_path, truth_path])
            
            assert exit_code == 0
            
            # 检查输出文件
            metrics_path = os.path.join(tmpdir, 'metrics.json')
            assert os.path.exists(metrics_path)
            
            with open(metrics_path, 'r', encoding='utf-8') as f:
                metrics = json.load(f)
            
            assert 'overall_accuracy' in metrics
            assert 'coverage' in metrics
            assert metrics['overall_accuracy'] == 1.0
    
    def test_evaluate_with_errors(self):
        """测试带错误的评估"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建预测文件（预测错误）
            predictions = [
                DetectorEvidence('test', 'payload', '', 1.0, True, 'test', details={'field_index': 0}),
                DetectorEvidence('test', 'constant', '', 1.0, True, 'test', details={'field_index': 1}),
            ]
            predictions_path = os.path.join(tmpdir, 'predictions.jsonl')
            export_predictions_to_jsonl(predictions, predictions_path)
            
            # 创建真值文件
            truths = [
                {'truth_id': 1, 'field_index': 0, 'semantic_type': 'constant', 'confidence': 1.0, 'is_hard_evidence': True},
                {'truth_id': 2, 'field_index': 1, 'semantic_type': 'payload', 'confidence': 1.0, 'is_hard_evidence': True},
            ]
            truth_path = os.path.join(tmpdir, 'truth.jsonl')
            with open(truth_path, 'w', encoding='utf-8') as f:
                for truth in truths:
                    f.write(json.dumps(truth) + '\n')
            
            # 运行 evaluate
            exit_code = main(['evaluate', predictions_path, truth_path])
            
            assert exit_code == 0
            
            # 检查错误文件
            errors_path = os.path.join(tmpdir, 'errors.jsonl')
            assert os.path.exists(errors_path)
    
    def test_evaluate_missing_predictions_file(self):
        """测试缺失预测文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            truth_path = os.path.join(tmpdir, 'truth.jsonl')
            with open(truth_path, 'w', encoding='utf-8') as f:
                f.write('{}\n')
            
            exit_code = main(['evaluate', 'nonexistent.jsonl', truth_path])
            
            assert exit_code == 2
    
    def test_evaluate_missing_truth_file(self):
        """测试缺失真值文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            predictions_path = os.path.join(tmpdir, 'predictions.jsonl')
            with open(predictions_path, 'w', encoding='utf-8') as f:
                f.write('{}\n')
            
            exit_code = main(['evaluate', predictions_path, 'nonexistent.jsonl'])
            
            assert exit_code == 2
    
    def test_evaluate_output_files(self):
        """测试输出文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建预测文件
            predictions = [
                DetectorEvidence('test', 'constant', '', 1.0, True, 'test', details={'field_index': 0}),
            ]
            predictions_path = os.path.join(tmpdir, 'predictions.jsonl')
            export_predictions_to_jsonl(predictions, predictions_path)
            
            # 创建真值文件
            truths = [
                {'truth_id': 1, 'field_index': 0, 'semantic_type': 'constant', 'confidence': 1.0, 'is_hard_evidence': True},
            ]
            truth_path = os.path.join(tmpdir, 'truth.jsonl')
            with open(truth_path, 'w', encoding='utf-8') as f:
                for truth in truths:
                    f.write(json.dumps(truth) + '\n')
            
            # 运行 evaluate
            exit_code = main(['evaluate', predictions_path, truth_path])
            
            assert exit_code == 0
            
            # 检查所有输出文件
            assert os.path.exists(os.path.join(tmpdir, 'metrics.json'))
            assert os.path.exists(os.path.join(tmpdir, 'per_label_metrics.csv'))
            assert os.path.exists(os.path.join(tmpdir, 'confusion_matrix.csv'))


def _make_semantic_prediction(field_index, coarse_label, confidence=1.0,
                              layout_id='default', direction=Direction.REQUEST):
    """构造 SemanticPrediction 辅助函数（R261/R262 测试用）"""
    return SemanticPrediction(
        run_id='test-run',
        layout_id=layout_id,
        direction=direction,
        field_index=field_index,
        coarse_label=coarse_label,
        fine_label='',
        confidence=confidence,
        abstained=False,
        evidence=(DetectorEvidence('test', coarse_label, '', confidence, True, 'test', details={}),),
        alternatives=(),
        prediction_status='confirmed',
    )


def _write_truth_jsonl(truth_path, entries):
    """写入 ground truth JSONL（每条含 layout_id/direction 形成完整 FieldKey）"""
    with open(truth_path, 'w', encoding='utf-8') as f:
        for entry in entries:
            f.write(json.dumps(entry) + '\n')


class TestCliEvaluateR261:
    """R261：evaluate CLI 接入真实 SemanticPrediction importer 端到端测试

    验收：合成 SemanticPrediction predictions/truth，生成 metrics、per-label、
    confusion、errors 四类输出，数值正确，向后兼容旧 DetectorEvidence 格式。
    """

    def test_evaluate_semantic_prediction_all_correct(self):
        """R261：SemanticPrediction 全对，metrics.json 含 counts，准确率 1.0"""
        with tempfile.TemporaryDirectory() as tmpdir:
            predictions = [
                _make_semantic_prediction(0, 'constant'),
                _make_semantic_prediction(1, 'payload'),
                _make_semantic_prediction(2, 'timestamp'),
            ]
            predictions_path = os.path.join(tmpdir, 'predictions.jsonl')
            export_predictions_to_jsonl(predictions, predictions_path)

            truths = [
                {'truth_id': 1, 'field_index': 0, 'semantic_type': 'constant',
                 'confidence': 1.0, 'is_hard_evidence': True,
                 'layout_id': 'default', 'direction': 'request'},
                {'truth_id': 2, 'field_index': 1, 'semantic_type': 'payload',
                 'confidence': 1.0, 'is_hard_evidence': True,
                 'layout_id': 'default', 'direction': 'request'},
                {'truth_id': 3, 'field_index': 2, 'semantic_type': 'timestamp',
                 'confidence': 1.0, 'is_hard_evidence': True,
                 'layout_id': 'default', 'direction': 'request'},
            ]
            truth_path = os.path.join(tmpdir, 'truth.jsonl')
            _write_truth_jsonl(truth_path, truths)

            exit_code = main(['evaluate', predictions_path, truth_path])
            assert exit_code == 0

            # metrics.json 含 counts 计数字段
            with open(os.path.join(tmpdir, 'metrics.json'), 'r', encoding='utf-8') as f:
                metrics = json.load(f)
            assert metrics['overall_accuracy'] == 1.0
            assert metrics['coverage'] == 1.0
            assert 'counts' in metrics
            counts = metrics['counts']
            assert counts['total_predictions'] == 3
            assert counts['total_truths'] == 3
            assert counts['matched_count'] == 3
            assert counts['unmatched_truths_count'] == 0
            assert counts['unmatched_predictions_count'] == 0
            assert counts['error_count'] == 0

    def test_evaluate_semantic_prediction_wrong_label_generates_errors(self):
        """R261：SemanticPrediction 含一个错标，errors.jsonl 含 wrong_label"""
        with tempfile.TemporaryDirectory() as tmpdir:
            predictions = [
                _make_semantic_prediction(0, 'constant'),
                _make_semantic_prediction(1, 'constant'),  # 错：truth 是 payload
            ]
            predictions_path = os.path.join(tmpdir, 'predictions.jsonl')
            export_predictions_to_jsonl(predictions, predictions_path)

            truths = [
                {'truth_id': 1, 'field_index': 0, 'semantic_type': 'constant',
                 'confidence': 1.0, 'is_hard_evidence': True,
                 'layout_id': 'default', 'direction': 'request'},
                {'truth_id': 2, 'field_index': 1, 'semantic_type': 'payload',
                 'confidence': 1.0, 'is_hard_evidence': True,
                 'layout_id': 'default', 'direction': 'request'},
            ]
            truth_path = os.path.join(tmpdir, 'truth.jsonl')
            _write_truth_jsonl(truth_path, truths)

            exit_code = main(['evaluate', predictions_path, truth_path])
            assert exit_code == 0

            # errors.jsonl 存在且含 wrong_label
            errors_path = os.path.join(tmpdir, 'errors.jsonl')
            assert os.path.exists(errors_path)
            with open(errors_path, 'r', encoding='utf-8') as f:
                errors = [json.loads(line) for line in f if line.strip()]
            assert len(errors) == 1
            assert errors[0]['error_type'] == 'wrong_label'
            assert errors[0]['predicted_label'] == 'constant'
            assert errors[0]['true_label'] == 'payload'

            # counts 守恒：error_count == 1
            with open(os.path.join(tmpdir, 'metrics.json'), 'r', encoding='utf-8') as f:
                metrics = json.load(f)
            assert metrics['counts']['error_count'] == 1
            assert metrics['overall_accuracy'] == 0.5

    def test_evaluate_semantic_prediction_generates_all_four_outputs(self):
        """R261：生成 metrics、per-label、confusion、errors 四类输出"""
        with tempfile.TemporaryDirectory() as tmpdir:
            predictions = [
                _make_semantic_prediction(0, 'constant'),
                _make_semantic_prediction(1, 'payload'),  # 错：truth 是 timestamp
            ]
            predictions_path = os.path.join(tmpdir, 'predictions.jsonl')
            export_predictions_to_jsonl(predictions, predictions_path)

            truths = [
                {'truth_id': 1, 'field_index': 0, 'semantic_type': 'constant',
                 'confidence': 1.0, 'is_hard_evidence': True,
                 'layout_id': 'default', 'direction': 'request'},
                {'truth_id': 2, 'field_index': 1, 'semantic_type': 'timestamp',
                 'confidence': 1.0, 'is_hard_evidence': True,
                 'layout_id': 'default', 'direction': 'request'},
            ]
            truth_path = os.path.join(tmpdir, 'truth.jsonl')
            _write_truth_jsonl(truth_path, truths)

            exit_code = main(['evaluate', predictions_path, truth_path])
            assert exit_code == 0

            # 四类输出全部生成
            assert os.path.exists(os.path.join(tmpdir, 'metrics.json'))
            assert os.path.exists(os.path.join(tmpdir, 'per_label_metrics.csv'))
            assert os.path.exists(os.path.join(tmpdir, 'confusion_matrix.csv'))
            assert os.path.exists(os.path.join(tmpdir, 'errors.jsonl'))

            # per_label_metrics.csv 含 tp/fp/fn 列（R260）
            with open(os.path.join(tmpdir, 'per_label_metrics.csv'), 'r', encoding='utf-8', newline='') as f:
                reader = csv.reader(f)
                header = next(reader)
            assert 'tp' in header
            assert 'fp' in header
            assert 'fn' in header

            # confusion_matrix.csv 可读回
            with open(os.path.join(tmpdir, 'confusion_matrix.csv'), 'r', encoding='utf-8', newline='') as f:
                reader = csv.reader(f)
                rows = list(reader)
            assert len(rows) >= 2  # 表头 + 至少一行

    def test_evaluate_backward_compatible_old_detector_evidence_format(self):
        """R261：旧 DetectorEvidence 格式通过 KeyError 回退仍可评价"""
        with tempfile.TemporaryDirectory() as tmpdir:
            predictions = [
                DetectorEvidence('test', 'constant', '', 1.0, True, 'test',
                                 details={'field_index': 0}),
            ]
            predictions_path = os.path.join(tmpdir, 'predictions.jsonl')
            export_predictions_to_jsonl(predictions, predictions_path)

            truths = [
                {'truth_id': 1, 'field_index': 0, 'semantic_type': 'constant',
                 'confidence': 1.0, 'is_hard_evidence': True},
            ]
            truth_path = os.path.join(tmpdir, 'truth.jsonl')
            _write_truth_jsonl(truth_path, truths)

            exit_code = main(['evaluate', predictions_path, truth_path])
            assert exit_code == 0

            with open(os.path.join(tmpdir, 'metrics.json'), 'r', encoding='utf-8') as f:
                metrics = json.load(f)
            assert metrics['overall_accuracy'] == 1.0
            # 旧格式无 FieldKey，但 details 含 field_index，对齐仍可工作
            assert metrics['counts']['matched_count'] == 1


class TestCliEvaluateR262:
    """R262：删除 evaluate 中固定 default/request 逻辑回归测试

    验收：同文件含多 layout/方向，匹配数正确（不塌缩到 default/request）。
    """

    def test_multi_layout_direction_matched_correctly(self):
        """R262：同文件含 4 个不同 (layout, direction, field_index) 组合，全部匹配"""
        with tempfile.TemporaryDirectory() as tmpdir:
            predictions = [
                _make_semantic_prediction(0, 'constant',
                                          layout_id='layout_a', direction=Direction.REQUEST),
                _make_semantic_prediction(0, 'payload',
                                          layout_id='layout_a', direction=Direction.RESPONSE),
                _make_semantic_prediction(1, 'timestamp',
                                          layout_id='layout_b', direction=Direction.REQUEST),
                _make_semantic_prediction(1, 'length',
                                          layout_id='layout_b', direction=Direction.RESPONSE),
            ]
            predictions_path = os.path.join(tmpdir, 'predictions.jsonl')
            export_predictions_to_jsonl(predictions, predictions_path)

            truths = [
                {'truth_id': 1, 'field_index': 0, 'semantic_type': 'constant',
                 'confidence': 1.0, 'is_hard_evidence': True,
                 'layout_id': 'layout_a', 'direction': 'request'},
                {'truth_id': 2, 'field_index': 0, 'semantic_type': 'payload',
                 'confidence': 1.0, 'is_hard_evidence': True,
                 'layout_id': 'layout_a', 'direction': 'response'},
                {'truth_id': 3, 'field_index': 1, 'semantic_type': 'timestamp',
                 'confidence': 1.0, 'is_hard_evidence': True,
                 'layout_id': 'layout_b', 'direction': 'request'},
                {'truth_id': 4, 'field_index': 1, 'semantic_type': 'length',
                 'confidence': 1.0, 'is_hard_evidence': True,
                 'layout_id': 'layout_b', 'direction': 'response'},
            ]
            truth_path = os.path.join(tmpdir, 'truth.jsonl')
            _write_truth_jsonl(truth_path, truths)

            exit_code = main(['evaluate', predictions_path, truth_path])
            assert exit_code == 0

            with open(os.path.join(tmpdir, 'metrics.json'), 'r', encoding='utf-8') as f:
                metrics = json.load(f)

            counts = metrics['counts']
            # 4 个不同 FieldKey 全部匹配（非塌缩到 default/request）
            assert counts['total_predictions'] == 4
            assert counts['total_truths'] == 4
            assert counts['matched_count'] == 4
            assert counts['unmatched_truths_count'] == 0
            assert counts['unmatched_predictions_count'] == 0
            assert metrics['overall_accuracy'] == 1.0

    def test_same_field_index_different_direction_not_collapsed(self):
        """R262：同 layout 同 field_index 但方向不同，视为两个不同 FieldKey

        若固定 default/request，则 layout_a/field_index=0 的 request 和 response
        会被错误合并为 1 个匹配。此处验证二者独立匹配。
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            predictions = [
                _make_semantic_prediction(0, 'constant',
                                          layout_id='layout_a', direction=Direction.REQUEST),
                _make_semantic_prediction(0, 'payload',
                                          layout_id='layout_a', direction=Direction.RESPONSE),
            ]
            predictions_path = os.path.join(tmpdir, 'predictions.jsonl')
            export_predictions_to_jsonl(predictions, predictions_path)

            truths = [
                {'truth_id': 1, 'field_index': 0, 'semantic_type': 'constant',
                 'confidence': 1.0, 'is_hard_evidence': True,
                 'layout_id': 'layout_a', 'direction': 'request'},
                {'truth_id': 2, 'field_index': 0, 'semantic_type': 'payload',
                 'confidence': 1.0, 'is_hard_evidence': True,
                 'layout_id': 'layout_a', 'direction': 'response'},
            ]
            truth_path = os.path.join(tmpdir, 'truth.jsonl')
            _write_truth_jsonl(truth_path, truths)

            exit_code = main(['evaluate', predictions_path, truth_path])
            assert exit_code == 0

            with open(os.path.join(tmpdir, 'metrics.json'), 'r', encoding='utf-8') as f:
                metrics = json.load(f)

            counts = metrics['counts']
            # request 和 response 是两个独立 FieldKey，匹配数为 2（非 1）
            assert counts['matched_count'] == 2
            assert metrics['overall_accuracy'] == 1.0

    def test_mismatched_layout_results_in_unmatched(self):
        """R262：layout_id 不匹配时预测落入 unmatched，不误匹配到 default"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 预测用 layout_x，真值用 layout_y（FieldKey 不匹配）
            predictions = [
                _make_semantic_prediction(0, 'constant',
                                          layout_id='layout_x', direction=Direction.REQUEST),
            ]
            predictions_path = os.path.join(tmpdir, 'predictions.jsonl')
            export_predictions_to_jsonl(predictions, predictions_path)

            truths = [
                {'truth_id': 1, 'field_index': 0, 'semantic_type': 'constant',
                 'confidence': 1.0, 'is_hard_evidence': True,
                 'layout_id': 'layout_y', 'direction': 'request'},
            ]
            truth_path = os.path.join(tmpdir, 'truth.jsonl')
            _write_truth_jsonl(truth_path, truths)

            exit_code = main(['evaluate', predictions_path, truth_path])
            assert exit_code == 0

            with open(os.path.join(tmpdir, 'metrics.json'), 'r', encoding='utf-8') as f:
                metrics = json.load(f)

            counts = metrics['counts']
            # layout 不匹配：matched=0，unmatched_predictions=1，unmatched_truths=1
            assert counts['matched_count'] == 0
            assert counts['unmatched_predictions_count'] == 1
            assert counts['unmatched_truths_count'] == 1


class TestCliEvaluateCorruptedGroundTruthR334:
    """R334：新增损坏 Ground Truth 的 CLI 失败测试（HIGH-3 阶段 B 首轮）

    06 计划 R334 验收规则：
    - 复现"1 条合法 + 1 条损坏 JSON 仍返回 0"的问题
    - 修复前测试失败，并明确断言：
      - return_code != 0
      - rejected_ground_truth.jsonl 存在
      - 正式 metrics 不得被当作完整结果

    HIGH-3 核心缺陷：read_ground_truth_jsonl 返回 (valid, rejected)，
    但 cmd_evaluate 完全忽略 rejected_truths，直接用 valid 继续计算 metrics
    并返回 0，导致损坏行被静默丢弃，metrics 被当作完整结果。

    本测试类在 R334 阶段（修复前）应全部失败，断言当前行为不符合验收规则。
    R335-R337 将修复生产代码使这些测试通过。
    """

    def test_corrupted_truth_returns_nonzero_exit_code(self):
        """R334: 1 条合法 + 1 条损坏 JSON 时返回码 != 0

        当前缺陷：cmd_evaluate 忽略 rejected_truths，返回 0。
        验收要求：return_code != 0（损坏行存在时不得成功退出）。
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            predictions = [
                _make_semantic_prediction(0, 'constant'),
                _make_semantic_prediction(1, 'payload'),
            ]
            predictions_path = os.path.join(tmpdir, 'predictions.jsonl')
            export_predictions_to_jsonl(predictions, predictions_path)

            # 1 条合法 + 1 条损坏 JSON（语法错误）
            truth_path = os.path.join(tmpdir, 'truth.jsonl')
            with open(truth_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps({
                    'truth_id': 1, 'field_index': 0, 'semantic_type': 'constant',
                    'confidence': 1.0, 'is_hard_evidence': True,
                    'layout_id': 'default', 'direction': 'request',
                }) + '\n')
                # 损坏行：缺少闭合花括号
                f.write('{"truth_id": 2, "field_index": 1, "semantic_type": "payload"\n')

            exit_code = main(['evaluate', predictions_path, truth_path])

            # 验收要求：return_code != 0
            assert exit_code != 0, (
                f"损坏 Ground Truth 存在时应返回非零退出码，实际: {exit_code}"
            )

    def test_corrupted_truth_produces_rejected_ground_truth_jsonl(self):
        """R334: 损坏行应导出到 rejected_ground_truth.jsonl

        当前缺陷：cmd_evaluate 不导出 rejected_ground_truth.jsonl。
        验收要求：rejected_ground_truth.jsonl 存在。
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            predictions = [
                _make_semantic_prediction(0, 'constant'),
            ]
            predictions_path = os.path.join(tmpdir, 'predictions.jsonl')
            export_predictions_to_jsonl(predictions, predictions_path)

            # 1 条合法 + 1 条损坏 JSON
            truth_path = os.path.join(tmpdir, 'truth.jsonl')
            with open(truth_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps({
                    'truth_id': 1, 'field_index': 0, 'semantic_type': 'constant',
                    'confidence': 1.0, 'is_hard_evidence': True,
                    'layout_id': 'default', 'direction': 'request',
                }) + '\n')
                # 损坏行：JSON 语法错误
                f.write('{invalid json without quotes}\n')

            main(['evaluate', predictions_path, truth_path])

            rejected_path = os.path.join(tmpdir, 'rejected_ground_truth.jsonl')
            assert os.path.exists(rejected_path), (
                "rejected_ground_truth.jsonl 应存在，记录被拒绝的损坏行"
            )

    def test_corrupted_truth_metrics_not_treated_as_complete(self):
        """R334: 损坏行存在时正式 metrics 不得被当作完整结果

        当前缺陷：metrics.json 正常生成，counts.total_truths 只计合法行，
        被当作完整结果。
        验收要求：metrics 应明确标记为不完整（如含 rejected_count 或
        incomplete 标记），或不得生成正式 metrics。
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            predictions = [
                _make_semantic_prediction(0, 'constant'),
                _make_semantic_prediction(1, 'payload'),
            ]
            predictions_path = os.path.join(tmpdir, 'predictions.jsonl')
            export_predictions_to_jsonl(predictions, predictions_path)

            # 1 条合法 + 1 条损坏 JSON
            truth_path = os.path.join(tmpdir, 'truth.jsonl')
            with open(truth_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps({
                    'truth_id': 1, 'field_index': 0, 'semantic_type': 'constant',
                    'confidence': 1.0, 'is_hard_evidence': True,
                    'layout_id': 'default', 'direction': 'request',
                }) + '\n')
                # 损坏行：field_index 为负数（语义校验失败）
                f.write(json.dumps({
                    'truth_id': 2, 'field_index': -1, 'semantic_type': 'payload',
                    'confidence': 1.0, 'is_hard_evidence': True,
                    'layout_id': 'default', 'direction': 'request',
                }) + '\n')

            main(['evaluate', predictions_path, truth_path])

            metrics_path = os.path.join(tmpdir, 'metrics.json')
            assert os.path.exists(metrics_path), "metrics.json 应存在（可能含不完整标记）"
            with open(metrics_path, 'r', encoding='utf-8') as f:
                metrics = json.load(f)

            # 验收要求：metrics 不得被当作完整结果
            # 应包含 rejected_count 或 incomplete 标记，或 total_truths 反映原始总数
            # R336：cmd_evaluate 在 counts 中写 rejected_ground_truth_count
            has_rejected_marker = (
                'rejected_count' in metrics
                or 'incomplete' in metrics
                or metrics.get('counts', {}).get('rejected_ground_truth_count', 0) > 0
            )
            assert has_rejected_marker, (
                "损坏行存在时 metrics 应明确标记为不完整（含 rejected_count 或 incomplete），"
                f"实际 metrics: {metrics}"
            )

    def test_validation_error_truth_returns_nonzero_exit_code(self):
        """R334: 语义校验失败（如 duplicate field_key）时返回码 != 0

        当前缺陷：validate_ground_truth 返回 rejected_validation，
        但 cmd_evaluate 忽略它，返回 0。
        验收要求：return_code != 0。
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            predictions = [
                _make_semantic_prediction(0, 'constant'),
            ]
            predictions_path = os.path.join(tmpdir, 'predictions.jsonl')
            export_predictions_to_jsonl(predictions, predictions_path)

            # 2 条相同 FieldKey（duplicate field_key 语义校验失败）
            truth_path = os.path.join(tmpdir, 'truth.jsonl')
            with open(truth_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps({
                    'truth_id': 1, 'field_index': 0, 'semantic_type': 'constant',
                    'confidence': 1.0, 'is_hard_evidence': True,
                    'layout_id': 'default', 'direction': 'request',
                }) + '\n')
                f.write(json.dumps({
                    'truth_id': 2, 'field_index': 0, 'semantic_type': 'constant',
                    'confidence': 1.0, 'is_hard_evidence': True,
                    'layout_id': 'default', 'direction': 'request',
                }) + '\n')

            exit_code = main(['evaluate', predictions_path, truth_path])

            # 验收要求：return_code != 0
            assert exit_code != 0, (
                f"语义校验失败（duplicate field_key）时应返回非零退出码，实际: {exit_code}"
            )


class TestCliEvaluateRejectedGroundTruthExportR336:
    """R336：Evaluate 导出 rejected_ground_truth.jsonl

    验收：
    - 文件每行可解析；
    - 无拒绝时写空文件，防止旧文件残留；
    - JSON 解析拒绝与验证拒绝都被包含；
    - 数量写入 metrics。
    """

    def test_rejected_file_each_line_parseable(self):
        """R336: rejected_ground_truth.jsonl 每行可解析为 JSON"""
        with tempfile.TemporaryDirectory() as tmpdir:
            predictions = [
                _make_semantic_prediction(0, 'constant'),
            ]
            predictions_path = os.path.join(tmpdir, 'predictions.jsonl')
            export_predictions_to_jsonl(predictions, predictions_path)

            # 1 合法 + 1 损坏 JSON（read 阶段拒绝）
            truth_path = os.path.join(tmpdir, 'truth.jsonl')
            with open(truth_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps({
                    'truth_id': 1, 'field_index': 0, 'semantic_type': 'constant',
                    'confidence': 1.0, 'is_hard_evidence': True,
                    'layout_id': 'default', 'direction': 'request',
                }) + '\n')
                f.write('{invalid json}\n')

            main(['evaluate', predictions_path, truth_path])

            rejected_path = os.path.join(tmpdir, 'rejected_ground_truth.jsonl')
            assert os.path.exists(rejected_path)
            with open(rejected_path, 'r', encoding='utf-8') as f:
                lines = [line for line in f if line.strip()]
            # 每行可解析为 JSON
            for line in lines:
                parsed = json.loads(line)
                assert isinstance(parsed, dict)
                assert 'stage' in parsed
                assert 'reason_code' in parsed
                assert 'message' in parsed

    def test_no_rejection_writes_empty_file_clearing_old(self):
        """R336: 无拒绝时写空文件，防止旧 rejected_ground_truth.jsonl 残留"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 预先写入一个旧的 rejected_ground_truth.jsonl（模拟残留）
            old_rejected_path = os.path.join(tmpdir, 'rejected_ground_truth.jsonl')
            with open(old_rejected_path, 'w', encoding='utf-8') as f:
                f.write('{"old": "stale record that should be cleared"}\n')

            predictions = [
                _make_semantic_prediction(0, 'constant'),
            ]
            predictions_path = os.path.join(tmpdir, 'predictions.jsonl')
            export_predictions_to_jsonl(predictions, predictions_path)

            # 全部合法 truth，无拒绝
            truth_path = os.path.join(tmpdir, 'truth.jsonl')
            with open(truth_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps({
                    'truth_id': 1, 'field_index': 0, 'semantic_type': 'constant',
                    'confidence': 1.0, 'is_hard_evidence': True,
                    'layout_id': 'default', 'direction': 'request',
                }) + '\n')

            main(['evaluate', predictions_path, truth_path])

            # 文件应被清空（空文件），无残留
            assert os.path.exists(old_rejected_path)
            with open(old_rejected_path, 'r', encoding='utf-8') as f:
                content = f.read()
            assert content == '', f"无拒绝时文件应为空，实际: {content!r}"

    def test_both_read_and_validate_rejections_included(self):
        """R336: JSON 解析拒绝（read）与验证拒绝（validate）都被包含"""
        with tempfile.TemporaryDirectory() as tmpdir:
            predictions = [
                _make_semantic_prediction(0, 'constant'),
            ]
            predictions_path = os.path.join(tmpdir, 'predictions.jsonl')
            export_predictions_to_jsonl(predictions, predictions_path)

            # 1 损坏 JSON（read 拒绝）+ 2 条 duplicate field_key（validate 拒绝）
            truth_path = os.path.join(tmpdir, 'truth.jsonl')
            with open(truth_path, 'w', encoding='utf-8') as f:
                # read 阶段拒绝：损坏 JSON
                f.write('{invalid json}\n')
                # 两条相同 FieldKey（validate 阶段拒绝第二条）
                f.write(json.dumps({
                    'truth_id': 1, 'field_index': 0, 'semantic_type': 'constant',
                    'confidence': 1.0, 'is_hard_evidence': True,
                    'layout_id': 'default', 'direction': 'request',
                }) + '\n')
                f.write(json.dumps({
                    'truth_id': 2, 'field_index': 0, 'semantic_type': 'constant',
                    'confidence': 1.0, 'is_hard_evidence': True,
                    'layout_id': 'default', 'direction': 'request',
                }) + '\n')

            main(['evaluate', predictions_path, truth_path])

            rejected_path = os.path.join(tmpdir, 'rejected_ground_truth.jsonl')
            with open(rejected_path, 'r', encoding='utf-8') as f:
                rejected = [json.loads(line) for line in f if line.strip()]

            # read 拒绝 + validate 拒绝都被包含
            stages = {r['stage'] for r in rejected}
            assert 'read' in stages, f"应包含 read 阶段拒绝，实际 stages: {stages}"
            assert 'validate' in stages, f"应包含 validate 阶段拒绝，实际 stages: {stages}"
            # read 拒绝的 reason_code
            read_rejections = [r for r in rejected if r['stage'] == 'read']
            assert any(r['reason_code'] == 'invalid_json' for r in read_rejections)
            # validate 拒绝的 reason_code
            validate_rejections = [r for r in rejected if r['stage'] == 'validate']
            assert any(r['reason_code'] == 'duplicate_field_key' for r in validate_rejections)

    def test_rejected_count_written_to_metrics(self):
        """R336: rejected_ground_truth_count 写入 metrics.counts"""
        with tempfile.TemporaryDirectory() as tmpdir:
            predictions = [
                _make_semantic_prediction(0, 'constant'),
            ]
            predictions_path = os.path.join(tmpdir, 'predictions.jsonl')
            export_predictions_to_jsonl(predictions, predictions_path)

            # 1 合法 + 2 损坏（read + validate）
            truth_path = os.path.join(tmpdir, 'truth.jsonl')
            with open(truth_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps({
                    'truth_id': 1, 'field_index': 0, 'semantic_type': 'constant',
                    'confidence': 1.0, 'is_hard_evidence': True,
                    'layout_id': 'default', 'direction': 'request',
                }) + '\n')
                f.write('{invalid json}\n')  # read 拒绝
                f.write(json.dumps({  # validate 拒绝（duplicate field_key）
                    'truth_id': 2, 'field_index': 0, 'semantic_type': 'constant',
                    'confidence': 1.0, 'is_hard_evidence': True,
                    'layout_id': 'default', 'direction': 'request',
                }) + '\n')

            main(['evaluate', predictions_path, truth_path])

            with open(os.path.join(tmpdir, 'metrics.json'), 'r', encoding='utf-8') as f:
                metrics = json.load(f)
            assert metrics['counts']['rejected_ground_truth_count'] == 2, (
                f"rejected_ground_truth_count 应为 2（1 read + 1 validate），"
                f"实际: {metrics['counts']['rejected_ground_truth_count']}"
            )


class TestCliEvaluateFailClosedR337:
    """R337：Evaluate 默认 fail closed

    验收：
    - rejected_ground_truth_count > 0 → exit code 1
    - metrics.status = "invalid_ground_truth"
    - metrics.valid_for_reporting = false
    - 无拒绝时 status = "ok", valid_for_reporting = true, exit 0
    """

    def test_rejected_truth_returns_exit_code_1(self):
        """R337: 存在被拒绝的 Ground Truth 时返回退出码 1"""
        with tempfile.TemporaryDirectory() as tmpdir:
            predictions = [
                _make_semantic_prediction(0, 'constant'),
            ]
            predictions_path = os.path.join(tmpdir, 'predictions.jsonl')
            export_predictions_to_jsonl(predictions, predictions_path)

            truth_path = os.path.join(tmpdir, 'truth.jsonl')
            with open(truth_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps({
                    'truth_id': 1, 'field_index': 0, 'semantic_type': 'constant',
                    'confidence': 1.0, 'is_hard_evidence': True,
                    'layout_id': 'default', 'direction': 'request',
                }) + '\n')
                f.write('{invalid json}\n')

            exit_code = main(['evaluate', predictions_path, truth_path])
            assert exit_code == 1, (
                f"存在被拒绝的 Ground Truth 时应返回 1，实际: {exit_code}"
            )

    def test_metrics_status_invalid_ground_truth_when_rejected(self):
        """R337: metrics.status = invalid_ground_truth 当存在拒绝时"""
        with tempfile.TemporaryDirectory() as tmpdir:
            predictions = [
                _make_semantic_prediction(0, 'constant'),
            ]
            predictions_path = os.path.join(tmpdir, 'predictions.jsonl')
            export_predictions_to_jsonl(predictions, predictions_path)

            truth_path = os.path.join(tmpdir, 'truth.jsonl')
            with open(truth_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps({
                    'truth_id': 1, 'field_index': 0, 'semantic_type': 'constant',
                    'confidence': 1.0, 'is_hard_evidence': True,
                    'layout_id': 'default', 'direction': 'request',
                }) + '\n')
                f.write('{invalid json}\n')

            main(['evaluate', predictions_path, truth_path])

            with open(os.path.join(tmpdir, 'metrics.json'), 'r', encoding='utf-8') as f:
                metrics = json.load(f)
            assert metrics['status'] == 'invalid_ground_truth', (
                f"status 应为 invalid_ground_truth，实际: {metrics.get('status')}"
            )

    def test_metrics_valid_for_reporting_false_when_rejected(self):
        """R337: metrics.valid_for_reporting = false 当存在拒绝时"""
        with tempfile.TemporaryDirectory() as tmpdir:
            predictions = [
                _make_semantic_prediction(0, 'constant'),
            ]
            predictions_path = os.path.join(tmpdir, 'predictions.jsonl')
            export_predictions_to_jsonl(predictions, predictions_path)

            # duplicate field_key（validate 阶段拒绝）
            truth_path = os.path.join(tmpdir, 'truth.jsonl')
            with open(truth_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps({
                    'truth_id': 1, 'field_index': 0, 'semantic_type': 'constant',
                    'confidence': 1.0, 'is_hard_evidence': True,
                    'layout_id': 'default', 'direction': 'request',
                }) + '\n')
                f.write(json.dumps({
                    'truth_id': 2, 'field_index': 0, 'semantic_type': 'constant',
                    'confidence': 1.0, 'is_hard_evidence': True,
                    'layout_id': 'default', 'direction': 'request',
                }) + '\n')

            main(['evaluate', predictions_path, truth_path])

            with open(os.path.join(tmpdir, 'metrics.json'), 'r', encoding='utf-8') as f:
                metrics = json.load(f)
            assert metrics['valid_for_reporting'] is False, (
                f"valid_for_reporting 应为 false，实际: {metrics.get('valid_for_reporting')}"
            )

    def test_no_rejection_status_ok_valid_for_reporting_true_exit_0(self):
        """R337: 无拒绝时 status=ok, valid_for_reporting=true, exit 0"""
        with tempfile.TemporaryDirectory() as tmpdir:
            predictions = [
                _make_semantic_prediction(0, 'constant'),
            ]
            predictions_path = os.path.join(tmpdir, 'predictions.jsonl')
            export_predictions_to_jsonl(predictions, predictions_path)

            truth_path = os.path.join(tmpdir, 'truth.jsonl')
            with open(truth_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps({
                    'truth_id': 1, 'field_index': 0, 'semantic_type': 'constant',
                    'confidence': 1.0, 'is_hard_evidence': True,
                    'layout_id': 'default', 'direction': 'request',
                }) + '\n')

            exit_code = main(['evaluate', predictions_path, truth_path])
            assert exit_code == 0

            with open(os.path.join(tmpdir, 'metrics.json'), 'r', encoding='utf-8') as f:
                metrics = json.load(f)
            assert metrics['status'] == 'ok'
            assert metrics['valid_for_reporting'] is True


class TestCliEvaluatePartialGroundTruthR338:
    """R338：显式 partial Ground Truth 模式

    验收：
    - 默认失败（无 --allow-partial-ground-truth 时 rejected → exit 1）
    - 显式 partial 继续（有 --allow-partial-ground-truth 且有合法子集 → exit 0 + partial_ground_truth=true）
    - 全部真值无效时，即使 partial 也必须失败（exit 1）
    """

    def test_default_fails_when_rejected(self):
        """R338: 默认（无 --allow-partial-ground-truth）rejected → exit 1"""
        with tempfile.TemporaryDirectory() as tmpdir:
            predictions = [
                _make_semantic_prediction(0, 'constant'),
            ]
            predictions_path = os.path.join(tmpdir, 'predictions.jsonl')
            export_predictions_to_jsonl(predictions, predictions_path)

            truth_path = os.path.join(tmpdir, 'truth.jsonl')
            with open(truth_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps({
                    'truth_id': 1, 'field_index': 0, 'semantic_type': 'constant',
                    'confidence': 1.0, 'is_hard_evidence': True,
                    'layout_id': 'default', 'direction': 'request',
                }) + '\n')
                f.write('{invalid json}\n')

            # 默认不传 --allow-partial-ground-truth
            exit_code = main(['evaluate', predictions_path, truth_path])
            assert exit_code == 1, (
                f"默认模式 rejected 应返回 1，实际: {exit_code}"
            )

    def test_partial_mode_continues_with_legal_subset(self):
        """R338: --allow-partial-ground-truth + 有合法子集 → exit 0 + partial_ground_truth=true"""
        with tempfile.TemporaryDirectory() as tmpdir:
            predictions = [
                _make_semantic_prediction(0, 'constant'),
            ]
            predictions_path = os.path.join(tmpdir, 'predictions.jsonl')
            export_predictions_to_jsonl(predictions, predictions_path)

            # 1 合法 + 1 损坏 JSON
            truth_path = os.path.join(tmpdir, 'truth.jsonl')
            with open(truth_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps({
                    'truth_id': 1, 'field_index': 0, 'semantic_type': 'constant',
                    'confidence': 1.0, 'is_hard_evidence': True,
                    'layout_id': 'default', 'direction': 'request',
                }) + '\n')
                f.write('{invalid json}\n')

            exit_code = main([
                'evaluate', predictions_path, truth_path,
                '--allow-partial-ground-truth',
            ])
            assert exit_code == 0, (
                f"partial 模式 + 有合法子集应返回 0，实际: {exit_code}"
            )

            with open(os.path.join(tmpdir, 'metrics.json'), 'r', encoding='utf-8') as f:
                metrics = json.load(f)
            assert metrics['status'] == 'partial_ground_truth', (
                f"status 应为 partial_ground_truth，实际: {metrics.get('status')}"
            )
            assert metrics['valid_for_reporting'] is False, (
                f"valid_for_reporting 应为 false，实际: {metrics.get('valid_for_reporting')}"
            )
            assert metrics.get('partial_ground_truth') is True, (
                f"partial_ground_truth 应为 true，实际: {metrics.get('partial_ground_truth')}"
            )
            assert metrics['counts']['rejected_ground_truth_count'] == 1

    def test_partial_mode_all_invalid_still_fails(self):
        """R338: --allow-partial-ground-truth 但全部真值无效 → exit 1"""
        with tempfile.TemporaryDirectory() as tmpdir:
            predictions = [
                _make_semantic_prediction(0, 'constant'),
            ]
            predictions_path = os.path.join(tmpdir, 'predictions.jsonl')
            export_predictions_to_jsonl(predictions, predictions_path)

            # 全部损坏（无合法真值）
            truth_path = os.path.join(tmpdir, 'truth.jsonl')
            with open(truth_path, 'w', encoding='utf-8') as f:
                f.write('{invalid json 1}\n')
                f.write('{invalid json 2}\n')

            exit_code = main([
                'evaluate', predictions_path, truth_path,
                '--allow-partial-ground-truth',
            ])
            assert exit_code == 1, (
                f"全部真值无效时即使 partial 也应返回 1，实际: {exit_code}"
            )

            with open(os.path.join(tmpdir, 'metrics.json'), 'r', encoding='utf-8') as f:
                metrics = json.load(f)
            # 全部无效时 status 仍为 invalid_ground_truth（未进入 partial 评价路径）
            assert metrics['status'] == 'invalid_ground_truth'
            assert metrics['valid_for_reporting'] is False


class TestCliEvaluateRewriteAllOutputsR339:
    """R339：修复评价旧 errors 产物残留

    每次 evaluate 都重写本命令拥有的 5 个文件：
    metrics.json / per_label_metrics.csv / confusion_matrix.csv /
    errors.jsonl / rejected_ground_truth.jsonl

    验收：第一次有 errors，第二次 0 error → 第二次 errors.jsonl 必须为空，
    不得保留第一次内容。
    """

    def test_errors_jsonl_rewritten_to_empty_on_second_run(self):
        """R339: 第一次有 errors，第二次 0 error → errors.jsonl 必须为空"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 第一次：1 错标 prediction → 1 error
            predictions_v1 = [
                _make_semantic_prediction(0, 'constant'),
                _make_semantic_prediction(1, 'constant'),  # 错：truth 是 payload
            ]
            predictions_path = os.path.join(tmpdir, 'predictions.jsonl')
            export_predictions_to_jsonl(predictions_v1, predictions_path)

            truths = [
                {'truth_id': 1, 'field_index': 0, 'semantic_type': 'constant',
                 'confidence': 1.0, 'is_hard_evidence': True,
                 'layout_id': 'default', 'direction': 'request'},
                {'truth_id': 2, 'field_index': 1, 'semantic_type': 'payload',
                 'confidence': 1.0, 'is_hard_evidence': True,
                 'layout_id': 'default', 'direction': 'request'},
            ]
            truth_path = os.path.join(tmpdir, 'truth.jsonl')
            _write_truth_jsonl(truth_path, truths)

            main(['evaluate', predictions_path, truth_path])

            errors_path = os.path.join(tmpdir, 'errors.jsonl')
            assert os.path.exists(errors_path)
            with open(errors_path, 'r', encoding='utf-8') as f:
                first_run_lines = [line for line in f if line.strip()]
            assert len(first_run_lines) == 1, (
                f"第一次应有 1 个 error，实际: {len(first_run_lines)}"
            )

            # 第二次：全对 prediction → 0 error
            predictions_v2 = [
                _make_semantic_prediction(0, 'constant'),
                _make_semantic_prediction(1, 'payload'),
            ]
            export_predictions_to_jsonl(predictions_v2, predictions_path)

            main(['evaluate', predictions_path, truth_path])

            with open(errors_path, 'r', encoding='utf-8') as f:
                second_run_content = f.read()
            assert second_run_content == '', (
                f"第二次 0 error 时 errors.jsonl 应为空，实际: {second_run_content!r}"
            )

    def test_all_five_outputs_rewritten_on_each_run(self):
        """R339: 5 个文件每次都被重写（无残留）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 预先写入 5 个旧文件（模拟残留）
            stale_files = [
                'metrics.json', 'per_label_metrics.csv', 'confusion_matrix.csv',
                'errors.jsonl', 'rejected_ground_truth.jsonl',
            ]
            for fname in stale_files:
                with open(os.path.join(tmpdir, fname), 'w', encoding='utf-8') as f:
                    f.write('STALE CONTENT FROM PREVIOUS RUN\n')

            predictions = [
                _make_semantic_prediction(0, 'constant'),
            ]
            predictions_path = os.path.join(tmpdir, 'predictions.jsonl')
            export_predictions_to_jsonl(predictions, predictions_path)

            truths = [
                {'truth_id': 1, 'field_index': 0, 'semantic_type': 'constant',
                 'confidence': 1.0, 'is_hard_evidence': True,
                 'layout_id': 'default', 'direction': 'request'},
            ]
            truth_path = os.path.join(tmpdir, 'truth.jsonl')
            _write_truth_jsonl(truth_path, truths)

            main(['evaluate', predictions_path, truth_path])

            # 5 个文件都不应含 STALE CONTENT
            for fname in stale_files:
                fpath = os.path.join(tmpdir, fname)
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()
                assert 'STALE CONTENT' not in content, (
                    f"{fname} 应被重写，但仍含 STALE CONTENT: {content!r}"
                )

            # errors.jsonl 和 rejected_ground_truth.jsonl 应为空（无 error 无 rejected）
            assert open(os.path.join(tmpdir, 'errors.jsonl'), 'r', encoding='utf-8').read() == ''
            assert open(os.path.join(tmpdir, 'rejected_ground_truth.jsonl'), 'r', encoding='utf-8').read() == ''
