# MediLocker Desktop Packaging Architecture (Milestone 17)

**Target Platform:** Windows x64 (`MediLocker-Setup-x64.exe` & `MediLocker-Portable-x64.exe`)  
**Output Directory:** `release/`

---

## 1. Discovered Repository Entrypoints & Data Flow
- **Frontend (`frontend/`):** Next.js 16.4.6 (App Router, `cacheComponents: true`, `partialPrefetching: true`, Tailwind CSS 4.3.3). Uses `output: "standalone"` for self-contained Node.js server bundling.
- **Backend (`backend/main.py`):** FastAPI 0.165.0 + Uvicorn 0.54.0, reading `MEDILOCKER_DB_PATH` / `MEDILOCKER_DATA_DIR`, `RAKSHA_SECRET`, `MEDILOCKER_AUTH_SECRET`, and `MEDILOCKER_OFFLINE_MODE`.
- **Privacy Engine (`starter/main.py` + `starter/raksha_engine/`):** Standalone Python stdlib-only two-pass engine. Invoked by `backend/engine_adapter.py`.
- **Database (`backend/database.py`):** Local SQLite (`guptkavach.db`) with `PRAGMA foreign_keys = ON` and `WAL` mode.
- **PDF Utility (`generate_pdf.py`):** ReportLab-based 2-page PDF generator.

---

## 2. Desktop Startup Sequence & Dependency Graph

```
MediLocker.exe (Electron Main Process — desktop/main.js)
  │
  ├─ 1. Acquire single-instance lock & resolve userData (%APPDATA%\MediLocker)
  ├─ 2. Initialize secrets.json (random 32-byte RAKSHA_SECRET & MEDILOCKER_AUTH_SECRET)
  ├─ 3. Allocate 2 free loopback ports (127.0.0.1:<apiPort>, 127.0.0.1:<uiPort>)
  ├─ 4. Spawn medilocker-backend.exe (PyInstaller bundle of FastAPI + starter/ + ReportLab)
  │       └─ Polls http://127.0.0.1:<apiPort>/api/health until 200 OK
  ├─ 5. Spawn bundled node.exe + Next.js standalone server.js on 127.0.0.1:<uiPort>
  │       └─ Polls http://127.0.0.1:<uiPort> until 200 OK
  └─ 6. Open BrowserWindow (contextIsolation=true, nodeIntegration=false, sandbox=true)
          ├─ preload.js exposes window.medilockerDesktop.apiBase = http://127.0.0.1:<apiPort>
          └─ Graceful shutdown kills backend + frontend process trees (zero orphans)
```

---

## 3. Frozen Engine Invocation (`--run-engine`)
When packaged via PyInstaller (`getattr(sys, "frozen", False)`), `sys.executable` points to `medilocker-backend.exe` rather than `python.exe`.
- `desktop/backend_entry.py` checks for `--run-engine`: if present, it dispatches directly to `starter/main.py` (`main()`) using the exact same offline privacy engine code.
- `backend/engine_adapter.py` uses `[sys.executable, "--run-engine", "--input", ..., "--output", ...]` when frozen, and `[sys.executable, str(MAIN_PY), ...]` when running from source.
- The standalone CLI (`python starter/main.py --input ... --output ...`) remains 100% unchanged for the official hackathon evaluator.
