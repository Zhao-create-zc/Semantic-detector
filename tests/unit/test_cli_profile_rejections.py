"""R384：Profile 静默忽略 rejection 的失败测试

复现 HIGH-3：profile 输入有 duplicate/invalid → exit 0 → 没有 rejected

当前 cmd_profile 行为（HIGH-3 根因）：
1. 第 306 行 `_rejected_records = read_jsonl_file(...)` 用下划线前缀，
   JSON 级拒绝（parse/contract/duplicate）被完全忽略，不导出 rejected.jsonl
2. 第 361 行 `return 0`，即使有组级拒绝也返回 0（fail open）

R384 期望（R385 修复后的正确行为）：
- exit 非零（任何 rejection → fail closed）
- rejected.jsonl 存在且可解析
- profiles 不得被作为完整成功结果

本轮不修改生产代码。测试当前会失败，R385 修复后通过。
"""

import json
from pathlib import Path

import pytest

from semantic_detector.cli import main


def _write_jsonl(path: Path, records: list) -> None:
    """写入 JSONL 文件"""
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _make_valid_record(message_id: str = "m1") -> dict:
    """构造一条合法记录"""
    return {
        "message_id": message_id,
        "layout_id": "L",
        "direction": "request",
        "payload_hex": "0001",
        "fields": [{"field_index": 0, "start": 0, "end": 2}],
    }


def _read_jsonl(path: Path) -> list:
    """读取 JSONL 文件为 list of dict（空文件返回空列表）"""
    if not path.exists():
        return []
    result = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                result.append(json.loads(line))
    return result


class TestCliProfileRejectionsR384:
    """R384：Profile 静默忽略 rejection 的失败测试

    复现 HIGH-3：当前 cmd_profile 忽略 JSON 级拒绝（_rejected_records），
    不导出 rejected.jsonl，且有拒绝时仍 return 0（fail open）。

    R385 修复后：
    - 任何 rejection → exit 非零（fail closed）
    - rejected.jsonl 存在且可解析
    - profiles 不得被作为完整成功结果
    """

    def test_r384_profile_invalid_json_rejected(self, tmp_path: Path) -> None:
        """R384: profile 输入含 invalid JSON 时应 exit 非零并导出 rejected.jsonl

        复现 HIGH-3：当前 cmd_profile 忽略 JSON 级拒绝，exit 0，无 rejected.jsonl。
        """
        input_path = tmp_path / "input.jsonl"
        # 1 valid + 1 invalid JSON
        with open(input_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(_make_valid_record("ok")) + "\n")
            f.write('{"message_id": "bad", invalid json}\n')

        output_dir = tmp_path / "out"
        rc = main(["profile", str(input_path), "--output-dir", str(output_dir)])

        # 断言 1: exit 非零（有 JSON 级拒绝，应 fail closed）
        assert rc != 0, (
            f"profile 输入含 invalid JSON 应 exit 非零（HIGH-3: 当前 return 0），got rc={rc}"
        )

        # 断言 2: rejected.jsonl 存在
        rejected_path = output_dir / "rejected.jsonl"
        assert rejected_path.exists(), (
            "rejected.jsonl 必须存在（HIGH-3: 当前 cmd_profile 不导出 rejected.jsonl）"
        )

        # 断言 3: rejected.jsonl 非空且可解析
        lines = [l.strip() for l in rejected_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        assert len(lines) > 0, "rejected.jsonl 不应为空（有 invalid JSON 拒绝）"
        for line in lines:
            item = json.loads(line)  # 不抛异常
            assert "reason_code" in item, f"rejected 记录缺 reason_code: {item}"

    def test_r384_profile_duplicate_message_id_rejected(self, tmp_path: Path) -> None:
        """R384: profile 输入含 duplicate message_id 时应 exit 非零并导出 rejected.jsonl

        复现 HIGH-3：当前 cmd_profile 忽略重复 message_id 拒绝。
        """
        records = [
            _make_valid_record("dup"),
            _make_valid_record("dup"),  # 重复
        ]
        input_path = tmp_path / "input.jsonl"
        _write_jsonl(input_path, records)

        output_dir = tmp_path / "out"
        rc = main(["profile", str(input_path), "--output-dir", str(output_dir)])

        # 断言 1: exit 非零
        assert rc != 0, (
            f"profile 输入含 duplicate message_id 应 exit 非零，got rc={rc}"
        )

        # 断言 2: rejected.jsonl 存在且含 duplicate_message_id
        rejected_path = output_dir / "rejected.jsonl"
        assert rejected_path.exists(), "rejected.jsonl 必须存在"
        lines = [l.strip() for l in rejected_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        assert len(lines) > 0, "rejected.jsonl 不应为空"
        reason_codes = set()
        for line in lines:
            item = json.loads(line)
            assert "reason_code" in item
            reason_codes.add(item["reason_code"])
        assert "duplicate_message_id" in reason_codes, (
            f"reason_code 应含 duplicate_message_id, got {reason_codes}"
        )

    def test_r384_profile_group_field_count_mismatch_rejected(self, tmp_path: Path) -> None:
        """R384: profile 输入含 group field-count mismatch 时应 exit 非零

        构造同组（layout_id+direction）但字段数不一致的记录，
        prepare_records_for_profiling 会拒绝该组。

        复现 HIGH-3：当前 cmd_profile 跳过该组但仍 return 0（fail open）。
        """
        records = [
            {
                "message_id": "m1",
                "layout_id": "L",
                "direction": "request",
                "payload_hex": "000102",
                "fields": [{"field_index": 0, "start": 0, "end": 2}],
            },
            {
                "message_id": "m2",
                "layout_id": "L",
                "direction": "request",
                "payload_hex": "0001020304",
                "fields": [
                    {"field_index": 0, "start": 0, "end": 2},
                    {"field_index": 1, "start": 2, "end": 4},
                ],
            },
        ]
        input_path = tmp_path / "input.jsonl"
        _write_jsonl(input_path, records)

        output_dir = tmp_path / "out"
        rc = main(["profile", str(input_path), "--output-dir", str(output_dir)])

        # 断言 1: exit 非零（组级拒绝应 fail closed）
        assert rc != 0, (
            f"profile 输入含 group field-count mismatch 应 exit 非零，got rc={rc}"
        )

    def test_r384_profile_does_not_silently_ignore_rejections(self, tmp_path: Path) -> None:
        """R384: profile 不得静默忽略任何 rejection

        综合验证：输入含 invalid JSON + duplicate 时，
        cmd_profile 必须 exit 非零并导出 rejected.jsonl。
        当前实现静默忽略（HIGH-3 根因）。
        """
        input_path = tmp_path / "input.jsonl"
        with open(input_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(_make_valid_record("ok")) + "\n")
            f.write('{"invalid json}\n')  # invalid JSON
            f.write(json.dumps(_make_valid_record("dup")) + "\n")  # 合法
            f.write(json.dumps(_make_valid_record("dup")) + "\n")  # duplicate

        output_dir = tmp_path / "out"
        rc = main(["profile", str(input_path), "--output-dir", str(output_dir)])

        # 必须有拒绝被检测到（exit 非零）
        assert rc != 0, "profile 不得静默忽略 rejection（HIGH-3）"

        # rejected.jsonl 必须存在且非空
        rejected_path = output_dir / "rejected.jsonl"
        assert rejected_path.exists(), "rejected.jsonl 必须存在"
        content = rejected_path.read_text(encoding="utf-8")
        assert content.strip(), "rejected.jsonl 不应为空"

    def test_r384_profile_rejected_jsonl_parseable(self, tmp_path: Path) -> None:
        """R384: profile 的 rejected.jsonl 每行可 JSON 解析

        R385 修复后，profile 也用 RejectedRecord.to_dict() 写入，
        每行可正常 json.dumps。当前不导出 rejected.jsonl。
        """
        records = [
            _make_valid_record("ok"),
            {
                "message_id": "bad_type",
                "layout_id": "L",
                "direction": "request",
                "payload_hex": "0001",
                "fields": [{"field_index": 0.0, "start": 0, "end": 2}],  # float
            },
        ]
        input_path = tmp_path / "input.jsonl"
        _write_jsonl(input_path, records)

        output_dir = tmp_path / "out"
        main(["profile", str(input_path), "--output-dir", str(output_dir)])

        rejected_path = output_dir / "rejected.jsonl"
        # R385 修复后 rejected.jsonl 必须存在
        assert rejected_path.exists(), "rejected.jsonl 必须存在"
        # 每行可 JSON 解析
        with open(rejected_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                if line.strip():
                    item = json.loads(line)  # 不抛异常
                    assert "reason_code" in item, f"第 {line_num} 行缺 reason_code"
                    assert "stage" in item, f"第 {line_num} 行缺 stage"

    def test_r384_profile_no_rejection_exit_zero(self, tmp_path: Path) -> None:
        """R384: profile 输入全部合法时应 exit 0（验证 fail closed 不误伤）

        这是 R385 修复后的正向测试：无拒绝时正常返回 0。
        当前实现也返回 0（但因为是 fail open，不是 fail closed）。
        """
        records = [
            _make_valid_record("m1"),
            _make_valid_record("m2"),
        ]
        input_path = tmp_path / "input.jsonl"
        _write_jsonl(input_path, records)

        output_dir = tmp_path / "out"
        rc = main(["profile", str(input_path), "--output-dir", str(output_dir)])

        # 无拒绝时应 exit 0
        assert rc == 0, f"profile 无拒绝时应 exit 0，got rc={rc}"
