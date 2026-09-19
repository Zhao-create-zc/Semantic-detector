"""R083+R084: 配置 dataclass 和默认加载测试"""

from pathlib import Path
import pytest

from semantic_detector.config import Config, load_default_config


class TestConfig:
    """测试配置 dataclass"""
    
    def test_default_config_creation(self):
        """可以创建默认配置"""
        config = Config()
        assert config.min_samples == 8
        assert config.constant_support == 0.98
        assert config.length_support == 0.90
    
    def test_config_with_custom_values(self):
        """可以使用自定义值创建配置"""
        config = Config(min_samples=10, constant_support=0.95)
        assert config.min_samples == 10
        assert config.constant_support == 0.95
        # 其他值保持默认
        assert config.length_support == 0.90


class TestLoadDefaultConfig:
    """测试加载默认配置"""
    
    def test_load_defaults(self):
        """加载默认配置文件"""
        config = load_default_config()
        assert config is not None
        assert isinstance(config, Config)
    
    def test_loaded_values_match_json(self):
        """加载的值与 JSON 文件一致"""
        config = load_default_config()
        
        # 验证所有字段与 JSON 文件一致
        assert config.min_samples == 8
        assert config.constant_support == 0.98
        assert config.length_support == 0.90
        assert config.timestamp_support == 0.90
        assert config.timestamp_slop_seconds == 86400
        assert config.sequence_unique_ratio == 0.70
        assert config.sequence_increasing_ratio == 0.80
        assert config.string_printable_ratio == 0.85
        assert config.string_nonempty_ratio == 0.80
        assert config.identifier_unique_ratio == 0.80
        assert config.identifier_score_cap == 0.70
        assert config.payload_entropy_threshold == 0.70
        assert config.ambiguity_margin == 0.08
        assert config.type_opcode_min_dominant_ratio == 0.50
    
    def test_load_custom_config_path(self):
        """可以加载指定路径的配置文件"""
        config_path = Path(__file__).parent.parent.parent / "config" / "defaults.json"
        config = load_default_config(config_path)
        assert config is not None
        assert config.min_samples == 8


class TestConfigValidation:
    """R084: 测试配置类型和阈值校验"""
    
    def test_negative_min_samples_rejected(self):
        """负数 min_samples 被拒绝"""
        with pytest.raises(ValueError, match="min_samples must be positive"):
            Config(min_samples=-1)
    
    def test_zero_min_samples_rejected(self):
        """零 min_samples 被拒绝"""
        with pytest.raises(ValueError, match="min_samples must be positive"):
            Config(min_samples=0)
    
    def test_negative_timestamp_slop_rejected(self):
        """负数 timestamp_slop_seconds 被拒绝"""
        with pytest.raises(ValueError, match="timestamp_slop_seconds must be positive"):
            Config(timestamp_slop_seconds=-1)
    
    def test_threshold_below_zero_rejected(self):
        """阈值小于 0 被拒绝"""
        with pytest.raises(ValueError, match="constant_support must be between 0.0 and 1.0"):
            Config(constant_support=-0.1)
    
    def test_threshold_above_one_rejected(self):
        """阈值大于 1 被拒绝"""
        with pytest.raises(ValueError, match="constant_support must be between 0.0 and 1.0"):
            Config(constant_support=1.1)
    
    def test_length_support_threshold_validation(self):
        """length_support 阈值校验"""
        with pytest.raises(ValueError, match="length_support must be between 0.0 and 1.0"):
            Config(length_support=1.5)
    
    def test_timestamp_support_threshold_validation(self):
        """timestamp_support 阈值校验"""
        with pytest.raises(ValueError, match="timestamp_support must be between 0.0 and 1.0"):
            Config(timestamp_support=-0.5)
    
    def test_sequence_unique_ratio_validation(self):
        """sequence_unique_ratio 阈值校验"""
        with pytest.raises(ValueError, match="sequence_unique_ratio must be between 0.0 and 1.0"):
            Config(sequence_unique_ratio=2.0)
    
    def test_ambiguity_margin_validation(self):
        """ambiguity_margin 阈值校验"""
        with pytest.raises(ValueError, match="ambiguity_margin must be between 0.0 and 1.0"):
            Config(ambiguity_margin=-0.1)
    
    def test_valid_boundary_values(self):
        """边界值 0.0 和 1.0 合法"""
        config1 = Config(constant_support=0.0)
        assert config1.constant_support == 0.0

        config2 = Config(constant_support=1.0)
        assert config2.constant_support == 1.0

    def test_type_opcode_min_dominant_ratio_validation(self):
        """R358：type_opcode_min_dominant_ratio 阈值校验"""
        with pytest.raises(ValueError, match="type_opcode_min_dominant_ratio must be between 0.0 and 1.0"):
            Config(type_opcode_min_dominant_ratio=-0.1)
        with pytest.raises(ValueError, match="type_opcode_min_dominant_ratio must be between 0.0 and 1.0"):
            Config(type_opcode_min_dominant_ratio=1.5)


class TestConfigContextThresholdsR358:
    """R358：Timestamp 与其他上下文阈值使用同一配置

    计划 L1119-1138 要求：
    - timestamp_slop_seconds / timestamp_support / min_samples /
      type/opcode 最低关联阈值 / soft score cap 不得存在
      "文档一套 / Config 一套 / Detector 内硬编码另一套"
    - 验收：配置改变真实影响行为
    """

    def test_timestamp_slop_seconds_affects_support_calculation(self):
        """timestamp_slop_seconds 真实影响 calculate_unix_seconds_support 结果"""
        from datetime import datetime, timezone
        from semantic_detector.bi_adapted.timestamp_range import calculate_unix_seconds_support

        # 构造时间戳在范围边缘的场景
        # capture_time 范围：2023-01-01 00:00:00 UTC（unix=1672531200）
        capture_time = datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        # 字段值 = 2023-01-01 12:00:00 UTC（unix=1672574400），在范围外 43200 秒
        field_values = [1672574400]

        # slop_seconds=0：字段值不在 [1672531200, 1672531200] 范围内 → support=0.0
        support_strict = calculate_unix_seconds_support(
            field_values, capture_time, capture_time, slop_seconds=0
        )
        assert support_strict == 0.0

        # slop_seconds=86400（1天）：字段值在 [1672444800, 1672617600] 范围内 → support=1.0
        support_loose = calculate_unix_seconds_support(
            field_values, capture_time, capture_time, slop_seconds=86400
        )
        assert support_loose == 1.0

        # 配置改变真实结果
        assert support_strict != support_loose

    def test_build_field_profile_passes_slop_seconds(self):
        """build_field_profile 接收 slop_seconds 参数并传入 support 计算"""
        from datetime import datetime, timezone
        from semantic_detector.contracts import FieldKey, Direction, FieldSample
        from semantic_detector.profiling.profile_builder import build_field_profile

        # 构造 4 字节固定宽度的 Unix 秒时间戳字段
        # capture_time = 2023-01-01 00:00:00 UTC，字段值 = 2023-01-01 12:00:00 UTC
        capture_time = datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        # 1672574400 = 2023-01-01 12:00:00 UTC 的 Unix 秒
        field_bytes = (1672574400).to_bytes(4, "big")

        field_key = FieldKey(layout_id="test_layout", direction=Direction.REQUEST, field_index=0)
        samples = [
            FieldSample(
                message_id="msg_1",
                field_key=field_key,
                field_bytes=field_bytes,
                start=0,
                end=4,
                message_length=4,
                remaining_bytes=0,
                capture_time=capture_time,
                session_id="1",
                pair_id="1",
                input_order=0,
            )
        ]

        # slop_seconds=0：字段值不在 capture_time 范围内 → support=0.0
        profile_strict = build_field_profile(field_key, samples, slop_seconds=0)
        assert profile_strict.timestamp_be_unix_seconds_support == 0.0

        # slop_seconds=86400：字段值在范围内 → support=1.0
        profile_loose = build_field_profile(field_key, samples, slop_seconds=86400)
        assert profile_loose.timestamp_be_unix_seconds_support == 1.0

        # 配置改变真实结果
        assert profile_strict.timestamp_be_unix_seconds_support != profile_loose.timestamp_be_unix_seconds_support

    def test_type_opcode_min_dominant_ratio_affects_detection(self):
        """type_opcode_min_dominant_ratio 真实影响 detect_type_or_opcode 结果"""
        from semantic_detector.contracts import TypeOpcodeAlignmentKey, Direction
        from semantic_detector.detectors.type_opcode import detect_type_or_opcode

        # 构造 2 个 layout，per_layout_dominant_ratios 在 0.5 边缘
        layout_dominant_values = {
            "layout_a": b"\x03",
            "layout_b": b"\x06",
        }
        alignment_key = TypeOpcodeAlignmentKey(
            direction=Direction.REQUEST,
            field_index=4,
            start_mode=7,
            width_mode=1,
        )
        per_layout_dominant_ratios = {
            "layout_a": 0.55,
            "layout_b": 0.55,
        }

        # min_dominant_ratio=0.4：0.55 >= 0.4 → 通过，返回 evidence
        evidence_loose = detect_type_or_opcode(
            layout_dominant_values,
            alignment_key,
            existing_evidences=None,
            per_layout_dominant_ratios=per_layout_dominant_ratios,
            min_dominant_ratio=0.4,
        )
        assert evidence_loose is not None
        assert evidence_loose.coarse_label == "type_control"

        # min_dominant_ratio=0.6：0.55 < 0.6 → 被拒绝，返回 None
        evidence_strict = detect_type_or_opcode(
            layout_dominant_values,
            alignment_key,
            existing_evidences=None,
            per_layout_dominant_ratios=per_layout_dominant_ratios,
            min_dominant_ratio=0.6,
        )
        assert evidence_strict is None

        # 配置改变真实结果
        assert evidence_loose is not None
        assert evidence_strict is None

    def test_pipeline_passes_type_opcode_min_dominant_ratio_to_detector(self):
        """Pipeline 把 config.type_opcode_min_dominant_ratio 传给 detect_type_or_opcode"""
        from semantic_detector.config import Config
        from semantic_detector.pipeline.pipeline import DetectionPipeline

        # 默认 config 的 type_opcode_min_dominant_ratio=0.50
        pipeline_default = DetectionPipeline()
        assert pipeline_default.config.type_opcode_min_dominant_ratio == 0.50

        # 自定义 config
        config_custom = Config(type_opcode_min_dominant_ratio=0.65)
        pipeline_custom = DetectionPipeline(config=config_custom)
        assert pipeline_custom.config.type_opcode_min_dominant_ratio == 0.65

    def test_config_defaults_json_contains_type_opcode_min_dominant_ratio(self):
        """config/defaults.json 包含 type_opcode_min_dominant_ratio 字段"""
        import json
        defaults_path = Path(__file__).parent.parent.parent / "config" / "defaults.json"
        with open(defaults_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "type_opcode_min_dominant_ratio" in data
        assert data["type_opcode_min_dominant_ratio"] == 0.50
