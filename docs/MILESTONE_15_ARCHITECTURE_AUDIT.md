# Milestone 15 — Complete Architecture Audit

**Date:** 2026-11-26  
**Branch:** `feature/guptkavach-privacy-engine`  
**Audit Scope:** Complete `starter/` pipeline, `raksha_engine/` (16 modules), `config/policy.yaml`, `backend/`, and `tests/`.

---

## 1. End-to-End Data-Flow Diagram

```
[Input Directory]
   │
   ├─► 1. Input Discovery & Path Containment (main.py, secure_fs.verify_path_containment)
   ├─► 2. Cryptographic Key Ring Init (crypto.GuptKavachKeyRing from RAKSHA_SECRET)
   ├─► 3. Format Detection & Decoding (UTF-8 / UTF-8-BOM / UTF-16 / cp1252)
   │       └─ Unsupported / Empty / Undecodable / Corrupt ──► Quarantine (report.json, never copied raw)
   │
   ├─► 4. Pass 1: Ingestion & Extraction
   │       ├─ 5-Tier Field Classification (qi_classifier.classify_field_tier, patterns.classify_field)
   │       ├─ Multilingual Name Harvesting (names.CorpusNameIndex, names.extract_names_from_text)
   │       └─ Identity Clue Extraction (linking.extract_clues_from_text, linking.merge_clues)
   │
   ├─► 5. Cross-Hospital Identity Resolution (linking.resolve_identities)
   │       └─ Union-Find with demographic compatibility + homonym & transliteration guards
   │
   ├─► 6. Pre-Mitigation Adversarial Risk & Attack Analysis
   │       ├─ Re-Identification Attack Simulator (attacker.simulate_attacks — 7 strategies)
   │       └─ Combination Risk Engine (risk_engine.evaluate_corpus_risk)
   │
   ├─► 7. Pass 2: Adaptive Mitigation & Sanitization
   │       ├─ Adaptive Mitigation Plan (mitigation.plan_record_mitigation)
   │       ├─ HMAC-SHA256 Pseudonyms & Date Shifting (privacy.pseudonym, privacy.shift_date_string)
   │       └─ Free-Text / CSV / JSON / FHIR R4 / Base64 / Filename Sanitization (sanitizer.py)
   │
   ├─► 8. Post-Mitigation Validation & Release Gate
   │       ├─ Offline FHIR R4 Bundle Validator (clinical_validator.validate_fhir_r4_bundle)
   │       ├─ Post-Mitigation Attack & Risk Re-Evaluation (attacker.py, risk_engine.py)
   │       └─ Release Gate (privacy_utility.evaluate_release_gate -> PASS / PASS_WITH_WARNINGS / BLOCKED)
   │
   └─► 9. Deterministic Output Export
           ├─ sanitized/ (UTF-8 sanitized files)
           ├─ records.jsonl (file, loc, pseudonymized patient)
           └─ report.json (counts, privacy_intelligence, clinical_integrity, stage_trace, timing, resources)
```

---

## 2. Module Dependency Map

| Module | Role | Connected in `main.py` | Dependencies |
| --- | --- | --- | --- |
| `patterns.py` | Regexes, column classification, `is_clinical_safe_field` | Yes | stdlib |
| `names.py` | Multilingual names, eponyms, org/Dr guards, phonetic norm | Yes | stdlib |
| `linking.py` | Clue extraction & conservative cross-file clustering | Yes | `names`, `patterns` |
| `privacy.py` | HMAC pseudonyms, secret date shifting, age bands, PIN prefix | Yes | stdlib |
| `sanitizer.py` | Free-text, CSV, JSON, FHIR R4, base64, filename sanitization | Yes | `names`, `patterns`, `privacy` |
| `qi_classifier.py` | 5-tier field classification (`A`–`E`) with reason codes | **Fixed in M15** (wired into `main.py`) | `patterns` |
| `attacker.py` | 7-strategy synthetic re-identification attack simulator | Yes | stdlib |
| `risk_engine.py` | Combination-based structural risk scoring & rare-group detection | Yes | `attacker` |
| `mitigation.py` | Adaptive generalisation/suppression planner | Yes | `risk_engine` |
| `privacy_utility.py` | Separated privacy/utility metrics & release gate | Yes | `attacker`, `risk_engine` |
| `clinical_validator.py` | Offline FHIR R4 Bundle validator & clinical probe checks | Yes | `privacy` |
| `crypto.py` | Key derivation & authenticated encryption helpers | Yes (`GuptKavachKeyRing`) | stdlib |
| `secure_fs.py` | Path traversal & symlink containment | Yes (`verify_path_containment`) | stdlib |
| `quarantine.py` | Encrypted quarantine vault helper | Imported (available for vault use) | `crypto`, `secure_fs` |
| `normalizer.py` | Offset-preserving multilingual normalizer (M9 unit-tested) | Standalone (`tests/multilingual`) | stdlib |
| `evidence.py` | Weighted evidence ledger (M9 unit-tested) | Standalone (`tests/multilingual`) | stdlib |

---

## 3. Audit Findings & Integration Fixes

1. **`qi_classifier.py` disconnected from `main.py`**: `classify_field_tier` was not called during Pass 1; wired into `main.py` to classify all CSV/JSON fields into tiers `A`–`E` and report `field_tier_counts` in `report.json`.
2. **Windows `peak_rss_mb` returning `0.0`**: `ctypes.windll.kernel32.GetCurrentProcess()` lacked `restype = wt.HANDLE` on 64-bit Windows, causing `GetProcessMemoryInfo` to fail silently. Fixed `argtypes`/`restype` so real `PeakWorkingSetSize` MB is reported.
3. **No stage-level execution trace in `report.json`**: Added `stage_trace` (safe non-PII metadata per pipeline stage) under `report.json["privacy_intelligence"]`.
4. **No duplicate/conflicting policy**: All thresholds and weights load centrally from `starter/config/policy.yaml`.
5. **Fallback safety**: Unsupported/empty/undecodable/corrupt files are quarantined in `report.json` and never copied raw to `sanitized/`.
