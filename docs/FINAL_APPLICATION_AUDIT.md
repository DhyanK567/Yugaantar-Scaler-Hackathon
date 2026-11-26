# MEDILOCKER / GUPTKAVACH — FINAL APPLICATION AUDIT
**Phase 1 Baseline Audit**  
**Date:** 2026-11-26  
**Scope:** Full-stack inspection of `frontend/`, `backend/`, `starter/`, `data/`, and `tests/`.

---

## 1. Executive Summary

The GuptKavach / MediLocker repository contains a mature, offline, CPU-only Python privacy engine (`starter/main.py` + `starter/raksha_engine/*`), a FastAPI backend (`backend/main.py`, `backend/engine_adapter.py`, `backend/database.py`), and a Next.js control console (`frontend/src/app/page.tsx`).

However, the **application integration between the engine, backend database, API endpoints, and frontend UI is incomplete**:
1. **Engine Runtime Regression on Python 3.8**: `starter/main.py:651` calls `dest.write_text(out_text, encoding="utf-8", newline="")`, which raises `TypeError: write_text() got an unexpected keyword argument 'newline'` on Python 3.8, causing all end-to-end pipeline runs and 5 integration/attack/clinical tests to fail.
2. **Hardcoded Baseline Metrics in Backend**: `backend/engine_adapter.py:get_actual_dev_metrics()` returns a static hardcoded dictionary (`files_total: 200`, `personal_data_leakage_rate: 1.08`, `medical_preservation_rate: 99.96`, etc.) rather than reading actual job outputs (`report.json`, `privacy_passport.json`, `records.jsonl`).
3. **Missing Single Source of Truth**: `jobs` table in `backend/database.py` lacks `dataset_id`, `org_id`, `current_stage`, `stage_history`, `output_dir`, `release_decision`, and assessment references. Switching organisations does not scope dashboard, jobs, datasets, identity, clinical, privacy intelligence, attack simulation, or audit views.
4. **Disconnected Engine Capabilities**: `starter/main.py` already executes `attacker.py` (7 vectors), `risk_engine.py`, `mitigation.py`, `clinical_validator.py`, and `passport.py`, writing `report.json`, `dataset_manifest.json`, `privacy_passport.json`, and `privacy_passport.html` — yet **none of those generated artifacts are served by `backend/main.py` or rendered in `frontend/src/app/page.tsx`**.
5. **Hardcoded / Static UI Sections**:
   - **Privacy Gateway** displays hardcoded `200 Files`, `195 Files Protected`, `5 Files Isolated` and a static 5-row quarantine table instead of actual uploaded/selected dataset & job results.
   - **Threat Laboratory / Attack Simulator** does not display the 7 attack vectors from `attacker.py` (`exact_combination`, `age_gender_location`, `rare_diagnosis_location`, `admission_los`, `geographic_narrowing`, `cross_record_linkage`, `rare_attribute_combination`).
   - **Clinical Integrity** has no dedicated view or backend endpoint exposing `clinical_integrity` from `report.json` or exact probe/FHIR counts.
   - **Privacy Passports** has no API endpoint or UI tab to inspect or verify `privacy_passport.json` / `privacy_passport.html`.
   - **Settings** inputs (`date_shift_max_days`, `min_group_size`, `age_band_width`) are `disabled` and hardcoded to `180`, `5`, `5` instead of reading/updating `/api/settings`.
   - **Research Network** cannot create new requests from the UI (no form wired to `POST /api/research/requests`), and approval does not link to an actual permitted job/dataset output.

---

## 2. Page-by-Page & Module Audit Matrix

### 2.1 Dashboard (`command_centre`)
- **UI Components**: `frontend/src/app/page.tsx` (lines 221–402): 4 KPI cards, 3 status banners, Firewall Processing Jobs table.
- **API Endpoint**: `GET /api/dashboard` (`backend/main.py:80-115`).
- **Backend Service**: `get_actual_dev_metrics()` + `SELECT * FROM jobs ORDER BY created_at DESC LIMIT 5`.
- **Database Tables**: `jobs`.
- **Working Interactions**: Fetches `/api/dashboard` and lists `recent_jobs` if present; download link works if `job_id` exists.
- **Broken Interactions / Missing Functionality**:
  - `get_actual_dev_metrics()` returns hardcoded stale numbers (`99.96%`, `98.92%`, `4,120`, `0.93`) regardless of actual executed jobs.
  - Fallback row `job-practice-baseline` is hardcoded in JSX when `recent_jobs` is empty.
  - No organisation scoping (`org_id`), no release readiness status from `release_gate`, no loading/error/NOT_MEASURED states.
- **Required Integration**: Scope dashboard metrics to selected `org_id` and latest completed job for that org; derive all numbers from actual `report.json` / `privacy_passport.json` stored for the job, or show `NOT_MEASURED` / empty state when no job exists.

### 2.2 Datasets & Privacy Engine / Privacy Gateway (`privacy_gateway`)
- **UI Components**: `frontend/src/app/page.tsx` (lines 456–572): Execute button, 3 static summary cards, static 5-row Quarantine table.
- **API Endpoints**: `GET /api/datasets`, `POST /api/jobs`, `GET /api/jobs/{job_id}`, `GET /api/jobs/{job_id}/download`.
- **Backend Service**: `execute_engine()` in `backend/engine_adapter.py`.
- **Database Tables**: `jobs`, `audit_logs`. (No `datasets` table — datasets are only scanned from `DATASETS_DIR`).
- **Working Interactions**: Clicking "Execute Privacy Engine" calls `POST /api/jobs` with `dataset_id=practice-dev-dataset` and runs `starter/main.py`.
- **Broken Interactions / Missing Functionality**:
  - **No file upload UI** (`<input type="file">`) or dataset selector in the frontend.
  - **No organisation selector** when uploading/registering datasets or running jobs.
  - **No content validation** (only filename sanitization in `backend/main.py:56`, no size/extension/content/archive-traversal validation before registration).
  - **Download endpoint** (`GET /api/jobs/{job_id}/download`) falls back to `DEFAULT_OUTPUT` if `job_output` doesn't exist, and does NOT check `release_decision` before permitting download.
  - Summary cards & quarantine table in UI are hardcoded instead of reading `job.files_report` from `GET /api/jobs/{job_id}`.
- **Required Integration**: Implement `datasets` table + `POST /api/datasets/upload` (with size/extension/content/path validation), dataset registration, job stage tracking, real `files_report` & quarantine reasons display, and release-gated download.

### 2.3 Organisations (`organisations`)
- **UI Components**: `frontend/src/app/page.tsx` (lines 405–453): 2-column grid of organisation cards.
- **API Endpoint**: `GET /api/organisations` (`backend/main.py:123-132`).
- **Database Tables**: `organisations` (seeded with 4 synthetic orgs).
- **Working Interactions**: Lists seeded synthetic organisations.
- **Broken Interactions / Missing Functionality**:
  - No active organisation selector/switcher in the header/sidebar to scope the entire console.
  - No create (`POST /api/organisations`) or edit (`PATCH /api/organisations/{org_id}`) UI or API.
  - Does not show associated datasets, jobs, or org-level metrics; `records_contributed` is static seeded data.
- **Required Integration**: Add global organisation context/switcher, create/edit organisation endpoints & UI, and compute org-level dataset/job/record counts dynamically from DB.

### 2.4 Identity Continuity (`identity_graph`)
- **UI Components**: `frontend/src/app/page.tsx` (lines 575–651): Cluster cards + selected cluster detail panel.
- **API Endpoint**: `GET /api/identity-graph` (`backend/main.py:360-368`).
- **Backend Service**: `parse_identity_continuity_graph()` (`backend/engine_adapter.py:172-279`).
- **Privacy Engine**: `starter/raksha_engine/linking.py`.
- **Working Interactions**: Parses `records.jsonl` and groups by pseudonymous `PSN-XXXXXX` IDs without exposing raw names.
- **Broken Interactions / Missing Functionality**:
  - Frontend calls `/api/identity-graph` without `job_id` or `org_id`, falling back to `DEFAULT_OUTPUT` (`test_output/`), so it can show stale results from another job/org.
  - `parse_identity_continuity_graph` infers org names via hardcoded filename heuristics instead of job/dataset metadata.
  - Does not display abstentions, conflicting evidence counts, unlinked records count, or real evaluated precision/recall (`NOT_MEASURED` when no ground truth).
  - Hardcoded `"False Merge Count: 0"` string in JSX.
- **Required Integration**: Scope `/api/identity-graph` by `org_id`, `dataset_id`, and `job_id`; surface real counts (total records, clusters, matched, unlinked, abstentions, conflicts, cross-hospital links, and `NOT_MEASURED` for precision/recall unless test ground truth is provided).

### 2.5 Clinical Integrity (Missing Dedicated Tab & Endpoint)
- **UI Components**: None dedicated (only a static `"99.96%"` card on Dashboard and `"VALID / 100%"` FHIR card in Threat Lab).
- **API Endpoint**: None.
- **Privacy Engine**: `starter/raksha_engine/clinical_validator.py` + `clinical_integrity` section in `report.json` (`fhir_bundles_checked`, `fhir_resources_checked`, `fhir_validation_passed`, `fhir_failures`).
- **Broken Interactions / Missing Functionality**:
  - No `/api/clinical-integrity` endpoint.
  - No UI tab/view for Clinical Integrity.
  - Exact numerator/denominator (`preserved / expected`) for medications, dosages, labs, vitals, and FHIR integrity are not computed/stored per job or shown in UI.
- **Required Integration**: Compute/store clinical integrity metrics per job (exact numerator/denominator or `NOT_MEASURED` when ground truth is absent, plus real FHIR R4 validation counts), add `GET /api/clinical-integrity` (scoped by `job_id`/`org_id`), and add a dedicated Clinical Integrity view in the frontend.

### 2.6 Privacy Intelligence (`privacy_intelligence`)
- **UI Components**: `frontend/src/app/page.tsx` (lines 790–858): 4 static trade-off cards + 3 static before/after sample cards.
- **API Endpoint**: `GET /api/privacy-intelligence` (`backend/main.py:400-443`).
- **Privacy Engine**: `starter/raksha_engine/risk_engine.py`, `mitigation.py`, `privacy_utility.py`, `qi_classifier.py`.
- **Broken Interactions / Missing Functionality**:
  - Backend returns hardcoded `get_actual_dev_metrics()` values (`< 0.05% Risk`, `±180 Days`, `5-Year Bands`, `k >= 5`) and static `before_after_samples`.
  - Actual `privacy_intelligence` from `report.json` (`release_gate`, `risk_summary`, `mitigation_actions`, `field_tier_counts`, `records_below_min_group_pre/post`) is completely ignored.
  - Direct/residual PII leakage shows static values instead of `NOT_MEASURED` when ground-truth leakage evaluation was not run.
  - No `job_id` or `org_id` filter.
- **Required Integration**: Read `privacy_intelligence` from the selected job's `report.json`; distinguish measured metrics, estimated risk index, and `NOT_MEASURED` metrics; add job/org filters.

### 2.7 Attack Simulator / Threat Laboratory (`threat_lab`)
- **UI Components**: `frontend/src/app/page.tsx` (lines 654–787): Canary card, hardcoded Latin/Devanagari/Hinglish bars, hardcoded 0.0% hidden channels, and `pii_detection_rules` table from static `get_actual_dev_metrics()`.
- **API Endpoint**: `GET /api/threat-lab` (`backend/main.py:371-397`).
- **Privacy Engine**: `starter/raksha_engine/attacker.py` implements 7 vectors:
  1. `exact_combination`
  2. `age_gender_location`
  3. `rare_diagnosis_location`
  4. `admission_los`
  5. `geographic_narrowing`
  6. `cross_record_linkage`
  7. `rare_attribute_combination`
- **Broken Interactions / Missing Functionality**:
  - Frontend/Backend **do not execute or display** the 7 attack vectors from `attacker.py`!
  - Threat Lab displays hardcoded `0.0%` leakage and `ZERO LEAKS` canary status even for newly uploaded jobs where canaries were not tested.
  - No per-vector breakdown (records tested, records at risk before mitigation, records at risk after mitigation, mitigation applied, residual risk, execution timestamp, status `BLOCKED` / `AT_RISK` / `NOT_TESTED` / `NOT_RUN`).
  - No button to re-run attack simulation on a job's sanitised output.
- **Required Integration**: Add `POST /api/attacks/run` and `GET /api/attacks` (and/or include in `/api/threat-lab`) that runs `simulate_attacks` against actual pre/post profiles of the sanitised job, persists per-vector results, and accurately reports `BLOCKED`, `AT_RISK`, `NOT_TESTED`, or `NOT_RUN`.

### 2.8 Privacy Passports (Missing UI Tab & Endpoint)
- **UI Components**: None.
- **API Endpoint**: None.
- **Privacy Engine**: `starter/raksha_engine/passport.py` & `passport_report.py` generate `privacy_passport.json`, `privacy_passport.html`, and `dataset_manifest.json` on every `starter/main.py` run; `starter/verify_passport.py` verifies integrity.
- **Broken Interactions / Missing Functionality**:
  - Passports generated by `starter/main.py` are sitting on disk in `job_output/` and are completely invisible in the web app.
  - No verification endpoint (`POST /api/passports/{job_id}/verify`).
  - No UI view to inspect Passport ID, manifest hashes, assessment summaries, release decision, signature/unsigned status, and disclaimer distinguishing evidence documents from external certification.
- **Required Integration**: Persist passport references per job, expose `GET /api/passports`, `GET /api/passports/{job_id}`, and `POST /api/passports/{job_id}/verify`, and add a Privacy Passports tab to the frontend.

### 2.9 Research Network (`research_collab`)
- **UI Components**: `frontend/src/app/page.tsx` (lines 861–943): Lists seeded requests with Approve/Reject buttons.
- **API Endpoints**: `GET /api/research/requests`, `POST /api/research/requests`, `POST /api/research/requests/{req_id}/approve`, `POST /api/research/requests/{req_id}/reject`.
- **Database Tables**: `research_requests`.
- **Working Interactions**: Approve and Reject buttons update SQLite and insert an audit log.
- **Broken Interactions / Missing Functionality**:
  - No UI modal/form to create a new research request (`POST /api/research/requests`).
  - Requests are not linked to actual `dataset_id` / `job_id` or permitted sanitised output references.
  - Reject action does not insert an audit log entry.
  - No download/reference link to approved sanitised output.
- **Required Integration**: Add request creation form, link requests to real datasets/approved jobs, record audit events on create/approve/reject, and expose permitted output reference only when approved.

### 2.10 Audit Trail (`trust_audit`)
- **UI Components**: `frontend/src/app/page.tsx` (lines 946–1008): Audit table.
- **API Endpoint**: `GET /api/audit`.
- **Database Tables**: `audit_logs`.
- **Working Interactions**: Displays `audit_logs` from SQLite.
- **Broken Interactions / Missing Functionality**:
  - Missing `event_id`, `actor`, `org_id`, `resource_id`, `outcome`, `safe_metadata` columns.
  - Most operations (dataset upload, validation, quarantine, attack simulation, passport generation, settings update, bundle download, research create/reject) do NOT write audit logs.
  - No filtering by `org_id` or `event_type`; no append-only protection / tamper-evident hash chain.
- **Required Integration**: Expand `audit_logs` schema (via safe migration), log all lifecycle events, enforce append-only (no update/delete endpoints), and add org/event filtering in UI.

### 2.11 Settings (`settings`)
- **UI Components**: `frontend/src/app/page.tsx` (lines 1011–1085): Static disabled inputs (`180`, `5`, `5`) and static `<pre>` YAML block.
- **API Endpoints**: `GET /api/settings`, `POST /api/settings`.
- **Broken Interactions / Missing Functionality**:
  - Inputs are `disabled` and hardcoded; `POST /api/settings` is never called by the frontend.
  - `POST /api/settings` does not log an audit event, does not validate bounds, and does not show encryption/secret configuration status, processing limits, retention settings, or offline mode status.
- **Required Integration**: Bind Settings UI to `GET /api/settings` and `POST /api/settings` (editable parameters with validation & save feedback), display secret/encryption/offline status without revealing secrets, and log policy updates to `audit_logs`.

---

## 3. Baseline Test Execution Findings

Running existing tests prior to integration modifications revealed:
- `tests/cryptography/test_crypto_security.py`: **13/13 PASSED**.
- `tests/privacy_passport/test_privacy_passport.py`: **19/19 PASSED**.
- `tests/privacy_attacks/test_privacy_attacks.py`: **9/10 PASSED**, 1 FAILED (`test_10_end_to_end_determinism_fhir_malformed_and_no_pii_leaks`).
- `tests/clinical_integrity/test_clinical_integrity.py`: **8/9 PASSED**, 1 FAILED (`test_09_csv_edge_cases_and_malformed_quarantine_e2e`).
- `tests/integration/test_full_pipeline_integration.py`: **0/3 PASSED**, 3 FAILED.

**Root Cause of all 5 failures:**
`starter/main.py:651` calls `dest.write_text(out_text, encoding="utf-8", newline="")`. `Path.write_text` does not accept `newline` in Python 3.8. Fixing this to `with open(dest, "w", encoding="utf-8", newline="") as f: f.write(out_text)` will restore 100% of the end-to-end engine tests.

---

## 4. Prioritized Integration Plan

1. **Fix `starter/main.py:651` Python 3.8 compatibility** and verify all existing engine tests pass.
2. **Phase 2 (Single Source of Truth DB Schema)**: Upgrade `backend/database.py` with idempotent schema migrations for `organisations`, `datasets`, `jobs` (with `dataset_id`, `org_id`, `current_stage`, `stage_history`, `output_dir`, `release_decision`, assessment refs), `attack_runs`, `passports`, `research_requests`, and `audit_logs`.
3. **Phase 3 & 4 (Dataset Workflow & Privacy Engine)**: Implement `POST /api/datasets/upload`, content/size/path validation, job stage execution, safe evidence records, and release-gated bundle download.
4. **Phase 5, 6, 7, 8 (Identity, Clinical, Intelligence, Attack Simulator)**: Replace all hardcoded `get_actual_dev_metrics()` calls with real per-job artifact readers (`report.json`, `records.jsonl`, `privacy_passport.json`) + real `attacker.py` execution & `NOT_MEASURED` / `NOT_TESTED` / `NOT_RUN` semantics.
5. **Phase 9, 10, 11, 12 (Passports, Research, Audit, Orgs, Settings)**: Expose Passport viewer/verifier, Research request creation & output linking, full Audit logging, Org CRUD + global org switcher, and editable Settings.
6. **Phase 13 & 14 (Frontend Integration)**: Update `frontend/src/app/page.tsx` cleanly (preserving the dark-navy/cyan console design) with all 12 navigation views/modules wired to real backend APIs, org switching, job selector, loading/error/empty/`NOT_MEASURED` states.
7. **Phase 15–17 (End-to-End Testing & Official Compliance)**: Build multi-hospital E2E integration tests, verify `check_submission.py`, `validate_output.py`, `check_dev.py`, and author `docs/FINAL_APPLICATION_INTEGRATION_REPORT.md`.
