# Demo 布局与固定标签清单

**设计说明**: （ 实施数据微调，本文档已同步实际产物）
**设计原则**: 每个 FieldKey 至少 8 样本，truth 先固定，覆盖全部 9 个标准粗粒度标签

---

## 一、Layout 清单

共 5 个 layout，每个 layout 8 条消息，合计 40 条消息。

| Layout | Direction | 消息数 | 字段数 | 覆盖标签 |
|--------|-----------|--------|--------|----------|
| login_request | request | 8 | 6 | type_control, length, sequence_or_counter, string×2, unknown |
| data_request | request | 8 | 4 | type_control, length, sequence_or_counter, payload |
| data_response | response | 8 | 4 | constant, length, timestamp, payload |
| heartbeat | request | 8 | 3 | type_control, constant, sequence_or_counter |
| auth_token | request | 8 | 4 | type_control, length, identifier, payload |

---

## 二、字段布局详述

### 2.1 login_request (request, 6 字段)

| field_index | start | end | width | 标签 | 说明 |
|-------------|-------|-----|-------|------|------|
| 0 | 0 | 1 | 1 | type_control | 固定 0x01（跨 layout 同位置） |
| 1 | 1 | 5 | 4 | length | BE message_length |
| 2 | 5 | 9 | 4 | sequence_or_counter | BE 严格递增序列号 |
| 3 | 9 | 变长 | 变长 | string | ASCII 用户名（printable >= 0.85） |
| 4 | 变长 | 变长 | 变长 | string | ASCII 密码（printable >= 0.85） |
| 5 | 变长 | 变长 | 变长 | unknown | 随机字节（无规律， 新增用于覆盖 unknown 标签） |

### 2.2 data_request (request, 4 字段)

| field_index | start | end | width | 标签 | 说明 |
|-------------|-------|-----|-------|------|------|
| 0 | 0 | 1 | 1 | type_control | 固定 0x02 |
| 1 | 1 | 5 | 4 | length | BE message_length |
| 2 | 5 | 9 | 4 | sequence_or_counter | BE 严格递增 |
| 3 | 9 | 变长 | 变长 | payload | 二进制数据 |

### 2.3 data_response (response, 4 字段)

| field_index | start | end | width | 标签 | 说明 |
|-------------|-------|-----|-------|------|------|
| 0 | 0 | 1 | 1 | constant | 固定 0x03（ 调整为 constant 以覆盖第二个 constant 标签） |
| 1 | 1 | 5 | 4 | length | BE message_length |
| 2 | 5 | 9 | 4 | timestamp | BE Unix 秒（capture_time 自然递增） |
| 3 | 9 | 变长 | 变长 | payload | 二进制数据 |

### 2.4 heartbeat (request, 3 字段)

| field_index | start | end | width | 标签 | 说明 |
|-------------|-------|-----|-------|------|------|
| 0 | 0 | 1 | 1 | type_control | 固定 0x04 |
| 1 | 1 | 5 | 4 | constant | 固定 0x00000000 |
| 2 | 5 | 9 | 4 | sequence_or_counter | BE 严格递增 |

### 2.5 auth_token (request, 4 字段)

| field_index | start | end | width | 标签 | 说明 |
|-------------|-------|-----|-------|------|------|
| 0 | 0 | 1 | 1 | type_control | 固定 0x05 |
| 1 | 1 | 5 | 4 | length | BE message_length |
| 2 | 5 | 9 | 4 | identifier | token ID（非严格递增，有重复，soft 候选） |
| 3 | 9 | 13 | 4 | payload | 二进制数据（ 调整为 payload 以覆盖第三个 payload 标签） |

---

## 三、type_control 跨 layout 分组验证

教程 10.3 type/opcode 跨 layout 分组条件：

| 条件 | 满足情况 |
|------|----------|
| 至少两个不同 layout | ✓ 4 个 layout（login_request/data_request/heartbeat/auth_token） |
| 至少两个不同主值 | ✓ 0x01/0x02/0x04/0x05 共 4 个（data_response field 0 已调整为 constant） |
| 宽度不超过 2 | ✓ 宽度 1 字节 |
| 同一 layout 只贡献一个真实主值 | ✓ 每个 layout field 0 固定一个值 |

type_control alignment_key = (request, field_index=0, width=1)

---

## 四、固定标签清单（Ground Truth）

共 21 个 FieldKey，每个至少 8 样本：

| # | FieldKey (layout_id, direction, field_index) | 标签 | 检测器 | 证据类型 |
|---|----------------------------------------------|------|--------|----------|
| 1 | (login_request, request, 0) | type_control | TypeOpcodeDetector | hard |
| 2 | (login_request, request, 1) | length | LengthDetector | hard |
| 3 | (login_request, request, 2) | sequence_or_counter | SequenceDetector | hard |
| 4 | (login_request, request, 3) | string | StringDetector | hard |
| 5 | (login_request, request, 4) | string | StringDetector | hard |
| 6 | (login_request, request, 5) | unknown | (none) | abstained |
| 7 | (data_request, request, 0) | type_control | TypeOpcodeDetector | hard |
| 8 | (data_request, request, 1) | length | LengthDetector | hard |
| 9 | (data_request, request, 2) | sequence_or_counter | SequenceDetector | hard |
| 10 | (data_request, request, 3) | payload | (fallback) | soft |
| 11 | (data_response, response, 0) | constant | ConstantDetector | hard |
| 12 | (data_response, response, 1) | length | LengthDetector | hard |
| 13 | (data_response, response, 2) | timestamp | TimestampDetector | hard |
| 14 | (data_response, response, 3) | payload | (fallback) | soft |
| 15 | (heartbeat, request, 0) | type_control | TypeOpcodeDetector | hard |
| 16 | (heartbeat, request, 1) | constant | ConstantDetector | hard |
| 17 | (heartbeat, request, 2) | sequence_or_counter | SequenceDetector | hard |
| 18 | (auth_token, request, 0) | type_control | TypeOpcodeDetector | hard |
| 19 | (auth_token, request, 1) | length | LengthDetector | hard |
| 20 | (auth_token, request, 2) | identifier | IdentifierDetector | soft |
| 21 | (auth_token, request, 3) | payload | (fallback) | soft |

---

## 五、标签覆盖核对

9 个标准粗粒度标签覆盖情况：

| 标签 | FieldKey | 数量 |
|------|----------|------|
| constant | (data_response, response, 0), (heartbeat, request, 1) | 2 |
| length | 4 个 layout 的 field 1 | 4 |
| timestamp | (data_response, response, 2) | 1 |
| sequence_or_counter | 3 个 layout 的 field 2 | 3 |
| string | (login_request, request, 3/4) | 2 |
| identifier | (auth_token, request, 2) | 1 |
| type_control | 4 个 layout 的 field 0 | 4 |
| payload | (data_request, 3), (data_response, 3), (auth_token, 3) | 3 |
| unknown | (login_request, request, 5) | 1 |
| **合计** | | **21** |

全部 9 个标准粗粒度标签覆盖。

---

## 六、冲突场景覆盖

| 冲突类型 | 场景 | 期望结果 |
|----------|------|----------|
| length-vs-sequence | (login_request, request, 1) length 和 (login_request, request, 2) sequence 不在同一 FieldKey | 无冲突（不同字段） |
| timestamp-vs-sequence | (data_response, response, 2) timestamp 值严格递增，可能触发 sequence | timestamp 胜出（） |
| constant-vs-string | heartbeat constant 与 login_request string 不在同一 FieldKey | 无冲突（不同字段） |

注：冲突规则在同一 FieldKey 的多个候选之间触发。本 Demo 设计中，timestamp 字段的值严格递增会同时触发 TimestampDetector 和 SequenceDetector，验证  timestamp-vs-sequence 冲突规则。

---

## 七、数据生成约束

1. **message_length 准确**: 每条消息的 message_length == len(payload_bytes)
2. **capture_time**: data_response 的 capture_time 从 2020-01-01 每小时递增（仅 data_response 有 capture_time）
3. **sequence 严格递增**: 每个 layout 的 sequence 字段在该 layout 内严格递增
4. **string printable**: 用户名/密码使用纯 ASCII 可打印字符
5. **identifier 非严格递增**: token ID 有重复值（如 1,2,1,3,2,4,3,5）
6. **unknown 随机**: auth_token field 3 使用随机字节，无任何规律
7. **type_control 固定**: 每个 layout 的 field 0 在该 layout 内固定值

