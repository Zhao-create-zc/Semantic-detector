"""常量检测器

检测字段是否为常量值（所有样本值相同）。
"""

from typing import List
from semantic_detector.detectors.base import Detector, create_hard_evidence, check_min_samples
from semantic_detector.contracts import DetectorEvidence
from semantic_detector.profiling.profile_builder import FieldProfile
from semantic_detector.config import Config


class ConstantDetector:
    """常量检测器
    
    检测字段是否为常量值。如果所有样本的值都相同，则输出 constant 证据。
    """
    
    name = "constant"
    
    def __init__(self, config: Config):
        """初始化常量检测器
        
        Args:
            config: 配置对象
        """
        self.config = config
    
    def detect(self, profile: FieldProfile) -> List[DetectorEvidence]:
        """检测字段是否为常量
        
        Args:
            profile: 字段画像
            
        Returns:
            检测器证据列表
        """
        # 检查样本数是否足够
        abstain = check_min_samples(
            sample_count=profile.sample_count,
            min_samples=self.config.min_samples,
            detector=self.name
        )
        if abstain:
            return [abstain]
        
        # 计算常量支持率
        # 如果 unique_value_count == 1，则所有样本值相同
        if profile.unique_value_count == 1:
            support_ratio = 1.0
        else:
            # 使用 dominant_value_ratio 作为支持率
            support_ratio = profile.dominant_value_ratio
        
        # 检查是否达到阈值
        if support_ratio >= self.config.constant_support:
            # 创建硬证据
            evidence = create_hard_evidence(
                detector=self.name,
                coarse_label="constant",
                fine_label="constant_value",
                score=support_ratio,
                reason_code="all_samples_identical",
                details={
                    "support_ratio": support_ratio,
                    "unique_value_count": profile.unique_value_count,
                    "sample_count": profile.sample_count
                }
            )
            return [evidence]
        
        # 未达到阈值，返回空列表
        return []


__all__ = ['ConstantDetector']
