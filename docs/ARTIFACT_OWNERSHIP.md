# 命令产物所有权清单（ARTIFACT_OWNERSHIP）

## 目的

R388：明确 `validate` / `profile` / `infer` / `run` / `evaluate` 五个 CLI 子命令各自负责的输出文件清单。

本清单是命令产物清理、原子写入和审计追溯的权威依据：

- **命令开始前**：`artifact_manager.clean_command_artifacts(output_dir, command)` 只删除本命令拥有的旧产物，避免旧成功产物残留（HIGH-4 修复）
- **命令结束时**：每个产物用原子写入（`atomic_write_jsonl/json/csv/text`），失败时写空文件或失败 Manifest
- **命令之间**：一个命令不清理其他命令的产物（避免误删）
- **用户输入**：输入文件（`input.jsonl` / `ground_truth.json` 等）不在任何命令的所有权清单中，永不被清理

## 所有权清单

实现位置：`src/semantic_detector/io/artifact_manager.py` 的 `COMMAND_ARTIFACTS` 字典。

### validate

| 文件 | 说明 | CLI 当前是否产生 |
|------|------|----------------|
| `validated.jsonl` | 通过 JSON 级 + 组级校验的有效记录 | 是 |
| `rejected.jsonl` | JSON 级拒绝记录（parse/contract/duplicate 阶段） | 是 |
| `rejected_groups.jsonl` | 组级拒绝记录（字段数不一致的组） | 是 |
| `validate.log` | validate 命令日志 | 否（声明所有权，预留扩展） |

### profile

| 文件 | 说明 | CLI 当前是否产生 |
|------|------|----------------|
| `field_profiles.jsonl` | 字段画像 | 是 |
| `rejected.jsonl` | JSON 级拒绝记录（R385 修复后产生） | 是 |
| `rejected_groups.jsonl` | 组级拒绝记录 | 是 |
| `profile.log` | profile 命令日志 | 否（声明所有权，预留扩展） |
| `profile_manifest.json` | profile 命令 Manifest | 否（声明所有权，预留扩展） |

### infer

| 文件 | 说明 | CLI 当前是否产生 |
|------|------|----------------|
| `predictions.jsonl` | 推断结果 | 是 |
| `infer.log` | infer 命令日志 | 否（声明所有权，预留扩展） |
| `infer_manifest.json` | infer 命令 Manifest | 否（声明所有权，预留扩展） |

### run

| 文件 | 说明 | CLI 当前是否产生 |
|------|------|----------------|
| `validated.jsonl` | 通过校验的有效记录 | 是 |
| `rejected.jsonl` | JSON 级拒绝记录 | 是 |
| `rejected_groups.jsonl` | 组级拒绝记录 | 是 |
| `field_profiles.jsonl` | 字段画像 | 是 |
| `predictions.jsonl` | 推断结果 | 是 |
| `manifest.json` | run 命令 Manifest（含 RunCounts + RunManifestInfo） | 是 |
| `run.log` | run 命令日志 | 是 |

### evaluate

| 文件 | 说明 | CLI 当前是否产生 |
|------|------|----------------|
| `metrics.json` | 评估指标（overall_accuracy/coverage/macro_f1 等） | 是 |
| `per_label_metrics.csv` | 每标签指标（precision/recall/f1/tp/fp/fn） | 是 |
| `confusion_matrix.csv` | 混淆矩阵 | 是 |
| `errors.jsonl` | 评估错误记录 | 是 |
| `rejected_ground_truth.jsonl` | 被拒绝的 Ground Truth 记录 | 是 |
| `evaluation_manifest.json` | evaluate 命令 Manifest | 否（声明所有权，预留扩展） |

## 所有权原则

1. **命令只清理自己拥有的文件**：`clean_command_artifacts(output_dir, "run")` 只删除 run 拥有的 7 个文件，不删除 evaluate 的 `metrics.json` 等
2. **不删除子目录**：清理时只删除文件，不递归删除子目录（保留其他 `run_id` 目录）
3. **不删除用户输入**：`input.jsonl` / `ground_truth.json` 等不在任何所有权清单中
4. **声明所有权 vs 实际产生**：即使 CLI 当前不产生某文件（如 `validate.log`），所有权声明仍有效，以便未来扩展或清理用户手动放置的文件
5. **共享文件的所有权**：`predictions.jsonl` 同时被 `infer` 和 `run` 拥有，任一命令运行时都会清理它（设计意图：重新生成）

## 失败运行的产物策略（R389-R390）

### run 命令失败时

- **开始前**：`clean_command_artifacts(output_dir, "run")` 清理旧产物
- **失败时**（如 profile 阶段异常）：
  - 写入失败 Manifest（`status=failed`，含 `error_stage` / `error_message`）
  - 写空 `predictions.jsonl` 和 `field_profiles.jsonl`（防止旧成功产物残留）
  - 不保留旧成功 Manifest

### no_valid_records 分支

- 已正确实现（cli.py 第 572-619 行）：
  - 写空 `predictions.jsonl` 和 `field_profiles.jsonl`
  - 写失败 Manifest（`status=no_valid_records`，`exit_code=1`）

## 相关文件

- `src/semantic_detector/io/artifact_manager.py`：产物所有权清单和原子写入实现
- `tests/unit/test_artifact_manager.py`：R388 所有权清单测试
- `tests/unit/test_atomic_write.py`：R351 原子写入测试
- `tests/integration/test_run_artifact_freshness.py`：R387 失败重复 Run 产物残留测试

## 变更历史

- R351：建立 COMMAND_ARTIFACTS 初版（validate/profile/infer/run/evaluate 基础清单）
- R388：完善清单，补充 validate.log / profile.log / profile_manifest.json / infer.log / infer_manifest.json / evaluation_manifest.json 所有权声明
