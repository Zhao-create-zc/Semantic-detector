"""类型/操作码检测器

检测跨 layout 的字段是否可能是类型或操作码。
"""

from typing import List, Tuple, Dict, Set, Optional, Union
from semantic_detector.contracts import FieldKey, DetectorEvidence, TypeOpcodeAlignmentKey
from semantic_detector.detectors.base import create_soft_evidence
from semantic_detector.taxonomy import CANONICAL_COARSE_LABELS


# R238: coarse_label 引用 taxonomy 标准标签 type_control，
# candidate 状态由 fine_label="type_or_opcode_candidate" 表达。
COARSE_LABEL = "type_control"  # CANONICAL_COARSE_LABELS 中的标准标签
FINE_LABEL = "type_or_opcode_candidate"


def is_dominant_ratio_qualified(ratio: float, threshold: float) -> bool:
    """判断主值支持率是否达到阈值（R403：统一 >= 语义）

    Pipeline 预过滤（通过 is_type_opcode_profile_eligible）和 Detector 硬性条件 4
    共用此比较，修复 R402 复现的 > vs >= 不一致（MEDIUM-1）。

    语义：``ratio >= threshold`` 通过。
    与项目其他检测器排除常量字段的 ``>=`` 语义一致
    （identifier/length/sequence/string/timestamp 均用 ``>=``）。

    Args:
        ratio: 主值支持率（dominant_value_ratio）
        threshold: 配置阈值（type_opcode_min_dominant_ratio）

    Returns:
        True 如果 ratio >= threshold
    """
    return ratio >= threshold


def is_type_opcode_profile_eligible(profile, config) -> bool:
    """判断单个 FieldProfile 是否具备 Type/Opcode 候选资格（R403）

    Pipeline 预过滤和 Detector 内部复用同一资格判断逻辑，统一 ``>=`` 语义。
    修复 R402 复现的 MEDIUM-1 缺陷（Pipeline ``>`` vs Detector ``>=`` 不一致）。

    检查项（计划 R403）：
    - direction 非空（身份字段完整）
    - field_index >= 0（身份字段合法）
    - sample_count > 0（有样本）
    - start_mode >= 0（位置合法）
    - width_mode <= 2（教程 10.3 硬性条件 2：宽度不超过 2）
    - dominant_value_hex is not None（有主值，tie 场景跳过）
    - dominant_value_ratio >= config.type_opcode_min_dominant_ratio（``>=`` 语义，统一）

    Args:
        profile: FieldProfile 对象
        config: Config 对象（需有 type_opcode_min_dominant_ratio 属性，鸭子类型避免循环导入）

    Returns:
        True 如果 profile 具备 Type/Opcode 候选资格
    """
    # 身份字段
    if not profile.direction:
        return False
    if profile.field_index < 0:
        return False
    # 样本
    if profile.sample_count <= 0:
        return False
    # 位置
    if profile.start_mode < 0:
        return False
    # 宽度（教程 10.3 硬性条件 2：宽度不超过 2）
    if profile.width_mode > 2:
        return False
    # 主值（tie 场景 dominant_value_hex 为 None，跳过）
    if profile.dominant_value_hex is None:
        return False
    # 主值支持率（>= 语义，与 Detector 硬性条件 4 复用同一比较函数）
    if not is_dominant_ratio_qualified(
        profile.dominant_value_ratio, config.type_opcode_min_dominant_ratio
    ):
        return False
    return True


def aggregate_dominant_values(
    layout_dominant_values: Dict[str, bytes]
) -> Dict[bytes, Set[str]]:
    """汇总不同 layout 的主值
    
    Args:
        layout_dominant_values: layout_id -> dominant_value 的映射
        
    Returns:
        dominant_value -> layout_ids 的映射
    """
    value_to_layouts: Dict[bytes, Set[str]] = {}
    
    for layout_id, dominant_value in layout_dominant_values.items():
        if dominant_value not in value_to_layouts:
            value_to_layouts[dominant_value] = set()
        value_to_layouts[dominant_value].add(layout_id)
    
    return value_to_layouts


def is_one_to_one_mapping(
    layout_dominant_values: Dict[str, bytes]
) -> bool:
    """判断主值与 layout 是否一一对应
    
    Args:
        layout_dominant_values: layout_id -> dominant_value 的映射
        
    Returns:
        True 如果主值与 layout 一一对应
    """
    if not layout_dominant_values:
        return False
    
    value_to_layouts = aggregate_dominant_values(layout_dominant_values)
    
    # 每个主值只对应一个 layout
    for layout_ids in value_to_layouts.values():
        if len(layout_ids) != 1:
            return False
    
    # 主值数量等于 layout 数量
    if len(value_to_layouts) != len(layout_dominant_values):
        return False
    
    return True


def detect_type_or_opcode(
    layout_dominant_values: Dict[str, bytes],
    alignment_key: TypeOpcodeAlignmentKey,
    existing_evidences: Optional[List[DetectorEvidence]] = None,
    per_layout_dominant_ratios: Optional[Dict[str, float]] = None,
    min_dominant_ratio: float = 0.5,
) -> Optional[DetectorEvidence]:
    """检测字段是否可能是类型或操作码

    R284：完善跨 layout 约束与证据 details（教程 10.3/10.4/10.5）。
    - 强证据排除扩展到 length 与 timestamp（教程 10.5：length 或 timestamp 强证据不得被覆盖）
    - details 增加 layout_values（layout_id -> hex 字符串）和 unique_value_count（教程 10.4）
    - 只在真实关联（一一对应映射）时输出

    R329：alignment_key 必须是 TypeOpcodeAlignmentKey 具名结构。
    删除 R328 的 tuple 兼容层，强制用具名字段访问，消除 HIGH-1 的 tuple 索引混淆。
    传入 tuple 将触发 AttributeError（tuple 没有 .width_mode 属性），错误类型明确。

    R331：重构评分逻辑，删除 layout_count/10 占位逻辑。
    多因子评分：layout_count / unique_dominant_value_count / per_layout_dominant_ratio /
    value_to_layout_purity / width_suitability / cross_layout_value_difference。
    硬性条件：至少 2 layout、至少 2 不同主值、每 layout 主值支持率达阈值、宽度<=2。
    不能只因 layout 数量多就高分。

    Args:
        layout_dominant_values: layout_id -> dominant_value 的映射
        alignment_key: TypeOpcodeAlignmentKey 具名对齐键（不接受 tuple）
        existing_evidences: 已存在的证据列表
        per_layout_dominant_ratios: layout_id -> dominant_value_ratio 的映射（R331 评分用）
        min_dominant_ratio: 主值支持率阈值（默认 0.5，R331 硬性条件）

    Returns:
        soft candidate evidence 如果检测成功，否则 None

    Raises:
        AttributeError: 当 alignment_key 不是 TypeOpcodeAlignmentKey 时（自然触发）
    """
    # R329: 直接用具名字段访问，禁止 tuple 索引
    direction_str = alignment_key.direction.value
    field_index = alignment_key.field_index
    start_mode = alignment_key.start_mode
    width_mode = alignment_key.width_mode

    # R284: 排除强语义证据（教程 10.5：length 或 timestamp 强证据不得被覆盖）
    if existing_evidences:
        for evidence in existing_evidences:
            if evidence.is_hard_evidence and evidence.coarse_label in ("length", "timestamp"):
                return None

    # 硬性条件 1：至少 2 个 layout（教程 10.3）
    if len(layout_dominant_values) < 2:
        return None

    # 硬性条件 2：宽度不超过 2（教程 10.3）
    if width_mode > 2:
        return None

    # 硬性条件 3：至少 2 个不同主值 + 一一对应映射（教程 10.3）
    if not is_one_to_one_mapping(layout_dominant_values):
        return None

    # 硬性条件 4（R331）：每个 layout 主值支持率达到配置阈值
    # R403: 复用 is_dominant_ratio_qualified，与 Pipeline 预过滤统一 >= 语义
    # 仅当 per_layout_dominant_ratios 提供时检查（防御性编程，pipeline 已预过滤）
    if per_layout_dominant_ratios is not None:
        for layout_id in layout_dominant_values:
            ratio = per_layout_dominant_ratios.get(layout_id, 0.0)
            if not is_dominant_ratio_qualified(ratio, min_dominant_ratio):
                return None

    # R331: 多因子评分
    score, score_factors = _compute_type_opcode_score(
        layout_dominant_values,
        width_mode,
        per_layout_dominant_ratios,
    )

    # R284: 构造教程 10.4 规定的完整 details
    layout_values = {
        layout_id: value.hex() for layout_id, value in layout_dominant_values.items()
    }
    unique_value_count = len(set(layout_dominant_values.values()))

    # R329: alignment_key 序列化为 list（具名字段顺序：direction/field_index/start_mode/width_mode）
    alignment_key_list = [direction_str, field_index, start_mode, width_mode]

    # 创建 soft evidence（R238: coarse_label 用标准标签 type_control）
    evidence = create_soft_evidence(
        detector="type_opcode",
        coarse_label=COARSE_LABEL,
        fine_label=FINE_LABEL,
        score=score,
        reason_code="one_to_one_mapping",
        details={
            "layout_values": layout_values,
            "layout_count": len(layout_dominant_values),
            "unique_value_count": unique_value_count,
            "alignment_key": alignment_key_list,
            "score_factors": score_factors,
            "min_dominant_ratio": min_dominant_ratio,
        }
    )

    return evidence


def _compute_type_opcode_score(
    layout_dominant_values: Dict[str, bytes],
    width_mode: int,
    per_layout_dominant_ratios: Optional[Dict[str, float]] = None,
) -> tuple:
    """R331: 多因子评分

    评分因子（权重）：
    - layout_count (0.15): 更多 layout 提供更强证据，但 5 个足够
    - unique_dominant_value_count (0.20): 不同主值越多越强
    - per_layout_dominant_ratio (0.25): 主值支持率越高越强
    - value_to_layout_purity (0.15): 每个值只对应一个 layout 时纯度最高
    - width_suitability (0.15): width=1 最优，width=2 次之
    - cross_layout_value_difference (0.10): 不同 layout 值差异度

    设计原则："不能只因 layout 数量多就高分"——layout_count 权重仅 0.15，
    且 cap 在 5 个 layout。即使 layout_count 因子满分，也只能贡献 0.15。

    Args:
        layout_dominant_values: layout_id -> dominant_value
        width_mode: 字段宽度模式
        per_layout_dominant_ratios: layout_id -> dominant_value_ratio

    Returns:
        (score, score_factors) 元组，score 在 [0, 1]
    """
    layout_count = len(layout_dominant_values)
    unique_values = set(layout_dominant_values.values())
    unique_value_count = len(unique_values)

    # 因子 1: layout_count — cap 在 5，防止只靠数量堆分
    f_layout_count = min(layout_count / 5.0, 1.0)

    # 因子 2: unique_dominant_value_count — 不同主值占比
    f_unique_values = unique_value_count / layout_count if layout_count > 0 else 0.0

    # 因子 3: per_layout_dominant_ratio — 平均主值支持率
    if per_layout_dominant_ratios is not None:
        ratios = [per_layout_dominant_ratios.get(lid, 0.0) for lid in layout_dominant_values]
        f_dominant_ratio = sum(ratios) / len(ratios) if ratios else 0.0
    else:
        # 未提供时默认满分（兼容直接调用场景）
        f_dominant_ratio = 1.0

    # 因子 4: value_to_layout_purity — 每个值只对应一个 layout 时纯度最高
    value_to_layouts = aggregate_dominant_values(layout_dominant_values)
    purities = [1.0 / len(layouts) for layouts in value_to_layouts.values()]
    f_purity = sum(purities) / len(purities) if purities else 0.0

    # 因子 5: width_suitability — width=1 最优，width=2 次之
    if width_mode == 1:
        f_width = 1.0
    elif width_mode == 2:
        f_width = 0.7
    else:
        f_width = 0.3

    # 因子 6: cross_layout_value_difference — 不同 layout 主值间的字节级差异度
    # 审计修复问题-4: 原实现与 f_unique_values 公式重复，现改为字节级 Hamming 距离
    # 计算所有 layout 主值两两之间的归一化 Hamming 距离平均值
    # （差异越大越可能是 type/opcode，因为不同操作码应有明显字节差异）
    values_list = list(layout_dominant_values.values())
    if len(values_list) >= 2:
        total_distance = 0.0
        pair_count = 0
        max_byte_diff_per_value = max(len(v) for v in values_list) * 8  # 每字节 8 位
        if max_byte_diff_per_value == 0:
            f_cross_difference = 0.0
        else:
            for i in range(len(values_list)):
                for j in range(i + 1, len(values_list)):
                    v1, v2 = values_list[i], values_list[j]
                    # 对齐到相同长度（短的左侧补 0）
                    max_len = max(len(v1), len(v2))
                    v1_padded = v1.rjust(max_len, b'\x00')
                    v2_padded = v2.rjust(max_len, b'\x00')
                    # 计算位差异
                    bit_diff = sum(
                        bin(b1 ^ b2).count('1')
                        for b1, b2 in zip(v1_padded, v2_padded)
                    )
                    total_distance += bit_diff / max_byte_diff_per_value
                    pair_count += 1
            f_cross_difference = total_distance / pair_count if pair_count > 0 else 0.0
    else:
        f_cross_difference = 0.0

    # 加权求和
    weights = {
        "layout_count": 0.15,
        "unique_values": 0.20,
        "dominant_ratio": 0.25,
        "purity": 0.15,
        "width": 0.15,
        "cross_difference": 0.10,
    }

    score = (
        weights["layout_count"] * f_layout_count
        + weights["unique_values"] * f_unique_values
        + weights["dominant_ratio"] * f_dominant_ratio
        + weights["purity"] * f_purity
        + weights["width"] * f_width
        + weights["cross_difference"] * f_cross_difference
    )

    # 钳位到 [0, 1]
    score = max(0.0, min(1.0, score))

    score_factors = {
        "layout_count": round(f_layout_count, 4),
        "unique_values": round(f_unique_values, 4),
        "dominant_ratio": round(f_dominant_ratio, 4),
        "purity": round(f_purity, 4),
        "width": round(f_width, 4),
        "cross_difference": round(f_cross_difference, 4),
        "weights": weights,
    }

    return score, score_factors


class TypeOpcodeDetector:
    """类型/操作码检测器

    检测跨 layout 的字段是否可能是类型或操作码。
    输出 soft candidate。

    R238：coarse_label 固定为标准标签 "type_control"（来自 taxonomy），
    candidate 状态由 fine_label="type_or_opcode_candidate" 表达。
    """

    name = "type_opcode"
    # R238: coarse_label 引用 taxonomy 标准标签
    COARSE_LABEL = "type_control"  # CANONICAL_COARSE_LABELS 中的标准标签
    FINE_LABEL = "type_or_opcode_candidate"

    def __init__(self):
        """初始化类型/操作码检测器"""
        pass
