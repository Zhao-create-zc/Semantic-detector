"""R351: 命令产物所有权清单和原子写入测试

验证：
- COMMAND_ARTIFACTS 5 个命令的产物清单已定义
- clean_command_artifacts 清理本命令旧产物
- clean_command_artifacts 不删除非本命令文件/子目录/用户输入
- atomic_write_jsonl/json/csv/text 原子写入
- 空结果写空文件（不保留旧文件）
- 原子替换无临时文件残留
"""

import json
import os
import tempfile
from pathlib import Path

from semantic_detector.io.artifact_manager import (
    COMMAND_ARTIFACTS,
    get_command_artifacts,
    clean_command_artifacts,
    atomic_write_jsonl,
    atomic_write_json,
    atomic_write_csv,
    atomic_write_text,
)


class TestCommandArtifactsR351:
    """R351: 命令产物所有权清单测试"""

    def test_five_commands_defined(self):
        """R351: 5 个命令（validate/profile/infer/run/evaluate）的产物清单已定义"""
        assert "validate" in COMMAND_ARTIFACTS
        assert "profile" in COMMAND_ARTIFACTS
        assert "infer" in COMMAND_ARTIFACTS
        assert "run" in COMMAND_ARTIFACTS
        assert "evaluate" in COMMAND_ARTIFACTS
        assert len(COMMAND_ARTIFACTS) == 5

    def test_validate_artifacts(self):
        """R351: validate 命令拥有 validated/rejected/rejected_groups"""
        artifacts = get_command_artifacts("validate")
        assert "validated.jsonl" in artifacts
        assert "rejected.jsonl" in artifacts
        assert "rejected_groups.jsonl" in artifacts

    def test_profile_artifacts(self):
        """R351: profile 命令拥有 field_profiles/rejected_groups"""
        artifacts = get_command_artifacts("profile")
        assert "field_profiles.jsonl" in artifacts
        assert "rejected_groups.jsonl" in artifacts

    def test_infer_artifacts(self):
        """R351: infer 命令拥有 predictions"""
        artifacts = get_command_artifacts("infer")
        assert "predictions.jsonl" in artifacts

    def test_run_artifacts_include_all_outputs(self):
        """R351: run 命令包含所有输出（validated/rejected/rejected_groups/field_profiles/predictions/manifest/run.log）"""
        artifacts = get_command_artifacts("run")
        assert "validated.jsonl" in artifacts
        assert "rejected.jsonl" in artifacts
        assert "rejected_groups.jsonl" in artifacts
        assert "field_profiles.jsonl" in artifacts
        assert "predictions.jsonl" in artifacts
        assert "manifest.json" in artifacts
        assert "run.log" in artifacts
        assert len(artifacts) == 7

    def test_evaluate_artifacts(self):
        """R351: evaluate 命令拥有 rejected_ground_truth/metrics/per_label/confusion/errors"""
        artifacts = get_command_artifacts("evaluate")
        assert "rejected_ground_truth.jsonl" in artifacts
        assert "metrics.json" in artifacts
        assert "per_label_metrics.csv" in artifacts
        assert "confusion_matrix.csv" in artifacts
        assert "errors.jsonl" in artifacts

    def test_unknown_command_returns_empty(self):
        """R351: 未知命令返回空元组"""
        assert get_command_artifacts("unknown") == ()
        assert get_command_artifacts("") == ()


class TestCleanCommandArtifactsR351:
    """R351: clean_command_artifacts 清理旧产物测试"""

    def test_removes_owned_files(self):
        """R351: 清理本命令拥有的旧产物文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建 validate 命令的旧产物
            for filename in ["validated.jsonl", "rejected.jsonl", "rejected_groups.jsonl"]:
                (Path(tmpdir) / filename).write_text("old content", encoding="utf-8")

            removed = clean_command_artifacts(tmpdir, "validate")

            assert sorted(removed) == ["rejected.jsonl", "rejected_groups.jsonl", "validated.jsonl"]
            for filename in ["validated.jsonl", "rejected.jsonl", "rejected_groups.jsonl"]:
                assert not (Path(tmpdir) / filename).exists()

    def test_preserves_other_command_files(self):
        """R351: 清理 validate 时不删除 evaluate 的文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # validate 的文件
            (Path(tmpdir) / "validated.jsonl").write_text("validate data", encoding="utf-8")
            # evaluate 的文件
            (Path(tmpdir) / "metrics.json").write_text('{"accuracy": 0.9}', encoding="utf-8")
            (Path(tmpdir) / "errors.jsonl").write_text("error data", encoding="utf-8")

            removed = clean_command_artifacts(tmpdir, "validate")

            assert "validated.jsonl" in removed
            assert "metrics.json" not in removed
            assert "errors.jsonl" not in removed
            # evaluate 的文件仍然存在
            assert (Path(tmpdir) / "metrics.json").exists()
            assert (Path(tmpdir) / "errors.jsonl").exists()

    def test_preserves_subdirs(self):
        """R351: 不删除子目录（不删除其他 run_id 目录）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建子目录（模拟其他 run_id 目录）
            subdir = Path(tmpdir) / "run_123"
            subdir.mkdir()
            (subdir / "manifest.json").write_text("old run data", encoding="utf-8")
            # 创建 run 命令的旧产物
            (Path(tmpdir) / "manifest.json").write_text("current run", encoding="utf-8")

            removed = clean_command_artifacts(tmpdir, "run")

            assert "manifest.json" in removed
            # 子目录及其内容未被删除
            assert subdir.exists()
            assert (subdir / "manifest.json").exists()

    def test_preserves_user_input(self):
        """R351: 不删除用户输入文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 用户输入文件（不在任何命令的产物清单中）
            user_input = Path(tmpdir) / "input.jsonl"
            user_input.write_text('{"message_id": "m1"}', encoding="utf-8")
            # run 命令的旧产物
            (Path(tmpdir) / "predictions.jsonl").write_text("old predictions", encoding="utf-8")

            removed = clean_command_artifacts(tmpdir, "run")

            assert "predictions.jsonl" in removed
            # 用户输入未被删除
            assert user_input.exists()
            assert user_input.read_text(encoding="utf-8") == '{"message_id": "m1"}'

    def test_nonexistent_directory_no_error(self):
        """R351: 不存在的目录不报错"""
        removed = clean_command_artifacts("/nonexistent/path/xyz", "run")
        assert removed == []

    def test_no_artifacts_to_clean_returns_empty(self):
        """R351: 目录中没有本命令产物时返回空列表"""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "other.txt").write_text("other", encoding="utf-8")
            removed = clean_command_artifacts(tmpdir, "run")
            assert removed == []

    def test_partial_files_removed(self):
        """R351: 只删除存在的文件，不存在的跳过"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 只创建 run 命令的部分产物
            (Path(tmpdir) / "validated.jsonl").write_text("data", encoding="utf-8")
            # predictions.jsonl 和 manifest.json 不存在

            removed = clean_command_artifacts(tmpdir, "run")

            assert "validated.jsonl" in removed
            assert "predictions.jsonl" not in removed
            assert "manifest.json" not in removed


class TestAtomicWriteJsonlR351:
    """R351: atomic_write_jsonl 原子写入测试"""

    def test_empty_records_writes_empty_file(self):
        """R351: 空列表写空文件（不保留旧文件）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.jsonl"
            # 先写旧内容
            output_path.write_text("old content\n", encoding="utf-8")

            atomic_write_jsonl(output_path, [])

            # 旧内容被替换为空文件
            assert output_path.exists()
            assert output_path.read_text(encoding="utf-8") == ""

    def test_with_records(self):
        """R351: 有记录时正常写入"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.jsonl"
            records = [
                {"id": 1, "name": "first"},
                {"id": 2, "name": "second"},
            ]

            atomic_write_jsonl(output_path, records)

            lines = output_path.read_text(encoding="utf-8").strip().splitlines()
            assert len(lines) == 2
            assert json.loads(lines[0]) == {"id": 1, "name": "first"}
            assert json.loads(lines[1]) == {"id": 2, "name": "second"}

    def test_atomic_replace_no_tmp_residual(self):
        """R351: 原子替换后无临时文件残留"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.jsonl"

            atomic_write_jsonl(output_path, [{"id": 1}])

            # 目录中只有目标文件，没有 .tmp 临时文件
            files = list(Path(tmpdir).iterdir())
            assert len(files) == 1
            assert files[0].name == "output.jsonl"

    def test_replaces_old_content_completely(self):
        """R351: 原子替换旧文件内容被完全替换"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.jsonl"
            # 旧文件有 3 行
            atomic_write_jsonl(output_path, [{"id": 1}, {"id": 2}, {"id": 3}])

            # 新写入只有 1 行
            atomic_write_jsonl(output_path, [{"id": 99}])

            lines = output_path.read_text(encoding="utf-8").strip().splitlines()
            assert len(lines) == 1
            assert json.loads(lines[0]) == {"id": 99}

    def test_with_serializer(self):
        """R351: 使用 serializer 函数转换记录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.jsonl"

            class Record:
                def __init__(self, value):
                    self.value = value

            def serializer(rec):
                return {"serialized_value": rec.value}

            atomic_write_jsonl(output_path, [Record(1), Record(2)], serializer=serializer)

            lines = output_path.read_text(encoding="utf-8").strip().splitlines()
            assert json.loads(lines[0]) == {"serialized_value": 1}
            assert json.loads(lines[1]) == {"serialized_value": 2}

    def test_creates_parent_dir(self):
        """R351: 自动创建父目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "subdir" / "output.jsonl"

            atomic_write_jsonl(output_path, [{"id": 1}])

            assert output_path.exists()
            assert output_path.parent.is_dir()


class TestAtomicWriteJsonR351:
    """R351: atomic_write_json 原子写入测试"""

    def test_writes_json_with_indent(self):
        """R351: 写入 JSON 带缩进"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "data.json"
            data = {"key": "value", "number": 42}

            atomic_write_json(output_path, data, indent=2)

            content = output_path.read_text(encoding="utf-8")
            assert json.loads(content) == data
            # 有缩进（包含换行）
            assert "\n" in content

    def test_replaces_old_json(self):
        """R351: 原子替换旧 JSON 文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "data.json"
            # 旧内容
            output_path.write_text('{"old": true}', encoding="utf-8")

            atomic_write_json(output_path, {"new": True})

            content = output_path.read_text(encoding="utf-8")
            assert json.loads(content) == {"new": True}
            assert "old" not in content

    def test_no_tmp_residual(self):
        """R351: 原子替换后无临时文件残留"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "data.json"

            atomic_write_json(output_path, {"key": "value"})

            files = list(Path(tmpdir).iterdir())
            assert len(files) == 1
            assert files[0].name == "data.json"


class TestAtomicWriteCsvR351:
    """R351: atomic_write_csv 原子写入测试"""

    def test_empty_rows_writes_empty_file(self):
        """R351: 空列表写空文件（不保留旧文件）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "data.csv"
            output_path.write_text("old,data\n1,2\n", encoding="utf-8")

            atomic_write_csv(output_path, [])

            assert output_path.exists()
            assert output_path.read_text(encoding="utf-8") == ""

    def test_with_rows(self):
        """R351: 有行时正常写入"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "data.csv"
            rows = [
                ["label", "precision", "recall"],
                ["integer", 0.95, 0.90],
            ]

            atomic_write_csv(output_path, rows)

            content = output_path.read_text(encoding="utf-8")
            lines = content.strip().splitlines()
            assert len(lines) == 2

    def test_no_tmp_residual(self):
        """R351: 原子替换后无临时文件残留"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "data.csv"

            atomic_write_csv(output_path, [["a", "b"], [1, 2]])

            files = list(Path(tmpdir).iterdir())
            assert len(files) == 1
            assert files[0].name == "data.csv"


class TestAtomicWriteTextR351:
    """R351: atomic_write_text 原子写入测试"""

    def test_writes_text(self):
        """R351: 写入文本内容"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "log.txt"

            atomic_write_text(output_path, "line 1\nline 2\n")

            assert output_path.read_text(encoding="utf-8") == "line 1\nline 2\n"

    def test_empty_string_writes_empty_file(self):
        """R351: 空字符串写空文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "log.txt"
            output_path.write_text("old log", encoding="utf-8")

            atomic_write_text(output_path, "")

            assert output_path.exists()
            assert output_path.read_text(encoding="utf-8") == ""

    def test_replaces_old_content(self):
        """R351: 原子替换旧内容"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "log.txt"
            output_path.write_text("old content", encoding="utf-8")

            atomic_write_text(output_path, "new content")

            assert output_path.read_text(encoding="utf-8") == "new content"

    def test_no_tmp_residual(self):
        """R351: 原子替换后无临时文件残留"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "log.txt"

            atomic_write_text(output_path, "content")

            files = list(Path(tmpdir).iterdir())
            assert len(files) == 1
            assert files[0].name == "log.txt"
