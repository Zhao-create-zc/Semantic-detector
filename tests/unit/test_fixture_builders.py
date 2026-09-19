"""测试合成信息集和真值构建器

验证构建器的功能。
"""

import pytest
from pathlib import Path
from tests.fixtures.builders import (
    SyntheticMessageBuilder,
    TruthBuilder,
    export_messages_to_jsonl,
    export_truth_to_jsonl
)


class TestSyntheticMessageBuilder:
    """合成消息构建器测试"""
    
    def test_build_constant_message(self):
        """测试构建常量字段消息"""
        builder = SyntheticMessageBuilder()
        
        message = builder.build_constant_message([
            b'\x00\x00\x00\x01',
            b'\x00\x00\x00\x02'
        ])
        
        assert "message_id" in message
        assert "layout_id" in message
        assert "direction" in message
        assert "fields" in message
        assert len(message["fields"]) == 2
    
    def test_message_id_increment(self):
        """测试消息 ID 递增"""
        builder = SyntheticMessageBuilder()
        
        msg1 = builder.build_constant_message([b'\x00'])
        msg2 = builder.build_constant_message([b'\x00'])
        
        assert msg2["message_id"] == msg1["message_id"] + 1
    
    def test_field_hex_valid(self):
        """测试字段 hex 合法"""
        builder = SyntheticMessageBuilder()
        
        message = builder.build_constant_message([
            b'\x01\x02\x03\x04',
            b'\xff\xfe\xfd\xfc'
        ])
        
        for field in message["fields"]:
            hex_value = field["value_hex"]
            assert len(hex_value) == field["width"] * 2
            assert all(c in '0123456789abcdef' for c in hex_value)
    
    def test_field_boundaries(self):
        """测试字段边界正确"""
        builder = SyntheticMessageBuilder()
        
        message = builder.build_constant_message([
            b'\x00\x00',
            b'\x00\x00\x00',
            b'\x00'
        ])
        
        assert message["fields"][0]["start"] == 0
        assert message["fields"][0]["end"] == 2
        assert message["fields"][1]["start"] == 2
        assert message["fields"][1]["end"] == 5
        assert message["fields"][2]["start"] == 5
        assert message["fields"][2]["end"] == 6
    
    def test_build_total_length_message(self):
        """测试构建 total_length 消息"""
        builder = SyntheticMessageBuilder()
        
        message = builder.build_total_length_message(100, b'\x00' * 10)
        
        assert len(message["fields"]) == 2
        assert message["fields"][0]["width"] == 4
    
    def test_build_remaining_length_message(self):
        """测试构建 remaining_length 消息"""
        builder = SyntheticMessageBuilder()
        
        message = builder.build_remaining_length_message(127, b'\x00' * 10)
        
        assert len(message["fields"]) == 2
        assert message["fields"][0]["width"] == 1
    
    def test_build_timestamp_message(self):
        """测试构建时间戳消息"""
        builder = SyntheticMessageBuilder()
        
        message = builder.build_timestamp_message(1609459200, b'\x00' * 10)
        
        assert len(message["fields"]) == 2
        assert message["fields"][0]["width"] == 4


class TestTruthBuilder:
    """真值构建器测试"""
    
    def test_build_field_truth(self):
        """测试构建字段真值"""
        builder = TruthBuilder()
        
        truth = builder.build_field_truth(
            field_index=0,
            semantic_type="integer",
            confidence=1.0,
            is_hard=True
        )
        
        assert "truth_id" in truth
        assert truth["field_index"] == 0
        assert truth["semantic_type"] == "integer"
        assert truth["confidence"] == 1.0
        assert truth["is_hard_evidence"] is True
    
    def test_truth_id_increment(self):
        """测试真值 ID 递增"""
        builder = TruthBuilder()
        
        truth1 = builder.build_field_truth(0, "integer")
        truth2 = builder.build_field_truth(1, "string")
        
        assert truth2["truth_id"] == truth1["truth_id"] + 1


class TestExportFunctions:
    """导出函数测试"""
    
    def test_export_messages_to_jsonl(self, tmp_path):
        """测试导出消息到 JSONL"""
        builder = SyntheticMessageBuilder()
        
        messages = [
            builder.build_constant_message([b'\x00']),
            builder.build_constant_message([b'\x01'])
        ]
        
        output_path = tmp_path / "messages.jsonl"
        export_messages_to_jsonl(messages, str(output_path))
        
        assert output_path.exists()
        assert output_path.stat().st_size > 0
    
    def test_export_truth_to_jsonl(self, tmp_path):
        """测试导出真值到 JSONL"""
        builder = TruthBuilder()
        
        truths = [
            builder.build_field_truth(0, "integer"),
            builder.build_field_truth(1, "string")
        ]
        
        output_path = tmp_path / "truth.jsonl"
        export_truth_to_jsonl(truths, str(output_path))
        
        assert output_path.exists()
        assert output_path.stat().st_size > 0
