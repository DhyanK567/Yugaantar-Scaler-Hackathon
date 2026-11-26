# MediLocker Windows Desktop EXE & Installer Build Script
$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path "$PSScriptRoot\..").Path

Write-Host "=== MediLocker Windows Desktop Build ===" -ForegroundColor Cyan

# 1. PyInstaller bundle
Write-Host "[1/4] Building PyInstaller medilocker-backend.exe..."
Push-Location $RepoRoot
& "$RepoRoot\.venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --distpath desktop\py_dist --workpath desktop\py_build desktop\medilocker_backend.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed" }

# 2. Next.js standalone build
Write-Host "[2/4] Building Next.js standalone frontend..."
Push-Location (Join-Path $RepoRoot "frontend")
pnpm build
if ($LASTEXITCODE -ne 0) { throw "Next.js build failed" }
Pop-Location

# 3. Stage standalone + Node runtime
Write-Host "[3/4] Staging standalone frontend and Node runtime..."
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue desktop\web_dist, desktop\node_runtime
New-Item -ItemType Directory -Force -Path desktop\web_dist, desktop\node_runtime | Out-Null
robocopy frontend\.next\standalone desktop\web_dist /E | Out-Null
New-Item -ItemType Directory -Force -Path desktop\web_dist\.next\static, desktop\web_dist\public | Out-Null
robocopy frontend\.next\static desktop\web_dist\.next\static /E | Out-Null
robocopy frontend\public desktop\web_dist\public /E | Out-Null
Copy-Item (Get-Command node).Source desktop\node_runtime\node.exe

# 4. Electron Builder (NSIS + Portable)
Write-Host "[4/4] Packaging NSIS Installer and Portable EXE..."
Push-Location (Join-Path $RepoRoot "desktop")
if (-not (Test-Path "node_modules")) { npm install }
npm run dist:win
if ($LASTEXITCODE -ne 0) { throw "electron-builder failed" }
Pop-Location
Pop-Location

Write-Host "[OK] Build complete. Outputs in release\" -ForegroundColor Green
