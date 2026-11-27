# M20 — Android Test & Release Gate Report

**Release Gate Verdict:** **RELEASE APPROVED** *(APK compiled, signed, and all frontend, backend, security, clinical, Python bridge E2E, and live Android 16 emulator installation/launch/UI/auth checks passed).*

---

## 1. Automated Verification Summary

| Gate | Command | Outcome | Observed Metrics |
|------|---------|---------|------------------|
| Frontend Lint | `cd frontend && pnpm run lint` | **PASSED** | `0 errors`, `8 warnings` |
| Frontend TypeScript | `cd frontend && npx tsc --noEmit` | **PASSED** | `0 errors` |
| Frontend Static Build | `cd frontend && pnpm run build` | **PASSED** | `22/22` static routes |
| Security Regression Gate | `python scripts/security_regression_gate.py` | **PASSED** | `10/10` gates (`12.64s`) |
| Legacy Auth & System | `python test_guptkavach_system.py` | **PASSED** | `11 PASSED, 0 FAILED` |
| Milestone 17 & 18 Suites | `pytest tests/milestone_17/test_milestone_17.py tests/milestone_18/test_offline_verification.py -q` | **PASSED** | `16 passed` (`9.58s`) |
| Official Track 3 Check | `python check_submission.py --repo starter --run` | **PASSED** | `READY TO SUBMIT` (`6.9s`, `CONTRACT OK`) |
| Integration Remediation | `python -m unittest tests/integration/test_final_remediation.py` | **PASSED** | `5/5 PASSED` (`0.389s`) |
| Independent Privacy Eval | `python tests/independent_eval/run_independent_eval.py` | **PASSED** | `0/10` PII leaked, `0/2` canaries leaked, `36/36 = 100.0%` clinical fidelity, `1/5` quarantined (`PASS`) |
| Android Python Bridge E2E | `android_api_bridge.py` (`init_android_runtime` + `handle_request`) | **PASSED** | `UNAUTH_401_OK`, `OFFLINE_DEMO_200_OK`, `DASHBOARD_200_OK`, `PROCESS_SAMPLE_COMPLETED_OK`, `PASSPORT_VERIFY_OK`, `ZERO_RAW_PII_IN_DB_OK` |
| APK Signature & Badging | `apksigner.bat verify` & `aapt2.exe dump badging` | **PASSED** | v2 scheme verified, RSA-2048, `minSdk 26`, `targetSdk 36` |
| Android Device / Emulator Run | `MediLocker_API36` (`android-36.1` `x86_64`) via `adb install -r` + `am start` | **PASSED** | `Performing Streamed Install -> Success`, `PID 3584`, `CSS_STATUS=200 (29941 bytes)`, `API_STATUS=200 (GuptKavach In-Process Chaquopy)`, Sign-in gate -> Offline Demo Mode -> Privacy Dashboard verified |

---

## 2. Live Emulator Verification Summary

- **Packaging Fix Verified:** Live emulator testing uncovered that AAPT2's default `<dir>_*` ignore pattern stripped `assets/www/_next/`. Updating `androidResources.ignoreAssetsPattern` in `android/app/build.gradle.kts` resolved the `404` and verified `HTTP 200` (`29,941` bytes) for `/_next/static/chunks/2mlmic0sqyonj.css`.
- **UI & Engine Loopback Verified:** Cold launch on `emulator-5554` (`MediLocker_API36`, Android 16) rendered the unauthenticated `Sign in required` gate, navigated to `Sign in to MediLocker`, authenticated via `Continue in Offline Demo Mode`, and opened `Privacy Dashboard`.
