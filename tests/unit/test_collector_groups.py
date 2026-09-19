"""R041+R042: 按 layout_id + direction 稳定分组与字段数量一致性测试"""

from semantic_detector.contracts import (
    Direction,
    FieldSpan,
    MessageRecord,
    REJECTION_REASON_INCONSISTENT_FIELD_COUNT,
)
from semantic_detector.profiling.collector import group_by_layout_and_direction, validate_group_field_count


def _make_record(msg_id, layout, direction, payload_hex="aabbccdd", num_fields=2):
    """构造 MessageRecord，num_fields 控制字段数量"""
    # 每个字段占 2 字节 = 4 个十六进制字符
    min_hex_chars = num_fields * 4
    if len(payload_hex) < min_hex_chars:
        payload_hex = payload_hex + "0" * (min_hex_chars - len(payload_hex))
    fields = tuple(
        FieldSpan(field_index=i, start=i * 2, end=(i + 1) * 2)
        for i in range(num_fields)
    )
    return MessageRecord(
        message_id=msg_id,
        layout_id=layout,
        direction=direction,
        payload=bytes.fromhex(payload_hex),
        fields=fields,
    )


class TestGroupByLayoutAndDirection:
    def test_single_group(self):
        records = [
            _make_record("m1", "L1", Direction.REQUEST),
            _make_record("m2", "L1", Direction.REQUEST),
        ]
        groups = group_by_layout_and_direction(records)
        assert len(groups) == 1
        assert ("L1", "request") in groups
        assert len(groups[("L1", "request")]) == 2

    def test_mixed_layout_and_direction(self):
        records = [
            _make_record("m1", "L1", Direction.REQUEST),
            _make_record("m2", "L2", Direction.RESPONSE),
            _make_record("m3", "L1", Direction.RESPONSE),
            _make_record("m4", "L2", Direction.REQUEST),
            _make_record("m5", "L1", Direction.REQUEST),
        ]
        groups = group_by_layout_and_direction(records)
        assert len(groups) == 4
        assert list(groups.keys()) == [
            ("L1", "request"),
            ("L1", "response"),
            ("L2", "request"),
            ("L2", "response"),
        ]

    def test_input_order_preserved_within_group(self):
        records = [
            _make_record("m1", "L1", Direction.REQUEST),
            _make_record("m2", "L2", Direction.REQUEST),
            _make_record("m3", "L1", Direction.REQUEST),
            _make_record("m4", "L1", Direction.REQUEST),
        ]
        groups = group_by_layout_and_direction(records)
        assert [r.message_id for r in groups[("L1", "request")]] == ["m1", "m3", "m4"]
        assert [r.message_id for r in groups[("L2", "request")]] == ["m2"]

    def test_group_keys_sorted(self):
        records = [
            _make_record("m1", "ZZ", Direction.UNKNOWN),
            _make_record("m2", "AA", Direction.REQUEST),
            _make_record("m3", "MM", Direction.RESPONSE),
        ]
        groups = group_by_layout_and_direction(records)
        assert list(groups.keys()) == [
            ("AA", "request"),
            ("MM", "response"),
            ("ZZ", "unknown"),
        ]

    def test_empty_input(self):
        groups = group_by_layout_and_direction([])
        assert len(groups) == 0

    def test_single_record(self):
        records = [_make_record("m1", "L1", Direction.REQUEST)]
        groups = group_by_layout_and_direction(records)
        assert len(groups) == 1
        assert groups[("L1", "request")][0].message_id == "m1"

    def test_all_directions(self):
        records = [
            _make_record("m1", "L1", Direction.REQUEST),
            _make_record("m2", "L1", Direction.RESPONSE),
            _make_record("m3", "L1", Direction.UNKNOWN),
        ]
        groups = group_by_layout_and_direction(records)
        assert len(groups) == 3
        assert list(groups.keys()) == [
            ("L1", "request"),
            ("L1", "response"),
            ("L1", "unknown"),
        ]


class TestValidateGroupFieldCount:
    def test_consistent_fields_pass(self):
        records = [
            _make_record("m1", "L1", Direction.REQUEST, num_fields=2),
            _make_record("m2", "L1", Direction.REQUEST, num_fields=2),
        ]
        groups = group_by_layout_and_direction(records)
        valid, rejected = validate_group_field_count(groups)
        assert len(valid) == 1
        assert len(valid[("L1", "request")]) == 2
        assert len(rejected) == 0

    def test_inconsistent_fields_rejected(self):
        """R226/R227: 2/3 字段混合组整组拒绝，返回 RejectionRecord。"""
        records = [
            _make_record("m1", "L1", Direction.REQUEST, num_fields=2),
            _make_record("m2", "L1", Direction.REQUEST, num_fields=3),
        ]
        groups = group_by_layout_and_direction(records)
        valid, rejections = validate_group_field_count(groups)
        # 整组拒绝：valid 中不存在该组，返回 1 个 RejectionRecord
        assert ("L1", "request") not in valid
        assert len(rejections) == 1
        rec = rejections[0]
        assert rec.group_key == ("L1", "request")
        assert rec.record_count == 2
        assert rec.field_counts == ((2, 1), (3, 1))
        assert rec.reason_code == REJECTION_REASON_INCONSISTENT_FIELD_COUNT
        assert [r.message_id for r in rec.records] == ["m1", "m2"]

    def test_majority_minority_whole_group_rejected(self):
        """R226/R227: 即使 2:1 多数，整组仍全部拒绝，field_counts 反映分布。"""
        records = [
            _make_record("m1", "L1", Direction.REQUEST, num_fields=2),
            _make_record("m2", "L1", Direction.REQUEST, num_fields=2),
            _make_record("m3", "L1", Direction.REQUEST, num_fields=3),
        ]
        groups = group_by_layout_and_direction(records)
        valid, rejections = validate_group_field_count(groups)
        assert ("L1", "request") not in valid
        assert len(rejections) == 1
        rec = rejections[0]
        assert rec.record_count == 3
        assert rec.field_counts == ((2, 2), (3, 1))
        assert rec.reason_code == REJECTION_REASON_INCONSISTENT_FIELD_COUNT

    def test_multiple_groups_independent(self):
        """R226/R227: 不一致组整组拒绝，一致组整组保留，互不影响。"""
        records = [
            _make_record("m1", "L1", Direction.REQUEST, num_fields=2),
            _make_record("m2", "L1", Direction.REQUEST, num_fields=3),
            _make_record("m3", "L2", Direction.REQUEST, num_fields=4),
            _make_record("m4", "L2", Direction.REQUEST, num_fields=4),
        ]
        groups = group_by_layout_and_direction(records)
        valid, rejections = validate_group_field_count(groups)
        # L1 不一致 → 整组拒绝；L2 一致 → 整组保留
        assert len(valid) == 1
        assert len(valid[("L2", "request")]) == 2
        assert len(rejections) == 1
        rec = rejections[0]
        assert rec.group_key == ("L1", "request")
        assert [r.message_id for r in rec.records] == ["m1", "m2"]

    def test_empty_group(self):
        groups = group_by_layout_and_direction([])
        valid, rejections = validate_group_field_count(groups)
        assert len(valid) == 0
        assert len(rejections) == 0

    def test_single_record_always_passes(self):
        records = [_make_record("m1", "L1", Direction.REQUEST, num_fields=5)]
        groups = group_by_layout_and_direction(records)
        valid, rejections = validate_group_field_count(groups)
        assert len(valid[("L1", "request")]) == 1
        assert len(rejections) == 0

    def test_all_different_rejected(self):
        """R226/R227: 三条记录字段数量各不相同，整组全部拒绝。"""
        records = [
            _make_record("m1", "L1", Direction.REQUEST, num_fields=2),
            _make_record("m2", "L1", Direction.REQUEST, num_fields=3),
            _make_record("m3", "L1", Direction.REQUEST, num_fields=4),
        ]
        groups = group_by_layout_and_direction(records)
        valid, rejections = validate_group_field_count(groups)
        assert ("L1", "request") not in valid
        assert len(rejections) == 1
        rec = rejections[0]
        assert rec.record_count == 3
        assert rec.field_counts == ((2, 1), (3, 1), (4, 1))

    def test_consistent_group_with_many_records_not_affected(self):
        """R226: 合法组（字段数一致）不受整组拒绝逻辑影响。"""
        records = [
            _make_record(f"m{i}", "L_ok", Direction.REQUEST, num_fields=3)
            for i in range(20)
        ]
        groups = group_by_layout_and_direction(records)
        valid, rejections = validate_group_field_count(groups)
        assert len(valid) == 1
        assert len(valid[("L_ok", "request")]) == 20
        assert len(rejections) == 0

    def test_rejected_records_preserve_input_order(self):
        """R226: 被整组拒绝的记录保持组内输入顺序。"""
        records = [
            _make_record("m1", "L1", Direction.REQUEST, num_fields=2),
            _make_record("m2", "L1", Direction.REQUEST, num_fields=3),
            _make_record("m3", "L1", Direction.REQUEST, num_fields=2),
        ]
        groups = group_by_layout_and_direction(records)
        valid, rejections = validate_group_field_count(groups)
        assert len(rejections) == 1
        assert [r.message_id for r in rejections[0].records] == ["m1", "m2", "m3"]

    def test_rejection_record_is_hashable_and_stable(self):
        """R227: RejectionRecord 是 frozen dataclass，可哈希且字段稳定。"""
        records = [
            _make_record("m1", "L1", Direction.REQUEST, num_fields=2),
            _make_record("m2", "L1", Direction.REQUEST, num_fields=3),
        ]
        groups = group_by_layout_and_direction(records)
        _, rejections = validate_group_field_count(groups)
        rec = rejections[0]
        # frozen dataclass 可哈希
        assert hash(rec) == hash(rec)
        # 重复调用结果稳定
        _, rejections2 = validate_group_field_count(
            group_by_layout_and_direction(records)
        )
        assert rec == rejections2[0]


class TestPrepareRecordsForProfiling:
    """R228: 共享 prepare_records_for_profiling 函数测试

    03 教程 6.1：统一入口返回 (valid_records, valid_groups, rejections)，
    供 cmd_validate / cmd_profile / cmd_run 复用，避免漏掉字段数校验（HIGH-2）。
    """

    def test_all_consistent_returns_all_records(self):
        """全一致输入：valid_records 包含全部记录，rejections 为空。"""
        from semantic_detector.profiling.collector import prepare_records_for_profiling

        records = [
            _make_record("m1", "L1", Direction.REQUEST, num_fields=2),
            _make_record("m2", "L1", Direction.REQUEST, num_fields=2),
            _make_record("m3", "L2", Direction.RESPONSE, num_fields=3),
            _make_record("m4", "L2", Direction.RESPONSE, num_fields=3),
        ]
        valid_records, valid_groups, rejections = prepare_records_for_profiling(records)

        assert len(valid_records) == 4
        assert len(valid_groups) == 2
        assert len(rejections) == 0
        assert set(valid_groups.keys()) == {("L1", "request"), ("L2", "response")}

    def test_inconsistent_group_excluded_from_valid_records(self):
        """不一致组的记录不进入 valid_records，进入 rejections。"""
        from semantic_detector.profiling.collector import prepare_records_for_profiling

        records = [
            _make_record("m1", "L1", Direction.REQUEST, num_fields=2),
            _make_record("m2", "L1", Direction.REQUEST, num_fields=3),  # 不一致
            _make_record("m3", "L2", Direction.REQUEST, num_fields=4),
            _make_record("m4", "L2", Direction.REQUEST, num_fields=4),
        ]
        valid_records, valid_groups, rejections = prepare_records_for_profiling(records)

        # L1 整组拒绝，L2 整组保留
        assert len(valid_records) == 2
        assert [r.message_id for r in valid_records] == ["m3", "m4"]
        assert len(valid_groups) == 1
        assert ("L2", "request") in valid_groups
        assert len(rejections) == 1
        assert rejections[0].group_key == ("L1", "request")
        assert rejections[0].record_count == 2

    def test_valid_records_flattened_in_group_sort_order(self):
        """valid_records 按组键排序展平，组内保持输入顺序。"""
        from semantic_detector.profiling.collector import prepare_records_for_profiling

        # 故意让输入顺序与组键排序不同：L2 在前，L1 在后
        records = [
            _make_record("m1", "L2", Direction.REQUEST, num_fields=2),
            _make_record("m2", "L2", Direction.REQUEST, num_fields=2),
            _make_record("m3", "L1", Direction.REQUEST, num_fields=2),
            _make_record("m4", "L1", Direction.REQUEST, num_fields=2),
        ]
        valid_records, valid_groups, _ = prepare_records_for_profiling(records)

        # 组键排序：("L1","request") < ("L2","request")，所以 L1 在前
        assert [r.message_id for r in valid_records] == ["m3", "m4", "m1", "m2"]
        assert list(valid_groups.keys()) == [("L1", "request"), ("L2", "request")]

    def test_empty_input(self):
        """空输入返回三个空容器。"""
        from semantic_detector.profiling.collector import prepare_records_for_profiling

        valid_records, valid_groups, rejections = prepare_records_for_profiling([])
        assert valid_records == []
        assert len(valid_groups) == 0
        assert rejections == []

    def test_single_entry_point_equivalent_to_manual_steps(self):
        """共享入口等价于手动 分组→校验→展平 三步。"""
        from semantic_detector.profiling.collector import (
            prepare_records_for_profiling,
            group_by_layout_and_direction,
            validate_group_field_count,
        )

        records = [
            _make_record("m1", "L1", Direction.REQUEST, num_fields=2),
            _make_record("m2", "L1", Direction.REQUEST, num_fields=3),
            _make_record("m3", "L2", Direction.REQUEST, num_fields=2),
        ]
        # 共享入口
        vr_shared, vg_shared, rej_shared = prepare_records_for_profiling(records)
        # 手动三步
        groups = group_by_layout_and_direction(records)
        vg_manual, rej_manual = validate_group_field_count(groups)
        vr_manual = [r for recs in vg_manual.values() for r in recs]

        assert [r.message_id for r in vr_shared] == [r.message_id for r in vr_manual]
        assert list(vg_shared.keys()) == list(vg_manual.keys())
        assert len(rej_shared) == len(rej_manual)
        assert rej_shared[0] == rej_manual[0]
