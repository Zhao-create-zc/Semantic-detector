"""长度检测器

检测字段值是否表示消息长度或剩余字节数。

R276（HIGH-7）：重写为使用 exact/offset support（来自 bi_adapted.length_relations），
替代 Pearson correlation。教程 8.1 明确：correlation=1.0 不代表 value==length。
判定依据改为 value==length 的精确支持率（exact_support）或带固定偏移的支持率（offset_support）。
教程 8.4 前置条件：distinct_value_count >= 2（排除常量伪证据）。

R279（HIGH-7）：单字节字段（width_mode == 1）BE 和 LE 解码结果完全相同，
跳过 LE 候选检查避免生成重复候选（端序折叠）。
"""

from typing import List
from semantic_detector.detectors.base import Detector, create_hard_evidence, check_min_samples
from semantic_detector.contracts import DetectorEvidence
from semantic_detector.profiling.profile_builder import FieldProfile
from semantic_detector.config import Config


class LengthDetector:
    """长度检测器

    R276：使用 exact_support / offset_support 替代 correlation。
    同时测试 BE 和 LE，不先验偏置，选择支持率更高的 endian。
    排除常量字段（dominant_value_ratio >= config.constant_support）。
    排除变宽字段（fixed_width = False）。
    排除宽度 > 4 的字段。
    R276 新增：distinct_value_count >= 2 才可能为长度字段（教程 8.4）。
    """

    name = "length"

    def __init__(self, config: Config):
        """初始化长度检测器

        Args:
            config: 配置对象
        """
        self.config = config

    def detect(self, profile: FieldProfile) -> List[DetectorEvidence]:
        """检测字段是否表示长度

        R276：使用 exact_support / offset_support 替代 correlation。
        - exact_support: value == message_length / remaining_bytes 的精确比例
        - offset_support: value == message_length / remaining_bytes + offset 的比例
        reason_code 反映真实算法：
        - exact: value_equals_message_length / value_equals_remaining_bytes
        - offset: value_equals_message_length_plus_offset / value_equals_remaining_bytes_plus_offset

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

        # 排除宽度 > 4 的字段
        if profile.width_mode > 4:
            return []

        # 排除常量字段（审计修复瑕疵-9：接入 config.constant_support 替代硬编码 0.98）
        if profile.dominant_value_ratio >= self.config.constant_support:
            return []

        # R276: 收集所有候选（BE 和 LE），使用 exact_support / offset_support
        candidates = []

        # BE 候选（教程 8.4：distinct_value_count >= 2 才可能是长度字段）
        be_distinct = profile.numeric_be_distinct_value_count or 0
        if be_distinct >= 2:
            candidates.extend(self._collect_endian_candidates(
                profile, endian="be",
                ml_exact=profile.numeric_be_message_length_exact_support,
                rb_exact=profile.numeric_be_remaining_bytes_exact_support,
                ml_offset_support=profile.numeric_be_message_length_offset_support,
                ml_offset=profile.numeric_be_message_length_offset,
                rb_offset_support=profile.numeric_be_remaining_bytes_offset_support,
                rb_offset=profile.numeric_be_remaining_bytes_offset,
            ))

        # LE 候选
        # R279: 单字节字段（width_mode == 1）BE 和 LE 解码结果完全相同，
        # 跳过 LE 检查避免生成重复候选（端序折叠）。
        le_distinct = profile.numeric_le_distinct_value_count or 0
        if le_distinct >= 2 and profile.width_mode > 1:
            candidates.extend(self._collect_endian_candidates(
                profile, endian="le",
                ml_exact=profile.numeric_le_message_length_exact_support,
                rb_exact=profile.numeric_le_remaining_bytes_exact_support,
                ml_offset_support=profile.numeric_le_message_length_offset_support,
                ml_offset=profile.numeric_le_message_length_offset,
                rb_offset_support=profile.numeric_le_remaining_bytes_offset_support,
                rb_offset=profile.numeric_le_remaining_bytes_offset,
            ))

        # 按支持率排序，选择最高的
        candidates.sort(key=lambda x: x["score"], reverse=True)

        # 为每个候选创建证据
        evidences = []
        for candidate in candidates:
            if candidate["relation"] == "total":
                fine_label = "total_message_length"
                if candidate["mode"] == "exact":
                    reason_code = "value_equals_message_length"
                else:
                    reason_code = "value_equals_message_length_plus_offset"
            else:
                fine_label = "remaining_bytes"
                if candidate["mode"] == "exact":
                    reason_code = "value_equals_remaining_bytes"
                else:
                    reason_code = "value_equals_remaining_bytes_plus_offset"

            evidence = create_hard_evidence(
                detector=self.name,
                coarse_label="length",
                fine_label=fine_label,
                score=candidate["score"],
                reason_code=reason_code,
                details={
                    "relation": candidate["relation"],
                    "endian": candidate["endian"],
                    "support_ratio": candidate["score"],
                    "offset": candidate["offset"],
                }
            )
            evidences.append(evidence)

        return evidences

    def _collect_endian_candidates(
        self,
        profile: FieldProfile,
        endian: str,
        ml_exact,
        rb_exact,
        ml_offset_support,
        ml_offset,
        rb_offset_support,
        rb_offset,
    ) -> list:
        """收集单个 endian 的长度候选

        R276：优先 exact（offset=0），若 exact 未达阈值但 offset（offset!=0）达阈值则用 offset。
        避免重复：offset==0 时只输出 exact 候选（offset_support == exact_support 时）。

        Args:
            profile: 字段画像
            endian: "be" 或 "le"
            ml_exact: message_length exact_support
            rb_exact: remaining_bytes exact_support
            ml_offset_support: message_length offset_support
            ml_offset: message_length offset 值
            rb_offset_support: remaining_bytes offset_support
            rb_offset: remaining_bytes offset 值

        Returns:
            候选字典列表
        """
        candidates = []
        threshold = self.config.length_support

        # message_length 候选
        if ml_exact is not None and ml_exact >= threshold:
            # exact 命中（offset=0）
            candidates.append({
                "endian": endian,
                "relation": "total",
                "mode": "exact",
                "score": ml_exact,
                "offset": 0,
            })
        elif (ml_offset_support is not None and ml_offset_support >= threshold
              and ml_offset is not None and ml_offset != 0):
            # offset 命中（offset!=0，避免与 exact 重复）
            candidates.append({
                "endian": endian,
                "relation": "total",
                "mode": "offset",
                "score": ml_offset_support,
                "offset": ml_offset,
            })

        # remaining_bytes 候选
        if rb_exact is not None and rb_exact >= threshold:
            candidates.append({
                "endian": endian,
                "relation": "remaining",
                "mode": "exact",
                "score": rb_exact,
                "offset": 0,
            })
        elif (rb_offset_support is not None and rb_offset_support >= threshold
              and rb_offset is not None and rb_offset != 0):
            candidates.append({
                "endian": endian,
                "relation": "remaining",
                "mode": "offset",
                "score": rb_offset_support,
                "offset": rb_offset,
            })

        return candidates


__all__ = ['LengthDetector']
