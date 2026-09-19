"""R388：命令产物所有权清单测试

验证 R388 定义的 5 个命令（validate/profile/infer/run/evaluate）的产物所有权清单：
- 每个命令拥有哪些文件
- 文件清单符合 07_简易字段语义检测器V3_五分钟逐轮详细修复计划_R372-R416.md R388 要求
- 命令之间不互相清理对方文件
- 所有权声明完整覆盖 CLI 实际产生的文件
"""

import tempfile
from pathlib import Path

import pytest

from semantic_detector.io.artifact_manager import (
    COMMAND_ARTIFACTS,
    get_command_artifacts,
    clean_command_artifacts,
)


class TestArtifactOwnershipR388:
    """R388：命令产物所有权清单测试"""

    def test_r388_five_commands_defined(self):
        """R388: 5 个命令的产物清单已定义"""
        assert "validate" in COMMAND_ARTIFACTS
        assert "profile" in COMMAND_ARTIFACTS
        assert "infer" in COMMAND_ARTIFACTS
        assert "run" in COMMAND_ARTIFACTS
        assert "evaluate" in COMMAND_ARTIFACTS
        assert len(COMMAND_ARTIFACTS) == 5

    def test_r388_validate_artifacts(self):
        """R388: validate 命令产物清单

        validate 负责：
        - validated.jsonl
        - rejected.jsonl
        - rejected_groups.jsonl（CLI 实际产生）
        - validate.log（R388 声明所有权，CLI 当前不产生但保留扩展）
        """
        artifacts = get_command_artifacts("validate")
        assert "validated.jsonl" in artifacts
        assert "rejected.jsonl" in artifacts
        assert "rejected_groups.jsonl" in artifacts
        assert "validate.log" in artifacts

    def test_r388_profile_artifacts(self):
        """R388: profile 命令产物清单

        profile 负责：
        - field_profiles.jsonl
        - rejected.jsonl（R385 修复后产生）
        - rejected_groups.jsonl
        - profile.log（R388 声明所有权）
        - profile_manifest.json（R388 声明所有权）
        """
        artifacts = get_command_artifacts("profile")
        assert "field_profiles.jsonl" in artifacts
        assert "rejected.jsonl" in artifacts
        assert "rejected_groups.jsonl" in artifacts
        assert "profile.log" in artifacts
        assert "profile_manifest.json" in artifacts

    def test_r388_infer_artifacts(self):
        """R388: infer 命令产物清单

        infer 负责：
        - predictions.jsonl
        - infer.log（R388 声明所有权）
        - infer_manifest.json（R388 声明所有权）
        """
        artifacts = get_command_artifacts("infer")
        assert "predictions.jsonl" in artifacts
        assert "infer.log" in artifacts
        assert "infer_manifest.json" in artifacts

    def test_r388_run_artifacts(self):
        """R388: run 命令产物清单

        run 负责（7 个文件）：
        - validated.jsonl
        - rejected.jsonl
        - rejected_groups.jsonl
        - field_profiles.jsonl
        - predictions.jsonl
        - manifest.json
        - run.log
        """
        artifacts = get_command_artifacts("run")
        assert "validated.jsonl" in artifacts
        assert "rejected.jsonl" in artifacts
        assert "rejected_groups.jsonl" in artifacts
        assert "field_profiles.jsonl" in artifacts
        assert "predictions.jsonl" in artifacts
        assert "manifest.json" in artifacts
        assert "run.log" in artifacts
        assert len(artifacts) == 7

    def test_r388_evaluate_artifacts(self):
        """R388: evaluate 命令产物清单

        evaluate 负责：
        - metrics.json
        - per_label_metrics.csv
        - confusion_matrix.csv
        - errors.jsonl
        - rejected_ground_truth.jsonl
        - evaluation_manifest.json（R388 声明所有权）
        """
        artifacts = get_command_artifacts("evaluate")
        assert "metrics.json" in artifacts
        assert "per_label_metrics.csv" in artifacts
        assert "confusion_matrix.csv" in artifacts
        assert "errors.jsonl" in artifacts
        assert "rejected_ground_truth.jsonl" in artifacts
        assert "evaluation_manifest.json" in artifacts

    def test_r388_unknown_command_returns_empty(self):
        """R388: 未知命令返回空元组"""
        assert get_command_artifacts("unknown") == ()
        assert get_command_artifacts("") == ()


class TestArtifactOwnershipIsolationR388:
    """R388：命令之间产物所有权隔离测试

    验证：一个命令清理时不会删除其他命令的产物。
    """

    def test_r388_validate_does_not_clean_run_files(self):
        """R388: validate 清理时不删除 run 拥有的 manifest.json/predictions.jsonl"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # run 命令的产物
            (Path(tmpdir) / "manifest.json").write_text('{"run": true}', encoding="utf-8")
            (Path(tmpdir) / "predictions.jsonl").write_text("predictions", encoding="utf-8")
            (Path(tmpdir) / "field_profiles.jsonl").write_text("profiles", encoding="utf-8")
            # validate 命令的产物
            (Path(tmpdir) / "validated.jsonl").write_text("validated", encoding="utf-8")

            removed = clean_command_artifacts(tmpdir, "validate")

            assert "validated.jsonl" in removed
            # run 的文件不应被删除
            assert "manifest.json" not in removed
            assert "predictions.jsonl" not in removed
            assert "field_profiles.jsonl" not in removed
            assert (Path(tmpdir) / "manifest.json").exists()
            assert (Path(tmpdir) / "predictions.jsonl").exists()
            assert (Path(tmpdir) / "field_profiles.jsonl").exists()

    def test_r388_profile_does_not_clean_evaluate_files(self):
        """R388: profile 清理时不删除 evaluate 拥有的 metrics.json/errors.jsonl"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # evaluate 命令的产物
            (Path(tmpdir) / "metrics.json").write_text('{"accuracy": 0.9}', encoding="utf-8")
            (Path(tmpdir) / "errors.jsonl").write_text("errors", encoding="utf-8")
            (Path(tmpdir) / "confusion_matrix.csv").write_text("matrix", encoding="utf-8")
            # profile 命令的产物
            (Path(tmpdir) / "field_profiles.jsonl").write_text("profiles", encoding="utf-8")

            removed = clean_command_artifacts(tmpdir, "profile")

            assert "field_profiles.jsonl" in removed
            # evaluate 的文件不应被删除
            assert "metrics.json" not in removed
            assert "errors.jsonl" not in removed
            assert "confusion_matrix.csv" not in removed
            assert (Path(tmpdir) / "metrics.json").exists()
            assert (Path(tmpdir) / "errors.jsonl").exists()
            assert (Path(tmpdir) / "confusion_matrix.csv").exists()

    def test_r388_run_does_not_clean_evaluate_files(self):
        """R388: run 清理时不删除 evaluate 拥有的文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # evaluate 命令的产物
            (Path(tmpdir) / "metrics.json").write_text('{"accuracy": 0.9}', encoding="utf-8")
            (Path(tmpdir) / "errors.jsonl").write_text("errors", encoding="utf-8")
            # run 命令的产物
            (Path(tmpdir) / "manifest.json").write_text('{"run": true}', encoding="utf-8")
            (Path(tmpdir) / "predictions.jsonl").write_text("predictions", encoding="utf-8")

            removed = clean_command_artifacts(tmpdir, "run")

            assert "manifest.json" in removed
            assert "predictions.jsonl" in removed
            # evaluate 的文件不应被删除
            assert "metrics.json" not in removed
            assert "errors.jsonl" not in removed
            assert (Path(tmpdir) / "metrics.json").exists()
            assert (Path(tmpdir) / "errors.jsonl").exists()

    def test_r388_evaluate_does_not_clean_run_files(self):
        """R388: evaluate 清理时不删除 run 拥有的 manifest.json/predictions.jsonl"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # run 命令的产物
            (Path(tmpdir) / "manifest.json").write_text('{"run": true}', encoding="utf-8")
            (Path(tmpdir) / "predictions.jsonl").write_text("predictions", encoding="utf-8")
            (Path(tmpdir) / "run.log").write_text("log", encoding="utf-8")
            # evaluate 命令的产物
            (Path(tmpdir) / "metrics.json").write_text('{"accuracy": 0.9}', encoding="utf-8")

            removed = clean_command_artifacts(tmpdir, "evaluate")

            assert "metrics.json" in removed
            # run 的文件不应被删除
            assert "manifest.json" not in removed
            assert "predictions.jsonl" not in removed
            assert "run.log" not in removed
            assert (Path(tmpdir) / "manifest.json").exists()
            assert (Path(tmpdir) / "predictions.jsonl").exists()
            assert (Path(tmpdir) / "run.log").exists()

    def test_r388_infer_does_not_clean_run_files(self):
        """R388: infer 清理时不删除 run 拥有的 manifest.json/field_profiles.jsonl

        注意：infer 和 run 都拥有 predictions.jsonl，infer 清理时会删除它。
        这是设计意图（infer 命令重新生成 predictions）。
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # run 命令独有的产物
            (Path(tmpdir) / "manifest.json").write_text('{"run": true}', encoding="utf-8")
            (Path(tmpdir) / "field_profiles.jsonl").write_text("profiles", encoding="utf-8")
            (Path(tmpdir) / "run.log").write_text("log", encoding="utf-8")
            # infer 和 run 共有的产物
            (Path(tmpdir) / "predictions.jsonl").write_text("predictions", encoding="utf-8")

            removed = clean_command_artifacts(tmpdir, "infer")

            # infer 拥有 predictions.jsonl，应删除
            assert "predictions.jsonl" in removed
            # run 独有的文件不应被删除
            assert "manifest.json" not in removed
            assert "field_profiles.jsonl" not in removed
            assert "run.log" not in removed
            assert (Path(tmpdir) / "manifest.json").exists()
            assert (Path(tmpdir) / "field_profiles.jsonl").exists()
            assert (Path(tmpdir) / "run.log").exists()


class TestArtifactOwnershipCoverageR388:
    """R388：产物所有权覆盖 CLI 实际产生文件测试

    验证 COMMAND_ARTIFACTS 覆盖 CLI 实际产生的所有文件。
    """

    def test_r388_validate_cleans_all_validate_outputs(self):
        """R388: validate 清理能覆盖 cmd_validate 实际产生的所有文件

        cmd_validate 产生：validated.jsonl, rejected.jsonl, rejected_groups.jsonl
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # 模拟 cmd_validate 产生的所有文件
            for filename in ["validated.jsonl", "rejected.jsonl", "rejected_groups.jsonl"]:
                (Path(tmpdir) / filename).write_text("data", encoding="utf-8")

            removed = clean_command_artifacts(tmpdir, "validate")

            # 所有 validate 产物都应被清理
            assert "validated.jsonl" in removed
            assert "rejected.jsonl" in removed
            assert "rejected_groups.jsonl" in removed
            # 目录中不应再有 validate 产物
            for filename in ["validated.jsonl", "rejected.jsonl", "rejected_groups.jsonl"]:
                assert not (Path(tmpdir) / filename).exists()

    def test_r388_profile_cleans_all_profile_outputs(self):
        """R388: profile 清理能覆盖 cmd_profile 实际产生的所有文件

        cmd_profile 产生：field_profiles.jsonl, rejected.jsonl, rejected_groups.jsonl
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            for filename in [
                "field_profiles.jsonl",
                "rejected.jsonl",
                "rejected_groups.jsonl",
            ]:
                (Path(tmpdir) / filename).write_text("data", encoding="utf-8")

            removed = clean_command_artifacts(tmpdir, "profile")

            assert "field_profiles.jsonl" in removed
            assert "rejected.jsonl" in removed
            assert "rejected_groups.jsonl" in removed
            for filename in [
                "field_profiles.jsonl",
                "rejected.jsonl",
                "rejected_groups.jsonl",
            ]:
                assert not (Path(tmpdir) / filename).exists()

    def test_r388_run_cleans_all_run_outputs(self):
        """R388: run 清理能覆盖 cmd_run 实际产生的所有文件

        cmd_run 产生 7 个文件：validated/rejected/rejected_groups/field_profiles/predictions/manifest/run.log
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            run_files = [
                "validated.jsonl",
                "rejected.jsonl",
                "rejected_groups.jsonl",
                "field_profiles.jsonl",
                "predictions.jsonl",
                "manifest.json",
                "run.log",
            ]
            for filename in run_files:
                (Path(tmpdir) / filename).write_text("data", encoding="utf-8")

            removed = clean_command_artifacts(tmpdir, "run")

            # 所有 run 产物都应被清理
            assert sorted(removed) == sorted(run_files)
            for filename in run_files:
                assert not (Path(tmpdir) / filename).exists()

    def test_r388_evaluate_cleans_all_evaluate_outputs(self):
        """R388: evaluate 清理能覆盖 cmd_evaluate 实际产生的所有文件

        cmd_evaluate 产生：metrics.json, per_label_metrics.csv, confusion_matrix.csv,
        errors.jsonl, rejected_ground_truth.jsonl
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            eval_files = [
                "metrics.json",
                "per_label_metrics.csv",
                "confusion_matrix.csv",
                "errors.jsonl",
                "rejected_ground_truth.jsonl",
            ]
            for filename in eval_files:
                (Path(tmpdir) / filename).write_text("data", encoding="utf-8")

            removed = clean_command_artifacts(tmpdir, "evaluate")

            # evaluate 实际产生的 5 个文件都应被清理
            for filename in eval_files:
                assert filename in removed
                assert not (Path(tmpdir) / filename).exists()

    def test_r388_user_input_not_in_any_ownership(self):
        """R388: 用户输入文件不在任何命令的所有权清单中

        验证：input.jsonl / ground_truth.json 等用户输入文件不会被任何命令清理。
        """
        user_files = [
            "input.jsonl",
            "ground_truth.json",
            "ground_truth.jsonl",
            "predictions.jsonl",  # 注意：这个在 infer/run 的所有权中
            "field_profiles.jsonl",  # 注意：这个在 profile/run 的所有权中
        ]

        # 用户输入文件（不在任何命令所有权中）
        pure_user_files = ["input.jsonl", "ground_truth.json", "ground_truth.jsonl"]

        for filename in pure_user_files:
            # 不应在任何命令的所有权清单中
            for command in ["validate", "profile", "infer", "run", "evaluate"]:
                artifacts = get_command_artifacts(command)
                assert filename not in artifacts, (
                    f"{filename} 不应在 {command} 的所有权清单中（用户输入文件）"
                )

        # 验证：清理任何命令时，用户输入文件不被删除
        with tempfile.TemporaryDirectory() as tmpdir:
            for filename in pure_user_files:
                (Path(tmpdir) / filename).write_text("user data", encoding="utf-8")

            for command in ["validate", "profile", "infer", "run", "evaluate"]:
                removed = clean_command_artifacts(tmpdir, command)
                for filename in pure_user_files:
                    assert filename not in removed
                    assert (Path(tmpdir) / filename).exists()


class TestArtifactOwnershipLogDeclarationR388:
    """R388：产物所有权声明测试（日志和 Manifest 文件）

    验证 R388 声明所有权的文件（即使 CLI 当前不产生）能被正确清理。
    这为未来扩展（如添加 validate.log）预留所有权。
    """

    def test_r388_validate_log_ownership(self):
        """R388: validate 声明 validate.log 所有权（CLI 当前不产生，但可清理）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "validate.log").write_text("log", encoding="utf-8")

            removed = clean_command_artifacts(tmpdir, "validate")

            assert "validate.log" in removed
            assert not (Path(tmpdir) / "validate.log").exists()

    def test_r388_profile_log_and_manifest_ownership(self):
        """R388: profile 声明 profile.log 和 profile_manifest.json 所有权"""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "profile.log").write_text("log", encoding="utf-8")
            (Path(tmpdir) / "profile_manifest.json").write_text("{}", encoding="utf-8")

            removed = clean_command_artifacts(tmpdir, "profile")

            assert "profile.log" in removed
            assert "profile_manifest.json" in removed

    def test_r388_infer_log_and_manifest_ownership(self):
        """R388: infer 声明 infer.log 和 infer_manifest.json 所有权"""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "infer.log").write_text("log", encoding="utf-8")
            (Path(tmpdir) / "infer_manifest.json").write_text("{}", encoding="utf-8")

            removed = clean_command_artifacts(tmpdir, "infer")

            assert "infer.log" in removed
            assert "infer_manifest.json" in removed

    def test_r388_evaluate_manifest_ownership(self):
        """R388: evaluate 声明 evaluation_manifest.json 所有权"""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "evaluation_manifest.json").write_text("{}", encoding="utf-8")

            removed = clean_command_artifacts(tmpdir, "evaluate")

            assert "evaluation_manifest.json" in removed
