"""R427：Run preflight 失败产物新鲜度集成测试

验证 V5 审计报告 HIGH-3 和 R427 计划要求：
  preflight 失败后，旧成功产物被失败产物替换，不残留旧数据。

核心场景（计划 4.11）：
  1. 第一次合法成功 → 生成 completed Manifest + predictions + profiles
  2. 第二次 preflight 失败（输入/配置类失败）→ 生成 failed Manifest
  3. 验证：
     - 旧成功 Manifest 被失败 Manifest 替换（run_id 不同）
     - 旧 predictions 被清空（无半成品）
     - 旧 profiles 被清空（无半成品）
     - run.log 可读取（句柄已关闭）

覆盖的 preflight 失败类型：
  - missing input（输入不存在）
  - input is directory（输入是目录）
  - missing config（配置不存在）
  - broken config JSON（配置 JSON 损坏）
  - invalid config values（配置值非法）

例外：输出目录本身不可创建不在此测试范围（无法写入产物）。
"""

import json
from pathlib import Path

import pytest

from semantic_detector.cli import main


def _write_records(path: Path, records: list) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _make_valid_record(msg_id: str = "m1") -> dict:
    """构造一条合法记录"""
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


def _run_success_first(tmp_path: Path) -> tuple:
    """第一次合法运行，返回 (output_dir, first_manifest, first_run_id)"""
    input_path = _prepare_valid_input(tmp_path)
    output_dir = tmp_path / "out"

    rc = main(["run", str(input_path), "--output-dir", str(output_dir)])
    assert rc == 0, f"第一次 run 应成功，got rc={rc}"

    manifest_path = output_dir / "manifest.json"
    predictions_path = output_dir / "predictions.jsonl"
    profiles_path = output_dir / "field_profiles.jsonl"

    first_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert first_manifest["status"] == "completed"
    first_run_id = first_manifest["run_id"]

    # 确认第一次有产物
    assert predictions_path.exists()
    assert predictions_path.read_text(encoding="utf-8").strip(), "第一次 predictions 应有内容"
    assert profiles_path.exists()
    assert profiles_path.read_text(encoding="utf-8").strip(), "第一次 profiles 应有内容"

    return output_dir, first_manifest, first_run_id


def _assert_second_run_replaced_first(
    output_dir: Path,
    first_run_id: str,
    expected_failure_stage: str,
) -> dict:
    """断言第二次失败 run 完全替换第一次成功产物"""
    manifest_path = output_dir / "manifest.json"
    predictions_path = output_dir / "predictions.jsonl"
    profiles_path = output_dir / "field_profiles.jsonl"
    log_path = output_dir / "run.log"

    # 旧成功 Manifest 被失败 Manifest 替换
    assert manifest_path.exists(), "失败 run 后 manifest.json 必须存在"
    second_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert second_manifest["status"] == "failed", (
        f"第二次 manifest status 应为 failed，got {second_manifest['status']!r}"
    )
    assert second_manifest["run_id"] != first_run_id, (
        "失败 Manifest run_id 应与第一次成功不同"
    )
    failure_stage = second_manifest.get("failure_stage") or second_manifest.get("error_stage")
    assert failure_stage == expected_failure_stage, (
        f"failure_stage 应为 {expected_failure_stage!r}，got {failure_stage!r}"
    )

    # 旧 predictions 被清空
    second_predictions = predictions_path.read_text(encoding="utf-8").strip()
    assert second_predictions == "", (
        f"preflight 失败后 predictions 应为空，实际有 {len(second_predictions)} 字符"
    )

    # 旧 profiles 被清空
    second_profiles = profiles_path.read_text(encoding="utf-8").strip()
    assert second_profiles == "", (
        f"preflight 失败后 profiles 应为空，实际有 {len(second_profiles)} 字符"
    )

    # run.log 可读取（句柄已关闭）
    assert log_path.exists(), "run.log 必须存在"
    log_content = log_path.read_text(encoding="utf-8")
    assert len(log_content) >= 0  # 只验证可读取

    return second_manifest


class TestRunPreflightArtifactFreshnessR427:
    """R427：preflight 失败产物新鲜度集成测试

    场景：第一次合法成功 → 第二次 preflight 失败 → 旧成功产物被替换
    """

    def test_success_then_missing_input_replaces_artifacts(self, tmp_path: Path) -> None:
        """第一次成功 → 第二次输入不存在 → 旧产物被失败 Manifest 替换"""
        output_dir, _, first_run_id = _run_success_first(tmp_path)

        # 第二次 run：输入不存在
        missing = tmp_path / "does_not_exist.jsonl"
        rc2 = main(["run", str(missing), "--output-dir", str(output_dir)])
        assert rc2 != 0

        _assert_second_run_replaced_first(output_dir, first_run_id, "validate_input_path")

    def test_success_then_input_is_directory_replaces_artifacts(self, tmp_path: Path) -> None:
        """第一次成功 → 第二次输入是目录 → 旧产物被失败 Manifest 替换"""
        output_dir, _, first_run_id = _run_success_first(tmp_path)

        # 第二次 run：输入是目录（tmp_path 本身）
        rc2 = main(["run", str(tmp_path), "--output-dir", str(output_dir)])
        assert rc2 != 0

        _assert_second_run_replaced_first(output_dir, first_run_id, "validate_input_path")

    def test_success_then_missing_config_replaces_artifacts(self, tmp_path: Path) -> None:
        """第一次成功 → 第二次配置不存在 → 旧产物被失败 Manifest 替换"""
        input_path = _prepare_valid_input(tmp_path)
        output_dir, _, first_run_id = _run_success_first(tmp_path)

        # 第二次 run：配置不存在
        missing_config = tmp_path / "missing_config.json"
        rc2 = main([
            "run", str(input_path),
            "--output-dir", str(output_dir),
            "--config", str(missing_config),
        ])
        assert rc2 != 0

        manifest = _assert_second_run_replaced_first(output_dir, first_run_id, "load_config")
        # config_source 应为用户指定的配置路径
        assert manifest.get("config_source") == str(missing_config)
        # 配置不存在时 config_sha256 应为空串
        assert manifest.get("config_sha256") == ""

    def test_success_then_broken_config_json_replaces_artifacts(self, tmp_path: Path) -> None:
        """第一次成功 → 第二次配置 JSON 损坏 → 旧产物被失败 Manifest 替换"""
        input_path = _prepare_valid_input(tmp_path)
        output_dir, _, first_run_id = _run_success_first(tmp_path)

        # 第二次 run：配置 JSON 损坏
        broken_config = tmp_path / "broken.json"
        broken_config.write_text('{"min_samples":', encoding="utf-8")
        rc2 = main([
            "run", str(input_path),
            "--output-dir", str(output_dir),
            "--config", str(broken_config),
        ])
        assert rc2 != 0

        manifest = _assert_second_run_replaced_first(output_dir, first_run_id, "load_config")
        # JSON 损坏但文件存在，config_sha256 应为非空
        assert manifest.get("config_sha256") and len(manifest.get("config_sha256")) == 64

    def test_success_then_invalid_config_values_replaces_artifacts(self, tmp_path: Path) -> None:
        """第一次成功 → 第二次配置值非法 → 旧产物被失败 Manifest 替换"""
        input_path = _prepare_valid_input(tmp_path)
        output_dir, _, first_run_id = _run_success_first(tmp_path)

        # 第二次 run：配置值非法（min_samples=0）
        invalid_config = tmp_path / "invalid.json"
        invalid_config.write_text(
            json.dumps({"min_samples": 0, "ambiguity_margin": 2.0}),
            encoding="utf-8",
        )
        rc2 = main([
            "run", str(input_path),
            "--output-dir", str(output_dir),
            "--config", str(invalid_config),
        ])
        assert rc2 != 0

        manifest = _assert_second_run_replaced_first(output_dir, first_run_id, "validate_config")
        # 配置文件存在且可读，config_sha256 应为非空
        assert manifest.get("config_sha256") and len(manifest.get("config_sha256")) == 64

    def test_success_then_open_log_failure_replaces_artifacts(self, tmp_path: Path) -> None:
        """第一次成功 → 第二次 open_log 失败 → 旧产物被失败 Manifest 替换

        注意：open_log 失败时 run.log 本身不存在（open 抛异常），不强制检查 run.log。
        """
        input_path = _prepare_valid_input(tmp_path)
        output_dir, _, first_run_id = _run_success_first(tmp_path)

        # 第二次 run：模拟 open_log 失败
        original_open = open

        def _fail_open_log(file, mode='r', *args, **kwargs):
            if 'w' in mode and isinstance(file, (str, Path)) and str(file).endswith("run.log"):
                raise PermissionError(f"R427 集成测试：open_log 失败: {file}")
            return original_open(file, mode, *args, **kwargs)

        from unittest.mock import patch
        with patch("builtins.open", side_effect=_fail_open_log):
            rc2 = main(["run", str(input_path), "--output-dir", str(output_dir)])
        assert rc2 != 0

        # open_log 失败时 run.log 不存在，跳过 run.log 检查
        manifest_path = output_dir / "manifest.json"
        predictions_path = output_dir / "predictions.jsonl"
        profiles_path = output_dir / "field_profiles.jsonl"

        second_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert second_manifest["status"] == "failed"
        assert second_manifest["run_id"] != first_run_id
        assert second_manifest.get("failure_stage") == "open_log"

        # 旧 predictions 被清空
        assert predictions_path.read_text(encoding="utf-8").strip() == ""
        # 旧 profiles 被清空
        assert profiles_path.read_text(encoding="utf-8").strip() == ""


class TestRunPreflightRunLogLifecycleR427:
    """R427：preflight 失败后 run.log 生命周期验证

    验证：
    - preflight 失败后 run.log 可重命名和删除（句柄已释放）
    - 同目录再次运行不受文件句柄锁影响
    """

    def test_preflight_failure_releases_log_handle(self, tmp_path: Path) -> None:
        """preflight 失败后 run.log 可重命名和删除（Windows 句柄锁验证）"""
        input_path = _prepare_valid_input(tmp_path)
        output_dir = tmp_path / "out"

        # 第一次：配置损坏 → preflight 失败
        broken_config = tmp_path / "broken.json"
        broken_config.write_text('invalid json', encoding="utf-8")
        rc = main([
            "run", str(input_path),
            "--output-dir", str(output_dir),
            "--config", str(broken_config),
        ])
        assert rc != 0

        log_path = output_dir / "run.log"
        # open_log 失败时 run.log 可能不存在，跳过重命名测试
        if log_path.exists():
            renamed = output_dir / "run_renamed.log"
            log_path.rename(renamed)
            assert renamed.exists()
            renamed.unlink()
            assert not renamed.exists()

        # 第二次：合法运行应成功（不受前一次句柄锁影响）
        rc2 = main(["run", str(input_path), "--output-dir", str(output_dir)])
        assert rc2 == 0, "同目录再次运行应成功"
        assert log_path.exists(), "再次运行应重新生成 run.log"


class TestRunPreflightManifestDeterminismR427:
    """R427：preflight 失败 Manifest 的 run_id 唯一性"""

    def test_repeated_preflight_failures_have_unique_run_ids(self, tmp_path: Path) -> None:
        """连续两次 preflight 失败，run_id 必须不同"""
        input_path = _prepare_valid_input(tmp_path)
        output_dir = tmp_path / "out"
        broken_config = tmp_path / "broken.json"
        broken_config.write_text('invalid json', encoding="utf-8")

        # 第一次失败
        rc1 = main([
            "run", str(input_path),
            "--output-dir", str(output_dir),
            "--config", str(broken_config),
        ])
        assert rc1 != 0
        first_manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
        first_run_id = first_manifest["run_id"]

        # 第二次失败（同配置）
        rc2 = main([
            "run", str(input_path),
            "--output-dir", str(output_dir),
            "--config", str(broken_config),
        ])
        assert rc2 != 0
        second_manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
        second_run_id = second_manifest["run_id"]

        assert first_run_id != second_run_id, (
            "连续两次 preflight 失败的 run_id 必须不同"
        )
        assert first_manifest["failure_stage"] == second_manifest["failure_stage"] == "load_config"
