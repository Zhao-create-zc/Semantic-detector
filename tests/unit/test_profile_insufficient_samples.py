"""R404: insufficient_samples 失败测试

复现 V3 独立审计 MEDIUM-2 缺陷：
    sample_count < min_samples 时 FieldProfile.insufficient_samples 仍为 False。

缺陷根因：
    - FieldProfile.insufficient_samples 字段存在（profile_builder.py:103），
      且会序列化到 JSON（to_dict 第 179 行）
    - mark_insufficient_groups 函数存在（collector.py:220），但在生产代码中
      无任何调用方（仅测试调用）
    - build_field_profiles 函数签名不接收 Config 或 min_samples 参数
      （profile_builder.py:454），内部不调用 mark_insufficient_groups
    - CLI cmd_profile / cmd_run 只传 slop_seconds，不传 min_samples
    - 后果：通过 CLI 生成的所有 FieldProfile 的 insufficient_samples 恒为 False，
      即使 sample_count < min_samples

按计划 R404 要求：
    场景：sample_count=1, min_samples=100
    预期：Profile JSON 中 insufficient_samples=true
    并且 profile 导出再导入保持一致。

本轮只复现，不修复（R405 将 build_field_profiles 接入 Config.min_samples）。
修复前：所有测试真实失败（insufficient_samples 恒为 False）。
"""

import json
import os
import tempfile

from semantic_detector.config import Config
from semantic_detector.contracts import (
    Direction,
    FieldKey,
    FieldSpan,
    MessageRecord,
)
from semantic_detector.io.exporters import (
    export_field_profiles,
    import_field_profiles,
)
from semantic_detector.profiling.profile_builder import (
    build_field_profile,
    build_field_profiles,
)


def _make_records(n: int = 1):
    """构造 n 条 MessageRecord（每条含 1 个 field_index=0 的字段）"""
    records = []
    for i in range(n):
        record = MessageRecord(
            message_id=f"m{i}",
            layout_id="L_SMALL",
            direction=Direction.REQUEST,
            payload=bytes.fromhex("aabbccdd"),
            fields=(FieldSpan(field_index=0, start=0, end=2),),
        )
        records.append(record)
    return records


def _make_field_samples(n: int = 1):
    """构造 n 个 FieldSample（field_index=0）"""
    from semantic_detector.profiling.collector import record_to_field_samples
    records = _make_records(n)
    samples = []
    for record in records:
        samples.extend(record_to_field_samples(record))
    return [s for s in samples if s.field_key.field_index == 0]


class TestInsufficientSamplesR404:
    """R404: 复现 sample_count < min_samples 时 insufficient_samples 仍为 False"""

    def test_build_field_profile_marks_insufficient_when_samples_below_min(self):
        """单字段画像：sample_count=1 < min_samples=100 → insufficient_samples=True

        R405 修复后：build_field_profile 接收 min_samples 参数，
        sample_count < min_samples 时标记 insufficient_samples=True。

        场景：1 个 FieldSample，min_samples=100
        预期：insufficient_samples == True
        """
        samples = _make_field_samples(1)
        assert len(samples) == 1

        field_key = FieldKey(layout_id="L_SMALL", direction=Direction.REQUEST, field_index=0)
        # R405：传入 min_samples=100
        profile = build_field_profile(field_key, samples, min_samples=100)

        assert profile.sample_count == 1, (
            f"sample_count 应为 1，实际 {profile.sample_count}"
        )
        # R405 修复：sample_count=1 < min_samples=100，标记为不足
        assert profile.insufficient_samples is True, (
            "R405 修复验证：sample_count=1 < min_samples=100，"
            f"insufficient_samples 应为 True，实际为 {profile.insufficient_samples}"
        )

    def test_build_field_profiles_marks_insufficient_for_small_dataset(self):
        """批量画像：1 条记录 + min_samples=100 → 所有 profile 标记为不足

        R405 修复后：build_field_profiles 接收 min_samples 参数，
        sample_count < min_samples 时标记 insufficient_samples=True。

        场景：1 条 MessageRecord（1 个字段），min_samples=100
        预期：所有 profile.insufficient_samples == True
        """
        records = _make_records(1)
        # R405：传入 min_samples=100
        profiles = build_field_profiles(records, min_samples=100)

        assert len(profiles) >= 1
        for profile in profiles:
            assert profile.sample_count == 1, (
                f"sample_count 应为 1，实际 {profile.sample_count}"
            )
            assert profile.insufficient_samples is True, (
                "R405 修复验证：sample_count=1 < min_samples=100，"
                f"insufficient_samples 应为 True，实际为 {profile.insufficient_samples}"
            )

    def test_build_field_profiles_sufficient_samples_not_marked(self):
        """对照测试：sample_count >= min_samples → insufficient_samples=False

        场景：100 条记录，min_samples=100
        预期：insufficient_samples == False

        本测试作为对照，修复前后都应通过，证明标记仅在样本不足时触发。
        """
        records = _make_records(100)
        # R405：传入 min_samples=100，sample_count=100 不 < 100，不标记
        profiles = build_field_profiles(records, min_samples=100)

        assert len(profiles) >= 1
        for profile in profiles:
            assert profile.sample_count == 100
            # 样本充足时不应标记为不足
            assert profile.insufficient_samples is False, (
                "对照测试：sample_count=100 >= min_samples=100，"
                f"insufficient_samples 应为 False，实际为 {profile.insufficient_samples}"
            )

    def test_min_samples_none_keeps_backward_compatibility(self):
        """向后兼容：min_samples=None 时不标记 insufficient_samples

        R405 设计：min_samples=None（默认）时不标记，保持向后兼容。
        现有 60+ 处调用不传 min_samples，insufficient_samples 保持默认 False。
        """
        records = _make_records(1)
        # 不传 min_samples（默认 None）
        profiles = build_field_profiles(records)

        assert len(profiles) >= 1
        for profile in profiles:
            assert profile.sample_count == 1
            # min_samples=None 时不标记，保持向后兼容
            assert profile.insufficient_samples is False, (
                "向后兼容：min_samples=None 时不标记，"
                f"insufficient_samples 应为 False，实际为 {profile.insufficient_samples}"
            )

    def test_build_field_profile_min_samples_none_backward_compatible(self):
        """向后兼容：build_field_profile min_samples=None 时不标记"""
        samples = _make_field_samples(1)
        field_key = FieldKey(layout_id="L_SMALL", direction=Direction.REQUEST, field_index=0)
        # 不传 min_samples（默认 None）
        profile = build_field_profile(field_key, samples)

        assert profile.sample_count == 1
        assert profile.insufficient_samples is False, (
            "向后兼容：min_samples=None 时不标记，"
            f"insufficient_samples 应为 False，实际为 {profile.insufficient_samples}"
        )

    def test_boundary_sample_count_equals_min_samples_not_marked(self):
        """边界：sample_count == min_samples → insufficient_samples=False（< 语义）

        R405 实现：sample_count < min_samples 才标记（严格小于）。
        sample_count == min_samples 时不标记（样本刚好够）。
        """
        records = _make_records(8)
        # sample_count=8, min_samples=8, 8 < 8 为 False，不标记
        profiles = build_field_profiles(records, min_samples=8)

        assert len(profiles) >= 1
        for profile in profiles:
            assert profile.sample_count == 8
            assert profile.insufficient_samples is False, (
                "边界：sample_count=8 == min_samples=8，"
                f"insufficient_samples 应为 False（< 语义），实际为 {profile.insufficient_samples}"
            )

    def test_cli_config_min_samples_default_is_8(self):
        """集成验证：Config 默认 min_samples=8，传入 build_field_profiles 后生效

        模拟 CLI 行为：config = Config(); build_field_profiles(records, min_samples=config.min_samples)
        """
        config = Config()  # 默认 min_samples=8
        assert config.min_samples == 8

        # sample_count=5 < min_samples=8 → 标记
        records_5 = _make_records(5)
        profiles_5 = build_field_profiles(records_5, min_samples=config.min_samples)
        for p in profiles_5:
            assert p.sample_count == 5
            assert p.insufficient_samples is True, (
                "Config 默认 min_samples=8，sample_count=5 < 8，"
                f"应标记 insufficient_samples=True，实际 {p.insufficient_samples}"
            )

        # sample_count=10 >= min_samples=8 → 不标记
        records_10 = _make_records(10)
        profiles_10 = build_field_profiles(records_10, min_samples=config.min_samples)
        for p in profiles_10:
            assert p.sample_count == 10
            assert p.insufficient_samples is False

    def test_insufficient_samples_round_trip_through_jsonl(self):
        """导出再导入保持一致：insufficient_samples=true 在 JSONL round-trip 中保持

        场景：手动构造 insufficient_samples=True 的 profile，导出再导入
        预期：导入后 insufficient_samples 仍为 True

        本测试验证序列化层是否正确传递该字段（与 R405 修复独立）。
        若此测试失败，说明 to_dict / import_field_profiles 未正确处理该字段。
        """
        # 手动构造一个 insufficient_samples=True 的 profile
        from semantic_detector.profiling.profile_builder import FieldProfile
        profile = FieldProfile(
            layout_id="L_SMALL",
            direction=Direction.REQUEST.value,
            field_index=0,
            sample_count=1,
            insufficient_samples=True,  # 显式标记
        )

        # 导出
        tmp = tempfile.mktemp(suffix=".jsonl")
        try:
            export_field_profiles([profile], tmp)
            assert os.path.exists(tmp)

            # 验证 JSONL 中包含 insufficient_samples: true
            with open(tmp, "r", encoding="utf-8") as f:
                line = f.readline()
                data = json.loads(line)
            assert data.get("insufficient_samples") is True, (
                "导出的 JSONL 中 insufficient_samples 应为 true，"
                f"实际 {data.get('insufficient_samples')}"
            )

            # 导入
            imported = import_field_profiles(tmp)
            assert len(imported) == 1
            assert imported[0].insufficient_samples is True, (
                "导入后 insufficient_samples 应保持 True，"
                f"实际 {imported[0].insufficient_samples}"
            )
            assert imported[0].sample_count == 1
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

    def test_min_samples_100_config_can_be_constructed(self):
        """Config 可构造 min_samples=100（验证配置层支持）

        本测试验证 Config 数据类支持 min_samples=100，
        为 R405 修复（build_field_profiles 接收 Config）提供基础。
        """
        config = Config(min_samples=100)
        assert config.min_samples == 100
        assert config.min_samples > 0

    def test_default_min_samples_is_8(self):
        """默认 Config.min_samples=8（验证默认值）"""
        config = Config()
        assert config.min_samples == 8


class TestCmdProfileMinSamplesR415:
    """R415: 回归测试——cmd_profile CLI 必须将 config.min_samples 传入 build_field_profiles

    缺陷背景：
        R405 修复了 cmd_run 的 min_samples 传递，但遗漏了 cmd_profile。
        导致 `profile --config config.json` 生成的 field_profiles.jsonl 中
        insufficient_samples 恒为 False，即使 sample_count < min_samples。

    场景：
        8 条记录 + config min_samples=100
        预期：profile 生成的 insufficient_samples=True（8 < 100）
    """

    def _write_input(self, tmpdir: str, n: int = 8):
        """构造 n 条合法 JSONL 记录（layout_001, request, 2 个字段）"""
        input_path = os.path.join(tmpdir, "input.jsonl")
        with open(input_path, "w", encoding="utf-8") as f:
            for i in range(1, n + 1):
                rec = {
                    "message_id": str(i),
                    "layout_id": "layout_001",
                    "direction": "request",
                    "payload_hex": "0100000016000003e86672616e6b736563726574abcd",
                    "fields": [
                        {"field_index": 0, "start": 0, "end": 1},
                        {"field_index": 1, "start": 1, "end": 5},
                    ],
                }
                f.write(json.dumps(rec) + "\n")
        return input_path

    def _write_config(self, tmpdir: str, min_samples: int):
        """构造 config.json"""
        config_path = os.path.join(tmpdir, "config.json")
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump({"min_samples": min_samples}, f)
        return config_path

    def test_cmd_profile_insufficient_samples_true_when_below_min(self):
        """cmd_profile + min_samples=100 + 8 条记录 → insufficient_samples=True

        R415 修复验证：cmd_profile 正确传入 config.min_samples。
        修复前：insufficient_samples 恒为 False（min_samples=None）。
        """
        from semantic_detector.cli import main

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = self._write_input(tmpdir, n=8)
            config_path = self._write_config(tmpdir, min_samples=100)
            output_dir = os.path.join(tmpdir, "output")

            exit_code = main([
                "profile", input_path,
                "--output-dir", output_dir,
                "--config", config_path,
            ])
            assert exit_code == 0, "cmd_profile 应成功退出"

            profiles_path = os.path.join(output_dir, "field_profiles.jsonl")
            assert os.path.exists(profiles_path), "field_profiles.jsonl 应存在"

            with open(profiles_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            assert len(lines) >= 1, "应至少生成 1 个画像"

            for line in lines:
                data = json.loads(line)
                assert data["sample_count"] == 8, (
                    f"sample_count 应为 8，实际 {data['sample_count']}"
                )
                assert data["insufficient_samples"] is True, (
                    "R415 修复验证：cmd_profile + min_samples=100，"
                    f"sample_count=8 < 100，insufficient_samples 应为 True，"
                    f"实际 {data['insufficient_samples']}"
                )

    def test_cmd_profile_sufficient_samples_not_marked(self):
        """对照测试：cmd_profile + min_samples=5 + 8 条记录 → insufficient_samples=False

        8 >= 5，样本充足，不应标记为不足。
        """
        from semantic_detector.cli import main

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = self._write_input(tmpdir, n=8)
            config_path = self._write_config(tmpdir, min_samples=5)
            output_dir = os.path.join(tmpdir, "output")

            exit_code = main([
                "profile", input_path,
                "--output-dir", output_dir,
                "--config", config_path,
            ])
            assert exit_code == 0

            profiles_path = os.path.join(output_dir, "field_profiles.jsonl")
            with open(profiles_path, "r", encoding="utf-8") as f:
                for line in f:
                    data = json.loads(line)
                    assert data["insufficient_samples"] is False, (
                        "对照测试：8 >= min_samples=5，"
                        f"insufficient_samples 应为 False，实际 {data['insufficient_samples']}"
                    )
