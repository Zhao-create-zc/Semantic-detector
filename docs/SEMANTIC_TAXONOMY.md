# 语义分类体系

本文档描述语义检测器使用的语义分类体系，与 [taxonomy.py](../src/semantic_detector/taxonomy.py) 和各检测器源码保持一致。

>  更新：9 个标准粗粒度标签与 candidate 状态拆分（candidate 状态由 `fine_label` 表达，不混入 `coarse_label`）；旧标签映射表；删除已废弃的 `total_length` / `remaining_length` / `utf8_string` / `ambiguous` 粗粒度标签。

---

## 一、设计原则

1. **粗粒度标签（coarse_label）** 只有 9 个，由 [taxonomy.py](../src/semantic_detector/taxonomy.py) `CANONICAL_COARSE_LABELS` 集中定义，不得根据协议名称动态猜测。
2. **candidate 状态由 `fine_label` 表达**，不混入 `coarse_label`。例如 `identifier_candidate` 是 `fine_label`，对应 `coarse_label="identifier"`。
3. **细粒度标签（fine_label）** 由各检测器输出，描述具体格式或子类型。
4. **拒识状态由 `prediction_status="abstained"` + `coarse_label="unknown"` 表达**，不再使用 `ambiguous` 标签。

---

## 二、9 个标准粗粒度标签

来源：[taxonomy.py](../src/semantic_detector/taxonomy.py) `CANONICAL_COARSE_LABELS`。

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

### 1. constant（常量）

- **定义**：在所有消息中取值相同的字段。
- **检测器**：[constant.py](../src/semantic_detector/detectors/constant.py) `ConstantDetector`
- **命中条件**：`dominant_value_ratio >= 0.98`（hard evidence，阻止 type_control 升级）
- **fine_label**：`constant_value`
- **reason_code**：`all_samples_identical`
- **典型场景**：协议版本号、固定魔数、固定长度消息的 length 字段（值始终相同）

### 2. length（长度）

- **定义**：表示数据长度的字段。
- **检测器**：[length.py](../src/semantic_detector/detectors/length.py) `LengthDetector`
- **命中条件**：
  - `exact_support` 达阈值（offset=0，值等于 message_length 或 remaining_bytes）或
  - `offset_support` 达阈值（offset≠0，值等于 message_length ± offset 或 remaining_bytes ± offset）
  - `distinct_value_count >= 2`（教程 8.4，防止常量字段被误判）
  -  修复：使用精确等式支持率，不再使用 Pearson correlation
- **fine_label**：
  - `total_message_length`（值等于消息总长度）
  - `remaining_bytes`（值等于剩余字节数）
- **reason_code**：`value_equals_message_length` / `value_equals_remaining_bytes_plus_offset` 等
- **典型场景**：字符串长度、数组长度、数据块长度

### 3. timestamp（时间戳）

- **定义**：表示时间点的字段。
- **检测器**：[timestamp.py](../src/semantic_detector/detectors/timestamp.py) `TimestampDetector`
- **命中条件**：
  - `timestamp_*_support` 达阈值（4 字节 Unix 秒/NTP 秒，8 字节 Unix 毫秒/微秒，BE/LE 独立）
  - `capture_time_count > 0` 且 `capture_time_coverage` 充足（教程 9.4，不兜底系统时间）
  -  修复：直接读取 profile 的 support 字段
- **fine_label** 格式：`{format}_{endian}`，如 `unix_seconds_be`、`unix_milliseconds_le`
- **支持的 format**：`unix_seconds` / `unix_milliseconds` / `unix_microseconds` / `ntp_seconds`
- **支持的 endian**：`be` / `le`
- **reason_code**：`value_is_{format}_{endian}`，如 `value_is_unix_seconds_be`
- **典型场景**：创建时间、更新时间、事件时间

### 4. sequence_or_counter（序列号/计数器）

- **定义**：递增或递减的序列字段。
- **检测器**：[sequence.py](../src/semantic_detector/detectors/sequence.py) `SequenceDetector`
- **命中条件**：
  - `unique_ratio >= 0.70`（Config.sequence_unique_ratio）
  - `strictly_increasing_ratio >= 0.80`（Config.sequence_increasing_ratio）
  - 输出 hard evidence
- **fine_label** 格式：`sequence_{bit_width}bit_{endian}`，如 `sequence_32bit_be`、`sequence_16bit_le`
- **reason_code**：`strictly_increasing_sequence` 等
- **典型场景**：消息序列号、请求 ID、事务 ID
- **冲突规则**（，）：与 length/timestamp 同时命中时，length/timestamp 胜出，sequence_or_counter 进入 alternatives

### 5. string（字符串）

- **定义**：文本字符串字段。
- **检测器**：[string.py](../src/semantic_detector/detectors/string.py) `StringDetector`
- **命中条件**：
  - `fixed_width=True` 且 `width_mode > 1`（防止单字节误命中）
  - `printable_ascii_ratio >= 0.85`（Config.string_printable_ratio）或 `utf8_decode_success_ratio` 达标
  - 输出 hard evidence
- **fine_label**：
  - `ascii_string`（printable ASCII）
  - `utf8_string`（UTF-8 可解码）
- **reason_code**：`ascii_string_detected` / `utf8_string_detected`
- **典型场景**：用户名、消息内容、文件名
- **冲突规则**（，）：与 constant 同时命中时，按宽度和 printable_ratio 选择（宽度>1 且 printable>=0.85 时 string 胜出，否则 constant 胜出）

### 6. identifier（标识符）

- **定义**：唯一性高、非递增的字段。
- **检测器**：[identifier.py](../src/semantic_detector/detectors/identifier.py) `IdentifierDetector`
- **命中条件**：
  - `unique_ratio >= 0.80`（Config.identifier_unique_ratio）
  - 非递增（与 sequence_or_counter 区分）
  - 输出 **soft evidence**，`score_cap = 0.70`（Config.identifier_score_cap）
- **fine_label**：`identifier_candidate`（candidate 状态由 fine_label 表达，不混入 coarse_label）
- **reason_code**：`high_unique_non_increasing`
- **典型场景**：会话 ID、用户 ID、UUID、哈希

### 7. type_control（类型/操作码）

- **定义**：跨多个 layout 在同位置出现一一对应映射的字段。
- **检测器**：[type_opcode.py](../src/semantic_detector/detectors/type_opcode.py) `TypeOpcodeDetector` + [pipeline.py](../src/semantic_detector/pipeline/pipeline.py) `_postprocess_type_opcode`
- **跨 layout 分组条件**（教程 10.3）：
  - 至少两个不同 layout
  - 至少两个不同主值
  - 宽度不超过 2
  - 同一 layout 只贡献一个真实主值
- **强证据排除**（教程 10.5，）：length 或 timestamp 强证据不得被 type/opcode 覆盖；constant 等可被升级
- **fine_label**：`type_or_opcode_candidate`（candidate 状态由 fine_label 表达）
- **reason_code**：`one_to_one_mapping`
- **details 必填键**（教程 10.4，）：`layout_values` / `layout_count` / `unique_value_count` / `alignment_key`
- **典型场景**：操作码、状态码、消息类型标识

### 8. payload（载荷）

- **定义**：高熵、无明显模式的字段。
- **检测器**：[payload.py](../src/semantic_detector/detectors/payload.py) `PayloadDetector`
- **命中条件**：
  - `normalized_entropy >= 0.70`（Config.payload_entropy_threshold）
  - 通常是末字段（`is_last_field_ratio` 高）
  - 输出 **soft evidence**（`is_hard_evidence=false`），不阻止其他检测器
- **fine_label**：`opaque_payload_candidate`（candidate 状态由 fine_label 表达）
- **reason_code**：`high_entropy_trailing_field`
- **典型场景**：加密数据、压缩数据、二进制载荷

### 9. unknown（未知/拒识）

- **定义**：无候选或 ambiguity 不可消解的字段。
- **来源**：[resolver.py](../src/semantic_detector/scoring/resolver.py) `resolve_with_context` 在无候选时输出
- **fine_label**：`unknown`
- **reason_code**：`no_candidates` / `ambiguous`（resolver 占位）
- **prediction_status**：`abstained`
- **典型场景**：新协议字段、自定义字段、特征不足的字段

---

## 三、candidate 状态拆分（核心设计）

**关键原则**：candidate 状态由 `fine_label` 表达，**不混入 `coarse_label`**。

| 检测器 | coarse_label | fine_label | is_hard_evidence | 说明 |
|--------|--------------|------------|------------------|------|
| ConstantDetector | `constant` | `constant_value` | True | hard |
| LengthDetector | `length` | `total_message_length` / `remaining_bytes` | True | hard |
| TimestampDetector | `timestamp` | `unix_seconds_be` 等 | True | hard |
| SequenceDetector | `sequence_or_counter` | `sequence_32bit_be` 等 | True | hard |
| StringDetector | `string` | `ascii_string` / `utf8_string` | True | hard |
| IdentifierDetector | `identifier` | `identifier_candidate` | **False** | soft，score_cap=0.7 |
| PayloadDetector | `payload` | `opaque_payload_candidate` | **False** | soft |
| TypeOpcodeDetector | `type_control` | `type_or_opcode_candidate` | **False** | soft（跨 layout 后处理升级） |
| Resolver（无候选） | `unknown` | `unknown` | False | abstained |

**注意**：
- `identifier_candidate`、`opaque_payload_candidate`、`type_or_opcode_candidate` 是 **fine_label**，不是粗粒度标签。对应的 `coarse_label` 分别是 `identifier`、`payload`、`type_control`。
- 旧文档可能误将 `identifier_candidate` / `type_opcode` 当作粗粒度标签，这是错误的。 已通过 `CANONICAL_COARSE_LABELS` 集中修正。

---

## 四、旧标签兼容映射

来源：[taxonomy.py](../src/semantic_detector/taxonomy.py) `_LEGACY_LABEL_MAP` 和 `normalize_legacy_label`。

`normalize_legacy_label` **仅用于读取历史产物或兼容旧测试**，不得根据协议名称动态猜测标签。

| 旧标签（已废弃） | 标准粗粒度标签 | 说明 |
|------------------|----------------|------|
| `identifier_candidate` | `identifier` | fine_label 误用为 coarse_label |
| `opaque_payload_candidate` | `payload` | fine_label 误用为 coarse_label |
| `opaque_payload` | `payload` | 旧简称 |
| `type_opcode` | `type_control` | 旧名 |
| `type_or_opcode` | `type_control` | 旧名 |
| `type_or_opcode_candidate` | `type_control` | fine_label 误用为 coarse_label |
| `type` | `type_control` | 旧简称 |
| `opcode` | `type_control` | 旧简称 |
| `sequence` | `sequence_or_counter` | 旧简称（ 修正 resolver） |
| `counter` | `sequence_or_counter` | 旧简称 |

### 已废弃的粗粒度标签（不再是 coarse_label）

| 旧粗粒度标签 | 现状 | 替代 |
|--------------|------|------|
| `total_length` | 已废弃 | `length` 的 fine_label `total_message_length` |
| `remaining_length` | 已废弃 | `length` 的 fine_label `remaining_bytes` |
| `utf8_string` | 已废弃 | `string` 的 fine_label `utf8_string` |
| `ambiguous` | 已废弃 | `prediction_status="abstained"` + `coarse_label="unknown"` |
| `identifier_candidate`（作为 coarse） | 已废弃 | `coarse_label="identifier"` + `fine_label="identifier_candidate"` |
| `type_opcode`（作为 coarse） | 已废弃 | `coarse_label="type_control"` |

---

## 五、预测状态

来源：[taxonomy.py](../src/semantic_detector/taxonomy.py) `PREDICTION_STATUSES` 和 [contracts.py](../src/semantic_detector/contracts.py) `SemanticPrediction.PREDICTION_STATUSES`。

```python
PREDICTION_STATUSES = ("confirmed", "candidate", "abstained")
```

| 状态 | 含义 | coarse_label | evidence[0].is_hard_evidence |
|------|------|--------------|------------------------------|
| `confirmed` | 选中的证据为 hard evidence | 非 unknown | True |
| `candidate` | 选中的证据为 soft evidence | 非 unknown | False |
| `abstained` | 无候选或 ambiguity 不可消解，拒识 | `unknown` | 无 evidence 或 resolver 占位 |

**与 candidate fine_label 的区别**：
- `prediction_status="candidate"` 是预测级别状态，表示最终选中的是 soft evidence
- `fine_label="*_candidate"`（如 `identifier_candidate`）是检测器级别的细粒度标签，表示该检测器输出的是候选证据
- 两者独立：一个 `prediction_status="candidate"` 的预测，其 `evidence[0].fine_label` 可能是 `identifier_candidate`（soft）或 `type_or_opcode_candidate`（soft）

---

## 六、Resolver 冲突规则与解析顺序

来源：[resolver.py](../src/semantic_detector/scoring/resolver.py) `resolve_with_context`。 修复。

### 正确解析顺序（教程 11.2）

1. 删除无效证据（score 不在 [0,1] 或 coarse_label 不合法）
2. 删除 abstain 占位（resolver unknown 占位不参与选择）
3. 规范化旧标签（`normalize_legacy_label`，仅读取历史产物时）
4. 执行专项冲突规则（教程 11.3）：
   - length vs sequence_or_counter → length 胜出
   - timestamp vs sequence_or_counter → timestamp 胜出
   - constant vs string → 按宽度/printable_ratio 选择
5. hard 优先（教程 11.2 第 5 步 / 11.4，）：有 hard evidence 时直接选最高分 hard，不走 ambiguity
6. 同等级按 score 降序排序（`select_best_candidate`）
7. ambiguity 检查（教程 11.4，仅在只有 soft 候选时）：同分差 < `ambiguity_margin` 时输出 unknown(abstained)
8. 无候选输出 unknown（`prediction_status="abstained"`）
9. 保留 alternatives：候选列表 = [primary] + alternatives，按分数降序，primary 在第一位

**关键约束**（教程 11.4）：ambiguity 检查必须在专项冲突规则和 hard 优先之后，否则 length=1.0/sequence=1.0 直接 unknown 导致领域规则失效。

---

## 七、标签层次结构

```
coarse_label（9 个标准粗粒度标签）
│
├── constant
│   └── fine_label: constant_value
│
├── length
│   ├── fine_label: total_message_length
│   └── fine_label: remaining_bytes
│
├── timestamp
│   ├── fine_label: unix_seconds_be
│   ├── fine_label: unix_seconds_le
│   ├── fine_label: unix_milliseconds_be
│   ├── fine_label: unix_milliseconds_le
│   ├── fine_label: unix_microseconds_be
│   ├── fine_label: unix_microseconds_le
│   ├── fine_label: ntp_seconds_be
│   └── fine_label: ntp_seconds_le
│
├── sequence_or_counter
│   ├── fine_label: sequence_8bit_be
│   ├── fine_label: sequence_16bit_be
│   ├── fine_label: sequence_32bit_be
│   ├── fine_label: sequence_8bit_le
│   ├── fine_label: sequence_16bit_le
│   └── fine_label: sequence_32bit_le
│
├── string
│   ├── fine_label: ascii_string
│   └── fine_label: utf8_string
│
├── identifier
│   └── fine_label: identifier_candidate  (soft, score_cap=0.7)
│
├── type_control
│   └── fine_label: type_or_opcode_candidate  (soft)
│
├── payload
│   └── fine_label: opaque_payload_candidate  (soft)
│
└── unknown
    └── fine_label: unknown  (prediction_status=abstained)
```

---

## 八、版本控制

语义分类体系版本: 2.0.0（ 更新，对应  修复后的实际实现）

变更时需要：
1. 更新版本号
2. 更新本文档
3. 更新 [taxonomy.py](../src/semantic_detector/taxonomy.py) `CANONICAL_COARSE_LABELS`
4. 运行所有测试确保兼容性：`python -m pytest -q`
