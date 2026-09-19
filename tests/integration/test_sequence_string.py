"""R131: 序列与字符串联合回归测试

验证 SequenceDetector 和 StringDetector 在同一数据上的行为，确保结果互不污染。
"""

import struct
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from semantic_detector.config import Config
from semantic_detector.contracts import FieldKey, FieldSample, Direction
from semantic_detector.detectors.sequence import SequenceDetector
from semantic_detector.detectors.string import StringDetector
from semantic_detector.detectors.timestamp import TimestampDetector
from semantic_detector.profiling.profile_builder import FieldProfile, build_field_profile
from semantic_detector.io.exporters import export_field_profiles, import_field_profiles
from semantic_detector.pipeline.pipeline import DetectionPipeline


class TestSequenceStringIntegration:
    """Tests for SequenceDetector and StringDetector integration."""
    
    def test_sequence_field_not_detected_as_string(self):
        """Sequence field should not be detected as string."""
        config = Config()
        sequence_detector = SequenceDetector(config)
        string_detector = StringDetector(config)
        
        # Create a sequence profile (递增数值)
        sequence_profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.0,
            all_zero_sample_ratio=0.0,
            unique_ratio=0.90,
            numeric_be_strictly_increasing_ratio=0.95,
            numeric_be_step_one_ratio=0.90,
            numeric_le_strictly_increasing_ratio=0.0,
            numeric_le_step_one_ratio=0.0,
            printable_ascii_ratio=0.0,
            nonempty_string_ratio=0.0,
            utf8_decode_success_ratio=0.0
        )
        
        # SequenceDetector should detect sequence
        sequence_evidences = sequence_detector.detect(sequence_profile)
        assert len(sequence_evidences) >= 1
        assert sequence_evidences[0].coarse_label == "sequence_or_counter"
        
        # StringDetector should not detect string
        string_evidences = string_detector.detect(sequence_profile)
        assert len(string_evidences) == 0
    
    def test_string_field_not_detected_as_sequence(self):
        """String field should not be detected as sequence."""
        config = Config()
        sequence_detector = SequenceDetector(config)
        string_detector = StringDetector(config)
        
        # Create a string profile (ASCII string)
        string_profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=10,
            dominant_value_ratio=0.0,
            all_zero_sample_ratio=0.0,
            unique_ratio=0.90,
            numeric_be_strictly_increasing_ratio=0.0,
            numeric_be_step_one_ratio=0.0,
            numeric_le_strictly_increasing_ratio=0.0,
            numeric_le_step_one_ratio=0.0,
            printable_ascii_ratio=0.95,
            nonempty_string_ratio=0.95,
            utf8_decode_success_ratio=0.95
        )
        
        # StringDetector should detect string
        string_evidences = string_detector.detect(string_profile)
        assert len(string_evidences) >= 1
        assert string_evidences[0].coarse_label == "string"
        
        # SequenceDetector should not detect sequence
        sequence_evidences = sequence_detector.detect(string_profile)
        assert len(sequence_evidences) == 0
    
    def test_both_detectors_on_mixed_data(self):
        """Both detectors should work independently on mixed data."""
        config = Config()
        sequence_detector = SequenceDetector(config)
        string_detector = StringDetector(config)
        
        # Create a mixed profile (neither sequence nor string)
        mixed_profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.0,
            all_zero_sample_ratio=0.0,
            unique_ratio=0.50,
            numeric_be_strictly_increasing_ratio=0.30,
            numeric_be_step_one_ratio=0.20,
            numeric_le_strictly_increasing_ratio=0.30,
            numeric_le_step_one_ratio=0.20,
            printable_ascii_ratio=0.50,
            nonempty_string_ratio=0.50,
            utf8_decode_success_ratio=0.50
        )
        
        # Neither detector should detect anything
        sequence_evidences = sequence_detector.detect(mixed_profile)
        string_evidences = string_detector.detect(mixed_profile)
        
        assert len(sequence_evidences) == 0
        assert len(string_evidences) == 0
    
    def test_detectors_do_not_modify_profile(self):
        """Detectors should not modify the input profile."""
        config = Config()
        sequence_detector = SequenceDetector(config)
        string_detector = StringDetector(config)
        
        # Create a profile
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.0,
            all_zero_sample_ratio=0.0,
            unique_ratio=0.90,
            numeric_be_strictly_increasing_ratio=0.95,
            numeric_be_step_one_ratio=0.90,
            numeric_le_strictly_increasing_ratio=0.0,
            numeric_le_step_one_ratio=0.0,
            printable_ascii_ratio=0.50,
            nonempty_string_ratio=0.50,
            utf8_decode_success_ratio=0.50
        )
        
        # Store original values
        original_sample_count = profile.sample_count
        original_width_mode = profile.width_mode
        original_unique_ratio = profile.unique_ratio
        
        # Run both detectors
        sequence_detector.detect(profile)
        string_detector.detect(profile)
        
        # Profile should not be modified
        assert profile.sample_count == original_sample_count
        assert profile.width_mode == original_width_mode
        assert profile.unique_ratio == original_unique_ratio
    
    def test_detectors_independent_execution_order(self):
        """Detectors should produce same results regardless of execution order."""
        config = Config()
        sequence_detector = SequenceDetector(config)
        string_detector = StringDetector(config)
        
        # Create a sequence profile
        sequence_profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.0,
            all_zero_sample_ratio=0.0,
            unique_ratio=0.90,
            numeric_be_strictly_increasing_ratio=0.95,
            numeric_be_step_one_ratio=0.90,
            numeric_le_strictly_increasing_ratio=0.0,
            numeric_le_step_one_ratio=0.0,
            printable_ascii_ratio=0.0,
            nonempty_string_ratio=0.0,
            utf8_decode_success_ratio=0.0
        )
        
        # Run sequence first, then string
        seq_first = sequence_detector.detect(sequence_profile)
        str_second = string_detector.detect(sequence_profile)
        
        # Run string first, then sequence
        str_first = string_detector.detect(sequence_profile)
        seq_second = sequence_detector.detect(sequence_profile)
        
        # Results should be identical regardless of order
        assert len(seq_first) == len(seq_second)
        assert len(str_first) == len(str_second)
        if seq_first:
            assert seq_first[0].coarse_label == seq_second[0].coarse_label
            assert seq_first[0].fine_label == seq_second[0].fine_label


class TestTimestampSequenceConflictEndToEndR294:
    """R294: 端到端 timestamp+sequence 冲突回归测试

    04 任务表 R294：
    "新增端到端 timestamp+sequence 冲突回归测试 | tests/integration/test_sequence_string.py |
     JSONL→run | 最终 prediction 为 timestamp"

    验证完整链路：
    1. 构造同时触发 timestamp 和 sequence 的合成 FieldSample
       （field_bytes 是 4 字节 Unix 秒 BE 时间戳，capture_time 自然递增）
    2. build_field_profile 生成 profile
    3. export_field_profiles 导出到 JSONL
    4. import_field_profiles 重新导入（round-trip）
    5. DetectionPipeline.detect_field 运行
    6. 最终 prediction.coarse_label == "timestamp"（不是 sequence，不是 unknown）

    R289 timestamp-vs-sequence 冲突规则应在 ambiguity 之前触发，timestamp 胜出。
    """

    def _make_timestamp_sequence_samples(self, count: int = 10):
        """构造同时触发 timestamp 和 sequence 的样本

        capture_time 从 2020-01-01 00:00 UTC 开始每小时递增，
        field_bytes 是对应 Unix 秒的 4 字节大端编码。

        - timestamp: value 在 capture_time 范围内 → support = 1.0
        - sequence: unix_seconds 严格递增 → strictly_increasing = 1.0
        """
        base_time = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        field_key = FieldKey(
            layout_id="ts_seq_layout",
            direction=Direction.REQUEST,
            field_index=0,
        )
        samples = []
        for i in range(count):
            capture_time = base_time + timedelta(hours=i)
            unix_seconds = int(capture_time.timestamp())
            field_bytes = struct.pack('>I', unix_seconds)
            samples.append(FieldSample(
                message_id=f"msg_{i}",
                field_key=field_key,
                field_bytes=field_bytes,
                start=0,
                end=4,
                message_length=4,
                remaining_bytes=0,
                capture_time=capture_time,
            ))
        return field_key, samples

    def test_profile_triggers_both_timestamp_and_sequence(self):
        """build_field_profile 生成的 profile 同时触发 timestamp 和 sequence 检测器"""
        field_key, samples = self._make_timestamp_sequence_samples()
        profile = build_field_profile(field_key, samples)

        # timestamp 前置条件
        assert profile.capture_time_count == 10
        assert profile.capture_time_coverage == 1.0
        assert profile.fixed_width is True
        assert profile.width_mode == 4

        # timestamp support 应为 1.0
        assert profile.timestamp_be_unix_seconds_support == 1.0

        # sequence strictly_increasing 应为 1.0
        assert profile.numeric_be_strictly_increasing_ratio == 1.0

        # 分别运行两个检测器，都应输出证据
        config = Config()
        timestamp_detector = TimestampDetector(config)
        sequence_detector = SequenceDetector(config)

        timestamp_evidences = timestamp_detector.detect(profile)
        sequence_evidences = sequence_detector.detect(profile)

        assert len(timestamp_evidences) >= 1
        assert timestamp_evidences[0].coarse_label == "timestamp"
        assert timestamp_evidences[0].is_hard_evidence is True

        assert len(sequence_evidences) >= 1
        assert sequence_evidences[0].coarse_label == "sequence_or_counter"
        assert sequence_evidences[0].is_hard_evidence is True

    def test_profile_jsonl_round_trip_preserves_conflict_evidence(self):
        """profile JSONL 导出/导入 round-trip 不丢 timestamp 和 sequence 证据"""
        field_key, samples = self._make_timestamp_sequence_samples()
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

            # round-trip 等价：timestamp 和 sequence 关键字段
            assert imported_profile.timestamp_be_unix_seconds_support == \
                profile.timestamp_be_unix_seconds_support
            assert imported_profile.numeric_be_strictly_increasing_ratio == \
                profile.numeric_be_strictly_increasing_ratio
            assert imported_profile.capture_time_count == profile.capture_time_count
            assert imported_profile.capture_time_coverage == profile.capture_time_coverage
            assert imported_profile.fixed_width == profile.fixed_width
            assert imported_profile.width_mode == profile.width_mode
        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_pipeline_prediction_is_timestamp(self):
        """R294 完成标准：JSONL→run 后最终 prediction 为 timestamp

        真正 CLI 路径：build_field_profile → export → import → DetectionPipeline.detect_field。
        timestamp 和 sequence 同时命中时，R289 timestamp-vs-sequence 冲突规则让 timestamp 胜出。
        """
        field_key, samples = self._make_timestamp_sequence_samples()
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

            # R294 完成标准：最终 prediction 为 timestamp
            assert prediction.coarse_label == "timestamp"
            assert prediction.abstained is False
            assert prediction.prediction_status == "confirmed"

            # evidence 列表应同时包含 timestamp 和 sequence
            timestamp_evidences = [
                e for e in prediction.evidence if e.coarse_label == "timestamp"
            ]
            sequence_evidences = [
                e for e in prediction.evidence if e.coarse_label == "sequence_or_counter"
            ]
            assert len(timestamp_evidences) >= 1
            assert len(sequence_evidences) >= 1

            # primary（evidence[0]）应为 timestamp
            assert prediction.evidence[0].coarse_label == "timestamp"
            assert prediction.evidence[0].is_hard_evidence is True
        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_pipeline_prediction_not_unknown_ambiguous(self):
        """R294: timestamp+sequence 冲突时 prediction 不返回 unknown(ambiguous)

        教程 11.4：ambiguity 不能在专项冲突规则前。
        修复前：timestamp=1.0/sequence=1.0 同分时 check_ambiguity 直接返回 unknown(ambiguous)。
        修复后：R289 timestamp-vs-sequence 冲突规则在 ambiguity 前触发，timestamp 胜出。
        """
        field_key, samples = self._make_timestamp_sequence_samples()
        profile = build_field_profile(field_key, samples)

        pipeline = DetectionPipeline()
        prediction = pipeline.detect_field(profile)

        # 不应是 unknown
        assert prediction.coarse_label != "unknown"
        assert prediction.abstained is False
        assert prediction.coarse_label == "timestamp"

    def test_sequence_in_alternatives(self):
        """R294: sequence_or_counter 在 alternatives 中（保留为备选）

        教程 11.3：时间自然递增的 timestamp 胜出，sequence_or_counter 保留为 alternative。
        """
        field_key, samples = self._make_timestamp_sequence_samples()
        profile = build_field_profile(field_key, samples)

        pipeline = DetectionPipeline()
        prediction = pipeline.detect_field(profile)

        # primary 是 timestamp
        assert prediction.coarse_label == "timestamp"

        # alternatives 应包含 sequence_or_counter
        alt_labels = [a["coarse_label"] for a in prediction.alternatives]
        assert "sequence_or_counter" in alt_labels

    def test_no_capture_time_only_sequence(self):
        """R294: 无 capture_time 时只有 sequence 命中（对照组）

        构造同样的 Unix 秒值，但 capture_time 全部为 None。
        此时 timestamp 不命中，只有 sequence 命中。
        验证冲突规则只在两者同时命中时触发。
        """
        field_key = FieldKey(
            layout_id="seq_only_no_ts_layout",
            direction=Direction.REQUEST,
            field_index=0,
        )
        base_time = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        samples = []
        for i in range(10):
            unix_seconds = int((base_time + timedelta(hours=i)).timestamp())
            field_bytes = struct.pack('>I', unix_seconds)
            samples.append(FieldSample(
                message_id=f"msg_{i}",
                field_key=field_key,
                field_bytes=field_bytes,
                start=0,
                end=4,
                message_length=4,
                remaining_bytes=0,
                capture_time=None,
            ))

        profile = build_field_profile(field_key, samples)

        # capture_time 缺失
        assert profile.capture_time_count == 0
        assert profile.timestamp_be_unix_seconds_support is None

        pipeline = DetectionPipeline()
        prediction = pipeline.detect_field(profile)

        # 只有 sequence 命中（timestamp 不命中因为 capture_time 缺失）
        # 此时没有冲突，sequence 正常胜出
        assert prediction.coarse_label == "sequence_or_counter"
