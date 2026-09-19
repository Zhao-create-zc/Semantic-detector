"""标识符候选检测器

检测字段值是否可能是标识符（高唯一率、非递增）。
"""

from typing import List, Optional
from semantic_detector.detectors.base import Detector, create_soft_evidence, check_min_samples
from semantic_detector.contracts import DetectorEvidence
from semantic_detector.profiling.profile_builder import FieldProfile
from semantic_detector.config import Config
from semantic_detector.taxonomy import CANONICAL_COARSE_LABELS


class IdentifierDetector:
    """标识符候选检测器

    检测字段值是否可能是标识符（高唯一率、非递增）。
    输出 soft candidate，分数不超过配置的 cap。

    R236：coarse_label 固定为标准标签 "identifier"（来自 taxonomy），
    candidate 状态由 fine_label="identifier_candidate" 表达，不混入 coarse_label。
    """

    name = "identifier"
    # R236: coarse_label 引用 taxonomy 标准标签
    COARSE_LABEL = "identifier"  # CANONICAL_COARSE_LABELS 中的标准标签
    FINE_LABEL = "identifier_candidate"

    def __init__(self, config: Config):
        """初始化标识符检测器

        Args:
            config: 配置对象
        """
        self.config = config

    def detect(
        self,
        profile: FieldProfile,
        existing_evidences: Optional[List[DetectorEvidence]] = None
    ) -> List[DetectorEvidence]:
        """检测字段是否可能是标识符

        Args:
            profile: 字段画像
            existing_evidences: 已存在的检测器证据列表（用于排除）

        Returns:
            检测器证据列表
        """
        # 检查是否已存在强证据
        if existing_evidences is not None:
            for evidence in existing_evidences:
                if evidence.is_hard_evidence:
                    # 已存在强证据，不再输出 identifier 候选
                    return []

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

        # 排除常量字段（审计修复瑕疵-9：接入 config.constant_support）
        if profile.dominant_value_ratio >= self.config.constant_support:
            return []

        # 检查唯一率
        if profile.unique_ratio is None:
            return []

        if profile.unique_ratio < self.config.identifier_unique_ratio:
            return []

        # 检查是否为递增序列（如果是递增，则不是标识符）
        if profile.numeric_be_strictly_increasing_ratio is not None:
            if profile.numeric_be_strictly_increasing_ratio >= 0.80:
                return []

        if profile.numeric_le_strictly_increasing_ratio is not None:
            if profile.numeric_le_strictly_increasing_ratio >= 0.80:
                return []

        # 计算分数（不超过 cap）
        if profile.unique_ratio > self.config.identifier_score_cap:
            score = self.config.identifier_score_cap
        else:
            score = profile.unique_ratio

        # 创建 soft evidence（R236: coarse_label 用标准标签 identifier）
        evidence = create_soft_evidence(
            detector=self.name,
            coarse_label=self.COARSE_LABEL,
            fine_label=self.FINE_LABEL,
            score=score,
            reason_code="high_unique_non_increasing",
            details={
                "unique_ratio": profile.unique_ratio,
                "score_cap": self.config.identifier_score_cap,
                "byte_width": profile.width_mode
            }
        )

        return [evidence]
