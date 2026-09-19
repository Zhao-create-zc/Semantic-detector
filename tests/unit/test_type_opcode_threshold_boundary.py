"""R402: Type/Opcode 阈值等号边界回归测试

复现 V3 独立审计 MEDIUM-1 缺陷：
    dominant_ratio == threshold 时 Pipeline 与 Detector 不一致。

缺陷根因：
    - Pipeline 预过滤（pipeline.py:345）：``ratio > threshold``（严格大于）
      → 当 ratio == threshold 时为 False，profile 被丢弃，不进入候选
    - Detector 硬性条件 4（type_opcode.py:133）：``ratio < threshold`` 才拒绝
      → 等价 ``ratio >= threshold`` 通过，当 ratio == threshold 时接受

按总体配置语义（与项目其他检测器排除常量字段统一使用 ``>=`` 一致）：
    ratio >= threshold 应允许进入候选分析。

横向对比：identifier.py / length.py / sequence.py / string.py / timestamp.py
排除常量字段均使用 ``profile.dominant_value_ratio >= self.config.constant_support``，
唯独 type_opcode 预过滤使用 ``>``，是项目中的"异类"。

本轮只复现，不修复（R403 将建立共享 Type/Opcode 资格判断函数统一两侧语义）。
修复前：Pipeline 侧测试与一致性测试真实失败；Detector 侧测试通过。
"""

from semantic_detector.config import Config
from semantic_detector.contracts import Direction, TypeOpcodeAlignmentKey
from semantic_detector.detectors.type_opcode import (
    detect_type_or_opcode,
    is_dominant_ratio_qualified,
    is_type_opcode_profile_eligible,
)
from semantic_detector.pipeline.pipeline import DetectionPipeline
from semantic_detector.profiling.profile_builder import FieldProfile


def _make_profile(
    layout_id: str,
    dominant_value_hex: str,
    dominant_value_ratio: float = 0.5,
    width_mode: int = 1,
    field_index: int = 0,
) -> FieldProfile:
    """构造 FieldProfile（默认 ratio=0.5，与默认 threshold 对齐）"""
    return FieldProfile(
        layout_id=layout_id,
        direction=Direction.REQUEST.value,
        field_index=field_index,
        sample_count=10,
        width_min=width_mode,
        width_max=width_mode,
        width_mode=width_mode,
        fixed_width=True,
        start_mode=0,
        dominant_value_ratio=dominant_value_ratio,
        dominant_value_hex=dominant_value_hex,
        dominant_value_count=5,
    )


def _make_alignment_key() -> TypeOpcodeAlignmentKey:
    """构造对齐键（width_mode=1，满足 Detector 硬性条件 2）"""
    return TypeOpcodeAlignmentKey(
        direction=Direction.REQUEST, field_index=0, start_mode=0, width_mode=1
    )


class TestTypeOpcodeThresholdBoundaryR402:
    """R402: 复现 ratio == threshold 时 Pipeline 与 Detector 不一致"""

    def test_detector_accepts_ratio_equal_to_threshold(self):
        """Detector 侧：ratio == threshold 应通过（Detector 用 < 拒绝，等价 >= 通过）

        场景：ratio = 0.50, threshold = 0.50
        预期：detect_type_or_opcode 返回非 None（Detector 语义为 >=）

        本测试体现 Detector 的正确语义，修复前应通过。
        """
        evidence = detect_type_or_opcode(
            {"L1": b'\x01', "L2": b'\x02'},
            _make_alignment_key(),
            per_layout_dominant_ratios={"L1": 0.50, "L2": 0.50},
            min_dominant_ratio=0.50,
        )
        # Detector 语义：ratio >= threshold 通过（仅 ratio < threshold 才拒绝）
        assert evidence is not None, (
            "Detector 应在 ratio == threshold (0.50 == 0.50) 时通过（>= 语义），"
            "但返回 None——Detector 阈值语义不符合总体配置要求"
        )

    def test_pipeline_should_accept_ratio_equal_to_threshold(self):
        """Pipeline 侧：ratio == threshold 应允许进入候选分析（按 >= 语义）

        场景：ratio = 0.50, threshold = 0.50（默认 config）
        预期按总体配置语义：ratio >= threshold 应允许进入候选分析，
        最终产生至少 1 个 type_control prediction。

        实际（缺陷）：Pipeline 预过滤 ``ratio > threshold`` 为 False，
        profile 被丢弃，type_control_count == 0。

        本测试复现缺陷，修复前应真实失败（R403 修复后转通过）。
        """
        # 默认 config: type_opcode_min_dominant_ratio = 0.50
        pipeline = DetectionPipeline()
        profiles = [
            _make_profile("layout_0", "01", dominant_value_ratio=0.50),
            _make_profile("layout_1", "02", dominant_value_ratio=0.50),
            _make_profile("layout_2", "03", dominant_value_ratio=0.50),
        ]

        predictions = pipeline.detect_fields(profiles)

        type_control_count = sum(
            1 for p in predictions if p.coarse_label == "type_control"
        )
        # 总体配置语义：ratio >= threshold 应允许进入候选分析
        assert type_control_count >= 1, (
            "MEDIUM-1 缺陷复现：Pipeline 预过滤使用 > 严格大于，"
            "当 ratio == threshold (0.50 == 0.50) 时错误丢弃 profile，"
            "导致 type_control 漏检。应使用 >= 语义让该 profile 进入候选。"
        )

    def test_pipeline_and_detector_semantic_consistency_at_boundary(self):
        """一致性：Pipeline 与 Detector 在 ratio == threshold 时语义必须一致

        按总体配置语义（ratio >= threshold 通过），两侧都应接受。
        实际不一致：Detector 接受，Pipeline 拒绝。

        本测试复现"不一致"这一核心缺陷，修复前应真实失败。
        """
        threshold = 0.50
        ratio = 0.50

        # Detector 侧：直接调用 detect_type_or_opcode
        detector_evidence = detect_type_or_opcode(
            {"L1": b'\x01', "L2": b'\x02'},
            _make_alignment_key(),
            per_layout_dominant_ratios={"L1": ratio, "L2": ratio},
            min_dominant_ratio=threshold,
        )
        detector_accepts = detector_evidence is not None

        # Pipeline 侧：通过 detect_fields 端到端验证
        config = Config(type_opcode_min_dominant_ratio=threshold)
        pipeline = DetectionPipeline(config=config)
        profiles = [
            _make_profile("layout_0", "01", dominant_value_ratio=ratio),
            _make_profile("layout_1", "02", dominant_value_ratio=ratio),
            _make_profile("layout_2", "03", dominant_value_ratio=ratio),
        ]
        predictions = pipeline.detect_fields(profiles)
        pipeline_accepts = any(
            p.coarse_label == "type_control" for p in predictions
        )

        # 两侧语义必须一致
        assert detector_accepts == pipeline_accepts, (
            f"Pipeline 与 Detector 在 ratio == threshold ({ratio} == {threshold}) "
            f"时语义不一致：Detector accepts={detector_accepts}, "
            f"Pipeline accepts={pipeline_accepts}。"
            f"按总体配置语义（ratio >= threshold 通过），两侧都应接受。"
        )

    def test_pipeline_accepts_ratio_strictly_above_threshold(self):
        """对照测试：ratio 略高于 threshold 时两侧都应接受（证明仅等号边界不一致）

        场景：ratio = 0.51, threshold = 0.50
        预期：Pipeline 与 Detector 都接受（> 和 >= 在 ratio > threshold 时行为相同）

        本测试作为对照，修复前后都应通过，证明缺陷仅在等号边界。
        """
        config = Config(type_opcode_min_dominant_ratio=0.50)
        pipeline = DetectionPipeline(config=config)
        profiles = [
            _make_profile("layout_0", "01", dominant_value_ratio=0.51),
            _make_profile("layout_1", "02", dominant_value_ratio=0.51),
            _make_profile("layout_2", "03", dominant_value_ratio=0.51),
        ]

        predictions = pipeline.detect_fields(profiles)
        type_control_count = sum(
            1 for p in predictions if p.coarse_label == "type_control"
        )
        # ratio > threshold 时 Pipeline 与 Detector 行为一致，都应接受
        assert type_control_count >= 1, (
            "对照测试：ratio=0.51 > threshold=0.50 时 Pipeline 应接受 profile "
            "并检测到 type_control（> 与 >= 在严格大于时行为相同）"
        )


class TestIsDominantRatioQualifiedR403:
    """R403: is_dominant_ratio_qualified 共享比较函数"""

    def test_ratio_equal_to_threshold_passes(self):
        """ratio == threshold 通过（>= 语义，MEDIUM-1 修复核心）"""
        assert is_dominant_ratio_qualified(0.50, 0.50) is True

    def test_ratio_above_threshold_passes(self):
        """ratio > threshold 通过"""
        assert is_dominant_ratio_qualified(0.51, 0.50) is True

    def test_ratio_below_threshold_rejected(self):
        """ratio < threshold 拒绝"""
        assert is_dominant_ratio_qualified(0.49, 0.50) is False

    def test_boundary_at_zero(self):
        """边界：threshold=0.0 时任何 ratio >= 0 通过"""
        assert is_dominant_ratio_qualified(0.0, 0.0) is True

    def test_boundary_at_one(self):
        """边界：ratio=1.0, threshold=1.0 通过"""
        assert is_dominant_ratio_qualified(1.0, 1.0) is True


class TestIsTypeOpcodeProfileEligibleR403:
    """R403: is_type_opcode_profile_eligible 共享资格判断函数"""

    def test_eligible_profile_at_boundary_ratio(self):
        """合法 profile + ratio == threshold → True（MEDIUM-1 修复核心）"""
        profile = _make_profile("l0", "01", dominant_value_ratio=0.50)
        config = Config()
        assert is_type_opcode_profile_eligible(profile, config) is True

    def test_eligible_profile_above_threshold(self):
        """合法 profile + ratio > threshold → True"""
        profile = _make_profile("l0", "01", dominant_value_ratio=0.80)
        config = Config()
        assert is_type_opcode_profile_eligible(profile, config) is True

    def test_rejected_below_threshold(self):
        """ratio < threshold → False"""
        profile = _make_profile("l0", "01", dominant_value_ratio=0.49)
        config = Config()
        assert is_type_opcode_profile_eligible(profile, config) is False

    def test_rejected_none_dominant_value_hex(self):
        """dominant_value_hex = None（tie 场景）→ False"""
        profile = _make_profile("l0", "01", dominant_value_ratio=0.80)
        profile.dominant_value_hex = None
        config = Config()
        assert is_type_opcode_profile_eligible(profile, config) is False

    def test_rejected_width_mode_too_large(self):
        """width_mode > 2（教程 10.3 硬性条件 2）→ False"""
        profile = _make_profile("l0", "01", dominant_value_ratio=0.80, width_mode=3)
        config = Config()
        assert is_type_opcode_profile_eligible(profile, config) is False

    def test_rejected_zero_sample_count(self):
        """sample_count = 0 → False"""
        profile = _make_profile("l0", "01", dominant_value_ratio=0.80)
        profile.sample_count = 0
        config = Config()
        assert is_type_opcode_profile_eligible(profile, config) is False

    def test_rejected_empty_direction(self):
        """direction 为空 → False"""
        profile = _make_profile("l0", "01", dominant_value_ratio=0.80)
        profile.direction = ""
        config = Config()
        assert is_type_opcode_profile_eligible(profile, config) is False

    def test_rejected_negative_field_index(self):
        """field_index < 0 → False"""
        profile = _make_profile("l0", "01", dominant_value_ratio=0.80)
        profile.field_index = -1
        config = Config()
        assert is_type_opcode_profile_eligible(profile, config) is False

    def test_rejected_negative_start_mode(self):
        """start_mode < 0 → False"""
        profile = _make_profile("l0", "01", dominant_value_ratio=0.80)
        profile.start_mode = -1
        config = Config()
        assert is_type_opcode_profile_eligible(profile, config) is False

    def test_custom_threshold_config(self):
        """自定义阈值 config：ratio=0.4, threshold=0.4 → True（>= 语义）"""
        profile = _make_profile("l0", "01", dominant_value_ratio=0.40)
        config = Config(type_opcode_min_dominant_ratio=0.40)
        assert is_type_opcode_profile_eligible(profile, config) is True
