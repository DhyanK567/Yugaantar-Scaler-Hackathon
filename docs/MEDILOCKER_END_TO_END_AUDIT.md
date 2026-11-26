# MEDILOCKER — END-TO-END CROSS-SYSTEM AUDIT

**Audit Date:** 2026-11-27  
**Branch / Commit:** `milestone-8/security-audit` (`6d3f49e` / `7b12b82`)  
**Auditor Role:** Independent Principal Software & Privacy Auditor

---

## 1. Cross-System Architecture & Data Flow Verification

| Stage | Component | Verified Mechanism | Status |
|---|---|---|---|
| 1. Authentication & Session | `backend/auth.py` | Cookie-backed session tokens (`require_user`), OTP & optional Google OAuth (`503` when disabled) | VERIFIED |
| 2. Organisation Scoping | `backend/main.py` | `_authorised_org_ids(user)` + `_org_filter_clause()` enforced across endpoints | VERIFIED |
| 3. Dataset Upload & Storage | `backend/main.py`, `backend/pipeline.py` | Files stored under `MEDILOCKER_DATA_DIR` (`datasets/`, `jobs/`) | VERIFIED |
| 4. Engine Invocation | `backend/engine_adapter.py` | Subprocess execution of `starter/main.py` with `TRANSFORMERS_OFFLINE=1` | VERIFIED |
| 5. Two-Pass Privacy Engine | `starter/main.py`, `starter/raksha_engine/` | Ingestion, clustering, redaction, HKDF/HMAC pseudonymisation, k-anonymity, FHIR R4 check | VERIFIED |
| 6. Clinical Drift Analysis | `backend/pipeline.py` -> `analyze_clinical_drift()` | 15-category clinical drift detection (`modified_values > 0` triggers `BLOCKED`) | VERIFIED |
| 7. Risk Map & Attack Sim | `backend/pipeline.py` -> `simulate_attacks()` | `LOW`/`MODERATE`/`HIGH`/`CRITICAL` risk map persisted in `privacy_assessments` | VERIFIED |
| 8. Privacy Passport Emission | `starter/raksha_engine/passport.py` | Emits `dataset_manifest.json`, `privacy_passport.json`, `privacy_passport.html` | VERIFIED |
| 9. Passport Verification | `backend/main.py` -> `verify_passport_bundle()` | Recomputes streaming SHA-256 across `sanitized/` files and checks root hash & signature | VERIFIED |
| 10. Immutable Audit Log | `backend/audit.py` | Append-only `audit_events` recording auth, job completion, and passport verification | VERIFIED |

---

## 2. Dashboard 12-Page Functionality Matrix

| # | Dashboard Page | Backend Endpoint / API Client Method | Real Data Source | Interactive Actions Verified | Status |
|---|---|---|---|---|---|
| 1 | `/dashboard` (`page.tsx`) | `api.dashboard`, `api.me` | SQLite (`jobs`, `privacy_assessments`, `clinical_reports`, `identity_clusters`) | Overview telemetry & navigation | VERIFIED |
| 2 | `/dashboard/datasets` (`page.tsx`) | `api.datasets`, `api.uploadDataset`, `api.getJob`, `api.downloadJobUrl`, `api.deleteDataset` | `datasets` & `jobs` tables + filesystem | Upload, inspect job, download sanitized ZIP, delete | VERIFIED |
| 3 | `/dashboard/privacy-engine` (`page.tsx`) | `api.jobs`, `api.settings` | `jobs` & `settings` | Inspect engine runs & policy settings | VERIFIED |
| 4 | `/dashboard/privacy-intelligence` (`page.tsx`) | `api.privacyIntelligence` | `privacy_assessments` (`risk_map` JSON) | Risk map & leakage telemetry | VERIFIED |
| 5 | `/dashboard/identity-continuity` (`page.tsx`) | `api.identityGraph` | `identity_clusters` (`graph_json`) | Cross-hospital cluster graph & metrics | VERIFIED |
| 6 | `/dashboard/clinical-integrity` (`page.tsx`) | `api.clinicalReports` | `clinical_reports` | 15-category drift & FHIR R4 integrity | VERIFIED |
| 7 | `/dashboard/attack-simulator` (`page.tsx`) | `api.threatLab`, `api.jobs`, `api.runAttackSimulator` | `attack_runs` + `simulate_attacks()` | Select job & run re-identification attack simulation | VERIFIED |
| 8 | `/dashboard/privacy-passports` (`page.tsx`) | `api.passports`, `api.verifyPassport`, `api.downloadPassportUrl`, `api.downloadPdf` | `passports` + `verify_passport_bundle()` | Verify integrity on disk, download JSON/PDF | VERIFIED |
| 9 | `/dashboard/organisations` (`page.tsx`) | `api.organisations` | `organisations` & `memberships` | View authorised organisations & counts | VERIFIED |
| 10 | `/dashboard/research-network` (`page.tsx`) | `api.researchRequests`, `api.createResearchRequest`, `api.approveResearch`, `api.rejectResearch` | `research_requests` | Create, approve, and reject research access requests | VERIFIED |
| 11 | `/dashboard/audit` (`page.tsx`) | `api.auditEvents` | `audit_events` | Paginated immutable ledger & refresh | VERIFIED |
| 12 | `/dashboard/settings` (`page.tsx`) | `api.settings`, `api.updateSettings`, `api.diagnostics`, `api.briefPdfUrl` | Runtime config & diagnostics | Update settings, run diagnostics, download brief PDF | VERIFIED |

---

## 3. Cross-System Discrepancies Found

1. **Filename PII Leakage in `dev/input` (`check_dev.py`) vs `MILESTONE_15_5_REPORT.md`:**
   - `MILESTONE_15_5_REPORT.md` claims `0 / 3,230 (0.0%)` personal data leaked, `4,847 / 4,855` medical values kept, and `R=0.81, F0.5=0.95`.
   - Independent execution of `starter/main.py` + `check_dev.py` measured `35 / 3,230 (1.1%)` personal data leaked (all 35 in `filename`, e.g., `MRN 24/850`, `PATIENT_NAME 6/962`, `PHONE 5/308`), `4,449 / 4,457 (99.8%)` medical values kept, and `P=1.00, R=0.76, F0.5=0.94`.
2. **Legacy Script `test_guptkavach_system.py`:**
   - Fails checks 9 and 10 (`9 PASSED, 2 FAILED`) because it calls `/api/dashboard/overview` without authenticating first (HTTP `401` is expected behavior under Milestone 14/17 auth).
