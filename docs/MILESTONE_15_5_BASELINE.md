# MEDILOCKER — MILESTONE 15.5 BASELINE AUDIT
**Phase 0 Repository & Evidence Audit**  
**Date:** 2026-11-27  
**Auditor:** Principal Privacy Engineer & Healthcare Security Architect

---

## 1. Executive Summary

This baseline audit evaluates the current MediLocker / GuptKavach repository (`61c237f`) prior to Milestone 15.5 hardening. The system combines:
- An offline, CPU-only Python privacy engine (`starter/main.py` + `starter/raksha_engine/*`).
- A FastAPI backend (`backend/main.py`, `backend/pipeline.py`, `backend/database.py`, `backend/engine_adapter.py`, `backend/auth.py`, `backend/audit.py`).
- A Next.js 16 monochrome dashboard (`frontend/src/app/dashboard/*`, `frontend/src/lib/api.ts`).

While the core anonymization engine performs strongly on the practice benchmark (**0/3,230 PII leaks**, **0/4 canaries leaked**, **4,847/4,855 medical values preserved = 99.84%**), this audit identifies concrete cryptographic, clinical-fidelity, passport-wiring, and risk-map gaps that must be closed with verifiable, non-fabricated implementations.

---

## 2. Existing Implementation & Confirmed Strengths

1. **Core Privacy Engine (`starter/main.py`, `starter/raksha_engine/`)**:
   - Two-pass deterministic pipeline (Pass 1: ingestion, clue extraction, conservative cross-file identity clustering; Pass 2: multilingual PII redaction, HMAC pseudonymisation, keyed date shifting, age/PIN generalisation, k-anonymity suppression, FHIR R4 structural validation, and Privacy Passport emission).
   - Existing test suites pass:
     - `tests/cryptography/test_crypto_security.py`: **13/13 PASSED**
     - `tests/privacy_passport/test_privacy_passport.py`: **19/19 PASSED**
     - `tests/privacy_attacks/test_privacy_attacks.py`: **10/10 PASSED**
     - `tests/clinical_integrity/test_clinical_integrity.py`: **9/9 PASSED**
     - `tests/integration/test_full_pipeline_integration.py`: **3/3 PASSED**
     - `tests/integration/test_dataset_workflow_e2e.py`: **4/4 PASSED**
     - `tests/multilingual/test_multilingual_pii.py`: **18/18 cases PASSED** (`P=1.000, R=1.000, F1=1.000`)
2. **Offline / CPU-Only Compliance**: Zero LLMs, zero generative AI, zero runtime network calls in `starter/main.py`.
3. **UI & Backend Structure**: Monochrome MediLocker UI with `PageHeader`, `StatePanels`, `NOT_RUN`/`NOT_MEASURED` badges, SQLite persistence, and immutable audit logging.

---

## 3. Identified Vulnerabilities & Missing Capabilities

### 3.1 Cryptographic Assurance Gaps (Phase 1)
- **Direct Secret Reuse Without HKDF-SHA256 Domain Separation**: `starter/raksha_engine/privacy.py` passes raw `secret` bytes directly into `hmac.new(secret, patient_key, hashlib.sha256)` for pseudonyms and `hmac.new(secret, b"shift|" + patient_key, hashlib.sha256)` for date shifting. While HMAC-SHA256 is already resistant to length-extension attacks, there is no standard RFC 5869 **HKDF-SHA256** key schedule separating:
  - Patient pseudonyms
  - Identity-linking tokens
  - Manifest integrity
  - Passport authentication / signatures
- **Missing Secret Validation**: `starter/main.py` reads `os.environ.get("RAKSHA_SECRET", "").encode("utf-8")` without rejecting empty/missing secrets or validating minimum strength in strict mode.

### 3.2 Clinical Fidelity & Drift Engine Gaps (Phase 2)
- **Single-Regex Clinical Evaluation in Backend**: `backend/pipeline.py:_evaluate_clinical_integrity()` uses only one regex (`CLINICAL_VALUE_RE`) and hardcodes `modified_values: 0`, then copies the identical `preserved / expected` ratio into `lab_integrity`, `medication_integrity`, `dosage_integrity`, and `vital_integrity`.
- **No Drift / Magnitude Change Detection**: A dosage mutation (e.g., `5 mg` -> `50 mg`) or unit swap is not categorized per clinical domain (medications, dosages, units, frequencies, routes, durations, BP, HR, Temp, SpO2, Hb, glucose, labs, diagnoses, FHIR codes/refs).

### 3.3 Multilingual Contextual PII Intelligence Gaps (Phase 3)
- Needs a dedicated contextual known-good clinical vocabulary & conflict-resolution test suite (`tests/multilingual_intelligence/`) verifying per-language Precision, Recall, F1, and clinical-term false-positive rate (ensuring `Asha Rajput` is redacted while `ASHA worker`, `Dr. Ramesh`, `C/O fever`, `Parkinson's disease`, and `Dolo 650 mg` are preserved without blanket dictionary exemptions).

### 3.4 Privacy Passport Disconnection in Backend (Phase 4)
- `starter/main.py` generates a full `privacy_passport.json` + `dataset_manifest.json` via `starter/raksha_engine/passport.py`, and `starter/verify_passport.py` verifies every file hash in `sanitized/` + manifest root hash + Ed25519 signature.
- However, `backend/pipeline.py` ignores `privacy_passport.json` and constructs a minimal custom payload hashing only `report.json`, and `backend/main.py` verification only checks `report.json` rather than recomputing the full `sanitized/` manifest and detecting altered output files.

### 3.5 Privacy Risk Map Gaps (Phase 5)
- `starter/main.py` computes `LOW`, `MODERATE`, `HIGH`, `CRITICAL` risk counts (`pre_categories` / `post_categories`) and `AttackSimulationSummary` in `report.json`, but `backend/pipeline.py` and `frontend/src/app/dashboard/privacy-intelligence/page.tsx` do not surface the dataset risk map (`LOW`/`MODERATE`/`HIGH`/`CRITICAL`, records requiring mitigation, blocked records, safe explanations, pre- vs post-mitigation risk).

### 3.6 Security Regression Gate & Independent Evaluation (Phases 6 & 7)
- No unified offline security regression gate script (`scripts/security_regression_gate.py`) fails the release gate on canary leaks, raw PII leaks, or clinical corruption.
- No independent held-out multi-hospital synthetic benchmark (`tests/independent_eval/`) separated from tuning data.

---

## 4. Proposed Milestone 15.5 Implementation Plan

1. **Phase 1**: Implement RFC 5869 **HKDF-SHA256** (`hkdf_extract`, `hkdf_expand`, `hkdf_sha256`) in `starter/raksha_engine/crypto.py` with explicit domain separation for pseudonyms, identity-linking tokens, manifest integrity, and passport authentication, plus secret validation and unit tests. Wire `privacy.py` to use HKDF-derived purpose keys deterministically.
2. **Phase 2**: Implement `ClinicalDriftAnalyzer` in `starter/raksha_engine/clinical_validator.py` tracking 14 clinical categories with exact `expected`, `preserved`, `missing`, `modified`, `unexpected`, and `preservation_pct` without storing raw patient text. Wire into `backend/pipeline.py` and add `tests/clinical_drift/`.
3. **Phase 3**: Harden contextual clinical vocabulary & conflict resolution in `starter/raksha_engine/evidence.py` and `names.py`, and create `tests/multilingual_intelligence/` measuring per-language P/R/F1 and clinical-term FPR.
4. **Phase 4**: Connect `backend/pipeline.py` and `backend/main.py` to `starter/raksha_engine/passport.py` and `starter/verify_passport.py` (`verify_passport_bundle`), detecting altered output files and tampered passports. Add `tests/privacy_passport_verification/`.
5. **Phase 5**: Surface the Privacy Risk Map (`LOW`/`MODERATE`/`HIGH`/`CRITICAL`, safe explanations, pre/post mitigation) in `backend/pipeline.py`, `backend/main.py`, and `frontend/src/app/dashboard/privacy-intelligence/page.tsx`.
6. **Phase 6**: Create `scripts/security_regression_gate.py` running all security, clinical, identity, multilingual, canary, attack, determinism, and cryptographic checks offline.
7. **Phase 7**: Create `tests/independent_eval/` with a fresh multi-hospital multilingual synthetic benchmark and record exact metrics.
8. **Phase 8**: Update `frontend/` dashboards (`privacy-intelligence`, `clinical-integrity`, `privacy-passports`), build frontend (`pnpm run build`), run all tests + `validate_output.py` + `check_dev.py` + `check_submission.py`, and author all required Milestone 15.5 docs.
