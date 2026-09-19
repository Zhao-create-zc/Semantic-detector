"""检测器模块"""

from typing import Dict, List
from semantic_detector.detectors.base import Detector


class DetectorRegistry:
    """检测器注册表
    
    管理所有检测器的注册和访问，保持注册顺序。
    """
    
    def __init__(self):
        self._detectors: Dict[str, Detector] = {}
        self._order: List[str] = []
    
    def register(self, detector: Detector) -> None:
        """注册检测器
        
        Args:
            detector: 要注册的检测器
            
        Raises:
            ValueError: 如果检测器名称已存在
        """
        if detector.name in self._detectors:
            raise ValueError(f"Detector '{detector.name}' already registered")
        
        self._detectors[detector.name] = detector
        self._order.append(detector.name)
    
    def get(self, name: str) -> Detector:
        """获取检测器
        
        Args:
            name: 检测器名称
            
        Returns:
            检测器实例
            
        Raises:
            KeyError: 如果检测器不存在
        """
        if name not in self._detectors:
            raise KeyError(f"Detector '{name}' not found")
        return self._detectors[name]
    
    def list_names(self) -> List[str]:
        """列出所有检测器名称（按注册顺序）
        
        Returns:
            检测器名称列表
        """
        return self._order.copy()
    
    def list_detectors(self) -> List[Detector]:
        """列出所有检测器（按注册顺序）
        
        Returns:
            检测器实例列表
        """
        return [self._detectors[name] for name in self._order]
    
    def count(self) -> int:
        """返回已注册检测器数量
        
        Returns:
            检测器数量
        """
        return len(self._detectors)


# 全局注册表实例
_registry = DetectorRegistry()


def register_detector(detector: Detector) -> None:
    """注册检测器到全局注册表
    
    Args:
        detector: 要注册的检测器
    """
    _registry.register(detector)


def get_detector(name: str) -> Detector:
    """从全局注册表获取检测器
    
    Args:
        name: 检测器名称
        
    Returns:
        检测器实例
    """
    return _registry.get(name)


def list_detectors() -> List[Detector]:
    """列出全局注册表中的所有检测器
    
    Returns:
        检测器实例列表
    """
    return _registry.list_detectors()


def clear_registry() -> None:
    """清空全局注册表（仅用于测试）"""
    global _registry
    _registry = DetectorRegistry()


def register_all_detectors() -> None:
    """注册所有检测器

    按固定顺序注册检测器：
    1. constant - 常量检测器
    2. length - 长度检测器
    3. timestamp - 时间戳检测器
    4. sequence - 序列检测器
    5. string - 字符串检测器
    6. identifier - 标识符检测器
    7. payload - 载荷检测器
    8. type_opcode - 类型/操作码检测器
    """
    from semantic_detector.config import Config
    # R355：未传 config 时用默认 Config（向后兼容）
    config = Config()
    register_all_detectors_with_config(config)


def register_all_detectors_with_config(config) -> None:
    """R355：用指定 Config 实例注册所有检测器

    所有检测器引用同一配置快照，禁止每个检测器内部再 Config()。

    Args:
        config: Config 实例（所有检测器共享）
    """
    from semantic_detector.detectors.constant import ConstantDetector
    from semantic_detector.detectors.length import LengthDetector
    from semantic_detector.detectors.timestamp import TimestampDetector
    from semantic_detector.detectors.sequence import SequenceDetector
    from semantic_detector.detectors.string import StringDetector
    from semantic_detector.detectors.identifier import IdentifierDetector
    from semantic_detector.detectors.payload import PayloadDetector
    from semantic_detector.detectors.type_opcode import TypeOpcodeDetector

    # 按固定顺序注册（所有检测器共享同一 config）
    register_detector(ConstantDetector(config))
    register_detector(LengthDetector(config))
    register_detector(TimestampDetector(config))
    register_detector(SequenceDetector(config))
    register_detector(StringDetector(config))
    register_detector(IdentifierDetector(config))
    register_detector(PayloadDetector(config))
    register_detector(TypeOpcodeDetector())


__all__ = [
    'Detector',
    'DetectorRegistry',
    'register_detector',
    'get_detector',
    'list_detectors',
    'clear_registry',
    'register_all_detectors',
    'register_all_detectors_with_config',
]
