"""Tests for payload_hex parsing."""

import pytest
from semantic_detector.io.jsonl import parse_payload_hex, validate_payload_hex


def test_parse_payload_hex_lowercase() -> None:
    """测试小写十六进制字符串"""
    result = parse_payload_hex("00010203")
    assert result == b'\x00\x01\x02\x03'


def test_parse_payload_hex_uppercase() -> None:
    """测试大写十六进制字符串"""
    result = parse_payload_hex("0A1B2C3D")
    assert result == b'\x0a\x1b\x2c\x3d'


def test_parse_payload_hex_mixed_case() -> None:
    """测试混合大小写十六进制字符串"""
    result = parse_payload_hex("aAbBcC01")
    assert result == b'\xaa\xbb\xcc\x01'


def test_parse_payload_hex_empty_string() -> None:
    """测试空字符串"""
    with pytest.raises(ValueError) as exc_info:
        parse_payload_hex("")
    assert "must not be empty" in str(exc_info.value)


def test_parse_payload_hex_odd_length() -> None:
    """测试奇数长度字符串"""
    with pytest.raises(ValueError) as exc_info:
        parse_payload_hex("00010")
    assert "length must be even" in str(exc_info.value)


def test_parse_payload_hex_invalid_character() -> None:
    """测试非法字符"""
    with pytest.raises(ValueError) as exc_info:
        parse_payload_hex("000G0102")
    assert "Invalid hex character" in str(exc_info.value)


def test_parse_payload_hex_non_string() -> None:
    """测试非字符串输入"""
    with pytest.raises(ValueError) as exc_info:
        parse_payload_hex(123)
    assert "must be a string" in str(exc_info.value)


def test_validate_payload_hex_valid() -> None:
    """测试合法十六进制字符串验证"""
    is_valid, error = validate_payload_hex("00010203")
    assert is_valid is True
    assert error == ""


def test_validate_payload_hex_invalid() -> None:
    """测试非法十六进制字符串验证"""
    is_valid, error = validate_payload_hex("000G0102")
    assert is_valid is False
    assert "Invalid hex character" in error


def test_parse_payload_hex_special_characters() -> None:
    """测试特殊字符"""
    with pytest.raises(ValueError) as exc_info:
        parse_payload_hex("00 01 02")
    assert "Invalid hex character" in str(exc_info.value)


def test_parse_payload_hex_long_string() -> None:
    """测试长字符串"""
    long_hex = "00" * 1000
    result = parse_payload_hex(long_hex)
    assert len(result) == 1000


def test_parse_payload_hex_single_byte() -> None:
    """测试单字节"""
    result = parse_payload_hex("FF")
    assert result == b'\xff'