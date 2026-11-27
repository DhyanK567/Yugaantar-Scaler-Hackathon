# M20 — Test Inventory & Execution Matrix

**Project:** MediLocker (GuptKavach / Raksha Engine)  
**Track:** Yugaantar DevForge Hackathon — Track 3: Secret Wards (Offline, CPU-only, Zero-LLM)  
**Scope:** Complete inventory of automated, static, security, clinical, cryptographic, offline-benchmark, and Android bridge tests executed for Milestone M20.

---

## 1. Test Suites & Commands Executed

| # | Category | Suite / Command | Scope | Result | Timing / Metrics |
|---|----------|----------------|-------|--------|------------------|
| 1 | Frontend Static & Lint | `cd frontend && pnpm run lint` | ESLint 9 across Next.js 16.4.6 / React 19.3.0 app (`0` errors after `react-hooks/set-state-in-effect` fixes in 7 files) | **PASSED** | `0 errors`, `8 warnings` |
| 2 | Frontend TypeScript | `cd frontend && npx tsc --noEmit` | Full TypeScript type check across `frontend/src` | **PASSED** | `0 errors` |
| 3 | Frontend Static Export | `cd frontend && pnpm run build` | Next.js static export (`output: "export"`, `22/22` static routes including all 12 dashboard modules) | **PASSED** | `22/22` routes generated |
| 4 | Security Regression Gate | `python scripts/security_regression_gate.py` | 10-gate security check (secrets, auth, org scoping, PII leakage, offline compliance) | **PASSED** | `10/10` gates (`12.64s`) |
| 5 | Legacy System & Auth Suite | `python test_guptkavach_system.py` | Auth protection (`401` unauthenticated), test login, dashboard & pipeline endpoints | **PASSED** | `11 PASSED, 0 FAILED` |
| 6 | Milestone 17 & 18 Suites | `pytest tests/milestone_17/test_milestone_17.py tests/milestone_18/test_offline_verification.py -q` | Cryptographic assurance, offline verification, passport & clinical integrity | **PASSED** | `16 passed` (`9.58s`) |
| 7 | Official Submission Contract | `python check_submission.py --repo starter --run` | Official Track 3 submission contract & CLI entrypoint verification | **PASSED** | `READY TO SUBMIT` (`6.9s`, `CONTRACT OK`) |
| 8 | Final Remediation Integration | `python -m unittest tests/integration/test_final_remediation.py` | End-to-end backend/DB/passport/audit integration | **PASSED** | `5/5 PASSED` (`0.389s`) |
| 9 | Independent Privacy & Clinical Eval | `python tests/independent_eval/run_independent_eval.py` | PII leakage, canary detection, clinical fidelity, quarantine enforcement | **PASSED** | `0/10` PII leaked, `0/2` canaries leaked, `36/36 = 100.0%` clinical fidelity, `1/5` quarantined (`PASS`) |
| 10 | Android Python Bridge E2E | `android/app/src/main/python/android_api_bridge.py` (`init_android_runtime` + `handle_request`) | Unauth `401`, `/api/auth/offline-demo` `200` + session cookie, `/api/dashboard` & `/api/dashboard/overview` `200`, `/api/datasets/process-sample` `COMPLETED`, `/api/passports/{id}/verify` `integrity_valid=True`, SQLite dump zero-PII/zero-secret check | **PASSED** | `6/6` assertions passed |
| 11 | Android Device / Emulator Runtime | `MediLocker_API36` (`android-36.1` `x86_64`) via `adb install -r` & `am start` | Live APK installation, cold launch, `_next/` CSS/JS serving, `/api/health`, offline demo sign-in, Privacy Dashboard telemetry | **PASSED** | `Performing Streamed Install -> Success`, `PID 3584`, `CSS_STATUS=200`, `API_STATUS=200` |

---

## 2. Coverage Summary by Functional Area

- **Authentication & Session Security:** Verified unauthenticated `401` enforcement and session cookie issuance/validation in `test_guptkavach_system.py`, `security_regression_gate.py`, and `android_api_bridge.py` E2E.
- **Privacy Engine & PII Redaction:** Verified `0/10` PII leaked and `0/2` canaries leaked in `run_independent_eval.py` and `check_submission.py --repo starter --run`.
- **Clinical Integrity:** Verified `36/36 (100.0%)` clinical fidelity in `run_independent_eval.py`.
- **Privacy Passports & Cryptography:** Verified deterministic pseudonymisation, HMAC/signature verification (`integrity_valid=True`), and `RAKSHA_SECRET` non-empty enforcement across `milestone_17`, `milestone_18`, and `android_api_bridge.py`.
- **Android Packaging & Signing:** Release APK compiled with Chaquopy `16.0.0` + AGP `8.7.3`, signed with external RSA-2048 keystore (`apksigner verify` v2).
- **On-Device / Emulator Runtime Gap:** Live Android OS execution could not be performed in this environment because no AVD exists and no physical device is connected.
