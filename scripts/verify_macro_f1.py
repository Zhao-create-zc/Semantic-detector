"""R322 审计补充：手算 Macro-F1 验证

可复现验证脚本：从 examples/output/predictions.jsonl 和 examples/ground_truth.jsonl
手算 Macro-F1/Precision/Recall，与 examples/output/metrics.json 比对。
"""
import json
from collections import defaultdict
from pathlib import Path

# 读取 predictions（Demo 实际产物路径）
preds = {}
with open('examples/output/predictions.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        p = json.loads(line)
        key = (p['layout_id'], p['direction'], p['field_index'])
        preds[key] = p['coarse_label']

# 读取 ground_truth
truths = {}
with open('examples/ground_truth.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        t = json.loads(line)
        key = (t['layout_id'], t['direction'], t['field_index'])
        truths[key] = t['semantic_label']

# 逐对对齐
tp = defaultdict(int)
fp = defaultdict(int)
fn = defaultdict(int)
truth_labels = set()

for key, truth_label in truths.items():
    truth_labels.add(truth_label)
    pred_label = preds.get(key, None)
    if pred_label == truth_label:
        tp[truth_label] += 1
    else:
        if pred_label is not None:
            fp[pred_label] += 1
        fn[truth_label] += 1

# 计算每个标签的 precision/recall/f1
f1_sum = 0
precision_sum = 0
recall_sum = 0
label_count = 0
print(f"{'Label':<22} {'TP':>3} {'FP':>3} {'FN':>3} {'P':>8} {'R':>8} {'F1':>8}")
for label in sorted(truth_labels):
    t_tp = tp[label]
    t_fp = fp[label]
    t_fn = fn[label]
    precision = t_tp / (t_tp + t_fp) if (t_tp + t_fp) > 0 else 0.0
    recall = t_tp / (t_tp + t_fn) if (t_tp + t_fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    print(f"{label:<22} {t_tp:>3} {t_fp:>3} {t_fn:>3} {precision:>8.4f} {recall:>8.4f} {f1:>8.4f}")
    f1_sum += f1
    precision_sum += precision
    recall_sum += recall
    label_count += 1

print(f"\nMacro F1 = {f1_sum}/{label_count} = {f1_sum/label_count:.10f}")
print(f"Macro Precision = {precision_sum}/{label_count} = {precision_sum/label_count:.10f}")
print(f"Macro Recall = {recall_sum}/{label_count} = {recall_sum/label_count:.10f}")
print(f"\nmetrics.json:")
with open('examples/output/metrics.json', 'r', encoding='utf-8') as f:
    m = json.load(f)
print(f"  macro_f1 = {m['macro_f1']}")
print(f"  macro_precision = {m['macro_precision']}")
print(f"  macro_recall = {m['macro_recall']}")
