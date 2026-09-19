"""R048: 按 capture_time 稳定排序测试"""

from datetime import datetime, timezone

from semantic_detector.contracts import Direction, FieldKey, FieldSample, FieldSpan, MessageRecord
from semantic_detector.profiling.collector import record_to_field_samples, sort_samples_by_capture_time


def _make_sample(msg_id, capture_time=None, input_order=0):
    record = MessageRecord(
        message_id=msg_id,
        layout_id="L1",
        direction=Direction.REQUEST,
        payload=bytes.fromhex("aabbccdd"),
        fields=(FieldSpan(field_index=0, start=0, end=2),),
        capture_time=capture_time,
        input_order=input_order,
    )
    return record_to_field_samples(record)[0]


def _utc(y, m, d, h=0, mi=0, s=0):
    return datetime(y, m, d, h, mi, s, tzinfo=timezone.utc)


class TestSortByCaptureTime:
    def test_sorted_by_time(self):
        t1 = _utc(2026, 1, 1)
        t2 = _utc(2026, 1, 2)
        t3 = _utc(2026, 1, 3)
        samples = [_make_sample("m3", t3), _make_sample("m1", t1), _make_sample("m2", t2)]
        result = sort_samples_by_capture_time(samples)
        assert [s.message_id for s in result] == ["m1", "m2", "m3"]

    def test_none_at_end(self):
        t1 = _utc(2026, 1, 1)
        samples = [
            _make_sample("m-none"),
            _make_sample("m-yes", t1),
            _make_sample("m-none2"),
        ]
        result = sort_samples_by_capture_time(samples)
        assert result[0].message_id == "m-yes"
        assert result[1].message_id == "m-none"
        assert result[2].message_id == "m-none2"

    def test_stable_sort_same_time(self):
        """同时间保持输入顺序"""
        t1 = _utc(2026, 6, 1)
        samples = [_make_sample("m-a", t1, input_order=0),
                    _make_sample("m-b", t1, input_order=1),
                    _make_sample("m-c", t1, input_order=2)]
        result = sort_samples_by_capture_time(samples)
        assert [s.message_id for s in result] == ["m-a", "m-b", "m-c"]

    def test_all_none(self):
        samples = [_make_sample("m1"), _make_sample("m2"), _make_sample("m3")]
        result = sort_samples_by_capture_time(samples)
        assert [s.message_id for s in result] == ["m1", "m2", "m3"]

    def test_all_have_time(self):
        samples = [_make_sample("m2", _utc(2026, 1, 2)),
                    _make_sample("m1", _utc(2026, 1, 1)),
                    _make_sample("m3", _utc(2026, 1, 3))]
        result = sort_samples_by_capture_time(samples)
        assert [s.message_id for s in result] == ["m1", "m2", "m3"]

    def test_empty_input(self):
        result = sort_samples_by_capture_time([])
        assert result == []

    def test_original_not_modified(self):
        t1 = _utc(2026, 1, 2)
        t2 = _utc(2026, 1, 1)
        samples = [_make_sample("m1", t1), _make_sample("m2", t2)]
        result = sort_samples_by_capture_time(samples)
        assert [s.message_id for s in samples] == ["m1", "m2"]
        assert [s.message_id for s in result] == ["m2", "m1"]
