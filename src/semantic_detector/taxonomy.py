"""R235: 标签规范集中管理

03 教程 7.4：集中定义 9 个标准粗粒度标签与预测状态，
提供 normalize_legacy_label() 仅用于读取历史产物或兼容旧测试，
不得根据协议名称动态猜测标签。

标准粗粒度标签（CANONICAL_COARSE_LABELS）：
    constant
    length
    timestamp
    sequence_or_counter
    string
    identifier
    type_control
    payload
    unknown

预测状态（PREDICTION_STATUSES）：
    confirmed / candidate / abstained
"""

from typing import Optional


# 9 个标准粗粒度标签，按教程 7.2 节固定
CANONICAL_COARSE_LABELS = (
    "constant",
    "length",
    "timestamp",
    "sequence_or_counter",
    "string",
    "identifier",
    "type_control",
    "payload",
    "unknown",
)

# 预测状态（与 contracts.SemanticPrediction.PREDICTION_STATUSES 保持一致）
PREDICTION_STATUSES = ("confirmed", "candidate", "abstained")


# 旧标签 → 标准标签的静态映射表
# 仅用于读取历史产物或兼容旧测试，不得根据协议名称动态猜测标签
_LEGACY_LABEL_MAP = {
    # identifier 系列
    "identifier_candidate": "identifier",
    # payload 系列
    "opaque_payload_candidate": "payload",
    "opaque_payload": "payload",
    # type/opcode 系列
    "type_opcode": "type_control",
    "type_or_opcode": "type_control",
    "type_or_opcode_candidate": "type_control",
    "type": "type_control",
    "opcode": "type_control",
    # sequence 系列
    "sequence": "sequence_or_counter",
    "counter": "sequence_or_counter",
}


def normalize_legacy_label(label: Optional[str]) -> Optional[str]:
    """将旧标签标准化为 9 个标准粗粒度标签之一。

    仅用于读取历史产物或兼容旧测试，不得根据协议名称动态猜测标签。
    如果 label 已经是标准标签，原样返回。
    如果 label 是已知旧标签，返回对应标准标签。
    如果 label 是 None，返回 None。
    如果 label 既非标准也非已知旧标签，原样返回（调用方需自行处理未知标签）。

    Args:
        label: 待标准化的标签字符串

    Returns:
        标准化后的标签字符串，或 None
    """
    if label is None:
        return None
    if label in CANONICAL_COARSE_LABELS:
        return label
    return _LEGACY_LABEL_MAP.get(label, label)


def is_canonical_coarse_label(label: Optional[str]) -> bool:
    """判断 label 是否为 9 个标准粗粒度标签之一。

    Args:
        label: 待判断的标签字符串

    Returns:
        True 如果 label 是标准粗粒度标签
    """
    return label in CANONICAL_COARSE_LABELS
