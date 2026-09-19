"""测试 infer 子命令参数解析

验证 infer 子命令的参数解析功能。
R245：新增完整 SemanticPrediction 导出验证（predictions 不再缺 FieldKey）。
"""

import json
import pytest
import tempfile
import os
from pathlib import Path
from semantic_detector.cli import main


class TestCliInfer:
    """infer 子命令测试"""
    
    def test_infer_missing_input_file(self):
        """测试缺少输入文件参数"""
        with pytest.raises(SystemExit) as exc_info:
            main(['infer'])
        assert exc_info.value.code == 2
    
    def test_infer_nonexistent_file(self):
        """测试不存在的文件"""
        exit_code = main(['infer', 'nonexistent_file.jsonl'])
        assert exit_code == 2
    
    def test_infer_valid_file(self):
        """测试合法文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "field_profiles.jsonl"
            input_path.write_text(
                '{"layout_id": "L1", "direction": "request", "field_index": 0, "sample_count": 10, "width_min": 4, "width_max": 4, "width_mode": 4, "fixed_width": true, "dominant_value_ratio": 1.0}\n',
                encoding='utf-8'
            )
            
            exit_code = main(['infer', str(input_path)])
            assert exit_code == 0
            
            # 检查输出文件
            predictions_path = Path(tmpdir) / "predictions.jsonl"
            assert predictions_path.exists()
    
    def test_infer_directory_not_file(self):
        """测试目录不是文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            exit_code = main(['infer', tmpdir])
            assert exit_code == 2
    
    def test_infer_with_output_dir(self):
        """测试带输出目录参数"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "field_profiles.jsonl"
            input_path.write_text(
                '{"layout_id": "L1", "direction": "request", "field_index": 0, "sample_count": 10, "width_min": 4, "width_max": 4, "width_mode": 4, "fixed_width": true, "dominant_value_ratio": 1.0}\n',
                encoding='utf-8'
            )
            
            output_dir = Path(tmpdir) / "output"
            exit_code = main(['infer', str(input_path), '--output-dir', str(output_dir)])
            assert exit_code == 0
            
            # 检查输出文件
            predictions_path = output_dir / "predictions.jsonl"
            assert predictions_path.exists()
    
    def test_infer_generates_predictions(self):
        """测试生成 predictions.jsonl"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "field_profiles.jsonl"
            input_path.write_text(
                '{"layout_id": "L1", "direction": "request", "field_index": 0, "sample_count": 10, "width_min": 4, "width_max": 4, "width_mode": 4, "fixed_width": true, "dominant_value_ratio": 1.0}\n',
                encoding='utf-8'
            )
            
            exit_code = main(['infer', str(input_path)])
            assert exit_code == 0
            
            # 检查输出文件
            predictions_path = Path(tmpdir) / "predictions.jsonl"
            assert predictions_path.exists()

            # 检查文件内容
            content = predictions_path.read_text(encoding='utf-8')
            assert len(content) > 0


class TestCliInferSemanticPredictionExport:
    """R245: infer CLI 使用完整预测导出验证

    03 教程 HIGH-3 / 04 任务表 R245：
    - profile fixture infer
    - predictions 不再缺 FieldKey（run_id/layout_id/direction/field_index）
    - 每行含完整身份和证据（prediction_status/evidence/alternatives）
    """

    def _write_profiles(self, tmpdir: str, profiles_data):
        """写入 field_profiles.jsonl fixture。"""
        input_path = Path(tmpdir) / "field_profiles.jsonl"
        lines = [json.dumps(p) for p in profiles_data]
        input_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return input_path

    def _read_predictions(self, tmpdir: str):
        """读取 predictions.jsonl 并解析为 dict 列表。"""
        predictions_path = Path(tmpdir) / "predictions.jsonl"
        assert predictions_path.exists()
        content = predictions_path.read_text(encoding="utf-8").strip()
        return [json.loads(line) for line in content.split("\n") if line.strip()]

    def test_infer_predictions_contain_fieldkey(self):
        """predictions.jsonl 每行含完整 FieldKey（run_id/layout/direction/index）。"""
        profiles = [
            {
                "layout_id": "L1", "direction": "request", "field_index": 0,
                "sample_count": 10, "width_min": 4, "width_max": 4,
                "width_mode": 4, "fixed_width": True, "dominant_value_ratio": 1.0,
            },
            {
                "layout_id": "L1", "direction": "request", "field_index": 1,
                "sample_count": 10, "width_min": 4, "width_max": 4,
                "width_mode": 4, "fixed_width": True, "dominant_value_ratio": 1.0,
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = self._write_profiles(tmpdir, profiles)
            exit_code = main(["infer", str(input_path)])
            assert exit_code == 0

            predictions = self._read_predictions(tmpdir)
            assert len(predictions) == 2

            for pred in predictions:
                # FieldKey 完整
                assert "run_id" in pred
                assert "layout_id" in pred
                assert "direction" in pred
                assert "field_index" in pred
                # 值非空
                assert pred["run_id"]
                assert pred["layout_id"]
                assert pred["direction"] in ("request", "response", "unknown")
                assert isinstance(pred["field_index"], int)

    def test_infer_predictions_contain_prediction_status(self):
        """predictions.jsonl 每行含 prediction_status。"""
        profiles = [
            {
                "layout_id": "L1", "direction": "request", "field_index": 0,
                "sample_count": 10, "width_min": 4, "width_max": 4,
                "width_mode": 4, "fixed_width": True, "dominant_value_ratio": 1.0,
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = self._write_profiles(tmpdir, profiles)
            exit_code = main(["infer", str(input_path)])
            assert exit_code == 0

            predictions = self._read_predictions(tmpdir)
            assert len(predictions) == 1

            pred = predictions[0]
            assert "prediction_status" in pred
            assert pred["prediction_status"] in ("confirmed", "candidate", "abstained")

    def test_infer_predictions_contain_evidence_and_alternatives(self):
        """predictions.jsonl 每行含 evidence 和 alternatives 字段。"""
        profiles = [
            {
                "layout_id": "L1", "direction": "request", "field_index": 0,
                "sample_count": 10, "width_min": 4, "width_max": 4,
                "width_mode": 4, "fixed_width": True, "dominant_value_ratio": 1.0,
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = self._write_profiles(tmpdir, profiles)
            exit_code = main(["infer", str(input_path)])
            assert exit_code == 0

            predictions = self._read_predictions(tmpdir)
            pred = predictions[0]

            assert "evidence" in pred
            assert "alternatives" in pred
            assert isinstance(pred["evidence"], list)
            assert isinstance(pred["alternatives"], list)
            # evidence 至少有 primary
            assert len(pred["evidence"]) >= 1

    def test_infer_predictions_fieldkey_matches_profile(self):
        """predictions FieldKey 与 profile 一一对应。"""
        profiles = [
            {
                "layout_id": "L1", "direction": "request", "field_index": 0,
                "sample_count": 10, "width_min": 4, "width_max": 4,
                "width_mode": 4, "fixed_width": True, "dominant_value_ratio": 1.0,
            },
            {
                "layout_id": "L2", "direction": "response", "field_index": 1,
                "sample_count": 10, "width_min": 4, "width_max": 4,
                "width_mode": 4, "fixed_width": True, "dominant_value_ratio": 1.0,
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = self._write_profiles(tmpdir, profiles)
            exit_code = main(["infer", str(input_path)])
            assert exit_code == 0

            predictions = self._read_predictions(tmpdir)
            assert len(predictions) == 2

            # FieldKey 一一对应
            assert predictions[0]["layout_id"] == "L1"
            assert predictions[0]["direction"] == "request"
            assert predictions[0]["field_index"] == 0

            assert predictions[1]["layout_id"] == "L2"
            assert predictions[1]["direction"] == "response"
            assert predictions[1]["field_index"] == 1

    def test_infer_predictions_shared_run_id(self):
        """同一次 infer 调用的所有 predictions 共享同一个 run_id。"""
        profiles = [
            {
                "layout_id": "L1", "direction": "request", "field_index": i,
                "sample_count": 10, "width_min": 4, "width_max": 4,
                "width_mode": 4, "fixed_width": True, "dominant_value_ratio": 1.0,
            }
            for i in range(3)
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = self._write_profiles(tmpdir, profiles)
            exit_code = main(["infer", str(input_path)])
            assert exit_code == 0

            predictions = self._read_predictions(tmpdir)
            assert len(predictions) == 3

            run_ids = {p["run_id"] for p in predictions}
            assert len(run_ids) == 1  # 共享同一个 run_id

    def test_infer_predictions_round_trip_readable(self):
        """predictions.jsonl 可被 read_semantic_predictions_from_jsonl 读回。"""
        from semantic_detector.io.exporters import read_semantic_predictions_from_jsonl
        from semantic_detector.contracts import SemanticPrediction

        profiles = [
            {
                "layout_id": "L1", "direction": "request", "field_index": 0,
                "sample_count": 10, "width_min": 4, "width_max": 4,
                "width_mode": 4, "fixed_width": True, "dominant_value_ratio": 1.0,
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = self._write_profiles(tmpdir, profiles)
            exit_code = main(["infer", str(input_path)])
            assert exit_code == 0

            predictions_path = Path(tmpdir) / "predictions.jsonl"
            read_back = read_semantic_predictions_from_jsonl(predictions_path)

            assert len(read_back) == 1
            assert isinstance(read_back[0], SemanticPrediction)
            assert read_back[0].layout_id == "L1"
            assert read_back[0].field_index == 0
