"""数据契约定义"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Set, Tuple, Optional, Any, List, Dict


class Direction(str, Enum):
    """消息方向枚举"""
    REQUEST = "request"
    RESPONSE = "response"
    UNKNOWN = "unknown"


# 所有允许的方向值
ALLOWED_DIRECTIONS: Set[str] = {d.value for d in Direction}


def validate_direction(direction: str) -> bool:
    """验证方向值是否合法
    
    Args:
        direction: 要验证的方向字符串
        
    Returns:
        True 如果方向合法，否则 False
    """
    return direction in ALLOWED_DIRECTIONS


def get_direction_or_raise(direction: str) -> Direction:
    """获取方向枚举值，非法时抛出异常
    
    Args:
        direction: 方向字符串
        
    Returns:
        Direction 枚举值
        
    Raises:
        ValueError: 当方向值不合法时
    """
    if not validate_direction(direction):
        raise ValueError(
            f"Invalid direction: {direction!r}. "
            f"Allowed values: {sorted(ALLOWED_DIRECTIONS)}"
        )
    return Direction(direction)


@dataclass(frozen=True)
class FieldSpan:
    """A byte span for one field within a message payload."""

    field_index: int
    start: int
    end: int

    def __post_init__(self):
        """验证字段边界

        R374（V3 审计 HIGH-1 修复）：严格整数类型校验。
        使用 type(value) is int 而非 isinstance(value, int)，因为
        bool 是 int 的子类（True == 1, False == 0），JSON 的 true/false
        不应被当作合法的字段索引或字节偏移。浮点数（0.0/1.0）同样拒绝，
        避免在 payload[start:end] 切片阶段崩溃。
        """
        # 严格类型校验：必须是 int，不接受 bool/float/str/None
        if type(self.field_index) is not int:
            raise ValueError(
                f"field_index must be int, got {type(self.field_index).__name__}: "
                f"{self.field_index!r}"
            )
        if type(self.start) is not int:
            raise ValueError(
                f"start must be int, got {type(self.start).__name__}: "
                f"{self.start!r}"
            )
        if type(self.end) is not int:
            raise ValueError(
                f"end must be int, got {type(self.end).__name__}: "
                f"{self.end!r}"
            )

        if self.field_index < 0:
            raise ValueError(f"field_index must be non-negative, got {self.field_index}")
        if self.start < 0:
            raise ValueError(f"start must be non-negative, got {self.start}")
        if self.end < 0:
            raise ValueError(f"end must be non-negative, got {self.end}")
        if self.start >= self.end:
            raise ValueError(
                f"start must be less than end, got start={self.start}, end={self.end}"
            )


@dataclass(frozen=True)
class MessageRecord:
    """消息记录数据结构"""
    
    message_id: str
    layout_id: str
    direction: Direction
    payload: bytes
    fields: Tuple[FieldSpan, ...]
    capture_time: Optional[Any] = None
    session_id: Optional[str] = None
    pair_id: Optional[str] = None
    metadata: Optional[dict] = None
    input_order: int = 0
    
    def __post_init__(self):
        """验证消息记录

        R376（V3 审计 HIGH-1 修复）：严格标识字段类型校验。
        - message_id/layout_id 必须是非空字符串（strip 后非空），不接受整数等
        - session_id/pair_id 必须是 str 或 None
        - input_order 必须是严格 int（不接受 bool）
        - metadata 必须是 dict 或 None
        不得静默字符串化或强制转换。
        """
        # 严格类型校验：message_id 必须是非空字符串
        if not isinstance(self.message_id, str):
            raise ValueError(
                f"message_id must be str, got {type(self.message_id).__name__}: "
                f"{self.message_id!r}"
            )
        if not self.message_id.strip():
            raise ValueError("message_id must not be empty")

        # 严格类型校验：layout_id 必须是非空字符串
        if not isinstance(self.layout_id, str):
            raise ValueError(
                f"layout_id must be str, got {type(self.layout_id).__name__}: "
                f"{self.layout_id!r}"
            )
        if not self.layout_id.strip():
            raise ValueError("layout_id must not be empty")

        if not isinstance(self.direction, Direction):
            raise ValueError(f"direction must be a Direction enum, got {type(self.direction)}")

        # R417：严格类型校验 payload 必须是 bytes（str 会导致 len() 返回字符数而非字节数）
        if not isinstance(self.payload, bytes):
            raise ValueError(
                f"payload must be bytes, got {type(self.payload).__name__}: "
                f"{self.payload!r}"
            )

        # R417：严格类型校验 fields 必须是 tuple（None 会崩溃，list 违反类型注解）
        if not isinstance(self.fields, tuple):
            raise ValueError(
                f"fields must be tuple, got {type(self.fields).__name__}: "
                f"{self.fields!r}"
            )

        # 严格类型校验：session_id 必须是 str 或 None
        if self.session_id is not None and not isinstance(self.session_id, str):
            raise ValueError(
                f"session_id must be str or None, got {type(self.session_id).__name__}: "
                f"{self.session_id!r}"
            )

        # 严格类型校验：pair_id 必须是 str 或 None
        if self.pair_id is not None and not isinstance(self.pair_id, str):
            raise ValueError(
                f"pair_id must be str or None, got {type(self.pair_id).__name__}: "
                f"{self.pair_id!r}"
            )

        # 严格类型校验：input_order 必须是严格 int（不接受 bool）
        if type(self.input_order) is not int:
            raise ValueError(
                f"input_order must be int, got {type(self.input_order).__name__}: "
                f"{self.input_order!r}"
            )

        # 严格类型校验：metadata 必须是 dict 或 None
        if self.metadata is not None and not isinstance(self.metadata, dict):
            raise ValueError(
                f"metadata must be dict or None, got {type(self.metadata).__name__}: "
                f"{self.metadata!r}"
            )

        # 验证字段越界
        payload_length = len(self.payload)
        for field in self.fields:
            if field.end > payload_length:
                raise ValueError(
                    f"Field {field.field_index} end ({field.end}) exceeds "
                    f"payload length ({payload_length})"
                )

        # 验证字段重叠
        sorted_fields = sorted(self.fields, key=lambda f: f.start)
        for i in range(len(sorted_fields) - 1):
            current = sorted_fields[i]
            next_field = sorted_fields[i + 1]
            if current.end > next_field.start:
                raise ValueError(
                    f"Fields overlap: field {current.field_index} end ({current.end}) "
                    f"> field {next_field.field_index} start ({next_field.start})"
                )

        # 验证 field_index 连续性
        if self.fields:
            indices = sorted([f.field_index for f in self.fields])
            expected = list(range(len(indices)))
            if indices != expected:
                raise ValueError(
                    f"field_index must be contiguous from 0, got {indices}"
                )


@dataclass(frozen=True)
class FieldKey:
    """字段组标识，用于聚合相同字段的样本

    R417（V3 审计 BUG 修复）：补齐阶段 A 遗漏的严格类型校验。
    bool 是 int 子类，hash(True)==hash(1) 且 True==1，若 field_index=True
    会被误判与 field_index=1 为同一键，导致样本错误合并。
    """

    layout_id: str
    direction: Direction
    field_index: int

    def __post_init__(self):
        # 严格类型校验：layout_id 必须是 str（不接受 None/int 等）
        if not isinstance(self.layout_id, str):
            raise ValueError(
                f"layout_id must be str, got {type(self.layout_id).__name__}: "
                f"{self.layout_id!r}"
            )
        # 严格类型校验：direction 必须是 Direction 枚举或合法方向字符串
        # Direction 继承 str，所以 Direction.REQUEST == "request" 为 True
        if not isinstance(self.direction, (Direction, str)):
            raise ValueError(
                f"direction must be a Direction or str, got {type(self.direction).__name__}"
            )
        # 严格类型校验：field_index 必须是严格 int（不接受 bool/float）
        if type(self.field_index) is not int:
            raise ValueError(
                f"field_index must be int, got {type(self.field_index).__name__}: "
                f"{self.field_index!r}"
            )
        if self.field_index < 0:
            raise ValueError(
                f"field_index must be >= 0, got {self.field_index}"
            )


@dataclass(frozen=True)
class TypeOpcodeAlignmentKey:
    """跨 layout Type/Opcode 对齐键（R327）

    V2 审计 HIGH-1 修复：消除 Pipeline 与 detector 对裸 tuple 索引含义不一致的问题。

    教程 10.3：Type/Opcode 检测器需要跨 layout 对齐相同语义位置的字段。
    旧实现使用裸 tuple `(direction, field_index, width_mode, start_mode)`，
    detector 却把 `alignment_key[3]` 当作 width，导致 start_mode=7 被误判为
    宽度 7，合法功能码被错误排除。

    本具名结构强制：
    - field_index >= 0
    - start_mode >= 0
    - width_mode > 0
    - 可稳定比较、哈希（frozen=True）
    - 不依赖 layout_id（该键用于跨 layout 对齐）
    - 不接受位置和宽度颠倒（必须用具名字段构造，语义清晰）

    字段顺序（声明顺序）为 direction, field_index, start_mode, width_mode，
    与 Pipeline 构造顺序 (direction, field_index, width_mode, start_mode) 不同，
    但因为必须用具名字段构造，不会产生顺序混淆。
    """

    direction: Direction
    field_index: int
    start_mode: int
    width_mode: int

    def __post_init__(self):
        """验证对齐键字段约束"""
        if not isinstance(self.direction, Direction):
            raise ValueError(
                f"direction must be a Direction enum, got {type(self.direction)}"
            )
        if self.field_index < 0:
            raise ValueError(
                f"field_index must be non-negative, got {self.field_index}"
            )
        if self.start_mode < 0:
            raise ValueError(
                f"start_mode must be non-negative, got {self.start_mode}"
            )
        if self.width_mode <= 0:
            raise ValueError(
                f"width_mode must be positive, got {self.width_mode}"
            )


# 组级拒绝的错误码常量
REJECTION_REASON_INCONSISTENT_FIELD_COUNT = "inconsistent_field_count"


@dataclass(frozen=True)
class RejectionRecord:
    """组级拒绝记录：带错误码的稳定错误结构。

    R227：validate_group_field_count 对不一致组返回 RejectionRecord 列表，
    取代裸 MessageRecord 列表，使拒绝原因可被 CLI 稳定上报与序列化。

    Attributes:
        group_key: 被拒绝组的 (layout_id, direction.value) 元组
        record_count: 该组被拒绝的记录总数
        field_counts: 组内出现的字段数分布，形如 ((2, 5), (3, 1)) 表示
            5 条记录有 2 个字段、1 条记录有 3 个字段；按 field_count 升序排序
        reason_code: 拒绝原因错误码（如 inconsistent_field_count）
        records: 被拒绝的 MessageRecord 列表（保持组内输入顺序），用于追溯
    """

    group_key: Tuple[str, str]
    record_count: int
    field_counts: Tuple[Tuple[int, int], ...]
    reason_code: str
    records: Tuple[MessageRecord, ...] = ()


# 记录级拒绝的统一错误码常量
REASON_CODE_DUPLICATE_MESSAGE_ID = "duplicate_message_id"
REASON_CODE_INVALID_JSON = "invalid_json"
REASON_CODE_MISSING_REQUIRED_FIELD = "missing_required_field"
REASON_CODE_VALUE_ERROR = "value_error"
REASON_CODE_TYPE_ERROR = "type_error"


@dataclass(frozen=True)
class RejectedRecord:
    """记录级拒绝：统一可序列化的拒绝结构。

    R382（V3 审计 HIGH-2 修复）：建立统一 RejectedRecord 数据模型。
    禁止 rejection 结构中直接包含 MessageRecord 等不可序列化对象，
    避免在 cmd_validate / cmd_run / cmd_profile 写出 rejected.jsonl 时
    因 `json.dumps(MessageRecord)` 抛 TypeError（HIGH-2 根因）。

    用于 parse / contract / duplicate / group 等所有阶段的单条记录拒绝。
    与 RejectionRecord（组级拒绝，可含 records: Tuple[MessageRecord, ...] 用于追溯）
    的区别：
    - RejectedRecord 是单条记录的拒绝，所有字段必须是 JSON 基本类型
    - RejectionRecord 是组级拒绝，允许保留 MessageRecord 对象用于追溯
    - 写入 rejected.jsonl 时使用 RejectedRecord；写入 rejected_groups.jsonl
      时从 RejectionRecord 转出可序列化 dict

    所有字段保证可 JSON 序列化：
    - line_number/message_id/layout_id/direction/raw_line 均为基本类型或 None
    - record_summary 是 dict（仅含基本类型），替代完整 MessageRecord 对象
    - 不保存 Python 对象实例（如 MessageRecord/Direction/FieldSpan）

    Attributes:
        line_number: 输入文件中的行号（1-based），None 表示非文件来源
        stage: 拒绝阶段标识（如 parse/contract/duplicate/group）
        reason_code: 稳定错误码（如 duplicate_message_id/invalid_json）
        message: 人类可读的拒绝消息
        message_id: 被拒绝记录的 message_id（如适用），None 表示无
        layout_id: 被拒绝记录的 layout_id（如适用）
        direction: 被拒绝记录的方向字符串值（如 "request"），用字符串而非
            Direction 枚举以便 JSON 序列化
        record_summary: 记录摘要（替代完整 MessageRecord 对象），如
            {'field_count': 2, 'payload_length': 4}
        raw_line: 原始行内容（如适用，便于调试），None 表示无
    """

    line_number: Optional[int]
    stage: str
    reason_code: str
    message: str
    message_id: Optional[str] = None
    layout_id: Optional[str] = None
    direction: Optional[str] = None
    record_summary: Optional[dict] = None
    raw_line: Optional[str] = None

    def __post_init__(self):
        """验证字段类型，保证所有字段可 JSON 序列化。

        R382：严格类型校验，禁止保存 Python 对象实例。
        - line_number 用 type is int 校验，拒绝 bool
        - stage/reason_code/message 必须是非空字符串
        - message_id/layout_id/direction/raw_line 必须是 str 或 None
        - record_summary 必须是 dict 或 None
        """
        # line_number 必须是 int 或 None（用 type is int 拒绝 bool）
        if self.line_number is not None and type(self.line_number) is not int:
            raise ValueError(
                f"line_number must be int or None, "
                f"got {type(self.line_number).__name__}: {self.line_number!r}"
            )

        # stage 必须是非空字符串
        if not isinstance(self.stage, str) or not self.stage.strip():
            raise ValueError(
                f"stage must be a non-empty string, got {self.stage!r}"
            )

        # reason_code 必须是非空字符串
        if not isinstance(self.reason_code, str) or not self.reason_code.strip():
            raise ValueError(
                f"reason_code must be a non-empty string, got {self.reason_code!r}"
            )

        # message 必须是字符串（允许空字符串，因为某些 reason_code 已足够说明）
        if not isinstance(self.message, str):
            raise ValueError(
                f"message must be str, got {type(self.message).__name__}: "
                f"{self.message!r}"
            )

        # message_id 必须是 str 或 None
        if self.message_id is not None and not isinstance(self.message_id, str):
            raise ValueError(
                f"message_id must be str or None, "
                f"got {type(self.message_id).__name__}: {self.message_id!r}"
            )

        # layout_id 必须是 str 或 None
        if self.layout_id is not None and not isinstance(self.layout_id, str):
            raise ValueError(
                f"layout_id must be str or None, "
                f"got {type(self.layout_id).__name__}: {self.layout_id!r}"
            )

        # direction 必须是 str 或 None（用字符串值而非 Direction 枚举，便于序列化）
        if self.direction is not None and not isinstance(self.direction, str):
            raise ValueError(
                f"direction must be str or None, "
                f"got {type(self.direction).__name__}: {self.direction!r}"
            )

        # record_summary 必须是 dict 或 None
        if self.record_summary is not None and not isinstance(self.record_summary, dict):
            raise ValueError(
                f"record_summary must be dict or None, "
                f"got {type(self.record_summary).__name__}: {self.record_summary!r}"
            )

        # raw_line 必须是 str 或 None
        if self.raw_line is not None and not isinstance(self.raw_line, str):
            raise ValueError(
                f"raw_line must be str or None, "
                f"got {type(self.raw_line).__name__}: {self.raw_line!r}"
            )

    def to_dict(self) -> dict:
        """转换为 JSON 可序列化的 dict。

        所有字段已是 JSON 基本类型（int/str/None/dict），可直接序列化。
        使用 dataclasses.asdict 保证字段完整且顺序稳定。

        Returns:
            包含所有字段的 dict，可直接传给 json.dumps
        """
        from dataclasses import asdict
        return asdict(self)


@dataclass(frozen=True)
class RunCounts:
    """分阶段 Run 计数数据模型。

    R348：停止使用 Prediction 数量冒充 validated_records。
    将 run 流水线各阶段的真实计数分开记录，避免混淆消息数和字段数。

    阶段划分：
    - input_line_count: 输入文件总行数（含空行）
    - JSON 解析阶段：json_valid_records / json_rejected_records
    - 契约校验阶段：contract_valid_records / contract_rejected_records
    - 组级校验阶段：group_valid_records / group_rejected_records
    - 产物阶段：field_profiles / predictions

    注意：
    - json_valid_records 包含通过 JSON 解析的记录（含后续契约校验失败的）；
      contract_valid_records 只含通过 JSON + 契约双重校验的记录
      （审计修复瑕疵-10：原实现两者等价、contract_rejected_records 恒为 0，现拆分）
    - group_valid_records 是进入 build_field_profiles 的记录数（消息数）
    - field_profiles 和 predictions 是字段数（不是消息数）
    - 不得用 predictions 数量冒充 validated_records（消息数）
    """

    input_line_count: int = 0
    json_valid_records: int = 0
    json_rejected_records: int = 0
    contract_valid_records: int = 0
    contract_rejected_records: int = 0
    group_valid_records: int = 0
    group_rejected_records: int = 0
    field_profiles: int = 0
    predictions: int = 0
    # R422：组数 vs 消息数严格分开
    # group_rejection_count：冲突组数量（每组包含多条消息）
    # group_rejected_records：这些组中实际包含的消息数量（与上面已存在的字段一致）
    # 原实现 total_rejections = len(rejected_records) + len(rejections) 混用记录数和组数，
    # R422 修正：total_rejected_record_count = 单记录拒绝数 + 组内消息数
    group_rejection_count: int = 0


@dataclass(frozen=True)
class RunManifestInfo:
    """Run manifest 运行状态和退出信息数据模型。

    R350：Manifest 增加运行状态和退出信息。
    将 run 命令的运行状态、退出码、partial 模式、报告可用性、
    开始/结束时间戳、命令行参数统一记录到 manifest。

    状态建议（与 cmd_run 三态逻辑对齐，R345）：
    - completed: 无 rejection，正常完成（exit 0）
    - partial_success: 有 rejection + --allow-partial-input + 有有效消息（exit 0）
    - invalid_input: 有 rejection + 无 --allow-partial-input（fail closed，exit 1）
    - no_valid_records: 0 有效记录（fail closed，exit 1）
    - invalid_ground_truth: （evaluate 命令用，run 不用）
    - failed: 其他未预期错误（exit 1）

    字段：
    - status: 运行状态字符串
    - exit_code: 退出码（0 成功，1 fail closed，2 输入文件问题）
    - partial_input: 是否启用了 --allow-partial-input
    - valid_for_reporting: manifest 指标是否可用于报告
    - started_at: 命令开始执行的 ISO 8601 时间戳
    - finished_at: 命令结束的 ISO 8601 时间戳
    - command_args: 命令行参数元组（frozen，用 tuple 而非 list）
    """

    status: str = "completed"
    exit_code: int = 0
    partial_input: bool = False
    valid_for_reporting: bool = True
    started_at: str = ""
    finished_at: str = ""
    command_args: Tuple[str, ...] = ()


@dataclass(frozen=True)
class FieldSample:
    """单个字段样本数据"""
    
    message_id: str
    field_key: FieldKey
    field_bytes: bytes
    start: int
    end: int
    message_length: int
    remaining_bytes: int
    capture_time: Optional[Any] = None
    session_id: Optional[str] = None
    pair_id: Optional[str] = None
    input_order: int = 0


@dataclass(frozen=True)
class DetectorEvidence:
    """检测器证据"""
    
    detector: str
    coarse_label: str
    fine_label: str
    score: float
    is_hard_evidence: bool
    reason_code: str
    details: Optional[dict] = None
    
    def __post_init__(self):
        """验证分数范围"""
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"score must be between 0.0 and 1.0, got {self.score}")


@dataclass(frozen=True)
class SemanticPrediction:
    """语义预测结果

    R234：新增 prediction_status 字段，允许值：
    - confirmed: 选中的证据为 hard evidence
    - candidate: 选中的证据为 soft evidence
    - abstained: 最终为 unknown（拒识）

    旧字段（run_id/layout_id/direction/field_index/coarse_label/fine_label/
    confidence/abstained/evidence/alternatives/config_summary）全部保留。
    """

    # 允许的 prediction_status 值
    PREDICTION_STATUSES = ("confirmed", "candidate", "abstained")

    run_id: str
    layout_id: str
    direction: Direction
    field_index: int
    coarse_label: str
    fine_label: str
    confidence: float
    abstained: bool
    evidence: Tuple[DetectorEvidence, ...]
    alternatives: Tuple[dict, ...]
    config_summary: Optional[dict] = None
    prediction_status: str = "abstained"

    def __post_init__(self):
        """验证预测结果"""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be between 0.0 and 1.0, got {self.confidence}")
        # R234: prediction_status 必须是合法值
        if self.prediction_status not in self.PREDICTION_STATUSES:
            raise ValueError(
                f"prediction_status must be one of {self.PREDICTION_STATUSES}, "
                f"got {self.prediction_status!r}"
            )


def to_json_safe(obj: Any) -> Any:
    """将对象转换为 JSON-safe 的 dict
    
    支持转换：
    - dataclass 实例
    - datetime 对象 -> ISO 8601 字符串
    - bytes 对象 -> 十六进制字符串
    - tuple/list -> 列表
    - Enum -> 值
    - 其他基本类型直接返回
    """
    from dataclasses import fields as dataclass_fields
    from datetime import datetime
    
    if hasattr(obj, '__dataclass_fields__'):
        result = {}
        for field in dataclass_fields(obj):
            value = getattr(obj, field.name)
            result[field.name] = to_json_safe(value)
        return result
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, bytes):
        return obj.hex()
    elif isinstance(obj, (tuple, list)):
        return [to_json_safe(item) for item in obj]
    elif isinstance(obj, Enum):
        return obj.value
    elif isinstance(obj, dict):
        return {k: to_json_safe(v) for k, v in obj.items()}
    else:
        return obj
