"""测试 manifest 生成功能

验证 manifest 的生成和内容。
"""

import pytest
import tempfile
import json
from pathlib import Path
from semantic_detector.pipeline.pipeline import DetectionPipeline
from semantic_detector.profiling.profile_builder import FieldProfile
from semantic_detector.contracts import RunCounts, RunManifestInfo


class TestManifest:
    """manifest 测试"""
    
    def test_generate_manifest(self):
        """测试生成 manifest"""
        pipeline = DetectionPipeline()
        
        # 创建测试数据
        profile = FieldProfile(
            field_index=0,
            layout_id="test_layout",
            direction="forward",
            width_mode=4,
            start_mode=0
        )
        
        from semantic_detector.contracts import DetectorEvidence
        prediction = DetectorEvidence(
            detector="test_detector",
            coarse_label="integer",
            fine_label="uint32",
            score=0.9,
            is_hard_evidence=True,
            reason_code="test_reason"
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "input.jsonl"
            input_file.write_text('{"test": "data"}\n', encoding='utf-8')
            
            manifest = pipeline.generate_manifest(
                str(input_file),
                tmpdir,
                [profile],
                [prediction]
            )
            
            # 检查必要字段
            assert "run_id" in manifest
            assert "timestamp" in manifest
            assert "input" in manifest
            assert "output" in manifest
            assert "config" in manifest
            assert "summary" in manifest
    
    def test_manifest_input_fields(self):
        """测试 manifest 输入字段"""
        pipeline = DetectionPipeline()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "input.jsonl"
            input_file.write_text('{"test": "data"}\n', encoding='utf-8')
            
            manifest = pipeline.generate_manifest(
                str(input_file),
                tmpdir,
                [],
                []
            )
            
            assert "file" in manifest["input"]
            assert "file_size" in manifest["input"]
    
    def test_manifest_output_fields(self):
        """测试 manifest 输出字段"""
        pipeline = DetectionPipeline()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "input.jsonl"
            input_file.write_text('{"test": "data"}\n', encoding='utf-8')
            
            manifest = pipeline.generate_manifest(
                str(input_file),
                tmpdir,
                [],
                []
            )
            
            assert "directory" in manifest["output"]
            assert "validated_records" in manifest["output"]
            assert "field_profiles" in manifest["output"]
            assert "predictions" in manifest["output"]
    
    def test_manifest_config_fields(self):
        """测试 manifest 配置字段"""
        pipeline = DetectionPipeline()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "input.jsonl"
            input_file.write_text('{"test": "data"}\n', encoding='utf-8')
            
            manifest = pipeline.generate_manifest(
                str(input_file),
                tmpdir,
                [],
                []
            )
            
            assert "detectors" in manifest["config"]
            assert "resolver" in manifest["config"]
    
    def test_manifest_summary_fields(self):
        """测试 manifest 摘要字段"""
        pipeline = DetectionPipeline()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "input.jsonl"
            input_file.write_text('{"test": "data"}\n', encoding='utf-8')
            
            manifest = pipeline.generate_manifest(
                str(input_file),
                tmpdir,
                [],
                []
            )
            
            assert "hard_evidence_count" in manifest["summary"]
            assert "soft_evidence_count" in manifest["summary"]
            assert "coarse_labels" in manifest["summary"]
    
    def test_manifest_run_id_format(self):
        """测试 manifest run_id 格式"""
        pipeline = DetectionPipeline()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "input.jsonl"
            input_file.write_text('{"test": "data"}\n', encoding='utf-8')
            
            manifest = pipeline.generate_manifest(
                str(input_file),
                tmpdir,
                [],
                []
            )
            
            # run_id 应该是 UUID 格式
            assert len(manifest["run_id"]) == 36
            assert manifest["run_id"].count("-") == 4


class TestRunCountsR348:
    """R348：分阶段 RunCounts 数据模型测试

    验收：
    - 默认构造全 0
    - 完整构造 9 个字段
    - frozen 不可变
    - 相等性
    - 字段独立性（不混淆消息数和字段数）
    - 不得用 predictions 冒充 validated_records（消息数）
    """

    def test_default_all_zero(self):
        """R348: 默认构造所有字段为 0"""
        counts = RunCounts()
        assert counts.input_line_count == 0
        assert counts.json_valid_records == 0
        assert counts.json_rejected_records == 0
        assert counts.contract_valid_records == 0
        assert counts.contract_rejected_records == 0
        assert counts.group_valid_records == 0
        assert counts.group_rejected_records == 0
        assert counts.field_profiles == 0
        assert counts.predictions == 0

    def test_full_construction_nine_fields(self):
        """R348: 完整构造 9 个字段"""
        counts = RunCounts(
            input_line_count=10,
            json_valid_records=8,
            json_rejected_records=2,
            contract_valid_records=8,
            contract_rejected_records=0,
            group_valid_records=6,
            group_rejected_records=2,
            field_profiles=12,
            predictions=12,
        )
        assert counts.input_line_count == 10
        assert counts.json_valid_records == 8
        assert counts.json_rejected_records == 2
        assert counts.contract_valid_records == 8
        assert counts.contract_rejected_records == 0
        assert counts.group_valid_records == 6
        assert counts.group_rejected_records == 2
        assert counts.field_profiles == 12
        assert counts.predictions == 12

    def test_frozen_immutable(self):
        """R348: RunCounts 是 frozen dataclass，不可修改"""
        counts = RunCounts(input_line_count=5)
        with pytest.raises((AttributeError, Exception)):
            counts.input_line_count = 10

    def test_equality_same_values(self):
        """R348: 相同值的两个实例相等"""
        counts1 = RunCounts(
            input_line_count=10,
            json_valid_records=8,
            json_rejected_records=2,
            contract_valid_records=8,
            contract_rejected_records=0,
            group_valid_records=6,
            group_rejected_records=2,
            field_profiles=12,
            predictions=12,
        )
        counts2 = RunCounts(
            input_line_count=10,
            json_valid_records=8,
            json_rejected_records=2,
            contract_valid_records=8,
            contract_rejected_records=0,
            group_valid_records=6,
            group_rejected_records=2,
            field_profiles=12,
            predictions=12,
        )
        assert counts1 == counts2

    def test_inequality_different_values(self):
        """R348: 不同值的两个实例不相等"""
        counts1 = RunCounts(input_line_count=10)
        counts2 = RunCounts(input_line_count=20)
        assert counts1 != counts2

    def test_message_count_vs_field_count_independent(self):
        """R348: 消息数（group_valid_records）与字段数（field_profiles/predictions）独立

        关键场景：6 条消息 × 2 字段 = 12 个画像/预测
        - group_valid_records = 6（消息数）
        - field_profiles = 12（字段数）
        - predictions = 12（字段数）
        不得用 predictions=12 冒充 validated_records=12（实际消息数只有 6）
        """
        counts = RunCounts(
            input_line_count=8,
            json_valid_records=6,
            json_rejected_records=2,
            contract_valid_records=6,
            contract_rejected_records=0,
            group_valid_records=6,
            group_rejected_records=0,
            field_profiles=12,
            predictions=12,
        )
        # 消息数 != 字段数
        assert counts.group_valid_records == 6
        assert counts.field_profiles == 12
        assert counts.predictions == 12
        # 关键断言：不得用 predictions 冒充 validated_records
        assert counts.predictions != counts.group_valid_records
        assert counts.predictions == counts.group_valid_records * 2  # 每条消息 2 字段

    def test_rejection_counts_split_by_stage(self):
        """R348: 拒绝计数按阶段分开（JSON 解析 vs 契约校验 vs 组级校验）"""
        counts = RunCounts(
            input_line_count=10,
            json_valid_records=8,
            json_rejected_records=2,  # JSON 解析失败
            contract_valid_records=8,
            contract_rejected_records=0,  # 契约校验全过
            group_valid_records=6,
            group_rejected_records=2,  # 组级字段数不一致
            field_profiles=12,
            predictions=12,
        )
        # 三个阶段的拒绝数独立记录
        assert counts.json_rejected_records == 2
        assert counts.contract_rejected_records == 0
        assert counts.group_rejected_records == 2
        # 总拒绝 != 任一阶段单独拒绝
        total_rejections = (
            counts.json_rejected_records
            + counts.contract_rejected_records
            + counts.group_rejected_records
        )
        assert total_rejections == 4


class TestRunManifestInfoR350:
    """R350：RunManifestInfo 运行状态和退出信息数据模型测试

    验收：
    - 默认构造 7 个字段
    - 完整构造 7 个字段
    - frozen 不可变
    - 相等性
    - command_args 是 tuple（frozen 要求）
    - 支持所有 6 种状态值
    """

    def test_default_values(self):
        """R350: 默认构造 7 个字段"""
        info = RunManifestInfo()
        assert info.status == "completed"
        assert info.exit_code == 0
        assert info.partial_input is False
        assert info.valid_for_reporting is True
        assert info.started_at == ""
        assert info.finished_at == ""
        assert info.command_args == ()

    def test_full_construction_seven_fields(self):
        """R350: 完整构造 7 个字段"""
        info = RunManifestInfo(
            status="partial_success",
            exit_code=0,
            partial_input=True,
            valid_for_reporting=False,
            started_at="2026-06-28T21:30:00",
            finished_at="2026-06-28T21:30:05",
            command_args=("run", "input.jsonl", "--output-dir", "out"),
        )
        assert info.status == "partial_success"
        assert info.exit_code == 0
        assert info.partial_input is True
        assert info.valid_for_reporting is False
        assert info.started_at == "2026-06-28T21:30:00"
        assert info.finished_at == "2026-06-28T21:30:05"
        assert info.command_args == ("run", "input.jsonl", "--output-dir", "out")

    def test_frozen_immutable(self):
        """R350: RunManifestInfo 是 frozen dataclass，不可修改"""
        info = RunManifestInfo(status="completed")
        with pytest.raises((AttributeError, Exception)):
            info.status = "failed"

    def test_equality_same_values(self):
        """R350: 相同值的两个实例相等"""
        info1 = RunManifestInfo(
            status="invalid_input",
            exit_code=1,
            partial_input=False,
            valid_for_reporting=False,
            started_at="2026-06-28T21:00:00",
            finished_at="2026-06-28T21:00:01",
            command_args=("run", "input.jsonl"),
        )
        info2 = RunManifestInfo(
            status="invalid_input",
            exit_code=1,
            partial_input=False,
            valid_for_reporting=False,
            started_at="2026-06-28T21:00:00",
            finished_at="2026-06-28T21:00:01",
            command_args=("run", "input.jsonl"),
        )
        assert info1 == info2

    def test_inequality_different_values(self):
        """R350: 不同值的两个实例不相等"""
        info1 = RunManifestInfo(status="completed", exit_code=0)
        info2 = RunManifestInfo(status="failed", exit_code=1)
        assert info1 != info2

    def test_command_args_is_tuple(self):
        """R350: command_args 是 tuple（frozen dataclass 要求不可变）"""
        info = RunManifestInfo(command_args=("run", "input.jsonl"))
        assert isinstance(info.command_args, tuple)
        assert info.command_args == ("run", "input.jsonl")

    def test_status_values_supported(self):
        """R350: 支持所有 6 种状态值（completed/partial_success/invalid_input/no_valid_records/invalid_ground_truth/failed）"""
        for status in [
            "completed",
            "partial_success",
            "invalid_input",
            "no_valid_records",
            "invalid_ground_truth",
            "failed",
        ]:
            info = RunManifestInfo(status=status)
            assert info.status == status


class TestManifestConfigR359:
    """R359：Manifest 保存有效配置和哈希

    计划 L1141-1157 要求：
    - manifest 必须写入 resolved_config / config_source / config_sha256
    - 若使用内建默认值，也要生成稳定配置摘要和哈希
    - 测试：同一配置哈希稳定；覆盖值改变哈希；manifest 值与 Pipeline 实际值一致
    """

    def _generate_manifest(self, pipeline, tmpdir):
        """辅助：生成一个最小 manifest"""
        input_file = Path(tmpdir) / "input.jsonl"
        input_file.write_text('{"test": "data"}\n', encoding='utf-8')
        return pipeline.generate_manifest(
            str(input_file), tmpdir, [], []
        )

    def test_manifest_contains_resolved_config(self):
        """manifest 包含 resolved_config 字段（Config 全部字段）"""
        pipeline = DetectionPipeline()
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = self._generate_manifest(pipeline, tmpdir)
        assert "resolved_config" in manifest["config"]
        resolved = manifest["config"]["resolved_config"]
        # 验证包含所有 Config 字段
        assert "min_samples" in resolved
        assert "constant_support" in resolved
        assert "timestamp_slop_seconds" in resolved
        assert "ambiguity_margin" in resolved
        assert "type_opcode_min_dominant_ratio" in resolved

    def test_manifest_contains_config_source(self):
        """manifest 包含 config_source 字段"""
        pipeline = DetectionPipeline()
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = self._generate_manifest(pipeline, tmpdir)
        assert "config_source" in manifest["config"]
        assert manifest["config"]["config_source"] == "default"

    def test_manifest_contains_config_sha256(self):
        """manifest 包含 config_sha256 字段（64 字符十六进制）"""
        pipeline = DetectionPipeline()
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = self._generate_manifest(pipeline, tmpdir)
        assert "config_sha256" in manifest["config"]
        sha = manifest["config"]["config_sha256"]
        assert isinstance(sha, str)
        assert len(sha) == 64  # SHA256 十六进制长度

    def test_same_config_sha256_stable(self):
        """同一配置哈希稳定：两次生成 manifest，config_sha256 相同"""
        from semantic_detector.config import Config
        config1 = Config()
        config2 = Config()
        assert config1.sha256() == config2.sha256()

        pipeline1 = DetectionPipeline(config=config1)
        pipeline2 = DetectionPipeline(config=config2)
        with tempfile.TemporaryDirectory() as tmpdir1, tempfile.TemporaryDirectory() as tmpdir2:
            manifest1 = self._generate_manifest(pipeline1, tmpdir1)
            manifest2 = self._generate_manifest(pipeline2, tmpdir2)
        assert manifest1["config"]["config_sha256"] == manifest2["config"]["config_sha256"]

    def test_different_config_sha256_changes(self):
        """覆盖值改变哈希：不同配置产生不同 config_sha256"""
        from semantic_detector.config import Config
        config_default = Config()
        config_custom = Config(min_samples=15, ambiguity_margin=0.12)
        assert config_default.sha256() != config_custom.sha256()

        pipeline_default = DetectionPipeline(config=config_default)
        pipeline_custom = DetectionPipeline(config=config_custom)
        with tempfile.TemporaryDirectory() as tmpdir1, tempfile.TemporaryDirectory() as tmpdir2:
            manifest_default = self._generate_manifest(pipeline_default, tmpdir1)
            manifest_custom = self._generate_manifest(pipeline_custom, tmpdir2)
        assert manifest_default["config"]["config_sha256"] != manifest_custom["config"]["config_sha256"]

    def test_manifest_config_matches_pipeline(self):
        """manifest 中的 resolved_config 与 Pipeline 实际 config 一致"""
        from semantic_detector.config import Config
        custom_config = Config(min_samples=12, constant_support=0.95, ambiguity_margin=0.10)
        pipeline = DetectionPipeline(config=custom_config)
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = self._generate_manifest(pipeline, tmpdir)
        resolved = manifest["config"]["resolved_config"]
        # 逐字段对比
        assert resolved["min_samples"] == pipeline.config.min_samples
        assert resolved["constant_support"] == pipeline.config.constant_support
        assert resolved["ambiguity_margin"] == pipeline.config.ambiguity_margin
        # 哈希一致
        assert manifest["config"]["config_sha256"] == pipeline.config.sha256()

    def test_default_config_has_stable_hash(self):
        """内建默认值也生成稳定配置摘要和哈希"""
        from semantic_detector.config import Config, load_default_config
        # 两种方式获取默认配置：Config() 和 load_default_config()
        config_direct = Config()
        config_loaded = load_default_config()
        # 哈希应相同（字段值相同）
        assert config_direct.sha256() == config_loaded.sha256()

        # 多次调用哈希稳定
        hash1 = config_direct.sha256()
        hash2 = config_direct.sha256()
        hash3 = config_direct.sha256()
        assert hash1 == hash2 == hash3

    def test_config_source_default(self):
        """默认 config_source 为 default"""
        pipeline = DetectionPipeline()
        assert pipeline.config_source == "default"

    def test_config_source_custom(self):
        """自定义 config_source 为用户路径"""
        from semantic_detector.config import Config
        pipeline = DetectionPipeline(
            config=Config(),
            config_source="/path/to/user_config.json",
        )
        assert pipeline.config_source == "/path/to/user_config.json"

        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = self._generate_manifest(pipeline, tmpdir)
        assert manifest["config"]["config_source"] == "/path/to/user_config.json"

    def test_config_to_dict_contains_all_fields(self):
        """Config.to_dict() 包含所有 15 个字段（R335 审计修复：含 resolver_min_score）"""
        from semantic_detector.config import Config
        config = Config()
        d = config.to_dict()
        expected_fields = [
            "min_samples", "constant_support", "length_support", "timestamp_support",
            "timestamp_slop_seconds", "sequence_unique_ratio", "sequence_increasing_ratio",
            "string_printable_ratio", "string_nonempty_ratio", "identifier_unique_ratio",
            "identifier_score_cap", "payload_entropy_threshold", "ambiguity_margin",
            "type_opcode_min_dominant_ratio", "resolver_min_score",
        ]
        assert set(d.keys()) == set(expected_fields)
        assert len(d) == 15
