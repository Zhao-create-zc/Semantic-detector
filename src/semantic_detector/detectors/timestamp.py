"""时间戳检测器

检测字段值是否表示时间戳（Unix 秒、毫秒、微秒等）。

R280（HIGH-4）：只读取 profile support，无额外参数调用。
Pipeline 统一 detect(profile)，不再传 low_timestamp/high_timestamp。
时间范围来自 profile.capture_time_min/capture_time_max（R270 已落地）。
timestamp_*_support 字段在 build_field_profile 中已计算（R271-R273），
TimestampDetector 只读取这些字段，不重新计算。
"""

from typing import List, Optional
from datetime import datetime, timezone
from semantic_detector.detectors.base import Detector, create_hard_evidence, check_min_samples
from semantic_detector.contracts import DetectorEvidence
from semantic_detector.profiling.profile_builder import FieldProfile
from semantic_detector.config import Config


class TimestampDetector:
    """时间戳检测器

    检测字段值是否表示时间戳。支持 Unix 秒/毫秒/微秒/NTP 秒（BE/LE）。
    R280：只读取 profile.timestamp_*_support 字段，不重新计算。
    """

    name = "timestamp"

    def __init__(self, config: Config):
        """初始化时间戳检测器

        Args:
            config: 配置对象
        """
        self.config = config

    def detect(
        self,
        profile: FieldProfile,
        low_timestamp: Optional[datetime] = None,
        high_timestamp: Optional[datetime] = None
    ) -> List[DetectorEvidence]:
        """检测字段是否表示时间戳

        R280：只读取 profile support 字段，不依赖 low_timestamp/high_timestamp 参数。
        Pipeline 统一 detect(profile) 调用。
        low_timestamp/high_timestamp 参数保留为向后兼容（已废弃，不再使用）。

        Args:
            profile: 字段画像
            low_timestamp: 已废弃（R280 前用于时间范围检查，现由 profile.capture_time_* 替代）
            high_timestamp: 已废弃（同上）

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

        # R280: capture_time 缺失时不输出（教程 9.4：不兜底系统时间）
        # profile.timestamp_*_support 字段在 capture_time 缺失时为 None，
        # 但显式检查 capture_time_min/capture_time_max 更清晰
        if profile.capture_time_min is None or profile.capture_time_max is None:
            return []

        evidences = []

        # 收集所有候选（BE 和 LE），直接读取 profile support 字段
        candidates = []

        # 4 字节候选：Unix 秒、NTP 秒
        if profile.width_mode == 4:
            # BE Unix 秒
            if profile.timestamp_be_unix_seconds_support is not None:
                support = profile.timestamp_be_unix_seconds_support
                if support >= self.config.timestamp_support:
                    candidates.append({
                        "endian": "be",
                        "format": "unix_seconds",
                        "byte_width": 4,
                        "score": support
                    })

            # LE Unix 秒
            if profile.timestamp_le_unix_seconds_support is not None:
                support = profile.timestamp_le_unix_seconds_support
                if support >= self.config.timestamp_support:
                    candidates.append({
                        "endian": "le",
                        "format": "unix_seconds",
                        "byte_width": 4,
                        "score": support
                    })

            # BE NTP 秒
            if profile.timestamp_be_ntp_seconds_support is not None:
                support = profile.timestamp_be_ntp_seconds_support
                if support >= self.config.timestamp_support:
                    candidates.append({
                        "endian": "be",
                        "format": "ntp_seconds",
                        "byte_width": 4,
                        "score": support
                    })

            # LE NTP 秒
            if profile.timestamp_le_ntp_seconds_support is not None:
                support = profile.timestamp_le_ntp_seconds_support
                if support >= self.config.timestamp_support:
                    candidates.append({
                        "endian": "le",
                        "format": "ntp_seconds",
                        "byte_width": 4,
                        "score": support
                    })

        # 8 字节候选：Unix 毫秒、Unix 微秒
        if profile.width_mode == 8:
            # BE Unix 毫秒
            if profile.timestamp_be_unix_milliseconds_support is not None:
                support = profile.timestamp_be_unix_milliseconds_support
                if support >= self.config.timestamp_support:
                    candidates.append({
                        "endian": "be",
                        "format": "unix_milliseconds",
                        "byte_width": 8,
                        "score": support
                    })

            # LE Unix 毫秒
            if profile.timestamp_le_unix_milliseconds_support is not None:
                support = profile.timestamp_le_unix_milliseconds_support
                if support >= self.config.timestamp_support:
                    candidates.append({
                        "endian": "le",
                        "format": "unix_milliseconds",
                        "byte_width": 8,
                        "score": support
                    })

            # BE Unix 微秒
            if profile.timestamp_be_unix_microseconds_support is not None:
                support = profile.timestamp_be_unix_microseconds_support
                if support >= self.config.timestamp_support:
                    candidates.append({
                        "endian": "be",
                        "format": "unix_microseconds",
                        "byte_width": 8,
                        "score": support
                    })

            # LE Unix 微秒
            if profile.timestamp_le_unix_microseconds_support is not None:
                support = profile.timestamp_le_unix_microseconds_support
                if support >= self.config.timestamp_support:
                    candidates.append({
                        "endian": "le",
                        "format": "unix_microseconds",
                        "byte_width": 8,
                        "score": support
                    })

        # 按支持率排序，选择最高的
        candidates.sort(key=lambda x: x["score"], reverse=True)

        # 为每个候选创建证据
        for candidate in candidates:
            fine_label = f"{candidate['format']}_{candidate['endian']}"
            reason_code = f"value_is_{candidate['format']}_{candidate['endian']}"

            evidence = create_hard_evidence(
                detector=self.name,
                coarse_label="timestamp",
                fine_label=fine_label,
                score=candidate["score"],
                reason_code=reason_code,
                details={
                    "format": candidate["format"],
                    "endian": candidate["endian"],
                    "byte_width": candidate["byte_width"],
                    "support_ratio": candidate["score"]
                }
            )
            evidences.append(evidence)

        return evidences


__all__ = ['TimestampDetector']
