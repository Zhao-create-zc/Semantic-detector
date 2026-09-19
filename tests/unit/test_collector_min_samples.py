"""R051: 字段组最小样本数标记但不丢弃测试"""

from semantic_detector.contracts import Direction, FieldKey, FieldSample, FieldSpan, MessageRecord
from semantic_detector.profiling.collector import (
    record_to_field_samples,
    aggregate_by_field_key,
    mark_insufficient_groups,
)


def _make_samples(n, layout="L1", direction=Direction.REQUEST):
    """构造 n 条消息的 FieldSample"""
    all_samples = []
    for i in range(n):
        record = MessageRecord(
            message_id=f"m{i}",
            layout_id=layout,
            direction=direction,
            payload=bytes.fromhex("aabbccdd"),
            fields=(FieldSpan(field_index=0, start=0, end=2),),
        )
        all_samples.extend(record_to_field_samples(record))
    return all_samples


class TestMarkInsufficientGroups:
    def test_all_insufficient(self):
        """少于 8 条的组全部标记"""
        samples = _make_samples(3)
        groups = aggregate_by_field_key(samples)
        groups, insufficient = mark_insufficient_groups(groups)
        assert len(insufficient) == 1
        fk = FieldKey(layout_id="L1", direction=Direction.REQUEST, field_index=0)
        assert fk in insufficient

    def test_sufficient_not_marked(self):
        """>= 8 条的组不被标记"""
        samples = _make_samples(10)
        groups = aggregate_by_field_key(samples)
        groups, insufficient = mark_insufficient_groups(groups)
        assert len(insufficient) == 0

    def test_groups_preserved(self):
        """所有组在标记后仍保留"""
        samples = _make_samples(3)
        groups = aggregate_by_field_key(samples)
        original_count = len(groups)
        groups, insufficient = mark_insufficient_groups(groups)
        assert len(groups) == original_count

    def test_mixed_groups(self):
        """混合：一组充足一组不足"""
        samples_good = _make_samples(10, layout="L1")
        samples_bad = _make_samples(3, layout="L2")
        groups = aggregate_by_field_key(samples_good + samples_bad)
        groups, insufficient = mark_insufficient_groups(groups)
        fk_good = FieldKey(layout_id="L1", direction=Direction.REQUEST, field_index=0)
        fk_bad = FieldKey(layout_id="L2", direction=Direction.REQUEST, field_index=0)
        assert fk_good not in insufficient
        assert fk_bad in insufficient
        assert len(groups) == 2

    def test_empty_groups(self):
        groups, insufficient = mark_insufficient_groups({})
        assert len(insufficient) == 0

    def test_custom_threshold(self):
        samples = _make_samples(5)
        groups = aggregate_by_field_key(samples)
        groups, insufficient = mark_insufficient_groups(groups, min_samples=3)
        assert len(insufficient) == 0
        groups, insufficient = mark_insufficient_groups(groups, min_samples=10)
        assert len(insufficient) == 1

    def test_boundary_threshold(self):
        """恰好等于阈值不算不足"""
        samples = _make_samples(8)
        groups = aggregate_by_field_key(samples)
        groups, insufficient = mark_insufficient_groups(groups)
        assert len(insufficient) == 0
