# M28 — Android Test Report

**Release Status:** **VERIFIED — RELEASE READY**  
**Validation Entrypoint:** `scripts/android_full_validation.ps1` (`exit code 0`)

---

## 1. Consolidated Gate & Suite Results

| # | Suite / Gate | Command | Result | Observed Details |
|---|---|---|---|---|
| 1 | Frontend Lint & TypeScript | `pnpm run lint && npx tsc --noEmit` | **PASSED** | `0 errors`, `8 warnings` |
| 2 | Security Regression Gate | `python scripts/security_regression_gate.py` | **PASSED** | `10 / 10 gates passed` (`18.87s`) |
| 3 | GuptKavach System & Auth | `python test_guptkavach_system.py` | **PASSED** | `11 PASSED, 0 FAILED` |
| 4 | Android Bridge Comprehensive | `pytest tests/android_bridge/test_android_bridge_comprehensive.py -v` | **PASSED** | `4 passed in 2.18s` (unauth `401`, empty/unsupported rejection, multiformat + Hindi filename + ZIP security, CLI parity) |
| 5 | Milestone 17 & 18 Suites | `pytest tests/milestone_17/test_milestone_17.py tests/milestone_18/test_offline_verification.py -q` | **PASSED** | `16 passed` |
| 6 | Final Remediation Integration | `python -m unittest tests/integration/test_final_remediation.py` | **PASSED** | `5 / 5 PASSED` |
| 7 | Independent Privacy & Clinical Eval | `python tests/independent_eval/run_independent_eval.py` | **PASSED** | `0/10` PII leaked, `0/2` canaries leaked, `36/36 = 100.0%` clinical fidelity, `release_decision: PASS` |
| 8 | Official Submission Check | `python check_submission.py --repo starter --run` | **PASSED** | `READY TO SUBMIT` (`CONTRACT OK`, `9.3s`) |
| 9 | Android JVM Unit Tests | `gradle testReleaseUnitTest --no-daemon` | **PASSED** | `LocalApiServerTest` (`BUILD SUCCESSFUL`) |
| 10 | Live Exact-APK E2E on Emulator | `MediLocker-release.apk` on `MediLocker_API36` (`emulator-5554`) | **PASSED** | `HEALTH: 200`, `CSS_OK: 200 (29941)`, `UNAUTH_401_OK`, `LOGIN_OK`, `UPLOAD_OK`, `PASSPORT_VERIFY_OK`, `ZIP_SECURITY_OK (5 files)` |
| 11 | Legacy Pre-M17 Suites (Non-Android) | `tests/pdf_reporting/` (`Py3.8` ReportLab), `tests/integration/test_full_app_e2e.py` (pre-M17 unauth) | **ENV / LEGACY DRIFT** | `test_pdf_reporting` requires Python 3.9+ (`usedforsecurity=False`); `test_full_app_e2e.py` predates M17 auth (`401` expected) |
