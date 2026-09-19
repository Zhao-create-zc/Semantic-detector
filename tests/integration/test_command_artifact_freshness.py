"""R392：Validate 和 Infer 产物清理测试

验证所有主要命令都遵守产物所有权（R392 计划三个验收点）：
1. validate 第二次无 rejection → rejected 空
2. infer 第二次空输入或失败 → 不保留旧 predictions
3. 命令之间不误删对方文件
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from semantic_detector.cli import main


def _write_jsonl(path: Path, records: list) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _make_valid_record(message_id: str = "m1", layout_id: str = "L1") -> dict:
    return {
        "message_id": message_id,
        "layout_id": layout_id,
        "direction": "request",
        "payload_hex": "0001",
        "fields": [{"field_index": 0, "start": 0, "end": 2}],
    }


def _make_profiles_file(path: Path, layout_id: str = "L1") -> None:
    """用 profile 命令生成合法的 field_profiles.jsonl（避免手写 FieldProfile 字段）

    通过 cmd_profile 生成真实可被 import_field_profiles 解析的画像文件，
    保证字段名与 FieldProfile dataclass 定义一致。
    """
    input_path = path.parent / f"input_{layout_id}.jsonl"
    _write_jsonl(input_path, [_make_valid_record("p1", layout_id=layout_id)])
    output_dir = path.parent / f"profile_output_{layout_id}"
    rc = main(["profile", str(input_path), "--output-dir", str(output_dir)])
    assert rc == 0, f"生成 profiles 失败 rc={rc}"
    profiles_generated = output_dir / "field_profiles.jsonl"
    assert profiles_generated.exists()
    # 复制到目标路径
    import shutil
    shutil.copy(profiles_generated, path)


class TestValidateArtifactFreshnessR392:
    """R392 验收点 1：validate 第二次无 rejection → rejected 空"""

    def test_r392_validate_second_run_no_rejection_clears_old_rejected(self, tmp_path: Path) -> None:
        """R392: validate 第二次无 rejection 时 rejected.jsonl 必须为空

        场景：
        1. 第一次 validate 含 invalid JSON → rejected.jsonl 有内容
        2. 第二次 validate 全合法 → rejected.jsonl 必须为空（覆盖旧文件）
        """
        # 第一次 validate：含 invalid JSON
        bad_input = tmp_path / "bad.jsonl"
        with open(bad_input, "w", encoding="utf-8") as f:
            f.write(json.dumps(_make_valid_record("ok")) + "\n")
            f.write('{"message_id": "bad", invalid json}\n')
        output_dir = tmp_path / "output"

        rc1 = main(["validate", str(bad_input), "--output-dir", str(output_dir)])
        assert rc1 != 0, "第一次 validate 含 invalid JSON 应 exit 非零"

        rejected_path = output_dir / "rejected.jsonl"
        assert rejected_path.exists()
        first_content = rejected_path.read_text(encoding="utf-8").strip()
        assert first_content, "第一次 rejected.jsonl 应有内容"

        # 第二次 validate：全合法
        good_input = tmp_path / "good.jsonl"
        _write_jsonl(good_input, [_make_valid_record("m1"), _make_valid_record("m2", layout_id="L2")])

        rc2 = main(["validate", str(good_input), "--output-dir", str(output_dir)])
        assert rc2 == 0, f"第二次 validate 全合法应 exit 0，got rc={rc2}"

        # rejected.jsonl 必须为空
        second_content = rejected_path.read_text(encoding="utf-8").strip()
        assert second_content == "", (
            f"R392: 第二次 validate 无 rejection 时 rejected.jsonl 必须为空，got: {second_content}"
        )

    def test_r392_validate_second_run_clears_old_rejected_groups(self, tmp_path: Path) -> None:
        """R392: validate 第二次无 rejection 时 rejected_groups.jsonl 必须为空

        场景：
        1. 第一次 validate 含 group field-count mismatch → rejected_groups.jsonl 有内容
        2. 第二次 validate 全合法 → rejected_groups.jsonl 必须为空
        """
        # 第一次 validate：group mismatch
        mismatch_input = tmp_path / "mismatch.jsonl"
        _write_jsonl(mismatch_input, [
            {
                "message_id": "m1", "layout_id": "L1", "direction": "request",
                "payload_hex": "000102", "fields": [{"field_index": 0, "start": 0, "end": 2}],
            },
            {
                "message_id": "m2", "layout_id": "L1", "direction": "request",
                "payload_hex": "0001020304",
                "fields": [
                    {"field_index": 0, "start": 0, "end": 2},
                    {"field_index": 1, "start": 2, "end": 4},
                ],
            },
        ])
        output_dir = tmp_path / "output"

        rc1 = main(["validate", str(mismatch_input), "--output-dir", str(output_dir)])
        assert rc1 != 0

        rejected_groups_path = output_dir / "rejected_groups.jsonl"
        assert rejected_groups_path.exists()
        first_content = rejected_groups_path.read_text(encoding="utf-8").strip()
        assert first_content, "第一次 rejected_groups.jsonl 应有内容"

        # 第二次 validate：全合法
        good_input = tmp_path / "good.jsonl"
        _write_jsonl(good_input, [_make_valid_record("m1"), _make_valid_record("m2", layout_id="L2")])

        rc2 = main(["validate", str(good_input), "--output-dir", str(output_dir)])
        assert rc2 == 0

        second_content = rejected_groups_path.read_text(encoding="utf-8").strip()
        assert second_content == "", (
            f"R392: 第二次 validate 无 rejection 时 rejected_groups.jsonl 必须为空，got: {second_content}"
        )


class TestInferArtifactFreshnessR392:
    """R392 验收点 2：infer 第二次空输入或失败 → 不保留旧 predictions"""

    def test_r392_infer_failed_read_does_not_retain_old_predictions(self, tmp_path: Path) -> None:
        """R392: infer 读取画像失败时不保留旧成功 predictions

        场景：
        1. 第一次 infer 成功 → predictions.jsonl 有内容
        2. 第二次 infer 输入文件含无效 JSON → import_field_profiles 抛异常 → 失败
        3. 断言：predictions.jsonl 必须为空（不保留旧成功产物）
        """
        # 准备一个合法的 field_profiles.jsonl
        profiles_input = tmp_path / "profiles.jsonl"
        _make_profiles_file(profiles_input, "L1")
        output_dir = tmp_path / "output"

        # 第一次 infer：成功
        rc1 = main(["infer", str(profiles_input), "--output-dir", str(output_dir)])
        assert rc1 == 0, f"第一次 infer 应成功，got rc={rc1}"

        predictions_path = output_dir / "predictions.jsonl"
        assert predictions_path.exists()
        first_content = predictions_path.read_text(encoding="utf-8").strip()
        assert first_content, "第一次 predictions 应有内容"

        # 第二次 infer：输入文件含无效 JSON → import_field_profiles 抛异常
        bad_profiles = tmp_path / "bad_profiles.jsonl"
        with open(bad_profiles, "w", encoding="utf-8") as f:
            f.write('{"invalid json content}\n')

        rc2 = main(["infer", str(bad_profiles), "--output-dir", str(output_dir)])
        assert rc2 != 0, f"第二次 infer 应失败（读取画像失败），got rc={rc2}"

        # predictions.jsonl 必须为空（不保留旧成功产物）
        second_content = predictions_path.read_text(encoding="utf-8").strip()
        assert second_content == "", (
            f"R392: infer 失败后 predictions.jsonl 必须为空（不保留旧成功产物），got: {second_content}"
        )

    def test_r392_infer_failed_detect_does_not_retain_old_predictions(self, tmp_path: Path) -> None:
        """R392: infer 推断失败时不保留旧成功 predictions

        场景：
        1. 第一次 infer 成功 → predictions.jsonl 有内容
        2. 第二次 infer 模拟 detect_fields 抛异常 → 失败
        3. 断言：predictions.jsonl 必须为空
        """
        profiles_input = tmp_path / "profiles.jsonl"
        _make_profiles_file(profiles_input, "L1")
        output_dir = tmp_path / "output"

        # 第一次 infer：成功
        rc1 = main(["infer", str(profiles_input), "--output-dir", str(output_dir)])
        assert rc1 == 0

        predictions_path = output_dir / "predictions.jsonl"
        first_content = predictions_path.read_text(encoding="utf-8").strip()
        assert first_content

        # 第二次 infer：模拟 detect_fields 抛异常
        with patch(
            "semantic_detector.pipeline.pipeline.DetectionPipeline.detect_fields",
            side_effect=RuntimeError("R392 模拟推断失败"),
        ):
            rc2 = main(["infer", str(profiles_input), "--output-dir", str(output_dir)])

        assert rc2 != 0

        # predictions.jsonl 必须为空
        second_content = predictions_path.read_text(encoding="utf-8").strip()
        assert second_content == "", (
            f"R392: infer 推断失败后 predictions.jsonl 必须为空，got: {second_content}"
        )


class TestCommandArtifactIsolationR392:
    """R392 验收点 3：命令之间不误删对方文件"""

    def test_r392_validate_does_not_delete_run_artifacts(self, tmp_path: Path) -> None:
        """R392: validate 不删除 run 命令的产物（manifest/run.log）

        场景：
        1. 先 run → 生成 manifest.json + run.log + predictions.jsonl 等
        2. 再 validate 同输出目录
        3. 断言：run 的 manifest.json 和 run.log 仍然存在
           （validate 不拥有这两个文件，不应删除）
        """
        # 先 run
        run_input = tmp_path / "run_input.jsonl"
        _write_jsonl(run_input, [_make_valid_record("m1"), _make_valid_record("m2", layout_id="L2")])
        output_dir = tmp_path / "output"

        rc_run = main(["run", str(run_input), "--output-dir", str(output_dir)])
        assert rc_run == 0

        manifest_path = output_dir / "manifest.json"
        run_log_path = output_dir / "run.log"
        assert manifest_path.exists(), "run 应生成 manifest.json"
        assert run_log_path.exists(), "run 应生成 run.log"
        manifest_sha_before = manifest_path.read_text(encoding="utf-8")

        # 再 validate 同输出目录
        validate_input = tmp_path / "validate_input.jsonl"
        _write_jsonl(validate_input, [_make_valid_record("v1")])

        rc_val = main(["validate", str(validate_input), "--output-dir", str(output_dir)])
        assert rc_val == 0

        # 断言：run 的 manifest.json 和 run.log 仍然存在且未被修改
        assert manifest_path.exists(), (
            "R392: validate 不应删除 run 的 manifest.json（命令隔离）"
        )
        assert run_log_path.exists(), (
            "R392: validate 不应删除 run 的 run.log（命令隔离）"
        )
        manifest_sha_after = manifest_path.read_text(encoding="utf-8")
        assert manifest_sha_after == manifest_sha_before, (
            "R392: validate 不应修改 run 的 manifest.json 内容"
        )

    def test_r392_infer_does_not_delete_validate_artifacts(self, tmp_path: Path) -> None:
        """R392: infer 不删除 validate 命令的产物（validated.jsonl/rejected.jsonl）

        场景：
        1. 先 validate → 生成 validated.jsonl + rejected.jsonl
        2. 再 infer 同输出目录
        3. 断言：validate 的 validated.jsonl 和 rejected.jsonl 仍然存在
        """
        # 先 validate
        validate_input = tmp_path / "validate_input.jsonl"
        _write_jsonl(validate_input, [_make_valid_record("v1")])
        output_dir = tmp_path / "output"

        rc_val = main(["validate", str(validate_input), "--output-dir", str(output_dir)])
        assert rc_val == 0

        validated_path = output_dir / "validated.jsonl"
        rejected_path = output_dir / "rejected.jsonl"
        assert validated_path.exists()
        assert rejected_path.exists()
        validated_content_before = validated_path.read_text(encoding="utf-8")

        # 再 infer 同输出目录
        profiles_input = tmp_path / "profiles.jsonl"
        _make_profiles_file(profiles_input, "L1")

        rc_infer = main(["infer", str(profiles_input), "--output-dir", str(output_dir)])
        assert rc_infer == 0

        # 断言：validate 的 validated.jsonl 和 rejected.jsonl 仍然存在且未修改
        assert validated_path.exists(), (
            "R392: infer 不应删除 validate 的 validated.jsonl（命令隔离）"
        )
        assert rejected_path.exists(), (
            "R392: infer 不应删除 validate 的 rejected.jsonl（命令隔离）"
        )
        validated_content_after = validated_path.read_text(encoding="utf-8")
        assert validated_content_after == validated_content_before, (
            "R392: infer 不应修改 validate 的 validated.jsonl 内容"
        )

        # infer 应生成自己的 predictions.jsonl
        predictions_path = output_dir / "predictions.jsonl"
        assert predictions_path.exists(), "infer 应生成 predictions.jsonl"
