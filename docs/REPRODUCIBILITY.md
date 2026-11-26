# MediLocker Reproducibility & Execution Guide

This guide provides exact, verified commands for running MediLocker offline, in development, as a Windows distribution, and via the independent hackathon CLI evaluator.

---

## 1. Prerequisites
- **Python:** 3.10+ (verified on Python 3.14.7)
- **Node.js & pnpm:** Node.js 20+ and `pnpm` (verified on `pnpm 12.18.0`)
- **Hardware:** CPU-only; tested within 2 CPUs / 4 GB RAM budget

---

## 2. Environment Setup

### Windows PowerShell
```powershell
git clone https://github.com/DhyanK567/Yugaantar-Scaler-Hackathon.git
cd Yugaantar-Scaler-Hackathon

python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 1. Offline Privacy Engine dependencies (Python stdlib only)
pip install -r starter\requirements.txt

# 2. Web Backend & Test dependencies
pip install fastapi uvicorn python-multipart google-auth requests httpx pytest reportlab

# 3. Frontend dependencies & production build
cd frontend
pnpm install
pnpm build
cd ..
```

### Git Bash (Windows) / Linux
```bash
python -m venv .venv
source .venv/Scripts/activate   # or: source .venv/bin/activate on Linux

pip install -r starter/requirements.txt
pip install fastapi uvicorn python-multipart google-auth requests httpx pytest reportlab

cd frontend && pnpm install && pnpm build && cd ..
```

---

## 3. Running MediLocker (4 Supported Modes)

### Mode A: Offline-First Local Application (Recommended for Judges)
Uses loopback-only binding (`127.0.0.1:8000` and `127.0.0.1:3001`), initializes SQLite automatically, enables Offline Local Demo Mode, and requires zero internet access:
```powershell
.\.venv\Scripts\python.exe launcher\medilocker_launcher.py
# Or double-click Start-MediLocker.bat in Windows Explorer
```

### Mode B: Development Mode (Hot Reload)
Terminal 1 (Backend):
```powershell
.\.venv\Scripts\uvicorn.exe backend.main:app --host 127.0.0.1 --port 8000 --reload
```
Terminal 2 (Frontend):
```powershell
cd frontend
pnpm dev -p 3001
```

### Mode C: Building the Portable Windows Distribution
Packages `Start-MediLocker.bat`, `launcher/`, `backend/`, `starter/`, built `frontend/.next/`, `.env.offline.template`, and `VERSION` into `dist/MediLocker-Windows/` without secrets or patient data:
```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_windows_dist.ps1
```

### Mode D: Independent CLI Evaluator (No Web Server, No Internet)
```powershell
$env:RAKSHA_SECRET="practice"
$env:HF_HUB_OFFLINE="1"
$env:TRANSFORMERS_OFFLINE="1"
.\.venv\Scripts\python.exe starter\main.py --input dev\input --output my_output_verify
.\.venv\Scripts\python.exe validate_output.py --input dev\input --output my_output_verify
.\.venv\Scripts\python.exe check_dev.py --output my_output_verify --show 10
.\.venv\Scripts\python.exe check_submission.py --repo starter
```

---

## 4. Running Automated Tests
```powershell
# Integration, Auth (OTP & Google OAuth), RBAC & Strict Offline Verification (16 tests)
.\.venv\Scripts\python.exe -m pytest tests\milestone_17\test_milestone_17.py tests\milestone_18\test_offline_verification.py -v

# 11-Point System Regression Suite
.\.venv\Scripts\python.exe test_guptkavach_system.py

# Adversarial Identity Benchmark
.\.venv\Scripts\python.exe tests\identity_adversarial\run_identity_benchmark.py

# Performance Benchmark Suite
.\.venv\Scripts\python.exe tests\performance\benchmark_suite.py
```
