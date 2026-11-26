# Milestone 13 — Clinical Integrity Baseline Snapshot

**Date:** 2026-11-26  
**Branch:** `feature/guptkavach-privacy-engine`  
**Environment:** Offline CPU-only Python 3.12.10  

---

## 1. Existing Clinical Preservation Implementation

- `starter/raksha_engine/patterns.py`: `CLINICAL_SAFE_COLS` and `is_clinical_safe_field()` protect structured clinical columns (`drug`, `medicine`, `dose`, `dosage`, `diagnosis`, `vitals`, `bp`, `lab`, `result`, `value`, `unit`, `range`, `amount`, etc.) from `RX_PIN` and `RX_LOCALITY` over-redaction.
- `starter/raksha_engine/names.py`: `CLINICAL_STOPWORDS` and `is_clinical_phrase()` guard against redacting clinical terms/eponyms, and `RX_DOCTOR` preserves `Dr. <Name>`.
- `starter/raksha_engine/sanitizer.py`: Preserves `name` on non-person FHIR resources (`Organization`, `Location`, `Practitioner`, `Medication`, `Substance`, `Device`), preserves FHIR URNs/references/codes, and shifts dates per patient to retain intervals.
- `starter/main.py`: Passes `clinical_safe` for CSV/JSON cells and runs M10 risk/mitigation/release-gate checks.

---

## 2. Baseline Measurements (`dev/input`, `RAKSHA_SECRET="m10-final-secret"`)

| Metric | Observed Baseline |
| --- | --- |
| Files / Records | 200 files (195 sanitized, 5 quarantined), 823 records |
| Official `validate_output.py` | `CONTRACT OK` |
| Direct PII leakage (`check_dev.py`) | `0 / 3230` |
| Canary detections (`check_dev.py`) | `0 / 4` |
| Medical values preserved (`check_dev.py`) | **`4845 / 4855`** (10 missing/modified) |
| M10 Privacy Attack tests (`tests/privacy_attacks`) | `10 / 10` passed |

### Exact 10 Missing/Modified Items in Baseline
1. `registration/arogya_legacy_export.csv` (`row:0`–`row:7`, 8 items): `Sitapur` (7x) and `Bahraich` (1x) suppressed by M10 `CRITICAL` district suppression.
2. `registration/arogya_legacy_export.csv` (`row:6`): `Referred by ASHA worker` (`ASHA` matched case-insensitively by `CorpusNameIndex`).
3. `clean/dengue_management_protocol.txt` (`doc`): `ASHA workers` (`ASHA` matched case-insensitively by `CorpusNameIndex`).

---

## 3. Identified Gaps for Milestone 13

1. Single-token `"Asha"` in `CorpusNameIndex.build_matcher()` still matches all-caps `"ASHA"` in `"ASHA worker"` / `"ASHA workers"`.
2. Organizational/professional phrases (`Apollo Hospital`, `Department of Cardiology`) are not explicitly guarded in free text alongside `Dr. <Name>`.
3. `CLINICAL_STOPWORDS` needs broader coverage of routes, frequencies, dosage units, and eponyms.
4. No dedicated offline FHIR R4 structural validator checks required fields across all 14 clinical resource types (`Patient`, `RelatedPerson`, `Encounter`, `Observation`, `Condition`, `Medication`, `MedicationRequest`, `MedicationStatement`, `DiagnosticReport`, `Practitioner`, `Organization`, `Location`, `Procedure`, `AllergyIntolerance`) and internal reference integrity.
5. No dedicated post-sanitisation semantic/referential clinical validator (`clinical_validator.py`) or `tests/clinical_integrity/` adversarial clinical regression suite exists yet.
