#!/usr/bin/env python3
"""M24 Independent Unseen-Dataset & Adversarial Benchmark Generator + Evaluator.

Generates deterministic synthetic datasets (held_out & adversarial splits) using
unseen schemas, Indian name variations, Hindi/Hinglish/mixed-script notes, FHIR R4
with extensions, nested JSON, JSONL, and malformed quarantine files, then executes
starter/main.py offline and measures PII, Clinical, Identity, Privacy, and Performance.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
STARTER_MAIN = REPO_ROOT / "starter" / "main.py"
VALIDATE_OUT = REPO_ROOT / "validate_output.py"


def _build_unseen_corpus(base_dir: Path, seed_tag: str = "m24-v1") -> Dict[str, Any]:
    """Create held-out and adversarial synthetic datasets independent of dev/input."""
    held_dir = base_dir / "held_out"
    adv_dir = base_dir / "adversarial"
    (held_dir / "ward_csv").mkdir(parents=True, exist_ok=True)
    (held_dir / "nested").mkdir(parents=True, exist_ok=True)
    (held_dir / "fhir").mkdir(parents=True, exist_ok=True)
    (held_dir / "notes").mkdir(parents=True, exist_ok=True)
    (adv_dir / "mixed").mkdir(parents=True, exist_ok=True)

    # 1. Held-out CSV with unseen column aliases & reordered columns
    (held_dir / "ward_csv" / "ward_intake_alpha.csv").write_text(
        "clinical_diagnosis,med_regimen,beneficiary_full_name,emergency_mobile,voter_id_no,age_yrs,visit_dt,hospital_unit\n"
        "Type 2 Diabetes,Metformin 500 mg twice daily,Kavita Deshmukh,9823456712,MHX4829103,49,2026-03-14,Metro Ward\n"
        "Hypertension,Amlodipine 5 mg once daily,S. P. Kulkarni,9811223344,DLQ9912345,56,2026-03-15,Metro Ward\n",
        encoding="utf-8",
    )

    # 2. Held-out Nested JSON (same patient Kavita Deshmukh in Hindi/Devanagari + phone match)
    (held_dir / "nested" / "lab_follow_up.json").write_text(
        json.dumps(
            {
                "facility": "Apex Diagnostics",
                "entries": [
                    {
                        "subject": {
                            "naam": "कविता देशमुख",
                            "contact_num": "+91 9823456712",
                            "pata": "14 MG Road, Pune",
                        },
                        "clinical": {
                            "lab_panel": "HbA1c 7.4%, Creatinine 1.0 mg/dL, BP 124/80 mmHg",
                            "attending": "Dr. Arvind Joshi",
                        },
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # 3. Held-out FHIR R4 Bundle with extensions
    (held_dir / "fhir" / "discharge_bundle.json").write_text(
        json.dumps(
            {
                "resourceType": "Bundle",
                "type": "collection",
                "entry": [
                    {
                        "resource": {
                            "resourceType": "Patient",
                            "id": "pat-unseen-1",
                            "name": [{"text": "Nikhil Subramanian"}],
                            "telecom": [{"system": "phone", "value": "9765432109"}],
                            "birthDate": "1978-08-22",
                            "address": [{"text": "22 Anna Salai, Chennai", "postalCode": "600002"}],
                        }
                    },
                    {
                        "resource": {
                            "resourceType": "Condition",
                            "id": "cond-1",
                            "subject": {"reference": "Patient/pat-unseen-1"},
                            "code": {"text": "Bronchial Asthma"},
                        }
                    },
                    {
                        "resource": {
                            "resourceType": "MedicationRequest",
                            "id": "med-1",
                            "subject": {"reference": "Patient/pat-unseen-1"},
                            "medicationCodeableConcept": {"text": "Salbutamol 100 mcg inhaler"},
                        }
                    },
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    # 4. Held-out Clinical Note (Hinglish + Hindi + Clinical Eponyms + Canary)
    (held_dir / "notes" / "nursing_note_01.txt").write_text(
        "Mareez ka naam: Farhan Siddiqui\n"
        "Pita ka naam: Tariq Siddiqui\n"
        "Ghar ka pata: 45 Hazratganj, Lucknow 226001\n"
        "Mobile number: 9415012345\n"
        "Voter ID: UPK7712390\n"
        "Driving Licence: UP32 20190045123\n"
        "Passport: K4829104\n"
        "Seen by Dr. Ramesh Kumar. ASHA worker coordinated follow-up.\n"
        "Clinical: Parkinson's disease; Paracetamol 650 mg twice daily; Temp 38.2 C; BP 120/80 mmHg.\n",
        encoding="utf-8",
    )

    # 5. Adversarial Corpus: Homonyms, Hindi labels, Malformed JSON (must quarantine)
    (adv_dir / "mixed" / "homonym_and_hindi.txt").write_text(
        "रोगी का नाम: श्रीमती Sunita Devi\n"
        "पति का नाम: श्री Rajesh Sharma\n"
        "मोबाइल नंबर: 9988776655\n"
        "पता: 88 Civil Lines, Jaipur\n"
        "Passport: K4829104\n"
        "Diagnosis: Addison's disease; HbA1c 6.9%; Creatinine 1.1 mg/dL.\n",
        encoding="utf-8",
    )
    (adv_dir / "mixed" / "corrupt_payload.json").write_text("{broken json: [1, 2", encoding="utf-8")

    # Ground-truth probes (never shared with engine)
    pii_probes = [
        ("PATIENT_NAME", "Kavita Deshmukh"),
        ("PATIENT_NAME", "S. P. Kulkarni"),
        ("PATIENT_NAME", "कविता देशमुख"),
        ("PATIENT_NAME", "Nikhil Subramanian"),
        ("PATIENT_NAME", "Farhan Siddiqui"),
        ("RELATIVE_NAME", "Tariq Siddiqui"),
        ("PATIENT_NAME", "Sunita Devi"),
        ("RELATIVE_NAME", "Rajesh Sharma"),
        ("PHONE", "9823456712"),
        ("PHONE", "9811223344"),
        ("PHONE", "9765432109"),
        ("PHONE", "9415012345"),
        ("PHONE", "9988776655"),
        ("VOTER_ID", "MHX4829103"),
        ("VOTER_ID", "DLQ9912345"),
        ("VOTER_ID", "UPK7712390"),
        ("DRIVING_LICENCE", "UP32 20190045123"),
        ("PASSPORT", "K4829104"),
    ]
    clinical_probes = [
        "Metformin 500 mg twice daily",
        "Amlodipine 5 mg once daily",
        "HbA1c 7.4%",
        "Creatinine 1.0 mg/dL",
        "BP 124/80 mmHg",
        "Bronchial Asthma",
        "Salbutamol 100 mcg inhaler",
        "Parkinson's disease",
        "Paracetamol 650 mg twice daily",
        "Temp 38.2 C",
        "BP 120/80 mmHg",
        "ASHA worker",
        "Dr. Ramesh Kumar",
        "Dr. Arvind Joshi",
        "Addison's disease",
        "HbA1c 6.9%",
        "Creatinine 1.1 mg/dL",
    ]
    return {"held_dir": held_dir, "adv_dir": adv_dir, "pii_probes": pii_probes, "clinical_probes": clinical_probes}


def run_benchmark() -> Dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        corpus = _build_unseen_corpus(tmp_path)

        # Combine into one input dir for unified run
        in_dir = tmp_path / "input"
        out_dir = tmp_path / "output"
        for src in (corpus["held_dir"], corpus["adv_dir"]):
            for p in src.rglob("*"):
                if p.is_file():
                    rel = p.relative_to(tmp_path)
                    dest = in_dir / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(p.read_bytes())

        env = os.environ.copy()
        env["RAKSHA_SECRET"] = "m24-unseen-benchmark-secret"
        env["HF_HUB_OFFLINE"] = "1"
        env["TRANSFORMERS_OFFLINE"] = "1"

        t0 = time.perf_counter()
        res = subprocess.run(
            [sys.executable, str(STARTER_MAIN), "--input", str(in_dir), "--output", str(out_dir)],
            capture_output=True,
            text=True,
            env=env,
        )
        runtime_s = time.perf_counter() - t0
        if res.returncode != 0:
            raise RuntimeError(f"Engine failed: {res.stderr}")

        val = subprocess.run(
            [sys.executable, str(VALIDATE_OUT), "--input", str(in_dir), "--output", str(out_dir)],
            capture_output=True,
            text=True,
        )

        # Collect all sanitized output text
        san_texts: List[str] = []
        for p in (out_dir / "sanitized").rglob("*"):
            if p.is_file():
                san_texts.append(p.read_text(encoding="utf-8", errors="ignore"))
        all_san = "\n".join(san_texts)

        leaked_pii: List[Tuple[str, str]] = []
        for cat, probe in corpus["pii_probes"]:
            if probe in all_san:
                leaked_pii.append((cat, probe))

        preserved_clin = 0
        missing_clin: List[str] = []
        for cprobe in corpus["clinical_probes"]:
            if cprobe in all_san:
                preserved_clin += 1
            else:
                missing_clin.append(cprobe)

        report_json = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
        records_lines = [
            json.loads(line)
            for line in (out_dir / "records.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

        # Check cross-language linking of Kavita Deshmukh (ward_intake_alpha.csv row 0 vs lab_follow_up.json)
        kavita_pids = [
            r.get("patient")
            for r in records_lines
            if "ward_intake_alpha" in r.get("file", "") and r.get("loc") == "row:0"
        ] + [
            r.get("patient")
            for r in records_lines
            if "lab_follow_up" in r.get("file", "")
        ]
        cross_lang_linked = len(kavita_pids) == 2 and kavita_pids[0] is not None and kavita_pids[0] == kavita_pids[1]

        pii_total = len(corpus["pii_probes"])
        pii_tp = pii_total - len(leaked_pii)
        clin_total = len(corpus["clinical_probes"])
        fp_clin = len(missing_clin)
        pii_prec = round(pii_tp / (pii_tp + fp_clin), 4) if (pii_tp + fp_clin) > 0 else 1.0
        pii_rec = round(pii_tp / pii_total, 4)
        pii_f1 = round((2 * pii_prec * pii_rec) / (pii_prec + pii_rec), 4) if (pii_prec + pii_rec) > 0 else 0.0

        return {
            "contract_ok": "CONTRACT OK" in val.stdout,
            "runtime_secs": round(runtime_s, 3),
            "files_total": report_json["counts"]["files_total"],
            "files_sanitized": report_json["counts"]["files_sanitized"],
            "files_quarantined": report_json["counts"]["files_quarantined"],
            "pii_total": pii_total,
            "pii_detected_and_removed": pii_tp,
            "pii_leaked_count": len(leaked_pii),
            "pii_leaked": leaked_pii,
            "pii_precision": pii_prec,
            "pii_recall": pii_rec,
            "pii_f1": pii_f1,
            "clinical_expected": clin_total,
            "clinical_preserved": preserved_clin,
            "clinical_missing": missing_clin,
            "clinical_fidelity_pct": round((preserved_clin / clin_total) * 100.0, 2),
            "cross_language_kavita_linked": cross_lang_linked,
            "kavita_pids": kavita_pids,
        }


if __name__ == "__main__":
    print(json.dumps(run_benchmark(), indent=2, ensure_ascii=False))
