"""检测流水线

整合所有检测器和 Resolver，对 FieldProfile 执行检测。
"""

import uuid
from typing import List, Dict, Tuple
from semantic_detector.contracts import (
    DetectorEvidence,
    SemanticPrediction,
    Direction,
    ALLOWED_DIRECTIONS,
    TypeOpcodeAlignmentKey,
    RunCounts,
    RunManifestInfo,
)
from semantic_detector.profiling.profile_builder import FieldProfile
from semantic_detector.detectors import list_detectors, register_all_detectors
from semantic_detector.detectors.type_opcode import (
    detect_type_or_opcode,
    is_type_opcode_profile_eligible,
)
from semantic_detector.scoring.resolver import Resolver


def build_type_opcode_alignment_key(profile: FieldProfile) -> TypeOpcodeAlignmentKey:
    """从 FieldProfile 构造 TypeOpcodeAlignmentKey（R328）

    V2 审计 HIGH-1 修复：唯一允许的对齐键构造方式，禁止手工拼 tuple。

    教程 10.3：Type/Opcode 检测器需要跨 layout 对齐相同语义位置的字段。
    旧实现手工拼 `key = (profile.direction, profile.field_index,
    profile.width_mode, profile.start_mode)`，但 detector 把 `[3]` 当作 width，
    导致 start_mode 被误判为宽度。

    本函数明确从 profile 读取 4 个具名字段，构造 TypeOpcodeAlignmentKey，
    消除位置索引歧义。

    Args:
        profile: 字段画像

    Returns:
        TypeOpcodeAlignmentKey 具名对齐键

    Raises:
        ValueError: 当 direction 非法时（通过 TypeOpcodeAlignmentKey.__post_init__）
    """
    # profile.direction 是字符串（"request"/"response"/"unknown"），转为 Direction 枚举
    if profile.direction in ALLOWED_DIRECTIONS:
        direction = Direction(profile.direction)
    else:
        direction = Direction.UNKNOWN
    return TypeOpcodeAlignmentKey(
        direction=direction,
        field_index=profile.field_index,
        start_mode=profile.start_mode,
        width_mode=profile.width_mode,
    )


class DetectionPipeline:
    """检测流水线

    整合所有检测器和 Resolver，对 FieldProfile 执行检测。

    R355：所有检测器和 Resolver 引用同一配置快照，禁止内部再 Config()。
    """

    def __init__(
        self,
        config=None,
        resolver: Resolver | None = None,
        run_id: str | None = None,
        config_source: str = "default",
    ):
        """初始化检测流水线

        R355：接收唯一 Config 实例，所有检测器和 Resolver 引用同一配置快照。
        R359：记录 config_source 用于 manifest 审计（"default" 或用户配置文件路径）。

        Args:
            config: Config 实例（R355）。如果为 None，使用默认 Config()
                保持向后兼容，但建议显式传入。禁止在 Pipeline 内部为每个
                检测器单独创建 Config。
            resolver: 解析器实例，如果为 None 则用 config 创建默认解析器
            run_id: 运行 ID，如果为 None 则自动生成
            config_source: 配置来源（R359）。"default" 表示内建默认配置，
                其他值为用户配置文件路径。用于 manifest 审计。
        """
        # R355：加载唯一 Config 实例（向后兼容：未传时用默认 Config）
        if config is None:
            from semantic_detector.config import Config
            config = Config()
        self.config = config
        # R359：记录配置来源（用于 manifest 审计）
        self.config_source = config_source

        # R355：用传入的 config 注册所有检测器（禁止内部再 Config()）
        # 清空全局注册表，确保用新 config 重新注册
        from semantic_detector.detectors import clear_registry, register_all_detectors_with_config
        clear_registry()
        register_all_detectors_with_config(config)

        self.detectors = list_detectors()
        self.resolver = resolver if resolver is not None else Resolver(
            min_score=config.resolver_min_score,
            ambiguity_margin=config.ambiguity_margin,
        )
        self.run_id = run_id if run_id is not None else self._generate_run_id()
    
    def _generate_run_id(self) -> str:
        """生成运行 ID
        
        Returns:
            UUID 格式的运行 ID
        """
        return str(uuid.uuid4())
    
    def detect_field(
        self,
        profile: FieldProfile
    ) -> SemanticPrediction:
        """对单个 FieldProfile 执行检测，包装为完整 SemanticPrediction

        R241：返回 SemanticPrediction 而非 DetectorEvidence。
        包含 run_id/layout_id/direction/field_index/coarse_label/fine_label/
        confidence/abstained/evidence/alternatives/prediction_status。

        prediction_status 规则：
        - confirmed: primary 是 hard evidence
        - candidate: primary 是 soft evidence
        - abstained: primary 是 unknown（拒识）

        Args:
            profile: 字段画像

        Returns:
            完整 SemanticPrediction
        """
        # 收集所有检测器的候选
        candidates: List[DetectorEvidence] = []

        for detector in self.detectors:
            # 跳过没有 detect 方法的检测器（如 TypeOpcodeDetector）
            if not hasattr(detector, 'detect'):
                continue

            evidences = detector.detect(profile)
            candidates.extend(evidences)

        # R241: 用 resolve_with_context 获取 primary 和 alternatives
        primary, alternative_evidences = self.resolver.resolve_with_context(candidates)

        return self._wrap_prediction(profile, primary, alternative_evidences)

    def _wrap_prediction(
        self,
        profile: FieldProfile,
        primary: DetectorEvidence,
        alternative_evidences: List[DetectorEvidence]
    ) -> SemanticPrediction:
        """将 primary evidence 和 alternatives 包装为 SemanticPrediction

        Args:
            profile: 字段画像（提供 run_id 之外的身份证号）
            primary: 主要证据（可能是 unknown）
            alternative_evidences: 备选证据列表

        Returns:
            完整 SemanticPrediction
        """
        # 判断 prediction_status
        if primary.coarse_label == "unknown":
            prediction_status = "abstained"
            abstained = True
        elif primary.is_hard_evidence:
            prediction_status = "confirmed"
            abstained = False
        else:
            prediction_status = "candidate"
            abstained = False

        # evidence = (primary,) + tuple(alternatives)
        evidence_tuple = (primary,) + tuple(alternative_evidences)

        # alternatives 序列化为 dict 列表
        alternatives_tuple = tuple(
            self.resolver.serialize_evidence(e) for e in alternative_evidences
        )

        # direction 转为 Direction 枚举
        # profile.direction 可能是 "request"（值）或 "Direction.REQUEST"（str(枚举)）或空
        # 用 ALLOWED_DIRECTIONS 稳健查找，非法值降级为 UNKNOWN
        if profile.direction in ALLOWED_DIRECTIONS:
            direction = Direction(profile.direction)
        else:
            direction = Direction.UNKNOWN

        return SemanticPrediction(
            run_id=self.run_id,
            layout_id=profile.layout_id,
            direction=direction,
            field_index=profile.field_index,
            coarse_label=primary.coarse_label,
            fine_label=primary.fine_label,
            confidence=primary.score,
            abstained=abstained,
            evidence=evidence_tuple,
            alternatives=alternatives_tuple,
            prediction_status=prediction_status,
        )

    def detect_fields(
        self,
        profiles: List[FieldProfile]
    ) -> List[SemanticPrediction]:
        """对多个 FieldProfile 执行检测，返回 SemanticPrediction 列表

        R242：返回 List[SemanticPrediction] 而非 List[DetectorEvidence]。
        保持顺序：predictions[i] 对应 profiles[i]，FieldKey 一一对应。
        type/opcode 后处理用 dataclasses.replace 重建 frozen SemanticPrediction。

        Args:
            profiles: 字段画像列表

        Returns:
            SemanticPrediction 列表（顺序与 profiles 一致）
        """
        predictions: List[SemanticPrediction] = []

        # 第一阶段：对每个字段单独检测
        for profile in profiles:
            prediction = self.detect_field(profile)
            predictions.append(prediction)

        # 第二阶段：跨 layout type/opcode 后处理
        predictions = self._postprocess_type_opcode(profiles, predictions)

        return predictions

    def _rebuild_prediction_with_resolver(
        self,
        prediction: SemanticPrediction,
        new_primary: DetectorEvidence,
        new_alternatives: List[DetectorEvidence],
    ) -> SemanticPrediction:
        """R332: 用 Resolver 仲裁后的新 primary 和 alternatives 重建 SemanticPrediction

        保留身份字段（run_id/layout_id/direction/field_index），
        用 Resolver 仲裁结果替换 coarse_label/fine_label/confidence/abstained/
        prediction_status/evidence/alternatives。

        R332 HIGH-2 修复：Type/Opcode 证据不再直接替换 primary，而是与原字段
        全部 DetectorEvidence 一起送入 Resolver 仲裁。Resolver 负责冲突仲裁：
        - hard length/timestamp 优先于 soft type_control（hard 优先规则）
        - type_control 低于 min_score 时被过滤
        - type_control 胜出时，原 constant 等证据保留为 alternatives

        Args:
            prediction: 原 SemanticPrediction
            new_primary: Resolver 仲裁后的新 primary evidence
            new_alternatives: Resolver 仲裁后的新 alternatives 列表

        Returns:
            重建后的 SemanticPrediction
        """
        from dataclasses import replace

        if new_primary.coarse_label == "unknown":
            new_status = "abstained"
            new_abstained = True
        elif new_primary.is_hard_evidence:
            new_status = "confirmed"
            new_abstained = False
        else:
            new_status = "candidate"
            new_abstained = False

        new_evidence = (new_primary,) + tuple(new_alternatives)
        new_alternatives_tuple = tuple(
            self.resolver.serialize_evidence(e) for e in new_alternatives
        )

        return replace(
            prediction,
            coarse_label=new_primary.coarse_label,
            fine_label=new_primary.fine_label,
            confidence=new_primary.score,
            abstained=new_abstained,
            prediction_status=new_status,
            evidence=new_evidence,
            alternatives=new_alternatives_tuple,
        )

    def _postprocess_type_opcode(
        self,
        profiles: List[FieldProfile],
        predictions: List[SemanticPrediction]
    ) -> List[SemanticPrediction]:
        """跨 layout type/opcode 后处理

        R242：接收并返回 List[SemanticPrediction]。
        R332 HIGH-2 修复：Type/Opcode 证据不再直接替换 primary，而是与原字段
        全部 DetectorEvidence 一起送入 Resolver 仲裁。

        正确流程：
        原字段全部 DetectorEvidence + 跨 layout Type/Opcode DetectorEvidence
        → Resolver → 新 SemanticPrediction

        Resolver 负责冲突仲裁：
        - hard length/timestamp 优先于 soft type_control（hard 优先规则）
        - type_control 低于 min_score 时被过滤
        - type_control 胜出时，原 constant 等证据保留为 alternatives
        - prediction 的 run_id 和 FieldKey 不变

        Args:
            profiles: 字段画像列表
            predictions: SemanticPrediction 列表

        Returns:
            更新后的 SemanticPrediction 列表
        """
        # 按 TypeOpcodeAlignmentKey 分组（R328：用具名键替代裸 tuple）
        alignment_groups: Dict[TypeOpcodeAlignmentKey, List[Tuple[FieldProfile, int]]] = {}

        for i, profile in enumerate(profiles):
            # R328：使用唯一构造函数，不再手工拼 tuple
            key = build_type_opcode_alignment_key(profile)
            if key not in alignment_groups:
                alignment_groups[key] = []
            alignment_groups[key].append((profile, i))

        # 对每个对齐组检测 type/opcode
        for alignment_key, group in alignment_groups.items():
            if len(group) < 2:
                continue

            # 收集 layout_dominant_values 和 per_layout_dominant_ratios
            layout_dominant_values: Dict[str, bytes] = {}
            per_layout_dominant_ratios: Dict[str, float] = {}
            group_indices: List[int] = []

            for profile, idx in group:
                # R283: 使用 profile.dominant_value_hex（hex 字符串）转换为 bytes，
                # 替代 b'\x00' 占位符。
                # R403: 复用共享资格判断函数 is_type_opcode_profile_eligible，
                # 与 Detector 硬性条件 4 统一 >= 语义（修复 MEDIUM-1：原 > 严格大于
                # 在 ratio == threshold 时错误丢弃 profile）。
                # 共享函数内部检查：direction/field_index/sample_count/start_mode/
                # width_mode/dominant_value_hex/dominant_value_ratio（>= 阈值）。
                if is_type_opcode_profile_eligible(profile, self.config):
                    layout_dominant_values[profile.layout_id] = bytes.fromhex(
                        profile.dominant_value_hex
                    )
                    # R331: 收集 per_layout_dominant_ratios 供评分使用
                    per_layout_dominant_ratios[profile.layout_id] = profile.dominant_value_ratio
                    group_indices.append(idx)

            if len(layout_dominant_values) < 2:
                continue

            # 从 SemanticPrediction.evidence[0] 提取 primary evidence 传入 detect_type_or_opcode
            primary_evidences = [
                predictions[idx].evidence[0] if predictions[idx].evidence
                else self.resolver.create_unknown_prediction()
                for idx in group_indices
            ]

            # 调用 detect_type_or_opcode（R331: 传入 per_layout_dominant_ratios）
            # R358：min_dominant_ratio 从 config.type_opcode_min_dominant_ratio 传入
            evidence = detect_type_or_opcode(
                layout_dominant_values,
                alignment_key,
                primary_evidences,
                per_layout_dominant_ratios=per_layout_dominant_ratios,
                min_dominant_ratio=self.config.type_opcode_min_dominant_ratio,
            )

            if evidence is not None:
                # R332 HIGH-2 修复：Type/Opcode 证据重新进入 Resolver
                # 禁止后处理直接替换 SemanticPrediction
                # 正确流程：原字段全部 DetectorEvidence + 跨 layout Type/Opcode
                # DetectorEvidence → Resolver → 新 SemanticPrediction
                for idx in group_indices:
                    original_prediction = predictions[idx]
                    # 从 evidence 恢复原始候选列表（primary + alternatives）
                    original_candidates = list(original_prediction.evidence)
                    # 加入跨 layout type/opcode 证据
                    new_candidates = original_candidates + [evidence]
                    # 重新送入 Resolver 仲裁
                    new_primary, new_alternatives = self.resolver.resolve_with_context(
                        new_candidates
                    )
                    # 重建 SemanticPrediction，保留身份字段
                    predictions[idx] = self._rebuild_prediction_with_resolver(
                        original_prediction, new_primary, new_alternatives
                    )

        return predictions
    
    def generate_manifest(
        self,
        input_file: str,
        output_dir: str,
        profiles: List[FieldProfile],
        predictions: List,
        run_counts: RunCounts = None,
        run_info: RunManifestInfo = None,
    ) -> Dict:
        """生成运行 manifest

        R242 过渡兼容：接受 SemanticPrediction 或 DetectorEvidence 列表。
        如果是 SemanticPrediction，从 evidence[0] 提取 primary 的 is_hard_evidence。

        R349：接受 RunCounts 分阶段计数，停止使用 Prediction 数量冒充 validated_records。
        如果提供 run_counts，manifest["output"] 使用真实阶段计数；
        如果未提供（旧调用方），保持旧行为（向后兼容，但不应依赖）。

        R350：接受 RunManifestInfo 运行状态和退出信息。
        如果提供 run_info，manifest 顶层写入 7 个字段：
        status/exit_code/partial_input/valid_for_reporting/started_at/finished_at/command_args。
        如果未提供（旧调用方），保持旧行为（向后兼容，但不应依赖）。

        Args:
            input_file: 输入文件路径
            output_dir: 输出目录路径
            profiles: 字段画像列表
            predictions: 预测列表（SemanticPrediction 或 DetectorEvidence）
            run_counts: 分阶段 RunCounts（R348 数据模型），可选
            run_info: 运行状态和退出信息（R350 数据模型），可选

        Returns:
            manifest 字典
        """
        from datetime import datetime
        from pathlib import Path

        # R242 过渡层：从 SemanticPrediction 提取 primary 的 is_hard_evidence
        def _is_hard(p):
            if isinstance(p, SemanticPrediction):
                return p.evidence[0].is_hard_evidence if p.evidence else False
            return p.is_hard_evidence

        # R349：使用真实阶段计数（禁止 validated_records = len(predictions)）
        if run_counts is not None:
            output_section = {
                "directory": str(Path(output_dir).resolve()),
                "validated_records": run_counts.group_valid_records,
                "field_profiles": run_counts.field_profiles,
                "predictions": run_counts.predictions,
                "input_line_count": run_counts.input_line_count,
                "json_valid_records": run_counts.json_valid_records,
                "json_rejected_records": run_counts.json_rejected_records,
                "contract_valid_records": run_counts.contract_valid_records,
                "contract_rejected_records": run_counts.contract_rejected_records,
                "group_valid_records": run_counts.group_valid_records,
                "group_rejected_records": run_counts.group_rejected_records,
                # R422：组数 vs 消息数严格分开
                # group_rejection_count：冲突组数量；group_rejected_records：组内消息数
                "group_rejection_count": run_counts.group_rejection_count,
            }
        else:
            # 向后兼容（旧调用方未传 run_counts）
            output_section = {
                "directory": str(Path(output_dir).resolve()),
                "validated_records": len(profiles),
                "field_profiles": len(profiles),
                "predictions": len(predictions)
            }

        manifest = {
            "run_id": self.run_id,
            "timestamp": datetime.now().isoformat(),
            "input": {
                "file": str(Path(input_file).resolve()),
                "file_size": Path(input_file).stat().st_size if Path(input_file).exists() else 0
            },
            "output": output_section,
            "config": {
                "detectors": [d.name for d in self.detectors],
                "resolver": self.resolver.__class__.__name__,
                "resolved_config": self.config.to_dict(),
                "config_source": self.config_source,
                "config_sha256": self.config.sha256(),
            },
            "summary": {
                "hard_evidence_count": len([p for p in predictions if _is_hard(p)]),
                "soft_evidence_count": len([p for p in predictions if not _is_hard(p)]),
                "coarse_labels": [p.coarse_label for p in predictions if p.coarse_label]
            }
        }

        # R350：写入运行状态和退出信息（7 个字段）
        if run_info is not None:
            manifest["status"] = run_info.status
            manifest["exit_code"] = run_info.exit_code
            manifest["partial_input"] = run_info.partial_input
            manifest["valid_for_reporting"] = run_info.valid_for_reporting
            manifest["started_at"] = run_info.started_at
            manifest["finished_at"] = run_info.finished_at
            manifest["command_args"] = list(run_info.command_args)

        return manifest
