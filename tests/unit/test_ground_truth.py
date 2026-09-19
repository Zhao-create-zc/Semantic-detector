"""Ground truth JSONL 解析测试

R249：新增完整 FieldKey 测试（layout_id/direction/field_index/semantic_label）。
"""

import pytest
import tempfile
import os
from semantic_detector.evaluation.ground_truth import (
    GroundTruthRecord,
    read_ground_truth_jsonl,
    validate_ground_truth,
)


class TestGroundTruthRecord:
    """Ground truth 记录测试"""

    def test_valid_record(self):
        """测试有效记录"""
        record = GroundTruthRecord(
            truth_id=1,
            field_index=0,
            semantic_label='constant',
            confidence=1.0,
            is_hard_evidence=True
        )

        assert record.truth_id == 1
        assert record.field_index == 0
        assert record.semantic_label == 'constant'
        assert record.confidence == 1.0
        assert record.is_hard_evidence is True

    def test_invalid_confidence(self):
        """测试无效 confidence"""
        with pytest.raises(ValueError):
            GroundTruthRecord(
                truth_id=1,
                field_index=0,
                semantic_label='constant',
                confidence=1.5,
                is_hard_evidence=True
            )

    def test_invalid_truth_id(self):
        """测试无效 truth_id"""
        with pytest.raises(ValueError):
            GroundTruthRecord(
                truth_id=0,
                field_index=0,
                semantic_label='constant',
                confidence=1.0,
                is_hard_evidence=True
            )

    def test_invalid_field_index(self):
        """测试无效 field_index"""
        with pytest.raises(ValueError):
            GroundTruthRecord(
                truth_id=1,
                field_index=-1,
                semantic_label='constant',
                confidence=1.0,
                is_hard_evidence=True
            )


class TestGroundTruthRecordFieldKey:
    """R249: GroundTruthRecord 完整 FieldKey 测试

    03 教程 12.1 / 04 任务表 R249：
    - truth 可生成完整 FieldKey (layout_id, direction, field_index)
    - 合法与缺字段
    """

    def test_record_with_full_fieldkey(self):
        """含完整 FieldKey 的记录。"""
        record = GroundTruthRecord(
            truth_id=1,
            field_index=2,
            semantic_label='length',
            confidence=1.0,
            is_hard_evidence=True,
            layout_id='layout_read',
            direction='request',
        )

        assert record.layout_id == 'layout_read'
        assert record.direction == 'request'
        assert record.field_index == 2

    def test_field_key_property(self):
        """field_key 属性返回 FieldKey 对象。"""
        from semantic_detector.contracts import FieldKey, Direction

        record = GroundTruthRecord(
            truth_id=1,
            field_index=3,
            semantic_label='timestamp',
            confidence=1.0,
            is_hard_evidence=True,
            layout_id='layout_a',
            direction='response',
        )

        # R252: field_key 返回 FieldKey 对象（direction 是 Direction 枚举）
        assert isinstance(record.field_key, FieldKey)
        assert record.field_key.layout_id == 'layout_a'
        assert record.field_key.direction == Direction.RESPONSE
        assert record.field_key.field_index == 3

    def test_field_key_default_values(self):
        """未指定 layout_id/direction 时使用默认值。

        教程 1.3：direction 缺失时降级为 "unknown"（不兜底 "request"）。
        """
        from semantic_detector.contracts import FieldKey, Direction

        record = GroundTruthRecord(
            truth_id=1,
            field_index=0,
            semantic_label='constant',
            confidence=1.0,
            is_hard_evidence=True,
        )

        assert record.layout_id == 'default'
        assert record.direction == 'unknown'
        # R252: field_key 返回 FieldKey 对象
        assert isinstance(record.field_key, FieldKey)
        assert record.field_key.layout_id == 'default'
        assert record.field_key.direction == Direction.UNKNOWN
        assert record.field_key.field_index == 0

    def test_empty_layout_id_rejected(self):
        """空 layout_id 抛出 ValueError。"""
        with pytest.raises(ValueError, match="layout_id must not be empty"):
            GroundTruthRecord(
                truth_id=1,
                field_index=0,
                semantic_label='constant',
                confidence=1.0,
                is_hard_evidence=True,
                layout_id='',
            )

    def test_empty_direction_rejected(self):
        """空 direction 抛出 ValueError。"""
        with pytest.raises(ValueError, match="direction must not be empty"):
            GroundTruthRecord(
                truth_id=1,
                field_index=0,
                semantic_label='constant',
                confidence=1.0,
                is_hard_evidence=True,
                direction='',
            )

    def test_semantic_type_backward_compatible(self):
        """@property semantic_type 向后兼容，返回 semantic_label 值。"""
        record = GroundTruthRecord(
            truth_id=1,
            field_index=0,
            semantic_label='length',
            confidence=1.0,
            is_hard_evidence=True,
        )

        # 旧代码访问 semantic_type 仍能工作
        assert record.semantic_type == 'length'
        assert record.semantic_type == record.semantic_label


class TestReadGroundTruthJsonl:
    """读取 ground truth JSONL 测试"""

    def test_valid_file(self):
        """测试有效文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"truth_id": 1, "field_index": 0, "semantic_type": "constant", "confidence": 1.0, "is_hard_evidence": true}\n')
            f.write('{"truth_id": 2, "field_index": 1, "semantic_type": "payload", "confidence": 1.0, "is_hard_evidence": true}\n')
            tmp_path = f.name

        try:
            valid, rejected = read_ground_truth_jsonl(tmp_path)

            assert len(valid) == 2
            assert len(rejected) == 0

            assert valid[0].truth_id == 1
            assert valid[0].semantic_label == 'constant'

            assert valid[1].truth_id == 2
            assert valid[1].semantic_label == 'payload'
        finally:
            os.remove(tmp_path)

    def test_missing_field(self):
        """测试缺少字段"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"truth_id": 1, "field_index": 0}\n')
            tmp_path = f.name

        try:
            valid, rejected = read_ground_truth_jsonl(tmp_path)

            assert len(valid) == 0
            assert len(rejected) == 1
            # R335: 统一拒绝记录结构
            assert rejected[0]['stage'] == 'read'
            assert rejected[0]['reason_code'] == 'missing_required_field'
            assert 'confidence' in rejected[0]['message']
            assert rejected[0]['line_number'] == 1
            assert 'raw_line' in rejected[0]
        finally:
            os.remove(tmp_path)

    def test_invalid_json(self):
        """测试无效 JSON"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('not a json\n')
            tmp_path = f.name

        try:
            valid, rejected = read_ground_truth_jsonl(tmp_path)

            assert len(valid) == 0
            assert len(rejected) == 1
        finally:
            os.remove(tmp_path)


class TestReadGroundTruthJsonlFieldKey:
    """R249: 读取含完整 FieldKey 的 ground truth JSONL

    03 教程 12.1 / 04 任务表 R249：
    - 支持 semantic_label 新键名
    - 兼容 semantic_type 旧键名
    - 支持 layout_id/direction 新字段
    - 缺失 layout_id/direction 时用默认值
    """

    def test_read_semantic_label_new_key(self):
        """读取 semantic_label 新键名。"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"truth_id": 1, "field_index": 0, "semantic_label": "length", '
                    '"confidence": 1.0, "is_hard_evidence": true, '
                    '"layout_id": "L1", "direction": "request"}\n')
            tmp_path = f.name

        try:
            valid, rejected = read_ground_truth_jsonl(tmp_path)

            assert len(valid) == 1
            assert len(rejected) == 0
            assert valid[0].semantic_label == 'length'
            assert valid[0].layout_id == 'L1'
            assert valid[0].direction == 'request'
        finally:
            os.remove(tmp_path)

    def test_read_semantic_type_old_key_compatible(self):
        """兼容读取 semantic_type 旧键名。"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"truth_id": 1, "field_index": 0, "semantic_type": "constant", '
                    '"confidence": 1.0, "is_hard_evidence": true}\n')
            tmp_path = f.name

        try:
            valid, rejected = read_ground_truth_jsonl(tmp_path)

            assert len(valid) == 1
            assert len(rejected) == 0
            # semantic_type 旧键名读到 semantic_label 字段
            assert valid[0].semantic_label == 'constant'
            # @property 向后兼容
            assert valid[0].semantic_type == 'constant'
        finally:
            os.remove(tmp_path)

    def test_read_layout_id_direction(self):
        """读取 layout_id 和 direction 字段。"""
        from semantic_detector.contracts import FieldKey, Direction

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"truth_id": 1, "field_index": 2, "semantic_label": "timestamp", '
                    '"confidence": 1.0, "is_hard_evidence": true, '
                    '"layout_id": "layout_ts", "direction": "response"}\n')
            tmp_path = f.name

        try:
            valid, rejected = read_ground_truth_jsonl(tmp_path)

            assert len(valid) == 1
            assert valid[0].layout_id == 'layout_ts'
            assert valid[0].direction == 'response'
            # R252: field_key 返回 FieldKey 对象
            assert isinstance(valid[0].field_key, FieldKey)
            assert valid[0].field_key.layout_id == 'layout_ts'
            assert valid[0].field_key.direction == Direction.RESPONSE
            assert valid[0].field_key.field_index == 2
        finally:
            os.remove(tmp_path)

    def test_read_missing_layout_id_uses_default(self):
        """缺失 layout_id 时用默认值 'default'。

        教程 1.3：direction 缺失时降级为 "unknown"（不兜底 "request"）。
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"truth_id": 1, "field_index": 0, "semantic_type": "constant", '
                    '"confidence": 1.0, "is_hard_evidence": true}\n')
            tmp_path = f.name

        try:
            valid, _ = read_ground_truth_jsonl(tmp_path)

            assert len(valid) == 1
            assert valid[0].layout_id == 'default'
            assert valid[0].direction == 'unknown'
        finally:
            os.remove(tmp_path)

    def test_read_missing_semantic_label_rejected(self):
        """同时缺失 semantic_label 和 semantic_type 时拒绝。"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"truth_id": 1, "field_index": 0, '
                    '"confidence": 1.0, "is_hard_evidence": true}\n')
            tmp_path = f.name

        try:
            valid, rejected = read_ground_truth_jsonl(tmp_path)

            assert len(valid) == 0
            assert len(rejected) == 1
            # R335: 统一拒绝记录结构
            assert rejected[0]['stage'] == 'read'
            assert rejected[0]['reason_code'] == 'missing_required_field'
            assert 'semantic_label' in rejected[0]['message']
        finally:
            os.remove(tmp_path)

    def test_read_multiple_layouts_directions(self):
        """读取多个 layout 和方向的 truth 记录。"""
        from semantic_detector.contracts import FieldKey, Direction

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"truth_id": 1, "field_index": 0, "semantic_label": "length", '
                    '"confidence": 1.0, "is_hard_evidence": true, '
                    '"layout_id": "L1", "direction": "request"}\n')
            f.write('{"truth_id": 2, "field_index": 0, "semantic_label": "timestamp", '
                    '"confidence": 1.0, "is_hard_evidence": true, '
                    '"layout_id": "L1", "direction": "response"}\n')
            f.write('{"truth_id": 3, "field_index": 1, "semantic_label": "constant", '
                    '"confidence": 1.0, "is_hard_evidence": true, '
                    '"layout_id": "L2", "direction": "request"}\n')
            tmp_path = f.name

        try:
            valid, rejected = read_ground_truth_jsonl(tmp_path)

            assert len(valid) == 3
            assert len(rejected) == 0

            # R252: field_key 返回 FieldKey 对象
            keys = {r.field_key for r in valid}
            assert FieldKey('L1', Direction.REQUEST, 0) in keys
            assert FieldKey('L1', Direction.RESPONSE, 0) in keys
            assert FieldKey('L2', Direction.REQUEST, 1) in keys
        finally:
            os.remove(tmp_path)


class TestValidateGroundTruth:
    """验证 ground truth 测试"""

    def test_valid_records(self):
        """测试有效记录"""
        records = [
            GroundTruthRecord(1, 0, 'constant', 1.0, True),
            GroundTruthRecord(2, 1, 'payload', 1.0, True),
        ]

        valid, rejected = validate_ground_truth(records)

        assert len(valid) == 2
        assert len(rejected) == 0

    def test_duplicate_truth_id(self):
        """测试重复 truth_id"""
        records = [
            GroundTruthRecord(1, 0, 'constant', 1.0, True),
            GroundTruthRecord(1, 1, 'payload', 1.0, True),
        ]

        valid, rejected = validate_ground_truth(records)

        assert len(valid) == 1
        assert len(rejected) == 1
        assert 'Duplicate truth_id' in rejected[0]['errors'][0]

    def test_invalid_semantic_type(self):
        """测试无效 semantic_label"""
        records = [
            GroundTruthRecord(1, 0, 'invalid_type', 1.0, True),
        ]

        valid, rejected = validate_ground_truth(records)

        assert len(valid) == 0
        assert len(rejected) == 1
        # R250: 错误消息改为 'Invalid semantic_label'
        assert 'Invalid semantic_label' in rejected[0]['errors'][0]
        assert 'invalid_type' in rejected[0]['errors'][0]


class TestValidateGroundTruthCanonicalLabels:
    """R250: 标准标签验证和旧标签兼容读取

    03 教程 7.4/7.5 / 04 任务表 R250：
    - 9 类标准标签验证
    - 旧标签兼容读取（normalize_legacy_label）
    - 新写出只使用标准标签
    """

    def test_validate_accepts_all_9_canonical_labels(self):
        """validate_ground_truth 接受 9 个标准标签。"""
        from semantic_detector.taxonomy import CANONICAL_COARSE_LABELS

        records = [
            GroundTruthRecord(
                truth_id=i + 1,
                field_index=i,
                semantic_label=label,
                confidence=1.0,
                is_hard_evidence=True,
            )
            for i, label in enumerate(CANONICAL_COARSE_LABELS)
        ]

        valid, rejected = validate_ground_truth(records)

        assert len(valid) == 9
        assert len(rejected) == 0

    def test_validate_rejects_non_canonical_label(self):
        """validate_ground_truth 拒绝非标准标签。"""
        # total_length 是旧标签，不在 9 个标准标签中
        records = [
            GroundTruthRecord(1, 0, 'total_length', 1.0, True),
        ]

        valid, rejected = validate_ground_truth(records)

        assert len(valid) == 0
        assert len(rejected) == 1
        assert 'Invalid semantic_label' in rejected[0]['errors'][0]

    def test_validate_rejects_candidate_label(self):
        """validate_ground_truth 拒绝候选状态标签（如 identifier_candidate）。"""
        # Ground Truth 不写候选状态，identifier_candidate 是旧标签
        # 如果未经 read 阶段 normalize，validate 会拒绝
        records = [
            GroundTruthRecord(1, 0, 'identifier_candidate', 1.0, True),
        ]

        valid, rejected = validate_ground_truth(records)

        assert len(valid) == 0
        assert len(rejected) == 1


class TestReadGroundTruthLegacyLabelNormalization:
    """R250: 读取阶段旧标签兼容 normalize

    03 教程 7.4 / 04 任务表 R250：
    - 旧标签在 read 阶段自动 normalize 为标准标签
    - 新写出只使用标准标签
    """

    def test_read_normalizes_identifier_candidate(self):
        """读取 identifier_candidate 旧标签 -> normalize 为 identifier。"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"truth_id": 1, "field_index": 0, "semantic_type": "identifier_candidate", '
                    '"confidence": 1.0, "is_hard_evidence": true}\n')
            tmp_path = f.name

        try:
            valid, rejected = read_ground_truth_jsonl(tmp_path)

            assert len(valid) == 1
            assert len(rejected) == 0
            # 旧标签 normalize 为标准标签
            assert valid[0].semantic_label == 'identifier'
        finally:
            os.remove(tmp_path)

    def test_read_normalizes_type_opcode(self):
        """读取 type_opcode 旧标签 -> normalize 为 type_control。"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"truth_id": 1, "field_index": 0, "semantic_type": "type_opcode", '
                    '"confidence": 1.0, "is_hard_evidence": true}\n')
            tmp_path = f.name

        try:
            valid, _ = read_ground_truth_jsonl(tmp_path)

            assert len(valid) == 1
            assert valid[0].semantic_label == 'type_control'
        finally:
            os.remove(tmp_path)

    def test_read_normalizes_type_or_opcode_candidate(self):
        """读取 type_or_opcode_candidate 旧标签 -> normalize 为 type_control。"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"truth_id": 1, "field_index": 0, "semantic_type": "type_or_opcode_candidate", '
                    '"confidence": 1.0, "is_hard_evidence": true}\n')
            tmp_path = f.name

        try:
            valid, _ = read_ground_truth_jsonl(tmp_path)

            assert len(valid) == 1
            assert valid[0].semantic_label == 'type_control'
        finally:
            os.remove(tmp_path)

    def test_read_normalizes_sequence(self):
        """读取 sequence 旧标签 -> normalize 为 sequence_or_counter。"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"truth_id": 1, "field_index": 0, "semantic_type": "sequence", '
                    '"confidence": 1.0, "is_hard_evidence": true}\n')
            tmp_path = f.name

        try:
            valid, _ = read_ground_truth_jsonl(tmp_path)

            assert len(valid) == 1
            assert valid[0].semantic_label == 'sequence_or_counter'
        finally:
            os.remove(tmp_path)

    def test_read_normalizes_opaque_payload_candidate(self):
        """读取 opaque_payload_candidate 旧标签 -> normalize 为 payload。"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"truth_id": 1, "field_index": 0, "semantic_type": "opaque_payload_candidate", '
                    '"confidence": 1.0, "is_hard_evidence": true}\n')
            tmp_path = f.name

        try:
            valid, _ = read_ground_truth_jsonl(tmp_path)

            assert len(valid) == 1
            assert valid[0].semantic_label == 'payload'
        finally:
            os.remove(tmp_path)

    def test_read_preserves_canonical_label(self):
        """读取标准标签原样保留（不 normalize）。"""
        for label in ['constant', 'length', 'timestamp', 'sequence_or_counter',
                      'string', 'identifier', 'type_control', 'payload', 'unknown']:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
                f.write(f'{{"truth_id": 1, "field_index": 0, "semantic_label": "{label}", '
                        f'"confidence": 1.0, "is_hard_evidence": true}}\n')
                tmp_path = f.name

            try:
                valid, _ = read_ground_truth_jsonl(tmp_path)

                assert len(valid) == 1
                assert valid[0].semantic_label == label
            finally:
                os.remove(tmp_path)

    def test_read_then_validate_legacy_label_passes(self):
        """读取旧标签后 validate 通过（因 read 阶段已 normalize）。"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"truth_id": 1, "field_index": 0, "semantic_type": "identifier_candidate", '
                    '"confidence": 1.0, "is_hard_evidence": true}\n')
            f.write('{"truth_id": 2, "field_index": 1, "semantic_type": "type_opcode", '
                    '"confidence": 1.0, "is_hard_evidence": true}\n')
            f.write('{"truth_id": 3, "field_index": 2, "semantic_type": "sequence", '
                    '"confidence": 1.0, "is_hard_evidence": true}\n')
            tmp_path = f.name

        try:
            valid_read, _ = read_ground_truth_jsonl(tmp_path)
            valid_validate, rejected_validate = validate_ground_truth(valid_read)

            assert len(valid_validate) == 3
            assert len(rejected_validate) == 0
            # 全部 normalize 为标准标签
            labels = {r.semantic_label for r in valid_validate}
            assert labels == {'identifier', 'type_control', 'sequence_or_counter'}
        finally:
            os.remove(tmp_path)

    def test_read_unknown_label_preserved_then_validate_rejects(self):
        """读取未知标签原样保留，validate 阶段拒绝。"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"truth_id": 1, "field_index": 0, "semantic_type": "totally_unknown_label", '
                    '"confidence": 1.0, "is_hard_evidence": true}\n')
            tmp_path = f.name

        try:
            valid_read, _ = read_ground_truth_jsonl(tmp_path)

            assert len(valid_read) == 1
            # 未知标签原样保留
            assert valid_read[0].semantic_label == 'totally_unknown_label'

            # validate 阶段拒绝
            valid_validate, rejected_validate = validate_ground_truth(valid_read)
            assert len(valid_validate) == 0
            assert len(rejected_validate) == 1
        finally:
            os.remove(tmp_path)


class TestValidateGroundTruthDuplicateFieldKey:
    """R251: Ground Truth 重复完整 FieldKey 拒绝

    03 教程 12.2 / 04 任务表 R251：
    - 两条相同 FieldKey
    - 不用 truth_id 代替 FieldKey 唯一性
    """

    def test_validate_rejects_duplicate_fieldkey_same_layout_direction_field_index(self):
        """重复 FieldKey（同 layout+direction+field_index）被拒绝。"""
        records = [
            GroundTruthRecord(
                truth_id=1, field_index=0, semantic_label='length',
                confidence=1.0, is_hard_evidence=True,
                layout_id='L1', direction='request',
            ),
            GroundTruthRecord(
                truth_id=2, field_index=0, semantic_label='length',
                confidence=1.0, is_hard_evidence=True,
                layout_id='L1', direction='request',
            ),
        ]

        valid, rejected = validate_ground_truth(records)

        # truth_id 不同，但 FieldKey 相同 -> 第二条被拒绝
        assert len(valid) == 1
        assert len(rejected) == 1
        assert 'Duplicate FieldKey' in rejected[0]['errors'][0]
        # R335: 统一拒绝记录结构，truth_id 在 record_summary 中
        assert rejected[0]['record_summary']['truth_id'] == 2
        assert rejected[0]['reason_code'] == 'duplicate_field_key'

    def test_validate_allows_same_layout_different_direction(self):
        """同 layout + 同 field_index 但 direction 不同 -> 不算重复。"""
        records = [
            GroundTruthRecord(
                truth_id=1, field_index=0, semantic_label='length',
                confidence=1.0, is_hard_evidence=True,
                layout_id='L1', direction='request',
            ),
            GroundTruthRecord(
                truth_id=2, field_index=0, semantic_label='timestamp',
                confidence=1.0, is_hard_evidence=True,
                layout_id='L1', direction='response',
            ),
        ]

        valid, rejected = validate_ground_truth(records)

        assert len(valid) == 2
        assert len(rejected) == 0

    def test_validate_allows_same_layout_direction_different_field_index(self):
        """同 layout + 同 direction 但 field_index 不同 -> 不算重复。"""
        records = [
            GroundTruthRecord(
                truth_id=1, field_index=0, semantic_label='length',
                confidence=1.0, is_hard_evidence=True,
                layout_id='L1', direction='request',
            ),
            GroundTruthRecord(
                truth_id=2, field_index=1, semantic_label='constant',
                confidence=1.0, is_hard_evidence=True,
                layout_id='L1', direction='request',
            ),
        ]

        valid, rejected = validate_ground_truth(records)

        assert len(valid) == 2
        assert len(rejected) == 0

    def test_validate_allows_different_layout_same_direction_field_index(self):
        """不同 layout + 同 direction + 同 field_index -> 不算重复。"""
        records = [
            GroundTruthRecord(
                truth_id=1, field_index=0, semantic_label='length',
                confidence=1.0, is_hard_evidence=True,
                layout_id='L1', direction='request',
            ),
            GroundTruthRecord(
                truth_id=2, field_index=0, semantic_label='timestamp',
                confidence=1.0, is_hard_evidence=True,
                layout_id='L2', direction='request',
            ),
        ]

        valid, rejected = validate_ground_truth(records)

        assert len(valid) == 2
        assert len(rejected) == 0

    def test_validate_duplicate_fieldkey_with_different_truth_id(self):
        """truth_id 不同但 FieldKey 相同 -> 仍被拒绝（不用 truth_id 代替 FieldKey 唯一性）。"""
        records = [
            GroundTruthRecord(
                truth_id=100, field_index=3, semantic_label='length',
                confidence=1.0, is_hard_evidence=True,
                layout_id='layout_a', direction='request',
            ),
            GroundTruthRecord(
                truth_id=200, field_index=3, semantic_label='constant',
                confidence=1.0, is_hard_evidence=True,
                layout_id='layout_a', direction='request',
            ),
        ]

        valid, rejected = validate_ground_truth(records)

        # truth_id 不同（100 vs 200），但 FieldKey 相同 -> 第二条被拒绝
        assert len(valid) == 1
        assert len(rejected) == 1
        # R335: 统一拒绝记录结构，truth_id 在 record_summary 中
        assert rejected[0]['record_summary']['truth_id'] == 200

    def test_validate_duplicate_fieldkey_error_message_contains_fieldkey(self):
        """错误消息含 layout_id/direction/field_index。"""
        records = [
            GroundTruthRecord(
                truth_id=1, field_index=5, semantic_label='length',
                confidence=1.0, is_hard_evidence=True,
                layout_id='layout_x', direction='response',
            ),
            GroundTruthRecord(
                truth_id=2, field_index=5, semantic_label='constant',
                confidence=1.0, is_hard_evidence=True,
                layout_id='layout_x', direction='response',
            ),
        ]

        valid, rejected = validate_ground_truth(records)

        assert len(rejected) == 1
        msg = rejected[0]['errors'][0]
        assert 'layout_x' in msg
        assert 'response' in msg
        assert '5' in msg

    def test_validate_both_duplicate_truth_id_and_fieldkey(self):
        """同时重复 truth_id 和 FieldKey -> 两个错误都报告。"""
        records = [
            GroundTruthRecord(
                truth_id=1, field_index=0, semantic_label='length',
                confidence=1.0, is_hard_evidence=True,
                layout_id='L1', direction='request',
            ),
            # 完全相同的 truth_id 和 FieldKey
            GroundTruthRecord(
                truth_id=1, field_index=0, semantic_label='length',
                confidence=1.0, is_hard_evidence=True,
                layout_id='L1', direction='request',
            ),
        ]

        valid, rejected = validate_ground_truth(records)

        assert len(valid) == 1
        assert len(rejected) == 1
        # 两个错误都报告
        errors = rejected[0]['errors']
        assert any('Duplicate truth_id' in e for e in errors)
        assert any('Duplicate FieldKey' in e for e in errors)

    def test_validate_three_records_third_duplicate_fieldkey(self):
        """三条记录，第三条 FieldKey 重复 -> 第三条被拒绝。"""
        records = [
            GroundTruthRecord(
                truth_id=1, field_index=0, semantic_label='length',
                confidence=1.0, is_hard_evidence=True,
                layout_id='L1', direction='request',
            ),
            GroundTruthRecord(
                truth_id=2, field_index=1, semantic_label='constant',
                confidence=1.0, is_hard_evidence=True,
                layout_id='L1', direction='request',
            ),
            # 第三条与第一条 FieldKey 重复
            GroundTruthRecord(
                truth_id=3, field_index=0, semantic_label='timestamp',
                confidence=1.0, is_hard_evidence=True,
                layout_id='L1', direction='request',
            ),
        ]

        valid, rejected = validate_ground_truth(records)

        assert len(valid) == 2
        assert len(rejected) == 1
        # R335: 统一拒绝记录结构，truth_id 在 record_summary 中
        assert rejected[0]['record_summary']['truth_id'] == 3


class TestGroundTruthRejectionStructureR335:
    """R335: 统一 Ground Truth 拒绝结构

    06 计划 R335 要求：
    - JSON 解析错误和语义校验错误使用统一可导出的拒绝记录
    - 拒绝记录至少包含：line_number / stage / reason_code / message / raw_line 或 record_summary

    reason_code 示例：invalid_json / missing_required_field / invalid_direction /
    invalid_label / duplicate_field_key / negative_field_index
    """

    def test_read_invalid_json_has_unified_structure(self):
        """R335: read 阶段 invalid_json 拒绝记录含 line_number/stage/reason_code/message/raw_line"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"truth_id": 1, "field_index": 0, "semantic_type": "constant", '
                    '"confidence": 1.0, "is_hard_evidence": true}\n')
            f.write('{invalid json}\n')
            tmp_path = f.name

        try:
            valid, rejected = read_ground_truth_jsonl(tmp_path)

            assert len(valid) == 1
            assert len(rejected) == 1
            r = rejected[0]
            # 统一结构 5 个字段
            assert r['line_number'] == 2
            assert r['stage'] == 'read'
            assert r['reason_code'] == 'invalid_json'
            assert 'JSON' in r['message']
            assert 'raw_line' in r
            assert 'invalid json' in r['raw_line']
        finally:
            os.remove(tmp_path)

    def test_read_missing_required_field_has_unified_structure(self):
        """R335: read 阶段 missing_required_field 拒绝记录含统一结构"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"truth_id": 1, "field_index": 0}\n')  # 缺 confidence/is_hard_evidence
            tmp_path = f.name

        try:
            valid, rejected = read_ground_truth_jsonl(tmp_path)

            assert len(rejected) == 1
            r = rejected[0]
            assert r['stage'] == 'read'
            assert r['reason_code'] == 'missing_required_field'
            assert 'confidence' in r['message']
            assert r['line_number'] == 1
            assert 'raw_line' in r
        finally:
            os.remove(tmp_path)

    def test_validate_duplicate_field_key_has_unified_structure(self):
        """R335: validate 阶段 duplicate_field_key 拒绝记录含统一结构"""
        records = [
            GroundTruthRecord(
                truth_id=1, field_index=0, semantic_label='constant',
                confidence=1.0, is_hard_evidence=True,
                layout_id='L1', direction='request',
            ),
            GroundTruthRecord(
                truth_id=2, field_index=0, semantic_label='constant',
                confidence=1.0, is_hard_evidence=True,
                layout_id='L1', direction='request',
            ),
        ]

        valid, rejected = validate_ground_truth(records)

        assert len(rejected) == 1
        r = rejected[0]
        # 统一结构
        assert r['stage'] == 'validate'
        assert r['reason_code'] == 'duplicate_field_key'
        assert 'Duplicate FieldKey' in r['message']
        assert 'record_summary' in r
        assert r['record_summary']['truth_id'] == 2
        assert r['record_summary']['layout_id'] == 'L1'
        assert r['record_summary']['direction'] == 'request'
        assert r['record_summary']['field_index'] == 0

    def test_validate_invalid_label_has_unified_structure(self):
        """R335: validate 阶段 invalid_label 拒绝记录含统一结构"""
        records = [
            GroundTruthRecord(
                truth_id=1, field_index=0, semantic_label='invalid_type',
                confidence=1.0, is_hard_evidence=True,
            ),
        ]

        valid, rejected = validate_ground_truth(records)

        assert len(rejected) == 1
        r = rejected[0]
        assert r['stage'] == 'validate'
        assert r['reason_code'] == 'invalid_label'
        assert 'Invalid semantic_label' in r['message']
        assert 'record_summary' in r

    def test_validate_duplicate_truth_id_has_unified_structure(self):
        """R335: validate 阶段 duplicate_truth_id 拒绝记录含统一结构"""
        records = [
            GroundTruthRecord(1, 0, 'constant', 1.0, True),
            GroundTruthRecord(1, 1, 'payload', 1.0, True),
        ]

        valid, rejected = validate_ground_truth(records)

        assert len(rejected) == 1
        r = rejected[0]
        assert r['stage'] == 'validate'
        assert r['reason_code'] == 'duplicate_truth_id'
        assert 'Duplicate truth_id' in r['message']
        assert r['record_summary']['truth_id'] == 1

    def test_read_and_validate_rejections_both_exportable(self):
        """R335: read 和 validate 两阶段拒绝记录都可导出（结构统一）"""
        # read 阶段拒绝
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"truth_id": 1, "field_index": 0, "semantic_type": "constant", '
                    '"confidence": 1.0, "is_hard_evidence": true}\n')
            f.write('bad json\n')
            tmp_path = f.name

        try:
            valid_read, rejected_read = read_ground_truth_jsonl(tmp_path)
        finally:
            os.remove(tmp_path)

        # validate 阶段拒绝（构造 duplicate field_key）
        records = [
            GroundTruthRecord(1, 0, 'constant', 1.0, True, layout_id='L1', direction='request'),
            GroundTruthRecord(2, 0, 'constant', 1.0, True, layout_id='L1', direction='request'),
        ]
        valid_validate, rejected_validate = validate_ground_truth(records)

        # 两个阶段的拒绝记录都含 stage/reason_code/message
        assert rejected_read[0]['stage'] == 'read'
        assert 'reason_code' in rejected_read[0]
        assert 'message' in rejected_read[0]
        assert 'raw_line' in rejected_read[0]

        assert rejected_validate[0]['stage'] == 'validate'
        assert 'reason_code' in rejected_validate[0]
        assert 'message' in rejected_validate[0]
        assert 'record_summary' in rejected_validate[0]
