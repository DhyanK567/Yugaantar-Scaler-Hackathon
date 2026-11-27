# MEDILOCKER M25 — FILENAME & METADATA PRIVACY REPORT

**Date:** 2026-11-27  
**Suite:** `tests/m25_adversarial_suite/run_m25_eval.py::eval_filename_privacy`

## 1. Boundary & Threat Evaluated

Input paths, nested folder names, Unicode filenames, duplicate filenames across directories, and short-digit hospital/MRN identifiers (`IP-26-00134`, `DHH-IPD-00591`, `IPD-2026-00432`, `JJH-0076928`), phone numbers (`7585697553`), and patient names (`Reena_Nishad`, `Rohan_Verma`, `कविता_देशमुख`, `Priya_Sharma`) were tested across:
1. Output paths under `sanitized/`
2. `report.json`
3. `records.jsonl`

## 2. Hardening & Observed Results

- **Hardening (`starter/raksha_engine/sanitizer.py::sanitize_filename`):** Added structured hospital/MRN ID detection (`(?:IP|IPD|OPD|UHID|ADM|MRN|DHH|SNJ|JJH)[-_]?\d{2,}(?:[-_]\d{2,})?`) alongside `\d{6,}`, non-ASCII, and `sanitize_free_text()` checks, mapping sensitive components to domain-separated HMAC-SHA256 pseudonymous tokens (`doc_fn...`, `dir_fn...`, `discharge_fn...`).
- **Observed Results (`8` adversarial files):**
  - `path_leaks`: **`[]` (`0` leaks)**
  - `report_leaks`: **`[]` (`0` leaks)**
  - `records_leaks`: **`[]` (`0` leaks)**
  - `contract`: **`CONTRACT OK`**
- **Note on `dev/input` (`check_dev.py`):** As documented in `M25_M24_REPRODUCTION.md`, `check_dev.py` reports `35/3,230` (CRLF checkout) or `13/3,230` (LF-normalized) filename leaks when `input_sha256` in `report.json` does not match `dev/truth/truth.json` or when a file is quarantined (`output: null`), causing `check_dev.py` to evaluate the raw input path rather than an exported file.
