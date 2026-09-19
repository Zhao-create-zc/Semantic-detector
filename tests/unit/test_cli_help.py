"""测试 CLI --help

验证 argparse CLI 骨架和 --help 功能。
"""

import pytest
from semantic_detector.cli import create_parser, main


class TestCliHelp:
    """CLI --help 测试"""
    
    def test_help_exits_zero(self):
        """测试 --help 退出码为 0"""
        with pytest.raises(SystemExit) as exc_info:
            main(['--help'])
        assert exc_info.value.code == 0
    
    def test_help_lists_subcommands(self, capsys):
        """测试 --help 列出子命令"""
        parser = create_parser()
        parser.print_help()
        captured = capsys.readouterr()
        
        # 验证子命令被列出
        assert 'validate' in captured.out
        assert 'profile' in captured.out
        assert 'infer' in captured.out
        assert 'run' in captured.out
        assert 'evaluate' in captured.out
    
    def test_no_command_shows_help(self, capsys):
        """测试无子命令时显示帮助"""
        exit_code = main([])
        assert exit_code == 0
        
        captured = capsys.readouterr()
        assert 'validate' in captured.out
        assert 'profile' in captured.out
    
    def test_validate_help(self, capsys):
        """测试 validate --help"""
        with pytest.raises(SystemExit) as exc_info:
            main(['validate', '--help'])
        assert exc_info.value.code == 0
        
        captured = capsys.readouterr()
        assert 'input_file' in captured.out
    
    def test_profile_help(self, capsys):
        """测试 profile --help"""
        with pytest.raises(SystemExit) as exc_info:
            main(['profile', '--help'])
        assert exc_info.value.code == 0
        
        captured = capsys.readouterr()
        assert 'input_file' in captured.out
    
    def test_infer_help(self, capsys):
        """测试 infer --help"""
        with pytest.raises(SystemExit) as exc_info:
            main(['infer', '--help'])
        assert exc_info.value.code == 0
        
        captured = capsys.readouterr()
        assert 'input_file' in captured.out
    
    def test_run_help(self, capsys):
        """测试 run --help"""
        with pytest.raises(SystemExit) as exc_info:
            main(['run', '--help'])
        assert exc_info.value.code == 0
        
        captured = capsys.readouterr()
        assert 'input_file' in captured.out
    
    def test_evaluate_help(self, capsys):
        """测试 evaluate --help"""
        with pytest.raises(SystemExit) as exc_info:
            main(['evaluate', '--help'])
        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        assert 'predictions_file' in captured.out


class TestCliConfigOptionR354:
    """R354: CLI 统一 --config 参数测试

    验证 profile/infer/run 三个子命令都接受 --config 参数。
    计划 L1015-1034 要求：
    - --config PATH
    - 默认使用 config/defaults.json 或内建等价值
    - 路径不存在、JSON 损坏、类型非法时 exit 非零
    - validate 是否使用配置需明确，不应伪装使用
    """

    def test_profile_accepts_config_option(self):
        """profile 子命令接受 --config 参数"""
        parser = create_parser()
        args = parser.parse_args(['profile', 'input.jsonl', '--config', 'my_config.json'])
        assert args.command == 'profile'
        assert args.config == 'my_config.json'

    def test_infer_accepts_config_option(self):
        """infer 子命令接受 --config 参数"""
        parser = create_parser()
        args = parser.parse_args(['infer', 'profiles.jsonl', '--config', 'my_config.json'])
        assert args.command == 'infer'
        assert args.config == 'my_config.json'

    def test_run_accepts_config_option(self):
        """run 子命令接受 --config 参数"""
        parser = create_parser()
        args = parser.parse_args(['run', 'input.jsonl', '--config', 'my_config.json'])
        assert args.command == 'run'
        assert args.config == 'my_config.json'

    def test_profile_config_defaults_to_none(self):
        """profile 未指定 --config 时 args.config 为 None"""
        parser = create_parser()
        args = parser.parse_args(['profile', 'input.jsonl'])
        assert args.config is None

    def test_infer_config_defaults_to_none(self):
        """infer 未指定 --config 时 args.config 为 None"""
        parser = create_parser()
        args = parser.parse_args(['infer', 'profiles.jsonl'])
        assert args.config is None

    def test_run_config_defaults_to_none(self):
        """run 未指定 --config 时 args.config 为 None"""
        parser = create_parser()
        args = parser.parse_args(['run', 'input.jsonl'])
        assert args.config is None

    def test_validate_does_not_have_config_option(self):
        """validate 子命令不支持 --config（validate 只做 JSON/组级校验，不使用检测器阈值）

        计划 L1034: "validate 是否使用配置需明确，不应伪装使用"
        validate 不调用检测器，因此不接收 --config 参数
        """
        parser = create_parser()
        args = parser.parse_args(['validate', 'input.jsonl'])
        assert not hasattr(args, 'config') or args.config is None

    def test_evaluate_does_not_have_config_option(self):
        """evaluate 子命令不支持 --config（evaluate 评估预测 vs 真值，不调用检测器）"""
        parser = create_parser()
        args = parser.parse_args(['evaluate', 'preds.jsonl', 'truth.jsonl'])
        assert not hasattr(args, 'config') or args.config is None

    def test_profile_help_shows_config_option(self, capsys):
        """profile --help 显示 --config 选项"""
        with pytest.raises(SystemExit) as exc_info:
            main(['profile', '--help'])
        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        assert '--config' in captured.out

    def test_infer_help_shows_config_option(self, capsys):
        """infer --help 显示 --config 选项"""
        with pytest.raises(SystemExit) as exc_info:
            main(['infer', '--help'])
        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        assert '--config' in captured.out

    def test_run_help_shows_config_option(self, capsys):
        """run --help 显示 --config 选项"""
        with pytest.raises(SystemExit) as exc_info:
            main(['run', '--help'])
        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        assert '--config' in captured.out
