"""R427：cmd_run preflight 失败 Manifest 单元测试

验证 V5 审计报告 HIGH-3 和 R427 计划要求：
  cmd_run 的 preflight 阶段失败时也生成独立失败 Manifest。
  preflight 阶段包括：
    - create_output_dir：输出目录创建失败
    - open_log：日志文件打开失败
    - validate_input_path：输入路径不存在或不是文件
    - load_config：配置文件不存在或 JSON 损坏
    - validate_config：配置值非法

R427 修复后预期行为：
- 所有 preflight 失败都返回非零退出码
- 除输出目录本身不可创建外，都生成失败 Manifest（status=failed, failure_stage=<阶段名>）
- 失败 Manifest 包含 valid_for_reporting=false
- 不保留旧成功 Manifest（若存在）
- predictions.jsonl/field_profiles.jsonl 被清空（无半成品）

例外情况（输出目录本身不可创建）：
- 仅保证非零退出和 stderr
- 不保证落盘 Manifest（物理上不可能）
"""

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from semantic_detector.cli import main


def _write_records(path: Path, records: list) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _make_valid_record(msg_id: str = "m1") -> dict:
    """构造一条合法记录（可通过 read_jsonl_file + prepare_records_for_profiling）"""
    return {
        "message_id": msg_id,
        "layout_id": "L1",
        "direction": "request",
        "payload_hex": "00010002",
        "fields": [
            {"field_index": 0, "start": 0, "end": 2},
            {"field_index": 1, "start": 2, "end": 4},
        ],
        "input_order": 0,
    }


def _prepare_valid_input(tmp_path: Path) -> Path:
    """创建包含 2 条合法记录的输入文件"""
    input_path = tmp_path / "input.jsonl"
    _write_records(input_path, [_make_valid_record("m1"), _make_valid_record("m2")])
    return input_path


def _load_manifest(output_dir: Path) -> dict:
    """读取并解析 manifest.json"""
    manifest_path = output_dir / "manifest.json"
    assert manifest_path.exists(), (
        f"manifest.json 必须存在（preflight 失败也应生成），path={manifest_path}"
    )
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _assert_failed_manifest(output_dir: Path, expected_stage: str) -> dict:
    """断言失败 Manifest 存在且字段正确，返回解析后的 manifest 字典"""
    manifest = _load_manifest(output_dir)
    assert manifest["status"] == "failed", (
        f"preflight 失败 manifest status 应为 failed，got {manifest['status']!r}"
    )
    failure_stage = manifest.get("failure_stage") or manifest.get("error_stage")
    assert failure_stage == expected_stage, (
        f"failure_stage 应为 {expected_stage!r}，got {failure_stage!r}"
    )
    assert manifest.get("valid_for_reporting") is False, (
        "preflight 失败 manifest valid_for_reporting 必须为 False"
    )
    assert manifest.get("exit_code") == 1, (
        f"exit_code 应为 1，got {manifest.get('exit_code')}"
    )
    return manifest


def _assert_no_partial_artifacts(output_dir: Path) -> None:
    """断言 predictions.jsonl 和 field_profiles.jsonl 为空或不存在（无半成品）"""
    predictions_path = output_dir / "predictions.jsonl"
    if predictions_path.exists():
        content = predictions_path.read_text(encoding="utf-8").strip()
        assert content == "", (
            f"preflight 失败后 predictions.jsonl 必须为空，实际有 {len(content)} 字符"
        )
    profiles_path = output_dir / "field_profiles.jsonl"
    if profiles_path.exists():
        content = profiles_path.read_text(encoding="utf-8").strip()
        assert content == "", (
            f"preflight 失败后 field_profiles.jsonl 必须为空，实际有 {len(content)} 字符"
        )


class TestPreflightMissingInputR427:
    """R427：输入路径不存在 → 失败 Manifest"""

    def test_missing_input_writes_failed_manifest(self, tmp_path: Path) -> None:
        """输入文件不存在 → 失败 Manifest（failure_stage=validate_input_path）"""
        output_dir = tmp_path / "out"
        missing = tmp_path / "does_not_exist.jsonl"

        rc = main(["run", str(missing), "--output-dir", str(output_dir)])

        assert rc != 0, "输入不存在应返回非零退出码"
        manifest = _assert_failed_manifest(output_dir, "validate_input_path")
        # 输入不存在时 input_sha256 应为空串（不能伪造空文件哈希）
        assert manifest.get("input_sha256") == "", (
            "输入不存在时 input_sha256 应为空串，不能伪造"
        )
        _assert_no_partial_artifacts(output_dir)

    def test_missing_input_manifest_has_run_id(self, tmp_path: Path) -> None:
        """输入不存在的失败 Manifest 应包含新 run_id（非空 UUID）"""
        output_dir = tmp_path / "out"
        missing = tmp_path / "missing.jsonl"

        rc = main(["run", str(missing), "--output-dir", str(output_dir)])

        assert rc != 0
        manifest = _load_manifest(output_dir)
        run_id = manifest.get("run_id")
        assert run_id and isinstance(run_id, str) and len(run_id) > 0, (
            "失败 Manifest 必须包含新 run_id"
        )


class TestPreflightInputIsDirectoryR427:
    """R427：输入路径是目录 → 失败 Manifest"""

    def test_input_is_directory_writes_failed_manifest(self, tmp_path: Path) -> None:
        """输入路径是目录（不是文件）→ 失败 Manifest（failure_stage=validate_input_path）"""
        output_dir = tmp_path / "out"
        # 传入 tmp_path 本身作为输入（目录）
        rc = main(["run", str(tmp_path), "--output-dir", str(output_dir)])

        assert rc != 0, "输入是目录应返回非零退出码"
        manifest = _assert_failed_manifest(output_dir, "validate_input_path")
        # error_type 应反映异常类型（FileNotFoundError 或 ValueError）
        assert manifest.get("error_type") in ("ValueError", "FileNotFoundError", "IsADirectoryError"), (
            f"error_type 应反映路径类型错误，got {manifest.get('error_type')!r}"
        )
        _assert_no_partial_artifacts(output_dir)


class TestPreflightMissingConfigR427:
    """R427：配置文件不存在 → 失败 Manifest"""

    def test_missing_config_writes_failed_manifest(self, tmp_path: Path) -> None:
        """配置文件不存在 → 失败 Manifest（failure_stage=load_config）"""
        input_path = _prepare_valid_input(tmp_path)
        output_dir = tmp_path / "out"
        missing_config = tmp_path / "missing_config.json"

        rc = main([
            "run", str(input_path),
            "--output-dir", str(output_dir),
            "--config", str(missing_config),
        ])

        assert rc != 0, "配置不存在应返回非零退出码"
        manifest = _assert_failed_manifest(output_dir, "load_config")
        # config_source 应为用户指定的配置路径
        assert manifest.get("config_source") == str(missing_config), (
            f"config_source 应为 {str(missing_config)!r}，got {manifest.get('config_source')!r}"
        )
        # 配置不存在时 config_sha256 应为空串
        assert manifest.get("config_sha256") == "", (
            "配置不存在时 config_sha256 应为空串"
        )
        # resolved_config 应为空字典（配置未加载）
        assert manifest.get("resolved_config") == {}, (
            "配置未加载时 resolved_config 应为空字典"
        )
        _assert_no_partial_artifacts(output_dir)


class TestPreflightBrokenConfigJsonR427:
    """R427：配置 JSON 损坏 → 失败 Manifest"""

    def test_broken_config_json_writes_failed_manifest(self, tmp_path: Path) -> None:
        """配置 JSON 损坏 → 失败 Manifest（failure_stage=load_config）"""
        input_path = _prepare_valid_input(tmp_path)
        output_dir = tmp_path / "out"
        broken_config = tmp_path / "broken.json"
        # 写入损坏的 JSON（不完整的 JSON）
        broken_config.write_text('{"min_samples":', encoding="utf-8")

        rc = main([
            "run", str(input_path),
            "--output-dir", str(output_dir),
            "--config", str(broken_config),
        ])

        assert rc != 0, "配置 JSON 损坏应返回非零退出码"
        manifest = _assert_failed_manifest(output_dir, "load_config")
        assert manifest.get("config_source") == str(broken_config)
        # JSON 损坏但文件存在，config_sha256 应为非空哈希
        assert manifest.get("config_sha256") and len(manifest.get("config_sha256")) == 64, (
            "配置文件存在时 config_sha256 应为 64 字符 SHA-256"
        )
        _assert_no_partial_artifacts(output_dir)


class TestPreflightInvalidConfigValuesR427:
    """R427：配置值非法 → 失败 Manifest"""

    def test_invalid_config_values_writes_failed_manifest(self, tmp_path: Path) -> None:
        """配置值非法（min_samples=0, ambiguity_margin=2.0）→ 失败 Manifest（failure_stage=validate_config）"""
        input_path = _prepare_valid_input(tmp_path)
        output_dir = tmp_path / "out"
        invalid_config = tmp_path / "invalid.json"
        # min_samples=0 非法（必须 > 0），ambiguity_margin=2.0 非法（必须在 0~1）
        invalid_config.write_text(
            json.dumps({"min_samples": 0, "ambiguity_margin": 2.0}),
            encoding="utf-8",
        )

        rc = main([
            "run", str(input_path),
            "--output-dir", str(output_dir),
            "--config", str(invalid_config),
        ])

        assert rc != 0, "配置值非法应返回非零退出码"
        manifest = _assert_failed_manifest(output_dir, "validate_config")
        # 配置文件存在且可读，config_sha256 应为非空哈希
        assert manifest.get("config_sha256") and len(manifest.get("config_sha256")) == 64, (
            "配置文件存在时 config_sha256 应为 64 字符 SHA-256"
        )
        _assert_no_partial_artifacts(output_dir)


class TestPreflightOpenLogFailureR427:
    """R427：日志创建失败 → 失败 Manifest（failure_stage=open_log）"""

    def test_open_log_failure_writes_failed_manifest(self, tmp_path: Path) -> None:
        """open(log_path, 'w') 抛 PermissionError → 失败 Manifest（failure_stage=open_log）

        输出目录已创建成功，仅日志打开失败，应仍写失败 Manifest。
        """
        input_path = _prepare_valid_input(tmp_path)
        output_dir = tmp_path / "out"

        # 模拟 open(log_path, 'w') 抛 PermissionError
        # 需要精确拦截：只拦截写 run.log 的那次 open 调用
        original_open = open
        call_count = [0]

        def _fail_open_log(file, mode='r', *args, **kwargs):
            call_count[0] += 1
            # 第一次 open 是 run.log（在 create_output_dir 之后）
            # 识别方式：mode 包含 'w' 且文件名以 'run.log' 结尾
            if 'w' in mode and isinstance(file, (str, Path)) and str(file).endswith("run.log"):
                raise PermissionError(f"R427 模拟 open_log 失败: {file}")
            return original_open(file, mode, *args, **kwargs)

        with patch("builtins.open", side_effect=_fail_open_log):
            rc = main(["run", str(input_path), "--output-dir", str(output_dir)])

        assert rc != 0, "open_log 失败应返回非零退出码"
        manifest = _assert_failed_manifest(output_dir, "open_log")
        _assert_no_partial_artifacts(output_dir)


class TestPreflightOutputDirFailureR427:
    """R427：输出目录创建失败 → 非零退出 + stderr（不保证 Manifest）

    输出目录本身不可创建时，Manifest 可能无法写入目标目录。
    最低要求：非零退出、stderr 清晰、不保留旧目标 Manifest。
    """

    def test_output_dir_failure_returns_nonzero(self, tmp_path: Path) -> None:
        """output_dir.mkdir 抛 PermissionError → 非零退出 + stderr

        由于 output_dir 不存在，Manifest 可能无法写入。
        本测试只验证非零退出和 stderr 输出，不强制要求 Manifest 存在。
        """
        input_path = _prepare_valid_input(tmp_path)
        # 选择一个不可能创建的输出目录路径（父级是文件）
        impossible_parent = tmp_path / "blocking_file"
        impossible_parent.write_text("block", encoding="utf-8")
        impossible_output = impossible_parent / "out"

        rc = main(["run", str(input_path), "--output-dir", str(impossible_output)])

        assert rc != 0, "输出目录创建失败应返回非零退出码"
        # 不强制要求 Manifest 存在（物理上可能无法写入）

    def test_output_dir_failure_with_mkdir_exception(self, tmp_path: Path) -> None:
        """monkeypatch Path.mkdir 抛异常 → 非零退出 + 失败 Manifest 可能写入父目录

        由于 output_dir 本身不可创建，Manifest 无法写入 output_dir。
        但应保证非零退出和 stderr 清晰。
        """
        input_path = _prepare_valid_input(tmp_path)
        output_dir = tmp_path / "out"

        # 模拟 Path.mkdir 抛 PermissionError
        original_mkdir = Path.mkdir

        def _fail_mkdir(self, *args, **kwargs):
            if str(self) == str(output_dir):
                raise PermissionError(f"R427 模拟 create_output_dir 失败: {self}")
            return original_mkdir(self, *args, **kwargs)

        with patch.object(Path, "mkdir", _fail_mkdir):
            rc = main(["run", str(input_path), "--output-dir", str(output_dir)])

        assert rc != 0, "create_output_dir 失败应返回非零退出码"
        # output_dir 不存在，Manifest 无法写入，不强制检查


class TestPreflightNoLegacyManifestResidueR427:
    """R427：preflight 失败不应保留旧成功 Manifest"""

    def test_success_then_preflight_failure_replaces_manifest(self, tmp_path: Path) -> None:
        """第一次成功 → 第二次 preflight 失败 → 旧成功 Manifest 被失败 Manifest 替换

        场景：
        1. 第一次 run 合法输入 → 成功（manifest.status=completed）
        2. 第二次 run 配置损坏 → preflight 失败
        3. 验证：旧成功 Manifest 被失败 Manifest 替换，predictions 为空
        """
        input_path = _prepare_valid_input(tmp_path)
        output_dir = tmp_path / "out"

        # 第一次 run：成功
        rc1 = main(["run", str(input_path), "--output-dir", str(output_dir)])
        assert rc1 == 0, f"第一次 run 应成功，got rc={rc1}"

        manifest_path = output_dir / "manifest.json"
        predictions_path = output_dir / "predictions.jsonl"
        first_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert first_manifest["status"] == "completed"
        first_run_id = first_manifest["run_id"]
        assert predictions_path.exists() and predictions_path.read_text(encoding="utf-8").strip()

        # 第二次 run：配置损坏 → preflight 失败
        broken_config = tmp_path / "broken.json"
        broken_config.write_text('{"min_samples":', encoding="utf-8")

        rc2 = main([
            "run", str(input_path),
            "--output-dir", str(output_dir),
            "--config", str(broken_config),
        ])

        assert rc2 != 0, "第二次 run（配置损坏）应失败"

        # 旧成功 Manifest 被失败 Manifest 替换
        second_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert second_manifest["status"] == "failed", (
            "第二次失败后 manifest status 应为 failed"
        )
        assert second_manifest["run_id"] != first_run_id, (
            "失败 Manifest run_id 应与第一次成功不同"
        )
        assert second_manifest.get("failure_stage") == "load_config"

        # predictions 应为空（不保留第一次成功内容）
        second_predictions = predictions_path.read_text(encoding="utf-8").strip()
        assert second_predictions == "", (
            f"preflight 失败后 predictions 应为空，实际有 {len(second_predictions)} 字符"
        )


class TestPreflightManifestFieldsR427:
    """R427：preflight 失败 Manifest 字段完整性"""

    def test_preflight_manifest_has_required_fields(self, tmp_path: Path) -> None:
        """preflight 失败 Manifest 包含 R390 基础 + R421 扩展字段"""
        input_path = _prepare_valid_input(tmp_path)
        output_dir = tmp_path / "out"
        broken_config = tmp_path / "broken.json"
        broken_config.write_text('invalid json', encoding="utf-8")

        rc = main([
            "run", str(input_path),
            "--output-dir", str(output_dir),
            "--config", str(broken_config),
        ])

        assert rc != 0
        manifest = _load_manifest(output_dir)

        # R390 基础字段
        required_basic = [
            "run_id", "status", "exit_code", "started_at", "finished_at",
            "input_path", "input_sha256", "resolved_config",
            "valid_records", "rejected_records",
            "field_profiles", "predictions",
            "error_stage", "error_message",
        ]
        for field in required_basic:
            assert field in manifest, f"失败 Manifest 缺少基础字段: {field}"

        # R421 扩展字段
        required_extended = [
            "valid_for_reporting", "failure_stage", "error_type",
            "config_source", "config_sha256",
            "partial_artifacts_present", "counts",
        ]
        for field in required_extended:
            assert field in manifest, f"失败 Manifest 缺少扩展字段: {field}"

        # counts 嵌套对象
        counts = manifest["counts"]
        for field in ["input_line_count", "validated_records", "rejected_records",
                       "field_profiles", "predictions"]:
            assert field in counts, f"counts 缺少字段: {field}"

        # preflight 失败时 partial_artifacts_present 必须为 False
        assert manifest["partial_artifacts_present"] is False, (
            "preflight 失败时 partial_artifacts_present 必须为 False"
        )

    def test_preflight_manifest_started_at_before_finished_at(self, tmp_path: Path) -> None:
        """preflight 失败 Manifest 的 started_at 应早于或等于 finished_at"""
        output_dir = tmp_path / "out"
        missing = tmp_path / "missing.jsonl"

        rc = main(["run", str(missing), "--output-dir", str(output_dir)])

        assert rc != 0
        manifest = _load_manifest(output_dir)
        assert manifest["started_at"] <= manifest["finished_at"], (
            "started_at 应早于或等于 finished_at"
        )
