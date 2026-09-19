"""命令产物所有权清单和原子写入管理

R351：建立命令产物所有权清单，统一管理 validate/profile/infer/run/evaluate
各自负责的输出文件。

功能：
- 命令开始时清理本命令旧产物（clean_command_artifacts）
- 命令结束时原子写入（atomic_write_jsonl/json/csv/text）
- 空结果写空 JSONL/CSV，而不是保留旧文件
- 不删除其他 run_id 目录（不删除子目录）
- 不删除用户输入（只删除本命令拥有的文件名）

设计原则：
- 清理时只删除 COMMAND_ARTIFACTS 中本命令拥有的文件名
- 不递归删除子目录，不删除未知文件
- 原子写入使用 tempfile + os.replace，确保文件完整写入后才替换旧文件
- 空结果写空文件（而非不写文件），防止旧产物残留
"""

import json
import os
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Callable, Optional


# R388：命令产物所有权清单
# 每个命令拥有的输出文件名元组（仅文件名，不含路径）
# 清理时只删除这些文件名，不删除其他文件
#
# 所有权原则：
# - 每个命令只清理自己拥有的文件（避免误删其他命令产物）
# - 清理时只删除文件，不删除子目录（不删除其他 run_id 目录）
# - 不删除用户输入文件（输入文件不在任何命令的所有权清单中）
# - 即使某些文件当前 CLI 不产生（如 validate.log），也声明所有权，
#   以便未来扩展或用户手动放置的文件能被正确清理
COMMAND_ARTIFACTS: Dict[str, tuple] = {
    "validate": (
        "validated.jsonl",
        "rejected.jsonl",
        "rejected_groups.jsonl",
        "validate.log",
    ),
    "profile": (
        "field_profiles.jsonl",
        "rejected.jsonl",
        "rejected_groups.jsonl",
        "profile.log",
        "profile_manifest.json",
    ),
    "infer": (
        "predictions.jsonl",
        "infer.log",
        "infer_manifest.json",
    ),
    "run": (
        "validated.jsonl",
        "rejected.jsonl",
        "rejected_groups.jsonl",
        "field_profiles.jsonl",
        "predictions.jsonl",
        "manifest.json",
        "run.log",
    ),
    "evaluate": (
        "rejected_ground_truth.jsonl",
        "metrics.json",
        "per_label_metrics.csv",
        "confusion_matrix.csv",
        "errors.jsonl",
        "evaluation_manifest.json",
    ),
}


def get_command_artifacts(command: str) -> tuple:
    """获取命令拥有的输出文件名元组

    Args:
        command: 命令名（validate/profile/infer/run/evaluate）

    Returns:
        文件名元组；未知命令返回空元组
    """
    return COMMAND_ARTIFACTS.get(command, ())


def clean_command_artifacts(output_dir: str | Path, command: str) -> List[str]:
    """清理本命令旧产物

    R351：命令开始时清理本命令拥有的旧产物文件，防止旧产物残留。

    约束：
    - 只删除本命令拥有的文件名（见 COMMAND_ARTIFACTS）
    - 不删除子目录（不删除其他 run_id 目录）
    - 不删除用户输入文件
    - 不删除非本命令拥有的文件
    - 删除失败不阻塞命令执行（返回已成功删除的列表）

    Args:
        output_dir: 输出目录路径
        command: 命令名

    Returns:
        已删除的文件名列表（仅文件名，不含路径）
    """
    output_dir = Path(output_dir)
    artifacts = get_command_artifacts(command)
    removed: List[str] = []

    for filename in artifacts:
        filepath = output_dir / filename
        # 只删除文件，不删除目录（防御性：避免删除子目录）
        if filepath.is_file():
            try:
                filepath.unlink()
                removed.append(filename)
            except OSError:
                # 删除失败不阻塞命令执行
                pass

    return removed


def atomic_write_jsonl(
    output_path: str | Path,
    records: List[Any],
    serializer: Optional[Callable[[Any], dict]] = None,
) -> None:
    """原子写入 JSONL 文件

    R351：原子写入 JSONL，空列表写空文件（不保留旧文件）。

    流程：
    1. 写入临时文件
    2. os.replace 原子替换目标文件

    Args:
        output_path: 输出文件路径
        records: 记录列表（空列表写空文件）
        serializer: 可选的序列化函数，将记录转为 dict；默认直接用记录
    """
    output_path = Path(output_path)
    dir_path = output_path.parent
    dir_path.mkdir(parents=True, exist_ok=True)

    # 写入临时文件
    with tempfile.NamedTemporaryFile(
        mode='w',
        dir=str(dir_path),
        delete=False,
        encoding='utf-8',
        suffix='.tmp',
    ) as tmp_file:
        for record in records:
            if serializer is not None:
                obj = serializer(record)
            else:
                obj = record
            tmp_file.write(json.dumps(obj, ensure_ascii=False) + '\n')
        tmp_path = tmp_file.name

    # 原子替换
    os.replace(tmp_path, str(output_path))


def atomic_write_json(
    output_path: str | Path,
    data: Any,
    indent: int = 2,
) -> None:
    """原子写入 JSON 文件

    R351：原子写入 JSON，确保文件完整写入后才替换旧文件。

    Args:
        output_path: 输出文件路径
        data: 要序列化的数据
        indent: JSON 缩进
    """
    output_path = Path(output_path)
    dir_path = output_path.parent
    dir_path.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        mode='w',
        dir=str(dir_path),
        delete=False,
        encoding='utf-8',
        suffix='.tmp',
    ) as tmp_file:
        json.dump(data, tmp_file, ensure_ascii=False, indent=indent)
        tmp_path = tmp_file.name

    os.replace(tmp_path, str(output_path))


def atomic_write_csv(
    output_path: str | Path,
    rows: List[List[Any]],
) -> None:
    """原子写入 CSV 文件

    R351：原子写入 CSV，空列表写空文件（不保留旧文件）。

    Args:
        output_path: 输出文件路径
        rows: 行列表（每行是字段列表；空列表写空文件）
    """
    import csv

    output_path = Path(output_path)
    dir_path = output_path.parent
    dir_path.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        mode='w',
        dir=str(dir_path),
        delete=False,
        encoding='utf-8',
        newline='',
        suffix='.tmp',
    ) as tmp_file:
        writer = csv.writer(tmp_file)
        for row in rows:
            writer.writerow(row)
        tmp_path = tmp_file.name

    os.replace(tmp_path, str(output_path))


def atomic_write_text(
    output_path: str | Path,
    content: str,
) -> None:
    """原子写入文本文件

    R351：原子写入纯文本文件（如 run.log）。

    Args:
        output_path: 输出文件路径
        content: 文本内容（空字符串写空文件）
    """
    output_path = Path(output_path)
    dir_path = output_path.parent
    dir_path.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        mode='w',
        dir=str(dir_path),
        delete=False,
        encoding='utf-8',
        suffix='.tmp',
    ) as tmp_file:
        tmp_file.write(content)
        tmp_path = tmp_file.name

    os.replace(tmp_path, str(output_path))
