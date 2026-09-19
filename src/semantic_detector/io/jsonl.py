"""JSONL I/O 模块"""

import json
from datetime import datetime, timezone
from typing import Tuple, Dict, Any

from semantic_detector.contracts import Direction, FieldSpan, MessageRecord, get_direction_or_raise


def parse_payload_hex(payload_hex: str) -> bytes:
    """严格解析 payload_hex 字符串为 bytes
    
    Args:
        payload_hex: 十六进制字符串，只允许 0-9, a-f, A-F
        
    Returns:
        解析后的 bytes
        
    Raises:
        ValueError: 当输入不是合法十六进制字符串时
    """
    if not isinstance(payload_hex, str):
        raise ValueError(f"payload_hex must be a string, got {type(payload_hex)}")
    
    if len(payload_hex) == 0:
        raise ValueError("payload_hex must not be empty")
    
    if len(payload_hex) % 2 != 0:
        raise ValueError(f"payload_hex length must be even, got {len(payload_hex)}")
    
    # 检查是否只包含十六进制字符
    for i, char in enumerate(payload_hex):
        if char not in "0123456789abcdefABCDEF":
            raise ValueError(f"Invalid hex character '{char}' at position {i}")
    
    return bytes.fromhex(payload_hex)


def validate_payload_hex(payload_hex: str) -> Tuple[bool, str]:
    """验证 payload_hex 字符串是否合法
    
    Args:
        payload_hex: 十六进制字符串
        
    Returns:
        (is_valid, error_message) 元组
    """
    try:
        parse_payload_hex(payload_hex)
        return True, ""
    except ValueError as e:
        return False, str(e)


def parse_capture_time(capture_time: str) -> datetime:
    """严格解析 ISO 8601 UTC 时间字符串
    
    Args:
        capture_time: ISO 8601 UTC 时间字符串，支持 "Z" 和 "+00:00" 格式
        
    Returns:
        带时区的 datetime 对象
        
    Raises:
        ValueError: 当输入不是合法 ISO 8601 UTC 时间字符串时
    """
    if not isinstance(capture_time, str):
        raise ValueError(f"capture_time must be a string, got {type(capture_time)}")
    
    if len(capture_time) == 0:
        raise ValueError("capture_time must not be empty")
    
    # 支持 "Z" 结尾的时间字符串
    if capture_time.endswith('Z'):
        # 将 "Z" 替换为 "+00:00" 以便解析
        capture_time_fixed = capture_time[:-1] + '+00:00'
    else:
        capture_time_fixed = capture_time
    
    try:
        dt = datetime.fromisoformat(capture_time_fixed)
        # 确保有时区信息
        if dt.tzinfo is None:
            raise ValueError("capture_time must have timezone information")
        return dt
    except ValueError as e:
        raise ValueError(f"Invalid ISO 8601 UTC time format: {capture_time}") from e


def parse_json_record(json_str: str) -> MessageRecord:
    """解析单行 JSON 对象为 MessageRecord
    
    Args:
        json_str: JSON 字符串
        
    Returns:
        MessageRecord 实例
        
    Raises:
        ValueError: 当 JSON 不合法或缺少必要字段时
    """
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}") from e
    
    if not isinstance(data, dict):
        raise ValueError(f"JSON must be an object, got {type(data)}")
    
    # 检查必要字段
    required_fields = ['message_id', 'layout_id', 'direction', 'payload_hex', 'fields']
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")
    
    # 解析 payload_hex
    payload = parse_payload_hex(data['payload_hex'])
    
    # 解析 direction
    direction = get_direction_or_raise(data['direction'])
    
    # 检查 fields 必须是列表
    if not isinstance(data['fields'], list):
        raise ValueError(f"fields must be a list, got {type(data['fields'])}")
    
    # 解析 fields
    fields = []
    for field_data in data['fields']:
        if not isinstance(field_data, dict):
            raise ValueError(f"Field must be an object, got {type(field_data)}")
        
        required_field_keys = ['field_index', 'start', 'end']
        for key in required_field_keys:
            if key not in field_data:
                raise ValueError(f"Missing required field key: {key}")
        
        field = FieldSpan(
            field_index=field_data['field_index'],
            start=field_data['start'],
            end=field_data['end']
        )
        fields.append(field)
    
    # 检查 metadata 必须是对象（如果存在）
    if 'metadata' in data and data['metadata'] is not None:
        if not isinstance(data['metadata'], dict):
            raise ValueError(f"metadata must be an object, got {type(data['metadata'])}")
    
    # 解析可选字段
    capture_time = None
    if 'capture_time' in data and data['capture_time'] is not None:
        capture_time = parse_capture_time(data['capture_time'])
    
    session_id = data.get('session_id')
    pair_id = data.get('pair_id')
    metadata = data.get('metadata')
    input_order = data.get('input_order', 0)
    
    return MessageRecord(
        message_id=data['message_id'],
        layout_id=data['layout_id'],
        direction=direction,
        payload=payload,
        fields=tuple(fields),
        capture_time=capture_time,
        session_id=session_id,
        pair_id=pair_id,
        metadata=metadata,
        input_order=input_order
    )


def read_jsonl_file(file_path: str, check_duplicate_ids: bool = True) -> tuple:
    """读取 JSONL 文件并返回 MessageRecord 列表和拒绝记录列表
    
    Args:
        file_path: JSONL 文件路径
        check_duplicate_ids: 是否检测重复 message_id
        
    Returns:
        (valid_records, rejected_records) 元组
        
    Raises:
        ValueError: 当文件不存在时
    """
    import os
    
    if not os.path.exists(file_path):
        raise ValueError(f"File not found: {file_path}")
    
    valid_records = []
    rejected_records = []
    seen_ids = set()
    input_order = 0
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:  # 跳过空行
                continue
            
            try:
                # 解析 JSON 并设置 input_order
                data = json.loads(line)
                if 'input_order' not in data:
                    data['input_order'] = input_order
                
                record = parse_json_record(json.dumps(data))
                
                # 检测重复 message_id
                if check_duplicate_ids and record.message_id in seen_ids:
                    rejected_records.append({
                        'line_number': line_num,
                        'record': record,
                        'reason': f'Duplicate message_id: {record.message_id}'
                    })
                else:
                    valid_records.append(record)
                    seen_ids.add(record.message_id)
                
                input_order += 1
            except ValueError as e:
                rejected_records.append({
                    'line_number': line_num,
                    'error': str(e)
                })
    
    return valid_records, rejected_records