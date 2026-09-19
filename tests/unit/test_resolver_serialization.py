"""测试候选解析器序列化"""

import pytest
from semantic_detector.scoring.resolver import Resolver
from semantic_detector.contracts import DetectorEvidence


class TestSerializeEvidence:
    """测试证据序列化"""
    
    def test_serialize_evidence(self):
        """序列化单个证据"""
        resolver = Resolver()
        
        evidence = DetectorEvidence(
            detector="length",
            coarse_label="length",
            fine_label="length_of_next_field",
            is_hard_evidence=True,
            score=0.90,
            reason_code="test",
            details={"offset": 0}
        )
        
        serialized = resolver.serialize_evidence(evidence)
        
        assert serialized["detector"] == "length"
        assert serialized["coarse_label"] == "length"
        assert serialized["fine_label"] == "length_of_next_field"
        assert serialized["is_hard_evidence"] is True
        assert serialized["score"] == 0.90
        assert serialized["reason_code"] == "test"
        assert serialized["details"]["offset"] == 0
    
    def test_serialize_evidences(self):
        """序列化证据列表"""
        resolver = Resolver()
        
        evidences = [
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
                coarse_label="sequence",
                fine_label="sequence_or_counter",
                is_hard_evidence=False,
                score=0.75,
                reason_code="test",
                details={}
            )
        ]
        
        serialized = resolver.serialize_evidences(evidences)
        
        assert len(serialized) == 2
        assert serialized[0]["detector"] == "length"
        assert serialized[1]["detector"] == "sequence"
    
    def test_serialize_empty_evidences(self):
        """序列化空证据列表"""
        resolver = Resolver()
        
        serialized = resolver.serialize_evidences([])
        
        assert len(serialized) == 0


class TestResolveWithCandidates:
    """测试解析并返回候选"""
    
    def test_resolve_with_candidates(self):
        """解析并返回候选"""
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
        
        prediction, serialized_candidates = resolver.resolve_with_candidates(candidates)
        
        assert prediction is not None
        assert prediction.coarse_label == "length"
        assert len(serialized_candidates) == 1
        assert serialized_candidates[0]["detector"] == "length"
    
    def test_resolve_with_multiple_candidates(self):
        """解析多个候选"""
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
                coarse_label="sequence",
                fine_label="sequence_or_counter",
                is_hard_evidence=False,
                score=0.75,
                reason_code="test",
                details={}
            )
        ]
        
        prediction, serialized_candidates = resolver.resolve_with_candidates(candidates)
        
        assert prediction is not None
        assert prediction.coarse_label == "length"
        assert len(serialized_candidates) == 2
        # 候选不丢失
        assert serialized_candidates[0]["detector"] == "length"
        assert serialized_candidates[1]["detector"] == "sequence"
    
    def test_resolve_with_empty_candidates(self):
        """解析空候选列表"""
        resolver = Resolver()
        
        prediction, serialized_candidates = resolver.resolve_with_candidates([])
        
        assert prediction is not None
        assert prediction.coarse_label == "unknown"
        assert len(serialized_candidates) == 0
    
    def test_candidates_not_lost_after_serialization(self):
        """序列化后候选不丢失"""
        resolver = Resolver()
        
        candidates = [
            DetectorEvidence(
                detector="constant",
                coarse_label="constant",
                fine_label="constant_value",
                is_hard_evidence=True,
                score=0.95,
                reason_code="test",
                details={"value": "0x01"}
            ),
            DetectorEvidence(
                detector="length",
                coarse_label="length",
                fine_label="length_of_next_field",
                is_hard_evidence=True,
                score=0.85,
                reason_code="test",
                details={"offset": 0}
            ),
            DetectorEvidence(
                detector="timestamp",
                coarse_label="timestamp",
                fine_label="unix_seconds",
                is_hard_evidence=True,
                score=0.75,
                reason_code="test",
                details={"encoding": "be"}
            )
        ]
        
        prediction, serialized_candidates = resolver.resolve_with_candidates(candidates)
        
        # 所有候选都应该保留
        assert len(serialized_candidates) == 3
        
        # 验证每个候选的字段完整
        for serialized in serialized_candidates:
            assert "detector" in serialized
            assert "coarse_label" in serialized
            assert "fine_label" in serialized
            assert "is_hard_evidence" in serialized
            assert "score" in serialized
            assert "reason_code" in serialized
            assert "details" in serialized


class TestResolveWithCandidatesR292:
    """R292: 保留全部候选和稳定 alternatives 顺序

    04 任务表 R292：
    "保留全部候选和稳定 alternatives 顺序 | resolver.py; test_resolver_serialization.py |
     多候选 | 预测可审计、顺序确定"

    教程 11.2 第 9 步：保留 alternatives
    顺序确定性：按分数降序，同分保持原顺序（稳定排序）

    R292 完成标准：多候选场景下预测可审计、顺序确定。
    """

    def _make_evidence(self, detector, coarse_label, score, is_hard=True, fine_label=None):
        return DetectorEvidence(
            detector=detector,
            coarse_label=coarse_label,
            fine_label=fine_label or f"{coarse_label}_candidate",
            is_hard_evidence=is_hard,
            score=score,
            reason_code="test",
            details={}
        )

    def test_candidates_sorted_by_score_descending(self):
        """R292: 候选列表按分数降序排列

        输入顺序打乱，输出应按分数降序。
        """
        resolver = Resolver()
        # 输入顺序：低分在前
        candidates = [
            self._make_evidence("timestamp", "timestamp", 0.75),
            self._make_evidence("constant", "constant", 0.95),
            self._make_evidence("length", "length", 0.85),
        ]

        prediction, serialized_candidates = resolver.resolve_with_candidates(candidates)

        # 候选列表按分数降序
        assert len(serialized_candidates) == 3
        assert serialized_candidates[0]["score"] == 0.95
        assert serialized_candidates[1]["score"] == 0.85
        assert serialized_candidates[2]["score"] == 0.75

    def test_primary_first_when_not_unknown(self):
        """R292: primary 非 unknown 时在候选列表第一位

        primary 是最高分候选，应在第一位。
        """
        resolver = Resolver()
        length = self._make_evidence("length", "length", 0.90)
        sequence = self._make_evidence("sequence", "sequence_or_counter", 0.75, is_hard=False)

        prediction, serialized_candidates = resolver.resolve_with_candidates([sequence, length])

        assert prediction is not None
        assert prediction.coarse_label == "length"
        # primary 在第一位
        assert serialized_candidates[0]["coarse_label"] == "length"
        assert serialized_candidates[0]["score"] == 0.90

    def test_all_candidates_preserved(self):
        """R292: 全部候选保留，不丢失

        5 个候选，输出应有 5 个。
        """
        resolver = Resolver()
        candidates = [
            self._make_evidence("constant", "constant", 0.95),
            self._make_evidence("length", "length", 0.85),
            self._make_evidence("timestamp", "timestamp", 0.75),
            self._make_evidence("identifier", "identifier", 0.65, is_hard=False),
            self._make_evidence("payload", "payload", 0.55, is_hard=False),
        ]

        prediction, serialized_candidates = resolver.resolve_with_candidates(candidates)

        assert len(serialized_candidates) == 5
        # 全部 detector 保留
        detectors = {s["detector"] for s in serialized_candidates}
        assert detectors == {"constant", "length", "timestamp", "identifier", "payload"}

    def test_same_score_preserves_input_order(self):
        """R292: 同分候选保持输入顺序（稳定排序）

        两个同分 hard 候选，输出顺序应与输入一致。
        """
        resolver = Resolver()
        first = self._make_evidence("constant", "constant", 0.90)
        second = self._make_evidence("length", "length", 0.90)

        prediction, serialized_candidates = resolver.resolve_with_candidates([first, second])

        # 同分保持输入顺序
        assert serialized_candidates[0]["detector"] == "constant"
        assert serialized_candidates[1]["detector"] == "length"

    def test_unknown_not_in_candidates_when_no_candidates(self):
        """R292: 无候选时 primary=unknown，候选列表为空

        unknown 不混入候选列表。
        """
        resolver = Resolver()

        prediction, serialized_candidates = resolver.resolve_with_candidates([])

        assert prediction.coarse_label == "unknown"
        assert prediction.reason_code == "no_candidates"
        assert len(serialized_candidates) == 0

    def test_unknown_not_in_candidates_when_all_below_threshold(self):
        """R292: 全部低于阈值时 primary=unknown，候选列表为空

        unknown 不混入候选列表。
        """
        resolver = Resolver(min_score=0.8)
        candidates = [
            self._make_evidence("constant", "constant", 0.50, is_hard=False),
            self._make_evidence("length", "length", 0.60, is_hard=False),
        ]

        prediction, serialized_candidates = resolver.resolve_with_candidates(candidates)

        assert prediction.coarse_label == "unknown"
        assert prediction.reason_code == "all_below_threshold"
        assert len(serialized_candidates) == 0

    def test_ambiguous_keeps_sorted_candidates(self):
        """R292: 模糊时 primary=unknown(ambiguous)，候选列表保留排序候选

        模糊场景下 unknown 不混入候选列表，但保留排序候选供审计。
        """
        resolver = Resolver(ambiguity_margin=0.1)
        # 两个 soft 候选，分数差 0.05 < margin 0.1，模糊
        candidates = [
            self._make_evidence("identifier", "identifier", 0.85, is_hard=False),
            self._make_evidence("payload", "payload", 0.80, is_hard=False),
        ]

        prediction, serialized_candidates = resolver.resolve_with_candidates(candidates)

        assert prediction.coarse_label == "unknown"
        assert prediction.reason_code == "ambiguous"
        # 候选列表保留排序候选（按分数降序）
        assert len(serialized_candidates) == 2
        assert serialized_candidates[0]["score"] == 0.85
        assert serialized_candidates[1]["score"] == 0.80

    def test_length_sequence_conflict_preserves_all_candidates(self):
        """R292: length-vs-sequence 冲突时全部候选保留

        length(0.90) + sequence(0.95) + identifier(0.70)
        length 胜出（专项规则），sequence 和 identifier 进 alternative
        候选列表 = [length, sequence, identifier]（按分数降序）
        """
        resolver = Resolver()
        length = self._make_evidence("length", "length", 0.90)
        sequence = self._make_evidence("sequence", "sequence_or_counter", 0.95)
        identifier = self._make_evidence("identifier", "identifier", 0.70, is_hard=False)

        prediction, serialized_candidates = resolver.resolve_with_candidates(
            [identifier, sequence, length]
        )

        # length 胜出（专项规则，不是最高分 sequence）
        assert prediction.coarse_label == "length"
        # 全部候选保留（3 个）
        assert len(serialized_candidates) == 3
        # 顺序：length(0.90) 在第一位（primary），其余按分数降序
        assert serialized_candidates[0]["coarse_label"] == "length"
        # sequence(0.95) 和 identifier(0.70) 按 score 降序
        assert serialized_candidates[1]["score"] == 0.95
        assert serialized_candidates[2]["score"] == 0.70

    def test_prediction_auditable_with_full_context(self):
        """R292: 预测可审计——候选列表包含完整上下文

        候选列表的每个元素都包含 detector/coarse_label/fine_label/
        is_hard_evidence/score/reason_code/details 7 个字段。
        """
        resolver = Resolver()
        candidates = [
            self._make_evidence("length", "length", 0.90, fine_label="length_of_next_field"),
        ]

        prediction, serialized_candidates = resolver.resolve_with_candidates(candidates)

        assert len(serialized_candidates) == 1
        s = serialized_candidates[0]
        # 7 个字段完整
        assert s["detector"] == "length"
        assert s["coarse_label"] == "length"
        assert s["fine_label"] == "length_of_next_field"
        assert s["is_hard_evidence"] is True
        assert s["score"] == 0.90
        assert s["reason_code"] == "test"
        assert s["details"] == {}

    def test_deterministic_order_across_calls(self):
        """R292: 顺序确定性——多次调用结果一致

        同一输入多次调用，候选列表顺序始终一致。
        """
        resolver = Resolver()
        candidates = [
            self._make_evidence("timestamp", "timestamp", 0.75),
            self._make_evidence("constant", "constant", 0.95),
            self._make_evidence("length", "length", 0.85),
        ]

        _, first_result = resolver.resolve_with_candidates(candidates)
        _, second_result = resolver.resolve_with_candidates(candidates)
        _, third_result = resolver.resolve_with_candidates(candidates)

        # 三次调用顺序一致
        assert first_result == second_result
        assert second_result == third_result
