"""合成信息集和真值构建器

用于生成测试用的合成消息和真值数据。
"""

import json
from typing import List, Dict, Any
from pathlib import Path


class SyntheticMessageBuilder:
    """合成消息构建器
    
    生成符合数据契约的合成消息。
    """
    
    def __init__(self):
        self.message_id = 0
        self.layout_id = 0
    
    def build_constant_message(
        self,
        field_values: List[bytes],
        direction: str = "request"
    ) -> Dict[str, Any]:
        """构建常量字段消息
        
        Args:
            field_values: 字段值列表（bytes）
            direction: 方向（request/response/unknown）
            
        Returns:
            消息字典
        """
        self.message_id += 1
        self.layout_id += 1
        
        # 计算 payload
        payload = b''.join(field_values)
        
        message = {
            "message_id": self.message_id,
            "layout_id": f"layout_{self.layout_id}",
            "direction": direction,
            "payload_hex": payload.hex(),
            "fields": []
        }
        
        for i, value in enumerate(field_values):
            field = {
                "field_index": i,
                "value_hex": value.hex(),
                "width": len(value),
                "start": sum(len(v) for v in field_values[:i]),
                "end": sum(len(v) for v in field_values[:i+1])
            }
            message["fields"].append(field)
        
        return message
    
    def build_total_length_message(
        self,
        total_length: int,
        payload: bytes,
        direction: str = "request"
    ) -> Dict[str, Any]:
        """构建 total_length 字段消息
        
        Args:
            total_length: 总长度值
            payload: 负载数据
            direction: 方向
            
        Returns:
            消息字典
        """
        self.message_id += 1
        self.layout_id += 1
        
        # total_length 字段（4 字节，大端序）
        total_length_bytes = total_length.to_bytes(4, byteorder='big')
        full_payload = total_length_bytes + payload
        
        message = {
            "message_id": self.message_id,
            "layout_id": f"layout_{self.layout_id}",
            "direction": direction,
            "payload_hex": full_payload.hex(),
            "fields": []
        }
        
        field_0 = {
            "field_index": 0,
            "value_hex": total_length_bytes.hex(),
            "width": 4,
            "start": 0,
            "end": 4
        }
        message["fields"].append(field_0)
        
        field_1 = {
            "field_index": 1,
            "value_hex": payload.hex(),
            "width": len(payload),
            "start": 4,
            "end": 4 + len(payload)
        }
        message["fields"].append(field_1)
        
        return message
    
    def build_remaining_length_message(
        self,
        remaining_length: int,
        payload: bytes,
        direction: str = "request"
    ) -> Dict[str, Any]:
        """构建 remaining_length 字段消息
        
        Args:
            remaining_length: 剩余长度值
            payload: 负载数据
            direction: 方向
            
        Returns:
            消息字典
        """
        self.message_id += 1
        self.layout_id += 1
        
        # remaining_length 字段（变长编码）
        remaining_bytes = self._encode_remaining_length(remaining_length)
        full_payload = remaining_bytes + payload
        
        message = {
            "message_id": self.message_id,
            "layout_id": f"layout_{self.layout_id}",
            "direction": direction,
            "payload_hex": full_payload.hex(),
            "fields": []
        }
        
        field_0 = {
            "field_index": 0,
            "value_hex": remaining_bytes.hex(),
            "width": len(remaining_bytes),
            "start": 0,
            "end": len(remaining_bytes)
        }
        message["fields"].append(field_0)
        
        field_1 = {
            "field_index": 1,
            "value_hex": payload.hex(),
            "width": len(payload),
            "start": len(remaining_bytes),
            "end": len(remaining_bytes) + len(payload)
        }
        message["fields"].append(field_1)
        
        return message
    
    def _encode_remaining_length(self, length: int) -> bytes:
        """编码 remaining_length（MQTT 变长编码）
        
        Args:
            length: 长度值
            
        Returns:
            编码后的 bytes
        """
        encoded = bytearray()
        while True:
            byte = length % 128
            length //= 128
            if length > 0:
                byte |= 0x80
            encoded.append(byte)
            if length == 0:
                break
        return bytes(encoded)
    
    def build_timestamp_message(
        self,
        timestamp: int,
        payload: bytes,
        direction: str = "request"
    ) -> Dict[str, Any]:
        """构建时间戳字段消息
        
        Args:
            timestamp: Unix 时间戳（秒）
            payload: 负载数据
            direction: 方向
            
        Returns:
            消息字典
        """
        self.message_id += 1
        self.layout_id += 1
        
        # timestamp 字段（4 字节，大端序）
        timestamp_bytes = timestamp.to_bytes(4, byteorder='big')
        full_payload = timestamp_bytes + payload
        
        message = {
            "message_id": self.message_id,
            "layout_id": f"layout_{self.layout_id}",
            "direction": direction,
            "payload_hex": full_payload.hex(),
            "fields": []
        }
        
        field_0 = {
            "field_index": 0,
            "value_hex": timestamp_bytes.hex(),
            "width": 4,
            "start": 0,
            "end": 4
        }
        message["fields"].append(field_0)
        
        field_1 = {
            "field_index": 1,
            "value_hex": payload.hex(),
            "width": len(payload),
            "start": 4,
            "end": 4 + len(payload)
        }
        message["fields"].append(field_1)
        
        return message


class TruthBuilder:
    """真值构建器
    
    生成字段语义真值。
    """
    
    def __init__(self):
        self.truth_id = 0
    
    def build_field_truth(
        self,
        field_index: int,
        semantic_type: str,
        confidence: float = 1.0,
        is_hard: bool = True,
        details: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        """构建字段真值
        
        Args:
            field_index: 字段索引
            semantic_type: 语义类型
            confidence: 置信度
            is_hard: 是否为 hard evidence
            details: 详细信息
            
        Returns:
            真值字典
        """
        self.truth_id += 1
        
        truth = {
            "truth_id": self.truth_id,
            "field_index": field_index,
            "semantic_type": semantic_type,
            "confidence": confidence,
            "is_hard_evidence": is_hard,
            "details": details or {}
        }
        
        return truth


def export_messages_to_jsonl(messages: List[Dict], output_path: str):
    """导出消息到 JSONL 文件
    
    Args:
        messages: 消息列表
        output_path: 输出文件路径
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for message in messages:
            f.write(json.dumps(message, ensure_ascii=False) + '\n')


def export_truth_to_jsonl(truths: List[Dict], output_path: str):
    """导出真值到 JSONL 文件
    
    Args:
        truths: 真值列表
        output_path: 输出文件路径
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for truth in truths:
            f.write(json.dumps(truth, ensure_ascii=False) + '\n')
