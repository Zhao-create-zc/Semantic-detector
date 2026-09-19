"""测试 Direction 验证函数"""

import pytest
from semantic_detector.contracts import (
    Direction,
    ALLOWED_DIRECTIONS,
    validate_direction,
    get_direction_or_raise,
)


class TestDirectionConstants:
    """测试 Direction 常量"""

    def test_request_value(self):
        """测试 request 方向值"""
        assert Direction.REQUEST.value == "request"

    def test_response_value(self):
        """测试 response 方向值"""
        assert Direction.RESPONSE.value == "response"

    def test_unknown_value(self):
        """测试 unknown 方向值"""
        assert Direction.UNKNOWN.value == "unknown"

    def test_allowed_directions_set(self):
        """测试允许的方向集合"""
        assert ALLOWED_DIRECTIONS == {"request", "response", "unknown"}


class TestValidateDirection:
    """测试 validate_direction 函数"""

    def test_valid_request(self):
        """测试合法的 request 方向"""
        assert validate_direction("request") is True

    def test_valid_response(self):
        """测试合法的 response 方向"""
        assert validate_direction("response") is True

    def test_valid_unknown(self):
        """测试合法的 unknown 方向"""
        assert validate_direction("unknown") is True

    def test_invalid_direction(self):
        """测试非法的方向值"""
        assert validate_direction("invalid") is False

    def test_empty_string(self):
        """测试空字符串"""
        assert validate_direction("") is False

    def test_none_value(self):
        """测试 None 值"""
        assert validate_direction(None) is False

    def test_case_sensitive(self):
        """测试大小写敏感"""
        assert validate_direction("Request") is False
        assert validate_direction("REQUEST") is False


class TestGetDirectionOrRaise:
    """测试 get_direction_or_raise 函数"""

    def test_valid_request(self):
        """测试获取合法的 request 方向"""
        result = get_direction_or_raise("request")
        assert result == Direction.REQUEST

    def test_valid_response(self):
        """测试获取合法的 response 方向"""
        result = get_direction_or_raise("response")
        assert result == Direction.RESPONSE

    def test_valid_unknown(self):
        """测试获取合法的 unknown 方向"""
        result = get_direction_or_raise("unknown")
        assert result == Direction.UNKNOWN

    def test_invalid_direction_raises(self):
        """测试非法方向抛出 ValueError"""
        with pytest.raises(ValueError) as exc_info:
            get_direction_or_raise("invalid")
        assert "Invalid direction" in str(exc_info.value)
        assert "invalid" in str(exc_info.value)

    def test_empty_string_raises(self):
        """测试空字符串抛出 ValueError"""
        with pytest.raises(ValueError):
            get_direction_or_raise("")

    def test_error_message_includes_allowed(self):
        """测试错误消息包含允许的值"""
        with pytest.raises(ValueError) as exc_info:
            get_direction_or_raise("bad")
        error_msg = str(exc_info.value)
        assert "request" in error_msg
        assert "response" in error_msg
        assert "unknown" in error_msg