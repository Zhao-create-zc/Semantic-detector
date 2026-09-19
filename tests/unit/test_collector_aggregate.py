"""R047+R049: 按 FieldKey 聚合 FieldSample 测试"""

from semantic_detector.contracts import Direction, FieldKey, FieldSample, FieldSpan, MessageRecord
from semantic_detector.profiling.collector import record_to_field_samples, aggregate_by_field_key


def _make_record(msg_id, layout, direction, payload_hex="aabbccdd"):
    return MessageRecord(
        message_id=msg_id,
        layout_id=layout,
        direction=direction,
        payload=bytes.fromhex(payload_hex),
        fields=(
            FieldSpan(field_index=0, start=0, end=2),
            FieldSpan(field_index=1, start=2, end=4),
        ),
    )


class TestAggregateByFieldKey:
    def test_two_messages_two_fields(self):
        """2 条消息各 2 字段 → 2 个 FieldKey，每组 2 个样本"""
        r1 = _make_record("m1", "L1", Direction.REQUEST)
        r2 = _make_record("m2", "L1", Direction.REQUEST)
        samples = record_to_field_samples(r1) + record_to_field_samples(r2)
        groups = aggregate_by_field_key(samples)
        assert len(groups) == 2
        fk0 = FieldKey(layout_id="L1", direction=Direction.REQUEST, field_index=0)
        fk1 = FieldKey(layout_id="L1", direction=Direction.REQUEST, field_index=1)
        assert len(groups[fk0]) == 2
        assert len(groups[fk1]) == 2
        assert groups[fk0][0].message_id == "m1"
        assert groups[fk0][1].message_id == "m2"

    def test_mixed_layout_direction(self):
        """不同 layout 和 direction 的样本分到不同组"""
        r1 = _make_record("m1", "L1", Direction.REQUEST)
        r2 = _make_record("m2", "L2", Direction.RESPONSE)
        samples = record_to_field_samples(r1) + record_to_field_samples(r2)
        groups = aggregate_by_field_key(samples)
        assert len(groups) == 4
        keys = list(groups.keys())
        key_tuples = [(k.layout_id, k.direction.value, k.field_index) for k in keys]
        assert ("L1", "request", 0) in key_tuples
        assert ("L1", "request", 1) in key_tuples
        assert ("L2", "response", 0) in key_tuples
        assert ("L2", "response", 1) in key_tuples

    def test_group_keys_sorted(self):
        """组间按 (layout_id, direction, field_index) 排序"""
        r1 = _make_record("m1", "ZZ", Direction.UNKNOWN)
        r2 = _make_record("m2", "AA", Direction.REQUEST)
        samples = record_to_field_samples(r1) + record_to_field_samples(r2)
        groups = aggregate_by_field_key(samples)
        keys = list(groups.keys())
        key_tuples = [(k.layout_id, k.direction.value, k.field_index) for k in keys]
        assert key_tuples == [
            ("AA", "request", 0), ("AA", "request", 1),
            ("ZZ", "unknown", 0), ("ZZ", "unknown", 1),
        ]

    def test_empty_input(self):
        groups = aggregate_by_field_key([])
        assert len(groups) == 0

    def test_single_sample(self):
        samples = record_to_field_samples(_make_record("m1", "L1", Direction.REQUEST))
        groups = aggregate_by_field_key(samples)
        assert len(groups) == 2
        for key, group in groups.items():
            assert len(group) == 1
            assert group[0].message_id == "m1"

    def test_sample_count_correct(self):
        """3 条消息各 2 字段 → 每个 key 3 个样本"""
        records = [_make_record(f"m{i}", "L1", Direction.REQUEST) for i in range(3)]
        samples = []
        for r in records:
            samples.extend(record_to_field_samples(r))
        groups = aggregate_by_field_key(samples)
        for key, group in groups.items():
            assert len(group) == 3


def test_cross_direction_not_aggregated():
    """R049: 同 layout 同 index 不同 direction → 生成两个独立字段组"""
    r1 = _make_record("m1", "L1", Direction.REQUEST)
    r2 = _make_record("m2", "L1", Direction.RESPONSE)
    samples = record_to_field_samples(r1) + record_to_field_samples(r2)
    groups = aggregate_by_field_key(samples)
    fk_req_0 = FieldKey(layout_id="L1", direction=Direction.REQUEST, field_index=0)
    fk_resp_0 = FieldKey(layout_id="L1", direction=Direction.RESPONSE, field_index=0)
    assert fk_req_0 in groups
    assert fk_resp_0 in groups
    assert len(groups[fk_req_0]) == 1
    assert groups[fk_req_0][0].message_id == "m1"
    assert len(groups[fk_resp_0]) == 1
    assert groups[fk_resp_0][0].message_id == "m2"


def test_cross_layout_not_aggregated():
    """R050: 同 direction 同 index 不同 layout → 生成两个独立字段组"""
    r1 = _make_record("m1", "L1", Direction.REQUEST)
    r2 = _make_record("m2", "L2", Direction.REQUEST)
    samples = record_to_field_samples(r1) + record_to_field_samples(r2)
    groups = aggregate_by_field_key(samples)
    fk_l1_0 = FieldKey(layout_id="L1", direction=Direction.REQUEST, field_index=0)
    fk_l2_0 = FieldKey(layout_id="L2", direction=Direction.REQUEST, field_index=0)
    assert fk_l1_0 in groups
    assert fk_l2_0 in groups
    assert len(groups[fk_l1_0]) == 1
    assert groups[fk_l1_0][0].message_id == "m1"
    assert len(groups[fk_l2_0]) == 1
    assert groups[fk_l2_0][0].message_id == "m2"
