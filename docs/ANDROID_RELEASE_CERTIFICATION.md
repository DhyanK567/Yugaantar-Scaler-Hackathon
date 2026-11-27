# M28 — Android Release Certification

**FINAL STATUS:** **VERIFIED — RELEASE READY**

---

## 1. Release Artifact Identity

| Field | Value |
|---|---|
| **APK Path (Root)** | `MediLocker-release.apk` |
| **APK Path (Dist)** | `dist/android/MediLocker-Android-Release.apk` |
| **SHA-256 Checksum File** | `MediLocker-release.apk.sha256` |
| **SHA-256 Digest** | `7EBCB287DCC05BA25E945B9DA8575B2823E6B5E8F1A0EB2F527D5C53E0A2A4A2` |
| **APK Size** | `35,655,500` bytes (~34.00 MiB) |
| **Package ID** | `org.medilocker.privacy` |
| **Version** | `1.0.0-m20` (`versionCode 1`) |
| **Min / Target SDK** | `26` (Android 8.0) / `36` (Android 16) |
| **ABIs** | `arm64-v8a`, `x86_64` |
| **Signing** | APK Signature Scheme v2 (`apksigner verify`: `Verifies`, RSA-2048 external keystore) |

---

## 2. Certification Checklist

- **Errors Discovered & Fixed:** `8` code/packaging/security defects fixed (`ERR-001` through `ERR-008` in `docs/ANDROID_ERROR_REGISTER.md`); `2` non-Android host/legacy items documented (`ERR-009`, `ERR-010`).
- **Automated Validation (`scripts/android_full_validation.ps1`):** **PASSED** (`exit code 0`).
- **Official Submission Checker (`check_submission.py --repo starter --run`):** **READY TO SUBMIT** (`CONTRACT OK`).
- **Exact-APK Emulator Installation (`adb install -r MediLocker-release.apk`):** **Success**.
- **Exact-APK Live E2E (`127.0.0.1:8000` on `emulator-5554`):** **PASSED** (`HEALTH: 200`, `CSS_OK: 200`, `UNAUTH_401_OK`, `LOGIN_OK`, `UPLOAD_OK`, `PASSPORT_VERIFY_OK`, `ZIP_SECURITY_OK`).
