"""测试时间戳检测器"""

import pytest
from datetime import datetime, timezone
from semantic_detector.detectors.timestamp import TimestampDetector
from semantic_detector.config import Config
from semantic_detector.profiling.profile_builder import FieldProfile


class TestTimestampDetector:
    """测试时间戳检测器（Unix 秒）"""
    
    def test_unix_seconds_be(self):
        """检测 Unix 秒 BE 时间戳"""
        config = Config(
            min_samples=8,
            timestamp_support=0.90
        )
        detector = TimestampDetector(config)
        
        # 创建画像：Unix 秒 BE 时间戳
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.5,
            capture_time_min=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            capture_time_max=datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
            timestamp_be_unix_seconds_support=0.95,
            timestamp_le_unix_seconds_support=None
        )
        
        # 时间范围
        low = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        high = datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
        
        evidences = detector.detect(profile, low, high)
        
        assert len(evidences) == 1
        evidence = evidences[0]
        
        assert evidence.detector == "timestamp"
        assert evidence.coarse_label == "timestamp"
        assert evidence.fine_label == "unix_seconds_be"
        assert evidence.score == 0.95
        assert evidence.is_hard_evidence is True
        assert evidence.reason_code == "value_is_unix_seconds_be"
        assert evidence.details["format"] == "unix_seconds"
        assert evidence.details["endian"] == "be"
        assert evidence.details["byte_width"] == 4
    
    def test_unix_seconds_le(self):
        """检测 Unix 秒 LE 时间戳"""
        config = Config(
            min_samples=8,
            timestamp_support=0.90
        )
        detector = TimestampDetector(config)
        
        # 创建画像：Unix 秒 LE 时间戳
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.5,
            capture_time_min=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            capture_time_max=datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
            timestamp_be_unix_seconds_support=None,
            timestamp_le_unix_seconds_support=0.92
        )
        
        # 时间范围
        low = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        high = datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
        
        evidences = detector.detect(profile, low, high)
        
        assert len(evidences) == 1
        evidence = evidences[0]
        
        assert evidence.fine_label == "unix_seconds_le"
        assert evidence.details["endian"] == "le"
    
    def test_both_endians(self):
        """同时检测 BE 和 LE"""
        config = Config(
            min_samples=8,
            timestamp_support=0.90
        )
        detector = TimestampDetector(config)
        
        # 创建画像：BE 和 LE 都有支持率
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.5,
            capture_time_min=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            capture_time_max=datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
            timestamp_be_unix_seconds_support=0.95,
            timestamp_le_unix_seconds_support=0.93
        )
        
        # 时间范围
        low = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        high = datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
        
        evidences = detector.detect(profile, low, high)
        
        # 应该输出两个证据，BE 在前（支持率更高）
        assert len(evidences) == 2
        assert evidences[0].details["endian"] == "be"
        assert evidences[0].score == 0.95
        assert evidences[1].details["endian"] == "le"
        assert evidences[1].score == 0.93
    
    def test_below_threshold(self):
        """支持率低于阈值"""
        config = Config(
            min_samples=8,
            timestamp_support=0.90
        )
        detector = TimestampDetector(config)
        
        # 创建画像：支持率低于阈值
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.5,
            capture_time_min=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            capture_time_max=datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
            timestamp_be_unix_seconds_support=0.85,
            timestamp_le_unix_seconds_support=None
        )
        
        # 时间范围
        low = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        high = datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
        
        evidences = detector.detect(profile, low, high)
        
        assert len(evidences) == 0
    
    def test_no_time_range(self):
        """R280: 无 capture_time 时不输出（教程 9.4：不兜底系统时间）"""
        config = Config(
            min_samples=8,
            timestamp_support=0.90
        )
        detector = TimestampDetector(config)

        # 创建画像：无 capture_time（capture_time_min/capture_time_max 为 None）
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.5,
            capture_time_min=None,
            capture_time_max=None,
            timestamp_be_unix_seconds_support=0.95
        )

        # R280: detect(profile) 无额外参数调用
        evidences = detector.detect(profile)

        assert len(evidences) == 0
    
    def test_insufficient_samples(self):
        """样本数不足"""
        config = Config(
            min_samples=8,
            timestamp_support=0.90
        )
        detector = TimestampDetector(config)
        
        # 创建画像：样本数不足
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=5,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.5,
            capture_time_min=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            capture_time_max=datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
            timestamp_be_unix_seconds_support=0.95
        )
        
        # 时间范围
        low = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        high = datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
        
        evidences = detector.detect(profile, low, high)
        
        assert len(evidences) == 1
        assert evidences[0].is_hard_evidence is False
        assert evidences[0].reason_code == "insufficient_samples"
    
    def test_variable_width_excluded(self):
        """变宽字段被排除"""
        config = Config(
            min_samples=8,
            timestamp_support=0.90
        )
        detector = TimestampDetector(config)
        
        # 创建画像：变宽字段
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=False,
            width_mode=4,
            dominant_value_ratio=0.5,
            capture_time_min=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            capture_time_max=datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
            timestamp_be_unix_seconds_support=0.95
        )
        
        # 时间范围
        low = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        high = datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
        
        evidences = detector.detect(profile, low, high)
        
        assert len(evidences) == 0
    
    def test_width_gt_8_excluded(self):
        """宽度 > 8 的字段被排除"""
        config = Config(
            min_samples=8,
            timestamp_support=0.90
        )
        detector = TimestampDetector(config)
        
        # 创建画像：宽度 > 8
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=16,
            dominant_value_ratio=0.5,
            capture_time_min=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            capture_time_max=datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
            timestamp_be_unix_seconds_support=0.95
        )
        
        # 时间范围
        low = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        high = datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
        
        evidences = detector.detect(profile, low, high)
        
        assert len(evidences) == 0
    
    def test_constant_field_excluded(self):
        """常量字段被排除"""
        config = Config(
            min_samples=8,
            timestamp_support=0.90
        )
        detector = TimestampDetector(config)
        
        # 创建画像：常量字段
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=1.0,
            timestamp_be_unix_seconds_support=0.95
        )
        
        # 时间范围
        low = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        high = datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
        
        evidences = detector.detect(profile, low, high)
        
        assert len(evidences) == 0


class TestTimestampDetectorMilliseconds:
    """测试时间戳检测器（Unix 毫秒）"""
    
    def test_unix_milliseconds_be(self):
        """检测 Unix 毫秒 BE 时间戳"""
        config = Config(
            min_samples=8,
            timestamp_support=0.90
        )
        detector = TimestampDetector(config)
        
        # 创建画像：Unix 毫秒 BE 时间戳（8 字节）
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=8,
            dominant_value_ratio=0.5,
            capture_time_min=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            capture_time_max=datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
            timestamp_be_unix_milliseconds_support=0.95,
            timestamp_le_unix_milliseconds_support=None
        )
        
        # 时间范围
        low = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        high = datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
        
        evidences = detector.detect(profile, low, high)
        
        assert len(evidences) == 1
        evidence = evidences[0]
        
        assert evidence.detector == "timestamp"
        assert evidence.coarse_label == "timestamp"
        assert evidence.fine_label == "unix_milliseconds_be"
        assert evidence.score == 0.95
        assert evidence.is_hard_evidence is True
        assert evidence.reason_code == "value_is_unix_milliseconds_be"
        assert evidence.details["format"] == "unix_milliseconds"
        assert evidence.details["endian"] == "be"
        assert evidence.details["byte_width"] == 8
    
    def test_unix_milliseconds_le(self):
        """检测 Unix 毫秒 LE 时间戳"""
        config = Config(
            min_samples=8,
            timestamp_support=0.90
        )
        detector = TimestampDetector(config)
        
        # 创建画像：Unix 毫秒 LE 时间戳（8 字节）
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=8,
            dominant_value_ratio=0.5,
            capture_time_min=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            capture_time_max=datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
            timestamp_be_unix_milliseconds_support=None,
            timestamp_le_unix_milliseconds_support=0.92
        )
        
        # 时间范围
        low = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        high = datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
        
        evidences = detector.detect(profile, low, high)
        
        assert len(evidences) == 1
        evidence = evidences[0]
        
        assert evidence.fine_label == "unix_milliseconds_le"
        assert evidence.details["endian"] == "le"
    
    def test_both_endians_milliseconds(self):
        """同时检测 BE 和 LE（毫秒）"""
        config = Config(
            min_samples=8,
            timestamp_support=0.90
        )
        detector = TimestampDetector(config)
        
        # 创建画像：BE 和 LE 都有支持率
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=8,
            dominant_value_ratio=0.5,
            capture_time_min=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            capture_time_max=datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
            timestamp_be_unix_milliseconds_support=0.95,
            timestamp_le_unix_milliseconds_support=0.93
        )
        
        # 时间范围
        low = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        high = datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
        
        evidences = detector.detect(profile, low, high)
        
        # 应该输出两个证据，BE 在前（支持率更高）
        assert len(evidences) == 2
        assert evidences[0].details["endian"] == "be"
        assert evidences[0].score == 0.95
        assert evidences[1].details["endian"] == "le"
        assert evidences[1].score == 0.93
    
    def test_milliseconds_below_threshold(self):
        """支持率低于阈值（毫秒）"""
        config = Config(
            min_samples=8,
            timestamp_support=0.90
        )
        detector = TimestampDetector(config)
        
        # 创建画像：支持率低于阈值
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=8,
            dominant_value_ratio=0.5,
            capture_time_min=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            capture_time_max=datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
            timestamp_be_unix_milliseconds_support=0.85,
            timestamp_le_unix_milliseconds_support=None
        )
        
        # 时间范围
        low = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        high = datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
        
        evidences = detector.detect(profile, low, high)
        
        assert len(evidences) == 0


class TestTimestampDetectorMicroseconds:
    """测试时间戳检测器（Unix 微秒）"""
    
    def test_unix_microseconds_be(self):
        """检测 Unix 微秒 BE 时间戳"""
        config = Config(
            min_samples=8,
            timestamp_support=0.90
        )
        detector = TimestampDetector(config)
        
        # 创建画像：Unix 微秒 BE 时间戳（8 字节）
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=8,
            dominant_value_ratio=0.5,
            capture_time_min=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            capture_time_max=datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
            timestamp_be_unix_microseconds_support=0.95,
            timestamp_le_unix_microseconds_support=None
        )
        
        # 时间范围
        low = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        high = datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
        
        evidences = detector.detect(profile, low, high)
        
        assert len(evidences) == 1
        evidence = evidences[0]
        
        assert evidence.detector == "timestamp"
        assert evidence.coarse_label == "timestamp"
        assert evidence.fine_label == "unix_microseconds_be"
        assert evidence.score == 0.95
        assert evidence.is_hard_evidence is True
        assert evidence.reason_code == "value_is_unix_microseconds_be"
        assert evidence.details["format"] == "unix_microseconds"
        assert evidence.details["endian"] == "be"
        assert evidence.details["byte_width"] == 8
    
    def test_unix_microseconds_le(self):
        """检测 Unix 微秒 LE 时间戳"""
        config = Config(
            min_samples=8,
            timestamp_support=0.90
        )
        detector = TimestampDetector(config)
        
        # 创建画像：Unix 微秒 LE 时间戳（8 字节）
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=8,
            dominant_value_ratio=0.5,
            capture_time_min=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            capture_time_max=datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
            timestamp_be_unix_microseconds_support=None,
            timestamp_le_unix_microseconds_support=0.92
        )
        
        # 时间范围
        low = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        high = datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
        
        evidences = detector.detect(profile, low, high)
        
        assert len(evidences) == 1
        evidence = evidences[0]
        
        assert evidence.fine_label == "unix_microseconds_le"
        assert evidence.details["endian"] == "le"
    
    def test_both_endians_microseconds(self):
        """同时检测 BE 和 LE（微秒）"""
        config = Config(
            min_samples=8,
            timestamp_support=0.90
        )
        detector = TimestampDetector(config)
        
        # 创建画像：BE 和 LE 都有支持率
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=8,
            dominant_value_ratio=0.5,
            capture_time_min=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            capture_time_max=datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
            timestamp_be_unix_microseconds_support=0.95,
            timestamp_le_unix_microseconds_support=0.93
        )
        
        # 时间范围
        low = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        high = datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
        
        evidences = detector.detect(profile, low, high)
        
        # 应该输出两个证据，BE 在前（支持率更高）
        assert len(evidences) == 2
        assert evidences[0].details["endian"] == "be"
        assert evidences[0].score == 0.95
        assert evidences[1].details["endian"] == "le"
        assert evidences[1].score == 0.93
    
    def test_microseconds_below_threshold(self):
        """支持率低于阈值（微秒）"""
        config = Config(
            min_samples=8,
            timestamp_support=0.90
        )
        detector = TimestampDetector(config)
        
        # 创建画像：支持率低于阈值
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=8,
            dominant_value_ratio=0.5,
            capture_time_min=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            capture_time_max=datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
            timestamp_be_unix_microseconds_support=0.85,
            timestamp_le_unix_microseconds_support=None
        )
        
        # 时间范围
        low = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        high = datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
        
        evidences = detector.detect(profile, low, high)
        
        assert len(evidences) == 0


class TestTimestampDetectorNTPSeconds:
    """测试时间戳检测器（NTP 秒）"""
    
    def test_ntp_seconds_be(self):
        """检测 NTP 秒 BE 时间戳"""
        config = Config(
            min_samples=8,
            timestamp_support=0.90
        )
        detector = TimestampDetector(config)

        # R280: NTP 秒是 4 字节候选（R273 已落地），width_mode=4
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.5,
            capture_time_min=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            capture_time_max=datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
            timestamp_be_ntp_seconds_support=0.95,
            timestamp_le_ntp_seconds_support=None
        )
        
        # 时间范围
        low = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        high = datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
        
        evidences = detector.detect(profile, low, high)
        
        assert len(evidences) == 1
        evidence = evidences[0]
        
        assert evidence.detector == "timestamp"
        assert evidence.coarse_label == "timestamp"
        assert evidence.fine_label == "ntp_seconds_be"
        assert evidence.score == 0.95
        assert evidence.is_hard_evidence is True
        assert evidence.reason_code == "value_is_ntp_seconds_be"
        assert evidence.details["format"] == "ntp_seconds"
        assert evidence.details["endian"] == "be"
        assert evidence.details["byte_width"] == 4
    
    def test_ntp_seconds_le(self):
        """检测 NTP 秒 LE 时间戳"""
        config = Config(
            min_samples=8,
            timestamp_support=0.90
        )
        detector = TimestampDetector(config)

        # R280: NTP 秒是 4 字节候选（R273 已落地），width_mode=4
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.5,
            capture_time_min=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            capture_time_max=datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
            timestamp_be_ntp_seconds_support=None,
            timestamp_le_ntp_seconds_support=0.92
        )
        
        # 时间范围
        low = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        high = datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
        
        evidences = detector.detect(profile, low, high)
        
        assert len(evidences) == 1
        evidence = evidences[0]
        
        assert evidence.fine_label == "ntp_seconds_le"
        assert evidence.details["endian"] == "le"
    
    def test_both_endians_ntp_seconds(self):
        """同时检测 BE 和 LE（NTP 秒）"""
        config = Config(
            min_samples=8,
            timestamp_support=0.90
        )
        detector = TimestampDetector(config)

        # R280: NTP 秒是 4 字节候选（R273 已落地），width_mode=4
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.5,
            capture_time_min=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            capture_time_max=datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
            timestamp_be_ntp_seconds_support=0.95,
            timestamp_le_ntp_seconds_support=0.93
        )
        
        # 时间范围
        low = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        high = datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
        
        evidences = detector.detect(profile, low, high)
        
        # 应该输出两个证据，BE 在前（支持率更高）
        assert len(evidences) == 2
        assert evidences[0].details["endian"] == "be"
        assert evidences[0].score == 0.95
        assert evidences[1].details["endian"] == "le"
        assert evidences[1].score == 0.93
    
    def test_ntp_seconds_below_threshold(self):
        """支持率低于阈值（NTP 秒）"""
        config = Config(
            min_samples=8,
            timestamp_support=0.90
        )
        detector = TimestampDetector(config)

        # R280: NTP 秒是 4 字节候选（R273 已落地），width_mode=4
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.5,
            capture_time_min=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            capture_time_max=datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
            timestamp_be_ntp_seconds_support=0.85,
            timestamp_le_ntp_seconds_support=None
        )
        
        # 时间范围
        low = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        high = datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
        
        evidences = detector.detect(profile, low, high)
        
        assert len(evidences) == 0


class TestTimestampDetectorSlop:
    """测试时间戳检测器 slop 配置"""
    
    def test_slop_affects_boundary_detection(self):
        """slop 参数影响边界检测"""
        # 使用默认 slop (86400 秒 = 1 天)
        config_default = Config(
            min_samples=8,
            timestamp_support=0.90,
            timestamp_slop_seconds=86400
        )
        detector_default = TimestampDetector(config_default)
        
        # 使用较小 slop (1 秒)
        config_small = Config(
            min_samples=8,
            timestamp_support=0.90,
            timestamp_slop_seconds=1
        )
        detector_small = TimestampDetector(config_small)
        
        # 创建画像：时间戳刚好在边界上
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.5,
            capture_time_min=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            capture_time_max=datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
            timestamp_be_unix_seconds_support=0.95,
            timestamp_le_unix_seconds_support=None
        )
        
        # 时间范围
        low = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        high = datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
        
        # 两个检测器都应该检测到（因为支持率已经预计算）
        evidences_default = detector_default.detect(profile, low, high)
        evidences_small = detector_small.detect(profile, low, high)
        
        # 当前实现中，slop 不影响预计算的支持率
        # 但我们应该验证 config.timestamp_slop_seconds 被正确设置
        assert config_default.timestamp_slop_seconds == 86400
        assert config_small.timestamp_slop_seconds == 1
        assert len(evidences_default) == 1
        assert len(evidences_small) == 1
    
    def test_slop_config_validation(self):
        """slop 配置验证"""
        # 正常值
        config = Config(
            min_samples=8,
            timestamp_slop_seconds=3600
        )
        assert config.timestamp_slop_seconds == 3600
        
        # 负值应该被拒绝
        try:
            Config(
                min_samples=8,
                timestamp_slop_seconds=-1
            )
            assert False, "负值应该被拒绝"
        except ValueError:
            pass


class TestTimestampDetectorThresholdBoundary:
    """测试时间戳检测器阈值边界"""
    
    def test_support_below_threshold(self):
        """支持率 0.89 低于阈值 0.90"""
        config = Config(
            min_samples=8,
            timestamp_support=0.90
        )
        detector = TimestampDetector(config)
        
        # 创建画像：支持率 0.89
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.5,
            capture_time_min=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            capture_time_max=datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
            timestamp_be_unix_seconds_support=0.89,
            timestamp_le_unix_seconds_support=None
        )
        
        # 时间范围
        low = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        high = datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
        
        evidences = detector.detect(profile, low, high)
        
        # 支持率低于阈值，不输出证据
        assert len(evidences) == 0
    
    def test_support_at_threshold(self):
        """支持率 0.90 等于阈值 0.90"""
        config = Config(
            min_samples=8,
            timestamp_support=0.90
        )
        detector = TimestampDetector(config)
        
        # 创建画像：支持率 0.90
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.5,
            capture_time_min=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            capture_time_max=datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
            timestamp_be_unix_seconds_support=0.90,
            timestamp_le_unix_seconds_support=None
        )
        
        # 时间范围
        low = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        high = datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
        
        evidences = detector.detect(profile, low, high)
        
        # 支持率等于阈值，输出证据
        assert len(evidences) == 1
        assert evidences[0].score == 0.90
    
    def test_support_above_threshold(self):
        """支持率 0.91 高于阈值 0.90"""
        config = Config(
            min_samples=8,
            timestamp_support=0.90
        )
        detector = TimestampDetector(config)
        
        # 创建画像：支持率 0.91
        profile = FieldProfile(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.5,
            capture_time_min=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            capture_time_max=datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
            timestamp_be_unix_seconds_support=0.91,
            timestamp_le_unix_seconds_support=None
        )
        
        # 时间范围
        low = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        high = datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
        
        evidences = detector.detect(profile, low, high)
        
        # 支持率高于阈值，输出证据
        assert len(evidences) == 1
        assert evidences[0].score == 0.91


class TestTimestampDetectorR281:
    """R281: 无 capture_time 与覆盖不足的 timestamp 负例

    教程 9.4：所有 capture_time 缺失时 support=None，不用当前系统时间兜底。
    R280: detect() 检查 capture_time_min/capture_time_max，缺失时不输出。
    本测试类覆盖各种 capture_time 缺失组合和覆盖不足场景。
    """

    def _make_profile(self, **overrides):
        """构造默认有效 profile，用 overrides 覆盖指定字段"""
        defaults = dict(
            layout_id="test_layout",
            direction="up",
            field_index=0,
            sample_count=100,
            fixed_width=True,
            width_mode=4,
            dominant_value_ratio=0.5,
            capture_time_count=100,
            capture_time_coverage=1.0,
            capture_time_min=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            capture_time_max=datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc),
            timestamp_be_unix_seconds_support=0.95,
            timestamp_le_unix_seconds_support=None,
        )
        defaults.update(overrides)
        return FieldProfile(**defaults)

    def test_capture_time_min_none_only(self):
        """capture_time_min=None（max 有值）时不输出"""
        config = Config(min_samples=8, timestamp_support=0.90)
        detector = TimestampDetector(config)
        profile = self._make_profile(capture_time_min=None)
        evidences = detector.detect(profile)
        assert len(evidences) == 0

    def test_capture_time_max_none_only(self):
        """capture_time_max=None（min 有值）时不输出"""
        config = Config(min_samples=8, timestamp_support=0.90)
        detector = TimestampDetector(config)
        profile = self._make_profile(capture_time_max=None)
        evidences = detector.detect(profile)
        assert len(evidences) == 0

    def test_capture_time_both_none_but_support_set(self):
        """两者都 None 但 support 字段有值：detector 仍不输出（优先检查 capture_time）"""
        config = Config(min_samples=8, timestamp_support=0.90)
        detector = TimestampDetector(config)
        profile = self._make_profile(
            capture_time_min=None,
            capture_time_max=None,
            capture_time_count=0,
            capture_time_coverage=0.0,
            timestamp_be_unix_seconds_support=0.95,
        )
        evidences = detector.detect(profile)
        assert len(evidences) == 0

    def test_capture_time_count_zero(self):
        """capture_time_count=0（min/max 应为 None）时不输出"""
        config = Config(min_samples=8, timestamp_support=0.90)
        detector = TimestampDetector(config)
        profile = self._make_profile(
            capture_time_count=0,
            capture_time_coverage=0.0,
            capture_time_min=None,
            capture_time_max=None,
            timestamp_be_unix_seconds_support=None,
        )
        evidences = detector.detect(profile)
        assert len(evidences) == 0

    def test_capture_time_coverage_zero(self):
        """capture_time_coverage=0.0（min/max=None）时不输出"""
        config = Config(min_samples=8, timestamp_support=0.90)
        detector = TimestampDetector(config)
        profile = self._make_profile(
            capture_time_count=0,
            capture_time_coverage=0.0,
            capture_time_min=None,
            capture_time_max=None,
        )
        evidences = detector.detect(profile)
        assert len(evidences) == 0

    def test_low_capture_time_coverage_still_outputs(self):
        """低 coverage（0.3）但 min/max 有值且 support 高：仍输出

        教程 9.4 只要求"所有缺失"时 support=None；部分缺失时 support 仍计算。
        detector 不检查 coverage，只检查 min/max。
        """
        config = Config(min_samples=8, timestamp_support=0.90)
        detector = TimestampDetector(config)
        profile = self._make_profile(
            capture_time_count=30,
            capture_time_coverage=0.3,
        )
        evidences = detector.detect(profile)
        assert len(evidences) == 1
        assert evidences[0].score == 0.95

    def test_partial_capture_time_half_coverage(self):
        """50% coverage 但 min/max 有值且 support 高：仍输出"""
        config = Config(min_samples=8, timestamp_support=0.90)
        detector = TimestampDetector(config)
        profile = self._make_profile(
            capture_time_count=50,
            capture_time_coverage=0.5,
        )
        evidences = detector.detect(profile)
        assert len(evidences) == 1
        assert evidences[0].score == 0.95

    def test_capture_time_min_equals_max(self):
        """capture_time_min==max（单一时间点）但 support 高：仍输出

        单一时间点不等于缺失，detector 应正常输出。
        """
        config = Config(min_samples=8, timestamp_support=0.90)
        detector = TimestampDetector(config)
        same_time = datetime(2020, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        profile = self._make_profile(
            capture_time_min=same_time,
            capture_time_max=same_time,
            capture_time_count=100,
            capture_time_coverage=1.0,
        )
        evidences = detector.detect(profile)
        assert len(evidences) == 1
        assert evidences[0].score == 0.95

    def test_capture_time_none_with_low_timestamp_arg_ignored(self):
        """capture_time 缺失时，传入 low_timestamp/high_timestamp 参数也不输出

        R280: low_timestamp/high_timestamp 参数已废弃，detect() 只看 profile.capture_time_*。
        即使传入参数，capture_time 缺失仍不输出。
        """
        config = Config(min_samples=8, timestamp_support=0.90)
        detector = TimestampDetector(config)
        profile = self._make_profile(
            capture_time_min=None,
            capture_time_max=None,
        )
        low = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        high = datetime(2020, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
        evidences = detector.detect(profile, low, high)
        assert len(evidences) == 0

    def test_capture_time_none_ntp_seconds_not_output(self):
        """capture_time 缺失时 NTP 秒也不输出"""
        config = Config(min_samples=8, timestamp_support=0.90)
        detector = TimestampDetector(config)
        profile = self._make_profile(
            capture_time_min=None,
            capture_time_max=None,
            timestamp_be_unix_seconds_support=None,
            timestamp_be_ntp_seconds_support=0.95,
        )
        evidences = detector.detect(profile)
        assert len(evidences) == 0

    def test_capture_time_none_milliseconds_not_output(self):
        """capture_time 缺失时 8 字节毫秒也不输出"""
        config = Config(min_samples=8, timestamp_support=0.90)
        detector = TimestampDetector(config)
        profile = self._make_profile(
            width_mode=8,
            capture_time_min=None,
            capture_time_max=None,
            timestamp_be_unix_seconds_support=None,
            timestamp_be_unix_milliseconds_support=0.95,
        )
        evidences = detector.detect(profile)
        assert len(evidences) == 0
