# Milestone 10 — Baseline Snapshot & Gap Analysis

**Date:** 2026-11-26  
**Branch:** `feature/guptkavach-privacy-engine` (commit `c91189e`)  
**Environment:** Offline CPU-only Python 3.12.10 (Windows)

---

## 1. Baseline Architecture

The existing GuptKavach (`starter/`) pipeline executes a two-pass offline architecture:

1. **Pass 1 (`starter/main.py`)**:
   - Reads `.csv`, `.tsv`, `.json`, and `.txt` files in sorted deterministic order; quarantines unsupported/empty/undecodable/corrupt files.
   - Extracts corpus-level person names (`raksha_engine/names.py`) and per-record identity clues (`raksha_engine/linking.py`).
   - Resolves cross-file patient clusters conservatively via union-find with demographic compatibility checks.
   - Counts `(5-year age_band, district)` quasi-identifier groups for basic rare-group flagging.
2. **Pass 2 (`starter/main.py`, `raksha_engine/sanitizer.py`, `raksha_engine/privacy.py`)**:
   - Redacts direct identifiers (Aadhaar, ABHA, PAN, Phone, Email, MRN, Insurance ID, Patient/Relative names, House, Locality, Landmark, Village, DOB) across free text, CSV/TSV, JSON/FHIR R4, filenames, headers, keys, and base64 attachments.
   - Applies HMAC-SHA256 pseudonyms (`PSN-XXXXXX`) and deterministic per-patient date shifting keyed by `RAKSHA_SECRET`.
   - Exports `sanitized/`, `records.jsonl`, and `report.json`.

---

## 2. Baseline Measurements (`dev/input`, `RAKSHA_SECRET="m10-baseline-secret"`)

| Check / Metric | Observed Baseline Result |
| --- | --- |
| Files processed | 200 total, 195 sanitized, 5 quarantined, 823 records |
| Official `validate_output.py` | `CONTRACT OK` |
| Personal data leakage (`check_dev.py`) | `0 / 3230` (0.0%) |
| Canary detections (`check_dev.py`) | `0 / 4` |
| Medical data preservation (`check_dev.py`) | `4853 / 4855` |
| Patient linking (`check_dev.py`) | Precision `1.00`, Recall `0.76`, F0.5 `0.94`, wrong merges `0` |
| Raw copies of broken/unsupported files | `0` |
| Determinism (same secret twice) | `PASS` |
| Pseudonym separation (different secrets) | `PASS` |
| Secret/log/file leak check | `PASS` |
| FHIR R4 bundle integrity (19 bundles) | `PASS` |
| Malformed/unsupported input test (san=1, quar=4) | `PASS` |

---

## 3. Identified Weaknesses for Milestone 10

1. **No formal 5-tier quasi-identifier classification layer (M10.1)**: Only flat regex column classification exists; fields are not categorized into Direct Identifier, Quasi-Identifier, Sensitive Clinical, Clinical Utility, and Safe Metadata with reason codes.
2. **No re-identification attack simulator (M10.2)**: No automated adversarial simulator tests exact combinations, age+gender+location, rare diagnosis+location, admission+LOS, geographic narrowing, cross-record linkage, or rare attribute combinations.
3. **No combination-based risk engine (M10.3–M10.4)**: Current QI check only counts `(age_band, district)`, ignoring multi-attribute combinations, temporal uniqueness, department rarity, and rare diagnosis/treatment combinations.
4. **No structured mitigation audit trail (M10.5)**: Generalisation/suppression decisions are not logged with `field_category`, `action`, `reason_code`, and `policy_version`.
5. **No privacy-utility coupling or release gate (M10.6–M10.7)**: `report.json` has no release eligibility decision (`PASS` / `PASS_WITH_WARNINGS` / `BLOCKED`) or pre/post attack risk reduction summary, and `resources.peak_rss_mb` is hardcoded to `0.0`.
6. **No dedicated adversarial privacy attack test suite (M10.8)**: `tests/privacy_attacks/` does not exist yet.
