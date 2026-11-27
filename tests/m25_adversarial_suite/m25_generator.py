#!/usr/bin/env python3
"""M25 Independent Synthetic & Adversarial Benchmark Generator.

Deterministic, seed-controlled generator producing:
1. Large Independent Benchmark: 1,200 synthetic records (600 dev_gen + 600 held_out)
2. 15-Category Adversarial PII Corpus
3. Identity Linking Stress Corpus (homonyms, transliterations, initials, traps)
4. 1,000+ Clinical Preservation Adversarial Values
5. Filename & Directory Metadata Privacy Corpus
6. Re-Identification Quasi-Identifier Attack Corpus
"""
from __future__ import annotations

import csv
import io
import json
import random
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Tuple


_FIRST_NAMES = [
    ("Aarav", "आरव"), ("Vivaan", "विवान"), ("Aditya", "आदित्य"), ("Vihaan", "विहान"),
    ("Arjun", "अर्जुन"), ("Sai", "साई"), ("Reyansh", "रेयांश"), ("Krishna", "कृष्ण"),
    ("Ananya", "अनन्या"), ("Diya", "दिया"), ("Saanvi", "सान्वी"), ("Aadhya", "आध्या"),
    ("Kavita", "कविता"), ("Sunita", "सुनीता"), ("Meera", "मीरा"), ("Priya", "प्रिया"),
    ("Farhan", "फरहान"), ("Zoya", "ज़ोया"), ("Harpreet", "हरप्रीत"), ("Gurpreet", "गुरप्रीत"),
    ("Rohan", "रोहन"), ("Nikhil", "निखिल"), ("Sneha", "स्नेहा"), ("Pooja", "पूजा"),
    ("Ramesh", "रमेश"), ("Suresh", "सुरेश"), ("Lakshmi", "लक्ष्मी"), ("Deepak", "दीपक"),
]

_LAST_NAMES = [
    ("Sharma", "शर्मा"), ("Verma", "वर्मा"), ("Deshmukh", "देशमुख"), ("Kulkarni", "कुलकर्णी"),
    ("Subramanian", "सुब्रमण्यन"), ("Nair", "नायर"), ("Iyer", "अय्यर"), ("Patel", "पटेल"),
    ("Siddiqui", "सिद्दीकी"), ("Khan", "खान"), ("Kaur", "कौर"), ("Gill", "गिल"),
    ("Chatterjee", "चटर्जी"), ("Banerjee", "बनर्जी"), ("Reddy", "रेड्डी"), ("Rao", "राव"),
    ("Mishra", "मिश्रा"), ("Tiwari", "तिवारी"), ("Joshi", "जोशी"), ("Gupta", "गुप्ता"),
]

_DOCTORS = [
    "Dr. Arvind Joshi", "Dr. Meenakshi Iyer", "Dr. Rajeshwar Rao",
    "Dr. Fatima Begum", "Dr. Harjinder Singh", "Dr. Sunanda Kulkarni",
]

_HOSPITALS = [
    "Sahyadri Care Centre", "Kaveri Memorial Hospital", "Deccan Health Institute",
    "Vindhya Medical Trust", "Narmada Multi-Specialty", "Ganga Apex Clinic",
]

_CITIES = [
    ("Pune", "411004"), ("Lucknow", "226001"), ("Chennai", "600002"),
    ("Jaipur", "302001"), ("Kochi", "682001"), ("Nagpur", "440001"),
    ("Indore", "452001"), ("Bhopal", "462001"), ("Chandigarh", "160017"),
]

_CLINICAL_ITEMS = [
    ("Type 2 Diabetes Mellitus", "Metformin 500 mg twice daily", "HbA1c 7.4%", "BP 124/80 mmHg"),
    ("Essential Hypertension", "Amlodipine 5 mg once daily", "Creatinine 1.0 mg/dL", "BP 138/86 mmHg"),
    ("Bronchial Asthma", "Salbutamol 100 mcg inhaler", "SpO2 97%", "Pulse 78 bpm"),
    ("Parkinson's disease", "Levodopa 100 mg thrice daily", "Temp 37.1 C", "RR 18 /min"),
    ("Addison's disease", "Hydrocortisone 20 mg morning", "Sodium 136 mEq/L", "Potassium 4.4 mEq/L"),
    ("Hypothyroidism", "Levothyroxine 50 mcg once daily", "TSH 3.8 mIU/L", "Hb 12.6 g/dL"),
    ("Community Acquired Pneumonia", "Azithromycin 500 mg OD", "WBC 11400 /uL", "Temp 38.4 C"),
    ("Chronic Kidney Disease", "Furosemide 40 mg OD", "eGFR 54 mL/min", "Urea 42 mg/dL"),
]


def _synth_phone(rng: random.Random) -> str:
    return f"{rng.choice(['9', '8', '7'])}{rng.randint(100000000, 999999999)}"


def _synth_aadhaar(rng: random.Random) -> str:
    return f"{rng.randint(2000, 9999)} {rng.randint(1000, 9999)} {rng.randint(1000, 9999)}"


def _synth_abha(rng: random.Random) -> str:
    return f"{rng.randint(10, 99)}-{rng.randint(1000, 9999)}-{rng.randint(1000, 9999)}-{rng.randint(1000, 9999)}"


def _synth_pan(rng: random.Random) -> str:
    letters = "ABCDEFGHJKLMNPQRSTUVWXYZ"
    return (
        "".join(rng.choice(letters) for _ in range(3))
        + "P"
        + rng.choice(letters)
        + f"{rng.randint(1000, 9999)}"
        + rng.choice(letters)
    )


def _synth_voter(rng: random.Random) -> str:
    letters = "ABCDEFGHJKLMNPQRSTUVWXYZ"
    return "".join(rng.choice(letters) for _ in range(3)) + f"{rng.randint(1000000, 9999999)}"


def _synth_dl(rng: random.Random) -> str:
    st = rng.choice(["MH12", "DL04", "KA01", "TN09", "UP32"])
    return f"{st} {rng.randint(2015, 2024)}{rng.randint(1000000, 9999999)}"


def _synth_mrn(rng: random.Random, idx: int) -> str:
    return rng.choice([
        f"IP-26-{idx:05d}",
        f"DHH-IPD-{idx:05d}",
        f"ADM{idx:06d}",
        f"UHID-{idx:06d}",
        f"SNJ-26-{idx:06d}",
    ])


def generate_large_split(
    out_dir: Path,
    split_name: str,
    seed: int,
    num_records: int = 600,
) -> Dict[str, Any]:
    """Generate `num_records` multi-format synthetic healthcare records + ground truth."""
    rng = random.Random(seed)
    split_dir = out_dir / split_name
    for sub in ("csv", "json", "jsonl", "fhir", "notes"):
        (split_dir / sub).mkdir(parents=True, exist_ok=True)

    pii_probes: List[Tuple[str, str, str]] = []  # (category, value, format)
    clinical_probes: List[str] = []

    # 1. Reordered CSVs with unseen column aliases (200 records across 4 files)
    csv_records_per_file = 50
    for f_idx in range(4):
        buf = io.StringIO()
        cols = [
            "clinical_diagnosis", "med_regimen", "lab_observation", "vital_sign",
            "beneficiary_full_name", "emergency_mobile", "voter_id_no", "mrn_code",
            "guardian_person", "visit_dt", "age_yrs", "hospital_unit",
        ]
        rng.shuffle(cols)
        writer = csv.DictWriter(buf, fieldnames=cols)
        writer.writeheader()
        for r_idx in range(csv_records_per_file):
            rec_num = f_idx * csv_records_per_file + r_idx
            fn_en, _ = rng.choice(_FIRST_NAMES)
            ln_en, _ = rng.choice(_LAST_NAMES)
            rel_fn, _ = rng.choice(_FIRST_NAMES)
            name = f"{fn_en} {ln_en}"
            rel_name = f"{rel_fn} {ln_en}"
            phone = _synth_phone(rng)
            voter = _synth_voter(rng)
            mrn = _synth_mrn(rng, rec_num + seed % 1000)
            diag, med, lab, vital = rng.choice(_CLINICAL_ITEMS)
            row = {
                "clinical_diagnosis": diag,
                "med_regimen": med,
                "lab_observation": lab,
                "vital_sign": vital,
                "beneficiary_full_name": name,
                "emergency_mobile": phone,
                "voter_id_no": voter,
                "mrn_code": mrn,
                "guardian_person": rel_name,
                "visit_dt": f"2026-{rng.randint(1,9):02d}-{rng.randint(10,28):02d}",
                "age_yrs": str(rng.randint(22, 82)),
                "hospital_unit": rng.choice(_HOSPITALS),
            }
            writer.writerow(row)
            pii_probes.extend([
                ("PATIENT_NAME", name, "csv"),
                ("PHONE", phone, "csv"),
                ("VOTER_ID", voter, "csv"),
                ("MRN", mrn, "csv"),
                ("RELATIVE_NAME", rel_name, "csv"),
            ])
            clinical_probes.extend([diag, med, lab, vital])
        (split_dir / "csv" / f"ward_roster_{f_idx:02d}.csv").write_text(buf.getvalue(), encoding="utf-8")

    # 2. Nested JSON with mixed English / Hindi / Romanised Hindi keys (150 records across 15 files)
    for f_idx in range(15):
        entries = []
        for r_idx in range(10):
            rec_num = 200 + f_idx * 10 + r_idx
            fn_en, fn_hi = rng.choice(_FIRST_NAMES)
            ln_en, ln_hi = rng.choice(_LAST_NAMES)
            use_hi = (r_idx % 2 == 1)
            name = f"{fn_hi} {ln_hi}" if use_hi else f"{fn_en} {ln_en}"
            phone = _synth_phone(rng)
            aadhaar = _synth_aadhaar(rng)
            city, pin = rng.choice(_CITIES)
            addr = f"{rng.randint(11, 290)} Sector {rng.randint(1, 24)}, {city} {pin}"
            diag, med, lab, vital = rng.choice(_CLINICAL_ITEMS)
            entries.append({
                "subject": {
                    "naam": name,
                    "contact_num": phone,
                    "aadhaar_id": aadhaar,
                    "pata": addr,
                },
                "clinical": {
                    "diagnosis": diag,
                    "rx": med,
                    "lab": lab,
                    "vitals": vital,
                    "attending": rng.choice(_DOCTORS),
                },
            })
            pii_probes.extend([
                ("PATIENT_NAME", name, "json"),
                ("PHONE", phone, "json"),
                ("AADHAAR", aadhaar, "json"),
                ("PIN", pin, "json"),
            ])
            clinical_probes.extend([diag, med, lab, vital])
        (split_dir / "json" / f"nested_ward_{f_idx:02d}.json").write_text(
            json.dumps({"facility": rng.choice(_HOSPITALS), "entries": entries}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # 3. JSONL referral / prescription stream (100 records across 5 files)
    for f_idx in range(5):
        lines = []
        for r_idx in range(20):
            fn_en, _ = rng.choice(_FIRST_NAMES)
            ln_en, _ = rng.choice(_LAST_NAMES)
            name = f"{fn_en} {ln_en}"
            abha = _synth_abha(rng)
            pan = _synth_pan(rng)
            diag, med, lab, vital = rng.choice(_CLINICAL_ITEMS)
            lines.append(json.dumps({
                "patient_full_name": name,
                "abha_no": abha,
                "pan_card": pan,
                "diagnosis": diag,
                "medication": med,
                "lab": lab,
            }))
            pii_probes.extend([
                ("PATIENT_NAME", name, "jsonl"),
                ("ABHA", abha, "jsonl"),
                ("PAN", pan, "jsonl"),
            ])
            clinical_probes.extend([diag, med, lab])
        (split_dir / "jsonl" / f"referrals_{f_idx:02d}.jsonl").write_text("\n".join(lines), encoding="utf-8")

    # 4. FHIR R4 Bundles (50 patient bundles across 10 files)
    for f_idx in range(10):
        bundle_entries = []
        for r_idx in range(5):
            fn_en, _ = rng.choice(_FIRST_NAMES)
            ln_en, _ = rng.choice(_LAST_NAMES)
            name = f"{fn_en} {ln_en}"
            phone = _synth_phone(rng)
            city, pin = rng.choice(_CITIES)
            diag, med, _, _ = rng.choice(_CLINICAL_ITEMS)
            pat_id = f"pat-{split_name}-{f_idx}-{r_idx}"
            bundle_entries.append({
                "resource": {
                    "resourceType": "Patient",
                    "id": pat_id,
                    "name": [{"text": name}],
                    "telecom": [{"system": "phone", "value": phone}],
                    "birthDate": f"{rng.randint(1955, 2000)}-{rng.randint(1,12):02d}-{rng.randint(10,28):02d}",
                    "address": [{"text": f"{rng.randint(1,99)} MG Road, {city}", "postalCode": pin}],
                }
            })
            bundle_entries.append({
                "resource": {
                    "resourceType": "Condition",
                    "id": f"cond-{f_idx}-{r_idx}",
                    "subject": {"reference": f"Patient/{pat_id}"},
                    "code": {"text": diag},
                }
            })
            bundle_entries.append({
                "resource": {
                    "resourceType": "MedicationRequest",
                    "id": f"med-{f_idx}-{r_idx}",
                    "subject": {"reference": f"Patient/{pat_id}"},
                    "medicationCodeableConcept": {"text": med},
                }
            })
            pii_probes.extend([
                ("PATIENT_NAME", name, "fhir"),
                ("PHONE", phone, "fhir"),
                ("PIN", pin, "fhir"),
            ])
            clinical_probes.extend([diag, med])
        (split_dir / "fhir" / f"fhir_bundle_{f_idx:02d}.json").write_text(
            json.dumps({"resourceType": "Bundle", "type": "collection", "entry": bundle_entries}, indent=2),
            encoding="utf-8",
        )

    # 5. Free-text Discharge Summaries, Prescriptions, Nursing Notes, Referrals (100 records across 100 files)
    for n_idx in range(100):
        fn_en, fn_hi = rng.choice(_FIRST_NAMES)
        ln_en, ln_hi = rng.choice(_LAST_NAMES)
        rel_fn, rel_hi = rng.choice(_FIRST_NAMES)
        phone = _synth_phone(rng)
        dl = _synth_dl(rng)
        diag, med, lab, vital = rng.choice(_CLINICAL_ITEMS)
        doc = rng.choice(_DOCTORS)
        hosp = rng.choice(_HOSPITALS)
        mode = n_idx % 4
        if mode == 0:  # Discharge summary (English)
            name = f"{fn_en} {ln_en}"
            rel = f"{rel_fn} {ln_en}"
            text = (
                f"DISCHARGE SUMMARY — {hosp}\n"
                f"Patient Name: {name}\n"
                f"S/O {rel}\n"
                f"Phone: {phone}\n"
                f"Driving Licence: {dl}\n"
                f"Attending: {doc}\n"
                f"Diagnosis: {diag}. Rx: {med}. Labs: {lab}. Vitals: {vital}.\n"
            )
        elif mode == 1:  # Hinglish nursing note
            name = f"{fn_en} {ln_en}"
            rel = f"{rel_fn} {ln_en}"
            text = (
                f"Nursing Note ({hosp})\n"
                f"Mareez ka naam: {name}\n"
                f"Pita ka naam: {rel}\n"
                f"Mobile number: {phone}\n"
                f"Attending {doc}.\n"
                f"Clinical: {diag}; {med}; {lab}; {vital}.\n"
            )
        elif mode == 2:  # Devanagari note
            name = f"{fn_hi} {ln_hi}"
            rel = f"{rel_hi} {ln_hi}"
            text = (
                f"रोगी का नाम: {name}\n"
                f"पति का नाम: {rel}\n"
                f"मोबाइल नंबर: {phone}\n"
                f"चिकित्सा: {diag}; {med}; {lab}; {vital}.\n"
            )
        else:  # Referral note with initials
            name = f"{fn_en[0]}. {ln_en}"
            rel = f"{rel_fn} {ln_en}"
            text = (
                f"REFERRAL NOTE to {hosp}\n"
                f"Patient: {name}, C/O {rel}, Contact: +91 {phone}.\n"
                f"Referred by {doc} for {diag}. Current regimen: {med}; {lab}.\n"
            )
        (split_dir / "notes" / f"clinical_doc_{n_idx:03d}.txt").write_text(text, encoding="utf-8")
        pii_probes.extend([
            ("PATIENT_NAME", name, "notes"),
            ("RELATIVE_NAME", rel, "notes"),
            ("PHONE", phone, "notes"),
        ])
        if mode == 0:
            pii_probes.append(("DRIVING_LICENCE", dl, "notes"))
        clinical_probes.extend([diag, med, lab, vital])

    return {
        "split": split_name,
        "records": num_records,
        "pii_probes": pii_probes,
        "clinical_probes": clinical_probes,
    }


def generate_adversarial_15(out_dir: Path) -> Dict[str, Any]:
    """Generate the 15-category adversarial PII test suite."""
    adv = out_dir / "adversarial_15"
    adv.mkdir(parents=True, exist_ok=True)
    cases: List[Dict[str, Any]] = []

    def add_case(cat: str, fname: str, content: str, pii: List[str], preserve: List[str] | None = None, expect_quarantine: bool = False):
        p = adv / fname
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        cases.append({
            "category": cat,
            "file": fname,
            "pii": pii,
            "preserve": preserve or [],
            "expect_quarantine": expect_quarantine,
        })

    # 1. Patient names without labels
    add_case("01_unlabeled_names", "cat01_unlabeled.txt",
             "Aarav Deshmukh presented with fever for 3 days. Paracetamol 650 mg given.",
             ["Aarav Deshmukh"], ["Paracetamol 650 mg"])

    # 2. Names embedded in long sentences
    add_case("02_long_sentence_names", "cat02_long.txt",
             "During the morning ward round at 08:30 AM, the resident noted that Meenakshi Sundaram complained of mild dyspnea after climbing two flights of stairs, though SpO2 remained 98%.",
             ["Meenakshi Sundaram"], ["SpO2 remained 98%"])

    # 3. Names beside medical terminology
    add_case("03_names_beside_med_terms", "cat03_med_adjacent.txt",
             "Patient: Kavita Nair; Diagnosis: Parkinson's disease and Addison's disease; Rx: Levodopa 100 mg.",
             ["Kavita Nair"], ["Parkinson's disease", "Addison's disease", "Levodopa 100 mg"])

    # 4. Doctor names resembling patient names (must preserve doctor, redact patient)
    add_case("04_doctor_vs_patient", "cat04_doctor.txt",
             "Patient Name: Ramesh Kulkarni\nSeen by Dr. Ramesh Sharma for Type 2 Diabetes.",
             ["Ramesh Kulkarni"], ["Dr. Ramesh Sharma", "Type 2 Diabetes"])

    # 5. Hospital names resembling personal names (must preserve hospital)
    add_case("05_hospital_personal_name", "cat05_hospital.txt",
             "Admitted to Ramaiah Memorial Hospital.\nPatient Name: Priya Nair\nBP 120/80 mmHg.",
             ["Priya Nair"], ["Ramaiah Memorial Hospital", "BP 120/80 mmHg"])

    # 6. Names with initials
    add_case("06_initials", "cat06_initials.txt",
             "Patient: S. P. Kulkarni\nFather: P. R. Kulkarni\nHbA1c 7.1%.",
             ["S. P. Kulkarni", "P. R. Kulkarni"], ["HbA1c 7.1%"])

    # 7. Names with inconsistent spacing
    add_case("07_inconsistent_spacing", "cat07_spacing.txt",
             "Patient Name:   Zoya   Siddiqui  \nMobile: 9823456712\nCreatinine 0.9 mg/dL.",
             ["Zoya   Siddiqui", "9823456712"], ["Creatinine 0.9 mg/dL"])

    # 8. Names written in different scripts
    add_case("08_mixed_scripts", "cat08_scripts.txt",
             "रोगी का नाम: कविता देशमुख\nPatient Name: Kavita Deshmukh\nBP 126/82 mmHg.",
             ["कविता देशमुख", "Kavita Deshmukh"], ["BP 126/82 mmHg"])

    # 9. Relative names without explicit labels
    add_case("09_unlabeled_relatives", "cat09_relatives.txt",
             "Patient: Farhan Siddiqui. Accompanied by brother Tariq Siddiqui who signed consent.",
             ["Farhan Siddiqui", "Tariq Siddiqui"], [])

    # 10. Identifiers embedded in narrative text
    add_case("10_narrative_ids", "cat10_narrative_ids.txt",
             "Caller reached 9811223344 and verified PAN ABCDE1234F, Voter ID MHX4829103, and ABHA 12-3456-7890-1234 before discharge.",
             ["9811223344", "ABCDE1234F", "MHX4829103", "12-3456-7890-1234"], [])

    # 11. PII in filenames (short-digit MRN + name + phone)
    add_case("11_pii_in_filename", "Discharge_Summary_Reena_Nishad_IP-26-00134_9823456712.txt",
             "Diagnosis: Bronchial Asthma. Salbutamol 100 mcg.",
             ["Reena", "Nishad", "IP-26-00134", "9823456712"], ["Bronchial Asthma", "Salbutamol 100 mcg"])

    # 12. PII in nested JSON keys and values
    add_case("12_nested_json_kv", "cat12_nested.json",
             json.dumps({"Rohan_Verma_9876543210": {"naam": "Rohan Verma", "bp": "120/80 mmHg"}}),
             ["Rohan Verma", "9876543210"], ["120/80 mmHg"])

    # 13. Unicode normalisation variants (fullwidth digits & NFD Devanagari)
    fw_phone = "".join(chr(0xFF10 + int(d)) for d in "9876543210")
    nfd_name = unicodedata.normalize("NFD", "कविता देशमुख")
    add_case("13_unicode_variants", "cat13_unicode.txt",
             f"रोगी का नाम: {nfd_name}\nPhone: {fw_phone}\nSpO2 98%.",
             [nfd_name, fw_phone, "9876543210"], ["SpO2 98%"])

    # 14. Malformed and truncated records
    add_case("14_malformed_truncated", "cat14_corrupt.json",
             '{"patient": "Leaked Name", "truncated": [1, 2',
             ["Leaked Name"], [], expect_quarantine=True)

    # 15. PII split across structured fields
    add_case("15_split_structured_fields", "cat15_split.csv",
             "first_name,last_name,std_code,phone_local,diagnosis\nAnanya,Chatterjee,022,24567890,Hypothyroidism\n",
             ["Ananya", "Chatterjee", "24567890"], ["Hypothyroidism"])

    return {"dir": adv, "cases": cases}
