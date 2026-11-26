# MEDILOCKER — FINAL INDEPENDENT TECHNICAL & SUBMISSION READINESS AUDIT

**Audit Date:** 2026-11-27  
**Target Branch / Commit:** `milestone-8/security-audit` (`6d3f49e` / `7b12b82`)  
**Track:** Yugaantar DevForge Track 3 — Secret Wards  
**Auditor Role:** Independent Principal Software Auditor & Healthcare Privacy Engineer

---

## A. Executive Summary & Overall Verdict

**Overall Verdict:** **PARTIALLY VERIFIED / CONDITIONAL PASS WITH CRITICAL DOCUMENTATION & FILENAME-LEAKAGE FINDINGS**

The MediLocker / GuptKavach platform genuinely implements an offline, CPU-only, non-LLM healthcare privacy engine (`starter/main.py` + `starter/raksha_engine/*`), HKDF-SHA256 domain-separated cryptography (`starter/raksha_engine/crypto.py`), 15-category clinical drift detection (`analyze_clinical_drift`), live verifiable Privacy Passports (`starter/raksha_engine/passport.py` + `verify_passport_bundle`), and a 12-page Next.js + FastAPI console.

However, an independent execution of the official dev benchmark (`starter/main.py` + `check_dev.py`) uncovered **two material gaps** that prevent an unconditional pass:
1. **Unredacted Filenames (`35 / 3,230` PII leaks = `1.1%`)**: `check_dev.py` detected 24 MRNs, 6 patient names, and 5 phone numbers leaking inside output **filenames** (`by hiding place: content 0.0%, filename 72.9%`), contradicting the `0 / 3,230 (0.0%)` claim in `docs/MILESTONE_15_5_REPORT.md`.
2. **Stale / Inconsistent Metrics in `docs/MILESTONE_15_5_REPORT.md` & `docs/MILESTONE_15_5_BASELINE.md`**: Claimed `4,847 / 4,855` medical values and `R=0.81, F0.5=0.95` linking do not match the actual measured `4,449 / 4,457` medical values and `R=0.76, F0.5=0.94` linking on `dev/input`.

---

## B. Track 3 Non-Negotiable Hackathon Rules Compliance

| # | Rule | Evidence | Status |
|---|---|---|---|
| 1 | Fully offline execution | `HF_HUB_OFFLINE=1` & `TRANSFORMERS_OFFLINE=1` clean worktree run succeeded (`CONTRACT OK`) | PASS |
| 2 | CPU-only processing | Pure Python stdlib + CPU FastAPI/SQLite; no GPU dependencies | PASS |
| 3 | No LLMs or generative models | Security sweep across `starter/`, `backend/`, `desktop/*.js` found 0 LLM/AI imports | PASS |
| 4 | No hosted AI APIs | 0 `openai`/`anthropic`/`huggingface` references in engine or backend | PASS |
| 5 | No pretrained transformers > 50M | `starter/requirements.txt` uses stdlib only; 0 transformer models | PASS |
| 6 | No internet dependency during eval | `starter/main.py` & `tests/independent_eval/run_independent_eval.py` run offline | PASS |
| 7 | No real patient data | Synthetic benchmark (`dev/input`, `tests/independent_eval/`) only | PASS |
| 8 | No raw PII/secrets in logs/reports | `check_submission.py`: `RAKSHA_SECRET is never written to output or logs`; `0` content leaks | PASS |
| 9 | No silently skipped files | `validate_output.py`: `files 200 sanitized 195 quarantined 5 records 823` | PASS |
| 10 | No raw input copied into sanitized | `check_dev.py`: `RAW COPIES: 0` | PASS |
| 11 | Deterministic pseudonymisation | `check_submission.py`: `same secret twice -> identical sanitized/ and records.jsonl` | PASS |
| 12 | Different secrets -> different output | `check_submission.py`: `different secret -> different output` | PASS |
| 13 | Preserve clinically meaningful info | `check_dev.py`: `4449 / 4457 (99.8%)`; `independent_eval`: `36 / 36 (100.0%)` | PASS |
| 14 | Avoid false patient identity merges | `check_dev.py`: `precision 1.00 (false merges: 0)` | PASS |
| 15 | Follow official input/output contract | `validate_output.py`: `CONTRACT OK` | PASS |

---

## C. 12-Item Final Verification Checklist

| Check | Item | Status | Evidence Summary |
|---|---|---|---|
| **CHECK 1** | Baseline Audit Completed and Reviewed | **PARTIALLY VERIFIED** | `MILESTONE_15_5_BASELINE.md` and `MILESTONE_15_5_REPORT.md` exist and match architecture, but contain stale benchmark numbers (`0/3230` leaks, `4847/4855` clinical, `R=0.81`) that contradict current `check_dev.py` output (`35/3230` filename leaks, `4449/4457` clinical, `R=0.76`). |
| **CHECK 2** | Cryptographic Tests Passed | **VERIFIED** | `crypto.py` implements RFC 5869 `hkdf_extract`/`hkdf_expand`/`hkdf_sha256` with 5 domain labels + `validate_secret()`. Regression gate `Cryptographic Assurance` passed (`0` exit code). |
| **CHECK 3** | Clinical Integrity & Drift Tests Passed | **VERIFIED** | `analyze_clinical_drift()` wired into `backend/pipeline.py` (line 140); gates `Clinical Fidelity & Drift Engine` and `Clinical Integrity & FHIR R4 Validation` passed. |
| **CHECK 4** | Multilingual PII & Clinical Preservation | **VERIFIED** | Gates `Multilingual Contextual PII Intelligence` and `Multilingual Benchmark Evaluator` passed; `check_dev.py` shows `deva 0.0%, hinglish 0.0%`. |
| **CHECK 5** | Privacy Passport Generation & Tamper Rejection | **VERIFIED** | `passport.py` + `verify_passport_bundle()` wired in `backend/pipeline.py` and `backend/main.py` (line 1492); `Live Verifiable Privacy Passport` and `Privacy Passport Core Suite` gates passed. |
| **CHECK 6** | Re-Identification Attack Simulator | **VERIFIED** | `simulate_attacks()` wired into `backend/pipeline.py` & `/api/attack-simulator/run`; `Re-Identification Attack Simulator` gate passed. |
| **CHECK 7** | End-to-End Backend & 12-Page UI Wiring | **VERIFIED** | All 12 `frontend/src/app/dashboard/**/page.tsx` routes wired to live `api.*` endpoints; `tests/milestone_17/test_milestone_17.py` + `tests/milestone_18/test_offline_verification.py` (`16 passed`). |
| **CHECK 8** | Security Sweep & Offline Compliance | **VERIFIED** | Targeted sweep of `starter/`, `backend/`, `desktop/*.js` found 0 LLM/AI imports, 0 `shell=True`/`eval`/`exec`. Legacy `test_guptkavach_system.py` fails 2 unauthenticated calls (`401` is expected auth behavior). |
| **CHECK 9** | Official Dev Benchmark (`check_dev.py` & `validate_output.py`) | **PARTIALLY VERIFIED** | `validate_output.py` returned `CONTRACT OK` (`files 200 sanitized 195 quarantined 5 records 823`), but `check_dev.py` reported `35 / 3,230 (1.1%)` PII leaks in **filenames** (`MRN 24/850`, `PATIENT_NAME 6/962`, `PHONE 5/308`). |
| **CHECK 10** | Official Submission Checker (`check_submission.py`) | **VERIFIED** | `python check_submission.py --repo starter --run` exited `0` (`READY TO SUBMIT` in `17.3s`, `CONTRACT OK`). |
| **CHECK 11** | Project Brief PDFs & Repo Packaging | **VERIFIED** | `submission/MediLocker_Project_Brief.pdf` (120,232 bytes, 2 pages), `starter/GuptKavach_Project_Brief.pdf` (8,403 bytes, 2 pages), `raksha.toml`, and `starter/raksha.toml` present and valid. |
| **CHECK 12** | Clean `git worktree` Offline Reproducibility | **VERIFIED** | Clean detached worktree at `6d3f49e` with `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` ran `starter/main.py` + `validate_output.py` with exit code `0` (`CONTRACT OK`). |

---

## D. Exact Executed Commands & Measured Outputs

1. **Automated Security Regression Gate (`.\.venv\Scripts\python.exe scripts/security_regression_gate.py`)**
   - **Exit Code:** `0`
   - **Output:** `GATE STATUS: PASSED (10/10 gates passed) in 38.85s`
2. **Independent Held-Out Evaluation (`.\.venv\Scripts\python.exe tests/independent_eval/run_independent_eval.py`)**
   - **Exit Code:** `0`
   - **Output:** `direct_pii_probes_tested: 10`, `direct_pii_leaked: 0`, `canaries_planted: 2`, `canaries_leaked: 0`, `pre_uniquely_distinguishable: 6`, `post_uniquely_distinguishable: 0`, `expected: 36`, `preserved: 36`, `exact_fidelity_pct: 100.0`, `files_total: 5` (`4 sanitized, 1 quarantined`), `runtime_secs: 1.304`, `peak_rss_mb: 29.64`, `release_decision: PASS`.
3. **Milestone 17 & 18 Pytest Suite (`.\.venv\Scripts\python.exe -m pytest tests/milestone_17/test_milestone_17.py tests/milestone_18/test_offline_verification.py test_guptkavach_system.py -v`)**
   - **Exit Code:** `0`
   - **Output:** `16 passed, 1 warning in 22.49s` (13 M17 tests + 3 M18 tests).
4. **Legacy System Script (`.\.venv\Scripts\python.exe test_guptkavach_system.py`)**
   - **Exit Code:** `1`
   - **Output:** `SUMMARY: 9 PASSED, 2 FAILED` — Checks 9 & 10 failed with HTTP `401` because the script queries `/api/dashboard/overview` without authenticating.
5. **Official Engine + Validator + Dev Check (`starter/main.py`, `validate_output.py`, `check_dev.py`)**
   - **Exit Code:** `0`
   - `validate_output.py`: `files 200 sanitized 195 quarantined 5 records 823`, `CONTRACT OK`
   - `check_dev.py`:
     - Personal data leaked: `35 / 3230 (1.1%)` — `MRN 24/850 (2.8%)`, `PATIENT_NAME 6/962 (0.6%)`, `PHONE 5/308 (1.6%)`, all in `filename` (`content 0.0%, filename 72.9%`)
     - Canaries leaked: `0 / 4`
     - Medical data kept: `4449 / 4457 (99.8%)`
     - Patient linking: `precision 1.00, recall 0.76, F0.5 0.94 (false merges: 0)`
     - Raw copies: `0`
6. **Official Submission Checker (`.\.venv\Scripts\python.exe check_submission.py --repo starter --run`)**
   - **Exit Code:** `0`
   - **Output:** `READY TO SUBMIT` (`17.3s`, `CONTRACT OK`).
7. **Clean Git Worktree Offline Check (`HEAD 6d3f49e`, `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`)**
   - **Exit Code:** `0`
   - **Output:** `files 200 sanitized 195 quarantined 5 records 823`, `CONTRACT OK`.

---

## E. Security & Integrity Findings

- **HIGH — Filename PII Leakage (`35 / 3,230`):** `starter/main.py` leaves patient names, MRNs, and phone numbers in sanitized output filenames (e.g., `discharge/Discharge_Summary_Reena_Nishad_JJH-0076928.txt`, `lab/7585697553_report_0010.json`). While `validate_output.py` passes `CONTRACT OK`, `check_dev.py` flags these as PII leaks.
- **MEDIUM — Stale Documentation Metrics:** `docs/MILESTONE_15_5_BASELINE.md` and `docs/MILESTONE_15_5_REPORT.md` state `0 / 3,230` leaks and `4,847 / 4,855` medical values, which do not match current measured outputs.
- **LOW — Legacy Unauthenticated Test Script:** `test_guptkavach_system.py` expects unauthenticated access to `/api/dashboard/overview` and fails with `401`.
- **INFO — Unsigned Passports by Default:** Passports default to `UNSIGNED` when no Ed25519 key env var (`GUPTKAVACH_SIGNING_KEY_PATH` / `GUPTKAVACH_SIGNING_KEY_PEM`) is provided; SHA-256 manifest verification remains active.

---

## F. Recommended Fixes (Awaiting User Approval)

1. **Sanitize Output Filenames in `starter/`:** Redact/pseudonymise patient names, MRNs, and phone numbers in output relative paths/filenames while preserving directory structure and extensions expected by `validate_output.py`.
2. **Update `docs/MILESTONE_15_5_BASELINE.md` & `docs/MILESTONE_15_5_REPORT.md`:** Align reported numerators/denominators with exact measured `check_dev.py` results after filename sanitization.
3. **Update `test_guptkavach_system.py`:** Authenticate via `/api/auth/dev-login` (or session cookie) before calling protected dashboard/download routes.
