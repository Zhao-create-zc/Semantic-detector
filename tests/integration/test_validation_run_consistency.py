"""R379：Validate 与 Run 一致性集成测试

证明"validate 通过的消息一定能安全进入 run 的切片阶段"（计划 R379）。

cmd_validate 和 cmd_run 都调用共享入口：
  read_jsonl_file → prepare_records_for_profiling

本测试通过 CLI 端到端验证：对同一输入文件，validate 和 run 的
accepted/rejected 集合必须一致，且拒绝的 reason_code 必须相同。

场景（计划 R379）：
- 合法整数边界
- 浮点边界
- bool 边界
- 非字符串 ID
- 非法 metadata
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


def _read_jsonl(path: Path) -> list:
    """读取 JSONL 文件为 list of dict（空文件返回空列表）"""
    if not path.exists():
        return []
    result = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                result.append(json.loads(line))
    return result


def _valid_record(message_id: str = "m1") -> dict:
    """构造一条合法记录"""
    return {
        "message_id": message_id,
        "layout_id": "L",
        "direction": "request",
        "payload_hex": "0001",
        "fields": [{"field_index": 0, "start": 0, "end": 2}],
    }


def _run_validate_and_run(tmp_path: Path, records: list) -> tuple:
    """对同一输入运行 validate 和 run，返回 (validate_outputs, run_outputs)

    返回：(validated_lines, rejected_lines) 各自 for validate 和 run
    """
    input_path = tmp_path / "input.jsonl"
    _write_jsonl(input_path, records)

    validate_dir = tmp_path / "validate_out"
    run_dir = tmp_path / "run_out"

    # validate 和 run 都会因 rejection 返回非零退出码，但仍写出产物文件
    main(["validate", str(input_path), "--output-dir", str(validate_dir)])
    # run 用 --allow-partial-input 避免全部拒绝时直接 fail closed 不写产物
    main(["run", str(input_path), "--output-dir", str(run_dir), "--allow-partial-input"])

    v_validated = _read_jsonl(validate_dir / "validated.jsonl")
    v_rejected = _read_jsonl(validate_dir / "rejected.jsonl")
    r_validated = _read_jsonl(run_dir / "validated.jsonl")
    r_rejected = _read_jsonl(run_dir / "rejected.jsonl")

    return (v_validated, v_rejected, r_validated, r_rejected)


def _rejected_reason_codes(rejected_lines: list) -> set:
    """提取 rejected.jsonl 的 reason_code 集合（R383 统一 RejectedRecord 格式）

    R383 后 validate 和 run 都用 RejectedRecord.to_dict() 写入，
    每行含 'reason_code' 字段（如 type_error/invalid_json/duplicate_message_id）。
    """
    return {item.get('reason_code') for item in rejected_lines}


def _validated_message_ids(validated_lines: list) -> set:
    """提取 validated.jsonl 的 message_id 集合"""
    return {item.get('message_id') for item in validated_lines}


class TestValidationRunConsistencyR379:
    """R379：Validate 与 Run 一致性集成测试。

    断言：validate accepted set == run preprocessing accepted set
    非法记录必须在两条路径中得到同一 reason_code。
    """

    def test_r379_legal_int_boundary(self, tmp_path: Path) -> None:
        """合法整数边界：validate 和 run 都接受"""
        records = [
            _valid_record("m1"),
            {
                "message_id": "m2",
                "layout_id": "L",
                "direction": "request",
                "payload_hex": "0203",
                "fields": [{"field_index": 0, "start": 0, "end": 2}],
            },
        ]
        v_validated, v_rejected, r_validated, r_rejected = _run_validate_and_run(
            tmp_path, records
        )

        # 两者都接受全部 2 条
        assert len(v_validated) == 2, f"validate 应接受 2 条，got {len(v_validated)}"
        assert len(r_validated) == 2, f"run 应接受 2 条，got {len(r_validated)}"
        assert _validated_message_ids(v_validated) == _validated_message_ids(r_validated)
        # 两者都无拒绝
        assert len(v_rejected) == 0
        assert len(r_rejected) == 0

    def test_r379_float_boundary(self, tmp_path: Path) -> None:
        """浮点边界：validate 和 run 都拒绝 float field_index"""
        records = [
            _valid_record("good"),
            {
                "message_id": "bad_float",
                "layout_id": "L",
                "direction": "request",
                "payload_hex": "0203",
                "fields": [{"field_index": 0.0, "start": 0, "end": 2}],  # float
            },
        ]
        v_validated, v_rejected, r_validated, r_rejected = _run_validate_and_run(
            tmp_path, records
        )

        # 两者都只接受 1 条（good）
        assert len(v_validated) == 1
        assert len(r_validated) == 1
        assert _validated_message_ids(v_validated) == _validated_message_ids(r_validated)
        assert _validated_message_ids(v_validated) == {"good"}
        # 两者都拒绝 1 条，reason_code 相同
        assert len(v_rejected) == 1
        assert len(r_rejected) == 1
        assert _rejected_reason_codes(v_rejected) == _rejected_reason_codes(r_rejected)

    def test_r379_bool_boundary(self, tmp_path: Path) -> None:
        """bool 边界：validate 和 run 都拒绝 bool end"""
        records = [
            _valid_record("good"),
            {
                "message_id": "bad_bool",
                "layout_id": "L",
                "direction": "request",
                "payload_hex": "0203",
                "fields": [{"field_index": 0, "start": 0, "end": True}],  # bool
            },
        ]
        v_validated, v_rejected, r_validated, r_rejected = _run_validate_and_run(
            tmp_path, records
        )

        assert len(v_validated) == 1
        assert len(r_validated) == 1
        assert _validated_message_ids(v_validated) == {"good"}
        assert len(v_rejected) == 1
        assert len(r_rejected) == 1
        assert _rejected_reason_codes(v_rejected) == _rejected_reason_codes(r_rejected)

    def test_r379_non_string_id(self, tmp_path: Path) -> None:
        """非字符串 ID：validate 和 run 都拒绝 integer message_id"""
        records = [
            _valid_record("good"),
            {
                "message_id": 123,  # int，非法
                "layout_id": "L",
                "direction": "request",
                "payload_hex": "0203",
                "fields": [{"field_index": 0, "start": 0, "end": 2}],
            },
        ]
        v_validated, v_rejected, r_validated, r_rejected = _run_validate_and_run(
            tmp_path, records
        )

        assert len(v_validated) == 1
        assert len(r_validated) == 1
        assert _validated_message_ids(v_validated) == {"good"}
        assert len(v_rejected) == 1
        assert len(r_rejected) == 1
        assert _rejected_reason_codes(v_rejected) == _rejected_reason_codes(r_rejected)

    def test_r379_invalid_metadata(self, tmp_path: Path) -> None:
        """非法 metadata：validate 和 run 都拒绝 list metadata"""
        records = [
            _valid_record("good"),
            {
                "message_id": "bad_meta",
                "layout_id": "L",
                "direction": "request",
                "payload_hex": "0203",
                "fields": [{"field_index": 0, "start": 0, "end": 2}],
                "metadata": [],  # list，非法
            },
        ]
        v_validated, v_rejected, r_validated, r_rejected = _run_validate_and_run(
            tmp_path, records
        )

        assert len(v_validated) == 1
        assert len(r_validated) == 1
        assert _validated_message_ids(v_validated) == {"good"}
        assert len(v_rejected) == 1
        assert len(r_rejected) == 1
        assert _rejected_reason_codes(v_rejected) == _rejected_reason_codes(r_rejected)

    def test_r379_mixed_records_full_consistency(self, tmp_path: Path) -> None:
        """混合记录：validate 和 run 的 accepted/rejected 集合完全一致

        构造 5 条记录：2 合法 + 3 非法（float/bool/int ID）。
        验证 validate 和 run 的 accepted message_id 集合相同，
        rejected reason_code 集合相同。
        """
        records = [
            _valid_record("good_1"),
            {
                "message_id": "bad_float",
                "layout_id": "L",
                "direction": "request",
                "payload_hex": "0203",
                "fields": [{"field_index": 0.0, "start": 0, "end": 2}],  # float
            },
            _valid_record("good_2"),
            {
                "message_id": "bad_bool",
                "layout_id": "L",
                "direction": "request",
                "payload_hex": "0203",
                "fields": [{"field_index": 0, "start": 0, "end": True}],  # bool
            },
            {
                "message_id": 999,  # int，非法
                "layout_id": "L",
                "direction": "request",
                "payload_hex": "0203",
                "fields": [{"field_index": 0, "start": 0, "end": 2}],
            },
        ]
        v_validated, v_rejected, r_validated, r_rejected = _run_validate_and_run(
            tmp_path, records
        )

        # accepted 集合一致（2 条合法）
        v_ids = _validated_message_ids(v_validated)
        r_ids = _validated_message_ids(r_validated)
        assert v_ids == r_ids, f"accepted 集合不一致: validate={v_ids}, run={r_ids}"
        assert v_ids == {"good_1", "good_2"}

        # rejected 集合一致（3 条非法）
        assert len(v_rejected) == 3
        assert len(r_rejected) == 3
        v_codes = _rejected_reason_codes(v_rejected)
        r_codes = _rejected_reason_codes(r_rejected)
        assert v_codes == r_codes, (
            f"rejected reason_code 集合不一致: validate={v_codes}, run={r_codes}"
        )

    def test_r379_all_invalid_consistency(self, tmp_path: Path) -> None:
        """全部非法：validate 和 run 都接受 0 条，拒绝集合一致"""
        records = [
            {
                "message_id": 1,  # int
                "layout_id": "L",
                "direction": "request",
                "payload_hex": "0203",
                "fields": [{"field_index": 0, "start": 0, "end": 2}],
            },
            {
                "message_id": "bad_float",
                "layout_id": "L",
                "direction": "request",
                "payload_hex": "0203",
                "fields": [{"field_index": 0.0, "start": 0, "end": 2}],  # float
            },
        ]
        v_validated, v_rejected, r_validated, r_rejected = _run_validate_and_run(
            tmp_path, records
        )

        # 两者都接受 0 条
        assert len(v_validated) == 0
        assert len(r_validated) == 0
        # 两者都拒绝 2 条，reason_code 集合一致
        assert len(v_rejected) == 2
        assert len(r_rejected) == 2
        assert _rejected_reason_codes(v_rejected) == _rejected_reason_codes(r_rejected)
