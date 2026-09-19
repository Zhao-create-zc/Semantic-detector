"""检测器基础模块"""

from typing import Protocol, List, runtime_checkable, Any, Optional

from semantic_detector.contracts import DetectorEvidence
from semantic_detector.profiling.profile_builder import FieldProfile


@runtime_checkable
class Detector(Protocol):
    """检测器协议
    
    所有检测器必须实现此协议，提供统一的接口。
    """
    
    name: str
    
    def detect(self, profile: FieldProfile) -> List[DetectorEvidence]:
        """检测字段语义
        
        Args:
            profile: 字段画像
            
        Returns:
            检测器证据列表
        """
        ...


def create_hard_evidence(
    detector: str,
    coarse_label: str,
    fine_label: str,
    score: float,
    reason_code: str,
    details: Optional[dict[str, Any]] = None
) -> DetectorEvidence:
    """创建硬证据
    
    硬证据表示强检测结果，通常来自明确的模式匹配或高置信度规则。
    
    Args:
        detector: 检测器名称
        coarse_label: 粗粒度标签
        fine_label: 细粒度标签
        score: 置信度分数 (0~1)
        reason_code: 原因代码
        details: 可选的详细信息字典，必须可 JSON 序列化
        
    Returns:
        DetectorEvidence 对象
    """
    return DetectorEvidence(
        detector=detector,
        coarse_label=coarse_label,
        fine_label=fine_label,
        score=score,
        is_hard_evidence=True,
        reason_code=reason_code,
        details=details
    )


def create_soft_evidence(
    detector: str,
    coarse_label: str,
    fine_label: str,
    score: float,
    reason_code: str,
    details: Optional[dict[str, Any]] = None
) -> DetectorEvidence:
    """创建软证据
    
    软证据表示弱检测结果，通常来自启发式规则或低置信度模式。
    
    Args:
        detector: 检测器名称
        coarse_label: 粗粒度标签
        fine_label: 细粒度标签
        score: 置信度分数 (0~1)
        reason_code: 原因代码
        details: 可选的详细信息字典，必须可 JSON 序列化
        
    Returns:
        DetectorEvidence 对象
    """
    return DetectorEvidence(
        detector=detector,
        coarse_label=coarse_label,
        fine_label=fine_label,
        score=score,
        is_hard_evidence=False,
        reason_code=reason_code,
        details=details
    )


def check_min_samples(
    sample_count: int,
    min_samples: int,
    detector: str
) -> Optional[DetectorEvidence]:
    """检查样本数是否满足最小要求
    
    如果样本数不足，返回 abstain 证据；否则返回 None。
    
    Args:
        sample_count: 实际样本数
        min_samples: 最小样本数阈值
        detector: 检测器名称
        
    Returns:
        如果样本数不足，返回 abstain 证据；否则返回 None
    """
    if sample_count < min_samples:
        return create_soft_evidence(
            detector=detector,
            coarse_label="unknown",
            fine_label="unknown",
            score=0.0,
            reason_code="insufficient_samples",
            details={
                "sample_count": sample_count,
                "min_samples": min_samples,
                "shortage": min_samples - sample_count
            }
        )
    return None
