# Milestone 13 — Clinical Integrity & Structured Medical Data Fidelity Report

**Date:** 2026-11-26  
**Branch:** `feature/guptkavach-privacy-engine`  
**Environment:** Offline CPU-only Python 3.12.10  

---

## 1. Baseline Clinical Integrity

Before Milestone 13, `check_dev.py` preserved `4845 / 4855` medical values (`dev/input`), with 10 missing/modified items: 8 `CRITICAL` district suppressions in `arogya_legacy_export.csv` and 2 `ASHA worker` / `ASHA workers` over-redactions. See [MILESTONE_13_BASELINE.md](MILESTONE_13_BASELINE.md).

---

## 2. Clinical Entity Detection

- [`starter/raksha_engine/names.py`](../starter/raksha_engine/names.py):
  - Separated `_EPONYM_WORDS` + `_EPONYM_SUFFIXES` from `CLINICAL_STOPWORDS` so eponyms (`Parkinson's disease`, `Alzheimer's disease`, `Hodgkin lymphoma`, `Crohn's disease`, `Bell's palsy`) are preserved while adversarial labeled names (`Patient Name: Parkinson Patel`) are still redacted.
  - Added `RX_ORG_PHRASE` (`Apollo Hospital`, `Department of Cardiology`) protected alongside `RX_DOCTOR` (`Dr. Ramesh`).
  - Added negative lookahead `(?!(?-i:ASHA)\b)` in `CorpusNameIndex.build_matcher()` and `local_first_names` regex so `ASHA worker` / `ASHA workers` are never redacted, while `Asha Rajput` and lowercase Hinglish first names (`kamlesh ko ...`) are redacted.

---

## 3. Medication Preservation

- [`starter/raksha_engine/patterns.py`](../starter/raksha_engine/patterns.py) & `names.py`:
  - Expanded `CLINICAL_STOPWORDS` and `CLINICAL_SAFE_COLS` with routes (`oral`, `iv`, `im`, `sc`, `subcutaneous`, `intravenous`, `topical`), frequencies (`twice`, `daily`, `bd`, `tds`, `qid`, `every`, `hours`), dosage forms (`tablet`, `syrup`, `drops`, `ointment`, `cream`, `inhaler`), and units (`mg`, `mcg`, `ml`, `units`, `mmol`, `mmhg`, `bpm`, `kg`, `cm`, `dl`).
  - Verified exact preservation of `Dolo 650 mg`, `Metformin 500 mg twice daily`, `Paracetamol 500 mg`, `Insulin 10 units`, `5 ml syrup`, `1 tablet every 8 hours`, `0.5 mg`, and `2.5 ml`.

---

## 4. Measurement Preservation

- [`starter/raksha_engine/patterns.py`](../starter/raksha_engine/patterns.py):
  - Guarded `RX_PIN` against decimal points (`(?<!\.)`) and trailing clinical units (`/uL`, `/cumm`, `/mm3`, `mg`, `mcg`, `ml`, `mmol`, `mmhg`, `g/dl`, `units`, `bpm`, `kg`, `cm`, `%`).
  - Verified exact preservation of `Blood pressure: 120/80 mmHg`, `Temperature: 98.6°F`, `Haemoglobin: 12.5 g/dL`, `Blood glucose: 110 mg/dL`, `SpO2: 98%`, `Heart rate: 76 bpm`, `Creatinine: 1.2 mg/dL`, `Sodium: 140 mmol/L`, `Height: 172 cm`, `Weight: 68 kg`, ranges (`150000-410000`), negative values (`-2.5`), and scientific notation (`1.2e5`).

---

## 5. FHIR R4 Integrity

- [`starter/raksha_engine/sanitizer.py`](../starter/raksha_engine/sanitizer.py): Preserves `name` (both string and `HumanName` list) on non-person FHIR resources (`Organization`, `Location`, `Practitioner`, `Medication`, `Substance`, `Device`) while redacting `Patient`, `Patient.contact`, `Patient.extension`, and `RelatedPerson` PII.
- [`starter/raksha_engine/clinical_validator.py`](../starter/raksha_engine/clinical_validator.py): Offline FHIR R4 Bundle validator (`validate_fhir_r4_bundle`) checking required fields across 14 resource types (`Patient`, `RelatedPerson`, `Encounter`, `Observation`, `Condition`, `Medication`, `MedicationRequest`, `MedicationStatement`, `DiagnosticReport`, `Practitioner`, `Organization`, `Location`, `Procedure`, `AllergyIntolerance`) and internal `urn:uuid:` reference integrity.
- **`dev/input` result (`report.json`)**: `19` bundles checked, `332` resources checked, `fhir_validation_passed: true`, `0` failures.

---

## 6. CSV and JSON Fidelity

- Verified CSV clinical vs PII column separation (`labs.csv`), nested JSON + base64 attachment sanitization, colliding sanitized key disambiguation (`by_name`), null/empty field preservation, and quarantine of malformed JSON / empty files without raw copies.

---

## 7. Semantic Validation

- [`starter/raksha_engine/clinical_validator.py`](../starter/raksha_engine/clinical_validator.py) separates:
  - A. Privacy transformations
  - B. Clinical data preservation (`validate_clinical_probes` with exact counts and `CLINICAL_VALUE_LOST` / `CLINICAL_ITEM_MODIFIED` reason codes)
  - C. Structural changes (`fhir_bundles_checked`, `fhir_resources_checked`, `verify_date_interval_preserved`)
  - D. Validation failures (`FHIR_REQUIRED_FIELD_MISSING`, `FHIR_BROKEN_REFERENCE`, `DATE_INTERVAL_MISMATCH`, `DATE_ORDER_VIOLATED`)

---

## 8. Adversarial Test Results

- `python -m unittest discover -s tests/clinical_integrity -v`: **9 / 9 tests passed in 1.368s** (`test_01` through `test_09`).
- `python -m unittest discover -s tests/privacy_attacks -v`: **10 / 10 tests passed in 3.674s**.
- `run_suite.py`: All 5 checks `PASS` (`DETERMINISM_SAME_SECRET`, `PSEUDONYM_SEPARATION_DIFF_SECRET`, `SECRET_LOG_FILE_LEAK_CHECK`, `FHIR_R4_INTEGRITY`, `MALFORMED_UNSUPPORTED_INPUTS`).

---

## 9. Exact Preservation Counts (`dev/input`)

| Metric | Baseline (M10) | After M13 |
| --- | --- | --- |
| Medical values preserved (`check_dev.py`) | `4845 / 4855` | **`4847 / 4855`** |
| Direct PII leaks (`check_dev.py`) | `0 / 3230` | **`0 / 3230`** |
| Canary detections (`check_dev.py`) | `0 / 4` | **`0 / 4`** |
| Patient linking (`check_dev.py`) | `P=1.00, R=0.76, F0.5=0.94` | `P=1.00, R=0.76, F0.5=0.94` |
| Files sanitized / quarantined | `195 / 5` (823 records) | `195 / 5` (823 records) |
| FHIR R4 bundles / resources validated | — | `19 / 332` (`0` failures) |
| Official `validate_output.py` | `CONTRACT OK` | `CONTRACT OK` |

---

## 10. Performance

- **Runtime on `dev/input` (200 files, 823 records)**: `5.08s` (within 900s limit).
- **Peak RSS**: `0.0` reported on Windows (`resource.getrusage` used on POSIX).

---

## 11. Known Limitations

1. `8 / 4855` location probes (`Sitapur` / `Bahraich` in `arogya_legacy_export.csv`) remain suppressed because M10 `CRITICAL` combination risk escalates rare-group records to suppress `district`.
2. `check_submission.py --repo starter` still flags `raksha.toml` `name = "your-team-name"`, `README.md` (268 words `< 300`), and missing 2-page Project Brief PDF.
3. Windows `K32GetProcessMemoryInfo` / `psapi` returned `0.0` for `peak_rss_mb`.
