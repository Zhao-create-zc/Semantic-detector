# run_demo.ps1 - 运行语义检测器完整演示（R304: 串联 run 和 evaluate）

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "语义检测器完整演示" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 设置项目根目录
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Write-Host "项目根目录: $ProjectRoot" -ForegroundColor Gray

# 切换到项目目录
Set-Location $ProjectRoot

# 步骤 1: 清理输出目录
Write-Host ""
Write-Host "[步骤 1/5] 清理输出目录..." -ForegroundColor Yellow
if (Test-Path examples\output) {
    Remove-Item -Recurse -Force examples\output\*
} else {
    New-Item -ItemType Directory -Path examples\output | Out-Null
}
Write-Host "清理完成!" -ForegroundColor Green

# 步骤 2: 验证输入文件
Write-Host ""
Write-Host "[步骤 2/5] 验证输入文件..." -ForegroundColor Yellow
python -m semantic_detector.cli validate examples/messages.jsonl --output-dir examples/output
if ($LASTEXITCODE -ne 0) {
    Write-Host "验证失败!" -ForegroundColor Red
    exit 1
}
Write-Host "验证成功!" -ForegroundColor Green

# 步骤 3: 运行完整流水线（生成预测）
Write-Host ""
Write-Host "[步骤 3/5] 运行完整流水线..." -ForegroundColor Yellow
python -m semantic_detector.cli run examples/messages.jsonl --output-dir examples/output
if ($LASTEXITCODE -ne 0) {
    Write-Host "流水线运行失败!" -ForegroundColor Red
    exit 1
}
Write-Host "流水线运行成功!" -ForegroundColor Green

# 步骤 4: 评估预测结果（R304: 串联 evaluate）
Write-Host ""
Write-Host "[步骤 4/5] 评估预测结果..." -ForegroundColor Yellow
python -m semantic_detector.cli evaluate examples/output/predictions.jsonl examples/ground_truth.jsonl
if ($LASTEXITCODE -ne 0) {
    Write-Host "评估失败!" -ForegroundColor Red
    exit 1
}
Write-Host "评估成功!" -ForegroundColor Green

# 步骤 5: 显示结果摘要
Write-Host ""
Write-Host "[步骤 5/5] 显示结果摘要..." -ForegroundColor Yellow
Write-Host ""
Write-Host "生成的文件:" -ForegroundColor Cyan
Get-ChildItem examples/output -File | ForEach-Object {
    Write-Host "  - $($_.Name)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "演示完成!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
