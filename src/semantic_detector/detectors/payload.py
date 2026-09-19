"""不透明载荷检测器

检测字段值是否可能是加密或压缩数据（高熵、变长）。
"""

from typing import List
from semantic_detector.detectors.base import Detector, create_soft_evidence, check_min_samples
from semantic_detector.contracts import DetectorEvidence
from semantic_detector.profiling.profile_builder import FieldProfile
from semantic_detector.config import Config
from semantic_detector.taxonomy import CANONICAL_COARSE_LABELS


class PayloadDetector:
    """不透明载荷检测器

    检测字段值是否可能是加密或压缩数据（高熵、变长）。
    输出 soft candidate。

    R237：coarse_label 固定为标准标签 "payload"（来自 taxonomy），
    candidate 状态由 fine_label="opaque_payload_candidate" 表达。
    """

    name = "payload"
    # R237: coarse_label 引用 taxonomy 标准标签
    COARSE_LABEL = "payload"  # CANONICAL_COARSE_LABELS 中的标准标签
    FINE_LABEL = "opaque_payload_candidate"

    def __init__(self, config: Config):
        """初始化载荷检测器

        Args:
            config: 配置对象
        """
        self.config = config

    def detect(
        self,
        profile: FieldProfile
    ) -> List[DetectorEvidence]:
        """检测字段是否可能是载荷

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

        # 检查是否为末尾字段
        if profile.is_last_field_ratio < 0.90:
            return []

        # 检查熵值
        if profile.normalized_entropy is None:
            return []

        if profile.normalized_entropy < self.config.payload_entropy_threshold:
            return []

        # 创建 soft evidence（R237: coarse_label 用标准标签 payload）
        evidence = create_soft_evidence(
            detector=self.name,
            coarse_label=self.COARSE_LABEL,
            fine_label=self.FINE_LABEL,
            score=profile.normalized_entropy,
            reason_code="high_entropy_trailing_field",
            details={
                "normalized_entropy": profile.normalized_entropy,
                "entropy_threshold": self.config.payload_entropy_threshold,
                "is_last_field_ratio": profile.is_last_field_ratio,
                "byte_width": profile.width_mode,
                "warning": "可能是密文或压缩数据"
            }
        )

        return [evidence]
