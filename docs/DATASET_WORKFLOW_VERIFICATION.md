# MediLocker — Dataset Processing End-to-End Verification Report

**Date:** 2026-11-26  
**Branch:** `feature/guptkavach-privacy-engine`  

---

## 1. End-to-End Stage Trace

| Stage | API Endpoint / UI Trigger | Backend Function & File |
| --- | --- | --- |
| 1. Dataset Upload & Validation | `POST /api/datasets` (`datasets/page.tsx` → `api.uploadDataset`) | `upload_dataset()` in `backend/main.py` (extension allowlist, non-empty check, SHA-256, `datasets` row) |
| 2. Job Creation & Queueing | `POST /api/datasets` (`auto_process=true`) or `POST /api/jobs` | `_create_and_start_job()` in `backend/main.py` → `launch_job_async()` / `execute_job_pipeline()` in `backend/pipeline.py` |
| 3. Input Validation (`VALIDATING`) | Background/sync job | `execute_job_pipeline()` in `backend/pipeline.py` (checks readable files; empty dataset → `FAILED` / `BLOCKED`) |
| 4. Privacy Engine (`PROCESSING`) | Background/sync job | `execute_engine()` in `backend/engine_adapter.py` → invokes `starter/main.py` CLI (`sanitized/`, `records.jsonl`, `report.json`) |
| 5. Canary & Privacy Analysis (`PRIVACY_ANALYSIS`) | Background/sync job | `_scan_canaries()` in `backend/pipeline.py` + `report.json["privacy_intelligence"]` |
| 6. Clinical & FHIR R4 Validation (`CLINICAL_VALIDATION`) | Background/sync job | `_evaluate_clinical_integrity()` in `backend/pipeline.py` + `validate_fhir_r4_bundle()` + `report.json["clinical_integrity"]` |
| 7. Re-identification & Identity (`SECURITY_VALIDATION`) | Background/sync job | `run_attack_simulation_for_job()` in `backend/pipeline.py` + `parse_identity_continuity_graph()` in `backend/engine_adapter.py` |
| 8. Release Gate | Background/sync job | Release gate in `backend/pipeline.py` (`APPROVED`, `APPROVED_WITH_WARNINGS`, `QUARANTINED`, `BLOCKED`) |
| 9. Bundle Generation & Download | `GET /api/jobs/{job_id}/download` | `download_job_outputs()` in `backend/main.py` (streams ZIP of `sanitized/`, `report.json`, `records.jsonl` only for `APPROVED` / `APPROVED_WITH_WARNINGS`) |
| 10. Audit Events | `GET /api/audit/events` | `record_audit_event()` in `backend/audit.py` (`DATASET_UPLOADED`, `JOB_CREATED`, `JOB_COMPLETED` / `JOB_FAILED`, `BUNDLE_DOWNLOADED`) |

---

## 2. Defects Found & Fixed

1. **Canary Scanner Gap (`backend/pipeline.py` `_scan_canaries`)**:
   - *Before*: Only scanned `sanitized/` for `CANARY_[A-Z0-9_]+`, missing `report.json`, `records.jsonl`, base64-encoded payloads, and labeled `canary:` tokens.
   - *Fix*: Scans `sanitized/` (filenames + content + base64 decoded), `report.json`, and `records.jsonl` for both `CANARY_[A-Z0-9_]+` and labeled canary values.
2. **Release Gate Ignored Engine Risk & FHIR Failures (`backend/pipeline.py`, `backend/engine_adapter.py`)**:
   - *Before*: `execute_job_pipeline` ignored `report.json["privacy_intelligence"]` (`CRITICAL` risk, `release_gate.status`), `clinical_integrity.fhir_validation_passed`, and missing `report.json`/`records.jsonl` artifacts; `reid_risk_level` only checked canary leaks.
   - *Fix*: `execute_engine` now forwards `privacy_intelligence` and `clinical_integrity`; `execute_job_pipeline` blocks release (`BLOCKED`) on missing artifacts, canary leaks, `CRITICAL` risk, `engine_gate == "BLOCKED"`, or `fhir_validation_passed == False`.
3. **Un-gated Bundle Download (`backend/main.py` `download_job_outputs`)**:
   - *Before*: Allowed downloading ZIP bundles even when `release_decision == "BLOCKED"` or `status == "FAILED"`, used OS-native path separators in ZIP entries, and logged no audit event.
   - *Fix*: Enforces `403 Forbidden` unless `release_decision in ("APPROVED", "APPROVED_WITH_WARNINGS")` and `status in ("COMPLETED", "COMPLETED_WITH_WARNINGS")`, requires `report.json` + `records.jsonl`, uses `.as_posix()`, and records `BUNDLE_DOWNLOADED`.
4. **Frontend Datasets Page Staleness & Missing Release Decision (`frontend/src/app/dashboard/datasets/page.tsx`, `frontend/src/lib/api.ts`)**:
   - *Before*: `GET /api/datasets` omitted `latest_release_decision`; switching `Target Organisation` left a stale `activeJob` visible; `Refresh` did not refresh `activeJob`; table rows lacked `latest_job_id`, `latest_release_decision`, and gated `Download Bundle`.
   - *Fix*: Added `latest_release_decision` to `/api/datasets` and `Dataset` type; clears `activeJob` on org switch; refreshes `activeJob` on `Refresh`; gates `Download Bundle` on both `status` and `release_decision`.

---

## 3. Test Commands & Observed Results

```powershell
python -m unittest tests.integration.test_dataset_workflow_e2e -v
```
Result: **`Ran 4 tests in 2.771s — OK`**
- `test_01_clean_dataset_e2e_approved_and_validated`: Clean 6-row CSV (`k >= 5`) → `COMPLETED` / `APPROVED`, `validate_output.py` → `CONTRACT OK`, `Patient0 Kumar` redacted, `Hypertension` & `Amlodipine 5 mg` preserved, `JOB_COMPLETED` audit event recorded.
- `test_02_canary_leak_in_content_base64_or_report_blocks_release`: `note_canary.csv` with `CANARY_TOKEN_9911` and base64-encoded `CANARY_B64_7722` → detected (`FAILED`, `leaks=1`), job set to `BLOCKED` / `BLOCKED`.
- `test_03_empty_unsupported_and_corrupt_files_never_approved`: Empty dataset → `FAILED` / `BLOCKED`; PNG + corrupt JSON → `QUARANTINED` / `QUARANTINED`, `0` raw copies in `sanitized/`.
- `test_04_critical_risk_fhir_failure_and_incomplete_artifacts_block_release`: `CRITICAL` risk + `fhir_validation_passed=False` → `BLOCKED` / `BLOCKED`.

### Environment Note
- `fastapi` and frontend `node_modules` (`tsc`) are not installed in this offline Python stdlib environment, so FastAPI HTTP routes (`403` download gate, `/api/datasets` response) were verified by code inspection and stdlib SQLite/pipeline E2E execution.
