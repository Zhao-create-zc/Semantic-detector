"""测试常量检测器"""

import pytest
from semantic_detector.detectors.constant import ConstantDetector
from semantic_detector.config import Config
from semantic_detector.profiling.profile_builder import FieldProfile


class TestConstantDetector:
    """测试常量检测器"""
    
    def test_all_samples_identical(self):
        """所有样本值相同，输出 constant hard evidence"""
        config = Config(
            min_samples=8,
            constant_support=0.98
        )
        detector = ConstantDetector(config)
        
        # 创建画像：所有样本值相同
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=10,
            unique_value_count=1,
            dominant_value_ratio=1.0
        )
        
        evidences = detector.detect(profile)
        
        assert len(evidences) == 1
        evidence = evidences[0]
        
        assert evidence.detector == "constant"
        assert evidence.coarse_label == "constant"
        assert evidence.fine_label == "constant_value"
        assert evidence.score == 1.0
        assert evidence.is_hard_evidence is True
        assert evidence.reason_code == "all_samples_identical"
        assert evidence.details["support_ratio"] == 1.0
        assert evidence.details["unique_value_count"] == 1
    
    def test_mostly_constant(self):
        """大部分样本值相同，达到阈值"""
        config = Config(
            min_samples=8,
            constant_support=0.98
        )
        detector = ConstantDetector(config)
        
        # 创建画像：98% 的样本值相同
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            unique_value_count=2,
            dominant_value_ratio=0.98
        )
        
        evidences = detector.detect(profile)
        
        assert len(evidences) == 1
        evidence = evidences[0]
        
        assert evidence.detector == "constant"
        assert evidence.score == 0.98
        assert evidence.is_hard_evidence is True
    
    def test_below_threshold(self):
        """支持率低于阈值，返回空列表"""
        config = Config(
            min_samples=8,
            constant_support=0.98
        )
        detector = ConstantDetector(config)
        
        # 创建画像：97% 的样本值相同（低于阈值）
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            unique_value_count=3,
            dominant_value_ratio=0.97
        )
        
        evidences = detector.detect(profile)
        
        assert len(evidences) == 0
    
    def test_insufficient_samples(self):
        """样本数不足，返回 abstain"""
        config = Config(
            min_samples=8,
            constant_support=0.98
        )
        detector = ConstantDetector(config)
        
        # 创建画像：样本数不足
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=5,
            unique_value_count=1,
            dominant_value_ratio=1.0
        )
        
        evidences = detector.detect(profile)
        
        assert len(evidences) == 1
        evidence = evidences[0]
        
        assert evidence.is_hard_evidence is False
        assert evidence.reason_code == "insufficient_samples"
    
    def test_exactly_min_samples(self):
        """刚好达到最小样本数"""
        config = Config(
            min_samples=8,
            constant_support=0.98
        )
        detector = ConstantDetector(config)
        
        # 创建画像：刚好 8 个样本
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=8,
            unique_value_count=1,
            dominant_value_ratio=1.0
        )
        
        evidences = detector.detect(profile)
        
        assert len(evidences) == 1
        evidence = evidences[0]
        
        assert evidence.is_hard_evidence is True
        assert evidence.score == 1.0
    
    def test_multiple_unique_values(self):
        """多个不同值，支持率低"""
        config = Config(
            min_samples=8,
            constant_support=0.98
        )
        detector = ConstantDetector(config)
        
        # 创建画像：多个不同值
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            unique_value_count=50,
            dominant_value_ratio=0.5
        )
        
        evidences = detector.detect(profile)
        
        assert len(evidences) == 0


class TestConstantDetectorBoundary:
    """测试常量检测器边界情况"""
    
    def test_97_percent_support_below_threshold(self):
        """97% 支持率，低于 98% 阈值，不通过"""
        config = Config(
            min_samples=8,
            constant_support=0.98
        )
        detector = ConstantDetector(config)
        
        # 创建画像：97% 支持率
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            unique_value_count=3,
            dominant_value_ratio=0.97
        )
        
        evidences = detector.detect(profile)
        
        # 97% < 98%，不通过
        assert len(evidences) == 0
    
    def test_98_percent_support_at_threshold(self):
        """98% 支持率，刚好达到 98% 阈值，通过"""
        config = Config(
            min_samples=8,
            constant_support=0.98
        )
        detector = ConstantDetector(config)
        
        # 创建画像：98% 支持率
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            unique_value_count=2,
            dominant_value_ratio=0.98
        )
        
        evidences = detector.detect(profile)
        
        # 98% >= 98%，通过
        assert len(evidences) == 1
        evidence = evidences[0]
        assert evidence.is_hard_evidence is True
        assert evidence.score == 0.98
    
    def test_99_percent_support_above_threshold(self):
        """99% 支持率，超过 98% 阈值，通过"""
        config = Config(
            min_samples=8,
            constant_support=0.98
        )
        detector = ConstantDetector(config)
        
        # 创建画像：99% 支持率
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            unique_value_count=2,
            dominant_value_ratio=0.99
        )
        
        evidences = detector.detect(profile)
        
        # 99% >= 98%，通过
        assert len(evidences) == 1
        evidence = evidences[0]
        assert evidence.is_hard_evidence is True
        assert evidence.score == 0.99
    
    def test_strict_threshold_behavior(self):
        """严格阈值行为：差 0.01 就不通过"""
        config = Config(
            min_samples=8,
            constant_support=0.98
        )
        detector = ConstantDetector(config)
        
        # 测试 0.9799（差一点点）
        profile_just_below = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=10000,
            unique_value_count=2,
            dominant_value_ratio=0.9799
        )
        
        evidences = detector.detect(profile_just_below)
        assert len(evidences) == 0
        
        # 测试 0.98（刚好）
        profile_exact = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=10000,
            unique_value_count=2,
            dominant_value_ratio=0.98
        )
        
        evidences = detector.detect(profile_exact)
        assert len(evidences) == 1
        assert evidences[0].score == 0.98


class TestConstantDetectorEdgeCases:
    """测试常量检测器不足样本和空值情况"""
    
    def test_zero_samples(self):
        """零样本返回 abstain"""
        config = Config(
            min_samples=8,
            constant_support=0.98
        )
        detector = ConstantDetector(config)
        
        # 创建画像：零样本
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=0,
            unique_value_count=0,
            dominant_value_ratio=0.0
        )
        
        evidences = detector.detect(profile)
        
        # 样本数不足，返回 abstain
        assert len(evidences) == 1
        evidence = evidences[0]
        assert evidence.is_hard_evidence is False
        assert evidence.reason_code == "insufficient_samples"
        assert evidence.details["sample_count"] == 0
        assert evidence.details["min_samples"] == 8
        assert evidence.details["shortage"] == 8
    
    def test_one_sample_below_min(self):
        """1 个样本，低于 min_samples，返回 abstain"""
        config = Config(
            min_samples=8,
            constant_support=0.98
        )
        detector = ConstantDetector(config)
        
        # 创建画像：1 个样本
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=1,
            unique_value_count=1,
            dominant_value_ratio=1.0
        )
        
        evidences = detector.detect(profile)
        
        assert len(evidences) == 1
        evidence = evidences[0]
        assert evidence.is_hard_evidence is False
        assert evidence.reason_code == "insufficient_samples"
        assert evidence.details["shortage"] == 7
    
    def test_seven_samples_below_min(self):
        """7 个样本，刚好少一个，返回 abstain"""
        config = Config(
            min_samples=8,
            constant_support=0.98
        )
        detector = ConstantDetector(config)
        
        # 创建画像：7 个样本
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=7,
            unique_value_count=1,
            dominant_value_ratio=1.0
        )
        
        evidences = detector.detect(profile)
        
        assert len(evidences) == 1
        evidence = evidences[0]
        assert evidence.is_hard_evidence is False
        assert evidence.reason_code == "insufficient_samples"
        assert evidence.details["shortage"] == 1
    
    def test_abstain_has_correct_structure(self):
        """abstain 证据结构正确"""
        config = Config(
            min_samples=8,
            constant_support=0.98
        )
        detector = ConstantDetector(config)
        
        # 创建画像：样本数不足
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=5,
            unique_value_count=1,
            dominant_value_ratio=1.0
        )
        
        evidences = detector.detect(profile)
        
        assert len(evidences) == 1
        evidence = evidences[0]
        
        # 验证 abstain 证据结构
        assert evidence.detector == "constant"
        assert evidence.coarse_label == "unknown"
        assert evidence.fine_label == "unknown"
        assert evidence.score == 0.0
        assert evidence.is_hard_evidence is False
        assert evidence.reason_code == "insufficient_samples"
        assert "sample_count" in evidence.details
        assert "min_samples" in evidence.details
        assert "shortage" in evidence.details
    
    def test_empty_candidate_vs_abstain(self):
        """区分空候选和 abstain"""
        config = Config(
            min_samples=8,
            constant_support=0.98
        )
        detector = ConstantDetector(config)
        
        # 情况 1：样本数不足，返回 abstain
        profile_insufficient = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=5,
            unique_value_count=1,
            dominant_value_ratio=1.0
        )
        
        evidences_insufficient = detector.detect(profile_insufficient)
        assert len(evidences_insufficient) == 1
        assert evidences_insufficient[0].is_hard_evidence is False
        assert evidences_insufficient[0].reason_code == "insufficient_samples"
        
        # 情况 2：样本数足够但支持率低，返回空列表
        profile_low_support = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            unique_value_count=50,
            dominant_value_ratio=0.5
        )
        
        evidences_low_support = detector.detect(profile_low_support)
        assert len(evidences_low_support) == 0
