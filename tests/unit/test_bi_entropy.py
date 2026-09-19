"""R059: 适配 BI entropybound.H 为纯函数测试"""

import math
from semantic_detector.bi_adapted.entropy import H


class TestEntropyFunction:
    def test_uniform_distribution(self):
        """均匀分布：4 个不同值，熵 = 2.0 bits"""
        result = H([1, 2, 3, 4])
        assert abs(result - 2.0) < 1e-9

    def test_all_same(self):
        """全部相同：熵 = 0.0 bits"""
        result = H([1, 1, 1, 1])
        assert abs(result - 0.0) < 1e-9

    def test_binary_50_50(self):
        """50/50 分布：熵 = 1.0 bit"""
        result = H([0, 1, 0, 1])
        assert abs(result - 1.0) < 1e-9

    def test_empty_input(self):
        """空输入：熵 = 0.0"""
        result = H([])
        assert result == 0.0

    def test_single_element(self):
        """单元素：熵 = 0.0"""
        result = H([42])
        assert abs(result - 0.0) < 1e-9

    def test_bytes_input(self):
        """bytes 输入：适配 bytes 类型"""
        result = H([b"\x01", b"\x02", b"\x03", b"\x04"])
        assert abs(result - 2.0) < 1e-9

    def test_string_input(self):
        """字符串输入：适配 str 类型"""
        result = H(["a", "b", "c"])
        expected = math.log(3, 2)
        assert abs(result - expected) < 1e-9

    def test_three_values_uneven(self):
        """3 值不均匀分布"""
        result = H([1, 1, 2])
        p1 = 2 / 3
        p2 = 1 / 3
        expected = -(p1 * math.log(p1, 2) + p2 * math.log(p2, 2))
        assert abs(result - expected) < 1e-9
