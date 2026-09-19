# 数据契约文档

本文档描述语义检测器中所有数据结构的契约定义，与 `src/semantic_detector/contracts.py`、`profile_builder.py`、`evaluation/ground_truth.py`、`evaluation/metrics.py` 中的实际实现保持一致。

> R310 更新：组级字段数不一致整组拒绝行为、SemanticPrediction（含 prediction_status）、9 个标准粗粒度标签、predictions.jsonl 实际输出格式均与代码核对一致。

---

## 一、核心数据结构

### Direction

来源：[contracts.py](src/semantic_detector/contracts.py)。

```python
class Direction(str, Enum):
    REQUEST = "request"
    RESPONSE = "response"
```

`ALLOWED_DIRECTIONS = {d.value for d in Direction}`。非法方向值在 `get_direction_or_raise` 中抛出 `ValueError`。

### FieldSpan

来源：[contracts.py](src/semantic_detector/contracts.py)。

```python
@dataclass(frozen=True)
class FieldSpan:
    field_index: int   # 字段索引，从 0 开始
    start: int         # 起始字节偏移（含）
    end: int           # 结束字节偏移（不含）
```

契约约束：
- `field_index >= 0`
- `start >= 0`，`end >= 0`
- `start < end`（空字段非法）

**R374 严格整数类型（HIGH-1 修复）**：
- `field_index`、`start`、`end` 必须是严格整数：`type(value) is int`
- **不接受** `bool`（因为 `True == 1`、`False == 0`，但 `isinstance(True, int)` 返回 `True`）
- **不接受** `float`（如 `0.0`、`1.0`）
- **不接受** `str`（如 `"1"`）
- **不接受** `None`
- JSONL 解析阶段同样严格，不做 `int()` / `str()` 静默转换

### MessageRecord

来源：[contracts.py](src/semantic_detector/contracts.py)。

```python
@dataclass(frozen=True)
class MessageRecord:
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
```

契约约束：
- `message_id`、`layout_id` 不能为空
- `direction` 必须是 `Direction` 枚举实例（不接受裸字符串）
- `payload` 不能为空
- `fields` 中每个 `FieldSpan.end <= len(payload)`（字段不得越界）
- `fields` 不得重叠（按 `start` 排序后相邻字段 `current.end <= next.start`）
- `field_index` 必须从 0 开始连续递增（`sorted(indices) == list(range(len(indices)))`）

**R376 严格类型（HIGH-1 修复）**：
- `message_id`、`layout_id`：必须为非空字符串（strip 后非空）
- `session_id`、`pair_id`：必须为字符串或 `None`
- `input_order`：必须是严格整数 `type(value) is int`，**不接受** `bool` / `float` / `str`
- `metadata`：必须为 `dict`，**不接受** `list`
- `payload`：必须为 `bytes`
- `fields`：必须为 `tuple[FieldSpan, ...]`
- JSONL 解析阶段不做 `str(123)` / `int("1")` / `dict(list)` 静默转换

### FieldKey

来源：[contracts.py](src/semantic_detector/contracts.py)。

```python
@dataclass(frozen=True)
class FieldKey:
    layout_id: str
    direction: Direction
    field_index: int
```

完整 FieldKey 三元组 `(layout_id, direction, field_index)` 唯一标识一个待检测字段组。所有 `direction` 必须是 `Direction` 枚举实例。

### RejectionRecord

来源：[contracts.py](src/semantic_detector/contracts.py)。R227 新增。

```python
REJECTION_REASON_INCONSISTENT_FIELD_COUNT = "inconsistent_field_count"

@dataclass(frozen=True)
class RejectionRecord:
    group_key: Tuple[str, str]                          # (layout_id, direction.value)
    record_count: int                                  # 该组被拒绝的记录总数
    field_counts: Tuple[Tuple[int, int], ...]          # 按 field_count 升序的 (count, num_records)
    reason_code: str                                   # 错误码，目前固定为 inconsistent_field_count
    records: Tuple[MessageRecord, ...] = ()
```

`field_counts` 形如 `((2, 5), (3, 1))` 表示 5 条记录有 2 个字段、1 条记录有 3 个字段；排序保证可复现。

### FieldSample

来源：[contracts.py](src/semantic_detector/contracts.py)。

```python
@dataclass(frozen=True)
class FieldSample:
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
```

`message_length` 是所属消息的总长度，`remaining_bytes = message_length - end`，`capture_time` 是消息抓取时间（UTC aware datetime，可为 None）。

### FieldProfile

来源：[profile_builder.py](src/semantic_detector/profiling/profile_builder.py)。R264-R275 持续扩展。

字段分组（节选，完整列表见源文件）：

| 分组 | 字段 |
|------|------|
| 标识 | `layout_id` / `direction` / `field_index` |
| 基础统计 | `sample_count` |
| 宽度与位置 | `width_min` / `width_max` / `width_mode` / `fixed_width` / `start_mode` / `end_mode` / `is_first_field_ratio` / `is_last_field_ratio` / `position_ratio_mean` |
| 字节统计 | `unique_value_count` / `unique_ratio` / `dominant_value_ratio` / `dominant_value_hex` / `dominant_value_count` / `all_zero_sample_ratio` / `zero_byte_ratio` / `printable_ascii_ratio` / `nonempty_string_ratio` / `utf8_decode_success_ratio` / `normalized_entropy` |
| 数值统计 BE | `numeric_be_min` / `_max` / `_mean` / `_median` / `_strictly_increasing_ratio` / `_nondecreasing_ratio` / `_step_one_ratio` / `_message_length_correlation` / `_remaining_bytes_correlation` / `_message_length_exact_support` / `_remaining_bytes_exact_support` / `_message_length_offset_support` / `_message_length_offset` / `_remaining_bytes_offset_support` / `_remaining_bytes_offset` |
| 数值统计 LE | 与 BE 对称（`numeric_le_*`） |
| 时间戳统计 BE | `timestamp_be_unix_seconds_support` / `_unix_milliseconds_support` / `_unix_microseconds_support` / `_ntp_seconds_support` |
| 时间戳统计 LE | 与 BE 对称（`timestamp_le_*`） |
| capture_time 元数据 | `capture_time_count` / `capture_time_coverage` / `capture_time_min` / `capture_time_max` |
| 元数据 | `insufficient_samples` / `numeric_be_distinct_value_count` / `numeric_le_distinct_value_count` |

关键契约：
- `dominant_value_hex` 在出现 tie（多个值同为最高频）时为 `None`，避免误导后续 type/opcode 后处理（R264/R283）。
- `numeric_be_distinct_value_count >= 2` 是 LengthDetector 的前置条件（教程 8.4，防止常量字段被误判为长度）。
- `capture_time_min/max` 仅在 `capture_time_count > 0` 时有值；TimestampDetector 不兜底系统时间（教程 9.4）。
- `numeric_be_message_length_correlation` 仅作辅助描述，不作为判定证据（R268 注释，R276 HIGH-7 修复改用 `*_exact_support`）。
- `to_dict()` 输出全部字段，`datetime` 转 ISO 字符串，`bytes` 转 hex，保证 JSON 可序列化（R274）。

### DetectorEvidence

来源：[contracts.py](src/semantic_detector/contracts.py)。

```python
@dataclass(frozen=True)
class DetectorEvidence:
    detector: str                       # 检测器名（constant/length/timestamp/sequence/string/identifier/payload/type_opcode/resolver）
    coarse_label: str                   # 9 个标准粗粒度标签之一
    fine_label: str                     # 细粒度标签（如 unix_seconds_be / ascii_string）
    score: float                        # [0.0, 1.0]
    is_hard_evidence: bool              # True 表示强证据
    reason_code: str                    # 机器可读原因码
    details: Optional[dict] = None      # 详细信息（检测器特定）
```

契约约束：
- `0.0 <= score <= 1.0`（`__post_init__` 强制）
- `coarse_label` 应为 9 个标准粗粒度标签之一（检测器内部需保证）
- `is_hard_evidence=True` 通常对应 `score >= 0.9`，但 `score` 不可单独推断 hard/soft（PayloadDetector `score=1.0` 仍是 soft）

### SemanticPrediction

来源：[contracts.py](src/semantic_detector/contracts.py)。R240-R248 修复 HIGH-3 后为流水线主输出。

```python
@dataclass(frozen=True)
class SemanticPrediction:
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
```

契约约束：
- `0.0 <= confidence <= 1.0`
- `prediction_status` 必须是 `confirmed` / `candidate` / `abstained` 三者之一（`__post_init__` 强制）
- `prediction_status` 与 `evidence[0].is_hard_evidence` 一致：
  - `confirmed`：选中的主证据为 hard evidence
  - `candidate`：选中的主证据为 soft evidence
  - `abstained`：无候选，最终为 `unknown`
- `evidence` 是元组（不可变），`evidence[0]` 为 primary，其余保留供审计
- `alternatives` 是稳定排序的字典元组，primary 不混入 alternatives（R292）

### GroundTruthRecord

来源：[ground_truth.py](src/semantic_detector/evaluation/ground_truth.py)。R249 新增 `layout_id` / `direction`，`semantic_type` 改名为 `semantic_label`。

```python
@dataclass(frozen=True)
class GroundTruthRecord:
    truth_id: int
    field_index: int
    semantic_label: str                 # 9 个标准粗粒度标签之一
    confidence: float
    is_hard_evidence: bool
    fine_label: Optional[str] = None
    details: Optional[dict] = None
    layout_id: str = "default"
    direction: str = "request"          # 字符串，不强制 Direction 枚举
```

契约约束：
- `truth_id` 必须唯一
- `(layout_id, direction, field_index)` 组合必须唯一
- `semantic_label` 必须是 9 个标准粗粒度标签之一（`validate_ground_truth` 强制）
- `0.0 <= confidence <= 1.0`
- 旧键名 `semantic_type` 在 `read_ground_truth_jsonl` 中仍被接受，自动映射为 `semantic_label`（向后兼容）

### AlignedPair

来源：[metrics.py](src/semantic_detector/evaluation/metrics.py)。

```python
@dataclass(frozen=True)
class AlignedPair:
    field_key: FieldKey
    prediction: Optional[DetectorEvidence]   # 从 SemanticPrediction.evidence[0] 提取
    truth: Optional[GroundTruthRecord]
    is_matched: bool
```

契约约束：
- `is_matched=True` 时 `prediction` 和 `truth` 都不能为 `None`
- `field_key` 来自 `(layout_id, direction, field_index)`

### EvaluationError

来源：[metrics.py](src/semantic_detector/evaluation/metrics.py)。

```python
@dataclass(frozen=True)
class EvaluationError:
    field_key: FieldKey
    error_type: str                          # wrong_label / abstained / missing_prediction / unexpected_prediction
    predicted_label: str
    true_label: str
    confidence: float
    details: Optional[dict] = None
```

四类错误分类：
- `wrong_label`：预测了非 unknown 标签但与真值不符
- `abstained`：预测为 unknown 但真值非 unknown
- `missing_prediction`：真值存在但无对应预测
- `unexpected_prediction`：预测存在但无对应真值

---

## 二、组级字段数不一致整组拒绝

来源：[collector.py](src/semantic_detector/profiling/collector.py) `validate_group_field_count`。R226-R232 修复 HIGH-2。

### 行为定义

对同一 `(layout_id, direction)` 组内的所有消息，若任一消息的 `len(fields)` 与其他消息不同，**整组拒绝**：
- 该组全部记录进入一个 `RejectionRecord`，`reason_code = "inconsistent_field_count"`
- **不保留第一条基准子集**，**不补齐**，**不截断**
- 只有组内所有记录字段数量一致时，整组保留为 `valid_groups`

### 稳定错误结构

`RejectionRecord.field_counts` 按 `field_count` 升序排序，形如 `((2, 5), (3, 1))`，保证不同运行可复现。

### CLI 接入

`prepare_records_for_profiling` 是 `cmd_validate` / `cmd_profile` / `cmd_run` 共享的单一入口，确保每个 CLI 命令都执行字段数校验，避免漏掉（修复 HIGH-2 的核心）。

### 与测试核对

`tests/unit/test_collector_groups.py` 覆盖：
- 全组字段数一致 → 整组保留
- 组内字段数不一致 → 整组拒绝，`RejectionRecord` 字段完整
- 多组混合：一组一致一组不一致
- `field_counts` 排序稳定性
- 空组处理

---

## 三、9 个标准粗粒度标签

来源：[taxonomy.py](src/semantic_detector/taxonomy.py)。R235 集中管理。

```python
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
```

| 标签 | 描述 | 典型特征 |
|------|------|----------|
| `constant` | 常量值 | `dominant_value_ratio >= 0.98`，`unique_value_count == 1` |
| `length` | 长度字段 | `exact_support` 或 `offset_support` 达阈值，`distinct_value_count >= 2` |
| `timestamp` | 时间戳 | `timestamp_*_support` 达阈值，`capture_time` 覆盖充足 |
| `sequence_or_counter` | 序列号/计数器 | `unique_ratio` 和 `strictly_increasing_ratio` 达阈值 |
| `string` | ASCII/UTF-8 字符串 | `printable_ascii_ratio` 达阈值，`fixed_width=True` 且 `width_mode > 1` |
| `identifier` | 标识符 | `unique_ratio == 1.0`，`score_cap = 0.7`（soft evidence） |
| `type_control` | 类型/操作码 | 跨 layout 一一对应映射，宽度 `<= 2`（教程 10.3） |
| `payload` | 载荷数据 | `normalized_entropy >= 0.7`，通常是末字段（soft evidence） |
| `unknown` | 未知/拒识 | 无候选或 ambiguity 不可消解 |

**旧标签兼容**：`normalize_legacy_label` 仅用于读取历史产物或兼容旧测试，不得根据协议名称动态猜测标签。映射表：

| 旧标签 | 标准标签 |
|-------|----------|
| `identifier_candidate` | `identifier` |
| `opaque_payload_candidate` / `opaque_payload` | `payload` |
| `type_opcode` / `type_or_opcode` / `type_or_opcode_candidate` / `type` / `opcode` | `type_control` |
| `sequence` / `counter` | `sequence_or_counter` |

**注意**：旧文档中出现的 `total_length` / `remaining_length` / `utf8_string` / `ambiguous` 等**不再是粗粒度标签**：
- `total_length` / `remaining_length` 是 `length` 的 `fine_label`
- `utf8_string` 是 `string` 的 `fine_label`
- `ambiguous` 状态由 `prediction_status="abstained"` + `coarse_label="unknown"` 表达

---

## 四、预测状态

来源：[taxonomy.py](src/semantic_detector/taxonomy.py) 和 [contracts.py](src/semantic_detector/contracts.py) `SemanticPrediction.PREDICTION_STATUSES`。

```python
PREDICTION_STATUSES = ("confirmed", "candidate", "abstained")
```

| 状态 | 含义 | coarse_label | evidence[0].is_hard_evidence |
|------|------|--------------|------------------------------|
| `confirmed` | 选中的证据为 hard evidence | 非 unknown | True |
| `candidate` | 选中的证据为 soft evidence | 非 unknown | False |
| `abstained` | 无候选或 ambiguity 不可消解，拒识 | `unknown` | 无 evidence 或 resolver 占位 |

`abstained` 字段（bool）与 `prediction_status == "abstained"` 等价，保留是为向后兼容旧消费者。

---

## 五、输入输出契约

### 输入文件 messages.jsonl

JSONL 格式，每行一个 JSON 对象：

```json
{
  "message_id": "msg_001",
  "layout_id": "login_request",
  "direction": "request",
  "payload_hex": "010000001a...",
  "fields": [
    {"field_index": 0, "start": 0, "end": 1},
    {"field_index": 1, "start": 1, "end": 5}
  ],
  "capture_time": "2020-01-01T00:00:00+00:00"
}
```

契约约束：
- `payload_hex` 必须是有效十六进制字符串
- `fields` 必须从 `field_index=0` 开始连续
- 字段边界不得越界、不得重叠
- 同 `(layout_id, direction)` 组内 `len(fields)` 必须一致，否则**整组拒绝**
- `capture_time` 可选，ISO 8601 字符串（UTC aware）

### 输出文件 predictions.jsonl

R240-R248 后，每行是一个 `SemanticPrediction` 序列化结果（不再是 `DetectorEvidence`）：

```json
{
  "run_id": "44f19d89-...",
  "layout_id": "auth_token",
  "direction": "request",
  "field_index": 0,
  "coarse_label": "type_control",
  "fine_label": "type_or_opcode_candidate",
  "confidence": 0.4,
  "abstained": false,
  "prediction_status": "candidate",
  "evidence": [
    {
      "detector": "type_opcode",
      "coarse_label": "type_control",
      "fine_label": "type_or_opcode_candidate",
      "is_hard_evidence": false,
      "score": 0.4,
      "reason_code": "one_to_one_mapping",
      "details": {
        "layout_values": {"auth_token": "05", "data_request": "02", "heartbeat": "04", "login_request": "01"},
        "layout_count": 4,
        "unique_value_count": 4,
        "alignment_key": ["request", 0, 1, 0]
      }
    }
  ],
  "alternatives": []
}
```

字段说明：
- `evidence` 是数组，`evidence[0]` 为 primary，其余为保留的候选证据
- `alternatives` 是数组，每个元素是除 primary 外的候选证据字典（R292 稳定排序）
- `confidence` 等于 `evidence[0].score`
- `prediction_status` 与 `evidence[0].is_hard_evidence` 一致

### 输出文件 metrics.json

```json
{
  "overall_accuracy": 0.8095,
  "coverage": 0.8571,
  "unknown_rate": 0.1429,
  "covered_accuracy": 0.9444,
  "fine_top1_accuracy": 0.8571,
  "macro_f1": 0.7556,
  "matched_count": 21,
  "total_truths": 21
}
```

### 输出文件 per_label_metrics.csv

```csv
label,precision,recall,f1,support
constant,1.0,1.0,1.0,2
length,1.0,1.0,1.0,4
...
```

### 输出文件 confusion_matrix.csv

```csv
true\pred,constant,length,payload,sequence_or_counter,string,timestamp,type_control,unknown
constant,2,0,0,0,0,0,0,0
length,0,4,0,0,0,0,0,0
...
```

### 输出文件 errors.jsonl

每行一个 `EvaluationError` 序列化结果：

```json
{
  "field_key": {"layout_id": "auth_token", "direction": "request", "field_index": 2},
  "error_type": "wrong_label",
  "predicted_label": "string",
  "true_label": "identifier",
  "confidence": 1.0,
  "details": {"evidence": {...}, "truth": {...}}
}
```

`error_type` 取值：`wrong_label` / `abstained` / `missing_prediction` / `unexpected_prediction`。

---

## 六、校验规则

### 输入校验（cmd_validate）

1. **字段越界校验**：`FieldSpan.end <= len(payload)`
2. **字段重叠校验**：按 `start` 排序后相邻字段不重叠
3. **field_index 连续性校验**：从 0 开始连续
4. **组级字段数一致性校验**：同 `(layout_id, direction)` 组内 `len(fields)` 必须一致，否则**整组拒绝**（HIGH-2）
5. **方向合法性校验**：`direction` 必须是 `request` 或 `response`

### 画像校验（build_field_profile）

1. `sample_count >= min_samples`（默认 8），否则 `insufficient_samples=True`
2. `dominant_value_hex` 在 tie 时为 `None`
3. `numeric_*_distinct_value_count` 防止常量字段被误判为长度

### 真值校验（validate_ground_truth）

1. `truth_id` 唯一
2. `(layout_id, direction, field_index)` 组合唯一
3. `semantic_label` 必须是 9 个标准粗粒度标签之一

### 预测校验（SemanticPrediction.__post_init__）

1. `0.0 <= confidence <= 1.0`
2. `prediction_status` 必须是 `confirmed` / `candidate` / `abstained` 之一

---

## 七、CLI 退出语义（R361）

来源：[cli.py](src/semantic_detector/cli.py) `cmd_validate` / `cmd_profile` / `cmd_run` / `cmd_evaluate`。

### validate

| 退出码 | 含义 |
|--------|------|
| 0 | 全部记录通过 JSON 解析 + 契约校验 + 组级字段数校验 |
| 1 | 存在任一拒绝（JSON 损坏 / 字段越界 / 字段数不一致等） |
| 2 | 输入文件不存在或路径不是文件 |

**默认 fail closed**：任何 `rejection > 0` → exit 1。无 `--allow-partial-input` 参数。

### profile

| 退出码 | 含义 |
|--------|------|
| 0 | 成功生成画像（即使存在被跳过的组级拒绝） |
| 1 | 读取/生成失败（如 JSON 损坏、画像构建异常） |
| 2 | 输入文件不存在或路径不是文件 |

**注意**：profile 对字段数不一致的组**跳过**（不送入 build_field_profiles），但 exit 0；如需 fail closed 请先用 `validate`。

### run

| 退出码 | 含义 |
|--------|------|
| 0 | 全链路成功，无任何拒绝 |
| 1 | 默认模式下存在任一拒绝（JSON/契约/组级）；或读取/生成/评估失败 |
| 2 | 输入文件不存在或路径不是文件 |

**默认 fail closed**：任何 `rejection > 0` → exit 1。
**显式 `--allow-partial-input`**：对有效消息子集继续 run，exit 0（即使存在拒绝）。

### evaluate

| 退出码 | 含义 |
|--------|------|
| 0 | 真值全部合法，评估完成 |
| 1 | 默认模式下存在任一真值拒绝；或评估失败 |
| 2 | 输入文件不存在或路径不是文件 |

**默认 fail closed**：任何真值拒绝 → exit 1。
**显式 `--allow-partial-ground-truth`**：对合法真值子集继续评价，exit 0（即使存在拒绝）。

---

## 八、partial-input 和 partial-ground-truth 模式（R361）

来源：[cli.py](src/semantic_detector/cli.py) `--allow-partial-input` / `--allow-partial-ground-truth`。

### 设计原则

- **默认 fail closed**：任何拒绝（JSON 损坏 / 契约不合规 / 组级字段数不一致 / 真值损坏）→ exit 1
- **显式 opt-in**：用户必须通过命令行参数显式允许 partial 模式
- **不允许默认静默吞掉错误**：partial 模式下仍导出 rejected*.jsonl，便于审计

### --allow-partial-input（run 子命令）

```bash
python -m semantic_detector.cli run input.jsonl --output-dir out --allow-partial-input
```

行为：
- 对有效消息子集继续 run（即使存在 JSON/契约/组级拒绝）
- exit 0（即使存在拒绝）
- 仍导出 `rejected.jsonl` / `rejected_groups.jsonl` 供审计

### --allow-partial-ground-truth（evaluate 子命令）

```bash
python -m semantic_detector.cli evaluate predictions.jsonl ground_truth.jsonl --allow-partial-ground-truth
```

行为：
- 对合法真值子集继续评价（即使存在真值拒绝）
- exit 0（即使存在真值拒绝）
- 仍导出 `rejected_ground_truth.jsonl` 供审计

---

## 九、配置使用方式（R361）

来源：[config.py](src/semantic_detector/config.py) + [cli.py](src/semantic_detector/cli.py) `--config` 参数。

### Config 数据类（14 个字段）

```python
@dataclass
class Config:
    min_samples: int = 8
    constant_support: float = 0.98
    length_support: float = 0.90
    timestamp_support: float = 0.90
    timestamp_slop_seconds: int = 86400
    sequence_unique_ratio: float = 0.70
    sequence_increasing_ratio: float = 0.80
    string_printable_ratio: float = 0.85
    string_nonempty_ratio: float = 0.80
    identifier_unique_ratio: float = 0.80
    identifier_score_cap: float = 0.70
    payload_entropy_threshold: float = 0.70
    ambiguity_margin: float = 0.08
    type_opcode_min_dominant_ratio: float = 0.50
```

### CLI --config 参数（profile / infer / run 子命令）

```bash
# 使用默认配置（config/defaults.json）
python -m semantic_detector.cli run input.jsonl --output-dir out

# 使用用户配置覆盖默认值
python -m semantic_detector.cli run input.jsonl --output-dir out --config my_config.json
```

`--config PATH` 加载用户配置文件，通过 `load_config_with_override` 用用户值覆盖默认值（只覆盖用户提供的字段，其余保持默认）。

### 配置端到端贯通（R354-R359 MEDIUM-3 修复链）

配置从 CLI → Pipeline → 检测器/Resolver → 上下文阈值 → Manifest 审计字段端到端贯通：

1. **CLI --config**（R354）：加载用户配置或默认配置
2. **Pipeline 接收 config**（R355）：`DetectionPipeline(config=config)` → 所有检测器和 Resolver 共享同一 Config 实例
3. **检测器使用 config**（R356）：11 个阈值真实影响检测器行为
4. **Resolver 使用 config**（R357）：`ambiguity_margin` 真实影响 Resolver 模糊检查
5. **上下文阈值统一**（R358）：5 个上下文阈值全部由 Config 驱动（timestamp_slop_seconds / timestamp_support / min_samples / type_opcode_min_dominant_ratio / identifier_score_cap）
6. **Manifest 配置审计**（R359）：manifest 写入 `resolved_config` / `config_source` / `config_sha256`

### Manifest 配置审计字段（R359）

`manifest.json` 的 `config` 段包含 5 个字段：

```json
{
  "config": {
    "detectors": ["constant", "length", "timestamp", ...],
    "resolver": "Resolver",
    "resolved_config": { /* Config.to_dict() 完整快照 */ },
    "config_source": "default",  // 或用户配置文件路径
    "config_sha256": "..."        // 64 字符 hex，基于 json.dumps(sort_keys=True) + sha256
  }
}
```

- 同一配置哈希稳定（`hash1 == hash2 == hash3`）
- 覆盖值改变哈希（如 `min_samples=10` vs 默认 `3`，哈希不同）
- manifest 中的 `resolved_config` 与 Pipeline 实际 `config.to_dict()` 一致

---

## 十、Demo 指标局限声明（R361）

### Demo 指标不是实际协议性能

本项目的 Demo 指标（`examples/output/evaluation/metrics.json`）仅基于 `examples/messages.jsonl`（21 条真值）的小样本评估，**不代表任意协议或真实流量上的检测准确率**。

### Demo 指标含义

| 指标 | Demo 值 | 含义 |
|------|---------|------|
| `overall_accuracy` | 0.8095 | 21 条真值中 17 条预测正确 |
| `coverage` | 0.8571 | 21 条真值中 18 条有非 unknown 预测 |
| `unknown_rate` | 0.1429 | 21 条真值中 3 条预测为 unknown（拒识） |
| `covered_accuracy` | 0.9444 | 18 条有预测的真值中 17 条正确 |
| `fine_top1_accuracy` | 0.8571 | 21 条真值中 18 条 fine_label 完全匹配 |
| `macro_f1` | 0.7556 | 8 个非 unknown 标签的宏平均 F1 |

### Demo 错误分析

Demo 中 4 个错误均为检测器的合理局限：
- 1 个 `wrong_label`：检测器在特征重叠时的合理误判
- 3 个 `abstained`：检测器在证据不足时主动拒识（非崩溃）

### 不得泛化

- **不得**将 Demo 指标泛化为"检测器在任意协议上准确率 80%+"
- **不得**将 Demo 指标用于论文级性能声明
- **不得**隐藏 Demo 的 4 个错误或夸大覆盖范围
- Demo 仅用于验证流水线端到端可运行 + 评估闭环可计算

---

## 十一、严格错误行为（R408）

本节汇总 R372-R406 修复链确立的 8 项严格错误行为，作为数据契约的强制规范。任何违反这些行为的输入或状态都必须被拒绝、标记或失败，不得静默降级。

### 1. 所有字段的严格 JSON 类型

**来源**：R374/R376/R377/R378（HIGH-1 修复，阶段 A）

- `field_index`、`start`、`end`：必须是严格整数 `type(value) is int`
- `message_id`、`layout_id`：必须为非空字符串（strip 后非空）
- `session_id`、`pair_id`：必须为字符串或 `None`
- `input_order`：必须为严格整数，**不接受** `bool` / `float` / `str`
- `metadata`：必须为 `dict`，**不接受** `list`
- `payload`：必须为 `bytes`
- JSONL 解析阶段不做 `int()` / `str()` / `dict()` 静默转换
- 非法类型进入 `rejected.jsonl`，`reason_code` 可定位到字段类型错误

### 2. bool 不接受为 int

**来源**：R374（HIGH-1 修复，阶段 A）

- Python 中 `True == 1`、`False == 0`，但 `isinstance(True, int)` 返回 `True`
- 所有整数字段必须用 `type(value) is int` 检查，**不接受** `isinstance(value, int)` 直接接受 bool
- `field_index = True`、`start = False`、`input_order = True` 必须被拒绝

### 3. 非法 direction 不转 unknown

**来源**：R397（HIGH-5 修复，阶段 D）

- `direction` 只接受 `request` 或 `response`（`ALLOWED_DIRECTIONS`）
- 非法值（如 `foo`、`bar`、`""`、`None`、`unknown`）在 `get_direction_or_raise` 中抛出 `ValueError`
- **不得**降级为 `Direction.UNKNOWN`（已删除该枚举值）
- Prediction 侧：`read_semantic_predictions_from_jsonl` 非法 direction 抛 `ValueError`
- Ground Truth 侧：`read_ground_truth_jsonl` 非法 direction 进入 rejected，`reason_code=invalid_direction`
- CLI `evaluate` 遇到非法 direction 返回退出码 1，不生成 `metrics.json`

### 4. duplicate FieldKey 评价失败

**来源**：R399（HIGH-5 修复，阶段 D）

- `FieldKey = (layout_id, direction, field_index)` 三元组唯一标识一个待检测字段组
- `align_predictions_with_truth` 先规范化（严格 direction 解析），再检查重复
- **不得**先用原始字符串判断不重复，后归一化成同一键，静默覆盖
- duplicate FieldKey 抛 `ValueError`，消息包含 `duplicate` 标识
- 错误顺序：读取原始记录 → 严格字段校验 → 规范化合法字段 → 生成 FieldKey → 检查重复 → 构建字典

### 5. 评价数量守恒

**来源**：R400（HIGH-5 修复，阶段 D）

- 正式评价必须满足：
  - `matched_predictions + unmatched_predictions = total_predictions`
  - `matched_truths + missing_predictions = total_truths`
- `missing_predictions = unmatched_truths`（有 truth 没 pred）
- 不守恒时 `valid_for_reporting=false`，`status=internal_count_inconsistency`
- `verify_count_conservation` 作为额外防御，即使有内部 bug 也能检测到不守恒

### 6. Profile 默认不允许部分输入

**来源**：R385（HIGH-3 修复，阶段 B）

- `profile` 命令默认对任何 rejection 都失败：`exit 1`，`status=invalid_input`
- **不得**静默丢弃 `_rejected_records`，**不得**返回 `exit 0` 冒充完整成功
- 所有 rejection 写入 `rejected.jsonl`，可 JSON 解析，`reason_code` 明确
- `--allow-partial-input` 必须显式开启：
  - `status=partial_success`
  - `valid_for_reporting=false`
  - rejected 数量写入 manifest 或 profile summary
  - 全部记录无效时，即使 partial 也必须失败

### 7. 失败 run 不保留旧结果

**来源**：R387-R390（HIGH-4 修复，阶段 C）

- `run` 命令开始时清理自身拥有的旧产物（`clean_command_artifacts`）
- 失败运行写入失败 Manifest（`build_failed_run_manifest`，14 字段）
- **不得**保留上一次成功的 `predictions.jsonl` 或 `manifest.json`
- **不得**没有 Manifest（失败也要有产物）
- 清理动作写入日志，不删除输入文件或其他 run_id 目录

### 8. 每个命令的产物所有权

**来源**：R388（HIGH-4 修复，阶段 C）

每个命令只负责清理和写入自己拥有的产物文件：

| 命令 | 拥有的产物 |
|------|-----------|
| `validate` | `validated.jsonl`、`rejected.jsonl`、`validate.log` |
| `profile` | `field_profiles.jsonl`、`rejected.jsonl`、`rejected_groups.jsonl`、`profile.log`、`profile_manifest.json` |
| `infer` | `predictions.jsonl`、`infer.log`、`infer_manifest.json` |
| `run` | `validated.jsonl`、`rejected.jsonl`、`rejected_groups.jsonl`、`field_profiles.jsonl`、`predictions.jsonl`、`manifest.json`、`run.log` |
| `evaluate` | `metrics.json`、`per_label_metrics.csv`、`confusion_matrix.csv`、`errors.jsonl`、`rejected_ground_truth.jsonl`、`evaluation_manifest.json` |

详细所有权清单见 [ARTIFACT_OWNERSHIP.md](ARTIFACT_OWNERSHIP.md)。

---

## 十二、版本控制

数据契约版本: 3.0.0（R310 初版，R361 新增第七至第十节，R408 新增第十一节"严格错误行为" + FieldSpan/MessageRecord 严格类型说明）

变更时需要：
1. 更新版本号
2. 更新本文档
3. 运行所有测试确保兼容性：`python -m pytest -q`
