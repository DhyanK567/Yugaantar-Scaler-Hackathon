# MediLocker Android — Installation & Verification Guide

**Package:** `org.medilocker.privacy`  
**Minimum Android Version:** Android 8.0 (`API 26`)  
**Target Android Version:** Android 16 (`API 36`)  
**APK Artifact:** `dist/android/MediLocker-Android-Release.apk`

---

## 1. Verify APK Integrity Before Installing

Check the SHA-256 checksum against `dist/android/MediLocker-Android-Release-SHA256.txt`:

```powershell
Get-FileHash dist\android\MediLocker-Android-Release.apk -Algorithm SHA256
```

Expected SHA-256:
```text
CD4D8B5AB8E69B1F905FD56CE78E077FEB75A832AB4024311105D212ADB50B08
```

## 2. Install via ADB (USB Debugging or Emulator)

1. Enable **Developer Options** and **USB Debugging** on your Android 8.0+ device (or start an AVD).
2. Confirm the device is visible:
   ```powershell
   adb devices
   ```
3. Install the signed release APK:
   ```powershell
   adb install -r dist\android\MediLocker-Android-Release.apk
   ```
4. Launch the app:
   ```powershell
   adb shell am start -n org.medilocker.privacy/.MainActivity
   ```

## 3. First-Run Offline Verification Checklist

1. On first launch, the app initializes the local SQLite database (`medilocker.db`) and generates a per-device `RAKSHA_SECRET` in `EncryptedSharedPreferences`.
2. Use **Offline Demo Login** (or configured credentials) to authenticate against `127.0.0.1`.
3. Run **Process Sample** in **Datasets** to verify the Chaquopy privacy engine completes (`COMPLETED`), generates a Privacy Passport, and passes **Verify Passport** (`integrity_valid: true`) completely offline (Airplane Mode supported).
