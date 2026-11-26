# Milestone 18 — Offline-First Local Application & Desktop Distribution Report

**Project:** MediLocker (`2.0.0-m18-offline`)  
**Date:** 2026-11-26  

---

## 1. Deliverables Created
- `docs/MILESTONE_18_ARCHITECTURE.md` — Offline-first loopback architecture, startup/shutdown lifecycle, and Windows packaging evaluation.
- `docs/OFFLINE_SETUP_GUIDE.md` — Windows & Linux offline setup and independent CLI evaluation guide.
- `docs/WINDOWS_BUILD_GUIDE.md` — Windows distribution build and security guarantees.
- `launcher/medilocker_launcher.py` & `Start-MediLocker.bat` — Single-instance launcher with port/storage/DB preflight, loopback-only (`127.0.0.1`) FastAPI + Next.js orchestration, health polling, browser launch, and SQLite WAL flush on shutdown.
- `scripts/build_windows_dist.ps1` — Builds self-contained `dist/MediLocker-Windows/` without secrets or patient data.
- `.env.offline.template` & `VERSION` — Offline configuration template and release version.
- `tests/milestone_18/test_offline_verification.py` — Automated offline verification suite blocking all non-loopback network sockets.

## 2. Exact Commands

### 1. Running in Development
```powershell
# Terminal 1: Backend
.\.venv\Scripts\uvicorn.exe backend.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2: Frontend
cd frontend
pnpm dev -p 3001
```

### 2. Running in Production Locally (Offline-First)
```powershell
cd frontend
pnpm build
cd ..
.\.venv\Scripts\python.exe launcher\medilocker_launcher.py
# Or double-click Start-MediLocker.bat
```

### 3. Building the Windows Package
```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_windows_dist.ps1
```
Output directory: `dist/MediLocker-Windows/`.

### 4. Running the Independent CLI Evaluator
```powershell
$env:RAKSHA_SECRET="practice"
.\.venv\Scripts\python.exe starter\main.py --input dev\input --output my_output
.\.venv\Scripts\python.exe validate_output.py --input dev\input --output my_output
.\.venv\Scripts\python.exe check_submission.py --repo starter
```

### 5. Running Offline Verification
```powershell
.\.venv\Scripts\python.exe -m pytest tests/milestone_17/test_milestone_17.py tests/milestone_18/test_offline_verification.py -v
```

## 3. Verification Results
- **Offline Verification & Integration Suite:** **16/16 passed** (`13.55s`) with all non-loopback sockets blocked (`OFFLINE_VIOLATION` guard).
- **Windows Distribution Build:** `scripts/build_windows_dist.ps1` completed (`22/22` Next.js routes compiled, `dist/MediLocker-Windows/` created).
- **Launcher Preflight (`--check-only`):** `[OK] Configuration, storage, SQLite DB, and loopback ports verified.`
- **Official Submission Checker:** `check_submission.py --repo starter` → **`READY TO SUBMIT`**.
