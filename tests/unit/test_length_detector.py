"""测试长度检测器"""

import pytest
from semantic_detector.detectors.length import LengthDetector
from semantic_detector.config import Config
from semantic_detector.profiling.profile_builder import FieldProfile


class TestLengthDetector:
    """测试长度检测器"""
    
    def test_total_message_length(self):
        """检测消息长度字段"""
        config = Config(
            min_samples=8,
            length_support=0.90
        )
        detector = LengthDetector(config)
        
        # 创建画像：字段值等于消息长度
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            numeric_be_message_length_exact_support=0.95,
            numeric_be_remaining_bytes_exact_support=None
        )
        
        evidences = detector.detect(profile)
        
        assert len(evidences) == 1
        evidence = evidences[0]
        
        assert evidence.detector == "length"
        assert evidence.coarse_label == "length"
        assert evidence.fine_label == "total_message_length"
        assert evidence.score == 0.95
        assert evidence.is_hard_evidence is True
        assert evidence.reason_code == "value_equals_message_length"
        assert evidence.details["relation"] == "total"
    
    def test_remaining_bytes(self):
        """检测剩余字节字段"""
        config = Config(
            min_samples=8,
            length_support=0.90
        )
        detector = LengthDetector(config)
        
        # 创建画像：字段值等于剩余字节
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            numeric_be_message_length_exact_support=None,
            numeric_be_remaining_bytes_exact_support=0.92
        )
        
        evidences = detector.detect(profile)
        
        assert len(evidences) == 1
        evidence = evidences[0]
        
        assert evidence.detector == "length"
        assert evidence.coarse_label == "length"
        assert evidence.fine_label == "remaining_bytes"
        assert evidence.score == 0.92
        assert evidence.is_hard_evidence is True
        assert evidence.reason_code == "value_equals_remaining_bytes"
        assert evidence.details["relation"] == "remaining"
    
    def test_both_relations(self):
        """同时检测到两种关系"""
        config = Config(
            min_samples=8,
            length_support=0.90
        )
        detector = LengthDetector(config)
        
        # 创建画像：同时满足两种关系
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            numeric_be_message_length_exact_support=0.95,
            numeric_be_remaining_bytes_exact_support=0.93
        )
        
        evidences = detector.detect(profile)
        
        # 应该输出两个证据
        assert len(evidences) == 2
        
        # 验证两个证据的 fine label 不同
        fine_labels = [e.fine_label for e in evidences]
        assert "total_message_length" in fine_labels
        assert "remaining_bytes" in fine_labels
    
    def test_below_threshold(self):
        """支持率低于阈值"""
        config = Config(
            min_samples=8,
            length_support=0.90
        )
        detector = LengthDetector(config)
        
        # 创建画像：支持率低于阈值
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            numeric_be_message_length_exact_support=0.85,
            numeric_be_remaining_bytes_exact_support=None
        )
        
        evidences = detector.detect(profile)
        
        assert len(evidences) == 0
    
    def test_insufficient_samples(self):
        """样本数不足"""
        config = Config(
            min_samples=8,
            length_support=0.90
        )
        detector = LengthDetector(config)
        
        # 创建画像：样本数不足
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=5,
            fixed_width=True,
            width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            numeric_be_message_length_exact_support=1.0,
            numeric_be_remaining_bytes_exact_support=None
        )
        
        evidences = detector.detect(profile)
        
        assert len(evidences) == 1
        evidence = evidences[0]
        
        assert evidence.is_hard_evidence is False
        assert evidence.reason_code == "insufficient_samples"
    
    def test_no_correlation(self):
        """无相关性"""
        config = Config(
            min_samples=8,
            length_support=0.90
        )
        detector = LengthDetector(config)
        
        # 创建画像：无相关性
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            numeric_be_message_length_exact_support=None,
            numeric_be_remaining_bytes_exact_support=None
        )
        
        evidences = detector.detect(profile)
        
        assert len(evidences) == 0


class TestLengthDetectorEndian:
    """测试 LengthDetector 的 BE/LE 支持"""
    
    def test_be_dataset(self):
        """BE 数据集：选择 BE endian"""
        config = Config(
            min_samples=8,
            length_support=0.90
        )
        detector = LengthDetector(config)
        
        # 创建画像：BE 支持率高，LE 支持率低
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            numeric_be_message_length_exact_support=0.95,
            numeric_le_message_length_exact_support=0.50
        )
        
        evidences = detector.detect(profile)
        
        assert len(evidences) == 1
        evidence = evidences[0]
        
        assert evidence.details["endian"] == "be"
        assert evidence.score == 0.95
    
    def test_le_dataset(self):
        """LE 数据集：选择 LE endian"""
        config = Config(
            min_samples=8,
            length_support=0.90
        )
        detector = LengthDetector(config)
        
        # 创建画像：LE 支持率高，BE 支持率低
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            numeric_be_message_length_exact_support=0.50,
            numeric_le_message_length_exact_support=0.92
        )
        
        evidences = detector.detect(profile)
        
        assert len(evidences) == 1
        evidence = evidences[0]
        
        assert evidence.details["endian"] == "le"
        assert evidence.score == 0.92
    
    def test_both_endians_high_support(self):
        """BE 和 LE 都高支持：选择支持率更高的"""
        config = Config(
            min_samples=8,
            length_support=0.90
        )
        detector = LengthDetector(config)
        
        # 创建画像：BE 和 LE 都高支持
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            numeric_be_message_length_exact_support=0.95,
            numeric_le_message_length_exact_support=0.93
        )
        
        evidences = detector.detect(profile)
        
        # 应该输出两个证据，BE 在前（支持率更高）
        assert len(evidences) == 2
        assert evidences[0].details["endian"] == "be"
        assert evidences[0].score == 0.95
        assert evidences[1].details["endian"] == "le"
        assert evidences[1].score == 0.93
    
    def test_no_endian_bias(self):
        """不先验偏置：根据数据选择"""
        config = Config(
            min_samples=8,
            length_support=0.90
        )
        detector = LengthDetector(config)
        
        # 创建画像：只有 LE 满足阈值
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            numeric_be_message_length_exact_support=0.50,
            numeric_le_message_length_exact_support=0.95
        )
        
        evidences = detector.detect(profile)
        
        # 应该选择 LE，而不是预设的 BE
        assert len(evidences) == 1
        assert evidences[0].details["endian"] == "le"
    
    def test_remaining_bytes_be_vs_le(self):
        """remaining_bytes 的 BE/LE 选择"""
        config = Config(
            min_samples=8,
            length_support=0.90
        )
        detector = LengthDetector(config)
        
        # 创建画像：BE 和 LE 的 remaining_bytes
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            numeric_be_remaining_bytes_exact_support=0.91,
            numeric_le_remaining_bytes_exact_support=0.96
        )
        
        evidences = detector.detect(profile)
        
        # LE 支持率更高，应该排在前面
        assert len(evidences) == 2
        assert evidences[0].details["endian"] == "le"
        assert evidences[0].score == 0.96


class TestLengthDetectorConstantField:
    """测试 LengthDetector 排除常量字段"""
    
    def test_constant_field_excluded(self):
        """常量字段：不输出长度证据"""
        config = Config(
            min_samples=8,
            length_support=0.90
        )
        detector = LengthDetector(config)
        
        # 创建画像：常量字段（dominant_value_ratio = 1.0）
        # 即使有长度相关性，也不输出长度证据
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=2,
            dominant_value_ratio=1.0,
            numeric_be_message_length_exact_support=0.95,
            numeric_be_remaining_bytes_exact_support=None
        )
        
        evidences = detector.detect(profile)
        
        # 常量字段不输出长度证据
        assert len(evidences) == 0
    
    def test_near_constant_field_excluded(self):
        """接近常量字段（dominant_value_ratio >= 0.98）：不输出长度证据"""
        config = Config(
            min_samples=8,
            length_support=0.90
        )
        detector = LengthDetector(config)
        
        # 创建画像：接近常量字段（dominant_value_ratio = 0.99）
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=2,
            dominant_value_ratio=0.99,
            numeric_be_message_length_exact_support=0.95,
            numeric_be_remaining_bytes_exact_support=None
        )
        
        evidences = detector.detect(profile)
        
        # 接近常量字段不输出长度证据
        assert len(evidences) == 0
    
    def test_constant_field_boundary(self):
        """常量字段边界：dominant_value_ratio = 0.98"""
        config = Config(
            min_samples=8,
            length_support=0.90
        )
        detector = LengthDetector(config)
        
        # 创建画像：dominant_value_ratio = 0.98（边界）
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=2,
            dominant_value_ratio=0.98,
            numeric_be_message_length_exact_support=0.95,
            numeric_be_remaining_bytes_exact_support=None
        )
        
        evidences = detector.detect(profile)
        
        # 边界情况：不输出长度证据
        assert len(evidences) == 0
    
    def test_non_constant_field_included(self):
        """非常量字段：输出长度证据"""
        config = Config(
            min_samples=8,
            length_support=0.90
        )
        detector = LengthDetector(config)
        
        # 创建画像：非常量字段（dominant_value_ratio = 0.97）
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=2,
            dominant_value_ratio=0.97,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            numeric_be_message_length_exact_support=0.95,
            numeric_be_remaining_bytes_exact_support=None
        )
        
        evidences = detector.detect(profile)
        
        # 非常量字段输出长度证据
        assert len(evidences) == 1
        assert evidences[0].fine_label == "total_message_length"
    
    def test_constant_field_with_both_relations(self):
        """常量字段：即使有多个长度关系也不输出"""
        config = Config(
            min_samples=8,
            length_support=0.90
        )
        detector = LengthDetector(config)
        
        # 创建画像：常量字段，同时有 message_length 和 remaining_bytes 相关性
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=2,
            dominant_value_ratio=1.0,
            numeric_be_message_length_exact_support=0.95,
            numeric_be_remaining_bytes_exact_support=0.93
        )
        
        evidences = detector.detect(profile)
        
        # 常量字段不输出任何长度证据
        assert len(evidences) == 0


class TestLengthDetectorWidth:
    """测试 LengthDetector 宽度限制"""
    
    def test_variable_width_field_excluded(self):
        """变宽字段：不输出长度证据"""
        config = Config(
            min_samples=8,
            length_support=0.90
        )
        detector = LengthDetector(config)
        
        # 创建画像：变宽字段（fixed_width = False）
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=False,
            width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            numeric_be_message_length_exact_support=0.95,
            numeric_be_remaining_bytes_exact_support=None
        )
        
        evidences = detector.detect(profile)
        
        # 变宽字段不输出长度证据
        assert len(evidences) == 0
    
    def test_width_gt_4_excluded(self):
        """宽度 > 4 的字段：不输出长度证据"""
        config = Config(
            min_samples=8,
            length_support=0.90
        )
        detector = LengthDetector(config)
        
        # 创建画像：宽度 = 5
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=5,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            numeric_be_message_length_exact_support=0.95,
            numeric_be_remaining_bytes_exact_support=None
        )
        
        evidences = detector.detect(profile)
        
        # 宽度 > 4 的字段不输出长度证据
        assert len(evidences) == 0
    
    def test_width_4_included(self):
        """宽度 = 4 的字段：输出长度证据"""
        config = Config(
            min_samples=8,
            length_support=0.90
        )
        detector = LengthDetector(config)
        
        # 创建画像：宽度 = 4
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            numeric_be_message_length_exact_support=0.95,
            numeric_be_remaining_bytes_exact_support=None
        )
        
        evidences = detector.detect(profile)
        
        # 宽度 = 4 的字段输出长度证据
        assert len(evidences) == 1
        assert evidences[0].fine_label == "total_message_length"
    
    def test_width_1_included(self):
        """宽度 = 1 的字段：输出长度证据"""
        config = Config(
            min_samples=8,
            length_support=0.90
        )
        detector = LengthDetector(config)
        
        # 创建画像：宽度 = 1
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=1,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            numeric_be_message_length_exact_support=0.95,
            numeric_be_remaining_bytes_exact_support=None
        )
        
        evidences = detector.detect(profile)
        
        # 宽度 = 1 的字段输出长度证据
        assert len(evidences) == 1
        assert evidences[0].fine_label == "total_message_length"
    
    def test_variable_width_and_width_gt_4(self):
        """变宽且宽度 > 4：不崩溃"""
        config = Config(
            min_samples=8,
            length_support=0.90
        )
        detector = LengthDetector(config)
        
        # 创建画像：变宽且宽度 > 4
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=False,
            width_mode=8,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            numeric_be_message_length_exact_support=0.95,
            numeric_be_remaining_bytes_exact_support=None
        )
        
        evidences = detector.detect(profile)
        
        # 不崩溃，返回空列表
        assert len(evidences) == 0


class TestLengthDetectorSupportBoundary:
    """测试 LengthDetector 支持率边界"""
    
    def test_support_below_threshold(self):
        """支持率 0.89（低于阈值 0.90）：不输出证据"""
        config = Config(
            min_samples=8,
            length_support=0.90
        )
        detector = LengthDetector(config)
        
        # 创建画像：支持率 0.89
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            numeric_be_message_length_exact_support=0.89,
            numeric_be_remaining_bytes_exact_support=None
        )
        
        evidences = detector.detect(profile)
        
        # 支持率低于阈值，不输出证据
        assert len(evidences) == 0
    
    def test_support_at_threshold(self):
        """支持率 0.90（等于阈值 0.90）：输出证据"""
        config = Config(
            min_samples=8,
            length_support=0.90
        )
        detector = LengthDetector(config)
        
        # 创建画像：支持率 0.90
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            numeric_be_message_length_exact_support=0.90,
            numeric_be_remaining_bytes_exact_support=None
        )
        
        evidences = detector.detect(profile)
        
        # 支持率等于阈值，输出证据
        assert len(evidences) == 1
        assert evidences[0].score == 0.90
    
    def test_support_above_threshold(self):
        """支持率 0.91（高于阈值 0.90）：输出证据"""
        config = Config(
            min_samples=8,
            length_support=0.90
        )
        detector = LengthDetector(config)
        
        # 创建画像：支持率 0.91
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            numeric_be_message_length_exact_support=0.91,
            numeric_be_remaining_bytes_exact_support=None
        )
        
        evidences = detector.detect(profile)
        
        # 支持率高于阈值，输出证据
        assert len(evidences) == 1
        assert evidences[0].score == 0.91
    
    def test_support_boundary_remaining_bytes(self):
        """remaining_bytes 支持率边界"""
        config = Config(
            min_samples=8,
            length_support=0.90
        )
        detector = LengthDetector(config)
        
        # 创建画像：remaining_bytes 支持率 0.89
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            numeric_be_message_length_exact_support=None,
            numeric_be_remaining_bytes_exact_support=0.89
        )
        
        evidences = detector.detect(profile)
        
        # 支持率低于阈值，不输出证据
        assert len(evidences) == 0
    
    def test_support_boundary_both_relations(self):
        """两种关系的支持率边界"""
        config = Config(
            min_samples=8,
            length_support=0.90
        )
        detector = LengthDetector(config)
        
        # 创建画像：message_length 0.91，remaining_bytes 0.89
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            numeric_be_message_length_exact_support=0.91,
            numeric_be_remaining_bytes_exact_support=0.89
        )
        
        evidences = detector.detect(profile)
        
        # 只有 message_length 满足阈值
        assert len(evidences) == 1
        assert evidences[0].fine_label == "total_message_length"
    
    def test_support_boundary_custom_threshold(self):
        """自定义阈值边界"""
        config = Config(
            min_samples=8,
            length_support=0.85
        )
        detector = LengthDetector(config)
        
        # 创建画像：支持率 0.85
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            numeric_be_message_length_exact_support=0.85,
            numeric_be_remaining_bytes_exact_support=None
        )
        
        evidences = detector.detect(profile)
        
        # 支持率等于自定义阈值，输出证据
        assert len(evidences) == 1
        assert evidences[0].score == 0.85


class TestLengthDetectorDetailsStandardized:
    """测试 LengthDetector details 字段标准化"""
    
    def test_details_fields_complete(self):
        """details 字段齐全：relation/endian/support_ratio/offset"""
        config = Config(
            min_samples=8,
            length_support=0.90
        )
        detector = LengthDetector(config)
        
        # 创建画像
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            numeric_be_message_length_exact_support=0.95,
            numeric_be_remaining_bytes_exact_support=None
        )
        
        evidences = detector.detect(profile)
        
        assert len(evidences) == 1
        evidence = evidences[0]
        
        # 检查 details 字段齐全
        assert "relation" in evidence.details
        assert "endian" in evidence.details
        assert "support_ratio" in evidence.details
        assert "offset" in evidence.details
        
        # 检查字段值
        assert evidence.details["relation"] == "total"
        assert evidence.details["endian"] == "be"
        assert evidence.details["support_ratio"] == 0.95
        assert evidence.details["offset"] == 0
    
    def test_details_json_serializable(self):
        """details 字段可 JSON 化"""
        import json
        
        config = Config(
            min_samples=8,
            length_support=0.90
        )
        detector = LengthDetector(config)
        
        # 创建画像
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            numeric_be_message_length_exact_support=0.95,
            numeric_be_remaining_bytes_exact_support=None
        )
        
        evidences = detector.detect(profile)
        
        assert len(evidences) == 1
        evidence = evidences[0]
        
        # 尝试 JSON 序列化
        details_json = json.dumps(evidence.details)
        
        # 尝试 JSON 反序列化
        details_parsed = json.loads(details_json)
        
        # 验证字段
        assert details_parsed["relation"] == "total"
        assert details_parsed["endian"] == "be"
        assert details_parsed["support_ratio"] == 0.95
        assert details_parsed["offset"] == 0
    
    def test_details_remaining_bytes(self):
        """remaining_bytes 的 details 字段"""
        config = Config(
            min_samples=8,
            length_support=0.90
        )
        detector = LengthDetector(config)
        
        # 创建画像
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            numeric_be_message_length_exact_support=None,
            numeric_be_remaining_bytes_exact_support=0.92
        )
        
        evidences = detector.detect(profile)
        
        assert len(evidences) == 1
        evidence = evidences[0]
        
        # 检查 details 字段
        assert evidence.details["relation"] == "remaining"
        assert evidence.details["endian"] == "be"
        assert evidence.details["support_ratio"] == 0.92
        assert evidence.details["offset"] == 0
    
    def test_details_le_endian(self):
        """LE endian 的 details 字段"""
        config = Config(
            min_samples=8,
            length_support=0.90
        )
        detector = LengthDetector(config)
        
        # 创建画像
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            numeric_be_message_length_exact_support=0.50,
            numeric_le_message_length_exact_support=0.95
        )
        
        evidences = detector.detect(profile)
        
        assert len(evidences) == 1
        evidence = evidences[0]
        
        # 检查 details 字段
        assert evidence.details["relation"] == "total"
        assert evidence.details["endian"] == "le"
        assert evidence.details["support_ratio"] == 0.95
        assert evidence.details["offset"] == 0
    
    def test_details_both_relations(self):
        """两种关系的 details 字段"""
        config = Config(
            min_samples=8,
            length_support=0.90
        )
        detector = LengthDetector(config)
        
        # 创建画像
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            numeric_be_message_length_exact_support=0.95,
            numeric_be_remaining_bytes_exact_support=0.93
        )
        
        evidences = detector.detect(profile)
        
        assert len(evidences) == 2
        
        # 检查第一个证据（支持率更高）
        assert evidences[0].details["relation"] == "total"
        assert evidences[0].details["support_ratio"] == 0.95
        assert evidences[0].details["offset"] == 0
        
        # 检查第二个证据
        assert evidences[1].details["relation"] == "remaining"
        assert evidences[1].details["support_ratio"] == 0.93
        assert evidences[1].details["offset"] == 0


class TestLengthDetectorR276:
    """R276: HIGH-7 重写后的 LengthDetector 专项测试

    教程 8.1：correlation=1.0 不代表 value==length。
    教程 8.4：distinct_value_count >= 2 才可能是长度字段。
    验收：total/remaining/offset 候选，reason_code 与真实算法一致。
    """

    def _make_config(self):
        return Config(min_samples=8, length_support=0.90)

    def test_offset_message_length_candidate(self):
        """offset 候选：exact_support 未达阈值但 offset_support 达阈值（offset!=0）"""
        config = self._make_config()
        detector = LengthDetector(config)
        profile = FieldProfile(
            layout_id="L1", direction="up", field_index=0,
            sample_count=100, fixed_width=True, width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            # exact 低于阈值 0.90
            numeric_be_message_length_exact_support=0.50,
            numeric_be_remaining_bytes_exact_support=None,
            # offset 达阈值且 offset!=0
            numeric_be_message_length_offset_support=0.93,
            numeric_be_message_length_offset=4,
        )
        evidences = detector.detect(profile)
        assert len(evidences) == 1
        ev = evidences[0]
        assert ev.fine_label == "total_message_length"
        assert ev.score == 0.93
        assert ev.reason_code == "value_equals_message_length_plus_offset"
        assert ev.details["offset"] == 4
        assert ev.details["endian"] == "be"
        assert ev.details["relation"] == "total"

    def test_offset_remaining_bytes_candidate(self):
        """offset 候选（remaining_bytes）：exact 未达阈值但 offset 达阈值"""
        config = self._make_config()
        detector = LengthDetector(config)
        profile = FieldProfile(
            layout_id="L1", direction="up", field_index=0,
            sample_count=100, fixed_width=True, width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            numeric_be_remaining_bytes_exact_support=0.40,
            numeric_be_message_length_exact_support=None,
            numeric_be_remaining_bytes_offset_support=0.92,
            numeric_be_remaining_bytes_offset=8,
        )
        evidences = detector.detect(profile)
        assert len(evidences) == 1
        ev = evidences[0]
        assert ev.fine_label == "remaining_bytes"
        assert ev.score == 0.92
        assert ev.reason_code == "value_equals_remaining_bytes_plus_offset"
        assert ev.details["offset"] == 8
        assert ev.details["endian"] == "be"
        assert ev.details["relation"] == "remaining"

    def test_distinct_below_two_excluded_be(self):
        """BE distinct_value_count < 2 时 BE 候选被排除（教程 8.4）"""
        config = self._make_config()
        detector = LengthDetector(config)
        profile = FieldProfile(
            layout_id="L1", direction="up", field_index=0,
            sample_count=100, fixed_width=True, width_mode=2,
            dominant_value_ratio=0.5,
            # BE distinct = 1（伪证据），LE distinct = 10
            numeric_be_distinct_value_count=1,
            numeric_le_distinct_value_count=10,
            # BE 看起来"命中"，但 distinct=1 表明是常量巧合
            numeric_be_message_length_exact_support=1.0,
            numeric_be_remaining_bytes_exact_support=None,
            # LE 真实命中
            numeric_le_message_length_exact_support=0.95,
            numeric_le_remaining_bytes_exact_support=None,
        )
        evidences = detector.detect(profile)
        # BE 被排除，只有 LE 命中
        assert len(evidences) == 1
        assert evidences[0].details["endian"] == "le"
        assert evidences[0].score == 0.95

    def test_distinct_below_two_excluded_le(self):
        """LE distinct_value_count < 2 时 LE 候选被排除"""
        config = self._make_config()
        detector = LengthDetector(config)
        profile = FieldProfile(
            layout_id="L1", direction="up", field_index=0,
            sample_count=100, fixed_width=True, width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=1,
            numeric_be_message_length_exact_support=0.94,
            numeric_le_message_length_exact_support=1.0,
        )
        evidences = detector.detect(profile)
        assert len(evidences) == 1
        assert evidences[0].details["endian"] == "be"

    def test_distinct_zero_excluded_both(self):
        """distinct_value_count = 0（None）时两端都被排除"""
        config = self._make_config()
        detector = LengthDetector(config)
        profile = FieldProfile(
            layout_id="L1", direction="up", field_index=0,
            sample_count=100, fixed_width=True, width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=0,
            numeric_le_distinct_value_count=0,
            numeric_be_message_length_exact_support=1.0,
            numeric_le_message_length_exact_support=1.0,
        )
        evidences = detector.detect(profile)
        assert len(evidences) == 0

    def test_distinct_two_minimum_legal(self):
        """distinct_value_count = 2 是长度字段的最小合法值（教程 8.4）"""
        config = self._make_config()
        detector = LengthDetector(config)
        profile = FieldProfile(
            layout_id="L1", direction="up", field_index=0,
            sample_count=100, fixed_width=True, width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=2,
            numeric_le_distinct_value_count=2,
            numeric_be_message_length_exact_support=0.95,
        )
        evidences = detector.detect(profile)
        assert len(evidences) == 1
        assert evidences[0].details["endian"] == "be"
        assert evidences[0].score == 0.95

    def test_reason_code_exact_message_length(self):
        """reason_code: exact 模式 message_length"""
        config = self._make_config()
        detector = LengthDetector(config)
        profile = FieldProfile(
            layout_id="L1", direction="up", field_index=0,
            sample_count=100, fixed_width=True, width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            numeric_be_message_length_exact_support=0.95,
        )
        evidences = detector.detect(profile)
        assert len(evidences) == 1
        assert evidences[0].reason_code == "value_equals_message_length"
        assert evidences[0].details["offset"] == 0

    def test_reason_code_offset_message_length(self):
        """reason_code: offset 模式 message_length"""
        config = self._make_config()
        detector = LengthDetector(config)
        profile = FieldProfile(
            layout_id="L1", direction="up", field_index=0,
            sample_count=100, fixed_width=True, width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            numeric_be_message_length_exact_support=0.50,
            numeric_be_message_length_offset_support=0.93,
            numeric_be_message_length_offset=4,
        )
        evidences = detector.detect(profile)
        assert len(evidences) == 1
        assert evidences[0].reason_code == "value_equals_message_length_plus_offset"
        assert evidences[0].details["offset"] == 4

    def test_reason_code_exact_remaining_bytes(self):
        """reason_code: exact 模式 remaining_bytes"""
        config = self._make_config()
        detector = LengthDetector(config)
        profile = FieldProfile(
            layout_id="L1", direction="up", field_index=0,
            sample_count=100, fixed_width=True, width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            numeric_be_remaining_bytes_exact_support=0.92,
        )
        evidences = detector.detect(profile)
        assert len(evidences) == 1
        assert evidences[0].reason_code == "value_equals_remaining_bytes"
        assert evidences[0].details["offset"] == 0

    def test_reason_code_offset_remaining_bytes(self):
        """reason_code: offset 模式 remaining_bytes"""
        config = self._make_config()
        detector = LengthDetector(config)
        profile = FieldProfile(
            layout_id="L1", direction="up", field_index=0,
            sample_count=100, fixed_width=True, width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            numeric_be_remaining_bytes_exact_support=0.40,
            numeric_be_remaining_bytes_offset_support=0.91,
            numeric_be_remaining_bytes_offset=8,
        )
        evidences = detector.detect(profile)
        assert len(evidences) == 1
        assert evidences[0].reason_code == "value_equals_remaining_bytes_plus_offset"
        assert evidences[0].details["offset"] == 8

    def test_exact_preferred_over_offset(self):
        """exact 与 offset 都达阈值时，只输出 exact（避免重复）"""
        config = self._make_config()
        detector = LengthDetector(config)
        profile = FieldProfile(
            layout_id="L1", direction="up", field_index=0,
            sample_count=100, fixed_width=True, width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            # exact 与 offset 都达阈值，但优先 exact
            numeric_be_message_length_exact_support=0.95,
            numeric_be_message_length_offset_support=0.93,
            numeric_be_message_length_offset=4,
        )
        evidences = detector.detect(profile)
        # 只输出一个候选（exact 优先），不重复
        assert len(evidences) == 1
        assert evidences[0].reason_code == "value_equals_message_length"
        assert evidences[0].score == 0.95
        assert evidences[0].details["offset"] == 0

    def test_offset_zero_not_used_as_offset_mode(self):
        """offset==0 时不会作为 offset 模式输出（避免与 exact 重复）"""
        config = self._make_config()
        detector = LengthDetector(config)
        profile = FieldProfile(
            layout_id="L1", direction="up", field_index=0,
            sample_count=100, fixed_width=True, width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            # exact 未达阈值，offset_support 达阈值但 offset==0（不应作为 offset 候选）
            numeric_be_message_length_exact_support=0.50,
            numeric_be_message_length_offset_support=0.95,
            numeric_be_message_length_offset=0,
        )
        evidences = detector.detect(profile)
        # offset==0 不应被作为 offset 模式输出
        assert len(evidences) == 0

    def test_offset_below_threshold_excluded(self):
        """offset_support 低于阈值时被排除"""
        config = self._make_config()
        detector = LengthDetector(config)
        profile = FieldProfile(
            layout_id="L1", direction="up", field_index=0,
            sample_count=100, fixed_width=True, width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            # exact 与 offset 都未达阈值
            numeric_be_message_length_exact_support=0.50,
            numeric_be_message_length_offset_support=0.60,
            numeric_be_message_length_offset=4,
        )
        evidences = detector.detect(profile)
        assert len(evidences) == 0

    def test_be_and_le_offset_both_above_threshold(self):
        """BE 和 LE 的 offset 候选都达阈值时，按支持率排序"""
        config = self._make_config()
        detector = LengthDetector(config)
        profile = FieldProfile(
            layout_id="L1", direction="up", field_index=0,
            sample_count=100, fixed_width=True, width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            numeric_be_message_length_exact_support=0.40,
            numeric_le_message_length_exact_support=0.40,
            numeric_be_message_length_offset_support=0.92,
            numeric_be_message_length_offset=4,
            numeric_le_message_length_offset_support=0.95,
            numeric_le_message_length_offset=4,
        )
        evidences = detector.detect(profile)
        # BE 和 LE 都命中 offset 候选，LE 支持率更高排前面
        assert len(evidences) == 2
        assert evidences[0].details["endian"] == "le"
        assert evidences[0].score == 0.95
        assert evidences[1].details["endian"] == "be"
        assert evidences[1].score == 0.92
        # 都是 offset 模式
        for ev in evidences:
            assert ev.reason_code == "value_equals_message_length_plus_offset"
            assert ev.details["offset"] == 4


class TestLengthDetectorR277:
    """R277：HIGH-7 长度负例——"高相关但非等式"

    教程 8.1：correlation=1.0 不代表 value==length（高相关 ≠ 长度字段）。
    验收：correlation 完美但 exact_support/offset_support 不达阈值时，
    LengthDetector 必须不输出 length 证据。
    R268 已在 profile 层面验证反例（correlation=1 + exact_support=0），
    R277 在 detector.detect() 层面验证 LengthDetector 行为正确。
    """

    def _make_config(self):
        return Config(min_samples=8, length_support=0.90)

    def test_correlation_one_but_exact_support_zero(self):
        """correlation=1.0 但 exact_support=0.0：不输出 length 证据

        教程 8.1 反例：value=[1,2,3,4], length=[100,200,300,400]
        correlation 完美正相关但 value != length（exact_support=0）。
        """
        config = self._make_config()
        detector = LengthDetector(config)
        profile = FieldProfile(
            layout_id="trap_layout", direction="up", field_index=0,
            sample_count=100, fixed_width=True, width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=4,
            numeric_le_distinct_value_count=4,
            # correlation=1.0（完美正相关）
            numeric_be_message_length_correlation=1.0,
            numeric_be_remaining_bytes_correlation=1.0,
            # 但 exact_support=0.0（没有任何 value == message_length）
            numeric_be_message_length_exact_support=0.0,
            numeric_be_remaining_bytes_exact_support=0.0,
        )
        evidences = detector.detect(profile)
        # 关键：correlation=1.0 但 exact_support=0.0，不得命中 length
        assert len(evidences) == 0

    def test_correlation_one_but_exact_support_none(self):
        """correlation=1.0 但 exact_support=None：不输出 length 证据

        exact_support 缺失（None）表明没有任何等式命中，
        即使 correlation 完美也不得判定为 length。
        """
        config = self._make_config()
        detector = LengthDetector(config)
        profile = FieldProfile(
            layout_id="trap_layout", direction="up", field_index=0,
            sample_count=100, fixed_width=True, width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            numeric_be_message_length_correlation=1.0,
            numeric_be_remaining_bytes_correlation=1.0,
            # exact_support 全部 None
            numeric_be_message_length_exact_support=None,
            numeric_be_remaining_bytes_exact_support=None,
        )
        evidences = detector.detect(profile)
        assert len(evidences) == 0

    def test_correlation_one_but_offset_support_below_threshold(self):
        """correlation=1.0 但 offset_support 未达阈值：不输出 length 证据

        即使存在 offset 关系（offset!=0），offset_support 低于阈值也不得命中。
        """
        config = self._make_config()
        detector = LengthDetector(config)
        profile = FieldProfile(
            layout_id="trap_layout", direction="up", field_index=0,
            sample_count=100, fixed_width=True, width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=4,
            numeric_le_distinct_value_count=4,
            numeric_be_message_length_correlation=1.0,
            # exact_support=0.0（不命中 exact）
            numeric_be_message_length_exact_support=0.0,
            # offset_support=0.5（最常见 offset 占比，低于阈值 0.90）
            numeric_be_message_length_offset_support=0.5,
            numeric_be_message_length_offset=99,
        )
        evidences = detector.detect(profile)
        assert len(evidences) == 0

    def test_correlation_one_but_offset_zero(self):
        """correlation=1.0 但 offset==0 且 exact_support=0：不输出 length 证据

        offset==0 时不会作为 offset 模式输出（避免与 exact 重复），
        exact_support=0 时也不命中 exact，故 LengthDetector 不得输出 length 证据。
        """
        config = self._make_config()
        detector = LengthDetector(config)
        profile = FieldProfile(
            layout_id="trap_layout", direction="up", field_index=0,
            sample_count=100, fixed_width=True, width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=4,
            numeric_le_distinct_value_count=4,
            numeric_be_message_length_correlation=1.0,
            numeric_be_message_length_exact_support=0.0,
            # offset_support 看起来"高"但 offset==0，不应作为 offset 候选
            numeric_be_message_length_offset_support=0.95,
            numeric_be_message_length_offset=0,
        )
        evidences = detector.detect(profile)
        assert len(evidences) == 0

    def test_correlation_one_both_endians_no_match(self):
        """correlation=1.0 BE 和 LE 都未命中：两端都不输出 length 证据"""
        config = self._make_config()
        detector = LengthDetector(config)
        profile = FieldProfile(
            layout_id="trap_layout", direction="up", field_index=0,
            sample_count=100, fixed_width=True, width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=4,
            numeric_le_distinct_value_count=4,
            # BE 和 LE 的 correlation 都完美
            numeric_be_message_length_correlation=1.0,
            numeric_le_message_length_correlation=1.0,
            # 但 BE 和 LE 的 exact_support 都为 0
            numeric_be_message_length_exact_support=0.0,
            numeric_le_message_length_exact_support=0.0,
        )
        evidences = detector.detect(profile)
        assert len(evidences) == 0

    def test_correlation_one_with_low_distinct_still_excluded(self):
        """correlation=1.0 但 distinct_value_count<2：不输出 length 证据

        即使 correlation 完美且 exact_support 巧合为 1.0，
        distinct_value_count=1 表明是常量伪证据（教程 8.4）。
        """
        config = self._make_config()
        detector = LengthDetector(config)
        profile = FieldProfile(
            layout_id="trap_layout", direction="up", field_index=0,
            sample_count=100, fixed_width=True, width_mode=2,
            dominant_value_ratio=0.5,
            # BE distinct=1（常量伪证据），LE distinct=1
            numeric_be_distinct_value_count=1,
            numeric_le_distinct_value_count=1,
            numeric_be_message_length_correlation=1.0,
            # 巧合命中 exact_support=1.0（但 distinct=1 是伪证据）
            numeric_be_message_length_exact_support=1.0,
        )
        evidences = detector.detect(profile)
        # distinct<2 时即使 correlation=1 + exact_support=1 也不得命中
        assert len(evidences) == 0

    def test_low_correlation_but_high_exact_support_still_matches(self):
        """对照：correlation 低但 exact_support 高时仍命中 length

        教程 8.1 反向验证：correlation 不是判定依据，
        即使 correlation=0 但 exact_support=1.0 仍应输出 length 证据。
        """
        config = self._make_config()
        detector = LengthDetector(config)
        profile = FieldProfile(
            layout_id="inverse_layout", direction="up", field_index=0,
            sample_count=100, fixed_width=True, width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            # correlation 低（但 length 判定不依赖它）
            numeric_be_message_length_correlation=0.0,
            # exact_support 高 → 命中 length
            numeric_be_message_length_exact_support=0.95,
        )
        evidences = detector.detect(profile)
        assert len(evidences) == 1
        assert evidences[0].reason_code == "value_equals_message_length"
        assert evidences[0].score == 0.95

    def test_no_correlation_field_set_but_exact_support_high(self):
        """correlation 字段完全未设置（None）但 exact_support 高时仍命中 length

        进一步证明 LengthDetector 不依赖 correlation 字段。
        """
        config = self._make_config()
        detector = LengthDetector(config)
        profile = FieldProfile(
            layout_id="no_corr_layout", direction="up", field_index=0,
            sample_count=100, fixed_width=True, width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            # correlation 字段全部 None（默认值）
            # 只设置 exact_support
            numeric_be_message_length_exact_support=0.95,
        )
        evidences = detector.detect(profile)
        assert len(evidences) == 1
        assert evidences[0].reason_code == "value_equals_message_length"
        assert evidences[0].score == 0.95


class TestLengthDetectorR278:
    """R278：HIGH-7 三类长度负例——常量、单值、变宽字段

    教程 8.4：LengthDetector 前置条件——distinct_value_count >= 2、支持率达阈值。
    验收：三类负例 | 不得产生 hard length。
    三类负例：
    1. 常量字段（dominant_value_ratio >= 0.98）
    2. 单值字段（distinct_value_count < 2）
    3. 变宽字段（fixed_width = False）
    """

    def _make_config(self):
        return Config(min_samples=8, length_support=0.90)

    # ===== 1. 常量字段负例 =====

    def test_constant_field_with_high_exact_support_excluded(self):
        """常量字段（dominant_value_ratio=1.0）即使 exact_support 高也不输出"""
        config = self._make_config()
        detector = LengthDetector(config)
        profile = FieldProfile(
            layout_id="const_layout", direction="up", field_index=0,
            sample_count=100, fixed_width=True, width_mode=2,
            dominant_value_ratio=1.0,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            numeric_be_message_length_exact_support=0.95,
        )
        evidences = detector.detect(profile)
        assert len(evidences) == 0

    def test_constant_field_with_high_offset_support_excluded(self):
        """常量字段即使 offset_support 高也不输出"""
        config = self._make_config()
        detector = LengthDetector(config)
        profile = FieldProfile(
            layout_id="const_layout", direction="up", field_index=0,
            sample_count=100, fixed_width=True, width_mode=2,
            dominant_value_ratio=1.0,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            numeric_be_message_length_exact_support=0.50,
            numeric_be_message_length_offset_support=0.95,
            numeric_be_message_length_offset=4,
        )
        evidences = detector.detect(profile)
        assert len(evidences) == 0

    def test_near_constant_field_with_high_exact_support_excluded(self):
        """接近常量字段（dominant_value_ratio=0.99）即使 exact_support 高也不输出"""
        config = self._make_config()
        detector = LengthDetector(config)
        profile = FieldProfile(
            layout_id="near_const_layout", direction="up", field_index=0,
            sample_count=100, fixed_width=True, width_mode=2,
            dominant_value_ratio=0.99,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            numeric_be_message_length_exact_support=0.95,
        )
        evidences = detector.detect(profile)
        assert len(evidences) == 0

    def test_constant_field_boundary_0_98_excluded(self):
        """常量字段边界（dominant_value_ratio=0.98）即使 exact_support 高也不输出"""
        config = self._make_config()
        detector = LengthDetector(config)
        profile = FieldProfile(
            layout_id="boundary_layout", direction="up", field_index=0,
            sample_count=100, fixed_width=True, width_mode=2,
            dominant_value_ratio=0.98,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            numeric_be_message_length_exact_support=0.95,
        )
        evidences = detector.detect(profile)
        assert len(evidences) == 0

    def test_constant_field_both_relations_excluded(self):
        """常量字段即使 message_length 和 remaining_bytes 都高也不输出"""
        config = self._make_config()
        detector = LengthDetector(config)
        profile = FieldProfile(
            layout_id="const_both_layout", direction="up", field_index=0,
            sample_count=100, fixed_width=True, width_mode=2,
            dominant_value_ratio=1.0,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            numeric_be_message_length_exact_support=0.95,
            numeric_be_remaining_bytes_exact_support=0.93,
        )
        evidences = detector.detect(profile)
        assert len(evidences) == 0

    # ===== 2. 单值字段负例（distinct_value_count < 2）=====

    def test_single_value_field_excluded_be(self):
        """单值字段（BE distinct=1）即使 exact_support 高也不输出 BE 候选"""
        config = self._make_config()
        detector = LengthDetector(config)
        profile = FieldProfile(
            layout_id="single_layout", direction="up", field_index=0,
            sample_count=100, fixed_width=True, width_mode=2,
            dominant_value_ratio=0.5,
            # BE distinct=1（单值伪证据），LE distinct=10
            numeric_be_distinct_value_count=1,
            numeric_le_distinct_value_count=10,
            # BE 巧合命中 exact_support=1.0，但 distinct=1 是伪证据
            numeric_be_message_length_exact_support=1.0,
            # LE 真实命中
            numeric_le_message_length_exact_support=0.95,
        )
        evidences = detector.detect(profile)
        # 只有 LE 命中
        assert len(evidences) == 1
        assert evidences[0].details["endian"] == "le"
        assert evidences[0].score == 0.95

    def test_single_value_field_excluded_le(self):
        """单值字段（LE distinct=1）即使 exact_support 高也不输出 LE 候选"""
        config = self._make_config()
        detector = LengthDetector(config)
        profile = FieldProfile(
            layout_id="single_layout", direction="up", field_index=0,
            sample_count=100, fixed_width=True, width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=1,
            numeric_be_message_length_exact_support=0.94,
            numeric_le_message_length_exact_support=1.0,
        )
        evidences = detector.detect(profile)
        assert len(evidences) == 1
        assert evidences[0].details["endian"] == "be"

    def test_single_value_field_both_endians_excluded(self):
        """单值字段（BE 和 LE 都 distinct=1）即使 exact_support 高也不输出"""
        config = self._make_config()
        detector = LengthDetector(config)
        profile = FieldProfile(
            layout_id="single_both_layout", direction="up", field_index=0,
            sample_count=100, fixed_width=True, width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=1,
            numeric_le_distinct_value_count=1,
            # 两端都"完美"命中但都是单值伪证据
            numeric_be_message_length_exact_support=1.0,
            numeric_le_message_length_exact_support=1.0,
        )
        evidences = detector.detect(profile)
        assert len(evidences) == 0

    def test_single_value_field_offset_excluded(self):
        """单值字段即使 offset_support 高也不输出"""
        config = self._make_config()
        detector = LengthDetector(config)
        profile = FieldProfile(
            layout_id="single_offset_layout", direction="up", field_index=0,
            sample_count=100, fixed_width=True, width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=1,
            numeric_le_distinct_value_count=1,
            numeric_be_message_length_exact_support=0.50,
            numeric_be_message_length_offset_support=0.95,
            numeric_be_message_length_offset=4,
        )
        evidences = detector.detect(profile)
        assert len(evidences) == 0

    def test_zero_distinct_excluded(self):
        """distinct_value_count=0（无值可去重）时不得输出"""
        config = self._make_config()
        detector = LengthDetector(config)
        profile = FieldProfile(
            layout_id="zero_distinct_layout", direction="up", field_index=0,
            sample_count=100, fixed_width=True, width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=0,
            numeric_le_distinct_value_count=0,
            numeric_be_message_length_exact_support=1.0,
            numeric_le_message_length_exact_support=1.0,
        )
        evidences = detector.detect(profile)
        assert len(evidences) == 0

    def test_none_distinct_excluded(self):
        """distinct_value_count=None（默认值，未计算）时不得输出"""
        config = self._make_config()
        detector = LengthDetector(config)
        profile = FieldProfile(
            layout_id="none_distinct_layout", direction="up", field_index=0,
            sample_count=100, fixed_width=True, width_mode=2,
            dominant_value_ratio=0.5,
            # distinct_value_count 未设置（默认 None）
            numeric_be_message_length_exact_support=0.95,
        )
        evidences = detector.detect(profile)
        assert len(evidences) == 0

    # ===== 3. 变宽字段负例 =====

    def test_variable_width_with_high_exact_support_excluded(self):
        """变宽字段（fixed_width=False）即使 exact_support 高也不输出"""
        config = self._make_config()
        detector = LengthDetector(config)
        profile = FieldProfile(
            layout_id="var_width_layout", direction="up", field_index=0,
            sample_count=100, fixed_width=False, width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            numeric_be_message_length_exact_support=0.95,
        )
        evidences = detector.detect(profile)
        assert len(evidences) == 0

    def test_variable_width_with_high_offset_support_excluded(self):
        """变宽字段即使 offset_support 高也不输出"""
        config = self._make_config()
        detector = LengthDetector(config)
        profile = FieldProfile(
            layout_id="var_width_offset_layout", direction="up", field_index=0,
            sample_count=100, fixed_width=False, width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            numeric_be_message_length_exact_support=0.50,
            numeric_be_message_length_offset_support=0.95,
            numeric_be_message_length_offset=4,
        )
        evidences = detector.detect(profile)
        assert len(evidences) == 0

    def test_variable_width_both_relations_excluded(self):
        """变宽字段即使 message_length 和 remaining_bytes 都高也不输出"""
        config = self._make_config()
        detector = LengthDetector(config)
        profile = FieldProfile(
            layout_id="var_width_both_layout", direction="up", field_index=0,
            sample_count=100, fixed_width=False, width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            numeric_be_message_length_exact_support=0.95,
            numeric_be_remaining_bytes_exact_support=0.93,
        )
        evidences = detector.detect(profile)
        assert len(evidences) == 0

    def test_variable_width_with_high_width_mode_excluded(self):
        """变宽字段 + width_mode > 4 也不输出（双重排除）"""
        config = self._make_config()
        detector = LengthDetector(config)
        profile = FieldProfile(
            layout_id="var_width_high_layout", direction="up", field_index=0,
            sample_count=100, fixed_width=False, width_mode=8,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            numeric_be_message_length_exact_support=0.95,
        )
        evidences = detector.detect(profile)
        assert len(evidences) == 0

    def test_fixed_width_with_high_width_mode_excluded(self):
        """定宽字段但 width_mode > 4 也不输出"""
        config = self._make_config()
        detector = LengthDetector(config)
        profile = FieldProfile(
            layout_id="high_width_layout", direction="up", field_index=0,
            sample_count=100, fixed_width=True, width_mode=8,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            numeric_be_message_length_exact_support=0.95,
        )
        evidences = detector.detect(profile)
        assert len(evidences) == 0


class TestLengthDetectorR279:
    """R279：HIGH-7 单字节和 BE/LE 同值的端序折叠

    教程 8.4 / 04 任务表 R279：
    "处理单字节和 BE/LE 同值的端序折叠 | length.py; test_length_detector.py | 1 字节 fixture | 不生成重复冲突候选"

    单字节字段（width_mode == 1）BE 和 LE 解码结果完全相同，
    LengthDetector 必须只输出一个候选（BE），不得生成重复的 LE 候选。
    """

    def _make_config(self):
        return Config(min_samples=8, length_support=0.90)

    def test_single_byte_no_duplicate_le_candidate(self):
        """单字节字段（width_mode=1）：BE 和 LE 都达阈值时只输出一个候选

        单字节 BE 和 LE 解码结果完全相同，不应生成重复候选。
        """
        config = self._make_config()
        detector = LengthDetector(config)
        profile = FieldProfile(
            layout_id="single_byte_layout", direction="up", field_index=0,
            sample_count=100, fixed_width=True, width_mode=1,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            # BE 和 LE 都达阈值（单字节时 BE==LE，但设置相同值模拟）
            numeric_be_message_length_exact_support=0.95,
            numeric_le_message_length_exact_support=0.95,
        )
        evidences = detector.detect(profile)
        # 关键：单字节只输出 1 个候选，不重复
        assert len(evidences) == 1
        # 默认保留 BE 候选
        assert evidences[0].details["endian"] == "be"
        assert evidences[0].score == 0.95

    def test_single_byte_be_only_high_support(self):
        """单字节字段：只有 BE 达阈值时输出 BE 候选"""
        config = self._make_config()
        detector = LengthDetector(config)
        profile = FieldProfile(
            layout_id="single_byte_be_layout", direction="up", field_index=0,
            sample_count=100, fixed_width=True, width_mode=1,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            numeric_be_message_length_exact_support=0.95,
            numeric_le_message_length_exact_support=0.50,
        )
        evidences = detector.detect(profile)
        assert len(evidences) == 1
        assert evidences[0].details["endian"] == "be"

    def test_single_byte_le_high_but_skipped(self):
        """单字节字段：LE 支持率高但 BE 低时也不输出 LE（端序折叠）

        单字节 BE==LE，故 LE 高意味着 BE 也应高；
        但如果测试构造 BE 低 LE 高的假数据，仍只检查 BE 候选（避免重复）。
        此场景下 BE 未达阈值，LengthDetector 不输出（不重复输出 LE）。
        """
        config = self._make_config()
        detector = LengthDetector(config)
        profile = FieldProfile(
            layout_id="single_byte_le_skipped_layout", direction="up", field_index=0,
            sample_count=100, fixed_width=True, width_mode=1,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            # BE 未达阈值，LE 达阈值（人为构造的假数据）
            numeric_be_message_length_exact_support=0.50,
            numeric_le_message_length_exact_support=0.95,
        )
        evidences = detector.detect(profile)
        # 单字节跳过 LE，BE 未达阈值，故不输出
        assert len(evidences) == 0

    def test_single_byte_both_relations_no_duplicate(self):
        """单字节字段：message_length 和 remaining_bytes 都达阈值时不重复"""
        config = self._make_config()
        detector = LengthDetector(config)
        profile = FieldProfile(
            layout_id="single_byte_both_layout", direction="up", field_index=0,
            sample_count=100, fixed_width=True, width_mode=1,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            # BE 和 LE 两种关系都达阈值
            numeric_be_message_length_exact_support=0.95,
            numeric_be_remaining_bytes_exact_support=0.93,
            numeric_le_message_length_exact_support=0.95,
            numeric_le_remaining_bytes_exact_support=0.93,
        )
        evidences = detector.detect(profile)
        # 单字节只输出 BE 的两个候选（total + remaining），不重复输出 LE
        assert len(evidences) == 2
        # 都是 BE
        for ev in evidences:
            assert ev.details["endian"] == "be"

    def test_single_byte_offset_no_duplicate(self):
        """单字节字段：offset 候选也不重复输出 LE"""
        config = self._make_config()
        detector = LengthDetector(config)
        profile = FieldProfile(
            layout_id="single_byte_offset_layout", direction="up", field_index=0,
            sample_count=100, fixed_width=True, width_mode=1,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            # BE 和 LE 都通过 offset 命中
            numeric_be_message_length_exact_support=0.50,
            numeric_be_message_length_offset_support=0.93,
            numeric_be_message_length_offset=4,
            numeric_le_message_length_exact_support=0.50,
            numeric_le_message_length_offset_support=0.93,
            numeric_le_message_length_offset=4,
        )
        evidences = detector.detect(profile)
        # 单字节只输出 BE offset 候选，不重复输出 LE
        assert len(evidences) == 1
        assert evidences[0].details["endian"] == "be"
        assert evidences[0].reason_code == "value_equals_message_length_plus_offset"

    def test_multi_byte_still_checks_both_endians(self):
        """对照：多字节字段（width_mode=2）仍同时检查 BE 和 LE"""
        config = self._make_config()
        detector = LengthDetector(config)
        profile = FieldProfile(
            layout_id="multi_byte_layout", direction="up", field_index=0,
            sample_count=100, fixed_width=True, width_mode=2,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            # BE 和 LE 都达阈值
            numeric_be_message_length_exact_support=0.95,
            numeric_le_message_length_exact_support=0.93,
        )
        evidences = detector.detect(profile)
        # 多字节同时输出 BE 和 LE 两个候选
        assert len(evidences) == 2
        endians = [ev.details["endian"] for ev in evidences]
        assert "be" in endians
        assert "le" in endians

    def test_single_byte_remaining_bytes_no_duplicate(self):
        """单字节字段：remaining_bytes 候选也不重复输出 LE"""
        config = self._make_config()
        detector = LengthDetector(config)
        profile = FieldProfile(
            layout_id="single_byte_rb_layout", direction="up", field_index=0,
            sample_count=100, fixed_width=True, width_mode=1,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            numeric_be_remaining_bytes_exact_support=0.92,
            numeric_le_remaining_bytes_exact_support=0.92,
        )
        evidences = detector.detect(profile)
        # 单字节只输出 BE remaining_bytes 候选
        assert len(evidences) == 1
        assert evidences[0].details["endian"] == "be"
        assert evidences[0].fine_label == "remaining_bytes"

    def test_single_byte_below_threshold_no_output(self):
        """单字节字段：BE 未达阈值时不输出（即使 LE 达阈值也不重复输出）"""
        config = self._make_config()
        detector = LengthDetector(config)
        profile = FieldProfile(
            layout_id="single_byte_below_layout", direction="up", field_index=0,
            sample_count=100, fixed_width=True, width_mode=1,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=10,
            numeric_le_distinct_value_count=10,
            # BE 和 LE 都未达阈值
            numeric_be_message_length_exact_support=0.50,
            numeric_le_message_length_exact_support=0.50,
        )
        evidences = detector.detect(profile)
        assert len(evidences) == 0

    def test_single_byte_distinct_below_two_excluded(self):
        """单字节字段：distinct_value_count < 2 时仍被排除（教程 8.4）"""
        config = self._make_config()
        detector = LengthDetector(config)
        profile = FieldProfile(
            layout_id="single_byte_distinct_layout", direction="up", field_index=0,
            sample_count=100, fixed_width=True, width_mode=1,
            dominant_value_ratio=0.5,
            numeric_be_distinct_value_count=1,
            numeric_le_distinct_value_count=1,
            numeric_be_message_length_exact_support=1.0,
            numeric_le_message_length_exact_support=1.0,
        )
        evidences = detector.detect(profile)
        # distinct<2 排除（教程 8.4）
        assert len(evidences) == 0
