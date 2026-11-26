# M16.1 — Filename Leakage Root Cause & Hardening Analysis

## 1. Root Cause
In earlier builds of GuptKavach, input relative paths (`rel`) were copied verbatim into `output/sanitized/<rel>`, exposing embedded PII such as patient names (`Discharge_Summary_Reena_Nishad_JJH-0076928.txt`), MRNs, and phone numbers in output filenames (35 leaks in the audit baseline: 24 MRNs, 6 patient names, 5 phone numbers).

While `sanitize_filename()` was subsequently added to `starter/raksha_engine/sanitizer.py`, inspection reveals four remaining architectural gaps against M16.1 requirements:
1. **Unsalted hash instead of secret-keyed domain-separated derivation**: `sanitize_filename()` currently formats renamed files with `raw_sha256[:8]` and does not accept `secret: bytes`. Changing `RAKSHA_SECRET` does not change output filenames, violating secret-separation requirements.
2. **Incomplete token/script normalization**: `sanitize_filename()` only replaces `_` with spaces when calling `sanitize_free_text()`, without replacing `-` or `.`, and does not pass `local_first_names=name_index.first_names`.
3. **Unsafe prefix retention**: `stem.split("_")[0].lower()` retains any alphabetic first token up to 12 characters unless it is in `name_index.first_names` — meaning an unseen Hinglish/transliterated name or hospital code at the start of a filename could still be retained.
4. **No explicit path-traversal guard**: `sanitize_filename()` does not normalize or reject `..`, leading slashes, backslashes, or null/control bytes before constructing output paths.

---

## 2. Affected Code Paths
- `starter/raksha_engine/crypto.py`: Defines `HKDF_DOMAIN_*` domain separation constants, but lacks `HKDF_DOMAIN_FILENAME` (`b"medilocker:v1:filename-pseudonym"`).
- `starter/raksha_engine/sanitizer.py`: `sanitize_filename(rel_posix, name_index, raw_sha256)` (lines 176–202).
- `starter/main.py`:
  - Line 507: Calls `sanitize_filename(rel, name_index, sha)` without `SECRET`.
  - Lines 508–511: Collision disambiguation appends `sha[:6]` instead of a keyed token.
  - Lines 564, 586, 613, 644, 653: Emit `sanitized/{out_rel}` in `records.jsonl` and `report.json`.
  - Line 502, 657: Quarantined entries in `report.json["files"]` set `output=None` and never emit raw filenames.

---

## 3. How Filenames Are Generated & Validated
- **Engine (`starter/main.py`)**: Computes `out_rel` per file, writes the sanitised file to `output/sanitized/<out_rel>`, records `{"file": "sanitized/<out_rel>", "loc": ..., "patient": pid}` in `records.jsonl`, and records `{"input_sha256": sha, "output": "sanitized/<out_rel>", "status": "sanitized"}` in `report.json["files"]`.
- **Official Validator (`validate_output.py`)**: Matches `report.json["files"]` by `input_sha256`, verifies that every declared `sanitized/<out_rel>` exists under `output/sanitized/`, verifies UTF-8 encoding, and verifies that every `records.jsonl` `"file"` entry points to an exported file.
- **Practice Self-Check (`check_dev.py`)**: Maps `input_sha256 -> output` via `report.json["files"]` and scans `norm(out_rel)` for `channel == "filename"` PII entities.

---

## 4. Compatibility & Security Risks
- **Contract Compatibility**: Because `validate_output.py` and `check_dev.py` resolve renamed files via `report.json["files"]` (`input_sha256 -> output`) and `records.jsonl` (`file`), deterministic pseudonymous filenames preserve 100% contract compatibility and identity linking (`patient` pseudonym in `records.jsonl` links records across files).
- **Quarantine Isolation**: Quarantined files must continue to emit `output: null` in `report.json` and opaque `QRN-...` references in MediLocker APIs, never raw filenames.
