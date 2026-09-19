"""测试跨 layout type/opcode 后处理

验证 DetectionPipeline 对跨 layout type/opcode 字段的后处理功能。
"""

import pytest
from semantic_detector.pipeline.pipeline import DetectionPipeline
from semantic_detector.profiling.profile_builder import FieldProfile
from semantic_detector.contracts import Direction, SemanticPrediction
from semantic_detector.config import Config
from semantic_detector.io.exporters import (
    export_predictions_to_jsonl,
    read_semantic_predictions_from_jsonl,
)


class TestTypeOpcodePostprocessR285:
    """R285: 确保 type/opcode 后处理保留原 SemanticPrediction 身份和证据

    04 任务表 R285：
    "确保 type/opcode 后处理保留原 SemanticPrediction 身份和证据 | pipeline.py;
     test_pipeline_type_postprocess.py | 升级后导出 | run_id/FieldKey 不变，alternatives 不丢"

    教程 10.5：跨 layout 后处理必须返回新的 SemanticPrediction，同时保留原 prediction 的
    evidence 和 alternatives，不得丢失字段身份。

    验证维度：
    - run_id 不变（pipeline 实例级身份）
    - FieldKey 不变（layout_id + direction + field_index）
    - alternatives 不丢（原备选证据列表保留）
    - evidence[0] 被替换为 type_or_opcode candidate，evidence[1:] 保留原 alternatives
    - 升级后导出 JSONL round-trip 等价
    """

    def _make_profile(
        self,
        layout_id: str,
        dominant_value_hex: str,
        dominant_value_ratio: float = 0.8,
        width_mode: int = 1,
        field_index: int = 0,
    ):
        return FieldProfile(
            layout_id=layout_id,
            direction=Direction.REQUEST.value,
            field_index=field_index,
            sample_count=10,
            width_min=width_mode,
            width_max=width_mode,
            width_mode=width_mode,
            fixed_width=True,
            start_mode=0,
            dominant_value_ratio=dominant_value_ratio,
            dominant_value_hex=dominant_value_hex,
            dominant_value_count=8,
        )

    def _make_upgradable_profiles(self):
        """构造可触发 type/opcode 升级的两个 layout（03/06，一一对应）"""
        return [
            self._make_profile("layout_read", "03"),
            self._make_profile("layout_write", "06"),
        ]

    def test_run_id_preserved_after_upgrade(self):
        """R285: 升级后 run_id 不变（pipeline 实例级身份）"""
        pipeline = DetectionPipeline(run_id="r285-run-id-fixed")
        predictions = pipeline.detect_fields(self._make_upgradable_profiles())

        assert len(predictions) == 2
        for p in predictions:
            assert p.run_id == "r285-run-id-fixed"

    def test_field_key_preserved_after_upgrade(self):
        """R285: FieldKey（layout_id + direction + field_index）不变"""
        pipeline = DetectionPipeline()
        profiles = self._make_upgradable_profiles()
        predictions = pipeline.detect_fields(profiles)

        assert len(predictions) == 2
        for profile, prediction in zip(profiles, predictions):
            assert prediction.layout_id == profile.layout_id
            assert prediction.direction.value == profile.direction
            assert prediction.field_index == profile.field_index

    def test_alternatives_preserved_after_upgrade(self):
        """R285: alternatives 不丢（原备选证据列表保留）

        升级前 alternatives 由 resolver.resolve_with_context 返回；
        升级后 _replace_primary_evidence 只替换 evidence[0]，保留 evidence[1:]。
        alternatives 序列化字段应保持不变（来自原 alternatives）。
        """
        pipeline = DetectionPipeline()
        profiles = self._make_upgradable_profiles()

        # 先获取未升级的 predictions（单字段 detect_field 不触发跨 layout 后处理）
        pre_predictions = [pipeline.detect_field(p) for p in profiles]
        pre_alternatives = [p.alternatives for p in pre_predictions]

        # 触发跨 layout 后处理
        post_predictions = pipeline.detect_fields(profiles)

        assert len(post_predictions) == 2
        # 找到被升级的 prediction（coarse_label == type_control）
        upgraded_count = 0
        for idx, post_p in enumerate(post_predictions):
            if post_p.coarse_label == "type_control":
                upgraded_count += 1
                # alternatives 元组应与升级前一致
                assert post_p.alternatives == pre_alternatives[idx]
        assert upgraded_count >= 1, "至少一个 prediction 应被升级为 type_control"

    def test_evidence_first_replaced_rest_preserved(self):
        """R285: evidence[0] 替换为 type_or_opcode candidate，evidence[1:] 保留原 alternatives"""
        pipeline = DetectionPipeline()
        profiles = self._make_upgradable_profiles()

        pre_predictions = [pipeline.detect_field(p) for p in profiles]
        post_predictions = pipeline.detect_fields(profiles)

        for idx, (pre_p, post_p) in enumerate(zip(pre_predictions, post_predictions)):
            if post_p.coarse_label == "type_control":
                # evidence[0] 已替换为 type_or_opcode candidate
                assert post_p.evidence[0].coarse_label == "type_control"
                assert post_p.evidence[0].fine_label == "type_or_opcode_candidate"
                # evidence[1:] 与升级前一致（原 alternatives 作为 evidence[1:]）
                assert post_p.evidence[1:] == pre_p.evidence[1:]

    def test_prediction_status_candidate_after_upgrade(self):
        """R285: 升级后 prediction_status 为 candidate（type/opcode 是 soft evidence）"""
        pipeline = DetectionPipeline()
        predictions = pipeline.detect_fields(self._make_upgradable_profiles())

        for p in predictions:
            if p.coarse_label == "type_control":
                assert p.prediction_status == "candidate"
                assert p.abstained is False

    def test_export_round_trip_after_upgrade(self, tmp_path):
        """R285 完成标准：升级后导出 JSONL round-trip 等价

        教程 10.5：跨 layout 后处理必须返回新的 SemanticPrediction，保留身份和证据。
        round-trip 验证：导出→读回后，run_id/FieldKey/coarse_label/fine_label/
        confidence/abstained/prediction_status/evidence/alternatives 全部等价。
        """
        pipeline = DetectionPipeline(run_id="r285-round-trip")
        predictions = pipeline.detect_fields(self._make_upgradable_profiles())

        output_path = tmp_path / "r285_predictions.jsonl"
        export_predictions_to_jsonl(predictions, output_path)

        read_back = read_semantic_predictions_from_jsonl(output_path)

        assert len(read_back) == len(predictions)
        for original, restored in zip(predictions, read_back):
            assert restored.run_id == original.run_id
            assert restored.layout_id == original.layout_id
            assert restored.direction == original.direction
            assert restored.field_index == original.field_index
            assert restored.coarse_label == original.coarse_label
            assert restored.fine_label == original.fine_label
            assert restored.confidence == original.confidence
            assert restored.abstained == original.abstained
            assert restored.prediction_status == original.prediction_status
            # evidence 元组逐项等价
            assert len(restored.evidence) == len(original.evidence)
            for r_e, o_e in zip(restored.evidence, original.evidence):
                assert r_e.detector == o_e.detector
                assert r_e.coarse_label == o_e.coarse_label
                assert r_e.fine_label == o_e.fine_label
                assert r_e.is_hard_evidence == o_e.is_hard_evidence
                assert r_e.score == o_e.score
                assert r_e.reason_code == o_e.reason_code
            # alternatives 元组逐项等价
            assert restored.alternatives == original.alternatives

    def test_upgraded_evidence_details_contain_layout_values(self, tmp_path):
        """R285: 升级后 evidence[0] 的 details 包含 R284 新增的 layout_values

        验证 R283-R284 的修复在 pipeline 后处理路径中完整生效：
        - R283: 使用真实 dominant_value_hex（03/06）而非 b'\\x00'
        - R284: details 包含 layout_values/layout_count/unique_value_count
        """
        pipeline = DetectionPipeline()
        predictions = pipeline.detect_fields(self._make_upgradable_profiles())

        upgraded = [p for p in predictions if p.coarse_label == "type_control"]
        assert len(upgraded) >= 1

        for p in upgraded:
            details = p.evidence[0].details
            assert "layout_values" in details
            assert "layout_count" in details
            assert "unique_value_count" in details
            assert "alignment_key" in details
            # layout_values 应包含 03 和 06（R283 真实 hex 值）
            assert details["layout_values"] == {
                "layout_read": "03",
                "layout_write": "06",
            }
            assert details["layout_count"] == 2
            assert details["unique_value_count"] == 2

    def test_no_upgrade_preserves_identity_completely(self):
        """R285: 未升级的 prediction 身份和证据完全保留（对照组）

        构造相同 dominant_value_hex（非一一对应，不触发升级），
        验证 predictions 与 detect_field 单字段结果完全一致。
        """
        pipeline = DetectionPipeline()
        profiles = [
            self._make_profile("layout_a", "01"),
            self._make_profile("layout_b", "01"),  # 相同值，不触发升级
        ]

        pre_predictions = [pipeline.detect_field(p) for p in profiles]
        post_predictions = pipeline.detect_fields(profiles)

        for pre_p, post_p in zip(pre_predictions, post_predictions):
            # 未升级：身份、coarse_label、evidence、alternatives 全部一致
            assert post_p.run_id == pre_p.run_id
            assert post_p.layout_id == pre_p.layout_id
            assert post_p.direction == pre_p.direction
            assert post_p.field_index == pre_p.field_index
            assert post_p.coarse_label == pre_p.coarse_label
            assert post_p.fine_label == pre_p.fine_label
            assert post_p.confidence == pre_p.confidence
            assert post_p.abstained == pre_p.abstained
            assert post_p.prediction_status == pre_p.prediction_status
            assert post_p.evidence == pre_p.evidence
            assert post_p.alternatives == pre_p.alternatives


class TestTypeOpcodePostprocessR283:
    """R283: type/opcode 后处理读取 dominant_value_hex，不再使用 b'\\x00' 占位符

    04 任务表 R283：
    "修改 type/opcode 后处理读取 dominant_value_hex | pipeline/pipeline.py;
     test_pipeline_type_postprocess.py | 两个 layout 03/06 | 不再使用 b'\\x00'"

    验证：
    - 不同 layout 有不同 dominant_value_hex（一一对应）时输出 type_control
    - 不同 layout 有相同 dominant_value_hex（非一一对应）时不出 type_control
    - dominant_value_hex 为 None（tie 场景）时跳过该 layout
    - dominant_value_ratio <= 0.5 时跳过
    """

    def _make_profile(
        self,
        layout_id: str,
        dominant_value_hex: str | None,
        dominant_value_ratio: float = 0.8,
        width_mode: int = 1,
        field_index: int = 0,
    ):
        return FieldProfile(
            layout_id=layout_id,
            direction=str(Direction.REQUEST),
            field_index=field_index,
            sample_count=10,
            width_min=width_mode,
            width_max=width_mode,
            width_mode=width_mode,
            fixed_width=True,
            start_mode=0,
            dominant_value_ratio=dominant_value_ratio,
            dominant_value_hex=dominant_value_hex,
            dominant_value_count=8,
        )

    def test_one_to_one_mapping_outputs_type_control(self):
        """不同 layout 有不同 dominant_value_hex（一一对应）时输出 type_control"""
        pipeline = DetectionPipeline()
        profiles = [
            self._make_profile("layout_0", "01"),
            self._make_profile("layout_1", "02"),
            self._make_profile("layout_2", "03"),
        ]

        predictions = pipeline.detect_fields(profiles)

        assert len(predictions) == 3
        # 至少一个预测被升级为 type_control
        type_control_count = sum(
            1 for p in predictions if p.coarse_label == "type_control"
        )
        assert type_control_count >= 1

    def test_same_dominant_value_not_one_to_one(self):
        """不同 layout 有相同 dominant_value_hex（非一一对应）时不出 type_control"""
        pipeline = DetectionPipeline()
        profiles = [
            self._make_profile("layout_0", "01"),
            self._make_profile("layout_1", "01"),  # 相同值
            self._make_profile("layout_2", "01"),  # 相同值
        ]

        predictions = pipeline.detect_fields(profiles)

        assert len(predictions) == 3
        # 非一一对应，不应输出 type_control
        type_control_count = sum(
            1 for p in predictions if p.coarse_label == "type_control"
        )
        assert type_control_count == 0

    def test_dominant_value_hex_none_skipped(self):
        """dominant_value_hex 为 None（tie 场景）时跳过该 layout"""
        pipeline = DetectionPipeline()
        profiles = [
            self._make_profile("layout_0", "01"),
            self._make_profile("layout_1", None),  # tie，跳过
            self._make_profile("layout_2", "03"),
        ]

        predictions = pipeline.detect_fields(profiles)

        assert len(predictions) == 3
        # layout_1 被跳过，但 layout_0 和 layout_2 仍一一对应
        type_control_count = sum(
            1 for p in predictions if p.coarse_label == "type_control"
        )
        # layout_0 和 layout_2 不同值，应触发后处理
        assert type_control_count >= 1

    def test_all_dominant_value_hex_none_no_type_control(self):
        """所有 layout 的 dominant_value_hex 都为 None 时不出 type_control"""
        pipeline = DetectionPipeline()
        profiles = [
            self._make_profile("layout_0", None),
            self._make_profile("layout_1", None),
            self._make_profile("layout_2", None),
        ]

        predictions = pipeline.detect_fields(profiles)

        assert len(predictions) == 3
        type_control_count = sum(
            1 for p in predictions if p.coarse_label == "type_control"
        )
        assert type_control_count == 0

    def test_dominant_value_ratio_below_threshold_skipped(self):
        """dominant_value_ratio <= 0.5 时跳过"""
        pipeline = DetectionPipeline()
        profiles = [
            self._make_profile("layout_0", "01", dominant_value_ratio=0.4),
            self._make_profile("layout_1", "02", dominant_value_ratio=0.4),
            self._make_profile("layout_2", "03", dominant_value_ratio=0.4),
        ]

        predictions = pipeline.detect_fields(profiles)

        assert len(predictions) == 3
        type_control_count = sum(
            1 for p in predictions if p.coarse_label == "type_control"
        )
        assert type_control_count == 0

    def test_audit_fix_bug1_low_threshold_config_no_missed_detection(self):
        """审计修复 BUG-1: 低阈值 config 不应导致漏检

        当 config.type_opcode_min_dominant_ratio = 0.4 时，
        dominant_value_ratio = 0.45 的 profile 应该进入 type/opcode 检测
        （修复前预过滤硬编码 0.5 会错误丢弃该 profile）。
        """
        # 构造低阈值配置
        low_threshold_config = Config(type_opcode_min_dominant_ratio=0.4)
        pipeline = DetectionPipeline(config=low_threshold_config)
        profiles = [
            self._make_profile("layout_0", "01", dominant_value_ratio=0.45),
            self._make_profile("layout_1", "02", dominant_value_ratio=0.45),
            self._make_profile("layout_2", "03", dominant_value_ratio=0.45),
        ]

        predictions = pipeline.detect_fields(profiles)

        assert len(predictions) == 3
        # 修复前：预过滤用硬编码 0.5 会丢弃所有 profile，type_control_count=0（漏检）
        # 修复后：预过滤用 config 0.4，profile 通过，type_control 应被检测出
        type_control_count = sum(
            1 for p in predictions if p.coarse_label == "type_control"
        )
        assert type_control_count >= 1, (
            "BUG-1 回归：低阈值 config 下应检测到 type_control，但被预过滤错误丢弃"
        )

    def test_audit_fix_bug1_high_threshold_config_filters_profile(self):
        """审计修复 BUG-1: 高阈值 config 应正确过滤

        当 config.type_opcode_min_dominant_ratio = 0.6 时，
        dominant_value_ratio = 0.55 的 profile 应被预过滤丢弃。
        """
        high_threshold_config = Config(type_opcode_min_dominant_ratio=0.6)
        pipeline = DetectionPipeline(config=high_threshold_config)
        profiles = [
            self._make_profile("layout_0", "01", dominant_value_ratio=0.55),
            self._make_profile("layout_1", "02", dominant_value_ratio=0.55),
            self._make_profile("layout_2", "03", dominant_value_ratio=0.55),
        ]

        predictions = pipeline.detect_fields(profiles)

        assert len(predictions) == 3
        type_control_count = sum(
            1 for p in predictions if p.coarse_label == "type_control"
        )
        assert type_control_count == 0, (
            "BUG-1 回归：高阈值 config 下应过滤掉 profile，不应检测到 type_control"
        )

    def test_two_byte_width_one_to_one_mapping(self):
        """2 字节 width 一一对应映射输出 type_control"""
        pipeline = DetectionPipeline()
        profiles = [
            self._make_profile("layout_0", "0102", width_mode=2),
            self._make_profile("layout_1", "0304", width_mode=2),
            self._make_profile("layout_2", "0506", width_mode=2),
        ]

        predictions = pipeline.detect_fields(profiles)

        assert len(predictions) == 3
        type_control_count = sum(
            1 for p in predictions if p.coarse_label == "type_control"
        )
        assert type_control_count >= 1

    def test_real_hex_values_not_zero_placeholder(self):
        """R283 核心验证：使用真实 hex 值而非 b'\\x00' 占位符

        构造两个 layout，dominant_value_hex 分别为 "03" 和 "06"（教程示例值），
        验证 type/opcode 后处理能正确识别一一对应映射。
        如果仍使用 b'\\x00'，所有 layout 值相同，不会触发一一对应映射。
        """
        pipeline = DetectionPipeline()
        profiles = [
            self._make_profile("layout_0", "03"),
            self._make_profile("layout_1", "06"),
        ]

        predictions = pipeline.detect_fields(profiles)

        assert len(predictions) == 2
        # 不同 hex 值，应触发一一对应映射
        type_control_count = sum(
            1 for p in predictions if p.coarse_label == "type_control"
        )
        assert type_control_count >= 1

        # 验证 evidence 的 fine_label
        for p in predictions:
            if p.coarse_label == "type_control":
                assert p.fine_label == "type_or_opcode_candidate"
                assert p.prediction_status == "candidate"


class TestTypeOpcodePostprocess:
    """type/opcode 后处理测试"""
    
    def test_postprocess_single_layout(self):
        """测试单个 layout 不触发后处理"""
        pipeline = DetectionPipeline()
        
        profiles = [
            FieldProfile(
                layout_id="layout_0",
                direction=str(Direction.REQUEST),
                field_index=0,
                sample_count=10,
                width_min=1,
                width_max=1,
                width_mode=1,
                fixed_width=True,
                start_mode=0,
                dominant_value_ratio=1.0
            )
        ]
        
        predictions = pipeline.detect_fields(profiles)
        
        assert len(predictions) == 1
        assert predictions[0] is not None
    
    def test_postprocess_multiple_layouts_same_field(self):
        """测试多个 layout 相同字段触发后处理"""
        pipeline = DetectionPipeline()
        
        profiles = [
            FieldProfile(
                layout_id="layout_0",
                direction=str(Direction.REQUEST),
                field_index=0,
                sample_count=10,
                width_min=1,
                width_max=1,
                width_mode=1,
                fixed_width=True,
                start_mode=0,
                dominant_value_ratio=1.0
            ),
            FieldProfile(
                layout_id="layout_1",
                direction=str(Direction.REQUEST),
                field_index=0,
                sample_count=10,
                width_min=1,
                width_max=1,
                width_mode=1,
                fixed_width=True,
                start_mode=0,
                dominant_value_ratio=1.0
            ),
            FieldProfile(
                layout_id="layout_2",
                direction=str(Direction.REQUEST),
                field_index=0,
                sample_count=10,
                width_min=1,
                width_max=1,
                width_mode=1,
                fixed_width=True,
                start_mode=0,
                dominant_value_ratio=1.0
            )
        ]
        
        predictions = pipeline.detect_fields(profiles)
        
        assert len(predictions) == 3
        for prediction in predictions:
            assert prediction is not None
    
    def test_postprocess_different_fields_not_grouped(self):
        """测试不同字段不被分组"""
        pipeline = DetectionPipeline()
        
        profiles = [
            FieldProfile(
                layout_id="layout_0",
                direction=str(Direction.REQUEST),
                field_index=0,
                sample_count=10,
                width_min=1,
                width_max=1,
                width_mode=1,
                fixed_width=True,
                start_mode=0,
                dominant_value_ratio=1.0
            ),
            FieldProfile(
                layout_id="layout_1",
                direction=str(Direction.REQUEST),
                field_index=1,
                sample_count=10,
                width_min=1,
                width_max=1,
                width_mode=1,
                fixed_width=True,
                start_mode=0,
                dominant_value_ratio=1.0
            )
        ]
        
        predictions = pipeline.detect_fields(profiles)
        
        assert len(predictions) == 2
        for prediction in predictions:
            assert prediction is not None
    
    def test_postprocess_width_gt_2_excluded(self):
        """测试宽度 > 2 被排除"""
        pipeline = DetectionPipeline()
        
        profiles = [
            FieldProfile(
                layout_id="layout_0",
                direction=str(Direction.REQUEST),
                field_index=0,
                sample_count=10,
                width_min=4,
                width_max=4,
                width_mode=4,
                fixed_width=True,
                start_mode=0,
                dominant_value_ratio=1.0
            ),
            FieldProfile(
                layout_id="layout_1",
                direction=str(Direction.REQUEST),
                field_index=0,
                sample_count=10,
                width_min=4,
                width_max=4,
                width_mode=4,
                fixed_width=True,
                start_mode=0,
                dominant_value_ratio=1.0
            )
        ]
        
        predictions = pipeline.detect_fields(profiles)
        
        assert len(predictions) == 2
        for prediction in predictions:
            assert prediction is not None
    
    def test_postprocess_preserves_predictions(self):
        """测试后处理保持预测数量"""
        pipeline = DetectionPipeline()
        
        profiles = [
            FieldProfile(
                layout_id=f"layout_{i}",
                direction=str(Direction.REQUEST),
                field_index=i % 2,
                sample_count=10,
                width_min=1,
                width_max=1,
                width_mode=1,
                fixed_width=True,
                start_mode=0,
                dominant_value_ratio=1.0
            )
            for i in range(6)
        ]
        
        predictions = pipeline.detect_fields(profiles)

        assert len(predictions) == len(profiles)


class TestTypeOpcodeNonzeroOffsetR326:
    """R326: 非零偏移 Type/Opcode 失败回归测试

    06 计划 R326：
    "用测试精确复现 start=7, width=1 被误当成宽度 7 的错误"

    V2 审计 HIGH-1：Pipeline 构造 alignment key 顺序为
    (direction, field_index, width_mode, start_mode)，
    但 detect_type_or_opcode 把 alignment_key[3] 当作 width。
    对 start_mode=7, width_mode=1 的 F4 字段，[3]=7 被当作 width，
    7 > 2 触发排除，合法功能码永远无法识别。

    本测试在 R327-R329 修复前必须失败，失败原因正是 tuple 顺序错误。
    修复后（具名 TypeOpcodeAlignmentKey）应通过。
    """

    def _make_nonzero_offset_profile(
        self,
        layout_id: str,
        dominant_value_hex: str,
        field_index: int = 4,
        start_mode: int = 7,
        width_mode: int = 1,
    ):
        """构造 Modbus 风格 F4 功能码字段（非零偏移）

        教程示例：
        - layout_read_request.F4  主值 03，start=7, width=1
        - layout_write_request.F4 主值 06，start=7, width=1
        """
        return FieldProfile(
            layout_id=layout_id,
            direction=Direction.REQUEST.value,
            field_index=field_index,
            sample_count=10,
            width_min=width_mode,
            width_max=width_mode,
            width_mode=width_mode,
            fixed_width=True,
            start_mode=start_mode,
            dominant_value_ratio=0.9,
            dominant_value_hex=dominant_value_hex,
            dominant_value_count=9,
        )

    def test_nonzero_offset_type_opcode_candidate_generated(self):
        """R326 核心断言：start=7,width=1 的 F4 应产生 type_control 候选

        修复前预期失败：
        - Pipeline 创建 key=(request, 4, 1, 7)
        - detect_type_or_opcode 把 alignment_key[3]=7 当作 width
        - 7 > 2 被错误排除，返回 None
        - 无 type_control 候选生成

        修复后预期通过：
        - 具名 key.width_mode=1 <= 2，放行
        - 具名 key.start_mode=7 仅作位置一致性证据
        - 两个 layout 主值 03/06 一一对应 -> type_control candidate
        """
        pipeline = DetectionPipeline()
        profiles = [
            self._make_nonzero_offset_profile(
                "layout_read_request", "03",
            ),
            self._make_nonzero_offset_profile(
                "layout_write_request", "06",
            ),
        ]

        predictions = pipeline.detect_fields(profiles)

        assert len(predictions) == 2
        type_control_count = sum(
            1 for p in predictions if p.coarse_label == "type_control"
        )
        # 修复前：type_control_count == 0（被 width=7 错误排除）
        # 修复后：type_control_count >= 1（具名字段正确识别 width=1）
        assert type_control_count >= 1, (
            "R326 失败：start=7, width=1 的 F4 功能码未生成 type_control 候选。"
            "原因定位：Pipeline 创建 alignment key 顺序为 "
            "(direction, field_index, width_mode, start_mode)，"
            "但 detect_type_or_opcode 把 alignment_key[3] 当作 width，"
            "start_mode=7 被误判为宽度 7，触发 width > 2 排除。"
            "需在 R327-R329 用具名 TypeOpcodeAlignmentKey 替换裸 tuple。"
        )

    def test_nonzero_offset_evidence_contains_real_hex_values(self):
        """R326 证据验证：非零偏移场景的 evidence 应含真实 03/06 而非占位符

        修复前：根本不会生成 evidence（被 width=7 排除）
        修复后：evidence[0].details.layout_values 应含 03 和 06
        """
        pipeline = DetectionPipeline()
        profiles = [
            self._make_nonzero_offset_profile(
                "layout_read_request", "03",
            ),
            self._make_nonzero_offset_profile(
                "layout_write_request", "06",
            ),
        ]

        predictions = pipeline.detect_fields(profiles)

        upgraded = [p for p in predictions if p.coarse_label == "type_control"]
        assert len(upgraded) >= 1, (
            "R326 失败：非零偏移 F4 未升级为 type_control，"
            "无法验证 evidence 含真实 hex 值。"
            "根因：alignment key tuple 顺序错误，width_mode=1 被当作 start，"
            "start_mode=7 被当作 width 并触发 >2 排除。"
        )

        for p in upgraded:
            details = p.evidence[0].details
            assert "layout_values" in details
            assert details["layout_values"] == {
                "layout_read_request": "03",
                "layout_write_request": "06",
            }

    def test_nonzero_offset_width_one_not_treated_as_seven(self):
        """R326 反例断言：width=1 的字段不得被当作 width=7 排除

        直接调用 detect_type_or_opcode，传入 Modbus 风格对齐键，
        验证 width<=2 放行。修复前 alignment_key[3]=7 被当作 width 而错误排除。

        R328 说明：本测试传入 TypeOpcodeAlignmentKey（具名键），由 R328 兼容层
        _extract_alignment_fields 提取 width_mode=1，放行通过。R329 将删除 tuple
        分支，本测试保留具名键调用形态。
        """
        from semantic_detector.detectors.type_opcode import detect_type_or_opcode
        from semantic_detector.contracts import TypeOpcodeAlignmentKey, Direction

        layout_dominant_values = {
            "layout_read_request": bytes.fromhex("03"),
            "layout_write_request": bytes.fromhex("06"),
        }
        # R328：用具名键，消除 tuple 索引歧义
        alignment_key = TypeOpcodeAlignmentKey(
            direction=Direction.REQUEST,
            field_index=4,
            start_mode=7,
            width_mode=1,
        )

        evidence = detect_type_or_opcode(layout_dominant_values, alignment_key)

        # 修复前：alignment_key[3]=7 被当作 width，7 > 2 返回 None
        # 修复后：key.width_mode=1 <= 2 放行，一一对应映射 -> 返回 evidence
        assert evidence is not None, (
            "R326 失败：detect_type_or_opcode 对 width=1, start=7 的字段返回 None。"
            "原因定位：alignment_key[3]=7 被当作 width，"
            "触发 'width > 2 -> return None' 分支。"
            "实际 width=1（alignment_key[2]），start_mode=7（alignment_key[3]）。"
            "需在 R329 让 detector 按具名字段读取 width_mode 而非 tuple 索引。"
        )
        assert evidence.coarse_label == "type_control"
        assert evidence.fine_label == "type_or_opcode_candidate"


class TestTypeOpcodeAlignmentKeyBuilderR328:
    """R328: build_type_opcode_alignment_key 键构造断言

    06 计划 R328：
    "新增键构造断言：start=7, width=1 → key.start_mode == 7, key.width_mode == 1"

    V2 审计 HIGH-1 修复核心：Pipeline 唯一允许的对齐键构造函数
    build_type_opcode_alignment_key(profile) 必须从 profile 明确读取
    direction/field_index/start_mode/width_mode 四个具名字段，禁止位置索引。

    本测试直接断言构造结果，与 R326 端到端测试形成双层保护：
    - R326：Pipeline 端到端验证（非零偏移 F4 应生成 type_control 候选）
    - R328：构造函数单元断言（start_mode/width_mode 不被位置颠倒）
    """

    def _make_profile(
        self,
        layout_id: str = "layout_read_request",
        direction: str = Direction.REQUEST.value,
        field_index: int = 4,
        start_mode: int = 7,
        width_mode: int = 1,
        dominant_value_hex: str = "03",
    ):
        return FieldProfile(
            layout_id=layout_id,
            direction=direction,
            field_index=field_index,
            sample_count=10,
            width_min=width_mode,
            width_max=width_mode,
            width_mode=width_mode,
            fixed_width=True,
            start_mode=start_mode,
            dominant_value_ratio=0.9,
            dominant_value_hex=dominant_value_hex,
            dominant_value_count=9,
        )

    def test_start_mode_seven_preserved(self):
        """R328 核心断言：start=7 必须保留在 key.start_mode，不得被当作 width

        修复前根因：Pipeline 拼 tuple (direction, field_index, width_mode, start_mode)
        = ("request", 4, 1, 7)，detector 把 [3]=7 当 width，触发 width>2 排除。
        """
        from semantic_detector.pipeline.pipeline import build_type_opcode_alignment_key

        profile = self._make_profile(start_mode=7, width_mode=1)
        key = build_type_opcode_alignment_key(profile)

        assert key.start_mode == 7, (
            "R328 失败：key.start_mode 应为 7，实际为 "
            f"{key.start_mode}。"
            "build_type_opcode_alignment_key 必须从 profile.start_mode 读取，"
            "不得与 width_mode 位置颠倒。"
        )

    def test_width_mode_one_preserved(self):
        """R328 核心断言：width=1 必须保留在 key.width_mode，不得被当作 start

        修复前根因：detector 把 alignment_key[3] 当 width，[3]=7 触发排除，
        实际 width=1 应放行。
        """
        from semantic_detector.pipeline.pipeline import build_type_opcode_alignment_key

        profile = self._make_profile(start_mode=7, width_mode=1)
        key = build_type_opcode_alignment_key(profile)

        assert key.width_mode == 1, (
            "R328 失败：key.width_mode 应为 1，实际为 "
            f"{key.width_mode}。"
            "build_type_opcode_alignment_key 必须从 profile.width_mode 读取，"
            "不得与 start_mode 位置颠倒。"
        )

    def test_named_fields_not_position_swapped(self):
        """R328 综合断言：start=7, width=1 不被位置颠倒

        同时验证四个具名字段，确保 build_type_opcode_alignment_key 完全按
        具名字段读取，不依赖位置索引。
        """
        from semantic_detector.pipeline.pipeline import build_type_opcode_alignment_key

        profile = self._make_profile(
            field_index=4,
            start_mode=7,
            width_mode=1,
        )
        key = build_type_opcode_alignment_key(profile)

        assert key.direction == Direction.REQUEST
        assert key.field_index == 4
        assert key.start_mode == 7
        assert key.width_mode == 1

    def test_returns_type_opcode_alignment_key_instance(self):
        """R328 类型断言：构造函数必须返回 TypeOpcodeAlignmentKey 实例

        禁止返回裸 tuple。Pipeline 不再手工拼 tuple。
        """
        from semantic_detector.pipeline.pipeline import build_type_opcode_alignment_key
        from semantic_detector.contracts import TypeOpcodeAlignmentKey

        profile = self._make_profile()
        key = build_type_opcode_alignment_key(profile)

        assert isinstance(key, TypeOpcodeAlignmentKey), (
            "R328 失败：build_type_opcode_alignment_key 必须返回 "
            "TypeOpcodeAlignmentKey 实例，禁止返回 tuple。"
            f"实际类型：{type(key).__name__}"
        )

    def test_invalid_direction_falls_back_to_unknown(self):
        """R328 鲁棒性断言：非法 direction 降级为 UNKNOWN 而非崩溃

        教程约束：非法方向不得让 Pipeline 崩溃，降级为 UNKNOWN 后由
        TypeOpcodeAlignmentKey.__post_init__ 验证 Direction 枚举类型。
        """
        from semantic_detector.pipeline.pipeline import build_type_opcode_alignment_key

        profile = self._make_profile(direction="invalid_direction")
        key = build_type_opcode_alignment_key(profile)

        assert key.direction == Direction.UNKNOWN

    def test_keys_group_only_when_all_four_named_fields_equal(self):
        """R328 分组语义断言：四个具名字段全等才分到同一组

        验证 TypeOpcodeAlignmentKey 作为 dict key 的分组语义：
        - direction 不同 → 不同组
        - field_index 不同 → 不同组
        - start_mode 不同 → 不同组
        - width_mode 不同 → 不同组
        """
        from semantic_detector.pipeline.pipeline import build_type_opcode_alignment_key

        base = self._make_profile(
            direction=Direction.REQUEST.value,
            field_index=4,
            start_mode=7,
            width_mode=1,
        )
        key_base = build_type_opcode_alignment_key(base)

        # direction 不同
        diff_direction = self._make_profile(
            direction=Direction.RESPONSE.value,
            field_index=4,
            start_mode=7,
            width_mode=1,
        )
        assert build_type_opcode_alignment_key(diff_direction) != key_base

        # field_index 不同
        diff_field_index = self._make_profile(
            field_index=5,
            start_mode=7,
            width_mode=1,
        )
        assert build_type_opcode_alignment_key(diff_field_index) != key_base

        # start_mode 不同
        diff_start = self._make_profile(
            start_mode=8,
            width_mode=1,
        )
        assert build_type_opcode_alignment_key(diff_start) != key_base

        # width_mode 不同
        diff_width = self._make_profile(
            start_mode=7,
            width_mode=2,
        )
        assert build_type_opcode_alignment_key(diff_width) != key_base

        # 全等才同组
        same = self._make_profile(
            layout_id="layout_other",
            direction=Direction.REQUEST.value,
            field_index=4,
            start_mode=7,
            width_mode=1,
            dominant_value_hex="06",
        )
        assert build_type_opcode_alignment_key(same) == key_base


class TestTypeOpcodeResolverR332:
    """R332: Type/Opcode 证据重新进入 Resolver（HIGH-2 修复）

    06 计划 R332 验收规则：
    - 原 constant evidence 仍在 evidence
    - type_control 可进入 alternatives
    - type_control 低于 min_score 时不能成为最终结果
    - type_control 不得覆盖强 length/timestamp
    - 最终选择 type_control 时，constant 仍可作为"单 layout 内稳定"的支持证据
    - prediction 的 run_id 和 FieldKey 不变

    核心变更：禁止 _postprocess_type_opcode 直接用 _replace_primary_evidence
    替换 SemanticPrediction。Type/Opcode 证据必须与原字段全部 DetectorEvidence
    一起送入 Resolver 仲裁。
    """

    def _make_profile(
        self,
        layout_id: str,
        dominant_value_hex: str,
        dominant_value_ratio: float = 1.0,
        width_mode: int = 1,
        field_index: int = 0,
        start_mode: int = 0,
    ):
        """构造可触发 constant（hard）+ type_control（soft）的 profile

        dominant_value_ratio=1.0 确保 constant 检测器产生 hard evidence
        （constant_support=0.98，1.0 >= 0.98）。
        """
        return FieldProfile(
            layout_id=layout_id,
            direction=Direction.REQUEST.value,
            field_index=field_index,
            sample_count=10,
            width_min=width_mode,
            width_max=width_mode,
            width_mode=width_mode,
            fixed_width=True,
            start_mode=start_mode,
            dominant_value_ratio=dominant_value_ratio,
            dominant_value_hex=dominant_value_hex,
            dominant_value_count=10,
        )

    def _make_upgradable_profiles(self):
        """构造可触发 type/opcode 升级的两个 layout（03/06，一一对应）

        dominant_value_ratio=1.0 触发 constant hard evidence。
        跨 layout 03/06 一一对应触发 type_control soft evidence。
        """
        return [
            self._make_profile("layout_read", "03"),
            self._make_profile("layout_write", "06"),
        ]

    def test_type_control_wins_through_resolver(self):
        """R332: type_control 通过 Resolver 仲裁胜出（不绕过 Resolver）"""
        pipeline = DetectionPipeline()
        predictions = pipeline.detect_fields(self._make_upgradable_profiles())

        for p in predictions:
            assert p.coarse_label == "type_control"
            assert p.fine_label == "type_or_opcode_candidate"

    def test_constant_evidence_still_in_evidence(self):
        """R332: 原 constant evidence 仍在 evidence（作为 alternative）"""
        pipeline = DetectionPipeline()
        predictions = pipeline.detect_fields(self._make_upgradable_profiles())

        for p in predictions:
            if p.coarse_label == "type_control":
                # constant 应在 evidence 中（作为 alternative）
                evidence_labels = [e.coarse_label for e in p.evidence]
                assert "constant" in evidence_labels, (
                    f"constant evidence 应保留在 evidence 中，实际: {evidence_labels}"
                )

    def test_constant_in_alternatives_when_type_control_wins(self):
        """R332: type_control 胜出时 constant 作为 alternative（支持证据）"""
        pipeline = DetectionPipeline()
        predictions = pipeline.detect_fields(self._make_upgradable_profiles())

        for p in predictions:
            if p.coarse_label == "type_control":
                alt_labels = [a["coarse_label"] for a in p.alternatives]
                assert "constant" in alt_labels, (
                    f"constant 应在 alternatives 中，实际: {alt_labels}"
                )

    def test_run_id_preserved_after_resolver(self):
        """R332: Resolver 仲裁后 run_id 不变"""
        pipeline = DetectionPipeline(run_id="r332-run-id-fixed")
        predictions = pipeline.detect_fields(self._make_upgradable_profiles())

        for p in predictions:
            assert p.run_id == "r332-run-id-fixed"

    def test_field_key_preserved_after_resolver(self):
        """R332: Resolver 仲裁后 FieldKey 不变"""
        pipeline = DetectionPipeline()
        profiles = self._make_upgradable_profiles()
        predictions = pipeline.detect_fields(profiles)

        for profile, prediction in zip(profiles, predictions):
            assert prediction.layout_id == profile.layout_id
            assert prediction.direction.value == profile.direction
            assert prediction.field_index == profile.field_index

    def test_prediction_status_candidate_after_resolver(self):
        """R332: type_control 是 soft evidence，prediction_status 为 candidate"""
        pipeline = DetectionPipeline()
        predictions = pipeline.detect_fields(self._make_upgradable_profiles())

        for p in predictions:
            if p.coarse_label == "type_control":
                assert p.prediction_status == "candidate"
                assert p.abstained is False

    def test_no_direct_replace_bypass(self):
        """R332: 禁止后处理直接替换 SemanticPrediction

        验证 type_control 证据经过 Resolver 仲裁，而非直接替换 primary。
        如果直接替换，constant evidence 会从 evidence 中丢失。
        """
        pipeline = DetectionPipeline()
        profiles = self._make_upgradable_profiles()

        # 单字段检测（不触发跨 layout 后处理）
        pre_predictions = [pipeline.detect_field(p) for p in profiles]
        # 触发跨 layout 后处理
        post_predictions = pipeline.detect_fields(profiles)

        for i, (pre_p, post_p) in enumerate(zip(pre_predictions, post_predictions)):
            # 升级后 coarse_label 应为 type_control
            assert post_p.coarse_label == "type_control"
            # 原 constant evidence 不应丢失（仍在 evidence 中）
            post_labels = [e.coarse_label for e in post_p.evidence]
            assert "constant" in post_labels, (
                f"字段 {i}: constant evidence 丢失，"
                f"post evidence labels = {post_labels}"
            )

    def test_type_control_not_overrides_hard_length(self):
        """R332: type_control 不得覆盖强 length（hard length 优先）"""
        from semantic_detector.contracts import DetectorEvidence
        from semantic_detector.scoring.resolver import Resolver

        resolver = Resolver()
        # 构造 constant + type_control + hard length 候选
        # length 分数最高，确保 hard priority 选 length 而非 constant
        constant = DetectorEvidence(
            detector="constant", coarse_label="constant",
            fine_label="constant_value", is_hard_evidence=True,
            score=0.85, reason_code="test", details={},
        )
        type_control = DetectorEvidence(
            detector="type_opcode", coarse_label="type_control",
            fine_label="type_or_opcode_candidate", is_hard_evidence=False,
            score=0.7, reason_code="one_to_one_mapping", details={},
        )
        length = DetectorEvidence(
            detector="length", coarse_label="length",
            fine_label="length_of_next_field", is_hard_evidence=True,
            score=0.95, reason_code="test", details={},
        )

        primary, alternatives = resolver.resolve_with_context(
            [constant, type_control, length]
        )

        # hard length 分数最高，胜出
        assert primary.coarse_label == "length"
        # type_control 进入 alternatives
        alt_labels = [a.coarse_label for a in alternatives]
        assert "type_control" in alt_labels
