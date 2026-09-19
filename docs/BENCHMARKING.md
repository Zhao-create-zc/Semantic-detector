# Benchmarking Protocol

本规范用于将 Semantic Detector 的结果从“Demo 能跑”升级为“实验可复现、可比较”。

## 1. 最小报告单元

每个 benchmark 必须绑定一个 `benchmark_id`，并保存：

1. 协议与消息类型；
2. 数据来源、获取日期、许可证/使用条款、文件哈希；
3. 输入消息数量和字段真值数量；
4. 真值构造方法与复核方式；
5. 完整配置文件及 SHA-256；
6. 原始 `metrics.json`、`per_label_metrics.csv`、`confusion_matrix.csv`、`errors.jsonl`；
7. 错误分析与已知局限。

元数据格式见 `schemas/benchmark_manifest.schema.json`。

## 2. 禁止做法

- 不得把 `examples/` 合成 Demo 指标描述为真实协议性能；
- 不得只挑成功样本并隐藏拒识/失败样本；
- 不得把不同数据集、不同预处理或不同配置的结果直接横向比较而不说明差异；
- 不得使用无权公开的 PCAP、客户流量或含敏感标识的数据作为仓库样本。

## 3. 必报指标

至少报告：`overall_accuracy`、`coverage`、`unknown_rate`、`covered_accuracy`、`fine_top1_accuracy`、`macro_f1`、样本/真值数量，以及四类错误计数。

## 4. 推荐实验层级

- **Level A — Smoke**：确认完整流水线可运行，不做性能主张；
- **Level B — Single-protocol**：一个协议/消息类型上的固定数据集实验；
- **Level C — Cross-protocol**：多个协议使用统一评价契约，分析泛化和拒识行为；
- **Level D — Boundary feedback**：在相同上游切分结果上比较“无语义反馈 vs 有语义反馈”。

## 5. 可复现命令

每份实验报告必须给出从输入到结果的命令，例如：

```bash
python -m semantic_detector.cli run benchmark/messages.jsonl \
  --output-dir benchmark/out \
  --config benchmark/config.json
python -m semantic_detector.cli evaluate \
  benchmark/out/predictions.jsonl benchmark/ground_truth.jsonl
```

## 6. Baseline comparison

For iterative detector work, compare a candidate run against a committed pinned baseline rather than relying on memory or demo output:

```bash
python -m scripts.benchmarks.compare_metrics \
  benchmarks/results/iti-dnp3-smoke-v1/metrics.json \
  benchmark-output/iti-dnp3-smoke-v1/run/metrics.json \
  --json-out benchmark-output/iti-dnp3-smoke-v1/baseline_comparison.json \
  --markdown-out benchmark-output/iti-dnp3-smoke-v1/BASELINE_COMPARISON.md
```

The comparison reports accuracy, coverage, unknown rate, covered accuracy, fine top-1 accuracy, macro F1, and error-count deltas. A better scalar metric does not by itself prove a better model; inspect the error cases and per-label effects before accepting a change.
