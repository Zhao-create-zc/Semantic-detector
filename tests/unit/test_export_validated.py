"""Tests for validated records JSONL export."""

import json
import tempfile
import os
import pytest
from datetime import datetime, timezone

from semantic_detector.contracts import Direction, FieldSpan, MessageRecord
from semantic_detector.io.exporters import export_validated_records
from semantic_detector.io.jsonl import read_jsonl_file


def test_export_validated_records_basic() -> None:
    """测试基本导出"""
    span = FieldSpan(field_index=0, start=0, end=2)
    record = MessageRecord(
        message_id="msg_0001",
        layout_id="layout_A",
        direction=Direction.REQUEST,
        payload=b'\x00\x01',
        fields=(span,),
        input_order=0
    )
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
        output_path = f.name
    
    try:
        export_validated_records([record], output_path)
        
        with open(output_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data['message_id'] == "msg_0001"
        assert data['layout_id'] == "layout_A"
        assert data['direction'] == "request"
        assert data['payload_hex'] == "0001"
        assert len(data['fields']) == 1
        assert data['fields'][0]['field_index'] == 0
        assert data['fields'][0]['start'] == 0
        assert data['fields'][0]['end'] == 2
        assert data['input_order'] == 0
    finally:
        os.unlink(output_path)


def test_export_and_reimport_preserves_payload_hex() -> None:
    """测试导出再解析，确保 payload_hex 不丢失"""
    span = FieldSpan(field_index=0, start=0, end=2)
    record = MessageRecord(
        message_id="msg_0001",
        layout_id="layout_A",
        direction=Direction.REQUEST,
        payload=b'\x00\x01',
        fields=(span,),
        input_order=0
    )
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
        output_path = f.name
    
    try:
        export_validated_records([record], output_path)
        
        valid_records, rejected_records = read_jsonl_file(output_path, check_duplicate_ids=False)
        
        assert len(valid_records) == 1
        assert len(rejected_records) == 0
        assert valid_records[0].payload == b'\x00\x01'
        assert valid_records[0].fields[0].field_index == 0
        assert valid_records[0].fields[0].start == 0
        assert valid_records[0].fields[0].end == 2
    finally:
        os.unlink(output_path)


def test_export_validated_records_multiple() -> None:
    """测试多条记录导出"""
    span1 = FieldSpan(field_index=0, start=0, end=2)
    span2 = FieldSpan(field_index=0, start=0, end=4)
    
    records = [
        MessageRecord(
            message_id="msg_0001",
            layout_id="layout_A",
            direction=Direction.REQUEST,
            payload=b'\x00\x01',
            fields=(span1,),
            input_order=0
        ),
        MessageRecord(
            message_id="msg_0002",
            layout_id="layout_A",
            direction=Direction.REQUEST,
            payload=b'\x02\x03\x04\x05',
            fields=(span2,),
            input_order=1
        )
    ]
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
        output_path = f.name
    
    try:
        export_validated_records(records, output_path)
        
        valid_records, rejected_records = read_jsonl_file(output_path, check_duplicate_ids=False)
        
        assert len(valid_records) == 2
        assert valid_records[0].message_id == "msg_0001"
        assert valid_records[1].message_id == "msg_0002"
        assert valid_records[0].payload == b'\x00\x01'
        assert valid_records[1].payload == b'\x02\x03\x04\x05'
    finally:
        os.unlink(output_path)


def test_export_validated_records_with_optional_fields() -> None:
    """测试包含可选字段的导出"""
    span = FieldSpan(field_index=0, start=0, end=2)
    record = MessageRecord(
        message_id="msg_0001",
        layout_id="layout_A",
        direction=Direction.REQUEST,
        payload=b'\x00\x01',
        fields=(span,),
        capture_time=datetime(2026, 6, 24, 0, 0, 1, tzinfo=timezone.utc),
        session_id="session_01",
        pair_id="pair_0001",
        metadata={"key": "value"},
        input_order=0
    )
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
        output_path = f.name
    
    try:
        export_validated_records([record], output_path)
        
        valid_records, rejected_records = read_jsonl_file(output_path, check_duplicate_ids=False)
        
        assert len(valid_records) == 1
        assert valid_records[0].capture_time is not None
        assert valid_records[0].session_id == "session_01"
        assert valid_records[0].pair_id == "pair_0001"
        assert valid_records[0].metadata == {"key": "value"}
    finally:
        os.unlink(output_path)