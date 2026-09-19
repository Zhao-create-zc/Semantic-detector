# Contributing

感谢你对 Semantic Detector 的关注。欢迎提交 bug 修复、测试、文档改进，以及对二进制协议字段语义检测规则的可复现实验。

## 开发环境

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -e .
pip install -r requirements.txt
python -m pytest -q
```

## 提交要求

- 新增或修改检测逻辑时，请同时增加相应测试。
- 不要提交真实敏感流量、账号凭据、私钥、Token 或受限制的数据集。
- 保持输入/输出契约向后兼容；若必须变更，请同步更新 `docs/DATA_CONTRACT.md`。
- 涉及第三方代码时，必须保留来源和许可证声明。

## Pull Request

PR 描述应说明：问题、修改方法、验证方式，以及是否影响数据契约或语义标签体系。
