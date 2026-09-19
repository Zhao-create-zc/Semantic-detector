"""测试检测器注册表"""

import pytest
from semantic_detector.detectors import (
    DetectorRegistry,
    register_detector,
    get_detector,
    list_detectors,
    clear_registry,
    register_all_detectors,
    register_all_detectors_with_config,
)
from semantic_detector.detectors.base import Detector
from semantic_detector.contracts import DetectorEvidence
from semantic_detector.profiling.profile_builder import FieldProfile
from semantic_detector.config import Config


class FakeDetector:
    """假检测器用于测试"""
    
    def __init__(self, name: str):
        self.name = name
    
    def detect(self, profile: FieldProfile) -> list[DetectorEvidence]:
        return []


class TestDetectorRegistry:
    """测试检测器注册表"""
    
    def test_register_detector(self):
        """注册检测器"""
        registry = DetectorRegistry()
        detector = FakeDetector("test_detector")
        
        registry.register(detector)
        
        assert registry.count() == 1
        assert "test_detector" in registry.list_names()
    
    def test_get_detector(self):
        """获取检测器"""
        registry = DetectorRegistry()
        detector = FakeDetector("test_detector")
        registry.register(detector)
        
        result = registry.get("test_detector")
        
        assert result is detector
        assert result.name == "test_detector"
    
    def test_register_duplicate_raises(self):
        """注册重复检测器抛出异常"""
        registry = DetectorRegistry()
        detector1 = FakeDetector("test_detector")
        detector2 = FakeDetector("test_detector")
        
        registry.register(detector1)
        
        with pytest.raises(ValueError, match="already registered"):
            registry.register(detector2)
    
    def test_get_nonexistent_raises(self):
        """获取不存在的检测器抛出异常"""
        registry = DetectorRegistry()
        
        with pytest.raises(KeyError, match="not found"):
            registry.get("nonexistent")
    
    def test_order_preserved(self):
        """注册顺序保持不变"""
        registry = DetectorRegistry()
        detector1 = FakeDetector("detector_1")
        detector2 = FakeDetector("detector_2")
        detector3 = FakeDetector("detector_3")
        
        registry.register(detector1)
        registry.register(detector2)
        registry.register(detector3)
        
        names = registry.list_names()
        assert names == ["detector_1", "detector_2", "detector_3"]
    
    def test_list_detectors(self):
        """列出所有检测器"""
        registry = DetectorRegistry()
        detector1 = FakeDetector("detector_1")
        detector2 = FakeDetector("detector_2")
        
        registry.register(detector1)
        registry.register(detector2)
        
        detectors = registry.list_detectors()
        
        assert len(detectors) == 2
        assert detectors[0] is detector1
        assert detectors[1] is detector2
    
    def test_count(self):
        """检测器计数"""
        registry = DetectorRegistry()
        
        assert registry.count() == 0
        
        registry.register(FakeDetector("detector_1"))
        assert registry.count() == 1
        
        registry.register(FakeDetector("detector_2"))
        assert registry.count() == 2


class TestGlobalRegistry:
    """测试全局注册表函数"""
    
    def setup_method(self):
        """每个测试前清空注册表"""
        clear_registry()
    
    def test_register_detector_global(self):
        """全局注册检测器"""
        detector = FakeDetector("test_detector")
        
        register_detector(detector)
        
        result = get_detector("test_detector")
        assert result is detector
    
    def test_list_detectors_global(self):
        """全局列出检测器"""
        detector1 = FakeDetector("detector_1")
        detector2 = FakeDetector("detector_2")
        
        register_detector(detector1)
        register_detector(detector2)
        
        detectors = list_detectors()
        
        assert len(detectors) == 2
        assert detectors[0] is detector1
        assert detectors[1] is detector2
    
    def test_clear_registry(self):
        """清空注册表"""
        detector = FakeDetector("test_detector")
        register_detector(detector)
        
        clear_registry()
        
        detectors = list_detectors()
        assert len(detectors) == 0


class TestRegisterAllDetectors:
    """测试注册所有检测器"""
    
    def setup_method(self):
        """每个测试前清空注册表"""
        clear_registry()
    
    def test_register_all_detectors_count(self):
        """注册所有检测器数量正确"""
        register_all_detectors()
        
        detectors = list_detectors()
        assert len(detectors) == 8
    
    def test_register_all_detectors_order(self):
        """注册所有检测器顺序正确"""
        register_all_detectors()
        
        names = [d.name for d in list_detectors()]
        expected = [
            "constant",
            "length",
            "timestamp",
            "sequence",
            "string",
            "identifier",
            "payload",
            "type_opcode"
        ]
        assert names == expected
    
    def test_register_all_detectors_can_get(self):
        """可以获取所有注册的检测器"""
        register_all_detectors()

        assert get_detector("constant").name == "constant"
        assert get_detector("length").name == "length"
        assert get_detector("timestamp").name == "timestamp"
        assert get_detector("sequence").name == "sequence"
        assert get_detector("string").name == "string"
        assert get_detector("identifier").name == "identifier"
        assert get_detector("payload").name == "payload"
        assert get_detector("type_opcode").name == "type_opcode"


class TestRegisterAllDetectorsWithConfig:
    """R355/R356：测试 register_all_detectors_with_config"""

    def setup_method(self):
        """每个测试前清空注册表"""
        clear_registry()

    def test_register_all_detectors_with_config_count(self):
        """用指定 config 注册所有检测器，数量正确"""
        config = Config()
        register_all_detectors_with_config(config)

        detectors = list_detectors()
        assert len(detectors) == 8

    def test_register_all_detectors_with_config_shared(self):
        """所有检测器引用同一 config 实例"""
        config = Config(min_samples=15)
        register_all_detectors_with_config(config)

        detectors = list_detectors()
        for d in detectors:
            if hasattr(d, 'config'):
                assert d.config is config

    def test_register_all_detectors_with_config_order(self):
        """用指定 config 注册，顺序正确"""
        config = Config()
        register_all_detectors_with_config(config)

        names = [d.name for d in list_detectors()]
        expected = [
            "constant", "length", "timestamp", "sequence",
            "string", "identifier", "payload", "type_opcode"
        ]
        assert names == expected


class TestDetectorConfigThresholdsR356:
    """R356：验证每个 config 阈值真实影响检测器行为

    计划 L1065-1090 要求：
    自定义 min_samples/constant_support/length_support/timestamp_support/
    sequence thresholds/string thresholds/identifier_score_cap/
    payload_entropy_threshold 均能影响对应 detector，而非只加载不使用。
    """

    def test_min_samples_affects_constant_detector(self):
        """min_samples 影响 ConstantDetector：低样本数 → abstain"""
        from semantic_detector.detectors.constant import ConstantDetector

        profile = FieldProfile(
            sample_count=5,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=1.0,
            unique_value_count=1,
        )

        # 默认 min_samples=8 → 样本不足 → abstain
        default_config = Config()
        detector_default = ConstantDetector(default_config)
        result_default = detector_default.detect(profile)
        assert len(result_default) == 1
        assert result_default[0].reason_code == "insufficient_samples"

        # 自定义 min_samples=3 → 样本足够 → 检测常量
        custom_config = Config(min_samples=3)
        detector_custom = ConstantDetector(custom_config)
        result_custom = detector_custom.detect(profile)
        assert len(result_custom) == 1
        assert result_custom[0].coarse_label == "constant"

    def test_constant_support_affects_constant_detector(self):
        """constant_support 影响 ConstantDetector：阈值变化改变检测结果"""
        from semantic_detector.detectors.constant import ConstantDetector

        # dominant_value_ratio=0.95：在 0.90 和 0.98 之间
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.95,
            unique_value_count=2,
        )

        # 默认 constant_support=0.98 → 0.95 < 0.98 → 无证据
        default_config = Config()
        detector_default = ConstantDetector(default_config)
        result_default = detector_default.detect(profile)
        assert len(result_default) == 0

        # 自定义 constant_support=0.90 → 0.95 >= 0.90 → 有证据
        custom_config = Config(constant_support=0.90)
        detector_custom = ConstantDetector(custom_config)
        result_custom = detector_custom.detect(profile)
        assert len(result_custom) == 1
        assert result_custom[0].coarse_label == "constant"

    def test_length_support_affects_length_detector(self):
        """length_support 影响 LengthDetector：阈值变化改变检测结果"""
        from semantic_detector.detectors.length import LengthDetector

        # exact_support=0.91：在 0.90 和 0.95 之间
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.0,
            unique_ratio=0.5,
            numeric_be_message_length_exact_support=0.91,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
        )

        # 默认 length_support=0.90 → 0.91 >= 0.90 → 有证据
        default_config = Config()
        detector_default = LengthDetector(default_config)
        result_default = detector_default.detect(profile)
        assert len(result_default) >= 1
        assert result_default[0].coarse_label == "length"

        # 自定义 length_support=0.95 → 0.91 < 0.95 → 无证据
        custom_config = Config(length_support=0.95)
        detector_custom = LengthDetector(custom_config)
        result_custom = detector_custom.detect(profile)
        assert len(result_custom) == 0

    def test_timestamp_support_affects_timestamp_detector(self):
        """timestamp_support 影响 TimestampDetector：阈值变化改变检测结果"""
        from semantic_detector.detectors.timestamp import TimestampDetector
        from datetime import datetime, timezone

        # support=0.91：在 0.90 和 0.95 之间
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.0,
            capture_time_min=datetime(2020, 1, 1, tzinfo=timezone.utc),
            capture_time_max=datetime(2020, 1, 2, tzinfo=timezone.utc),
            timestamp_be_unix_seconds_support=0.91,
        )

        # 默认 timestamp_support=0.90 → 0.91 >= 0.90 → 有证据
        default_config = Config()
        detector_default = TimestampDetector(default_config)
        result_default = detector_default.detect(profile)
        assert len(result_default) >= 1
        assert result_default[0].coarse_label == "timestamp"

        # 自定义 timestamp_support=0.95 → 0.91 < 0.95 → 无证据
        custom_config = Config(timestamp_support=0.95)
        detector_custom = TimestampDetector(custom_config)
        result_custom = detector_custom.detect(profile)
        assert len(result_custom) == 0

    def test_sequence_unique_ratio_affects_sequence_detector(self):
        """sequence_unique_ratio 影响 SequenceDetector：唯一率预过滤阈值变化"""
        from semantic_detector.detectors.sequence import SequenceDetector

        # unique_ratio=0.6：在 0.50 和 0.70 之间
        # numeric_be_strictly_increasing_ratio=0.9：高于 sequence_increasing_ratio
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.0,
            unique_ratio=0.6,
            numeric_be_strictly_increasing_ratio=0.9,
        )

        # 默认 sequence_unique_ratio=0.70 → 0.6 < 0.70 → 无证据（被预过滤）
        default_config = Config()
        detector_default = SequenceDetector(default_config)
        result_default = detector_default.detect(profile)
        assert len(result_default) == 0

        # 自定义 sequence_unique_ratio=0.50 → 0.6 >= 0.50 → 通过预过滤 → 有证据
        custom_config = Config(sequence_unique_ratio=0.50)
        detector_custom = SequenceDetector(custom_config)
        result_custom = detector_custom.detect(profile)
        assert len(result_custom) >= 1
        assert result_custom[0].coarse_label == "sequence_or_counter"

    def test_sequence_increasing_ratio_affects_sequence_detector(self):
        """sequence_increasing_ratio 影响 SequenceDetector：递增率阈值变化"""
        from semantic_detector.detectors.sequence import SequenceDetector

        # strictly_increasing_ratio=0.85：在 0.80 和 0.90 之间
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.0,
            unique_ratio=0.9,
            numeric_be_strictly_increasing_ratio=0.85,
        )

        # 默认 sequence_increasing_ratio=0.80 → 0.85 >= 0.80 → 有证据
        default_config = Config()
        detector_default = SequenceDetector(default_config)
        result_default = detector_default.detect(profile)
        assert len(result_default) >= 1
        assert result_default[0].coarse_label == "sequence_or_counter"

        # 自定义 sequence_increasing_ratio=0.90 → 0.85 < 0.90 → 无证据
        custom_config = Config(sequence_increasing_ratio=0.90)
        detector_custom = SequenceDetector(custom_config)
        result_custom = detector_custom.detect(profile)
        assert len(result_custom) == 0

    def test_string_printable_ratio_affects_string_detector(self):
        """string_printable_ratio 影响 StringDetector：ASCII 阈值变化改变 fine_label"""
        from semantic_detector.detectors.string import StringDetector

        # printable_ascii_ratio=0.86：在 0.85 和 0.90 之间
        # utf8_decode_success_ratio=0.9：高于 string_nonempty_ratio，保证 UTF-8 回退可触发
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.0,
            printable_ascii_ratio=0.86,
            utf8_decode_success_ratio=0.9,
            all_zero_sample_ratio=0.0,
            nonempty_string_ratio=0.9,
        )

        # 默认 string_printable_ratio=0.85 → 0.86 >= 0.85 → ASCII 路径 → fine_label=ascii_string
        default_config = Config()
        detector_default = StringDetector(default_config)
        result_default = detector_default.detect(profile)
        assert len(result_default) >= 1
        assert result_default[0].coarse_label == "string"
        assert result_default[0].fine_label == "ascii_string"

        # 自定义 string_printable_ratio=0.90 → 0.86 < 0.90 → ASCII 失败 → UTF-8 回退 → fine_label=utf8_string
        custom_config = Config(string_printable_ratio=0.90)
        detector_custom = StringDetector(custom_config)
        result_custom = detector_custom.detect(profile)
        assert len(result_custom) >= 1
        assert result_custom[0].coarse_label == "string"
        assert result_custom[0].fine_label == "utf8_string"

    def test_string_nonempty_ratio_affects_string_detector(self):
        """string_nonempty_ratio 影响 StringDetector：非空率阈值变化"""
        from semantic_detector.detectors.string import StringDetector

        # utf8_decode_success_ratio=0.81：在 0.80 和 0.85 之间
        # printable_ascii_ratio=0.95：高于任何 string_printable_ratio
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.0,
            printable_ascii_ratio=0.95,
            utf8_decode_success_ratio=0.81,
            all_zero_sample_ratio=0.0,
            nonempty_string_ratio=0.9,
        )

        # 默认 string_nonempty_ratio=0.80 → 0.81 >= 0.80 → 有证据
        default_config = Config()
        detector_default = StringDetector(default_config)
        result_default = detector_default.detect(profile)
        assert len(result_default) >= 1
        assert result_default[0].coarse_label == "string"

        # 自定义 string_nonempty_ratio=0.85 → 0.81 < 0.85 → 无证据
        custom_config = Config(string_nonempty_ratio=0.85)
        detector_custom = StringDetector(custom_config)
        result_custom = detector_custom.detect(profile)
        assert len(result_custom) == 0

    def test_identifier_unique_ratio_affects_identifier_detector(self):
        """identifier_unique_ratio 影响 IdentifierDetector：唯一率阈值变化"""
        from semantic_detector.detectors.identifier import IdentifierDetector

        # unique_ratio=0.75：在 0.70 和 0.80 之间
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.0,
            unique_ratio=0.75,
        )

        # 默认 identifier_unique_ratio=0.80 → 0.75 < 0.80 → 无证据
        default_config = Config()
        detector_default = IdentifierDetector(default_config)
        result_default = detector_default.detect(profile)
        assert len(result_default) == 0

        # 自定义 identifier_unique_ratio=0.70 → 0.75 >= 0.70 → 有证据
        custom_config = Config(identifier_unique_ratio=0.70)
        detector_custom = IdentifierDetector(custom_config)
        result_custom = detector_custom.detect(profile)
        assert len(result_custom) >= 1
        assert result_custom[0].coarse_label == "identifier"

    def test_identifier_score_cap_affects_identifier_detector(self):
        """identifier_score_cap 影响 IdentifierDetector：分数上限变化"""
        from semantic_detector.detectors.identifier import IdentifierDetector

        # unique_ratio=0.95：高于任何合理的 score_cap
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.0,
            unique_ratio=0.95,
        )

        # 默认 identifier_score_cap=0.70 → score 被 cap 到 0.70
        default_config = Config()
        detector_default = IdentifierDetector(default_config)
        result_default = detector_default.detect(profile)
        assert len(result_default) == 1
        assert result_default[0].score == 0.70

        # 自定义 identifier_score_cap=0.60 → score 被 cap 到 0.60
        custom_config = Config(identifier_score_cap=0.60)
        detector_custom = IdentifierDetector(custom_config)
        result_custom = detector_custom.detect(profile)
        assert len(result_custom) == 1
        assert result_custom[0].score == 0.60

    def test_payload_entropy_threshold_affects_payload_detector(self):
        """payload_entropy_threshold 影响 PayloadDetector：熵阈值变化"""
        from semantic_detector.detectors.payload import PayloadDetector

        # normalized_entropy=0.75：在 0.70 和 0.80 之间
        profile = FieldProfile(
            sample_count=10,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.0,
            is_last_field_ratio=1.0,
            normalized_entropy=0.75,
        )

        # 默认 payload_entropy_threshold=0.70 → 0.75 >= 0.70 → 有证据
        default_config = Config()
        detector_default = PayloadDetector(default_config)
        result_default = detector_default.detect(profile)
        assert len(result_default) >= 1
        assert result_default[0].coarse_label == "payload"

        # 自定义 payload_entropy_threshold=0.80 → 0.75 < 0.80 → 无证据
        custom_config = Config(payload_entropy_threshold=0.80)
        detector_custom = PayloadDetector(custom_config)
        result_custom = detector_custom.detect(profile)
        assert len(result_custom) == 0
