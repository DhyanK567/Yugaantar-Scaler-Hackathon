# Milestone 10 — Re-identification Defence & Adversarial Privacy Intelligence Report

**Date:** 2026-11-26  
**Branch:** `feature/guptkavach-privacy-engine`  
**Policy Version:** `m10-v1`  

---

## 1. Baseline Architecture

Before Milestone 10, `starter/` ran a two-pass offline CPU-only pipeline (`main.py` + `raksha_engine/{patterns,names,linking,privacy,sanitizer}.py`) that redacted direct identifiers, resolved patient clusters, shifted dates per patient, and applied a single `(5-year age_band, district)` count for rare-group suppression. See [MILESTONE_10_BASELINE.md](MILESTONE_10_BASELINE.md) for the full baseline snapshot.

---

## 2. Implemented Modules

- [`starter/raksha_engine/qi_classifier.py`](../starter/raksha_engine/qi_classifier.py) (M10.1): 5-tier deterministic field classifier (`A_DIRECT_IDENTIFIER`, `B_QUASI_IDENTIFIER`, `C_SENSITIVE_CLINICAL`, `D_CLINICAL_UTILITY`, `E_SAFE_METADATA`) supporting English, Hindi, and Hinglish field names with stable reason codes.
- [`starter/raksha_engine/attacker.py`](../starter/raksha_engine/attacker.py) (M10.2): Deterministic synthetic re-identification attack simulator evaluating 7 combination attack strategies without emitting raw PII.
- [`starter/raksha_engine/risk_engine.py`](../starter/raksha_engine/risk_engine.py) (M10.3 & M10.4): Combination-based risk engine & rare-group/attribute detector with configurable weights, explicitly separating measured uniqueness (`k_group_size`, `measured_is_unique`) from the 0–100 estimated structural risk index.
- [`starter/raksha_engine/mitigation.py`](../starter/raksha_engine/mitigation.py) (M10.5): Adaptive, least-destructive mitigation planner recording `field_category`, `action`, `reason_code`, and `policy_version`.
- [`starter/raksha_engine/privacy_utility.py`](../starter/raksha_engine/privacy_utility.py) (M10.6 & M10.7): Separated privacy vs. clinical utility metrics (exact numerators/denominators) and configurable release gate (`PASS`, `PASS_WITH_WARNINGS`, `BLOCKED`).
- [`starter/config/policy.yaml`](../starter/config/policy.yaml): Extended with `policy_version`, `upper_age_band`, `pin_prefix_digits`, risk weights, risk thresholds, and release gate thresholds.
- [`starter/main.py`](../starter/main.py): Integrated pre-mitigation attack/risk evaluation, adaptive mitigation planning, post-mitigation re-evaluation, and `privacy_intelligence` reporting into `report.json` while preserving the output contract.
- [`tests/privacy_attacks/test_privacy_attacks.py`](../tests/privacy_attacks/test_privacy_attacks.py) (M10.8): 10-test adversarial privacy & clinical utility unittest suite.

---

## 3. New Algorithms

1. **5-Tier Field Classification**: Normalizes Unicode/case and classifies headers/keys into Direct, Quasi-Identifier, Sensitive Clinical, Clinical Utility, or Safe Metadata, prioritizing clinical utility/diagnosis preservation before identifier matching.
2. **Equivalence-Class Attack Simulation**: Groups `RecordProfile`s by each of the 7 attack key tuples, measures candidate group size `k` and distinct `patient_key` count, and flags uniquely distinguishable records (`k == 1` or `unique_patients == 1`).
3. **Combination-Based Structural Risk Scoring**: Computes a configurable weighted sum (`group_size=35`, `qi_uniqueness=25`, `geo_rarity=15`, `temporal=10`, `rare_dx=10`, `linkage=5`) and maps to `LOW` (<25), `MODERATE` (25–49), `HIGH` (50–74), or `CRITICAL` (≥75).
4. **Adaptive Escalation**: Escalates 5-year age bands to 10-year bands, masks PINs to 3-digit prefixes or suppresses PINs, and suppresses rare districts/tehsils only when justified by `HIGH`/`CRITICAL` or `k < min_group_size`.

---

## 4. Attack Strategies Evaluated

1. `exact_combination`: `(age, birth_year, gender, district, village_or_loc, pin)`
2. `age_gender_location`: `(age, gender, district, pin)`
3. `rare_diagnosis_location`: `(diagnosis, district, village_or_loc)`
4. `admission_los`: `(admission_date, los_days)`
5. `geographic_narrowing`: `(district, village_or_loc, pin)`
6. `cross_record_linkage`: `(hospital_count, record_count, gender, district)`
7. `rare_attribute_combination`: `(age, gender, hospital_dept, treatment)`

---

## 5. Mitigation Policies

Defined in `starter/config/policy.yaml` (`policy_version: m10-v1`):
- `age_band_years: 5` (widened to 10 years for `below_min_group` / `HIGH` / `CRITICAL` records), `upper_age_band: 85` (`85+`)
- `date_shift_max_days: 180` (secret-keyed per-patient offset preserving temporal intervals)
- `min_group_size: 5`, `pin_prefix_digits: 3`
- Release gate: `max_critical_records_for_pass: 0`, `max_high_risk_ratio_for_pass: 0.15`, `min_clinical_retention_ratio: 0.90`

---

## 6. Test Coverage

`python -m unittest discover -s tests/privacy_attacks -v`: **10 / 10 tests passed in 4.260s** covering:
- Multilingual (English/Hindi/Hinglish) QI classification & clinical preservation
- Unique age + gender + village attack & mitigation
- Rare diagnosis + exact date (diagnosis preserved, dates shifted)
- Small hospital department & rare attribute combination
- Rare age group + PIN prefix
- Cross-hospital identity correlation
- Combined individually-safe QIs & zero-risk record negative test
- Clinical values untouched (`120/80`, `98.6`, `Dolo 650 mg`, `Parkinson's disease`) & date interval preservation
- Release gate blocking on `CRITICAL` risk and direct PII leaks
- End-to-end determinism, secret separation, quarantine handling, FHIR R4 Bundle preservation, and zero raw PII in logs/reports.

---

## 7. Before / After Measurements (`dev/input`, 200 files, 823 records)

| Metric | Pre-Mitigation | Post-Mitigation |
| --- | --- | --- |
| `CRITICAL` risk records | 72 / 823 | **0 / 823** |
| `HIGH` risk records | 60 / 823 | **5 / 823** |
| `MODERATE` risk records | 59 / 823 | 81 / 823 |
| `LOW` risk records | 632 / 823 | **737 / 823** |
| Records below `min_group_size` (5) | 200 / 823 | **103 / 823** |
| Uniquely distinguishable records (all attacks) | 433 / 823 | **310 / 823** |
| `exact_combination` attack successes | 281 / 823 | **86 / 823** |
| `age_gender_location` attack successes | 277 / 823 | **86 / 823** |
| `rare_diagnosis_location` attack successes | 34 / 823 | **0 / 823** |
| `geographic_narrowing` attack successes | 48 / 823 | **0 / 823** |
| `rare_attribute_combination` attack successes | 146 / 823 | **42 / 823** |
| `cross_record_linkage` attack successes | 297 / 823 | 273 / 823 |
| Direct PII leaks (`check_dev.py`) | — | **0 / 3230** |
| Canary detections (`check_dev.py`) | — | **0 / 4** |
| Release Gate status | — | **`PASS_WITH_WARNINGS`** (`RESIDUAL_UNIQUE_QUASI_COMBINATIONS`) |

---

## 8. Clinical Utility Results (`dev/input`)

- **Medical data preserved (`check_dev.py`)**: **`4845 / 4855`** (exact count; 99.8%)
- **Patient linking (`check_dev.py`)**: Precision `1.00`, Recall `0.76`, F0.5 `0.94`, wrong merges `0`
- **Records generalized / suppressed**: `676 / 823` generalized, `143 / 823` suppressed, `0 / 823` records quarantined (`5 / 200` malformed/unsupported files quarantined, `0` raw copies)

---

## 9. Performance Measurements

- **Runtime on `dev/input` (200 files, 823 records)**: `5.19s` (well within the 900s sandbox limit).
- **Peak RSS**: `0.0` reported in `report.json` (`K32GetProcessMemoryInfo` returned 0 in this Windows Python build; Linux `resource.getrusage` populates MB on POSIX).

---

## 10. Known Limitations

1. **Residual `cross_record_linkage` (273) and `exact_combination` (86) uniqueness**: Linked multi-record patients in a 200-file corpus still share `(gender, district)` or `(10y_age_band, gender)` when `district` is retained for geographic utility.
2. **8 medical values (`4853/4855` → `4845/4855`)**: Escalating `CRITICAL` records to suppress `district`/`tehsil` accounts for 8 preserved-location probes in `check_dev.py`.
3. **`check_submission.py` items**: `starter/raksha.toml` still has `name = "your-team-name"`, `starter/README.md` is 268 words (`< 300`), and the 2-page Project Brief PDF is not yet added.
4. **Windows `K32GetProcessMemoryInfo` / `psapi`**: `peak_rss_mb` fallback returned `0.0` on Windows; POSIX `resource.getrusage` is used in the Linux sandbox.

---

## 11. Commands to Reproduce Results

```powershell
# 1. Run Milestone 10 adversarial privacy & utility test suite
python -m unittest discover -s tests/privacy_attacks -v

# 2. Run pipeline on dev/input
$env:RAKSHA_SECRET="m10-final-secret"
python starter/main.py --input dev/input --output my_output

# 3. Validate output contract & practice metrics
python validate_output.py --input dev/input --output my_output
python check_dev.py --output my_output

# 4. Run submission checker
python check_submission.py --repo starter
```
