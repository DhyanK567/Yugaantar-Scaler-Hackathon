"""M15.3 & M15.7 — Independent Seeded Multi-Hospital & Multilingual Benchmark."""
from __future__ import annotations

import base64
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STARTER = ROOT / "starter"
SEED = 20261126


def _run_cli(inp: Path, out: Path, secret: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ, RAKSHA_SECRET=secret, HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    return subprocess.run(
        [sys.executable, str(STARTER / "main.py"), "--input", str(inp), "--output", str(out)],
        capture_output=True, text=True, env=env, timeout=120,
    )


class TestIndependentBenchmark(unittest.TestCase):
    def test_multi_hospital_multilingual_independent_benchmark(self) -> None:
        rng = random.Random(SEED)
        work = Path(tempfile.mkdtemp(prefix="m15_bench_"))
        try:
            inp, out = work / "inp", work / "out"
            (inp / "hospital_a").mkdir(parents=True)
            (inp / "hospital_b").mkdir(parents=True)
            (inp / "hospital_c").mkdir(parents=True)
            (inp / "lab_d").mkdir(parents=True)

            # Unseen synthetic patients across 4 institutions + multilingual variants
            # PT1: Harishchandra Kulkarni (appears in Hospital A CSV, Hospital B FHIR, Lab D JSON)
            # PT2: Prabhavati Deshmukh (appears in Hospital A CSV, Hospital C Hindi note)
            # PT3: Devanand Tiwari (same name, DIFFERENT person from PT4 Devanand Tiwari!)
            # PT4: Devanand Tiwari (different age/gender/phone -> must NOT merge with PT3)
            (inp / "hospital_a" / "reg.csv").write_text(
                "UHID,Patient Name,Gender,Age,DOB,Village,District,PIN,Mobile,Diagnosis,BP,Medication\n"
                "HA-9001,Harishchandra Kulkarni,M,58,1968-04-11,Wai,Satara,412803,9822001100,Graves' disease,112/74,Methimazole 10 mg\n"
                "HA-9002,Prabhavati Deshmukh,F,64,1962-09-22,Karad,Satara,415110,9822002200,Myocardial infarction,134/86,Aspirin 75 mg\n"
                "HA-9003,Devanand Tiwari,M,31,1995-01-10,Phulpur,Prayagraj,211002,9839003300,Typhoid,118/76,Azithromycin 500 mg\n"
                "HA-9004,Devanand Tiwari,M,67,1959-06-05,Soraon,Prayagraj,212502,9839004400,Hypertension,146/92,Amlodipine 5 mg\n",
                encoding="utf-8",
            )

            # Hospital B: FHIR R4 Bundle for PT1
            (inp / "hospital_b" / "fhir_pt1.json").write_text(json.dumps({
                "resourceType": "Bundle",
                "type": "collection",
                "entry": [
                    {"fullUrl": "urn:uuid:p1", "resource": {
                        "resourceType": "Patient", "id": "p1",
                        "name": [{"text": "Harishchandra Kulkarni"}],
                        "gender": "male", "birthDate": "1968-04-11",
                        "telecom": [{"system": "phone", "value": "9822001100"}],
                    }},
                    {"fullUrl": "urn:uuid:orgB", "resource": {
                        "resourceType": "Organization", "id": "orgB", "name": "Sahyadri Specialty Hospital",
                    }},
                    {"fullUrl": "urn:uuid:cond1", "resource": {
                        "resourceType": "Condition", "id": "cond1",
                        "subject": {"reference": "urn:uuid:p1"},
                        "code": {"text": "Graves' disease"},
                    }},
                    {"fullUrl": "urn:uuid:obs1", "resource": {
                        "resourceType": "Observation", "id": "obs1", "status": "final",
                        "subject": {"reference": "urn:uuid:p1"},
                        "code": {"text": "TSH"},
                        "valueQuantity": {"value": 4.8, "unit": "mIU/L"},
                    }},
                ],
            }), encoding="utf-8")

            # Hospital C: Hindi / Devanagari nursing note for PT2
            (inp / "hospital_c" / "note_pt2.txt").write_text(
                "मरीज: प्रभावती देशमुख, आयु: 64 वर्ष\n"
                "मोबाइल: 9822002200\n"
                "प्रभावती जी को रात में सीने में दर्द था। BP 134/86 mmHg. Aspirin 75 mg दिया गया।\n",
                encoding="utf-8",
            )

            # Lab D: Nested JSON with base64 report for PT1
            b64 = base64.b64encode(b"Patient: Harishchandra Kulkarni, Phone 9822001100. TSH 4.8 mIU/L.").decode("ascii")
            (inp / "lab_d" / "lab_pt1.json").write_text(json.dumps({
                "lab_name": "Metro Diagnostics D",
                "patient": {"name": "Harishchandra Kulkarni", "phone": "9822001100", "uhid": "HA-9001"},
                "panels": [{"test": "Levothyroxine check", "value": 50, "unit": "mcg"}],
                "attachment_b64": b64,
            }), encoding="utf-8")

            # Malformed input
            (inp / "lab_d" / "broken.bin").write_bytes(b"\x00\xff\xfe\x81")

            res = _run_cli(inp, out, f"bench-secret-{rng.randint(1000, 9999)}")
            self.assertEqual(res.returncode, 0, res.stderr)

            # Verify contract
            v = subprocess.run(
                [sys.executable, str(ROOT / "validate_output.py"), "--input", str(inp), "--output", str(out)],
                capture_output=True, text=True, timeout=60,
            )
            self.assertIn("CONTRACT OK", v.stdout)

            # Verify zero direct PII leaks across all exported files + report.json
            all_out_text = (out / "report.json").read_text(encoding="utf-8")
            for p in (out / "sanitized").rglob("*"):
                if p.is_file():
                    all_out_text += "\n" + p.read_text(encoding="utf-8")
            for pii in ("Harishchandra Kulkarni", "Prabhavati Deshmukh", "प्रभावती देशमुख", "Devanand Tiwari", "9822001100", "9822002200", "9839003300", "9839004400"):
                self.assertNotIn(pii, all_out_text)

            # Verify clinical values preserved
            for clin in ("Graves' disease", "Myocardial infarction", "Methimazole 10 mg", "Aspirin 75 mg", "Azithromycin 500 mg", "Amlodipine 5 mg", "Sahyadri Specialty Hospital", "4.8"):
                self.assertIn(clin, all_out_text)

            # Verify identity resolution: PT1 linked across A, B, D; PT3 != PT4 (no false merge!)
            recs = [json.loads(l) for l in (out / "records.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
            by_loc = {(r["file"].replace("sanitized/", "", 1), r["loc"]): r["patient"] for r in recs}
            pt1_ids = {
                by_loc.get(("hospital_a/reg.csv", "row:0")),
                by_loc.get(("hospital_b/fhir_pt1.json", "doc")),
                by_loc.get(("lab_d/lab_pt1.json", "doc")),
            }
            self.assertEqual(len(pt1_ids), 1)
            self.assertIsNotNone(next(iter(pt1_ids)))
            pt3_id = by_loc.get(("hospital_a/reg.csv", "row:2"))
            pt4_id = by_loc.get(("hospital_a/reg.csv", "row:3"))
            self.assertIsNotNone(pt3_id)
            self.assertIsNotNone(pt4_id)
            self.assertNotEqual(pt3_id, pt4_id)
        finally:
            shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
