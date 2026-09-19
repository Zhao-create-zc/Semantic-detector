"""R081+R087: Detector 协议和基础检测器抽象测试"""

import json
from semantic_detector.detectors.base import Detector, create_hard_evidence, create_soft_evidence
from semantic_detector.contracts import DetectorEvidence
from semantic_detector.profiling.profile_builder import FieldProfile


class MockDetector:
    """最小假检测器，用于测试协议"""
    
    name = "mock_detector"
    
    def detect(self, profile: FieldProfile) -> list[DetectorEvidence]:
        """返回空证据列表"""
        return []


class TestDetectorProtocol:
    """测试 Detector 协议"""
    
    def test_detector_is_protocol(self):
        """Detector 是 Protocol"""
        from typing import Protocol
        assert issubclass(Detector, Protocol)
    
    def test_mock_detector_satisfies_protocol(self):
        """假检测器满足协议"""
        detector = MockDetector()
        assert isinstance(detector, Detector)
    
    def test_detector_has_name(self):
        """检测器有 name 属性"""
        detector = MockDetector()
        assert hasattr(detector, 'name')
        assert detector.name == "mock_detector"
    
    def test_detector_has_detect_method(self):
        """检测器有 detect 方法"""
        detector = MockDetector()
        assert hasattr(detector, 'detect')
        assert callable(detector.detect)
    
    def test_detect_returns_list(self):
        """detect 返回列表"""
        detector = MockDetector()
        profile = FieldProfile()
        result = detector.detect(profile)
        assert isinstance(result, list)
    
    def test_detect_returns_evidence_list(self):
        """detect 返回 DetectorEvidence 列表"""
        detector = MockDetector()
        profile = FieldProfile()
        result = detector.detect(profile)
        # 空列表也是合法的
        assert all(isinstance(e, DetectorEvidence) for e in result)
    
    def test_protocol_enforces_name(self):
        """协议强制要求 name 属性"""
        class BadDetector:
            def detect(self, profile: FieldProfile) -> list[DetectorEvidence]:
                return []
        
        # 没有 name 属性的类不满足协议
        bad_detector = BadDetector()
        assert not isinstance(bad_detector, Detector)
    
    def test_protocol_enforces_detect(self):
        """协议强制要求 detect 方法"""
        class BadDetector:
            name = "bad_detector"
        
        # 没有 detect 方法的类不满足协议
        bad_detector = BadDetector()
        assert not isinstance(bad_detector, Detector)


class TestDetectorEvidenceFactory:
    """R087: 测试 DetectorEvidence 工厂助手"""
    
    def test_create_hard_evidence(self):
        """创建硬证据"""
        evidence = create_hard_evidence(
            detector="constant_detector",
            coarse_label="constant",
            fine_label="constant",
            score=0.98,
            reason_code="all_samples_same"
        )
        
        assert evidence.detector == "constant_detector"
        assert evidence.coarse_label == "constant"
        assert evidence.fine_label == "constant"
        assert evidence.score == 0.98
        assert evidence.is_hard_evidence is True
        assert evidence.reason_code == "all_samples_same"
        assert evidence.details is None
    
    def test_create_soft_evidence(self):
        """创建软证据"""
        evidence = create_soft_evidence(
            detector="identifier_detector",
            coarse_label="identifier_candidate",
            fine_label="identifier_candidate",
            score=0.65,
            reason_code="high_unique_ratio"
        )
        
        assert evidence.detector == "identifier_detector"
        assert evidence.coarse_label == "identifier_candidate"
        assert evidence.fine_label == "identifier_candidate"
        assert evidence.score == 0.65
        assert evidence.is_hard_evidence is False
        assert evidence.reason_code == "high_unique_ratio"
    
    def test_create_hard_evidence_with_details(self):
        """创建带 details 的硬证据"""
        details = {
            "support_ratio": 0.98,
            "dominant_value": "0x01",
            "sample_count": 100
        }
        
        evidence = create_hard_evidence(
            detector="constant_detector",
            coarse_label="constant",
            fine_label="constant",
            score=0.98,
            reason_code="all_samples_same",
            details=details
        )
        
        assert evidence.details is not None
        assert evidence.details["support_ratio"] == 0.98
        assert evidence.details["dominant_value"] == "0x01"
        assert evidence.details["sample_count"] == 100
    
    def test_create_soft_evidence_with_details(self):
        """创建带 details 的软证据"""
        details = {
            "unique_ratio": 0.85,
            "increasing_ratio": 0.30
        }
        
        evidence = create_soft_evidence(
            detector="identifier_detector",
            coarse_label="identifier_candidate",
            fine_label="identifier_candidate",
            score=0.65,
            reason_code="high_unique_ratio",
            details=details
        )
        
        assert evidence.details is not None
        assert evidence.details["unique_ratio"] == 0.85
    
    def test_details_json_serializable(self):
        """details 可 JSON 序列化"""
        details = {
            "support_ratio": 0.98,
            "value": "0x01",
            "count": 100,
            "nested": {"key": "value"}
        }
        
        evidence = create_hard_evidence(
            detector="test",
            coarse_label="test",
            fine_label="test",
            score=0.5,
            reason_code="test",
            details=details
        )
        
        # 验证 details 可以 JSON 序列化
        json_str = json.dumps(evidence.details)
        assert json_str is not None
        
        # 验证可以反序列化
        decoded = json.loads(json_str)
        assert decoded["support_ratio"] == 0.98
        assert decoded["count"] == 100
    
    def test_details_with_list(self):
        """details 包含列表"""
        details = {
            "values": [1, 2, 3],
            "labels": ["a", "b", "c"]
        }
        
        evidence = create_hard_evidence(
            detector="test",
            coarse_label="test",
            fine_label="test",
            score=0.5,
            reason_code="test",
            details=details
        )
        
        # 验证可以 JSON 序列化
        json_str = json.dumps(evidence.details)
        decoded = json.loads(json_str)
        assert decoded["values"] == [1, 2, 3]
    
    def test_hard_vs_soft_evidence(self):
        """硬证据和软证据的区别"""
        hard = create_hard_evidence(
            detector="test",
            coarse_label="label",
            fine_label="sublabel",
            score=0.9,
            reason_code="hard_match"
        )
        soft = create_soft_evidence(
            detector="test",
            coarse_label="label",
            fine_label="sublabel",
            score=0.9,
            reason_code="soft_match"
        )
        
        assert hard.is_hard_evidence is True
        assert soft.is_hard_evidence is False


class TestMinSamplesCheck:
    """测试样本数检查"""
    
    def test_insufficient_samples(self):
        """样本数不足返回 abstain"""
        from semantic_detector.detectors.base import check_min_samples
        
        result = check_min_samples(
            sample_count=5,
            min_samples=8,
            detector="test_detector"
        )
        
        assert result is not None
        assert result.detector == "test_detector"
        assert result.coarse_label == "unknown"
        assert result.fine_label == "unknown"
        assert result.score == 0.0
        assert result.is_hard_evidence is False
        assert result.reason_code == "insufficient_samples"
        assert result.details["sample_count"] == 5
        assert result.details["min_samples"] == 8
        assert result.details["shortage"] == 3
    
    def test_sufficient_samples(self):
        """样本数足够返回 None"""
        from semantic_detector.detectors.base import check_min_samples
        
        result = check_min_samples(
            sample_count=8,
            min_samples=8,
            detector="test_detector"
        )
        
        assert result is None
    
    def test_more_than_min_samples(self):
        """样本数超过最小值返回 None"""
        from semantic_detector.detectors.base import check_min_samples
        
        result = check_min_samples(
            sample_count=10,
            min_samples=8,
            detector="test_detector"
        )
        
        assert result is None
    
    def test_zero_samples(self):
        """零样本返回 abstain"""
        from semantic_detector.detectors.base import check_min_samples
        
        result = check_min_samples(
            sample_count=0,
            min_samples=1,
            detector="test_detector"
        )
        
        assert result is not None
        assert result.reason_code == "insufficient_samples"
        assert result.details["shortage"] == 1
    
    def test_boundary_case(self):
        """边界情况：刚好少一个"""
        from semantic_detector.detectors.base import check_min_samples
        
        result = check_min_samples(
            sample_count=7,
            min_samples=8,
            detector="test_detector"
        )
        
        assert result is not None
        assert result.details["shortage"] == 1
