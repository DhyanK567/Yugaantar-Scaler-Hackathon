# MediLocker Windows Distribution Build Script
# Creates a clean, self-contained Windows bundle in dist/MediLocker-Windows/
# Never packages .env secrets, SQLite databases, or real patient data.

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path "$PSScriptRoot\..").Path
$DistDir = Join-Path $RepoRoot "dist\MediLocker-Windows"

Write-Host "=== Building MediLocker Windows Distribution ===" -ForegroundColor Cyan

if (Test-Path $DistDir) {
    Remove-Item -Recurse -Force $DistDir
}
New-Item -ItemType Directory -Path $DistDir -Force | Out-Null

# 1. Build frontend production bundle
Write-Host "[1/4] Building Next.js frontend..."
Push-Location (Join-Path $RepoRoot "frontend")
pnpm build
if ($LASTEXITCODE -ne 0) { throw "Frontend build failed" }
Pop-Location

# 2. Copy runtime modules (excluding secrets, __pycache__, and local DBs)
Write-Host "[2/4] Copying backend, starter engine, and launcher..."
Copy-Item (Join-Path $RepoRoot "VERSION") $DistDir
Copy-Item (Join-Path $RepoRoot ".env.offline.template") $DistDir
Copy-Item (Join-Path $RepoRoot "Start-MediLocker.bat") $DistDir

New-Item -ItemType Directory -Path (Join-Path $DistDir "launcher") -Force | Out-Null
Copy-Item (Join-Path $RepoRoot "launcher\medilocker_launcher.py") (Join-Path $DistDir "launcher\")

robocopy (Join-Path $RepoRoot "backend") (Join-Path $DistDir "backend") /E /XD __pycache__ | Out-Null
robocopy (Join-Path $RepoRoot "starter") (Join-Path $DistDir "starter") /E /XD __pycache__ | Out-Null

# 3. Copy built Next.js frontend runtime
Write-Host "[3/4] Copying Next.js production artifacts..."
$DistFrontend = Join-Path $DistDir "frontend"
New-Item -ItemType Directory -Path $DistFrontend -Force | Out-Null
Copy-Item (Join-Path $RepoRoot "frontend\package.json") $DistFrontend
Copy-Item (Join-Path $RepoRoot "frontend\next.config.ts") $DistFrontend
robocopy (Join-Path $RepoRoot "frontend\public") (Join-Path $DistFrontend "public") /E | Out-Null
robocopy (Join-Path $RepoRoot "frontend\.next") (Join-Path $DistFrontend ".next") /E /XD cache | Out-Null

# 4. Write quick-start note
Write-Host "[4/4] Writing Windows Quick-Start README..."
@"
MediLocker Offline-First Windows Distribution
=============================================
1. Ensure Python 3.11+ and Node.js 20+ are installed on Windows.
2. Install Python backend dependencies:
   pip install -r starter\requirements.txt
   pip install fastapi uvicorn python-multipart google-auth requests
3. Install frontend runtime dependencies (once, while online or from offline cache):
   cd frontend && pnpm install --prod
4. Double-click Start-MediLocker.bat (or run: python launcher\medilocker_launcher.py)
5. MediLocker opens automatically at http://127.0.0.1:3001/login in Offline Local Demo Mode.
"@ | Out-File -FilePath (Join-Path $DistDir "README_WINDOWS.txt") -Encoding utf8

Write-Host "[OK] Windows distribution built at: $DistDir" -ForegroundColor Green
