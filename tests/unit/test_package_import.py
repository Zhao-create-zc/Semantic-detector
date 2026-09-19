"""测试包导入功能"""


def test_package_import():
    """测试 semantic_detector 包可以正常导入"""
    import semantic_detector
    assert hasattr(semantic_detector, "__version__")
    assert semantic_detector.__version__ == "0.1.0"


def test_package_has_version():
    """测试包有版本号"""
    import semantic_detector
    assert isinstance(semantic_detector.__version__, str)