# MediLocker Windows Desktop Installation Guide

## 1. System Requirements
- Windows 10 / 11 (x64)
- 2+ CPUs, 4 GB+ RAM, ~600 MB free disk space
- **No Python or Node.js installation required**
- **No internet connection required**

## 2. Installing via `MediLocker-Setup-x64.exe`
1. Verify SHA-256 checksum against `release/SHA256SUMS.txt`:
   ```powershell
   Get-FileHash release\MediLocker-Setup-x64.exe -Algorithm SHA256
   ```
2. Double-click `MediLocker-Setup-x64.exe`.
3. Choose installation directory (per-user install by default).
4. Start Menu and Desktop shortcuts for **MediLocker** are created automatically.

## 3. Running Portable (`MediLocker-Portable-x64.exe`)
- Double-click `MediLocker-Portable-x64.exe`.
- All user data, SQLite DB (`guptkavach.db`), and generated secrets are stored in `%APPDATA%\MediLocker\` (not inside temporary extraction folders) so data persists across runs.

## 4. Upgrading & Uninstalling
- Running a newer `MediLocker-Setup-x64.exe` upgrades application binaries while preserving `%APPDATA%\MediLocker\` (datasets, jobs, passports, audit trail).
- Uninstalling via Windows **Apps & Features** removes the installed program files; `%APPDATA%\MediLocker\` is preserved unless manually deleted.
