"""R395：非法 direction 的 Prediction 导入失败测试

复现 HIGH-5：predictions 中 `direction=foo` 被静默转成 unknown 的问题。

R395 计划要求（修复前测试应真实失败，本轮不修改生产代码）：
- 非法 direction 必须进入 rejection
- 不构造 SemanticPrediction
- 不参与评价
- 不自动降级为 unknown

R397 修复后行为：
- read_semantic_predictions_from_jsonl 对非法 direction 抛 ValueError
- 不再降级为 Direction.UNKNOWN
- 合法 direction（request/response/unknown）仍被接受

本测试验证：非法 direction 被严格拒绝（抛 ValueError），合法 direction 被接受。
"""

import json
from pathlib import Path

import pytest

from semantic_detector.io.exporters import read_semantic_predictions_from_jsonl
from semantic_detector.contracts import Direction, SemanticPrediction


def _write_prediction_line(path: Path, direction_value: str) -> None:
    """写一行 SemanticPrediction 格式的 JSONL，direction 用指定值"""
    pred_dict = {
        "run_id": "r1",
        "layout_id": "L1",
        "direction": direction_value,
        "field_index": 0,
        "coarse_label": "constant",
        "fine_label": "constant",
        "confidence": 1.0,
        "abstained": False,
        "evidence": [
            {
                "detector": "constant",
                "coarse_label": "constant",
                "fine_label": "constant",
                "is_hard_evidence": True,
                "score": 1.0,
                "reason_code": "constant",
                "details": {"field_index": 0},
            }
        ],
        "alternatives": [],
    }
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(pred_dict, ensure_ascii=False) + "\n")


class TestPredictionImportDirectionR395:
    """R395：非法 direction 的 Prediction 导入失败测试

    R397 修复后：read_semantic_predictions_from_jsonl 对非法 direction 抛 ValueError。
    """

    def test_r395_direction_foo_must_be_rejected(self, tmp_path: Path) -> None:
        """R395/R397: direction=foo 必须被拒绝，抛 ValueError

        修复前缺陷：read_semantic_predictions_from_jsonl 把 "foo" 降级为 Direction.UNKNOWN，
        返回一个 direction=UNKNOWN 的 SemanticPrediction，不拒绝。

        R397 修复后：direction=foo 抛 ValueError，不构造 SemanticPrediction。
        """
        pred_path = tmp_path / "predictions.jsonl"
        _write_prediction_line(pred_path, "foo")

        with pytest.raises(ValueError, match="Invalid direction"):
            read_semantic_predictions_from_jsonl(pred_path)

    def test_r395_direction_bar_must_be_rejected(self, tmp_path: Path) -> None:
        """R395/R397: direction=bar 必须被拒绝，抛 ValueError

        同 test_r395_direction_foo_must_be_rejected，验证另一个非法值。
        """
        pred_path = tmp_path / "predictions.jsonl"
        _write_prediction_line(pred_path, "bar")

        with pytest.raises(ValueError, match="Invalid direction"):
            read_semantic_predictions_from_jsonl(pred_path)

    def test_r395_direction_foo_not_silently_downgraded_to_unknown(self, tmp_path: Path) -> None:
        """R395/R397: direction=foo 不应被静默降级为 unknown（核心断言）

        修复前缺陷：read_semantic_predictions_from_jsonl 把 "foo" 降级为 Direction.UNKNOWN。

        R397 修复后：direction=foo 抛 ValueError，不会产生 direction=UNKNOWN 的 prediction。
        """
        pred_path = tmp_path / "predictions.jsonl"
        _write_prediction_line(pred_path, "foo")

        # R397 断言：非法 direction 应抛 ValueError，不会返回任何 prediction
        with pytest.raises(ValueError, match="Invalid direction"):
            read_semantic_predictions_from_jsonl(pred_path)

    def test_r395_valid_directions_still_accepted(self, tmp_path: Path) -> None:
        """R395 正向对照：合法 direction 仍被接受

        验证修复后不会误伤合法 direction（request/response/unknown）。
        """
        for valid_dir in ["request", "response", "unknown"]:
            pred_path = tmp_path / f"pred_{valid_dir}.jsonl"
            _write_prediction_line(pred_path, valid_dir)

            predictions = read_semantic_predictions_from_jsonl(pred_path)
            assert len(predictions) == 1, (
                f"R395 正向对照：direction={valid_dir} 应被接受，"
                f"got {len(predictions)} predictions"
            )
            assert predictions[0].direction == Direction(valid_dir), (
                f"R395 正向对照：direction={valid_dir} 应保持原值，"
                f"got {predictions[0].direction}"
            )

    def test_r395_mixed_valid_and_invalid_direction(self, tmp_path: Path) -> None:
        """R395/R397: 混合合法+非法 direction 时，非法的必须被拒绝

        场景：同一文件含 1 条合法（request）+ 1 条非法（foo）

        R397 修复后：遇到非法 direction 抛 ValueError，整个读取失败
        （read_semantic_predictions_from_jsonl 签名不支持部分拒绝，严格拒绝更安全）。
        """
        pred_path = tmp_path / "predictions.jsonl"
        with open(pred_path, "w", encoding="utf-8") as f:
            # 合法 direction
            valid_pred = {
                "run_id": "r1", "layout_id": "L1", "direction": "request",
                "field_index": 0, "coarse_label": "constant",
                "fine_label": "constant", "confidence": 1.0,
                "abstained": False,
                "evidence": [{
                    "detector": "constant", "coarse_label": "constant",
                    "fine_label": "constant", "is_hard_evidence": True,
                    "score": 1.0, "reason_code": "constant",
                    "details": {"field_index": 0},
                }],
                "alternatives": [],
            }
            # 非法 direction
            invalid_pred = {
                "run_id": "r1", "layout_id": "L1", "direction": "foo",
                "field_index": 1, "coarse_label": "payload",
                "fine_label": "payload", "confidence": 1.0,
                "abstained": False,
                "evidence": [{
                    "detector": "payload", "coarse_label": "payload",
                    "fine_label": "payload", "is_hard_evidence": True,
                    "score": 1.0, "reason_code": "payload",
                    "details": {"field_index": 1},
                }],
                "alternatives": [],
            }
            f.write(json.dumps(valid_pred, ensure_ascii=False) + "\n")
            f.write(json.dumps(invalid_pred, ensure_ascii=False) + "\n")

        # R397 断言：遇到非法 direction 抛 ValueError，不静默接受
        with pytest.raises(ValueError, match="Invalid direction"):
            read_semantic_predictions_from_jsonl(pred_path)
