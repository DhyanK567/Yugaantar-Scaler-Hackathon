# Milestone 17 — Complete Repository Integration Audit

**Project:** MediLocker (GuptKavach / Secret-Wards-ToolKit)  
**Date:** 2026-11-26  

---

## 1. Existing Architecture Inventory

### Frontend (`frontend/src/`)
- **Pages:** `/`, `/faq`, `/pricing`, `/login`, `/register`, `/forgot-password`, `/dashboard`, `/dashboard/datasets`, `/dashboard/organisations`, `/dashboard/privacy-engine`, `/dashboard/privacy-intelligence`, `/dashboard/attack-simulator`, `/dashboard/identity-continuity`, `/dashboard/clinical-integrity`, `/dashboard/privacy-passports`, `/dashboard/research-network`, `/dashboard/audit`, `/dashboard/settings`.
- **Note on Sidebar Routes:** `Sidebar.tsx` currently links to `/dashboard/*`, while Milestone 17 specifies top-level routes (`/datasets`, `/privacy-engine`, `/privacy-intelligence`, `/attack-simulator`, `/organisations`, `/identity-continuity`, `/clinical-integrity`, `/privacy-passports`, `/research-network`, `/audit`, `/settings`) as well as `/dashboard`. Both route groups should work seamlessly (via top-level routes with `AppLayout` or clean redirects/shared components).
- **API Client:** `frontend/src/lib/api.ts` — hardcodes `http://localhost:8000`, has no auth token/session handling, and expects flat response shapes that do not match the current FastAPI backend.

### Backend (`backend/`)
- `backend/main.py` — FastAPI app with CORS `allow_origins=["*"]`.
- `backend/database.py` — SQLite (`data/guptkavach.db`) with 5 tables: `jobs`, `audit_logs`, `organisations`, `research_requests`, `settings`.
- `backend/engine_adapter.py` — Invokes `starter/main.py` via subprocess, parses `records.jsonl` for identity graph, and contains `get_actual_dev_metrics()` which returns **hardcoded static benchmark numbers** instead of reading real job results.

### Offline Privacy Engine (`starter/`)
- `starter/main.py` + `starter/raksha_engine/` (`sanitizer.py`, `patterns.py`, `names.py`, `normalizer.py`, `evidence.py`, `linking.py`, `privacy.py`, `risk_engine.py`, `attacker.py`, `clinical_validator.py`, `quarantine.py`, `crypto.py`, `secure_fs.py`).
- Official evaluation entrypoints: `starter/main.py`, `validate_output.py`, `check_dev.py`, `check_submission.py`.

---

## 2. Gap Analysis

### A. Implemented Functionality
- Offline deterministic privacy engine (`starter/main.py`) with `CONTRACT OK` and `READY TO SUBMIT`.
- SQLite persistence for basic `jobs`, `audit_logs`, `organisations`, `research_requests`.
- Subprocess execution of `starter/main.py` from `backend/engine_adapter.py`.
- Next.js App Router UI shell and MediLocker design system.

### B. Partially Implemented / Disconnected Functionality
1. **Dashboard (`/dashboard`):** `GET /api/dashboard` returns hardcoded `get_actual_dev_metrics()` under `summary`, while the frontend reads top-level flat keys (`total_records`, `sanitised_files`, etc.), causing dashes (`—`) and misleading `"Review required"` / `"⚠ Canary escaped"` states when fields are undefined.
2. **Datasets (`/datasets` & `/dashboard/datasets`):** No `datasets` table in SQLite; `POST /api/jobs` runs synchronously without dataset metadata persistence, organisation association, or multi-stage lifecycle tracking.
3. **Privacy Engine & Intelligence:** `/api/privacy-intelligence` and `/api/threat-lab` return static dev metrics rather than real per-job assessments stored in DB.
4. **Attack Simulator:** `starter/raksha_engine/attacker.py` exists, but `/api/threat-lab` does not execute it on demand against real job outputs.
5. **Identity Continuity:** `parse_identity_continuity_graph` falls back to `test_output/records.jsonl` and returns `{ nodes, edges, ... }`, but doesn't expose match evidence categories, conflict status, or abstentions from DB/job outputs.
6. **Clinical Integrity:** `starter/raksha_engine/clinical_validator.py` exists, but there is no `clinical_reports` table or `/api/clinical/reports` endpoint returning exact numerators/denominators.
7. **Privacy Passports:** No `passports` table, no JSON/HTML downloadable passport generation, and no `/api/passports/{id}/verify` endpoint.
8. **Research Network:** Uses `"Pending"`/`"Approved"`/`"Rejected"` instead of persistent workflow states (`DRAFT`, `SUBMITTED`, `UNDER_REVIEW`, `APPROVED`, `REJECTED`, `EXPIRED`, `COMPLETED`) and lacks RBAC.
9. **Audit Trail:** `audit_logs` lacks actor, role, resource type/id, outcome, and pagination.

### C. Broken / Missing Functionality
1. **Authentication & Session Management:** `/login`, `/register`, `/forgot-password` are frontend-only stubs. No `users`, `sessions`, `memberships`, `otp_challenges`, or `oauth_identities` tables exist.
2. **SMTP Email OTP:** Not implemented.
3. **Google OAuth 2.0 / OIDC:** Not implemented.
4. **RBAC & Organisation Isolation:** Zero backend authorisation checks; any caller can access or mutate any organisation's data.
5. **Frontend/Backend Schema Mismatches:**
   - `GET /api/organisations` returns `{ organisations: [...] }` but `api.ts` expects `Organisation[]`.
   - `GET /api/datasets` returns `{ datasets: [...] }` but `api.ts` expects `Dataset[]`.
   - `GET /api/research/requests` returns `{ requests: [...] }` but `api.ts` expects `ResearchRequest[]`.
   - `GET /api/audit` returns `{ audit_logs: [...] }` but `api.ts` expects `AuditEvent[]`.
   - `POST /api/jobs` returns `{ job_id, status, result }` but `api.ts` expects `JobRecord`.
   - `GET /api/jobs/{id}` returns `{ job: {...} }` but `api.ts` expects `JobRecord`.

### D. Security Gaps
- `CORS allow_origins=["*"]` with `allow_credentials=True` (insecure combination).
- No HttpOnly/SameSite session cookies or Bearer token validation.
- No rate limiting on auth or job endpoints.
- No organisation-level access verification on datasets, jobs, or passports.

---

## 3. Integration Plan
1. **Database Schema & Migrations (`backend/migrations.py` + `backend/database.py`):** Add normalized tables with foreign keys and indexes for `users`, `organisations`, `memberships`, `sessions`, `otp_challenges`, `oauth_identities`, `datasets`, `jobs` (full lifecycle), `job_events`, `privacy_assessments`, `identity_clusters`, `clinical_reports`, `attack_runs`, `passports`, `research_requests`, and `audit_events`. Preserve existing data non-destructively.
2. **Authentication & Security (`backend/auth.py`, `backend/security.py`):**
   - Cryptographic 6-digit Email OTP via `smtplib` (STARTTLS/SSL) with HMAC-SHA256 hashed OTP storage, 5-min expiry, max 5 attempts, 60s resend cooldown, IP+email rate limiting, and anti-enumeration generic responses.
   - Google OAuth 2.0 / OIDC Authorization Code + PKCE + state + nonce + `google-auth` ID token verification + safe account linking.
   - Secure HttpOnly/SameSite session cookies + Bearer token support, RBAC (`PLATFORM_ADMIN`, `ORG_ADMIN`, `PRIVACY_OFFICER`, `RESEARCHER`, `AUDITOR`), and organisation isolation.
3. **Connected Pipeline (`backend/pipeline.py`, `backend/engine_adapter.py`):**
   - Background worker thread executing the real `starter/main.py` engine plus `clinical_validator`, `risk_engine`, `attacker`, and Privacy Passport generation, persisting every stage (`CREATED` -> `VALIDATING` -> `QUEUED` -> `PROCESSING` -> `PRIVACY_ANALYSIS` -> `CLINICAL_VALIDATION` -> `SECURITY_VALIDATION` -> `COMPLETED` / `COMPLETED_WITH_WARNINGS` / `QUARANTINED` / `BLOCKED` / `FAILED`) and emitting `audit_events`.
4. **Unified API Contract (`backend/main.py`):** Expose all Milestone 17 endpoints (`/api/auth/*`, `/api/dashboard/*`, `/api/organisations/*`, `/api/datasets/*`, `/api/jobs/*`, `/api/privacy/*`, `/api/identity/*`, `/api/clinical/*`, `/api/attack-simulator/*`, `/api/passports/*`, `/api/research/*`, `/api/audit/*`, `/api/settings`) while keeping backward-compatible aliases where helpful.
5. **Frontend Integration (`frontend/src/`):** Centralize `api.ts` with `credentials: "include"`, typed models, auth context, real empty/loading/error states (`NOT_RUN`, `NOT_MEASURED`, `PASS`, `WARNING`, `FAILED`, `BLOCKED`), top-level routes + `/dashboard/*` routes, and full OTP + Google Sign-In UI.
6. **Automated Test Suite (`tests/milestone_17/`):** Comprehensive pytest suite covering dashboard empty/populated states, dataset upload/isolation, full pipeline, OTP security, Google OAuth validation, RBAC authorisation, plus official `validate_output.py` and `check_submission.py`.
