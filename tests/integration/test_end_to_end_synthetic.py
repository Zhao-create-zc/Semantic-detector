"""端到端集成测试：合成数据集完整流水线

测试使用合成 fixture 数据运行完整的检测流水线，验证 predictions 输出。
"""

import pytest
import struct
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta
from semantic_detector.io.jsonl import read_jsonl_file
from semantic_detector.config import Config
from semantic_detector.contracts import FieldKey, FieldSample, Direction
from semantic_detector.profiling.collector import (
    group_by_layout_and_direction,
    validate_group_field_count,
    record_to_field_samples,
    aggregate_by_field_key,
    mark_insufficient_groups,
)
from semantic_detector.profiling.profile_builder import build_field_profile
from semantic_detector.io.exporters import export_field_profiles, import_field_profiles
from semantic_detector.pipeline.pipeline import DetectionPipeline
from semantic_detector.detectors.constant import ConstantDetector
from semantic_detector.detectors.length import LengthDetector
from semantic_detector.detectors.timestamp import TimestampDetector
from semantic_detector.detectors.sequence import SequenceDetector
from semantic_detector.detectors.string import StringDetector
from semantic_detector.detectors.payload import PayloadDetector
from semantic_detector.detectors.identifier import IdentifierDetector
from semantic_detector.evaluation.ground_truth import read_ground_truth_jsonl, validate_ground_truth
from semantic_detector.evaluation.metrics import (
    align_predictions_with_truth,
    calculate_overall_accuracy,
    calculate_coverage,
    calculate_unknown_rate,
    calculate_covered_accuracy,
    collect_errors,
)


class TestEndToEndSynthetic:
    """端到端合成数据测试"""
    
    def _run_pipeline(self, fixture_path: Path, min_samples: int = 5):
        """运行完整流水线并返回画像和证据"""
        valid, rejected = read_jsonl_file(str(fixture_path))
        
        # 分组
        groups = group_by_layout_and_direction(valid)
        
        # 校验字段数量
        valid_groups, rejected_records = validate_group_field_count(groups)
        
        # 转换为 FieldSample
        all_samples = []
        for key, records in valid_groups.items():
            for record in records:
                all_samples.extend(record_to_field_samples(record))
        
        # 按 FieldKey 聚合
        field_groups = aggregate_by_field_key(all_samples)
        
        # 标记不足
        field_groups, insufficient = mark_insufficient_groups(field_groups, min_samples=min_samples)
        
        # 生成画像
        profiles = []
        for fk, samples in field_groups.items():
            profile = build_field_profile(fk, samples)
            profiles.append(profile)
        
        return profiles, valid, rejected
    
    def test_constant_messages(self):
        """测试常量字段 fixture"""
        fixture_path = Path("tests/fixtures/constant_messages.jsonl")
        if not fixture_path.exists():
            pytest.skip("constant_messages.jsonl not found")
        
        profiles, valid, rejected = self._run_pipeline(fixture_path)
        
        assert len(valid) == 10
        assert len(rejected) == 0
        assert len(profiles) > 0
        
        # 运行检测器
        config = Config(min_samples=5)
        constant_detector = ConstantDetector(config)
        length_detector = LengthDetector(config)
        
        all_evidences = []
        for profile in profiles:
            all_evidences.extend(constant_detector.detect(profile))
            all_evidences.extend(length_detector.detect(profile))
        
        # 应该有检测结果
        assert len(all_evidences) > 0
    
    def test_sequence_messages(self):
        """测试序列字段 fixture"""
        fixture_path = Path("tests/fixtures/sequence.jsonl")
        if not fixture_path.exists():
            pytest.skip("sequence.jsonl not found")
        
        profiles, valid, rejected = self._run_pipeline(fixture_path)
        
        assert len(valid) == 10
        assert len(rejected) == 0
        assert len(profiles) > 0
        
        # 运行检测器
        config = Config(min_samples=5)
        sequence_detector = SequenceDetector(config)
        length_detector = LengthDetector(config)
        
        all_evidences = []
        for profile in profiles:
            all_evidences.extend(sequence_detector.detect(profile))
            all_evidences.extend(length_detector.detect(profile))
        
        # 应该有检测结果
        assert len(all_evidences) > 0
    
    def test_timestamp_seconds_messages(self):
        """测试时间戳秒字段 fixture"""
        fixture_path = Path("tests/fixtures/timestamp_seconds.jsonl")
        if not fixture_path.exists():
            pytest.skip("timestamp_seconds.jsonl not found")
        
        profiles, valid, rejected = self._run_pipeline(fixture_path)
        
        assert len(valid) == 10
        assert len(rejected) == 0
        assert len(profiles) > 0
        
        # 运行检测器
        config = Config(min_samples=5)
        timestamp_detector = TimestampDetector(config)
        
        all_evidences = []
        for profile in profiles:
            all_evidences.extend(timestamp_detector.detect(profile))
        
        # 应该有检测结果
        assert len(all_evidences) > 0
    
    def test_string_ascii_messages(self):
        """测试 ASCII string 字段 fixture"""
        fixture_path = Path("tests/fixtures/string_ascii.jsonl")
        if not fixture_path.exists():
            pytest.skip("string_ascii.jsonl not found")
        
        profiles, valid, rejected = self._run_pipeline(fixture_path)
        
        assert len(valid) == 10
        assert len(rejected) == 0
        assert len(profiles) > 0
        
        # 运行检测器
        config = Config(min_samples=5)
        string_detector = StringDetector(config)
        
        all_evidences = []
        for profile in profiles:
            all_evidences.extend(string_detector.detect(profile))
        
        # 应该有检测结果
        assert len(all_evidences) > 0
    
    def test_payload_messages(self):
        """测试 payload 字段 fixture"""
        fixture_path = Path("tests/fixtures/payload.jsonl")
        if not fixture_path.exists():
            pytest.skip("payload.jsonl not found")
        
        profiles, valid, rejected = self._run_pipeline(fixture_path)
        
        assert len(valid) == 10
        assert len(rejected) == 0
        assert len(profiles) > 0
        
        # 运行检测器
        config = Config(min_samples=5)
        payload_detector = PayloadDetector(config)
        constant_detector = ConstantDetector(config)
        
        all_evidences = []
        for profile in profiles:
            all_evidences.extend(payload_detector.detect(profile))
            all_evidences.extend(constant_detector.detect(profile))
        
        # 应该有检测结果
        assert len(all_evidences) > 0
    
    def test_identifier_messages(self):
        """测试标识符字段 fixture"""
        fixture_path = Path("tests/fixtures/identifier.jsonl")
        if not fixture_path.exists():
            pytest.skip("identifier.jsonl not found")
        
        profiles, valid, rejected = self._run_pipeline(fixture_path)
        
        assert len(valid) == 10
        assert len(rejected) == 0
        assert len(profiles) > 0
        
        # 运行检测器
        config = Config(min_samples=5)
        identifier_detector = IdentifierDetector(config)
        
        all_evidences = []
        for profile in profiles:
            all_evidences.extend(identifier_detector.detect(profile))

        # 应该有检测结果
        assert len(all_evidences) > 0


class TestTimestampProfileInferRoundTrip:
    """R282: profile JSONL→infer 的 timestamp 集成测试

    04 任务表 R282：
    "增加 profile JSONL→infer 的 timestamp 集成测试 | tests/integration/test_end_to_end_synthetic.py |
     profile/infer 两阶段 | 真正 CLI 路径识别 timestamp"

    验证完整链路：
    1. 构造带 capture_time 的合成 FieldSample（4 字节 Unix 秒 BE 时间戳）
    2. build_field_profile 计算 timestamp support
    3. export_field_profiles 导出到 JSONL
    4. import_field_profiles 重新导入（round-trip 不丢证据）
    5. DetectionPipeline.detect_field 识别 timestamp
    """

    def _make_timestamp_samples(self, count: int = 10):
        """构造 count 个 4 字节 Unix 秒 BE 时间戳样本

        capture_time 从 2020-01-01 00:00 UTC 开始每小时递增，
        field_bytes 是对应 Unix 秒的 4 字节大端编码。
        """
        base_time = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        field_key = FieldKey(
            layout_id="ts_layout",
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

    def test_profile_builds_timestamp_support(self):
        """build_field_profile 正确计算 timestamp support"""
        field_key, samples = self._make_timestamp_samples()
        profile = build_field_profile(field_key, samples)

        # capture_time 元数据
        assert profile.capture_time_count == 10
        assert profile.capture_time_coverage == 1.0
        assert profile.capture_time_min is not None
        assert profile.capture_time_max is not None

        # 4 字节固定宽度
        assert profile.fixed_width is True
        assert profile.width_mode == 4

        # Unix 秒 BE support 应为 1.0（所有值都在 capture_time 范围内）
        assert profile.timestamp_be_unix_seconds_support is not None
        assert profile.timestamp_be_unix_seconds_support == 1.0

    def test_profile_jsonl_round_trip_preserves_timestamp(self):
        """profile JSONL 导出/导入 round-trip 不丢 timestamp 证据"""
        field_key, samples = self._make_timestamp_samples()
        profile = build_field_profile(field_key, samples)

        # 导出到临时 JSONL
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.jsonl', delete=False, encoding='utf-8'
        ) as f:
            output_path = f.name
        try:
            export_field_profiles([profile], output_path)

            # 重新导入
            imported = import_field_profiles(output_path)
            assert len(imported) == 1
            imported_profile = imported[0]

            # round-trip 等价：timestamp support 字段
            assert imported_profile.timestamp_be_unix_seconds_support == \
                profile.timestamp_be_unix_seconds_support
            assert imported_profile.timestamp_le_unix_seconds_support == \
                profile.timestamp_le_unix_seconds_support

            # capture_time 元数据 round-trip
            assert imported_profile.capture_time_count == profile.capture_time_count
            assert imported_profile.capture_time_coverage == profile.capture_time_coverage
            assert imported_profile.capture_time_min == profile.capture_time_min
            assert imported_profile.capture_time_max == profile.capture_time_max

            # 宽度与固定宽度
            assert imported_profile.fixed_width is True
            assert imported_profile.width_mode == 4
        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_detector_detects_timestamp_from_imported_profile(self):
        """TimestampDetector.detect 从导入的 profile 识别 timestamp

        真正 CLI 路径：build_field_profile → export → import → TimestampDetector.detect。
        验证导入后的 profile 仍能生成 timestamp hard evidence。
        """
        field_key, samples = self._make_timestamp_samples()
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

            # R280: TimestampDetector.detect(profile) 只读取 profile support 字段
            config = Config(min_samples=8, timestamp_support=0.90)
            detector = TimestampDetector(config)
            evidences = detector.detect(imported_profile)

            assert len(evidences) == 1
            evidence = evidences[0]
            assert evidence.detector == "timestamp"
            assert evidence.coarse_label == "timestamp"
            assert evidence.fine_label == "unix_seconds_be"
            assert evidence.score == 1.0
            assert evidence.is_hard_evidence is True
            assert evidence.reason_code == "value_is_unix_seconds_be"
            assert evidence.details["format"] == "unix_seconds"
            assert evidence.details["endian"] == "be"
            assert evidence.details["byte_width"] == 4
        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_pipeline_evidence_contains_timestamp(self):
        """Pipeline.detect_field 的 evidence 列表包含 timestamp hard evidence

        HIGH-6 resolver 冲突规则在 R287-R295 修复前，timestamp 与其他检测器
        （sequence/payload）同时命中时 primary 可能返回 unknown(ambiguous)。
        但 evidence 列表应包含 timestamp hard evidence 供下游判断。
        本测试验证 profile → pipeline 链路生成包含 timestamp 的 evidence。
        """
        field_key, samples = self._make_timestamp_samples()
        profile = build_field_profile(field_key, samples)

        pipeline = DetectionPipeline()
        prediction = pipeline.detect_field(profile)

        # evidence 列表应包含 timestamp hard evidence
        timestamp_evidences = [
            e for e in prediction.evidence
            if e.coarse_label == "timestamp" and e.is_hard_evidence
        ]
        assert len(timestamp_evidences) >= 1
        ts_ev = timestamp_evidences[0]
        assert ts_ev.fine_label == "unix_seconds_be"
        assert ts_ev.score == 1.0
        assert ts_ev.reason_code == "value_is_unix_seconds_be"

    def test_no_capture_time_not_detected_as_timestamp(self):
        """无 capture_time 的样本不被识别为 timestamp（教程 9.4）"""
        field_key = FieldKey(
            layout_id="ts_layout",
            direction=Direction.REQUEST,
            field_index=0,
        )
        # 同样的 Unix 秒值，但 capture_time 全部为 None
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
        assert profile.capture_time_coverage == 0.0
        assert profile.capture_time_min is None
        assert profile.capture_time_max is None

        # timestamp support 应为 None（教程 9.4）
        assert profile.timestamp_be_unix_seconds_support is None

        # Pipeline evidence 不应包含 timestamp
        pipeline = DetectionPipeline()
        prediction = pipeline.detect_field(profile)
        timestamp_evidences = [
            e for e in prediction.evidence if e.coarse_label == "timestamp"
        ]
        assert len(timestamp_evidences) == 0

    def test_milliseconds_timestamp_round_trip(self):
        """8 字节 Unix 毫秒时间戳 round-trip 与 detector 识别"""
        field_key = FieldKey(
            layout_id="ms_layout",
            direction=Direction.REQUEST,
            field_index=0,
        )
        base_time = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        samples = []
        for i in range(10):
            capture_time = base_time + timedelta(hours=i)
            unix_ms = int(capture_time.timestamp() * 1000)
            field_bytes = struct.pack('>Q', unix_ms)
            samples.append(FieldSample(
                message_id=f"msg_{i}",
                field_key=field_key,
                field_bytes=field_bytes,
                start=0,
                end=8,
                message_length=8,
                remaining_bytes=0,
                capture_time=capture_time,
            ))

        profile = build_field_profile(field_key, samples)
        assert profile.width_mode == 8
        assert profile.timestamp_be_unix_milliseconds_support is not None
        assert profile.timestamp_be_unix_milliseconds_support == 1.0

        # round-trip
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.jsonl', delete=False, encoding='utf-8'
        ) as f:
            output_path = f.name
        try:
            export_field_profiles([profile], output_path)
            imported = import_field_profiles(output_path)
            assert len(imported) == 1
            imported_profile = imported[0]
            assert imported_profile.timestamp_be_unix_milliseconds_support == 1.0

            # R280: TimestampDetector.detect 从导入的 profile 识别毫秒时间戳
            config = Config(min_samples=8, timestamp_support=0.90)
            detector = TimestampDetector(config)
            evidences = detector.detect(imported_profile)

            assert len(evidences) == 1
            evidence = evidences[0]
            assert evidence.coarse_label == "timestamp"
            assert evidence.fine_label == "unix_milliseconds_be"
            assert evidence.score == 1.0
            assert evidence.is_hard_evidence is True
            assert evidence.details["byte_width"] == 8
        finally:
            Path(output_path).unlink(missing_ok=True)


class TestDemoR305R307:
    """R305-R307: Demo 端到端测试

    R305: 非 unknown 类别断言（length/timestamp/string/constant/sequence 至少命中）
    R306: FieldKey 匹配数和指标范围断言（matched>0，所有指标 0~1）
    R307: errors 与 metrics 计数一致性（correct+wrong+abstained+missing 可核对）
    """

    def _run_demo_pipeline(self):
        """运行 Demo 流水线，返回 (predictions, truths, aligned_pairs, unmatched_truths)"""
        # 读取 examples/messages.jsonl
        messages_path = Path("examples/messages.jsonl")
        if not messages_path.exists():
            pytest.skip("examples/messages.jsonl not found")

        valid, rejected = read_jsonl_file(str(messages_path))
        assert len(rejected) == 0

        # 分组、校验、转换、聚合
        groups = group_by_layout_and_direction(valid)
        valid_groups, _ = validate_group_field_count(groups)
        all_samples = []
        for key, records in valid_groups.items():
            for record in records:
                all_samples.extend(record_to_field_samples(record))
        field_groups = aggregate_by_field_key(all_samples)
        field_groups, _ = mark_insufficient_groups(field_groups, min_samples=5)

        # 生成画像
        profiles = []
        for fk, samples in field_groups.items():
            profile = build_field_profile(fk, samples)
            profiles.append(profile)

        # 运行流水线（含 type_control 后处理）
        pipeline = DetectionPipeline()
        predictions = pipeline.detect_fields(profiles)

        # 读取 ground truth
        truth_path = Path("examples/ground_truth.jsonl")
        truth_records, truth_rejected = read_ground_truth_jsonl(str(truth_path))
        assert len(truth_rejected) == 0
        valid_truths, _ = validate_ground_truth(truth_records)
        assert len(valid_truths) > 0

        # 对齐
        aligned_pairs, unmatched_preds, unmatched_truths = align_predictions_with_truth(
            predictions, valid_truths
        )

        return predictions, valid_truths, aligned_pairs, unmatched_truths

    def test_r305_non_unknown_labels_hit(self):
        """R305: length/timestamp/string/constant/sequence 至少各有一个命中"""
        predictions, _, _, _ = self._run_demo_pipeline()

        labels_found = set(p.coarse_label for p in predictions if p.coarse_label != "unknown")

        # 教程要求的核心类别至少各有一个命中
        required_labels = {"length", "timestamp", "string", "constant", "sequence_or_counter"}
        missing = required_labels - labels_found
        assert not missing, f"缺少必需标签: {missing}, 实际命中: {labels_found}"

    def test_r305_type_control_and_payload_also_present(self):
        """R305 扩展: type_control 和 payload 也应命中"""
        predictions, _, _, _ = self._run_demo_pipeline()

        labels_found = set(p.coarse_label for p in predictions if p.coarse_label != "unknown")
        assert "type_control" in labels_found, "type_control 未命中"
        assert "payload" in labels_found, "payload 未命中"

    def test_r306_fieldkey_match_count(self):
        """R306: FieldKey 匹配数 > 0"""
        _, truths, aligned_pairs, unmatched_truths = self._run_demo_pipeline()

        assert len(aligned_pairs) > 0, "匹配数应 > 0"
        assert len(aligned_pairs) == len(truths), "全部 truth 应被匹配"

    def test_r306_metrics_in_range(self):
        """R306: 所有指标在 0~1 范围"""
        _, truths, aligned_pairs, unmatched_truths = self._run_demo_pipeline()

        accuracy = calculate_overall_accuracy(aligned_pairs, unmatched_truths)
        coverage = calculate_coverage(aligned_pairs, unmatched_truths)
        unknown_rate = calculate_unknown_rate(aligned_pairs, unmatched_truths)
        covered_accuracy = calculate_covered_accuracy(aligned_pairs)

        assert 0.0 <= accuracy <= 1.0, f"accuracy 超出范围: {accuracy}"
        assert 0.0 <= coverage <= 1.0, f"coverage 超出范围: {coverage}"
        assert 0.0 <= unknown_rate <= 1.0, f"unknown_rate 超出范围: {unknown_rate}"
        assert 0.0 <= covered_accuracy <= 1.0, f"covered_accuracy 超出范围: {covered_accuracy}"

    def test_r307_errors_metrics_consistency(self):
        """R307: correct + wrong + abstained + missing = 总 truth 数"""
        _, truths, aligned_pairs, unmatched_truths = self._run_demo_pipeline()

        errors = collect_errors(aligned_pairs, unmatched_truths)

        # 分类错误
        wrong_label_count = sum(1 for e in errors if e.error_type == "wrong_label")
        abstained_count = sum(1 for e in errors if e.error_type == "abstained")
        missing_count = sum(1 for e in errors if e.error_type == "missing_prediction")
        unexpected_count = sum(1 for e in errors if e.error_type == "unexpected_prediction")

        # correct = aligned_pairs 中没有错误的
        total_errors_in_aligned = wrong_label_count + abstained_count
        correct_count = len(aligned_pairs) - total_errors_in_aligned

        # missing = unmatched_truths
        missing_from_unmatched = len(unmatched_truths)

        # 总数核对：correct + wrong + abstained + missing = 总 truth 数
        total = correct_count + wrong_label_count + abstained_count + missing_from_unmatched
        assert total == len(truths), (
            f"计数不一致: correct={correct_count}, wrong={wrong_label_count}, "
            f"abstained={abstained_count}, missing={missing_from_unmatched}, "
            f"total={total}, truths={len(truths)}"
        )


class TestTypeOpcodeNonzeroOffsetR330:
    """R330: Modbus 风格 F4 功能码非零偏移端到端回归测试

    验证 HIGH-1 修复：F4 在 start=7, width=1 的非零偏移场景下，
    能正确进入 Type/Opcode 候选流程，不被 start_mode=7 误判为宽度 7。

    数据要求（计划 R330）：
    - 至少 8 条读请求（layout_read_request.F4 主值 03）
    - 至少 8 条写请求（layout_write_request.F4 主值 06）
    - F4 start=7, end=8（width=1）

    验收要求：
    - 两个 F4 均产生 type_control 候选
    - 证据中含真实 03/06
    - 不是通过 layout 名称硬编码
    """

    def _run_full_pipeline(self, fixture_path: Path, min_samples: int = 5):
        """运行完整流水线并返回 profiles 和 predictions"""
        valid, rejected = read_jsonl_file(str(fixture_path))

        groups = group_by_layout_and_direction(valid)
        valid_groups, _ = validate_group_field_count(groups)

        all_samples = []
        for key, records in valid_groups.items():
            for record in records:
                all_samples.extend(record_to_field_samples(record))

        field_groups = aggregate_by_field_key(all_samples)
        field_groups, _ = mark_insufficient_groups(field_groups, min_samples=min_samples)

        profiles = []
        for fk, samples in field_groups.items():
            profile = build_field_profile(fk, samples)
            profiles.append(profile)

        pipeline = DetectionPipeline()
        predictions = pipeline.detect_fields(profiles)
        return profiles, predictions

    def test_f4_nonzero_offset_produces_type_control(self):
        """R330: F4 (start=7, width=1) 应产生 type_control 候选

        HIGH-1 核心场景：start_mode=7 不应被误判为 width=7。
        修复前 width_mode=1 会被 tuple 索引 [3] 读取为 start_mode=7，导致 width>2 被拒绝。
        修复后用具名字段 width_mode 读取，width=1 <= 2，应通过。
        """
        fixture_path = Path("tests/fixtures/type_opcode_nonzero_offset.jsonl")
        if not fixture_path.exists():
            pytest.skip("type_opcode_nonzero_offset.jsonl not found")

        profiles, predictions = self._run_full_pipeline(fixture_path)

        # 找到 F4 字段（field_index=4, direction=request, start_mode=7, width_mode=1）
        # 不按 layout_id 查找，只按对齐键的 4 个具名字段查找
        f4_entries = [
            (p, pred) for p, pred in zip(profiles, predictions)
            if p.field_index == 4
            and p.direction == "request"
            and p.start_mode == 7
            and p.width_mode == 1
        ]

        # 应该有两个 F4 预测（layout_read_request 和 layout_write_request）
        assert len(f4_entries) == 2, (
            f"Expected 2 F4 predictions (read+write), got {len(f4_entries)}"
        )

        # 两个 F4 均应产生 type_control 候选
        for profile, prediction in f4_entries:
            assert prediction.coarse_label == "type_control", (
                f"F4 in {profile.layout_id}: expected type_control, "
                f"got {prediction.coarse_label}"
            )
            assert prediction.fine_label == "type_or_opcode_candidate"

    def test_f4_evidence_contains_real_function_codes(self):
        """R330: 证据中应含真实 03/06 值

        验证 type_or_opcode evidence 的 details.layout_values 包含真实的
        function code 值 03（读）和 06（写），不是占位符或硬编码。
        """
        fixture_path = Path("tests/fixtures/type_opcode_nonzero_offset.jsonl")
        if not fixture_path.exists():
            pytest.skip("type_opcode_nonzero_offset.jsonl not found")

        profiles, predictions = self._run_full_pipeline(fixture_path)

        # 收集所有 F4 预测的证据
        f4_predictions = [
            (p, pred) for p, pred in zip(profiles, predictions)
            if p.field_index == 4 and p.direction == "request"
            and p.start_mode == 7 and p.width_mode == 1
        ]
        assert len(f4_predictions) == 2

        # 收集所有 type_or_opcode 证据中的 layout_values
        all_layout_values = {}
        for profile, prediction in f4_predictions:
            for evidence in prediction.evidence:
                if (hasattr(evidence, 'detector') and evidence.detector == "type_opcode"
                        and hasattr(evidence, 'details') and evidence.details):
                    layout_values = evidence.details.get("layout_values", {})
                    all_layout_values.update(layout_values)

        # 应包含真实 03 和 06
        values_list = list(all_layout_values.values())
        assert "03" in values_list, (
            f"Evidence should contain real function code 03, got {values_list}"
        )
        assert "06" in values_list, (
            f"Evidence should contain real function code 06, got {values_list}"
        )

    def test_f4_not_hardcoded_by_layout_name(self):
        """R330: 检测不依赖 layout 名称硬编码

        验证 alignment_key 只包含 4 个具名字段
        (direction, field_index, start_mode, width_mode)，
        不包含 layout_id。生产代码不应通过 layout 名称识别 type/opcode。
        """
        fixture_path = Path("tests/fixtures/type_opcode_nonzero_offset.jsonl")
        if not fixture_path.exists():
            pytest.skip("type_opcode_nonzero_offset.jsonl not found")

        profiles, predictions = self._run_full_pipeline(fixture_path)

        # 找到 F4 预测
        f4_predictions = [
            (p, pred) for p, pred in zip(profiles, predictions)
            if p.field_index == 4 and p.direction == "request"
            and p.start_mode == 7 and p.width_mode == 1
        ]
        assert len(f4_predictions) == 2

        # 验证证据的 alignment_key 不包含 layout_id
        for profile, prediction in f4_predictions:
            for evidence in prediction.evidence:
                if (hasattr(evidence, 'detector') and evidence.detector == "type_opcode"
                        and hasattr(evidence, 'details') and evidence.details):
                    if "alignment_key" in evidence.details:
                        align_key = evidence.details["alignment_key"]
                        # alignment_key 应该是 [direction_str, field_index, start_mode, width_mode]
                        assert len(align_key) == 4, (
                            f"alignment_key should have 4 named fields, got {align_key}"
                        )
                        # 验证字段值（不依赖 layout_id）
                        assert align_key[0] == "request"  # direction
                        assert align_key[1] == 4  # field_index
                        assert align_key[2] == 7  # start_mode
                        assert align_key[3] == 1  # width_mode
