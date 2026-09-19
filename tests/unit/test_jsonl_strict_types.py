"""R377：JSONL 严格类型拒绝测试

确认 JSONL 入口不会绕过 dataclass 的严格校验（V3 审计 HIGH-1）。

R374（FieldSpan）+ R376（MessageRecord）已让 contracts 层做严格类型校验。
本测试验证：通过 JSONL 入口（read_jsonl_file → parse_json_record）输入的
非法类型记录，必须被拒绝并进入 rejected_records，不得静默接受或崩溃。

场景（计划 R377）：
- float field_index
- float start
- bool end
- integer message_id
- integer layout_id
- string input_order
- integer session_id
- list metadata
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from semantic_detector.io.jsonl import read_jsonl_file


def _write_temp_jsonl(content: str) -> str:
    """写入临时 JSONL 文件，返回路径"""
    f = tempfile.NamedTemporaryFile(
        mode='w', suffix='.jsonl', delete=False, encoding='utf-8'
    )
    f.write(content)
    f.close()
    return f.name


def _make_valid_record_json(message_id: str = "m1") -> dict:
    """构造一条合法记录 dict（用于混入非法记录的测试）"""
    return {
        "message_id": message_id,
        "layout_id": "L",
        "direction": "request",
        "payload_hex": "0001",
        "fields": [{"field_index": 0, "start": 0, "end": 2}],
    }


class TestJsonlStrictTypesR377:
    """R377：JSONL 入口严格类型拒绝测试。

    每个测试构造一条含非法类型的 JSONL 行，验证它被 read_jsonl_file 拒绝。
    """

    def setup_method(self):
        self._paths = []

    def teardown_method(self):
        for p in self._paths:
            try:
                os.unlink(p)
            except OSError:
                pass

    def _read(self, record_dict: dict):
        """把单条记录写入临时文件并读回"""
        path = _write_temp_jsonl(json.dumps(record_dict) + '\n')
        self._paths.append(path)
        return read_jsonl_file(path)

    def test_r377_rejects_float_field_index(self) -> None:
        """float field_index 必须被 JSONL 入口拒绝"""
        rec = _make_valid_record_json()
        rec["fields"][0]["field_index"] = 0.0  # float
        valid, rejected = self._read(rec)
        assert len(valid) == 0, "float field_index 不应进入 valid"
        assert len(rejected) == 1, "float field_index 应被拒绝"

    def test_r377_rejects_float_start(self) -> None:
        """float start 必须被 JSONL 入口拒绝"""
        rec = _make_valid_record_json()
        rec["fields"][0]["start"] = 0.0  # float
        valid, rejected = self._read(rec)
        assert len(valid) == 0
        assert len(rejected) == 1

    def test_r377_rejects_bool_end(self) -> None:
        """bool end 必须被 JSONL 入口拒绝（bool 不算 int）"""
        rec = _make_valid_record_json()
        rec["fields"][0]["end"] = True  # bool
        valid, rejected = self._read(rec)
        assert len(valid) == 0
        assert len(rejected) == 1

    def test_r377_rejects_integer_message_id(self) -> None:
        """integer message_id 必须被 JSONL 入口拒绝（必须是 str）"""
        rec = _make_valid_record_json()
        rec["message_id"] = 123  # int
        valid, rejected = self._read(rec)
        assert len(valid) == 0
        assert len(rejected) == 1

    def test_r377_rejects_integer_layout_id(self) -> None:
        """integer layout_id 必须被 JSONL 入口拒绝（必须是 str）"""
        rec = _make_valid_record_json()
        rec["layout_id"] = 456  # int
        valid, rejected = self._read(rec)
        assert len(valid) == 0
        assert len(rejected) == 1

    def test_r377_rejects_string_input_order(self) -> None:
        """string input_order 必须被 JSONL 入口拒绝（必须是 int）"""
        rec = _make_valid_record_json()
        rec["input_order"] = "1"  # str
        valid, rejected = self._read(rec)
        assert len(valid) == 0
        assert len(rejected) == 1

    def test_r377_rejects_integer_session_id(self) -> None:
        """integer session_id 必须被 JSONL 入口拒绝（必须是 str 或 None）"""
        rec = _make_valid_record_json()
        rec["session_id"] = 789  # int
        valid, rejected = self._read(rec)
        assert len(valid) == 0
        assert len(rejected) == 1

    def test_r377_rejects_list_metadata(self) -> None:
        """list metadata 必须被 JSONL 入口拒绝（必须是 dict 或 None）"""
        rec = _make_valid_record_json()
        rec["metadata"] = []  # list
        valid, rejected = self._read(rec)
        assert len(valid) == 0
        assert len(rejected) == 1

    def test_r377_valid_record_still_accepted(self) -> None:
        """合法记录仍被接受（边界测试，确保严格校验不误伤）"""
        rec = _make_valid_record_json()
        valid, rejected = self._read(rec)
        assert len(valid) == 1, "合法记录应被接受"
        assert len(rejected) == 0
        assert valid[0].message_id == "m1"

    def test_r377_mixed_valid_and_invalid_records(self) -> None:
        """混合输入：合法记录保留，非法记录拒绝"""
        valid_rec = _make_valid_record_json("good")
        invalid_rec = _make_valid_record_json("bad")
        invalid_rec["message_id"] = 999  # int，非法

        content = (
            json.dumps(valid_rec) + '\n' +
            json.dumps(invalid_rec) + '\n'
        )
        path = _write_temp_jsonl(content)
        self._paths.append(path)
        valid, rejected = read_jsonl_file(path)

        assert len(valid) == 1, "只有 1 条合法记录应被接受"
        assert valid[0].message_id == "good"
        assert len(rejected) == 1, "1 条非法记录应被拒绝"


# ---------------------------------------------------------------------------
# R378：JSONL 解析器类型保持测试
#
# R378 目标：确保 JSONL parser 不做静默类型转换（如 str(123)、int("1")）。
# jsonl.py 的 parse_json_record 已直接传值给 FieldSpan/MessageRecord，
# 不做 str()/int() 隐式转换。本测试验证：
# 1. JSON 原始类型被原样传递到 contracts 层
# 2. 非法类型在 contracts 层被拒绝（不因 JSONL 入口转换而变合法）
# 3. 合法类型原样保留（如 input_order=5 是 int，不被转为 str）
# ---------------------------------------------------------------------------


class TestJsonlTypePassthroughR378:
    """R378：JSONL 解析器类型保持测试。

    验证 JSONL 入口不做 str()/int()/float() 等隐式转换，JSON 原始类型
    原样传递到 contracts 层。如果 JSONL 入口做了 str(123) 转换，
    下面的拒绝测试就会失败（转换后类型变合法）。
    """

    def setup_method(self):
        self._paths = []

    def teardown_method(self):
        for p in self._paths:
            try:
                os.unlink(p)
            except OSError:
                pass

    def _read(self, record_dict: dict):
        """把单条记录写入临时文件并读回"""
        path = _write_temp_jsonl(json.dumps(record_dict) + '\n')
        self._paths.append(path)
        return read_jsonl_file(path)

    def test_r378_rejects_integer_direction(self) -> None:
        """integer direction 必须被拒绝（不得 str() 转换为 "123" 再匹配）"""
        rec = _make_valid_record_json()
        rec["direction"] = 123  # int
        valid, rejected = self._read(rec)
        assert len(valid) == 0
        assert len(rejected) == 1

    def test_r378_rejects_bool_direction(self) -> None:
        """bool direction 必须被拒绝（True 不应被转为 "True" 或 "1"）"""
        rec = _make_valid_record_json()
        rec["direction"] = True  # bool
        valid, rejected = self._read(rec)
        assert len(valid) == 0
        assert len(rejected) == 1

    def test_r378_rejects_bool_input_order(self) -> None:
        """bool input_order 必须被拒绝（bool 不算 int）"""
        rec = _make_valid_record_json()
        rec["input_order"] = True  # bool
        valid, rejected = self._read(rec)
        assert len(valid) == 0
        assert len(rejected) == 1

    def test_r378_rejects_float_input_order(self) -> None:
        """float input_order 必须被拒绝（不得 int() 转换）"""
        rec = _make_valid_record_json()
        rec["input_order"] = 1.0  # float
        valid, rejected = self._read(rec)
        assert len(valid) == 0
        assert len(rejected) == 1

    def test_r378_rejects_none_message_id(self) -> None:
        """null message_id 必须被拒绝（不得 str(None) 转换为 "None"）"""
        rec = _make_valid_record_json()
        rec["message_id"] = None  # null
        valid, rejected = self._read(rec)
        assert len(valid) == 0
        assert len(rejected) == 1

    def test_r378_rejects_string_fields(self) -> None:
        """string fields 必须被拒绝（fields 必须是 list）"""
        rec = _make_valid_record_json()
        rec["fields"] = "not a list"  # str
        valid, rejected = self._read(rec)
        assert len(valid) == 0
        assert len(rejected) == 1

    def test_r378_rejects_list_payload_hex(self) -> None:
        """list payload_hex 必须被拒绝（必须是 str）"""
        rec = _make_valid_record_json()
        rec["payload_hex"] = ["00", "01"]  # list
        valid, rejected = self._read(rec)
        assert len(valid) == 0
        assert len(rejected) == 1

    def test_r378_valid_types_passthrough_unchanged(self) -> None:
        """合法类型原样传递到 MessageRecord（类型保持验证）

        构造一条全字段合法记录，验证读回的 MessageRecord 字段类型与
        JSON 原始类型一致（不被 JSONL 入口转换）。
        """
        rec = {
            "message_id": "msg_001",        # str
            "layout_id": "layout_A",         # str
            "direction": "request",          # str -> Direction
            "payload_hex": "0001",           # str -> bytes
            "fields": [                      # list -> tuple
                {"field_index": 0, "start": 0, "end": 2}  # int
            ],
            "input_order": 5,                # int
            "session_id": "sess_01",         # str
            "pair_id": "pair_01",            # str
            "metadata": {"key": "value"},    # dict
        }
        valid, rejected = self._read(rec)
        assert len(valid) == 1, "合法记录应被接受"
        assert len(rejected) == 0

        record = valid[0]
        # 类型保持验证
        assert isinstance(record.message_id, str)
        assert record.message_id == "msg_001"
        assert isinstance(record.layout_id, str)
        assert isinstance(record.payload, bytes)
        assert isinstance(record.fields, tuple)
        assert isinstance(record.fields[0].field_index, int)
        assert type(record.fields[0].field_index) is int  # 严格 int，非 bool
        assert isinstance(record.input_order, int)
        assert type(record.input_order) is int  # 严格 int
        assert isinstance(record.session_id, str)
        assert isinstance(record.pair_id, str)
        assert isinstance(record.metadata, dict)

    def test_r378_default_input_order_is_strict_int(self) -> None:
        """缺省 input_order 必须是严格 int（0），不是 bool/float"""
        rec = _make_valid_record_json()
        # 不设置 input_order，让 JSONL 入口使用默认值 0
        valid, rejected = self._read(rec)
        assert len(valid) == 1
        assert type(valid[0].input_order) is int
        assert valid[0].input_order == 0
