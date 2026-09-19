"""Evaluation errors 测试"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from semantic_detector.contracts import DetectorEvidence, FieldKey, Direction
from semantic_detector.evaluation.ground_truth import GroundTruthRecord
from semantic_detector.evaluation.metrics import (
    AlignedPair,
    EvaluationError,
    collect_errors,
    export_errors_to_jsonl,
)


class TestEvaluationError:
    """EvaluationError 数据类测试"""

    def test_create_error(self):
        """测试创建错误记录"""
        field_key = FieldKey("l1", "r", 0)
        error = EvaluationError(
            field_key=field_key,
            error_type='wrong_label',
            predicted_label='payload',
            true_label='constant',
            confidence=0.9
        )

        assert error.field_key == field_key
        assert error.error_type == 'wrong_label'
        assert error.predicted_label == 'payload'
        assert error.true_label == 'constant'
        assert error.confidence == 0.9


class TestCollectErrors:
    """收集错误测试"""

    def test_empty_inputs(self):
        """测试空输入"""
        errors = collect_errors([], [])
        assert errors == []

    def test_no_errors(self):
        """测试无错误"""
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('test', 'constant', '', 1.0, True, 'test'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
        ]

        errors = collect_errors(pairs, [])
        assert errors == []

    def test_wrong_label_error(self):
        """测试分类错误（wrong_label）"""
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('test', 'payload', '', 0.9, True, 'test'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
        ]

        errors = collect_errors(pairs, [])

        assert len(errors) == 1
        assert errors[0].error_type == 'wrong_label'
        assert errors[0].predicted_label == 'payload'
        assert errors[0].true_label == 'constant'
        assert errors[0].confidence == 0.9

    def test_missing_prediction_error(self):
        """测试漏检错误（missing_prediction）"""
        unmatched_truths = [
            GroundTruthRecord(1, 0, 'constant', 1.0, True),
        ]

        errors = collect_errors([], unmatched_truths)

        assert len(errors) == 1
        assert errors[0].error_type == 'missing_prediction'
        assert errors[0].predicted_label == 'none'
        assert errors[0].true_label == 'constant'
        assert errors[0].confidence == 0.0

    def test_mixed_errors(self):
        """测试混合错误"""
        pairs = [
            # 正确预测
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('test', 'constant', '', 1.0, True, 'test'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
            # 错误预测
            AlignedPair(
                FieldKey("l1", "r", 1),
                DetectorEvidence('test', 'payload', '', 0.9, True, 'test'),
                GroundTruthRecord(2, 1, 'constant', 1.0, True),
                True
            ),
        ]

        unmatched_truths = [
            GroundTruthRecord(3, 2, 'timestamp', 1.0, True),
        ]

        errors = collect_errors(pairs, unmatched_truths)

        assert len(errors) == 2

        # 第一个错误是分类错误
        wrong_errors = [e for e in errors if e.error_type == 'wrong_label']
        assert len(wrong_errors) == 1

        # 第二个错误是漏检
        missing_errors = [e for e in errors if e.error_type == 'missing_prediction']
        assert len(missing_errors) == 1

    def test_field_key_tracking(self):
        """测试 FieldKey 追踪"""
        pairs = [
            AlignedPair(
                FieldKey("layout1", "request", 5),
                DetectorEvidence('test', 'payload', '', 0.9, True, 'test'),
                GroundTruthRecord(1, 5, 'constant', 1.0, True),
                True
            ),
        ]

        errors = collect_errors(pairs, [])

        assert len(errors) == 1
        assert errors[0].field_key.layout_id == "layout1"
        assert errors[0].field_key.direction == Direction.REQUEST
        assert errors[0].field_key.field_index == 5


class TestCollectErrorsR259:
    """R259：四类错误分类测试

    验收：wrong/abstained/missing/unexpected，每条带 FieldKey 与 evidence。
    """

    def test_wrong_label_with_evidence(self):
        """R259：wrong_label 错误带 FieldKey 与 evidence"""
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('const_det', 'payload', 'payload_v1', 0.9, True, 'rc_low'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True, fine_label='const_v1'),
                True
            ),
        ]

        errors = collect_errors(pairs, [])

        assert len(errors) == 1
        err = errors[0]
        assert err.error_type == 'wrong_label'
        assert err.predicted_label == 'payload'
        assert err.true_label == 'constant'
        assert err.confidence == 0.9
        # FieldKey
        assert err.field_key == FieldKey("l1", "r", 0)
        # evidence
        assert err.details['evidence']['detector'] == 'const_det'
        assert err.details['evidence']['reason_code'] == 'rc_low'
        assert err.details['evidence']['score'] == 0.9
        assert err.details['evidence']['fine_label'] == 'payload_v1'
        # truth
        assert err.details['truth']['semantic_label'] == 'constant'
        assert err.details['truth']['confidence'] == 1.0
        assert err.details['truth']['fine_label'] == 'const_v1'

    def test_abstained_prediction(self):
        """R259：预测为 unknown 分类为 abstained（而非 wrong_label）"""
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('unk_det', 'unknown', '', 0.3, True, 'no_match'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
        ]

        errors = collect_errors(pairs, [])

        assert len(errors) == 1
        err = errors[0]
        assert err.error_type == 'abstained'
        assert err.predicted_label == 'unknown'
        assert err.true_label == 'constant'
        assert err.confidence == 0.3
        assert err.details['evidence']['detector'] == 'unk_det'
        assert err.details['evidence']['reason_code'] == 'no_match'

    def test_missing_prediction_with_truth_field_key(self):
        """R259：missing_prediction 用 truth 完整 FieldKey（非 'unknown' 占位）"""
        unmatched_truths = [
            GroundTruthRecord(
                1, 2, 'timestamp', 1.0, True,
                layout_id='layout_a', direction='response'
            ),
        ]

        errors = collect_errors([], unmatched_truths)

        assert len(errors) == 1
        err = errors[0]
        assert err.error_type == 'missing_prediction'
        assert err.predicted_label == 'none'
        assert err.true_label == 'timestamp'
        # 用 truth 完整 FieldKey，不是 'unknown' 占位
        assert err.field_key.layout_id == 'layout_a'
        assert err.field_key.direction == Direction.RESPONSE
        assert err.field_key.field_index == 2
        # evidence 为 None（无预测）
        assert err.details['evidence'] is None
        assert err.details['truth']['semantic_label'] == 'timestamp'
        assert err.details['truth']['truth_id'] == 1

    def test_unexpected_prediction(self):
        """R259：有预测无 truth 分类为 unexpected_prediction"""
        # 用 DetectorEvidence 携带 details 中的身份信息
        unmatched_predictions = [
            DetectorEvidence(
                'extra_det', 'payload', 'payload_v2', 0.8, True, 'extra',
                details={'field_index': 3, 'layout_id': 'l1', 'direction': 'request'}
            ),
        ]

        errors = collect_errors([], [], unmatched_predictions)

        assert len(errors) == 1
        err = errors[0]
        assert err.error_type == 'unexpected_prediction'
        assert err.predicted_label == 'payload'
        assert err.true_label == 'none'
        assert err.confidence == 0.8
        # FieldKey 从 prediction 提取
        assert err.field_key.layout_id == 'l1'
        assert err.field_key.direction == Direction.REQUEST
        assert err.field_key.field_index == 3
        # evidence 来自预测
        assert err.details['evidence']['detector'] == 'extra_det'
        assert err.details['evidence']['reason_code'] == 'extra'
        # truth 为 None
        assert err.details['truth'] is None

    def test_unexpected_prediction_no_field_key(self):
        """R259：无法提取 FieldKey 的预测用占位 FieldKey"""
        unmatched_predictions = [
            DetectorEvidence('det', 'payload', '', 0.5, True, 'rc'),
            # 无 details，无法提取 field_index
        ]

        errors = collect_errors([], [], unmatched_predictions)

        assert len(errors) == 1
        err = errors[0]
        assert err.error_type == 'unexpected_prediction'
        assert err.field_key.layout_id == 'unknown'
        assert err.field_key.direction == Direction.UNKNOWN
        assert err.field_key.field_index == 0  # R417：field_index>=0（FieldKey 校验）

    def test_all_four_error_types(self):
        """R259：四类错误同时存在"""
        pairs = [
            # wrong_label：预测 payload 实际 constant
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('det', 'payload', '', 0.9, True, 'rc'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
            # abstained：预测 unknown 实际 timestamp
            AlignedPair(
                FieldKey("l1", "r", 1),
                DetectorEvidence('det', 'unknown', '', 0.2, True, 'rc'),
                GroundTruthRecord(2, 1, 'timestamp', 1.0, True),
                True
            ),
            # 正确预测（不产生错误）
            AlignedPair(
                FieldKey("l1", "r", 2),
                DetectorEvidence('det', 'constant', '', 1.0, True, 'rc'),
                GroundTruthRecord(3, 2, 'constant', 1.0, True),
                True
            ),
        ]
        unmatched_truths = [
            # missing_prediction：有 truth 无预测
            GroundTruthRecord(4, 3, 'length', 1.0, True),
        ]
        unmatched_predictions = [
            # unexpected_prediction：有预测无 truth
            DetectorEvidence(
                'det', 'string', '', 0.7, True, 'rc',
                details={'field_index': 4, 'layout_id': 'l1', 'direction': 'request'}
            ),
        ]

        errors = collect_errors(pairs, unmatched_truths, unmatched_predictions)

        # 四类各一个
        error_types = sorted(e.error_type for e in errors)
        assert error_types == [
            'abstained',
            'missing_prediction',
            'unexpected_prediction',
            'wrong_label',
        ]

    def test_legacy_label_normalized_in_wrong_label(self):
        """R259：wrong_label 标签归一化（旧标签 'sequence' -> 'sequence_or_counter'）"""
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('det', 'sequence', '', 0.9, True, 'rc'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
        ]

        errors = collect_errors(pairs, [])

        assert len(errors) == 1
        err = errors[0]
        assert err.error_type == 'wrong_label'
        # 'sequence' 归一化为 'sequence_or_counter'
        assert err.predicted_label == 'sequence_or_counter'
        assert err.true_label == 'constant'

    def test_correct_prediction_no_error(self):
        """R259：正确预测不产生错误（含旧标签归一化后匹配）"""
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('det', 'sequence', '', 0.9, True, 'rc'),
                GroundTruthRecord(1, 0, 'sequence_or_counter', 1.0, True),
                True
            ),
        ]

        errors = collect_errors(pairs, [])
        assert errors == []

    def test_backward_compatible_without_unmatched_predictions(self):
        """R259：不传 unmatched_predictions 时向后兼容（不收集 unexpected）"""
        pairs = [
            AlignedPair(
                FieldKey("l1", "r", 0),
                DetectorEvidence('det', 'payload', '', 0.9, True, 'rc'),
                GroundTruthRecord(1, 0, 'constant', 1.0, True),
                True
            ),
        ]
        unmatched_truths = [
            GroundTruthRecord(2, 1, 'timestamp', 1.0, True),
        ]

        # 不传第三个参数
        errors = collect_errors(pairs, unmatched_truths)

        # 只有 wrong_label 和 missing_prediction
        error_types = sorted(e.error_type for e in errors)
        assert error_types == ['missing_prediction', 'wrong_label']


class TestExportErrorsToJsonl:
    """导出错误到 JSONL 测试"""

    def test_export_single_error(self):
        """测试导出单个错误"""
        errors = [
            EvaluationError(
                FieldKey("l1", "r", 0),
                'wrong_label',
                'payload',
                'constant',
                0.9
            )
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            output_path = f.name

        try:
            export_errors_to_jsonl(errors, output_path)

            # 读取并验证
            with open(output_path, 'r', encoding='utf-8') as f:
                line = f.readline()
                data = json.loads(line)

            assert data['error_type'] == 'wrong_label'
            assert data['predicted_label'] == 'payload'
            assert data['true_label'] == 'constant'
            assert data['confidence'] == 0.9
            assert data['field_key']['layout_id'] == 'l1'
            assert data['field_key']['direction'] == 'r'
            assert data['field_key']['field_index'] == 0
        finally:
            os.unlink(output_path)

    def test_export_multiple_errors(self):
        """测试导出多个错误"""
        errors = [
            EvaluationError(
                FieldKey("l1", "r", 0),
                'wrong_label',
                'payload',
                'constant',
                0.9
            ),
            EvaluationError(
                FieldKey("l1", "r", 1),
                'missing_prediction',
                'none',
                'timestamp',
                0.0
            )
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            output_path = f.name

        try:
            export_errors_to_jsonl(errors, output_path)

            # 读取并验证
            with open(output_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            assert len(lines) == 2

            data1 = json.loads(lines[0])
            data2 = json.loads(lines[1])

            assert data1['error_type'] == 'wrong_label'
            assert data2['error_type'] == 'missing_prediction'
        finally:
            os.unlink(output_path)

    def test_jsonl_format(self):
        """测试 JSONL 格式"""
        errors = [
            EvaluationError(
                FieldKey("l1", "r", 0),
                'wrong_label',
                'payload',
                'constant',
                0.9,
                details={'reason': 'low_confidence'}
            )
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            output_path = f.name

        try:
            export_errors_to_jsonl(errors, output_path)

            # 读取原始内容
            with open(output_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 验证每行是合法 JSON
            lines = content.strip().split('\n')
            for line in lines:
                data = json.loads(line)
                assert 'field_key' in data
                assert 'error_type' in data
                assert 'predicted_label' in data
                assert 'true_label' in data
                assert 'confidence' in data
        finally:
            os.unlink(output_path)

    def test_export_with_evidence_details(self):
        """R259：导出含 evidence 的 details"""
        errors = [
            EvaluationError(
                FieldKey("l1", "r", 0),
                'wrong_label',
                'payload',
                'constant',
                0.9,
                details={
                    'evidence': {
                        'detector': 'det',
                        'reason_code': 'rc',
                        'score': 0.9,
                    },
                    'truth': {
                        'semantic_label': 'constant',
                        'confidence': 1.0,
                    }
                }
            ),
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            output_path = f.name

        try:
            export_errors_to_jsonl(errors, output_path)

            with open(output_path, 'r', encoding='utf-8') as f:
                data = json.loads(f.readline())

            assert data['details']['evidence']['detector'] == 'det'
            assert data['details']['evidence']['reason_code'] == 'rc'
            assert data['details']['truth']['semantic_label'] == 'constant'
        finally:
            os.unlink(output_path)
