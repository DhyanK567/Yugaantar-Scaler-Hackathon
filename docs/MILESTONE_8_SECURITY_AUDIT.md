# GuptKavach — Milestone 8 Security, Privacy & Robustness Audit

**Date:** 2026-11-26  
**Scope:** Standalone Privacy Engine (`starter/`), FastAPI Backend (`backend/`), Adversarial Suite (`tests/adversarial/`), Re-identification Attack Simulator (`tests/privacy_attacks/`).  
**Status:** Audit complete — **zero production files modified**.

---

## 1. Current Architecture

GuptKavach operates as a two-pass, offline, CPU-only, standard-library Python pipeline (`starter/main.py` + `starter/raksha_engine/`):

1. **Pass 1 (Ingestion & Discovery):** Deterministic sorted traversal of `input/`, multi-encoding decode (`UTF-8`, `UTF-8-BOM`, `UTF-16`, `cp1252`), quarantine gate for unsupported/empty/undecodable/deep/malformed files, semantic column/JSON-key classification (`patterns.py`), corpus-level multilingual name harvesting (`names.py`), conservative Union-Find identity clustering (`linking.py`), and `(age_band, district)` quasi-identifier frequency counting.
2. **Pass 2 (Sanitization & Export):** Multilingual & context-aware redaction, base64 payload sanitization, filename/header/metadata cleaning, FHIR R4 `Patient`/`RelatedPerson` handling (`sanitizer.py`), keyed HMAC-SHA256 pseudonyms (`PSN-XXXXXX`) and per-patient secret date shifting (`privacy.py`), and export of `sanitized/`, `report.json`, and `records.jsonl`.
3. **Web Gateway (`backend/`):** FastAPI wrapper invoking `starter/main.py` via subprocess (`engine_adapter.py`) and storing job metadata/audit logs in SQLite (`database.py`).

---

## 2. Verified Baseline (Independently Re-run)

| Check / Suite | Command | Measured Result |
|---|---|---|
| **Official Contract Validator** | `python validate_output.py --input dev/input --output my_output_m8` | **`CONTRACT OK`** (200 total, 195 sanitized, 5 quarantined, 823 records) |
| **Practice Self-Check** | `python check_dev.py --output my_output_m8 --show 10` | **Personal Data Leaked:** `35/3230` (`1.1%` — all 35 in `filename` channel; `content`, `deva`, `hinglish`, `base64`, `metadata`, `key`, `header` all `0.0%`) |
| **Canaries (`dev/input`)** | `check_dev.py` | **`0 / 4`** leaked |
| **Clinical Data Kept** | `check_dev.py` | **`4455 / 4457`** (`100.0%` rounded; **2 values lost**) |
| **Patient Linking** | `check_dev.py` | **`F0.5 = 0.93`**, `Precision = 1.00`, `Recall = 0.72`, `False Merges = 0` |
| **Raw Broken Copies** | `check_dev.py` | **`0`** |
| **Adversarial Suite** | `python tests/adversarial/run_adversarial.py` | `CONTRACT OK`; **2 / 21** missed PII (`Abdul Rahman`, `अब्दुल रहमान` due to `\u200b` zero-width evasion); **3 / 4** `CANARY_*` tokens leaked; **0 / 12** clinical traps lost |
| **Re-ID Attack Simulator** | `python tests/privacy_attacks/simulate_attack.py` | Raw CSV: `52/425` unique (`12.24%`); Sanitized CSV: **`6/425`** unique, **`10/425`** vulnerable `k<=2` (**`2.35%`**); Profiles uniquely re-ID'd: **`0/67`** |
| **Performance & Memory** | `tracemalloc` benchmark on `dev/input` | Peak Python traced memory: **`18.18 MB`** (limit: 4,096 MB); Wall time without profiler: **`~5.2s`** (limit: 900s) |

---

## 3. Identified Vulnerabilities (Ranked by Official Scoring Impact)

### V1. [CRITICAL] Zero-Width & Unicode Homoglyph Evasion (`patterns.py`, `names.py`)
- **Finding:** `normalize_digits()` only translates Devanagari digits (`०-९`). It does **not** apply `unicodedata.normalize("NFKC", ...)` or strip zero-width characters (`\u200b`, `\u200c`, `\u200d`, `\ufeff`).
- **Reproducible Failure:** In `tests/adversarial/input/notes/unicode_hinglish_note.txt`, `"Patient: Ab\u200bdu\u200bl Rah\u200bman"` bypassed both `RX_LABELED_NAME` and `CorpusNameIndex`, causing both `"Abdul Rahman"` and `"अब्दुल रहमान"` to leak (`2/21` FN).
- **Scoring Impact:** Direct identifier/full-name leak (`-1` penalty each, lowers Detection F2 recall, and A1 direct exposure risk).

### V2. [HIGH] Residual Quasi-Identifier Vulnerability (`k <= 2`: 10/425 CSV rows, 6 unique) (`starter/main.py`, `sanitizer.py`)
- **Finding:** `starter/main.py` computes `qi_counts` only over `(age_band, district)` without `gender`, and skips records where `district` is absent (e.g., `arogya_legacy_export.csv` or rows with only `PIN` prefix + `age_band` + `gender`). As a result, `rare_suppress` remains `False` for cells that are unique in the auxiliary voter registry (`registry.csv`).
- **Reproducible Failure:** `tests/privacy_attacks/simulate_attack.py` uniquely re-identified **6/425** sanitized CSV records (`10` with `k <= 2`, `2.35%` attack success rate).
- **Scoring Impact:** Directly impacts **Privacy Attack Arena (25% weight)** — A2/A3 record linkage and A5 targeted attack.

### V3. [HIGH] Clinical Meaning-Trap False Positive: `ASHA worker` (`names.py`)
- **Finding:** When `"Asha"` appears as a patient's first name in the corpus, `CorpusNameIndex` / `local_first_names` redacts `"ASHA"` inside `"Referred by ASHA worker"` and `"ASHA workers"`.
- **Reproducible Failure:** Exact 2 lost clinical preserve probes on `dev/input`:
  - `registration/arogya_legacy_export.csv` (`row:6`): `'Referred by ASHA worker'`
  - `clean/dengue_management_protocol.txt` (`doc`): `'ASHA workers'`
- **Scoring Impact:** Directly reduces **Detection Contextual Precision (`asha` trap group)** and **Clinical Utility (20% weight)**.

### V4. [HIGH] Backend Security & Data-at-Rest Gaps (`backend/main.py`, `backend/database.py`)
- **Findings:**
  1. **Unencrypted uploads & no cleanup:** `POST /api/jobs` writes raw uploaded files to `data/jobs/{job_id}/input/` in plaintext and never deletes them after job completion.
  2. **Error leakage:** `create_job` stores raw `result["stderr"]` in `jobs.error_msg` in SQLite and returns it via `GET /api/jobs/{job_id}`.
  3. **False tamper-proof claim:** `GET /api/audit` returns `"tamper_proof_seal": "HMAC-SHA256 Deterministic Ledger"`, but `audit_logs` has no HMAC signature column or verification.
  4. **Path containment & zip safety:** `GET /api/jobs/{job_id}/download` constructs `JOBS_DIR / job_id` without validating `job_id` format or resolving against `JOBS_DIR`.
  5. **Policy bounds:** `POST /api/settings` writes `date_shift_max_days`, `min_group_size`, `age_band_width` without range validation (`> 0`).
  6. **CORS:** `allow_origins=["*"]` combined with `allow_credentials=True`.

### V5. [MEDIUM] Identity Linking Recall (`0.72`) & Missing Initials/Relative Corroboration (`linking.py`)
- **Finding:** `linking.py` requires exact phonetic first-name + surname token match or exact `strong_id`/`MRN`. Records with initials (`R. K. Verma` vs `Rajesh Kumar Verma`), surname-first (`Verma, Rajesh K.`), or shared `relative_name + district + age` are left unlinked (`recall = 0.72`).
- **Scoring Impact:** **Identity Resolution (15% weight)**. Must improve recall conservatively without introducing any false merges (`precision = 1.00`).

### V6. [MEDIUM] Arbitrary `CANARY_*` Token Pattern (`patterns.py`)
- **Finding:** `tests/adversarial/` planted `CANARY_ALPHA_9911`, `CANARY_B64_7722`, `CANARY_META_5544` (3/4 leaked; only the filename canary was caught). While `dev/input` uses person-name canaries (`0/4` leaked), adding a generic `CANARY_[A-Z0-9_]+` safeguard prevents any synthetic canary-token leak.

### V7. [LOW] `check_dev.py` `filename` Channel Reporting (`35/3230` on `dev/input`)
- **Finding:** All 35 remaining leaks reported by `check_dev.py` on `my_output_m8` are in `filename` (`72.9%`), e.g. `Discharge_Summary_Reena_Nishad_JJH-0076928.txt`. Investigation needed to verify whether `sanitize_filename` skipped them or `check_dev.py` matched un-renamed paths.

---

## 4. Files Requiring Modification

| File | Planned Changes | Regression Risk |
|---|---|---|
| `starter/raksha_engine/patterns.py` | Strip zero-width chars & NFKC in `normalize_digits()`; add optional `CANARY_` pattern | Low (pure normalization) |
| `starter/raksha_engine/names.py` | Protect `ASHA worker`/`workers`/`didi`/`karmi` from patient-name redaction | Low (improves precision) |
| `starter/main.py` + `sanitizer.py` | Expand `qi_counts` to `(age_band, district, gender)` + `PIN` prefix suppression on `k < min_group`; inspect filename renaming | Medium (must keep utility >= 95%) |
| `starter/raksha_engine/linking.py` | Add initial-matching (`R. K. Verma` ↔ `Rajesh Kumar Verma`) & surname-first normalization with strict homonym guards | Medium (must keep `false_merges == 0`) |
| `backend/main.py` + `database.py` | Encrypt/clean up temp `job_input`, sanitize `error_msg`, add real HMAC chaining on `audit_logs`, validate `job_id` & settings bounds, fix CORS | Low (backend only; CLI untouched) |

---

## 5. New Tests Required

- `tests/adversarial/run_adversarial.py` (created; currently fails V1 & V6 — target `0` FN, `0` canary, `0` FP).
- `tests/privacy_attacks/simulate_attack.py` (created; target `0` unique re-identifications).
- `tests/test_linking_hardening.py` (to create: initials, cross-script, homonym separation, contradictory strong IDs).
- `tests/test_clinical_invariants.py` (to create: 9-day stay invariance, age-band containment, FHIR reference resolution, `ASHA worker` preservation).

---

## 6. Prioritised Implementation Order

1. **P0 — Fix V1 (Zero-width & NFKC normalization)** in `patterns.py` → re-run `tests/adversarial/run_adversarial.py`.
2. **P0 — Fix V3 (`ASHA worker` preserve guard)** in `names.py` → verify `4457/4457` clinical preservation on `dev/input`.
3. **P1 — Fix V2 (Stronger k-anonymity QI generalization/suppression)** in `main.py` / `sanitizer.py` → re-run `tests/privacy_attacks/simulate_attack.py` to drive unique re-identifications toward `0`.
4. **P1 — Fix V6 & V7 (Canary token guard + filename check)**.
5. **P2 — Fix V5 (Conservative initial/surname-first linking)** in `linking.py` → verify `false_merges == 0` and higher recall.
6. **P2 — Fix V4 (Backend temp cleanup, at-rest encryption/key handling, HMAC audit log, path containment, error sanitization)** in `backend/`.
