# MediLocker — Final Winning-Stretch Remediation Baseline

> **Repository**: `Yugaantar-Scaler-Hackathon-main` (Branch: `feature/guptkavach-privacy-engine`)  
> **Scope**: Phase 1 Baseline Inspection covering Privacy Intelligence Visualisation, Quarantine Transparency, and One-Click Verification.

---

## 1. Existing Architecture & Authoritative Data Sources

### 1.1 Backend Engine & Pipeline
- **Core Privacy Engine (`starter/main.py` & `starter/raksha_engine/`)**:
  - Offline, CPU-only deterministic sanitisation engine.
  - Produces `sanitized/`, `records.jsonl`, and `report.json` preserving the official evaluation contract.
  - `starter/raksha_engine/quarantine.py` provides `QuarantineVault` and `QuarantineMetadata` for encrypted quarantine storage (`quarantine_manifest.jsonl`) with non-sensitive metadata (`rel_path`, `original_sha256`, `quarantine_reason`, `timestamp`, `file_size_bytes`, `is_encrypted`, `cipher_algorithm`).
  - In `starter/main.py`, quarantined files are also recorded in `report.json["files"]` as `{ "input_sha256": ..., "output": null, "status": "quarantined", "reason": "..." }`.
- **Engine Adapter (`backend/engine_adapter.py`)**:
  - `execute_engine()` runs `starter/main.py` via subprocess on the job's input directory and returns `files_total`, `files_sanitized`, `files_quarantined`, `records_processed`, `records_linked`, `identifiers_detected`, `files_report`, `privacy_intelligence`, and `clinical_integrity`.
- **Job Pipeline (`backend/pipeline.py`)**:
  - `execute_job_pipeline()` executes: `VALIDATING` → `PROCESSING` → `PRIVACY_ANALYSIS` → `CLINICAL_VALIDATION` → `SECURITY_VALIDATION` → Release Decision (`APPROVED`, `APPROVED_WITH_WARNINGS`, `QUARANTINED`, `BLOCKED`).
  - `_evaluate_clinical_integrity()` scans `CLINICAL_VALUE_RE` across `input_dir` and `sanitized_dir` and validates FHIR R4 bundles, computing `expected_values`, `preserved_values`, `modified_values`, `missing_values`, `lab_integrity`, `medication_integrity`, `dosage_integrity`, `vital_integrity`, `fhir_integrity`, `fhir_bundles_checked`, and `fhir_bundles_valid`.
  - Persists results to SQLite tables in `backend/database.py`: `jobs`, `job_events`, `privacy_assessments`, `clinical_reports`, `identity_clusters`, `attack_runs`, `passports`, `audit_events`.

### 1.2 Existing APIs (`backend/main.py`)
- `GET /api/jobs` & `GET /api/jobs/{job_id}`: Job execution summaries, counts, and release decisions.
- `GET /api/privacy-intelligence`: Currently returns `status`, `assessments_count`, `total_pii_detected`, `total_residual_leakage`, `canary_status`, `reid_risk_level`, and `assessments` (global org-scoped list).
- `GET /api/clinical/reports`: Returns `clinical_reports` rows.
- `GET /api/threat-lab`: Returns `attack_runs` rows.
- `GET /api/passports`: Returns `passports` rows.
- `GET /api/reports/*.pdf`: Dynamic PDF reporting endpoints via `backend/services/pdf_reporting/`.

### 1.3 Existing Frontend Pages
- `frontend/src/app/dashboard/privacy-intelligence/page.tsx`:
  - Calls `api.privacyIntelligence()` only.
  - Displays a top summary banner and a `Measured Privacy Assessments` table.
- `frontend/src/app/dashboard/privacy-passports/page.tsx`:
  - Calls `api.passports()` only.
  - Displays Privacy Passport cards with Verify Hash, JSON, HTML, and Download PDF actions.

---

## 2. Identified Gaps

### Gap 1: Privacy Intelligence Page Lacks Clinical Fidelity, Drift & Attack Visualisation
- No job/dataset selector to inspect a specific run's metrics independently.
- No Clinical Fidelity Overview (`expected_values`, `preserved_values`, `modified_values`, `missing_values`, lab/medication/dosage/vital/FHIR integrity).
- No Clinical Drift Visualisation comparing input vs output distributions across clinical categories (`medication_dosage`, `blood_pressure`, `glucose`, `temperature`, `spo2`, `other_measurements`) or explicitly reporting `NOT_MEASURED`.
- No Attack Simulation Overview distinguishing `BLOCKED`, `EXPOSED`, `NOT_EXECUTED`, `FAILED`, `INCONCLUSIVE`.
- No Privacy Before vs After comparison or Dataset Release Readiness summary (`PASS`, `PASS_WITH_WARNINGS`, `BLOCKED`).

### Gap 2: Quarantine Transparency Is Incomplete
- `jobs.files_quarantined` records the count of quarantined files, and `report.json["files"]` records quarantined entries during execution, but individual quarantined file metadata is not persisted to a queryable API or displayed in the UI.
- Users and judges cannot inspect why a file was quarantined, which pipeline stage rejected it, whether retry is safe, or what remediation action to take.
- Must strictly enforce zero raw PII/content/sensitive filename/canary exposure in quarantine metadata and zero raw download paths for quarantined artifacts.

### Gap 3: Reproducible One-Command Verification & README Entry Point
- Individual checks exist (`validate_output.py`, `check_dev.py`, `check_submission.py`, `tests/*`), but there is no single script (`scripts/verify_submission.ps1` / `scripts/verify_submission.sh`) that runs the full verification suite and prints a structured pass/fail summary.
- `README.md` does not yet surface `# One-Click Verification` near the top with exact reproducible commands.

---

## 3. Change Risks & Safeguards
- **Risk**: Exposing raw filenames or error tracebacks containing PII in quarantine metadata.  
  **Safeguard**: Generate opaque references (`QRN-<sha256[:10]>`), map exceptions to safe error codes + generic human-readable remediation reasons, and never store or return raw file contents or raw sensitive paths.
- **Risk**: Breaking existing `GET /api/privacy-intelligence` consumers.  
  **Safeguard**: Preserve all existing top-level response fields (`status`, `assessments_count`, `total_pii_detected`, `total_residual_leakage`, `canary_status`, `reid_risk_level`, `assessments`) while adding new structured fields (`jobs`, `selected_job_id`, `clinical_fidelity`, `clinical_drift`, `attack_overview`, `before_after`, `release_readiness`, `last_updated`).
- **Risk**: Fabricating metrics when a job has no clinical or attack run.  
  **Safeguard**: Explicitly return `NOT_MEASURED` / `NOT_EXECUTED` when underlying records are absent.
