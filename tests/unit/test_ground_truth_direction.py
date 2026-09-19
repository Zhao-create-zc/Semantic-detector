"""R396：非法 direction 的 Ground Truth 导入失败测试

复现 HIGH-5（Ground Truth 侧）：ground truth 中 `direction=foo` 被静默接受的问题。

R396 计划要求（修复前测试应真实失败，本轮不修改生产代码）：
- Ground Truth 采用相同严格规则
- 合法值仅允许：request/response/unknown
- 推荐只接受规范小写，不自动转化任意字符串

当前行为（HIGH-5 缺陷）：
- read_ground_truth_jsonl 第 139 行：direction = data.get('direction', 'unknown')
  直接取值，不校验合法性
- validate_ground_truth 不检查 direction 合法性
  （只检查 truth_id/FieldKey 唯一性 + label 合法性）
- GroundTruthRecord.field_key 属性第 70-73 行：非法 direction 降级为 Direction.UNKNOWN

本测试验证：非法 direction 不应被静默接受。
"""

import json
from pathlib import Path

import pytest

from semantic_detector.evaluation.ground_truth import (
    read_ground_truth_jsonl,
    validate_ground_truth,
)
from semantic_detector.contracts import Direction, ALLOWED_DIRECTIONS


def _write_truth_line(path: Path, direction_value) -> None:
    """写一行 GroundTruthRecord 格式的 JSONL，direction 用指定值"""
    truth_dict = {
        "truth_id": 1,
        "field_index": 0,
        "semantic_label": "constant",
        "confidence": 1.0,
        "is_hard_evidence": True,
        "layout_id": "L1",
        "direction": direction_value,
    }
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(truth_dict, ensure_ascii=False) + "\n")


class TestGroundTruthDirectionR396:
    """R396：非法 direction 的 Ground Truth 导入失败测试

    复现 HIGH-5（Ground Truth 侧）：非法 direction 被静默接受。
    修复前：read_ground_truth_jsonl 不拒绝非法 direction，直接构造 GroundTruthRecord。
    修复后（R398）：非法 direction 应进入 rejection，不构造 GroundTruthRecord。
    """

    def test_r396_direction_foo_must_be_rejected(self, tmp_path: Path) -> None:
        """R396: direction=foo 必须被拒绝，不静默接受

        当前缺陷：read_ground_truth_jsonl 把 "foo" 直接赋值给 record.direction，
        不拒绝，返回 1 个 valid record。

        修复后预期：direction=foo 应触发 rejection，不构造 GroundTruthRecord。
        """
        truth_path = tmp_path / "truth.jsonl"
        _write_truth_line(truth_path, "foo")

        valid_records, rejected_records = read_ground_truth_jsonl(str(truth_path))

        # R396 断言：非法 direction 必须被拒绝
        # 当前缺陷：valid_records 非空（1 个），rejected_records 为空
        assert len(valid_records) == 0, (
            f"R396: direction=foo 必须被拒绝，不应构造 GroundTruthRecord。"
            f"当前返回 {len(valid_records)} 个 valid record（被静默接受）。"
        )
        assert len(rejected_records) == 1, (
            f"R396: direction=foo 应产生 1 条 rejection，"
            f"got {len(rejected_records)} rejections。"
        )
        # rejection 的 reason_code 应标识为 direction 问题
        assert rejected_records[0]["reason_code"] == "invalid_direction", (
            f"R396: reason_code 应为 invalid_direction，"
            f"got {rejected_records[0]['reason_code']}"
        )

    def test_r396_direction_bar_must_be_rejected(self, tmp_path: Path) -> None:
        """R396: direction=bar 必须被拒绝

        同 test_r396_direction_foo_must_be_rejected，验证另一个非法值。
        """
        truth_path = tmp_path / "truth.jsonl"
        _write_truth_line(truth_path, "bar")

        valid_records, rejected_records = read_ground_truth_jsonl(str(truth_path))

        assert len(valid_records) == 0, (
            f"R396: direction=bar 必须被拒绝，不应构造 GroundTruthRecord。"
            f"当前返回 {len(valid_records)} 个 valid record。"
        )
        assert len(rejected_records) == 1
        assert rejected_records[0]["reason_code"] == "invalid_direction"

    def test_r396_direction_uppercase_request_rejected(self, tmp_path: Path) -> None:
        """R396: direction=Request（大写）必须被拒绝（不自动转化任意字符串）

        R396 计划："推荐只接受规范小写，不自动转化任意字符串"
        当前缺陷：大写 "Request" 不在 ALLOWED_DIRECTIONS 中，但会被静默接受
        （field_key 降级为 UNKNOWN）。
        """
        truth_path = tmp_path / "truth.jsonl"
        _write_truth_line(truth_path, "Request")

        valid_records, rejected_records = read_ground_truth_jsonl(str(truth_path))

        # R396 断言：大写 "Request" 必须被拒绝（不自动转小写）
        assert len(valid_records) == 0, (
            f"R396: direction=Request（大写）必须被拒绝，不应自动转小写。"
            f"当前返回 {len(valid_records)} 个 valid record。"
        )
        assert len(rejected_records) == 1
        assert rejected_records[0]["reason_code"] == "invalid_direction"

    def test_r396_direction_foo_not_silently_downgraded_in_field_key(self, tmp_path: Path) -> None:
        """R396: direction=foo 不应在 field_key 中被静默降级为 unknown

        当前缺陷：GroundTruthRecord.field_key 属性第 70-73 行
        把非法 direction 降级为 Direction.UNKNOWN。

        R396 断言：如果非法 direction 被错误接受，其 field_key.direction
        不应是 Direction.UNKNOWN（因为 "foo" 不应变成 UNKNOWN）。
        但更严格地：非法 direction 根本不应被接受。
        """
        truth_path = tmp_path / "truth.jsonl"
        _write_truth_line(truth_path, "foo")

        valid_records, _ = read_ground_truth_jsonl(str(truth_path))

        # 当前缺陷：valid_records 非空，field_key.direction == Direction.UNKNOWN
        # R396 断言：不应有 direction=UNKNOWN 的 field_key（"foo" 不应变成 UNKNOWN）
        unknown_downgraded = [
            r for r in valid_records
            if r.field_key.direction == Direction.UNKNOWN
        ]
        assert len(unknown_downgraded) == 0, (
            f"R396: direction=foo 不应被静默降级为 Direction.UNKNOWN。"
            f"发现 {len(unknown_downgraded)} 个 field_key.direction=UNKNOWN 的 record。"
        )

    def test_r396_valid_directions_still_accepted(self, tmp_path: Path) -> None:
        """R396 正向对照：合法 direction 仍被接受

        验证修复后不会误伤合法 direction（request/response/unknown）。
        """
        for valid_dir in ["request", "response", "unknown"]:
            truth_path = tmp_path / f"truth_{valid_dir}.jsonl"
            _write_truth_line(truth_path, valid_dir)

            valid_records, rejected_records = read_ground_truth_jsonl(str(truth_path))
            assert len(valid_records) == 1, (
                f"R396 正向对照：direction={valid_dir} 应被接受，"
                f"got {len(valid_records)} valid records"
            )
            assert len(rejected_records) == 0, (
                f"R396 正向对照：direction={valid_dir} 不应被拒绝，"
                f"got {len(rejected_records)} rejections"
            )
            assert valid_records[0].direction == valid_dir, (
                f"R396 正向对照：direction={valid_dir} 应保持原值，"
                f"got {valid_records[0].direction}"
            )

    def test_r396_validate_ground_truth_rejects_invalid_direction(self, tmp_path: Path) -> None:
        """R396/R397: validate_ground_truth 路径——非法 direction 在 read 阶段已拒绝

        修复前缺陷：read_ground_truth_jsonl 错误接受非法 direction，
        validate_ground_truth 也不检查 direction 合法性。

        R397 修复后：read_ground_truth_jsonl 已在读取阶段拒绝非法 direction，
        返回 0 个 valid record + 1 个 rejection（reason_code=invalid_direction）。
        validate_ground_truth 不会收到非法 direction。
        """
        truth_path = tmp_path / "truth.jsonl"
        _write_truth_line(truth_path, "foo")

        # R397 修复后：read 阶段已拒绝非法 direction
        valid_records, rejected_records = read_ground_truth_jsonl(str(truth_path))

        # R397 断言：read 阶段已拒绝，valid_records 为空
        assert len(valid_records) == 0, (
            f"R397: read_ground_truth_jsonl 应拒绝非法 direction=foo，"
            f"不应返回 valid record。当前返回 {len(valid_records)} 个。"
        )
        # R397 断言：read 阶段产生 1 个 rejection，reason_code=invalid_direction
        assert len(rejected_records) == 1, (
            f"R397: read_ground_truth_jsonl 应产生 1 条 rejection，"
            f"got {len(rejected_records)} rejections"
        )
        assert rejected_records[0]["reason_code"] == "invalid_direction", (
            f"R397: rejection 的 reason_code 应为 invalid_direction，"
            f"got {rejected_records[0]['reason_code']}"
        )

    def test_r396_mixed_valid_and_invalid_direction(self, tmp_path: Path) -> None:
        """R396: 混合合法+非法 direction 时，非法的必须被拒绝

        场景：同一文件含 1 条合法（request）+ 1 条非法（foo）
        当前缺陷：两条都被接受
        R396 断言：只应返回 1 条合法 record，非法的进入 rejection
        """
        truth_path = tmp_path / "truth.jsonl"
        with open(truth_path, "w", encoding="utf-8") as f:
            # 合法 direction
            valid_truth = {
                "truth_id": 1, "field_index": 0,
                "semantic_label": "constant",
                "confidence": 1.0, "is_hard_evidence": True,
                "layout_id": "L1", "direction": "request",
            }
            # 非法 direction
            invalid_truth = {
                "truth_id": 2, "field_index": 1,
                "semantic_label": "payload",
                "confidence": 1.0, "is_hard_evidence": True,
                "layout_id": "L1", "direction": "foo",
            }
            f.write(json.dumps(valid_truth, ensure_ascii=False) + "\n")
            f.write(json.dumps(invalid_truth, ensure_ascii=False) + "\n")

        valid_records, rejected_records = read_ground_truth_jsonl(str(truth_path))

        # R396 断言：只应返回合法的 1 条，非法的进入 rejection
        # 当前缺陷：返回 2 条 valid，0 条 rejection
        assert len(valid_records) == 1, (
            f"R396: 混合输入时只应返回 1 条合法 record，"
            f"非法 direction=foo 不应被接受。当前返回 {len(valid_records)} 条 valid。"
        )
        assert len(rejected_records) == 1, (
            f"R396: 非法 direction=foo 应进入 rejection，"
            f"got {len(rejected_records)} rejections"
        )
        assert valid_records[0].direction == "request", (
            f"R396: 剩余的 record 应是 direction=request，"
            f"got {valid_records[0].direction}"
        )
        assert rejected_records[0]["reason_code"] == "invalid_direction"
