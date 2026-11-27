# MEDILOCKER M23 — FINAL REMEDIATION REPORT

**Date:** 2026-11-27  
**FINAL STATUS:** **VERIFIED — READY FOR JUDGE EVALUATION**

---

## 1. Root Cause & Changes Applied

| File | Problem | Root Cause | Fix | Test & Result |
|---|---|---|---|---|
| `backend/auth.py` | `"Insufficient role permissions"` when uploading in Judge Mode; stale `RESEARCHER` role shown | `get_current_user_optional()` read stale `medilocker_session` cookies before checking `is_judge_mode()` | Short-circuit `get_current_user_optional()` in Judge Mode to `_get_or_create_judge_user_context()` (`org-judge-eval`, `ROLE_LOCAL_EVALUATOR`); added dedicated Judge Mode policy in `require_org_access()` | `test_01_judge_mode_ignores_stale_researcher_cookie_and_uploads_cleanly` **PASSED** |
| `backend/main.py` | Frontend-supplied `organisation_id` could collide in Judge Mode; missing size limit cleanup | `upload_dataset` accepted arbitrary `organisation_id` and lacked size-limit cleanup | Force `org-judge-eval` in Judge Mode, enforce `25 MB`/file & `100 MB` total caps with `shutil.rmtree` cleanup on failure | `test_03_edge_cases_empty_and_unsupported_files` **PASSED** |
| `frontend/src/components/layout/Sidebar.tsx` | Displayed stale org selector, `RESEARCHER` role, and `Sign out` during `LOCAL EVALUATION MODE` | `Sidebar` rendered `api.me()` without checking `authConfig().judge_mode` | Hide org switcher and `Sign out` in Judge Mode; show `Local Evaluation Workspace` and `Local Evaluator` | `pnpm run lint` (`0` errors) & `pnpm run build` (`24/24` routes) **PASSED** |
| `frontend/src/app/dashboard/datasets/page.tsx` & `protect-data/page.tsx` | Showed organisation `<select>` in Judge Mode | Missing `judge_mode` UI state | Display static `Local Evaluation Workspace` in Judge Mode | `pnpm run build` **PASSED** |
