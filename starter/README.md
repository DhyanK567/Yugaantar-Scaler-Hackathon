# GuptKavach — Adversarial Healthcare Privacy Intelligence Engine

> **Track 3 · Secret Wards**  
> **Team:** Team Halfwave  
> **Tagline:** Protect the Identity. Preserve the Medicine. Enable Collaboration.

---

## 1. Executive Summary & Vision

Healthcare generates vast quantities of valuable clinical data across hospital chains, diagnostic laboratories, and research institutions. While this data holds immense potential for medical research, epidemiological surveillance, and clinical quality improvement, the risk of patient re-identification remains a formidable barrier.

Medical records contain direct identifiers (names, relatives' names, phone numbers, Aadhaar, ABHA identifiers, MRNs, addresses, and PIN codes) as well as indirect quasi-identifiers (dates of admission, birth dates, ages, localities, and rare clinical attributes). Furthermore, in Indian healthcare systems, data is inherently multilingual—spanning English, Hindi (Devanagari script), and Hinglish transliterations.

**GuptKavach** is an air-gapped, CPU-only, zero-internet healthcare privacy firewall. It transforms sensitive clinical records into research-ready, privacy-protected datasets. GuptKavach simultaneously optimizes for two critical goals:
1. **Zero-Knowledge Re-Identification Defense:** Prevents adversarial re-identification across multilingual text, filenames, metadata, JSON keys, and encoded attachments.
2. **Clinical Utility Preservation:** Preserves diagnostic terms, medications, dosages, lab values, and temporal clinical trajectories intact.

---

## 2. System Architecture

GuptKavach employs an offline two-pass deterministic processing architecture:

```
[ Input Files ] (CSV, FHIR JSON, TXT, Binaries)
       │
       ▼
┌────────────────────────────────────────────────────────┐
│ PASS 1: Deterministic Ingestion & Corpus Intelligence  │
│  • Encodings: UTF-8, UTF-8-BOM, UTF-16, CP1252        │
│  • Strict Quarantine of binaries (PDF, PNG, XML, etc.) │
│  • Corpus-level name index & clinical lexicon filter   │
│  • Identity clue extraction (phonetic & demographic)   │
│  • Conservative cross-file clustering (F0.5 optimized) │
│  • Quasi-identifier group counting (k-anonymity)       │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│ PASS 2: Privacy Transformation & Output Export         │
│  • Contextual & multilingual redaction (En, Hi, Hing)  │
│  • Hidden-channel sanitization (names, keys, headers)  │
│  • FHIR R4 resource preservation & non-person safety   │
│  • Keyed HMAC-SHA256 pseudonyms (PSN-XXXXXX)           │
│  • Interval-preserving date shifting (±180 days)       │
│  • 5-year age banding & rare-value suppression         │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
[ Output Contract ]
 ├── sanitized/       (Protected records matching input structure)
 ├── records.jsonl    (Record-to-pseudonym continuity mapping)
 └── report.json      (SHA-256 digests, timings, andHonest counts)
```

---

## 3. How Each Part Works

### A. Ingestion & Format Preservation
- **Encoding Normalization:** Accurately decodes UTF-8, UTF-8 with BOM, UTF-16, and CP1252. Emits clean UTF-8.
- **Structural Integrity:** Retains exact CSV delimiters and headers; preserves JSON object nesting and FHIR R4 Bundle structure.
- **Quarantine Isolation:** Broken JSON, zero-byte files, and unsupported formats (PDF, PNG, XML) are routed into quarantine and explicitly declared in `report.json` with isolation reasons. They are never copied out raw.

### B. Detection & Meaning Traps
- **Multilingual Support:** Implements bilingual entity detection for English, Hindi (Devanagari), and Hinglish transliterations.
- **Clinical Distinction:** Uses a specialized clinical phrase dictionary to avoid the "meaning trap"—ensuring medical entities (e.g., *Parkinson's Disease*, *Alzheimer's*, *Bell's Palsy*, *Aspirin*, *Dr. Sharma*) are distinguished from patient identities.
- **Hidden Channels:** Automatically cleans sensitive patient identifiers from file names, JSON keys, metadata headers, and Base64-encoded file payloads.

### C. Linkage & Pseudonyms
- **Conservative Identity Graph:** Links records only when multi-point evidence (e.g., matching name soundex/metaphone, identical age/gender, or shared phone/MRN clues) establishes high consensus.
- **False-Merge Prevention:** Optimizes for F0.5 score (prioritizing precision over recall). If evidence is ambiguous, the system abstains rather than creating a false link.
- **Keyed Pseudonyms:** Generates deterministic `PSN-XXXXXX` pseudonyms using HMAC-SHA256 seeded with the private `RAKSHA_SECRET`. The same secret yields identical pseudonyms; different secrets produce completely disjoint pseudonym spaces.

### D. Privacy Layer & Quasi-Identifiers
- **Date Shifting:** Applies a deterministic integer day shift (within `±180` days) calculated as `HMAC(patient_key, RAKSHA_SECRET) % max_days`. All events for a single patient are shifted by the exact same offset, preserving longitudinal clinical intervals and disease trajectories.
- **Age Generalization:** Groups continuous ages into 5-year bands (e.g., 42 becomes `40-44`).
- **Quasi-Identifier Suppression:** Evaluates demographic group frequencies against a minimum group threshold (`k >= 5`). Unique outliers that could facilitate auxiliary linkage attacks are generalized or suppressed.

---

## 4. Models and Algorithms

To comply with the air-gapped, CPU-only requirement and prevent nondeterministic hallucination:
- **No LLMs, Generative AI, or Prohibited Models:** Zero dependencies on external AI APIs or heavyweight weights.
- **Deterministic Pattern Classifiers:** High-performance regular expression automata for Indian national identifiers (Aadhaar, PAN, ABHA, MRN, phone numbers, PIN codes).
- **Phonetic Transliteration & Normalization:** Rule-based Indic-to-Latin transliteration mapping and phonetic matching for Devanagari and Hinglish name variants.
- **HMAC-SHA256 Cryptographic Primitives:** Python standard library `hashlib` and `hmac` for keyed pseudonyms and deterministic date-shift generation.
- **Disjoint-Set Union-Find Clustering:** Efficient $O(N \cdot \alpha(N))$ graph clustering for cross-file patient record continuity.

---

## 5. Security Design & Air-Gap Compliance

- **Zero-Internet Operation:** Operates completely offline with network calls disabled.
- **Secret Containment:** `RAKSHA_SECRET` is read strictly from the process environment; it is never written to output files, debug logs, terminal standard output, or reports.
- **Log Privacy:** Terminal output emits only aggregate counts. Zero raw PII is logged.
- **Input Immutability:** Input directory files are treated as read-only and verified never to be modified or touched during processing.

---

## 6. Setup & Execution Instructions

### Prerequisites
- Python 3.8+ (CPU only, standard library + requirements.txt)

### Installation
```bash
pip install -r requirements.txt
```

### Standalone CLI Execution (Official Contract)
```bash
export RAKSHA_SECRET="practice"
python main.py --input ../dev/input --output ../my_output
```

### Verification & Self-Check
```bash
# Verify output contract
python ../validate_output.py --input ../dev/input --output ../my_output

# Run practice self-check scoring
python ../check_dev.py --output ../my_output

# Run official submission checker (3 runs, determinism, leakage check)
python ../check_submission.py --repo . --run
```

---

## 7. Web Control Centre (GuptKavach Console)

For operational deployment, GuptKavach includes an enterprise cybersecurity console:
- **Frontend:** Next.js + React + TypeScript + Tailwind CSS (dark navy, ice-blue/cyan accents).
- **Backend:** FastAPI (Python) wrapping the standalone engine without duplicating sanitisation logic.
- **Database:** Local SQLite for operational metadata and audit trails.

### Running the Web Console
```bash
# Start Backend API (Port 8000)
cd Yugaantar-Scaler-Hackathon
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

# Start Frontend Console (Port 3000)
cd frontend
pnpm run dev
```

---

## 8. Limitations and Future Roadmap

1. **OCR for Scanned Records:** Current policy quarantines image/PDF files to guarantee zero leak. Future milestones will integrate an offline, deterministic Tesseract-based Indic OCR pipeline.
2. **Audio Dictation Sanitization:** Future extensions will support streaming clinical audio redaction for outpatient voice notes.
3. **Differential Privacy Epsilon Guarantees:** Implementing formal $(\epsilon, \delta)$-differential privacy budgets for statistical query interfaces.
