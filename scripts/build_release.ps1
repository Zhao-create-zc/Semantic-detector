# build_release.ps1 - 构建发布包
# R410: 打包前自动清理，生成不含 venv/cache/pyc 的发布压缩包 + 文件清单 manifest
param(
    [string]$OutputDir = "dist",
    [string]$ReleaseName = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Get-Location

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "构建发布包 (R410)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: 清理运行产物和发布卫生目标
Write-Host "[Step 1] 清理运行产物和发布卫生目标..." -ForegroundColor Yellow
& "$ProjectRoot\scripts\clean_artifacts.ps1" -Force
Write-Host ""

# Step 2: 确定输出路径
if (-not $ReleaseName) {
    $ReleaseName = "semantic_detector_release_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
}
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
}
$ZipPath = Join-Path $OutputDir "$ReleaseName.zip"
$ManifestPath = Join-Path $OutputDir "$ReleaseName.manifest.json"

Write-Host "[Step 2] 输出路径:" -ForegroundColor Yellow
Write-Host "  ZIP:      $ZipPath" -ForegroundColor Gray
Write-Host "  Manifest: $ManifestPath" -ForegroundColor Gray
Write-Host ""

# Step 3: 使用 Python 创建 zip 和 manifest（可靠跨平台文件处理）
Write-Host "[Step 3] 创建发布压缩包..." -ForegroundColor Yellow

$helperPy = Join-Path $env:TEMP "r410_build_release_helper.py"

@'
import zipfile
import hashlib
import json
import os
import sys
import fnmatch
from datetime import datetime, timezone

project_root = sys.argv[1]
zip_path = sys.argv[2]
manifest_path = sys.argv[3]

# R410: 禁止包含的目录名（任意层级匹配）
FORBIDDEN_DIR_NAMES = {
    "__pycache__", ".pytest_cache", ".git", ".idea", ".vscode",
    ".mypy_cache", ".pyre", ".pytype", ".tox", ".nox",
    ".cleanroom_venv", "venv_cleanroom",
    ".venv_release_check", ".venv_v3_final_check",
    ".venv_r424_release_check",
    ".venv", "venv", "env", "ENV",
    "temp_audit", "temp_cleanroom",
    "dist", "htmlcov", "cover",
    "artifacts\\runs", "artifacts/runs",
}

# R410: 禁止包含的目录后缀
FORBIDDEN_DIR_SUFFIXES = (".egg-info",)

# R410: 禁止包含的文件模式
FORBIDDEN_FILE_PATTERNS = [
    "*.pyc", "*.pyo", "*.pyd",
    ".DS_Store", "Thumbs.db",
    "*.log",
]

# R410: 禁止包含的顶级路径（相对项目根）
FORBIDDEN_TOP_PATHS = {
    "examples/output",
    "examples\\output",
    "artifacts/runs",
    "artifacts\\runs",
    ".git",
}

# R410: 必须包含的顶级路径
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


def normalize(path):
    return path.replace("\\", "/")


def is_forbidden_dir_name(name):
    if name in FORBIDDEN_DIR_NAMES:
        return True
    for suffix in FORBIDDEN_DIR_SUFFIXES:
        if name.endswith(suffix):
            return True
    return False


def is_forbidden_file(name):
    for pattern in FORBIDDEN_FILE_PATTERNS:
        if fnmatch.fnmatch(name, pattern):
            return True
    return False


def is_forbidden_top_path(rel_path):
    norm = normalize(rel_path)
    for fp in FORBIDDEN_TOP_PATHS:
        if norm == normalize(fp) or norm.startswith(normalize(fp) + "/"):
            return True
    return False


def collect_files(root):
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root)
        if rel_dir == ".":
            rel_dir = ""
        # 过滤禁止的子目录（原地修改 dirnames 实现 prune）
        dirnames[:] = [d for d in dirnames if not is_forbidden_dir_name(d)]
        # 检查当前目录是否在禁止的顶级路径下
        if rel_dir and is_forbidden_top_path(rel_dir):
            dirnames[:] = []
            continue
        for fname in filenames:
            if is_forbidden_file(fname):
                continue
            full = os.path.join(dirpath, fname)
            rel = os.path.relpath(full, root)
            files.append((full, rel))
    return files


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    files = collect_files(project_root)

    # 验证必须包含的顶级路径
    rel_paths_norm = set(normalize(r) for _, r in files)
    missing = []
    for req in REQUIRED_TOP_PATHS:
        req_norm = normalize(req)
        found = any(
            rp == req_norm or rp.startswith(req_norm + "/")
            for rp in rel_paths_norm
        )
        if not found:
            missing.append(req)

    if missing:
        print("ERROR: Missing required paths: " + ", ".join(missing), file=sys.stderr)
        sys.exit(1)

    # 创建 zip
    total_size = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for full, rel in sorted(files, key=lambda x: normalize(x[1])):
            zf.write(full, normalize(rel))
            total_size += os.path.getsize(full)

    # 生成 manifest
    manifest = {
        "build_time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "release_name": os.path.basename(zip_path).replace(".zip", ""),
        "project_root": normalize(project_root),
        "total_files": len(files),
        "total_uncompressed_bytes": total_size,
        "required_top_paths_verified": REQUIRED_TOP_PATHS,
        "forbidden_patterns_applied": {
            "dir_names": sorted(FORBIDDEN_DIR_NAMES),
            "dir_suffixes": list(FORBIDDEN_DIR_SUFFIXES),
            "file_patterns": FORBIDDEN_FILE_PATTERNS,
            "top_paths": sorted(normalize(p) for p in FORBIDDEN_TOP_PATHS),
        },
        "files": [],
    }
    for full, rel in sorted(files, key=lambda x: normalize(x[1])):
        size = os.path.getsize(full)
        sha = sha256_file(full)
        manifest["files"].append({
            "path": normalize(rel),
            "size": size,
            "sha256": sha,
        })

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"Created: {zip_path}")
    print(f"  Files: {len(files)}")
    print(f"  Uncompressed: {total_size} bytes ({total_size / 1024 / 1024:.2f} MB)")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
'@ | Set-Content -Path $helperPy -Encoding UTF8

python $helperPy $ProjectRoot $ZipPath $ManifestPath
$buildExit = $LASTEXITCODE
Remove-Item $helperPy -Force -ErrorAction SilentlyContinue

if ($buildExit -ne 0) {
    Write-Host "构建失败 (exit code $buildExit)" -ForegroundColor Red
    exit $buildExit
}

Write-Host ""
Write-Host "[Step 4] 验证压缩包内容..." -ForegroundColor Yellow

# 验证：zip 不含禁止模式，含必须路径
$verifyPy = Join-Path $env:TEMP "r410_verify_release.py"

@'
import zipfile
import sys
import json

zip_path = sys.argv[1]
manifest_path = sys.argv[2]

FORBIDDEN_PATTERNS = [
    "/__pycache__/", "\\__pycache__\\",
    ".pyc", ".pyo",
    ".egg-info",
    "/.pytest_cache/", "\\pytest_cache\\",
    ".cleanroom_venv", "venv_cleanroom",
    ".venv_release_check", ".venv_v3_final_check",
    ".venv_r424_release_check",
    "/.venv/", "\\venv\\",
    "/temp_audit/", "\\temp_audit\\",
]

REQUIRED_ENTRIES = [
    "src/", "tests/", "examples/", "config/", "docs/", "scripts/",
    "LICENSE", "README.md", "pyproject.toml", "requirements.txt",
]

with zipfile.ZipFile(zip_path, "r") as zf:
    names = zf.namelist()

errors = []

# 检查禁止模式
for name in names:
    for pattern in FORBIDDEN_PATTERNS:
        if pattern in name:
            errors.append(f"FORBIDDEN: '{pattern}' found in '{name}'")
            break

# 检查必须包含的路径
for req in REQUIRED_ENTRIES:
    found = any(n.startswith(req) or n == req.rstrip("/") for n in names)
    if not found:
        errors.append(f"MISSING: required entry '{req}' not found")

# 验证 manifest 可解析
with open(manifest_path, "r", encoding="utf-8") as f:
    manifest = json.load(f)

if manifest["total_files"] != len(names):
    errors.append(
        f"COUNT MISMATCH: manifest={manifest['total_files']}, zip={len(names)}"
    )

if errors:
    print("VERIFICATION FAILED:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    print(f"VERIFICATION PASSED: {len(names)} files, all checks passed")
    print(f"  Manifest: {manifest['total_files']} files, "
          f"{manifest['total_uncompressed_bytes']} bytes")
'@ | Set-Content -Path $verifyPy -Encoding UTF8

python $verifyPy $ZipPath $ManifestPath
$verifyExit = $LASTEXITCODE
Remove-Item $verifyPy -Force -ErrorAction SilentlyContinue

if ($verifyExit -ne 0) {
    Write-Host "验证失败 (exit code $verifyExit)" -ForegroundColor Red
    exit $verifyExit
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "发布包构建完成!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ZIP:      $ZipPath" -ForegroundColor Gray
Write-Host "  Manifest: $ManifestPath" -ForegroundColor Gray
