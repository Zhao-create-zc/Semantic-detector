"""测试候选解析器"""

import pytest
from semantic_detector.scoring.resolver import Resolver
from semantic_detector.contracts import DetectorEvidence


class TestResolverInit:
    """测试解析器初始化"""
    
    def test_init_with_default_min_score(self):
        """使用默认最小分数初始化"""
        resolver = Resolver()
        assert resolver.min_score == 0.5
    
    def test_init_with_custom_min_score(self):
        """使用自定义最小分数初始化"""
        resolver = Resolver(min_score=0.7)
        assert resolver.min_score == 0.7
    
    def test_init_with_invalid_min_score_raises(self):
        """无效最小分数抛出异常"""
        with pytest.raises(ValueError, match="min_score must be in"):
            Resolver(min_score=-0.1)
        
        with pytest.raises(ValueError, match="min_score must be in"):
            Resolver(min_score=1.1)


class TestFilterLowScoreCandidates:
    """测试丢弃低阈值候选"""
    
    def test_filter_removes_low_score_candidates(self):
        """丢弃低于阈值的候选"""
        resolver = Resolver(min_score=0.5)
        
        candidates = [
            DetectorEvidence(
                detector="test",
                coarse_label="label1",
                fine_label="fine1",
                is_hard_evidence=True,
                score=0.8,
                reason_code="test",
                details={}
            ),
            DetectorEvidence(
                detector="test",
                coarse_label="label2",
                fine_label="fine2",
                is_hard_evidence=False,
                score=0.3,
                reason_code="test",
                details={}
            ),
            DetectorEvidence(
                detector="test",
                coarse_label="label3",
                fine_label="fine3",
                is_hard_evidence=False,
                score=0.6,
                reason_code="test",
                details={}
            )
        ]
        
        filtered = resolver.filter_low_score_candidates(candidates)
        
        # 只有分数 >= 0.5 的候选被保留
        assert len(filtered) == 2
        assert filtered[0].coarse_label == "label1"
        assert filtered[1].coarse_label == "label3"
    
    def test_filter_keeps_all_high_score_candidates(self):
        """保留所有高于阈值的候选"""
        resolver = Resolver(min_score=0.5)
        
        candidates = [
            DetectorEvidence(
                detector="test",
                coarse_label="label1",
                fine_label="fine1",
                is_hard_evidence=True,
                score=0.8,
                reason_code="test",
                details={}
            ),
            DetectorEvidence(
                detector="test",
                coarse_label="label2",
                fine_label="fine2",
                is_hard_evidence=False,
                score=0.9,
                reason_code="test",
                details={}
            )
        ]
        
        filtered = resolver.filter_low_score_candidates(candidates)
        
        assert len(filtered) == 2
    
    def test_filter_removes_all_low_score_candidates(self):
        """丢弃所有低于阈值的候选"""
        resolver = Resolver(min_score=0.5)
        
        candidates = [
            DetectorEvidence(
                detector="test",
                coarse_label="label1",
                fine_label="fine1",
                is_hard_evidence=False,
                score=0.1,
                reason_code="test",
                details={}
            ),
            DetectorEvidence(
                detector="test",
                coarse_label="label2",
                fine_label="fine2",
                is_hard_evidence=False,
                score=0.2,
                reason_code="test",
                details={}
            )
        ]
        
        filtered = resolver.filter_low_score_candidates(candidates)
        
        assert len(filtered) == 0
    
    def test_filter_empty_candidates(self):
        """空候选列表返回空列表"""
        resolver = Resolver()
        
        filtered = resolver.filter_low_score_candidates([])
        
        assert len(filtered) == 0
    
    def test_filter_boundary_score(self):
        """边界分数测试"""
        resolver = Resolver(min_score=0.5)
        
        candidates = [
            DetectorEvidence(
                detector="test",
                coarse_label="label1",
                fine_label="fine1",
                is_hard_evidence=False,
                score=0.49,
                reason_code="test",
                details={}
            ),
            DetectorEvidence(
                detector="test",
                coarse_label="label2",
                fine_label="fine2",
                is_hard_evidence=False,
                score=0.50,
                reason_code="test",
                details={}
            ),
            DetectorEvidence(
                detector="test",
                coarse_label="label3",
                fine_label="fine3",
                is_hard_evidence=False,
                score=0.51,
                reason_code="test",
                details={}
            )
        ]
        
        filtered = resolver.filter_low_score_candidates(candidates)
        
        # 0.49 被丢弃，0.50 和 0.51 被保留
        assert len(filtered) == 2
        assert filtered[0].score == 0.50
        assert filtered[1].score == 0.51


class TestSortCandidatesByScore:
    """测试按 score 降序排序"""
    
    def test_sort_descending_order(self):
        """按分数降序排序"""
        resolver = Resolver()
        
        candidates = [
            DetectorEvidence(
                detector="test",
                coarse_label="label1",
                fine_label="fine1",
                is_hard_evidence=False,
                score=0.5,
                reason_code="test",
                details={}
            ),
            DetectorEvidence(
                detector="test",
                coarse_label="label2",
                fine_label="fine2",
                is_hard_evidence=False,
                score=0.9,
                reason_code="test",
                details={}
            ),
            DetectorEvidence(
                detector="test",
                coarse_label="label3",
                fine_label="fine3",
                is_hard_evidence=False,
                score=0.7,
                reason_code="test",
                details={}
            )
        ]
        
        sorted_candidates = resolver.sort_candidates_by_score(candidates)
        
        assert len(sorted_candidates) == 3
        assert sorted_candidates[0].score == 0.9
        assert sorted_candidates[1].score == 0.7
        assert sorted_candidates[2].score == 0.5
    
    def test_sort_stable_for_same_score(self):
        """同分候选保持原始顺序"""
        resolver = Resolver()
        
        candidates = [
            DetectorEvidence(
                detector="test",
                coarse_label="label1",
                fine_label="fine1",
                is_hard_evidence=False,
                score=0.8,
                reason_code="test",
                details={}
            ),
            DetectorEvidence(
                detector="test",
                coarse_label="label2",
                fine_label="fine2",
                is_hard_evidence=False,
                score=0.8,
                reason_code="test",
                details={}
            ),
            DetectorEvidence(
                detector="test",
                coarse_label="label3",
                fine_label="fine3",
                is_hard_evidence=False,
                score=0.8,
                reason_code="test",
                details={}
            )
        ]
        
        sorted_candidates = resolver.sort_candidates_by_score(candidates)
        
        # 同分候选保持原始顺序
        assert len(sorted_candidates) == 3
        assert sorted_candidates[0].coarse_label == "label1"
        assert sorted_candidates[1].coarse_label == "label2"
        assert sorted_candidates[2].coarse_label == "label3"
    
    def test_sort_empty_candidates(self):
        """空候选列表返回空列表"""
        resolver = Resolver()
        
        sorted_candidates = resolver.sort_candidates_by_score([])
        
        assert len(sorted_candidates) == 0
    
    def test_sort_single_candidate(self):
        """单个候选返回单元素列表"""
        resolver = Resolver()
        
        candidates = [
            DetectorEvidence(
                detector="test",
                coarse_label="label1",
                fine_label="fine1",
                is_hard_evidence=False,
                score=0.5,
                reason_code="test",
                details={}
            )
        ]
        
        sorted_candidates = resolver.sort_candidates_by_score(candidates)
        
        assert len(sorted_candidates) == 1
        assert sorted_candidates[0].score == 0.5
    
    def test_sort_mixed_scores_with_same_score(self):
        """混合分数和同分候选"""
        resolver = Resolver()
        
        candidates = [
            DetectorEvidence(
                detector="test",
                coarse_label="label1",
                fine_label="fine1",
                is_hard_evidence=False,
                score=0.5,
                reason_code="test",
                details={}
            ),
            DetectorEvidence(
                detector="test",
                coarse_label="label2",
                fine_label="fine2",
                is_hard_evidence=False,
                score=0.9,
                reason_code="test",
                details={}
            ),
            DetectorEvidence(
                detector="test",
                coarse_label="label3",
                fine_label="fine3",
                is_hard_evidence=False,
                score=0.9,
                reason_code="test",
                details={}
            ),
            DetectorEvidence(
                detector="test",
                coarse_label="label4",
                fine_label="fine4",
                is_hard_evidence=False,
                score=0.7,
                reason_code="test",
                details={}
            )
        ]
        
        sorted_candidates = resolver.sort_candidates_by_score(candidates)
        
        assert len(sorted_candidates) == 4
        # 0.9 在前，同分保持原顺序
        assert sorted_candidates[0].score == 0.9
        assert sorted_candidates[0].coarse_label == "label2"
        assert sorted_candidates[1].score == 0.9
        assert sorted_candidates[1].coarse_label == "label3"
        # 0.7 次之
        assert sorted_candidates[2].score == 0.7
        # 0.5 最后
        assert sorted_candidates[3].score == 0.5


class TestCheckAmbiguity:
    """测试模糊边界拒识"""
    
    def test_init_with_default_ambiguity_margin(self):
        """使用默认模糊边界初始化"""
        resolver = Resolver()
        assert resolver.ambiguity_margin == 0.1
    
    def test_init_with_custom_ambiguity_margin(self):
        """使用自定义模糊边界初始化"""
        resolver = Resolver(ambiguity_margin=0.08)
        assert resolver.ambiguity_margin == 0.08
    
    def test_init_with_invalid_ambiguity_margin_raises(self):
        """无效模糊边界抛出异常"""
        with pytest.raises(ValueError, match="ambiguity_margin must be in"):
            Resolver(ambiguity_margin=-0.1)
        
        with pytest.raises(ValueError, match="ambiguity_margin must be in"):
            Resolver(ambiguity_margin=1.1)
    
    def test_ambiguity_detected_when_diff_below_margin(self):
        """前两名分数差 < margin 时检测到模糊"""
        resolver = Resolver(ambiguity_margin=0.1)
        
        candidates = [
            DetectorEvidence(
                detector="test",
                coarse_label="label1",
                fine_label="fine1",
                is_hard_evidence=True,
                score=0.85,
                reason_code="test",
                details={}
            ),
            DetectorEvidence(
                detector="test",
                coarse_label="label2",
                fine_label="fine2",
                is_hard_evidence=False,
                score=0.80,
                reason_code="test",
                details={}
            )
        ]
        
        # 分数差 = 0.85 - 0.80 = 0.05 < 0.1
        is_ambiguous = resolver.check_ambiguity(candidates)
        
        assert is_ambiguous is True
    
    def test_no_ambiguity_when_diff_above_margin(self):
        """前两名分数差 > margin 时无模糊"""
        resolver = Resolver(ambiguity_margin=0.1)
        
        candidates = [
            DetectorEvidence(
                detector="test",
                coarse_label="label1",
                fine_label="fine1",
                is_hard_evidence=True,
                score=0.90,
                reason_code="test",
                details={}
            ),
            DetectorEvidence(
                detector="test",
                coarse_label="label2",
                fine_label="fine2",
                is_hard_evidence=False,
                score=0.75,
                reason_code="test",
                details={}
            )
        ]
        
        # 分数差 = 0.90 - 0.75 = 0.15 > 0.1
        is_ambiguous = resolver.check_ambiguity(candidates)
        
        assert is_ambiguous is False
    
    def test_boundary_diff_07(self):
        """边界测试：分数差 0.07 < 0.08"""
        resolver = Resolver(ambiguity_margin=0.08)
        
        candidates = [
            DetectorEvidence(
                detector="test",
                coarse_label="label1",
                fine_label="fine1",
                is_hard_evidence=True,
                score=0.90,
                reason_code="test",
                details={}
            ),
            DetectorEvidence(
                detector="test",
                coarse_label="label2",
                fine_label="fine2",
                is_hard_evidence=False,
                score=0.83,
                reason_code="test",
                details={}
            )
        ]
        
        # 分数差 = 0.90 - 0.83 = 0.07 < 0.08
        is_ambiguous = resolver.check_ambiguity(candidates)
        
        assert is_ambiguous is True
    
    def test_boundary_diff_08(self):
        """边界测试：分数差 0.08 = 0.08"""
        resolver = Resolver(ambiguity_margin=0.08)
        
        candidates = [
            DetectorEvidence(
                detector="test",
                coarse_label="label1",
                fine_label="fine1",
                is_hard_evidence=True,
                score=0.90,
                reason_code="test",
                details={}
            ),
            DetectorEvidence(
                detector="test",
                coarse_label="label2",
                fine_label="fine2",
                is_hard_evidence=False,
                score=0.82,
                reason_code="test",
                details={}
            )
        ]
        
        # 分数差 = 0.90 - 0.82 = 0.08 = 0.08
        # 差 < margin 时模糊，差 >= margin 时清晰
        is_ambiguous = resolver.check_ambiguity(candidates)
        
        assert is_ambiguous is False
    
    def test_boundary_diff_09(self):
        """边界测试：分数差 0.09 > 0.08"""
        resolver = Resolver(ambiguity_margin=0.08)
        
        candidates = [
            DetectorEvidence(
                detector="test",
                coarse_label="label1",
                fine_label="fine1",
                is_hard_evidence=True,
                score=0.90,
                reason_code="test",
                details={}
            ),
            DetectorEvidence(
                detector="test",
                coarse_label="label2",
                fine_label="fine2",
                is_hard_evidence=False,
                score=0.81,
                reason_code="test",
                details={}
            )
        ]
        
        # 分数差 = 0.90 - 0.81 = 0.09 > 0.08
        is_ambiguous = resolver.check_ambiguity(candidates)
        
        assert is_ambiguous is False
    
    def test_no_ambiguity_with_single_candidate(self):
        """单个候选不存在模糊"""
        resolver = Resolver()
        
        candidates = [
            DetectorEvidence(
                detector="test",
                coarse_label="label1",
                fine_label="fine1",
                is_hard_evidence=True,
                score=0.90,
                reason_code="test",
                details={}
            )
        ]
        
        is_ambiguous = resolver.check_ambiguity(candidates)
        
        assert is_ambiguous is False
    
    def test_no_ambiguity_with_empty_candidates(self):
        """空候选列表不存在模糊"""
        resolver = Resolver()
        
        is_ambiguous = resolver.check_ambiguity([])
        
        assert is_ambiguous is False


class TestSelectBestCandidate:
    """测试选择最佳候选"""
    
    def test_hard_evidence_over_soft_candidate(self):
        """hard evidence 优于 soft candidate"""
        resolver = Resolver()
        
        candidates = [
            DetectorEvidence(
                detector="identifier",
                coarse_label="identifier",
                fine_label="identifier_candidate",
                is_hard_evidence=False,
                score=0.95,
                reason_code="test",
                details={}
            ),
            DetectorEvidence(
                detector="length",
                coarse_label="length",
                fine_label="length_of_next_field",
                is_hard_evidence=True,
                score=0.80,
                reason_code="test",
                details={}
            )
        ]
        
        best = resolver.select_best_candidate(candidates)
        
        # 即使 identifier 分数更高，也选择 length（hard evidence）
        assert best is not None
        assert best.coarse_label == "length"
        assert best.is_hard_evidence is True
    
    def test_select_highest_score_hard_evidence(self):
        """多个 hard evidence 时选择最高分"""
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
                detector="length",
                coarse_label="length",
                fine_label="length_of_next_field",
                is_hard_evidence=True,
                score=0.95,
                reason_code="test",
                details={}
            )
        ]
        
        best = resolver.select_best_candidate(candidates)
        
        assert best is not None
        assert best.coarse_label == "length"
        assert best.score == 0.95
    
    def test_select_highest_score_soft_candidate(self):
        """只有 soft candidate 时选择最高分"""
        resolver = Resolver()
        
        candidates = [
            DetectorEvidence(
                detector="identifier",
                coarse_label="identifier",
                fine_label="identifier_candidate",
                is_hard_evidence=False,
                score=0.70,
                reason_code="test",
                details={}
            ),
            DetectorEvidence(
                detector="payload",
                coarse_label="payload",
                fine_label="opaque_payload_candidate",
                is_hard_evidence=False,
                score=0.90,
                reason_code="test",
                details={}
            )
        ]
        
        best = resolver.select_best_candidate(candidates)
        
        assert best is not None
        assert best.coarse_label == "payload"
        assert best.score == 0.90
    
    def test_select_single_hard_evidence(self):
        """单个 hard evidence 直接返回"""
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
            )
        ]
        
        best = resolver.select_best_candidate(candidates)
        
        assert best is not None
        assert best.coarse_label == "length"
    
    def test_select_single_soft_candidate(self):
        """单个 soft candidate 直接返回"""
        resolver = Resolver()
        
        candidates = [
            DetectorEvidence(
                detector="identifier",
                coarse_label="identifier",
                fine_label="identifier_candidate",
                is_hard_evidence=False,
                score=0.75,
                reason_code="test",
                details={}
            )
        ]
        
        best = resolver.select_best_candidate(candidates)
        
        assert best is not None
        assert best.coarse_label == "identifier"
    
    def test_select_from_empty_candidates(self):
        """空候选列表返回 None"""
        resolver = Resolver()
        
        best = resolver.select_best_candidate([])
        
        assert best is None


class TestCreateUnknownPrediction:
    """测试创建 unknown 预测"""
    
    def test_create_unknown_prediction(self):
        """创建 unknown 预测"""
        resolver = Resolver()
        
        prediction = resolver.create_unknown_prediction()
        
        assert prediction is not None
        assert prediction.coarse_label == "unknown"
        assert prediction.fine_label == "unknown"
        assert prediction.score == 0.0
        assert prediction.reason_code == "no_candidates"
        assert prediction.details["abstained"] is True
    
    def test_create_unknown_prediction_with_custom_reason(self):
        """使用自定义原因创建 unknown 预测"""
        resolver = Resolver()
        
        prediction = resolver.create_unknown_prediction(reason_code="ambiguous")
        
        assert prediction is not None
        assert prediction.reason_code == "ambiguous"
        assert prediction.details["abstained"] is True


class TestResolve:
    """测试解析候选列表"""
    
    def test_resolve_empty_candidates_returns_unknown(self):
        """空候选列表返回 unknown"""
        resolver = Resolver()
        
        prediction = resolver.resolve([])
        
        assert prediction is not None
        assert prediction.coarse_label == "unknown"
        assert prediction.reason_code == "no_candidates"
        assert prediction.details["abstained"] is True
    
    def test_resolve_all_below_threshold_returns_unknown(self):
        """所有候选低于阈值返回 unknown"""
        resolver = Resolver(min_score=0.5)
        
        candidates = [
            DetectorEvidence(
                detector="test",
                coarse_label="label1",
                fine_label="fine1",
                is_hard_evidence=False,
                score=0.3,
                reason_code="test",
                details={}
            )
        ]
        
        prediction = resolver.resolve(candidates)
        
        assert prediction is not None
        assert prediction.coarse_label == "unknown"
        assert prediction.reason_code == "all_below_threshold"
    
    def test_resolve_ambiguous_returns_unknown(self):
        """模糊候选返回 unknown"""
        resolver = Resolver(ambiguity_margin=0.1)
        
        candidates = [
            DetectorEvidence(
                detector="test",
                coarse_label="label1",
                fine_label="fine1",
                is_hard_evidence=True,
                score=0.85,
                reason_code="test",
                details={}
            ),
            DetectorEvidence(
                detector="test",
                coarse_label="label2",
                fine_label="fine2",
                is_hard_evidence=True,
                score=0.80,
                reason_code="test",
                details={}
            )
        ]
        
        prediction = resolver.resolve(candidates)
        
        assert prediction is not None
        assert prediction.coarse_label == "unknown"
        assert prediction.reason_code == "ambiguous"
    
    def test_resolve_returns_best_candidate(self):
        """返回最佳候选"""
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
        
        prediction = resolver.resolve(candidates)

        assert prediction is not None
        assert prediction.coarse_label == "length"
        assert prediction.score == 0.90


class TestResolveWithContext:
    """R240: resolve_with_context 返回 primary 和 alternatives 的最小接口

    03 教程 HIGH-3 修复链：为 Pipeline 包装 SemanticPrediction 提供上下文。
    验收场景：无候选、单候选、多候选；不破坏现有 resolve 兼容行为。
    """

    def _make_evidence(
        self,
        coarse_label: str,
        fine_label: str,
        score: float,
        is_hard: bool = False,
        detector: str = "test",
    ) -> DetectorEvidence:
        return DetectorEvidence(
            detector=detector,
            coarse_label=coarse_label,
            fine_label=fine_label,
            is_hard_evidence=is_hard,
            score=score,
            reason_code="test",
            details={},
        )

    def test_no_candidates_returns_unknown_and_empty_alternatives(self):
        """无候选 -> primary=unknown(no_candidates), alternatives=[]"""
        resolver = Resolver()

        primary, alternatives = resolver.resolve_with_context([])

        assert primary.coarse_label == "unknown"
        assert primary.reason_code == "no_candidates"
        assert alternatives == []

    def test_all_below_threshold_returns_unknown_and_empty_alternatives(self):
        """全部低于阈值 -> primary=unknown(all_below_threshold), alternatives=[]"""
        resolver = Resolver(min_score=0.5)

        candidates = [
            self._make_evidence("label1", "fine1", 0.3, is_hard=False),
        ]

        primary, alternatives = resolver.resolve_with_context(candidates)

        assert primary.coarse_label == "unknown"
        assert primary.reason_code == "all_below_threshold"
        assert alternatives == []

    def test_single_candidate_returns_primary_and_empty_alternatives(self):
        """单候选 -> primary=该候选, alternatives=[]"""
        resolver = Resolver()

        candidate = self._make_evidence(
            "length", "length_of_next_field", 0.90, is_hard=True, detector="length"
        )

        primary, alternatives = resolver.resolve_with_context([candidate])

        assert primary is candidate
        assert primary.coarse_label == "length"
        assert primary.score == 0.90
        assert alternatives == []

    def test_multiple_candidates_returns_primary_and_sorted_alternatives(self):
        """多候选 -> primary=最佳候选, alternatives=排除 primary 后按分数降序"""
        resolver = Resolver()

        # 分数差明显大于 ambiguity_margin(0.1)，避免浮点精度触发模糊
        candidate_a = self._make_evidence(
            "length", "length_of_next_field", 0.95, is_hard=True, detector="length"
        )
        candidate_b = self._make_evidence(
            "identifier", "identifier_candidate", 0.80, is_hard=False, detector="identifier"
        )
        candidate_c = self._make_evidence(
            "payload", "opaque_payload_candidate", 0.70, is_hard=False, detector="payload"
        )

        primary, alternatives = resolver.resolve_with_context(
            [candidate_c, candidate_a, candidate_b]  # 故意打乱输入顺序
        )

        # hard evidence 优先，primary 应为 candidate_a
        assert primary is candidate_a
        assert primary.coarse_label == "length"
        assert primary.score == 0.95

        # alternatives 排除 primary，按分数降序
        assert len(alternatives) == 2
        assert alternatives[0] is candidate_b  # score=0.80
        assert alternatives[1] is candidate_c  # score=0.70
        assert alternatives[0].score >= alternatives[1].score

    def test_ambiguous_returns_unknown_and_keeps_sorted_candidates(self):
        """模糊 -> primary=unknown(ambiguous), alternatives=排序后候选

        R291 后：hard 优先在 ambiguity 前，hard 候选不走 ambiguity。
        此测试改用 soft 候选验证 ambiguity 行为（hard 候选的 hard 优先行为
        由 TestResolveWithContextR291 覆盖）。
        """
        resolver = Resolver(ambiguity_margin=0.1)

        # 前两名分数差 0.05 < 0.1，模糊（soft 候选）
        candidate_a = self._make_evidence("label1", "fine1", 0.85, is_hard=False)
        candidate_b = self._make_evidence("label2", "fine2", 0.80, is_hard=False)

        primary, alternatives = resolver.resolve_with_context([candidate_a, candidate_b])

        assert primary.coarse_label == "unknown"
        assert primary.reason_code == "ambiguous"
        # 模糊时 alternatives 保留排序候选供下游判断
        assert len(alternatives) == 2
        assert alternatives[0].score >= alternatives[1].score
        assert alternatives[0].score == 0.85
        assert alternatives[1].score == 0.80

    def test_primary_compatible_with_resolve(self):
        """不破坏现有 resolve 兼容行为：正常场景下 primary 与 resolve() 返回值等价"""
        resolver = Resolver()

        # 分数差明显大于 ambiguity_margin(0.1)，避免浮点精度触发模糊
        candidate_a = self._make_evidence(
            "length", "length_of_next_field", 0.95, is_hard=True, detector="length"
        )
        candidate_b = self._make_evidence(
            "identifier", "identifier_candidate", 0.70, is_hard=False, detector="identifier"
        )
        candidates = [candidate_a, candidate_b]

        primary, alternatives = resolver.resolve_with_context(candidates)
        resolved = resolver.resolve(candidates)

        # 正常场景（非模糊），primary 与 resolve() 返回值是同一对象
        assert primary is resolved
        assert primary is candidate_a
        # alternatives 仅排除 primary
        assert alternatives == [candidate_b]


class TestResolveWithContextR288:
    """R288: 把 length-vs-sequence 规则接入 resolve_with_context

    04 任务表 R288：
    "把 length-vs-sequence 规则接入 resolve_with_context | resolver.py;
     test_resolver_conflicts.py | 同分 1.0 | length 胜出、sequence 进 alternative"

    教程 11.3：若长度证据来自真实等式/固定偏移支持率，length 胜出，
    sequence_or_counter 保留为 alternative。
    教程 11.4：ambiguity 不能在专项冲突规则前，否则 length=1.0/sequence=1.0
    会直接 unknown，导致领域规则失效。

    R288 完成标准：同分 1.0 时 length 胜出、sequence 进 alternative。
    """

    def _make_length_candidate(self, score=1.0, hard=True):
        return DetectorEvidence(
            detector="length",
            coarse_label="length",
            fine_label="length_of_next_field",
            is_hard_evidence=hard,
            score=score,
            reason_code="exact_support",
            details={}
        )

    def _make_sequence_candidate(self, score=1.0, hard=True):
        return DetectorEvidence(
            detector="sequence",
            coarse_label="sequence_or_counter",
            fine_label="monotonic_counter",
            is_hard_evidence=hard,
            score=score,
            reason_code="strictly_increasing",
            details={}
        )

    def test_same_score_length_wins_sequence_in_alternative(self):
        """R288 完成标准：同分 1.0 时 length 胜出、sequence 进 alternative

        修复前：length=1.0/sequence=1.0 分差 0 < margin，直接返回 unknown(ambiguous)
        修复后：length-vs-sequence 冲突规则在 ambiguity 前执行，length 胜出
        """
        resolver = Resolver()
        candidates = [
            self._make_length_candidate(score=1.0),
            self._make_sequence_candidate(score=1.0),
        ]

        primary, alternatives = resolver.resolve_with_context(candidates)

        assert primary is not None
        assert primary.coarse_label == "length"
        assert primary.score == 1.0
        # sequence_or_counter 在 alternatives 中
        assert len(alternatives) >= 1
        seq_alts = [a for a in alternatives if a.coarse_label == "sequence_or_counter"]
        assert len(seq_alts) == 1
        assert seq_alts[0].score == 1.0

    def test_length_wins_even_when_sequence_score_higher(self):
        """R288: 即使 sequence 分数更高，length 仍胜出（领域规则优先于分数）"""
        resolver = Resolver()
        candidates = [
            self._make_length_candidate(score=0.85),
            self._make_sequence_candidate(score=0.95),
        ]

        primary, alternatives = resolver.resolve_with_context(candidates)

        assert primary is not None
        assert primary.coarse_label == "length"
        assert primary.score == 0.85
        # sequence 在 alternatives 中
        seq_alts = [a for a in alternatives if a.coarse_label == "sequence_or_counter"]
        assert len(seq_alts) == 1

    def test_no_ambiguous_when_length_sequence_conflict(self):
        """R288: length+sequence 冲突时不返回 unknown(ambiguous)

        教程 11.4：ambiguity 不能在专项冲突规则前。
        """
        resolver = Resolver()
        candidates = [
            self._make_length_candidate(score=1.0),
            self._make_sequence_candidate(score=1.0),
        ]

        primary, alternatives = resolver.resolve_with_context(candidates)

        # 不应是 unknown
        assert primary.coarse_label != "unknown"
        assert primary.coarse_label == "length"

    def test_length_only_no_conflict_resolution(self):
        """R288: 只有 length（无 sequence）时不触发冲突规则，走正常路径"""
        resolver = Resolver()
        length = self._make_length_candidate(score=0.95)
        candidates = [length]

        primary, alternatives = resolver.resolve_with_context(candidates)

        assert primary is length
        assert alternatives == []

    def test_sequence_only_no_conflict_resolution(self):
        """R288: 只有 sequence（无 length）时不触发冲突规则，走正常路径"""
        resolver = Resolver()
        sequence = self._make_sequence_candidate(score=0.95)
        candidates = [sequence]

        primary, alternatives = resolver.resolve_with_context(candidates)

        assert primary is sequence
        assert alternatives == []

    def test_other_candidates_still_use_ambiguity(self):
        """R288: 无 length/sequence 冲突时仍走 ambiguity 检查（回归验证）

        构造两个同分的非 length/sequence 候选，应返回 unknown(ambiguous)。
        """
        resolver = Resolver(ambiguity_margin=0.1)
        candidates = [
            DetectorEvidence(
                detector="identifier",
                coarse_label="identifier",
                fine_label="identifier_candidate",
                is_hard_evidence=False,
                score=0.9,
                reason_code="test",
                details={}
            ),
            DetectorEvidence(
                detector="payload",
                coarse_label="payload",
                fine_label="opaque_payload_candidate",
                is_hard_evidence=False,
                score=0.9,
                reason_code="test",
                details={}
            ),
        ]

        primary, alternatives = resolver.resolve_with_context(candidates)

        # 无 length/sequence 冲突，分差 0 < margin，应返回 unknown(ambiguous)
        assert primary.coarse_label == "unknown"
        assert primary.reason_code == "ambiguous"
        assert len(alternatives) == 2

    def test_length_sequence_with_other_candidates(self):
        """R288: length+sequence 冲突 + 其他候选，length 胜出，其余进 alternative"""
        resolver = Resolver()
        length = self._make_length_candidate(score=0.9)
        sequence = self._make_sequence_candidate(score=0.95)
        other = DetectorEvidence(
            detector="identifier",
            coarse_label="identifier",
            fine_label="identifier_candidate",
            is_hard_evidence=False,
            score=0.7,
            reason_code="test",
            details={}
        )
        candidates = [length, sequence, other]

        primary, alternatives = resolver.resolve_with_context(candidates)

        assert primary is length
        # alternatives 包含 sequence 和 other（排除 primary）
        assert len(alternatives) == 2
        alt_labels = [a.coarse_label for a in alternatives]
        assert "sequence_or_counter" in alt_labels
        assert "identifier" in alt_labels

    def test_soft_length_soft_sequence_conflict(self):
        """R288: soft length + soft sequence 冲突，length 仍胜出

        R291 才调整 hard 优先，R288 只接入 length-vs-sequence 规则，
        不区分 hard/soft。
        """
        resolver = Resolver()
        candidates = [
            self._make_length_candidate(score=0.7, hard=False),
            self._make_sequence_candidate(score=0.8, hard=False),
        ]

        primary, alternatives = resolver.resolve_with_context(candidates)

        assert primary is not None
        assert primary.coarse_label == "length"
        seq_alts = [a for a in alternatives if a.coarse_label == "sequence_or_counter"]
        assert len(seq_alts) == 1


class TestResolveWithContextR289:
    """R289: 把 timestamp-vs-sequence 规则接入主 resolve

    04 任务表 R289：
    "把 timestamp-vs-sequence 规则接入主 resolve | resolver.py;
     test_resolver_conflicts.py | 时间自然递增 | timestamp 胜出"

    教程 11.3：时间自然递增的 timestamp 证据胜出，
    sequence_or_counter 保留为 alternative。
    教程 11.4：ambiguity 不能在专项冲突规则前，否则 timestamp=1.0/sequence=1.0
    会直接 unknown，导致领域规则失效。

    R289 完成标准：同分 1.0 时 timestamp 胜出、sequence 进 alternative。
    """

    def _make_timestamp_candidate(self, score=1.0, hard=True):
        return DetectorEvidence(
            detector="timestamp",
            coarse_label="timestamp",
            fine_label="unix_seconds",
            is_hard_evidence=hard,
            score=score,
            reason_code="natural_increasing",
            details={}
        )

    def _make_sequence_candidate(self, score=1.0, hard=True):
        return DetectorEvidence(
            detector="sequence",
            coarse_label="sequence_or_counter",
            fine_label="monotonic_counter",
            is_hard_evidence=hard,
            score=score,
            reason_code="strictly_increasing",
            details={}
        )

    def test_same_score_timestamp_wins_sequence_in_alternative(self):
        """R289 完成标准：同分 1.0 时 timestamp 胜出、sequence 进 alternative

        修复前：timestamp=1.0/sequence=1.0 分差 0 < margin，直接返回 unknown(ambiguous)
        修复后：timestamp-vs-sequence 冲突规则在 ambiguity 前执行，timestamp 胜出
        """
        resolver = Resolver()
        candidates = [
            self._make_timestamp_candidate(score=1.0),
            self._make_sequence_candidate(score=1.0),
        ]

        primary, alternatives = resolver.resolve_with_context(candidates)

        assert primary is not None
        assert primary.coarse_label == "timestamp"
        assert primary.score == 1.0
        # sequence_or_counter 在 alternatives 中
        assert len(alternatives) >= 1
        seq_alts = [a for a in alternatives if a.coarse_label == "sequence_or_counter"]
        assert len(seq_alts) == 1
        assert seq_alts[0].score == 1.0

    def test_timestamp_wins_even_when_sequence_score_higher(self):
        """R289: 即使 sequence 分数更高，timestamp 仍胜出（领域规则优先于分数）

        时间自然递增的 timestamp 证据（教程 11.3）应胜过单纯递增的 sequence。
        """
        resolver = Resolver()
        candidates = [
            self._make_timestamp_candidate(score=0.85),
            self._make_sequence_candidate(score=0.95),
        ]

        primary, alternatives = resolver.resolve_with_context(candidates)

        assert primary is not None
        assert primary.coarse_label == "timestamp"
        assert primary.score == 0.85
        # sequence 在 alternatives 中
        seq_alts = [a for a in alternatives if a.coarse_label == "sequence_or_counter"]
        assert len(seq_alts) == 1

    def test_no_ambiguous_when_timestamp_sequence_conflict(self):
        """R289: timestamp+sequence 冲突时不返回 unknown(ambiguous)

        教程 11.4：ambiguity 不能在专项冲突规则前。
        """
        resolver = Resolver()
        candidates = [
            self._make_timestamp_candidate(score=1.0),
            self._make_sequence_candidate(score=1.0),
        ]

        primary, alternatives = resolver.resolve_with_context(candidates)

        # 不应是 unknown
        assert primary.coarse_label != "unknown"
        assert primary.coarse_label == "timestamp"

    def test_timestamp_only_no_conflict_resolution(self):
        """R289: 只有 timestamp（无 sequence）时不触发冲突规则，走正常路径"""
        resolver = Resolver()
        timestamp = self._make_timestamp_candidate(score=0.95)
        candidates = [timestamp]

        primary, alternatives = resolver.resolve_with_context(candidates)

        assert primary is timestamp
        assert alternatives == []

    def test_sequence_only_no_timestamp_conflict_resolution(self):
        """R289: 只有 sequence（无 timestamp）时不触发 timestamp-vs-sequence 冲突规则"""
        resolver = Resolver()
        sequence = self._make_sequence_candidate(score=0.95)
        candidates = [sequence]

        primary, alternatives = resolver.resolve_with_context(candidates)

        assert primary is sequence
        assert alternatives == []

    def test_length_takes_priority_over_timestamp_sequence(self):
        """R289: length+timestamp+sequence 三者共存时，length 先胜出

        R288 length-vs-sequence 规则先于 R289 timestamp-vs-sequence 执行。
        当 length 与 sequence 同时存在时，length-vs-sequence 分支先返回。
        """
        resolver = Resolver()
        length = DetectorEvidence(
            detector="length",
            coarse_label="length",
            fine_label="length_of_next_field",
            is_hard_evidence=True,
            score=0.9,
            reason_code="exact_support",
            details={}
        )
        timestamp = self._make_timestamp_candidate(score=0.95)
        sequence = self._make_sequence_candidate(score=0.85)
        candidates = [length, timestamp, sequence]

        primary, alternatives = resolver.resolve_with_context(candidates)

        # length-vs-sequence 先触发，length 胜出
        assert primary is length
        # alternatives 包含 timestamp 和 sequence
        assert len(alternatives) == 2
        alt_labels = [a.coarse_label for a in alternatives]
        assert "timestamp" in alt_labels
        assert "sequence_or_counter" in alt_labels

    def test_timestamp_sequence_with_other_candidates(self):
        """R289: timestamp+sequence 冲突 + 其他候选，timestamp 胜出，其余进 alternative"""
        resolver = Resolver()
        timestamp = self._make_timestamp_candidate(score=0.9)
        sequence = self._make_sequence_candidate(score=0.95)
        other = DetectorEvidence(
            detector="identifier",
            coarse_label="identifier",
            fine_label="identifier_candidate",
            is_hard_evidence=False,
            score=0.7,
            reason_code="test",
            details={}
        )
        candidates = [timestamp, sequence, other]

        primary, alternatives = resolver.resolve_with_context(candidates)

        assert primary is timestamp
        # alternatives 包含 sequence 和 other（排除 primary）
        assert len(alternatives) == 2
        alt_labels = [a.coarse_label for a in alternatives]
        assert "sequence_or_counter" in alt_labels
        assert "identifier" in alt_labels

    def test_soft_timestamp_soft_sequence_conflict(self):
        """R289: soft timestamp + soft sequence 冲突，timestamp 仍胜出

        R291 才调整 hard 优先，R289 只接入 timestamp-vs-sequence 规则，
        不区分 hard/soft。
        """
        resolver = Resolver()
        candidates = [
            self._make_timestamp_candidate(score=0.7, hard=False),
            self._make_sequence_candidate(score=0.8, hard=False),
        ]

        primary, alternatives = resolver.resolve_with_context(candidates)

        assert primary is not None
        assert primary.coarse_label == "timestamp"
        seq_alts = [a for a in alternatives if a.coarse_label == "sequence_or_counter"]
        assert len(seq_alts) == 1


class TestResolveWithContextR290:
    """R290: 把 constant-vs-string 规则接入主 resolve

    04 任务表 R290：
    "把 constant-vs-string 规则接入主 resolve | resolver.py;
     test_resolver_conflicts.py | 固定 ASCII | 按宽度/printable 选择"

    教程 11.3：constant vs string 冲突，按宽度/printable 选择：
    - 宽度 > 1 且 printable_ratio >= 0.85 → string 胜出，constant 进 alternative
    - 否则 constant 胜出，string 进 alternative

    R290 完成标准：固定 ASCII 字段（宽度 > 1 且 printable 高）按宽度/printable 选择。
    """

    def _make_constant_candidate(self, score=1.0, hard=True):
        return DetectorEvidence(
            detector="constant",
            coarse_label="constant",
            fine_label="constant_value",
            is_hard_evidence=hard,
            score=score,
            reason_code="dominant_value",
            details={}
        )

    def _make_string_candidate(self, score=1.0, hard=True, byte_width=1, printable_ascii_ratio=0.0):
        return DetectorEvidence(
            detector="string",
            coarse_label="string",
            fine_label="ascii_string",
            is_hard_evidence=hard,
            score=score,
            reason_code="ascii_string_detected",
            details={
                "printable_ascii_ratio": printable_ascii_ratio,
                "utf8_decode_success_ratio": printable_ascii_ratio,
                "byte_width": byte_width
            }
        )

    def test_wide_high_printable_string_wins(self):
        """R290 完成标准：宽度 > 1 且 printable >= 0.85 时 string 胜出

        教程 11.3：固定 ASCII 字段，宽度 > 1 且 printable_ratio >= 0.85 → string。
        """
        resolver = Resolver()
        candidates = [
            self._make_constant_candidate(score=1.0),
            self._make_string_candidate(score=1.0, byte_width=4, printable_ascii_ratio=0.95),
        ]

        primary, alternatives = resolver.resolve_with_context(candidates)

        assert primary is not None
        assert primary.coarse_label == "string"
        # constant 在 alternatives 中
        const_alts = [a for a in alternatives if a.coarse_label == "constant"]
        assert len(const_alts) == 1

    def test_wide_high_printable_no_ambiguous(self):
        """R290: 宽度高 printable 冲突时不返回 unknown(ambiguous)

        教程 11.4：ambiguity 不能在专项冲突规则前。
        """
        resolver = Resolver()
        candidates = [
            self._make_constant_candidate(score=1.0),
            self._make_string_candidate(score=1.0, byte_width=4, printable_ascii_ratio=0.95),
        ]

        primary, alternatives = resolver.resolve_with_context(candidates)

        assert primary.coarse_label != "unknown"
        assert primary.coarse_label == "string"

    def test_narrow_string_constant_wins(self):
        """R290: 宽度 == 1 时 constant 胜出（即使 printable 高）

        教程 11.3：宽度不 > 1，选择 constant。
        """
        resolver = Resolver()
        candidates = [
            self._make_constant_candidate(score=1.0),
            self._make_string_candidate(score=1.0, byte_width=1, printable_ascii_ratio=0.95),
        ]

        primary, alternatives = resolver.resolve_with_context(candidates)

        assert primary is not None
        assert primary.coarse_label == "constant"
        # string 在 alternatives 中
        string_alts = [a for a in alternatives if a.coarse_label == "string"]
        assert len(string_alts) == 1

    def test_wide_low_printable_constant_wins(self):
        """R290: 宽度 > 1 但 printable < 0.85 时 constant 胜出

        教程 11.3：宽度 > 1 但 printable_ratio < 0.85，选择 constant。
        """
        resolver = Resolver()
        candidates = [
            self._make_constant_candidate(score=1.0),
            self._make_string_candidate(score=1.0, byte_width=4, printable_ascii_ratio=0.50),
        ]

        primary, alternatives = resolver.resolve_with_context(candidates)

        assert primary is not None
        assert primary.coarse_label == "constant"
        string_alts = [a for a in alternatives if a.coarse_label == "string"]
        assert len(string_alts) == 1

    def test_printable_boundary_085_string_wins(self):
        """R290: printable_ratio == 0.85 边界，宽度 > 1 时 string 胜出

        教程 11.3：printable_ratio >= 0.85（含等号）。
        """
        resolver = Resolver()
        candidates = [
            self._make_constant_candidate(score=1.0),
            self._make_string_candidate(score=1.0, byte_width=2, printable_ascii_ratio=0.85),
        ]

        primary, alternatives = resolver.resolve_with_context(candidates)

        assert primary is not None
        assert primary.coarse_label == "string"

    def test_constant_only_no_conflict_resolution(self):
        """R290: 只有 constant（无 string）时不触发冲突规则，走正常路径"""
        resolver = Resolver()
        constant = self._make_constant_candidate(score=0.95)
        candidates = [constant]

        primary, alternatives = resolver.resolve_with_context(candidates)

        assert primary is constant
        assert alternatives == []

    def test_string_only_no_conflict_resolution(self):
        """R290: 只有 string（无 constant）时不触发冲突规则，走正常路径"""
        resolver = Resolver()
        string = self._make_string_candidate(score=0.95, byte_width=4, printable_ascii_ratio=0.95)
        candidates = [string]

        primary, alternatives = resolver.resolve_with_context(candidates)

        assert primary is string
        assert alternatives == []

    def test_constant_string_with_other_candidates(self):
        """R290: constant+string 冲突 + 其他候选，string 胜出，其余进 alternative"""
        resolver = Resolver()
        constant = self._make_constant_candidate(score=0.9)
        string = self._make_string_candidate(score=0.95, byte_width=4, printable_ascii_ratio=0.95)
        other = DetectorEvidence(
            detector="identifier",
            coarse_label="identifier",
            fine_label="identifier_candidate",
            is_hard_evidence=False,
            score=0.7,
            reason_code="test",
            details={}
        )
        candidates = [constant, string, other]

        primary, alternatives = resolver.resolve_with_context(candidates)

        assert primary is string
        # alternatives 包含 constant 和 other（排除 primary）
        assert len(alternatives) == 2
        alt_labels = [a.coarse_label for a in alternatives]
        assert "constant" in alt_labels
        assert "identifier" in alt_labels

    def test_string_details_missing_defaults_to_constant(self):
        """R290: string details 缺失 byte_width/printable 时默认 constant 胜出

        默认 field_width=1, printable_ratio=0.0，不满足 string 条件，constant 胜出。
        """
        resolver = Resolver()
        string_no_details = DetectorEvidence(
            detector="string",
            coarse_label="string",
            fine_label="ascii_string",
            is_hard_evidence=True,
            score=1.0,
            reason_code="ascii_string_detected",
            details={}
        )
        constant = self._make_constant_candidate(score=1.0)
        candidates = [constant, string_no_details]

        primary, alternatives = resolver.resolve_with_context(candidates)

        assert primary is not None
        assert primary.coarse_label == "constant"


class TestResolveWithContextR291:
    """R291: 调整 hard 优先和 ambiguity 顺序

    04 任务表 R291：
    "调整 hard 优先和 ambiguity 顺序 | resolver.py; test_resolver.py |
     hard 0.8 vs soft 0.95 | hard 优先，专项规则先于 margin"

    教程 11.2 第 5 步：hard 优先
    教程 11.2 第 7 步：ambiguity_margin
    教程 11.4：专项规则先于 margin

    修复前问题：check_ambiguity 在 select_best_candidate 之前执行，
    当 hard 0.85 vs soft 0.90 时（差 0.05 < margin 0.1），直接返回 unknown(ambiguous)，
    hard 优先逻辑（select_best_candidate）无法生效。

    R291 完成标准：hard 0.8 vs soft 0.95 时 hard 优先，专项规则先于 margin。
    """

    def _make_hard_candidate(self, coarse_label="identifier", score=0.8):
        return DetectorEvidence(
            detector="test",
            coarse_label=coarse_label,
            fine_label=f"{coarse_label}_candidate",
            is_hard_evidence=True,
            score=score,
            reason_code="test",
            details={}
        )

    def _make_soft_candidate(self, coarse_label="payload", score=0.95):
        return DetectorEvidence(
            detector="test",
            coarse_label=coarse_label,
            fine_label=f"{coarse_label}_candidate",
            is_hard_evidence=False,
            score=score,
            reason_code="test",
            details={}
        )

    def test_hard_08_wins_over_soft_095(self):
        """R291 完成标准：hard 0.8 vs soft 0.95 时 hard 优先

        修复前：差 0.15 > margin 0.1，不模糊，select_best_candidate 选 hard 0.8（看似正确）
        但修复前 hard 0.85 vs soft 0.90 会误判 ambiguous。
        R291 后：hard 优先在 ambiguity 前，任何 hard vs soft 都选 hard。
        """
        resolver = Resolver()
        hard = self._make_hard_candidate(score=0.8)
        soft = self._make_soft_candidate(score=0.95)
        candidates = [hard, soft]

        primary, alternatives = resolver.resolve_with_context(candidates)

        assert primary is hard
        assert primary.score == 0.8
        assert primary.is_hard_evidence is True
        # soft 在 alternatives 中
        assert soft in alternatives

    def test_hard_085_wins_over_soft_090_no_ambiguous(self):
        """R291: hard 0.85 vs soft 0.90 时不返回 unknown(ambiguous)

        修复前：差 0.05 < margin 0.1，返回 unknown(ambiguous)
        修复后：hard 优先在 ambiguity 前，选 hard 0.85
        """
        resolver = Resolver(ambiguity_margin=0.1)
        hard = self._make_hard_candidate(score=0.85)
        soft = self._make_soft_candidate(score=0.90)
        candidates = [hard, soft]

        primary, alternatives = resolver.resolve_with_context(candidates)

        assert primary is hard
        assert primary.coarse_label != "unknown"
        assert primary.reason_code != "ambiguous"

    def test_soft_only_ambiguous_when_diff_below_margin(self):
        """R291: 只有 soft 候选且分数差 < margin 时仍返回 unknown(ambiguous)

        hard 优先只在有 hard evidence 时触发，soft 候选之间仍走 ambiguity。
        """
        resolver = Resolver(ambiguity_margin=0.1)
        candidates = [
            self._make_soft_candidate(coarse_label="identifier", score=0.85),
            self._make_soft_candidate(coarse_label="payload", score=0.90),
        ]

        primary, alternatives = resolver.resolve_with_context(candidates)

        assert primary.coarse_label == "unknown"
        assert primary.reason_code == "ambiguous"
        assert len(alternatives) == 2

    def test_soft_only_no_ambiguous_when_diff_above_margin(self):
        """R291: 只有 soft 候选且分数差 > margin 时选最高分 soft"""
        resolver = Resolver(ambiguity_margin=0.1)
        soft_low = self._make_soft_candidate(coarse_label="identifier", score=0.80)
        soft_high = self._make_soft_candidate(coarse_label="payload", score=0.95)
        candidates = [soft_low, soft_high]

        primary, alternatives = resolver.resolve_with_context(candidates)

        assert primary is soft_high
        assert soft_low in alternatives

    def test_multiple_hard_candidates_select_highest_score(self):
        """R291: 多个 hard 候选时选最高分 hard"""
        resolver = Resolver()
        hard_low = self._make_hard_candidate(coarse_label="identifier", score=0.7)
        hard_high = self._make_hard_candidate(coarse_label="payload", score=0.9)
        candidates = [hard_low, hard_high]

        primary, alternatives = resolver.resolve_with_context(candidates)

        assert primary is hard_high
        assert hard_low in alternatives

    def test_hard_with_other_soft_candidates(self):
        """R291: hard + 多个 soft 候选，hard 优先，soft 进 alternative"""
        resolver = Resolver()
        hard = self._make_hard_candidate(score=0.8)
        soft1 = self._make_soft_candidate(coarse_label="identifier", score=0.9)
        soft2 = self._make_soft_candidate(coarse_label="payload", score=0.7)
        candidates = [hard, soft1, soft2]

        primary, alternatives = resolver.resolve_with_context(candidates)

        assert primary is hard
        assert len(alternatives) == 2
        assert soft1 in alternatives
        assert soft2 in alternatives

    def test_specialty_conflict_before_hard_priority(self):
        """R291: 专项冲突规则先于 hard 优先（回归保护）

        length hard + sequence hard，length-vs-sequence 专项规则先触发，
        返回 length（不走 hard 优先）。
        """
        resolver = Resolver()
        length = DetectorEvidence(
            detector="length",
            coarse_label="length",
            fine_label="length_of_next_field",
            is_hard_evidence=True,
            score=0.8,
            reason_code="exact_support",
            details={}
        )
        sequence = DetectorEvidence(
            detector="sequence",
            coarse_label="sequence_or_counter",
            fine_label="monotonic_counter",
            is_hard_evidence=True,
            score=0.95,
            reason_code="strictly_increasing",
            details={}
        )
        candidates = [length, sequence]

        primary, alternatives = resolver.resolve_with_context(candidates)

        # length-vs-sequence 专项规则先触发，返回 length（不是最高分 sequence）
        assert primary is length
        assert sequence in alternatives

    def test_only_hard_no_ambiguous(self):
        """R291: 只有 hard 候选（同分）时不返回 unknown(ambiguous)

        修复前：两个 hard 同分 0.9，差 0 < margin，返回 unknown(ambiguous)
        修复后：hard 优先在 ambiguity 前，选第一个 hard
        """
        resolver = Resolver(ambiguity_margin=0.1)
        hard1 = self._make_hard_candidate(coarse_label="identifier", score=0.9)
        hard2 = self._make_hard_candidate(coarse_label="payload", score=0.9)
        candidates = [hard1, hard2]

        primary, alternatives = resolver.resolve_with_context(candidates)

        assert primary is hard1
        assert primary.coarse_label != "unknown"
        assert hard2 in alternatives


class TestResolverConfigAmbiguityMarginR357:
    """R357: Resolver 使用配置中的 ambiguity_margin

    计划 L1093-1116 要求：
    - 候选 0.70 和 0.61（差值 0.09）
    - ambiguity_margin=0.08：选择第一名
    - ambiguity_margin=0.10：unknown/ambiguous
    - 必须证明配置改变真实结果
    """

    def _make_soft_candidate(self, coarse_label="identifier", score=0.70):
        return DetectorEvidence(
            detector="test",
            coarse_label=coarse_label,
            fine_label=f"{coarse_label}_candidate",
            is_hard_evidence=False,
            score=score,
            reason_code="test",
            details={}
        )

    def test_plan_key_regression_margin_008_selects_first(self):
        """计划关键回归：差值 0.09，ambiguity_margin=0.08 → 选择第一名"""
        resolver = Resolver(ambiguity_margin=0.08)
        candidates = [
            self._make_soft_candidate(coarse_label="identifier", score=0.70),
            self._make_soft_candidate(coarse_label="payload", score=0.61),
        ]

        primary, alternatives = resolver.resolve_with_context(candidates)

        # 0.09 >= 0.08 → 不模糊 → 选第一名（0.70）
        assert primary is not None
        assert primary.coarse_label == "identifier"
        assert primary.score == 0.70
        assert primary.coarse_label != "unknown"

    def test_plan_key_regression_margin_010_returns_unknown(self):
        """计划关键回归：差值 0.09，ambiguity_margin=0.10 → unknown/ambiguous"""
        resolver = Resolver(ambiguity_margin=0.10)
        candidates = [
            self._make_soft_candidate(coarse_label="identifier", score=0.70),
            self._make_soft_candidate(coarse_label="payload", score=0.61),
        ]

        primary, alternatives = resolver.resolve_with_context(candidates)

        # 0.09 < 0.10 → 模糊 → unknown
        assert primary.coarse_label == "unknown"
        assert primary.reason_code == "ambiguous"
        assert len(alternatives) == 2

    def test_config_change_changes_result(self):
        """配置改变真实结果：同一组候选，不同 ambiguity_margin 产生不同结果"""
        candidates = [
            self._make_soft_candidate(coarse_label="identifier", score=0.70),
            self._make_soft_candidate(coarse_label="payload", score=0.61),
        ]

        # margin=0.08 → 选第一名
        resolver_008 = Resolver(ambiguity_margin=0.08)
        primary_008, _ = resolver_008.resolve_with_context(candidates)
        assert primary_008.coarse_label == "identifier"

        # margin=0.10 → unknown
        resolver_010 = Resolver(ambiguity_margin=0.10)
        primary_010, _ = resolver_010.resolve_with_context(candidates)
        assert primary_010.coarse_label == "unknown"

        # 两个结果不同
        assert primary_008.coarse_label != primary_010.coarse_label

    def test_pipeline_passes_config_ambiguity_margin_to_resolver(self):
        """Pipeline 把 config.ambiguity_margin 传给 Resolver"""
        from semantic_detector.config import Config
        from semantic_detector.pipeline.pipeline import DetectionPipeline

        config = Config(ambiguity_margin=0.15)
        pipeline = DetectionPipeline(config=config)

        assert pipeline.resolver.ambiguity_margin == 0.15

    def test_pipeline_default_config_ambiguity_margin(self):
        """Pipeline 默认 config 的 ambiguity_margin=0.08 传给 Resolver"""
        from semantic_detector.pipeline.pipeline import DetectionPipeline

        pipeline = DetectionPipeline()

        # 默认 Config 的 ambiguity_margin 是 0.08
        assert pipeline.resolver.ambiguity_margin == 0.08

    def test_pipeline_config_change_changes_resolver_behavior(self):
        """通过 Pipeline 的 config 改变 Resolver 行为"""
        from semantic_detector.config import Config
        from semantic_detector.pipeline.pipeline import DetectionPipeline

        candidates = [
            self._make_soft_candidate(coarse_label="identifier", score=0.70),
            self._make_soft_candidate(coarse_label="payload", score=0.61),
        ]

        # config ambiguity_margin=0.08 → Resolver 选第一名
        config_008 = Config(ambiguity_margin=0.08)
        pipeline_008 = DetectionPipeline(config=config_008)
        primary_008, _ = pipeline_008.resolver.resolve_with_context(candidates)
        assert primary_008.coarse_label == "identifier"

        # config ambiguity_margin=0.10 → Resolver 返回 unknown
        config_010 = Config(ambiguity_margin=0.10)
        pipeline_010 = DetectionPipeline(config=config_010)
        primary_010, _ = pipeline_010.resolver.resolve_with_context(candidates)
        assert primary_010.coarse_label == "unknown"

    def test_check_ambiguity_directly_with_config_margin(self):
        """直接验证 check_ambiguity 使用 config 的 ambiguity_margin"""
        resolver_008 = Resolver(ambiguity_margin=0.08)
        resolver_010 = Resolver(ambiguity_margin=0.10)

        # 分数差 0.09 的候选
        candidates = [
            self._make_soft_candidate(score=0.70),
            self._make_soft_candidate(score=0.61),
        ]
        sorted_candidates = resolver_008.sort_candidates_by_score(candidates)

        # margin=0.08: 0.09 >= 0.08 → 不模糊
        assert resolver_008.check_ambiguity(sorted_candidates) is False

        # margin=0.10: 0.09 < 0.10 → 模糊
        assert resolver_010.check_ambiguity(sorted_candidates) is True
