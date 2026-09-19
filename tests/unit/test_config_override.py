"""R085+R086: 用户配置覆盖测试"""

from pathlib import Path
import json
import pytest

from semantic_detector.config import Config, load_config_with_override


class TestConfigOverride:
    """R085: 测试用户配置覆盖默认配置"""
    
    def test_override_min_samples(self, tmp_path):
        """覆盖 min_samples"""
        # 创建用户配置文件
        user_config = {"min_samples": 16}
        user_config_path = tmp_path / "user_config.json"
        with open(user_config_path, 'w', encoding='utf-8') as f:
            json.dump(user_config, f)
        
        # 加载配置
        config = load_config_with_override(user_config_path)
        
        # 验证覆盖的值
        assert config.min_samples == 16
        # 验证未覆盖的值保持默认
        assert config.constant_support == 0.98
        assert config.length_support == 0.90
    
    def test_override_constant_support(self, tmp_path):
        """覆盖 constant_support"""
        user_config = {"constant_support": 0.95}
        user_config_path = tmp_path / "user_config.json"
        with open(user_config_path, 'w', encoding='utf-8') as f:
            json.dump(user_config, f)
        
        config = load_config_with_override(user_config_path)
        
        assert config.constant_support == 0.95
        assert config.min_samples == 8  # 默认值
    
    def test_override_multiple_fields(self, tmp_path):
        """覆盖多个字段"""
        user_config = {
            "min_samples": 10,
            "constant_support": 0.95,
            "length_support": 0.85
        }
        user_config_path = tmp_path / "user_config.json"
        with open(user_config_path, 'w', encoding='utf-8') as f:
            json.dump(user_config, f)
        
        config = load_config_with_override(user_config_path)
        
        assert config.min_samples == 10
        assert config.constant_support == 0.95
        assert config.length_support == 0.85
        # 未覆盖的值保持默认
        assert config.timestamp_support == 0.90
    
    def test_override_all_threshold_fields(self, tmp_path):
        """覆盖所有阈值字段"""
        user_config = {
            "constant_support": 0.99,
            "length_support": 0.95,
            "timestamp_support": 0.95,
            "sequence_unique_ratio": 0.75,
            "sequence_increasing_ratio": 0.85,
            "string_printable_ratio": 0.90,
            "string_nonempty_ratio": 0.85,
            "identifier_unique_ratio": 0.85,
            "identifier_score_cap": 0.75,
            "payload_entropy_threshold": 0.75,
            "ambiguity_margin": 0.10
        }
        user_config_path = tmp_path / "user_config.json"
        with open(user_config_path, 'w', encoding='utf-8') as f:
            json.dump(user_config, f)
        
        config = load_config_with_override(user_config_path)
        
        assert config.constant_support == 0.99
        assert config.length_support == 0.95
        assert config.timestamp_support == 0.95
        assert config.ambiguity_margin == 0.10
    
    def test_empty_user_config_keeps_defaults(self, tmp_path):
        """空用户配置保持所有默认值"""
        user_config = {}
        user_config_path = tmp_path / "user_config.json"
        with open(user_config_path, 'w', encoding='utf-8') as f:
            json.dump(user_config, f)
        
        config = load_config_with_override(user_config_path)
        
        # 所有值都是默认值
        assert config.min_samples == 8
        assert config.constant_support == 0.98
        assert config.length_support == 0.90


class TestConfigUnknownKey:
    """R086: 测试配置未知 key 拒绝"""
    
    def test_unknown_key_ignored(self, tmp_path):
        """未知 key 被忽略（不报错，但不影响配置）"""
        user_config = {
            "min_samples": 16,
            "unknown_key": "some_value"
        }
        user_config_path = tmp_path / "user_config.json"
        with open(user_config_path, 'w', encoding='utf-8') as f:
            json.dump(user_config, f)
        
        config = load_config_with_override(user_config_path)
        
        # 已知的 key 生效
        assert config.min_samples == 16
        # 未知的 key 不影响配置（没有对应的属性）
        assert not hasattr(config, 'unknown_key')
    
    def test_misspelled_key_ignored(self, tmp_path):
        """拼错的 key 被忽略"""
        user_config = {
            "min_sampels": 16  # 拼写错误
        }
        user_config_path = tmp_path / "user_config.json"
        with open(user_config_path, 'w', encoding='utf-8') as f:
            json.dump(user_config, f)
        
        config = load_config_with_override(user_config_path)
        
        # 拼错的 key 不生效，保持默认值
        assert config.min_samples == 8
    
    def test_multiple_unknown_keys_ignored(self, tmp_path):
        """多个未知 key 都被忽略"""
        user_config = {
            "min_samples": 20,
            "unknown1": 100,
            "unknown2": "test",
            "unknown3": 0.5
        }
        user_config_path = tmp_path / "user_config.json"
        with open(user_config_path, 'w', encoding='utf-8') as f:
            json.dump(user_config, f)

        config = load_config_with_override(user_config_path)

        # 只有已知的 key 生效
        assert config.min_samples == 20
        assert config.constant_support == 0.98  # 默认值


class TestCliConfigLoadingR354:
    """R354: CLI --config 参数加载测试

    计划 L1029-1034 要求：
    - 路径不存在、JSON 损坏、类型非法时 exit 非零
    - 通过 _load_config_from_args 辅助函数加载
    """

    def test_load_config_with_nonexistent_path_returns_nonzero(self, tmp_path):
        """--config 指向不存在的路径时 exit 非零"""
        from semantic_detector.cli import main

        nonexistent = tmp_path / "nonexistent.json"
        # 构造一个有效的输入文件避免被输入校验拦截
        input_file = tmp_path / "input.jsonl"
        input_file.write_text(
            '{"message_id": 1, "layout_id": "test", "direction": "request", '
            '"payload_hex": "01", "fields": [{"field_index": 0, "start": 0, "end": 1}]}\n',
            encoding='utf-8',
        )

        rc = main([
            'profile', str(input_file),
            '--config', str(nonexistent),
            '--output-dir', str(tmp_path / 'out'),
        ])
        assert rc != 0, "--config 指向不存在的路径应 exit 非零"

    def test_load_config_with_corrupted_json_returns_nonzero(self, tmp_path):
        """--config 指向 JSON 损坏文件时 exit 非零"""
        from semantic_detector.cli import main

        bad_config = tmp_path / "bad.json"
        bad_config.write_text("{ this is not valid json", encoding='utf-8')

        input_file = tmp_path / "input.jsonl"
        input_file.write_text(
            '{"message_id": 1, "layout_id": "test", "direction": "request", '
            '"payload_hex": "01", "fields": [{"field_index": 0, "start": 0, "end": 1}]}\n',
            encoding='utf-8',
        )

        rc = main([
            'profile', str(input_file),
            '--config', str(bad_config),
            '--output-dir', str(tmp_path / 'out'),
        ])
        assert rc != 0, "--config 指向损坏 JSON 应 exit 非零"

    def test_load_config_with_invalid_type_returns_nonzero(self, tmp_path):
        """--config 指向类型非法的配置时 exit 非零"""
        from semantic_detector.cli import main

        # min_samples 应为正整数，这里传字符串触发 TypeError
        bad_config = tmp_path / "bad_type.json"
        with open(bad_config, 'w', encoding='utf-8') as f:
            json.dump({"min_samples": "not_an_int"}, f)

        input_file = tmp_path / "input.jsonl"
        input_file.write_text(
            '{"message_id": 1, "layout_id": "test", "direction": "request", '
            '"payload_hex": "01", "fields": [{"field_index": 0, "start": 0, "end": 1}]}\n',
            encoding='utf-8',
        )

        rc = main([
            'profile', str(input_file),
            '--config', str(bad_config),
            '--output-dir', str(tmp_path / 'out'),
        ])
        assert rc != 0, "--config 类型非法应 exit 非零"

    def test_load_config_with_out_of_range_value_returns_nonzero(self, tmp_path):
        """--config 指向值越界的配置时 exit 非零"""
        from semantic_detector.cli import main

        # constant_support 应在 0~1 范围内，这里传 1.5 触发 ValueError
        bad_config = tmp_path / "bad_range.json"
        with open(bad_config, 'w', encoding='utf-8') as f:
            json.dump({"constant_support": 1.5}, f)

        input_file = tmp_path / "input.jsonl"
        input_file.write_text(
            '{"message_id": 1, "layout_id": "test", "direction": "request", '
            '"payload_hex": "01", "fields": [{"field_index": 0, "start": 0, "end": 1}]}\n',
            encoding='utf-8',
        )

        rc = main([
            'profile', str(input_file),
            '--config', str(bad_config),
            '--output-dir', str(tmp_path / 'out'),
        ])
        assert rc != 0, "--config 值越界应 exit 非零"

    def test_load_config_with_valid_user_config_succeeds(self, tmp_path):
        """--config 指向有效用户配置时成功执行"""
        from semantic_detector.cli import main

        # 构造有效用户配置（覆盖 min_samples）
        user_config = tmp_path / "user.json"
        with open(user_config, 'w', encoding='utf-8') as f:
            json.dump({"min_samples": 5}, f)

        # 使用 examples/messages.jsonl（至少 8 条记录才能触发 min_samples=8）
        messages_path = Path("examples/messages.jsonl")
        if not messages_path.exists():
            pytest.skip("examples/messages.jsonl not found")

        output_dir = tmp_path / "out"
        rc = main([
            'profile', str(messages_path),
            '--config', str(user_config),
            '--output-dir', str(output_dir),
        ])
        assert rc == 0, "--config 指向有效用户配置应成功"

        # 验证产生了 field_profiles.jsonl
        assert (output_dir / "field_profiles.jsonl").exists()

    def test_load_config_default_when_not_specified(self, tmp_path):
        """未指定 --config 时使用默认 config/defaults.json"""
        from semantic_detector.cli import _load_config_from_args

        # 构造一个 Namespace 模拟未指定 --config
        import argparse
        args = argparse.Namespace(config=None)

        config = _load_config_from_args(args)
        # 验证默认值与 config/defaults.json 一致
        assert config.min_samples == 8
        assert config.constant_support == 0.98
        assert config.length_support == 0.90

    def test_load_config_with_explicit_user_config(self, tmp_path):
        """_load_config_from_args 使用显式用户配置覆盖默认值"""
        from semantic_detector.cli import _load_config_from_args

        import argparse
        user_config = tmp_path / "user.json"
        with open(user_config, 'w', encoding='utf-8') as f:
            json.dump({"min_samples": 16, "constant_support": 0.95}, f)

        args = argparse.Namespace(config=str(user_config))
        config = _load_config_from_args(args)

        assert config.min_samples == 16
        assert config.constant_support == 0.95
        # 未覆盖的字段保持默认
        assert config.length_support == 0.90
