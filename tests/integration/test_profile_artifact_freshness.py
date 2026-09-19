"""R391：Profile 命令产物新鲜度测试

复现 MEDIUM-3：cmd_profile 用 `if rejections:` 条件写入 rejected_groups.jsonl，
第二次全合法时不写 → 旧 rejected_groups.jsonl 残留。

R391 修复后（与 cmd_validate 对齐，无条件写入）：
- 第一次 profile 产生 group rejection → rejected_groups.jsonl 有内容
- 第二次 profile 全合法 → rejected_groups.jsonl 必须为空文件（覆盖旧文件）
- profiles 属于本轮（field_profiles.jsonl 覆盖旧文件）
"""

import hashlib
import json
from pathlib import Path

import pytest

from semantic_detector.cli import main


def _write_jsonl(path: Path, records: list) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _make_valid_record(message_id: str = "m1", layout_id: str = "L1") -> dict:
    """构造一条合法记录（单字段，可通过组级字段数校验）"""
    return {
        "message_id": message_id,
        "layout_id": layout_id,
        "direction": "request",
        "payload_hex": "0001",
        "fields": [{"field_index": 0, "start": 0, "end": 2}],
    }


def _make_group_mismatch_records() -> list:
    """构造同组（layout_id+direction）但字段数不一致的记录

    prepare_records_for_profiling 会拒绝该组（group rejection）。
    """
    return [
        {
            "message_id": "m1",
            "layout_id": "L1",
            "direction": "request",
            "payload_hex": "000102",
            "fields": [{"field_index": 0, "start": 0, "end": 2}],
        },
        {
            "message_id": "m2",
            "layout_id": "L1",
            "direction": "request",
            "payload_hex": "0001020304",
            "fields": [
                {"field_index": 0, "start": 0, "end": 2},
                {"field_index": 1, "start": 2, "end": 4},
            ],
        },
    ]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


class TestProfileArtifactFreshnessR391:
    """R391：Profile 命令产物新鲜度测试

    复现 MEDIUM-3：cmd_profile 条件写入 rejected_groups.jsonl，
    第二次全合法时旧文件残留。
    """

    def test_r391_second_profile_overwrites_old_rejected_groups(self, tmp_path: Path) -> None:
        """R391: 第二次 profile 全合法时 rejected_groups.jsonl 必须为空

        场景（R391 计划）：
        1. 第一次 profile 产生 group rejection → rejected_groups.jsonl 有内容
        2. 第二次 profile 全合法 → rejected_groups.jsonl 必须为空

        修复前：`if rejections:` 条件写入，第二次不写 → 旧文件残留
        修复后：无条件写入，第二次写空文件覆盖旧文件
        """
        # 第一次 profile：产生 group rejection
        mismatch_input = tmp_path / "mismatch.jsonl"
        _write_jsonl(mismatch_input, _make_group_mismatch_records())
        output_dir = tmp_path / "output"

        rc1 = main(["profile", str(mismatch_input), "--output-dir", str(output_dir)])
        assert rc1 != 0, "第一次 profile 含 group mismatch 应 exit 非零"

        rejected_groups_path = output_dir / "rejected_groups.jsonl"
        assert rejected_groups_path.exists(), "第一次 profile 应生成 rejected_groups.jsonl"
        first_content = rejected_groups_path.read_text(encoding="utf-8").strip()
        assert first_content, "第一次 rejected_groups.jsonl 应有内容（group rejection）"

        # 验证第一次内容可解析
        first_lines = [l for l in first_content.splitlines() if l.strip()]
        for line in first_lines:
            item = json.loads(line)
            assert "reason_code" in item
            assert "group_key" in item

        first_sha = _sha256(rejected_groups_path)

        # 第二次 profile：全合法输入（无 group rejection）
        valid_input = tmp_path / "valid.jsonl"
        _write_jsonl(valid_input, [
            _make_valid_record("ok1"),
            _make_valid_record("ok2", layout_id="L2"),
        ])

        rc2 = main(["profile", str(valid_input), "--output-dir", str(output_dir)])
        assert rc2 == 0, f"第二次 profile 全合法应 exit 0，got rc={rc2}"

        # 断言 1: rejected_groups.jsonl 必须为空（覆盖旧文件）
        second_content = rejected_groups_path.read_text(encoding="utf-8").strip()
        assert second_content == "", (
            f"R391: 第二次全合法 profile 后 rejected_groups.jsonl 必须为空，"
            f"实际内容: {second_content}"
        )

        # 断言 2: SHA 必须不同（旧文件被覆盖）
        second_sha = _sha256(rejected_groups_path)
        assert second_sha != first_sha, (
            "R391: 第二次 profile 后 rejected_groups.jsonl SHA 必须不同（旧文件未覆盖）"
        )

    def test_r391_second_profile_field_profiles_belong_to_current_run(self, tmp_path: Path) -> None:
        """R391: 第二次 profile 的 field_profiles.jsonl 必须属于本轮

        场景：
        1. 第一次 profile 用 L1（1 字段）→ field_profiles.jsonl 有 L1 画像
        2. 第二次 profile 用 L2（1 字段）→ field_profiles.jsonl 必须是 L2 画像（不是 L1）

        验证 profiles 属于本轮（R391 计划要求）。
        """
        # 第一次 profile：L1
        input1 = tmp_path / "input1.jsonl"
        _write_jsonl(input1, [_make_valid_record("m1", layout_id="L1")])
        output_dir = tmp_path / "output"

        rc1 = main(["profile", str(input1), "--output-dir", str(output_dir)])
        assert rc1 == 0

        profiles_path = output_dir / "field_profiles.jsonl"
        first_profiles = profiles_path.read_text(encoding="utf-8").strip()
        assert first_profiles, "第一次 field_profiles.jsonl 应有内容"
        first_layout_ids = set()
        for line in first_profiles.splitlines():
            if line.strip():
                item = json.loads(line)
                first_layout_ids.add(item.get("layout_id"))

        # 第二次 profile：L2
        input2 = tmp_path / "input2.jsonl"
        _write_jsonl(input2, [_make_valid_record("m2", layout_id="L2")])

        rc2 = main(["profile", str(input2), "--output-dir", str(output_dir)])
        assert rc2 == 0

        second_profiles = profiles_path.read_text(encoding="utf-8").strip()
        assert second_profiles, "第二次 field_profiles.jsonl 应有内容"
        second_layout_ids = set()
        for line in second_profiles.splitlines():
            if line.strip():
                item = json.loads(line)
                second_layout_ids.add(item.get("layout_id"))

        # 断言：第二次的 layout_id 与第一次不同（profiles 属于本轮）
        assert first_layout_ids != second_layout_ids, (
            f"R391: 第二次 field_profiles 应属于本轮（layout_id 不同），"
            f"第一次={first_layout_ids}, 第二次={second_layout_ids}"
        )
        assert "L2" in second_layout_ids, (
            f"第二次应包含 L2 画像，got {second_layout_ids}"
        )

    def test_r391_rejected_groups_empty_when_no_mismatch(self, tmp_path: Path) -> None:
        """R391: 全合法 profile 时 rejected_groups.jsonl 必须为空文件

        正向验证：无 group rejection 时 rejected_groups.jsonl 是空文件（不是不存在）。
        修复前：`if rejections:` 不写 → 文件不存在或残留旧内容
        修复后：无条件写入空文件
        """
        valid_input = tmp_path / "valid.jsonl"
        _write_jsonl(valid_input, [
            _make_valid_record("m1"),
            _make_valid_record("m2", layout_id="L2"),
        ])
        output_dir = tmp_path / "output"

        rc = main(["profile", str(valid_input), "--output-dir", str(output_dir)])
        assert rc == 0

        rejected_groups_path = output_dir / "rejected_groups.jsonl"
        # 文件必须存在（不是不存在）
        assert rejected_groups_path.exists(), (
            "R391: 全合法 profile 后 rejected_groups.jsonl 必须存在（空文件）"
        )
        # 内容必须为空
        content = rejected_groups_path.read_text(encoding="utf-8").strip()
        assert content == "", (
            f"R391: 全合法 profile 时 rejected_groups.jsonl 必须为空，got: {content}"
        )

    def test_r391_rejected_jsonl_also_overwritten(self, tmp_path: Path) -> None:
        """R391: 第二次 profile 全合法时 rejected.jsonl 也必须为空

        验证 rejected.jsonl（JSON 级拒绝）也被覆盖为空文件。
        export_rejected_records_unified 已是无条件写入，此测试作为对照。
        """
        # 第一次 profile：含 invalid JSON → rejected.jsonl 有内容
        mismatch_input = tmp_path / "mismatch.jsonl"
        with open(mismatch_input, "w", encoding="utf-8") as f:
            f.write(json.dumps(_make_valid_record("ok")) + "\n")
            f.write('{"message_id": "bad", invalid json}\n')
        output_dir = tmp_path / "output"

        rc1 = main(["profile", str(mismatch_input), "--output-dir", str(output_dir)])
        assert rc1 != 0

        rejected_path = output_dir / "rejected.jsonl"
        assert rejected_path.exists()
        first_content = rejected_path.read_text(encoding="utf-8").strip()
        assert first_content, "第一次 rejected.jsonl 应有内容"

        # 第二次 profile：全合法
        valid_input = tmp_path / "valid.jsonl"
        _write_jsonl(valid_input, [_make_valid_record("ok1"), _make_valid_record("ok2", layout_id="L2")])

        rc2 = main(["profile", str(valid_input), "--output-dir", str(output_dir)])
        assert rc2 == 0

        # rejected.jsonl 必须为空
        second_content = rejected_path.read_text(encoding="utf-8").strip()
        assert second_content == "", (
            f"R391: 第二次全合法 profile 后 rejected.jsonl 必须为空，got: {second_content}"
        )
