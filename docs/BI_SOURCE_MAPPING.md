# BinaryInferno 源码映射文档

本文档记录所有从 BinaryInferno 项目复制和适配的源码文件，包括来源路径、改动说明和许可证信息。

> R314 更新：补充 length/timestamp 修复（HIGH-7 / HIGH-4）所用适配函数的来源与修改记录，与 [bi_adapted/](../src/semantic_detector/bi_adapted) 实际代码逐项对照。

---

## 一、许可证信息

BinaryInferno 源码采用 **GNU General Public License v3.0 (GPLv3)** 许可证。

- **原作者**: Jared Chandler (jared.chandler@tufts.edu)
- **原仓库**: https://github.com/ChandlerChip/BinaryInferno
- **版权年份**: 2023

所有复制到本项目的代码**保留原许可证**，并在每个文件头部注明来源路径、原作者和修改说明。本项目整体采用 GPL-3.0-or-later 许可证（见 [pyproject.toml](../pyproject.toml)），与 BinaryInferno 许可证兼容。

---

## 二、源码映射表

### 1. entropy.py

| 项 | 值 |
|----|-----|
| 源路径 | `binaryinferno-main/src/binaryinferno/entropybound.py` |
| 目标路径 | [src/semantic_detector/bi_adapted/entropy.py](../src/semantic_detector/bi_adapted/entropy.py) |
| 原函数 | `H()` Shannon 熵计算 |
| 修改说明 | 剥离 BI 特有依赖（sumeng/Sigma/deconflict/Weights/print），保留纯熵函数 |
| 行数 | ~43 行 |
| 许可证 | GPLv3，保留原版权声明 |

**导出函数**：
- `H(xs)`：计算字节序列的 Shannon 熵（bits，>= 0）

**用途**：被 [payload.py](../src/semantic_detector/detectors/payload.py) `PayloadDetector` 用于计算 `normalized_entropy`，作为 payload 字段的命中条件（`normalized_entropy >= 0.70`）。

---

### 2. length_relations.py

| 项 | 值 |
|----|-----|
| 源路径 | `binaryinferno-main/src/binaryinferno/lv.py` / `lv2.py` / `lv3.py` / `lv4.py` |
| 目标路径 | [src/semantic_detector/bi_adapted/length_relations.py](../src/semantic_detector/bi_adapted/length_relations.py) |
| 原函数 | Length-Value pair detection |
| 修改说明 | 统一 1~4 字节长度提取、固定端序支持、字段边界感知（不扫描其他偏移） |
| 行数 | ~285 行 |
| 许可证 | GPLv3，保留原版权声明 |

**导出函数**：
- `LengthCandidate` dataclass：长度候选值（value/byte_width/endian/source）
- `extract_length_candidates_be(field_bytes, max_width=4)`：大端长度候选
- `extract_length_candidates_le(field_bytes, max_width=4)`：小端长度候选
- `extract_length_candidates(field_bytes, max_width=4, endian='both')`：双端长度候选
- `calculate_message_length_support(field_values, message_lengths)`：value == message_length 支持率
- `calculate_remaining_bytes_support(field_values, remaining_bytes)`：value == remaining_bytes 支持率
- `calculate_offset_message_length_support(field_values, message_lengths)`：value + offset == message_length 支持率（统一偏移）
- `calculate_offset_remaining_bytes_support(field_values, remaining_bytes)`：value + offset == remaining_bytes 支持率（统一偏移）

**用途（HIGH-7 length 修复，R266/R267/R276）**：
- R266：[profile_builder.py](../src/semantic_detector/profiling/profile_builder.py) 接入 `calculate_message_length_support` / `calculate_remaining_bytes_support` / `calculate_offset_*_support`，计算 BE 精确长度关系支持率（`numeric_be_message_length_exact_support` 等 6 个字段）
- R267：对称增加 LE 精确长度关系支持率（`numeric_le_*` 6 个字段）
- R276：[length.py](../src/semantic_detector/detectors/length.py) `LengthDetector` 重写，**使用 `exact_support` / `offset_support` 替代 Pearson correlation**（HIGH-7 修复核心），新增 `distinct_value_count >= 2` 前置条件（教程 8.4，防止常量字段被误判）

**关键设计**：
- 只接受**统一偏移**（所有样本使用相同 offset），不支持每样本独立偏移
- `Counter` 统计最常见偏移的支持率，保证可复现
- 不扫描其他偏移，只使用 FieldProfile 提供的字段值

---

### 3. sequence_heuristic.py

| 项 | 值 |
|----|-----|
| 源路径 | `binaryinferno-main/src/binaryinferno/sequence.py` |
| 目标路径 | [src/semantic_detector/bi_adapted/sequence_heuristic.py](../src/semantic_detector/bi_adapted/sequence_heuristic.py) |
| 原函数 | `sequenceHeur` |
| 修改说明 | 重命名为 `calculate_strictly_increasing_ratio`；新增空/单元素列表安全检查；移除 print；添加类型注解；安全除零 |
| 行数 | ~122 行 |
| 许可证 | GPLv3，保留原版权声明 |

**导出函数**：
- `calculate_strictly_increasing_ratio(values)`：严格递增相邻对比率（None if 不足）
- `calculate_nondecreasing_ratio(values)`：非递减相邻对比率
- `calculate_step_one_ratio(values)`：步长为 1 的相邻对比率
- `detect_sequence_pattern(values, threshold=0.7)`：检测序列模式（step_one/strictly_increasing/nondecreasing/None）

**用途**：被 [sequence.py](../src/semantic_detector/detectors/sequence.py) `SequenceDetector` 用于计算 `strictly_increasing_ratio`，作为 sequence_or_counter 字段的命中条件（`unique_ratio >= 0.70` 且 `strictly_increasing_ratio >= 0.80`）。

**安全修正**：
- 空列表或单元素列表返回 `None`（不抛 ZeroDivisionError）
- 只有一对比较时返回 `None`（统计意义不足）

---

### 4. timestamp_range.py

| 项 | 值 |
|----|-----|
| 源路径 | `binaryinferno-main/src/binaryinferno/tsbyrange.py` |
| 目标路径 | [src/semantic_detector/bi_adapted/timestamp_range.py](../src/semantic_detector/bi_adapted/timestamp_range.py) |
| 原函数 | `predictts()` |
| 修改说明 | (1) 移除打印；(2) 改为纯函数返回支持率；(3) 字段边界感知；(4) 不扫描；(5) 只返回支持率 |
| 行数 | ~309 行 |
| 许可证 | GPLv3，保留原版权声明 |

**导出函数**：
- `TIMESTAMP_UNAVAILABLE` 常量
- `is_timestamp_available(capture_times)`：检查是否有可用时间戳
- `get_time_range(capture_times, default_range=None)`：获取时间范围（全 None 时返回 (None, None)，**不兜底系统时间**）
- `calculate_timestamp_support(field_values, low/high_timestamp, epoch_offset, scale, slop_seconds)`：通用时间戳支持率
- `decode_timestamp_bytes_be(field_bytes, byte_width=4)`：大端解码
- `decode_timestamp_bytes_le(field_bytes, byte_width=4)`：小端解码
- `calculate_unix_seconds_support(field_values, low/high_timestamp, slop_seconds)`：Unix 秒支持率
- `calculate_unix_milliseconds_support(...)`：Unix 毫秒支持率
- `calculate_unix_microseconds_support(...)`：Unix 微秒支持率
- `calculate_ntp_seconds_support(...)`：NTP 秒支持率（NTP 纪元偏移 2208988800）

**用途（HIGH-4 timestamp 修复，R271-R273/R280）**：
- R271：[profile_builder.py](../src/semantic_detector/profiling/profile_builder.py) 接入 `calculate_unix_seconds_support`，计算 4 字节 Unix 秒 BE/LE support（`timestamp_be_unix_seconds_support` / `timestamp_le_unix_seconds_support`）
- R272：新增 `calculate_unix_milliseconds_support` 和 `calculate_unix_microseconds_support`，计算 8 字节毫秒/微秒 BE/LE support
- R273：新增 `calculate_ntp_seconds_support`，计算 4 字节 NTP 秒 BE/LE support（NTP 纪元 1900）
- R280：[timestamp.py](../src/semantic_detector/detectors/timestamp.py) `TimestampDetector` 重写，**移除 bi_adapted.timestamp_range imports 和所有 `_calculate_*_support` 辅助方法**，直接读取 profile 的 support 字段（HIGH-4 修复核心），新增 `capture_time_min/max` 检查（教程 9.4 不兜底系统时间）

**关键设计**：
- 时间范围全 None 时返回 0.0（教程 9.4，**不兜底系统时间**）
- 支持 Unix 秒（4 字节）/ Unix 毫秒（8 字节）/ Unix 微秒（8 字节）/ NTP 秒（4 字节）
- BE/LE 独立计算，端序不折叠
- slop_seconds 容差默认 86400（1 天）

---

### 5. __init__.py

| 项 | 值 |
|----|-----|
| 源路径 | 无（本项目创建） |
| 目标路径 | [src/semantic_detector/bi_adapted/__init__.py](../src/semantic_detector/bi_adapted/__init__.py) |
| 修改说明 | 空文件，仅作为包标识 |
| 行数 | 0 行 |
| 许可证 | 本项目 GPL-3.0-or-later |

---

## 三、改动统计

| 文件 | 源行数 | 目标行数 | 改动类型 | HIGH 修复关联 |
|------|--------|----------|----------|---------------|
| entropy.py | ~30 | ~43 | 剥离 BI 依赖，纯函数 | - |
| length_relations.py | ~200 | ~285 | 统一 1~4 字节、字段边界感知、统一偏移 | HIGH-7 (R266/R267/R276) |
| sequence_heuristic.py | ~80 | ~122 | 安全检查、类型注解、移除 print | - |
| timestamp_range.py | ~150 | ~309 | 纯函数、字段边界感知、4 种时间戳格式 | HIGH-4 (R271-R273/R280) |
| __init__.py | 0 | 0 | 新建空文件 | - |

**总计**: 4 个文件从 BinaryInferno 复制并适配，1 个文件新创建。

---

## 四、改动原则

所有改动遵循以下原则：

1. **保留核心算法逻辑**：不改变检测算法的核心数学逻辑（熵计算、长度支持率、序列比率、时间戳范围检查）
2. **剥离 BI 特有依赖**：移除 sumeng/Sigma/deconflict/Weights/print 等 BI 内部依赖
3. **字段边界感知**：只使用 FieldProfile 提供的字段值，不扫描其他偏移
4. **纯函数**：所有函数返回值，不产生副作用，不打印
5. **类型注解**：添加完整类型注解
6. **安全检查**：空列表/单元素列表/全 None 时间戳等边界情况安全处理
7. **保留许可证**：所有文件头部保留原版权声明和 GPLv3 许可证
8. **注明来源**：所有文件头部注明原始来源路径、原作者和修改说明

---

## 五、HIGH 修复关联说明

### HIGH-7 length 用 Pearson correlation 冒充精确等式

**修复轮次**：R276-R279

**使用的适配函数**：[length_relations.py](../src/semantic_detector/bi_adapted/length_relations.py)
- `calculate_message_length_support`：精确等式支持率（offset=0）
- `calculate_remaining_bytes_support`：精确等式支持率（offset=0）
- `calculate_offset_message_length_support`：统一偏移支持率（offset≠0）
- `calculate_offset_remaining_bytes_support`：统一偏移支持率（offset≠0）

**修复内容**：
- R266/R267：profile_builder.py 接入上述函数，计算 BE/LE 精确长度关系支持率（12 个字段）
- R276：LengthDetector.detect 重写，使用 `exact_support` / `offset_support` 替代 Pearson correlation
- R277-R279：增加负例测试（高相关但非等式、常量字段、单值字段、变宽字段、单字节端序折叠）

### HIGH-4 timestamp 检测器未接入真实流水线

**修复轮次**：R280-R282

**使用的适配函数**：[timestamp_range.py](../src/semantic_detector/bi_adapted/timestamp_range.py)
- `calculate_unix_seconds_support`：4 字节 Unix 秒
- `calculate_unix_milliseconds_support`：8 字节 Unix 毫秒
- `calculate_unix_microseconds_support`：8 字节 Unix 微秒
- `calculate_ntp_seconds_support`：4 字节 NTP 秒
- `decode_timestamp_bytes_be` / `decode_timestamp_bytes_le`：BE/LE 解码

**修复内容**：
- R271-R273：profile_builder.py 接入上述函数，计算 8 个 timestamp support 字段（4 种格式 × BE/LE）
- R280：TimestampDetector.detect 重写，移除 bi_adapted.timestamp_range imports 和 `_calculate_*_support` 辅助方法，直接读取 profile 的 support 字段
- R281-R282：增加无 capture_time 负例和 profile JSONL→infer 集成测试

---

## 六、使用方式

本项目通过以下方式使用 BinaryInferno 适配代码：

```python
# 熵计算（PayloadDetector）
from semantic_detector.bi_adapted.entropy import H

# 长度关系支持率（profile_builder.py，HIGH-7 修复）
from semantic_detector.bi_adapted.length_relations import (
    calculate_message_length_support,
    calculate_remaining_bytes_support,
    calculate_offset_message_length_support,
    calculate_offset_remaining_bytes_support,
)

# 序列检测（SequenceDetector）
from semantic_detector.bi_adapted.sequence_heuristic import (
    calculate_strictly_increasing_ratio,
    calculate_nondecreasing_ratio,
)

# 时间戳支持率（profile_builder.py，HIGH-4 修复）
from semantic_detector.bi_adapted.timestamp_range import (
    calculate_unix_seconds_support,
    calculate_unix_milliseconds_support,
    calculate_unix_microseconds_support,
    calculate_ntp_seconds_support,
    decode_timestamp_bytes_be,
    decode_timestamp_bytes_le,
)
```

**注意**：[timestamp.py](../src/semantic_detector/detectors/timestamp.py) `TimestampDetector` 在 R280 重写后**不再直接导入 bi_adapted.timestamp_range**，而是读取 profile_builder.py 预计算的 support 字段。bi_adapted.timestamp_range 的调用方只有 profile_builder.py。

---

## 七、版本控制

BinaryInferno 源码版本: 基于 binaryinferno-main 最新版本

映射文档版本: 2.0.0（R314 更新，补充 HIGH-7 / HIGH-4 修复所用适配函数的来源与修改记录）

变更时需要：
1. 更新本文档
2. 确保所有文件都有正确的来源声明
3. 运行所有测试确保兼容性：`python -m pytest -q`
