"""测试 run_id 生成和固定随机无关性

验证 DetectionPipeline 的 run_id 生成功能。
"""

import pytest
import re
from semantic_detector.pipeline.pipeline import DetectionPipeline
from semantic_detector.profiling.profile_builder import FieldProfile
from semantic_detector.contracts import Direction


class TestRunId:
    """run_id 测试"""
    
    def test_run_id_generated(self):
        """测试 run_id 自动生成"""
        pipeline = DetectionPipeline()
        
        assert pipeline.run_id is not None
        assert isinstance(pipeline.run_id, str)
        assert len(pipeline.run_id) > 0
    
    def test_run_id_format(self):
        """测试 run_id 格式为 UUID"""
        pipeline = DetectionPipeline()
        
        # UUID 格式: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        )
        assert uuid_pattern.match(pipeline.run_id) is not None
    
    def test_run_id_unique(self):
        """测试 run_id 唯一性"""
        pipeline1 = DetectionPipeline()
        pipeline2 = DetectionPipeline()
        
        assert pipeline1.run_id != pipeline2.run_id
    
    def test_run_id_custom(self):
        """测试自定义 run_id"""
        custom_id = "custom-run-id-12345"
        pipeline = DetectionPipeline(run_id=custom_id)
        
        assert pipeline.run_id == custom_id
    
    def test_run_id_does_not_affect_results(self):
        """测试 run_id 不影响检测结果顺序"""
        # 创建两个 pipeline，使用不同的 run_id
        pipeline1 = DetectionPipeline(run_id="run-1")
        pipeline2 = DetectionPipeline(run_id="run-2")
        
        # 创建相同的输入
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
                layout_id="layout_0",
                direction=str(Direction.REQUEST),
                field_index=1,
                sample_count=10,
                width_min=4,
                width_max=4,
                width_mode=4,
                fixed_width=True
            )
        ]
        
        # 执行检测
        predictions1 = pipeline1.detect_fields(profiles)
        predictions2 = pipeline2.detect_fields(profiles)
        
        # 验证结果相同（run_id 不影响检测结果）
        assert len(predictions1) == len(predictions2)
        for p1, p2 in zip(predictions1, predictions2):
            assert p1.coarse_label == p2.coarse_label
            assert p1.fine_label == p2.fine_label
            # R242: detect_fields 返回 SemanticPrediction，用 confidence 替代 score
            assert p1.confidence == p2.confidence
