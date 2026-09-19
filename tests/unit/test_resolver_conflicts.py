"""测试候选解析器冲突解决"""

import pytest
from semantic_detector.scoring.resolver import Resolver
from semantic_detector.contracts import DetectorEvidence


class TestResolveLengthSequenceConflict:
    """测试 length 与 sequence 冲突解决"""
    
    def test_length_over_sequence(self):
        """length 优于 sequence"""
        resolver = Resolver()
        
        candidates = [
            DetectorEvidence(
                detector="length",
                coarse_label="length",
                fine_label="length_of_next_field",
                is_hard_evidence=True,
                score=0.85,
                reason_code="test",
                details={}
            ),
            DetectorEvidence(
                detector="sequence",
                coarse_label="sequence_or_counter",
                fine_label="sequence_or_counter",
                is_hard_evidence=True,
                score=0.95,
                reason_code="test",
                details={}
            )
        ]
        
        primary, alternative = resolver.resolve_length_sequence_conflict(candidates)
        
        # 即使 sequence 分数更高，也选择 length
        assert primary is not None
        assert primary.coarse_label == "length"
        assert alternative is not None
        assert alternative.coarse_label == "sequence_or_counter"
    
    def test_length_only(self):
        """只有 length 候选"""
        resolver = Resolver()
        
        candidates = [
            DetectorEvidence(
                detector="length",
                coarse_label="length",
                fine_label="length_of_next_field",
                is_hard_evidence=True,
                score=0.90,
                reason_code="test",
                details={}
            )
        ]
        
        primary, alternative = resolver.resolve_length_sequence_conflict(candidates)
        
        assert primary is not None
        assert primary.coarse_label == "length"
        assert alternative is None
    
    def test_sequence_only(self):
        """只有 sequence 候选"""
        resolver = Resolver()
        
        candidates = [
            DetectorEvidence(
                detector="sequence",
                coarse_label="sequence_or_counter",
                fine_label="sequence_or_counter",
                is_hard_evidence=True,
                score=0.90,
                reason_code="test",
                details={}
            )
        ]
        
        primary, alternative = resolver.resolve_length_sequence_conflict(candidates)
        
        assert primary is not None
        assert primary.coarse_label == "sequence_or_counter"
        assert alternative is None
    
    def test_multiple_length_candidates(self):
        """多个 length 候选时选择最高分"""
        resolver = Resolver()
        
        candidates = [
            DetectorEvidence(
                detector="length",
                coarse_label="length",
                fine_label="length_of_next_field",
                is_hard_evidence=True,
                score=0.80,
                reason_code="test",
                details={}
            ),
            DetectorEvidence(
                detector="length",
                coarse_label="length",
                fine_label="length_of_remaining",
                is_hard_evidence=True,
                score=0.95,
                reason_code="test",
                details={}
            ),
            DetectorEvidence(
                detector="sequence",
                coarse_label="sequence_or_counter",
                fine_label="sequence_or_counter",
                is_hard_evidence=True,
                score=0.85,
                reason_code="test",
                details={}
            )
        ]
        
        primary, alternative = resolver.resolve_length_sequence_conflict(candidates)
        
        assert primary is not None
        assert primary.coarse_label == "length"
        assert primary.score == 0.95
        assert alternative is not None
        assert alternative.coarse_label == "sequence_or_counter"
    
    def test_multiple_sequence_candidates(self):
        """多个 sequence 候选时保留最高分作为备选"""
        resolver = Resolver()
        
        candidates = [
            DetectorEvidence(
                detector="length",
                coarse_label="length",
                fine_label="length_of_next_field",
                is_hard_evidence=True,
                score=0.90,
                reason_code="test",
                details={}
            ),
            DetectorEvidence(
                detector="sequence",
                coarse_label="sequence_or_counter",
                fine_label="sequence_or_counter_be",
                is_hard_evidence=True,
                score=0.80,
                reason_code="test",
                details={}
            ),
            DetectorEvidence(
                detector="sequence",
                coarse_label="sequence_or_counter",
                fine_label="sequence_or_counter_le",
                is_hard_evidence=True,
                score=0.95,
                reason_code="test",
                details={}
            )
        ]
        
        primary, alternative = resolver.resolve_length_sequence_conflict(candidates)
        
        assert primary is not None
        assert primary.coarse_label == "length"
        assert alternative is not None
        assert alternative.coarse_label == "sequence_or_counter"
        assert alternative.score == 0.95
    
    def test_other_candidates_only(self):
        """只有其他候选时选择最高分"""
        resolver = Resolver()
        
        candidates = [
            DetectorEvidence(
                detector="timestamp",
                coarse_label="timestamp",
                fine_label="unix_seconds",
                is_hard_evidence=True,
                score=0.85,
                reason_code="test",
                details={}
            ),
            DetectorEvidence(
                detector="constant",
                coarse_label="constant",
                fine_label="constant_value",
                is_hard_evidence=True,
                score=0.90,
                reason_code="test",
                details={}
            )
        ]
        
        primary, alternative = resolver.resolve_length_sequence_conflict(candidates)
        
        assert primary is not None
        assert primary.coarse_label == "constant"
        assert alternative is None
    
    def test_empty_candidates(self):
        """空候选列表返回 (None, None)"""
        resolver = Resolver()
        
        primary, alternative = resolver.resolve_length_sequence_conflict([])
        
        assert primary is None
        assert alternative is None


class TestResolveTimestampSequenceConflict:
    """测试 timestamp 与 sequence 冲突解决"""
    
    def test_timestamp_over_sequence(self):
        """timestamp 优于 sequence"""
        resolver = Resolver()
        
        candidates = [
            DetectorEvidence(
                detector="timestamp",
                coarse_label="timestamp",
                fine_label="unix_seconds",
                is_hard_evidence=True,
                score=0.85,
                reason_code="test",
                details={}
            ),
            DetectorEvidence(
                detector="sequence",
                coarse_label="sequence_or_counter",
                fine_label="sequence_or_counter",
                is_hard_evidence=True,
                score=0.95,
                reason_code="test",
                details={}
            )
        ]
        
        primary, alternative = resolver.resolve_timestamp_sequence_conflict(candidates)
        
        # 即使 sequence 分数更高，也选择 timestamp
        assert primary is not None
        assert primary.coarse_label == "timestamp"
        assert alternative is not None
        assert alternative.coarse_label == "sequence_or_counter"
    
    def test_timestamp_only(self):
        """只有 timestamp 候选"""
        resolver = Resolver()
        
        candidates = [
            DetectorEvidence(
                detector="timestamp",
                coarse_label="timestamp",
                fine_label="unix_seconds",
                is_hard_evidence=True,
                score=0.90,
                reason_code="test",
                details={}
            )
        ]
        
        primary, alternative = resolver.resolve_timestamp_sequence_conflict(candidates)
        
        assert primary is not None
        assert primary.coarse_label == "timestamp"
        assert alternative is None
    
    def test_sequence_only(self):
        """只有 sequence 候选"""
        resolver = Resolver()
        
        candidates = [
            DetectorEvidence(
                detector="sequence",
                coarse_label="sequence_or_counter",
                fine_label="sequence_or_counter",
                is_hard_evidence=True,
                score=0.90,
                reason_code="test",
                details={}
            )
        ]
        
        primary, alternative = resolver.resolve_timestamp_sequence_conflict(candidates)
        
        assert primary is not None
        assert primary.coarse_label == "sequence_or_counter"
        assert alternative is None
    
    def test_multiple_timestamp_candidates(self):
        """多个 timestamp 候选时选择最高分"""
        resolver = Resolver()
        
        candidates = [
            DetectorEvidence(
                detector="timestamp",
                coarse_label="timestamp",
                fine_label="unix_seconds",
                is_hard_evidence=True,
                score=0.80,
                reason_code="test",
                details={}
            ),
            DetectorEvidence(
                detector="timestamp",
                coarse_label="timestamp",
                fine_label="unix_milliseconds",
                is_hard_evidence=True,
                score=0.95,
                reason_code="test",
                details={}
            ),
            DetectorEvidence(
                detector="sequence",
                coarse_label="sequence_or_counter",
                fine_label="sequence_or_counter",
                is_hard_evidence=True,
                score=0.85,
                reason_code="test",
                details={}
            )
        ]
        
        primary, alternative = resolver.resolve_timestamp_sequence_conflict(candidates)
        
        assert primary is not None
        assert primary.coarse_label == "timestamp"
        assert primary.score == 0.95
        assert alternative is not None
        assert alternative.coarse_label == "sequence_or_counter"
    
    def test_other_candidates_only(self):
        """只有其他候选时选择最高分"""
        resolver = Resolver()
        
        candidates = [
            DetectorEvidence(
                detector="length",
                coarse_label="length",
                fine_label="length_of_next_field",
                is_hard_evidence=True,
                score=0.85,
                reason_code="test",
                details={}
            ),
            DetectorEvidence(
                detector="constant",
                coarse_label="constant",
                fine_label="constant_value",
                is_hard_evidence=True,
                score=0.90,
                reason_code="test",
                details={}
            )
        ]
        
        primary, alternative = resolver.resolve_timestamp_sequence_conflict(candidates)
        
        assert primary is not None
        assert primary.coarse_label == "constant"
        assert alternative is None
    
    def test_empty_candidates(self):
        """空候选列表返回 (None, None)"""
        resolver = Resolver()
        
        primary, alternative = resolver.resolve_timestamp_sequence_conflict([])
        
        assert primary is None
        assert alternative is None


class TestResolveConstantStringConflict:
    """测试 constant 与 string 冲突解决"""
    
    def test_string_over_constant_when_wide_and_printable(self):
        """宽度 > 1 且 printable 时选择 string"""
        resolver = Resolver()
        
        candidates = [
            DetectorEvidence(
                detector="constant",
                coarse_label="constant",
                fine_label="constant_value",
                is_hard_evidence=True,
                score=0.95,
                reason_code="test",
                details={}
            ),
            DetectorEvidence(
                detector="string",
                coarse_label="string",
                fine_label="ascii_string",
                is_hard_evidence=True,
                score=0.85,
                reason_code="test",
                details={}
            )
        ]
        
        # 宽度 > 1 且 printable_ratio >= 0.85
        primary, alternative = resolver.resolve_constant_string_conflict(
            candidates,
            field_width=8,
            printable_ratio=0.90
        )
        
        # 即使 constant 分数更高，也选择 string
        assert primary is not None
        assert primary.coarse_label == "string"
        assert alternative is not None
        assert alternative.coarse_label == "constant"
    
    def test_constant_over_string_when_narrow(self):
        """宽度 = 1 时选择 constant"""
        resolver = Resolver()
        
        candidates = [
            DetectorEvidence(
                detector="constant",
                coarse_label="constant",
                fine_label="constant_value",
                is_hard_evidence=True,
                score=0.85,
                reason_code="test",
                details={}
            ),
            DetectorEvidence(
                detector="string",
                coarse_label="string",
                fine_label="ascii_string",
                is_hard_evidence=True,
                score=0.95,
                reason_code="test",
                details={}
            )
        ]
        
        # 宽度 = 1
        primary, alternative = resolver.resolve_constant_string_conflict(
            candidates,
            field_width=1,
            printable_ratio=0.90
        )
        
        # 选择 constant
        assert primary is not None
        assert primary.coarse_label == "constant"
        assert alternative is not None
        assert alternative.coarse_label == "string"
    
    def test_constant_over_string_when_low_printable(self):
        """printable_ratio < 0.85 时选择 constant"""
        resolver = Resolver()
        
        candidates = [
            DetectorEvidence(
                detector="constant",
                coarse_label="constant",
                fine_label="constant_value",
                is_hard_evidence=True,
                score=0.85,
                reason_code="test",
                details={}
            ),
            DetectorEvidence(
                detector="string",
                coarse_label="string",
                fine_label="ascii_string",
                is_hard_evidence=True,
                score=0.95,
                reason_code="test",
                details={}
            )
        ]
        
        # printable_ratio < 0.85
        primary, alternative = resolver.resolve_constant_string_conflict(
            candidates,
            field_width=8,
            printable_ratio=0.80
        )
        
        # 选择 constant
        assert primary is not None
        assert primary.coarse_label == "constant"
        assert alternative is not None
        assert alternative.coarse_label == "string"
    
    def test_constant_only(self):
        """只有 constant 候选"""
        resolver = Resolver()
        
        candidates = [
            DetectorEvidence(
                detector="constant",
                coarse_label="constant",
                fine_label="constant_value",
                is_hard_evidence=True,
                score=0.90,
                reason_code="test",
                details={}
            )
        ]
        
        primary, alternative = resolver.resolve_constant_string_conflict(candidates)
        
        assert primary is not None
        assert primary.coarse_label == "constant"
        assert alternative is None
    
    def test_string_only(self):
        """只有 string 候选"""
        resolver = Resolver()
        
        candidates = [
            DetectorEvidence(
                detector="string",
                coarse_label="string",
                fine_label="ascii_string",
                is_hard_evidence=True,
                score=0.90,
                reason_code="test",
                details={}
            )
        ]
        
        primary, alternative = resolver.resolve_constant_string_conflict(candidates)
        
        assert primary is not None
        assert primary.coarse_label == "string"
        assert alternative is None
    
    def test_other_candidates_only(self):
        """只有其他候选时选择最高分"""
        resolver = Resolver()
        
        candidates = [
            DetectorEvidence(
                detector="length",
                coarse_label="length",
                fine_label="length_of_next_field",
                is_hard_evidence=True,
                score=0.85,
                reason_code="test",
                details={}
            ),
            DetectorEvidence(
                detector="timestamp",
                coarse_label="timestamp",
                fine_label="unix_seconds",
                is_hard_evidence=True,
                score=0.90,
                reason_code="test",
                details={}
            )
        ]
        
        primary, alternative = resolver.resolve_constant_string_conflict(candidates)
        
        assert primary is not None
        assert primary.coarse_label == "timestamp"
        assert alternative is None
    
    def test_empty_candidates(self):
        """空候选列表返回 (None, None)"""
        resolver = Resolver()

        primary, alternative = resolver.resolve_constant_string_conflict([])

        assert primary is None
        assert alternative is None


class TestResolverR287:
    """R287: 修正 Resolver 所有旧 sequence 标签为 sequence_or_counter

    04 任务表 R287：
    "修正 Resolver 所有旧 sequence 标签为 sequence_or_counter |
     scoring/resolver.py; test_resolver_conflicts.py | 标签测试 | 冲突函数能找到序列候选"

    教程 11.1：代码虽定义了 resolve_length_sequence_conflict /
    resolve_timestamp_sequence_conflict，但检查标签时还使用了旧字符串 "sequence"，
    导致 sequence_or_counter 候选无法被找到。

    R287 完成标准：冲突函数能找到 sequence_or_counter 候选。
    """

    def _make_sequence_candidate(self, score=0.95, hard=True):
        """构造 sequence_or_counter 候选（R239 标准标签）"""
        return DetectorEvidence(
            detector="sequence",
            coarse_label="sequence_or_counter",
            fine_label="monotonic_counter",
            is_hard_evidence=hard,
            score=score,
            reason_code="test",
            details={}
        )

    def _make_length_candidate(self, score=0.85, hard=True):
        return DetectorEvidence(
            detector="length",
            coarse_label="length",
            fine_label="length_of_next_field",
            is_hard_evidence=hard,
            score=score,
            reason_code="test",
            details={}
        )

    def _make_timestamp_candidate(self, score=0.90, hard=True):
        return DetectorEvidence(
            detector="timestamp",
            coarse_label="timestamp",
            fine_label="unix_seconds_be",
            is_hard_evidence=hard,
            score=score,
            reason_code="test",
            details={}
        )

    def test_length_sequence_conflict_finds_sequence_or_counter(self):
        """R287 完成标准：resolve_length_sequence_conflict 能找到 sequence_or_counter 候选

        修复前：coarse_label == "sequence" 无法匹配 "sequence_or_counter"，
        sequence_candidates 为空，冲突规则失效。
        修复后：coarse_label == "sequence_or_counter" 正确匹配。
        """
        resolver = Resolver()
        candidates = [
            self._make_length_candidate(score=0.85),
            self._make_sequence_candidate(score=0.95),
        ]

        primary, alternative = resolver.resolve_length_sequence_conflict(candidates)

        assert primary is not None
        assert primary.coarse_label == "length"
        assert alternative is not None
        assert alternative.coarse_label == "sequence_or_counter"

    def test_timestamp_sequence_conflict_finds_sequence_or_counter(self):
        """R287 完成标准：resolve_timestamp_sequence_conflict 能找到 sequence_or_counter 候选"""
        resolver = Resolver()
        candidates = [
            self._make_timestamp_candidate(score=0.90),
            self._make_sequence_candidate(score=0.95),
        ]

        primary, alternative = resolver.resolve_timestamp_sequence_conflict(candidates)

        assert primary is not None
        assert primary.coarse_label == "timestamp"
        assert alternative is not None
        assert alternative.coarse_label == "sequence_or_counter"

    def test_old_sequence_label_not_matched(self):
        """R287: 旧标签 "sequence" 不再被匹配（反向验证）

        构造 coarse_label="sequence"（旧标签）的候选，
        冲突函数不应将其识别为 sequence 候选。
        """
        resolver = Resolver()
        old_sequence = DetectorEvidence(
            detector="sequence",
            coarse_label="sequence",  # 旧标签
            fine_label="monotonic_counter",
            is_hard_evidence=True,
            score=0.95,
            reason_code="test",
            details={}
        )
        length = self._make_length_candidate(score=0.85)

        primary, alternative = resolver.resolve_length_sequence_conflict([length, old_sequence])

        # old_sequence 不被识别为 sequence 候选，归入 other_candidates
        # length_candidates 非空但 sequence_candidates 为空，走 "只有 length" 分支
        assert primary is not None
        assert primary.coarse_label == "length"
        assert alternative is None

    def test_sequence_or_counter_only_length_conflict(self):
        """R287: 只有 sequence_or_counter 候选时正确返回"""
        resolver = Resolver()
        candidates = [self._make_sequence_candidate(score=0.95)]

        primary, alternative = resolver.resolve_length_sequence_conflict(candidates)

        assert primary is not None
        assert primary.coarse_label == "sequence_or_counter"
        assert alternative is None

    def test_sequence_or_counter_only_timestamp_conflict(self):
        """R287: 只有 sequence_or_counter 候选时正确返回（timestamp 冲突）"""
        resolver = Resolver()
        candidates = [self._make_sequence_candidate(score=0.95)]

        primary, alternative = resolver.resolve_timestamp_sequence_conflict(candidates)

        assert primary is not None
        assert primary.coarse_label == "sequence_or_counter"
        assert alternative is None

    def test_sequence_or_counter_in_other_candidates(self):
        """R287: sequence_or_counter 在 other_candidates 中被正确排除

        当调用 resolve_constant_string_conflict 时，sequence_or_counter
        不属于 constant/string，应归入 other_candidates。
        """
        resolver = Resolver()
        sequence = self._make_sequence_candidate(score=0.95)
        constant = DetectorEvidence(
            detector="constant",
            coarse_label="constant",
            fine_label="constant_value",
            is_hard_evidence=True,
            score=0.85,
            reason_code="test",
            details={}
        )

        primary, alternative = resolver.resolve_constant_string_conflict([constant, sequence])

        # constant 和 string 都在，但 sequence_or_counter 归入 other
        # 只有 constant（无 string），走 "只有 constant" 分支
        assert primary is not None
        assert primary.coarse_label == "constant"
        assert alternative is None

    def test_label_uses_canonical_taxonomy_label(self):
        """R287: resolver 使用 taxonomy 标准标签 sequence_or_counter"""
        from semantic_detector.taxonomy import CANONICAL_COARSE_LABELS

        assert "sequence_or_counter" in CANONICAL_COARSE_LABELS
        # 旧标签 "sequence" 不在标准标签中
        assert "sequence" not in CANONICAL_COARSE_LABELS


class TestConstantTypeOpcodeConflictR332:
    """R332: constant 与 type_control 冲突解决

    06 计划 R332 验收规则：
    - 原 constant evidence 仍在 evidence
    - type_control 可进入 alternatives
    - type_control 不得覆盖强 length/timestamp
    - 最终选择 type_control 时，constant 仍可作为"单 layout 内稳定"的支持证据

    教程 10.5：跨 layout type/opcode 比单 layout 内常量更具语义信息。
    一个在各 layout 内都恒定、但跨 layout 呈一一对应映射的字段，
    语义上是 type/opcode 而非常量。
    """

    def _make_constant_candidate(self, score=1.0, hard=True):
        return DetectorEvidence(
            detector="constant",
            coarse_label="constant",
            fine_label="constant_value",
            is_hard_evidence=hard,
            score=score,
            reason_code="test",
            details={}
        )

    def _make_type_control_candidate(self, score=0.7, hard=False):
        return DetectorEvidence(
            detector="type_opcode",
            coarse_label="type_control",
            fine_label="type_or_opcode_candidate",
            is_hard_evidence=hard,
            score=score,
            reason_code="one_to_one_mapping",
            details={}
        )

    def _make_length_candidate(self, score=0.9, hard=True):
        return DetectorEvidence(
            detector="length",
            coarse_label="length",
            fine_label="length_of_next_field",
            is_hard_evidence=hard,
            score=score,
            reason_code="test",
            details={}
        )

    def _make_timestamp_candidate(self, score=0.9, hard=True):
        return DetectorEvidence(
            detector="timestamp",
            coarse_label="timestamp",
            fine_label="unix_timestamp",
            is_hard_evidence=hard,
            score=score,
            reason_code="test",
            details={}
        )

    def test_type_control_wins_over_constant(self):
        """R332: type_control 胜出，constant 保留为 alternative"""
        resolver = Resolver()
        candidates = [
            self._make_constant_candidate(score=1.0, hard=True),
            self._make_type_control_candidate(score=0.7, hard=False),
        ]

        primary, alternative = resolver.resolve_constant_type_opcode_conflict(candidates)

        assert primary is not None
        assert primary.coarse_label == "type_control"
        assert alternative is not None
        assert alternative.coarse_label == "constant"

    def test_hard_length_prevents_rule(self):
        """R332: 存在 hard length 证据时不触发规则（type_control 不得覆盖强 length）"""
        resolver = Resolver()
        candidates = [
            self._make_constant_candidate(score=1.0, hard=True),
            self._make_type_control_candidate(score=0.7, hard=False),
            self._make_length_candidate(score=0.9, hard=True),
        ]

        primary, alternative = resolver.resolve_constant_type_opcode_conflict(candidates)

        # 返回 None，交给 hard priority 处理
        assert primary is None
        assert alternative is None

    def test_hard_timestamp_prevents_rule(self):
        """R332: 存在 hard timestamp 证据时不触发规则"""
        resolver = Resolver()
        candidates = [
            self._make_constant_candidate(score=1.0, hard=True),
            self._make_type_control_candidate(score=0.7, hard=False),
            self._make_timestamp_candidate(score=0.9, hard=True),
        ]

        primary, alternative = resolver.resolve_constant_type_opcode_conflict(candidates)

        assert primary is None
        assert alternative is None

    def test_soft_length_does_not_prevent_rule(self):
        """R332: soft length 不阻止规则（仅 hard length/timestamp 阻止）"""
        resolver = Resolver()
        candidates = [
            self._make_constant_candidate(score=1.0, hard=True),
            self._make_type_control_candidate(score=0.7, hard=False),
            self._make_length_candidate(score=0.9, hard=False),
        ]

        primary, alternative = resolver.resolve_constant_type_opcode_conflict(candidates)

        assert primary is not None
        assert primary.coarse_label == "type_control"

    def test_only_constant_returns_none(self):
        """R332: 只有 constant 时返回 None"""
        resolver = Resolver()
        candidates = [self._make_constant_candidate(score=1.0)]

        primary, alternative = resolver.resolve_constant_type_opcode_conflict(candidates)

        assert primary is None
        assert alternative is None

    def test_only_type_control_returns_none(self):
        """R332: 只有 type_control 时返回 None"""
        resolver = Resolver()
        candidates = [self._make_type_control_candidate(score=0.7)]

        primary, alternative = resolver.resolve_constant_type_opcode_conflict(candidates)

        assert primary is None
        assert alternative is None

    def test_empty_candidates_returns_none(self):
        """R332: 空候选列表返回 None"""
        resolver = Resolver()

        primary, alternative = resolver.resolve_constant_type_opcode_conflict([])

        assert primary is None
        assert alternative is None

    def test_resolve_with_context_type_control_wins(self):
        """R332: resolve_with_context 中 type_control 胜过 constant（hard）"""
        resolver = Resolver()
        candidates = [
            self._make_constant_candidate(score=1.0, hard=True),
            self._make_type_control_candidate(score=0.7, hard=False),
        ]

        primary, alternatives = resolver.resolve_with_context(candidates)

        assert primary.coarse_label == "type_control"
        # constant 仍在 alternatives 中
        assert any(a.coarse_label == "constant" for a in alternatives)

    def test_resolve_with_context_hard_length_wins_over_type_control(self):
        """R332: hard length 胜过 type_control（type_control 不得覆盖强 length）"""
        resolver = Resolver()
        candidates = [
            self._make_constant_candidate(score=0.85, hard=True),
            self._make_type_control_candidate(score=0.7, hard=False),
            self._make_length_candidate(score=0.95, hard=True),
        ]

        primary, alternatives = resolver.resolve_with_context(candidates)

        # hard length 分数最高，胜出
        assert primary.coarse_label == "length"
        # type_control 进入 alternatives
        assert any(a.coarse_label == "type_control" for a in alternatives)

    def test_resolve_with_context_hard_timestamp_wins_over_type_control(self):
        """R332: hard timestamp 胜过 type_control"""
        resolver = Resolver()
        candidates = [
            self._make_constant_candidate(score=0.85, hard=True),
            self._make_type_control_candidate(score=0.7, hard=False),
            self._make_timestamp_candidate(score=0.95, hard=True),
        ]

        primary, alternatives = resolver.resolve_with_context(candidates)

        assert primary.coarse_label == "timestamp"
        assert any(a.coarse_label == "type_control" for a in alternatives)
