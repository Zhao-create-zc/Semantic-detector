"""R235: taxonomy.py 标签规范集中管理测试

03 教程 7.4：验证 9 个标准粗粒度标签、预测状态、旧标签标准化。
"""

from semantic_detector.taxonomy import (
    CANONICAL_COARSE_LABELS,
    PREDICTION_STATUSES,
    is_canonical_coarse_label,
    normalize_legacy_label,
)


class TestCanonicalCoarseLabels:
    """R235: 9 个标准粗粒度标签"""

    def test_nine_canonical_labels(self):
        """恰好 9 个标准粗粒度标签。"""
        assert len(CANONICAL_COARSE_LABELS) == 9

    def test_canonical_labels_content(self):
        """9 个标准标签内容正确。"""
        assert set(CANONICAL_COARSE_LABELS) == {
            "constant",
            "length",
            "timestamp",
            "sequence_or_counter",
            "string",
            "identifier",
            "type_control",
            "payload",
            "unknown",
        }

    def test_no_protocol_specific_hardcoded_labels(self):
        """标准标签中无协议专属硬编码（如 modbus/coap/dnp3 等）。"""
        forbidden = {"modbus", "coap", "dnp3", "mqtt", "ip", "tcp", "udp", "http"}
        for label in CANONICAL_COARSE_LABELS:
            assert label.lower() not in forbidden, (
                f"标准标签 {label!r} 不应是协议专属硬编码"
            )


class TestPredictionStatuses:
    """R235: 预测状态"""

    def test_three_statuses(self):
        """恰好 3 个预测状态。"""
        assert PREDICTION_STATUSES == ("confirmed", "candidate", "abstained")


class TestNormalizeLegacyLabel:
    """R235: 旧标签标准化"""

    def test_canonical_label_returned_as_is(self):
        """标准标签原样返回。"""
        for label in CANONICAL_COARSE_LABELS:
            assert normalize_legacy_label(label) == label

    def test_identifier_candidate_to_identifier(self):
        assert normalize_legacy_label("identifier_candidate") == "identifier"

    def test_opaque_payload_candidate_to_payload(self):
        assert normalize_legacy_label("opaque_payload_candidate") == "payload"

    def test_opaque_payload_to_payload(self):
        assert normalize_legacy_label("opaque_payload") == "payload"

    def test_type_opcode_to_type_control(self):
        assert normalize_legacy_label("type_opcode") == "type_control"

    def test_type_or_opcode_to_type_control(self):
        assert normalize_legacy_label("type_or_opcode") == "type_control"

    def test_type_or_opcode_candidate_to_type_control(self):
        assert normalize_legacy_label("type_or_opcode_candidate") == "type_control"

    def test_sequence_to_sequence_or_counter(self):
        assert normalize_legacy_label("sequence") == "sequence_or_counter"

    def test_counter_to_sequence_or_counter(self):
        assert normalize_legacy_label("counter") == "sequence_or_counter"

    def test_none_returns_none(self):
        assert normalize_legacy_label(None) is None

    def test_unknown_label_returned_as_is(self):
        """未知旧标签原样返回，调用方需自行处理。"""
        assert normalize_legacy_label("some_unknown_label") == "some_unknown_label"

    def test_no_dynamic_protocol_guessing(self):
        """normalize 不得根据协议名称动态猜测标签。

        协议专属字符串（如 modbus_function_code）不应被映射为任何标准标签。
        """
        assert normalize_legacy_label("modbus_function_code") == "modbus_function_code"
        assert normalize_legacy_label("coap_token") == "coap_token"


class TestIsCanonicalCoarseLabel:
    """R235: is_canonical_coarse_label 判断函数"""

    def test_canonical_labels_recognized(self):
        for label in CANONICAL_COARSE_LABELS:
            assert is_canonical_coarse_label(label) is True

    def test_legacy_labels_not_canonical(self):
        assert is_canonical_coarse_label("identifier_candidate") is False
        assert is_canonical_coarse_label("sequence") is False
        assert is_canonical_coarse_label("type_opcode") is False

    def test_none_not_canonical(self):
        assert is_canonical_coarse_label(None) is False

    def test_unknown_not_canonical(self):
        assert is_canonical_coarse_label("some_unknown") is False
