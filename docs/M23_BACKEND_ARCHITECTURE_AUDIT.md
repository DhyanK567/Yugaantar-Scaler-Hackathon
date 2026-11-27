# MEDILOCKER M23 — BACKEND ARCHITECTURE & ROOT-CAUSE AUDIT

**Date:** 2026-11-27  
**Track:** Yugaantar DevForge — Track 3: Secret Wards

---

## 1. Exact Root Cause Trace: `"Insufficient role permissions"` in Judge Mode

| Step | Layer | File & Symbol | Observed Behaviour |
|---|---|---|---|
| 1 | Frontend Upload | `frontend/src/app/dashboard/datasets/page.tsx` (`handleUpload`) | Sends `POST /api/datasets` with `credentials: "include"` and `organisation_id` from `api.organisations()`. |
| 2 | Backend Endpoint | `backend/main.py:843` (`upload_dataset`) | Calls `require_org_access(user, target_org, [ROLE_PLATFORM_ADMIN, ROLE_ORG_ADMIN, ROLE_PRIVACY_OFFICER])`. |
| 3 | Auth Dependency | `backend/auth.py` (`require_user` -> `get_current_user_optional`) | **Root Cause:** `get_current_user_optional()` read a stale `medilocker_session` browser cookie from a prior `RESEARCHER` login *before* checking `is_judge_mode()`. |
| 4 | Role Loaded | `RESEARCHER` | Because `get_current_user_optional()` returned the stale `RESEARCHER` session user, `require_user()` never invoked `_get_or_create_judge_user_context()`. |
| 5 | Permission Failure | `backend/auth.py:550` (`require_org_access`) | `RESEARCHER` is not in `[PLATFORM_ADMIN, ORG_ADMIN, PRIVACY_OFFICER]` → raised HTTP `403` `"Insufficient role permissions"`. |
| 6 | UI Contradiction | `AppLayout.tsx` vs `Sidebar.tsx` | `AppLayout.tsx` read `authConfig().judge_mode === true` (`LOCAL EVALUATION MODE`), while `Sidebar.tsx` read `api.me()` (stale `RESEARCHER` user) and rendered the old org selector, `RESEARCHER` role, and `Sign out` button. |

---

## 2. Security & Architectural Remediation Plan

1. **Strict Judge Mode Isolation (`backend/auth.py`):**
   - In `get_current_user_optional()` / `require_user()`, when `is_judge_mode()` is `True`, ignore stale browser session cookies and always return the explicit `Local Evaluator` context (`usr-judge-evaluator`, `org-judge-eval`, `ROLE_LOCAL_EVALUATOR`).
   - Enforce `MEDILOCKER_ENV=production` fail-closed guard so Judge Mode can never be enabled in production.
2. **Dedicated Judge Mode Permission Policy (`backend/auth.py`, `backend/main.py`):**
   - Allow `ROLE_LOCAL_EVALUATOR` in Judge Mode to upload, validate, process, inspect clinical/identity/quarantine results, generate reports, and download sanitised bundles, while keeping `records.jsonl` mapping downloads blocked (`403`) and Organisation Mode RBAC untouched.
3. **Upload Hardening & Structured Errors (`backend/main.py`):**
   - Enforce per-file (`25 MB`) and total (`100 MB`) upload limits, duplicate-job race protection (`409`), and structured error codes (`UPLOAD_PERMISSION_DENIED`, `INVALID_FILE_FORMAT`, `FILE_TOO_LARGE`, `INVALID_DATASET`, `MAPPING_RESTRICTED`).
4. **Frontend Judge Mode Alignment (`Sidebar.tsx`, `datasets/page.tsx`):**
   - Hide organisation switcher and `Sign out` in Judge Mode; display `"Local Evaluation Workspace"` and `"Local Evaluator"` consistently.
