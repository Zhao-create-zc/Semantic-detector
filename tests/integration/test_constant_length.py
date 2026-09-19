"""常量与长度检测器联合回归测试

测试同一数据同时运行两个检测器，验证候选完整且无异常。
"""

import struct
import tempfile
from pathlib import Path

import pytest
from semantic_detector.detectors.constant import ConstantDetector
from semantic_detector.detectors.length import LengthDetector
from semantic_detector.detectors.sequence import SequenceDetector
from semantic_detector.config import Config
from semantic_detector.contracts import FieldKey, FieldSample, Direction
from semantic_detector.profiling.profile_builder import FieldProfile, build_field_profile
from semantic_detector.io.exporters import export_field_profiles, import_field_profiles
from semantic_detector.pipeline.pipeline import DetectionPipeline


class TestConstantLengthIntegration:
    """常量与长度检测器联合测试"""
    
    def test_constant_field(self):
        """常量字段：ConstantDetector 输出证据，LengthDetector 不输出"""
        config = Config(
            min_samples=8,
            constant_support=0.98,
            length_support=0.90
        )
        
        constant_detector = ConstantDetector(config)
        length_detector = LengthDetector(config)
        
        # 创建画像：常量字段
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=2,
            unique_value_count=1,
            dominant_value_ratio=1.0,
            numeric_be_message_length_correlation=0.95,
            numeric_be_remaining_bytes_correlation=None
        )
        
        # 运行两个检测器
        constant_evidences = constant_detector.detect(profile)
        length_evidences = length_detector.detect(profile)
        
        # ConstantDetector 应该输出证据
        assert len(constant_evidences) == 1
        assert constant_evidences[0].coarse_label == "constant"
        
        # LengthDetector 不应该输出证据（常量字段被排除）
        assert len(length_evidences) == 0
    
    def test_length_field(self):
        """长度字段：LengthDetector 输出证据，ConstantDetector 不输出"""
        config = Config(
            min_samples=8,
            constant_support=0.98,
            length_support=0.90
        )
        
        constant_detector = ConstantDetector(config)
        length_detector = LengthDetector(config)
        
        # 创建画像：长度字段（非常量）
        # R276：使用 exact_support 替代 correlation，并设置 distinct_value_count >= 2（教程 8.4）
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=2,
            unique_value_count=50,
            dominant_value_ratio=0.5,
            numeric_be_message_length_exact_support=0.95,
            numeric_be_remaining_bytes_exact_support=None,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
        )
        
        # 运行两个检测器
        constant_evidences = constant_detector.detect(profile)
        length_evidences = length_detector.detect(profile)
        
        # ConstantDetector 不应该输出证据
        assert len(constant_evidences) == 0
        
        # LengthDetector 应该输出证据
        assert len(length_evidences) == 1
        assert length_evidences[0].coarse_label == "length"
    
    def test_neither_constant_nor_length(self):
        """既非常量也非长度：两个检测器都不输出"""
        config = Config(
            min_samples=8,
            constant_support=0.98,
            length_support=0.90
        )
        
        constant_detector = ConstantDetector(config)
        length_detector = LengthDetector(config)
        
        # 创建画像：既非常量也非长度
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=2,
            unique_value_count=50,
            dominant_value_ratio=0.5,
            numeric_be_message_length_correlation=0.50,
            numeric_be_remaining_bytes_correlation=None
        )
        
        # 运行两个检测器
        constant_evidences = constant_detector.detect(profile)
        length_evidences = length_detector.detect(profile)
        
        # 两个检测器都不应该输出证据
        assert len(constant_evidences) == 0
        assert len(length_evidences) == 0
    
    def test_insufficient_samples(self):
        """样本不足：两个检测器都输出 abstain"""
        config = Config(
            min_samples=8,
            constant_support=0.98,
            length_support=0.90
        )
        
        constant_detector = ConstantDetector(config)
        length_detector = LengthDetector(config)
        
        # 创建画像：样本不足
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=5,
            fixed_width=True,
            width_mode=2,
            unique_value_count=1,
            dominant_value_ratio=1.0,
            numeric_be_message_length_correlation=0.95,
            numeric_be_remaining_bytes_correlation=None
        )
        
        # 运行两个检测器
        constant_evidences = constant_detector.detect(profile)
        length_evidences = length_detector.detect(profile)
        
        # 两个检测器都应该输出 abstain
        assert len(constant_evidences) == 1
        assert constant_evidences[0].is_hard_evidence is False
        assert constant_evidences[0].reason_code == "insufficient_samples"
        
        assert len(length_evidences) == 1
        assert length_evidences[0].is_hard_evidence is False
        assert length_evidences[0].reason_code == "insufficient_samples"
    
    def test_both_detectors_no_exception(self):
        """两个检测器都不抛异常"""
        config = Config(
            min_samples=8,
            constant_support=0.98,
            length_support=0.90
        )
        
        constant_detector = ConstantDetector(config)
        length_detector = LengthDetector(config)
        
        # 创建画像
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=2,
            unique_value_count=50,
            dominant_value_ratio=0.5,
            numeric_be_message_length_correlation=0.95,
            numeric_be_remaining_bytes_correlation=0.93
        )
        
        # 运行两个检测器，不应该抛异常
        try:
            constant_evidences = constant_detector.detect(profile)
            length_evidences = length_detector.detect(profile)
        except Exception as e:
            pytest.fail(f"检测器抛出异常: {e}")
        
        # 验证结果
        assert isinstance(constant_evidences, list)
        assert isinstance(length_evidences, list)
    
    def test_evidence_structure_consistent(self):
        """证据结构一致"""
        config = Config(
            min_samples=8,
            constant_support=0.98,
            length_support=0.90
        )
        
        constant_detector = ConstantDetector(config)
        length_detector = LengthDetector(config)
        
        # 创建画像
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=2,
            unique_value_count=50,
            dominant_value_ratio=0.5,
            numeric_be_message_length_correlation=0.95,
            numeric_be_remaining_bytes_correlation=None
        )
        
        # 运行两个检测器
        constant_evidences = constant_detector.detect(profile)
        length_evidences = length_detector.detect(profile)
        
        # 验证证据结构
        if len(constant_evidences) > 0:
            evidence = constant_evidences[0]
            assert hasattr(evidence, 'detector')
            assert hasattr(evidence, 'coarse_label')
            assert hasattr(evidence, 'fine_label')
            assert hasattr(evidence, 'score')
            assert hasattr(evidence, 'is_hard_evidence')
            assert hasattr(evidence, 'reason_code')
            assert hasattr(evidence, 'details')
        
        if len(length_evidences) > 0:
            evidence = length_evidences[0]
            assert hasattr(evidence, 'detector')
            assert hasattr(evidence, 'coarse_label')
            assert hasattr(evidence, 'fine_label')
            assert hasattr(evidence, 'score')
            assert hasattr(evidence, 'is_hard_evidence')
            assert hasattr(evidence, 'reason_code')
            assert hasattr(evidence, 'details')
    
    def test_multiple_profiles(self):
        """多个画像：每个画像都运行两个检测器"""
        config = Config(
            min_samples=8,
            constant_support=0.98,
            length_support=0.90
        )
        
        constant_detector = ConstantDetector(config)
        length_detector = LengthDetector(config)
        
        # 创建多个画像
        profiles = [
            FieldProfile(
                layout_id="layout1",
                direction="up",
                field_index=0,
                sample_count=100,
                fixed_width=True,
                width_mode=2,
                unique_value_count=1,
                dominant_value_ratio=1.0,
                numeric_be_message_length_correlation=0.95,
                numeric_be_remaining_bytes_correlation=None
            ),
            FieldProfile(
                layout_id="layout2",
                direction="up",
                field_index=0,
                sample_count=100,
                fixed_width=True,
                width_mode=2,
                unique_value_count=50,
                dominant_value_ratio=0.5,
                numeric_be_message_length_correlation=0.95,
                numeric_be_remaining_bytes_correlation=None
            ),
            FieldProfile(
                layout_id="layout3",
                direction="up",
                field_index=0,
                sample_count=100,
                fixed_width=True,
                width_mode=2,
                unique_value_count=50,
                dominant_value_ratio=0.5,
                numeric_be_message_length_correlation=0.50,
                numeric_be_remaining_bytes_correlation=None
            )
        ]
        
        # 对每个画像运行两个检测器
        for profile in profiles:
            constant_evidences = constant_detector.detect(profile)
            length_evidences = length_detector.detect(profile)

            # 验证结果
            assert isinstance(constant_evidences, list)
            assert isinstance(length_evidences, list)


class TestLengthSequenceConflictEndToEndR293:
    """R293: 端到端 length+sequence 冲突回归测试

    04 任务表 R293：
    "新增端到端 length+sequence 冲突回归测试 | tests/integration/test_constant_length.py |
     JSONL→run | 最终 prediction 为 length"

    验证完整链路：
    1. 构造同时触发 length 和 sequence 的合成 FieldSample
       （field_bytes 解码值 = message_length 且严格递增）
    2. build_field_profile 生成 profile
    3. export_field_profiles 导出到 JSONL
    4. import_field_profiles 重新导入（round-trip）
    5. DetectionPipeline.detect_field 运行
    6. 最终 prediction.coarse_label == "length"（不是 sequence，不是 unknown）

    R288 length-vs-sequence 冲突规则应在 ambiguity 之前触发，length 胜出。
    """

    def _make_length_sequence_samples(self, count: int = 10):
        """构造同时触发 length 和 sequence 的样本

        消息长度从 10 递增到 19，field_bytes = 2 字节大端编码的 message_length。
        - length: value(10+i) == message_length(10+i) → exact_support = 1.0
        - sequence: 10, 11, ..., 19 严格递增 → strictly_increasing = 1.0
        """
        field_key = FieldKey(
            layout_id="len_seq_layout",
            direction=Direction.REQUEST,
            field_index=0,
        )
        samples = []
        for i in range(count):
            message_length = 10 + i
            field_bytes = struct.pack('>H', message_length)
            samples.append(FieldSample(
                message_id=f"msg_{i}",
                field_key=field_key,
                field_bytes=field_bytes,
                start=0,
                end=2,
                message_length=message_length,
                remaining_bytes=0,
                capture_time=None,
            ))
        return field_key, samples

    def test_profile_triggers_both_length_and_sequence(self):
        """build_field_profile 生成的 profile 同时触发 length 和 sequence 检测器"""
        field_key, samples = self._make_length_sequence_samples()
        profile = build_field_profile(field_key, samples)

        # length 前置条件
        assert profile.fixed_width is True
        assert profile.width_mode == 2
        assert profile.dominant_value_ratio < 0.98  # 非常量
        assert profile.numeric_be_distinct_value_count >= 2  # 教程 8.4

        # length exact_support 应为 1.0（value == message_length）
        assert profile.numeric_be_message_length_exact_support == 1.0

        # sequence strictly_increasing 应为 1.0
        assert profile.numeric_be_strictly_increasing_ratio == 1.0

        # 分别运行两个检测器，都应输出证据
        config = Config()
        length_detector = LengthDetector(config)
        sequence_detector = SequenceDetector(config)

        length_evidences = length_detector.detect(profile)
        sequence_evidences = sequence_detector.detect(profile)

        assert len(length_evidences) >= 1
        assert length_evidences[0].coarse_label == "length"
        assert length_evidences[0].is_hard_evidence is True

        assert len(sequence_evidences) >= 1
        assert sequence_evidences[0].coarse_label == "sequence_or_counter"
        assert sequence_evidences[0].is_hard_evidence is True

    def test_profile_jsonl_round_trip_preserves_conflict_evidence(self):
        """profile JSONL 导出/导入 round-trip 不丢 length 和 sequence 证据"""
        field_key, samples = self._make_length_sequence_samples()
        profile = build_field_profile(field_key, samples)

        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.jsonl', delete=False, encoding='utf-8'
        ) as f:
            output_path = f.name
        try:
            export_field_profiles([profile], output_path)
            imported = import_field_profiles(output_path)
            assert len(imported) == 1
            imported_profile = imported[0]

            # round-trip 等价：length 和 sequence 关键字段
            assert imported_profile.numeric_be_message_length_exact_support == \
                profile.numeric_be_message_length_exact_support
            assert imported_profile.numeric_be_strictly_increasing_ratio == \
                profile.numeric_be_strictly_increasing_ratio
            assert imported_profile.numeric_be_distinct_value_count == \
                profile.numeric_be_distinct_value_count
            assert imported_profile.dominant_value_ratio == \
                profile.dominant_value_ratio
            assert imported_profile.fixed_width == profile.fixed_width
            assert imported_profile.width_mode == profile.width_mode
        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_pipeline_prediction_is_length(self):
        """R293 完成标准：JSONL→run 后最终 prediction 为 length

        真正 CLI 路径：build_field_profile → export → import → DetectionPipeline.detect_field。
        length 和 sequence 同时命中时，R288 length-vs-sequence 冲突规则让 length 胜出。
        """
        field_key, samples = self._make_length_sequence_samples()
        profile = build_field_profile(field_key, samples)

        # JSONL round-trip
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.jsonl', delete=False, encoding='utf-8'
        ) as f:
            output_path = f.name
        try:
            export_field_profiles([profile], output_path)
            imported = import_field_profiles(output_path)
            assert len(imported) == 1
            imported_profile = imported[0]

            # Pipeline 运行
            pipeline = DetectionPipeline()
            prediction = pipeline.detect_field(imported_profile)

            # R293 完成标准：最终 prediction 为 length
            assert prediction.coarse_label == "length"
            assert prediction.abstained is False
            assert prediction.prediction_status == "confirmed"

            # evidence 列表应同时包含 length 和 sequence（length 在前）
            length_evidences = [
                e for e in prediction.evidence if e.coarse_label == "length"
            ]
            sequence_evidences = [
                e for e in prediction.evidence if e.coarse_label == "sequence_or_counter"
            ]
            assert len(length_evidences) >= 1
            assert len(sequence_evidences) >= 1

            # primary（evidence[0]）应为 length
            assert prediction.evidence[0].coarse_label == "length"
            assert prediction.evidence[0].is_hard_evidence is True
        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_pipeline_prediction_not_unknown_ambiguous(self):
        """R293: length+sequence 冲突时 prediction 不返回 unknown(ambiguous)

        教程 11.4：ambiguity 不能在专项冲突规则前。
        修复前：length=1.0/sequence=1.0 同分时 check_ambiguity 直接返回 unknown(ambiguous)。
        修复后：R288 length-vs-sequence 冲突规则在 ambiguity 前触发，length 胜出。
        """
        field_key, samples = self._make_length_sequence_samples()
        profile = build_field_profile(field_key, samples)

        pipeline = DetectionPipeline()
        prediction = pipeline.detect_field(profile)

        # 不应是 unknown
        assert prediction.coarse_label != "unknown"
        assert prediction.abstained is False
        assert prediction.coarse_label == "length"

    def test_sequence_in_alternatives(self):
        """R293: sequence_or_counter 在 alternatives 中（保留为备选）

        教程 11.3：length 胜出，sequence_or_counter 保留为 alternative。
        """
        field_key, samples = self._make_length_sequence_samples()
        profile = build_field_profile(field_key, samples)

        pipeline = DetectionPipeline()
        prediction = pipeline.detect_field(profile)

        # primary 是 length
        assert prediction.coarse_label == "length"

        # alternatives 应包含 sequence_or_counter
        alt_labels = [a["coarse_label"] for a in prediction.alternatives]
        assert "sequence_or_counter" in alt_labels

    def test_length_with_offset_zero_not_conflict_with_sequence(self):
        """R293: length offset==0（exact）与 sequence 冲突时 length 仍胜出

        构造 message_length 固定为 10，但 field_bytes 编码值递增。
        此时 length 不命中（因为 value != message_length），
        只有 sequence 命中。这是一个对照组，验证冲突规则只在两者同时命中时触发。
        """
        field_key = FieldKey(
            layout_id="seq_only_layout",
            direction=Direction.REQUEST,
            field_index=0,
        )
        samples = []
        for i in range(10):
            # message_length 固定 10，field_bytes 递增（不等于 message_length）
            field_bytes = struct.pack('>H', 100 + i)
            samples.append(FieldSample(
                message_id=f"msg_{i}",
                field_key=field_key,
                field_bytes=field_bytes,
                start=0,
                end=2,
                message_length=10,
                remaining_bytes=0,
                capture_time=None,
            ))

        profile = build_field_profile(field_key, samples)

        pipeline = DetectionPipeline()
        prediction = pipeline.detect_field(profile)

        # 只有 sequence 命中（length 不命中因为 value != message_length）
        # 此时没有冲突，sequence 正常胜出
        assert prediction.coarse_label == "sequence_or_counter"
