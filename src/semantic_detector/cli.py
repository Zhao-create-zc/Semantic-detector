"""命令行接口

提供语义检测器的命令行工具。
"""

import argparse
import sys
from typing import List


def create_parser() -> argparse.ArgumentParser:
    """创建命令行解析器
    
    Returns:
        ArgumentParser 实例
    """
    parser = argparse.ArgumentParser(
        prog='semantic_detector',
        description='简易字段语义检测器',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(
        title='子命令',
        dest='command',
        description='可用的子命令'
    )
    
    # validate 子命令
    validate_parser = subparsers.add_parser(
        'validate',
        help='验证输入 JSONL 文件'
    )
    validate_parser.add_argument(
        'input_file',
        help='输入 JSONL 文件路径'
    )
    validate_parser.add_argument(
        '--output-dir',
        help='输出目录'
    )
    
    # profile 子命令
    profile_parser = subparsers.add_parser(
        'profile',
        help='生成字段画像'
    )
    profile_parser.add_argument(
        'input_file',
        help='输入 JSONL 文件路径'
    )
    profile_parser.add_argument(
        '--output-dir',
        help='输出目录'
    )
    # R354：统一 --config 参数（profile 使用配置中的 min_samples 等阈值）
    profile_parser.add_argument(
        '--config',
        help='配置文件路径（默认使用 config/defaults.json）'
    )

    # infer 子命令
    infer_parser = subparsers.add_parser(
        'infer',
        help='推断字段语义'
    )
    infer_parser.add_argument(
        'input_file',
        help='输入字段画像文件路径'
    )
    infer_parser.add_argument(
        '--output-dir',
        help='输出目录'
    )
    # R354：统一 --config 参数（infer 使用配置中的检测器阈值）
    infer_parser.add_argument(
        '--config',
        help='配置文件路径（默认使用 config/defaults.json）'
    )

    # run 子命令
    run_parser = subparsers.add_parser(
        'run',
        help='运行完整流水线'
    )
    run_parser.add_argument(
        'input_file',
        help='输入 JSONL 文件路径'
    )
    run_parser.add_argument(
        '--output-dir',
        help='输出目录'
    )
    # R345：显式 partial input 模式
    # 默认 fail closed（任何 rejection → exit 1）；显式指定时继续处理有效消息子集
    run_parser.add_argument(
        '--allow-partial-input',
        action='store_true',
        help='允许对有效消息子集继续 run（默认任何 rejection → exit 1）'
    )
    # R354：统一 --config 参数（run 使用配置中的检测器阈值）
    run_parser.add_argument(
        '--config',
        help='配置文件路径（默认使用 config/defaults.json）'
    )

    # evaluate 子命令
    evaluate_parser = subparsers.add_parser(
        'evaluate',
        help='评估推断结果'
    )
    evaluate_parser.add_argument(
        'predictions_file',
        help='预测结果文件路径'
    )
    evaluate_parser.add_argument(
        'ground_truth_file',
        help='真值文件路径'
    )
    # R338：显式 partial Ground Truth 模式
    # 默认 fail closed（任何拒绝 → exit 1）；显式指定时继续评价合法子集
    evaluate_parser.add_argument(
        '--allow-partial-ground-truth',
        action='store_true',
        help='允许对合法真值子集继续评价（默认拒绝任何损坏 truth）'
    )

    return parser


def _load_config_from_args(args: argparse.Namespace):
    """R354：从命令行参数加载配置

    根据 args.config 加载配置文件：
    - 指定 --config PATH：用用户配置覆盖默认配置（load_config_with_override）
    - 未指定 --config：使用 config/defaults.json（load_default_config）

    Args:
        args: 解析后的参数（可能包含 args.config）

    Returns:
        Config 对象

    Raises:
        FileNotFoundError: 配置文件路径不存在
        json.JSONDecodeError: JSON 格式损坏（继承自 ValueError）
        ValueError: 配置值类型非法或超出范围
        TypeError: 配置值类型不匹配
    """
    from pathlib import Path
    from semantic_detector.config import load_default_config, load_config_with_override

    config_path = getattr(args, 'config', None)
    if config_path:
        return load_config_with_override(Path(config_path))
    else:
        return load_default_config()


def cmd_validate(args: argparse.Namespace) -> int:
    """validate 子命令处理

    修复 HIGH-2：接入组级字段数校验。读取 JSONL 后调用共享入口
    prepare_records_for_profiling 执行 分组→字段数校验→展平，
    对不一致组报错并退出非零。

    Args:
        args: 解析后的参数

    Returns:
        退出码：0 全部通过；1 存在组级拒绝；2 输入文件问题
    """
    import os
    import json
    from pathlib import Path
    from semantic_detector.io.jsonl import read_jsonl_file
    from semantic_detector.io.exporters import (
        export_validated_records,
        export_rejected_records_unified,
    )
    from semantic_detector.profiling.collector import prepare_records_for_profiling

    # 检查输入文件是否存在
    if not os.path.exists(args.input_file):
        print(f"错误: 输入文件不存在: {args.input_file}", file=sys.stderr)
        return 2

    # 检查输入文件是否为文件
    if not os.path.isfile(args.input_file):
        print(f"错误: 输入路径不是文件: {args.input_file}", file=sys.stderr)
        return 2

    # 读取并验证 JSONL 文件（JSON 级校验）
    try:
        valid_records, rejected_records = read_jsonl_file(args.input_file)
    except Exception as e:
        print(f"错误: 读取文件失败: {e}", file=sys.stderr)
        return 1

    # 组级字段数校验（HIGH-2：原 cmd_validate 漏掉此步）
    group_valid_records, _valid_groups, rejections = prepare_records_for_profiling(
        valid_records
    )

    # 确定输出目录
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = Path(args.input_file).parent

    output_dir.mkdir(parents=True, exist_ok=True)

    # R392：开始前清理 validate 拥有的旧产物（产物所有权接入）
    # 只清理 validate 命令拥有的文件（validated/rejected/rejected_groups/validate.log），
    # 不删除输入文件、不删除子目录、不删除其他命令的产物。
    from semantic_detector.io.artifact_manager import clean_command_artifacts
    removed_artifacts = clean_command_artifacts(str(output_dir), "validate")
    if removed_artifacts:
        print(f"已清理 validate 旧产物: {', '.join(sorted(removed_artifacts))}")

    # R342：无条件导出 validated 记录（空列表写空文件，防止旧产物残留）
    validated_path = output_dir / "validated.jsonl"
    if group_valid_records:
        export_validated_records(group_valid_records, str(validated_path))
        print(f"导出 {len(group_valid_records)} 条有效记录到 {validated_path}")
    else:
        # 无有效记录时写空文件
        with open(validated_path, 'w', encoding='utf-8') as f:
            pass
        print(f"无有效记录，{validated_path} 已重写为空文件")

    # R383：使用统一 RejectedRecord 导出（HIGH-2 修复）
    # 不直接 json.dumps(MessageRecord)；用 RejectedRecord.to_dict() 保证可序列化。
    # 无 rejection 时写空文件，避免旧文件残留。
    rejected_path = output_dir / "rejected.jsonl"
    export_rejected_records_unified(rejected_records, str(rejected_path))
    if rejected_records:
        print(f"导出 {len(rejected_records)} 条 JSON 级拒绝记录到 {rejected_path}")

    # R342：无条件导出组级 rejected_groups 记录（空列表写空文件）
    rejected_groups_path = output_dir / "rejected_groups.jsonl"
    with open(rejected_groups_path, 'w', encoding='utf-8') as f:
        for rec in rejections:
            entry = {
                "group_key": list(rec.group_key),
                "record_count": rec.record_count,
                "field_counts": [list(pair) for pair in rec.field_counts],
                "reason_code": rec.reason_code,
                "rejected_message_ids": [r.message_id for r in rec.records],
            }
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    if rejections:
        print(f"导出 {len(rejections)} 个组级拒绝组到 {rejected_groups_path}")
        for rec in rejections:
            print(
                f"错误: 组 {rec.group_key} 字段数不一致 "
                f"(record_count={rec.record_count}, field_counts={rec.field_counts}, "
                f"reason_code={rec.reason_code})",
                file=sys.stderr,
            )

    # R342/R422：统一拒绝计数（严格区分记录数和组数）
    # R422 修正：原 total_rejections = len(rejected_records) + len(rejections) 混用记录数和组数
    # 现在：total_rejected_record_count = 单记录拒绝数 + 组内消息数
    single_record_rejection_count = len(rejected_records)
    group_rejection_count = len(rejections)
    group_rejected_record_count = sum(rec.record_count for rec in rejections)
    total_rejected_record_count = single_record_rejection_count + group_rejected_record_count
    print(
        f"验证完成: {len(group_valid_records)} 组级有效, "
        f"{single_record_rejection_count} 单记录拒绝, "
        f"{group_rejection_count} 冲突组数, "
        f"{group_rejected_record_count} 冲突组内消息数, "
        f"{total_rejected_record_count} 总拒绝消息数"
    )
    # R342：任何 rejection > 0 → exit 1（fail closed）
    return 1 if total_rejected_record_count > 0 else 0


def cmd_profile(args: argparse.Namespace) -> int:
    """profile 子命令处理

    修复 HIGH-2：接入共享准备流程 prepare_records_for_profiling。
    对字段数不一致的组**跳过**（不送入 build_field_profiles），
    并导出 rejected_groups.jsonl；为通过校验的组生成画像。

    Args:
        args: 解析后的参数

    Returns:
        退出码：0 成功生成画像（即使存在被跳过的组）；1 读取/生成失败；2 输入文件问题
    """
    import os
    import json
    from pathlib import Path
    from semantic_detector.io.jsonl import read_jsonl_file
    from semantic_detector.io.exporters import (
        export_field_profiles,
        export_rejected_records_unified,
    )
    from semantic_detector.io.artifact_manager import clean_command_artifacts
    from semantic_detector.profiling.profile_builder import build_field_profiles
    from semantic_detector.profiling.collector import prepare_records_for_profiling

    # 检查输入文件是否存在
    if not os.path.exists(args.input_file):
        print(f"错误: 输入文件不存在: {args.input_file}", file=sys.stderr)
        return 2

    # 检查输入文件是否为文件
    if not os.path.isfile(args.input_file):
        print(f"错误: 输入路径不是文件: {args.input_file}", file=sys.stderr)
        return 2

    # R354：加载配置（R355 将把 config 传给 Pipeline/检测器）
    # 路径不存在/JSON 损坏/类型非法时抛异常，由 main() 捕获返回非零退出码
    config = _load_config_from_args(args)
    if args.config:
        print(f"使用用户配置: {args.config}")
    else:
        print(f"使用默认配置: config/defaults.json")

    # 读取输入文件
    # R385：不忽略 rejected_records（HIGH-3 修复），用于导出 rejected.jsonl
    try:
        valid_records, rejected_records = read_jsonl_file(args.input_file)
    except Exception as e:
        print(f"错误: 读取文件失败: {e}", file=sys.stderr)
        return 1

    # 组级字段数校验（HIGH-2：原 cmd_profile 直接 build_field_profiles(valid_records)，漏掉校验）
    group_valid_records, _valid_groups, rejections = prepare_records_for_profiling(
        valid_records
    )

    # 确定输出目录（R417：提前到 build_field_profiles 之前，以便失败时也能清理旧产物）
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = Path(args.input_file).parent

    output_dir.mkdir(parents=True, exist_ok=True)

    # R417：清理旧产物（补齐阶段 C 遗漏，与 cmd_validate/cmd_run/cmd_infer 对齐）
    # 确保即使 build_field_profiles 失败，旧 field_profiles.jsonl 也不会残留
    clean_command_artifacts(str(output_dir), "profile")

    # 生成字段画像（仅对通过组级校验的记录）
    # R358：传入 config.timestamp_slop_seconds 让时间戳容差由配置驱动
    # R415：传入 config.min_samples 让样本不足标志由配置驱动（修复 R405 遗漏 cmd_profile）
    try:
        profiles = build_field_profiles(
            group_valid_records,
            slop_seconds=config.timestamp_slop_seconds,
            min_samples=config.min_samples,
        )
    except Exception as e:
        print(f"错误: 生成字段画像失败: {e}", file=sys.stderr)
        # R417：失败时写空 field_profiles.jsonl 覆盖（已被 clean 删除，此处重建空文件）
        profiles_path = output_dir / "field_profiles.jsonl"
        with open(profiles_path, 'w', encoding='utf-8'):
            pass
        return 1

    # 导出字段画像
    profiles_path = output_dir / "field_profiles.jsonl"
    export_field_profiles(profiles, str(profiles_path))
    print(f"导出 {len(profiles)} 个字段画像到 {profiles_path}")

    # R385：导出 JSON 级 rejected 记录（HIGH-3 修复）
    # 不再忽略 rejected_records；用统一 RejectedRecord.to_dict() 写入。
    # 无 rejection 时写空文件，避免旧文件残留。
    rejected_path = output_dir / "rejected.jsonl"
    export_rejected_records_unified(rejected_records, str(rejected_path))
    if rejected_records:
        print(f"导出 {len(rejected_records)} 条 JSON 级拒绝记录到 {rejected_path}")

    # R391：无条件导出组级 rejected_groups 记录（空列表写空文件，覆盖旧产物）
    # 与 cmd_validate 对齐：原实现 `if rejections:` 条件写入，
    # 第二次全合法时不写 → 旧 rejected_groups.jsonl 残留（MEDIUM-3 修复）。
    rejected_groups_path = output_dir / "rejected_groups.jsonl"
    with open(rejected_groups_path, 'w', encoding='utf-8') as f:
        for rec in rejections:
            entry = {
                "group_key": list(rec.group_key),
                "record_count": rec.record_count,
                "field_counts": [list(pair) for pair in rec.field_counts],
                "reason_code": rec.reason_code,
                "rejected_message_ids": [r.message_id for r in rec.records],
            }
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    if rejections:
        print(f"跳过 {len(rejections)} 个字段数不一致的组，导出到 {rejected_groups_path}")
        for rec in rejections:
            print(
                f"警告: 跳过组 {rec.group_key} "
                f"(record_count={rec.record_count}, field_counts={rec.field_counts}, "
                f"reason_code={rec.reason_code})",
                file=sys.stderr,
            )
    else:
        print(f"导出 0 个组级拒绝组到 {rejected_groups_path}（空文件）")

    # R385/R422：fail closed（HIGH-3 修复）+ 严格区分记录数和组数
    # R422 修正：原 total_rejections = len(rejected_records) + len(rejections) 混用记录数和组数
    # 现在：total_rejected_record_count = 单记录拒绝数 + 组内消息数
    single_record_rejection_count = len(rejected_records)
    group_rejection_count = len(rejections)
    group_rejected_record_count = sum(rec.record_count for rec in rejections)
    total_rejected_record_count = single_record_rejection_count + group_rejected_record_count
    print(
        f"验证完成: {len(group_valid_records)} 组级有效, "
        f"{single_record_rejection_count} 单记录拒绝, "
        f"{group_rejection_count} 冲突组数, "
        f"{group_rejected_record_count} 冲突组内消息数, "
        f"{total_rejected_record_count} 总拒绝消息数"
    )
    return 1 if total_rejected_record_count > 0 else 0


def main(argv: List[str] | None = None) -> int:
    """主函数
    
    Args:
        argv: 命令行参数，如果为 None 则使用 sys.argv[1:]
        
    Returns:
        退出码
    """
    # R350：规范化 argv，便于把原始命令行参数传给 cmd_run（避免测试环境捕获 sys.argv 中的 pytest 参数）
    if argv is None:
        argv = sys.argv[1:]
    parser = create_parser()
    
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        raise
    
    if args.command is None:
        parser.print_help()
        return 0
    
    try:
        if args.command == 'validate':
            return cmd_validate(args)
        
        if args.command == 'profile':
            return cmd_profile(args)
        
        if args.command == 'infer':
            return cmd_infer(args)
        
        if args.command == 'run':
            return cmd_run(args, cli_args=tuple(argv))
        
        if args.command == 'evaluate':
            return cmd_evaluate(args)
        
        print(f"子命令 '{args.command}' 尚未实现", file=sys.stderr)
        return 1
    except FileNotFoundError as e:
        print(f"错误: 文件未找到: {e}", file=sys.stderr)
        return 2
    except PermissionError as e:
        print(f"错误: 权限不足: {e}", file=sys.stderr)
        return 2
    except ValueError as e:
        print(f"错误: 数据格式错误: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1


def _write_failed_run_artifacts(
    output_dir,
    input_file: str,
    config,
    started_at: str,
    error_stage: str,
    error_message: str,
    valid_records: int,
    rejected_records: int,
    log_fn,
    error_type: str = "",
    config_source: str = "default",
    config_path: str = "",
    input_line_count: int = 0,
) -> None:
    """R390/R421/R427：失败 Run 写入失败 Manifest + 半成品清理

    失败运行不能没有 Manifest，也不能留下旧成功 Manifest。
    本函数在 cmd_run 的失败路径调用，执行：

    1. 写空 predictions.jsonl（始终覆盖，predictions 不得保留旧内容/半写内容）
    2. 根据失败阶段决定是否清空 field_profiles.jsonl：
       - 失败阶段在 build_profiles/export_profiles 或之前：写空 profiles
       - 失败阶段在 detect_fields 及之后：保留诊断用 profiles，标记 partial_artifacts_present=true
    3. 生成新 run_id（禁止复用旧 run_id）
    4. 计算输入文件 SHA-256（无法读取时为空串）
    5. 计算配置文件 SHA-256（无配置文件时为空串）
    6. 构建失败 Manifest（R390 14 基础 + R421 7 扩展字段，status=failed）
    7. 原子写入 manifest.json（覆盖旧成功 Manifest）
    8. 失败 Manifest 写入失败的兜底：清理旧 manifest + stderr 输出

    R427 扩展：支持 preflight 阶段（create_output_dir/open_log/validate_input_path/
    load_config/validate_config）失败时调用。config 可为 None（配置加载失败前），
    此时 resolved_config 写空字典。

    Args:
        output_dir: 输出目录（Path）
        input_file: 输入文件路径
        config: Config 对象（含 to_dict()），R427 起可为 None（preflight 失败前）
        started_at: 命令开始时间 ISO 8601 字符串
        error_stage: 失败阶段名（read_jsonl / build_field_profiles / validate_input_path 等）
        error_message: 错误消息字符串
        valid_records: 进入失败阶段时的有效记录数
        rejected_records: 进入失败阶段时的拒绝记录数
        log_fn: 日志函数（cmd_run 内的 log 闭包）
        error_type: 异常类型名（如 "RuntimeError"），R421 扩展
        config_source: 配置来源（"default" 或用户配置路径），R421 扩展
        config_path: 配置文件路径（用于计算 SHA-256，无配置时为空串），R421 扩展
        input_line_count: 输入文件总行数，R421 扩展
    """
    import json
    import os
    import sys
    import uuid
    import tempfile
    from datetime import datetime
    from pathlib import Path
    from semantic_detector.io.exporters import build_failed_run_manifest, hash_file_sha256

    # R426/R427：统一阶段顺序 + 纯函数 + 文件存在性检查
    # R427：新增 preflight 阶段（create_output_dir/open_log/validate_input_path/
    # load_config/validate_config），序号在 read_input 之前
    # 替换零散的 STAGES_BEFORE_PROFILES/STAGES_BEFORE_PREDICTIONS 集合
    # 解决 MEDIUM-1：write_rejected_groups/count_input_lines 未加入阶段集合的问题
    RUN_STAGE_ORDER: dict = {
        "initialize": 0,
        "create_output_dir": 1,
        "open_log": 2,
        "validate_input_path": 3,
        "load_config": 4,
        "validate_config": 5,
        "read_input": 10,
        "validate_input": 20,
        "export_validated": 30,
        "export_rejected": 40,
        "write_rejected_groups": 50,
        "count_input_lines": 60,
        "build_profiles": 70,
        "export_profiles": 80,
        "detect_fields": 90,
        "export_predictions": 100,
        "generate_manifest": 110,
        "write_manifest": 120,
        "finalize": 130,
    }

    def stage_may_have_profiles(stage: str) -> bool:
        """阶段在 build_profiles 之后：profiles 可能已完整写入文件"""
        current = RUN_STAGE_ORDER.get(stage)
        build = RUN_STAGE_ORDER["build_profiles"]
        return current is not None and current > build

    def stage_may_have_predictions(stage: str) -> bool:
        """阶段在 export_predictions 之后：predictions 可能已完整写入文件"""
        current = RUN_STAGE_ORDER.get(stage)
        export_pred = RUN_STAGE_ORDER["export_predictions"]
        return current is not None and current > export_pred

    predictions_path = output_dir / "predictions.jsonl"
    profiles_path = output_dir / "field_profiles.jsonl"

    # R427：preflight 阶段（create_output_dir/open_log/validate_input_path/load_config/
    # validate_config）序号都 < read_input(10)，stage_may_have_profiles/predictions 均返回
    # False，因此 partial_artifacts_present=False，predictions/profiles 都会被清空。
    # 但若 create_output_dir 失败导致 output_dir 不存在，清理动作需跳过（无法写入）。
    output_dir_exists = output_dir.exists() and output_dir.is_dir()

    # R426：基于阶段序号 + 文件真实存在性判断 partial_artifacts_present
    # R427：output_dir 不存在时直接 False（无法读取文件状态）
    if output_dir_exists:
        profiles_present = (
            stage_may_have_profiles(error_stage)
            and profiles_path.exists()
            and profiles_path.stat().st_size > 0
        )
        predictions_present = (
            stage_may_have_predictions(error_stage)
            and predictions_path.exists()
            and predictions_path.stat().st_size > 0
        )
    else:
        profiles_present = False
        predictions_present = False
    partial_artifacts_present = profiles_present or predictions_present

    # R427：output_dir 不存在时跳过 predictions/profiles 清理（无法创建文件）
    # 此时调用方应已通过 stderr 输出明确错误
    if output_dir_exists:
        # 1. predictions 清理策略：
        #    - 阶段在 export_predictions 或之前：清空（半写或未生成）
        #    - 阶段在 export_predictions 之后：保留已写入的诊断 predictions
        if not stage_may_have_predictions(error_stage):
            with open(predictions_path, 'w', encoding='utf-8') as f:
                pass
        else:
            # 保留已写入的 predictions，但若不存在则写空文件
            if not predictions_path.exists():
                with open(predictions_path, 'w', encoding='utf-8') as f:
                    pass

        # 2. profiles 清理策略：
        #    - 阶段在 build_profiles 或之前：清空
        #    - 阶段在 export_profiles 之后：保留诊断用 profiles
        if not stage_may_have_profiles(error_stage):
            with open(profiles_path, 'w', encoding='utf-8') as f:
                pass
        else:
            # 保留诊断用 profiles，但若不存在则写空文件
            if not profiles_path.exists():
                with open(profiles_path, 'w', encoding='utf-8') as f:
                    pass

    # 3. 生成新 run_id（不复用旧 run_id）
    failed_run_id = str(uuid.uuid4())

    # 4. 计算输入文件 SHA-256（无法读取时为空串）
    try:
        input_sha256 = hash_file_sha256(input_file)
    except (OSError, IOError):
        input_sha256 = ""

    # 5. 计算配置文件 SHA-256（无配置文件时为空串）
    config_sha256 = ""
    if config_path:
        try:
            config_sha256 = hash_file_sha256(config_path)
        except (OSError, IOError):
            config_sha256 = ""

    # 6. 构建失败 Manifest（R390 14 基础 + R421 7 扩展字段）
    # R427：config 可能为 None（preflight 失败前，配置尚未加载），此时用空字典
    resolved_config = config.to_dict() if config is not None else {}
    manifest = build_failed_run_manifest(
        run_id=failed_run_id,
        status="failed",
        exit_code=1,
        started_at=started_at,
        finished_at=datetime.now().isoformat(),
        input_path=str(Path(input_file).resolve()),
        input_sha256=input_sha256,
        resolved_config=resolved_config,
        valid_records=valid_records,
        rejected_records=rejected_records,
        error_stage=error_stage,
        error_message=error_message,
        error_type=error_type,
        config_source=config_source,
        config_sha256=config_sha256,
        input_line_count=input_line_count,
        partial_artifacts_present=partial_artifacts_present,
    )

    # 7. 原子写入 manifest.json（临时文件 + os.replace）
    manifest_path = output_dir / "manifest.json"
    tmp_path = None  # R426-BUG2：提前初始化，确保 except 块能正确清理
    try:
        with tempfile.NamedTemporaryFile(
            mode='w',
            dir=str(output_dir),
            delete=False,
            encoding='utf-8',
            suffix='.tmp',
        ) as tmp_file:
            tmp_path = tmp_file.name  # R426-BUG2：进入 with 后立即赋值，json.dump 失败也能清理
            json.dump(manifest, tmp_file, indent=2, ensure_ascii=False)
        os.replace(tmp_path, str(manifest_path))
        try:  # R426-BUG7：log_fn 包裹 try/except，避免日志写入失败掩盖原始异常
            log_fn(f"  导出失败 manifest 到 {manifest_path}（status=failed, error_stage={error_stage}）")
        except Exception:
            pass
    except (OSError, IOError, ValueError) as write_exc:
        # 8. 失败 Manifest 写入失败的兜底：
        # - 清理临时文件
        # - 清理旧成功 Manifest（不得回退保留旧 Manifest）
        # - stderr 输出
        # - 不抛异常（避免掩盖原始异常）
        try:
            if tmp_path is not None and os.path.exists(tmp_path):
                os.unlink(tmp_path)
        except OSError:
            pass
        try:
            if manifest_path.exists():
                manifest_path.unlink()
        except OSError:
            pass
        print(
            f"错误: 写入失败 Manifest 失败: {write_exc}（已清理旧 Manifest，不保留旧成功产物）",
            file=sys.stderr,
        )
        try:  # R426-BUG7：log_fn 包裹 try/except
            log_fn(f"  错误: 写入失败 Manifest 失败: {write_exc}")
        except Exception:
            pass


def cmd_run(args: argparse.Namespace, cli_args: tuple = ()) -> int:
    """run 子命令处理

    R427 重构：将输入检查、配置加载、输出目录创建、日志打开等 preflight 阶段
    全部移入统一 try/except/finally，确保 preflight 失败也能生成失败 Manifest。
    例外：输出目录本身不可创建时，仅保证非零退出和 stderr，不保证落盘 Manifest。

    Args:
        args: 解析后的参数
        cli_args: 原始命令行参数元组（R350：用于 manifest 的 command_args，避免测试环境捕获 sys.argv）

    Returns:
        退出码
    """
    import os
    import json
    from pathlib import Path
    from datetime import datetime
    from semantic_detector.io.jsonl import read_jsonl_file
    from semantic_detector.io.exporters import (
        export_validated_records,
        export_field_profiles,
        export_predictions_to_jsonl,
        export_rejected_records_unified,
    )
    from semantic_detector.io.artifact_manager import clean_command_artifacts
    from semantic_detector.profiling.profile_builder import build_field_profiles
    from semantic_detector.pipeline.pipeline import DetectionPipeline

    # R427：最早确定 started_at/command_args/output_dir（preflight 失败也能用）
    # R350：使用 main 传入的 cli_args，避免在测试环境捕获 sys.argv 中的 pytest 参数
    started_at = datetime.now().isoformat()
    command_args = cli_args if cli_args else (tuple(sys.argv[1:]) if hasattr(sys, 'argv') else tuple())

    # 确定输出目录（提前确定，便于 preflight 失败时也能写入 Manifest）
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = Path(args.input_file).parent / "output"

    # R427：config 延迟到 try 内加载；config_source 提前计算（用于失败 Manifest）
    config = None
    config_source = getattr(args, 'config', None) or "default"

    # R427：log_file 延迟到 try 内打开；在此之前用 noop_log 兜底
    log_file = None

    def noop_log(message: str):
        """R427：log_file 未打开时的兜底日志函数（仅 stderr）"""
        print(message, file=sys.stderr)

    log = noop_log

    # R420/R427：current_stage 跟踪当前执行阶段，用于失败 Manifest 的 error_stage
    # R427：初始阶段为 create_output_dir（最早的 preflight 阶段）
    current_stage = "create_output_dir"
    # R420：跟踪失败时已知的计数值（传入 _write_failed_run_artifacts）
    valid_records_count = 0
    rejected_records_count = 0
    # R421：input_line_count 跟踪（在 try 内更新），用于失败 Manifest 的 counts
    input_line_count = 0

    try:
        # R427 Preflight 阶段 0a: create_output_dir
        current_stage = "create_output_dir"
        output_dir.mkdir(parents=True, exist_ok=True)

        # R389：开始前清理 run 拥有的旧产物（HIGH-4 修复）
        # 只清理 run 命令拥有的 7 个文件（validated/rejected/rejected_groups/
        # field_profiles/predictions/manifest/run.log），不删除输入文件、
        # 不删除子目录、不删除其他命令的产物。
        removed_artifacts = clean_command_artifacts(str(output_dir), "run")

        # R427 Preflight 阶段 0b: open_log
        current_stage = "open_log"
        log_path = output_dir / "run.log"
        log_file = open(log_path, 'w', encoding='utf-8')

        def file_log(message: str):
            """同时写入日志文件和控制台"""
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_line = f"[{timestamp}] {message}"
            try:
                log_file.write(log_line + '\n')
            except Exception:
                pass  # 日志写入失败不应影响主流程
            print(message)

        log = file_log  # 替换为正式日志函数

        # R389：记录清理动作到日志
        if removed_artifacts:
            log(f"已清理 run 旧产物: {', '.join(sorted(removed_artifacts))}")
        else:
            log("无 run 旧产物需要清理")

        # R427 Preflight 阶段 0c: validate_input_path
        current_stage = "validate_input_path"
        if not os.path.exists(args.input_file):
            raise FileNotFoundError(f"输入文件不存在: {args.input_file}")
        if not os.path.isfile(args.input_file):
            raise ValueError(f"输入路径不是文件: {args.input_file}")

        log(f"开始流水线: {args.input_file} -> {output_dir}")

        # R427 Preflight 阶段 0d: load_config
        # R354：加载配置（R355 将把 config 传给 Pipeline/检测器）
        # 路径不存在/JSON 损坏时抛异常（load_config 阶段）
        # 配置值非法时由 Config.__post_init__ 抛 ValueError（validate_config 阶段）
        # R427：拆分为两步，便于失败 Manifest 精确定位 failure_stage
        current_stage = "load_config"
        from semantic_detector.config import (
            load_default_config as _load_default_config,
            load_config_with_override as _load_config_with_override,
        )
        config_path_arg = getattr(args, 'config', None)
        if config_path_arg:
            from pathlib import Path as _Path
            # Step 1: load_config — 读取并解析 JSON（FileNotFoundError / JSONDecodeError）
            # 复用 load_config_with_override 但捕获 ValueError（来自 __post_init__）以便分阶段标记
            try:
                config = _load_config_with_override(_Path(config_path_arg))
            except (FileNotFoundError, json.JSONDecodeError, KeyError, TypeError):
                # 这些异常属于 load_config 阶段（路径/JSON/键问题）
                raise
            except ValueError:
                # ValueError 来自 Config.__post_init__ 的值校验 → 重新标记为 validate_config
                current_stage = "validate_config"
                raise
        else:
            try:
                config = _load_default_config()
            except (FileNotFoundError, json.JSONDecodeError, KeyError, TypeError):
                raise
            except ValueError:
                current_stage = "validate_config"
                raise

        # R427 Preflight 阶段 0e: validate_config
        # Config.__post_init__ 已在构造时验证（min_samples>0、阈值在 0~1 范围等），
        # 若到达此处说明配置合法。此处显式标记阶段，便于后续阶段失败时精确定位。
        current_stage = "validate_config"
        config_source = getattr(args, 'config', None) or "default"

        # 阶段 1: validate (read_input)
        current_stage = "read_input"
        log("阶段 1: 验证记录...")
        valid_records, rejected_records = read_jsonl_file(args.input_file)
        rejected_records_count = len(rejected_records)

        # 审计修复瑕疵-10：拆分 JSON 解析拒绝与契约校验拒绝
        # read_jsonl_file 同时做 JSON 解析和契约校验（重复 message_id），
        # 返回的 rejected_records 混合两类：{'error': ...} 为 JSON 解析失败；
        # {'reason': 'Duplicate message_id: ...'} 为契约校验失败。
        # 原实现将两者全部计入 json_rejected_records，contract_rejected_records 恒为 0。
        json_rejected_count = sum(1 for r in rejected_records if 'error' in r)
        contract_rejected_count = sum(1 for r in rejected_records if 'reason' in r)

        # 组级字段数校验（HIGH-2：原 cmd_run 直接 build_field_profiles(valid_records)，漏掉校验）
        current_stage = "validate_input"
        from semantic_detector.profiling.collector import prepare_records_for_profiling
        group_valid_records, _valid_groups, rejections = prepare_records_for_profiling(
            valid_records
        )
        valid_records_count = len(group_valid_records)
        # R426-BUG3：失败路径 rejected_records_count 不再混用记录数和组数
        # 原实现：len(rejected_records) + len(rejections) ← 记录数 + 组数（维度混用）
        # R426 修正：单记录拒绝数 + 组内消息数（都是消息数，维度一致）
        rejected_records_count = len(rejected_records) + sum(
            rec.record_count for rec in rejections
        )

        # 导出 validated 记录（通过组级校验的）
        current_stage = "export_validated"
        validated_path = output_dir / "validated.jsonl"
        if group_valid_records:
            export_validated_records(group_valid_records, str(validated_path))
            log(f"  导出 {len(group_valid_records)} 条有效记录到 {validated_path}")
        else:
            with open(validated_path, 'w', encoding='utf-8') as f:
                pass
            log(f"  导出 0 条有效记录到 {validated_path}")

        # R383：使用统一 RejectedRecord 导出（HIGH-2 修复，与 cmd_validate 一致）
        current_stage = "export_rejected"
        rejected_path = output_dir / "rejected.jsonl"
        export_rejected_records_unified(rejected_records, str(rejected_path))
        if rejected_records:
            log(f"  导出 {len(rejected_records)} 条 JSON 级拒绝记录到 {rejected_path}")

        # R344：无条件导出组级 rejected_groups 记录（空列表写空文件）
        # R426-BUG5：rejected_groups 写入单独设置 stage，提升失败诊断精度
        current_stage = "write_rejected_groups"
        rejected_groups_path = output_dir / "rejected_groups.jsonl"
        with open(rejected_groups_path, 'w', encoding='utf-8') as f:
            for rec in rejections:
                entry = {
                    "group_key": list(rec.group_key),
                    "record_count": rec.record_count,
                    "field_counts": [list(pair) for pair in rec.field_counts],
                    "reason_code": rec.reason_code,
                    "rejected_message_ids": [r.message_id for r in rec.records],
                }
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        if rejections:
            log(f"  导出 {len(rejections)} 个组级拒绝组到 {rejected_groups_path}")

        # R349/R350：提前统计输入文件总行数和组级拒绝记录数（0 有效记录分支和正常分支共用）
        # R421：input_line_count 已在 try 前初始化为 0，此处累加实际行数
        # R426-BUG5：input_line_count 计数单独设置 stage
        current_stage = "count_input_lines"
        with open(args.input_file, 'r', encoding='utf-8') as f:
            for _ in f:
                input_line_count += 1
        group_rejected_count = sum(rec.record_count for rec in rejections)

        # R344：0 有效记录时 fail closed
        # status=no_valid_records + exit 1 + predictions/profiles 写空文件 + 不输出"流水线完成"
        if not group_valid_records:
            log("错误: 无有效记录（全部输入被拒绝）")
            # 写空 predictions 和 profiles 文件（防止旧产物残留）
            predictions_path = output_dir / "predictions.jsonl"
            with open(predictions_path, 'w', encoding='utf-8') as f:
                pass
            profiles_path = output_dir / "field_profiles.jsonl"
            with open(profiles_path, 'w', encoding='utf-8') as f:
                pass
            # R349/R350：用 generate_manifest 生成统一 manifest（含 RunCounts + RunManifestInfo）
            # 审计修复瑕疵-10：json_valid_records 包含通过 JSON 解析的记录（含后续契约失败的）；
            # contract_valid_records 只含通过 JSON + 契约双重校验的记录（即 valid_records）。
            # R422：group_rejection_count（组数）vs group_rejected_records（组内消息数）严格分开
            from semantic_detector.contracts import RunCounts, RunManifestInfo
            run_counts = RunCounts(
                input_line_count=input_line_count,
                json_valid_records=len(valid_records) + contract_rejected_count,
                json_rejected_records=json_rejected_count,
                contract_valid_records=len(valid_records),
                contract_rejected_records=contract_rejected_count,
                group_valid_records=0,
                group_rejected_records=group_rejected_count,
                field_profiles=0,
                predictions=0,
                group_rejection_count=len(rejections),
            )
            run_info = RunManifestInfo(
                status="no_valid_records",
                exit_code=1,
                partial_input=getattr(args, 'allow_partial_input', False),
                valid_for_reporting=False,
                started_at=started_at,
                finished_at=datetime.now().isoformat(),
                command_args=command_args,
            )
            # R426-BUG4：no_valid_records 分支也更新 current_stage，提升失败诊断精度
            current_stage = "generate_manifest"
            no_valid_pipeline = DetectionPipeline(config=config, config_source=config_source)
            manifest = no_valid_pipeline.generate_manifest(
                args.input_file,
                str(output_dir),
                [],
                [],
                run_counts=run_counts,
                run_info=run_info,
            )
            current_stage = "write_manifest"
            manifest_path = output_dir / "manifest.json"
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)
            log(f"  导出 manifest 到 {manifest_path}（status=no_valid_records）")
            return 1

        # 阶段 2: profile（仅对通过组级校验的记录生成画像）
        current_stage = "build_profiles"
        log("阶段 2: 生成字段画像...")
        # R358：传入 config.timestamp_slop_seconds 让时间戳容差由配置驱动
        # R405：传入 config.min_samples 让样本不足标志由配置驱动
        profiles = build_field_profiles(
            group_valid_records,
            slop_seconds=config.timestamp_slop_seconds,
            min_samples=config.min_samples,
        )

        current_stage = "export_profiles"
        profiles_path = output_dir / "field_profiles.jsonl"
        export_field_profiles(profiles, str(profiles_path))
        log(f"  导出 {len(profiles)} 个字段画像到 {profiles_path}")

        # 阶段 3: infer
        current_stage = "detect_fields"
        log("阶段 3: 执行推断...")
        # R359：传入 config_source 用于 manifest 审计（config_source 已在前面提前计算）
        pipeline = DetectionPipeline(config=config, config_source=config_source)
        predictions = pipeline.detect_fields(profiles)

        current_stage = "export_predictions"
        predictions_path = output_dir / "predictions.jsonl"
        export_predictions_to_jsonl(predictions, str(predictions_path))
        log(f"  导出 {len(predictions)} 个预测结果到 {predictions_path}")

        # 生成 manifest
        current_stage = "generate_manifest"
        log("生成 manifest...")
        # R349：构造 RunCounts（input_line_count 和 group_rejected_count 已提前计算）
        # 审计修复瑕疵-10：拆分 JSON 解析拒绝与契约校验拒绝（原 contract_rejected_records 恒为 0）
        # R422：group_rejection_count（组数）vs group_rejected_records（组内消息数）严格分开
        from semantic_detector.contracts import RunCounts, RunManifestInfo
        group_rejection_count = len(rejections)  # 冲突组数量
        run_counts = RunCounts(
            input_line_count=input_line_count,
            json_valid_records=len(valid_records) + contract_rejected_count,
            json_rejected_records=json_rejected_count,
            contract_valid_records=len(valid_records),  # 通过 JSON + 契约双重校验
            contract_rejected_records=contract_rejected_count,
            group_valid_records=len(group_valid_records),
            group_rejected_records=group_rejected_count,
            field_profiles=len(profiles),
            predictions=len(predictions),
            group_rejection_count=group_rejection_count,
        )
        # R350：构造 RunManifestInfo（统一 status/exit_code/partial_input/valid_for_reporting/started_at/finished_at/command_args）
        # 三态 status 逻辑（R345）：
        # - 无 rejection：status=completed, exit_code=0, valid_for_reporting=true
        # - 有 rejection + 无 --allow-partial-input：status=invalid_input, exit_code=1, valid_for_reporting=false（fail closed）
        # - 有 rejection + 有 --allow-partial-input 且有有效消息：status=partial_success, exit_code=0, valid_for_reporting=false
        allow_partial_input = getattr(args, 'allow_partial_input', False)
        # R422：修正 total_rejections 计算 — 不再混用记录数和组数
        # 原实现：total_rejections = len(rejected_records) + len(rejections) ← 记录数 + 组数（错误混用）
        # R422 修正：total_rejected_record_count = 单记录拒绝数 + 组内消息数
        single_record_rejection_count = len(rejected_records)  # 单记录拒绝数（JSON 级 + 契约级）
        total_rejected_record_count = single_record_rejection_count + group_rejected_count
        if total_rejected_record_count > 0:
            if allow_partial_input:
                run_status = "partial_success"
                run_exit_code = 0
                run_valid_for_reporting = False
            else:
                run_status = "invalid_input"
                run_exit_code = 1
                run_valid_for_reporting = False
        else:
            run_status = "completed"
            run_exit_code = 0
            run_valid_for_reporting = True
        run_info = RunManifestInfo(
            status=run_status,
            exit_code=run_exit_code,
            partial_input=allow_partial_input,
            valid_for_reporting=run_valid_for_reporting,
            started_at=started_at,
            finished_at=datetime.now().isoformat(),
            command_args=command_args,
        )
        manifest = pipeline.generate_manifest(
            args.input_file,
            str(output_dir),
            profiles,
            predictions,
            run_counts=run_counts,
            run_info=run_info,
        )

        current_stage = "write_manifest"
        manifest_path = output_dir / "manifest.json"
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        log(f"  导出 manifest 到 {manifest_path}")

        # R422：CLI 输出严格区分组数和消息数
        log(
            f"输入行数: {input_line_count}, "
            f"单记录拒绝: {single_record_rejection_count}, "
            f"冲突组数: {group_rejection_count}, "
            f"冲突组内消息数: {group_rejected_count}, "
            f"总拒绝消息数: {total_rejected_record_count}, "
            f"有效消息数: {len(group_valid_records)}"
        )

        # R345/R350：返回逻辑（exit_code 与 run_info.exit_code 一致）
        current_stage = "finalize"
        if total_rejected_record_count > 0:
            if allow_partial_input:
                log(f"流水线部分完成: {args.input_file} -> {output_dir}（{total_rejected_record_count} 条拒绝消息，status=partial_success）")
                return 0
            else:
                log(f"流水线失败: 检测到 {total_rejected_record_count} 个拒绝消息（未启用 --allow-partial-input）")
                return 1

        log(f"流水线完成: {args.input_file} -> {output_dir}")
        return 0

    except Exception as exc:
        # R420/R421/R427：统一异常处理 — 所有阶段异常（含 preflight）都尝试写失败 Manifest
        # 不吞异常：保留异常类型、消息、失败阶段、退出码
        # R421：传入 error_type/config_source/config_path/input_line_count 用于扩展 Manifest 字段
        # R426-BUG6：记录完整 traceback 用于调试（不写入正式 Manifest，仅写入日志）
        # R427：preflight 失败时 log_file 可能未打开（用 noop_log 兜底），config 可能为 None
        import traceback
        # R427：stderr 始终输出错误（无论 log_file 是否打开），保证用户可见
        print(f"错误: {current_stage} 阶段失败: {exc}", file=sys.stderr)
        log(f"错误: {current_stage} 阶段失败: {exc}")
        try:
            log(traceback.format_exc())
        except Exception:
            pass  # 日志写入失败不应掩盖原始异常
        _write_failed_run_artifacts(
            output_dir=output_dir,
            input_file=args.input_file,
            config=config,
            started_at=started_at,
            error_stage=current_stage,
            error_message=str(exc),
            valid_records=valid_records_count,
            rejected_records=rejected_records_count,
            log_fn=log,
            error_type=type(exc).__name__,
            config_source=config_source,
            config_path=getattr(args, 'config', '') or '',
            input_line_count=input_line_count,
        )
        return 1
    finally:
        # R420/R427：日志生命周期统一 — finally 中始终关闭 log_file（若已打开）
        # 解决 MEDIUM-1：异常路径 log_file 未关闭（Windows 文件锁）
        # R427：log_file 可能为 None（open_log 失败前），需检查
        if log_file is not None:
            try:
                log_file.close()
            except Exception:
                pass  # 关闭失败不应掩盖原始异常


def cmd_infer(args: argparse.Namespace) -> int:
    """infer 子命令处理
    
    Args:
        args: 解析后的参数
        
    Returns:
        退出码
    """
    import os
    from pathlib import Path
    from semantic_detector.io.exporters import import_field_profiles, export_predictions_to_jsonl
    from semantic_detector.io.artifact_manager import clean_command_artifacts
    from semantic_detector.pipeline.pipeline import DetectionPipeline

    # 检查输入文件是否存在
    if not os.path.exists(args.input_file):
        print(f"错误: 输入文件不存在: {args.input_file}", file=sys.stderr)
        return 2

    # 检查输入文件是否为文件
    if not os.path.isfile(args.input_file):
        print(f"错误: 输入路径不是文件: {args.input_file}", file=sys.stderr)
        return 2

    # R354：加载配置（R355 将把 config 传给 Pipeline/检测器）
    # 路径不存在/JSON 损坏/类型非法时抛异常，由 main() 捕获返回非零退出码
    config = _load_config_from_args(args)

    # 确定输出目录（提前确定，便于失败时也能清理旧产物）
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = Path(args.input_file).parent

    output_dir.mkdir(parents=True, exist_ok=True)

    # R392：开始前清理 infer 拥有的旧产物（产物所有权接入）
    # 只清理 infer 命令拥有的文件（predictions/infer.log/infer_manifest.json），
    # 不删除输入文件、不删除子目录、不删除其他命令的产物。
    removed_artifacts = clean_command_artifacts(str(output_dir), "infer")
    if removed_artifacts:
        print(f"已清理 infer 旧产物: {', '.join(sorted(removed_artifacts))}")

    # 读取字段画像
    try:
        profiles = import_field_profiles(args.input_file)
    except Exception as e:
        print(f"错误: 读取字段画像失败: {e}", file=sys.stderr)
        # R392：失败时写空 predictions，避免保留旧成功产物
        predictions_path = output_dir / "predictions.jsonl"
        with open(predictions_path, 'w', encoding='utf-8') as f:
            pass
        print(f"已写空 predictions.jsonl（读取画像失败，覆盖旧产物）")
        return 1

    # 创建检测流水线（R355：传入 config，所有检测器共享同一配置快照）
    # R359：传入 config_source 用于 manifest 审计
    config_source = getattr(args, 'config', None) or "default"
    pipeline = DetectionPipeline(config=config, config_source=config_source)

    # 执行推断
    try:
        predictions = pipeline.detect_fields(profiles)
    except Exception as e:
        print(f"错误: 推断失败: {e}", file=sys.stderr)
        # R392：失败时写空 predictions，避免保留旧成功产物
        predictions_path = output_dir / "predictions.jsonl"
        with open(predictions_path, 'w', encoding='utf-8') as f:
            pass
        print(f"已写空 predictions.jsonl（推断失败，覆盖旧产物）")
        return 1

    # 导出预测结果
    predictions_path = output_dir / "predictions.jsonl"
    export_predictions_to_jsonl(predictions, str(predictions_path))
    print(f"导出 {len(predictions)} 个预测结果到 {predictions_path}")

    return 0


def cmd_evaluate(args: argparse.Namespace) -> int:
    """evaluate 子命令处理
    
    Args:
        args: 解析后的参数
        
    Returns:
        退出码
    """
    import os
    import json
    from pathlib import Path
    from semantic_detector.io.exporters import (
        read_predictions_from_jsonl,
        read_semantic_predictions_from_jsonl,
        export_metrics_to_json,
        export_per_label_metrics_to_csv,
        export_confusion_matrix_to_csv,
        build_metrics_dict,
        export_rejected_records,
    )
    from semantic_detector.evaluation.ground_truth import read_ground_truth_jsonl, validate_ground_truth
    from semantic_detector.evaluation.metrics import (
        align_predictions_with_truth,
        calculate_overall_accuracy,
        calculate_coverage,
        calculate_unknown_rate,
        calculate_covered_accuracy,
        calculate_fine_top1_accuracy,
        collect_errors,
        export_errors_to_jsonl,
    )
    from semantic_detector.evaluation.confusion import (
        calculate_per_label_stats,
        calculate_per_label_metrics,
        calculate_macro_f1,
        calculate_macro_precision,
        calculate_macro_recall,
        build_confusion_matrix,
        get_all_labels,
        get_truth_labels,
    )
    from semantic_detector.io.artifact_manager import clean_command_artifacts

    # 检查预测文件是否存在
    if not os.path.exists(args.predictions_file):
        print(f"错误: 预测文件不存在: {args.predictions_file}", file=sys.stderr)
        return 2

    # 检查真值文件是否存在
    if not os.path.exists(args.ground_truth_file):
        print(f"错误: 真值文件不存在: {args.ground_truth_file}", file=sys.stderr)
        return 2

    # R417：提前确定输出目录并清理旧产物（补齐阶段 C 遗漏）
    # 确保即使 align/指标计算失败，旧 metrics.json/errors.jsonl 也不会残留
    _output_dir = Path(args.predictions_file).parent
    clean_command_artifacts(str(_output_dir), "evaluate")
    
    # 读取预测结果（R261：优先用真实 SemanticPrediction importer，
    # 向后兼容旧 DetectorEvidence 格式：旧格式缺 run_id 等键触发 KeyError 时回退）
    try:
        try:
            predictions = read_semantic_predictions_from_jsonl(args.predictions_file)
        except KeyError:
            predictions = read_predictions_from_jsonl(args.predictions_file)
    except Exception as e:
        print(f"错误: 读取预测文件失败: {e}", file=sys.stderr)
        return 1
    
    # 读取真值
    try:
        truths, rejected_truths = read_ground_truth_jsonl(args.ground_truth_file)
        truths, rejected_validation = validate_ground_truth(truths)
    except Exception as e:
        print(f"错误: 读取真值文件失败: {e}", file=sys.stderr)
        return 1

    # R336：合并 read/validate 两阶段拒绝记录并导出 rejected_ground_truth.jsonl
    # 无论评价是否继续，都写入当前评价目录；无拒绝时写空文件防止旧文件残留
    rejected_ground_truth = list(rejected_truths) + list(rejected_validation)
    predictions_path_for_dir = Path(args.predictions_file)
    output_dir_for_rejected = predictions_path_for_dir.parent
    rejected_path = output_dir_for_rejected / "rejected_ground_truth.jsonl"
    export_rejected_records(rejected_ground_truth, str(rejected_path))
    rejected_ground_truth_count = len(rejected_ground_truth)
    if rejected_ground_truth_count > 0:
        print(f"导出 {rejected_ground_truth_count} 个被拒绝的 Ground Truth 到 {rejected_path}")
    
    # 对齐预测和真值（R262：移除固定 default/request，R252 已改为从预测对象提取完整 FieldKey）
    aligned_pairs, unmatched_predictions, unmatched_truths = align_predictions_with_truth(
        predictions, truths
    )
    
    # 计算指标
    overall_accuracy = calculate_overall_accuracy(aligned_pairs, unmatched_truths)
    coverage = calculate_coverage(aligned_pairs, unmatched_truths)
    unknown_rate = calculate_unknown_rate(aligned_pairs, unmatched_truths)
    covered_accuracy = calculate_covered_accuracy(aligned_pairs)
    fine_top1_accuracy = calculate_fine_top1_accuracy(aligned_pairs)
    
    # 计算每标签统计
    label_stats = calculate_per_label_stats(aligned_pairs, unmatched_truths)
    label_metrics = calculate_per_label_metrics(label_stats)

    # 计算宏平均（R257：仅按 truth 出现的标签等权）
    truth_labels = get_truth_labels(aligned_pairs, unmatched_truths)
    macro_f1 = calculate_macro_f1(label_metrics, truth_labels)
    macro_precision = calculate_macro_precision(label_metrics, truth_labels)
    macro_recall = calculate_macro_recall(label_metrics, truth_labels)
    
    # 构建混淆矩阵
    labels = get_all_labels(aligned_pairs, unmatched_truths)
    confusion_matrix = build_confusion_matrix(aligned_pairs, unmatched_truths, labels)
    
    # 收集错误（R259：四类错误，传入 unmatched_predictions 收集 unexpected_prediction）
    errors = collect_errors(aligned_pairs, unmatched_truths, unmatched_predictions)
    
    # 确定输出目录
    predictions_path = Path(args.predictions_file)
    output_dir = predictions_path.parent
    
    # 导出 metrics.json（R260：含 counts 计数字段，导出再解析后指标与计数一致）
    counts = {
        'total_predictions': len(predictions),
        'total_truths': len(truths),
        'matched_count': len(aligned_pairs),
        'unmatched_truths_count': len(unmatched_truths),
        'unmatched_predictions_count': len(unmatched_predictions),
        'error_count': len(errors),
        'rejected_ground_truth_count': rejected_ground_truth_count,
    }
    metrics = build_metrics_dict(
        overall_accuracy=overall_accuracy,
        coverage=coverage,
        unknown_rate=unknown_rate,
        covered_accuracy=covered_accuracy,
        fine_top1_accuracy=fine_top1_accuracy,
        macro_f1=macro_f1,
        macro_precision=macro_precision,
        macro_recall=macro_recall,
        counts=counts
    )
    # R337/R338：fail closed + 显式 partial 模式
    # - 无拒绝：status=ok, valid_for_reporting=true
    # - 有拒绝 + 无 --allow-partial-ground-truth：status=invalid_ground_truth, valid_for_reporting=false
    # - 有拒绝 + 有 --allow-partial-ground-truth 且有合法子集：status=partial_ground_truth,
    #   valid_for_reporting=false, partial_ground_truth=true，继续评价合法子集
    # - 有拒绝 + 有 --allow-partial-ground-truth 但全部真值无效：status=invalid_ground_truth,
    #   valid_for_reporting=false（即使 partial 也失败）
    allow_partial = getattr(args, 'allow_partial_ground_truth', False)
    if rejected_ground_truth_count > 0:
        if allow_partial and len(truths) > 0:
            metrics['status'] = 'partial_ground_truth'
            metrics['valid_for_reporting'] = False
            metrics['partial_ground_truth'] = True
        else:
            metrics['status'] = 'invalid_ground_truth'
            metrics['valid_for_reporting'] = False
    else:
        metrics['status'] = 'ok'
        metrics['valid_for_reporting'] = True
    metrics_path = output_dir / "metrics.json"
    export_metrics_to_json(metrics, str(metrics_path))
    print(f"导出指标到 {metrics_path}")

    # 导出 per_label_metrics.csv（R260：含 tp/fp/fn 计数列）
    per_label_path = output_dir / "per_label_metrics.csv"
    export_per_label_metrics_to_csv(label_metrics, str(per_label_path), label_stats)
    print(f"导出每标签指标到 {per_label_path}")
    
    # 导出 confusion_matrix.csv
    confusion_path = output_dir / "confusion_matrix.csv"
    export_confusion_matrix_to_csv(confusion_matrix, str(confusion_path))
    print(f"导出混淆矩阵到 {confusion_path}")
    
    # R339：无条件导出 errors.jsonl（空列表时写空文件，防止旧产物残留）
    errors_path = output_dir / "errors.jsonl"
    export_errors_to_jsonl(errors, str(errors_path))
    if errors:
        print(f"导出 {len(errors)} 个错误到 {errors_path}")
    else:
        print(f"错误数: 0，{errors_path} 已重写为空文件")
    
    # 打印摘要
    print("\n评估结果摘要:")
    print(f"  总体准确率: {overall_accuracy:.4f}")
    print(f"  覆盖率: {coverage:.4f}")
    print(f"  Unknown 比率: {unknown_rate:.4f}")
    print(f"  覆盖准确率: {covered_accuracy:.4f}")
    if fine_top1_accuracy > 0:
        print(f"  Fine top-1 准确率: {fine_top1_accuracy:.4f}")
    print(f"  Macro F1: {macro_f1:.4f}")
    print(f"  总预测数: {len(predictions)}")
    print(f"  总真值数: {len(truths)}")
    print(f"  匹配数: {len(aligned_pairs)}")
    print(f"  错误数: {len(errors)}")
    if rejected_ground_truth_count > 0:
        print(f"  被拒绝的 Ground Truth: {rejected_ground_truth_count}")

    # R337/R338：fail closed + 显式 partial 模式
    # - 无拒绝：return 0
    # - 有拒绝 + 无 --allow-partial-ground-truth：return 1（fail closed）
    # - 有拒绝 + 有 --allow-partial-ground-truth 且有合法真值子集：return 0（partial 模式继续评价）
    # - 有拒绝 + 有 --allow-partial-ground-truth 但全部真值无效：return 1（即使 partial 也失败）
    if rejected_ground_truth_count > 0:
        if allow_partial and len(truths) > 0:
            print(
                f"\n注意: 检测到 {rejected_ground_truth_count} 个被拒绝的 Ground Truth，"
                f"已启用 --allow-partial-ground-truth，对 {len(truths)} 条合法真值继续评价。"
                f"metrics 标记为 partial_ground_truth（valid_for_reporting=false）。",
                file=sys.stderr,
            )
            return 0
        else:
            reason = (
                "全部 Ground Truth 无效" if len(truths) == 0
                else "未启用 --allow-partial-ground-truth"
            )
            print(
                f"\n警告: 检测到 {rejected_ground_truth_count} 个被拒绝的 Ground Truth（{reason}），"
                f"评价结果标记为 {metrics['status']}（valid_for_reporting=false）。",
                file=sys.stderr,
            )
            return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
