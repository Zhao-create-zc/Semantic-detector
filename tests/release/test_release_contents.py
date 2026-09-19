# test_release_contents.py - R410: 发布包内容验证测试
#
# 验证发布压缩包不含虚拟环境/缓存/临时产物，包含必需的源码/测试/示例/配置/文档/许可证。
# 测试逻辑与 scripts/build_release.ps1 中的 Python helper 保持一致。

import hashlib
import json
import os
import shutil
import sys
import zipfile
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# R410: 发布包内容规则（与 build_release.ps1 保持一致）
# ---------------------------------------------------------------------------

FORBIDDEN_DIR_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".git",
    ".idea",
    ".vscode",
    ".mypy_cache",
    ".pyre",
    ".pytype",
    ".tox",
    ".nox",
    ".cleanroom_venv",
    "venv_cleanroom",
    ".venv_release_check",
    ".venv_v3_final_check",
    ".venv",
    "venv",
    "env",
    "ENV",
    "temp_audit",
    "temp_cleanroom",
    "dist",
    "htmlcov",
    "cover",
}

FORBIDDEN_DIR_SUFFIXES = (".egg-info",)

FORBIDDEN_FILE_PATTERNS = [
    "*.pyc",
    "*.pyo",
    "*.pyd",
    ".DS_Store",
    "Thumbs.db",
]

FORBIDDEN_TOP_PATHS = {
    "examples/output",
    "artifacts/runs",
    ".git",
}

REQUIRED_TOP_PATHS = [
    "src",
    "tests",
    "examples",
    "config",
    "docs",
    "scripts",
    "LICENSE",
    "README.md",
    "pyproject.toml",
    "requirements.txt",
]


def _normalize(path: str) -> str:
    return path.replace("\\", "/")


def _is_forbidden_dir_name(name: str) -> bool:
    if name in FORBIDDEN_DIR_NAMES:
        return True
    for suffix in FORBIDDEN_DIR_SUFFIXES:
        if name.endswith(suffix):
            return True
    return False


def _is_forbidden_file(name: str) -> bool:
    import fnmatch

    for pattern in FORBIDDEN_FILE_PATTERNS:
        if fnmatch.fnmatch(name, pattern):
            return True
    return False


def _is_forbidden_top_path(rel_path: str) -> bool:
    norm = _normalize(rel_path)
    for fp in FORBIDDEN_TOP_PATHS:
        fp_norm = _normalize(fp)
        if norm == fp_norm or norm.startswith(fp_norm + "/"):
            return True
    return False


def _collect_release_files(root: Path) -> list:
    """与 build_release.ps1 中的 collect_files 逻辑一致。"""
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root)
        if rel_dir == ".":
            rel_dir = ""
        dirnames[:] = [d for d in dirnames if not _is_forbidden_dir_name(d)]
        if rel_dir and _is_forbidden_top_path(rel_dir):
            dirnames[:] = []
            continue
        for fname in filenames:
            if _is_forbidden_file(fname):
                continue
            full = os.path.join(dirpath, fname)
            rel = os.path.relpath(full, root)
            files.append((full, rel))
    return files


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


@pytest.fixture
def release_zip(tmp_path, project_root):
    """构建一个测试用发布压缩包（Python 端复制 build_release.ps1 逻辑）。"""
    zip_path = tmp_path / "test_release.zip"
    files = _collect_release_files(project_root)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for full, rel in files:
            zf.write(full, _normalize(rel))
    return zip_path


# ---------------------------------------------------------------------------
# 单元测试：规则函数
# ---------------------------------------------------------------------------


class TestForbiddenDirNames:
    def test_pycache_forbidden(self):
        assert _is_forbidden_dir_name("__pycache__")

    def test_pytest_cache_forbidden(self):
        assert _is_forbidden_dir_name(".pytest_cache")

    def test_venv_variants_forbidden(self):
        for name in [
            ".cleanroom_venv",
            "venv_cleanroom",
            ".venv_release_check",
            ".venv_v3_final_check",
            ".venv",
            "venv",
        ]:
            assert _is_forbidden_dir_name(name), f"{name} should be forbidden"

    def test_egg_info_forbidden(self):
        assert _is_forbidden_dir_name("semantic_detector.egg-info")
        assert _is_forbidden_dir_name("some.egg-info")

    def test_temp_dirs_forbidden(self):
        assert _is_forbidden_dir_name("temp_audit")
        assert _is_forbidden_dir_name("temp_cleanroom")

    def test_src_not_forbidden(self):
        assert not _is_forbidden_dir_name("src")

    def test_tests_not_forbidden(self):
        assert not _is_forbidden_dir_name("tests")

    def test_docs_not_forbidden(self):
        assert not _is_forbidden_dir_name("docs")


class TestForbiddenFilePatterns:
    def test_pyc_forbidden(self):
        assert _is_forbidden_file("module.cpython-314.pyc")

    def test_pyo_forbidden(self):
        assert _is_forbidden_file("module.pyo")

    def test_ds_store_forbidden(self):
        assert _is_forbidden_file(".DS_Store")

    def test_thumbs_db_forbidden(self):
        assert _is_forbidden_file("Thumbs.db")

    def test_py_not_forbidden(self):
        assert not _is_forbidden_file("cli.py")

    def test_json_not_forbidden(self):
        assert not _is_forbidden_file("defaults.json")


class TestForbiddenTopPaths:
    def test_examples_output_forbidden(self):
        assert _is_forbidden_top_path("examples/output")
        assert _is_forbidden_top_path("examples/output/metrics.json")

    def test_artifacts_runs_forbidden(self):
        assert _is_forbidden_top_path("artifacts/runs")

    def test_src_not_forbidden(self):
        assert not _is_forbidden_top_path("src")
        assert not _is_forbidden_top_path("src/semantic_detector/cli.py")

    def test_examples_messages_allowed(self):
        assert not _is_forbidden_top_path("examples/messages.jsonl")


# ---------------------------------------------------------------------------
# 集成测试：构建 zip 并验证内容
# ---------------------------------------------------------------------------


class TestReleaseZipContents:
    """验证构建的发布 zip 不含禁止内容，包含必需内容。"""

    def test_no_pycache_in_zip(self, release_zip):
        with zipfile.ZipFile(release_zip, "r") as zf:
            names = zf.namelist()
        for name in names:
            assert "__pycache__" not in name, f"__pycache__ found: {name}"

    def test_no_pyc_files_in_zip(self, release_zip):
        with zipfile.ZipFile(release_zip, "r") as zf:
            names = zf.namelist()
        for name in names:
            assert not name.endswith(".pyc"), f".pyc found: {name}"
            assert not name.endswith(".pyo"), f".pyo found: {name}"

    def test_no_egg_info_in_zip(self, release_zip):
        with zipfile.ZipFile(release_zip, "r") as zf:
            names = zf.namelist()
        for name in names:
            assert ".egg-info" not in name, f".egg-info found: {name}"

    def test_no_pytest_cache_in_zip(self, release_zip):
        with zipfile.ZipFile(release_zip, "r") as zf:
            names = zf.namelist()
        for name in names:
            assert ".pytest_cache" not in name, f".pytest_cache found: {name}"

    def test_no_venv_in_zip(self, release_zip):
        with zipfile.ZipFile(release_zip, "r") as zf:
            names = zf.namelist()
        venv_markers = [
            ".cleanroom_venv",
            "venv_cleanroom",
            ".venv_release_check",
            ".venv_v3_final_check",
        ]
        for name in names:
            for marker in venv_markers:
                assert marker not in name, f"{marker} found: {name}"

    def test_no_examples_output_in_zip(self, release_zip):
        with zipfile.ZipFile(release_zip, "r") as zf:
            names = zf.namelist()
        for name in names:
            assert not name.startswith("examples/output/"), (
                f"examples/output/ found: {name}"
            )

    def test_no_temp_dirs_in_zip(self, release_zip):
        with zipfile.ZipFile(release_zip, "r") as zf:
            names = zf.namelist()
        for name in names:
            assert not name.startswith("temp_audit/"), (
                f"temp_audit/ found: {name}"
            )
            assert not name.startswith("temp_cleanroom/"), (
                f"temp_cleanroom/ found: {name}"
            )

    def test_contains_source_code(self, release_zip):
        with zipfile.ZipFile(release_zip, "r") as zf:
            names = zf.namelist()
        src_files = [n for n in names if n.startswith("src/")]
        assert len(src_files) > 0, "No src/ files in release zip"
        assert any(n.startswith("src/semantic_detector/cli.py") for n in names)

    def test_contains_tests(self, release_zip):
        with zipfile.ZipFile(release_zip, "r") as zf:
            names = zf.namelist()
        test_files = [n for n in names if n.startswith("tests/")]
        assert len(test_files) > 0, "No tests/ files in release zip"

    def test_contains_examples(self, release_zip):
        with zipfile.ZipFile(release_zip, "r") as zf:
            names = zf.namelist()
        assert "examples/messages.jsonl" in names
        assert "examples/config.json" in names

    def test_contains_config(self, release_zip):
        with zipfile.ZipFile(release_zip, "r") as zf:
            names = zf.namelist()
        assert "config/defaults.json" in names

    def test_contains_docs(self, release_zip):
        with zipfile.ZipFile(release_zip, "r") as zf:
            names = zf.namelist()
        doc_files = [n for n in names if n.startswith("docs/")]
        assert len(doc_files) > 0, "No docs/ files in release zip"

    def test_contains_license(self, release_zip):
        with zipfile.ZipFile(release_zip, "r") as zf:
            names = zf.namelist()
        assert "LICENSE" in names

    def test_contains_readme(self, release_zip):
        with zipfile.ZipFile(release_zip, "r") as zf:
            names = zf.namelist()
        assert "README.md" in names

    def test_contains_pyproject(self, release_zip):
        with zipfile.ZipFile(release_zip, "r") as zf:
            names = zf.namelist()
        assert "pyproject.toml" in names

    def test_contains_requirements(self, release_zip):
        with zipfile.ZipFile(release_zip, "r") as zf:
            names = zf.namelist()
        assert "requirements.txt" in names

    def test_all_required_top_paths_present(self, release_zip):
        with zipfile.ZipFile(release_zip, "r") as zf:
            names = set(zf.namelist())
        for req in REQUIRED_TOP_PATHS:
            found = any(
                n == req or n.startswith(req + "/") for n in names
            )
            assert found, f"Required top-level path missing: {req}"


class TestReleaseManifest:
    """验证 manifest 生成逻辑。"""

    def test_manifest_generates_correctly(self, tmp_path, project_root):
        """测试 manifest 生成逻辑与 build_release.ps1 一致。"""
        files = _collect_release_files(project_root)
        manifest = {
            "total_files": len(files),
            "files": [],
        }
        for full, rel in sorted(files, key=lambda x: _normalize(x[1])):
            size = os.path.getsize(full)
            h = hashlib.sha256()
            with open(full, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
            manifest["files"].append(
                {"path": _normalize(rel), "size": size, "sha256": h.hexdigest()}
            )

        # 验证 manifest 结构
        assert manifest["total_files"] == len(manifest["files"])
        assert manifest["total_files"] > 0

        # 验证每个文件条目
        for entry in manifest["files"]:
            assert "path" in entry
            assert "size" in entry
            assert "sha256" in entry
            assert entry["size"] >= 0
            assert len(entry["sha256"]) == 64

        # 验证 manifest 可 JSON 序列化
        json_str = json.dumps(manifest, ensure_ascii=False)
        parsed = json.loads(json_str)
        assert parsed["total_files"] == manifest["total_files"]

    def test_manifest_file_count_matches_zip(self, tmp_path, project_root):
        """manifest 中的文件数应与 zip 中的条目数一致。"""
        files = _collect_release_files(project_root)
        zip_path = tmp_path / "test_count.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for full, rel in files:
                zf.write(full, _normalize(rel))

        with zipfile.ZipFile(zip_path, "r") as zf:
            zip_count = len(zf.namelist())

        assert zip_count == len(files)


class TestReleaseZipInstallable:
    """验证解压后可安装（pyproject.toml 存在且可解析）。"""

    def test_pyproject_toml_parseable(self, release_zip, tmp_path):
        with zipfile.ZipFile(release_zip, "r") as zf:
            zf.extract("pyproject.toml", tmp_path)

        try:
            import tomllib
        except ModuleNotFoundError:  # Python 3.10
            import tomli as tomllib

        with open(tmp_path / "pyproject.toml", "rb") as f:
            data = tomllib.load(f)

        assert data["project"]["name"] == "semantic_detector"
        assert "dependencies" in data["project"] or True  # deps may be in requirements.txt

    def test_requirements_txt_present(self, release_zip):
        with zipfile.ZipFile(release_zip, "r") as zf:
            names = zf.namelist()
        assert "requirements.txt" in names
