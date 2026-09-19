"""R040: JSONL 验证与导出集成测试

混合输入（有效记录 + 无效记录 + 重复 ID）→ read_jsonl_file →
export_validated_records / export_rejected_records → 验证产物正确。
"""

import json
import os
import tempfile

from semantic_detector.io.jsonl import read_jsonl_file, parse_json_record
from semantic_detector.io.exporters import (
    export_validated_records,
    export_rejected_records,
    atomic_write_file,
    hash_file_sha256,
)


# ---------------------------------------------------------------------------
# 辅助：写临时 JSONL 文件
# ---------------------------------------------------------------------------

def _write_jsonl(lines, path):
    with open(path, "w", encoding="utf-8") as f:
        for obj in lines:
            if isinstance(obj, str):
                f.write(obj + "\n")
            else:
                f.write(json.dumps(obj, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# 合法消息的工厂函数
# ---------------------------------------------------------------------------

def _good_msg(msg_id="msg-001", layout="L1", direction="request", payload_hex="aabbccdd"):
    """构造一条完全合法的消息 JSON 对象"""
    return {
        "message_id": msg_id,
        "layout_id": layout,
        "direction": direction,
        "payload_hex": payload_hex,
        "fields": [
            {"field_index": 0, "start": 0, "end": 2},
            {"field_index": 1, "start": 2, "end": 4},
        ],
    }


# ===================================================================
# 测试用例
# ===================================================================


class TestFullValidationFlow:
    """混合输入 → 读取 → 分流 → 导出 → 验证产物"""

    def test_mixed_input_separates_valid_and_rejected(self, tmp_path):
        input_file = str(tmp_path / "input.jsonl")
        valid_out = str(tmp_path / "valid.jsonl")
        reject_out = str(tmp_path / "rejected.jsonl")

        # 构造混合输入
        lines = [
            _good_msg("msg-001"),                        # 0: 有效
            _good_msg("msg-002", payload_hex="11223344", direction="response"),  # 1: 有效
            {"message_id": "msg-bad"},                   # 2: 缺少必要字段 → rejected
            _good_msg("msg-003"),                        # 3: 有效
            _good_msg("msg-001"),                        # 4: 重复 ID → rejected
            "not json at all !!!",                          # 5: 非法 JSON → rejected
            _good_msg("msg-004", direction="unknown"),   # 6: 有效（unknown 方向）
        ]
        _write_jsonl(lines, input_file)

        valid, rejected = read_jsonl_file(input_file)

        # 有效: msg-001, msg-002, msg-003, msg-004
        assert len(valid) == 4
        assert [r.message_id for r in valid] == [
            "msg-001", "msg-002", "msg-003", "msg-004"
        ]

        # 拒绝: line 2(缺字段), line 4(重复), line 5(非法JSON)
        assert len(rejected) == 3

        # 导出有效记录
        export_validated_records(valid, valid_out)
        assert os.path.exists(valid_out)
        with open(valid_out, "r", encoding="utf-8") as f:
            valid_lines = [l for l in f if l.strip()]
        assert len(valid_lines) == 4

        # 每行可解析且 payload_hex 不丢失
        for line_str in valid_lines:
            parsed = json.loads(line_str)
            assert "message_id" in parsed
            assert "payload_hex" in parsed
            assert "fields" in parsed
            assert len(parsed["fields"]) > 0

        # 导出拒绝记录
        export_rejected_records(rejected, reject_out)
        assert os.path.exists(reject_out)
        with open(reject_out, "r", encoding="utf-8") as f:
            reject_lines = [l for l in f if l.strip()]
        assert len(reject_lines) == 3

        for line_str in reject_lines:
            parsed = json.loads(line_str)
            assert "line_number" in parsed
            assert "code" in parsed

    def test_empty_file_yields_nothing(self, tmp_path):
        input_file = str(tmp_path / "empty.jsonl")
        valid_out = str(tmp_path / "valid.jsonl")
        reject_out = str(tmp_path / "rejected.jsonl")

        with open(input_file, "w") as f:
            pass  # 空文件

        valid, rejected = read_jsonl_file(input_file)
        assert len(valid) == 0
        assert len(rejected) == 0

        export_validated_records(valid, valid_out)
        export_rejected_records(rejected, reject_out)

        with open(valid_out, "r") as f:
            assert f.read() == ""
        with open(reject_out, "r") as f:
            assert f.read() == ""

    def test_validated_export_roundtrip_preserves_payload(self, tmp_path):
        """导出 → 重新读入 → payload_hex 一致"""
        input_file = str(tmp_path / "input.jsonl")
        valid_out = str(tmp_path / "valid.jsonl")

        payload_hex = "deadbeef01020304"
        lines = [_good_msg("msg-rt", payload_hex=payload_hex, direction="response")]
        _write_jsonl(lines, input_file)

        valid, _ = read_jsonl_file(input_file)
        export_validated_records(valid, valid_out)

        # 重新读入
        valid2, rejected2 = read_jsonl_file(valid_out)
        assert len(valid2) == 1
        assert len(rejected2) == 0
        assert valid2[0].payload.hex() == payload_hex
        assert valid2[0].message_id == "msg-rt"

    def test_hash_matches_validated_file(self, tmp_path):
        """导出文件的 SHA-256 可计算且非空"""
        valid_out = str(tmp_path / "valid.jsonl")
        lines = [_good_msg("msg-h1"), _good_msg("msg-h2")]
        valid_records = [parse_json_record(json.dumps(m)) for m in lines]
        export_validated_records(valid_records, valid_out)

        h = hash_file_sha256(valid_out)
        assert len(h) == 64  # SHA-256 hex digest length
        assert all(c in "0123456789abcdef" for c in h)

    def test_atomic_write_then_read(self, tmp_path):
        """atomic_write_file 写入后可被 read_jsonl_file 正确读取"""
        target = str(tmp_path / "atomic.jsonl")
        line1 = json.dumps(_good_msg("msg-a1"))
        line2 = json.dumps(_good_msg("msg-a2"))
        content = line1 + "\n" + line2 + "\n"

        atomic_write_file(target, content)
        valid, rejected = read_jsonl_file(target)

        assert len(valid) == 2
        assert len(rejected) == 0
        assert valid[0].message_id == "msg-a1"
        assert valid[1].message_id == "msg-a2"
