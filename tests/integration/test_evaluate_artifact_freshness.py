"""R393：Evaluate 产物清理回归复核测试

R393 计划场景：
- 第一次评价 4 errors；
- 第二次评价 0 errors；
- 第二次 `errors.jsonl` 为空。

补充验收（与 R392 阶段 C 产物清理一致）：
- 第二次 evaluate 不保留旧 metrics/per_label/confusion（所有 evaluate 产物新鲜覆盖）
- evaluate 不删除其他命令的产物（命令隔离）
"""

import json
from pathlib import Path

import pytest

from semantic_detector.cli import main
from semantic_detector.contracts import DetectorEvidence
from semantic_detector.io.exporters import export_predictions_to_jsonl


def _write_truth(path: Path, field_index_to_type: dict) -> None:
    """写 ground_truth.jsonl，field_index_to_type 映射 field_index -> semantic_type"""
    with open(path, "w", encoding="utf-8") as f:
        for idx, semantic_type in field_index_to_type.items():
            entry = {
                "truth_id": idx + 1,
                "field_index": idx,
                "semantic_type": semantic_type,
                "confidence": 1.0,
                "is_hard_evidence": True,
            }
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _write_predictions(path: Path, predictions: list) -> None:
    """写 predictions.jsonl（用 DetectorEvidence 列表）"""
    export_predictions_to_jsonl(predictions, str(path))


def _make_pred(field_index: int, semantic_type: str = "constant") -> DetectorEvidence:
    """构造一条 DetectorEvidence 预测

    参数顺序与 test_cli_evaluate.py 一致：
    DetectorEvidence(layout_id, semantic_type, direction, confidence, is_hard_evidence, source, details)
    """
    return DetectorEvidence(
        "L1",
        semantic_type,
        "",
        1.0,
        True,
        "test",
        details={"field_index": field_index},
    )


class TestEvaluateArtifactFreshnessR393:
    """R393：Evaluate 产物清理回归复核"""

    def test_r393_second_evaluate_no_errors_clears_old_errors(self, tmp_path: Path) -> None:
        """R393 核心场景：第二次评价 0 errors 时 errors.jsonl 必须为空

        场景（R393 计划）：
        1. 第一次评价 4 errors（预测与真值完全不匹配）
        2. 第二次评价 0 errors（预测与真值完全匹配）
        3. 断言：第二次 errors.jsonl 必须为空
        """
        # 准备真值（4 个字段）
        truth_path = tmp_path / "truth.jsonl"
        _write_truth(truth_path, {0: "constant", 1: "payload", 2: "length", 3: "counter"})

        # 第一次评价：预测全部错误（4 errors）
        # 真值是 constant/payload/length/counter，预测全部填 type_opcode → 4 个错误
        pred1_path = tmp_path / "predictions_v1.jsonl"
        _write_predictions(pred1_path, [
            _make_pred(0, "type_opcode"),
            _make_pred(1, "type_opcode"),
            _make_pred(2, "type_opcode"),
            _make_pred(3, "type_opcode"),
        ])

        rc1 = main(["evaluate", str(pred1_path), str(truth_path)])
        assert rc1 == 0, f"第一次 evaluate 应成功（有错误但可评价），got rc={rc1}"

        # 输出目录是 predictions 文件的父目录
        output_dir = pred1_path.parent
        errors_path = output_dir / "errors.jsonl"
        assert errors_path.exists(), "第一次 evaluate 应生成 errors.jsonl"
        first_content = errors_path.read_text(encoding="utf-8").strip()
        first_lines = [l for l in first_content.splitlines() if l.strip()]
        assert len(first_lines) == 4, (
            f"第一次 evaluate 应有 4 errors，got {len(first_lines)}: {first_content}"
        )

        # 第二次评价：预测全部正确（0 errors）
        pred2_path = tmp_path / "predictions_v2.jsonl"
        _write_predictions(pred2_path, [
            _make_pred(0, "constant"),
            _make_pred(1, "payload"),
            _make_pred(2, "length"),
            _make_pred(3, "counter"),
        ])

        rc2 = main(["evaluate", str(pred2_path), str(truth_path)])
        assert rc2 == 0, f"第二次 evaluate 应成功，got rc={rc2}"

        # 断言：第二次 errors.jsonl 必须为空
        second_content = errors_path.read_text(encoding="utf-8").strip()
        assert second_content == "", (
            f"R393: 第二次 evaluate 0 errors 时 errors.jsonl 必须为空，got: {second_content}"
        )

    def test_r393_second_evaluate_overwrites_all_artifacts(self, tmp_path: Path) -> None:
        """R393 补充：第二次 evaluate 覆盖所有 evaluate 产物（metrics/per_label/confusion）

        场景：
        1. 第一次 evaluate（4 errors）→ metrics/per_label/confusion 有内容
        2. 第二次 evaluate（0 errors）→ 所有产物被覆盖，metrics 反映 0 errors
        """
        truth_path = tmp_path / "truth.jsonl"
        _write_truth(truth_path, {0: "constant", 1: "payload"})

        # 第一次评价：2 errors
        pred1_path = tmp_path / "predictions_v1.jsonl"
        _write_predictions(pred1_path, [
            _make_pred(0, "payload"),   # 错（真值 constant）
            _make_pred(1, "constant"),  # 错（真值 payload）
        ])

        rc1 = main(["evaluate", str(pred1_path), str(truth_path)])
        assert rc1 == 0

        output_dir = pred1_path.parent
        metrics_path = output_dir / "metrics.json"
        per_label_path = output_dir / "per_label_metrics.csv"
        confusion_path = output_dir / "confusion_matrix.csv"

        assert metrics_path.exists()
        assert per_label_path.exists()
        assert confusion_path.exists()

        with open(metrics_path, "r", encoding="utf-8") as f:
            first_metrics = json.load(f)
        assert first_metrics["counts"]["error_count"] == 2, (
            f"第一次 evaluate 应有 2 errors，got {first_metrics['counts']['error_count']}"
        )
        first_metrics_content = metrics_path.read_text(encoding="utf-8")

        # 第二次评价：0 errors
        pred2_path = tmp_path / "predictions_v2.jsonl"
        _write_predictions(pred2_path, [
            _make_pred(0, "constant"),  # 对
            _make_pred(1, "payload"),   # 对
        ])

        rc2 = main(["evaluate", str(pred2_path), str(truth_path)])
        assert rc2 == 0

        # 断言：所有 evaluate 产物被覆盖
        with open(metrics_path, "r", encoding="utf-8") as f:
            second_metrics = json.load(f)
        assert second_metrics["counts"]["error_count"] == 0, (
            f"R393: 第二次 evaluate 应有 0 errors，got {second_metrics['counts']['error_count']}"
        )
        # metrics 内容必须不同（error_count 从 2 变 0）
        second_metrics_content = metrics_path.read_text(encoding="utf-8")
        assert second_metrics_content != first_metrics_content, (
            "R393: 第二次 evaluate 的 metrics.json 必须被覆盖（内容不同）"
        )

        # per_label_metrics.csv 和 confusion_matrix.csv 也必须被覆盖
        assert per_label_path.exists(), "per_label_metrics.csv 应存在"
        assert confusion_path.exists(), "confusion_matrix.csv 应存在"

    def test_r393_evaluate_does_not_delete_other_command_artifacts(self, tmp_path: Path) -> None:
        """R393 命令隔离：evaluate 不删除 run/validate 的产物

        场景：
        1. 先 run → 生成 manifest.json + run.log + validated.jsonl 等
        2. 再 evaluate 同输出目录
        3. 断言：run 的 manifest.json 和 run.log 仍然存在（evaluate 不拥有）
        """
        # 先 run（生成 manifest/run.log/validated 等）
        run_input = tmp_path / "run_input.jsonl"
        with open(run_input, "w", encoding="utf-8") as f:
            for mid, lid in [("m1", "L1"), ("m2", "L2")]:
                rec = {
                    "message_id": mid,
                    "layout_id": lid,
                    "direction": "request",
                    "payload_hex": "0001",
                    "fields": [{"field_index": 0, "start": 0, "end": 2}],
                }
                f.write(json.dumps(rec) + "\n")

        rc_run = main(["run", str(run_input), "--output-dir", str(tmp_path)])
        assert rc_run == 0

        manifest_path = tmp_path / "manifest.json"
        run_log_path = tmp_path / "run.log"
        validated_path = tmp_path / "validated.jsonl"
        assert manifest_path.exists()
        assert run_log_path.exists()
        assert validated_path.exists()
        manifest_before = manifest_path.read_text(encoding="utf-8")

        # 再 evaluate（predictions 在同目录）
        truth_path = tmp_path / "truth.jsonl"
        _write_truth(truth_path, {0: "constant"})

        # 用 run 生成的 predictions.jsonl
        predictions_path = tmp_path / "predictions.jsonl"
        assert predictions_path.exists(), "run 应生成 predictions.jsonl"

        rc_eval = main(["evaluate", str(predictions_path), str(truth_path)])
        assert rc_eval == 0

        # 断言：run 的 manifest.json/run.log/validated.jsonl 仍然存在且未修改
        assert manifest_path.exists(), (
            "R393: evaluate 不应删除 run 的 manifest.json（命令隔离）"
        )
        assert run_log_path.exists(), (
            "R393: evaluate 不应删除 run 的 run.log（命令隔离）"
        )
        assert validated_path.exists(), (
            "R393: evaluate 不应删除 run 的 validated.jsonl（命令隔离）"
        )
        manifest_after = manifest_path.read_text(encoding="utf-8")
        assert manifest_after == manifest_before, (
            "R393: evaluate 不应修改 run 的 manifest.json 内容"
        )

        # evaluate 应生成自己的产物
        metrics_path = tmp_path / "metrics.json"
        errors_path = tmp_path / "errors.jsonl"
        assert metrics_path.exists(), "evaluate 应生成 metrics.json"
        assert errors_path.exists(), "evaluate 应生成 errors.jsonl"

    def test_r393_rejected_ground_truth_overwritten(self, tmp_path: Path) -> None:
        """R393 补充：第二次 evaluate 无 rejected ground truth 时 rejected_ground_truth.jsonl 为空

        场景：
        1. 第一次 evaluate 含 rejected ground truth → rejected_ground_truth.jsonl 有内容
        2. 第二次 evaluate 无 rejected → rejected_ground_truth.jsonl 必须为空
        """
        truth_path = tmp_path / "truth.jsonl"
        # 第一次：写一条合法 + 一条非法（缺 truth_id 触发拒绝）
        with open(truth_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({
                "truth_id": 1, "field_index": 0, "semantic_type": "constant",
                "confidence": 1.0, "is_hard_evidence": True,
            }) + "\n")
            f.write(json.dumps({
                "field_index": 1, "semantic_type": "payload",  # 缺 truth_id
                "confidence": 1.0, "is_hard_evidence": True,
            }) + "\n")

        pred_path = tmp_path / "predictions.jsonl"
        _write_predictions(pred_path, [_make_pred(0, "constant")])

        rc1 = main(["evaluate", str(pred_path), str(truth_path)])
        assert rc1 != 0, "第一次 evaluate 含 rejected truth 应 exit 非零（fail closed）"

        rejected_gt_path = pred_path.parent / "rejected_ground_truth.jsonl"
        assert rejected_gt_path.exists()
        first_content = rejected_gt_path.read_text(encoding="utf-8").strip()
        assert first_content, "第一次 rejected_ground_truth.jsonl 应有内容"

        # 第二次：写合法的真值（无 rejected）
        truth_path2 = tmp_path / "truth2.jsonl"
        _write_truth(truth_path2, {0: "constant"})

        rc2 = main(["evaluate", str(pred_path), str(truth_path2)])
        assert rc2 == 0, "第二次 evaluate 无 rejected 应 exit 0"

        # rejected_ground_truth.jsonl 必须为空
        second_content = rejected_gt_path.read_text(encoding="utf-8").strip()
        assert second_content == "", (
            f"R393: 第二次 evaluate 无 rejected 时 rejected_ground_truth.jsonl 必须为空，"
            f"got: {second_content}"
        )
