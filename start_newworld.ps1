param(
    [switch]$Install
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$Python = "C:\miniconda\envs\py3.8\python.exe"

if (-not (Test-Path $Python)) {
    throw "未找到 Python 3.8 环境：$Python"
}

if (-not (Test-Path $Backend)) {
    throw "未找到后端目录：$Backend"
}

if (-not (Test-Path $Frontend)) {
    throw "未找到前端目录：$Frontend"
}

if ($Install) {
    Write-Host "安装后端依赖..." -ForegroundColor Cyan
    Push-Location $Backend
    & $Python -m pip install -r requirements-dev.txt
    Pop-Location

    Write-Host "安装前端依赖..." -ForegroundColor Cyan
    Push-Location $Frontend
    npm install
    Pop-Location
}

Write-Host "启动 NewWorld..." -ForegroundColor Green

$backendCommand = "cd /d `"$Backend`" && `"$Python`" -m uvicorn app.main:app --reload --port 8000"
$frontendCommand = "cd /d `"$Frontend`" && npm run dev"

Start-Process -FilePath "cmd.exe" -ArgumentList "/k", $backendCommand -WindowStyle Normal
Start-Process -FilePath "cmd.exe" -ArgumentList "/k", $frontendCommand -WindowStyle Normal

Write-Host ""
Write-Host "后端 API: http://127.0.0.1:8000" -ForegroundColor Yellow
Write-Host "后端文档: http://127.0.0.1:8000/docs" -ForegroundColor Yellow
Write-Host "前端工作台: http://127.0.0.1:5173" -ForegroundColor Yellow
Write-Host ""
Write-Host "如果首次运行缺依赖，请执行：" -ForegroundColor Gray
Write-Host "powershell -ExecutionPolicy Bypass -File .\start_newworld.ps1 -Install" -ForegroundColor Gray
