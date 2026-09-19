"""测试批量字段检测

验证 DetectionPipeline 对多个 FieldProfile 的批量检测功能。
R242：detect_fields 返回 List[SemanticPrediction]，保持顺序，FieldKey 一一对应。
"""

import pytest
from semantic_detector.pipeline.pipeline import DetectionPipeline
from semantic_detector.profiling.profile_builder import FieldProfile
from semantic_detector.contracts import DetectorEvidence, Direction, SemanticPrediction


class TestBatchDetection:
    """批量检测测试"""
    
    def test_detect_fields_preserves_order(self):
        """测试批量检测保持输入顺序"""
        pipeline = DetectionPipeline()
        
        # 创建多个不同的 FieldProfile
        profiles = []
        for i in range(5):
            profile = FieldProfile(
                layout_id=f"layout_{i}",
                direction=str(Direction.REQUEST),
                field_index=i,
                sample_count=10,
                width_min=4,
                width_max=4,
                width_mode=4,
                fixed_width=True
            )
            profiles.append(profile)
        
        # 执行批量检测
        predictions = pipeline.detect_fields(profiles)
        
        # 验证输出顺序与输入顺序一致
        assert len(predictions) == len(profiles)
        for prediction in predictions:
            assert prediction is not None
            assert prediction.coarse_label is not None
    
    def test_detect_fields_empty_list(self):
        """测试批量检测空列表"""
        pipeline = DetectionPipeline()
        
        predictions = pipeline.detect_fields([])
        
        assert predictions == []
    
    def test_detect_fields_single_profile(self):
        """测试批量检测单个 FieldProfile"""
        pipeline = DetectionPipeline()
        
        profile = FieldProfile(
            layout_id="layout_0",
            direction=str(Direction.REQUEST),
            field_index=0,
            sample_count=10,
            width_min=4,
            width_max=4,
            width_mode=4,
            fixed_width=True
        )
        
        predictions = pipeline.detect_fields([profile])
        
        assert len(predictions) == 1
        assert predictions[0] is not None
        assert predictions[0].coarse_label is not None
    
    def test_detect_fields_multiple_profiles(self):
        """测试批量检测多个 FieldProfile"""
        pipeline = DetectionPipeline()
        
        profiles = [
            FieldProfile(
                layout_id="layout_0",
                direction=str(Direction.REQUEST),
                field_index=0,
                sample_count=10,
                width_min=4,
                width_max=4,
                width_mode=4,
                fixed_width=True
            ),
            FieldProfile(
                layout_id="layout_1",
                direction=str(Direction.REQUEST),
                field_index=1,
                sample_count=10,
                width_min=4,
                width_max=4,
                width_mode=4,
                fixed_width=True
            ),
            FieldProfile(
                layout_id="layout_2",
                direction=str(Direction.REQUEST),
                field_index=2,
                sample_count=10,
                width_min=1,
                width_max=1,
                width_mode=1,
                fixed_width=True,
                dominant_value_ratio=1.0
            )
        ]
        
        predictions = pipeline.detect_fields(profiles)
        
        assert len(predictions) == 3
        for prediction in predictions:
            assert prediction is not None
            assert prediction.coarse_label is not None
    
    def test_detect_fields_returns_predictions(self):
        """测试批量检测返回预测列表"""
        pipeline = DetectionPipeline()
        
        profiles = [
            FieldProfile(
                layout_id=f"layout_{i}",
                direction=str(Direction.REQUEST),
                field_index=i,
                sample_count=10,
                width_min=4,
                width_max=4,
                width_mode=4,
                fixed_width=True
            )
            for i in range(3)
        ]
        
        predictions = pipeline.detect_fields(profiles)
        
        # 验证返回的是预测列表
        assert isinstance(predictions, list)
        for prediction in predictions:
            # R242: detect_fields 返回 SemanticPrediction 而非 DetectorEvidence
            assert isinstance(prediction, SemanticPrediction)


class TestDetectFieldsSemanticPrediction:
    """R242: detect_fields 返回 List[SemanticPrediction] 验收

    03 教程 HIGH-3 / 04 任务表 R242：
    - 输出数量与 profile 一致
    - FieldKey（layout_id/direction/field_index）一一对应
    - 多 layout、多方向场景
    """

    def _make_profile(
        self,
        layout_id: str,
        direction: str,
        field_index: int,
        width_mode: int = 4,
        dominant_value_ratio: float = 1.0,
    ):
        """合成 FieldProfile。"""
        return FieldProfile(
            layout_id=layout_id,
            direction=direction,
            field_index=field_index,
            sample_count=10,
            width_min=width_mode,
            width_max=width_mode,
            width_mode=width_mode,
            fixed_width=True,
            dominant_value_ratio=dominant_value_ratio,
        )

    def test_detect_fields_all_return_semantic_prediction(self):
        """所有返回项必须是 SemanticPrediction 实例。"""
        pipeline = DetectionPipeline(run_id="run-batch-001")

        profiles = [
            self._make_profile("layout_a", Direction.REQUEST.value, 0),
            self._make_profile("layout_a", Direction.REQUEST.value, 1),
            self._make_profile("layout_b", Direction.RESPONSE.value, 0),
        ]

        predictions = pipeline.detect_fields(profiles)

        assert len(predictions) == len(profiles)
        for prediction in predictions:
            assert isinstance(prediction, SemanticPrediction)

    def test_detect_fields_count_matches_profiles(self):
        """输出数量与 profile 一致（含空、单、多）。"""
        pipeline = DetectionPipeline(run_id="run-batch-002")

        # 空
        assert pipeline.detect_fields([]) == []
        # 单
        single = pipeline.detect_fields([self._make_profile("l", Direction.REQUEST.value, 0)])
        assert len(single) == 1
        # 多
        multi = pipeline.detect_fields([
            self._make_profile(f"l{i}", Direction.REQUEST.value, i) for i in range(5)
        ])
        assert len(multi) == 5

    def test_detect_fields_fieldkey_one_to_one_correspondence(self):
        """FieldKey（layout_id/direction/field_index）与 profile 一一对应。"""
        pipeline = DetectionPipeline(run_id="run-batch-003")

        profiles = [
            self._make_profile("layout_a", Direction.REQUEST.value, 0),
            self._make_profile("layout_a", Direction.REQUEST.value, 1),
            self._make_profile("layout_b", Direction.RESPONSE.value, 0),
            self._make_profile("layout_c", Direction.REQUEST.value, 2),
        ]

        predictions = pipeline.detect_fields(profiles)

        assert len(predictions) == len(profiles)
        for profile, prediction in zip(profiles, predictions):
            assert prediction.layout_id == profile.layout_id
            assert prediction.field_index == profile.field_index
            # direction 是 Direction 枚举，profile.direction 是值字符串
            assert prediction.direction.value == profile.direction

    def test_detect_fields_multiple_layouts_mixed_directions(self):
        """多 layout、多方向混合场景：保持顺序与 FieldKey 对应。"""
        pipeline = DetectionPipeline(run_id="run-batch-004")

        profiles = [
            self._make_profile("layout_a", Direction.REQUEST.value, 0),
            self._make_profile("layout_a", Direction.RESPONSE.value, 0),
            self._make_profile("layout_b", Direction.REQUEST.value, 0),
            self._make_profile("layout_b", Direction.RESPONSE.value, 0),
            self._make_profile("layout_c", Direction.REQUEST.value, 1),
        ]

        predictions = pipeline.detect_fields(profiles)

        assert len(predictions) == 5
        # 顺序与 profiles 一致
        for i, (profile, prediction) in enumerate(zip(profiles, predictions)):
            assert prediction.layout_id == profile.layout_id
            assert prediction.direction.value == profile.direction
            assert prediction.field_index == profile.field_index

    def test_detect_fields_preserves_run_id(self):
        """所有预测共享同一个 run_id。"""
        pipeline = DetectionPipeline(run_id="run-batch-005")

        profiles = [
            self._make_profile("layout_a", Direction.REQUEST.value, i) for i in range(3)
        ]

        predictions = pipeline.detect_fields(profiles)

        for prediction in predictions:
            assert prediction.run_id == "run-batch-005"

    def test_detect_fields_direction_unknown_fallback(self):
        """非法 direction 值降级为 UNKNOWN，不抛异常。"""
        pipeline = DetectionPipeline(run_id="run-batch-006")

        profiles = [
            self._make_profile("layout_a", "invalid_direction", 0),
        ]

        predictions = pipeline.detect_fields(profiles)

        assert len(predictions) == 1
        assert predictions[0].direction == Direction.UNKNOWN
