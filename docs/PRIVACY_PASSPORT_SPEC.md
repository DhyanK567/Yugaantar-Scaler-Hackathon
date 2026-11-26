# GuptKavach Privacy Passport Specification (`guptkavach-passport/1.0`)

**Version:** `1.0`  
**Engine:** `guptkavach-engine/15.5`  
**Status:** Production Offline Specification

---

## 1. Overview & Trust Model

The **GuptKavach Privacy Passport** is a portable, tamper-evident evidence bundle emitted alongside every sanitised dataset release:

- `dataset_manifest.json` — Canonical sorted list of every sanitised output file's relative POSIX path, byte size, and streaming SHA-256 digest, plus the `root_hash`.
- `privacy_passport.json` — Machine-readable certificate containing Sections A–G and the `signature` block.
- `privacy_passport.html` — Self-contained, offline-rendered HTML report with zero external network or CDN dependencies.

### Integrity Verification vs. Proof of Anonymity

- **What the Privacy Passport proves:** Which files were released, their exact SHA-256 digests, which policy version and engine version produced them, which automated checks ran (or were `NOT_RUN` / `NOT_MEASURED`), and whether an Ed25519 signing key attested to the certificate.
- **What it does NOT claim:** It does **not** constitute a zero-knowledge proof, differential privacy guarantee, formal mathematical proof of k-anonymity/re-identification impossibility, or regulatory/legal certification (HIPAA/DPDP).

---

## 2. Certificate Schema (`privacy_passport.json`)

| Section | Key | Required Fields |
| --- | --- | --- |
| **A. Certificate Identity** | `certificate_identity` | `certificate_id`, `schema_version`, `created_at`, `expires_at`, `engine_version`, `policy_version`, `certificate_status` (`SIGNED` \| `UNSIGNED`) |
| **B. Dataset Provenance** | `dataset_provenance` | `input_dataset_fingerprint`, `output_dataset_root_hash`, `manifest_file`, `input_files_total`, `files_processed`, `files_sanitised`, `files_quarantined`, `files_failed`, `records_processed`, `output_files_count`, `output_total_bytes` |
| **C. Privacy Assessment** | `privacy_assessment` | `pii_detection`, `residual_leakage_test`, `canary_test`, `multilingual_detection_coverage`, `quasi_identifier_risk`, `reidentification_attack_simulation`, `unresolved_privacy_warnings` |
| **D. Identity Assessment** | `identity_assessment` | `linked_records`, `unlinked_records`, `abstentions`, `identity_precision`, `identity_recall`, `f0_5_score`, `false_merge_count`, `conflict_count` |
| **E. Clinical Integrity** | `clinical_integrity` | `expected_clinical_values`, `preserved_values`, `modified_values`, `missing_values`, `clinical_preservation_rate`, `medication_integrity`, `dosage_integrity`, `laboratory_value_integrity`, `fhir_validation` |
| **F. Security Assessment** | `security_assessment` | `encryption_at_rest`, `temporary_file_cleanup`, `log_sanitisation`, `output_integrity`, `path_traversal_protection`, `secret_configuration` |
| **G. Release Decision** | `release_decision` | `status` (`PASS` \| `PASS_WITH_WARNINGS` \| `BLOCKED`), `policy_version`, `gates`, `reason_codes`, `blocking_reasons`, `warnings`, `required_tests_not_run`, `explanation` |
| **Signature** | `signature` | `status` (`SIGNED` \| `UNSIGNED`), `algorithm` (`Ed25519` \| `NONE`), `key_id`, `public_key_pem`, `value` |

### Honest Reporting Invariants
- Any test not executed during the run is recorded as `"NOT_RUN"`.
- Any metric requiring ground truth (`truth.json`) or unavailable inline is recorded as `"NOT_MEASURED"`.
- Missing metrics are never coerced to `0` or rounded to `100%`.
- Original input filenames (which may contain patient names) are never stored in `dataset_manifest.json`, `privacy_passport.json`, or `privacy_passport.html`.

---

## 3. Cryptographic Design & Key Management

1. **Streaming File Hashing:** Each output file under `sanitized/` is hashed with SHA-256 in 64 KiB chunks (`stream_sha256`).
2. **Canonical Manifest & Root Hash:** Entries are normalized to POSIX relative paths (`/`), sorted lexicographically by `path`, serialized with canonical JSON (`sort_keys=True, separators=(",", ":"), ensure_ascii=False`), and hashed with SHA-256 to yield `root_hash`.
3. **Key Separation:** Ed25519 signing keys are loaded strictly from `--signing-key`, `GUPTKAVACH_SIGNING_KEY_PATH`, or `GUPTKAVACH_SIGNING_KEY_PEM` (with optional `GUPTKAVACH_SIGNING_KEY_PASSPHRASE`). They are **never** derived from `RAKSHA_SECRET` and **never** hardcoded.
4. **Canonical Signature:** When an Ed25519 private key is provided, the signature covers the canonical JSON bytes of the passport excluding the `signature` field.
5. **Honest `UNSIGNED` Mode:** When no signing key is configured, `signature.status` is `"UNSIGNED"` and `certificate_status` is `"UNSIGNED"`. Integrity verification still checks all SHA-256 file hashes and the root hash.
6. **Key-Management Limitations:** Without an external PKI/trust store or `--public-key` pinning, a verifier using the embedded `public_key_pem` verifies internal consistency against tampering rather than signer identity. Production deployments should pin trusted public keys via `--public-key`.

---

## 4. Independent Verification (`verify_passport.py`)

```bash
python3 starter/verify_passport.py \
  --passport path/to/privacy_passport.json \
  --output path/to/output_dir \
  [--public-key path/to/public_key.pem] \
  [--require-signature] \
  [--json]
```

Possible verification outcomes:
- `VERIFIED` (exit `0`): Schema valid, not expired, all output files present and matching SHA-256, root hash matches, Ed25519 signature valid.
- `UNSIGNED` (exit `0`, or `1` with `--require-signature`): Integrity verified, no digital signature supplied.
- `TAMPERED` (exit `1`): Modified file, unexpected extra file, or root/manifest hash mismatch.
- `INCOMPLETE` (exit `1`): Expected output file(s) missing.
- `INVALID_SIGNATURE` (exit `1`): Signature verification failed or public key mismatch.
- `INVALID_CERTIFICATE` (exit `1`): Malformed JSON, missing sections, unsupported `schema_version`, or expired certificate.

---

## 5. Policy-Based Release Gate (`starter/config/policy.yaml`)

- **Blocking Conditions:** `DIRECT_PII_LEAK_DETECTED`, `CRITICAL_REIDENTIFICATION_RISK_EXCEEDED`, `CANARY_EXPOSURE_DETECTED`, `RESIDUAL_DIRECT_PII_LEAK_DETECTED`, `MANDATORY_FHIR_VALIDATION_FAILED`, `CLINICAL_PRESERVATION_BELOW_THRESHOLD`, `QUARANTINED_FILE_IN_RELEASED_OUTPUT`, `CRYPTOGRAPHIC_ROOT_HASH_MISSING`, `REQUIRED_DIGITAL_SIGNATURE_MISSING`, `TEMPORARY_FILE_CLEANUP_NOT_VERIFIED`.
- **Warning Conditions:** `RESIDUAL_UNIQUE_QUASI_COMBINATIONS`, `HIGH_RISK_RECORD_RATIO_ELEVATED`, `RAKSHA_SECRET_NOT_CONFIGURED_EPHEMERAL_MODE`, `PASSPORT_UNSIGNED_INTEGRITY_ONLY`, `FHIR_BUNDLES_NOT_PRESENT_IN_CORPUS`.

---

## 6. Reproducibility & Offline Operation

- Set `GUPTKAVACH_PASSPORT_TIMESTAMP` (ISO-8601 UTC) or `SOURCE_DATE_EPOCH` for deterministic `created_at` / `expires_at` timestamps across repeat runs.
- Ed25519 signatures are deterministic per RFC 8032 for identical canonical payloads and keys.
- Both `main.py` and `verify_passport.py` operate 100% offline on CPU with zero network calls.
