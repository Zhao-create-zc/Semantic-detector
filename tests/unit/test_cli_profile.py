"""测试 profile 子命令参数解析

验证 profile 子命令的参数解析功能。
"""

import pytest
import tempfile
import os
from pathlib import Path
from semantic_detector.cli import main


class TestCliProfile:
    """profile 子命令测试"""
    
    def test_profile_missing_input_file(self):
        """测试缺少输入文件参数"""
        with pytest.raises(SystemExit) as exc_info:
            main(['profile'])
        assert exc_info.value.code == 2
    
    def test_profile_nonexistent_file(self):
        """测试不存在的文件"""
        exit_code = main(['profile', 'nonexistent_file.jsonl'])
        assert exit_code == 2
    
    def test_profile_valid_file(self):
        """测试合法文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.jsonl"
            input_path.write_text(
                '{"message_id": "msg_001", "layout_id": "L1", "direction": "request", "payload_hex": "0001", "fields": [{"field_index": 0, "start": 0, "end": 2}], "input_order": 0}\n',
                encoding='utf-8'
            )
            
            exit_code = main(['profile', str(input_path)])
            assert exit_code == 0
            
            # 检查输出文件
            profiles_path = Path(tmpdir) / "field_profiles.jsonl"
            assert profiles_path.exists()
    
    def test_profile_directory_not_file(self):
        """测试目录不是文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            exit_code = main(['profile', tmpdir])
            assert exit_code == 2
    
    def test_profile_with_output_dir(self):
        """测试带输出目录参数"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.jsonl"
            input_path.write_text(
                '{"message_id": "msg_001", "layout_id": "L1", "direction": "request", "payload_hex": "0001", "fields": [{"field_index": 0, "start": 0, "end": 2}], "input_order": 0}\n',
                encoding='utf-8'
            )
            
            output_dir = Path(tmpdir) / "output"
            exit_code = main(['profile', str(input_path), '--output-dir', str(output_dir)])
            assert exit_code == 0
            
            # 检查输出文件
            profiles_path = output_dir / "field_profiles.jsonl"
            assert profiles_path.exists()
    
    def test_profile_generates_field_profiles(self):
        """测试生成 field_profiles.jsonl"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.jsonl"
            input_path.write_text(
                '{"message_id": "msg_001", "layout_id": "L1", "direction": "request", "payload_hex": "0001", "fields": [{"field_index": 0, "start": 0, "end": 2}], "input_order": 0}\n',
                encoding='utf-8'
            )

            exit_code = main(['profile', str(input_path)])
            assert exit_code == 0

            # 检查输出文件
            profiles_path = Path(tmpdir) / "field_profiles.jsonl"
            assert profiles_path.exists()

            # 检查文件内容
            content = profiles_path.read_text(encoding='utf-8')
            assert len(content) > 0


class TestCliProfileArtifactCleanR417:
    """R417：cmd_profile 失败时清理旧产物（补齐阶段 C 遗漏）

    修复前：cmd_profile 未调用 clean_command_artifacts，build_field_profiles
    失败时旧 field_profiles.jsonl 残留。修复后：失败时旧产物被清理，
    field_profiles.jsonl 被写为空文件。
    """

    def _write_valid_input(self, path):
        """构造 8 条合法记录（满足 min_samples=8）"""
        import json as _json
        with open(path, "w", encoding="utf-8") as f:
            for i in range(1, 9):
                rec = {
                    "message_id": str(i),
                    "layout_id": "L1",
                    "direction": "request",
                    "payload_hex": "0100000016000003e86672616e6b736563726574abcd",
                    "fields": [
                        {"field_index": 0, "start": 0, "end": 1},
                        {"field_index": 1, "start": 1, "end": 5},
                    ],
                }
                f.write(_json.dumps(rec) + "\n")

    def test_profile_failure_cleans_old_artifacts(self):
        """profile 失败时旧 field_profiles.jsonl 被清理（写空文件）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.jsonl"
            self._write_valid_input(str(input_path))

            output_dir = Path(tmpdir) / "output"

            # 第一次运行：成功，产出有内容的 field_profiles.jsonl
            exit_code = main(['profile', str(input_path), '--output-dir', str(output_dir)])
            assert exit_code == 0
            profiles_path = output_dir / "field_profiles.jsonl"
            assert profiles_path.exists()
            old_content = profiles_path.read_text(encoding='utf-8')
            assert len(old_content) > 0

            # 第二次运行：用空输入文件模拟失败（0 条记录导致 build_field_profiles 无样本）
            # 实际上空文件会在 read_jsonl_file 阶段成功但 prepare_records_for_profiling 后
            # group_valid_records 为空，build_field_profiles 返回空列表（exit 0）。
            # 为了触发 build_field_profiles 失败，我们用 monkeypatch。
            import semantic_detector.cli as cli_mod
            original_build = cli_mod.cmd_profile  # 保存原始函数

            # 用一个会触发 build_field_profiles 异常的输入：字段数不一致的组
            import json as _json
            bad_input = Path(tmpdir) / "bad_input.jsonl"
            with open(bad_input, "w", encoding="utf-8") as f:
                # 单条记录，field_index=0 但 end=99 越界 → 不会在 read 阶段拒绝
                # 但会在 build_field_profiles 阶段因样本不足返回空（exit 0）
                # 所以改用 mock 方式
                f.write(_json.dumps({
                    "message_id": "1", "layout_id": "L1", "direction": "request",
                    "payload_hex": "01", "fields": [{"field_index": 0, "start": 0, "end": 1}],
                }) + "\n")

            # 用 monkeypatch 让 build_field_profiles 抛异常
            from unittest.mock import patch
            from semantic_detector.profiling import profile_builder

            with patch.object(profile_builder, 'build_field_profiles',
                              side_effect=RuntimeError("mock failure")):
                exit_code = main(['profile', str(bad_input), '--output-dir', str(output_dir)])

            # 失败退出码 1
            assert exit_code == 1

            # R417：旧 field_profiles.jsonl 被清理（写空文件覆盖）
            new_content = profiles_path.read_text(encoding='utf-8')
            assert new_content == "", (
                f"R417：失败后 field_profiles.jsonl 应为空，实际: {new_content!r}"
            )


class TestCliProfileGroupFieldCount:
    """R230: cmd_profile 接入共享准备流程并导出 rejected 测试

    修复 HIGH-2：profile 命令对字段数不一致的组**跳过**（不送入 build_field_profiles），
    为通过校验的组生成画像，并导出 rejected_groups.jsonl。
    """

    def _write_records(self, path, records):
        import json as _json

        with open(path, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(_json.dumps(rec, ensure_ascii=False) + "\n")

    def test_inconsistent_group_skipped_and_rejected_exported(self):
        """不一致组被跳过，rejected_groups.jsonl 导出，画像仍为一致组生成。

        R385：有组级拒绝时 exit 1（fail closed），但仍为一致组生成画像。
        """
        import json as _json

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
                    # L2 不一致（一条 2 字段，一条 3 字段）
                    {
                        "message_id": "m2",
                        "layout_id": "L2",
                        "direction": "request",
                        "payload_hex": "00050006",
                        "fields": [
                            {"field_index": 0, "start": 0, "end": 2},
                            {"field_index": 1, "start": 2, "end": 4},
                        ],
                        "input_order": 1,
                    },
                    {
                        "message_id": "m3",
                        "layout_id": "L2",
                        "direction": "request",
                        "payload_hex": "000500060007",
                        "fields": [
                            {"field_index": 0, "start": 0, "end": 2},
                            {"field_index": 1, "start": 2, "end": 4},
                            {"field_index": 2, "start": 4, "end": 6},
                        ],
                        "input_order": 2,
                    },
                ],
            )

            exit_code = main(["profile", str(input_path)])
            # R385: 有组级拒绝 → exit 1（fail closed）
            assert exit_code == 1, "profile 有组级拒绝应 exit 1（R385 fail closed）"

            # field_profiles.jsonl 应只含 L1 的画像（不应有 L2）
            profiles_path = Path(tmpdir) / "field_profiles.jsonl"
            assert profiles_path.exists()
            profile_layouts = set()
            for line in profiles_path.read_text(encoding="utf-8").strip().splitlines():
                profile_layouts.add(_json.loads(line)["layout_id"])
            assert profile_layouts == {"L1"}, f"不应包含被跳过的 L2，实际: {profile_layouts}"

            # rejected_groups.jsonl 应存在并记录 L2
            rejected_groups_path = Path(tmpdir) / "rejected_groups.jsonl"
            assert rejected_groups_path.exists()
            entry = _json.loads(
                rejected_groups_path.read_text(encoding="utf-8").strip().splitlines()[0]
            )
            assert entry["group_key"] == ["L2", "request"]
            assert entry["reason_code"] == "inconsistent_field_count"
            assert sorted(entry["rejected_message_ids"]) == ["m2", "m3"]

    def test_consistent_input_no_rejected_groups_file(self):
        """全一致输入时 rejected_groups.jsonl 为空文件（R391：无条件写入覆盖旧产物）。"""
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

            exit_code = main(["profile", str(input_path)])
            assert exit_code == 0

            rejected_groups_path = Path(tmpdir) / "rejected_groups.jsonl"
            # R391：rejected_groups.jsonl 必须存在且为空（无条件写入，覆盖旧产物）
            assert rejected_groups_path.exists(), (
                "R391: 全合法输入时 rejected_groups.jsonl 必须存在（空文件，覆盖旧产物）"
            )
            assert rejected_groups_path.read_text(encoding="utf-8").strip() == "", (
                "R391: 全合法输入时 rejected_groups.jsonl 必须为空"
            )
            profiles_path = Path(tmpdir) / "field_profiles.jsonl"
            assert profiles_path.exists()

    def test_all_inconsistent_exits_one_with_empty_profiles(self):
        """全部组不一致 → 画像为空且 exit 1（R385 fail closed），并导出 rejected_groups。"""
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

            exit_code = main(["profile", str(input_path)])
            # R385: 有组级拒绝 → exit 1（fail closed）
            assert exit_code == 1

            profiles_path = Path(tmpdir) / "field_profiles.jsonl"
            assert profiles_path.exists()
            # 画像为空文件
            assert profiles_path.read_text(encoding="utf-8").strip() == ""

            rejected_groups_path = Path(tmpdir) / "rejected_groups.jsonl"
            assert rejected_groups_path.exists()
            entry = _json.loads(
                rejected_groups_path.read_text(encoding="utf-8").strip().splitlines()[0]
            )
            assert entry["group_key"] == ["L1", "request"]
