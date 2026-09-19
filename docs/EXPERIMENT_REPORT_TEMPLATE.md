# Experiment Report Template

## 1. Experiment identity

- Benchmark ID:
- Protocol / message type:
- Semantic Detector commit:
- Date:

## 2. Dataset

- Source:
- License / terms:
- Retrieved at:
- SHA-256:
- Redistributable: yes / no
- Message count:

## 3. Ground truth

- Field count:
- Construction method:
- Reviewer / cross-check method:
- Known ambiguous labels:

## 4. Configuration

- Config file:
- Config SHA-256:
- Deviations from defaults:

## 5. Reproduction

```bash
# exact commands here
```

## 6. Results

| Metric | Value |
|---|---:|
| overall_accuracy | |
| coverage | |
| unknown_rate | |
| covered_accuracy | |
| fine_top1_accuracy | |
| macro_f1 | |

## 7. Error analysis

- wrong_label:
- abstained:
- missing_prediction:
- unexpected_prediction:
- dominant failure patterns:

## 8. Limitations

说明数据规模、协议覆盖、真值不确定性、可能的数据偏差，以及结果不能外推到哪些场景。
