# clean_artifacts.ps1 - 清理运行产物

param(
    [switch]$DryRun,
    [switch]$Force
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "清理运行产物" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 设置项目根目录
$ProjectRoot = Get-Location

Write-Host "项目根目录: $ProjectRoot" -ForegroundColor Gray

if ($DryRun) {
    Write-Host "模式: DRY-RUN (仅显示，不删除)" -ForegroundColor Yellow
} else {
    Write-Host "模式: 执行删除" -ForegroundColor Yellow
}

Write-Host ""

# 定义要清理的目录和文件
$ArtifactsToClean = "examples\output", "examples\validated.jsonl", "examples\rejected.jsonl", "examples\field_profiles.jsonl", "examples\predictions.jsonl", "examples\manifest.json", "examples\metrics.json", "examples\per_label_metrics.csv", "examples\confusion_matrix.csv", "examples\errors.jsonl"

# R363/R409: 发布卫生清理目标 - cleanroom 虚拟环境、Python 缓存、egg-info、临时 audit 场景
# R409: 扩展清单 - 新增 .venv_release_check、.venv_v3_final_check、*.pyc
$ReleaseHygieneTargets = ".cleanroom_venv", "venv_cleanroom", ".venv_release_check", ".venv_v3_final_check", "__pycache__", ".pytest_cache", "*.egg-info", "*.pyc", "temp_audit", "temp_cleanroom"

# R409: 定义不应删除的目录和文件（计划要求：src/tests/examples/config/docs/LICENSE/NOTICE/THIRD_PARTY_LICENSES/必要审计记录）
$ProtectedPaths = "docs", "tests", "src", "scripts", "config", "examples\messages.jsonl", "examples\config.json", "LICENSE", "NOTICE", "THIRD_PARTY_LICENSES", "artifacts\rounds", "artifacts\audit", "artifacts\heartbeat"

Write-Host "受保护的路径（不会被删除）:" -ForegroundColor Cyan
foreach ($path in $ProtectedPaths) {
    Write-Host "  - $path" -ForegroundColor Gray
}

Write-Host ""
Write-Host "将要清理的产物:" -ForegroundColor Cyan

$FilesToDelete = @()
$DirsToDelete = @()

foreach ($artifact in $ArtifactsToClean) {
    $fullPath = Join-Path $ProjectRoot $artifact

    if (Test-Path $fullPath) {
        $item = Get-Item $fullPath
        if ($item -is [System.IO.DirectoryInfo]) {
            $DirsToDelete += $fullPath
            Write-Host "  [DIR]  $artifact" -ForegroundColor Yellow
        } else {
            $FilesToDelete += $fullPath
            Write-Host "  [FILE] $artifact" -ForegroundColor Yellow
        }
    }
}

# R363/R409: 发布卫生清理 - 递归查找 cleanroom 虚拟环境、Python 缓存、egg-info、临时 audit 场景
# R409: 同时清理目录（__pycache__/.pytest_cache/*.egg-info/venv 等）和文件（*.pyc）
Write-Host ""
Write-Host "发布卫生目标 (R363/R409):" -ForegroundColor Cyan

# R409: 分离目录目标和文件目标（*.pyc 是文件，其余是目录）
$DirTargets = @()
$FileTargets = @()
foreach ($t in $ReleaseHygieneTargets) {
    if ($t -like "*.pyc") {
        $FileTargets += $t
    } else {
        $DirTargets += $t
    }
}

foreach ($target in $DirTargets) {
    $foundItems = Get-ChildItem -Path $ProjectRoot -Recurse -Filter $target -Directory -ErrorAction SilentlyContinue
    foreach ($item in $foundItems) {
        # 审计修复问题-6: 原模式 "*\$protected\*" 过宽 —
        #   (a) 会保护受保护目录下的所有内容（包括 __pycache__/.pytest_cache 等本应清理的产物）；
        #   (b) 会匹配任意深度的同名子目录（如 venv 内 site-packages/xxx/src/__pycache__）。
        # 改为只保护受保护路径本身（顶级目录或具体文件），允许清理其内部 Python 缓存。
        $isProtected = $false
        foreach ($protected in $ProtectedPaths) {
            $protectedFull = Join-Path $ProjectRoot $protected
            if ($item.FullName -eq $protectedFull) {
                $isProtected = $true
                break
            }
        }
        if (-not $isProtected) {
            $DirsToDelete += $item.FullName
            $relPath = $item.FullName.Substring($ProjectRoot.Length).TrimStart("\")
            Write-Host "  [HYGIENE-DIR] $relPath" -ForegroundColor Yellow
        }
    }
}

# R409: 清理文件目标（*.pyc）
foreach ($target in $FileTargets) {
    $foundFiles = Get-ChildItem -Path $ProjectRoot -Recurse -Filter $target -File -ErrorAction SilentlyContinue
    foreach ($item in $foundFiles) {
        $isProtected = $false
        foreach ($protected in $ProtectedPaths) {
            $protectedFull = Join-Path $ProjectRoot $protected
            if ($item.FullName -eq $protectedFull) {
                $isProtected = $true
                break
            }
        }
        if (-not $isProtected) {
            $FilesToDelete += $item.FullName
            $relPath = $item.FullName.Substring($ProjectRoot.Length).TrimStart("\")
            Write-Host "  [HYGIENE-FILE] $relPath" -ForegroundColor Yellow
        }
    }
}

if (($FilesToDelete.Count -eq 0) -and ($DirsToDelete.Count -eq 0)) {
    Write-Host "  无产物需要清理" -ForegroundColor Green
    exit 0
}

Write-Host ""
Write-Host "统计:" -ForegroundColor Cyan
Write-Host "  文件数: $($FilesToDelete.Count)" -ForegroundColor Gray
Write-Host "  目录数: $($DirsToDelete.Count)" -ForegroundColor Gray

if ($DryRun) {
    Write-Host ""
    Write-Host "DRY-RUN 模式: 不执行删除" -ForegroundColor Yellow
    Write-Host "使用 -Force 参数执行实际删除" -ForegroundColor Yellow
    exit 0
}

if (-not $Force) {
    Write-Host ""
    Write-Host "需要 -Force 参数执行删除" -ForegroundColor Red
    Write-Host "示例: .\clean_artifacts.ps1 -Force" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "执行删除..." -ForegroundColor Yellow

# 删除文件
foreach ($file in $FilesToDelete) {
    if (Test-Path $file) {
        Remove-Item $file -Force -ErrorAction SilentlyContinue
        $fileName = Split-Path -Leaf $file
        Write-Host "  已删除: $fileName" -ForegroundColor Green
    }
}

# 删除目录（R410: 先按路径深度降序排序，先删子目录再删父目录，避免递归删除父目录后子目录不存在）
$SortedDirs = $DirsToDelete | Sort-Object { $_.Length } -Descending
foreach ($dir in $SortedDirs) {
    if (Test-Path $dir) {
        Remove-Item $dir -Recurse -Force -ErrorAction SilentlyContinue
        $dirName = Split-Path -Leaf $dir
        Write-Host "  已删除: $dirName" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "清理完成!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
