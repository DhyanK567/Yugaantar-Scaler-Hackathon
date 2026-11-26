#!/usr/bin/env python3
"""
Phase 7 — Independent Held-Out Synthetic Evaluation Benchmark.
Fresh synthetic multi-hospital cohort (Hospital A, Hospital B, Hospital C) not used for tuning.
Includes English, Hindi, Hinglish, CSV, JSON, JSONL, FHIR R4, clinical notes, prescriptions,
malformed inputs, rare diagnosis combinations, multilingual names, relatives, fragmented IDs,
and planted canaries.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
STARTER_DIR = REPO_ROOT / "starter"
sys.path.insert(0, str(STARTER_DIR))

from raksha_engine.clinical_validator import analyze_clinical_drift

CANARY_TOKENS = [
    "Rajeshwari Devi",
    "9123456789",
]

RAW_PII_PROBES = [
    "Neha Kulkarni",
    "Prakash Kulkarni",
    "9820112233",
    "7711223344",
    "4123 8899 0012",
    "अरविंद मिश्रा",
    "कमला मिश्रा",
    "9935112200",
    "Ritu Saxena",
    "14-9988-7766-5544",
]


def build_heldout_corpus(inp_dir: Path) -> list[str]:
    inp_dir.mkdir(parents=True, exist_ok=True)
    texts = []

    # 1. Hospital A CSV (rare diagnosis + English)
    csv_txt = (
        "patient_name,age,gender,district,pin,aadhaar,diagnosis,medication,dosage\n"
        "Neha Kulkarni,34,F,Pune,411001,4123 8899 0012,Guillain-Barre syndrome,IVIG,400 mg\n"
        "Suresh Patil,36,M,Pune,411001,5123 8899 0013,Dengue fever,Paracetamol,500 mg\n"
        "Anita Joshi,33,F,Pune,411001,6123 8899 0014,Typhoid,Azithromycin,500 mg\n"
        "Rohan Deshmukh,35,M,Pune,411001,7123 8899 0015,Asthma,Salbutamol,100 mcg\n"
        "Kiran Kale,37,F,Pune,411001,8123 8899 0016,Diabetes,Metformin,500 mg\n"
    )
    (inp_dir / "hosp_a_opd.csv").write_text(csv_txt, encoding="utf-8")
    texts.append(csv_txt)

    # 2. Hospital B Hindi Clinical Note + Canary + Relative
    hindi_txt = (
        "मरीज: अरविंद मिश्रा, पिता: कमला मिश्रा, मोबाइल: 9935112200।\n"
        "नाम: Rajeshwari Devi\n"
        "Diagnosis: Diabetes mellitus. BP 130/84 mmHg, Hb 12.8 g/dL, Tab Metformin 500 mg BD for 30 days.\n"
    )
    (inp_dir / "hosp_b_note.txt").write_text(hindi_txt, encoding="utf-8")
    texts.append(hindi_txt)

    # 3. Hospital C Hinglish Prescription + Relative + Phone
    hg_txt = (
        "Mareez: Neha Kulkarni, pita ka naam Prakash Kulkarni, phone: 9820112233.\n"
        "Tab Dolo 650 mg PO TDS for 5 days. Temp 100.8 F, SpO2 97 %.\n"
    )
    (inp_dir / "hosp_c_rx.txt").write_text(hg_txt, encoding="utf-8")
    texts.append(hg_txt)

    # 4. FHIR R4 Bundle with Canary
    fhir = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {
                "fullUrl": "urn:uuid:pt-eval-1",
                "resource": {
                    "resourceType": "Patient",
                    "id": "pt-eval-1",
                    "name": [{"text": "Ritu Saxena"}],
                    "identifier": [{"system": "https://healthid.ndhm.gov.in", "value": "14-9988-7766-5544"}],
                    "telecom": [{"system": "phone", "value": "7711223344"}],
                    "gender": "female",
                    "birthDate": "1990-03-22",
                    "address": [{"district": "Lucknow", "postalCode": "226001"}],
                },
            },
            {
                "fullUrl": "urn:uuid:obs-eval-1",
                "resource": {
                    "resourceType": "Observation",
                    "id": "obs-eval-1",
                    "status": "final",
                    "code": {"text": "Hemoglobin"},
                    "note": [{"text": "Contact: 9123456789"}],
                    "subject": {"reference": "urn:uuid:pt-eval-1"},
                },
            },
        ],
    }
    fhir_str = json.dumps(fhir, indent=2)
    (inp_dir / "hosp_b_fhir.json").write_text(fhir_str, encoding="utf-8")
    texts.append(fhir_str)

    # 5. Malformed JSON (must be quarantined, never copied raw)
    (inp_dir / "malformed_lab.json").write_text("{broken: json", encoding="utf-8")

    return texts


def run_eval() -> dict:
    tmp = Path(tempfile.mkdtemp(prefix="m15_5_ind_eval_"))
    try:
        inp = tmp / "input"
        out = tmp / "output"
        in_texts = build_heldout_corpus(inp)

        t0 = time.perf_counter()
        env = dict(os.environ, RAKSHA_SECRET="ind_eval_secret_2026")
        res = subprocess.run(
            [sys.executable, str(STARTER_DIR / "main.py"), "--input", str(inp), "--output", str(out)],
            cwd=str(STARTER_DIR),
            env=env,
            capture_output=True,
            text=True,
        )
        runtime = time.perf_counter() - t0
        if res.returncode != 0:
            raise RuntimeError(f"Engine failed: {res.stderr}")

        report = json.loads((out / "report.json").read_text(encoding="utf-8"))
        san_dir = out / "sanitized"
        san_texts = []
        fhir_bundles = []
        for p in sorted(san_dir.rglob("*")):
            if p.is_file():
                t = p.read_text(encoding="utf-8", errors="ignore")
                san_texts.append(t)
                if p.suffix.lower() == ".json":
                    try:
                        obj = json.loads(t)
                        if isinstance(obj, dict) and obj.get("resourceType") == "Bundle":
                            fhir_bundles.append(obj)
                    except Exception:
                        pass

        all_out_text = "\n".join(san_texts) + "\n" + (out / "records.jsonl").read_text(encoding="utf-8")
        pii_leaked = [p for p in RAW_PII_PROBES if p.lower() in all_out_text.lower()]
        canaries_leaked = [c for c in CANARY_TOKENS if c in all_out_text]

        clinical = analyze_clinical_drift(in_texts, san_texts, fhir_bundles=fhir_bundles)
        pi = report.get("privacy_intelligence", {})
        atk = pi.get("attack_simulation", {})
        counts = report.get("counts", {})

        summary = {
            "privacy": {
                "direct_pii_probes_tested": len(RAW_PII_PROBES),
                "direct_pii_leaked": len(pii_leaked),
                "leaked_probes": pii_leaked,
                "canaries_planted": len(CANARY_TOKENS),
                "canaries_leaked": len(canaries_leaked),
                "pre_uniquely_distinguishable": atk.get("pre_uniquely_distinguishable"),
                "post_uniquely_distinguishable": atk.get("post_uniquely_distinguishable"),
            },
            "clinical": clinical["overall"],
            "clinical_passed": clinical["passed"],
            "operations": {
                "files_total": counts.get("files_total"),
                "files_sanitized": counts.get("files_sanitized"),
                "files_quarantined": counts.get("files_quarantined"),
                "records_processed": counts.get("records_processed"),
                "records_linked": counts.get("records_linked"),
                "runtime_secs": round(runtime, 3),
                "peak_rss_mb": report.get("resources", {}).get("peak_rss_mb"),
                "release_decision": pi.get("release_gate", {}).get("status"),
            },
        }
        print(json.dumps(summary, indent=2))
        return summary
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    s = run_eval()
    ok = (
        s["privacy"]["direct_pii_leaked"] == 0
        and s["privacy"]["canaries_leaked"] == 0
        and s["clinical_passed"]
        and s["operations"]["files_quarantined"] == 1
    )
    sys.exit(0 if ok else 1)
