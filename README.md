# 简易字段语义检测器

一个基于规则的二进制协议字段语义检测器，用于自动识别消息字段的可能语义类型。

---

## 安装

### 系统要求

- Python 3.10+（在 3.14 上验证通过）
- Windows / Linux / macOS

### 安装步骤

```bash
# 1. 安装运行时依赖
pip install -r requirements.txt

# 2. 以 editable 模式安装本包（推荐，无需设置 PYTHONPATH）
pip install -e .
```

`pip install -e .` 会读取 [pyproject.toml](pyproject.toml) 并将 `semantic_detector` 注册为本地包，之后可直接用 `python -m semantic_detector.cli ...` 或 `python -m semantic_detector ...` 调用，无需手动设置 `PYTHONPATH`。

### 验证安装

```bash
# 查看帮助
python -m semantic_detector.cli --help

# 验证包可导入
python -c "import semantic_detector; print(semantic_detector.__file__)"
```

---

## 快速开始

### 1. 验证输入文件

```bash
python -m semantic_detector.cli validate examples/messages.jsonl --output-dir examples/output
```

### 2. 运行完整流水线

```bash
python -m semantic_detector.cli run examples/messages.jsonl --output-dir examples/output
```

### 3. 评估预测结果

```bash
python -m semantic_detector.cli evaluate examples/output/predictions.jsonl examples/ground_truth.jsonl
```

### 4. 运行完整 Demo（PowerShell）

```bash
PowerShell -ExecutionPolicy Bypass -File scripts/run_demo.ps1
```

`run_demo.ps1` 串联了清理 → 验证 → 运行流水线 → 评估 → 显示结果五个步骤。

---

## 命令行接口

### validate - 验证输入文件

```bash
python -m semantic_detector.cli validate <input_file> [--output-dir <output_dir>]
```

验证 JSONL 输入文件的格式、字段边界、字段数一致性（同 `(layout_id, direction)` 组内字段数不一致整组拒绝，HIGH-2）。

**输出产物**（位于 `--output-dir`）：

| 文件 | 说明 |
|------|------|
| `validated.jsonl` | 验证通过的记录 |
| `rejected.jsonl` | 因字段越界/重叠/索引不连续被拒绝的记录 |
| `rejected_groups.jsonl` | 因组内字段数不一致被整组拒绝的 `RejectionRecord` |

### profile - 生成字段画像

```bash
python -m semantic_detector.cli profile <input_file> [--output-dir <output_dir>] [--config <config_file>]
```

为每个字段生成统计画像（宽度、字节统计、数值统计 BE/LE、时间戳 support、capture_time 元数据等）。

**输出产物**：

| 文件 | 说明 |
|------|------|
| `field_profiles.jsonl` | 字段画像（每个 FieldKey 一行） |
| `rejected_groups.jsonl` | 因组内字段数不一致被整组拒绝的 `RejectionRecord` |

### infer - 执行推断

```bash
python -m semantic_detector.cli infer <profiles_file> [--output-dir <output_dir>] [--config <config_file>]
```

基于 `field_profiles.jsonl` 推断字段语义，输出 `SemanticPrediction`（含 evidence 数组 + alternatives + prediction_status）。

**输出产物**：

| 文件 | 说明 |
|------|------|
| `predictions.jsonl` | 预测结果，每行一个 `SemanticPrediction` 序列化结果 |

### run - 运行完整流水线

```bash
python -m semantic_detector.cli run <input_file> [--output-dir <output_dir>] [--allow-partial-input] [--config <config_file>]
```

执行完整的验证 → 画像生成 → 推断流程。

**默认 fail closed**：任何拒绝（JSON/契约/组级字段数不一致）→ exit 1。
**`--allow-partial-input`**：对有效消息子集继续 run，exit 0（仍导出 rejected*.jsonl 供审计）。

**输出产物**（位于 `--output-dir`）：

| 文件 | 说明 |
|------|------|
| `validated.jsonl` | 验证通过的记录 |
| `rejected.jsonl` | 因字段越界/重叠/索引不连续被拒绝的记录 |
| `rejected_groups.jsonl` | 因组内字段数不一致被整组拒绝的 `RejectionRecord` |
| `field_profiles.jsonl` | 字段画像 |
| `predictions.jsonl` | 预测结果（`SemanticPrediction` 序列化） |
| `manifest.json` | 流水线 manifest（含 run_id、输入输出路径、配置摘要、`resolved_config`/`config_source`/`config_sha256`） |

### evaluate - 评估推断结果

```bash
python -m semantic_detector.cli evaluate <predictions_file> <ground_truth_file> [--allow-partial-ground-truth]
```

评估预测结果与真值的匹配度，生成评估指标。

**默认 fail closed**：任何真值拒绝 → exit 1。
**`--allow-partial-ground-truth`**：对合法真值子集继续评价，exit 0（仍导出 `rejected_ground_truth.jsonl` 供审计）。

**输出产物**（默认输出到 predictions_file 同目录的 `evaluation/` 子目录）：

| 文件 | 说明 |
|------|------|
| `metrics.json` | 总体指标（overall_accuracy / coverage / unknown_rate / covered_accuracy / fine_top1_accuracy / macro_f1 / matched_count / total_truths） |
| `per_label_metrics.csv` | 每标签指标（precision / recall / f1 / support / tp / fp / fn） |
| `confusion_matrix.csv` | 混淆矩阵（行为真值，列为预测） |
| `errors.jsonl` | 错误记录（`wrong_label` / `abstained` / `missing_prediction` / `unexpected_prediction` 四类） |
| `rejected_ground_truth.jsonl` | 因真值损坏被拒绝的记录（仅 `--allow-partial-ground-truth` 模式下有内容） |

---

## 输入格式

输入文件为 JSONL 格式，每行一个 JSON 对象：

```json
{
  "message_id": "msg_001",
  "layout_id": "login_request",
  "direction": "request",
  "payload_hex": "010000001a0000016c7573657270617373",
  "fields": [
    {"field_index": 0, "start": 0, "end": 1},
    {"field_index": 1, "start": 1, "end": 5}
  ],
  "capture_time": "2020-01-01T00:00:00+00:00"
}
```

字段说明：
- `message_id`：消息唯一标识（字符串）
- `layout_id`：布局标识
- `direction`：方向，`request` 或 `response`
- `payload_hex`：十六进制编码的消息载荷
- `fields`：字段边界列表，`field_index` 从 0 开始连续
- `capture_time`：可选，ISO 8601 字符串（UTC aware），用于 timestamp 检测

**输入约束**：
- 同 `(layout_id, direction)` 组内 `len(fields)` 必须一致，否则**整组拒绝**
- 字段边界不得越界、不得重叠
- `field_index` 必须从 0 开始连续

详细契约见 [docs/DATA_CONTRACT.md](docs/DATA_CONTRACT.md)。

---

## 输出格式

### predictions.jsonl

每行是一个 `SemanticPrediction` 序列化结果：

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
      "details": {...}
    }
  ],
  "alternatives": [...]
}
```

字段说明：
- `evidence` 是数组，`evidence[0]` 为 primary 证据，其余为保留的候选证据
- `alternatives` 是数组，每个元素是除 primary 外的候选证据字典（稳定排序）
- `confidence` 等于 `evidence[0].score`
- `prediction_status`：`confirmed`（hard evidence）/ `candidate`（soft evidence）/ `abstained`（unknown 拒识）

### metrics.json

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

### errors.jsonl

每行一个错误记录，`error_type` 取值：`wrong_label` / `abstained` / `missing_prediction` / `unexpected_prediction`。

详细契约见 [docs/DATA_CONTRACT.md](docs/DATA_CONTRACT.md)。

---

## 支持的语义类型

9 个标准粗粒度标签（来源：[taxonomy.py](src/semantic_detector/taxonomy.py) `CANONICAL_COARSE_LABELS`）：

| 标签 | 描述 | 典型 fine_label |
|------|------|------------------|
| `constant` | 常量值 | `constant_value` |
| `length` | 长度字段 | `total_message_length` / `remaining_bytes` |
| `timestamp` | 时间戳 | `unix_seconds_be` / `unix_milliseconds_le` 等 |
| `sequence_or_counter` | 序列号/计数器 | `sequence_32bit_be` 等 |
| `string` | ASCII/UTF-8 字符串 | `ascii_string` / `utf8_string` |
| `identifier` | 标识符 | `identifier_candidate`（soft） |
| `type_control` | 类型/操作码 | `type_or_opcode_candidate`（soft） |
| `payload` | 载荷数据 | `opaque_payload_candidate`（soft） |
| `unknown` | 未知/拒识 | `unknown` |

详细分类体系见 [docs/SEMANTIC_TAXONOMY.md](docs/SEMANTIC_TAXONOMY.md)。

---

## 项目结构

```
semantic_detector/
├── src/semantic_detector/          # 源代码
│   ├── contracts.py                # 数据契约（Direction/FieldSpan/MessageRecord/FieldKey/DetectorEvidence/SemanticPrediction）
│   ├── taxonomy.py                 # 9 个标准粗粒度标签集中管理
│   ├── config.py                   # Config dataclass（14 个文档化阈值 + to_dict + sha256）
│   ├── cli.py                      # 命令行接口
│   ├── detectors/                  # 检测器
│   │   ├── constant.py             # ConstantDetector
│   │   ├── length.py               # LengthDetector
│   │   ├── timestamp.py            # TimestampDetector
│   │   ├── sequence.py             # SequenceDetector
│   │   ├── string.py               # StringDetector
│   │   ├── identifier.py           # IdentifierDetector
│   │   ├── payload.py              # PayloadDetector
│   │   └── type_opcode.py          # TypeOpcodeDetector
│   ├── evaluation/                 # 评估模块
│   │   ├── ground_truth.py         # GroundTruthRecord
│   │   ├── metrics.py              # 指标计算
│   │   └── confusion.py            # 混淆矩阵
│   ├── io/                         # 输入输出
│   ├── pipeline/                   # 流水线（含 type/opcode 后处理）
│   ├── profiling/                  # 画像生成
│   │   ├── collector.py            # 分组与字段数校验
│   │   └── profile_builder.py      # FieldProfile 构建
│   └── scoring/                    # 评分与解析
│       └── resolver.py             # Resolver 冲突规则
├── tests/                          # 测试
├── examples/                       # 示例
├── config/                         # 默认配置
├── scripts/                        # 脚本
├── docs/                           # 文档
└── pyproject.toml                  # 项目配置
```

---

## 配置

默认配置位于 [config/defaults.json](config/defaults.json)，包含 14 个文档化阈值：

```json
{
  "min_samples": 8,
  "constant_support": 0.98,
  "length_support": 0.90,
  "timestamp_support": 0.90,
  "timestamp_slop_seconds": 86400,
  "sequence_unique_ratio": 0.70,
  "sequence_increasing_ratio": 0.80,
  "string_printable_ratio": 0.85,
  "string_nonempty_ratio": 0.80,
  "identifier_unique_ratio": 0.80,
  "identifier_score_cap": 0.70,
  "payload_entropy_threshold": 0.70,
  "ambiguity_margin": 0.08,
  "type_opcode_min_dominant_ratio": 0.50
}
```

### CLI --config 参数（R354）

`profile` / `infer` / `run` 子命令支持 `--config <config_file>` 参数：

```bash
# 使用默认配置（config/defaults.json）
python -m semantic_detector.cli run input.jsonl --output-dir out

# 使用用户配置覆盖默认值
python -m semantic_detector.cli run input.jsonl --output-dir out --config my_config.json
```

`--config PATH` 通过 `load_config_with_override` 用用户值覆盖默认值（只覆盖用户提供的字段，其余保持默认）。

### 配置端到端贯通（R354-R359）

配置从 CLI → Pipeline → 检测器/Resolver → 上下文阈值 → Manifest 审计字段端到端贯通：
- `manifest.json` 写入 `resolved_config`（Config.to_dict 完整快照）/ `config_source`（"default" 或用户路径）/ `config_sha256`（64 字符 hex 稳定哈希）
- 同一配置哈希稳定；覆盖值改变哈希；manifest 值与 Pipeline 实际值一致

示例配置见 [examples/config.json](examples/config.json)（与 defaults.json 一致，不以降低科学标准换结果）。

---

## CLI 退出语义（R361）

所有子命令默认 **fail closed**（任何拒绝 → exit 1），需显式参数才允许 partial 模式。

| 子命令 | exit 0 | exit 1 | exit 2 |
|--------|--------|--------|--------|
| `validate` | 全部通过 | 存在任一拒绝 | 输入文件问题 |
| `profile` | 成功生成画像（即使跳过组级拒绝） | 读取/生成失败 | 输入文件问题 |
| `run` | 全链路成功无拒绝 | 默认模式存在任一拒绝 | 输入文件问题 |
| `evaluate` | 真值全部合法 | 默认模式存在真值拒绝 | 输入文件问题 |

**partial 模式**（显式 opt-in）：
- `run --allow-partial-input`：对有效消息子集继续 run，exit 0（仍导出 rejected*.jsonl）
- `evaluate --allow-partial-ground-truth`：对合法真值子集继续评价，exit 0（仍导出 rejected_ground_truth.jsonl）

详细退出语义见 [docs/DATA_CONTRACT.md](docs/DATA_CONTRACT.md) 第七节。

---

## Demo 指标局限声明（R361）

**Demo 指标不是实际协议性能**。本项目的 Demo 指标（`examples/output/evaluation/metrics.json`）仅基于 `examples/messages.jsonl`（21 条真值）的小样本评估，**不代表任意协议或真实流量上的检测准确率**。

| 指标 | Demo 值 | 含义 |
|------|---------|------|
| `overall_accuracy` | 0.8095 | 21 条真值中 17 条预测正确 |
| `coverage` | 0.8571 | 21 条真值中 18 条有非 unknown 预测 |
| `unknown_rate` | 0.1429 | 3 条预测为 unknown（拒识） |
| `covered_accuracy` | 0.9444 | 18 条有预测的真值中 17 条正确 |

Demo 中 4 个错误均为检测器的合理局限（1 个 `wrong_label` + 3 个 `abstained`）。

**不得**将 Demo 指标泛化为"检测器在任意协议上准确率 80%+"，**不得**用于论文级性能声明。Demo 仅用于验证流水线端到端可运行 + 评估闭环可计算。

---

## 严格错误行为（R408）

本检测器对非法输入、重复标识、失败运行、产物覆盖和评价键冲突采用统一、严格、可审计的行为。以下 8 项行为是数据契约的强制规范，详见 [DATA_CONTRACT.md](docs/DATA_CONTRACT.md) 第十一节。

### 1. 所有字段的严格 JSON 类型

- `field_index`、`start`、`end`、`input_order` 必须是严格整数 `type(value) is int`
- `message_id`、`layout_id` 必须为非空字符串
- `metadata` 必须为 `dict`（不接受 `list`）
- JSONL 解析阶段不做 `int()` / `str()` / `dict()` 静默转换
- 非法类型进入 `rejected.jsonl`，`reason_code` 可定位到字段类型错误

### 2. bool 不接受为 int

- Python 中 `True == 1`、`False == 0`，但所有整数字段必须用 `type(value) is int` 检查
- `isinstance(True, int)` 返回 `True`，因此 **不接受** `isinstance(value, int)` 直接接受 bool
- `field_index = True`、`start = False`、`input_order = True` 必须被拒绝

### 3. 非法 direction 不转 unknown

- `direction` 只接受 `request` 或 `response`
- 非法值（如 `foo`、`bar`、`""`、`None`、`unknown`）抛出 `ValueError`
- **不得**降级为 `Direction.UNKNOWN`（已删除该枚举值）
- CLI `evaluate` 遇到非法 direction 返回退出码 1，不生成 `metrics.json`

### 4. duplicate FieldKey 评价失败

- `FieldKey = (layout_id, direction, field_index)` 三元组唯一标识一个字段组
- `align_predictions_with_truth` 先规范化（严格 direction 解析），再检查重复
- duplicate FieldKey 抛 `ValueError`，消息包含 `duplicate` 标识
- **不得**静默覆盖（先用原始字符串判断不重复，后归一化成同一键）

### 5. 评价数量守恒

- 正式评价必须满足 `matched + unmatched = total`（两侧）
- 不守恒时 `valid_for_reporting=false`，`status=internal_count_inconsistency`
- `verify_count_conservation` 作为额外防御，即使有内部 bug 也能检测到不守恒

### 6. Profile 默认不允许部分输入

- `profile` 命令默认对任何 rejection 都失败：`exit 1`，`status=invalid_input`
- **不得**静默丢弃 `_rejected_records`，**不得**返回 `exit 0` 冒充完整成功
- `--allow-partial-input` 必须显式开启：`status=partial_success`，`valid_for_reporting=false`
- 全部记录无效时，即使 partial 也必须失败

### 7. 失败 run 不保留旧结果

- `run` 命令开始时清理自身拥有的旧产物（`clean_command_artifacts`）
- 失败运行写入失败 Manifest（`build_failed_run_manifest`，14 基础字段 + 7 扩展字段）
- **不得**保留上一次成功的 `predictions.jsonl` 或 `manifest.json`
- **不得**没有 Manifest（失败也要有产物）

#### Manifest 覆盖范围（R427 起）

- 正常 Run：生成 `completed` Manifest
- 进入 Run 后任意业务阶段失败：生成 `failed` Manifest（含 `failure_stage`/`error_type`/`partial_artifacts_present`）
- 输入/配置类 preflight 失败（输入不存在、输入不是文件、配置不存在、配置 JSON 损坏、配置值非法、日志创建失败）：尽可能生成 `failed` Manifest
- 输出目录本身无法创建或写入：仅保证非零退出和 stderr（物理上无法落盘 Manifest）

> 除输出位置本身不可写外，Run 的正常运行和失败运行均生成独立 Manifest。

### 8. 每个命令的产物所有权

每个命令只负责清理和写入自己拥有的产物文件，详细清单见 [ARTIFACT_OWNERSHIP.md](docs/ARTIFACT_OWNERSHIP.md)。

| 命令 | 拥有的产物 |
|------|-----------|
| `validate` | `validated.jsonl`、`rejected.jsonl`、`validate.log` |
| `profile` | `field_profiles.jsonl`、`rejected.jsonl`、`rejected_groups.jsonl`、`profile.log`、`profile_manifest.json` |
| `infer` | `predictions.jsonl`、`infer.log`、`infer_manifest.json` |
| `run` | `validated.jsonl`、`rejected.jsonl`、`rejected_groups.jsonl`、`field_profiles.jsonl`、`predictions.jsonl`、`manifest.json`、`run.log` |
| `evaluate` | `metrics.json`、`per_label_metrics.csv`、`confusion_matrix.csv`、`errors.jsonl`、`rejected_ground_truth.jsonl`、`evaluation_manifest.json` |

---

## 测试

运行单元测试：

```bash
python -m pytest tests/unit/ -v
```

运行集成测试：

```bash
python -m pytest tests/integration/ -v
```

运行所有测试：

```bash
python -m pytest -q
```

当前全量测试：1676 passed，0 failed。

---

## 清理产物

清理运行产物（dry-run 模式）：

```bash
PowerShell -ExecutionPolicy Bypass -File scripts/clean_artifacts.ps1 -DryRun
```

执行清理：

```bash
PowerShell -ExecutionPolicy Bypass -File scripts/clean_artifacts.ps1 -Force
```

---

## 许可证

本项目采用 GPL-3.0-or-later 许可证，详见 [pyproject.toml](pyproject.toml)。

## 参考

基于 BinaryInferno 的字段语义检测思想，实现了独立的规则检测器。length/timestamp 修复所用适配函数的来源见 [docs/BI_SOURCE_MAPPING.md](docs/BI_SOURCE_MAPPING.md)。
