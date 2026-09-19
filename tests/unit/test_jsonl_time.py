"""Tests for ISO 8601 UTC capture_time parsing."""

import pytest
from datetime import datetime, timezone
from semantic_detector.io.jsonl import parse_capture_time


def test_parse_capture_time_with_z() -> None:
    """测试以 Z 结尾的时间字符串"""
    result = parse_capture_time("2026-06-24T00:00:01Z")
    expected = datetime(2026, 6, 24, 0, 0, 1, tzinfo=timezone.utc)
    assert result == expected


def test_parse_capture_time_with_offset() -> None:
    """测试以 +00:00 结尾的时间字符串"""
    result = parse_capture_time("2026-06-24T00:00:01+00:00")
    expected = datetime(2026, 6, 24, 0, 0, 1, tzinfo=timezone.utc)
    assert result == expected


def test_parse_capture_time_with_microseconds() -> None:
    """测试包含微秒的时间字符串"""
    result = parse_capture_time("2026-06-24T00:00:01.123456Z")
    expected = datetime(2026, 6, 24, 0, 0, 1, 123456, tzinfo=timezone.utc)
    assert result == expected


def test_parse_capture_time_empty_string() -> None:
    """测试空字符串"""
    with pytest.raises(ValueError) as exc_info:
        parse_capture_time("")
    assert "must not be empty" in str(exc_info.value)


def test_parse_capture_time_non_string() -> None:
    """测试非字符串输入"""
    with pytest.raises(ValueError) as exc_info:
        parse_capture_time(123)
    assert "must be a string" in str(exc_info.value)


def test_parse_capture_time_invalid_format() -> None:
    """测试非法格式"""
    with pytest.raises(ValueError) as exc_info:
        parse_capture_time("2026-06-24")
    assert "Invalid ISO 8601 UTC time format" in str(exc_info.value)


def test_parse_capture_time_no_timezone() -> None:
    """测试没有时区信息的时间字符串"""
    with pytest.raises(ValueError) as exc_info:
        parse_capture_time("2026-06-24T00:00:01")
    assert "Invalid ISO 8601 UTC time format" in str(exc_info.value)