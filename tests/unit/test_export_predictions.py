"""测试预测 JSONL 导出与读回

验证 export_predictions_to_jsonl 和 read_predictions_from_jsonl 功能。
R243：新增 SemanticPrediction 完整字段导出测试。
"""

import json
import pytest
import tempfile
from pathlib import Path
from semantic_detector.io.exporters import (
    export_predictions_to_jsonl,
    read_predictions_from_jsonl,
    read_semantic_predictions_from_jsonl,
    _serialize_semantic_prediction,
    _deserialize_detector_evidence,
)
from semantic_detector.contracts import DetectorEvidence, SemanticPrediction, Direction


class TestExportPredictions:
    """预测导出测试"""
    
    def test_export_single_prediction(self):
        """测试导出单个预测"""
        predictions = [
            DetectorEvidence(
                detector="constant",
                coarse_label="constant",
                fine_label="constant_4byte",
                score=0.95,
                is_hard_evidence=True,
                reason_code="dominant_value_ratio_high",
                details={"ratio": 1.0}
            )
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            output_path = Path(f.name)
        
        try:
            export_predictions_to_jsonl(predictions, output_path)
            
            assert output_path.exists()
            content = output_path.read_text(encoding='utf-8')
            assert len(content) > 0
        finally:
            output_path.unlink(missing_ok=True)
    
    def test_export_multiple_predictions(self):
        """测试导出多个预测"""
        predictions = [
            DetectorEvidence(
                detector="constant",
                coarse_label="constant",
                fine_label="constant_4byte",
                score=0.95,
                is_hard_evidence=True,
                reason_code="dominant_value_ratio_high",
                details={"ratio": 1.0}
            ),
            DetectorEvidence(
                detector="length",
                coarse_label="length",
                fine_label="length_4byte",
                score=0.9,
                is_hard_evidence=True,
                reason_code="valid_length_values",
                details={"count": 100}
            )
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            output_path = Path(f.name)
        
        try:
            export_predictions_to_jsonl(predictions, output_path)
            
            assert output_path.exists()
            lines = output_path.read_text(encoding='utf-8').strip().split('\n')
            assert len(lines) == 2
        finally:
            output_path.unlink(missing_ok=True)
    
    def test_read_single_prediction(self):
        """测试读回单个预测"""
        predictions = [
            DetectorEvidence(
                detector="constant",
                coarse_label="constant",
                fine_label="constant_4byte",
                score=0.95,
                is_hard_evidence=True,
                reason_code="dominant_value_ratio_high",
                details={"ratio": 1.0}
            )
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            output_path = Path(f.name)
        
        try:
            export_predictions_to_jsonl(predictions, output_path)
            read_back = read_predictions_from_jsonl(output_path)
            
            assert len(read_back) == 1
            assert read_back[0].detector == predictions[0].detector
            assert read_back[0].coarse_label == predictions[0].coarse_label
            assert read_back[0].fine_label == predictions[0].fine_label
            assert read_back[0].score == predictions[0].score
            assert read_back[0].is_hard_evidence == predictions[0].is_hard_evidence
            assert read_back[0].reason_code == predictions[0].reason_code
        finally:
            output_path.unlink(missing_ok=True)
    
    def test_read_multiple_predictions(self):
        """测试读回多个预测"""
        predictions = [
            DetectorEvidence(
                detector="constant",
                coarse_label="constant",
                fine_label="constant_4byte",
                score=0.95,
                is_hard_evidence=True,
                reason_code="dominant_value_ratio_high",
                details={"ratio": 1.0}
            ),
            DetectorEvidence(
                detector="length",
                coarse_label="length",
                fine_label="length_4byte",
                score=0.9,
                is_hard_evidence=True,
                reason_code="valid_length_values",
                details={"count": 100}
            )
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            output_path = Path(f.name)
        
        try:
            export_predictions_to_jsonl(predictions, output_path)
            read_back = read_predictions_from_jsonl(output_path)
            
            assert len(read_back) == 2
            for i, pred in enumerate(predictions):
                assert read_back[i].detector == pred.detector
                assert read_back[i].coarse_label == pred.coarse_label
                assert read_back[i].fine_label == pred.fine_label
                assert read_back[i].score == pred.score
                assert read_back[i].is_hard_evidence == pred.is_hard_evidence
                assert read_back[i].reason_code == pred.reason_code
        finally:
            output_path.unlink(missing_ok=True)
    
    def test_export_and_read_preserves_all_fields(self):
        """测试导出和读回保留所有字段"""
        predictions = [
            DetectorEvidence(
                detector="timestamp",
                coarse_label="timestamp",
                fine_label="unix_seconds_be",
                score=0.85,
                is_hard_evidence=False,
                reason_code="valid_timestamp_range",
                details={
                    "min": 1000000,
                    "max": 2000000,
                    "count": 50
                }
            )
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            output_path = Path(f.name)
        
        try:
            export_predictions_to_jsonl(predictions, output_path)
            read_back = read_predictions_from_jsonl(output_path)
            
            assert len(read_back) == 1
            assert read_back[0].detector == predictions[0].detector
            assert read_back[0].coarse_label == predictions[0].coarse_label
            assert read_back[0].fine_label == predictions[0].fine_label
            assert read_back[0].score == predictions[0].score
            assert read_back[0].is_hard_evidence == predictions[0].is_hard_evidence
            assert read_back[0].reason_code == predictions[0].reason_code
            assert read_back[0].details == predictions[0].details
        finally:
            output_path.unlink(missing_ok=True)


class TestExportSemanticPrediction:
    """R243: SemanticPrediction 完整字段导出测试

    03 教程 HIGH-3 / 04 任务表 R243：
    - 导出后逐行解析
    - 每行含完整身份（run_id/layout_id/direction/field_index）和证据
      （coarse_label/fine_label/confidence/abstained/prediction_status/
       evidence/alternatives）
    """

    def _make_evidence(self, detector="length", score=0.95, is_hard=True, reason="value_equals_message_length"):
        """合成 DetectorEvidence。"""
        return DetectorEvidence(
            detector=detector,
            coarse_label="length",
            fine_label="total_message_length",
            is_hard_evidence=is_hard,
            score=score,
            reason_code=reason,
            details={"relation": "total", "endian": "be", "support_ratio": score, "offset": 0},
        )

    def _make_prediction(self, run_id="run-r243-001", field_index=0, status="confirmed"):
        """合成 SemanticPrediction。"""
        primary = self._make_evidence()
        alt_evidence = DetectorEvidence(
            detector="sequence",
            coarse_label="sequence_or_counter",
            fine_label="sequence_32bit_be",
            is_hard_evidence=False,
            score=0.6,
            reason_code="monotonic_increase",
            details={},
        )
        return SemanticPrediction(
            run_id=run_id,
            layout_id="layout_r243",
            direction=Direction.REQUEST,
            field_index=field_index,
            coarse_label=primary.coarse_label,
            fine_label=primary.fine_label,
            confidence=primary.score,
            abstained=(status == "abstained"),
            evidence=(primary, alt_evidence),
            alternatives=(
                {
                    "detector": "sequence",
                    "coarse_label": "sequence_or_counter",
                    "fine_label": "sequence_32bit_be",
                    "is_hard_evidence": False,
                    "score": 0.6,
                    "reason_code": "monotonic_increase",
                    "details": {},
                },
            ),
            prediction_status=status,
        )

    def test_serialize_semantic_prediction_contains_all_identity_fields(self):
        """_serialize_semantic_prediction 返回完整身份字段。"""
        prediction = self._make_prediction(field_index=3)

        d = _serialize_semantic_prediction(prediction)

        assert d["run_id"] == "run-r243-001"
        assert d["layout_id"] == "layout_r243"
        assert d["direction"] == "request"
        assert d["field_index"] == 3

    def test_serialize_semantic_prediction_contains_all_prediction_fields(self):
        """返回完整预测字段（coarse/fine/confidence/abstained/status）。"""
        prediction = self._make_prediction(status="confirmed")

        d = _serialize_semantic_prediction(prediction)

        assert d["coarse_label"] == "length"
        assert d["fine_label"] == "total_message_length"
        assert d["confidence"] == 0.95
        assert d["abstained"] is False
        assert d["prediction_status"] == "confirmed"

    def test_serialize_semantic_prediction_serializes_evidence_as_list_of_dicts(self):
        """evidence 元组序列化为 dict 列表。"""
        prediction = self._make_prediction()

        d = _serialize_semantic_prediction(prediction)

        assert isinstance(d["evidence"], list)
        assert len(d["evidence"]) == 2
        # primary 在前
        assert d["evidence"][0]["detector"] == "length"
        assert d["evidence"][0]["is_hard_evidence"] is True
        # alternative 在后
        assert d["evidence"][1]["detector"] == "sequence"

    def test_serialize_semantic_prediction_serializes_alternatives_as_list_of_dicts(self):
        """alternatives 元组序列化为 dict 列表。"""
        prediction = self._make_prediction()

        d = _serialize_semantic_prediction(prediction)

        assert isinstance(d["alternatives"], list)
        assert len(d["alternatives"]) == 1
        assert d["alternatives"][0]["detector"] == "sequence"

    def test_export_semantic_prediction_writes_full_fields_per_line(self):
        """导出后逐行解析，每行含完整身份和证据。"""
        predictions = [
            self._make_prediction(run_id="run-a", field_index=0, status="confirmed"),
            self._make_prediction(run_id="run-a", field_index=1, status="candidate"),
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            output_path = Path(f.name)

        try:
            export_predictions_to_jsonl(predictions, output_path)

            lines = output_path.read_text(encoding='utf-8').strip().split('\n')
            assert len(lines) == 2

            for i, line in enumerate(lines):
                d = json.loads(line)
                # 完整身份
                assert "run_id" in d
                assert "layout_id" in d
                assert "direction" in d
                assert "field_index" in d
                # 完整预测
                assert "coarse_label" in d
                assert "fine_label" in d
                assert "confidence" in d
                assert "abstained" in d
                assert "prediction_status" in d
                # 完整证据
                assert "evidence" in d
                assert "alternatives" in d
                # 字段索引与顺序一致
                assert d["field_index"] == i
        finally:
            output_path.unlink(missing_ok=True)

    def test_export_semantic_prediction_direction_serialized_as_value_string(self):
        """direction 序列化为值字符串（request/response/unknown），非枚举名。"""
        for direction, expected in [
            (Direction.REQUEST, "request"),
            (Direction.RESPONSE, "response"),
            (Direction.UNKNOWN, "unknown"),
        ]:
            prediction = SemanticPrediction(
                run_id="run-dir",
                layout_id="layout_dir",
                direction=direction,
                field_index=0,
                coarse_label="length",
                fine_label="total_message_length",
                confidence=0.9,
                abstained=False,
                evidence=(self._make_evidence(),),
                alternatives=(),
                prediction_status="confirmed",
            )

            d = _serialize_semantic_prediction(prediction)

            assert d["direction"] == expected

    def test_export_mixed_list_semantic_and_evidence(self):
        """混合列表（SemanticPrediction + DetectorEvidence）各自按格式导出。"""
        sem_pred = self._make_prediction()
        det_ev = DetectorEvidence(
            detector="constant",
            coarse_label="constant",
            fine_label="constant_4byte",
            score=0.95,
            is_hard_evidence=True,
            reason_code="dominant_value_ratio_high",
            details={"ratio": 1.0},
        )

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            output_path = Path(f.name)

        try:
            export_predictions_to_jsonl([sem_pred, det_ev], output_path)

            lines = output_path.read_text(encoding='utf-8').strip().split('\n')
            assert len(lines) == 2

            first = json.loads(lines[0])
            second = json.loads(lines[1])

            # 第一行：SemanticPrediction 完整格式
            assert "run_id" in first
            assert "prediction_status" in first
            assert "evidence" in first

            # 第二行：DetectorEvidence 旧格式
            assert "detector" in second
            assert "score" in second
            assert "run_id" not in second
        finally:
            output_path.unlink(missing_ok=True)

    def test_export_abstained_prediction(self):
        """abstained 预测导出 prediction_status=abstained，abstained=True。"""
        primary_unknown = DetectorEvidence(
            detector="resolver",
            coarse_label="unknown",
            fine_label="unknown",
            is_hard_evidence=False,
            score=0.0,
            reason_code="no_candidates",
            details={},
        )
        prediction = SemanticPrediction(
            run_id="run-abstain",
            layout_id="layout_abstain",
            direction=Direction.UNKNOWN,
            field_index=0,
            coarse_label="unknown",
            fine_label="unknown",
            confidence=0.0,
            abstained=True,
            evidence=(primary_unknown,),
            alternatives=(),
            prediction_status="abstained",
        )

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            output_path = Path(f.name)

        try:
            export_predictions_to_jsonl([prediction], output_path)

            line = output_path.read_text(encoding='utf-8').strip()
            d = json.loads(line)

            assert d["prediction_status"] == "abstained"
            assert d["abstained"] is True
            assert d["coarse_label"] == "unknown"
            assert d["direction"] == "unknown"
        finally:
            output_path.unlink(missing_ok=True)


class TestReadSemanticPredictionsRoundTrip:
    """R244: SemanticPrediction JSONL 严格读回（round-trip 等价）

    03 教程 HIGH-3 / 04 任务表 R244：
    - round-trip：导入对象与导出对象等价
    - 含 evidence 元组和 alternatives 元组
    """

    def _make_evidence(self, detector="length", score=0.95, is_hard=True):
        return DetectorEvidence(
            detector=detector,
            coarse_label="length",
            fine_label="total_message_length",
            is_hard_evidence=is_hard,
            score=score,
            reason_code="value_equals_message_length",
            details={"relation": "total", "endian": "be", "support_ratio": score, "offset": 0},
        )

    def _make_prediction(self, run_id="run-rt-001", field_index=0, direction=Direction.REQUEST, status="confirmed"):
        primary = self._make_evidence()
        alt = DetectorEvidence(
            detector="sequence",
            coarse_label="sequence_or_counter",
            fine_label="sequence_32bit_be",
            is_hard_evidence=False,
            score=0.6,
            reason_code="monotonic_increase",
            details={"step": 1},
        )
        return SemanticPrediction(
            run_id=run_id,
            layout_id="layout_rt",
            direction=direction,
            field_index=field_index,
            coarse_label=primary.coarse_label,
            fine_label=primary.fine_label,
            confidence=primary.score,
            abstained=(status == "abstained"),
            evidence=(primary, alt),
            alternatives=(
                {
                    "detector": "sequence",
                    "coarse_label": "sequence_or_counter",
                    "fine_label": "sequence_32bit_be",
                    "is_hard_evidence": False,
                    "score": 0.6,
                    "reason_code": "monotonic_increase",
                    "details": {"step": 1},
                },
            ),
            prediction_status=status,
        )

    def test_deserialize_detector_evidence_inverse_of_serialize(self):
        """_deserialize_detector_evidence 与 _serialize_detector_evidence 互逆。"""
        from semantic_detector.io.exporters import _serialize_detector_evidence

        original = self._make_evidence()

        serialized = _serialize_detector_evidence(original)
        restored = _deserialize_detector_evidence(serialized)

        assert restored == original

    def test_round_trip_single_prediction_identity_fields(self):
        """round-trip 保留身份字段（run_id/layout/direction/index）。"""
        original = self._make_prediction(run_id="run-rt-002", field_index=3, direction=Direction.RESPONSE)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            output_path = Path(f.name)

        try:
            export_predictions_to_jsonl([original], output_path)
            read_back = read_semantic_predictions_from_jsonl(output_path)

            assert len(read_back) == 1
            r = read_back[0]
            assert r.run_id == original.run_id
            assert r.layout_id == original.layout_id
            assert r.direction == original.direction
            assert r.field_index == original.field_index
        finally:
            output_path.unlink(missing_ok=True)

    def test_round_trip_single_prediction_prediction_fields(self):
        """round-trip 保留预测字段（coarse/fine/confidence/abstained/status）。"""
        original = self._make_prediction(status="candidate")

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            output_path = Path(f.name)

        try:
            export_predictions_to_jsonl([original], output_path)
            read_back = read_semantic_predictions_from_jsonl(output_path)

            r = read_back[0]
            assert r.coarse_label == original.coarse_label
            assert r.fine_label == original.fine_label
            assert r.confidence == original.confidence
            assert r.abstained == original.abstained
            assert r.prediction_status == original.prediction_status
        finally:
            output_path.unlink(missing_ok=True)

    def test_round_trip_evidence_tuple_of_detector_evidence(self):
        """round-trip evidence 元组保留 DetectorEvidence 内容。"""
        original = self._make_prediction()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            output_path = Path(f.name)

        try:
            export_predictions_to_jsonl([original], output_path)
            read_back = read_semantic_predictions_from_jsonl(output_path)

            r = read_back[0]
            # evidence 是 tuple
            assert isinstance(r.evidence, tuple)
            assert len(r.evidence) == len(original.evidence)
            # 每个 DetectorEvidence 内容等价
            for orig_ev, read_ev in zip(original.evidence, r.evidence):
                assert read_ev == orig_ev
        finally:
            output_path.unlink(missing_ok=True)

    def test_round_trip_alternatives_tuple_of_dicts(self):
        """round-trip alternatives 元组保留 dict 内容。"""
        original = self._make_prediction()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            output_path = Path(f.name)

        try:
            export_predictions_to_jsonl([original], output_path)
            read_back = read_semantic_predictions_from_jsonl(output_path)

            r = read_back[0]
            # alternatives 是 tuple
            assert isinstance(r.alternatives, tuple)
            assert len(r.alternatives) == len(original.alternatives)
            for orig_alt, read_alt in zip(original.alternatives, r.alternatives):
                assert read_alt == orig_alt
        finally:
            output_path.unlink(missing_ok=True)

    def test_round_trip_multiple_predictions_preserves_order(self):
        """round-trip 多个预测保持顺序。"""
        originals = [
            self._make_prediction(run_id="run-rt-003", field_index=0, status="confirmed"),
            self._make_prediction(run_id="run-rt-003", field_index=1, status="candidate"),
            self._make_prediction(run_id="run-rt-003", field_index=2, direction=Direction.RESPONSE, status="abstained"),
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            output_path = Path(f.name)

        try:
            export_predictions_to_jsonl(originals, output_path)
            read_back = read_semantic_predictions_from_jsonl(output_path)

            assert len(read_back) == 3
            for orig, r in zip(originals, read_back):
                assert r.run_id == orig.run_id
                assert r.field_index == orig.field_index
                assert r.direction == orig.direction
                assert r.prediction_status == orig.prediction_status
        finally:
            output_path.unlink(missing_ok=True)

    def test_round_trip_direction_all_variants(self):
        """round-trip direction 三个值都能正确读回。"""
        for direction in [Direction.REQUEST, Direction.RESPONSE, Direction.UNKNOWN]:
            original = self._make_prediction(direction=direction)

            with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
                output_path = Path(f.name)

            try:
                export_predictions_to_jsonl([original], output_path)
                read_back = read_semantic_predictions_from_jsonl(output_path)

                assert read_back[0].direction == direction
            finally:
                output_path.unlink(missing_ok=True)

    def test_round_trip_abstained_prediction(self):
        """round-trip abstained 预测保留 abstained=True 和 status=abstained。"""
        primary_unknown = DetectorEvidence(
            detector="resolver",
            coarse_label="unknown",
            fine_label="unknown",
            is_hard_evidence=False,
            score=0.0,
            reason_code="no_candidates",
            details={},
        )
        original = SemanticPrediction(
            run_id="run-abstain-rt",
            layout_id="layout_abstain",
            direction=Direction.UNKNOWN,
            field_index=0,
            coarse_label="unknown",
            fine_label="unknown",
            confidence=0.0,
            abstained=True,
            evidence=(primary_unknown,),
            alternatives=(),
            prediction_status="abstained",
        )

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            output_path = Path(f.name)

        try:
            export_predictions_to_jsonl([original], output_path)
            read_back = read_semantic_predictions_from_jsonl(output_path)

            r = read_back[0]
            assert r.abstained is True
            assert r.prediction_status == "abstained"
            assert r.coarse_label == "unknown"
            assert r.evidence[0].reason_code == "no_candidates"
            assert r.alternatives == ()
        finally:
            output_path.unlink(missing_ok=True)

    def test_read_handles_empty_file(self):
        """空文件读回空列表。"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            output_path = Path(f.name)

        try:
            read_back = read_semantic_predictions_from_jsonl(output_path)
            assert read_back == []
        finally:
            output_path.unlink(missing_ok=True)

    def test_read_skips_blank_lines(self):
        """读回跳过空行。"""
        original1 = self._make_prediction(field_index=0)
        original2 = self._make_prediction(field_index=1)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            output_path = Path(f.name)
            # 手动写入：有效行 + 空行 + 有效行（FieldKey 不同，避免 R247 重复检测）
            from semantic_detector.io.exporters import _serialize_semantic_prediction
            f.write(json.dumps(_serialize_semantic_prediction(original1)) + '\n')
            f.write('\n')
            f.write(json.dumps(_serialize_semantic_prediction(original2)) + '\n')

        try:
            read_back = read_semantic_predictions_from_jsonl(output_path)
            assert len(read_back) == 2
        finally:
            output_path.unlink(missing_ok=True)


class TestReadSemanticPredictionsRejectDuplicateFieldKey:
    """R247: 重复预测 FieldKey 拒绝测试

    03 教程 6.5 / 04 任务表 R247：
    - 重复 key 输入
    - 明确错误，不静默覆盖
    """

    def _make_prediction_dict(self, layout_id="L1", direction="request", field_index=0, run_id="run-dup-001"):
        """合成 SemanticPrediction dict（直接用于写 JSONL）。"""
        return {
            "run_id": run_id,
            "layout_id": layout_id,
            "direction": direction,
            "field_index": field_index,
            "coarse_label": "length",
            "fine_label": "total_message_length",
            "confidence": 0.95,
            "abstained": False,
            "prediction_status": "confirmed",
            "evidence": [
                {
                    "detector": "length",
                    "coarse_label": "length",
                    "fine_label": "total_message_length",
                    "is_hard_evidence": True,
                    "score": 0.95,
                    "reason_code": "value_equals_message_length",
                    "details": {},
                }
            ],
            "alternatives": [],
        }

    def test_read_rejects_duplicate_fieldkey_same_direction(self):
        """重复 FieldKey（同 layout+direction+field_index）抛出 ValueError。"""
        duplicate_line = self._make_prediction_dict("L1", "request", 0)
        # 完全相同的 FieldKey 重复
        lines = [json.dumps(duplicate_line), json.dumps(duplicate_line)]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write("\n".join(lines) + "\n")
            output_path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="重复 FieldKey"):
                read_semantic_predictions_from_jsonl(output_path)
        finally:
            output_path.unlink(missing_ok=True)

    def test_read_rejects_duplicate_fieldkey_different_run_id(self):
        """即使 run_id 不同，FieldKey 重复仍抛出 ValueError。"""
        first = self._make_prediction_dict("L1", "request", 0, run_id="run-a")
        second = self._make_prediction_dict("L1", "request", 0, run_id="run-b")
        # FieldKey 相同（L1/request/0），run_id 不同
        lines = [json.dumps(first), json.dumps(second)]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write("\n".join(lines) + "\n")
            output_path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="重复 FieldKey"):
                read_semantic_predictions_from_jsonl(output_path)
        finally:
            output_path.unlink(missing_ok=True)

    def test_read_allows_same_layout_different_direction(self):
        """同 layout + 同 field_index 但 direction 不同 → 不算重复。"""
        request_pred = self._make_prediction_dict("L1", "request", 0)
        response_pred = self._make_prediction_dict("L1", "response", 0)
        lines = [json.dumps(request_pred), json.dumps(response_pred)]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write("\n".join(lines) + "\n")
            output_path = Path(f.name)

        try:
            read_back = read_semantic_predictions_from_jsonl(output_path)
            assert len(read_back) == 2
        finally:
            output_path.unlink(missing_ok=True)

    def test_read_allows_same_layout_direction_different_field_index(self):
        """同 layout + 同 direction 但 field_index 不同 → 不算重复。"""
        first = self._make_prediction_dict("L1", "request", 0)
        second = self._make_prediction_dict("L1", "request", 1)
        lines = [json.dumps(first), json.dumps(second)]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write("\n".join(lines) + "\n")
            output_path = Path(f.name)

        try:
            read_back = read_semantic_predictions_from_jsonl(output_path)
            assert len(read_back) == 2
        finally:
            output_path.unlink(missing_ok=True)

    def test_read_allows_different_layout_same_direction_field_index(self):
        """不同 layout + 同 direction + 同 field_index → 不算重复。"""
        first = self._make_prediction_dict("L1", "request", 0)
        second = self._make_prediction_dict("L2", "request", 0)
        lines = [json.dumps(first), json.dumps(second)]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write("\n".join(lines) + "\n")
            output_path = Path(f.name)

        try:
            read_back = read_semantic_predictions_from_jsonl(output_path)
            assert len(read_back) == 2
        finally:
            output_path.unlink(missing_ok=True)

    def test_read_duplicate_error_message_contains_fieldkey(self):
        """错误消息含 layout_id/direction/field_index 和行号。"""
        duplicate_line = self._make_prediction_dict("L1", "request", 0)
        lines = [json.dumps(duplicate_line), json.dumps(duplicate_line)]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write("\n".join(lines) + "\n")
            output_path = Path(f.name)

        try:
            with pytest.raises(ValueError) as exc_info:
                read_semantic_predictions_from_jsonl(output_path)

            msg = str(exc_info.value)
            assert "L1" in msg
            assert "request" in msg
            assert "0" in msg
            assert "第 2 行" in msg  # 重复出现在第 2 行
        finally:
            output_path.unlink(missing_ok=True)

    def test_read_duplicate_at_third_line(self):
        """第 3 行重复时错误消息含正确的行号。"""
        first = self._make_prediction_dict("L1", "request", 0)
        second = self._make_prediction_dict("L1", "request", 1)
        # 第三行与第一行重复
        third = self._make_prediction_dict("L1", "request", 0)
        lines = [json.dumps(first), json.dumps(second), json.dumps(third)]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write("\n".join(lines) + "\n")
            output_path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="第 3 行") as exc_info:
                read_semantic_predictions_from_jsonl(output_path)
        finally:
            output_path.unlink(missing_ok=True)

    def test_read_duplicate_after_blank_line_counts_correct_line(self):
        """空行不计入行号，重复检测的行号基于实际文件行。"""
        first = self._make_prediction_dict("L1", "request", 0)
        # 完全相同的 FieldKey 重复
        lines = [json.dumps(first), "", json.dumps(first)]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write("\n".join(lines) + "\n")
            output_path = Path(f.name)

        try:
            with pytest.raises(ValueError) as exc_info:
                read_semantic_predictions_from_jsonl(output_path)

            # 第 3 行是重复行（空行是第 2 行，但仍计入文件行号）
            msg = str(exc_info.value)
            assert "第 3 行" in msg
        finally:
            output_path.unlink(missing_ok=True)
