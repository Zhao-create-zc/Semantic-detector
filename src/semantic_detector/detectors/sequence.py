"""序列检测器

检测字段值是否表示序列号或计数器（严格递增、非递减、步长为 1 等）。
"""

from typing import List, Optional
from semantic_detector.detectors.base import Detector, create_hard_evidence, check_min_samples
from semantic_detector.contracts import DetectorEvidence
from semantic_detector.profiling.profile_builder import FieldProfile
from semantic_detector.config import Config
from semantic_detector.taxonomy import CANONICAL_COARSE_LABELS


class SequenceDetector:
    """序列检测器

    检测字段值是否表示序列号或计数器。
    支持 BE 和 LE，不先验偏置，选择支持率更高的 endian。

    R239：coarse_label 固定为标准标签 "sequence_or_counter"（来自 taxonomy）。
    fine_label 动态生成（含 bit 宽度与 endian），不引入固定 FINE_LABEL 常量。
    输出 hard evidence（与 identifier/payload/type_opcode 的 soft candidate 不同）。
    """

    name = "sequence"
    # R239: coarse_label 引用 taxonomy 标准标签
    COARSE_LABEL = "sequence_or_counter"  # CANONICAL_COARSE_LABELS 中的标准标签
    
    def __init__(self, config: Config):
        """初始化序列检测器
        
        Args:
            config: 配置对象
        """
        self.config = config
    
    def detect(
        self,
        profile: FieldProfile
    ) -> List[DetectorEvidence]:
        """检测字段是否表示序列号或计数器
        
        同时测试 BE 和 LE，不先验偏置，选择支持率更高的 endian。
        
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
        
        # 排除宽度 > 8 的字段
        if profile.width_mode > 8:
            return []
        
        # 排除常量字段（审计修复瑕疵-9：接入 config.constant_support）
        if profile.dominant_value_ratio >= self.config.constant_support:
            return []
        
        # R356：使用 config.sequence_unique_ratio 替代硬编码 0.5
        if profile.unique_ratio < self.config.sequence_unique_ratio:
            return []
        
        evidences = []
        
        # 收集所有候选（BE 和 LE）
        candidates = []
        
        # BE 候选
        be_score = self._calculate_sequence_score_be(profile)
        if be_score is not None and be_score >= self.config.sequence_increasing_ratio:
            candidates.append({
                "endian": "be",
                "byte_width": profile.width_mode,
                "score": be_score
            })
        
        # LE 候选
        le_score = self._calculate_sequence_score_le(profile)
        if le_score is not None and le_score >= self.config.sequence_increasing_ratio:
            candidates.append({
                "endian": "le",
                "byte_width": profile.width_mode,
                "score": le_score
            })
        
        # 按分数降序排序
        candidates.sort(key=lambda x: x["score"], reverse=True)
        
        # 创建证据（R239: coarse_label 用标准标签 sequence_or_counter）
        for candidate in candidates:
            evidence = create_hard_evidence(
                detector=self.name,
                coarse_label=self.COARSE_LABEL,
                fine_label=f"sequence_{candidate['byte_width']*8}bit_{candidate['endian']}",
                score=candidate["score"],
                reason_code="sequence_detected",
                details={
                    "endian": candidate["endian"],
                    "byte_width": candidate["byte_width"],
                    "support_ratio": candidate["score"]
                }
            )
            evidences.append(evidence)
        
        return evidences
    
    def _calculate_sequence_score_be(self, profile: FieldProfile) -> Optional[float]:
        """计算 BE 序列分数
        
        优先检查 step_one_ratio，然后是 strictly_increasing_ratio。
        
        Args:
            profile: 字段画像
            
        Returns:
            序列分数（0.0 到 1.0），或 None 如果无法计算
        """
        # 优先检查 step_one_ratio
        if profile.numeric_be_step_one_ratio is not None:
            if profile.numeric_be_step_one_ratio >= 0.7:
                return profile.numeric_be_step_one_ratio
        
        # 然后检查 strictly_increasing_ratio
        if profile.numeric_be_strictly_increasing_ratio is not None:
            return profile.numeric_be_strictly_increasing_ratio
        
        return None
    
    def _calculate_sequence_score_le(self, profile: FieldProfile) -> Optional[float]:
        """计算 LE 序列分数
        
        优先检查 step_one_ratio，然后是 strictly_increasing_ratio。
        
        Args:
            profile: 字段画像
            
        Returns:
            序列分数（0.0 到 1.0），或 None 如果无法计算
        """
        # 优先检查 step_one_ratio
        if profile.numeric_le_step_one_ratio is not None:
            if profile.numeric_le_step_one_ratio >= 0.7:
                return profile.numeric_le_step_one_ratio
        
        # 然后检查 strictly_increasing_ratio
        if profile.numeric_le_strictly_increasing_ratio is not None:
            return profile.numeric_le_strictly_increasing_ratio
        
        return None
