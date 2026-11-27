# MediLocker — Offline Judge Mode Launcher (Windows PowerShell)
$ErrorActionPreference = "Stop"

$env:MEDILOCKER_MODE = "judge"
$env:MEDILOCKER_ENV = "development"
$env:MEDILOCKER_OFFLINE_MODE = "true"
if (-not $env:RAKSHA_SECRET) { $env:RAKSHA_SECRET = "practice" }

Write-Host "Starting MediLocker in LOCAL EVALUATION MODE (MEDILOCKER_MODE=judge, CPU-only, offline)..."
Write-Host "Backend:  http://127.0.0.1:8000"
Write-Host "Frontend: http://127.0.0.1:3001/dashboard"

Start-Process -NoNewWindow -FilePath ".\.venv\Scripts\uvicorn.exe" -ArgumentList "backend.main:app --host 127.0.0.1 --port 8000"
.\.venv\Scripts\python.exe -m http.server 3001 --bind 127.0.0.1 --directory frontend\out
