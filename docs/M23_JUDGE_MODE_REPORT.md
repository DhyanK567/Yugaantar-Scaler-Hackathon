# MEDILOCKER M23 — JUDGE MODE ARCHITECTURE REPORT

**Date:** 2026-11-27

---

## 1. Mode Separation

- **`MEDILOCKER_MODE=judge` (`MEDILOCKER_ENV=development`):**
  - `backend/auth.py:get_current_user_optional()` short-circuits before reading any browser `medilocker_session` cookie and returns `_get_or_create_judge_user_context()` (`usr-judge-evaluator`, `org-judge-eval` `"Local Evaluation Workspace"`, role `ROLE_LOCAL_EVALUATOR`).
  - `backend/auth.py:require_org_access()` enforces a dedicated Judge Mode policy: requests are confined to `org-judge-eval` and authorised for upload, processing, reports, and bundle downloads, while `/api/jobs/{id}/mapping` (`records.jsonl`) remains blocked (`403`).
  - Frontend `Sidebar.tsx`, `datasets/page.tsx`, `protect-data/page.tsx`, and `AppLayout.tsx` display `LOCAL EVALUATION MODE`, `Local Evaluation Workspace`, and `Local Evaluator`, hiding `Sign out` and organisation selectors.
- **`MEDILOCKER_MODE=organisation` (or `MEDILOCKER_ENV=production`):**
  - `MEDILOCKER_ENV=production` always forces `organisation` mode.
  - Preserves full session validation, RBAC (`RESEARCHER` upload blocked with `403`), cross-organisation isolation, and audit logging.
