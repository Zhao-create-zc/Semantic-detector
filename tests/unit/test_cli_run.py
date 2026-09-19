"""R231: cmd_run 接入共享准备流程测试

修复 HIGH-2：run 命令对字段数不一致的组跳过（不送入 build_field_profiles），
为通过校验的组生成画像与预测，并导出 rejected_groups.jsonl；
manifest 的计数必须反映组级校验后的真实数量。
"""

import json as _json
import os
import tempfile
from pathlib import Path

from semantic_detector.cli import main


def _write_records(path, records):
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(_json.dumps(rec, ensure_ascii=False) + "\n")


def _two_field_record(msg_id, layout, direction, payload_hex="00010002", input_order=0):
    return {
        "message_id": msg_id,
        "layout_id": layout,
        "direction": direction,
        "payload_hex": payload_hex,
        "fields": [
            {"field_index": 0, "start": 0, "end": 2},
            {"field_index": 1, "start": 2, "end": 4},
        ],
        "input_order": input_order,
    }


class TestCliRunPrepareRecordsForProfiling:
    """R231: cmd_run 接入共享准备流程"""

    def test_run_inconsistent_group_excluded_from_validated_and_profiles(self):
        """不一致组不进 validated.jsonl，不进 field_profiles.jsonl。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.jsonl"
            _write_records(
                input_path,
                [
                    _two_field_record("m1", "L1", "request", "00010002", 0),
                    _two_field_record("m2", "L1", "request", "00030004", 1),
                    # L2 不一致：一条 2 字段，一条 3 字段
                    _two_field_record("m3", "L2", "request", "00050006", 2),
                    {
                        "message_id": "m4",
                        "layout_id": "L2",
                        "direction": "request",
                        "payload_hex": "000500060007",
                        "fields": [
                            {"field_index": 0, "start": 0, "end": 2},
                            {"field_index": 1, "start": 2, "end": 4},
                            {"field_index": 2, "start": 4, "end": 6},
                        ],
                        "input_order": 3,
                    },
                ],
            )

            exit_code = main(["run", str(input_path), "--output-dir", str(tmpdir), "--allow-partial-input"])
            # R345：有 rejection（L2 不一致）+ --allow-partial-input + 有有效消息 → exit 0 + partial_success
            assert exit_code == 0

            # validated.jsonl 只含 L1 的两条
            validated_path = Path(tmpdir) / "validated.jsonl"
            assert validated_path.exists()
            validated_ids = [
                _json.loads(line)["message_id"]
                for line in validated_path.read_text(encoding="utf-8").strip().splitlines()
                if line.strip()
            ]
            assert sorted(validated_ids) == ["m1", "m2"]

            # field_profiles.jsonl 只含 L1 的画像
            profiles_path = Path(tmpdir) / "field_profiles.jsonl"
            assert profiles_path.exists()
            profile_layouts = set()
            for line in profiles_path.read_text(encoding="utf-8").strip().splitlines():
                if line.strip():
                    profile_layouts.add(_json.loads(line)["layout_id"])
            assert profile_layouts == {"L1"}, f"不应包含被跳过的 L2，实际: {profile_layouts}"

            # rejected_groups.jsonl 记录 L2
            rejected_groups_path = Path(tmpdir) / "rejected_groups.jsonl"
            assert rejected_groups_path.exists()
            entry = _json.loads(
                rejected_groups_path.read_text(encoding="utf-8").strip().splitlines()[0]
            )
            assert entry["group_key"] == ["L2", "request"]
            assert entry["reason_code"] == "inconsistent_field_count"
            assert sorted(entry["rejected_message_ids"]) == ["m3", "m4"]

    def test_run_manifest_counts_reflect_group_validation(self):
        """manifest 的 validated_records/field_profiles/predictions 计数正确。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.jsonl"
            _write_records(
                input_path,
                [
                    _two_field_record("m1", "L1", "request", "00010002", 0),
                    _two_field_record("m2", "L1", "request", "00030004", 1),
                ],
            )

            exit_code = main(["run", str(input_path), "--output-dir", str(tmpdir)])
            assert exit_code == 0

            manifest_path = Path(tmpdir) / "manifest.json"
            assert manifest_path.exists()
            manifest = _json.loads(manifest_path.read_text(encoding="utf-8"))

            # 2 条记录 → 通过组级校验 → validated_records 反映画像数
            assert manifest["output"]["validated_records"] >= 1
            assert manifest["output"]["field_profiles"] == 2  # 2 字段 × 1 组
            assert manifest["output"]["predictions"] == 2
            # R344：无组级拒绝 → rejected_groups.jsonl 无条件写空文件（不再是不存在）
            rejected_groups_path = Path(tmpdir) / "rejected_groups.jsonl"
            assert rejected_groups_path.exists()
            assert rejected_groups_path.read_text(encoding="utf-8") == ""

    def test_run_all_inconsistent_still_exits_zero_with_empty_profiles(self):
        """全部组不一致 → 0 有效记录 → R344: exit 1，并导出 rejected_groups。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.jsonl"
            _write_records(
                input_path,
                [
                    {
                        "message_id": "m1",
                        "layout_id": "L1",
                        "direction": "request",
                        "payload_hex": "0001",
                        "fields": [{"field_index": 0, "start": 0, "end": 2}],
                        "input_order": 0,
                    },
                    _two_field_record("m2", "L1", "request", "00010002", 1),
                ],
            )

            exit_code = main(["run", str(input_path), "--output-dir", str(tmpdir)])
            # R344：0 有效记录 → fail closed (exit 1)
            assert exit_code == 1

            profiles_path = Path(tmpdir) / "field_profiles.jsonl"
            assert profiles_path.exists()
            assert profiles_path.read_text(encoding="utf-8").strip() == ""

            rejected_groups_path = Path(tmpdir) / "rejected_groups.jsonl"
            assert rejected_groups_path.exists()
            entry = _json.loads(
                rejected_groups_path.read_text(encoding="utf-8").strip().splitlines()[0]
            )
            assert entry["group_key"] == ["L1", "request"]

    def test_run_consistent_input_no_rejected_groups_file(self):
        """全一致输入 → R344: rejected_groups.jsonl 无条件写空文件，validated 含全部记录。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.jsonl"
            _write_records(
                input_path,
                [
                    _two_field_record("m1", "L1", "request", "00010002", 0),
                    _two_field_record("m2", "L1", "request", "00030004", 1),
                ],
            )

            exit_code = main(["run", str(input_path), "--output-dir", str(tmpdir)])
            assert exit_code == 0

            # R344：无组级拒绝 → rejected_groups.jsonl 无条件写空文件
            rejected_groups_path = Path(tmpdir) / "rejected_groups.jsonl"
            assert rejected_groups_path.exists()
            assert rejected_groups_path.read_text(encoding="utf-8") == ""

            validated_path = Path(tmpdir) / "validated.jsonl"
            validated_ids = [
                _json.loads(line)["message_id"]
                for line in validated_path.read_text(encoding="utf-8").strip().splitlines()
                if line.strip()
            ]
            assert sorted(validated_ids) == ["m1", "m2"]


class TestCliRunDifferentDirectionsDifferentFieldCounts:
    """R232: 不同方向字段数不同仍各自合法的 CLI 回归测试

    03 教程关键原则：组级字段数校验按 (layout_id, direction) 分组，
    request 2 字段、response 3 字段属于不同组，互不影响，都应合法保留。
    这是防止 R226 整组拒绝逻辑误伤跨方向合法输入的回归测试。
    """

    def test_request_2_fields_response_3_fields_both_valid(self):
        """同 layout 但 request 2 字段、response 3 字段 → 两个组都合法，全部保留。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.jsonl"
            _write_records(
                input_path,
                [
                    # request 组：2 字段
                    _two_field_record("req1", "L1", "request", "00010002", 0),
                    _two_field_record("req2", "L1", "request", "00030004", 1),
                    # response 组：3 字段
                    {
                        "message_id": "resp1",
                        "layout_id": "L1",
                        "direction": "response",
                        "payload_hex": "000100020003",
                        "fields": [
                            {"field_index": 0, "start": 0, "end": 2},
                            {"field_index": 1, "start": 2, "end": 4},
                            {"field_index": 2, "start": 4, "end": 6},
                        ],
                        "input_order": 2,
                    },
                    {
                        "message_id": "resp2",
                        "layout_id": "L1",
                        "direction": "response",
                        "payload_hex": "000400050006",
                        "fields": [
                            {"field_index": 0, "start": 0, "end": 2},
                            {"field_index": 1, "start": 2, "end": 4},
                            {"field_index": 2, "start": 4, "end": 6},
                        ],
                        "input_order": 3,
                    },
                ],
            )

            exit_code = main(["run", str(input_path), "--output-dir", str(tmpdir)])
            assert exit_code == 0

            # 两个组都合法 → 全部 4 条记录进 validated
            validated_path = Path(tmpdir) / "validated.jsonl"
            validated_ids = [
                _json.loads(line)["message_id"]
                for line in validated_path.read_text(encoding="utf-8").strip().splitlines()
                if line.strip()
            ]
            assert sorted(validated_ids) == ["req1", "req2", "resp1", "resp2"]

            # R344：无组级拒绝 → rejected_groups.jsonl 无条件写空文件
            rejected_groups_path = Path(tmpdir) / "rejected_groups.jsonl"
            assert rejected_groups_path.exists()
            assert rejected_groups_path.read_text(encoding="utf-8") == ""

            # field_profiles 应包含 5 个画像：request 2 + response 3
            profiles_path = Path(tmpdir) / "field_profiles.jsonl"
            assert profiles_path.exists()
            profile_lines = [
                line for line in profiles_path.read_text(encoding="utf-8").strip().splitlines()
                if line.strip()
            ]
            assert len(profile_lines) == 5

            # 按 (direction, field_index) 分组验证
            direction_field_pairs = set()
            for line in profile_lines:
                p = _json.loads(line)
                direction_field_pairs.add((p["direction"], p["field_index"]))
            assert direction_field_pairs == {
                ("request", 0),
                ("request", 1),
                ("response", 0),
                ("response", 1),
                ("response", 2),
            }

    def test_request_3_fields_response_2_fields_both_valid(self):
        """反向：request 3 字段、response 2 字段也各自合法。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.jsonl"
            _write_records(
                input_path,
                [
                    # request 组：3 字段
                    {
                        "message_id": "req1",
                        "layout_id": "L1",
                        "direction": "request",
                        "payload_hex": "000100020003",
                        "fields": [
                            {"field_index": 0, "start": 0, "end": 2},
                            {"field_index": 1, "start": 2, "end": 4},
                            {"field_index": 2, "start": 4, "end": 6},
                        ],
                        "input_order": 0,
                    },
                    # response 组：2 字段
                    _two_field_record("resp1", "L1", "response", "00010002", 1),
                    _two_field_record("resp2", "L1", "response", "00030004", 2),
                ],
            )

            exit_code = main(["run", str(input_path), "--output-dir", str(tmpdir)])
            assert exit_code == 0

            validated_path = Path(tmpdir) / "validated.jsonl"
            validated_ids = [
                _json.loads(line)["message_id"]
                for line in validated_path.read_text(encoding="utf-8").strip().splitlines()
                if line.strip()
            ]
            assert sorted(validated_ids) == ["req1", "resp1", "resp2"]
            # R344：无组级拒绝 → rejected_groups.jsonl 无条件写空文件
            rejected_groups_path = Path(tmpdir) / "rejected_groups.jsonl"
            assert rejected_groups_path.exists()
            assert rejected_groups_path.read_text(encoding="utf-8") == ""

    def test_one_direction_consistent_other_independent_independent(self):
        """request 组一致、response 组内部不一致 → 仅 response 整组拒绝。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.jsonl"
            _write_records(
                input_path,
                [
                    # request 组：2 字段，一致
                    _two_field_record("req1", "L1", "request", "00010002", 0),
                    _two_field_record("req2", "L1", "request", "00030004", 1),
                    # response 组：一条 2 字段，一条 3 字段，不一致
                    _two_field_record("resp1", "L1", "response", "00010002", 2),
                    {
                        "message_id": "resp2",
                        "layout_id": "L1",
                        "direction": "response",
                        "payload_hex": "000100020003",
                        "fields": [
                            {"field_index": 0, "start": 0, "end": 2},
                            {"field_index": 1, "start": 2, "end": 4},
                            {"field_index": 2, "start": 4, "end": 6},
                        ],
                        "input_order": 3,
                    },
                ],
            )

            exit_code = main(["run", str(input_path), "--output-dir", str(tmpdir), "--allow-partial-input"])
            # R345：有 rejection（response 组不一致）+ --allow-partial-input + 有有效消息 → exit 0 + partial_success
            assert exit_code == 0

            # request 组保留，response 组整组拒绝
            validated_path = Path(tmpdir) / "validated.jsonl"
            validated_ids = [
                _json.loads(line)["message_id"]
                for line in validated_path.read_text(encoding="utf-8").strip().splitlines()
                if line.strip()
            ]
            assert sorted(validated_ids) == ["req1", "req2"]

            rejected_groups_path = Path(tmpdir) / "rejected_groups.jsonl"
            assert rejected_groups_path.exists()
            entry = _json.loads(
                rejected_groups_path.read_text(encoding="utf-8").strip().splitlines()[0]
            )
            assert entry["group_key"] == ["L1", "response"]
            assert sorted(entry["rejected_message_ids"]) == ["resp1", "resp2"]


class TestCliRunSemanticPredictionManifest:
    """R246: run CLI 和 manifest 统计完整预测

    03 教程 HIGH-3 / 04 任务表 R246：
    - 完整 run
    - predictions 唯一（无重复 FieldKey）
    - manifest 数量一致（predictions == field_profiles == predictions.jsonl 行数）
    """

    def _run_with_two_field_records(self, tmpdir, records=None):
        """运行 run CLI 并返回 (manifest, predictions_dict_list)。"""
        if records is None:
            records = [
                _two_field_record("m1", "L1", "request", "00010002", 0),
                _two_field_record("m2", "L1", "request", "00030004", 1),
            ]
        input_path = Path(tmpdir) / "input.jsonl"
        _write_records(input_path, records)

        exit_code = main(["run", str(input_path), "--output-dir", str(tmpdir)])
        assert exit_code == 0

        manifest_path = Path(tmpdir) / "manifest.json"
        manifest = _json.loads(manifest_path.read_text(encoding="utf-8"))

        predictions_path = Path(tmpdir) / "predictions.jsonl"
        predictions = [
            _json.loads(line)
            for line in predictions_path.read_text(encoding="utf-8").strip().splitlines()
            if line.strip()
        ]
        return manifest, predictions

    def test_run_predictions_contain_complete_fieldkey(self):
        """run CLI predictions.jsonl 每行含完整 FieldKey。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            _, predictions = self._run_with_two_field_records(tmpdir)

            assert len(predictions) == 2
            for pred in predictions:
                assert "run_id" in pred
                assert "layout_id" in pred
                assert "direction" in pred
                assert "field_index" in pred
                assert pred["run_id"]
                assert pred["layout_id"]
                assert pred["direction"] in ("request", "response", "unknown")
                assert isinstance(pred["field_index"], int)

    def test_run_predictions_fieldkey_unique(self):
        """predictions 唯一：无重复 FieldKey（layout_id+direction+field_index）。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            _, predictions = self._run_with_two_field_records(tmpdir)

            fieldkeys = {
                (p["layout_id"], p["direction"], p["field_index"]) for p in predictions
            }
            assert len(fieldkeys) == len(predictions), "predictions 存在重复 FieldKey"

    def test_run_manifest_predictions_count_matches_jsonl(self):
        """manifest predictions 数量与 predictions.jsonl 行数一致。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest, predictions = self._run_with_two_field_records(tmpdir)

            assert manifest["output"]["predictions"] == len(predictions)

    def test_run_manifest_predictions_count_matches_field_profiles(self):
        """manifest predictions 数量与 field_profiles 数量一致。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest, _ = self._run_with_two_field_records(tmpdir)

            assert manifest["output"]["predictions"] == manifest["output"]["field_profiles"]

    def test_run_manifest_hard_soft_evidence_sum_matches_predictions(self):
        """manifest hard_evidence_count + soft_evidence_count == predictions 总数。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest, predictions = self._run_with_two_field_records(tmpdir)

            hard = manifest["summary"]["hard_evidence_count"]
            soft = manifest["summary"]["soft_evidence_count"]
            assert hard + soft == len(predictions)
            assert hard + soft == manifest["output"]["predictions"]

    def test_run_predictions_shared_run_id(self):
        """同一次 run 调用的所有 predictions 共享同一个 run_id。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            _, predictions = self._run_with_two_field_records(tmpdir)

            run_ids = {p["run_id"] for p in predictions}
            assert len(run_ids) == 1

    def test_run_predictions_round_trip_readable(self):
        """run CLI predictions.jsonl 可被 read_semantic_predictions_from_jsonl 读回。"""
        from semantic_detector.io.exporters import read_semantic_predictions_from_jsonl
        from semantic_detector.contracts import SemanticPrediction

        with tempfile.TemporaryDirectory() as tmpdir:
            _, _ = self._run_with_two_field_records(tmpdir)

            predictions_path = Path(tmpdir) / "predictions.jsonl"
            read_back = read_semantic_predictions_from_jsonl(predictions_path)

            assert len(read_back) == 2
            for p in read_back:
                assert isinstance(p, SemanticPrediction)
                assert p.run_id
                assert p.layout_id
                assert p.direction.value in ("request", "response", "unknown")

    def test_run_manifest_run_id_matches_predictions_run_id(self):
        """manifest run_id 与 predictions.jsonl 中 run_id 一致。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest, predictions = self._run_with_two_field_records(tmpdir)

            manifest_run_id = manifest["run_id"]
            for pred in predictions:
                assert pred["run_id"] == manifest_run_id


class TestCliRunAllInvalidInputR343:
    """R343：新增 Run 全无效输入失败测试（HIGH-4 Run 部分）

    精确复现：全部输入为无效 JSON
    → 0 valid
    → run exit 0（HIGH-4 缺陷）

    验收（复现，不修复生产代码）：
    - exit 非零（修复前失败：exit 0）
    - 不输出"完整成功"状态
    - manifest status 不是 completed
    - 仍生成诊断 rejected 和 log
    """

    def test_all_invalid_json_exits_nonzero(self):
        """R343: 全部输入为无效 JSON → run exit != 0

        复现 HIGH-4：cmd_run 第 490 行 return 0 无条件返回 0。
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "input.jsonl")
            # 全部无效 JSON
            with open(input_path, "w", encoding="utf-8") as f:
                f.write("{invalid json 1}\n")
                f.write("{invalid json 2}\n")

            output_dir = os.path.join(tmpdir, "output")
            exit_code = main(["run", input_path, "--output-dir", output_dir])
            assert exit_code != 0, (
                f"全部输入为无效 JSON 时 run 应返回非零退出码，实际: {exit_code}"
            )

    def test_all_invalid_json_no_completion_status(self):
        """R343: 全无效输入时不输出"流水线完成"状态"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "input.jsonl")
            with open(input_path, "w", encoding="utf-8") as f:
                f.write("{invalid json}\n")

            output_dir = os.path.join(tmpdir, "output")
            main(["run", input_path, "--output-dir", output_dir])

            log_path = os.path.join(output_dir, "run.log")
            assert os.path.exists(log_path), "run.log 应存在"
            with open(log_path, "r", encoding="utf-8") as f:
                log_content = f.read()
            assert "流水线完成" not in log_content, (
                f"全无效输入时不应输出'流水线完成'，run.log: {log_content}"
            )

    def test_all_invalid_json_manifest_status_not_completed(self):
        """R343: 全无效输入时 manifest status 不是 completed"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "input.jsonl")
            with open(input_path, "w", encoding="utf-8") as f:
                f.write("{invalid json}\n")

            output_dir = os.path.join(tmpdir, "output")
            main(["run", input_path, "--output-dir", output_dir])

            manifest_path = os.path.join(output_dir, "manifest.json")
            if os.path.exists(manifest_path):
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest = _json.load(f)
                assert manifest.get("status") != "completed", (
                    f"全无效输入时 manifest status 不应为 completed，实际: {manifest.get('status')}"
                )

    def test_all_invalid_json_still_generates_rejected_and_log(self):
        """R343: 全无效输入时仍生成诊断 rejected 和 log"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "input.jsonl")
            with open(input_path, "w", encoding="utf-8") as f:
                f.write("{invalid json}\n")

            output_dir = os.path.join(tmpdir, "output")
            main(["run", input_path, "--output-dir", output_dir])

            # rejected.jsonl 应存在且含 1 条拒绝
            rejected_path = os.path.join(output_dir, "rejected.jsonl")
            assert os.path.exists(rejected_path), "rejected.jsonl 应存在"
            with open(rejected_path, "r", encoding="utf-8") as f:
                lines = [line for line in f if line.strip()]
            assert len(lines) == 1, (
                f"rejected.jsonl 应有 1 行，实际: {len(lines)}"
            )

            # run.log 应存在
            log_path = os.path.join(output_dir, "run.log")
            assert os.path.exists(log_path), "run.log 应存在"


class TestCliRunNoValidRecordsR344:
    """R344：修复 Run 的 0 有效记录行为

    验收：
    - group_valid_records == 0 → status=no_valid_records
    - exit 1
    - predictions/profiles 写空文件（无残留）
    - rejected 保留真实错误
    - 不输出"流水线完成"
    - manifest 含 status=no_valid_records
    """

    def test_no_valid_records_manifest_status(self):
        """R344/R350: 0 有效记录时 manifest status=no_valid_records，使用统一 generate_manifest 结构"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "input.jsonl")
            with open(input_path, "w", encoding="utf-8") as f:
                f.write("{invalid json}\n")

            output_dir = os.path.join(tmpdir, "output")
            main(["run", input_path, "--output-dir", output_dir])

            manifest_path = os.path.join(output_dir, "manifest.json")
            assert os.path.exists(manifest_path)
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = _json.load(f)
            assert manifest["status"] == "no_valid_records", (
                f"status 应为 no_valid_records，实际: {manifest.get('status')}"
            )
            # R350：0 有效记录分支统一用 generate_manifest，字段在 output 子字典中
            assert manifest["output"]["validated_records"] == 0
            assert manifest["output"]["predictions"] == 0
            assert manifest["output"]["field_profiles"] == 0
            # R350：manifest 包含运行状态和退出信息
            assert manifest["exit_code"] == 1
            assert manifest["valid_for_reporting"] is False
            assert "started_at" in manifest
            assert "finished_at" in manifest
            assert "command_args" in manifest

    def test_no_valid_records_predictions_and_profiles_empty(self):
        """R344: 0 有效记录时 predictions.jsonl 和 field_profiles.jsonl 写空文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 预先写入旧文件（模拟残留）
            output_dir = os.path.join(tmpdir, "output")
            os.makedirs(output_dir)
            for fname in ["predictions.jsonl", "field_profiles.jsonl"]:
                with open(os.path.join(output_dir, fname), "w", encoding="utf-8") as f:
                    f.write("STALE CONTENT\n")

            input_path = os.path.join(tmpdir, "input.jsonl")
            with open(input_path, "w", encoding="utf-8") as f:
                f.write("{invalid json}\n")

            main(["run", input_path, "--output-dir", output_dir])

            # 两个文件应被重写为空
            pred_content = open(os.path.join(output_dir, "predictions.jsonl"), "r", encoding="utf-8").read()
            profile_content = open(os.path.join(output_dir, "field_profiles.jsonl"), "r", encoding="utf-8").read()
            assert pred_content == "", f"predictions.jsonl 应为空，实际: {pred_content!r}"
            assert profile_content == "", f"field_profiles.jsonl 应为空，实际: {profile_content!r}"

    def test_no_valid_records_rejected_preserved(self):
        """R344: 0 有效记录时 rejected.jsonl 保留真实错误"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "input.jsonl")
            with open(input_path, "w", encoding="utf-8") as f:
                f.write("{invalid json 1}\n")
                f.write("{invalid json 2}\n")

            output_dir = os.path.join(tmpdir, "output")
            exit_code = main(["run", input_path, "--output-dir", output_dir])
            assert exit_code == 1

            rejected_path = os.path.join(output_dir, "rejected.jsonl")
            with open(rejected_path, "r", encoding="utf-8") as f:
                lines = [line for line in f if line.strip()]
            assert len(lines) == 2, (
                f"rejected.jsonl 应有 2 行，实际: {len(lines)}"
            )

    def test_no_valid_records_no_completion_message(self):
        """R344: 0 有效记录时 run.log 不含'流水线完成'"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "input.jsonl")
            with open(input_path, "w", encoding="utf-8") as f:
                f.write("{invalid json}\n")

            output_dir = os.path.join(tmpdir, "output")
            main(["run", input_path, "--output-dir", output_dir])

            log_path = os.path.join(output_dir, "run.log")
            with open(log_path, "r", encoding="utf-8") as f:
                log_content = f.read()
            assert "流水线完成" not in log_content, (
                f"0 有效记录时不应输出'流水线完成'，run.log: {log_content}"
            )
            assert "无有效记录" in log_content, (
                f"应输出'无有效记录'错误，run.log: {log_content}"
            )

    def test_audit_fix_bug2_no_valid_records_with_user_config_manifest_correct(self):
        """审计修复 BUG-2: 0 有效记录 + --config 用户配置时 manifest config 审计字段应正确

        修复前：no_valid_records 分支 DetectionPipeline() 未传 config/config_source，
                manifest 的 resolved_config/config_source/config_sha256 反映默认配置而非用户配置。
        修复后：传入 config 和 config_source，manifest 审计字段与用户配置一致。
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "input.jsonl")
            with open(input_path, "w", encoding="utf-8") as f:
                f.write("{invalid json}\n")

            # 用户配置文件（type_opcode_min_dominant_ratio 改为 0.42，与默认 0.5 不同）
            user_config_path = os.path.join(tmpdir, "user_config.json")
            with open(user_config_path, "w", encoding="utf-8") as f:
                _json.dump({"type_opcode_min_dominant_ratio": 0.42}, f)

            output_dir = os.path.join(tmpdir, "output")
            main(["run", input_path, "--output-dir", output_dir,
                  "--config", user_config_path])

            manifest_path = os.path.join(output_dir, "manifest.json")
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = _json.load(f)

            # 修复后：config_source 应为用户配置路径，而非 "default"
            assert manifest["config"]["config_source"] == user_config_path, (
                f"BUG-2 回归：config_source 应为用户路径 {user_config_path}，"
                f"实际: {manifest['config']['config_source']}"
            )
            # 修复后：resolved_config 应反映用户配置值 0.42
            assert manifest["config"]["resolved_config"]["type_opcode_min_dominant_ratio"] == 0.42, (
                f"BUG-2 回归：resolved_config 应含用户值 0.42，"
                f"实际: {manifest['config']['resolved_config']['type_opcode_min_dominant_ratio']}"
            )


class TestCliRunPartialInputR345:
    """R345：定义部分有效输入的严格策略（--allow-partial-input）

    三态语义：
    - 无 rejection：status=completed, valid_for_reporting=true, exit 0
    - 有 rejection + 无 --allow-partial-input：status=invalid_input, valid_for_reporting=false, exit 1
    - 有 rejection + 有 --allow-partial-input 且有有效消息：status=partial_success, valid_for_reporting=false, exit 0
    """

    @staticmethod
    def _write_partial_input(input_path):
        """1 valid + 1 invalid JSON（部分有效输入）"""
        _write_records(
            input_path,
            [_two_field_record("m1", "L1", "request", "00010002", 0)],
        )
        with open(input_path, "a", encoding="utf-8") as f:
            f.write("{invalid json}\n")

    def test_default_fails_when_partial_rejection(self):
        """R345: 默认（无 --allow-partial-input）有 rejection → exit 1"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.jsonl"
            self._write_partial_input(input_path)

            exit_code = main(["run", str(input_path), "--output-dir", str(tmpdir)])
            assert exit_code == 1, (
                f"默认模式有 rejection 应返回 1，实际: {exit_code}"
            )

    def test_partial_mode_continues_with_valid_subset(self):
        """R345: --allow-partial-input + 有有效消息 → exit 0 + status=partial_success"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.jsonl"
            self._write_partial_input(input_path)

            exit_code = main([
                "run", str(input_path), "--output-dir", str(tmpdir),
                "--allow-partial-input",
            ])
            assert exit_code == 0, (
                f"partial 模式 + 有有效消息应返回 0，实际: {exit_code}"
            )

            manifest_path = Path(tmpdir) / "manifest.json"
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = _json.load(f)
            assert manifest["status"] == "partial_success", (
                f"status 应为 partial_success，实际: {manifest.get('status')}"
            )
            assert manifest["valid_for_reporting"] is False, (
                f"valid_for_reporting 应为 false，实际: {manifest.get('valid_for_reporting')}"
            )
            assert manifest.get("partial_input") is True, (
                f"partial_input 应为 true，实际: {manifest.get('partial_input')}"
            )

    def test_no_rejection_completed_status(self):
        """R345: 无 rejection → status=completed, valid_for_reporting=true, exit 0"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.jsonl"
            _write_records(
                input_path,
                [
                    _two_field_record("m1", "L1", "request", "00010002", 0),
                    _two_field_record("m2", "L1", "request", "00030004", 1),
                ],
            )

            exit_code = main(["run", str(input_path), "--output-dir", str(tmpdir)])
            assert exit_code == 0

            manifest_path = Path(tmpdir) / "manifest.json"
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = _json.load(f)
            assert manifest["status"] == "completed", (
                f"status 应为 completed，实际: {manifest.get('status')}"
            )
            assert manifest["valid_for_reporting"] is True, (
                f"valid_for_reporting 应为 true，实际: {manifest.get('valid_for_reporting')}"
            )


class TestCliRunRewriteAllOutputsR346:
    """R346：修复 Run 旧 rejected 产物残留

    验收：
    - run 1：坏输入 → rejected > 0
    - run 2：合法输入 → rejected = 0
    - 第二轮文件不得保留第一轮内容

    cmd_run 拥有的输出文件全部无条件重写（R344 已将 rejected/rejected_groups
    改为无条件写空文件）。R346 补充专属回归测试防止旧产物残留。
    """

    def test_rejected_cleared_on_second_run_with_valid_input(self):
        """R346: run 1 坏输入 → rejected > 0；run 2 合法输入 → rejected = 0"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "output"
            output_dir.mkdir()

            # run 1：坏输入（1 条 invalid JSON）→ rejected.jsonl 有 1 行，exit 1
            bad_input = Path(tmpdir) / "bad.jsonl"
            with open(bad_input, "w", encoding="utf-8") as f:
                f.write("{invalid json}\n")

            exit_code_1 = main(["run", str(bad_input), "--output-dir", str(output_dir)])
            assert exit_code_1 == 1, f"run 1 坏输入应 exit 1，实际: {exit_code_1}"

            rejected_path = output_dir / "rejected.jsonl"
            lines_1 = [
                line for line in rejected_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            assert len(lines_1) == 1, (
                f"run 1 后 rejected.jsonl 应有 1 行，实际: {len(lines_1)}"
            )

            # run 2：合法输入（同一输出目录）→ rejected.jsonl 空，exit 0
            good_input = Path(tmpdir) / "good.jsonl"
            _write_records(
                good_input,
                [
                    _two_field_record("m1", "L1", "request", "00010002", 0),
                    _two_field_record("m2", "L1", "request", "00030004", 1),
                ],
            )

            exit_code_2 = main(["run", str(good_input), "--output-dir", str(output_dir)])
            assert exit_code_2 == 0, f"run 2 合法输入应 exit 0，实际: {exit_code_2}"

            lines_2 = [
                line for line in rejected_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            assert lines_2 == [], (
                f"run 2 后 rejected.jsonl 应为空（不保留第一轮内容），实际: {lines_2}"
            )

    def test_rejected_groups_cleared_on_second_run_with_consistent_input(self):
        """R346: run 1 组级不一致 → rejected_groups > 0；run 2 一致输入 → rejected_groups = 0"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "output"
            output_dir.mkdir()

            # run 1：L1 组内字段数不一致（一条 2 字段，一条 3 字段）
            # 用 --allow-partial-input 让 run 1 继续（否则 R345 默认 fail closed）
            # 但 0 有效记录会 R344 fail closed；这里 L2 组一致保证有有效记录
            mismatch_input = Path(tmpdir) / "mismatch.jsonl"
            _write_records(
                mismatch_input,
                [
                    # L1 不一致组：m1 2 字段，m2 3 字段
                    _two_field_record("m1", "L1", "request", "00010002", 0),
                    {
                        "message_id": "m2",
                        "layout_id": "L1",
                        "direction": "request",
                        "payload_hex": "000100020003",
                        "fields": [
                            {"field_index": 0, "start": 0, "end": 2},
                            {"field_index": 1, "start": 2, "end": 4},
                            {"field_index": 2, "start": 4, "end": 6},
                        ],
                        "input_order": 1,
                    },
                    # L2 一致组：保证有有效记录
                    _two_field_record("m3", "L2", "request", "00050006", 2),
                    _two_field_record("m4", "L2", "request", "00070008", 3),
                ],
            )

            exit_code_1 = main([
                "run", str(mismatch_input), "--output-dir", str(output_dir),
                "--allow-partial-input",
            ])
            assert exit_code_1 == 0, (
                f"run 1 partial 模式应 exit 0，实际: {exit_code_1}"
            )

            rejected_groups_path = output_dir / "rejected_groups.jsonl"
            groups_1 = [
                line for line in rejected_groups_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            assert len(groups_1) == 1, (
                f"run 1 后 rejected_groups.jsonl 应有 1 行（L1 不一致），实际: {len(groups_1)}"
            )

            # run 2：全部一致输入（同一输出目录）→ rejected_groups.jsonl 空
            good_input = Path(tmpdir) / "good.jsonl"
            _write_records(
                good_input,
                [
                    _two_field_record("m1", "L1", "request", "00010002", 0),
                    _two_field_record("m2", "L1", "request", "00030004", 1),
                ],
            )

            exit_code_2 = main(["run", str(good_input), "--output-dir", str(output_dir)])
            assert exit_code_2 == 0, f"run 2 合法输入应 exit 0，实际: {exit_code_2}"

            groups_2 = [
                line for line in rejected_groups_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            assert groups_2 == [], (
                f"run 2 后 rejected_groups.jsonl 应为空（不保留第一轮内容），实际: {groups_2}"
            )

    def test_all_run_outputs_rewritten_no_stale_residue(self):
        """R346: run 1 坏输入产生旧产物；run 2 合法输入 → 全部文件重写无残留

        cmd_run 拥有的 5 个核心输出文件全部无条件重写：
        - validated.jsonl
        - rejected.jsonl
        - rejected_groups.jsonl
        - predictions.jsonl
        - field_profiles.jsonl
        - manifest.json
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "output"
            output_dir.mkdir()

            # run 1：坏输入 → rejected.jsonl 有 1 行，validated/predictions/profiles 空
            bad_input = Path(tmpdir) / "bad.jsonl"
            with open(bad_input, "w", encoding="utf-8") as f:
                f.write("{invalid json}\n")

            main(["run", str(bad_input), "--output-dir", str(output_dir)])

            rejected_path = output_dir / "rejected.jsonl"
            assert len([
                line for line in rejected_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]) == 1
            manifest_1 = _json.loads(
                (output_dir / "manifest.json").read_text(encoding="utf-8")
            )
            assert manifest_1["status"] == "no_valid_records"

            # run 2：合法输入（同一输出目录）
            good_input = Path(tmpdir) / "good.jsonl"
            _write_records(
                good_input,
                [
                    _two_field_record("m1", "L1", "request", "00010002", 0),
                    _two_field_record("m2", "L1", "request", "00030004", 1),
                ],
            )

            exit_code_2 = main(["run", str(good_input), "--output-dir", str(output_dir)])
            assert exit_code_2 == 0

            # 5 个文件全部重写验证
            # 1. rejected.jsonl 空（不保留第一轮的 1 行）
            rejected_2 = [
                line for line in rejected_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            assert rejected_2 == [], (
                f"run 2 后 rejected.jsonl 应为空，实际: {rejected_2}"
            )

            # 2. rejected_groups.jsonl 空
            rejected_groups_2 = [
                line for line in (output_dir / "rejected_groups.jsonl")
                .read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            assert rejected_groups_2 == [], (
                f"run 2 后 rejected_groups.jsonl 应为空，实际: {rejected_groups_2}"
            )

            # 3. validated.jsonl 有 2 条合法记录（不是空文件）
            validated_2 = [
                line for line in (output_dir / "validated.jsonl")
                .read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            assert len(validated_2) == 2, (
                f"run 2 后 validated.jsonl 应有 2 条，实际: {len(validated_2)}"
            )

            # 4. predictions.jsonl 有内容（不是空文件）
            predictions_2 = [
                line for line in (output_dir / "predictions.jsonl")
                .read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            assert len(predictions_2) >= 1, (
                f"run 2 后 predictions.jsonl 应有预测结果，实际: {len(predictions_2)}"
            )

            # 5. field_profiles.jsonl 有内容（不是空文件）
            profiles_2 = [
                line for line in (output_dir / "field_profiles.jsonl")
                .read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            assert len(profiles_2) >= 1, (
                f"run 2 后 field_profiles.jsonl 应有画像，实际: {len(profiles_2)}"
            )

            # 6. manifest.json status=completed（不是 no_valid_records）
            manifest_2 = _json.loads(
                (output_dir / "manifest.json").read_text(encoding="utf-8")
            )
            assert manifest_2["status"] == "completed", (
                f"run 2 后 manifest status 应为 completed，实际: {manifest_2.get('status')}"
            )


class TestCliRunManifestRealCountsR349:
    """R349：Generate Manifest 使用真实阶段计数

    验收：
    - manifest["output"] 包含 9 个 RunCounts 字段
    - validated_records == group_valid_records（消息数），不是 predictions 数量
    - 消息数与字段数独立（4 消息 × 2 字段 = 2 画像/2 预测，validated_records=4）
    - 禁止 validated_records = len(predictions)
    - 拒绝计数反映在 manifest
    """

    def test_manifest_contains_all_run_counts_fields(self):
        """R349: manifest["output"] 包含 9 个 RunCounts 字段"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.jsonl"
            _write_records(
                input_path,
                [
                    _two_field_record("m1", "L1", "request", "00010002", 0),
                    _two_field_record("m2", "L1", "request", "00030004", 1),
                ],
            )

            main(["run", str(input_path), "--output-dir", str(tmpdir)])

            manifest = _json.loads(
                (Path(tmpdir) / "manifest.json").read_text(encoding="utf-8")
            )
            output = manifest["output"]
            # 9 个 RunCounts 字段
            assert "input_line_count" in output, f"缺 input_line_count: {output}"
            assert "json_valid_records" in output, f"缺 json_valid_records: {output}"
            assert "json_rejected_records" in output, f"缺 json_rejected_records: {output}"
            assert "contract_valid_records" in output, f"缺 contract_valid_records: {output}"
            assert "contract_rejected_records" in output, f"缺 contract_rejected_records: {output}"
            assert "group_valid_records" in output, f"缺 group_valid_records: {output}"
            assert "group_rejected_records" in output, f"缺 group_rejected_records: {output}"
            assert "field_profiles" in output, f"缺 field_profiles: {output}"
            assert "predictions" in output, f"缺 predictions: {output}"

    def test_manifest_validated_records_is_message_count_not_predictions(self):
        """R349: validated_records == group_valid_records（消息数），不是 predictions 数量

        4 条同 layout 消息 × 2 字段 → 2 个画像（F0, F1 合并）+ 2 个预测
        - group_valid_records = 4（消息数）
        - field_profiles = 2（字段数）
        - predictions = 2（字段数）
        - validated_records = 4（消息数，不是 predictions=2）
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.jsonl"
            _write_records(
                input_path,
                [
                    _two_field_record("m1", "L1", "request", "00010002", 0),
                    _two_field_record("m2", "L1", "request", "00030004", 1),
                    _two_field_record("m3", "L1", "request", "00050006", 2),
                    _two_field_record("m4", "L1", "request", "00070008", 3),
                ],
            )

            main(["run", str(input_path), "--output-dir", str(tmpdir)])

            manifest = _json.loads(
                (Path(tmpdir) / "manifest.json").read_text(encoding="utf-8")
            )
            output = manifest["output"]

            # 4 条消息，2 个字段 → 2 个画像（F0, F1 各合并 4 条消息）
            assert output["group_valid_records"] == 4, (
                f"group_valid_records 应为 4（消息数），实际: {output['group_valid_records']}"
            )
            assert output["field_profiles"] == 2, (
                f"field_profiles 应为 2（F0+F1 合并），实际: {output['field_profiles']}"
            )
            assert output["predictions"] == 2, (
                f"predictions 应为 2，实际: {output['predictions']}"
            )
            # 关键断言：validated_records 是消息数，不是 predictions 数量
            assert output["validated_records"] == 4, (
                f"validated_records 应为 4（消息数），实际: {output['validated_records']}"
            )
            # 禁止 validated_records = len(predictions)
            assert output["validated_records"] != output["predictions"], (
                f"validated_records 不得等于 predictions（消息数 {output['validated_records']} != 字段数 {output['predictions']}）"
            )

    def test_manifest_rejection_counts_reflected(self):
        """R349: 拒绝计数反映在 manifest（1 valid + 1 invalid JSON）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.jsonl"
            _write_records(
                input_path,
                [_two_field_record("m1", "L1", "request", "00010002", 0)],
            )
            with open(input_path, "a", encoding="utf-8") as f:
                f.write("{invalid json}\n")

            main([
                "run", str(input_path), "--output-dir", str(tmpdir),
                "--allow-partial-input",
            ])

            manifest = _json.loads(
                (Path(tmpdir) / "manifest.json").read_text(encoding="utf-8")
            )
            output = manifest["output"]

            # 2 行输入，1 合法 + 1 拒绝
            assert output["input_line_count"] == 2, (
                f"input_line_count 应为 2，实际: {output['input_line_count']}"
            )
            assert output["json_valid_records"] == 1, (
                f"json_valid_records 应为 1，实际: {output['json_valid_records']}"
            )
            assert output["json_rejected_records"] == 1, (
                f"json_rejected_records 应为 1，实际: {output['json_rejected_records']}"
            )
            assert output["group_valid_records"] == 1, (
                f"group_valid_records 应为 1，实际: {output['group_valid_records']}"
            )
            assert output["group_rejected_records"] == 0, (
                f"group_rejected_records 应为 0，实际: {output['group_rejected_records']}"
            )

    def test_manifest_group_rejection_counts_reflected(self):
        """R349: 组级拒绝计数反映在 manifest（L1 不一致 + L2 一致）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.jsonl"
            _write_records(
                input_path,
                [
                    # L1 不一致：m1 2 字段，m2 3 字段
                    _two_field_record("m1", "L1", "request", "00010002", 0),
                    {
                        "message_id": "m2",
                        "layout_id": "L1",
                        "direction": "request",
                        "payload_hex": "000100020003",
                        "fields": [
                            {"field_index": 0, "start": 0, "end": 2},
                            {"field_index": 1, "start": 2, "end": 4},
                            {"field_index": 2, "start": 4, "end": 6},
                        ],
                        "input_order": 1,
                    },
                    # L2 一致：2 条
                    _two_field_record("m3", "L2", "request", "00050006", 2),
                    _two_field_record("m4", "L2", "request", "00070008", 3),
                ],
            )

            main([
                "run", str(input_path), "--output-dir", str(tmpdir),
                "--allow-partial-input",
            ])

            manifest = _json.loads(
                (Path(tmpdir) / "manifest.json").read_text(encoding="utf-8")
            )
            output = manifest["output"]

            # 4 行输入，全部 JSON 合法
            assert output["input_line_count"] == 4
            assert output["json_valid_records"] == 4
            assert output["json_rejected_records"] == 0
            # L1 组 2 条被组级拒绝，L2 组 2 条通过
            assert output["group_valid_records"] == 2, (
                f"group_valid_records 应为 2（L2 组），实际: {output['group_valid_records']}"
            )
            assert output["group_rejected_records"] == 2, (
                f"group_rejected_records 应为 2（L1 组），实际: {output['group_rejected_records']}"
            )

    def test_audit_fix_flaw10_contract_rejected_records_reflected(self):
        """审计修复瑕疵-10: 重复 message_id 应计入 contract_rejected_records（原恒为 0）

        场景：3 行输入，1 条重复 message_id（契约拒绝）+ 2 条正常
        预期：
        - json_rejected_records == 0（无 JSON 解析失败）
        - contract_rejected_records == 1（重复 message_id）
        - json_valid_records == 3（全部通过 JSON 解析，含重复 ID 的那条）
        - contract_valid_records == 2（排除重复 ID 后）
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.jsonl"
            _write_records(
                input_path,
                [
                    _two_field_record("m1", "L1", "request", "00010002", 0),
                    # 重复 message_id="m1"，会被 read_jsonl_file 标记为契约拒绝
                    _two_field_record("m1", "L1", "request", "00030004", 1),
                    _two_field_record("m2", "L1", "request", "00050006", 2),
                ],
            )

            main([
                "run", str(input_path), "--output-dir", str(tmpdir),
                "--allow-partial-input",
            ])

            manifest = _json.loads(
                (Path(tmpdir) / "manifest.json").read_text(encoding="utf-8")
            )
            output = manifest["output"]

            # 3 行输入，全部 JSON 解析成功
            assert output["input_line_count"] == 3
            assert output["json_rejected_records"] == 0, (
                f"json_rejected_records 应为 0（无 JSON 解析失败），实际: {output['json_rejected_records']}"
            )
            # 1 条重复 message_id → contract_rejected_records=1（原实现恒为 0）
            assert output["contract_rejected_records"] == 1, (
                f"contract_rejected_records 应为 1（重复 message_id），实际: {output['contract_rejected_records']}"
            )
            # json_valid_records 包含通过 JSON 解析的记录（含契约失败的）
            assert output["json_valid_records"] == 3, (
                f"json_valid_records 应为 3（全部通过 JSON 解析），实际: {output['json_valid_records']}"
            )
            # contract_valid_records 只含通过 JSON + 契约双重校验的记录
            assert output["contract_valid_records"] == 2, (
                f"contract_valid_records 应为 2（排除重复 ID），实际: {output['contract_valid_records']}"
            )


class TestCliRunManifestRunInfoR350:
    """R350：Manifest 增加运行状态和退出信息

    验收：
    - manifest 包含 7 个字段：status/exit_code/partial_input/valid_for_reporting/started_at/finished_at/command_args
    - completed 状态：无 rejection → status=completed, exit_code=0, valid_for_reporting=True
    - partial_success 状态：有 rejection + --allow-partial-input → exit_code=0, partial_input=True
    - invalid_input 状态：有 rejection + 无 --allow-partial-input → exit_code=1, valid_for_reporting=False
    - no_valid_records 状态：0 有效记录 → exit_code=1, valid_for_reporting=False
    - started_at <= finished_at
    - command_args 捕获命令行参数
    """

    def test_manifest_contains_all_run_info_fields(self):
        """R350: manifest 包含 7 个 RunManifestInfo 字段"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.jsonl"
            _write_records(
                input_path,
                [
                    _two_field_record("m1", "L1", "request", "00010002", 0),
                    _two_field_record("m2", "L1", "request", "00030004", 1),
                ],
            )

            main(["run", str(input_path), "--output-dir", str(tmpdir)])

            manifest = _json.loads(
                (Path(tmpdir) / "manifest.json").read_text(encoding="utf-8")
            )
            # 7 个 RunManifestInfo 字段
            assert "status" in manifest, f"缺 status: {manifest.keys()}"
            assert "exit_code" in manifest, f"缺 exit_code: {manifest.keys()}"
            assert "partial_input" in manifest, f"缺 partial_input: {manifest.keys()}"
            assert "valid_for_reporting" in manifest, f"缺 valid_for_reporting: {manifest.keys()}"
            assert "started_at" in manifest, f"缺 started_at: {manifest.keys()}"
            assert "finished_at" in manifest, f"缺 finished_at: {manifest.keys()}"
            assert "command_args" in manifest, f"缺 command_args: {manifest.keys()}"

    def test_completed_status_no_rejection(self):
        """R350: 无 rejection → status=completed, exit_code=0, valid_for_reporting=True"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.jsonl"
            _write_records(
                input_path,
                [
                    _two_field_record("m1", "L1", "request", "00010002", 0),
                    _two_field_record("m2", "L1", "request", "00030004", 1),
                ],
            )

            exit_code = main(["run", str(input_path), "--output-dir", str(tmpdir)])
            assert exit_code == 0

            manifest = _json.loads(
                (Path(tmpdir) / "manifest.json").read_text(encoding="utf-8")
            )
            assert manifest["status"] == "completed"
            assert manifest["exit_code"] == 0
            assert manifest["partial_input"] is False
            assert manifest["valid_for_reporting"] is True

    def test_partial_success_status(self):
        """R350: 有 rejection + --allow-partial-input → status=partial_success, exit_code=0, partial_input=True"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.jsonl"
            _write_records(
                input_path,
                [_two_field_record("m1", "L1", "request", "00010002", 0)],
            )
            with open(input_path, "a", encoding="utf-8") as f:
                f.write("{invalid json}\n")

            exit_code = main([
                "run", str(input_path), "--output-dir", str(tmpdir),
                "--allow-partial-input",
            ])
            assert exit_code == 0

            manifest = _json.loads(
                (Path(tmpdir) / "manifest.json").read_text(encoding="utf-8")
            )
            assert manifest["status"] == "partial_success"
            assert manifest["exit_code"] == 0
            assert manifest["partial_input"] is True
            assert manifest["valid_for_reporting"] is False

    def test_invalid_input_status_fail_closed(self):
        """R350: 有 rejection + 无 --allow-partial-input → status=invalid_input, exit_code=1, valid_for_reporting=False"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.jsonl"
            _write_records(
                input_path,
                [_two_field_record("m1", "L1", "request", "00010002", 0)],
            )
            with open(input_path, "a", encoding="utf-8") as f:
                f.write("{invalid json}\n")

            exit_code = main(["run", str(input_path), "--output-dir", str(tmpdir)])
            assert exit_code == 1

            manifest = _json.loads(
                (Path(tmpdir) / "manifest.json").read_text(encoding="utf-8")
            )
            assert manifest["status"] == "invalid_input"
            assert manifest["exit_code"] == 1
            assert manifest["partial_input"] is False
            assert manifest["valid_for_reporting"] is False

    def test_no_valid_records_status_has_run_info(self):
        """R350: 0 有效记录 → status=no_valid_records, exit_code=1, valid_for_reporting=False + 7 字段全在"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.jsonl"
            with open(input_path, "w", encoding="utf-8") as f:
                f.write("{invalid json}\n")

            exit_code = main(["run", str(input_path), "--output-dir", str(tmpdir)])
            assert exit_code == 1

            manifest = _json.loads(
                (Path(tmpdir) / "manifest.json").read_text(encoding="utf-8")
            )
            assert manifest["status"] == "no_valid_records"
            assert manifest["exit_code"] == 1
            assert manifest["valid_for_reporting"] is False
            # 0 有效记录分支也包含全部 7 个字段
            assert "started_at" in manifest
            assert "finished_at" in manifest
            assert "command_args" in manifest
            assert "partial_input" in manifest

    def test_started_at_before_finished_at(self):
        """R350: started_at <= finished_at（时间戳顺序正确）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.jsonl"
            _write_records(
                input_path,
                [_two_field_record("m1", "L1", "request", "00010002", 0)],
            )

            main(["run", str(input_path), "--output-dir", str(tmpdir)])

            manifest = _json.loads(
                (Path(tmpdir) / "manifest.json").read_text(encoding="utf-8")
            )
            started = manifest["started_at"]
            finished = manifest["finished_at"]
            assert started, "started_at 不得为空"
            assert finished, "finished_at 不得为空"
            assert started <= finished, (
                f"started_at ({started}) 应 <= finished_at ({finished})"
            )

    def test_command_args_captured(self):
        """R350: command_args 捕获命令行参数（包含 run 子命令）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.jsonl"
            _write_records(
                input_path,
                [_two_field_record("m1", "L1", "request", "00010002", 0)],
            )

            main(["run", str(input_path), "--output-dir", str(tmpdir)])

            manifest = _json.loads(
                (Path(tmpdir) / "manifest.json").read_text(encoding="utf-8")
            )
            cmd_args = manifest["command_args"]
            assert isinstance(cmd_args, list), f"command_args 应为 list，实际: {type(cmd_args)}"
            assert "run" in cmd_args, f"command_args 应包含 'run'，实际: {cmd_args}"
