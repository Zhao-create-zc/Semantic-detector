"""R139: TypeOpcodeDetector 对齐键测试"""

import pytest

from semantic_detector.detectors.type_opcode import (
    aggregate_dominant_values,
    is_one_to_one_mapping,
    detect_type_or_opcode,
    TypeOpcodeDetector
)
from semantic_detector.contracts import FieldKey, Direction, TypeOpcodeAlignmentKey


class TestAggregateDominantValues:
    """Tests for dominant value aggregation."""
    
    def test_aggregate_different_constants(self):
        """Three layouts with different constants should aggregate correctly."""
        layout_dominant_values = {
            "L1": b'\x01',
            "L2": b'\x02',
            "L3": b'\x03'
        }
        
        result = aggregate_dominant_values(layout_dominant_values)
        
        # Each value should map to one layout
        assert len(result) == 3
        assert result[b'\x01'] == {"L1"}
        assert result[b'\x02'] == {"L2"}
        assert result[b'\x03'] == {"L3"}
    
    def test_aggregate_same_values(self):
        """Multiple layouts with same value should group together."""
        layout_dominant_values = {
            "L1": b'\x01',
            "L2": b'\x01',
            "L3": b'\x02'
        }
        
        result = aggregate_dominant_values(layout_dominant_values)
        
        # Two layouts share the same value
        assert len(result) == 2
        assert result[b'\x01'] == {"L1", "L2"}
        assert result[b'\x02'] == {"L3"}
    
    def test_aggregate_empty_input(self):
        """Empty input should return empty dict."""
        result = aggregate_dominant_values({})
        assert len(result) == 0


class TestOneToOneMapping:
    """Tests for one-to-one mapping detection."""
    
    def test_one_to_one_mapping_detected(self):
        """One-to-one mapping should be detected."""
        layout_dominant_values = {
            "L1": b'\x01',
            "L2": b'\x02',
            "L3": b'\x03'
        }
        
        assert is_one_to_one_mapping(layout_dominant_values) is True
    
    def test_not_one_to_one_mapping(self):
        """Not one-to-one mapping should be rejected."""
        layout_dominant_values = {
            "L1": b'\x01',
            "L2": b'\x01',  # Same value as L1
            "L3": b'\x02'
        }
        
        assert is_one_to_one_mapping(layout_dominant_values) is False
    
    def test_empty_mapping_returns_false(self):
        """Empty mapping should return False."""
        assert is_one_to_one_mapping({}) is False


class TestDetectTypeOrOpcode:
    """Tests for type/opcode detection."""
    
    def test_detect_outputs_soft_candidate(self):
        """Detection should output soft candidate."""
        layout_dominant_values = {
            "L1": b'\x01',
            "L2": b'\x02',
            "L3": b'\x03'
        }
        
        alignment_key = TypeOpcodeAlignmentKey(
            direction=Direction.REQUEST, field_index=0, start_mode=5, width_mode=2
        )
        
        evidence = detect_type_or_opcode(layout_dominant_values, alignment_key)

        assert evidence is not None
        assert evidence.is_hard_evidence is False
        assert evidence.coarse_label == "type_control"
        assert evidence.fine_label == "type_or_opcode_candidate"
    
    def test_detect_not_one_to_one_returns_none(self):
        """Not one-to-one mapping should return None."""
        layout_dominant_values = {
            "L1": b'\x01',
            "L2": b'\x01',
            "L3": b'\x02'
        }
        
        alignment_key = TypeOpcodeAlignmentKey(
            direction=Direction.REQUEST, field_index=0, start_mode=5, width_mode=2
        )
        
        evidence = detect_type_or_opcode(layout_dominant_values, alignment_key)
        
        assert evidence is None
    
    def test_detect_single_layout_returns_none(self):
        """Single layout should return None."""
        layout_dominant_values = {
            "L1": b'\x01'
        }
        
        alignment_key = TypeOpcodeAlignmentKey(
            direction=Direction.REQUEST, field_index=0, start_mode=5, width_mode=2
        )
        
        evidence = detect_type_or_opcode(layout_dominant_values, alignment_key)
        
        assert evidence is None
    
    def test_detect_width_gt_2_returns_none(self):
        """Width > 2 should return None."""
        layout_dominant_values = {
            "L1": b'\x01',
            "L2": b'\x02',
            "L3": b'\x03'
        }
        
        alignment_key = TypeOpcodeAlignmentKey(
            direction=Direction.REQUEST, field_index=0, start_mode=5, width_mode=3
        )  # width = 3
        
        evidence = detect_type_or_opcode(layout_dominant_values, alignment_key)
        
        assert evidence is None
    
    def test_detect_width_1_is_allowed(self):
        """Width = 1 should be allowed."""
        layout_dominant_values = {
            "L1": b'\x01',
            "L2": b'\x02',
            "L3": b'\x03'
        }
        
        alignment_key = TypeOpcodeAlignmentKey(
            direction=Direction.REQUEST, field_index=0, start_mode=5, width_mode=1
        )  # width = 1
        
        evidence = detect_type_or_opcode(layout_dominant_values, alignment_key)
        
        assert evidence is not None
        assert evidence.fine_label == "type_or_opcode_candidate"
    
    def test_detect_width_2_is_allowed(self):
        """Width = 2 should be allowed."""
        layout_dominant_values = {
            "L1": b'\x01',
            "L2": b'\x02',
            "L3": b'\x03'
        }
        
        alignment_key = TypeOpcodeAlignmentKey(
            direction=Direction.REQUEST, field_index=0, start_mode=5, width_mode=2
        )  # width = 2
        
        evidence = detect_type_or_opcode(layout_dominant_values, alignment_key)
        
        assert evidence is not None
        assert evidence.fine_label == "type_or_opcode_candidate"
    
    def test_detect_hard_length_evidence_returns_none(self):
        """Hard length evidence should return None."""
        from semantic_detector.contracts import DetectorEvidence
        
        layout_dominant_values = {
            "L1": b'\x01',
            "L2": b'\x02',
            "L3": b'\x03'
        }
        
        alignment_key = TypeOpcodeAlignmentKey(
            direction=Direction.REQUEST, field_index=0, start_mode=5, width_mode=2
        )
        
        # 创建强长度证据
        hard_length_evidence = DetectorEvidence(
            detector="length",
            coarse_label="length",
            fine_label="length_of_next_field",
            is_hard_evidence=True,
            score=1.0,
            reason_code="test",
            details={}
        )
        
        evidence = detect_type_or_opcode(
            layout_dominant_values,
            alignment_key,
            existing_evidences=[hard_length_evidence]
        )
        
        assert evidence is None
    
    def test_detect_soft_length_evidence_is_allowed(self):
        """Soft length evidence should be allowed."""
        from semantic_detector.contracts import DetectorEvidence
        
        layout_dominant_values = {
            "L1": b'\x01',
            "L2": b'\x02',
            "L3": b'\x03'
        }
        
        alignment_key = TypeOpcodeAlignmentKey(
            direction=Direction.REQUEST, field_index=0, start_mode=5, width_mode=2
        )
        
        # 创建软长度证据
        soft_length_evidence = DetectorEvidence(
            detector="length",
            coarse_label="length",
            fine_label="length_of_next_field",
            is_hard_evidence=False,
            score=0.5,
            reason_code="test",
            details={}
        )
        
        evidence = detect_type_or_opcode(
            layout_dominant_values,
            alignment_key,
            existing_evidences=[soft_length_evidence]
        )
        
        assert evidence is not None
        assert evidence.fine_label == "type_or_opcode_candidate"
    
    def test_detect_other_hard_evidence_is_allowed(self):
        """Hard evidence from other detectors should be allowed."""
        from semantic_detector.contracts import DetectorEvidence
        
        layout_dominant_values = {
            "L1": b'\x01',
            "L2": b'\x02',
            "L3": b'\x03'
        }
        
        alignment_key = TypeOpcodeAlignmentKey(
            direction=Direction.REQUEST, field_index=0, start_mode=5, width_mode=2
        )
        
        # 创建其他强证据
        hard_constant_evidence = DetectorEvidence(
            detector="constant",
            coarse_label="constant",
            fine_label="constant_value",
            is_hard_evidence=True,
            score=1.0,
            reason_code="test",
            details={}
        )
        
        evidence = detect_type_or_opcode(
            layout_dominant_values,
            alignment_key,
            existing_evidences=[hard_constant_evidence]
        )
        
        assert evidence is not None
        assert evidence.fine_label == "type_or_opcode_candidate"


class TestTypeOpcodeDetectorBasic:
    """Tests for TypeOpcodeDetector basic functionality."""

    def test_detector_name(self):
        """Detector name should be 'type_opcode'."""
        detector = TypeOpcodeDetector()
        assert detector.name == "type_opcode"


class TestTypeOpcodeDetectorCanonicalLabel:
    """R238: type/opcode detector coarse_label 统一为标准标签 type_control

    03 教程 7.3：coarse_label=type_control, fine_label=type_or_opcode_candidate,
    is_hard_evidence=False。candidate 状态由 fine_label 表达。
    """

    def _make_layout_dominant_values(self):
        return {
            "L1": b'\x01',
            "L2": b'\x02',
            "L3": b'\x03',
        }

    def _make_alignment_key(self):
        return TypeOpcodeAlignmentKey(
            direction=Direction.REQUEST, field_index=0, start_mode=5, width_mode=2
        )

    def test_coarse_label_is_canonical_type_control(self):
        """coarse_label 必须是 taxonomy 标准标签 type_control。"""
        from semantic_detector.taxonomy import (
            CANONICAL_COARSE_LABELS,
            is_canonical_coarse_label,
        )

        evidence = detect_type_or_opcode(
            self._make_layout_dominant_values(),
            self._make_alignment_key(),
        )
        assert evidence is not None
        assert evidence.coarse_label == "type_control"
        assert is_canonical_coarse_label(evidence.coarse_label) is True
        assert "type_control" in CANONICAL_COARSE_LABELS

    def test_fine_label_is_type_or_opcode_candidate(self):
        """fine_label 必须是 type_or_opcode_candidate。"""
        evidence = detect_type_or_opcode(
            self._make_layout_dominant_values(),
            self._make_alignment_key(),
        )
        assert evidence is not None
        assert evidence.fine_label == "type_or_opcode_candidate"
        assert evidence.is_hard_evidence is False

    def test_type_opcode_detector_constants_reference_taxonomy(self):
        """检测器 COARSE_LABEL 常量与 taxonomy 标准标签一致。"""
        from semantic_detector.taxonomy import CANONICAL_COARSE_LABELS
        from semantic_detector.detectors.type_opcode import (
            COARSE_LABEL as MODULE_COARSE_LABEL,
            FINE_LABEL as MODULE_FINE_LABEL,
        )

        assert TypeOpcodeDetector.COARSE_LABEL == "type_control"
        assert TypeOpcodeDetector.COARSE_LABEL in CANONICAL_COARSE_LABELS
        assert TypeOpcodeDetector.FINE_LABEL == "type_or_opcode_candidate"
        # 模块级常量与类常量保持一致
        assert MODULE_COARSE_LABEL == TypeOpcodeDetector.COARSE_LABEL
        assert MODULE_FINE_LABEL == TypeOpcodeDetector.FINE_LABEL


class TestTypeOpcodeR284:
    """R284: 完善 type/opcode 跨 layout 约束与证据 details

    04 任务表 R284：
    "完善 type/opcode 跨 layout 约束与证据 details | detectors/type_opcode.py;
     test_type_opcode.py | 单 layout/同值/宽度>2/强 length | 只在真实关联时输出"

    教程 10.4 details 必须包含：
    - layout_values: {layout_id: hex_string}
    - layout_count: int
    - unique_value_count: int
    - alignment_key: list

    教程 10.5：length 或 timestamp 强证据不得被覆盖。
    """

    def _make_layout_dominant_values(self):
        return {
            "layout_read": b'\x03',
            "layout_write": b'\x06',
        }

    def _make_alignment_key(self):
        return TypeOpcodeAlignmentKey(
            direction=Direction.REQUEST, field_index=0, start_mode=5, width_mode=1
        )

    def test_details_contains_layout_values(self):
        """details 必须包含 layout_values（layout_id -> hex 字符串，教程 10.4）"""
        evidence = detect_type_or_opcode(
            self._make_layout_dominant_values(),
            self._make_alignment_key(),
        )
        assert evidence is not None
        assert "layout_values" in evidence.details
        assert evidence.details["layout_values"] == {
            "layout_read": "03",
            "layout_write": "06",
        }

    def test_details_contains_layout_count(self):
        """details 必须包含 layout_count"""
        evidence = detect_type_or_opcode(
            self._make_layout_dominant_values(),
            self._make_alignment_key(),
        )
        assert evidence is not None
        assert evidence.details["layout_count"] == 2

    def test_details_contains_unique_value_count(self):
        """details 必须包含 unique_value_count（不同主值数量，教程 10.4）"""
        evidence = detect_type_or_opcode(
            self._make_layout_dominant_values(),
            self._make_alignment_key(),
        )
        assert evidence is not None
        assert evidence.details["unique_value_count"] == 2

    def test_details_contains_alignment_key(self):
        """details 必须包含 alignment_key"""
        evidence = detect_type_or_opcode(
            self._make_layout_dominant_values(),
            self._make_alignment_key(),
        )
        assert evidence is not None
        assert evidence.details["alignment_key"] == ["request", 0, 5, 1]

    def test_details_layout_values_three_layouts(self):
        """三个 layout 的 layout_values/layout_count/unique_value_count 完整性"""
        layout_dominant_values = {
            "layout_read": b'\x03',
            "layout_write": b'\x06',
            "layout_diag": b'\x08',
        }
        evidence = detect_type_or_opcode(
            layout_dominant_values,
            self._make_alignment_key(),
        )
        assert evidence is not None
        assert evidence.details["layout_values"] == {
            "layout_read": "03",
            "layout_write": "06",
            "layout_diag": "08",
        }
        assert evidence.details["layout_count"] == 3
        assert evidence.details["unique_value_count"] == 3

    def test_hard_timestamp_evidence_returns_none(self):
        """R284: 强 timestamp 证据应阻止 type/opcode 输出（教程 10.5）"""
        from semantic_detector.contracts import DetectorEvidence

        hard_timestamp_evidence = DetectorEvidence(
            detector="timestamp",
            coarse_label="timestamp",
            fine_label="unix_seconds_be",
            is_hard_evidence=True,
            score=0.95,
            reason_code="test",
            details={}
        )

        evidence = detect_type_or_opcode(
            self._make_layout_dominant_values(),
            self._make_alignment_key(),
            existing_evidences=[hard_timestamp_evidence]
        )
        assert evidence is None

    def test_soft_timestamp_evidence_is_allowed(self):
        """R284: 软 timestamp 证据不阻止 type/opcode 输出"""
        from semantic_detector.contracts import DetectorEvidence

        soft_timestamp_evidence = DetectorEvidence(
            detector="timestamp",
            coarse_label="timestamp",
            fine_label="unix_seconds_be",
            is_hard_evidence=False,
            score=0.5,
            reason_code="test",
            details={}
        )

        evidence = detect_type_or_opcode(
            self._make_layout_dominant_values(),
            self._make_alignment_key(),
            existing_evidences=[soft_timestamp_evidence]
        )
        assert evidence is not None
        assert evidence.fine_label == "type_or_opcode_candidate"

    def test_hard_length_evidence_returns_none_r284(self):
        """R284: 强 length 证据仍应阻止 type/opcode 输出（回归验证）"""
        from semantic_detector.contracts import DetectorEvidence

        hard_length_evidence = DetectorEvidence(
            detector="length",
            coarse_label="length",
            fine_label="length_of_next_field",
            is_hard_evidence=True,
            score=1.0,
            reason_code="test",
            details={}
        )

        evidence = detect_type_or_opcode(
            self._make_layout_dominant_values(),
            self._make_alignment_key(),
            existing_evidences=[hard_length_evidence]
        )
        assert evidence is None

    def test_single_layout_returns_none_r284(self):
        """R284: 单 layout 不输出（教程 10.3：至少两个不同 layout）"""
        evidence = detect_type_or_opcode(
            {"L1": b'\x01'},
            self._make_alignment_key(),
        )
        assert evidence is None

    def test_same_value_returns_none_r284(self):
        """R284: 同值不输出（教程 10.3：至少两个不同主值）"""
        evidence = detect_type_or_opcode(
            {"L1": b'\x01', "L2": b'\x01', "L3": b'\x02'},
            self._make_alignment_key(),
        )
        # L1 和 L2 同值，非一一对应
        assert evidence is None

    def test_width_gt_2_returns_none_r284(self):
        """R284: 宽度 > 2 不输出（教程 10.3：宽度不超过 2 字节）"""
        evidence = detect_type_or_opcode(
            self._make_layout_dominant_values(),
            TypeOpcodeAlignmentKey(
                direction=Direction.REQUEST, field_index=0, start_mode=5, width_mode=3
            ),  # width = 3
        )
        assert evidence is None

    def test_only_outputs_when_truly_associated(self):
        """R284 完成标准：只在真实关联时输出（综合验证）

        真实关联 = 不同 layout 不同主值 + 宽度 <= 2 + 无强 length/timestamp 证据。
        R331：details 新增 score_factors 和 min_dominant_ratio。
        """
        evidence = detect_type_or_opcode(
            self._make_layout_dominant_values(),
            self._make_alignment_key(),
        )
        assert evidence is not None
        assert evidence.coarse_label == "type_control"
        assert evidence.fine_label == "type_or_opcode_candidate"
        assert evidence.is_hard_evidence is False
        # details 完整性：R331 新增 score_factors 和 min_dominant_ratio
        assert set(evidence.details.keys()) == {
            "layout_values", "layout_count", "unique_value_count",
            "alignment_key", "score_factors", "min_dominant_ratio"
        }
        assert evidence.details["layout_values"] == {
            "layout_read": "03",
            "layout_write": "06",
        }
        assert evidence.details["layout_count"] == 2
        assert evidence.details["unique_value_count"] == 2


class TestTypeOpcodeNamedFieldsR329:
    """R329: TypeOpcodeDetector 按具名字段读取宽度与位置

    06 计划 R329 必须测试：
    - start=7、width=1：允许
    - start=1、width=4：拒绝
    - direction 不同：不合并
    - field_index 不同：不合并
    - width 不同：不合并

    R329 删除 R328 的 tuple 兼容层，detect_type_or_opcode 只接受
    TypeOpcodeAlignmentKey，直接用具名字段访问 width_mode/start_mode。
    """

    def _make_layout_dominant_values(self):
        return {
            "layout_read": b'\x03',
            "layout_write": b'\x06',
        }

    def test_start_seven_width_one_allowed(self):
        """R329: start=7, width=1 应允许（HIGH-1 核心场景）

        修复前：tuple ("request", 4, 1, 7) 的 [3]=7 被当 width，7 > 2 拒绝
        修复后：key.width_mode=1 <= 2 放行，key.start_mode=7 不影响宽度判断
        """
        alignment_key = TypeOpcodeAlignmentKey(
            direction=Direction.REQUEST, field_index=4, start_mode=7, width_mode=1
        )
        evidence = detect_type_or_opcode(
            self._make_layout_dominant_values(),
            alignment_key,
        )
        assert evidence is not None
        assert evidence.coarse_label == "type_control"
        assert evidence.fine_label == "type_or_opcode_candidate"

    def test_start_one_width_four_rejected(self):
        """R329: start=1, width=4 应拒绝（width_mode > 2）

        验证 width_mode=4 触发排除，与 start_mode 无关。
        """
        alignment_key = TypeOpcodeAlignmentKey(
            direction=Direction.REQUEST, field_index=4, start_mode=1, width_mode=4
        )
        evidence = detect_type_or_opcode(
            self._make_layout_dominant_values(),
            alignment_key,
        )
        assert evidence is None

    def test_different_direction_not_merged(self):
        """R329: direction 不同 → 两个 key 不相等 → 不合并到同一组

        Pipeline 用 TypeOpcodeAlignmentKey 作为 dict key 分组，
        direction 不同则 key 不相等，自然分到不同组。
        """
        key_request = TypeOpcodeAlignmentKey(
            direction=Direction.REQUEST, field_index=0, start_mode=5, width_mode=2
        )
        key_response = TypeOpcodeAlignmentKey(
            direction=Direction.RESPONSE, field_index=0, start_mode=5, width_mode=2
        )
        assert key_request != key_response
        assert hash(key_request) != hash(key_response)

    def test_different_field_index_not_merged(self):
        """R329: field_index 不同 → 两个 key 不相等 → 不合并到同一组"""
        key_0 = TypeOpcodeAlignmentKey(
            direction=Direction.REQUEST, field_index=0, start_mode=5, width_mode=2
        )
        key_1 = TypeOpcodeAlignmentKey(
            direction=Direction.REQUEST, field_index=1, start_mode=5, width_mode=2
        )
        assert key_0 != key_1

    def test_different_width_not_merged(self):
        """R329: width 不同 → 两个 key 不相等 → 不合并到同一组

        验证 width_mode 是分组键的一部分，width=1 和 width=2 不合并。
        """
        key_width_1 = TypeOpcodeAlignmentKey(
            direction=Direction.REQUEST, field_index=0, start_mode=5, width_mode=1
        )
        key_width_2 = TypeOpcodeAlignmentKey(
            direction=Direction.REQUEST, field_index=0, start_mode=5, width_mode=2
        )
        assert key_width_1 != key_width_2

    def test_tuple_rejected_with_attribute_error(self):
        """R329: 传入 tuple 应触发明确错误，不静默兜底

        R329 删除 tuple 兼容层后，detect_type_or_opcode 直接访问
        alignment_key.width_mode，tuple 没有此属性，触发 AttributeError。
        错误类型明确，不静默兜底。
        """
        alignment_key_tuple = ("request", 0, 5, 2)
        with pytest.raises(AttributeError):
            detect_type_or_opcode(
                self._make_layout_dominant_values(),
                alignment_key_tuple,
            )


class TestTypeOpcodeScoringR331:
    """R331: 重构 Type/Opcode 关联评分

    删除 layout_count/10 占位逻辑，改为多因子评分：
    - layout_count (0.15)
    - unique_dominant_value_count (0.20)
    - per_layout_dominant_ratio (0.25)
    - value_to_layout_purity (0.15)
    - width_suitability (0.15)
    - cross_layout_value_difference (0.10)

    硬性条件：至少 2 layout、至少 2 不同主值、每 layout 主值支持率达阈值、宽度<=2。
    不能只因 layout 数量多就高分。输出 score 在 [0, 1]。

    必须负例：
    - 两个 layout 主值都为 03
    - 一个 layout 主值支持率低
    - 只有一个 layout
    - 多 layout 但主值与 layout 无稳定关系
    """

    def _make_alignment_key(self, width_mode=1):
        return TypeOpcodeAlignmentKey(
            direction=Direction.REQUEST, field_index=0, start_mode=5, width_mode=width_mode
        )

    def test_score_in_zero_one_range(self):
        """R331: score 必须在 [0, 1]"""
        layout_dominant_values = {
            "L1": b'\x01', "L2": b'\x02', "L3": b'\x03',
            "L4": b'\x04', "L5": b'\x05',
        }
        evidence = detect_type_or_opcode(
            layout_dominant_values,
            self._make_alignment_key(),
        )
        assert evidence is not None
        assert 0.0 <= evidence.score <= 1.0

    def test_score_factors_present_in_details(self):
        """R331: details 必须包含 score_factors"""
        evidence = detect_type_or_opcode(
            {"L1": b'\x01', "L2": b'\x02'},
            self._make_alignment_key(),
        )
        assert evidence is not None
        assert "score_factors" in evidence.details
        factors = evidence.details["score_factors"]
        # 6 个因子 + weights
        assert "layout_count" in factors
        assert "unique_values" in factors
        assert "dominant_ratio" in factors
        assert "purity" in factors
        assert "width" in factors
        assert "cross_difference" in factors
        assert "weights" in factors

    def test_width_one_scores_higher_than_width_two(self):
        """R331: width=1 的评分应高于 width=2（width_suitability 因子）"""
        layout_dominant_values = {"L1": b'\x01', "L2": b'\x02'}
        evidence_w1 = detect_type_or_opcode(
            layout_dominant_values,
            self._make_alignment_key(width_mode=1),
        )
        evidence_w2 = detect_type_or_opcode(
            layout_dominant_values,
            self._make_alignment_key(width_mode=2),
        )
        assert evidence_w1 is not None
        assert evidence_w2 is not None
        assert evidence_w1.score > evidence_w2.score
        # 验证 width 因子差异
        assert evidence_w1.details["score_factors"]["width"] == 1.0
        assert evidence_w2.details["score_factors"]["width"] == 0.7

    def test_more_layouts_not_alone_dominates_score(self):
        """R331: 不能只因 layout 数量多就高分

        2 个完美 layout（一一映射、高主值率）的分数应与 5 个 layout 接近，
        因为 layout_count 权重仅 0.15，且 cap 在 5。
        """
        # 2 layouts, perfect ratios
        ev_2 = detect_type_or_opcode(
            {"L1": b'\x01', "L2": b'\x02'},
            self._make_alignment_key(),
            per_layout_dominant_ratios={"L1": 1.0, "L2": 1.0},
        )
        # 5 layouts, perfect ratios
        ev_5 = detect_type_or_opcode(
            {"L1": b'\x01', "L2": b'\x02', "L3": b'\x03', "L4": b'\x04', "L5": b'\x05'},
            self._make_alignment_key(),
            per_layout_dominant_ratios={
                "L1": 1.0, "L2": 1.0, "L3": 1.0, "L4": 1.0, "L5": 1.0
            },
        )
        assert ev_2 is not None
        assert ev_5 is not None
        # 5 layouts 分数确实更高，但差距不应超过 layout_count 权重 0.15
        diff = ev_5.score - ev_2.score
        assert diff <= 0.15 + 0.001, (
            f"Score difference {diff} exceeds layout_count weight 0.15, "
            f"layout_count should not dominate"
        )

    def test_per_layout_dominant_ratio_affects_score(self):
        """R331: per_layout_dominant_ratio 影响评分"""
        layout_dominant_values = {"L1": b'\x01', "L2": b'\x02'}
        # 高主值率
        ev_high = detect_type_or_opcode(
            layout_dominant_values,
            self._make_alignment_key(),
            per_layout_dominant_ratios={"L1": 1.0, "L2": 1.0},
        )
        # 中等主值率
        ev_mid = detect_type_or_opcode(
            layout_dominant_values,
            self._make_alignment_key(),
            per_layout_dominant_ratios={"L1": 0.6, "L2": 0.7},
        )
        assert ev_high is not None
        assert ev_mid is not None
        assert ev_high.score > ev_mid.score

    # ===== 必须负例 =====

    def test_negative_same_dominant_value(self):
        """R331 负例 1: 两个 layout 主值都为 03 → 非一一映射 → None"""
        evidence = detect_type_or_opcode(
            {"L1": b'\x03', "L2": b'\x03'},
            self._make_alignment_key(),
        )
        assert evidence is None

    def test_negative_low_dominant_ratio(self):
        """R331 负例 2: 一个 layout 主值支持率低 → 低于阈值 → None"""
        evidence = detect_type_or_opcode(
            {"L1": b'\x01', "L2": b'\x02'},
            self._make_alignment_key(),
            per_layout_dominant_ratios={"L1": 1.0, "L2": 0.3},  # L2 低于 0.5
            min_dominant_ratio=0.5,
        )
        assert evidence is None

    def test_negative_single_layout(self):
        """R331 负例 3: 只有一个 layout → None"""
        evidence = detect_type_or_opcode(
            {"L1": b'\x01'},
            self._make_alignment_key(),
        )
        assert evidence is None

    def test_negative_unstable_mapping(self):
        """R331 负例 4: 多 layout 但主值与 layout 无稳定关系 → 非一一映射 → None

        L1 和 L2 都有主值 01，L3 有主值 02，不是一一对应。
        """
        evidence = detect_type_or_opcode(
            {"L1": b'\x01', "L2": b'\x01', "L3": b'\x02'},
            self._make_alignment_key(),
        )
        assert evidence is None

    def test_score_not_layout_count_div_10(self):
        """R331: 验证评分不再是 layout_count/10 占位逻辑"""
        # 2 layouts: 旧逻辑 score = 2/10 = 0.2
        # 新逻辑: 多因子加权，至少 0.5+
        evidence = detect_type_or_opcode(
            {"L1": b'\x01', "L2": b'\x02'},
            self._make_alignment_key(),
            per_layout_dominant_ratios={"L1": 1.0, "L2": 1.0},
        )
        assert evidence is not None
        # 旧逻辑会给 0.2，新逻辑应明显高于此值
        assert evidence.score > 0.2, (
            f"Score {evidence.score} should be higher than old layout_count/10=0.2"
        )
