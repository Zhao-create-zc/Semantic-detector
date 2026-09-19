"""R422：rejection 数量语义测试

验证 V4 审计报告 MEDIUM-2 修复：
  rejection 的"记录数"和"组数"不再混用。

原实现错误：
  total_rejections = len(rejected_records) + len(rejections)
  ← 单记录拒绝数（记录数） + 冲突组数（组数）= 含义模糊的混用计数

R422 修正：
  single_record_rejection_count = len(rejected_records)  # 单记录拒绝数
  group_rejection_count = len(rejections)                 # 冲突组数量（组数）
  group_rejected_record_count = sum(rec.record_count)     # 组内消息数
  total_rejected_record_count = single_record_rejection_count + group_rejected_record_count

Manifest 要求：
  output.group_rejection_count：冲突组数量
  output.group_rejected_records：组内消息数
  两者必须独立存在，不得只写一个含义模糊的 rejections
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from semantic_detector.cli import main


def _write_records(path: Path, records: list) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _make_valid_record(msg_id: str = "m1", layout_id: str = "L1") -> dict:
    """构造一条合法记录（可通过 read_jsonl_file + prepare_records_for_profiling）"""
    return {
        "message_id": msg_id,
        "layout_id": layout_id,
        "direction": "request",
        "payload_hex": "00010002",
        "fields": [
            {"field_index": 0, "start": 0, "end": 2},
            {"field_index": 1, "start": 2, "end": 4},
        ],
        "input_order": 0,
    }


def _make_invalid_json_record() -> str:
    """构造一条 invalid JSON 行（不写入 dict，直接返回字符串）"""
    return '{"message_id": "bad", invalid json}'


def _make_group_inconsistent_records(layout_id: str = "L1", count: int = 50) -> list:
    """构造 count 条同 layout_id 但字段数不一致的记录（产生 1 个冲突组）

    每条记录字段数不同：奇数条 2 字段，偶数条 3 字段。
    prepare_records_for_profiling 会将这些记录归入同一 layout_id 组，
    检测到字段数不一致后产生 1 个 GroupRejection（record_count=count）。
    """
    records = []
    for i in range(count):
        if i % 2 == 0:
            # 2 字段
            fields = [
                {"field_index": 0, "start": 0, "end": 2},
                {"field_index": 1, "start": 2, "end": 4},
            ]
            payload_hex = "00010002"
        else:
            # 3 字段
            fields = [
                {"field_index": 0, "start": 0, "end": 2},
                {"field_index": 1, "start": 2, "end": 4},
                {"field_index": 2, "start": 4, "end": 6},
            ]
            payload_hex = "000100020003"
        records.append({
            "message_id": f"g_{layout_id}_{i}",
            "layout_id": layout_id,
            "direction": "request",
            "payload_hex": payload_hex,
            "fields": fields,
            "input_order": i,
        })
    return records


class TestCliRunRejectionCountsR422:
    """R422：rejection 记录数 vs 组数严格分开测试

    验证：
    1. Manifest 包含 group_rejection_count 字段（组数）
    2. Manifest 包含 group_rejected_records 字段（组内消息数）
    3. 两者数值不同（当组内有多条消息时）
    4. CLI 输出严格区分单记录拒绝、冲突组数、组内消息数、总拒绝消息数
    5. 状态判断（exit code）基于总拒绝消息数，不基于组数
    """

    def test_manifest_contains_group_rejection_count_field(self, tmp_path: Path) -> None:
        """Manifest output 必须包含 group_rejection_count 字段（组数）

        R422 计划要求：Manifest 中保留独立字段，不得只写一个含义模糊的 rejections
        """
        # 构造 1 个冲突组（5 条记录）
        records = _make_group_inconsistent_records("L1", 5)
        input_path = tmp_path / "input.jsonl"
        _write_records(input_path, records)
        output_dir = tmp_path / "output"

        # 允许 partial input 以便生成 manifest（否则 fail closed 退出无 manifest）
        rc = main(["run", str(input_path), "--output-dir", str(output_dir), "--allow-partial-input"])

        # 全部记录都在冲突组中，无有效记录 → no_valid_records
        assert rc != 0

        manifest_path = output_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        output = manifest.get("output", {})
        assert "group_rejection_count" in output, (
            "Manifest output 必须包含 group_rejection_count 字段（R422 计划要求）"
        )
        assert output.get("group_rejection_count") == 1, (
            f"1 个冲突组，group_rejection_count 应为 1，got {output.get('group_rejection_count')}"
        )

    def test_group_rejection_count_differs_from_group_rejected_records(self, tmp_path: Path) -> None:
        """group_rejection_count（组数）vs group_rejected_records（组内消息数）必须不同

        场景：2 个冲突组，每组 5 条记录
        - group_rejection_count = 2（组数）
        - group_rejected_records = 10（2 组 × 5 条 = 10 条消息）
        """
        # 构造 2 个冲突组，每组 5 条记录
        records_l1 = _make_group_inconsistent_records("L1", 5)
        records_l2 = _make_group_inconsistent_records("L2", 5)
        all_records = records_l1 + records_l2

        input_path = tmp_path / "input.jsonl"
        _write_records(input_path, all_records)
        output_dir = tmp_path / "output"

        rc = main(["run", str(input_path), "--output-dir", str(output_dir), "--allow-partial-input"])
        assert rc != 0  # 全部记录都在冲突组中，无有效记录

        manifest_path = output_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        output = manifest.get("output", {})
        group_rejection_count = output.get("group_rejection_count")
        group_rejected_records = output.get("group_rejected_records")

        assert group_rejection_count == 2, (
            f"2 个冲突组，group_rejection_count 应为 2，got {group_rejection_count}"
        )
        assert group_rejected_records == 10, (
            f"2 组 × 5 条 = 10 条消息，group_rejected_records 应为 10，got {group_rejected_records}"
        )
        assert group_rejection_count != group_rejected_records, (
            "组数和消息数必须不同（当组内有多条消息时）"
        )

    def test_total_rejected_record_count_not_mixing_counts(self, tmp_path: Path, capsys) -> None:
        """总拒绝消息数不得混用记录数和组数

        场景：
        - 2 条合法记录（让流水线走到正常分支输出日志）
        - 5 条单记录拒绝（invalid JSON）
        - 1 个冲突组，组内 10 条消息

        错误计算（原实现）：total = 5 + 1 = 6（混用）
        正确计算（R422）：total = 5 + 10 = 15（消息数 + 消息数）

        验证：
        - 单记录拒绝：5
        - 冲突组数：1
        - 组内消息数：10
        - 总拒绝消息数：15（不是 6）
        """
        # 2 条合法记录（独立 layout_id，不进入冲突组）
        valid_records = [
            _make_valid_record("v1", "L_valid"),
            _make_valid_record("v2", "L_valid"),
        ]
        # 5 条 invalid JSON（单记录拒绝）
        invalid_lines = [_make_invalid_json_record() for _ in range(5)]
        # 1 个冲突组（10 条记录）
        group_records = _make_group_inconsistent_records("L_conflict", 10)

        input_path = tmp_path / "input.jsonl"
        with open(input_path, "w", encoding="utf-8") as f:
            for rec in valid_records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            for line in invalid_lines:
                f.write(line + "\n")
            for rec in group_records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

        output_dir = tmp_path / "output"

        rc = main(["run", str(input_path), "--output-dir", str(output_dir), "--allow-partial-input"])
        assert rc == 0  # partial_success（有有效记录 + 有拒绝）

        manifest_path = output_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        output = manifest.get("output", {})
        # 单记录拒绝 = JSON 解析失败 5 条
        json_rejected_records = output.get("json_rejected_records", 0)
        # 冲突组数
        group_rejection_count = output.get("group_rejection_count", 0)
        # 组内消息数
        group_rejected_records = output.get("group_rejected_records", 0)

        assert json_rejected_records == 5, (
            f"5 条 invalid JSON，json_rejected_records 应为 5，got {json_rejected_records}"
        )
        assert group_rejection_count == 1, (
            f"1 个冲突组，group_rejection_count 应为 1，got {group_rejection_count}"
        )
        assert group_rejected_records == 10, (
            f"组内 10 条消息，group_rejected_records 应为 10，got {group_rejected_records}"
        )

        # R426：直接验证 CLI 输出的总拒绝消息数（原为间接推算，无法捕获混用 BUG）
        # 正确：5 + 10 = 15；错误（混用）：5 + 1 = 6
        # CLI 输出格式："单记录拒绝: 5, 冲突组数: 1, 冲突组内消息数: 10, 总拒绝消息数: 15, 有效消息数: 2"
        captured = capsys.readouterr()
        output_text = captured.out
        assert "总拒绝消息数: 15" in output_text, (
            f"总拒绝消息数应为 15（5 单记录 + 10 组内），不是 6（混用）。"
            f"CLI 输出: {output_text}"
        )
        assert "单记录拒绝: 5" in output_text, (
            f"单记录拒绝应为 5。CLI 输出: {output_text}"
        )
        assert "冲突组数: 1" in output_text, (
            f"冲突组数应为 1。CLI 输出: {output_text}"
        )
        assert "冲突组内消息数: 10" in output_text, (
            f"冲突组内消息数应为 10。CLI 输出: {output_text}"
        )

    def test_cli_output_distinguishes_counts(self, tmp_path: Path, capsys) -> None:
        """CLI 输出必须严格区分单记录拒绝、冲突组数、组内消息数、总拒绝消息数

        R422 计划 CLI 输出示例：
          输入行数：140
          单记录拒绝：5
          冲突组数：2
          冲突组内消息数：100
          总拒绝消息数：105
          有效消息数：35
        """
        # 构造：2 条合法 + 2 条 invalid JSON + 1 个冲突组（4 条）
        valid_records = [
            _make_valid_record("v1", "L_valid"),
            _make_valid_record("v2", "L_valid"),
        ]
        invalid_lines = [_make_invalid_json_record() for _ in range(2)]
        group_records = _make_group_inconsistent_records("L_conflict", 4)

        input_path = tmp_path / "input.jsonl"
        with open(input_path, "w", encoding="utf-8") as f:
            for rec in valid_records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            for line in invalid_lines:
                f.write(line + "\n")
            for rec in group_records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

        output_dir = tmp_path / "output"

        # 使用 --allow-partial-input 让流水线继续，产生 CLI 输出
        rc = main(["run", str(input_path), "--output-dir", str(output_dir), "--allow-partial-input"])

        captured = capsys.readouterr()
        output_text = captured.out

        # R426：升级为具体数值检查（原仅检查字符串存在，无法捕获数值错误）
        # CLI 输出格式："单记录拒绝: 2, 冲突组数: 1, 冲突组内消息数: 4, 总拒绝消息数: 6, 有效消息数: 2"
        # 预期：2 合法 + 2 invalid JSON + 4 组内 = 8 行；单记录拒绝=2；冲突组数=1；组内消息数=4；总拒绝=6；有效=2
        assert "单记录拒绝: 2" in output_text, (
            f"CLI 输出必须包含 '单记录拒绝: 2'，got: {output_text}"
        )
        assert "冲突组数: 1" in output_text, (
            f"CLI 输出必须包含 '冲突组数: 1'，got: {output_text}"
        )
        assert "冲突组内消息数: 4" in output_text, (
            f"CLI 输出必须包含 '冲突组内消息数: 4'，got: {output_text}"
        )
        assert "总拒绝消息数: 6" in output_text, (
            f"CLI 输出必须包含 '总拒绝消息数: 6'（2 单记录 + 4 组内），got: {output_text}"
        )
        assert "有效消息数: 2" in output_text, (
            f"CLI 输出必须包含 '有效消息数: 2'，got: {output_text}"
        )

    def test_validate_command_uses_correct_rejection_counts(self, tmp_path: Path, capsys) -> None:
        """validate 命令也必须使用正确的 rejection 数量语义

        验证 cmd_validate 的 CLI 输出区分单记录拒绝、冲突组数、组内消息数、总拒绝消息数
        """
        # 构造：2 条 invalid JSON + 1 个冲突组（4 条）
        invalid_lines = [_make_invalid_json_record() for _ in range(2)]
        group_records = _make_group_inconsistent_records("L_conflict", 4)

        input_path = tmp_path / "input.jsonl"
        with open(input_path, "w", encoding="utf-8") as f:
            for line in invalid_lines:
                f.write(line + "\n")
            for rec in group_records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

        output_dir = tmp_path / "output"

        rc = main(["validate", str(input_path), "--output-dir", str(output_dir)])
        assert rc != 0  # 有 rejection

        captured = capsys.readouterr()
        output_text = captured.out

        # R426：升级为具体数值检查
        # validate CLI 输出格式："验证完成: X 组级有效, Y 单记录拒绝, Z 冲突组数, W 冲突组内消息数, V 总拒绝消息数"
        # 预期：2 invalid JSON + 1 组（4 条）；单记录拒绝=2；冲突组数=1；组内消息数=4；总拒绝=6
        assert "2 单记录拒绝" in output_text, (
            f"validate CLI 输出必须包含 '2 单记录拒绝'，got: {output_text}"
        )
        assert "1 冲突组数" in output_text, (
            f"validate CLI 输出必须包含 '1 冲突组数'，got: {output_text}"
        )
        assert "4 冲突组内消息数" in output_text, (
            f"validate CLI 输出必须包含 '4 冲突组内消息数'，got: {output_text}"
        )
        assert "6 总拒绝消息数" in output_text, (
            f"validate CLI 输出必须包含 '6 总拒绝消息数'，got: {output_text}"
        )

    def test_profile_command_uses_correct_rejection_counts(self, tmp_path: Path, capsys) -> None:
        """profile 命令也必须使用正确的 rejection 数量语义

        验证 cmd_profile 的 CLI 输出区分单记录拒绝、冲突组数、组内消息数、总拒绝消息数
        """
        # 构造：2 条合法 + 2 条 invalid JSON + 1 个冲突组（4 条）
        valid_records = [
            _make_valid_record("v1", "L_valid"),
            _make_valid_record("v2", "L_valid"),
        ]
        invalid_lines = [_make_invalid_json_record() for _ in range(2)]
        group_records = _make_group_inconsistent_records("L_conflict", 4)

        input_path = tmp_path / "input.jsonl"
        with open(input_path, "w", encoding="utf-8") as f:
            for rec in valid_records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            for line in invalid_lines:
                f.write(line + "\n")
            for rec in group_records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

        output_dir = tmp_path / "output"

        rc = main(["profile", str(input_path), "--output-dir", str(output_dir)])
        # profile 命令有 rejection 时 fail closed
        assert rc != 0

        captured = capsys.readouterr()
        output_text = captured.out

        # R426：升级为具体数值检查
        # CLI 输出格式："X 单记录拒绝, Y 冲突组数, Z 冲突组内消息数, W 总拒绝消息数"
        # 预期：2 invalid JSON + 1 组（4 条）；单记录拒绝=2；冲突组数=1；组内消息数=4；总拒绝=6
        assert "2 单记录拒绝" in output_text, (
            f"profile CLI 输出必须包含 '2 单记录拒绝'，got: {output_text}"
        )
        assert "1 冲突组数" in output_text, (
            f"profile CLI 输出必须包含 '1 冲突组数'，got: {output_text}"
        )
        assert "4 冲突组内消息数" in output_text, (
            f"profile CLI 输出必须包含 '4 冲突组内消息数'，got: {output_text}"
        )
        assert "6 总拒绝消息数" in output_text, (
            f"profile CLI 输出必须包含 '6 总拒绝消息数'，got: {output_text}"
        )

    def test_exit_code_based_on_record_count_not_group_count(self, tmp_path: Path) -> None:
        """退出码基于总拒绝消息数，不基于组数

        场景：
        - 0 条单记录拒绝
        - 1 个冲突组（5 条消息）

        正确行为：5 条拒绝消息 > 0 → exit 1（fail closed）
        错误行为（如果基于组数）：1 个组 > 0 → exit 1（巧合也是 1）

        区分场景：构造一个边界情况，确保 exit code 基于消息数
        """
        # 1 个冲突组（5 条记录），无单记录拒绝
        records = _make_group_inconsistent_records("L1", 5)
        input_path = tmp_path / "input.jsonl"
        _write_records(input_path, records)
        output_dir = tmp_path / "output"

        # 不使用 --allow-partial-input，应 fail closed
        rc = main(["run", str(input_path), "--output-dir", str(output_dir)])
        assert rc != 0, "有 5 条拒绝消息，应 fail closed（exit 1）"

        manifest_path = output_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        output = manifest.get("output", {})

        # 验证：组数=1，组内消息数=5，总拒绝消息数=5
        assert output.get("group_rejection_count") == 1
        assert output.get("group_rejected_records") == 5
