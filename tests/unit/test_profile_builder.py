"""R065: profile_builder 调用基础统计测试"""

import json
from datetime import datetime, timezone, timedelta
from semantic_detector.contracts import Direction, FieldKey, FieldSample, FieldSpan, MessageRecord
from semantic_detector.profiling.profile_builder import build_field_profile, FieldProfile
from semantic_detector.profiling.collector import record_to_field_samples


def _make_field_key(layout="L1", direction=Direction.REQUEST, field_index=0):
    return FieldKey(layout_id=layout, direction=direction, field_index=field_index)


def _make_samples(n, field_index=0, layout="L1", direction=Direction.REQUEST):
    all_samples = []
    for i in range(n):
        record = MessageRecord(
            message_id=f"m{i}",
            layout_id=layout,
            direction=direction,
            payload=bytes.fromhex("aabbccdd"),
            fields=(FieldSpan(field_index=field_index, start=0, end=2),),
        )
        all_samples.extend(record_to_field_samples(record))
    return [s for s in all_samples if s.field_key.field_index == field_index]


class TestBuildFieldProfile:
    def test_basic_fields_filled(self):
        """基础字段全部填充"""
        fk = _make_field_key()
        samples = _make_samples(10)
        profile = build_field_profile(fk, samples)
        assert profile.layout_id == "L1"
        assert profile.direction == "request"
        assert profile.field_index == 0
        assert profile.sample_count == 10

    def test_width_stats_filled(self):
        fk = _make_field_key()
        samples = _make_samples(5)
        profile = build_field_profile(fk, samples)
        assert profile.width_min == 2
        assert profile.width_max == 2
        assert profile.fixed_width is True

    def test_position_stats_filled(self):
        fk = _make_field_key()
        samples = _make_samples(3)
        profile = build_field_profile(fk, samples)
        assert profile.start_mode == 0
        assert profile.is_first_field_ratio == 1.0

    def test_value_stats_filled(self):
        fk = _make_field_key()
        samples = _make_samples(5)
        profile = build_field_profile(fk, samples)
        assert profile.unique_value_count == 1
        assert abs(profile.dominant_value_ratio - 1.0) < 1e-9

    def test_dominant_value_hex_and_count_filled(self):
        """R264: 主值 hex 和 count 来自真实样本统计，非 detector 猜测"""
        fk = _make_field_key()
        samples = _make_samples(5)
        profile = build_field_profile(fk, samples)
        # 所有样本 field_bytes = b'\xaa\xbb'（span 0-2 of aabbccdd）→ hex "aabb"
        assert profile.dominant_value_hex == "aabb"
        assert profile.dominant_value_count == 5

    def test_dominant_value_tie_returns_null_hex(self):
        """R264: 主值并列（tie）时 dominant_value_hex 为 None，不伪造稳定主值"""
        samples = []
        for payload_hex in ["aabbccdd", "aabbccdd", "11223344", "11223344"]:
            record = MessageRecord(
                message_id=f"m_{payload_hex}",
                layout_id="L1",
                direction=Direction.REQUEST,
                payload=bytes.fromhex(payload_hex),
                fields=(FieldSpan(field_index=0, start=0, end=2),),
            )
            samples.extend(record_to_field_samples(record))
        samples = [s for s in samples if s.field_key.field_index == 0]
        profile = build_field_profile(_make_field_key(), samples)
        # 2 个 "aabb" + 2 个 "1122" → 并列，hex 为 None
        assert profile.dominant_value_hex is None
        assert profile.dominant_value_count == 2
        assert abs(profile.dominant_value_ratio - 0.5) < 1e-9

    def test_dominant_value_hex_in_to_dict(self):
        """R264: to_dict 含 dominant_value_hex/count 字段"""
        fk = _make_field_key()
        samples = _make_samples(3)
        profile = build_field_profile(fk, samples)
        d = profile.to_dict()
        assert d["dominant_value_hex"] == "aabb"
        assert d["dominant_value_count"] == 3

    def test_entropy_stats_filled(self):
        fk = _make_field_key()
        samples = _make_samples(4)
        profile = build_field_profile(fk, samples)
        assert profile.normalized_entropy == 0.0

    def test_string_stats_filled(self):
        fk = _make_field_key()
        samples = _make_samples(3)
        profile = build_field_profile(fk, samples)
        assert 0.0 <= profile.printable_ascii_ratio <= 1.0
        assert 0.0 <= profile.utf8_decode_success_ratio <= 1.0

    def test_to_dict_roundtrip(self):
        """to_dict → JSON → back"""
        fk = _make_field_key()
        samples = _make_samples(5)
        profile = build_field_profile(fk, samples)
        d = profile.to_dict()
        serialized = json.dumps(d)
        deserialized = json.loads(serialized)
        assert deserialized["sample_count"] == 5
        assert deserialized["layout_id"] == "L1"

    def test_empty_samples_raises_error(self):
        """R066: 传空列表抛统一错误而非除零"""
        fk = _make_field_key()
        import pytest
        with pytest.raises(ValueError, match="empty samples"):
            build_field_profile(fk, [])


class TestBuildFieldProfilesDirectionRegression:
    """R222: 复现 build_field_profiles 破坏 direction 的缺陷

    审计 HIGH-1：build_field_profiles() 使用 str(record.direction) 生成键，
    在 Python 3.11+ 得到 'Direction.REQUEST' 而非 'request'；后续比较
    direction_str == 'request' 失败，回退到外层循环遗留的 record.direction，
    导致同 layout 的 request/response 画像方向被错归类。
    本测试在修复前必须失败，修复后必须通过。
    """

    def _make_records(self, n, direction, layout="L_dir", field_index=0):
        records = []
        for i in range(n):
            records.append(
                MessageRecord(
                    message_id=f"{direction.value}_{i}",
                    layout_id=layout,
                    direction=direction,
                    payload=bytes.fromhex("aabbccdd"),
                    fields=(FieldSpan(field_index=field_index, start=0, end=2),),
                )
            )
        return records

    def test_request_and_response_same_layout_produce_two_profiles(self):
        """同 layout 的 request 与 response 必须生成两个方向不同的画像。

        修复前：两个画像方向都被错归为最后一条记录的方向（response）。
        """
        from semantic_detector.profiling.profile_builder import build_field_profiles

        records = self._make_records(8, Direction.REQUEST) + self._make_records(
            8, Direction.RESPONSE
        )

        profiles = build_field_profiles(records)

        # 必须生成两个画像，分别对应 request 与 response
        assert len(profiles) == 2, f"expected 2 profiles, got {len(profiles)}"

        directions = sorted(p.direction for p in profiles)
        assert directions == ["request", "response"], (
            f"expected directions ['request','response'], got {directions}"
        )

    def test_each_profile_sample_count_correct(self):
        """每个方向画像的 sample_count 必须为 8，且互不混淆。"""
        from semantic_detector.profiling.profile_builder import build_field_profiles

        records = self._make_records(8, Direction.REQUEST) + self._make_records(
            8, Direction.RESPONSE
        )

        profiles = build_field_profiles(records)
        by_direction = {p.direction: p for p in profiles}

        assert by_direction["request"].sample_count == 8, (
            f"request sample_count={by_direction['request'].sample_count}"
        )
        assert by_direction["response"].sample_count == 8, (
            f"response sample_count={by_direction['response'].sample_count}"
        )

    def test_two_profiles_field_keys_differ(self):
        """request 与 response 画像的 (layout_id, direction, field_index) 必须不同。"""
        from semantic_detector.profiling.profile_builder import build_field_profiles

        records = self._make_records(8, Direction.REQUEST) + self._make_records(
            8, Direction.RESPONSE
        )

        profiles = build_field_profiles(records)
        keys = {(p.layout_id, p.direction, p.field_index) for p in profiles}
        assert len(keys) == 2, f"expected 2 distinct FieldKeys, got {keys}"
        assert ("L_dir", "request", 0) in keys
        assert ("L_dir", "response", 0) in keys


class TestCaptureTimeMetadataR270:
    """R270：FieldProfile capture_time_count/coverage/min/max 测试

    验收：有/无/部分时间 | UTC 时间可 JSON 化。
    教程 9.3/9.4：从 FieldSample.capture_time 提取统计，
    所有 capture_time 缺失时 count=0/coverage=0.0/min/max=None，
    不使用当前系统时间兜底。
    """

    def _make_sample_with_capture(self, capture_time=None, field_bytes=b'\x00\x01',
                                   message_id='m1', field_index=0):
        """构造带 capture_time 的 FieldSample"""
        return FieldSample(
            message_id=message_id,
            field_key=FieldKey(layout_id="L_cap", direction=Direction.REQUEST, field_index=field_index),
            field_bytes=field_bytes,
            start=0,
            end=len(field_bytes),
            message_length=10,
            remaining_bytes=8,
            capture_time=capture_time,
        )

    def test_all_samples_have_capture_time(self):
        """R270：所有样本都有 capture_time → coverage=1.0，min/max 正确"""
        t1 = datetime(2026, 6, 27, 10, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 6, 27, 11, 0, 0, tzinfo=timezone.utc)
        t3 = datetime(2026, 6, 27, 12, 0, 0, tzinfo=timezone.utc)
        samples = [
            self._make_sample_with_capture(t1, message_id='m1'),
            self._make_sample_with_capture(t2, message_id='m2'),
            self._make_sample_with_capture(t3, message_id='m3'),
        ]
        fk = FieldKey(layout_id="L_cap", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(fk, samples)

        assert profile.capture_time_count == 3
        assert abs(profile.capture_time_coverage - 1.0) < 1e-9
        assert profile.capture_time_min == t1
        assert profile.capture_time_max == t3

    def test_no_samples_have_capture_time(self):
        """R270：所有样本都无 capture_time → count=0/coverage=0.0/min/max=None

        教程 9.4：所有 capture_time 缺失时不能用当前系统时间兜底。
        """
        samples = [
            self._make_sample_with_capture(None, message_id='m1'),
            self._make_sample_with_capture(None, message_id='m2'),
        ]
        fk = FieldKey(layout_id="L_cap", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(fk, samples)

        assert profile.capture_time_count == 0
        assert profile.capture_time_coverage == 0.0
        assert profile.capture_time_min is None
        assert profile.capture_time_max is None

    def test_partial_samples_have_capture_time(self):
        """R270：部分样本有 capture_time → coverage=0.5，min/max 来自有时间的样本"""
        t1 = datetime(2026, 6, 27, 10, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 6, 27, 11, 0, 0, tzinfo=timezone.utc)
        samples = [
            self._make_sample_with_capture(t1, message_id='m1'),
            self._make_sample_with_capture(None, message_id='m2'),
            self._make_sample_with_capture(t2, message_id='m3'),
            self._make_sample_with_capture(None, message_id='m4'),
        ]
        fk = FieldKey(layout_id="L_cap", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(fk, samples)

        # 4 个样本，2 个有时间 → coverage=0.5
        assert profile.capture_time_count == 2
        assert abs(profile.capture_time_coverage - 0.5) < 1e-9
        # min/max 来自有时间的样本（忽略 None）
        assert profile.capture_time_min == t1
        assert profile.capture_time_max == t2

    def test_capture_time_iso_serializable_in_to_dict(self):
        """R270：capture_time_min/max 在 to_dict 中转 ISO 字符串（UTC 时间可 JSON 化）

        教程 9.3：UTC 时间可 JSON 化。
        """
        t1 = datetime(2026, 6, 27, 10, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 6, 27, 12, 0, 0, tzinfo=timezone.utc)
        samples = [
            self._make_sample_with_capture(t1, message_id='m1'),
            self._make_sample_with_capture(t2, message_id='m2'),
        ]
        fk = FieldKey(layout_id="L_cap", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(fk, samples)
        d = profile.to_dict()

        # to_dict 中应为 ISO 字符串
        assert d["capture_time_count"] == 2
        assert d["capture_time_coverage"] == 1.0
        assert isinstance(d["capture_time_min"], str)
        assert isinstance(d["capture_time_max"], str)
        # ISO 字符串可 JSON 化
        serialized = json.dumps(d)
        deserialized = json.loads(serialized)
        assert deserialized["capture_time_min"] == "2026-06-27T10:00:00+00:00"
        assert deserialized["capture_time_max"] == "2026-06-27T12:00:00+00:00"

    def test_capture_time_none_in_to_dict_when_missing(self):
        """R270：无 capture_time 时 to_dict 中 min/max 为 None"""
        samples = [self._make_sample_with_capture(None, message_id='m1')]
        fk = FieldKey(layout_id="L_cap", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(fk, samples)
        d = profile.to_dict()

        assert d["capture_time_count"] == 0
        assert d["capture_time_coverage"] == 0.0
        assert d["capture_time_min"] is None
        assert d["capture_time_max"] is None

    def test_capture_time_min_max_correct_ordering(self):
        """R270：min/max 正确处理乱序输入"""
        t1 = datetime(2026, 6, 27, 10, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 6, 27, 11, 0, 0, tzinfo=timezone.utc)
        t3 = datetime(2026, 6, 27, 12, 0, 0, tzinfo=timezone.utc)
        # 乱序输入：t3, t1, t2
        samples = [
            self._make_sample_with_capture(t3, message_id='m1'),
            self._make_sample_with_capture(t1, message_id='m2'),
            self._make_sample_with_capture(t2, message_id='m3'),
        ]
        fk = FieldKey(layout_id="L_cap", direction=Direction.REQUEST, field_index=0)
        profile = build_field_profile(fk, samples)

        # min/max 应正确（不依赖输入顺序）
        assert profile.capture_time_min == t1
        assert profile.capture_time_max == t3

