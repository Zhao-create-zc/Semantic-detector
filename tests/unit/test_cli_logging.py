"""测试 CLI 日志功能

验证 CLI 的日志功能。
"""

import pytest
import tempfile
import os
from pathlib import Path
from semantic_detector.cli import main


def _valid_record(msg_id, input_order=0):
    """R344：合法记录（满足 read_jsonl_file 必填字段）"""
    import json
    return json.dumps({
        "message_id": msg_id,
        "layout_id": "L1",
        "direction": "request",
        "payload_hex": "00010002",
        "fields": [
            {"field_index": 0, "start": 0, "end": 2, "input_order": input_order},
            {"field_index": 1, "start": 2, "end": 4, "input_order": input_order},
        ],
        "input_order": input_order,
    })


class TestCliLogging:
    """CLI 日志测试"""

    def test_run_creates_log_file(self):
        """测试 run 命令创建日志文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.jsonl"
            input_path.write_text(_valid_record("m1") + "\n", encoding='utf-8')

            output_dir = Path(tmpdir) / "output"
            exit_code = main(['run', str(input_path), '--output-dir', str(output_dir)])
            assert exit_code == 0

            # 检查日志文件存在
            log_path = output_dir / "run.log"
            assert log_path.exists()

    def test_log_contains_timestamp(self):
        """测试日志包含时间戳"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.jsonl"
            input_path.write_text(_valid_record("m1") + "\n", encoding='utf-8')

            output_dir = Path(tmpdir) / "output"
            exit_code = main(['run', str(input_path), '--output-dir', str(output_dir)])
            assert exit_code == 0

            # 检查日志包含时间戳
            log_path = output_dir / "run.log"
            log_content = log_path.read_text(encoding='utf-8')
            assert "[" in log_content
            assert "]" in log_content

    def test_log_contains_stages(self):
        """测试日志包含阶段信息"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.jsonl"
            input_path.write_text(_valid_record("m1") + "\n", encoding='utf-8')

            output_dir = Path(tmpdir) / "output"
            exit_code = main(['run', str(input_path), '--output-dir', str(output_dir)])
            assert exit_code == 0

            # 检查日志包含阶段信息
            log_path = output_dir / "run.log"
            log_content = log_path.read_text(encoding='utf-8')
            assert "阶段 1" in log_content
            assert "阶段 2" in log_content
            assert "阶段 3" in log_content

    def test_log_contains_results(self):
        """测试日志包含结果信息"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.jsonl"
            input_path.write_text(_valid_record("m1") + "\n", encoding='utf-8')

            output_dir = Path(tmpdir) / "output"
            exit_code = main(['run', str(input_path), '--output-dir', str(output_dir)])
            assert exit_code == 0

            # 检查日志包含结果信息
            log_path = output_dir / "run.log"
            log_content = log_path.read_text(encoding='utf-8')
            assert "导出" in log_content
            assert "流水线完成" in log_content

    def test_log_with_empty_input(self):
        """测试空输入的日志（R344: 空文件 → 0 valid → exit 1）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.jsonl"
            input_path.write_text('', encoding='utf-8')

            output_dir = Path(tmpdir) / "output"
            exit_code = main(['run', str(input_path), '--output-dir', str(output_dir)])
            # R344：0 有效记录 → fail closed (exit 1)
            assert exit_code == 1

            # 检查日志文件存在
            log_path = output_dir / "run.log"
            assert log_path.exists()

    def test_log_with_multiple_records(self):
        """测试多条记录的日志"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.jsonl"
            input_path.write_text(
                _valid_record("m1", 0) + "\n" + _valid_record("m2", 1) + "\n",
                encoding='utf-8'
            )

            output_dir = Path(tmpdir) / "output"
            exit_code = main(['run', str(input_path), '--output-dir', str(output_dir)])
            assert exit_code == 0

            # 检查日志文件存在
            log_path = output_dir / "run.log"
            assert log_path.exists()

            # 检查日志包含多条记录信息
            log_content = log_path.read_text(encoding='utf-8')
            assert "2 条" in log_content or "2 个" in log_content
