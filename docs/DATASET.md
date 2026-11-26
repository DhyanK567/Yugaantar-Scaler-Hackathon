# The synthetic hidden dataset

> For teams: your practice copy is in [`dev/`](../dev). This page explains how every dataset,
> practice and hidden, is built. New to this? Read [START_HERE.md](../START_HERE.md) first.

The organisers' generator builds a complete,
**synthetic** Indian hospital export and its private ground truth. Nothing in it
describes a real person: names, villages and identifiers are all generated. District
and tehsil names are real public administrative areas.

## Why generated, not hand-written

* **Same difficulty for everyone, unknown to everyone.** The hidden seed is committed by
  hash before the event ([FAIRNESS.md](FAIRNESS.md)). Teams can practise on public dev
  seeds with full ground truth, but cannot memorise the hidden data.
* **Truth can't drift from the bytes.** Every PII mention, clinical value, date and
  quasi-identifier is registered at the moment it is written into the file.
* **Bit-for-bit reproducible.** The RNG uses only `getrandbits`, so it is stable across
  Python versions. The manifest records SHA-256 hashes of the input tree, truth and
  attacker data, so anyone can regenerate and verify.

## Profiles

| Profile | Patients | Registry (population) | Files | Records | Use |
|---|---:|---:|---:|---:|---|
| `tiny` | 16 | 80 | ~107 | ~300 | unit tests |
| `small` | 48 | 240 | ~195 | ~810 | CI calibration, quick team self-checks |
| `standard` | 300 | 1,200 | 817 | 5,756 | **event default** |
| `large` | 900 | 3,600 | ~2,360 | ~18,600 | scaling run (Challenge 7) |

(`standard` numbers are for seed `dev-seed-1`; other seeds vary by a few percent.)

## Layout

```
<dir>/input/                    what the submission receives (read-only in the sandbox)
  registration/                 4 hospital systems, 4 formats, 4 encodings, 3 date conventions
  opd/                          nested JSON per hospital/month, with export metadata
  discharge/                    English, Hindi (Devanagari) and fragmentary discharge notes
  notes/                        Hinglish nursing notes
  prescriptions/                English/Hinglish and Hindi OPD prescriptions
  fhir/                         FHIR R4 document Bundles (ABDM-style discharge summaries)
  lab/                          long-format lab CSVs, JSON reports, one bulk LIMS export
  billing/                      PM-JAY/insurance claims (PAN, policy, rare procedures)
  clean/                        documents with no PII at all (false-positive traps)
  misc/                         hidden-leakage traps and malformed / unsupported files
<dir>/truth/truth.json          ground truth (never mounted into the sandbox)
<dir>/attacker/registry.csv     voter-roll-style population registry
<dir>/attacker/known_facts.jsonl  partial knowledge about some people (+ decoys)
<dir>/dataset_manifest.json     counts + hashes (publishable)
```

## Hospital systems (heterogeneity by design)

| System | Registration export | Encoding | Date format | UHID format |
|---|---|---|---|---|
| Sanjeevani Multispeciality (Lucknow) | CSV, full names, masked/plain Aadhaar, ABHA | UTF-8 with BOM, plus a byte-identical "(1)" duplicate | DD/MM/YYYY | `SNJ/26/071345` |
| Jeevan Jyoti Charitable (Barabanki) | Excel "Unicode text" TSV with Hindi headers; 35% of rows in Devanagari | **UTF-16 LE** with BOM | DD-MM-YYYY | `JJH-0071345` |
| Arogya Seva Sadan (Sitapur) | Legacy CSV, split first/last name, ragged rows, multi-line quoted notes | **cp1252** | **MM/DD/YYYY** | `UHID-071345` |
| District Hospital Hardoi | Nested JSON; Aadhaar stored as a JSON **number** under a misspelled key | UTF-8 | ISO | `DHH2026-071345` |

Patients from neighbouring districts register at a second hospital (22%), and 6%
re-register at the same hospital with a new UHID. That gives the duplicate and
partially overlapping records of Challenge 7.

## The seven challenges, as planted

| Challenge | What is planted | How it is scored |
|---|---|---|
| 1 Language trap | 5% of patients (preferring "Mohammad X") appear as `Mohammad Arif` (registration), `मोहम्मद आरिफ को … बुखार है` (Hindi prescription with **no ID**, only name + age + village), `Md. Arif - K/C/O …` (nursing note with IPD no.), `Arif sahab ka BP …` (OPD JSON note) | Script-level leak recall; language-trap link recall |
| 2 Meaning trap | 5% of patients get a relative named **Ramesh** and the doctor **Dr. Ramesh Srivastava**, plus `C/O Ramesh …, Ward 5` vs `C/O fever for 5 days`, `Ward: 5 (Medicine)`, `Ramipril 5 mg`, eponyms, "ASHA worker", `1-0-1` dose notation, `Levodopa 100/25 mg` | Relative-name leaks vs doctor/complaint/ward/dose preserve-probes |
| 3 Fragmented identity | 5% of married women: registration row (UHID, name, village), OPD JSON (`patient_ref`), and a discharge note with only `Meera, W/o Rajan` and `Visit: 18 November` | Link recall (linkable only through the name + relative combination) |
| 4 Re-identification | ≥1.2% of patients aged 95–99, moved to the tiniest village, rare disease + rare procedure, exact dates | Attack arena (quasi-identifier and date-anchored attacks) |
| 5 Clinical integrity | DOB, admission/discharge with real length of stay, BP, HbA1c, labs, dose + frequency everywhere | Preserve-probes, interval preservation, age-band truthfulness, statistics fidelity |
| 6 Hidden leakage | Names/IDs in JSON **keys**, a CSV **header**, **filenames**, export **metadata** (`source_path`), FHIR `text.div`, `meta.source`, a base64 `DocumentReference` attachment, JSON with `\u`-escaped Devanagari | Channel-by-channel leak scan |
| 7 Performance / robustness | 1,800-row bulk export, 1,500-deep nested JSON, truncated JSON, XML, PDF, JPEG, empty file, invalid UTF-8, JSON behind a `.csv` extension | Runtime, memory, scaling, crash-safety, quarantine handling |

## The chaos round (generalisation, not memorisation)

The practice data reveals its templates, labels, ID formats and name pool, so a system can
memorise them. At least one **hidden** dataset keeps the same challenges but adds variation
that **never appears in practice data**: people with names from other regions of India,
new field labels in English and Hindi, noisier identifier and phone formats, new date
formats and renamed export columns. What exactly changes stays sealed until the results.

A solution tuned only to the practice files loses about 30 points on that dataset.
Build rules that understand **context** ("this is a label for a name", "this column holds
phone numbers") instead of lists of exact strings.

## Canaries

Every dataset plants 4 **canary identities**: names and phone numbers that exist nowhere
else in the data or in any name list. They sit in a visitor log, a nested helpdesk ticket,
a base64 attachment inside JSON, and a CSV remark column. No gazetteer can find them; only
context-aware detection can ("Visitor log: …", "called by …", "raised_by.name"). If a
canary appears anywhere in a release or side channel, it proves a leak path, and it is
penalised separately (−3 each, see [SCORING.md](SCORING.md)).

## WhatsApp forwards

About 15% of lab encounters also arrive as a WhatsApp-forwarded message: a timestamped
header from a relative ("Mohan Chachu"), the patient by honorific name, lab values,
"Dolo 650 BD x 5 days" (a dose, not a phone number) and a phone number to call.

## Homonyms (anti-merge)

At least 2% of patients are paired with another patient who has **exactly the same
name** but a different village, age and relative. Natural name collisions in the
population add more. Merging a pair is a false merge.

## Ground truth model

The scoring unit is a **record**: `row:N` (CSV/TSV data row), an RFC 6901 pointer
(`/visits/3`, `/patients/12`, `/results/40`), `doc` (a whole text or FHIR document), or a
file-level channel (`@file` metadata/keys, `@header`, `@filename`).

Each unit stores:

* `entities`: every PII mention, with type, surface string, script (`latin`, `deva`,
  `hinglish`), channel, and whether it is a *critical* direct identifier. Names keep
  their identifying tokens (generic tokens such as *Devi*, *Kumar*, *Md.* and *ji* are not
  identifying on their own).
* `preserve`: clinical and contextual probes (medication + dose, frequency, vitals,
  labs, diagnosis codes, complaints, doctor lines, hospital ward, eponyms). An optional
  `path` pins a probe to a structured field, and `trap` marks a Challenge-2 probe.
* `dates`: each clinical event date with its true value, the patient, and how to find
  it in the output (column/pointer for structured data, the text anchor for notes).
* `fields`: quasi-identifier truth (age, DOB, gender, village, district, PIN) for
  checking that generalisations are truthful.
* `cid`: the linkability component (below).

### Linkability is computed, not hand-labelled

Two records of the same patient count as **linkable** when the data itself contains a
path between them:

* a shared strong identifier (UHID, IPD no., Aadhaar, ABHA, phone, email, PAN,
  insurance ID) that belongs to that patient alone, **or**
* the same name key plus a secondary key (DOB, relative's name, or village + age ±1)
  whose combination is unique to that patient across the whole dataset.

Records inside one connected component must be linked (recall). Records with no such
path are *ambiguous*: leaving them unlinked costs nothing, but linking one to the wrong
patient is a false merge (precision). This is how "avoid linking records when evidence
is insufficient" becomes measurable.

## Attacker knowledge (never shown to submissions)

* `registry.csv`: every person in the synthetic population (4–5× the number of
  patients), with name, relation + relative name, gender, age, house number, mohalla,
  village, tehsil, district and PIN, like an electoral roll. For 60% of people a
  "leaked contacts" overlay adds phone, email and the last 4 Aadhaar digits.
* `known_facts.jsonl`: for ~30% of patients (and every re-identification-trap patient),
  one true visit date, the hospital, and sometimes the condition. Decoys (people who
  never visited) test membership inference.
