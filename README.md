# GuptKavach (RAKSHA) — Adversarial Healthcare Privacy Intelligence Engine

**Yugaantar DevForge Hackathon · Track 3: Secret Wards**

An offline, CPU-only, LLM-free healthcare privacy firewall that sanitizes heterogeneous clinical exports (English, Hindi/Devanagari, Hinglish; CSV, TSV, JSON, FHIR R4 Bundles, clinical notes, and WhatsApp forwards), preserves medical utility, resolves cross-file patient identities with keyed HMAC pseudonyms, and defends against linkage and re-identification attacks.

---

## Problem Statement

Multi-hospital clinical research datasets combine heterogeneous exports containing direct identifiers (names, relatives, phones, Aadhaar, ABHA, MRNs, PAN, insurance IDs) and quasi-identifiers (dates, ages, villages, PINs) across visible and hidden channels (filenames, CSV headers, JSON keys, metadata paths, base64 attachments). Naive redaction either leaks multilingual/hidden PII or destroys clinical utility (doses, vitals, diagnoses, length of stay).

---

## Architecture

GuptKavach implements a deterministic **two-pass offline pipeline** in `starter/`:

```text
dev/input/ (CSV, TSV, JSON, FHIR R4, TXT, malformed/binary)
   │
   ▼
[Pass 1: Ingestion & Discovery]  (starter/main.py)
   ├─ Multi-encoding decode (UTF-8, UTF-8-BOM, UTF-16, cp1252)
   ├─ Quarantine gate (unsupported, empty, undecodable, deep/malformed JSON)
   ├─ Semantic column & JSON-key classification (raksha_engine/patterns.py)
   ├─ Corpus-level multilingual name & clue extraction (raksha_engine/names.py)
   ├─ Conservative cross-file clustering (raksha_engine/linking.py)
   └─ Quasi-identifier group counting (age_band, district)
   │
   ▼
[Pass 2: Sanitization & Export]  (raksha_engine/sanitizer.py, privacy.py)
   ├─ Multilingual & context-aware PII redaction (English / Devanagari / Hinglish)
   ├─ Medical-context guards (Dr., C/O complaints, K/C/O, doses, labs, eponyms)
   ├─ Hidden-channel sanitization (filenames, headers, keys, metadata, base64)
   ├─ FHIR R4 Patient & RelatedPerson sanitization with reference preservation
   ├─ Keyed HMAC-SHA256 pseudonyms (PSN-XXXXXX) & per-patient secret date shifts
   └─ Age banding, PIN prefixing, location generalization, rare-group widening
   │
   ▼
output/
   ├── sanitized/     (clean research release)
   ├── report.json    (SHA-256 mappings, honest counts, timing, RSS)
   └── records.jsonl  (record locators + pseudonymous patient IDs)
```

---

## Technology Stack

- **Language:** Python 3.10+ (tested on Python 3.14.7)
- **Runtime Dependencies:** Python Standard Library only (`csv`, `json`, `hmac`, `hashlib`, `re`, `unicodedata`, `base64`, `datetime`, `pathlib`) — zero external network calls, zero LLMs, zero models > 50M parameters, CPU-only, < 6 seconds execution time.
- **Configuration:** `starter/config/policy.yaml` (`age_band_years: 5`, `date_shift_max_days: 180`, `min_group_size: 5`).

---

## Privacy Methodology

1. **Multilingual & Contextual PII Detection:**
   - Semantic column/key classification supporting English, Hinglish (`Naam`, `Ling`, `Umar`, `Janm Tithi`, `Pata`, `Gaon`, `Jila`), and Devanagari (`नाम`, `ग्राम`, `मकान नं.`) variants.
   - Rule-based Devanagari-to-Latin phonetic transliteration (`मोहम्मद` ↔ `Mohd` ↔ `Mohammad`) and corpus-learned name matching.
   - Medical-context preserve guards protecting `Dr. <Name>`, `C/O <symptom>`, `K/C/O <disease>`, eponyms (`Addison's`, `Parkinson's`, `Crohn's`), drug dosages (`650mg`, `1-1-1`), and lab values.
2. **Hidden-Channel Hygiene:**
   - Deterministic filename sanitization for PII-bearing paths with `input_sha256` → `output` declaration in `report.json`.
   - Base64 attachment decoding, sanitization, and re-encoding; JSON key/metadata (`source_path`) and CSV header cleaning.
3. **Conservative Cross-File Identity Resolution:**
   - Blocking and Union-Find clustering over strong IDs (`PHONE`, `AADHAAR`, `ABHA`, `PAN`, `MRN`/`UHID`) and corroborated transliterated full names.
   - Demographic compatibility checks (gender, birth year, age) prevent homonym merges; uncertain records return `null`.
4. **Quasi-Identifier Protection:**
   - Keyed HMAC-SHA256 pseudonyms (`PSN-XXXXXX`) and per-patient secret date shifts (`±180` days, preserving intervals and length of stay).
   - 5-year age bands (`85+` cap), 3-digit PIN prefixes (`229***`), village suppression, and rare-group widening (`10`-year bands / district suppression when `(age_band, district)` count `< min_group_size`).

---

## Installation & Execution

```bash
# 1. Create and activate virtual environment
python -m venv .venv
source .venv/Scripts/activate        # Git Bash (Windows)
# .\.venv\Scripts\Activate.ps1       # PowerShell (Windows)

# 2. Install dependencies (stdlib only)
pip install -r starter/requirements.txt

# 3. Run GuptKavach / RAKSHA
export RAKSHA_SECRET="practice"      # Git Bash
python starter/main.py --input dev/input --output my_output_v2
```

---

## Testing & Measured Results (`dev/input`)

```bash
python validate_output.py --input dev/input --output my_output_v2
python check_dev.py --output my_output_v2 --show 10
```

| Metric | Starter Baseline | GuptKavach (Current) |
|---|---:|---:|
| Contract Validation (`validate_output.py`) | `CONTRACT OK` | `CONTRACT OK` |
| Files Sanitized / Quarantined | `195` / `5` | `195` / `5` |
| Raw Broken Files Copied | `0` | `0` |
| Personal Data Leaked (overall) | `84.1%` (`2718/3230`) | **`2.8%`** (`92/3230`) |
| Latin / Devanagari / Hinglish Leaked | `82.8%` / `100%` / `100%` | **`2.8%` / `3.5%` / `2.7%`** |
| Base64 / Metadata / Key Leaked | `100%` / `100%` / `100%` | **`0.0%` / `0.0%` / `0.0%`** |
| Medical Data Preserved | `100.0%` | **`98.8%`** (`4404/4457`) |
| Patient Linking (`F0.5` / Precision / Recall) | `0.00` / `0.00` / `0.00` | **`0.66`** / `0.63` / `0.78` |
| Execution Time | `5.06s` | **`5.23s`** |
| Determinism (2 runs, same secret) | — | **`100%` byte-identical** |

---

## Security Considerations

- `RAKSHA_SECRET` is read solely from the environment and never logged, printed, or written to disk.
- Stdout logs only aggregate counts (`files`, `sanitized`, `quarantined`, `records`).
- Unsupported, empty, undecodable, or deeply nested/malformed files are quarantined (`output: null`) and never copied raw into `sanitized/`.
- Original input files are read-only and never modified.

---

## Known Limitations

- Remaining `2.8%` leaks are primarily unlabelled relative names inside FHIR narrative/composition fields, a small number of `MM-DD-YYYY` DOBs in mixed-format columns, and `3` of `4` planted canaries in edge-case channels.
- `check_dev.py` checks `sanitized/` paths against `truth.json` relative names when files are renamed, accounting for the reported `filename` metric even though PII filenames were replaced in `sanitized/`.
- `peak_rss_mb` reports `0.0` on Windows because Python's `resource` module is Unix-only (populated automatically in the Linux evaluation sandbox).
