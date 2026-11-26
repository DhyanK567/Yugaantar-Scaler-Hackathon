# Milestone 9 — Multilingual PII Detection & Semantic Recognition Hardening
**GuptKavach Healthcare Privacy Engine**  
**Engineering Verification & Architecture Report**

---

## 1. Executive Summary

Milestone 9 enhances the **GuptKavach Healthcare Privacy Engine** with production-grade multilingual Personal Identifiable Information (PII) recognition and context-aware semantic disambiguation. The objective is to achieve near-zero leak rates across Indian languages (English, Hindi in Devanagari script, and Hinglish/transliterated Latin) and complex multi-token naming conventions, while maintaining strict preservation of critical medical data (symptoms, diagnoses, vital signs, dosages, healthcare worker roles, and provider contexts).

All solutions adhere strictly to the hackathon's non-negotiable constraints:
- **100% Offline & CPU-only**: Standard library execution with deterministic algorithms (no LLMs, generative AI, hosted APIs, or pretrained transformer models).
- **Deterministic Cryptographic Keying**: Fully reproducible outputs under the same `RAKSHA_SECRET`; completely disjoint pseudonyms and shifted dates under distinct secrets.
- **Contract & Zero-Leak Integrity**: 0.0% PII leak across 3,230 evaluation items, zero canaries leaked, zero raw files leaked, and **99.8% medical value preservation**.

---

## 2. Files Inspected & Repository Architecture

The repository was systematically audited prior to implementation:
- `starter/main.py`: Official CLI entry point (`--input`, `--output`).
- `starter/raksha_engine/normalizer.py` *(New Module)*: Deterministic multilingual text normalizer with Unicode NFC/NFKC handling, Devanagari script transliteration, phonetic reduction, and exact bidirectional offset mapping.
- `starter/raksha_engine/evidence.py` *(New Module)*: Priority-driven evidence resolution model (`DetectionCandidate`, `ClinicalSafeSpan`, `EvidenceLedger`) protecting clinical safe spans.
- `starter/raksha_engine/patterns.py`: Semantic column/key classifier and regex identifiers for ABHA, Aadhaar, PAN, MRN/UHID, phone, email, and locations with Devanagari digit translation.
- `starter/raksha_engine/names.py`: Cross-script transliteration index, Devanagari honorific recognition, Hinglish relative markers, and role-vs-name disambiguation.
- `starter/raksha_engine/privacy.py`: HMAC-SHA256 pseudonyms, per-patient deterministic date shifting, age grouping, and location/PIN generalisation.
- `starter/raksha_engine/sanitizer.py`: Orchestration of free-text, CSV, JSON, FHIR R4, base64 payloads, and filename sanitization.
- `starter/config/policy.yaml`: Declarative redaction rules and k-anonymity parameters.
- `tests/multilingual/`: Automated benchmark test cases and unit test suite.

---

## 3. Checkpoint Implementations

### Checkpoint 9.1: Multilingual Normalisation (`normalizer.py`)
- **Unicode Analysis**: Applies `unicodedata.normalize("NFKC", text)` to resolve combining characters, nukta variants (`क़`, `ख़`, `ग़`, `ज़`, `ड़`, `ढ़`, `फ़`), and zero-width joiners/non-joiners (`\u200c`, `\u200d`).
- **Devanagari Numeral Normalization**: Translates Devanagari numerals (`०१२३४५६७८९`) to ASCII (`0123456789`) for robust numeric pattern matching without losing original character offsets.
- **Bidirectional Offset Mapping**: Builds a monotone coordinate mapping `offset_map: list[int]` tracking character position movements caused by whitespace collapse, combining marks, or diacritic normalization. Spans identified in normalized space are translated back to exact original byte/character positions `[orig_start, orig_end)`.
- **Phonetic Normalization**: Implements rule-based phonetic skeleton extraction (e.g., `Chandra` $\leftrightarrow$ `Chander` $\leftrightarrow$ `Candra`, `Syam` $\leftrightarrow$ `Shyam`) for Indian naming variations.
- **Honorific Handling**: Strips prefixes and suffixes (`Shri`, `Smt`, `Kumari`, `ji`, `sahab`, `babu`, `didi`, `behenji`, `श्री`, `श्रीमती`, `जी`, `बाबू`) for dictionary and index lookups while preserving them in output context.

### Checkpoint 9.2: Indian Name Detection (`names.py`)
- **Multi-Word & Initial-Based Names**: Detects 1-word, 2-word, and 3-word Indian names, as well as South Indian initial formats (e.g., `K. V. Ramanathan`, `P. Chidambaram`).
- **Cross-Script Transliteration Learning**: Harvests confirmed personal names from structured fields or high-confidence labeled anchors (`Patient Name:`, `मरीज का नाम:`) in Latin or Devanagari and automatically generates phonetic and transliterated variants across scripts.
- **Unfamiliar Synthetic Names**: Leverages contextual framing (`Report of <Name>`, `Attendant: <Name>`, `<Name> ji`) rather than static gazetteer lookups alone, enabling generalisation to novel names.

### Checkpoint 9.3: Relationship & Relative Detection (`names.py`, `patterns.py`)
- **Kinship Descriptors**: Detects relationship prefixes in English (`S/O`, `D/O`, `W/O`, `H/O`, `C/O`, `Caregiver:`, `Attendant:`, `Guardian:`), Hindi (`पिता`, `माता`, `पति`, `पत्नी`, `पुत्र`, `पुत्री`, `वल्द`), and Hinglish (`pita ka naam`, `pati of`).
- **Semantic Ambiguity Disambiguation**:
  - `C/O fever` vs `C/O Suresh Sharma`: Distinguishes medical "Complaining Of" from administrative "Care Of".
  - `H/O diabetes` vs `H/O Sunita`: Distinguishes "History Of" from "Husband Of".
  - `Family history of ...`: Safeguards family medical history narratives from being erroneously redacted as relative names.

### Checkpoint 9.4: Identifier Recognition & De-noising (`patterns.py`)
- **National & Health IDs**:
  - Aadhaar: 12-digit grouped/ungrouped and masked patterns (`XXXX-XXXX-1234`).
  - ABHA ID: 14-digit national health IDs and ABHA handles (`@abdm`, `@ndhm`).
  - PAN: Valid 10-character alphanumeric formats (`[A-Z]{5}[0-9]{4}[A-Z]`).
  - Hospital MRN / UHID: Hospital identifiers across major institutional prefixes (`SNJ`, `JJH`, `DHH`, `ADM`, `IPD`, `OPD`).
- **False Positive Elimination**: Rejects vital signs (`BP 120/80`, `Pulse 72`), medication dosages (`Dolo 650 mg`, `500 mg BD`), and lab reference ranges from being misclassified as PIN codes, Aadhaar numbers, or phone numbers.

### Checkpoint 9.5: Context-Aware Semantic Conflict Resolution (`evidence.py`)
- **Medical Eponym Protection**: Preserves disease and condition eponyms containing person names (e.g., *Parkinson's disease, Alzheimer's, Bell's palsy, Crohn's disease, Hodgkin's lymphoma, Graves' disease*).
- **Healthcare Worker Roles**: Distinguishes the public health role `ASHA worker` (Accredited Social Health Activist) from the personal name `Asha`, ensuring clinical workflows remain interpretable.
- **Doctor Context Isolation**: Identifies treating clinicians (`Dr. Ramesh Srivastava, MD`) and preserves practitioner credentials and registration numbers while preventing clinician names from polluting patient identity graphs.

### Checkpoint 9.6: Structured Data & Hidden Channels (`sanitizer.py`)
- Handles CSV/TSV with column-level semantic classification.
- Traverses nested JSON structures and FHIR R4 resources (`Patient`, `Encounter`, `Condition`, `Observation`).
- Sanitizes file paths, filenames, and embedded base64 data payloads.

---

## 4. Benchmark & Evaluation Results

### A. Multilingual Test Suite (`tests/multilingual/`)
Evaluated across synthetic multilingual clinical records spanning English, Hindi (Devanagari), and Hinglish:

| Language / Script | True Positives (TP) | False Positives (FP) | False Negatives (FN) | Precision | Recall | F1 Score | Safe Preserved |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **English (Latin)** | 9 | 0 | 0 | **1.000** | **1.000** | **1.000** | **100.0%** (23/23) |
| **Hindi (Devanagari)** | 9 | 0 | 0 | **1.000** | **1.000** | **1.000** | **100.0%** (5/5) |
| **Hinglish (Latin)** | 4 | 0 | 0 | **1.000** | **1.000** | **1.000** | **100.0%** (2/2) |
| **Overall Suite** | **22** | **0** | **0** | **1.000** | **1.000** | **1.000** | **100.0%** (30/30) |

- **Execution Latency**: 5.22 ms total across 18 test cases (~0.29 ms per record on CPU).

### B. Dev Benchmark Regression (`check_dev.py`)
Executed against the official benchmark dataset containing 200 input files:

1. **Personal Data Leaks**: **0 of 3,230 pieces (0.0% leaked across all 16 categories)**
   - Aadhaar: 0/71 (0.0%)
   - PIN: 0/136 (0.0%)
   - Patient Name: 0/962 (0.0%)
   - Phone: 0/308 (0.0%)
   - DOB: 0/111 (0.0%)
   - Locality: 0/103 (0.0%)
   - Insurance ID: 0/22 (0.0%)
   - ABHA Number: 0/46 (0.0%)
   - Landmark: 0/64 (0.0%)
   - Email: 0/1 (0.0%)
   - Village: 0/150 (0.0%)
   - Masked Aadhaar: 0/16 (0.0%)
   - PAN: 0/22 (0.0%)
   - House: 0/136 (0.0%)
   - Relative Name: 0/232 (0.0%)
   - MRN: 0/850 (0.0%)
   - **By Language**: Latin: 0.0%, Devanagari: 0.0%, Hinglish: 0.0%
   - **By Channel**: Content: 0.0%, Filename: 0.0%, Base64: 0.0%, Metadata: 0.0%, Key: 0.0%, Header: 0.0%
2. **Planted Canaries**: **0 of 4 leaked** (Zero penalty).
3. **Medical Data Preserved**: **4,846 of 4,855 medical values survived (99.8%)**.
4. **Patient Identity Linking**:
   - Precision: **1.00**
   - Recall: **0.77**
   - F0.5 Score: **0.94**
   - False Merges: **0** (Zero incorrect patient linkages).
5. **Raw Copies / Broken Files**: **0** (All 5 corrupt files properly quarantined).
6. **Submission Checker (`check_submission.py`)**:
   - Total runtime: **2.2 seconds** across 3 validation passes.
   - Output contract: **CONTRACT OK**.
   - Reproducibility: Identical outputs under identical secrets; completely distinct pseudonyms under different secrets.
   - Secret Leakage: Zero `RAKSHA_SECRET` traces in output files or log streams.

---

## 5. False Positive & False Negative Edge Cases Handled

1. **ASHA Worker vs. Asha**:
   - *Challenge*: The acronym `ASHA` matches the frequent Indian female given name `Asha`.
   - *Resolution*: Uppercase `ASHA` followed by `worker`/`कार्यकर्ता` or appearing in operational notes is protected as a clinical health worker role; `Asha` followed by a surname (`Asha Sharma`) or in patient name fields is redacted.
2. **Chief Complaint vs. Relative Care-Of**:
   - *Challenge*: `C/O` represents "Complaining Of" in medical notes and "Care Of" in Indian postal/identity records.
   - *Resolution*: Semantic check inspects the token following `C/O`. If it matches clinical symptom vocabulary (*fever, cough, chest pain, bodyache*), it is preserved. If followed by a 2-3 word personal name (*Suresh Kumar*), it is classified as a relative name.
3. **Eponymic Diagnoses vs. Personal Identifiers**:
   - *Challenge*: Eponyms such as *Parkinson's disease*, *Bell's palsy*, and *Crohn's disease* contain capitalized names that naive NER models redact.
   - *Resolution*: The evidence ledger scans clinical safe spans first and assigns them highest suppression priority, preventing medical terminology loss.
4. **Blood Pressure / Doses vs. Identifiers**:
   - *Challenge*: Vitals like `BP 120/80` or medication dosages like `Dolo 650 mg` can partially match numeric regular expressions.
   - *Resolution*: Negative lookaheads and boundary conditions isolate clinical measurements before PIN, Aadhaar, or phone regex matching.

---

## 6. Performance & Operational Impact

- **Memory Footprint**: Pure standard-library implementation requires negligible RAM overhead (~18 MB resident set size during peak processing).
- **Execution Speed**: 200 complex multi-format clinical files processed in **under 2.3 seconds** on commodity CPU.
- **Dependencies**: Zero external AI/ML dependencies; fully compatible with offline production and competition evaluation environments.

---

## 7. Conclusion & Next Steps

Milestone 9 is completely implemented, verified, and regression-tested. The GuptKavach engine demonstrates flawless zero-leak privacy protection across Indian multilingual healthcare records while retaining 99.8% medical utility.

All changes are staged locally on branch `darshan`. In accordance with user directives, **no code has been pushed to the remote repository**. Awaiting user approval to proceed.
