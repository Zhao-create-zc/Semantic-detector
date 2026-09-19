"""Tests for JSONL file reading."""

import pytest
import tempfile
import os
from semantic_detector.io.jsonl import read_jsonl_file


def test_read_jsonl_file_3_lines() -> None:
    """测试读取 3 行 JSONL 文件"""
    # 创建临时 JSONL 文件
    content = '{"message_id": "msg_0001", "layout_id": "layout_A", "direction": "request", "payload_hex": "0001", "fields": [{"field_index": 0, "start": 0, "end": 2}]}\n'
    content += '{"message_id": "msg_0002", "layout_id": "layout_A", "direction": "request", "payload_hex": "0203", "fields": [{"field_index": 0, "start": 0, "end": 2}]}\n'
    content += '{"message_id": "msg_0003", "layout_id": "layout_A", "direction": "request", "payload_hex": "0405", "fields": [{"field_index": 0, "start": 0, "end": 2}]}\n'
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
        f.write(content)
        temp_path = f.name
    
    try:
        valid_records, rejected_records = read_jsonl_file(temp_path)
        
        assert len(valid_records) == 3
        assert len(rejected_records) == 0
        assert valid_records[0].message_id == "msg_0001"
        assert valid_records[1].message_id == "msg_0002"
        assert valid_records[2].message_id == "msg_0003"
        assert valid_records[0].input_order == 0
        assert valid_records[1].input_order == 1
        assert valid_records[2].input_order == 2
    finally:
        os.unlink(temp_path)


def test_read_jsonl_file_empty_lines() -> None:
    """测试跳过空行"""
    content = '{"message_id": "msg_0001", "layout_id": "layout_A", "direction": "request", "payload_hex": "0001", "fields": [{"field_index": 0, "start": 0, "end": 2}]}\n'
    content += '\n'
    content += '{"message_id": "msg_0002", "layout_id": "layout_A", "direction": "request", "payload_hex": "0203", "fields": [{"field_index": 0, "start": 0, "end": 2}]}\n'
    content += '   \n'
    content += '{"message_id": "msg_0003", "layout_id": "layout_A", "direction": "request", "payload_hex": "0405", "fields": [{"field_index": 0, "start": 0, "end": 2}]}\n'
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
        f.write(content)
        temp_path = f.name
    
    try:
        valid_records, rejected_records = read_jsonl_file(temp_path)
        
        assert len(valid_records) == 3
        assert len(rejected_records) == 0
        assert valid_records[0].message_id == "msg_0001"
        assert valid_records[1].message_id == "msg_0002"
        assert valid_records[2].message_id == "msg_0003"
    finally:
        os.unlink(temp_path)


def test_read_jsonl_file_not_found() -> None:
    """测试文件不存在"""
    with pytest.raises(ValueError) as exc_info:
        read_jsonl_file("nonexistent.jsonl")
    assert "File not found" in str(exc_info.value)


def test_read_jsonl_file_empty() -> None:
    """测试空文件"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
        temp_path = f.name
    
    try:
        valid_records, rejected_records = read_jsonl_file(temp_path)
        assert len(valid_records) == 0
        assert len(rejected_records) == 0
    finally:
        os.unlink(temp_path)


def test_read_jsonl_file_duplicate_ids() -> None:
    """测试重复 message_id 检测"""
    content = '{"message_id": "msg_0001", "layout_id": "layout_A", "direction": "request", "payload_hex": "0001", "fields": [{"field_index": 0, "start": 0, "end": 2}]}\n'
    content += '{"message_id": "msg_0002", "layout_id": "layout_A", "direction": "request", "payload_hex": "0203", "fields": [{"field_index": 0, "start": 0, "end": 2}]}\n'
    content += '{"message_id": "msg_0001", "layout_id": "layout_A", "direction": "request", "payload_hex": "0405", "fields": [{"field_index": 0, "start": 0, "end": 2}]}\n'
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
        f.write(content)
        temp_path = f.name
    
    try:
        valid_records, rejected_records = read_jsonl_file(temp_path, check_duplicate_ids=True)
        
        assert len(valid_records) == 2
        assert len(rejected_records) == 1
        assert valid_records[0].message_id == "msg_0001"
        assert valid_records[1].message_id == "msg_0002"
        assert rejected_records[0]['reason'] == 'Duplicate message_id: msg_0001'
    finally:
        os.unlink(temp_path)


def test_read_jsonl_file_no_duplicate_check() -> None:
    """测试不检测重复 message_id"""
    content = '{"message_id": "msg_0001", "layout_id": "layout_A", "direction": "request", "payload_hex": "0001", "fields": [{"field_index": 0, "start": 0, "end": 2}]}\n'
    content += '{"message_id": "msg_0001", "layout_id": "layout_A", "direction": "request", "payload_hex": "0203", "fields": [{"field_index": 0, "start": 0, "end": 2}]}\n'
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
        f.write(content)
        temp_path = f.name
    
    try:
        valid_records, rejected_records = read_jsonl_file(temp_path, check_duplicate_ids=False)
        
        assert len(valid_records) == 2
        assert len(rejected_records) == 0
        assert valid_records[0].message_id == "msg_0001"
        assert valid_records[1].message_id == "msg_0001"
    finally:
        os.unlink(temp_path)


def test_read_jsonl_file_duplicate_ids() -> None:
    """测试重复 message_id 检测"""
    content = '{"message_id": "msg_0001", "layout_id": "layout_A", "direction": "request", "payload_hex": "0001", "fields": [{"field_index": 0, "start": 0, "end": 2}]}\n'
    content += '{"message_id": "msg_0002", "layout_id": "layout_A", "direction": "request", "payload_hex": "0203", "fields": [{"field_index": 0, "start": 0, "end": 2}]}\n'
    content += '{"message_id": "msg_0001", "layout_id": "layout_A", "direction": "request", "payload_hex": "0405", "fields": [{"field_index": 0, "start": 0, "end": 2}]}\n'
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
        f.write(content)
        temp_path = f.name
    
    try:
        valid_records, rejected_records = read_jsonl_file(temp_path, check_duplicate_ids=True)
        
        assert len(valid_records) == 2
        assert len(rejected_records) == 1
        assert valid_records[0].message_id == "msg_0001"
        assert valid_records[1].message_id == "msg_0002"
        assert rejected_records[0]['reason'] == 'Duplicate message_id: msg_0001'
    finally:
        os.unlink(temp_path)


def test_read_jsonl_file_no_duplicate_check() -> None:
    """测试不检测重复 message_id"""
    content = '{"message_id": "msg_0001", "layout_id": "layout_A", "direction": "request", "payload_hex": "0001", "fields": [{"field_index": 0, "start": 0, "end": 2}]}\n'
    content += '{"message_id": "msg_0001", "layout_id": "layout_A", "direction": "request", "payload_hex": "0203", "fields": [{"field_index": 0, "start": 0, "end": 2}]}\n'
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
        f.write(content)
        temp_path = f.name
    
    try:
        valid_records, rejected_records = read_jsonl_file(temp_path, check_duplicate_ids=False)
        
        assert len(valid_records) == 2
        assert len(rejected_records) == 0
        assert valid_records[0].message_id == "msg_0001"
        assert valid_records[1].message_id == "msg_0001"
    finally:
        os.unlink(temp_path)


def test_read_jsonl_file_duplicate_ids() -> None:
    """测试重复 message_id 检测"""
    content = '{"message_id": "msg_0001", "layout_id": "layout_A", "direction": "request", "payload_hex": "0001", "fields": [{"field_index": 0, "start": 0, "end": 2}]}\n'
    content += '{"message_id": "msg_0002", "layout_id": "layout_A", "direction": "request", "payload_hex": "0203", "fields": [{"field_index": 0, "start": 0, "end": 2}]}\n'
    content += '{"message_id": "msg_0001", "layout_id": "layout_A", "direction": "request", "payload_hex": "0405", "fields": [{"field_index": 0, "start": 0, "end": 2}]}\n'
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
        f.write(content)
        temp_path = f.name
    
    try:
        valid_records, rejected_records = read_jsonl_file(temp_path, check_duplicate_ids=True)
        
        assert len(valid_records) == 2
        assert len(rejected_records) == 1
        assert valid_records[0].message_id == "msg_0001"
        assert valid_records[1].message_id == "msg_0002"
        assert rejected_records[0]['reason'] == 'Duplicate message_id: msg_0001'
    finally:
        os.unlink(temp_path)


def test_read_jsonl_file_no_duplicate_check() -> None:
    """测试不检测重复 message_id"""
    content = '{"message_id": "msg_0001", "layout_id": "layout_A", "direction": "request", "payload_hex": "0001", "fields": [{"field_index": 0, "start": 0, "end": 2}]}\n'
    content += '{"message_id": "msg_0001", "layout_id": "layout_A", "direction": "request", "payload_hex": "0203", "fields": [{"field_index": 0, "start": 0, "end": 2}]}\n'
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
        f.write(content)
        temp_path = f.name
    
    try:
        valid_records, rejected_records = read_jsonl_file(temp_path, check_duplicate_ids=False)
        
        assert len(valid_records) == 2
        assert len(rejected_records) == 0
        assert valid_records[0].message_id == "msg_0001"
        assert valid_records[1].message_id == "msg_0001"
    finally:
        os.unlink(temp_path)


def test_read_jsonl_file_duplicate_ids() -> None:
    """测试重复 message_id 检测"""
    content = '{"message_id": "msg_0001", "layout_id": "layout_A", "direction": "request", "payload_hex": "0001", "fields": [{"field_index": 0, "start": 0, "end": 2}]}\n'
    content += '{"message_id": "msg_0002", "layout_id": "layout_A", "direction": "request", "payload_hex": "0203", "fields": [{"field_index": 0, "start": 0, "end": 2}]}\n'
    content += '{"message_id": "msg_0001", "layout_id": "layout_A", "direction": "request", "payload_hex": "0405", "fields": [{"field_index": 0, "start": 0, "end": 2}]}\n'
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
        f.write(content)
        temp_path = f.name
    
    try:
        valid_records, rejected_records = read_jsonl_file(temp_path, check_duplicate_ids=True)
        
        assert len(valid_records) == 2
        assert len(rejected_records) == 1
        assert valid_records[0].message_id == "msg_0001"
        assert valid_records[1].message_id == "msg_0002"
        assert rejected_records[0]['reason'] == 'Duplicate message_id: msg_0001'
    finally:
        os.unlink(temp_path)


def test_read_jsonl_file_no_duplicate_check() -> None:
    """测试不检测重复 message_id"""
    content = '{"message_id": "msg_0001", "layout_id": "layout_A", "direction": "request", "payload_hex": "0001", "fields": [{"field_index": 0, "start": 0, "end": 2}]}\n'
    content += '{"message_id": "msg_0001", "layout_id": "layout_A", "direction": "request", "payload_hex": "0203", "fields": [{"field_index": 0, "start": 0, "end": 2}]}\n'
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
        f.write(content)
        temp_path = f.name
    
    try:
        valid_records, rejected_records = read_jsonl_file(temp_path, check_duplicate_ids=False)
        
        assert len(valid_records) == 2
        assert len(rejected_records) == 0
        assert valid_records[0].message_id == "msg_0001"
        assert valid_records[1].message_id == "msg_0001"
    finally:
        os.unlink(temp_path)


def test_read_jsonl_file_duplicate_ids() -> None:
    """测试重复 message_id 检测"""
    content = '{"message_id": "msg_0001", "layout_id": "layout_A", "direction": "request", "payload_hex": "0001", "fields": [{"field_index": 0, "start": 0, "end": 2}]}\n'
    content += '{"message_id": "msg_0002", "layout_id": "layout_A", "direction": "request", "payload_hex": "0203", "fields": [{"field_index": 0, "start": 0, "end": 2}]}\n'
    content += '{"message_id": "msg_0001", "layout_id": "layout_A", "direction": "request", "payload_hex": "0405", "fields": [{"field_index": 0, "start": 0, "end": 2}]}\n'
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
        f.write(content)
        temp_path = f.name
    
    try:
        valid_records, rejected_records = read_jsonl_file(temp_path, check_duplicate_ids=True)
        
        assert len(valid_records) == 2
        assert len(rejected_records) == 1
        assert valid_records[0].message_id == "msg_0001"
        assert valid_records[1].message_id == "msg_0002"
        assert rejected_records[0]['reason'] == 'Duplicate message_id: msg_0001'
    finally:
        os.unlink(temp_path)


def test_read_jsonl_file_no_duplicate_check() -> None:
    """测试不检测重复 message_id"""
    content = '{"message_id": "msg_0001", "layout_id": "layout_A", "direction": "request", "payload_hex": "0001", "fields": [{"field_index": 0, "start": 0, "end": 2}]}\n'
    content += '{"message_id": "msg_0001", "layout_id": "layout_A", "direction": "request", "payload_hex": "0203", "fields": [{"field_index": 0, "start": 0, "end": 2}]}\n'
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
        f.write(content)
        temp_path = f.name
    
    try:
        valid_records, rejected_records = read_jsonl_file(temp_path, check_duplicate_ids=False)
        
        assert len(valid_records) == 2
        assert len(rejected_records) == 0
        assert valid_records[0].message_id == "msg_0001"
        assert valid_records[1].message_id == "msg_0001"
    finally:
        os.unlink(temp_path)


def test_read_jsonl_file_duplicate_ids() -> None:
    """测试重复 message_id 检测"""
    content = '{"message_id": "msg_0001", "layout_id": "layout_A", "direction": "request", "payload_hex": "0001", "fields": [{"field_index": 0, "start": 0, "end": 2}]}\n'
    content += '{"message_id": "msg_0002", "layout_id": "layout_A", "direction": "request", "payload_hex": "0203", "fields": [{"field_index": 0, "start": 0, "end": 2}]}\n'
    content += '{"message_id": "msg_0001", "layout_id": "layout_A", "direction": "request", "payload_hex": "0405", "fields": [{"field_index": 0, "start": 0, "end": 2}]}\n'
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
        f.write(content)
        temp_path = f.name
    
    try:
        valid_records, rejected_records = read_jsonl_file(temp_path, check_duplicate_ids=True)
        
        assert len(valid_records) == 2
        assert len(rejected_records) == 1
        assert valid_records[0].message_id == "msg_0001"
        assert valid_records[1].message_id == "msg_0002"
        assert rejected_records[0]['reason'] == 'Duplicate message_id: msg_0001'
    finally:
        os.unlink(temp_path)


def test_read_jsonl_file_no_duplicate_check() -> None:
    """测试不检测重复 message_id"""
    content = '{"message_id": "msg_0001", "layout_id": "layout_A", "direction": "request", "payload_hex": "0001", "fields": [{"field_index": 0, "start": 0, "end": 2}]}\n'
    content += '{"message_id": "msg_0001", "layout_id": "layout_A", "direction": "request", "payload_hex": "0203", "fields": [{"field_index": 0, "start": 0, "end": 2}]}\n'
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False, encoding='utf-8') as f:
        f.write(content)
        temp_path = f.name
    
    try:
        valid_records, rejected_records = read_jsonl_file(temp_path, check_duplicate_ids=False)
        
        assert len(valid_records) == 2
        assert len(rejected_records) == 0
        assert valid_records[0].message_id == "msg_0001"
        assert valid_records[1].message_id == "msg_0001"
    finally:
        os.unlink(temp_path)