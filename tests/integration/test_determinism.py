"""R308: Demo 确定性测试

验证同一 Demo 连续两次运行，除 run_id/时间/绝对路径外结果一致。
"""

import pytest
from pathlib import Path

from semantic_detector.io.jsonl import read_jsonl_file
from semantic_detector.profiling.collector import (
    group_by_layout_and_direction,
    validate_group_field_count,
    record_to_field_samples,
    aggregate_by_field_key,
    mark_insufficient_groups,
)
from semantic_detector.profiling.profile_builder import build_field_profile
from semantic_detector.pipeline.pipeline import DetectionPipeline


def _build_profiles():
    """读取 Demo 数据并构建画像"""
    messages_path = Path("examples/messages.jsonl")
    if not messages_path.exists():
        pytest.skip("examples/messages.jsonl not found")

    valid, rejected = read_jsonl_file(str(messages_path))
    assert len(rejected) == 0

    groups = group_by_layout_and_direction(valid)
    valid_groups, _ = validate_group_field_count(groups)
    all_samples = []
    for key, records in valid_groups.items():
        for record in records:
            all_samples.extend(record_to_field_samples(record))
    field_groups = aggregate_by_field_key(all_samples)
    field_groups, _ = mark_insufficient_groups(field_groups, min_samples=8)

    profiles = []
    for fk, samples in field_groups.items():
        profile = build_field_profile(fk, samples)
        profiles.append(profile)
    return profiles


class TestDeterminismR308:
    """R308: 验证同一 Demo 连续两次运行结果可复现"""

    def test_run_id_changes_between_runs(self):
        """两次运行的 run_id 应不同（每次生成新 UUID）"""
        profiles = _build_profiles()

        pipeline1 = DetectionPipeline()
        predictions1 = pipeline1.detect_fields(profiles)

        pipeline2 = DetectionPipeline()
        predictions2 = pipeline2.detect_fields(profiles)

        assert predictions1[0].run_id != predictions2[0].run_id, "run_id 应每次不同"

    def test_identity_fields_stable(self):
        """身份字段（layout_id/direction/field_index）两次一致"""
        profiles = _build_profiles()

        pipeline1 = DetectionPipeline()
        predictions1 = pipeline1.detect_fields(profiles)

        pipeline2 = DetectionPipeline()
        predictions2 = pipeline2.detect_fields(profiles)

        assert len(predictions1) == len(predictions2)
        for p1, p2 in zip(predictions1, predictions2):
            assert p1.layout_id == p2.layout_id
            assert p1.direction == p2.direction
            assert p1.field_index == p2.field_index

    def test_coarse_label_stable(self):
        """coarse_label 两次一致"""
        profiles = _build_profiles()

        predictions1 = DetectionPipeline().detect_fields(profiles)
        predictions2 = DetectionPipeline().detect_fields(profiles)

        for p1, p2 in zip(predictions1, predictions2):
            assert p1.coarse_label == p2.coarse_label, (
                f"coarse_label 不一致: {p1.layout_id}/{p1.field_index} "
                f"{p1.coarse_label} vs {p2.coarse_label}"
            )

    def test_fine_label_and_confidence_stable(self):
        """fine_label 和 confidence 两次一致"""
        profiles = _build_profiles()

        predictions1 = DetectionPipeline().detect_fields(profiles)
        predictions2 = DetectionPipeline().detect_fields(profiles)

        for p1, p2 in zip(predictions1, predictions2):
            assert p1.fine_label == p2.fine_label
            assert p1.confidence == p2.confidence

    def test_prediction_status_and_abstained_stable(self):
        """prediction_status 和 abstained 两次一致"""
        profiles = _build_profiles()

        predictions1 = DetectionPipeline().detect_fields(profiles)
        predictions2 = DetectionPipeline().detect_fields(profiles)

        for p1, p2 in zip(predictions1, predictions2):
            assert p1.prediction_status == p2.prediction_status
            assert p1.abstained == p2.abstained

    def test_evidence_detector_and_label_stable(self):
        """evidence 的 detector/coarse_label/fine_label/score 两次一致"""
        profiles = _build_profiles()

        predictions1 = DetectionPipeline().detect_fields(profiles)
        predictions2 = DetectionPipeline().detect_fields(profiles)

        for p1, p2 in zip(predictions1, predictions2):
            assert len(p1.evidence) == len(p2.evidence)
            for e1, e2 in zip(p1.evidence, p2.evidence):
                assert e1.detector == e2.detector
                assert e1.coarse_label == e2.coarse_label
                assert e1.fine_label == e2.fine_label
                assert e1.score == e2.score
                assert e1.is_hard_evidence == e2.is_hard_evidence
                assert e1.reason_code == e2.reason_code

    def test_alternatives_count_stable(self):
        """alternatives 数量两次一致"""
        profiles = _build_profiles()

        predictions1 = DetectionPipeline().detect_fields(profiles)
        predictions2 = DetectionPipeline().detect_fields(profiles)

        for p1, p2 in zip(predictions1, predictions2):
            assert len(p1.alternatives) == len(p2.alternatives)

    def test_cli_predictions_file_stable_except_run_id(self, tmp_path):
        """两次导出 predictions.jsonl 文件内容一致（除 run_id 外）

        R308+: 教程要求"同一输入两次运行结果一致，除 run_id/时间/绝对路径"。
        本测试验证文件 I/O 层的确定性：导出 JSONL 后读回，比较除 run_id 外的全部字段。
        """
        import json
        from semantic_detector.io.exporters import export_predictions_to_jsonl

        profiles = _build_profiles()

        pipeline1 = DetectionPipeline()
        predictions1 = pipeline1.detect_fields(profiles)
        out1 = tmp_path / "preds1.jsonl"
        export_predictions_to_jsonl(predictions1, str(out1))

        pipeline2 = DetectionPipeline()
        predictions2 = pipeline2.detect_fields(profiles)
        out2 = tmp_path / "preds2.jsonl"
        export_predictions_to_jsonl(predictions2, str(out2))

        # 读回并比较（除 run_id 外）
        with open(out1, 'r', encoding='utf-8') as f:
            lines1 = [json.loads(line) for line in f if line.strip()]
        with open(out2, 'r', encoding='utf-8') as f:
            lines2 = [json.loads(line) for line in f if line.strip()]

        assert len(lines1) == len(lines2)
        for d1, d2 in zip(lines1, lines2):
            # run_id 每次不同，跳过比较
            d1.pop('run_id', None)
            d2.pop('run_id', None)
            assert d1 == d2, f"文件输出不一致: {d1} vs {d2}"


class TestRepeatedRunArtifactsR352:
    """R352: 重复运行旧产物集成测试

    验证场景（计划 L976-991）：
    - run：先失败再成功；
    - evaluate：先有错误再无错误；
    - infer：先有预测再空预测；
    - 所有文件 SHA/行数属于第二次运行。

    核心目标：同一输出目录重复运行时，第二次运行的产物完全覆盖第一次，
    不残留旧数据（R342/R339/R351 无条件重写原则的端到端验证）。
    """

    @staticmethod
    def _write_jsonl(path, records):
        """写入 JSONL 文件"""
        import json
        with open(path, 'w', encoding='utf-8') as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + '\n')

    @staticmethod
    def _count_lines(path):
        """计算文件非空行数"""
        p = Path(path)
        if not p.exists():
            return -1
        with open(p, 'r', encoding='utf-8') as f:
            return sum(1 for line in f if line.strip())

    @staticmethod
    def _file_sha256(path):
        """计算文件 SHA256"""
        import hashlib
        p = Path(path)
        if not p.exists():
            return None
        h = hashlib.sha256()
        with open(p, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def _read_json(path):
        """读取 JSON 文件"""
        import json
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def test_run_fail_then_success_artifacts_belong_to_second_run(self, tmp_path):
        """run：先失败再成功（同一输出目录），验证产物属于第二次运行

        场景：
        1. 第一次 run：无效输入（同组字段数不一致）→ 失败（return 1）
        2. 第二次 run：有效输入（examples/messages.jsonl）→ 成功（return 0）
        3. 验证：manifest.status=completed，predictions 行数 > 0，
           且 SHA 与第一次不同（属于第二次运行）
        """
        from semantic_detector.cli import main

        output_dir = tmp_path / "run_output"

        # 第一次 run：构造字段数不一致的无效输入（同 layout_id+direction 下字段数不同）
        invalid_input = tmp_path / "invalid.jsonl"
        invalid_records = [
            {"message_id": "1", "layout_id": "bad_group", "direction": "request",
             "payload_hex": "0102",
             "fields": [{"field_index": 0, "start": 0, "end": 1},
                        {"field_index": 1, "start": 1, "end": 2}]},
            {"message_id": "2", "layout_id": "bad_group", "direction": "request",
             "payload_hex": "010203",
             "fields": [{"field_index": 0, "start": 0, "end": 1},
                        {"field_index": 1, "start": 1, "end": 2},
                        {"field_index": 2, "start": 2, "end": 3}]},
        ]
        self._write_jsonl(invalid_input, invalid_records)

        rc1 = main(["run", str(invalid_input), "--output-dir", str(output_dir)])
        assert rc1 != 0, "第一次 run 应失败（字段数不一致，fail closed）"

        # 记录第一次运行后的产物 SHA（失败的 run 也会写 manifest/predictions 空文件）
        manifest_path = output_dir / "manifest.json"
        predictions_path = output_dir / "predictions.jsonl"
        first_manifest_sha = self._file_sha256(manifest_path)
        first_predictions_sha = self._file_sha256(predictions_path)

        # 验证第一次 manifest status 不是 completed
        if manifest_path.exists():
            first_manifest = self._read_json(manifest_path)
            assert first_manifest.get("status") != "completed"

        # 第二次 run：有效输入
        messages_path = Path("examples/messages.jsonl")
        if not messages_path.exists():
            pytest.skip("examples/messages.jsonl not found")

        rc2 = main(["run", str(messages_path), "--output-dir", str(output_dir)])
        assert rc2 == 0, "第二次 run 应成功"

        # 验证第二次产物属于第二次运行
        second_manifest = self._read_json(manifest_path)
        assert second_manifest.get("status") == "completed"

        # predictions.jsonl 行数 > 0（第二次有预测）
        second_predictions_lines = self._count_lines(predictions_path)
        assert second_predictions_lines > 0, "第二次 run 应有预测结果"

        # manifest SHA 应改变（第二次覆盖了第一次）
        second_manifest_sha = self._file_sha256(manifest_path)
        if first_manifest_sha is not None:
            assert second_manifest_sha != first_manifest_sha, (
                "manifest.json 应被第二次运行覆盖（SHA 改变）"
            )

        # predictions SHA 应改变（第一次为空文件，第二次有内容）
        second_predictions_sha = self._file_sha256(predictions_path)
        if first_predictions_sha is not None:
            assert second_predictions_sha != first_predictions_sha, (
                "predictions.jsonl 应被第二次运行覆盖（SHA 改变）"
            )

    def test_evaluate_errors_then_no_errors_artifacts_belong_to_second_run(self, tmp_path):
        """evaluate：先有错误再无错误（同一输出目录），验证产物属于第二次运行

        场景：
        1. 第一次 evaluate：predictions 与 ground_truth 标签不匹配 → errors.jsonl 有内容
        2. 第二次 evaluate：predictions 与 ground_truth 标签完全匹配 → errors.jsonl 为空
        3. 验证：errors.jsonl 为空文件（0 行），metrics.json error_count=0，
           且 SHA 与第一次不同（属于第二次运行）
        """
        from semantic_detector.cli import main

        output_dir = tmp_path / "eval_output"
        output_dir.mkdir(parents=True, exist_ok=True)

        # 构造 predictions（1 条预测，coarse_label="length"）
        predictions_path = output_dir / "predictions.jsonl"
        pred_record = {
            "run_id": "test-run-352",
            "layout_id": "test_layout",
            "direction": "request",
            "field_index": 0,
            "coarse_label": "length",
            "fine_label": "total_message_length",
            "confidence": 1.0,
            "abstained": False,
            "prediction_status": "confirmed",
            "evidence": [],
            "alternatives": [],
        }
        self._write_jsonl(predictions_path, [pred_record])

        # 第一次 evaluate：ground_truth 标签不匹配（semantic_label="constant"）
        gt_bad_path = tmp_path / "gt_bad.jsonl"
        gt_bad_record = {
            "truth_id": 1,
            "layout_id": "test_layout",
            "direction": "request",
            "field_index": 0,
            "semantic_label": "constant",
            "fine_label": "constant_value",
            "confidence": 1.0,
            "is_hard_evidence": True,
        }
        self._write_jsonl(gt_bad_path, [gt_bad_record])

        rc1 = main(["evaluate", str(predictions_path), str(gt_bad_path)])
        assert rc1 == 0, "第一次 evaluate 应成功（有错误但 evaluate 本身返回 0）"

        # 验证第一次有错误
        errors_path = output_dir / "errors.jsonl"
        first_errors_lines = self._count_lines(errors_path)
        assert first_errors_lines > 0, "第一次 evaluate 应有错误（标签不匹配）"

        first_errors_sha = self._file_sha256(errors_path)
        first_metrics_sha = self._file_sha256(output_dir / "metrics.json")

        # 第二次 evaluate：ground_truth 标签匹配（semantic_label="length"）
        gt_good_path = tmp_path / "gt_good.jsonl"
        gt_good_record = {
            "truth_id": 1,
            "layout_id": "test_layout",
            "direction": "request",
            "field_index": 0,
            "semantic_label": "length",
            "fine_label": "total_message_length",
            "confidence": 1.0,
            "is_hard_evidence": True,
        }
        self._write_jsonl(gt_good_path, [gt_good_record])

        rc2 = main(["evaluate", str(predictions_path), str(gt_good_path)])
        assert rc2 == 0, "第二次 evaluate 应成功"

        # 验证第二次 errors.jsonl 为空文件（0 行）
        second_errors_lines = self._count_lines(errors_path)
        assert second_errors_lines == 0, "第二次 evaluate 应无错误（errors.jsonl 为空）"

        # 验证 errors.jsonl SHA 改变（第一次有内容，第二次空文件）
        second_errors_sha = self._file_sha256(errors_path)
        assert second_errors_sha != first_errors_sha, (
            "errors.jsonl 应被第二次运行覆盖（SHA 改变）"
        )

        # 验证 metrics.json error_count=0
        second_metrics = self._read_json(output_dir / "metrics.json")
        assert second_metrics.get("counts", {}).get("error_count") == 0, (
            "第二次 evaluate 的 metrics error_count 应为 0"
        )

        # 验证 metrics.json SHA 改变
        second_metrics_sha = self._file_sha256(output_dir / "metrics.json")
        assert second_metrics_sha != first_metrics_sha, (
            "metrics.json 应被第二次运行覆盖（SHA 改变）"
        )

    def test_infer_predictions_then_empty_artifacts_belong_to_second_run(self, tmp_path):
        """infer：先有预测再空预测（同一输出目录），验证产物属于第二次运行

        场景：
        1. 先运行 profile 命令在 tmp_path 内生成 field_profiles.jsonl
        2. 第一次 infer：输入有 profiles → predictions.jsonl 有内容
        3. 第二次 infer：输入空 profiles 文件 → predictions.jsonl 为空
        4. 验证：predictions.jsonl 为空文件（0 行），且 SHA 与第一次不同

        R426：不再依赖 examples/output/field_profiles.jsonl（发布包排除该目录导致条件 skip），
        改为在 tmp_path 内自行运行 profile 命令生成 profiles。
        """
        from semantic_detector.cli import main

        messages_path = Path("examples/messages.jsonl")
        if not messages_path.exists():
            pytest.skip("examples/messages.jsonl not found")
        config_path = Path("examples/config.json")

        # 步骤 1：在 tmp_path 内运行 profile 命令生成 field_profiles.jsonl
        profile_dir = tmp_path / "profile_output"
        profile_dir.mkdir(parents=True, exist_ok=True)
        profile_args = ["profile", str(messages_path), "--output-dir", str(profile_dir)]
        if config_path.exists():
            profile_args.extend(["--config", str(config_path)])
        rc_profile = main(profile_args)
        assert rc_profile == 0, "profile 命令应成功"

        profiles_path = profile_dir / "field_profiles.jsonl"
        assert profiles_path.exists(), "profile 命令应生成 field_profiles.jsonl"
        assert profiles_path.stat().st_size > 0, "field_profiles.jsonl 不应为空"

        # 步骤 2：第一次 infer 使用生成的 profiles
        output_dir = tmp_path / "infer_output"
        output_dir.mkdir(parents=True, exist_ok=True)

        rc1 = main(["infer", str(profiles_path), "--output-dir", str(output_dir)])
        assert rc1 == 0, "第一次 infer 应成功"

        predictions_path = output_dir / "predictions.jsonl"
        first_predictions_lines = self._count_lines(predictions_path)
        assert first_predictions_lines > 0, "第一次 infer 应有预测结果"

        first_predictions_sha = self._file_sha256(predictions_path)

        # 步骤 3：第二次 infer：输入空 profiles 文件
        empty_profiles_path = tmp_path / "empty_profiles.jsonl"
        empty_profiles_path.write_text("", encoding="utf-8")

        rc2 = main(["infer", str(empty_profiles_path), "--output-dir", str(output_dir)])
        assert rc2 == 0, "第二次 infer 应成功（空 profiles → 空预测）"

        # 验证第二次 predictions.jsonl 为空文件（0 行）
        second_predictions_lines = self._count_lines(predictions_path)
        assert second_predictions_lines == 0, (
            "第二次 infer 应无预测结果（predictions.jsonl 为空文件）"
        )

        # 验证 predictions.jsonl SHA 改变（第一次有内容，第二次空文件）
        second_predictions_sha = self._file_sha256(predictions_path)
        assert second_predictions_sha != first_predictions_sha, (
            "predictions.jsonl 应被第二次运行覆盖（SHA 改变）"
        )
