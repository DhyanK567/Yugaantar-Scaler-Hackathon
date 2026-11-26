# MediLocker Windows Distribution Build Guide

## 1. Build Command
Run from the repository root in PowerShell:
```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_windows_dist.ps1
```

## 2. Output Structure (`dist/MediLocker-Windows/`)
- `Start-MediLocker.bat` — Windows double-click entrypoint.
- `launcher/medilocker_launcher.py` — Single-instance lock, port checks, SQLite migration, loopback server manager, clean shutdown.
- `backend/` — FastAPI backend & SQLite database layer.
- `starter/` — Unmodified offline deterministic privacy engine.
- `frontend/` — Pre-built Next.js `.next/` production server & static assets.
- `.env.offline.template` — Offline loopback configuration template (no secrets).
- `VERSION` — Release version (`2.0.0-m18-offline`).

## 3. Security Guarantees of the Package
- Never includes `.env`, SMTP credentials, Google OAuth secrets, `data/guptkavach.db`, or real patient records.
- Binds strictly to `127.0.0.1` (ports `8000` and `3001`).
