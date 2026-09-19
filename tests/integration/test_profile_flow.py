"""R068: 阶段 3B 检查 — 输入消息可生成可解析画像"""

import json

from semantic_detector.contracts import Direction, FieldKey, FieldSpan, MessageRecord
from semantic_detector.profiling.collector import (
    group_by_layout_and_direction,
    validate_group_field_count,
    record_to_field_samples,
    aggregate_by_field_key,
    mark_insufficient_groups,
)
from semantic_detector.profiling.profile_builder import build_field_profile
from semantic_detector.io.exporters import export_field_profiles, import_field_profiles


def _make_records():
    records = []
    for i in range(12):
        record = MessageRecord(
            message_id=f"msg-{i:03d}",
            layout_id="L_CAN",
            direction=Direction.REQUEST,
            payload=bytes.fromhex("01020304aabbccdd"),
            fields=(
                FieldSpan(field_index=0, start=0, end=4),
                FieldSpan(field_index=1, start=4, end=8),
            ),
        )
        records.append(record)
    return records


class TestProfileFlow:
    def test_full_pipeline(self):
        """完整流程：JSONL消息 → 分组 → 切片 → 聚合 → 画像 → 导出 → 读回"""
        records = _make_records()

        # 1. 分组
        groups = group_by_layout_and_direction(records)
        assert len(groups) == 1
        key = ("L_CAN", "request")
        assert key in groups

        # 2. 校验字段数量
        valid_groups, rejected = validate_group_field_count(groups)
        assert len(rejected) == 0
        assert len(valid_groups) == 1

        # 3. 转换为 FieldSample
        all_samples = []
        for record in valid_groups[key]:
            all_samples.extend(record_to_field_samples(record))
        assert len(all_samples) == 24  # 12 records * 2 fields

        # 4. 按 FieldKey 聚合
        field_groups = aggregate_by_field_key(all_samples)
        assert len(field_groups) == 2  # field 0 and field 1

        # 5. 标记不足
        field_groups, insufficient = mark_insufficient_groups(field_groups)
        # 12 samples per key >= 8, so none insufficient
        assert len(insufficient) == 0

        # 6. 生成画像
        profiles = []
        for fk, samples in field_groups.items():
            profile = build_field_profile(fk, samples)
            profiles.append(profile)

        assert len(profiles) == 2
        for p in profiles:
            assert p.sample_count == 12
            assert p.layout_id == "L_CAN"
            assert p.direction == "request"

        # 7. 导出
        import tempfile, os
        tmp = tempfile.mktemp(suffix=".jsonl")
        export_field_profiles(profiles, tmp)
        assert os.path.exists(tmp)

        # 8. 读回
        imported = import_field_profiles(tmp)
        assert len(imported) == 2
        for p in imported:
            assert p.sample_count == 12
            d = p.to_dict()
            serialized = json.dumps(d)
            deserialized = json.loads(serialized)
            assert deserialized["sample_count"] == 12

        os.remove(tmp)


class TestInterleavedRequestResponseOrder:
    """R225: 交错输入顺序的 request/response 集成测试

    03 教程 4.3 测试 B：按 request_1, response_1, request_2, response_2, ...
    交错顺序输入，验收结果必须与先放全部 request、再放全部 response 完全一致。
    验证 R223 修复后的 build_field_profiles 不受输入顺序影响。
    """

    def _make_record(self, i, direction):
        return MessageRecord(
            message_id=f"{direction.value}_{i:03d}",
            layout_id="L_interleave",
            direction=direction,
            payload=bytes.fromhex("01020304aabbccdd"),
            fields=(
                FieldSpan(field_index=0, start=0, end=4),
                FieldSpan(field_index=1, start=4, end=8),
            ),
        )

    def _build_records_interleaved(self, n_each):
        """request_1, response_1, request_2, response_2, ..."""
        records = []
        for i in range(n_each):
            records.append(self._make_record(i, Direction.REQUEST))
            records.append(self._make_record(i, Direction.RESPONSE))
        return records

    def _build_records_grouped(self, n_each):
        """request × n, response × n"""
        records = []
        for i in range(n_each):
            records.append(self._make_record(i, Direction.REQUEST))
        for i in range(n_each):
            records.append(self._make_record(i, Direction.RESPONSE))
        return records

    def _profiles_to_comparable(self, profiles):
        """将画像转为可比较的稳定结构 (layout, direction, field_index, sample_count)"""
        return sorted(
            ((p.layout_id, p.direction, p.field_index, p.sample_count) for p in profiles),
            key=lambda x: (x[0], x[1], x[2]),
        )

    def test_interleaved_produces_two_directions(self):
        """交错输入必须生成 request 与 response 两个方向各 2 个画像。"""
        from semantic_detector.profiling.profile_builder import build_field_profiles

        records = self._build_records_interleaved(8)
        profiles = build_field_profiles(records)

        assert len(profiles) == 4, f"expected 4 profiles, got {len(profiles)}"

        by_direction = {}
        for p in profiles:
            by_direction.setdefault(p.direction, []).append(p)
        assert set(by_direction.keys()) == {"request", "response"}, (
            f"expected both directions, got {set(by_direction.keys())}"
        )
        for direction, group in by_direction.items():
            assert len(group) == 2, (
                f"{direction} expected 2 field profiles, got {len(group)}"
            )
            for p in group:
                assert p.sample_count == 8, (
                    f"{direction} field {p.field_index} sample_count={p.sample_count}"
                )

    def test_interleaved_equals_grouped_order(self):
        """交错顺序的结果必须与先 request 后 response 的分组顺序完全一致。"""
        from semantic_detector.profiling.profile_builder import build_field_profiles

        interleaved = build_field_profiles(self._build_records_interleaved(8))
        grouped = build_field_profiles(self._build_records_grouped(8))

        assert self._profiles_to_comparable(interleaved) == self._profiles_to_comparable(
            grouped
        ), "interleaved order produced different FieldKey/sample_count than grouped order"

    def test_interleaved_field_keys_distinct(self):
        """交错输入后 4 个 FieldKey 必须互不相同。"""
        from semantic_detector.profiling.profile_builder import build_field_profiles

        profiles = build_field_profiles(self._build_records_interleaved(8))
        keys = {(p.layout_id, p.direction, p.field_index) for p in profiles}
        assert len(keys) == 4, f"expected 4 distinct FieldKeys, got {len(keys)}: {keys}"
        assert ("L_interleave", "request", 0) in keys
        assert ("L_interleave", "request", 1) in keys
        assert ("L_interleave", "response", 0) in keys
        assert ("L_interleave", "response", 1) in keys
