# MediLocker PDF Reporting — User Guide

## Operational PDF Reports (Live Persisted Data)

1. **Privacy Passport PDF** (`Privacy Passports` → **Download PDF**)
   - Endpoint: `GET /api/passports/{passport_id}/download?format=pdf`
   - Contains: Passport ID, pseudonymous dataset reference, job ID, organisation, policy version, sanitisation/clinical/identity/risk summary, release decision, and SHA-256 manifest hash.
2. **Privacy Intelligence PDF** (`Privacy Intelligence` → **Export Assessment PDF**)
   - Endpoint: `GET /api/privacy/assessments/{assessment_id}/download?format=pdf`
   - Contains: Assessment ID, risk classification, measured PII redacted vs. residual leaks, canary status, QI categories, methodology, mitigations, and limitations.
3. **Attack Simulation PDF** (`Attack Simulator` → **Download Simulation Report**)
   - Endpoint: `GET /api/attack-simulator/runs/{run_id}/download?format=pdf`
   - Contains: Simulation ID, job ID, records evaluated, vectors blocked, residual distinguishability rate, vector-by-vector table, and limitations.
4. **Clinical Integrity PDF** (`Clinical Integrity` → **Export Clinical Report**)
   - Endpoint: `GET /api/clinical/reports/{report_id}/download?format=pdf`
   - Contains: Exact `preserved / expected` counts, missing/modified counts, medication/dosage/lab/vital integrity, and FHIR R4 Bundle validation status.
5. **Audit Trail PDF** (`Audit Trail` → **Export Audit Report**)
   - Endpoint: `GET /api/audit/export`
   - Contains: Organisation-scoped append-only event ledger with pseudonymous actor references (`ROLE (USR-...)`) and safe resource references.

## Static Submission Brief (`generate_pdf.py`)

`generate_pdf.py` remains preserved at the repository root solely for generating the static 2-page hackathon brief (`starter/GuptKavach_Project_Brief.pdf` and `docs/GuptKavach_Project_Brief.pdf`). It is not imported by the backend API.
