"""候选解析器

从多个检测器候选中选择最终预测。
"""

from dataclasses import replace
from typing import List, Tuple
from semantic_detector.contracts import DetectorEvidence
from semantic_detector.detectors.base import create_soft_evidence
from semantic_detector.taxonomy import normalize_legacy_label


class Resolver:
    """候选解析器
    
    从多个检测器候选中选择最终预测。
    """
    
    def __init__(self, min_score: float = 0.5, ambiguity_margin: float = 0.1):
        """初始化解析器
        
        Args:
            min_score: 最小分数阈值，低于此值的候选将被丢弃
            ambiguity_margin: 模糊边界，前两名分数差小于此值时拒识
        """
        if not 0.0 <= min_score <= 1.0:
            raise ValueError(f"min_score must be in [0, 1], got {min_score}")
        
        if not 0.0 <= ambiguity_margin <= 1.0:
            raise ValueError(f"ambiguity_margin must be in [0, 1], got {ambiguity_margin}")
        
        self.min_score = min_score
        self.ambiguity_margin = ambiguity_margin
    
    def filter_low_score_candidates(
        self,
        candidates: List[DetectorEvidence]
    ) -> List[DetectorEvidence]:
        """丢弃低阈值候选
        
        Args:
            candidates: 候选列表
            
        Returns:
            过滤后的候选列表（分数 >= min_score）
        """
        return [c for c in candidates if c.score >= self.min_score]
    
    def sort_candidates_by_score(
        self,
        candidates: List[DetectorEvidence]
    ) -> List[DetectorEvidence]:
        """按 score 降序排序，同分时保持稳定次序
        
        Args:
            candidates: 候选列表
            
        Returns:
            排序后的候选列表（分数降序，同分保持原顺序）
        """
        # 使用 enumerate 保持稳定排序
        # 按分数降序，同分时按原始索引升序（保持原顺序）
        indexed = list(enumerate(candidates))
        indexed.sort(key=lambda x: (-x[1].score, x[0]))
        return [c for _, c in indexed]
    
    def check_ambiguity(
        self,
        sorted_candidates: List[DetectorEvidence]
    ) -> bool:
        """检查是否存在模糊（前两名分数差 < margin）
        
        Args:
            sorted_candidates: 已排序的候选列表（降序）
            
        Returns:
            True 如果存在模糊（应拒识），False 如果清晰（可选择第一名）
        """
        # 少于 2 个候选，不存在模糊
        if len(sorted_candidates) < 2:
            return False
        
        # 计算前两名分数差
        top1_score = sorted_candidates[0].score
        top2_score = sorted_candidates[1].score
        score_diff = top1_score - top2_score
        
        # 分数差 < margin 时存在模糊
        return score_diff < self.ambiguity_margin
    
    def select_best_candidate(
        self,
        candidates: List[DetectorEvidence]
    ) -> DetectorEvidence | None:
        """选择最佳候选
        
        规则：
        1. hard evidence 优于 soft candidate
        2. 同类型按分数降序选择
        
        Args:
            candidates: 候选列表
            
        Returns:
            最佳候选，如果无候选则返回 None
        """
        if not candidates:
            return None
        
        # 分离 hard evidence 和 soft candidate
        hard_evidences = [c for c in candidates if c.is_hard_evidence]
        soft_candidates = [c for c in candidates if not c.is_hard_evidence]
        
        # hard evidence 优先
        if hard_evidences:
            # 按 score 降序选择最高分的 hard evidence
            sorted_hard = self.sort_candidates_by_score(hard_evidences)
            return sorted_hard[0]
        
        # 否则选择最高分的 soft candidate
        if soft_candidates:
            sorted_soft = self.sort_candidates_by_score(soft_candidates)
            return sorted_soft[0]
        
        return None
    
    def resolve_length_sequence_conflict(
        self,
        candidates: List[DetectorEvidence]
    ) -> Tuple[DetectorEvidence | None, DetectorEvidence | None]:
        """解决 length 与 sequence 冲突
        
        规则：
        1. 当 length 和 sequence 同时存在时，选择 length
        2. 保留 sequence 作为备选
        
        Args:
            candidates: 候选列表
            
        Returns:
            (主要候选, 备选候选)
        """
        if not candidates:
            return (None, None)
        
        # R287: 使用标准标签 sequence_or_counter（教程 7.2/11.1，旧字符串 "sequence" 无法匹配候选）
        # 分离 length 和 sequence_or_counter 候选
        length_candidates = [c for c in candidates if c.coarse_label == "length"]
        sequence_candidates = [c for c in candidates if c.coarse_label == "sequence_or_counter"]
        other_candidates = [c for c in candidates if c.coarse_label not in ("length", "sequence_or_counter")]
        
        # 如果同时存在 length 和 sequence
        if length_candidates and sequence_candidates:
            # 选择最高分的 length
            sorted_length = self.sort_candidates_by_score(length_candidates)
            primary = sorted_length[0]
            
            # 保留最高分的 sequence 作为备选
            sorted_sequence = self.sort_candidates_by_score(sequence_candidates)
            alternative = sorted_sequence[0]
            
            return (primary, alternative)
        
        # 如果只有 length
        if length_candidates:
            sorted_length = self.sort_candidates_by_score(length_candidates)
            return (sorted_length[0], None)
        
        # 如果只有 sequence
        if sequence_candidates:
            sorted_sequence = self.sort_candidates_by_score(sequence_candidates)
            return (sorted_sequence[0], None)
        
        # 其他候选
        if other_candidates:
            sorted_other = self.sort_candidates_by_score(other_candidates)
            return (sorted_other[0], None)
        
        return (None, None)
    
    def resolve_timestamp_sequence_conflict(
        self,
        candidates: List[DetectorEvidence]
    ) -> Tuple[DetectorEvidence | None, DetectorEvidence | None]:
        """解决 timestamp 与 sequence 冲突
        
        规则：
        1. 当 timestamp 和 sequence 同时存在时，选择 timestamp
        2. 保留 sequence 作为备选
        
        Args:
            candidates: 候选列表
            
        Returns:
            (主要候选, 备选候选)
        """
        if not candidates:
            return (None, None)
        
        # R287: 使用标准标签 sequence_or_counter（教程 7.2/11.1，旧字符串 "sequence" 无法匹配候选）
        # 分离 timestamp 和 sequence_or_counter 候选
        timestamp_candidates = [c for c in candidates if c.coarse_label == "timestamp"]
        sequence_candidates = [c for c in candidates if c.coarse_label == "sequence_or_counter"]
        other_candidates = [c for c in candidates if c.coarse_label not in ("timestamp", "sequence_or_counter")]
        
        # 如果同时存在 timestamp 和 sequence
        if timestamp_candidates and sequence_candidates:
            # 选择最高分的 timestamp
            sorted_timestamp = self.sort_candidates_by_score(timestamp_candidates)
            primary = sorted_timestamp[0]
            
            # 保留最高分的 sequence 作为备选
            sorted_sequence = self.sort_candidates_by_score(sequence_candidates)
            alternative = sorted_sequence[0]
            
            return (primary, alternative)
        
        # 如果只有 timestamp
        if timestamp_candidates:
            sorted_timestamp = self.sort_candidates_by_score(timestamp_candidates)
            return (sorted_timestamp[0], None)
        
        # 如果只有 sequence
        if sequence_candidates:
            sorted_sequence = self.sort_candidates_by_score(sequence_candidates)
            return (sorted_sequence[0], None)
        
        # 其他候选
        if other_candidates:
            sorted_other = self.sort_candidates_by_score(other_candidates)
            return (sorted_other[0], None)
        
        return (None, None)
    
    def resolve_constant_string_conflict(
        self,
        candidates: List[DetectorEvidence],
        field_width: int = 1,
        printable_ratio: float = 0.0
    ) -> Tuple[DetectorEvidence | None, DetectorEvidence | None]:
        """解决 constant 与 string 冲突
        
        规则：
        1. 当 constant 和 string 同时存在时，按宽度和 printable 选择
        2. 如果宽度 > 1 且 printable_ratio >= 0.85，选择 string
        3. 否则选择 constant
        
        Args:
            candidates: 候选列表
            field_width: 字段宽度
            printable_ratio: 可打印字符比例
            
        Returns:
            (主要候选, 备选候选)
        """
        if not candidates:
            return (None, None)
        
        # 分离 constant 和 string 候选
        constant_candidates = [c for c in candidates if c.coarse_label == "constant"]
        string_candidates = [c for c in candidates if c.coarse_label == "string"]
        other_candidates = [c for c in candidates if c.coarse_label not in ("constant", "string")]
        
        # 如果同时存在 constant 和 string
        if constant_candidates and string_candidates:
            # 如果宽度 > 1 且 printable_ratio >= 0.85，选择 string
            if field_width > 1 and printable_ratio >= 0.85:
                sorted_string = self.sort_candidates_by_score(string_candidates)
                primary = sorted_string[0]
                
                sorted_constant = self.sort_candidates_by_score(constant_candidates)
                alternative = sorted_constant[0]
                
                return (primary, alternative)
            else:
                # 否则选择 constant
                sorted_constant = self.sort_candidates_by_score(constant_candidates)
                primary = sorted_constant[0]
                
                sorted_string = self.sort_candidates_by_score(string_candidates)
                alternative = sorted_string[0]
                
                return (primary, alternative)
        
        # 如果只有 constant
        if constant_candidates:
            sorted_constant = self.sort_candidates_by_score(constant_candidates)
            return (sorted_constant[0], None)
        
        # 如果只有 string
        if string_candidates:
            sorted_string = self.sort_candidates_by_score(string_candidates)
            return (sorted_string[0], None)
        
        # 其他候选
        if other_candidates:
            sorted_other = self.sort_candidates_by_score(other_candidates)
            return (sorted_other[0], None)

        return (None, None)

    def resolve_constant_type_opcode_conflict(
        self,
        candidates: List[DetectorEvidence],
    ) -> Tuple[DetectorEvidence | None, DetectorEvidence | None]:
        """R332: 解决 constant 与 type_control 冲突

        规则：
        1. 当 constant 和 type_control 同时存在时，type_control 胜出
           （跨 layout 一一对应映射比单 layout 内常量更具语义信息）
        2. constant 保留为 alternative（作为"单 layout 内稳定"的支持证据）
        3. 如果存在 hard length/timestamp 证据，不触发本规则
           （type_control 不得覆盖强 length/timestamp）

        教程 10.5：type/opcode 检测是跨 layout 对齐后的语义判断，
        比"单 layout 内值不变"的 constant 更具体。一个在各 layout 内都恒定、
        但跨 layout 呈一一对应映射的字段，语义上是 type/opcode 而非常量。

        Args:
            candidates: 候选列表

        Returns:
            (主要候选, 备选候选)
        """
        if not candidates:
            return (None, None)

        # 检查是否存在 hard length/timestamp 证据
        # type_control 不得覆盖强 length/timestamp（验收规则）
        has_hard_length_or_timestamp = any(
            c.is_hard_evidence and c.coarse_label in ("length", "timestamp")
            for c in candidates
        )
        if has_hard_length_or_timestamp:
            return (None, None)

        constant_candidates = [c for c in candidates if c.coarse_label == "constant"]
        type_control_candidates = [c for c in candidates if c.coarse_label == "type_control"]

        if constant_candidates and type_control_candidates:
            sorted_type_control = self.sort_candidates_by_score(type_control_candidates)
            primary = sorted_type_control[0]

            sorted_constant = self.sort_candidates_by_score(constant_candidates)
            alternative = sorted_constant[0]

            return (primary, alternative)

        return (None, None)

    def create_unknown_prediction(
        self,
        reason_code: str = "no_candidates"
    ) -> DetectorEvidence:
        """创建 unknown 预测
        
        当无候选或拒识时，返回 unknown 预测。
        
        Args:
            reason_code: 原因代码
            
        Returns:
            unknown 预测证据
        """
        return create_soft_evidence(
            detector="resolver",
            coarse_label="unknown",
            fine_label="unknown",
            score=0.0,
            reason_code=reason_code,
            details={
                "abstained": True
            }
        )
    
    def resolve(
        self,
        candidates: List[DetectorEvidence]
    ) -> DetectorEvidence:
        """解析候选列表，返回最终预测

        Args:
            candidates: 候选列表

        Returns:
            最终预测（如果无候选则返回 unknown）
        """
        if not candidates:
            return self.create_unknown_prediction(reason_code="no_candidates")

        # 过滤低分候选
        filtered = self.filter_low_score_candidates(candidates)

        if not filtered:
            return self.create_unknown_prediction(reason_code="all_below_threshold")

        # 排序
        sorted_candidates = self.sort_candidates_by_score(filtered)

        # 检查模糊
        if self.check_ambiguity(sorted_candidates):
            return self.create_unknown_prediction(reason_code="ambiguous")

        # 选择最佳候选
        best = self.select_best_candidate(sorted_candidates)

        if best is None:
            return self.create_unknown_prediction(reason_code="no_valid_candidate")

        return best

    def resolve_with_context(
        self,
        candidates: List[DetectorEvidence]
    ) -> Tuple[DetectorEvidence, List[DetectorEvidence]]:
        """解析候选列表，返回主要预测和备选列表

        R240：为 Pipeline 包装 SemanticPrediction 提供上下文。
        与 resolve() 的区别：
        - resolve() 只返回单个最佳候选（或 unknown）
        - resolve_with_context() 额外返回 alternatives，供下游 SemanticPrediction
          包装 confirmed/candidate/abstained 状态

        R288：接入 length-vs-sequence 专项冲突规则（教程 11.3/11.4）。
        在 ambiguity 检查之前执行冲突规则，避免 length=1.0/sequence=1.0
        直接返回 unknown(ambiguous) 导致领域规则失效。

        R289：接入 timestamp-vs-sequence 专项冲突规则（教程 11.3/11.4）。
        在 length-vs-sequence 之后、ambiguity 之前执行，确保时间自然递增的
        timestamp 证据胜出，sequence_or_counter 保留为 alternative。

        R290：接入 constant-vs-string 专项冲突规则（教程 11.3）。
        在 timestamp-vs-sequence 之后、ambiguity 之前执行，按宽度/printable
        选择：宽度 > 1 且 printable_ratio >= 0.85 → string 胜出，否则 constant 胜出。
        width 和 printable_ratio 从 string 候选的 details 提取（StringDetector 已写入）。

        R291：调整 hard 优先和 ambiguity 顺序（教程 11.2 第 5 步 / 11.4）。
        在专项冲突规则之后、ambiguity 之前执行 hard 优先：如果有 hard evidence，
        直接选最高分 hard evidence，不走 ambiguity。这避免 hard 0.8 vs soft 0.95
        时因分数接近而误判为 ambiguous。ambiguity 只在只有 soft 候选时才检查。

        拒识语义（与 resolve() 一致）：
        - 无候选 -> primary=unknown(no_candidates), alternatives=[]
        - 全部低于阈值 -> primary=unknown(all_below_threshold), alternatives=[]
        - 模糊（前两名差 < margin）-> primary=unknown(ambiguous), alternatives=排序后候选
        - 正常 -> primary=最佳候选, alternatives=排除 primary 后的剩余候选（按分数降序）

        不破坏现有 resolve() 兼容行为：当 alternatives 为空且 primary 非 unknown 时，
        primary 与 resolve(candidates) 返回值等价。

        Args:
            candidates: 候选列表

        Returns:
            (primary, alternatives)
            - primary: 主要预测（DetectorEvidence），无候选或拒识时返回 unknown
            - alternatives: 备选候选列表（List[DetectorEvidence]），按分数降序，
              已排除 primary。模糊时保留排序候选供下游判断。
        """
        if not candidates:
            return (self.create_unknown_prediction(reason_code="no_candidates"), [])

        # 教程 11.2 第 2 步：删除 abstain 证据（显式步骤，不依赖 min_score 隐式过滤）
        # abstain 证据特征：coarse_label="unknown" 且 is_hard_evidence=False
        # （check_min_samples 返回的 insufficient_samples 证据）
        # 这样即使 min_score=0.0，abstain 证据也不会污染后续流程
        non_abstain = [
            c for c in candidates
            if not (c.coarse_label == "unknown" and not c.is_hard_evidence)
        ]

        if not non_abstain:
            return (self.create_unknown_prediction(reason_code="all_abstained"), [])

        # 教程 11.2 第 3 步：规范化旧标签（兼容历史产物）
        # 将旧标签（如 "sequence"/"type_opcode"/"opaque_payload"）映射为标准标签
        # 这样三个专项冲突规则才能正确匹配标准标签
        normalized = []
        for c in non_abstain:
            norm_label = normalize_legacy_label(c.coarse_label)
            if norm_label != c.coarse_label:
                # 重建 DetectorEvidence（frozen dataclass，用 replace）
                c = replace(c, coarse_label=norm_label)
            normalized.append(c)

        # 过滤低分候选
        filtered = self.filter_low_score_candidates(normalized)

        if not filtered:
            return (self.create_unknown_prediction(reason_code="all_below_threshold"), [])

        # 排序
        sorted_candidates = self.sort_candidates_by_score(filtered)

        # R288: 执行 length-vs-sequence 专项冲突规则（教程 11.3/11.4）
        # 在 ambiguity 检查之前，避免 length=1.0/sequence=1.0 直接 unknown
        # 教程 11.3：若长度证据来自真实等式/固定偏移支持率，length 胜出，
        # sequence_or_counter 保留为 alternative
        has_length = any(c.coarse_label == "length" for c in sorted_candidates)
        has_sequence = any(c.coarse_label == "sequence_or_counter" for c in sorted_candidates)
        if has_length and has_sequence:
            primary, _alt = self.resolve_length_sequence_conflict(sorted_candidates)
            if primary is not None:
                # alternatives：排除 primary，保留其余候选（按分数降序）
                # sequence_or_counter 候选已在 sorted_candidates 中，会被包含在 alternatives 中
                alternatives = [c for c in sorted_candidates if c is not primary]
                return (primary, alternatives)

        # R289: 执行 timestamp-vs-sequence 专项冲突规则（教程 11.3/11.4）
        # 在 ambiguity 检查之前，避免 timestamp=1.0/sequence=1.0 直接 unknown
        # 教程 11.3：时间自然递增的 timestamp 证据胜出，
        # sequence_or_counter 保留为 alternative
        # 注意：length-vs-sequence 已先于本分支处理，此处不会再同时出现 length 与 sequence
        has_timestamp = any(c.coarse_label == "timestamp" for c in sorted_candidates)
        if has_timestamp and has_sequence:
            primary, _alt = self.resolve_timestamp_sequence_conflict(sorted_candidates)
            if primary is not None:
                # alternatives：排除 primary，保留其余候选（按分数降序）
                # sequence_or_counter 候选已在 sorted_candidates 中，会被包含在 alternatives 中
                alternatives = [c for c in sorted_candidates if c is not primary]
                return (primary, alternatives)

        # R332: 执行 constant-vs-type_control 专项冲突规则
        # 在 constant-vs-string 之前、hard 优先之前执行
        # 教程 10.5：跨 layout type/opcode 比单 layout 内常量更具语义信息
        # type_control 胜出时 constant 保留为 alternative（"单 layout 内稳定"支持证据）
        # 但 type_control 不得覆盖强 length/timestamp（规则内部检查）
        has_constant = any(c.coarse_label == "constant" for c in sorted_candidates)
        has_type_control = any(c.coarse_label == "type_control" for c in sorted_candidates)
        if has_constant and has_type_control:
            primary, _alt = self.resolve_constant_type_opcode_conflict(sorted_candidates)
            if primary is not None:
                alternatives = [c for c in sorted_candidates if c is not primary]
                return (primary, alternatives)

        # R290: 执行 constant-vs-string 专项冲突规则（教程 11.3）
        # 在 ambiguity 检查之前，避免 constant=1.0/string=1.0 直接 unknown
        # 教程 11.3：固定 ASCII 字段，按宽度/printable 选择
        # - 宽度 > 1 且 printable_ratio >= 0.85 → string 胜出，constant 进 alternative
        # - 否则 constant 胜出，string 进 alternative
        # width 和 printable_ratio 从 string 候选的 details 提取（StringDetector 已写入）
        has_constant = any(c.coarse_label == "constant" for c in sorted_candidates)
        has_string = any(c.coarse_label == "string" for c in sorted_candidates)
        if has_constant and has_string:
            string_candidate = next(c for c in sorted_candidates if c.coarse_label == "string")
            string_details = string_candidate.details or {}
            field_width = string_details.get("byte_width", 1)
            printable_ratio = string_details.get("printable_ascii_ratio", 0.0)
            primary, _alt = self.resolve_constant_string_conflict(
                sorted_candidates,
                field_width=field_width,
                printable_ratio=printable_ratio
            )
            if primary is not None:
                alternatives = [c for c in sorted_candidates if c is not primary]
                return (primary, alternatives)

        # R291: hard 优先（教程 11.2 第 5 步 / 11.4）
        # 专项冲突规则已先于本分支处理（R288/R289/R290）
        # 如果有 hard evidence，直接选最高分 hard evidence，不走 ambiguity
        # 这避免 hard 0.8 vs soft 0.95 时因分数接近而误判为 ambiguous
        # 教程 11.2：hard 优先（第 5 步）先于 ambiguity_margin（第 7 步）
        hard_evidences = [c for c in sorted_candidates if c.is_hard_evidence]
        if hard_evidences:
            sorted_hard = self.sort_candidates_by_score(hard_evidences)
            best = sorted_hard[0]
            alternatives = [c for c in sorted_candidates if c is not best]
            return (best, alternatives)

        # 检查模糊：只有 soft 候选时才检查（hard 优先已在上方处理）
        # primary 返回 unknown，但 alternatives 保留排序候选
        if self.check_ambiguity(sorted_candidates):
            primary = self.create_unknown_prediction(reason_code="ambiguous")
            return (primary, sorted_candidates)

        # 选择最佳候选（此时只剩 soft 候选，select_best_candidate 走 soft 分支）
        best = self.select_best_candidate(sorted_candidates)

        if best is None:
            primary = self.create_unknown_prediction(reason_code="no_valid_candidate")
            return (primary, sorted_candidates)

        # alternatives 排除 best（按对象身份，frozen dataclass 不可变）
        alternatives = [c for c in sorted_candidates if c is not best]

        return (best, alternatives)
    
    def serialize_evidence(
        self,
        evidence: DetectorEvidence
    ) -> dict:
        """将证据序列化为 JSON-safe 字典
        
        Args:
            evidence: 证据对象
            
        Returns:
            JSON-safe 字典
        """
        return {
            "detector": evidence.detector,
            "coarse_label": evidence.coarse_label,
            "fine_label": evidence.fine_label,
            "is_hard_evidence": evidence.is_hard_evidence,
            "score": evidence.score,
            "reason_code": evidence.reason_code,
            "details": evidence.details
        }
    
    def serialize_evidences(
        self,
        evidences: List[DetectorEvidence]
    ) -> List[dict]:
        """将证据列表序列化为 JSON-safe 列表
        
        Args:
            evidences: 证据列表
            
        Returns:
            JSON-safe 列表
        """
        return [self.serialize_evidence(e) for e in evidences]
    
    def resolve_with_candidates(
        self,
        candidates: List[DetectorEvidence]
    ) -> Tuple[DetectorEvidence, List[dict]]:
        """解析候选列表，返回最终预测和所有候选

        R292：保留全部候选和稳定 alternatives 顺序（教程 11.2 第 9 步）。
        使用 resolve_with_context 获取 (primary, alternatives)，
        候选列表 = [primary] + alternatives（按分数降序，primary 在第一位）。
        当 primary 是 unknown（无候选/拒识）时，候选列表 = alternatives
        （unknown 不混入候选列表，但保留排序候选供审计）。

        顺序确定性：
        - alternatives 来自 sorted_candidates（sort_candidates_by_score 降序，同分保持原顺序）
        - primary 在第一位（当非 unknown），其余按分数降序
        - 同分候选保持输入顺序（稳定排序）

        Args:
            candidates: 候选列表

        Returns:
            (最终预测, 序列化的候选列表)
            - 最终预测：DetectorEvidence，无候选或拒识时返回 unknown
            - 序列化的候选列表：按分数降序，primary 在第一位（当非 unknown）
        """
        primary, alternatives = self.resolve_with_context(candidates)

        # 保留全部候选，按分数降序，顺序确定
        # - primary 非 unknown：候选列表 = [primary] + alternatives（primary 在第一位）
        # - primary 是 unknown：候选列表 = alternatives（unknown 不混入候选列表）
        if primary.coarse_label == "unknown":
            all_candidates = alternatives
        else:
            all_candidates = [primary] + alternatives

        serialized_candidates = self.serialize_evidences(all_candidates)

        return (primary, serialized_candidates)
