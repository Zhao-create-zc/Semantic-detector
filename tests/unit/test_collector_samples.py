"""R045+R046: MessageRecord 到 FieldSample 列表转换测试"""

from semantic_detector.contracts import Direction, FieldSample, FieldSpan, MessageRecord
from semantic_detector.profiling.collector import record_to_field_samples


def test_3_fields_message():
    """3 字段消息生成 3 个可追溯样本"""
    record = MessageRecord(
        message_id="m1",
        layout_id="L1",
        direction=Direction.REQUEST,
        payload=bytes.fromhex("aabbccddeeff"),
        fields=(
            FieldSpan(field_index=0, start=0, end=2),
            FieldSpan(field_index=1, start=2, end=4),
            FieldSpan(field_index=2, start=4, end=6),
        ),
    )
    samples = record_to_field_samples(record)
    assert len(samples) == 3

    # 每个样本可追溯到 message_id
    for s in samples:
        assert s.message_id == "m1"

    # field_bytes 与切片一致
    assert samples[0].field_bytes == b"\xaa\xbb"
    assert samples[1].field_bytes == b"\xcc\xdd"
    assert samples[2].field_bytes == b"\xee\xff"

    # start/end 保持
    assert samples[0].start == 0
    assert samples[0].end == 2
    assert samples[1].start == 2
    assert samples[1].end == 4
    assert samples[2].start == 4
    assert samples[2].end == 6


def test_message_length_and_remaining():
    """message_length 和 remaining_bytes 正确"""
    record = MessageRecord(
        message_id="m1",
        layout_id="L1",
        direction=Direction.REQUEST,
        payload=bytes.fromhex("aabbccddeeff"),
        fields=(
            FieldSpan(field_index=0, start=0, end=2),
            FieldSpan(field_index=1, start=2, end=4),
            FieldSpan(field_index=2, start=4, end=6),
        ),
    )
    samples = record_to_field_samples(record)
    for s in samples:
        assert s.message_length == 6
    assert samples[0].remaining_bytes == 4
    assert samples[1].remaining_bytes == 2
    assert samples[2].remaining_bytes == 0


def test_field_key_is_correct():
    """FieldKey 包含正确的 layout_id, direction, field_index"""
    record = MessageRecord(
        message_id="m1",
        layout_id="L2",
        direction=Direction.RESPONSE,
        payload=bytes.fromhex("aabbccdd"),
        fields=(
            FieldSpan(field_index=0, start=0, end=2),
            FieldSpan(field_index=1, start=2, end=4),
        ),
    )
    samples = record_to_field_samples(record)
    assert samples[0].field_key.layout_id == "L2"
    assert samples[0].field_key.direction == Direction.RESPONSE
    assert samples[0].field_key.field_index == 0
    assert samples[1].field_key.field_index == 1


def test_optional_fields_preserved():
    """可选字段 capture_time, session_id, pair_id 被保留"""
    from datetime import datetime, timezone

    ct = datetime(2026, 1, 1, tzinfo=timezone.utc)
    record = MessageRecord(
        message_id="m1",
        layout_id="L1",
        direction=Direction.REQUEST,
        payload=bytes.fromhex("aabbccdd"),
        fields=(FieldSpan(field_index=0, start=0, end=2),),
        capture_time=ct,
        session_id="sess-1",
        pair_id="pair-1",
    )
    samples = record_to_field_samples(record)
    assert len(samples) == 1
    assert samples[0].capture_time == ct
    assert samples[0].session_id == "sess-1"
    assert samples[0].pair_id == "pair-1"


def test_empty_fields():
    """无字段消息返回空列表"""
    record = MessageRecord(
        message_id="m1",
        layout_id="L1",
        direction=Direction.REQUEST,
        payload=b"",
        fields=(),
    )
    samples = record_to_field_samples(record)
    assert samples == []


def test_input_order_preserved():
    """input_order 被保留"""
    record = MessageRecord(
        message_id="m1",
        layout_id="L1",
        direction=Direction.REQUEST,
        payload=bytes.fromhex("aabbccdd"),
        fields=(
            FieldSpan(field_index=0, start=0, end=2),
            FieldSpan(field_index=1, start=2, end=4),
        ),
        input_order=42,
    )
    samples = record_to_field_samples(record)
    for s in samples:
        assert s.input_order == 42


def test_remaining_bytes_middle_field():
    """中间字段 remaining_bytes = len(payload) - end"""
    record = MessageRecord(
        message_id="m1",
        layout_id="L1",
        direction=Direction.REQUEST,
        payload=bytes.fromhex("aabbccddeeff"),
        fields=(
            FieldSpan(field_index=0, start=0, end=2),
            FieldSpan(field_index=1, start=2, end=4),
            FieldSpan(field_index=2, start=4, end=6),
        ),
    )
    samples = record_to_field_samples(record)
    # 中间字段 end=4, payload_len=6, remaining=2
    assert samples[1].remaining_bytes == 6 - 4


def test_remaining_bytes_last_field():
    """末字段 remaining_bytes = 0"""
    record = MessageRecord(
        message_id="m1",
        layout_id="L1",
        direction=Direction.REQUEST,
        payload=bytes.fromhex("aabbccddeeff"),
        fields=(
            FieldSpan(field_index=0, start=0, end=2),
            FieldSpan(field_index=1, start=2, end=4),
            FieldSpan(field_index=2, start=4, end=6),
        ),
    )
    samples = record_to_field_samples(record)
    # 末字段 end=6, payload_len=6, remaining=0
    assert samples[2].remaining_bytes == 0


class TestFieldSampleContextPreservation:
    """R224: FieldSample 四类上下文逐项保留测试

    03 教程 4.3 测试 C：从 MessageRecord 转 FieldSample 后检查
    capture_time / session_id / pair_id / input_order 均保持原值。
    本测试同时覆盖 record_to_field_samples 与 aggregate_by_field_key
    （R223 build_field_profiles 新接入的路径），确保上下文不在聚合阶段丢失。
    """

    def _make_record_with_full_context(self, input_order, message_id="m_ctx"):
        from datetime import datetime, timezone

        return MessageRecord(
            message_id=message_id,
            layout_id="L_ctx",
            direction=Direction.REQUEST,
            payload=bytes.fromhex("aabbccdd"),
            fields=(
                FieldSpan(field_index=0, start=0, end=2),
                FieldSpan(field_index=1, start=2, end=4),
            ),
            capture_time=datetime(2026, 6, 27, 10, 0, 0, tzinfo=timezone.utc),
            session_id="sess-ctx-1",
            pair_id="pair-ctx-1",
            input_order=input_order,
        )

    def test_capture_time_preserved_through_record_to_field_samples(self):
        record = self._make_record_with_full_context(input_order=7)
        samples = record_to_field_samples(record)
        assert len(samples) == 2
        for s in samples:
            assert s.capture_time == record.capture_time, (
                f"capture_time lost on field_index={s.field_key.field_index}"
            )

    def test_session_id_preserved_through_record_to_field_samples(self):
        record = self._make_record_with_full_context(input_order=7)
        samples = record_to_field_samples(record)
        for s in samples:
            assert s.session_id == "sess-ctx-1", (
                f"session_id lost on field_index={s.field_key.field_index}"
            )

    def test_pair_id_preserved_through_record_to_field_samples(self):
        record = self._make_record_with_full_context(input_order=7)
        samples = record_to_field_samples(record)
        for s in samples:
            assert s.pair_id == "pair-ctx-1", (
                f"pair_id lost on field_index={s.field_key.field_index}"
            )

    def test_input_order_preserved_through_record_to_field_samples(self):
        record = self._make_record_with_full_context(input_order=7)
        samples = record_to_field_samples(record)
        for s in samples:
            assert s.input_order == 7, (
                f"input_order lost on field_index={s.field_key.field_index}"
            )

    def test_all_four_contexts_preserved_through_aggregate_by_field_key(self):
        """四类上下文在 aggregate_by_field_key 聚合后仍逐项保持。

        这是 R223 build_field_profiles 新接入的路径，必须确保上下文不在聚合阶段丢失。
        """
        from semantic_detector.profiling.collector import aggregate_by_field_key

        records = [
            self._make_record_with_full_context(input_order=i, message_id=f"m_ctx_{i}")
            for i in range(3)
        ]
        all_samples = []
        for r in records:
            all_samples.extend(record_to_field_samples(r))

        grouped = aggregate_by_field_key(all_samples)

        # 应聚合为 2 个 FieldKey（field_index 0 和 1），每个 3 个样本
        assert len(grouped) == 2
        for field_key, samples in grouped.items():
            assert len(samples) == 3
            # 每个样本四类上下文逐项保持
            for i, s in enumerate(samples):
                assert s.capture_time == records[i].capture_time, (
                    f"capture_time lost after aggregate on {field_key} sample {i}"
                )
                assert s.session_id == "sess-ctx-1", (
                    f"session_id lost after aggregate on {field_key} sample {i}"
                )
                assert s.pair_id == "pair-ctx-1", (
                    f"pair_id lost after aggregate on {field_key} sample {i}"
                )
                assert s.input_order == i, (
                    f"input_order lost after aggregate on {field_key} sample {i}"
                )
