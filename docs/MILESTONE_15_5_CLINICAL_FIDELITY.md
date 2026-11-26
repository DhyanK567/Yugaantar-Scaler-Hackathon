# MEDILOCKER — MILESTONE 15.5 CLINICAL FIDELITY & DRIFT ENGINE
**Phase 2 Specification & Verification**

---

## 1. Architecture (`starter/raksha_engine/clinical_validator.py`)

`analyze_clinical_drift(input_texts, sanitized_texts, fhir_bundles=None)` performs deterministic, zero-PII-exposure comparison across **15 clinical domains**:
1. `medication_names`
2. `dosages`
3. `units`
4. `frequencies`
5. `administration_routes`
6. `treatment_duration`
7. `blood_pressure`
8. `heart_rate`
9. `temperature`
10. `spo2`
11. `haemoglobin`
12. `blood_glucose`
13. `laboratory_measurements`
14. `diagnoses`
15. `fhir_resource_codes_and_refs`

---

## 2. Exact Aggregation & Drift Rules

- **Per-Category Metrics**: `expected`, `preserved`, `missing`, `modified`, `unexpected`, `exact_preservation_pct`.
- **Overall Exact Fidelity**:
  $$\text{Clinical Fidelity (\%)} = \frac{\sum \text{Preserved Expected Entities}}{\sum \text{Total Expected Entities}} \times 100$$
- **No Rounding to 100%**: `_safe_pct(preserved, expected)` clamps any `< 100%` ratio (such as `4853 / 4855 = 99.96%` or `49999 / 50000`) strictly below `100.0%`.
- **Dosage / Numeric Drift Detection**: Unmatched tokens within numeric/clinical categories (`dosages`, `blood_pressure`, `heart_rate`, `temperature`, `spo2`, `haemoglobin`, `blood_glucose`, `laboratory_measurements`) are flagged as `CLINICAL_VALUE_DRIFT` (`modified > 0`, `passed = False`) — e.g. `5 mg` $\rightarrow$ `50 mg` is a critical integrity failure.
- **Zero Raw Patient Data in Reports**: Reports emit only aggregate counts and structural error codes, never patient names or raw clinical notes.
