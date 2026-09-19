"""R387：失败重复 Run 的旧产物残留测试

复现 HIGH-4：
  第一次成功 run
  第二次失败 run（profile 阶段异常）
  → 旧 predictions/manifest 仍存在

当前 cmd_run 在 build_field_profiles 抛异常时（cli.py 第 629-632 行）
直接 return 1，不清理旧产物，不写失败 Manifest。
artifact_manager.clean_command_artifacts 从未被 CLI 主链调用。

R387 期望（R389-R390 修复后的正确行为）：
- 第二次失败后不得保留第一次成功 predictions
- 第二次失败后不得保留第一次成功 manifest
- 必须有属于第二次运行的失败状态产物

本轮不修改生产代码。测试当前会失败，R389-R390 修复后通过。
"""

import hashlib
import json
import tempfile
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


def _sha256(path: Path) -> str:
    """计算文件 SHA-256"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


class TestRunArtifactFreshnessR387:
    """R387：失败重复 Run 的旧产物残留测试

    复现 HIGH-4：artifact_manager 未接入 CLI 主链，
    第二次 run 失败时（profile 阶段异常）保留第一次成功产物。
    """

    def test_r387_failed_run_does_not_retain_old_predictions(self, tmp_path: Path) -> None:
        """R387: 第二次 run 失败后不得保留第一次成功 predictions

        场景：
        1. 第一次 run 合法输入 → 成功，predictions.jsonl 有内容
        2. 第二次 run 同一输入，但 build_field_profiles 被模拟抛异常 → 失败
        3. 断言：第二次失败后 predictions.jsonl 不应与第一次相同

        当前实现：build_field_profiles 异常时直接 return 1，
        不清理 predictions.jsonl，旧文件保留 → 测试失败（复现 HIGH-4）
        R389 修复后：cmd_run 开始时调用 clean_command_artifacts 清理旧产物 → 测试通过
        """
        input_path = tmp_path / "input.jsonl"
        _write_records(input_path, [_make_valid_record("m1"), _make_valid_record("m2")])

        output_dir = tmp_path / "output"

        # 第一次 run：合法输入 → 成功
        rc1 = main(["run", str(input_path), "--output-dir", str(output_dir)])
        assert rc1 == 0, f"第一次 run 应成功，got rc={rc1}"

        predictions_path = output_dir / "predictions.jsonl"
        manifest_path = output_dir / "manifest.json"
        assert predictions_path.exists(), "第一次 run 应生成 predictions.jsonl"
        assert manifest_path.exists(), "第一次 run 应生成 manifest.json"

        first_predictions_sha = _sha256(predictions_path)
        first_manifest_sha = _sha256(manifest_path)

        # 验证第一次 predictions 有内容
        first_content = predictions_path.read_text(encoding="utf-8").strip()
        assert first_content, "第一次 predictions 应有内容"

        # 第二次 run：模拟 build_field_profiles 抛异常 → 失败
        with patch(
            "semantic_detector.profiling.profile_builder.build_field_profiles",
            side_effect=RuntimeError("模拟 profile 阶段失败（R387 复现 HIGH-4）"),
        ):
            rc2 = main(["run", str(input_path), "--output-dir", str(output_dir)])

        # 第二次应失败
        assert rc2 != 0, f"第二次 run 应失败（profile 异常），got rc={rc2}"

        # 断言 1: 旧 predictions 不得保留（SHA 必须不同）
        second_predictions_sha = _sha256(predictions_path)
        assert second_predictions_sha != first_predictions_sha, (
            "HIGH-4 复现：第二次失败后仍保留第一次成功 predictions（SHA 相同）"
        )

    def test_r387_failed_run_does_not_retain_old_manifest(self, tmp_path: Path) -> None:
        """R387: 第二次 run 失败后不得保留第一次成功 manifest

        当前实现：build_field_profiles 异常时直接 return 1，
        不写新 manifest，旧成功 manifest 保留 → 测试失败（复现 HIGH-4）
        R390 修复后：失败时写失败 Manifest（status=failed）→ 测试通过
        """
        input_path = tmp_path / "input.jsonl"
        _write_records(input_path, [_make_valid_record("m1"), _make_valid_record("m2")])

        output_dir = tmp_path / "output"

        # 第一次 run：成功
        rc1 = main(["run", str(input_path), "--output-dir", str(output_dir)])
        assert rc1 == 0

        manifest_path = output_dir / "manifest.json"
        first_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert first_manifest.get("status") == "completed", (
            f"第一次 manifest status 应为 completed，got {first_manifest.get('status')}"
        )
        first_manifest_sha = _sha256(manifest_path)

        # 第二次 run：模拟 profile 阶段失败
        with patch(
            "semantic_detector.profiling.profile_builder.build_field_profiles",
            side_effect=RuntimeError("模拟 profile 阶段失败（R387 复现 HIGH-4）"),
        ):
            rc2 = main(["run", str(input_path), "--output-dir", str(output_dir)])

        assert rc2 != 0

        # 断言 1: 旧 manifest 不得保留（SHA 必须不同）
        second_manifest_sha = _sha256(manifest_path)
        assert second_manifest_sha != first_manifest_sha, (
            "HIGH-4 复现：第二次失败后仍保留第一次成功 manifest（SHA 相同）"
        )

        # 断言 2: 新 manifest 必须属于第二次运行（status=failed/invalid_input）
        second_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        second_status = second_manifest.get("status")
        assert second_status in ("failed", "invalid_input", "no_valid_records"), (
            f"第二次 manifest status 应为失败状态，got {second_status}"
        )

    def test_r387_failed_run_writes_failed_status_artifact(self, tmp_path: Path) -> None:
        """R387: 第二次 run 失败后必须有失败状态产物

        R390 修复后：失败 run 写入 manifest.json，status=failed，
        含 error_stage/error_message 等信息。

        当前实现：build_field_profiles 异常时不写任何 manifest → 测试失败
        """
        input_path = tmp_path / "input.jsonl"
        _write_records(input_path, [_make_valid_record("m1")])

        output_dir = tmp_path / "output"

        # 第一次 run：成功
        main(["run", str(input_path), "--output-dir", str(output_dir)])

        # 第二次 run：模拟 profile 阶段失败
        with patch(
            "semantic_detector.profiling.profile_builder.build_field_profiles",
            side_effect=RuntimeError("模拟 profile 阶段失败（R387 复现 HIGH-4）"),
        ):
            rc2 = main(["run", str(input_path), "--output-dir", str(output_dir)])

        assert rc2 != 0

        # 失败状态产物：manifest.json 必须存在且 status 为失败
        manifest_path = output_dir / "manifest.json"
        assert manifest_path.exists(), "失败 run 后 manifest.json 必须存在（失败状态产物）"

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        status = manifest.get("status")
        assert status in ("failed", "invalid_input", "no_valid_records"), (
            f"失败 run manifest status 应为失败状态，got {status}"
        )

    def test_r387_clean_command_artifacts_called_by_run(self, tmp_path: Path) -> None:
        """R387: cmd_run 必须调用 clean_command_artifacts（HIGH-4 根因验证）

        HIGH-4 根因：artifact_manager.clean_command_artifacts 从未被 CLI 主链调用。
        R389 修复后：cmd_run 开始时调用 clean_command_artifacts("run")。

        当前实现：cmd_run 不调用 clean_command_artifacts → 测试失败
        """
        from semantic_detector.io import artifact_manager

        input_path = tmp_path / "input.jsonl"
        _write_records(input_path, [_make_valid_record("m1")])
        output_dir = tmp_path / "output"

        # 用 spy 监控 clean_command_artifacts 是否被调用
        with patch.object(
            artifact_manager,
            "clean_command_artifacts",
            wraps=artifact_manager.clean_command_artifacts,
        ) as spy:
            rc = main(["run", str(input_path), "--output-dir", str(output_dir)])
            assert rc == 0

        # 断言：clean_command_artifacts 必须被调用（至少一次，command="run"）
        assert spy.called, (
            "HIGH-4 复现：cmd_run 未调用 clean_command_artifacts（artifact_manager 未接入主链）"
        )

        # 验证调用参数：command 应为 "run"
        call_args = spy.call_args_list
        run_calls = [
            c for c in call_args
            if len(c.args) >= 2 and c.args[1] == "run"
        ]
        assert len(run_calls) > 0, (
            f"clean_command_artifacts 应以 command='run' 调用，实际调用: {call_args}"
        )

    def test_r387_no_valid_records_overwrites_old_predictions(self, tmp_path: Path) -> None:
        """R387: 全部拒绝的第二次 run 必须覆盖第一次成功 predictions

        这是一个对比测试：no_valid_records 分支已正确覆盖旧文件，
        但 profile 异常分支未覆盖。两者应有一致的行为。

        当前实现：no_valid_records 分支已写空 predictions → 测试通过
        （此测试作为正面对照，验证期望行为）

        触发 no_valid_records 分支：所有行都是 invalid JSON，
        read_jsonl_file 返回 valid_records=[] → group_valid_records=[] → no_valid_records
        """
        valid_input = tmp_path / "valid.jsonl"
        _write_records(valid_input, [_make_valid_record("m1"), _make_valid_record("m2")])

        # 全部拒绝的输入（所有行都是 invalid JSON）
        invalid_input = tmp_path / "invalid.jsonl"
        with open(invalid_input, "w", encoding="utf-8") as f:
            f.write('{"message_id": "bad1", invalid json}\n')
            f.write('{"message_id": "bad2", invalid json}\n')

        output_dir = tmp_path / "output"

        # 第一次 run：成功
        rc1 = main(["run", str(valid_input), "--output-dir", str(output_dir)])
        assert rc1 == 0

        predictions_path = output_dir / "predictions.jsonl"
        first_sha = _sha256(predictions_path)
        assert predictions_path.read_text(encoding="utf-8").strip()

        # 第二次 run：全部拒绝 → no_valid_records
        rc2 = main(["run", str(invalid_input), "--output-dir", str(output_dir)])
        assert rc2 != 0

        # no_valid_records 分支应覆盖旧 predictions（写空文件）
        second_sha = _sha256(predictions_path)
        assert second_sha != first_sha, (
            "no_valid_records 分支应覆盖旧 predictions（SHA 必须不同）"
        )
        # 第二次 predictions 应为空
        assert predictions_path.read_text(encoding="utf-8").strip() == "", (
            "no_valid_records 分支应写空 predictions"
        )
