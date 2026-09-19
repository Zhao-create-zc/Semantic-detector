"""测试 validate 子命令参数解析

验证 validate 子命令的参数解析功能。
"""

import pytest
import tempfile
import os
from pathlib import Path
from semantic_detector.cli import main


class TestCliValidate:
    """validate 子命令测试"""
    
    def test_validate_missing_input_file(self):
        """测试缺少输入文件参数"""
        with pytest.raises(SystemExit) as exc_info:
            main(['validate'])
        assert exc_info.value.code == 2
    
    def test_validate_nonexistent_file(self):
        """测试不存在的文件"""
        exit_code = main(['validate', 'nonexistent_file.jsonl'])
        assert exit_code == 2
    
    def test_validate_valid_file(self):
        """测试合法文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.jsonl"
            input_path.write_text('{"message_id": "msg_001", "layout_id": "L1", "direction": "request", "payload_hex": "0001", "fields": [{"field_index": 0, "start": 0, "end": 2}], "input_order": 0}\n', encoding='utf-8')
            
            exit_code = main(['validate', str(input_path)])
            assert exit_code == 0
            
            # 检查输出文件
            validated_path = Path(tmpdir) / "validated.jsonl"
            assert validated_path.exists()
    
    def test_validate_directory_not_file(self):
        """测试目录不是文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            exit_code = main(['validate', tmpdir])
            assert exit_code == 2
    
    def test_validate_with_output_dir(self):
        """测试带输出目录参数"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.jsonl"
            input_path.write_text('{"message_id": "msg_001", "layout_id": "L1", "direction": "request", "payload_hex": "0001", "fields": [{"field_index": 0, "start": 0, "end": 2}], "input_order": 0}\n', encoding='utf-8')
            
            output_dir = Path(tmpdir) / "output"
            exit_code = main(['validate', str(input_path), '--output-dir', str(output_dir)])
            assert exit_code == 0
            
            # 检查输出文件
            validated_path = output_dir / "validated.jsonl"
            assert validated_path.exists()
    
    def test_validate_generates_validated_and_rejected(self):
        """测试生成 validated 和 rejected 文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.jsonl"
            # 写入一条有效记录和一条无效记录
            input_path.write_text(
                '{"message_id": "msg_001", "layout_id": "L1", "direction": "request", "payload_hex": "0001", "fields": [{"field_index": 0, "start": 0, "end": 2}], "input_order": 0}\n'
                '{"invalid": "record"}\n',
                encoding='utf-8'
            )

            exit_code = main(['validate', str(input_path)])
            # R342：任何 rejection > 0 → exit 1（1 条 JSON 级拒绝）
            assert exit_code == 1

            # 检查输出文件
            validated_path = Path(tmpdir) / "validated.jsonl"
            rejected_path = Path(tmpdir) / "rejected.jsonl"
            assert validated_path.exists() or rejected_path.exists()


class TestCliValidateGroupFieldCount:
    """R229: cmd_validate 接入组级字段数校验测试

    修复 HIGH-2：同 (layout_id, direction) 组内字段数不一致时，
    validate 命令必须报错并退出非零，并导出 rejected_groups.jsonl。
    """

    def _write_records(self, path, records):
        import json as _json

        with open(path, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(_json.dumps(rec, ensure_ascii=False) + "\n")

    def test_inconsistent_group_exits_nonzero(self):
        """同组字段数不一致 → 退出码 1。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.jsonl"
            # 同组 L1/request，一条 1 字段，一条 2 字段 → 整组拒绝
            self._write_records(
                input_path,
                [
                    {
                        "message_id": "m1",
                        "layout_id": "L1",
                        "direction": "request",
                        "payload_hex": "0001",
                        "fields": [{"field_index": 0, "start": 0, "end": 2}],
                        "input_order": 0,
                    },
                    {
                        "message_id": "m2",
                        "layout_id": "L1",
                        "direction": "request",
                        "payload_hex": "00010002",
                        "fields": [
                            {"field_index": 0, "start": 0, "end": 2},
                            {"field_index": 1, "start": 2, "end": 4},
                        ],
                        "input_order": 1,
                    },
                ],
            )

            exit_code = main(["validate", str(input_path)])
            assert exit_code == 1, "不一致组应退出非零"

    def test_inconsistent_group_exports_rejected_groups(self):
        """不一致组导出 rejected_groups.jsonl，含 group_key/field_counts/reason_code。"""
        import json as _json

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.jsonl"
            self._write_records(
                input_path,
                [
                    {
                        "message_id": "m1",
                        "layout_id": "L1",
                        "direction": "request",
                        "payload_hex": "0001",
                        "fields": [{"field_index": 0, "start": 0, "end": 2}],
                        "input_order": 0,
                    },
                    {
                        "message_id": "m2",
                        "layout_id": "L1",
                        "direction": "request",
                        "payload_hex": "00010002",
                        "fields": [
                            {"field_index": 0, "start": 0, "end": 2},
                            {"field_index": 1, "start": 2, "end": 4},
                        ],
                        "input_order": 1,
                    },
                ],
            )

            exit_code = main(["validate", str(input_path)])
            assert exit_code == 1

            rejected_groups_path = Path(tmpdir) / "rejected_groups.jsonl"
            assert rejected_groups_path.exists(), "rejected_groups.jsonl 应存在"
            lines = rejected_groups_path.read_text(encoding="utf-8").strip().splitlines()
            assert len(lines) == 1
            entry = _json.loads(lines[0])
            assert entry["group_key"] == ["L1", "request"]
            assert entry["record_count"] == 2
            assert entry["reason_code"] == "inconsistent_field_count"
            # field_counts 按 field_count 升序: [[1,1],[2,1]]
            assert entry["field_counts"] == [[1, 1], [2, 1]]
            assert sorted(entry["rejected_message_ids"]) == ["m1", "m2"]

    def test_consistent_groups_exit_zero(self):
        """全一致组 → 退出码 0，不生成 rejected_groups.jsonl。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.jsonl"
            self._write_records(
                input_path,
                [
                    {
                        "message_id": "m1",
                        "layout_id": "L1",
                        "direction": "request",
                        "payload_hex": "00010002",
                        "fields": [
                            {"field_index": 0, "start": 0, "end": 2},
                            {"field_index": 1, "start": 2, "end": 4},
                        ],
                        "input_order": 0,
                    },
                    {
                        "message_id": "m2",
                        "layout_id": "L1",
                        "direction": "request",
                        "payload_hex": "00030004",
                        "fields": [
                            {"field_index": 0, "start": 0, "end": 2},
                            {"field_index": 1, "start": 2, "end": 4},
                        ],
                        "input_order": 1,
                    },
                ],
            )

            exit_code = main(["validate", str(input_path)])
            assert exit_code == 0

            # R342：rejected_groups.jsonl 无条件写空文件（无拒绝时为空）
            rejected_groups_path = Path(tmpdir) / "rejected_groups.jsonl"
            assert rejected_groups_path.exists()
            assert rejected_groups_path.read_text(encoding='utf-8') == '', (
                "一致组时 rejected_groups.jsonl 应为空文件"
            )
            validated_path = Path(tmpdir) / "validated.jsonl"
            assert validated_path.exists()

    def test_mixed_consistent_and_independent_inconsistent_group(self):
        """一个一致组保留，一个不一致组拒绝，退出码 1。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.jsonl"
            self._write_records(
                input_path,
                [
                    # L1 一致（2 字段）
                    {
                        "message_id": "m1",
                        "layout_id": "L1",
                        "direction": "request",
                        "payload_hex": "00010002",
                        "fields": [
                            {"field_index": 0, "start": 0, "end": 2},
                            {"field_index": 1, "start": 2, "end": 4},
                        ],
                        "input_order": 0,
                    },
                    {
                        "message_id": "m2",
                        "layout_id": "L1",
                        "direction": "request",
                        "payload_hex": "00030004",
                        "fields": [
                            {"field_index": 0, "start": 0, "end": 2},
                            {"field_index": 1, "start": 2, "end": 4},
                        ],
                        "input_order": 1,
                    },
                    # L2 不一致（一条 2 字段，一条 3 字段）
                    {
                        "message_id": "m3",
                        "layout_id": "L2",
                        "direction": "request",
                        "payload_hex": "00050006",
                        "fields": [
                            {"field_index": 0, "start": 0, "end": 2},
                            {"field_index": 1, "start": 2, "end": 4},
                        ],
                        "input_order": 2,
                    },
                    {
                        "message_id": "m4",
                        "layout_id": "L2",
                        "direction": "request",
                        "payload_hex": "000500060007",
                        "fields": [
                            {"field_index": 0, "start": 0, "end": 2},
                            {"field_index": 1, "start": 2, "end": 4},
                            {"field_index": 2, "start": 4, "end": 6},
                        ],
                        "input_order": 3,
                    },
                ],
            )

            exit_code = main(["validate", str(input_path)])
            assert exit_code == 1

            # validated.jsonl 应只含 L1 的两条
            validated_path = Path(tmpdir) / "validated.jsonl"
            assert validated_path.exists()
            import json as _json

            validated_ids = [
                _json.loads(line)["message_id"]
                for line in validated_path.read_text(encoding="utf-8").strip().splitlines()
            ]
            assert sorted(validated_ids) == ["m1", "m2"]

            rejected_groups_path = Path(tmpdir) / "rejected_groups.jsonl"
            assert rejected_groups_path.exists()
            entry = _json.loads(
                rejected_groups_path.read_text(encoding="utf-8").strip().splitlines()[0]
            )
            assert entry["group_key"] == ["L2", "request"]
            assert sorted(entry["rejected_message_ids"]) == ["m3", "m4"]


class TestCliValidateJsonRejectionExitR341:
    """R341：新增 Validate JSON 级拒绝退出测试（HIGH-4 阶段 C 首轮）

    精确复现：1 valid + 1 invalid JSON → validate 不得 exit 0

    验收：修复前失败（exit 0），不修改生产代码。
    """

    def test_one_valid_one_invalid_json_exits_nonzero(self):
        """R341: 1 valid + 1 invalid JSON → exit != 0

        复现 HIGH-4：cmd_validate 只检查组级 rejections，
        忽略 JSON 级 rejected_records，导致 exit 0。
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, 'input.jsonl')
            # 1 valid（fields 内 field 含 field_index/start/end 满足 read_jsonl_file）+ 1 invalid JSON
            with open(input_path, 'w', encoding='utf-8') as f:
                f.write('{"message_id": "m1", "layout_id": "L1", "direction": "request", "payload_hex": "0001", "fields": [{"name": "f1", "raw_hex": "00", "field_index": 0, "start": 0, "end": 1, "input_order": 0}]}\n')
                f.write('{invalid json}\n')

            exit_code = main(['validate', input_path])
            assert exit_code != 0, (
                f"1 valid + 1 invalid JSON 时 validate 应返回非零退出码，实际: {exit_code}"
            )

    def test_invalid_json_produces_rejected_jsonl(self):
        """R341: invalid JSON 应导出到 rejected.jsonl"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, 'input.jsonl')
            with open(input_path, 'w', encoding='utf-8') as f:
                f.write('{"message_id": "m1", "layout_id": "L1", "direction": "request", "payload_hex": "0001", "fields": [{"name": "f1", "raw_hex": "00", "field_index": 0, "start": 0, "end": 1, "input_order": 0}]}\n')
                f.write('{invalid json}\n')

            main(['validate', input_path])

            rejected_path = os.path.join(tmpdir, 'rejected.jsonl')
            assert os.path.exists(rejected_path), (
                f"invalid JSON 应导出到 rejected.jsonl，但文件不存在"
            )
            with open(rejected_path, 'r', encoding='utf-8') as f:
                lines = [line for line in f if line.strip()]
            assert len(lines) == 1, (
                f"rejected.jsonl 应有 1 行，实际: {len(lines)}"
            )

    def test_all_valid_json_exits_zero(self):
        """R341: 全部合法 JSON 时 exit 0（对照测试）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, 'input.jsonl')
            with open(input_path, 'w', encoding='utf-8') as f:
                f.write('{"message_id": "m1", "layout_id": "L1", "direction": "request", "payload_hex": "0001", "fields": [{"name": "f1", "raw_hex": "00", "field_index": 0, "start": 0, "end": 1, "input_order": 0}]}\n')
                f.write('{"message_id": "m2", "layout_id": "L1", "direction": "request", "payload_hex": "0002", "fields": [{"name": "f1", "raw_hex": "01", "field_index": 0, "start": 0, "end": 1, "input_order": 0}]}\n')

            exit_code = main(['validate', input_path])
            assert exit_code == 0, (
                f"全部合法 JSON 时 validate 应返回 0，实际: {exit_code}"
            )


class TestCliValidateUnifiedRejectionExitR342:
    """R342：修复 Validate 统一拒绝计数和退出码

    验收：
    - 任何 rejection > 0（JSON 级 + 组级）→ exit 1
    - 无 rejection → exit 0
    - validated 文件只含合法记录
    - rejected 文件含 JSON 级全部拒绝
    - rejected_groups 文件含组级全部拒绝
    - 无拒绝时 3 个文件都写空文件（防止旧产物残留）
    """

    def test_json_rejection_only_exits_nonzero(self):
        """R342: 仅 JSON 级拒绝（无组级拒绝）→ exit 1"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, 'input.jsonl')
            with open(input_path, 'w', encoding='utf-8') as f:
                f.write('{"message_id": "m1", "layout_id": "L1", "direction": "request", "payload_hex": "0001", "fields": [{"name": "f1", "raw_hex": "00", "field_index": 0, "start": 0, "end": 1, "input_order": 0}]}\n')
                f.write('{invalid json}\n')

            exit_code = main(['validate', input_path])
            assert exit_code == 1, (
                f"仅 JSON 级拒绝应返回 1，实际: {exit_code}"
            )

    def test_no_rejection_all_three_files_empty(self):
        """R342: 无拒绝时 validated/rejected/rejected_groups 都写空文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 预先写入旧文件（模拟残留）
            for fname in ['validated.jsonl', 'rejected.jsonl', 'rejected_groups.jsonl']:
                with open(os.path.join(tmpdir, fname), 'w', encoding='utf-8') as f:
                    f.write('STALE CONTENT\n')

            input_path = os.path.join(tmpdir, 'input.jsonl')
            # 2 条一致记录（构成一致组，无拒绝）
            with open(input_path, 'w', encoding='utf-8') as f:
                f.write('{"message_id": "m1", "layout_id": "L1", "direction": "request", "payload_hex": "0001", "fields": [{"name": "f1", "raw_hex": "00", "field_index": 0, "start": 0, "end": 1, "input_order": 0}]}\n')
                f.write('{"message_id": "m2", "layout_id": "L1", "direction": "request", "payload_hex": "0002", "fields": [{"name": "f1", "raw_hex": "01", "field_index": 0, "start": 0, "end": 1, "input_order": 0}]}\n')

            exit_code = main(['validate', input_path])
            assert exit_code == 0

            # rejected.jsonl 和 rejected_groups.jsonl 应为空（无残留）
            rejected_content = open(os.path.join(tmpdir, 'rejected.jsonl'), 'r', encoding='utf-8').read()
            rejected_groups_content = open(os.path.join(tmpdir, 'rejected_groups.jsonl'), 'r', encoding='utf-8').read()
            assert rejected_content == '', f"rejected.jsonl 应为空，实际: {rejected_content!r}"
            assert rejected_groups_content == '', f"rejected_groups.jsonl 应为空，实际: {rejected_groups_content!r}"

            # validated.jsonl 应含 2 条合法记录（非 STALE CONTENT）
            validated_content = open(os.path.join(tmpdir, 'validated.jsonl'), 'r', encoding='utf-8').read()
            assert 'STALE CONTENT' not in validated_content
            assert validated_content.count('\n') == 2

    def test_rejected_file_contains_all_json_rejections(self):
        """R342: rejected.jsonl 含全部 JSON 级拒绝"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, 'input.jsonl')
            with open(input_path, 'w', encoding='utf-8') as f:
                f.write('{"message_id": "m1", "layout_id": "L1", "direction": "request", "payload_hex": "0001", "fields": [{"name": "f1", "raw_hex": "00", "field_index": 0, "start": 0, "end": 1, "input_order": 0}]}\n')
                f.write('{invalid json 1}\n')
                f.write('{invalid json 2}\n')

            exit_code = main(['validate', input_path])
            assert exit_code == 1

            rejected_path = os.path.join(tmpdir, 'rejected.jsonl')
            with open(rejected_path, 'r', encoding='utf-8') as f:
                lines = [line for line in f if line.strip()]
            assert len(lines) == 2, (
                f"rejected.jsonl 应有 2 行（2 条 JSON 级拒绝），实际: {len(lines)}"
            )
