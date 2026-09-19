"""Tests for the serialization helpers."""

import json
from datetime import datetime, timezone
from semantic_detector.contracts import (
    Direction,
    FieldSpan,
    FieldKey,
    FieldSample,
    DetectorEvidence,
    SemanticPrediction,
    to_json_safe,
)


def test_to_json_safe_datetime() -> None:
    """测试 datetime 序列化"""
    dt = datetime(2026, 6, 24, 0, 0, 1, tzinfo=timezone.utc)
    result = to_json_safe(dt)
    
    assert isinstance(result, str)
    assert "2026-06-24" in result


def test_to_json_safe_bytes() -> None:
    """测试 bytes 序列化"""
    data = b'\x00\x01\x02\x03'
    result = to_json_safe(data)
    
    assert isinstance(result, str)
    assert result == "00010203"


def test_to_json_safe_tuple() -> None:
    """测试 tuple 序列化"""
    data = (1, 2, 3)
    result = to_json_safe(data)
    
    assert isinstance(result, list)
    assert result == [1, 2, 3]


def test_to_json_safe_nested_tuple() -> None:
    """测试嵌套 tuple 序列化"""
    data = ((1, 2), (3, 4))
    result = to_json_safe(data)
    
    assert isinstance(result, list)
    assert result == [[1, 2], [3, 4]]


def test_to_json_safe_enum() -> None:
    """测试 Enum 序列化"""
    result = to_json_safe(Direction.REQUEST)
    
    assert isinstance(result, str)
    assert result == "request"


def test_to_json_safe_dict() -> None:
    """测试 dict 序列化"""
    data = {"key": b'\x00\x01', "nested": (1, 2)}
    result = to_json_safe(data)
    
    assert isinstance(result, dict)
    assert result["key"] == "0001"
    assert result["nested"] == [1, 2]


def test_to_json_safe_field_span() -> None:
    """测试 FieldSpan 序列化"""
    span = FieldSpan(field_index=0, start=0, end=2)
    result = to_json_safe(span)
    
    assert isinstance(result, dict)
    assert result["field_index"] == 0
    assert result["start"] == 0
    assert result["end"] == 2


def test_to_json_safe_field_key() -> None:
    """测试 FieldKey 序列化"""
    key = FieldKey(
        layout_id="layout_A",
        direction=Direction.REQUEST,
        field_index=0,
    )
    result = to_json_safe(key)
    
    assert isinstance(result, dict)
    assert result["layout_id"] == "layout_A"
    assert result["direction"] == "request"
    assert result["field_index"] == 0


def test_to_json_safe_detector_evidence() -> None:
    """测试 DetectorEvidence 序列化"""
    evidence = DetectorEvidence(
        detector="constant",
        coarse_label="constant",
        fine_label="constant",
        score=0.98,
        is_hard_evidence=True,
        reason_code="dominant_value_ratio_high",
        details={"dominant_value": b'\x00\x01'},
    )
    result = to_json_safe(evidence)
    
    assert isinstance(result, dict)
    assert result["detector"] == "constant"
    assert result["score"] == 0.98
    assert result["details"]["dominant_value"] == "0001"


def test_to_json_safe_semantic_prediction() -> None:
    """测试 SemanticPrediction 序列化"""
    evidence = DetectorEvidence(
        detector="constant",
        coarse_label="constant",
        fine_label="constant",
        score=0.98,
        is_hard_evidence=True,
        reason_code="dominant_value_ratio_high",
    )
    prediction = SemanticPrediction(
        run_id="run_20260624_000001",
        layout_id="layout_A",
        direction=Direction.REQUEST,
        field_index=0,
        coarse_label="constant",
        fine_label="constant",
        confidence=0.98,
        abstained=False,
        evidence=(evidence,),
        alternatives=(),
    )
    result = to_json_safe(prediction)
    
    assert isinstance(result, dict)
    assert result["run_id"] == "run_20260624_000001"
    assert result["direction"] == "request"
    assert len(result["evidence"]) == 1


def test_to_json_safe_json_serializable() -> None:
    """测试序列化结果可 JSON 序列化"""
    evidence = DetectorEvidence(
        detector="constant",
        coarse_label="constant",
        fine_label="constant",
        score=0.98,
        is_hard_evidence=True,
        reason_code="dominant_value_ratio_high",
    )
    prediction = SemanticPrediction(
        run_id="run_20260624_000001",
        layout_id="layout_A",
        direction=Direction.REQUEST,
        field_index=0,
        coarse_label="constant",
        fine_label="constant",
        confidence=0.98,
        abstained=False,
        evidence=(evidence,),
        alternatives=(),
    )
    result = to_json_safe(prediction)
    
    json_str = json.dumps(result)
    assert isinstance(json_str, str)
    assert len(json_str) > 0