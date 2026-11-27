# MEDILOCKER — OFFLINE JUDGE MODE & OPTIONAL AUTHENTICATION REPORT

**Date:** 2026-11-27  
**Track:** Yugaantar DevForge — Track 3: Secret Wards

---

## 1. Architecture Summary

MediLocker now supports two explicit backend-enforced operating modes via `MEDILOCKER_MODE`:

1. **Offline Judge Mode (`MEDILOCKER_MODE=judge`, `MEDILOCKER_ENV=development`):**
   - `backend/auth.py` (`get_operating_mode()`, `is_judge_mode()`, `require_user()`) provisions a local synthetic evaluator context (`usr-judge-evaluator` in `org-judge-eval`, `"Local Evaluation Ward (Synthetic)"`) without requiring login, SMTP, or Google OAuth.
   - `frontend/src/components/layout/AppLayout.tsx` displays a persistent **`LOCAL EVALUATION MODE`** banner.
   - `frontend/src/app/login/page.tsx` and `frontend/src/app/register/page.tsx` automatically redirect to `/dashboard` when `judge_mode` is `true`.
   - Restricted patient mapping exports (`/api/jobs/{job_id}/mapping` and `include_mapping=true`) remain **blocked (`403`)** in Judge Mode.
2. **Organisation Mode (`MEDILOCKER_MODE=organisation` or `MEDILOCKER_ENV=production`):**
   - Production safety guard: when `MEDILOCKER_ENV=production`, `get_operating_mode()` **always** forces `"organisation"` even if `MEDILOCKER_MODE=judge` is set.
   - Preserves full login, RBAC roles, organisation isolation, restricted `records.jsonl` mapping access, and audit logging.

---

## 2. Exact Commands

### Offline Judge Mode
```powershell
.\scripts\run_judge_mode.ps1
```
Or Linux/macOS:
```bash
bash scripts/run_judge_mode.sh
```

### Authenticated Organisation Mode
```powershell
$env:MEDILOCKER_MODE = "organisation"
$env:MEDILOCKER_ENV = "production"
.\.venv\Scripts\uvicorn.exe backend.main:app --host 127.0.0.1 --port 8000
```

---

## 3. Verified Test Evidence

- **Judge Mode, Production Guard & Organisation Mode Suite:**
  - Command: `.\.venv\Scripts\python.exe -m pytest tests/judge_mode/test_judge_mode.py tests/milestone_17/test_milestone_17.py tests/milestone_18/test_offline_verification.py -v`
  - Result: **19/19 PASSED** in `24.11s`:
    - `test_01_judge_mode_full_workflow_without_login`: Verified `/api/dashboard/overview` (`200` without login), synthetic CSV + quarantined PDF upload, full `starter/main.py` execution (`sanitized/`, `report.json`, `records.jsonl` generated), privacy/clinical/identity/passport results, bundle ZIP download (`records.jsonl` excluded), `403` on `/api/jobs/{id}/mapping`, and 3-page PDF report (`200`).
    - `test_02_production_cannot_bypass_auth_with_judge_mode`: Verified `MEDILOCKER_ENV=production` rejects `MEDILOCKER_MODE=judge` (`401` on `/api/dashboard/overview`).
    - `test_03_organisation_mode_preserves_auth_and_isolation`: Verified `401` unauthenticated, `200` authenticated, and `403` cross-organisation upload block.
- **Official Submission Checker:**
  - Command: `.\.venv\Scripts\python.exe check_submission.py --repo starter --run`
  - Result: **`READY TO SUBMIT`** (`11.6s`, `CONTRACT OK`).

---

## 4. Limitations

- Switching between `judge` and `organisation` modes requires restarting the backend process with the desired `MEDILOCKER_MODE` environment variable.
- If `MEDILOCKER_ENV=production` is set, Judge Mode is intentionally disabled to prevent accidental auth bypass on deployed servers.
