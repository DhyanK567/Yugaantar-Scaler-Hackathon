# Milestone 15.5 — GuptKavach Privacy Passport & Verifiable Release Certificate Report

**Date:** 2026-11-26  
**Branch:** `mailestone-15.5`  
**Environment:** Offline CPU-only Python 3.14.4 (`cryptography 46.0.5`)

---

## 1. Summary of Changes

### What Was Already Present
- `starter/main.py` two-pass offline sanitisation pipeline (`sanitized/`, `records.jsonl`, `report.json` with `raksha-report/1`).
- `starter/raksha_engine/crypto.py` (`GuptKavachKeyRing` with `scrypt` KDF and AES-256-GCM / ChaCha20-Poly1305), `secure_fs.py` (`verify_path_containment`), `quarantine.py` (`QuarantineVault`, imported but uninvoked in `main.py`).
- `starter/raksha_engine/attacker.py`, `risk_engine.py`, `clinical_validator.py`, and `privacy_utility.py` (`evaluate_release_gate`).

### What Was Newly Implemented
- **`starter/raksha_engine/passport.py`**:
  - Streaming SHA-256 file hashing (`stream_sha256`, 64 KiB chunks) and deterministic manifest generation (`build_dataset_manifest`, `compute_manifest_root_hash`).
  - Ed25519 signing and verification (`generate_ed25519_keypair_pem`, `load_signing_key`, `sign_passport_payload`, `verify_passport_signature`) with honest `UNSIGNED` fallback.
  - Evidence collector (`PassportEvidenceInput`, `build_privacy_passport`) consuming existing pipeline results without duplicating expensive passes, marking unexecuted tests `NOT_RUN` and unavailable ground-truth metrics `NOT_MEASURED`.
  - Policy-based release gate (`evaluate_passport_release_gate`) enforcing privacy, clinical, security, and cryptographic integrity rules.
  - Zero-PII / zero-secret guardrail (`assert_no_sensitive_data`).
- **`starter/raksha_engine/passport_report.py`**:
  - Self-contained offline HTML report (`render_passport_html`) with dark navy cybersecurity styling and zero external dependencies.
- **`starter/verify_passport.py`**:
  - Independent offline verifier CLI supporting `VERIFIED`, `UNSIGNED`, `TAMPERED`, `INCOMPLETE`, `INVALID_SIGNATURE`, and `INVALID_CERTIFICATE` outcomes.
- **`starter/main.py` & `starter/config/policy.yaml`**:
  - Integrated `dataset_manifest.json`, `privacy_passport.json`, and `privacy_passport.html` generation into the sanitisation workflow while preserving the official output contract (`sanitized/`, `records.jsonl`, `report.json`).
  - Updated `policy.yaml` to `policy_version: m15.5-v1` with explicit release gate flags and boolean parsing in `load_policy()`.

---

## 2. Files Created & Modified

- **Created:**
  - `starter/raksha_engine/passport.py`
  - `starter/raksha_engine/passport_report.py`
  - `starter/verify_passport.py`
  - `tests/privacy_passport/test_privacy_passport.py`
  - `docs/MILESTONE_15_5_BASELINE.md`
  - `docs/PRIVACY_PASSPORT_SPEC.md`
  - `docs/MILESTONE_15_5_REPORT.md`
- **Modified:**
  - `starter/main.py`
  - `starter/config/policy.yaml`

---

## 3. Test & Evaluator Results

- **Privacy Passport Adversarial Suite (`tests/privacy_passport/test_privacy_passport.py`):** `19 / 19` tests passed (covering all 20 tampering, missing file, unexpected file, modified certificate, invalid signature, unsigned mode, unsupported version, malformed manifest, reordered manifest, empty dataset, quarantined input, PII guardrail, Unicode filenames, Windows path normalization, repeated verification, relocated directory, and offline CLI scenarios).
- **Full Unit Suite (`tests/privacy_passport`, `tests/cryptography`, `tests/clinical_integrity`, `tests/privacy_attacks`, `tests/multilingual/test_unit.py`):** `58 / 58` tests passed in `1.811s`.
- **Official Output Contract (`validate_output.py` on `dev/input`):** `CONTRACT OK` (`200` input files, `195` sanitized, `5` quarantined, `823` records).
- **Official Submission Checker (`check_submission.py --repo starter --run`):** `READY TO SUBMIT` (`exit code 0 in 1.8s`, `CONTRACT OK`, deterministic same-secret runs, keyed different-secret separation, zero `RAKSHA_SECRET` leakage, input folder unchanged).
- **Practice Self-Check (`check_dev.py` on `dev/input`):** `0 / 3230` (`0.0%`) personal data leaked, `0 / 4` canaries exposed, `4847 / 4855` (`99.8%`) medical values preserved, patient linking `P=1.00, R=0.81, F0.5=0.95` (`0` false merges).
- **Signed & Unsigned CLI Verification (`verify_passport.py` on `dev/input`):**
  - Unsigned run: `STATUS: UNSIGNED` (all 195 output file hashes and root hash verified).
  - Signed run (`--signing-key` + `--public-key --require-signature`): `STATUS: VERIFIED` (Ed25519 signature + all 195 output file hashes verified).

---

## 4. Performance Measurements (`dev/input`, 195 sanitized files)

| Metric | Measured Value |
| --- | --- |
| Streaming file hashing (`build_dataset_manifest`) | `0.0816 s` |
| Passport + HTML generation (`build_privacy_passport` + `render_passport_html`) | `0.0028 s` |
| Independent verification (`verify_passport_bundle`) | `0.0266 s` |
| Peak traced memory (`tracemalloc` during manifest/passport/verify) | `300.0 KB` |
| `privacy_passport.json` size | `5,732 B` |
| `dataset_manifest.json` size | `33,268 B` |
| `privacy_passport.html` size | `10,630 B` |

---

## 5. Known Limitations

1. **Ground-truth metrics during blind runs:** Identity precision/recall/F0.5, canary exposure, and ground-truth clinical recall require `truth.json` and are honestly marked `NOT_MEASURED` / `NOT_RUN` during blind sanitisation.
2. **Encryption at rest in `main.py`:** `QuarantineVault` is implemented and tested in `tests/cryptography/`, but `main.py` does not write quarantined payloads to disk, so `encryption_at_rest` is reported as `NOT_RUN` during CLI runs.
3. **Key pinning:** Without `--public-key`, `verify_passport.py` uses the embedded `public_key_pem`, which proves tamper-evidence against the embedded key rather than external signer identity.
4. **Host `python` alias:** `starter/raksha.toml` invokes `python main.py ...`; on systems where only `python3` is in `PATH`, a `.venv` or `python` symlink is needed.
