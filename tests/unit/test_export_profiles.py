"""R067: FieldProfile JSONL 导出与读回测试"""

import json
import os

from semantic_detector.profiling.profile_builder import FieldProfile
from semantic_detector.io.exporters import export_field_profiles, import_field_profiles


class TestExportProfiles:
    def test_roundtrip_preserves_fields(self):
        """导出再读取：字段和浮点值保持"""
        profiles = [
            FieldProfile(
                layout_id="L1", direction="request", field_index=0,
                sample_count=10, width_min=2, width_max=4, width_mode=2,
                fixed_width=False, start_mode=0, end_mode=2,
                is_first_field_ratio=0.8, is_last_field_ratio=0.2,
                position_ratio_mean=0.15,
                unique_value_count=5, unique_ratio=0.5,
                dominant_value_ratio=0.3, all_zero_sample_ratio=0.1,
                zero_byte_ratio=0.05, printable_ascii_ratio=0.9,
                utf8_decode_success_ratio=0.95,
                normalized_entropy=0.7, insufficient_samples=False,
            ),
        ]

        output_path = os.path.join(tempfile.gettempdir(), "test_profiles.jsonl")
        export_field_profiles(profiles, output_path)
        imported = import_field_profiles(output_path)

        assert len(imported) == 1
        p = imported[0]
        assert p.layout_id == "L1"
        assert p.direction == "request"
        assert p.field_index == 0
        assert p.sample_count == 10
        assert p.width_min == 2
        assert p.width_max == 4
        assert p.fixed_width is False
        assert abs(p.is_first_field_ratio - 0.8) < 1e-9
        assert abs(p.position_ratio_mean - 0.15) < 1e-9
        assert abs(p.unique_ratio - 0.5) < 1e-9
        assert abs(p.normalized_entropy - 0.7) < 1e-9
        assert p.insufficient_samples is False
        os.remove(output_path)

    def test_multiple_profiles(self):
        profiles = [
            FieldProfile(layout_id="L1", direction="request", field_index=0, sample_count=5),
            FieldProfile(layout_id="L2", direction="response", field_index=1, sample_count=8),
        ]

        output_path = os.path.join(tempfile.gettempdir(), "test_multi.jsonl")
        export_field_profiles(profiles, output_path)
        imported = import_field_profiles(output_path)

        assert len(imported) == 2
        assert imported[0].layout_id == "L1"
        assert imported[1].layout_id == "L2"
        assert imported[0].sample_count == 5
        assert imported[1].sample_count == 8
        os.remove(output_path)

    def test_empty_export(self):
        output_path = os.path.join(tempfile.gettempdir(), "test_empty.jsonl")
        export_field_profiles([], output_path)
        imported = import_field_profiles(output_path)
        assert len(imported) == 0
        os.remove(output_path)

    def test_json_is_valid(self):
        profiles = [FieldProfile(layout_id="L1", direction="request")]
        output_path = os.path.join(tempfile.gettempdir(), "test_json_valid.jsonl")
        export_field_profiles(profiles, output_path)
        with open(output_path, 'r') as f:
            for line in f:
                parsed = json.loads(line.strip())
                assert isinstance(parsed, dict)
        os.remove(output_path)


import tempfile


# R274: profile 导出/导入 round-trip 覆盖 R264-R273 全部新增字段
from datetime import datetime, timezone


class TestExportProfilesR274:
    """R274: profile 导出/导入 round-trip 覆盖 R264-R273 全部新增字段

    验收：profile→JSONL→profile 不丢证据。
    教程要求：导出/导入必须支持全部新增字段（包括 datetime 字段）。
    R274 修改 export_field_profiles 使用 to_dict()（替代 asdict），
    import_field_profiles 把 ISO 字符串解析回 datetime。
    """

    def _roundtrip(self, profile):
        """辅助：导出再导入，返回导入后的 profile"""
        output_path = os.path.join(tempfile.gettempdir(), "test_r274.jsonl")
        export_field_profiles([profile], output_path)
        imported = import_field_profiles(output_path)
        os.remove(output_path)
        assert len(imported) == 1
        return imported[0]

    def test_roundtrip_dominant_value_hex_count_r264(self):
        """R264: dominant_value_hex/count round-trip"""
        p = FieldProfile(
            layout_id="L1", direction="request", field_index=0,
            dominant_value_hex="0a00", dominant_value_count=7,
        )
        result = self._roundtrip(p)
        assert result.dominant_value_hex == "0a00"
        assert result.dominant_value_count == 7

    def test_roundtrip_be_length_relations_r266(self):
        """R266: BE 6 个 length relations 字段 round-trip"""
        p = FieldProfile(
            layout_id="L1", direction="request", field_index=0,
            numeric_be_message_length_exact_support=1.0,
            numeric_be_remaining_bytes_exact_support=0.5,
            numeric_be_message_length_offset_support=0.75,
            numeric_be_message_length_offset=4,
            numeric_be_remaining_bytes_offset_support=0.25,
            numeric_be_remaining_bytes_offset=8,
        )
        result = self._roundtrip(p)
        assert abs(result.numeric_be_message_length_exact_support - 1.0) < 1e-9
        assert abs(result.numeric_be_remaining_bytes_exact_support - 0.5) < 1e-9
        assert abs(result.numeric_be_message_length_offset_support - 0.75) < 1e-9
        assert result.numeric_be_message_length_offset == 4
        assert abs(result.numeric_be_remaining_bytes_offset_support - 0.25) < 1e-9
        assert result.numeric_be_remaining_bytes_offset == 8

    def test_roundtrip_le_length_relations_r267(self):
        """R267: LE 6 个 length relations 字段 round-trip"""
        p = FieldProfile(
            layout_id="L1", direction="request", field_index=0,
            numeric_le_message_length_exact_support=0.8,
            numeric_le_remaining_bytes_exact_support=0.3,
            numeric_le_message_length_offset_support=0.6,
            numeric_le_message_length_offset=2,
            numeric_le_remaining_bytes_offset_support=0.4,
            numeric_le_remaining_bytes_offset=6,
        )
        result = self._roundtrip(p)
        assert abs(result.numeric_le_message_length_exact_support - 0.8) < 1e-9
        assert abs(result.numeric_le_remaining_bytes_exact_support - 0.3) < 1e-9
        assert abs(result.numeric_le_message_length_offset_support - 0.6) < 1e-9
        assert result.numeric_le_message_length_offset == 2
        assert abs(result.numeric_le_remaining_bytes_offset_support - 0.4) < 1e-9
        assert result.numeric_le_remaining_bytes_offset == 6

    def test_roundtrip_distinct_value_count_r266_r267(self):
        """R266/R267: BE/LE distinct_value_count round-trip"""
        p = FieldProfile(
            layout_id="L1", direction="request", field_index=0,
            numeric_be_distinct_value_count=5,
            numeric_le_distinct_value_count=3,
        )
        result = self._roundtrip(p)
        assert result.numeric_be_distinct_value_count == 5
        assert result.numeric_le_distinct_value_count == 3

    def test_roundtrip_capture_time_metadata_r270(self):
        """R270: capture_time_count/coverage/min/max round-trip（含 datetime）

        关键：datetime 必须从 ISO 字符串解析回 datetime 才能等价。
        asdict 会抛 TypeError，to_dict + fromisoformat 才正确。
        """
        t1 = datetime(2026, 6, 27, 10, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 6, 27, 11, 0, 0, tzinfo=timezone.utc)
        p = FieldProfile(
            layout_id="L1", direction="request", field_index=0,
            sample_count=10,
            capture_time_count=8,
            capture_time_coverage=0.8,
            capture_time_min=t1,
            capture_time_max=t2,
        )
        result = self._roundtrip(p)
        assert result.capture_time_count == 8
        assert abs(result.capture_time_coverage - 0.8) < 1e-9
        # datetime 从 ISO 字符串解析回 datetime，应等价
        assert result.capture_time_min == t1
        assert result.capture_time_max == t2
        # 确保类型真的是 datetime（不是字符串）
        assert isinstance(result.capture_time_min, datetime)
        assert isinstance(result.capture_time_max, datetime)

    def test_roundtrip_capture_time_none_r270(self):
        """R270: capture_time 缺失（None）时 round-trip 保持 None"""
        p = FieldProfile(
            layout_id="L1", direction="request", field_index=0,
            sample_count=5,
            capture_time_count=0,
            capture_time_coverage=0.0,
            capture_time_min=None,
            capture_time_max=None,
        )
        result = self._roundtrip(p)
        assert result.capture_time_count == 0
        assert result.capture_time_coverage == 0.0
        assert result.capture_time_min is None
        assert result.capture_time_max is None

    def test_roundtrip_unix_seconds_support_r271(self):
        """R271: Unix seconds BE/LE support round-trip"""
        p = FieldProfile(
            layout_id="L1", direction="request", field_index=0,
            timestamp_be_unix_seconds_support=1.0,
            timestamp_le_unix_seconds_support=0.5,
        )
        result = self._roundtrip(p)
        assert abs(result.timestamp_be_unix_seconds_support - 1.0) < 1e-9
        assert abs(result.timestamp_le_unix_seconds_support - 0.5) < 1e-9

    def test_roundtrip_unix_ms_us_support_r272(self):
        """R272: Unix ms/us BE/LE support round-trip"""
        p = FieldProfile(
            layout_id="L1", direction="request", field_index=0,
            timestamp_be_unix_milliseconds_support=0.9,
            timestamp_be_unix_microseconds_support=0.1,
            timestamp_le_unix_milliseconds_support=0.8,
            timestamp_le_unix_microseconds_support=0.2,
        )
        result = self._roundtrip(p)
        assert abs(result.timestamp_be_unix_milliseconds_support - 0.9) < 1e-9
        assert abs(result.timestamp_be_unix_microseconds_support - 0.1) < 1e-9
        assert abs(result.timestamp_le_unix_milliseconds_support - 0.8) < 1e-9
        assert abs(result.timestamp_le_unix_microseconds_support - 0.2) < 1e-9

    def test_roundtrip_ntp_seconds_support_r273(self):
        """R273: NTP seconds BE/LE support round-trip"""
        p = FieldProfile(
            layout_id="L1", direction="request", field_index=0,
            timestamp_be_ntp_seconds_support=1.0,
            timestamp_le_ntp_seconds_support=0.0,
        )
        result = self._roundtrip(p)
        assert abs(result.timestamp_be_ntp_seconds_support - 1.0) < 1e-9
        assert result.timestamp_le_ntp_seconds_support == 0.0

    def test_roundtrip_full_profile_all_fields(self):
        """R274: 全字段 round-trip（综合测试，不丢任何证据）

        覆盖 R264-R273 所有新增字段，证明导出/导入链路完整。
        """
        t1 = datetime(2026, 6, 27, 10, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 6, 27, 11, 30, 0, tzinfo=timezone.utc)
        p = FieldProfile(
            layout_id="L_full", direction="response", field_index=3,
            sample_count=20,
            # R264
            dominant_value_hex="deadbeef", dominant_value_count=15,
            # R266 BE
            numeric_be_message_length_exact_support=0.95,
            numeric_be_remaining_bytes_exact_support=0.85,
            numeric_be_message_length_offset_support=0.75,
            numeric_be_message_length_offset=10,
            numeric_be_remaining_bytes_offset_support=0.65,
            numeric_be_remaining_bytes_offset=20,
            # R267 LE
            numeric_le_message_length_exact_support=0.55,
            numeric_le_remaining_bytes_exact_support=0.45,
            numeric_le_message_length_offset_support=0.35,
            numeric_le_message_length_offset=30,
            numeric_le_remaining_bytes_offset_support=0.25,
            numeric_le_remaining_bytes_offset=40,
            # R266/R267 distinct
            numeric_be_distinct_value_count=12,
            numeric_le_distinct_value_count=11,
            # R270 capture_time
            capture_time_count=18,
            capture_time_coverage=0.9,
            capture_time_min=t1,
            capture_time_max=t2,
            # R271 Unix seconds
            timestamp_be_unix_seconds_support=1.0,
            timestamp_le_unix_seconds_support=0.3,
            # R272 Unix ms/us
            timestamp_be_unix_milliseconds_support=0.7,
            timestamp_be_unix_microseconds_support=0.2,
            timestamp_le_unix_milliseconds_support=0.6,
            timestamp_le_unix_microseconds_support=0.4,
            # R273 NTP
            timestamp_be_ntp_seconds_support=0.0,
            timestamp_le_ntp_seconds_support=1.0,
        )
        result = self._roundtrip(p)
        # 基础身份
        assert result.layout_id == "L_full"
        assert result.direction == "response"
        assert result.field_index == 3
        assert result.sample_count == 20
        # R264
        assert result.dominant_value_hex == "deadbeef"
        assert result.dominant_value_count == 15
        # R266 BE
        assert abs(result.numeric_be_message_length_exact_support - 0.95) < 1e-9
        assert abs(result.numeric_be_remaining_bytes_exact_support - 0.85) < 1e-9
        assert abs(result.numeric_be_message_length_offset_support - 0.75) < 1e-9
        assert result.numeric_be_message_length_offset == 10
        assert abs(result.numeric_be_remaining_bytes_offset_support - 0.65) < 1e-9
        assert result.numeric_be_remaining_bytes_offset == 20
        # R267 LE
        assert abs(result.numeric_le_message_length_exact_support - 0.55) < 1e-9
        assert abs(result.numeric_le_remaining_bytes_exact_support - 0.45) < 1e-9
        assert abs(result.numeric_le_message_length_offset_support - 0.35) < 1e-9
        assert result.numeric_le_message_length_offset == 30
        assert abs(result.numeric_le_remaining_bytes_offset_support - 0.25) < 1e-9
        assert result.numeric_le_remaining_bytes_offset == 40
        # R266/R267 distinct
        assert result.numeric_be_distinct_value_count == 12
        assert result.numeric_le_distinct_value_count == 11
        # R270 capture_time
        assert result.capture_time_count == 18
        assert abs(result.capture_time_coverage - 0.9) < 1e-9
        assert result.capture_time_min == t1
        assert result.capture_time_max == t2
        # R271 Unix seconds
        assert abs(result.timestamp_be_unix_seconds_support - 1.0) < 1e-9
        assert abs(result.timestamp_le_unix_seconds_support - 0.3) < 1e-9
        # R272 Unix ms/us
        assert abs(result.timestamp_be_unix_milliseconds_support - 0.7) < 1e-9
        assert abs(result.timestamp_be_unix_microseconds_support - 0.2) < 1e-9
        assert abs(result.timestamp_le_unix_milliseconds_support - 0.6) < 1e-9
        assert abs(result.timestamp_le_unix_microseconds_support - 0.4) < 1e-9
        # R273 NTP
        assert result.timestamp_be_ntp_seconds_support == 0.0
        assert abs(result.timestamp_le_ntp_seconds_support - 1.0) < 1e-9
