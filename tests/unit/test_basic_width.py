"""R054: 宽度 min/max/mode/fixed 统计测试"""

from semantic_detector.contracts import Direction, FieldKey, FieldSample, FieldSpan, MessageRecord
from semantic_detector.profiling.basic_stats import compute_width_stats
from semantic_detector.profiling.profile_builder import FieldProfile
from semantic_detector.profiling.collector import record_to_field_samples, aggregate_by_field_key


def _make_samples(widths):
    """构造指定宽度的 FieldSample 列表"""
    all_samples = []
    for i, w in enumerate(widths):
        payload_hex = "aa" * w
        record = MessageRecord(
            message_id=f"m{i}",
            layout_id="L1",
            direction=Direction.REQUEST,
            payload=bytes.fromhex(payload_hex),
            fields=(FieldSpan(field_index=0, start=0, end=w),),
        )
        all_samples.extend(record_to_field_samples(record))
    return all_samples


class TestWidthStats:
    def test_fixed_width(self):
        samples = _make_samples([4, 4, 4, 4])
        profile = FieldProfile(layout_id="L1", direction="request", field_index=0)
        compute_width_stats(samples, profile)
        assert profile.width_min == 4
        assert profile.width_max == 4
        assert profile.width_mode == 4
        assert profile.fixed_width is True
        assert profile.sample_count == 4

    def test_variable_width(self):
        samples = _make_samples([2, 4, 4, 6])
        profile = FieldProfile(layout_id="L1", direction="request", field_index=0)
        compute_width_stats(samples, profile)
        assert profile.width_min == 2
        assert profile.width_max == 6
        assert profile.width_mode == 4
        assert profile.fixed_width is False
        assert profile.sample_count == 4

    def test_single_sample(self):
        samples = _make_samples([3])
        profile = FieldProfile()
        compute_width_stats(samples, profile)
        assert profile.width_min == 3
        assert profile.width_max == 3
        assert profile.width_mode == 3
        assert profile.fixed_width is True
        assert profile.sample_count == 1

    def test_empty_samples(self):
        profile = FieldProfile()
        compute_width_stats([], profile)
        assert profile.sample_count == 0

    def test_mode_picks_most_common(self):
        samples = _make_samples([2, 2, 2, 4, 6])
        profile = FieldProfile()
        compute_width_stats(samples, profile)
        assert profile.width_mode == 2

    def test_integration_with_aggregate(self):
        """与 aggregate_by_field_key 集成"""
        records = []
        for i, w in enumerate([4, 4, 6]):
            payload_hex = "aa" * w
            records.append(MessageRecord(
                message_id=f"m{i}",
                layout_id="L1",
                direction=Direction.REQUEST,
                payload=bytes.fromhex(payload_hex),
                fields=(FieldSpan(field_index=0, start=0, end=w),),
            ))
        all_samples = []
        for r in records:
            all_samples.extend(record_to_field_samples(r))
        groups = aggregate_by_field_key(all_samples)
        for key, samples in groups.items():
            profile = FieldProfile(layout_id=key.layout_id, direction=key.direction.value, field_index=key.field_index)
            compute_width_stats(samples, profile)
            assert profile.width_min == 4
            assert profile.width_max == 6
            assert profile.fixed_width is False
