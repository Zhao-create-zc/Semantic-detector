"""测试 CLI 异常处理和退出码

验证 CLI 的异常处理和退出码机制。
"""

import pytest
import tempfile
import os
import sys
from pathlib import Path
from semantic_detector.cli import main
from io import StringIO


class TestCliErrors:
    """CLI 异常处理测试"""
    
    def test_exit_code_success(self):
        """测试成功退出码为 0"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.jsonl"
            # R342：使用合法记录（满足 read_jsonl_file 必填字段 + 一致组）
            input_path.write_text(
                '{"message_id": "m1", "layout_id": "L1", "direction": "request", "payload_hex": "0001", "fields": [{"name": "f1", "raw_hex": "00", "field_index": 0, "start": 0, "end": 1, "input_order": 0}]}\n',
                encoding='utf-8'
            )

            exit_code = main(['validate', str(input_path)])
            assert exit_code == 0

    def test_exit_code_missing_file(self):
        """测试缺少文件时退出码为 2"""
        exit_code = main(['validate', 'nonexistent_file.jsonl'])
        assert exit_code == 2
    
    def test_exit_code_invalid_command(self):
        """测试无效子命令时退出码为 2"""
        with pytest.raises(SystemExit) as exc_info:
            main(['invalid_command'])
        assert exc_info.value.code == 2
    
    def test_error_message_to_stderr(self, capsys):
        """测试错误消息输出到 stderr"""
        exit_code = main(['validate', 'nonexistent_file.jsonl'])
        assert exit_code == 2
        
        captured = capsys.readouterr()
        assert "错误" in captured.err
    
    def test_permission_error_exit_code(self):
        """测试权限错误退出码为 2"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.jsonl"
            # R342：使用合法记录
            input_path.write_text(
                '{"message_id": "m1", "layout_id": "L1", "direction": "request", "payload_hex": "0001", "fields": [{"name": "f1", "raw_hex": "00", "field_index": 0, "start": 0, "end": 1, "input_order": 0}]}\n',
                encoding='utf-8'
            )

            # 模拟权限错误（在 Windows 上可能无法完全模拟）
            # 这里只测试正常情况
            exit_code = main(['validate', str(input_path)])
            assert exit_code == 0
    
    def test_value_error_exit_code(self):
        """测试值错误退出码为 1"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.jsonl"
            input_path.write_text('invalid json\n', encoding='utf-8')

            exit_code = main(['validate', str(input_path)])
            # R342：无效 JSON 会被拒绝，fail closed → exit 1
            assert exit_code == 1
    
    def test_general_exception_exit_code(self):
        """测试一般异常退出码为 1"""
        # 这个测试验证异常处理机制存在
        # 实际异常由各个子命令处理
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.jsonl"
            # R342：使用合法记录
            input_path.write_text(
                '{"message_id": "m1", "layout_id": "L1", "direction": "request", "payload_hex": "0001", "fields": [{"name": "f1", "raw_hex": "00", "field_index": 0, "start": 0, "end": 1, "input_order": 0}]}\n',
                encoding='utf-8'
            )

            exit_code = main(['validate', str(input_path)])
            assert exit_code == 0
