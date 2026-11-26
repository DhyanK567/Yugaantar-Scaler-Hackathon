# MediLocker Desktop Security Architecture

- **Electron Hardening (`desktop/main.js`, `desktop/preload.js`):**
  - `contextIsolation: true`, `nodeIntegration: false`, `sandbox: true`.
  - `remote` module disabled.
  - Explicit IPC surface (`dialog:openFiles`, `dialog:saveFile`, `app:info`) with `path.basename` sanitization on save dialogs.
  - Navigation restricted strictly to `http://127.0.0.1:<uiPort>`; external URLs and `window.open` blocked.
  - Strict Content Security Policy (`default-src 'self'`, `connect-src 'self' http://127.0.0.1:<apiPort> http://127.0.0.1:<uiPort>`, `frame-ancestors 'none'`).
- **Loopback-Only Processes:**
  - `medilocker-backend.exe` binds strictly to `127.0.0.1` on a dynamically allocated free port (never `0.0.0.0`).
  - Next.js standalone server binds strictly to `127.0.0.1` on a separate free port.
  - `taskkill /PID ... /T /F` terminates both child process trees on exit to prevent orphaned processes.
- **Per-Install Cryptographic Secrets:**
  - Generated on first launch via `crypto.randomBytes(32)` and stored in `%APPDATA%\MediLocker\secrets.json` (never hardcoded or exposed to renderer JS).
