"""字符串检测器

检测字段值是否表示 ASCII 或 UTF-8 字符串。
"""

from typing import List, Optional
from semantic_detector.detectors.base import Detector, create_hard_evidence, check_min_samples
from semantic_detector.contracts import DetectorEvidence
from semantic_detector.profiling.profile_builder import FieldProfile
from semantic_detector.config import Config


class StringDetector:
    """字符串检测器
    
    检测字段值是否表示 ASCII 或 UTF-8 字符串。
    """
    
    name = "string"
    
    def __init__(self, config: Config):
        """初始化字符串检测器
        
        Args:
            config: 配置对象
        """
        self.config = config
    
    def detect(
        self,
        profile: FieldProfile
    ) -> List[DetectorEvidence]:
        """检测字段是否表示字符串
        
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
        
        # 排除变宽字段
        if not profile.fixed_width:
            return []
        
        # 排除宽度 = 1 的字段（单字节）
        if profile.width_mode == 1:
            return []
        
        # 排除常量字段（审计修复瑕疵-9：接入 config.constant_support）
        if profile.dominant_value_ratio >= self.config.constant_support:
            return []
        
        # 排除全零字段
        if profile.all_zero_sample_ratio >= 0.95:
            return []
        
        # 排除全空字符串字段
        if profile.nonempty_string_ratio <= 0.05:
            return []
        
        evidences = []
        
        # 检查 ASCII 字符串
        if profile.printable_ascii_ratio is not None:
            if profile.printable_ascii_ratio >= self.config.string_printable_ratio:
                # 检查非空字符串比例
                if profile.utf8_decode_success_ratio is not None:
                    nonempty_ratio = profile.utf8_decode_success_ratio
                    if nonempty_ratio >= self.config.string_nonempty_ratio:
                        evidence = create_hard_evidence(
                            detector=self.name,
                            coarse_label="string",
                            fine_label="ascii_string",
                            score=profile.printable_ascii_ratio,
                            reason_code="ascii_string_detected",
                            details={
                                "printable_ascii_ratio": profile.printable_ascii_ratio,
                                "utf8_decode_success_ratio": profile.utf8_decode_success_ratio,
                                "byte_width": profile.width_mode
                            }
                        )
                        evidences.append(evidence)
        
        # 检查 UTF-8 字符串（仅当 ASCII 检测失败时）
        if not evidences:
            if profile.utf8_decode_success_ratio is not None:
                if profile.utf8_decode_success_ratio >= self.config.string_nonempty_ratio:
                    evidence = create_hard_evidence(
                        detector=self.name,
                        coarse_label="string",
                        fine_label="utf8_string",
                        score=profile.utf8_decode_success_ratio,
                        reason_code="utf8_string_detected",
                        details={
                            "printable_ascii_ratio": profile.printable_ascii_ratio,
                            "utf8_decode_success_ratio": profile.utf8_decode_success_ratio,
                            "byte_width": profile.width_mode
                        }
                    )
                    evidences.append(evidence)
        
        return evidences
