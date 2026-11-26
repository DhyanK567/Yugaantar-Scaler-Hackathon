# Milestone 15 — Full-System Integration & Independent Adversarial Evaluation Report

**Date:** 2026-11-26  
**Branch:** `feature/guptkavach-privacy-engine`  
**Policy Version:** `m10-v1`  

---

## 1. Integrated Architecture

GuptKavach (`starter/`) integrates 16 modules under `starter/raksha_engine/` with `starter/main.py` and `starter/config/policy.yaml`, running offline on CPU-only Python 3.12 with zero LLMs, zero network calls, and zero external transformer models. See [MILESTONE_15_ARCHITECTURE_AUDIT.md](MILESTONE_15_ARCHITECTURE_AUDIT.md).

---

## 2. Complete Data-Flow Explanation

1. **Ingestion & Security**: `verify_path_containment` blocks symlinks/traversal; `GuptKavachKeyRing` derives purpose-separated keys from `RAKSHA_SECRET`; unsupported/empty/undecodable/corrupt files are quarantined.
2. **Pass 1 (Classification & Clues)**: `qi_classifier.classify_field_tier` classifies fields into tiers `A`–`E`; `names.CorpusNameIndex` harvests multilingual names; `linking.extract_clues_from_text` extracts identity clues.
3. **Identity Resolution**: `linking.resolve_identities` links patients conservatively across hospitals/scripts.
4. **Pre-Mitigation Risk & Attack Analysis**: `attacker.simulate_attacks` (7 strategies) and `risk_engine.evaluate_corpus_risk` assess combination risk.
5. **Pass 2 (Adaptive Mitigation & Sanitization)**: `mitigation.plan_record_mitigation`, `privacy.pseudonym`, `privacy.shift_date_string`, and `sanitizer.py` redact PII and sanitize CSV/TSV/JSON/FHIR/TXT/base64/filenames.
6. **Validation & Release Gate**: `clinical_validator.validate_fhir_r4_bundle` validates exported FHIR R4 Bundles; `privacy_utility.evaluate_release_gate` issues `PASS` / `PASS_WITH_WARNINGS` / `BLOCKED`; `report.json` records `stage_trace`, `privacy_intelligence`, `clinical_integrity`, timing, and `peak_rss_mb`.

---

## 3. End-to-End Pipeline Results (`dev/input`)

- **Files**: `200` total (`195` sanitized, `5` quarantined, `0` raw copies)
- **Records**: `823` processed, `776` linked, `676` generalized, `143` suppressed
- **Field Tiers Classified (CSV headers)**: `A_DIRECT_IDENTIFIER`: `60`, `B_QUASI_IDENTIFIER`: `41`, `C_SENSITIVE_CLINICAL`: `5`, `D_CLINICAL_UTILITY`: `38`, `E_SAFE_METADATA`: `28`
- **Stage Trace (`report.json`)**: All 4 pipeline phases completed (`ingestion_and_extraction`, `identity_resolution`, `pre_mitigation_risk_and_attack`, `sanitization_validation_and_gate`)

---

## 4. Synthetic Dataset Description

- **Development Corpus (`dev/input`)**: 200 files across 10 clinical/admin channels (English, Hindi/Devanagari, Hinglish, CSV, TSV, JSON, FHIR R4, base64, malformed).
- **Independent Seeded Benchmark (`SEED=20261126`, `tests/independent_benchmark/`)**: Multi-institution synthetic dataset spanning Hospital A (CSV), Hospital B (FHIR R4), Hospital C (Devanagari nursing notes), and Lab D (nested JSON + base64 + binary malformed file) with unseen names, unseen MRNs, and homonym conflict pairs.

---

## 5. Adversarial Attack Results

- `tests/integration`: **3 / 3 passed** (1.999s)
- `tests/independent_benchmark`: **1 / 1 passed** (3.053s)
- `tests/privacy_attacks`: **10 / 10 passed**
- `tests/clinical_integrity`: **9 / 9 passed** (1.345s)
- `tests/cryptography`: **13 / 13 passed**
- `tests/multilingual`: **7 / 7 passed** (0.002s)

---

## 6. Privacy Measurements (`dev/input`, `check_dev.py`)

- **Direct identifiers detected**: `3436`
- **Residual PII leakage**: **`0 / 3230` (0.0%)** across all 16 PII types, all languages (`latin 0.0%, deva 0.0%, hinglish 0.0%`), and all channels (`content, filename, base64, metadata, key, header` all `0.0%`)
- **Canary exposure**: **`0 / 4`**
- **Release Gate**: `PASS_WITH_WARNINGS` (`RESIDUAL_UNIQUE_QUASI_COMBINATIONS`; `CRITICAL: 0`)

---

## 7. Identity Measurements

- **`dev/input` (`check_dev.py`)**: Precision `1.00`, Recall `0.81`, F0.5 `0.95`, wrong merges `0`
- **Adversarial Identity Benchmark (`tests/identity_adversarial/run_identity_benchmark.py`)**: `29` records — TP `10`, FP `0`, FN `0`, Precision `1.0`, Recall `1.0`, F0.5 `1.0`, false merges `0`, abstentions `2`, order invariance `True`, cross-secret collisions `0`
- **Independent Benchmark (`tests/independent_benchmark`)**: Cross-hospital linkage across A/B/D succeeded; same-name homonyms (`Devanand Tiwari` PT3 vs PT4) kept separate (`0` false merges).

---

## 8. Clinical Integrity Measurements

- **`dev/input` (`check_dev.py`)**: **`4847 / 4855`** medical values preserved (`99.8%`; 8 `CRITICAL` district suppressions in `arogya_legacy_export.csv`)
- **FHIR R4 Validation (`report.json`)**: `19` bundles checked, `332` resources checked, `fhir_validation_passed: true`, `0` failures
- **`tests/clinical_integrity`**: **9 / 9 passed** (medications, decimals, lab units, eponyms, orgs/doctors, date intervals, CSV/JSON/FHIR fidelity)

---

## 9. Security Measurements

- `tests/cryptography`: **13 / 13 passed** (AEAD tamper rejection, nonce freshness, key domain separation, empty-secret rejection, encrypted quarantine vault, path traversal containment)
- `check_submission.py --repo starter --run`: `RAKSHA_SECRET is never written to output or logs`, `input folder left unchanged`, `same secret twice -> identical sanitized/ and records.jsonl`, `different secret -> different output`

---

## 10. Failure-Recovery Results (`tests/integration::test_02`)

Verified detection and safe handling of: empty secret (`InvalidSecretError`), tampered AEAD ciphertext (`DecryptionAuthenticationError`), path traversal (`PathSecurityError`), corrupt JSON, empty file, unsupported `.png` binary (`3` quarantined, `0` raw copies), and malformed FHIR Bundle (`fhir_validation_passed: false`).

---

## 11. Performance Measurements (`dev/input`)

- **Pipeline Runtime**: `5.23s` (within 900s / 15-minute limit)
- **Peak RSS Memory**: **`40.89 MB`** (within 4096 MB limit)
- **Submission 3-Run Check**: Exit code `0` in `6.8s`

---

## 12. Official Validator Results

- `python validate_output.py --input dev/input --output ...`: **`CONTRACT OK`**
- `python check_submission.py --repo starter --run`: **`READY TO SUBMIT`**

---

## 13. Remaining Weaknesses

See [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md).

---

## 14. Reproduction Instructions

```powershell
python -m unittest discover -s tests/integration -v
python -m unittest discover -s tests/independent_benchmark -v
python -m unittest discover -s tests/clinical_integrity -v
python -m unittest discover -s tests/privacy_attacks -v
python -m unittest discover -s tests/cryptography -v
python -m unittest discover -s tests/multilingual -v
python tests/identity_adversarial/run_identity_benchmark.py
python validate_output.py --input dev/input --output <out>
python check_dev.py --output <out>
python check_submission.py --repo starter --run
```
