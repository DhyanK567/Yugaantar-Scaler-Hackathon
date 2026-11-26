# Milestone 17 — Full Application Integration, Functional Dashboard & Secure Authentication Report

**Project:** MediLocker (GuptKavach / Secret-Wards-ToolKit)  
**Date:** 2026-11-26  

---

## 1. Existing Functionality Discovered
- `starter/main.py` and `starter/raksha_engine/` (deterministic, CPU-only, offline privacy engine).
- `backend/main.py`, `backend/database.py`, `backend/engine_adapter.py` (FastAPI + SQLite metadata + subprocess engine runner).
- Next.js 16.4.6 frontend under `frontend/src/app/`.

## 2. Broken Workflows Repaired
- Eliminated hardcoded benchmark numbers (`get_actual_dev_metrics()`) from `/api/dashboard`, `/api/threat-lab`, and `/api/privacy-intelligence`.
- Fixed frontend/backend schema mismatches across `api.ts` and `backend/main.py`.
- Replaced frontend-only login/register stubs with real backend-enforced SMTP Email OTP and Google OAuth 2.0 / OIDC authentication.
- Connected dataset uploads to persistent multi-stage processing jobs, real privacy/clinical/identity/attack assessments, Privacy Passports, and append-only audit events.

## 3. New & Unified API Endpoints
- **Auth:** `GET /api/auth/config`, `POST /api/auth/register`, `POST /api/auth/otp/request`, `POST /api/auth/otp/verify`, `GET /api/auth/google/login`, `POST /api/auth/google/link`, `GET|POST /api/auth/google/callback`, `GET /api/auth/me`, `POST /api/auth/switch-org`, `POST /api/auth/logout`.
- **Dashboard:** `GET /api/dashboard/overview` (and `/api/dashboard`), `GET /api/dashboard/metrics`, `GET /api/dashboard/recent-jobs`, `GET /api/dashboard/audit-events`.
- **Organisations:** `GET|POST /api/organisations`, `GET /api/organisations/{id}`, `GET /api/organisations/{id}/members`.
- **Datasets & Jobs:** `GET|POST /api/datasets`, `GET|DELETE /api/datasets/{id}`, `GET|POST /api/jobs`, `GET /api/jobs/{id}`, `GET /api/jobs/{id}/events`, `GET /api/jobs/{id}/results`, `GET /api/jobs/{id}/download`.
- **Assessments & Passports:** `GET /api/privacy/assessments`, `GET /api/privacy-intelligence`, `GET /api/identity/clusters`, `GET /api/clinical/reports`, `GET /api/threat-lab`, `POST /api/attack-simulator/run`, `GET /api/passports`, `GET /api/passports/{id}`, `POST /api/passports/{id}/verify`, `GET /api/passports/{id}/download?format=json|html`.
- **Research, Audit & Settings:** `GET|POST /api/research/requests`, `POST /api/research/requests/{id}/approve|reject`, `GET /api/audit/events`, `GET|POST /api/settings`.

## 4. Database Migrations (`backend/database.py`)
Non-destructive schema migration (`m17_v1`) with `PRAGMA foreign_keys = ON` and `WAL` mode:
- `users`, `memberships`, `sessions`, `otp_challenges`, `oauth_identities`, `oauth_states`
- `datasets`, `jobs` (extended lifecycle columns), `job_events`
- `privacy_assessments`, `identity_clusters`, `clinical_reports`, `attack_runs`, `passports`, `audit_events`

## 5. Frontend Pages Connected
- `/login`, `/register`, `/auth/google/callback`
- `/dashboard`, `/dashboard/datasets`, `/dashboard/organisations`, `/dashboard/privacy-engine`, `/dashboard/privacy-intelligence`, `/dashboard/attack-simulator`, `/dashboard/identity-continuity`, `/dashboard/clinical-integrity`, `/dashboard/privacy-passports`, `/dashboard/research-network`, `/dashboard/audit`, `/dashboard/settings`

## 6. Dashboard Metrics & Data Sources
All 6 dashboard cards read from SQLite tables (`datasets`, `jobs`, `privacy_assessments`, `clinical_reports`, `identity_clusters`) scoped to the user's authorised organisations, using explicit states (`NOT_RUN`, `NOT_MEASURED`, `PASS`, `WARNING`, `FAILED`, `BLOCKED`).

## 7. SMTP Email OTP Implementation (`backend/auth.py`)
- Cryptographic 6-digit OTP (`secrets.randbelow`), HMAC-SHA256 hashed storage, 5-minute expiry, max 5 attempts, 60-second resend cooldown, IP + email rate limiting, prior-code invalidation, anti-enumeration generic responses, and no session creation on SMTP failure.

## 8. SMTP Environment Variables
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`, `SMTP_FROM_NAME`, `SMTP_USE_TLS`

## 9. Google OAuth 2.0 / OIDC Implementation (`backend/auth.py`)
- Authorization code flow with PKCE (`S256`), `state` and `nonce` validation, `google.oauth2.id_token.verify_oauth2_token` signature/issuer/audience/expiry/email_verified checks, and safe account-linking protection (blocks automatic takeover of existing unlinked Email OTP accounts).
- Environment variables: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`.

## 10. Security Controls & Role Permissions
- HttpOnly, SameSite=Lax cookies (`Secure` in production), Bearer token support, strict CORS via `FRONTEND_ORIGINS`, SQLite parameterized queries, append-only `audit_events`.
- Roles: `PLATFORM_ADMIN`, `ORG_ADMIN`, `PRIVACY_OFFICER`, `RESEARCHER`, `AUDITOR`.

## 11. Tests Executed & Results
- `tests/milestone_17/test_milestone_17.py`: **12/12 passed** (dashboard empty/populated states, full pipeline + passport verification, canary pass check, invalid uploads, OTP security/lockout/replay/SMTP failure, Google OAuth + account linking protection, RBAC + cross-org isolation).
- `pnpm build` in `frontend/`: **22/22 routes compiled cleanly**.
- `check_submission.py --repo starter`: **`READY TO SUBMIT`**.

## 12. Remaining Limitations
- Privacy Passports emit SHA-256 hash-verified manifests explicitly labelled `UNSIGNED` until an asymmetric PKI signing key is provisioned.
- Offline privacy engine (`starter/main.py`) remains completely decoupled from web authentication and requires zero network access.

## 13. Manual Testing Sequence
1. Configure backend env vars (`SMTP_*`, `GOOGLE_*`, `RAKSHA_SECRET`, `MEDILOCKER_AUTH_SECRET`).
2. Start backend: `.\.venv\Scripts\uvicorn.exe backend.main:app --port 8000`
3. Start frontend: `cd frontend; .\node_modules\.bin\next.cmd start -p 3001`
4. Open `http://localhost:3001/login`, register or sign in via Email OTP (or Google Sign-In).
5. Navigate to `/dashboard/datasets`, select an organisation, upload a synthetic CSV/JSON/TXT dataset, and observe live stage progression.
6. Inspect `/dashboard`, `/dashboard/privacy-intelligence`, `/dashboard/identity-continuity`, `/dashboard/clinical-integrity`, `/dashboard/privacy-passports`, and `/dashboard/audit`.
7. Verify Privacy Passport hash and download JSON/HTML.
8. Sign out via Sidebar and test Google Sign-In.
