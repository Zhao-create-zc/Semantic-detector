"""测试检测流水线"""

import pytest
from semantic_detector.pipeline.pipeline import DetectionPipeline
from semantic_detector.scoring.resolver import Resolver
from semantic_detector.profiling.profile_builder import FieldProfile
from semantic_detector.contracts import Direction, SemanticPrediction


class TestDetectionPipeline:
    """测试检测流水线"""

    def test_pipeline_init(self):
        """初始化检测流水线"""
        pipeline = DetectionPipeline()

        assert pipeline.detectors is not None
        assert len(pipeline.detectors) > 0
        assert pipeline.resolver is not None

    def test_pipeline_init_with_custom_resolver(self):
        """使用自定义解析器初始化"""
        resolver = Resolver(min_score=0.7, ambiguity_margin=0.15)
        pipeline = DetectionPipeline(resolver=resolver)

        assert pipeline.resolver.min_score == 0.7
        assert pipeline.resolver.ambiguity_margin == 0.15

    def test_detect_field_returns_prediction(self):
        """对单个 FieldProfile 执行检测返回预测"""
        pipeline = DetectionPipeline()

        # 创建一个简单的 FieldProfile
        profile = FieldProfile(
            layout_id="test_layout",
            direction=str(Direction.REQUEST),
            field_index=0,
            sample_count=10,
            width_min=4,
            width_max=4,
            width_mode=4,
            fixed_width=True,
            dominant_value_ratio=1.0
        )

        prediction = pipeline.detect_field(profile)

        assert prediction is not None
        assert prediction.coarse_label is not None

    def test_detect_fields_returns_predictions(self):
        """对多个 FieldProfile 执行检测返回预测列表"""
        pipeline = DetectionPipeline()

        # 创建两个 FieldProfile
        profile1 = FieldProfile(
            layout_id="test_layout",
            direction=str(Direction.REQUEST),
            field_index=0,
            sample_count=10,
            width_min=4,
            width_max=4,
            width_mode=4,
            fixed_width=True,
            dominant_value_ratio=1.0
        )

        profile2 = FieldProfile(
            layout_id="test_layout",
            direction=str(Direction.REQUEST),
            field_index=1,
            sample_count=10,
            width_min=4,
            width_max=4,
            width_mode=4,
            fixed_width=True,
            dominant_value_ratio=1.0
        )

        predictions = pipeline.detect_fields([profile1, profile2])

        assert len(predictions) == 2
        assert predictions[0] is not None
        assert predictions[1] is not None

    def test_detect_constant_field(self):
        """检测常量字段"""
        pipeline = DetectionPipeline()

        # 创建一个常量字段（dominant_value_ratio = 1.0）
        profile = FieldProfile(
            layout_id="test_layout",
            direction=str(Direction.REQUEST),
            field_index=0,
            sample_count=100,
            width_min=4,
            width_max=4,
            width_mode=4,
            fixed_width=True,
            dominant_value_ratio=1.0
        )

        prediction = pipeline.detect_field(profile)

        assert prediction is not None
        # 常量字段应该被检测为 constant
        assert prediction.coarse_label == "constant"


class TestDetectFieldSemanticPrediction:
    """R241: detect_field 包装完整 SemanticPrediction

    03 教程 HIGH-3：Pipeline 输出 SemanticPrediction 而非 DetectorEvidence。
    验收：合成 length profile；run_id/layout/direction/index/status/evidence 完整。
    """

    def _make_length_profile(self, field_index: int = 0):
        """合成 length profile：触发 LengthDetector 输出 hard evidence。"""
        return FieldProfile(
            layout_id="layout_length",
            direction=Direction.REQUEST.value,
            field_index=field_index,
            sample_count=10,
            width_min=4,
            width_max=4,
            width_mode=4,
            fixed_width=True,
            dominant_value_ratio=0.0,
            unique_ratio=0.5,
            # R276：使用 exact_support 替代 correlation（教程 8.1/8.4）
            # distinct_value_count >= 2 才可能是长度字段（教程 8.4）
            numeric_be_message_length_exact_support=0.95,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
        )

    def _make_abstained_profile(self):
        """合成 abstained profile：所有检测器都不触发，无候选。"""
        return FieldProfile(
            layout_id="layout_empty",
            direction=Direction.REQUEST.value,
            field_index=2,
            sample_count=10,
            width_min=4,
            width_max=4,
            width_mode=4,
            fixed_width=True,
            dominant_value_ratio=0.5,  # 非常量
            unique_ratio=0.5,  # 不触发 identifier
            is_last_field_ratio=0.0,  # 非 trailing，不触发 payload
        )

    def test_detect_field_returns_semantic_prediction_instance(self):
        """detect_field 必须返回 SemanticPrediction 实例。"""
        pipeline = DetectionPipeline(run_id="run-test-001")

        prediction = pipeline.detect_field(self._make_length_profile())

        assert isinstance(prediction, SemanticPrediction)

    def test_detect_field_length_profile_confirmed_status(self):
        """合成 length profile -> prediction_status=confirmed，evidence 完整。"""
        pipeline = DetectionPipeline(run_id="run-test-001")

        prediction = pipeline.detect_field(self._make_length_profile())

        # length 是 hard evidence -> confirmed
        assert prediction.prediction_status == "confirmed"
        assert prediction.abstained is False
        assert prediction.coarse_label == "length"
        assert prediction.confidence > 0.0
        # evidence 非空，且第一个是 primary（length hard evidence）
        assert len(prediction.evidence) >= 1
        assert prediction.evidence[0].coarse_label == "length"

    def test_detect_field_contains_full_identity(self):
        """run_id/layout/direction/index 必须完整。"""
        pipeline = DetectionPipeline(run_id="run-test-001")

        prediction = pipeline.detect_field(self._make_length_profile(field_index=3))

        assert prediction.run_id == "run-test-001"
        assert prediction.layout_id == "layout_length"
        assert prediction.direction == Direction.REQUEST
        assert prediction.field_index == 3

    def test_detect_field_abstained_when_no_candidates(self):
        """无候选 -> prediction_status=abstained，abstained=True。"""
        pipeline = DetectionPipeline(run_id="run-test-001")

        prediction = pipeline.detect_field(self._make_abstained_profile())

        assert prediction.prediction_status == "abstained"
        assert prediction.abstained is True
        assert prediction.coarse_label == "unknown"
        # abstained 时 evidence 仍包含 unknown primary
        assert len(prediction.evidence) >= 1
        assert prediction.evidence[0].coarse_label == "unknown"

    def test_detect_field_alternatives_serialized_as_dicts(self):
        """alternatives 是序列化后的 dict 元组。"""
        pipeline = DetectionPipeline(run_id="run-test-001")

        prediction = pipeline.detect_field(self._make_length_profile())

        # alternatives 是 tuple of dict（可能为空，如果 length 是唯一候选）
        assert isinstance(prediction.alternatives, tuple)
        for alt in prediction.alternatives:
            assert isinstance(alt, dict)
            assert "detector" in alt
            assert "coarse_label" in alt


class TestPipelineConfigInstanceR355:
    """R355: Pipeline 接收唯一 Config 实例

    计划 L1038-1061 要求：
    - DetectionPipeline(config: Config, ...)
    - 禁止在内部再次 Config()
    - 所有检测器和 Resolver 必须引用同一配置快照
    """

    def test_pipeline_accepts_config_parameter(self):
        """Pipeline 接受 config 参数"""
        from semantic_detector.config import Config

        config = Config(min_samples=5, constant_support=0.95)
        pipeline = DetectionPipeline(config=config)

        # 验证 config 被存储
        assert pipeline.config is config
        assert pipeline.config.min_samples == 5
        assert pipeline.config.constant_support == 0.95

    def test_pipeline_defaults_to_config_when_not_specified(self):
        """未传 config 时用默认 Config()（向后兼容）"""
        pipeline = DetectionPipeline()

        # 验证使用了默认 Config
        assert pipeline.config is not None
        assert pipeline.config.min_samples == 8
        assert pipeline.config.constant_support == 0.98

    def test_pipeline_config_shared_with_detectors(self):
        """所有检测器引用同一 config 实例"""
        from semantic_detector.config import Config

        config = Config(min_samples=12, constant_support=0.99)
        pipeline = DetectionPipeline(config=config)

        # 验证所有检测器都持有同一个 config 对象
        assert len(pipeline.detectors) > 0
        for detector in pipeline.detectors:
            # TypeOpcodeDetector 没有 config 属性，跳过
            if hasattr(detector, 'config'):
                assert detector.config is config, (
                    f"检测器 {detector.name} 的 config 不是共享实例"
                )

    def test_pipeline_resolver_uses_config_ambiguity_margin(self):
        """Resolver 使用 config 的 ambiguity_margin"""
        from semantic_detector.config import Config

        config = Config(ambiguity_margin=0.15)
        pipeline = DetectionPipeline(config=config)

        # 验证 Resolver 的 ambiguity_margin 来自 config
        assert pipeline.resolver.ambiguity_margin == 0.15

    def test_pipeline_default_resolver_ambiguity_margin(self):
        """默认 config 时 Resolver 使用默认 ambiguity_margin"""
        pipeline = DetectionPipeline()

        # 默认 Config 的 ambiguity_margin 是 0.08
        assert pipeline.resolver.ambiguity_margin == 0.08

    def test_pipeline_custom_resolver_overrides_config(self):
        """显式传入 resolver 时优先使用，不覆盖 config"""
        from semantic_detector.config import Config

        config = Config(ambiguity_margin=0.15)
        resolver = Resolver(min_score=0.7, ambiguity_margin=0.20)
        pipeline = DetectionPipeline(config=config, resolver=resolver)

        # 显式 resolver 优先
        assert pipeline.resolver is resolver
        assert pipeline.resolver.ambiguity_margin == 0.20
        assert pipeline.resolver.min_score == 0.7

    def test_pipeline_custom_config_affects_detectors(self):
        """自定义 config 影响检测器行为（min_samples 传递）"""
        from semantic_detector.config import Config

        # 用非默认 min_samples 创建 Pipeline
        config = Config(min_samples=20)
        pipeline = DetectionPipeline(config=config)

        # 验证至少一个检测器的 config.min_samples == 20
        detector_configs = [
            d.config for d in pipeline.detectors if hasattr(d, 'config')
        ]
        assert len(detector_configs) > 0
        for dc in detector_configs:
            assert dc.min_samples == 20

    def test_pipeline_no_internal_config_creation_when_provided(self):
        """传入 config 时不在内部创建新 Config()"""
        from semantic_detector.config import Config

        custom_config = Config(min_samples=15, constant_support=0.97)
        pipeline = DetectionPipeline(config=custom_config)

        # 验证 pipeline.config 是传入的实例（不是内部新建的）
        assert pipeline.config is custom_config

        # 验证检测器的 config 也是传入的实例（不是内部新建的）
        for detector in pipeline.detectors:
            if hasattr(detector, 'config'):
                assert detector.config is custom_config

    def test_pipeline_two_instances_with_different_configs(self):
        """两个 Pipeline 实例使用不同 config 互不影响"""
        from semantic_detector.config import Config

        config1 = Config(min_samples=5, constant_support=0.95)
        config2 = Config(min_samples=20, constant_support=0.99)

        pipeline1 = DetectionPipeline(config=config1)
        pipeline2 = DetectionPipeline(config=config2)

        # 验证两个 Pipeline 的 config 不同
        assert pipeline1.config is not pipeline2.config
        assert pipeline1.config.min_samples == 5
        assert pipeline2.config.min_samples == 20

        # 验证两个 Pipeline 的检测器 config 也不同
        for d1, d2 in zip(pipeline1.detectors, pipeline2.detectors):
            if hasattr(d1, 'config') and hasattr(d2, 'config'):
                assert d1.config is config1
                assert d2.config is config2
                assert d1.config is not d2.config
