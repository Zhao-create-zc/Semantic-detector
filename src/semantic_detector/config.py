"""配置模块"""

import hashlib
import json
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Optional


@dataclass
class Config:
    """配置数据类"""

    min_samples: int = 8
    constant_support: float = 0.98
    length_support: float = 0.90
    timestamp_support: float = 0.90
    timestamp_slop_seconds: int = 86400
    sequence_unique_ratio: float = 0.70
    sequence_increasing_ratio: float = 0.80
    string_printable_ratio: float = 0.85
    string_nonempty_ratio: float = 0.80
    identifier_unique_ratio: float = 0.80
    identifier_score_cap: float = 0.70
    payload_entropy_threshold: float = 0.70
    ambiguity_margin: float = 0.08
    type_opcode_min_dominant_ratio: float = 0.50
    resolver_min_score: float = 0.5

    def __post_init__(self):
        """验证配置参数"""
        # 验证 min_samples 为正整数
        if self.min_samples <= 0:
            raise ValueError(f"min_samples must be positive, got {self.min_samples}")

        # 验证 timestamp_slop_seconds 为正整数
        if self.timestamp_slop_seconds <= 0:
            raise ValueError(f"timestamp_slop_seconds must be positive, got {self.timestamp_slop_seconds}")

        # 验证所有阈值字段在 0~1 范围内
        threshold_fields = [
            ('constant_support', self.constant_support),
            ('length_support', self.length_support),
            ('timestamp_support', self.timestamp_support),
            ('sequence_unique_ratio', self.sequence_unique_ratio),
            ('sequence_increasing_ratio', self.sequence_increasing_ratio),
            ('string_printable_ratio', self.string_printable_ratio),
            ('string_nonempty_ratio', self.string_nonempty_ratio),
            ('identifier_unique_ratio', self.identifier_unique_ratio),
            ('identifier_score_cap', self.identifier_score_cap),
            ('payload_entropy_threshold', self.payload_entropy_threshold),
            ('ambiguity_margin', self.ambiguity_margin),
            ('type_opcode_min_dominant_ratio', self.type_opcode_min_dominant_ratio),
            ('resolver_min_score', self.resolver_min_score),
        ]

        for field_name, value in threshold_fields:
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{field_name} must be between 0.0 and 1.0, got {value}")

    def to_dict(self) -> dict:
        """R359：生成稳定的配置字典（字段顺序固定，用于 manifest 和哈希）

        Returns:
            按 dataclass 字段定义顺序排列的字典
        """
        return {f.name: getattr(self, f.name) for f in fields(self)}

    def sha256(self) -> str:
        """R359：生成配置的稳定 SHA256 哈希

        将 to_dict() 序列化为 JSON（sort_keys=True 保证键顺序稳定），
        然后计算 SHA256 十六进制摘要。

        Returns:
            64 字符的十六进制 SHA256 摘要
        """
        payload = json.dumps(self.to_dict(), sort_keys=True).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


def load_default_config(config_path: Optional[Path] = None) -> Config:
    """加载默认配置
    
    Args:
        config_path: 配置文件路径，默认为 config/defaults.json
        
    Returns:
        Config 对象
    """
    if config_path is None:
        # 默认配置文件路径
        # config.py 位于 src/semantic_detector/config.py
        # 需要向上 3 级到项目根目录，然后进入 config/defaults.json
        config_path = Path(__file__).parent.parent.parent / "config" / "defaults.json"
    
    with open(config_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return Config(**data)


def load_config_with_override(user_config_path: Path) -> Config:
    """加载用户配置并覆盖默认配置
    
    Args:
        user_config_path: 用户配置文件路径
        
    Returns:
        合并后的 Config 对象
    """
    # 加载默认配置
    default_config = load_default_config()
    
    # 加载用户配置
    with open(user_config_path, 'r', encoding='utf-8') as f:
        user_data = json.load(f)
    
    # 获取默认配置的所有字段
    default_dict = {
        'min_samples': default_config.min_samples,
        'constant_support': default_config.constant_support,
        'length_support': default_config.length_support,
        'timestamp_support': default_config.timestamp_support,
        'timestamp_slop_seconds': default_config.timestamp_slop_seconds,
        'sequence_unique_ratio': default_config.sequence_unique_ratio,
        'sequence_increasing_ratio': default_config.sequence_increasing_ratio,
        'string_printable_ratio': default_config.string_printable_ratio,
        'string_nonempty_ratio': default_config.string_nonempty_ratio,
        'identifier_unique_ratio': default_config.identifier_unique_ratio,
        'identifier_score_cap': default_config.identifier_score_cap,
        'payload_entropy_threshold': default_config.payload_entropy_threshold,
        'ambiguity_margin': default_config.ambiguity_margin,
        'type_opcode_min_dominant_ratio': default_config.type_opcode_min_dominant_ratio,
        'resolver_min_score': default_config.resolver_min_score,
    }
    
    # 用用户配置覆盖默认配置
    for key, value in user_data.items():
        if key in default_dict:
            default_dict[key] = value
    
    return Config(**default_dict)
