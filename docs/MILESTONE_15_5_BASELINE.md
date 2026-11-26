# Milestone 15.5 — GuptKavach Privacy Passport Baseline Audit

**Date:** 2026-11-26  
**Branch:** `mailestone-15.5`  
**Audit Scope:** `starter/`, `tests/`, `validate_output.py`, `check_submission.py`, `check_dev.py`

---

## 1. Existing Pipeline & Release Decision Point

The core offline sanitisation pipeline lives in [`starter/main.py`](../starter/main.py):

1. **Pass 1 (Ingestion & Clue Extraction):**
   - Recursively walks `--input` using `verify_path_containment()` (`starter/raksha_engine/secure_fs.py`) to reject symlinks and path escapes.
   - Parses `.csv`, `.tsv`, `.json`, and `.txt` files; unsupported/empty/undecodable/malformed files are marked `status = "quarantined"` with a reason code.
   - Extracts `RecordClues` (`linking.py`) and corpus names (`names.py`), then clusters identities via `resolve_identities()`.
   - Computes pre-mitigation attack simulation (`attacker.py`: `simulate_attacks()`) and combination-based risk (`risk_engine.py`: `evaluate_corpus_risk()`).

2. **Pass 2 (Sanitisation & Export):**
   - Sanitises filenames (`sanitize_filename()`), CSV/TSV cells (`sanitize_structured_cell()`), JSON nodes (`sanitize_json_node()`), and free text (`sanitize_free_text()`).
   - Writes sanitised outputs to `<output>/sanitized/` and linkage records to `<output>/records.jsonl`.
   - Validates exported FHIR R4 Bundles via `validate_fhir_r4_bundle()` (`clinical_validator.py`).
   - Computes post-mitigation attack simulation (`post_attack`) and risk (`post_risk`).

3. **Release Decision Point (`starter/main.py` lines 656–657):**
   - Calls `evaluate_release_gate()` (`starter/raksha_engine/privacy_utility.py`) using `PrivacyMetrics`, `ClinicalUtilityMetrics`, `post_risk`, `pre_attack`, `post_attack`, and `POLICY` (`starter/config/policy.yaml`).
   - Outputs `<output>/report.json` (`schema: "raksha-report/1"`).

---

## 2. Verification of Existing Modules & Gaps

| Area | What Exists in Code | Gaps / Findings |
| --- | --- | --- |
| **Cryptographic Engine (`crypto.py`)** | `GuptKavachKeyRing` with `scrypt` / `PBKDF2-HMAC-SHA256` KDF, domain-separated subkeys (`pseudonym`, `date_shift`, `encryption`, `integrity`, `quarantine`), AES-256-GCM / ChaCha20-Poly1305 / HMAC-CTR fallback. | `main.py` instantiates `keyring = GuptKavachKeyRing(SECRET)` when `RAKSHA_SECRET` is set, but `privacy.py` still uses raw `SECRET` directly. No asymmetric signing (Ed25519) or certificate manifest hashing exists yet. |
| **Quarantine (`quarantine.py`)** | `QuarantineVault` implements AES-256-GCM encrypted vaulting + `quarantine_manifest.jsonl`. | Imported in `starter/main.py` (line 52), **but never called** in `main()`. Quarantined files are simply omitted from `sanitized/` and recorded in `report.json`. |
| **Secure FS (`secure_fs.py`)** | `verify_path_containment()`, `secure_temporary_directory()`, `EncryptedFileVault`. | `verify_path_containment()` is used on input files in `main.py`. |
| **Privacy & Attack Metrics (`attacker.py`, `risk_engine.py`, `privacy_utility.py`)** | `simulate_attacks()` (7 strategies), `evaluate_corpus_risk()`, `evaluate_release_gate()`. | Available at runtime in `main.py`. `ClinicalUtilityMetrics.clinical_values_preserved` and `clinical_values_total` are passed as `None` in `main.py` (not measured inline during pipeline run). |
| **Clinical & FHIR (`clinical_validator.py`)** | `validate_fhir_r4_bundle()` is called in `main.py` (19 bundles, 332 resources on `dev/input`). `validate_clinical_probes()` exists in `clinical_validator.py`. | `fhir_failures` is recorded in `report.json`, but **not** fed into `evaluate_release_gate()`. Ground-truth clinical preservation (`4847/4855`) is only measured externally by `check_dev.py` because `main.py` has no `truth.json`. |
| **Identity Metrics** | `records_processed` and `records_linked` are counted in `main.py`. | Precision, recall, F0.5, and false merges require ground truth (`truth.json`), so they are `NOT_MEASURED` during blind pipeline execution unless evaluated against truth. |
| **CLI & Contract (`validate_output.py`, `check_submission.py`)** | `python main.py --input {input} --output {output}` via `starter/raksha.toml`. | `validate_output.py` requires `sanitized/`, `report.json`, and `records.jsonl`. `check_submission.py --run` checks determinism (`sanitized/`, `records.jsonl`), secret-keyed output, and zero `RAKSHA_SECRET` leakage. |

---

## 3. Baseline Measurements (`dev/input`)

Executed `RAKSHA_SECRET=test-secret-baseline python3 starter/main.py --input dev/input --output /tmp/gk_baseline_out`:

- **Pipeline output:** `files 200 sanitized 195 quarantined 5 records 823` (`1.57s`, `43.61 MB` peak RSS).
- **`validate_output.py`:** `CONTRACT OK`.
- **`check_dev.py`:**
  - Personal data leaked: `0 / 3230` (`0.0%`).
  - Canaries found: `0 / 4`.
  - Medical data kept: `4847 / 4855` (`99.8%`).
  - Patient linking: `precision 1.00, recall 0.81, F0.5 0.95` (`0` false merges).
  - Raw copies of broken/unsupported files: `0`.
- **Existing unit tests (`tests/cryptography`, `tests/clinical_integrity`, `tests/privacy_attacks`, `tests/multilingual/test_unit.py`):** `39 / 39` passed in `1.344s`.
- **`check_submission.py --repo starter --run`:** Static checks passed; `--run` failed because `python` binary is not in `PATH` on this host (`python3` is available).

---

## 4. Architecture Decisions & Risks for Milestone 15.5

1. **Non-disruptive Evidence Layer:**
   - Keep `sanitized/`, `records.jsonl`, and `report.json` (`raksha-report/1`) intact so `validate_output.py` and `check_submission.py` continue to pass.
   - Add `dataset_manifest.json`, `privacy_passport.json`, and `privacy_passport.html` to `--output`.
   - Note: `check_submission.py` scans ALL files in `out.rglob("*")` for `RAKSHA_SECRET` bytes — never write `RAKSHA_SECRET` or private keys into any output file.
   - Note: `check_submission.py` checks `tree_digest()` on `sanitized/` and `records.jsonl` only (not `privacy_passport.json`), so timestamps/signatures in `privacy_passport.json` will not break `check_submission.py`, and we will still make the passport payload deterministic (with optional deterministic or explicit timestamp handling).

2. **Honest `NOT_MEASURED` / `NOT_RUN` Reporting:**
   - During blind sanitisation (`main.py`), ground-truth metrics (canary check against `truth.json`, clinical probe recall vs `truth.json`, identity precision/recall/F0.5) are not available without ground truth. They **must** be recorded as `"NOT_MEASURED"` / `"NOT_RUN"` rather than `0` or `100%`.
   - Metrics that *are* measured inline (attack simulation pre/post, combination risk categories, FHIR R4 bundle/resource validation, direct identifiers detected, file counts, security checks) will be populated from actual pipeline results.

3. **Cryptographic Integrity & Signing:**
   - `cryptography` (`46.0.5`) is available in the Python environment, providing Ed25519 (`cryptography.hazmat.primitives.asymmetric.ed25519`).
   - Signing keys must be kept completely separate from `RAKSHA_SECRET` (never derived from `RAKSHA_SECRET` or hardcoded).
   - Support Ed25519 signing via an explicit signing key path (`--signing-key` / `GUPTKAVACH_SIGNING_KEY_PATH` / PEM env) and an explicit `UNSIGNED` integrity-only mode when no signing key is configured.

4. **Risks:**
   - **PII leakage into certificate/manifest:** Original input filenames can contain patient names (e.g. `Discharge_Summary_Fatima_Bano_SNJ-26-064508.txt`). The passport and `dataset_manifest.json` must only reference **sanitised** output relative paths and SHA-256 digests, never raw input filenames.
   - **Offline HTML rendering:** `privacy_passport.html` must be 100% self-contained (inline CSS, zero external CDNs or fonts).
