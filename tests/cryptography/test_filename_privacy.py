"""Regression tests for M16.1 Zero PII Filename Leakage."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
STARTER_DIR = REPO_ROOT / "starter"
for p in (str(REPO_ROOT), str(STARTER_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from raksha_engine.crypto import (  # noqa: E402
    HKDF_DOMAIN_FILENAME,
    HKDF_DOMAIN_PSEUDONYM,
    pseudonymous_filename_token,
)
from raksha_engine.names import CorpusNameIndex  # noqa: E402
from raksha_engine.sanitizer import sanitize_filename  # noqa: E402
from backend.pipeline import _build_safe_quarantine_records  # noqa: E402


class TestFilenamePrivacyM161(unittest.TestCase):
    def setUp(self) -> None:
        self.secret_a = b"alpha-hospital-secret-key-2026"
        self.secret_b = b"beta-hospital-secret-key-2026"
        self.name_index = CorpusNameIndex()
        self.name_index.add_name("Reena Nishad")
        self.name_index.add_name("Ramesh Verma")
        self.name_index.add_name("Sita Devi")

    def test_audit_example_and_mrn_phone_redacted(self) -> None:
        cases = [
            "Discharge_Summary_Reena_Nishad_JJH-0076928.txt",
            "Lab_Report_MRN-9988776_9876543210.csv",
            "OPD_Ramesh_Verma_9123456789.json",
            "रमेश_कुमार_9876543210.txt",
            "Hinglish_Chacha_Sita_Devi_Note.txt",
            "Patient Name (Reena, Nishad) - Summary!.txt",
        ]
        for idx, rel in enumerate(cases):
            out = sanitize_filename(rel, self.name_index, f"{idx:064x}", secret=self.secret_a)
            low = out.lower()
            self.assertNotIn("reena", low)
            self.assertNotIn("nishad", low)
            self.assertNotIn("ramesh", low)
            self.assertNotIn("verma", low)
            self.assertNotIn("sita", low)
            self.assertNotIn("devi", low)
            self.assertNotIn("0076928", low)
            self.assertNotIn("9988776", low)
            self.assertNotIn("9876543210", low)
            self.assertNotIn("9123456789", low)
            self.assertNotIn("रमेश", out)
            self.assertTrue(out.endswith(Path(rel).suffix.lower()))

    def test_determinism_and_secret_separation(self) -> None:
        rel = "Discharge_Summary_Reena_Nishad_JJH-0076928.txt"
        sha = "a" * 64
        out_a1 = sanitize_filename(rel, self.name_index, sha, secret=self.secret_a)
        out_a2 = sanitize_filename(rel, self.name_index, sha, secret=self.secret_a)
        out_b = sanitize_filename(rel, self.name_index, sha, secret=self.secret_b)
        self.assertEqual(out_a1, out_a2)
        self.assertNotEqual(out_a1, out_b)
        self.assertNotEqual(HKDF_DOMAIN_FILENAME, HKDF_DOMAIN_PSEUDONYM)

    def test_duplicate_filenames_and_path_traversal(self) -> None:
        t1 = pseudonymous_filename_token("dept_a/Reena_Nishad.txt", "1" * 64, self.secret_a)
        t2 = pseudonymous_filename_token("dept_b/Reena_Nishad.txt", "2" * 64, self.secret_a)
        self.assertNotEqual(t1, t2)

        trav = sanitize_filename("../../etc/Reena_Nishad_0076928.txt", self.name_index, "3" * 64, secret=self.secret_a)
        self.assertNotIn("..", trav)
        self.assertFalse(trav.startswith("/"))
        self.assertNotIn("reena", trav.lower())

    def test_quarantine_and_engine_e2e_no_filename_leak(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inp = Path(tmp) / "in"
            out = Path(tmp) / "out"
            inp.mkdir()
            (inp / "Discharge_Summary_Reena_Nishad_JJH-0076928.txt").write_text(
                "Patient: Reena Nishad\nMRN: JJH-0076928\nBP: 120/80 mmHg\nMetformin 500mg\n",
                encoding="utf-8",
            )
            (inp / "bad_Reena_Nishad_9876543210.bin").write_bytes(b"\x00\xff\xfe\xfd")

            proc = subprocess.run(
                [sys.executable, str(STARTER_DIR / "main.py"), "--input", str(inp), "--output", str(out)],
                env={"PATH": "", "SYSTEMROOT": r"C:\Windows", "RAKSHA_SECRET": self.secret_a.decode()},
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertNotIn("Reena", proc.stdout + proc.stderr)
            self.assertNotIn("0076928", proc.stdout + proc.stderr)

            report = json.loads((out / "report.json").read_text(encoding="utf-8"))
            report_text = json.dumps(report)
            self.assertNotIn("Reena", report_text)
            self.assertNotIn("0076928", report_text)
            self.assertNotIn("9876543210", report_text)

            exported = [p.name for p in (out / "sanitized").rglob("*") if p.is_file()]
            self.assertEqual(len(exported), 1)
            self.assertNotIn("Reena", exported[0])
            self.assertNotIn("0076928", exported[0])

            q_recs = _build_safe_quarantine_records(
                "job-q", "ds-q", "org-q", report["files"], 1, inp, 1000.0
            )
            self.assertEqual(len(q_recs), 1)
            self.assertNotIn("Reena", json.dumps(q_recs))


if __name__ == "__main__":
    unittest.main(verbosity=2)
