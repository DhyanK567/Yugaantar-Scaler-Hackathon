# MEDILOCKER M25 — ADVERSARIAL PII EVALUATION REPORT

**Date:** 2026-11-27  
**Suite:** `tests/m25_adversarial_suite/m25_generator.py::generate_adversarial_15`

## 1. Per-Category Adversarial Results (Pre- vs. Post-Hardening)

| Category | Pre-Hardening Recall | Pre-Hardening Failure | Post-Hardening Precision | Post-Hardening Recall | False Positives |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `01_unlabeled_names` | `0.00` (`0/1`) | Missed `Aarav Deshmukh` | **`1.00`** | **`1.00` (`1/1`)** | `0` |
| `02_long_sentence_names` | `0.00` (`0/1`) | Missed `Meenakshi Sundaram` | **`1.00`** | **`1.00` (`1/1`)** | `0` |
| `03_names_beside_med_terms` | `1.00` (`1/1`) | — | **`1.00`** | **`1.00` (`1/1`)** | `0` |
| `04_doctor_vs_patient` | `1.00` (`1/1`) | — | **`1.00`** | **`1.00` (`1/1`)** | `0` |
| `05_hospital_personal_name` | `1.00` (`1/1`) | — | **`1.00`** | **`1.00` (`1/1`)** | `0` |
| `06_initials` | `1.00` (`2/2`) | — | **`1.00`** | **`1.00` (`2/2`)** | `0` |
| `07_inconsistent_spacing` | `1.00` (`2/2`) | — | **`1.00`** | **`1.00` (`2/2`)** | `0` |
| `08_mixed_scripts` | `1.00` (`2/2`) | — | **`1.00`** | **`1.00` (`2/2`)** | `0` |
| `09_unlabeled_relatives` | `0.00` (`0/2`) | Missed `Farhan Siddiqui` & `Tariq Siddiqui` | **`1.00`** | **`1.00` (`2/2`)** | `0` |
| `10_narrative_ids` | `1.00` (`4/4`) | — | **`1.00`** | **`1.00` (`4/4`)** | `0` |
| `11_pii_in_filename` | `1.00` (`4/4`) | — | **`1.00`** | **`1.00` (`4/4`)** | `0` |
| `12_nested_json_kv` | `1.00` (`2/2`) | — | **`1.00`** | **`1.00` (`2/2`)** | `0` |
| `13_unicode_variants` | `0.33` (`1/3`) | Missed fullwidth `９８７６５４３２１０` | **`1.00`** | **`1.00` (`3/3`)** | `0` |
| `14_malformed_truncated` | `1.00` (`1/1` quarantined) | — | **`1.00`** | **`1.00` (`1/1` quarantined)** | `0` |
| `15_split_structured_fields` | `1.00` (`3/3`) | — | **`1.00`** | **`1.00` (`3/3`)** | `0` |

## 2. Generalisable Fixes Implemented

1. **`starter/raksha_engine/normalizer.py`:** Added fullwidth ASCII digit translation (`０-９` → `0-9`) and `NFC` script normalization in `normalize_digits()`, preserving clinical symbols (`µg`, `m²`).
2. **`starter/raksha_engine/names.py`:**
   - Added `.` to `RX_LABELED_NAME` lookahead (`Patient: Farhan Siddiqui.`).
   - Added `S/O|D/O|W/O|H/O` and English kinship cues (`brother`, `sister`, `uncle`, `aunt`, `spouse`, `cousin`, `nephew`, `niece`) to `RX_RELATIVE`.
   - Added gazetteer-anchored unlabeled Indian full-name detection in `redact_names_in_text()` strictly guarded by `RX_DOCTOR`, `RX_ORG_PHRASE`, `CLINICAL_STOPWORDS`, and `is_clinical_phrase()`.
