#!/usr/bin/env python3
"""M26 Regression Suite: Independent Held-Out Identity & Comprehensive Filename Privacy."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
STARTER_MAIN = REPO_ROOT / "starter" / "main.py"
VALIDATE_OUT = REPO_ROOT / "validate_output.py"
sys.path.insert(0, str(REPO_ROOT / "starter"))

from raksha_engine.names import CorpusNameIndex
from raksha_engine.sanitizer import sanitize_filename


class M26HardeningTests(unittest.TestCase):
    def test_01_held_out_identity_continuity_zero_false_merges(self) -> None:
        """Independent held-out identity dataset testing initials, cross-script, hospital-scoped MRNs, and homonyms."""
        docs = {
            # T1: Initials vs expanded with exact DOB
            "t1_a.json": ({"patient_name": "Suresh Kumar Iyer", "dob": "1979-05-14", "mrn": "HOSP1-101"}, "T1"),
            "t1_b.json": ({"patient_name": "S. K. Iyer", "dob": "1979-05-14", "mrn": "HOSP2-889"}, "T1"),
            # T2: Homonym of Suresh Kumar Iyer with different DOB (MUST NOT merge)
            "t2_homonym.json": ({"patient_name": "Suresh Kumar Iyer", "dob": "1991-12-01", "mrn": "HOSP1-999"}, "T2"),
            # T3: Cross-language Devanagari <-> Latin + shared phone
            "t3_en.json": ({"patient_name": "Aarav Sharma", "phone": "9822001122", "dob": "1988-03-22"}, "T3"),
            "t3_hi.json": ({"naam": "आरव शर्मा", "contact_num": "+91 9822001122"}, "T3"),
            # T4 vs T5: Same unprefixed MRN '00123' at DIFFERENT hospitals (MUST NOT merge)
            "arogya_t4.json": ({"patient_name": "Meera Nair", "mrn": "00123", "dob": "1975-02-10"}, "T4"),
            "sanjeevani_t5.json": ({"patient_name": "Meera Nair", "mrn": "00123", "dob": "1990-08-19"}, "T5"),
        }
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            in_dir = tmp_path / "in"
            out_dir = tmp_path / "out"
            in_dir.mkdir(parents=True, exist_ok=True)
            sha_true = {}
            for fname, (obj, tid) in docs.items():
                raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
                (in_dir / fname).write_bytes(raw)
                sha_true[hashlib.sha256(raw).hexdigest()] = tid

            env = os.environ.copy()
            env["RAKSHA_SECRET"] = "m26-id-heldout"
            res = subprocess.run([sys.executable, str(STARTER_MAIN), "--input", str(in_dir), "--output", str(out_dir)], env=env, check=True, capture_output=True)
            report = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
            recs = [json.loads(l) for l in (out_dir / "records.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]

            out_to_true = {e["output"]: sha_true.get(e["input_sha256"]) for e in report["files"] if e.get("output")}
            units = [(out_to_true[r["file"]], r.get("patient")) for r in recs if r["file"] in out_to_true]

            tp = fp = fn = 0
            for i in range(len(units)):
                for j in range(i + 1, len(units)):
                    st = units[i][0] == units[j][0]
                    sp = (units[i][1] is not None) and (units[i][1] == units[j][1])
                    if st and sp:
                        tp += 1
                    elif not st and sp:
                        fp += 1
                    elif st and not sp:
                        fn += 1
            self.assertEqual(fp, 0, f"False merges detected: {units}")
            self.assertEqual(fn, 0, f"Missed links detected: {units}")
            self.assertEqual(tp, 2)

    def test_02_comprehensive_filename_privacy(self) -> None:
        """Test names, MRNs, phones, Indian IDs, nested folders, Unicode, fullwidth digits, duplicates, mixed separators, multi-extensions."""
        idx = CorpusNameIndex()
        idx.add_name("Rohan Verma")
        fw_phone = "".join(chr(0xFF10 + int(d)) for d in "9876543210")
        cases = [
            ("Rohan_Verma/Ward__A/Discharge--Summary_Rohan_Verma_IP-26-00134.tar.txt", ["rohan", "verma", "ip-26-00134"]),
            (f"nested/{fw_phone}_lab_report.json", [fw_phone, "9876543210"]),
            ("nested/कविता_देशमुख_ABCDE1234F.txt", ["कविता", "देशमुख", "abcde1234f"]),
            ("dup_a/dhhardoi_ds_DHH-IPD-00591.txt", ["dhh-ipd-00591"]),
            ("dup_b/dhhardoi_ds_DHH-IPD-00591.txt", ["dhh-ipd-00591"]),
        ]
        outputs = []
        for path, forbidden in cases:
            out = sanitize_filename(path, idx, hashlib.sha256(path.encode("utf-8")).hexdigest(), secret=b"m26-fn-sec")
            outputs.append(out)
            low = out.casefold()
            for tok in forbidden:
                self.assertNotIn(tok, low, f"Token {tok} leaked in {out}")
        self.assertEqual(len(outputs), len(set(outputs)), "Duplicate filenames across dirs collided")


if __name__ == "__main__":
    unittest.main()
