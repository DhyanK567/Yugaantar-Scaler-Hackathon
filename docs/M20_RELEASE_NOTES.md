# MediLocker Android — Milestone M20 Release Notes

**Version:** `1.0.0-m20` (`org.medilocker.privacy`)  
**Release Gate Status:** **RELEASE APPROVED** *(Signed release APK, all automated backend/frontend/bridge/security checks, and live Android 16 emulator installation/launch/UI verification passed).*

---

## Highlights

- **Full Offline Android Packaging:** Bundles the Next.js static UI (`22/22` routes), a localhost-only NanoHTTPD API server (`LocalApiServer.kt`), and the real offline CPU-only Python privacy engine (`starter/main.py` + `starter/raksha_engine/`) via Chaquopy `16.0.0`.
- **Per-Device Keystore Secret Generation:** Generates and persists `RAKSHA_SECRET` inside Android `EncryptedSharedPreferences` at first launch and injects it directly into `engine_main.SECRET` in `android_api_bridge.py`.
- **Frontend Stability Fixes:** Resolved all 7 `react-hooks/set-state-in-effect` ESLint errors across dashboard and auth callback pages (`0` lint errors, `0` TypeScript errors).
- **Verified Privacy & Clinical Fidelity:** Passed all 10 security regression gates, `check_submission.py --repo starter --run` (`READY TO SUBMIT`), `run_independent_eval.py` (`0/10` PII leaked, `0/2` canaries leaked, `100.0%` clinical fidelity), and `android_api_bridge.py` E2E tests.

## Deliverables

- `dist/android/MediLocker-Android-Release.apk` (`35,671,884` bytes, v2 signed)
- `dist/android/MediLocker-Android-Release-SHA256.txt` (`CD4D8B5AB8E69B1F905FD56CE78E077FEB75A832AB4024311105D212ADB50B08`)
- `docs/M20_ANDROID_ARCHITECTURE_AUDIT.md`
- `docs/M20_TEST_INVENTORY.md`
- `docs/M20_ANDROID_BUILD_REPORT.md`
- `docs/M20_ANDROID_TEST_REPORT.md`
- `docs/M20_ANDROID_SECURITY_REPORT.md`
- `docs/M20_ANDROID_INSTALLATION_GUIDE.md`

## Live Emulator Verification

- Verified on `MediLocker_API36` (`android-36.1` `x86_64`): `adb install -r` succeeded, `MainActivity` launched cleanly, `/_next/static/chunks/2mlmic0sqyonj.css` returned `200`, `/api/health` returned `200` (`GuptKavach In-Process Chaquopy`), and `Sign in required` -> `Continue in Offline Demo Mode` -> `Privacy Dashboard` rendered cleanly.
