# M20 — Android Build Report

**Status:** Signed Release APK Built & Verified  
**Package ID:** `org.medilocker.privacy`  
**Version:** `1.0.0-m20` (`versionCode: 1`)  
**Artifact Path:** `dist/android/MediLocker-Android-Release.apk`  
**Checksum Path:** `dist/android/MediLocker-Android-Release-SHA256.txt`

---

## 1. Build Toolchain & Configuration

| Component | Version / Detail |
|-----------|------------------|
| **Gradle** | `8.13` (`--no-daemon`) |
| **JDK** | Adoptium Temurin `17.0.21.1+2` (`C:\Users\Dell\.jdks\jdk-17.0.21.1+2`) |
| **Android Gradle Plugin (AGP)** | `8.7.3` |
| **Kotlin** | `2.0.21` |
| **Chaquopy** | `16.0.0` (in-process Python `3.11` runtime) |
| **Compile / Target SDK** | `36` (`Android 16`) |
| **Min SDK** | `26` (`Android 8.0`) |
| **ABIs** | `arm64-v8a`, `armeabi-v7a`, `x86_64` |
| **R8 / Shrinker** | `minifyEnabled = true`, `shrinkResources = true` |

---

## 2. Architecture Summary

- **UI Layer:** Next.js `16.4.6` static export (`output: "export"`, `22/22` static routes) bundled in `android/app/src/main/assets/www` and served via `WebViewAssetLoader` / `127.0.0.1` loopback in `MainActivity.kt`.
- **Local HTTP Bridge:** `LocalApiServer.kt` (NanoHTTPD bound exclusively to `127.0.0.1` on an ephemeral localhost port) dispatching `/api/*` requests into Chaquopy.
- **Privacy Engine Runtime:** `android/app/src/main/python/android_api_bridge.py` invoking the unmodified offline CPU-only `starter/main.py`, `starter/verify_passport.py`, `starter/config/policy.yaml`, and `starter/raksha_engine/*`.
- **Secret Management:** `MainActivity.kt` generates a per-device 256-bit random `RAKSHA_SECRET` stored in Android `EncryptedSharedPreferences` (backed by Android Keystore) and injects it into `init_android_runtime(files_dir, raksha_secret)`. No secret or keystore is embedded in the APK or repository.

---

## 3. Release Artifact & Signature Verification

- **Build Result:** `BUILD SUCCESSFUL in 2m` (`58 actionable tasks: 12 executed, 46 up-to-date`, `androidResources.ignoreAssetsPattern` configured to retain `_next/` static chunks)
- **APK Size:** `35,671,884` bytes (~34.02 MiB)
- **SHA-256:** `CD4D8B5AB8E69B1F905FD56CE78E077FEB75A832AB4024311105D212ADB50B08`
- **APK Signature (`apksigner.bat verify --verbose --print-certs`):**
  - `Verifies`
  - `Verified using v2 scheme (APK Signature Scheme v2): true`
  - `Signer #1 certificate DN: CN=MediLocker, OU=SecretWards, O=MediLocker, L=Bengaluru, ST=KA, C=IN`
  - `Signer #1 key algorithm: RSA`, `2048` bits
  - External keystore location: `C:\Users\Dell\.medilocker\medilocker-release.jks` (not committed to git)
- **Manifest Badging (`aapt2.exe dump badging`):**
  - `package: name='org.medilocker.privacy' versionCode='1' versionName='1.0.0-m20'`
  - `minSdkVersion:'26'`, `targetSdkVersion:'36'`
  - Permissions: `android.permission.INTERNET`, `android.permission.ACCESS_NETWORK_STATE`, `org.medilocker.privacy.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION`
