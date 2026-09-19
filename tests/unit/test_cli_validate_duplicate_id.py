"""R381：重复 message_id 的 rejection 序列化失败测试

精确复现 HIGH-2：
  Object of type MessageRecord is not JSON serializable

当前 cmd_validate 直接 json.dumps(rejected_record)，但 rejected_record 含
MessageRecord 对象（重复 message_id 时），导致 TypeError 崩溃。

R381 期望（R383 修复后的正确行为）：
- validate exit 非零
- rejected.jsonl 必须存在
- 文件不为空
- 每行可 JSON 解析
- reason_code=duplicate_message_id

本轮不修改生产代码。测试当前会失败，R383 修复后通过。
"""

import json
from pathlib import Path

import pytest

from semantic_detector.cli import main


def _write_jsonl(path: Path, records: list) -> None:
    """写入 JSONL 文件"""
    with open(path, 'w', encoding='utf-8') as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')


def _make_record(message_id: str = "m1") -> dict:
    """构造一条合法记录"""
    return {
        "message_id": message_id,
        "layout_id": "L",
        "direction": "request",
        "payload_hex": "0001",
        "fields": [{"field_index": 0, "start": 0, "end": 2}],
    }


class TestCliValidateDuplicateIdR381:
    """R381：validate 重复 message_id 的 rejection 序列化测试。

    复现 HIGH-2：当前 cmd_validate 第 222-225 行直接 json.dumps(rejected_record)，
    但重复 message_id 的 rejected_record 含 MessageRecord 对象（'record' 键），
    导致 TypeError: Object of type MessageRecord is not JSON serializable。

    R383 修复后，rejected.jsonl 应可正常写入，含 reason_code=duplicate_message_id。
    """

    def test_r381_validate_duplicate_message_id_rejection_serializable(
        self, tmp_path: Path
    ) -> None:
        """R381: validate 重复 message_id 的 rejection 必须可 JSON 序列化

        复现 HIGH-2。当前实现崩溃在 json.dumps(MessageRecord)，
        R383 修复后应正常写出 rejected.jsonl。
        """
        # 构造两条相同 message_id
        records = [
            _make_record("dup_001"),
            {
                "message_id": "dup_001",  # 重复
                "layout_id": "L",
                "direction": "request",
                "payload_hex": "0203",
                "fields": [{"field_index": 0, "start": 0, "end": 2}],
            },
        ]
        input_path = tmp_path / "input.jsonl"
        _write_jsonl(input_path, records)

        output_dir = tmp_path / "out"
        rc = main(["validate", str(input_path), "--output-dir", str(output_dir)])

        # 断言 1: validate exit 非零（有 rejection）
        assert rc != 0, f"validate 应 exit 非零（有 rejection），got rc={rc}"

        # 断言 2: rejected.jsonl 必须存在
        rejected_path = output_dir / "rejected.jsonl"
        assert rejected_path.exists(), "rejected.jsonl 必须存在"

        # 断言 3: 文件不为空（至少 1 条非空行）
        lines = []
        with open(rejected_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    lines.append(line.strip())
        assert len(lines) > 0, "rejected.jsonl 不应为空（有重复 message_id 拒绝）"

        # 断言 4: 每行可 JSON 解析（不崩溃）
        parsed = [json.loads(line) for line in lines]

        # 断言 5: 每行含 reason_code 字段
        for item in parsed:
            assert "reason_code" in item, (
                f"rejected 记录缺 reason_code 字段: {item}（HIGH-2 根因：当前用 'reason' 而非 'reason_code'）"
            )

        # 断言 6: 必须有 duplicate_message_id reason_code
        reason_codes = {item["reason_code"] for item in parsed}
        assert "duplicate_message_id" in reason_codes, (
            f"reason_code 应含 duplicate_message_id, got {reason_codes}"
        )

    def test_r381_rejected_record_no_message_record_object(self, tmp_path: Path) -> None:
        """R381: rejected 记录不得包含 MessageRecord 对象（必须可序列化）

        当前实现 rejected_record 含 'record': MessageRecord，
        json.dumps 崩溃。R383 修复后应转为可序列化摘要。
        """
        records = [
            _make_record("dup_002"),
            {
                "message_id": "dup_002",  # 重复
                "layout_id": "L",
                "direction": "request",
                "payload_hex": "0203",
                "fields": [{"field_index": 0, "start": 0, "end": 2}],
            },
        ]
        input_path = tmp_path / "input.jsonl"
        _write_jsonl(input_path, records)

        output_dir = tmp_path / "out"
        main(["validate", str(input_path), "--output-dir", str(output_dir)])

        rejected_path = output_dir / "rejected.jsonl"
        if not rejected_path.exists():
            pytest.fail("rejected.jsonl 不存在（cmd_validate 崩溃前未创建）")

        # 每行必须可 JSON 解析（不崩溃）
        with open(rejected_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    # 不得包含不可序列化的 'record' 键（MessageRecord 对象）
                    assert "record" not in item, (
                        f"rejected 记录不得含 'record' MessageRecord 对象: {item}"
                    )

    def test_r381_validate_rejected_jsonl_no_crash_on_duplicate(self, tmp_path: Path) -> None:
        """R381: validate 处理重复 message_id 时不得崩溃

        当前实现 json.dumps(MessageRecord) 抛 TypeError 被 main 捕获，
        但 rejected.jsonl 写入不完整。R383 修复后应无异常。
        """
        records = [
            _make_record("dup_003"),
            _make_record("dup_003"),  # 重复
        ]
        input_path = tmp_path / "input.jsonl"
        _write_jsonl(input_path, records)

        output_dir = tmp_path / "out"
        # 不应抛异常（main 捕获后返回非零退出码）
        rc = main(["validate", str(input_path), "--output-dir", str(output_dir)])

        # 必须返回非零（有 rejection）
        assert rc != 0

        # rejected.jsonl 必须可正常读取（无部分写入崩溃）
        rejected_path = output_dir / "rejected.jsonl"
        assert rejected_path.exists()
        # 读取整个文件不应抛异常
        content = rejected_path.read_text(encoding='utf-8')
        # 必须有非空内容
        assert content.strip(), "rejected.jsonl 不应为空"


class TestCliValidateRejectionFormatR383:
    """R383：Validate 拒绝记录统一格式测试

    R383 修复后，rejected.jsonl 用 RejectedRecord.to_dict() 写入，
    每行含 line_number/stage/reason_code/message 等统一字段。
    覆盖 parse/contract/duplicate 三类拒绝阶段。
    """

    def test_r383_parse_error_rejection_format(self, tmp_path: Path) -> None:
        """R383: parse 阶段拒绝（Invalid JSON）格式正确

        构造一行非法 JSON，验证 rejected.jsonl 含：
        - stage="parse"
        - reason_code="invalid_json"
        - message 含原始错误消息
        - line_number 正确
        """
        input_path = tmp_path / "input.jsonl"
        # 第一行合法，第二行非法 JSON
        with open(input_path, 'w', encoding='utf-8') as f:
            f.write(json.dumps(_make_record("ok")) + '\n')
            f.write('{"message_id": "bad", invalid json}\n')

        output_dir = tmp_path / "out"
        rc = main(["validate", str(input_path), "--output-dir", str(output_dir)])

        assert rc != 0  # 有拒绝
        rejected_path = output_dir / "rejected.jsonl"
        assert rejected_path.exists()
        lines = [l.strip() for l in rejected_path.read_text(encoding='utf-8').splitlines() if l.strip()]
        assert len(lines) == 1
        item = json.loads(lines[0])
        assert item["stage"] == "parse"
        assert item["reason_code"] == "invalid_json"
        # message 是 JSONDecodeError 原始消息（如 "Expecting property name..."），
        # 不一定含 "Invalid JSON" 字样（read_jsonl_file 直接捕获 json.loads 错误）
        assert item["message"], "parse 拒绝的 message 不应为空"
        assert item["line_number"] == 2

    def test_r383_contract_missing_field_rejection_format(self, tmp_path: Path) -> None:
        """R383: contract 阶段拒绝（缺少必填字段）格式正确"""
        input_path = tmp_path / "input.jsonl"
        with open(input_path, 'w', encoding='utf-8') as f:
            # 缺少 payload_hex 字段
            f.write('{"message_id": "m1", "layout_id": "L", "direction": "request", "fields": []}\n')

        output_dir = tmp_path / "out"
        rc = main(["validate", str(input_path), "--output-dir", str(output_dir)])

        assert rc != 0
        rejected_path = output_dir / "rejected.jsonl"
        lines = [l.strip() for l in rejected_path.read_text(encoding='utf-8').splitlines() if l.strip()]
        assert len(lines) == 1
        item = json.loads(lines[0])
        assert item["stage"] == "contract"
        assert item["reason_code"] == "missing_required_field"
        assert "Missing required field" in item["message"]
        assert item["line_number"] == 1

    def test_r383_contract_type_error_rejection_format(self, tmp_path: Path) -> None:
        """R383: contract 阶段拒绝（类型错误，float field_index）格式正确"""
        input_path = tmp_path / "input.jsonl"
        with open(input_path, 'w', encoding='utf-8') as f:
            f.write(json.dumps({
                "message_id": "m1",
                "layout_id": "L",
                "direction": "request",
                "payload_hex": "0001",
                "fields": [{"field_index": 0.0, "start": 0, "end": 2}],  # float
            }) + '\n')

        output_dir = tmp_path / "out"
        rc = main(["validate", str(input_path), "--output-dir", str(output_dir)])

        assert rc != 0
        rejected_path = output_dir / "rejected.jsonl"
        lines = [l.strip() for l in rejected_path.read_text(encoding='utf-8').splitlines() if l.strip()]
        assert len(lines) == 1
        item = json.loads(lines[0])
        assert item["stage"] == "contract"
        assert item["reason_code"] == "type_error"
        assert "must be int" in item["message"]

    def test_r383_duplicate_rejection_has_record_summary(self, tmp_path: Path) -> None:
        """R383: duplicate 阶段拒绝含 record_summary 摘要（不含 MessageRecord 对象）"""
        records = [
            _make_record("dup"),
            _make_record("dup"),  # 重复
        ]
        input_path = tmp_path / "input.jsonl"
        _write_jsonl(input_path, records)

        output_dir = tmp_path / "out"
        main(["validate", str(input_path), "--output-dir", str(output_dir)])

        rejected_path = output_dir / "rejected.jsonl"
        lines = [l.strip() for l in rejected_path.read_text(encoding='utf-8').splitlines() if l.strip()]
        assert len(lines) == 1
        item = json.loads(lines[0])
        assert item["stage"] == "duplicate"
        assert item["reason_code"] == "duplicate_message_id"
        assert item["message_id"] == "dup"
        assert item["layout_id"] == "L"
        assert item["direction"] == "request"
        # record_summary 含字段数和 payload 长度
        assert "record_summary" in item
        summary = item["record_summary"]
        assert summary["field_count"] == 1
        assert summary["payload_length"] == 2
        # 不含 MessageRecord 对象（无 'record' 键）
        assert "record" not in item

    def test_r383_no_rejection_writes_empty_file(self, tmp_path: Path) -> None:
        """R383: 无拒绝时 rejected.jsonl 为空文件（避免旧文件残留）"""
        records = [_make_record("m1"), _make_record("m2")]
        input_path = tmp_path / "input.jsonl"
        _write_jsonl(input_path, records)

        output_dir = tmp_path / "out"
        rc = main(["validate", str(input_path), "--output-dir", str(output_dir)])

        assert rc == 0  # 无拒绝
        rejected_path = output_dir / "rejected.jsonl"
        # 文件必须存在（无条件写入空文件）
        assert rejected_path.exists()
        # 文件必须为空
        content = rejected_path.read_text(encoding='utf-8')
        assert content == "", f"无拒绝时 rejected.jsonl 应为空，got: {content!r}"

    def test_r383_all_rejections_json_serializable(self, tmp_path: Path) -> None:
        """R383: 所有类型拒绝的 rejected.jsonl 每行可 JSON 解析（HIGH-2 核心）"""
        input_path = tmp_path / "input.jsonl"
        with open(input_path, 'w', encoding='utf-8') as f:
            f.write('{"invalid json}\n')  # parse 错误
            f.write('{"message_id": "m1", "layout_id": "L"}\n')  # missing field
            f.write(json.dumps(_make_record("dup")) + '\n')  # 合法
            f.write(json.dumps(_make_record("dup")) + '\n')  # duplicate
            f.write(json.dumps({
                "message_id": "bad_type",
                "layout_id": "L",
                "direction": "request",
                "payload_hex": "0001",
                "fields": [{"field_index": True, "start": 0, "end": 2}],  # bool type error
            }) + '\n')

        output_dir = tmp_path / "out"
        main(["validate", str(input_path), "--output-dir", str(output_dir)])

        rejected_path = output_dir / "rejected.jsonl"
        # 每行必须可 JSON 解析（不崩溃）
        with open(rejected_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                if line.strip():
                    item = json.loads(line)  # 不抛异常
                    # 每行含必需字段
                    assert "stage" in item, f"第 {line_num} 行缺 stage"
                    assert "reason_code" in item, f"第 {line_num} 行缺 reason_code"
                    assert "message" in item, f"第 {line_num} 行缺 message"
