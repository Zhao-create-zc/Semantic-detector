# Benchmarks

本目录预留给可复现的真实协议 benchmark。每个 benchmark 建议使用独立子目录，并包含：

```text
benchmarks/<benchmark-id>/
├── manifest.json
├── config.json
├── messages.jsonl          # 仅在数据允许再分发时提交
├── ground_truth.jsonl
├── README.md               # 获取/预处理/复现步骤
└── expected/               # 经过审核、与固定 commit 绑定的结果摘要（可选）
```

数据源政策见 `docs/DATASET_POLICY.md`，实验方法见 `docs/BENCHMARKING.md`。
