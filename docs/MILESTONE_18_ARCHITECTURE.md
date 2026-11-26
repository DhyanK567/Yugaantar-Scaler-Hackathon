# Milestone 18 — Offline-First Local Application & Desktop Distribution Architecture

**Project:** MediLocker (GuptKavach / Secret-Wards-ToolKit)  
**Version:** 2.0.0-m18-offline  
**Date:** 2026-11-26  

---

## 1. System Inventory
- **Frontend:** Next.js 16.4.6 (App Router, Turbopack), React 19.3.0, TypeScript 5.9.3 (`frontend/`).
- **Backend API:** FastAPI 0.165.0 + Uvicorn (`backend/main.py`, `backend/auth.py`, `backend/pipeline.py`, `backend/database.py`, `backend/engine_adapter.py`).
- **Offline Privacy Engine:** Standalone deterministic Python engine (`starter/main.py`, `starter/raksha_engine/*`) with zero external network or LLM dependencies.
- **Database:** Local SQLite (`data/guptkavach.db`) with `PRAGMA foreign_keys = ON` and `WAL` journal mode.
- **Local Storage:** `data/datasets/` (uploaded raw batches), `data/jobs/<job_id>/output/` (sanitised files, `report.json`, `records.jsonl`).
- **Official Evaluator Entrypoints (Preserved Unchanged):** `starter/main.py`, `validate_output.py`, `check_dev.py`, `check_submission.py`.

---

## 2. Offline-First Architecture

```
+-------------------------------------------------------------------+
|               Local Machine (127.0.0.1 / Loopback Only)           |
|                                                                   |
|  +---------------------------+      +--------------------------+  |
|  |   MediLocker Launcher     |      |   Browser / Desktop UI   |  |
|  | launcher/medilocker_      |----->|   http://127.0.0.1:3001  |  |
|  | launcher.py               |      +------------+-------------+  |
|  +-------------+-------------+                   |                |
|                | manages                         | HTTP (loopback)|
|                v                                 v                |
|  +---------------------------+      +--------------------------+  |
|  |   Next.js Local Server    |      |   FastAPI Local Backend  |  |
|  |   127.0.0.1:3001          |      |   127.0.0.1:8000         |  |
|  +---------------------------+      +------------+-------------+  |
|                                                  | subprocess     |
|                                                  v                |
|  +---------------------------+      +--------------------------+  |
|  |   SQLite + Local Storage  |<---->|   Offline Privacy Engine |  |
|  |   data/guptkavach.db      |      |   starter/main.py        |  |
|  |   data/datasets/, jobs/   |      |   (CPU-only, air-gapped) |  |
|  +---------------------------+      +--------------------------+  |
+-------------------------------------------------------------------+
```

### Key Offline-First Guarantees
1. **Zero External Network Dependencies:** Dataset upload, PII detection, identity continuity, clinical validation, 7-vector attack simulation, Privacy Passport generation, and audit logging all execute 100% locally.
2. **Loopback-Only Binding:** Both FastAPI (`127.0.0.1:8000`) and Next.js (`127.0.0.1:3001`) bind strictly to `127.0.0.1` so the service is never exposed to the LAN/public network by default.
3. **Offline Local Demo Access Mode:** When `MEDILOCKER_OFFLINE_MODE=true` is set by the local launcher, `/api/auth/offline-demo` (and `/login`'s clearly labelled **Offline Local Demo Mode** button) issues a local `HttpOnly` session cookie without requiring SMTP or Google OAuth.
4. **Independent CLI Preserved:** `starter/main.py --input <dir> --output <dir>` runs independently without FastAPI, Next.js, the launcher, or any logged-in web user.

---

## 3. Startup & Shutdown Lifecycle (`launcher/medilocker_launcher.py`)
1. **Single-Instance Lock:** Acquires `data/medilocker.lock` (with PID check) and verifies ports `8000` and `3001` are free; fails fast with a clear, actionable error if occupied.
2. **Storage & DB Check:** Verifies write access to `data/`, `data/datasets/`, and `data/jobs/`, then initializes/migrates `data/guptkavach.db` via `backend.database.init_db()`.
3. **Backend Launch:** Starts `uvicorn backend.main:app --host 127.0.0.1 --port 8000` with `MEDILOCKER_OFFLINE_MODE=true`, `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`.
4. **Frontend Launch:** Starts Next.js production server on `127.0.0.1:3001`.
5. **Health Verification:** Polls `http://127.0.0.1:8000/api/health` and `http://127.0.0.1:3001` before opening `http://127.0.0.1:3001/login` in the default browser.
6. **Clean Shutdown:** On `SIGINT`/`SIGTERM`/exit, terminates child processes, runs `PRAGMA wal_checkpoint(TRUNCATE)` to flush SQLite WAL, removes `data/medilocker.lock`, and preserves all completed jobs and audit history.

---

## 4. Packaging Strategy Evaluation (Windows Distribution)
- **Evaluated Options:**
  - *Single-file PyInstaller bundle of Python + Node + Next.js:* Rejected because bundling Node.js runtime + Next.js `.next` server + FastAPI + subprocess `starter/main.py` into a single EXE creates fragile extraction paths and antivirus false positives.
  - *Portable Windows Distribution (`dist/MediLocker-Windows/`):* **Selected.** Packages `Start-MediLocker.bat`, `launcher/medilocker_launcher.py`, `backend/`, `starter/`, pre-built `frontend/.next/` + `node_modules` (or standalone server), `.env.offline.template`, and `VERSION` with zero secrets and zero real patient data.
