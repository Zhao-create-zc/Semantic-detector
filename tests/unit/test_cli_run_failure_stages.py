"""R419：cmd_run 后半段异常失败回归测试

复现 V4 审计报告 HIGH-2：
  cmd_run 后半段 5 个阶段无统一异常保护：
  - export_field_profiles（cli.py 第 780 行）
  - pipeline.detect_fields（cli.py 第 787 行）
  - export_predictions_to_jsonl（cli.py 第 790 行）
  - pipeline.generate_manifest（cli.py 第 838-845 行）
  - write_manifest / json.dump（cli.py 第 847-848 行）

当前实现：这些阶段抛异常时传播到 main()，main 捕获后返回 1，
但不生成失败 Manifest、不清理半成品、不关闭 run.log。

R420-R421 修复后（预期行为）：
- 统一 try/except/finally 捕获所有阶段异常
- 写失败 Manifest（status=failed, error_stage=<阶段名>）
- 清理或替换半成品（predictions/profiles/manifest）
- finally 中关闭 run.log

本轮不修改生产代码。测试当前会失败（复现 HIGH-2），R420-R421 修复后通过。
"""

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


def _prepare_input(tmp_path: Path) -> Path:
    """创建包含 2 条合法记录的输入文件"""
    input_path = tmp_path / "input.jsonl"
    _write_records(input_path, [_make_valid_record("m1"), _make_valid_record("m2")])
    return input_path


def _assert_failed_manifest(output_dir: Path, expected_stage: str) -> dict:
    """断言失败 Manifest 存在且 status=failed，返回解析后的 manifest 字典"""
    manifest_path = output_dir / "manifest.json"
    assert manifest_path.exists(), (
        f"失败 run 后 manifest.json 必须存在（失败状态产物），stage={expected_stage}"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    status = manifest.get("status")
    assert status == "failed", (
        f"失败 run manifest status 应为 failed，got {status!r}，stage={expected_stage}"
    )
    # 失败信息中包含真实阶段名
    error_stage = manifest.get("error_stage") or manifest.get("failure_stage")
    assert error_stage == expected_stage, (
        f"失败 manifest error_stage 应为 {expected_stage!r}，got {error_stage!r}"
    )
    return manifest


def _assert_no_partial_predictions(output_dir: Path) -> None:
    """断言 predictions.jsonl 不含半写/旧内容（空文件或不存在）"""
    predictions_path = output_dir / "predictions.jsonl"
    if predictions_path.exists():
        content = predictions_path.read_text(encoding="utf-8").strip()
        assert content == "", (
            f"失败 run 后 predictions.jsonl 必须为空（无半写内容），实际有 {len(content)} 字符"
        )


def _assert_run_log_readable(output_dir: Path) -> None:
    """断言 run.log 可重新打开和读取（验证日志句柄已关闭）"""
    log_path = output_dir / "run.log"
    assert log_path.exists(), "run.log 必须存在"
    # 能正常读取即说明句柄已关闭（Windows 下未关闭会抛 PermissionError）
    content = log_path.read_text(encoding="utf-8")
    assert len(content) >= 0  # 只验证可读取


class TestCliRunFailureStagesR419:
    """R419：cmd_run 后半段 5 个阶段异常失败回归测试

    每个阶段异常都必须：
    1. 返回非零退出码
    2. 生成失败 Manifest（status=failed, error_stage=<阶段名>）
    3. 不留下半写 predictions.jsonl
    4. run.log 可重新读取（日志句柄已关闭）

    当前实现（R418 基线）这些阶段无统一异常保护，测试会失败。
    R420-R421 修复后通过。
    """

    def test_export_profiles_failure(self, tmp_path: Path) -> None:
        """export_field_profiles 抛异常 → 失败 Manifest + 无半成品

        复现：export_field_profiles（cli.py 第 780 行）无 try/except 保护，
        异常传播到 main()，不生成失败 Manifest。
        """
        input_path = _prepare_input(tmp_path)
        output_dir = tmp_path / "output"

        with patch(
            "semantic_detector.io.exporters.export_field_profiles",
            side_effect=RuntimeError("R419 模拟 export_profiles 失败"),
        ):
            rc = main(["run", str(input_path), "--output-dir", str(output_dir)])

        assert rc != 0, "export_profiles 异常应返回非零退出码"
        _assert_failed_manifest(output_dir, "export_profiles")
        _assert_no_partial_predictions(output_dir)
        _assert_run_log_readable(output_dir)

    def test_detect_fields_failure(self, tmp_path: Path) -> None:
        """pipeline.detect_fields 抛异常 → 失败 Manifest + 无半成品

        复现：detect_fields（cli.py 第 787 行）无 try/except 保护。
        """
        input_path = _prepare_input(tmp_path)
        output_dir = tmp_path / "output"

        with patch(
            "semantic_detector.pipeline.pipeline.DetectionPipeline.detect_fields",
            side_effect=RuntimeError("R419 模拟 detect_fields 失败"),
        ):
            rc = main(["run", str(input_path), "--output-dir", str(output_dir)])

        assert rc != 0, "detect_fields 异常应返回非零退出码"
        _assert_failed_manifest(output_dir, "detect_fields")
        _assert_no_partial_predictions(output_dir)
        _assert_run_log_readable(output_dir)

    def test_export_predictions_failure(self, tmp_path: Path) -> None:
        """export_predictions_to_jsonl 抛异常 → 失败 Manifest + 无半写预测

        复现：export_predictions_to_jsonl（cli.py 第 790 行）无 try/except 保护。
        不得留下半写的 predictions.jsonl。
        """
        input_path = _prepare_input(tmp_path)
        output_dir = tmp_path / "output"

        with patch(
            "semantic_detector.io.exporters.export_predictions_to_jsonl",
            side_effect=RuntimeError("R419 模拟 export_predictions 失败"),
        ):
            rc = main(["run", str(input_path), "--output-dir", str(output_dir)])

        assert rc != 0, "export_predictions 异常应返回非零退出码"
        _assert_failed_manifest(output_dir, "export_predictions")
        _assert_no_partial_predictions(output_dir)
        _assert_run_log_readable(output_dir)

    def test_generate_manifest_failure(self, tmp_path: Path) -> None:
        """pipeline.generate_manifest 抛异常 → 失败 Manifest + 保留诊断 predictions

        R420 修复后：except 捕获 → _write_failed_run_artifacts 写失败 Manifest。
        R426-BUG1 修复后：generate_manifest 阶段失败时保留已写入的 predictions 作为诊断数据
        （partial_artifacts_present=true），不再清空。
        """
        input_path = _prepare_input(tmp_path)
        output_dir = tmp_path / "output"

        with patch(
            "semantic_detector.pipeline.pipeline.DetectionPipeline.generate_manifest",
            side_effect=RuntimeError("R419 模拟 generate_manifest 失败"),
        ):
            rc = main(["run", str(input_path), "--output-dir", str(output_dir)])

        assert rc != 0, "generate_manifest 异常应返回非零退出码"
        manifest = _assert_failed_manifest(output_dir, "generate_manifest")
        # R426-BUG1：generate_manifest 阶段失败时 predictions 应保留（诊断数据）
        assert manifest.get("partial_artifacts_present") is True, (
            "generate_manifest 失败时 partial_artifacts_present 应为 True（保留诊断 predictions）"
        )
        predictions_path = output_dir / "predictions.jsonl"
        assert predictions_path.exists(), "predictions.jsonl 应存在（保留诊断数据）"
        content = predictions_path.read_text(encoding="utf-8").strip()
        assert content != "", (
            "generate_manifest 失败后 predictions.jsonl 应保留已写入的诊断内容，不应为空"
        )
        _assert_run_log_readable(output_dir)

    def test_write_manifest_failure(self, tmp_path: Path) -> None:
        """json.dump 写 manifest 抛异常 → 旧 Manifest 已清理 + 失败 Manifest

        复现：write_manifest（cli.py 第 847-848 行）无 try/except 保护。
        使用 fail-once 策略：第一次 json.dump 调用（写正式 manifest）失败，
        后续 json.dump 调用（R420 修复后 _write_failed_run_artifacts 写失败 manifest）正常。

        当前实现：json.dump 失败 → 异常传播到 main() → 不生成失败 Manifest。
        R420 修复后：except 捕获 → _write_failed_run_artifacts 的 json.dump（第 539 行）正常 → 失败 Manifest 生成。
        """
        input_path = _prepare_input(tmp_path)
        output_dir = tmp_path / "output"

        # fail-once：第一次 json.dump 调用失败（写正式 manifest），后续正常
        # side_effect 必须在非首次调用时执行原始 json.dump，否则 manifest 不会被写入
        original_json_dump = json.dump
        call_count = [0]

        def _fail_once(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("R419 模拟 write_manifest 失败")
            return original_json_dump(*args, **kwargs)

        with patch("json.dump", side_effect=_fail_once):
            rc = main(["run", str(input_path), "--output-dir", str(output_dir)])

        assert rc != 0, "write_manifest 异常应返回非零退出码"
        manifest = _assert_failed_manifest(output_dir, "write_manifest")
        # R426-BUG1：write_manifest 阶段失败时 predictions 应保留（诊断数据）
        assert manifest.get("partial_artifacts_present") is True, (
            "write_manifest 失败时 partial_artifacts_present 应为 True（保留诊断 predictions）"
        )
        predictions_path = output_dir / "predictions.jsonl"
        assert predictions_path.exists(), "predictions.jsonl 应存在（保留诊断数据）"
        content = predictions_path.read_text(encoding="utf-8").strip()
        assert content != "", (
            "write_manifest 失败后 predictions.jsonl 应保留已写入的诊断内容，不应为空"
        )
        _assert_run_log_readable(output_dir)


class TestCliRunFailureComboR419:
    """R419：成功后失败的重复运行组合测试

    场景：
    1. 第一次 run 合法输入 → 成功（predictions + manifest 有内容）
    2. 第二次 run 同一输入，detect_fields 被模拟抛异常 → 失败

    第二次失败后必须验证：
    - 旧 predictions 不存在（被清理或覆盖为空）
    - 旧成功 Manifest 不存在（被失败 Manifest 覆盖）
    - 当前失败 Manifest 存在
    - 失败 Manifest.run_id 与第一次成功 Manifest.run_id 不同
    """

    def test_success_then_detect_failure(self, tmp_path: Path) -> None:
        """第一次成功，第二次 detect_fields 失败 → 无旧成功产物 + 失败 Manifest"""
        input_path = _prepare_input(tmp_path)
        output_dir = tmp_path / "output"

        # 第一次 run：成功
        rc1 = main(["run", str(input_path), "--output-dir", str(output_dir)])
        assert rc1 == 0, f"第一次 run 应成功，got rc={rc1}"

        predictions_path = output_dir / "predictions.jsonl"
        manifest_path = output_dir / "manifest.json"
        assert predictions_path.exists(), "第一次 run 应生成 predictions.jsonl"
        assert manifest_path.exists(), "第一次 run 应生成 manifest.json"

        first_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert first_manifest.get("status") == "completed", (
            f"第一次 manifest status 应为 completed，got {first_manifest.get('status')}"
        )
        first_run_id = first_manifest.get("run_id")
        first_predictions_content = predictions_path.read_text(encoding="utf-8").strip()
        assert first_predictions_content, "第一次 predictions 应有内容"

        # 第二次 run：模拟 detect_fields 抛异常 → 失败
        with patch(
            "semantic_detector.pipeline.pipeline.DetectionPipeline.detect_fields",
            side_effect=RuntimeError("R419 组合测试：detect_fields 失败"),
        ):
            rc2 = main(["run", str(input_path), "--output-dir", str(output_dir)])

        assert rc2 != 0, "第二次 run 应失败（detect_fields 异常）"

        # 旧 predictions 不存在或为空（不得保留第一次成功内容）
        second_predictions_content = predictions_path.read_text(encoding="utf-8").strip()
        assert second_predictions_content != first_predictions_content, (
            "第二次失败后不得保留第一次成功 predictions（内容相同）"
        )
        assert second_predictions_content == "", (
            f"第二次失败后 predictions 应为空，实际有 {len(second_predictions_content)} 字符"
        )

        # 旧成功 Manifest 不存在（被失败 Manifest 覆盖）
        second_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        second_status = second_manifest.get("status")
        assert second_status == "failed", (
            f"第二次 manifest status 应为 failed，got {second_status!r}"
        )

        # 失败 Manifest.run_id 与第一次不同
        second_run_id = second_manifest.get("run_id")
        assert second_run_id != first_run_id, (
            f"失败 Manifest run_id 应与第一次不同：first={first_run_id}, second={second_run_id}"
        )

        # 失败信息包含真实阶段名
        error_stage = second_manifest.get("error_stage") or second_manifest.get("failure_stage")
        assert error_stage == "detect_fields", (
            f"失败 manifest error_stage 应为 detect_fields，got {error_stage!r}"
        )

    def test_log_handle_released_after_failure(self, tmp_path: Path) -> None:
        """失败后 run.log 可重命名和删除（验证日志句柄已释放）

        Windows 下若 run.log 句柄未关闭，重命名和删除会抛 PermissionError。
        """
        input_path = _prepare_input(tmp_path)
        output_dir = tmp_path / "output"

        with patch(
            "semantic_detector.pipeline.pipeline.DetectionPipeline.detect_fields",
            side_effect=RuntimeError("R419 日志句柄测试：detect_fields 失败"),
        ):
            rc = main(["run", str(input_path), "--output-dir", str(output_dir)])

        assert rc != 0

        log_path = output_dir / "run.log"
        assert log_path.exists(), "run.log 必须存在"

        # 重命名 run.log（Windows 下句柄未关闭会抛 PermissionError）
        renamed = output_dir / "run_renamed.log"
        log_path.rename(renamed)
        assert renamed.exists(), "重命名后文件应存在"

        # 删除 run.log
        renamed.unlink()
        assert not renamed.exists(), "删除后文件不应存在"

        # 同目录再次运行（不受文件句柄锁影响）
        rc2 = main(["run", str(input_path), "--output-dir", str(output_dir)])
        assert rc2 == 0, "同目录再次运行应成功"
        assert log_path.exists(), "再次运行应重新生成 run.log"


class TestCliRunFailureManifestR421:
    """R421：失败 Manifest 扩展字段与半成品策略测试

    验证 R421 计划要求的失败 Manifest 字段完整性和半成品处理策略：
    - 扩展字段：valid_for_reporting/failure_stage/error_type/config_source/
      config_sha256/counts/partial_artifacts_present
    - 半成品策略：
      - 失败阶段在 build_profiles/export_profiles 或之前：profiles 清空，partial=false
      - 失败阶段在 detect_fields 及之后：profiles 保留，partial=true
    - 正常运行 Manifest 不受影响（无扩展失败字段）
    """

    def test_failed_manifest_contains_r421_extended_fields(self, tmp_path: Path) -> None:
        """失败 Manifest 必须包含 R421 扩展字段

        验证字段：valid_for_reporting=false, failure_stage, error_type,
        config_source, config_sha256, counts, partial_artifacts_present
        """
        input_path = _prepare_input(tmp_path)
        output_dir = tmp_path / "output"

        with patch(
            "semantic_detector.pipeline.pipeline.DetectionPipeline.detect_fields",
            side_effect=RuntimeError("R421 扩展字段测试"),
        ):
            rc = main(["run", str(input_path), "--output-dir", str(output_dir)])

        assert rc != 0
        manifest = _assert_failed_manifest(output_dir, "detect_fields")

        # R421 扩展字段
        assert manifest.get("valid_for_reporting") is False, (
            f"valid_for_reporting 应为 False，got {manifest.get('valid_for_reporting')}"
        )
        assert manifest.get("failure_stage") == "detect_fields", (
            f"failure_stage 应为 detect_fields，got {manifest.get('failure_stage')}"
        )
        assert manifest.get("error_type") == "RuntimeError", (
            f"error_type 应为 RuntimeError，got {manifest.get('error_type')}"
        )
        assert manifest.get("config_source") == "default", (
            f"config_source 应为 default，got {manifest.get('config_source')}"
        )
        # config_sha256 默认配置时为空串
        assert isinstance(manifest.get("config_sha256"), str), (
            f"config_sha256 应为字符串，got {type(manifest.get('config_sha256'))}"
        )

        # counts 嵌套对象
        counts = manifest.get("counts")
        assert isinstance(counts, dict), f"counts 应为 dict，got {type(counts)}"
        assert "input_line_count" in counts, "counts 必须包含 input_line_count"
        assert "validated_records" in counts, "counts 必须包含 validated_records"
        assert "rejected_records" in counts, "counts 必须包含 rejected_records"
        assert counts.get("field_profiles") == 0, "失败 counts.field_profiles 应为 0"
        assert counts.get("predictions") == 0, "失败 counts.predictions 应为 0"
        # input_line_count 应反映输入文件真实行数（2 条记录）
        assert counts.get("input_line_count") == 2, (
            f"input_line_count 应为 2，got {counts.get('input_line_count')}"
        )

        # partial_artifacts_present 必须存在（布尔值）
        assert "partial_artifacts_present" in manifest, (
            "失败 Manifest 必须包含 partial_artifacts_present 字段"
        )
        assert isinstance(manifest.get("partial_artifacts_present"), bool), (
            f"partial_artifacts_present 应为 bool，got {type(manifest.get('partial_artifacts_present'))}"
        )

    def test_partial_artifacts_present_true_when_detect_fails(self, tmp_path: Path) -> None:
        """detect_fields 失败时 profiles 已成功 → partial_artifacts_present=true，profiles 保留

        场景：
        1. 第一次 run 成功（predictions + profiles + manifest 都有内容）
        2. 第二次 run 模拟 detect_fields 失败
        3. 断言：
           - partial_artifacts_present=true
           - field_profiles.jsonl 保留诊断内容（不被清空）
           - predictions.jsonl 为空（始终清空）
        """
        input_path = _prepare_input(tmp_path)
        output_dir = tmp_path / "output"

        # 第一次 run 成功
        rc1 = main(["run", str(input_path), "--output-dir", str(output_dir)])
        assert rc1 == 0

        profiles_path = output_dir / "field_profiles.jsonl"
        first_profiles_content = profiles_path.read_text(encoding="utf-8").strip()
        assert first_profiles_content, "第一次 run 应生成有内容的 profiles"

        # 第二次 run：detect_fields 失败
        with patch(
            "semantic_detector.pipeline.pipeline.DetectionPipeline.detect_fields",
            side_effect=RuntimeError("R421 partial_artifacts 测试：detect_fields 失败"),
        ):
            rc2 = main(["run", str(input_path), "--output-dir", str(output_dir)])
        assert rc2 != 0

        manifest = _assert_failed_manifest(output_dir, "detect_fields")
        assert manifest.get("partial_artifacts_present") is True, (
            f"detect_fields 失败时 partial_artifacts_present 应为 True，got {manifest.get('partial_artifacts_present')}"
        )

        # profiles 保留诊断内容（第二次 run 重新生成的 profiles，非空）
        second_profiles_content = profiles_path.read_text(encoding="utf-8").strip()
        assert second_profiles_content, (
            "detect_fields 失败后 profiles 应保留诊断内容（非空）"
        )

        # predictions 始终为空
        predictions_path = output_dir / "predictions.jsonl"
        predictions_content = predictions_path.read_text(encoding="utf-8").strip()
        assert predictions_content == "", (
            f"detect_fields 失败后 predictions 应为空，实际有 {len(predictions_content)} 字符"
        )

    def test_partial_artifacts_present_false_when_build_profiles_fails(self, tmp_path: Path) -> None:
        """build_profiles 失败时 profiles 未生成 → partial_artifacts_present=false，profiles 清空

        场景：
        1. 第一次 run 成功
        2. 第二次 run 模拟 build_field_profiles 失败
        3. 断言：
           - partial_artifacts_present=false
           - field_profiles.jsonl 为空（清空）
           - predictions.jsonl 为空
        """
        input_path = _prepare_input(tmp_path)
        output_dir = tmp_path / "output"

        # 第一次 run 成功
        rc1 = main(["run", str(input_path), "--output-dir", str(output_dir)])
        assert rc1 == 0

        profiles_path = output_dir / "field_profiles.jsonl"
        assert profiles_path.read_text(encoding="utf-8").strip(), "第一次 run 应生成有内容的 profiles"

        # 第二次 run：build_field_profiles 失败
        with patch(
            "semantic_detector.profiling.profile_builder.build_field_profiles",
            side_effect=RuntimeError("R421 partial_artifacts 测试：build_profiles 失败"),
        ):
            rc2 = main(["run", str(input_path), "--output-dir", str(output_dir)])
        assert rc2 != 0

        manifest = _assert_failed_manifest(output_dir, "build_profiles")
        assert manifest.get("partial_artifacts_present") is False, (
            f"build_profiles 失败时 partial_artifacts_present 应为 False，got {manifest.get('partial_artifacts_present')}"
        )

        # profiles 清空
        profiles_content = profiles_path.read_text(encoding="utf-8").strip()
        assert profiles_content == "", (
            f"build_profiles 失败后 profiles 应为空，实际有 {len(profiles_content)} 字符"
        )

        # predictions 也为空
        predictions_path = output_dir / "predictions.jsonl"
        predictions_content = predictions_path.read_text(encoding="utf-8").strip()
        assert predictions_content == "", (
            f"build_profiles 失败后 predictions 应为空，实际有 {len(predictions_content)} 字符"
        )

    def test_normal_run_manifest_not_affected_by_r421(self, tmp_path: Path) -> None:
        """正常运行的 Manifest 不受 R421 失败字段影响

        正常 run 的 manifest 应保持原有结构（status=completed），
        不应出现 valid_for_reporting=false/failure_stage/error_type 等失败字段。
        """
        input_path = _prepare_input(tmp_path)
        output_dir = tmp_path / "output"

        rc = main(["run", str(input_path), "--output-dir", str(output_dir)])
        assert rc == 0

        manifest_path = output_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        # 正常 manifest 应为 completed 状态
        assert manifest.get("status") == "completed", (
            f"正常 run manifest status 应为 completed，got {manifest.get('status')}"
        )
        # 不应包含失败字段
        assert "failure_stage" not in manifest, "正常 manifest 不应包含 failure_stage"
        assert "error_type" not in manifest, "正常 manifest 不应包含 error_type"
        assert "error_stage" not in manifest, "正常 manifest 不应包含 error_stage"
        assert "error_message" not in manifest, "正常 manifest 不应包含 error_message"
        assert "partial_artifacts_present" not in manifest, (
            "正常 manifest 不应包含 partial_artifacts_present"
        )


class TestCliRunFailureStagesR426:
    """R426：失败阶段标志准确性测试

    验证 V5 审计 MEDIUM-1 修复：
    - write_rejected_groups/count_input_lines 失败时 partial_artifacts_present=False
    - detect_fields 失败时 partial_artifacts_present=True（profiles 保留）
    - export_predictions 失败时 predictions 不存在或为空
    """

    def test_write_rejected_groups_failure_has_no_partial_artifacts(self, tmp_path: Path) -> None:
        """write_rejected_groups 失败时 partial_artifacts_present=False

        write_rejected_groups 阶段在 build_profiles 之前，
        profiles 和 predictions 都不可能存在，partial_artifacts_present 必须为 False。
        """
        import builtins

        input_path = _prepare_input(tmp_path)
        output_dir = tmp_path / "output"

        original_open = builtins.open
        call_count = [0]

        def _fail_on_rejected_groups(*args, **kwargs):
            call_count[0] += 1
            # 拦截写 rejected_groups.jsonl 的 open 调用
            filename = str(args[0]) if args else str(kwargs.get("file", ""))
            if "rejected_groups.jsonl" in filename and args and "w" in str(args[1] if len(args) > 1 else kwargs.get("mode", "")):
                raise OSError("R426 模拟 write_rejected_groups 失败")
            return original_open(*args, **kwargs)

        with patch("builtins.open", side_effect=_fail_on_rejected_groups):
            rc = main(["run", str(input_path), "--output-dir", str(output_dir)])

        assert rc != 0, "write_rejected_groups 异常应返回非零退出码"
        manifest = _assert_failed_manifest(output_dir, "write_rejected_groups")
        # R426：write_rejected_groups 在 build_profiles 之前，不应有半成品
        assert manifest.get("partial_artifacts_present") is False, (
            f"write_rejected_groups 失败时 partial_artifacts_present 应为 False，"
            f"got {manifest.get('partial_artifacts_present')}"
        )
        _assert_run_log_readable(output_dir)

    def test_count_input_lines_failure_has_no_partial_artifacts(self, tmp_path: Path) -> None:
        """count_input_lines 失败时 partial_artifacts_present=False

        count_input_lines 阶段在 build_profiles 之前，
        profiles 和 predictions 都不可能存在，partial_artifacts_present 必须为 False。
        """
        import builtins

        input_path = _prepare_input(tmp_path)
        output_dir = tmp_path / "output"

        original_open = builtins.open
        input_open_count = [0]

        def _fail_on_second_input_read(*args, **kwargs):
            filename = str(args[0]) if args else str(kwargs.get("file", ""))
            # 拦截第二次打开 input_file（第一次是 read_jsonl_file，第二次是 count_input_lines）
            if str(input_path) in filename:
                input_open_count[0] += 1
                if input_open_count[0] == 2:
                    raise OSError("R426 模拟 count_input_lines 失败")
            return original_open(*args, **kwargs)

        with patch("builtins.open", side_effect=_fail_on_second_input_read):
            rc = main(["run", str(input_path), "--output-dir", str(output_dir)])

        assert rc != 0, "count_input_lines 异常应返回非零退出码"
        manifest = _assert_failed_manifest(output_dir, "count_input_lines")
        # R426：count_input_lines 在 build_profiles 之前，不应有半成品
        assert manifest.get("partial_artifacts_present") is False, (
            f"count_input_lines 失败时 partial_artifacts_present 应为 False，"
            f"got {manifest.get('partial_artifacts_present')}"
        )
        _assert_run_log_readable(output_dir)

    def test_detect_fields_failure_may_keep_profiles_but_not_predictions(self, tmp_path: Path) -> None:
        """detect_fields 失败时 partial_artifacts_present=True（profiles 保留）

        detect_fields 阶段在 export_profiles 之后，profiles 已完整写入文件，
        predictions 尚未生成。partial_artifacts_present 应为 True（profiles 存在）。
        """
        input_path = _prepare_input(tmp_path)
        output_dir = tmp_path / "output"

        with patch(
            "semantic_detector.pipeline.pipeline.DetectionPipeline.detect_fields",
            side_effect=RuntimeError("R426 模拟 detect_fields 失败"),
        ):
            rc = main(["run", str(input_path), "--output-dir", str(output_dir)])

        assert rc != 0, "detect_fields 异常应返回非零退出码"
        manifest = _assert_failed_manifest(output_dir, "detect_fields")
        # R426：detect_fields 在 export_profiles 之后，profiles 应保留
        assert manifest.get("partial_artifacts_present") is True, (
            f"detect_fields 失败时 partial_artifacts_present 应为 True（profiles 保留），"
            f"got {manifest.get('partial_artifacts_present')}"
        )
        # profiles 应非空（保留诊断数据）
        profiles_path = output_dir / "field_profiles.jsonl"
        assert profiles_path.exists(), "profiles.jsonl 应存在"
        profiles_content = profiles_path.read_text(encoding="utf-8").strip()
        assert profiles_content != "", (
            f"detect_fields 失败后 profiles 应保留非空诊断内容，实际有 {len(profiles_content)} 字符"
        )
        # predictions 应为空（detect_fields 失败，predictions 未生成）
        predictions_path = output_dir / "predictions.jsonl"
        predictions_content = predictions_path.read_text(encoding="utf-8").strip()
        assert predictions_content == "", (
            f"detect_fields 失败后 predictions 应为空，实际有 {len(predictions_content)} 字符"
        )
        _assert_run_log_readable(output_dir)

    def test_export_predictions_failure_does_not_keep_partial_predictions(self, tmp_path: Path) -> None:
        """export_predictions 失败时 predictions 不存在或为空

        export_predictions 阶段在 detect_fields 之后，profiles 已完整写入，
        但 predictions 文件不能视为完整（可能半写）。predictions 必须清空。
        partial_artifacts_present 应为 True（profiles 存在）。
        """
        input_path = _prepare_input(tmp_path)
        output_dir = tmp_path / "output"

        with patch(
            "semantic_detector.io.exporters.export_predictions_to_jsonl",
            side_effect=RuntimeError("R426 模拟 export_predictions 失败"),
        ):
            rc = main(["run", str(input_path), "--output-dir", str(output_dir)])

        assert rc != 0, "export_predictions 异常应返回非零退出码"
        manifest = _assert_failed_manifest(output_dir, "export_predictions")
        # R426：export_predictions 在 export_profiles 之后，profiles 应保留
        assert manifest.get("partial_artifacts_present") is True, (
            f"export_predictions 失败时 partial_artifacts_present 应为 True（profiles 保留），"
            f"got {manifest.get('partial_artifacts_present')}"
        )
        # predictions 必须为空（半写被清空）
        predictions_path = output_dir / "predictions.jsonl"
        predictions_content = predictions_path.read_text(encoding="utf-8").strip()
        assert predictions_content == "", (
            f"export_predictions 失败后 predictions 必须为空（无半写内容），"
            f"实际有 {len(predictions_content)} 字符"
        )
        _assert_run_log_readable(output_dir)
