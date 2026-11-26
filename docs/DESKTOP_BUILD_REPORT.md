# MediLocker Windows Desktop Build Report

**Date:** 2026-11-27  
**Version:** `2.0.0` (`org.yugaantar.medilocker`)  

---

## 1. Generated Artifacts (`release/`)

| Artifact | Size | SHA-256 |
|---|---|---|
| `release/MediLocker-Setup-x64.exe` | `136.78 MB` (`143,420,354` bytes) | `7748c6aaa952ff961ddd8bc721fbde3383cfbb0bf0feab763798c098844e0785` |
| `release/MediLocker-Portable-x64.exe` | `124.17 MB` (`130,203,843` bytes) | `d0ba9f1748a0ca180dff7dc36021d071e14fe4d70f955b61d8a8332bc882edc5` |
| `release/win-unpacked/MediLocker.exe` | `191.91 MB` (`201,233,408` bytes) | `f65f111a47953139b9babbd6d10ac6c51c02ebc01151fb40fa1b392227c37c8c` |
| `release/win-unpacked/resources/backend/medilocker-backend.exe` | `12.66 MB` (`13,276,362` bytes) | `b7d1c455a153aef44bc94af2fcdf373b9937965dec788223ece40e4930539c13` |

Checksums saved to `release/SHA256SUMS.txt` and `release/BUILD_MANIFEST.json`.

## 2. Reproducible Build Command
```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_desktop_exe.ps1
```

## 3. Verified Functional & Offline Tests
- **Frozen Engine CLI (`medilocker-backend.exe --run-engine`):** Exited `0`, processed synthetic CSV (`files 1 sanitized 1 quarantined 0 records 1`), generated `sanitized/sample.csv`.
- **Frozen FastAPI Server (`medilocker-backend.exe --host 127.0.0.1 --port 8097`):**
  - `GET /api/health` → `healthy`
  - `POST /api/auth/offline-demo` → authenticated session token issued
  - `GET /api/system/diagnostics` → `RUNTIME=Electron + Frozen Python`, `ENGINE=READY`, `DB=CONNECTED`
  - `GET /api/reports/brief-pdf` → generated valid `1,817`-byte PDF via ReportLab
  - `GET /api/dashboard/overview` → `READINESS=NOT_RUN`
- **Official Hackathon CLI Checker (`check_submission.py --repo starter`):** `READY TO SUBMIT`.

## 4. Known Limitations
- Executables are unsigned (`no code signing certificate configured`), so Windows SmartScreen may show an unverified publisher prompt on first run.
- Electron GUI window rendering was verified structurally; full interactive GUI click-through on a fresh Windows VM without Python/Node was not executed in this headless tool session (the frozen backend + engine + bundled `node.exe` + Next.js standalone server were verified).
