# MediLocker Offline Setup & Evaluation Guide

## 1. Prerequisites
- **Hardware:** 2 CPUs, 4 GB RAM (CPU-only, no GPU required).
- **Software:** Python 3.11+ and Node.js 20+ (`pnpm`).

## 2. Offline-First Local Run (Windows & Linux)
1. Copy the offline configuration template:
   ```powershell
   Copy-Item .env.offline.template .env
   ```
2. Build the frontend once:
   ```powershell
   cd frontend
   pnpm build
   cd ..
   ```
3. Launch MediLocker locally (loopback `127.0.0.1` only):
   ```powershell
   .\.venv\Scripts\python.exe launcher\medilocker_launcher.py
   ```
   Or double-click `Start-MediLocker.bat` on Windows.
4. Click **Continue in Offline Demo Mode** at `http://127.0.0.1:3001/login` — zero internet, SMTP, or Google OAuth required.

## 3. Independent CLI Evaluator (Linux & Windows, Zero Web Dependencies)
The privacy engine runs completely independently of FastAPI, Next.js, and the desktop launcher:

### Windows
```powershell
$env:RAKSHA_SECRET="practice"
.\.venv\Scripts\python.exe starter\main.py --input dev\input --output my_output
.\.venv\Scripts\python.exe validate_output.py --input dev\input --output my_output
.\.venv\Scripts\python.exe check_submission.py --repo starter
```

### Linux
```bash
export RAKSHA_SECRET=practice
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
python3 starter/main.py --input dev/input --output my_output
python3 validate_output.py --input dev/input --output my_output
python3 check_submission.py --repo starter
```
