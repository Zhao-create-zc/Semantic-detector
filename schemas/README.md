# JSON Schemas

本目录提供 Semantic Detector 公开数据契约的机器可读 JSON Schema（Draft 2020-12）。

- `message.schema.json`：输入 `messages.jsonl` 单行记录
- `ground_truth.schema.json`：评估真值 `ground_truth.jsonl` 单行记录
- `semantic_prediction.schema.json`：`predictions.jsonl` 单行预测记录
- `benchmark_manifest.schema.json`：公开 benchmark 的来源、配置与报告元数据

JSON Schema 用于**结构级预检**，不能替代程序内部的跨字段约束。例如字段不得重叠、`end` 不得超过 payload 字节长度、同组字段数一致性等仍由 Semantic Detector 自身校验器负责。
