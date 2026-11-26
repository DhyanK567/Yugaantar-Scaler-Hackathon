"""Integration tests for MediLocker Final Winning-Stretch Remediation.

Tests quarantine metadata safety, clinical drift category computation,
and verification script integrity using Python stdlib only.
"""
from __future__ import annotations

import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.pipeline import (  # noqa: E402
    _build_safe_quarantine_records,
    _classify_quarantine_reason,
    _evaluate_clinical_integrity,
)


class FinalRemediationTests(unittest.TestCase):
    def test_quarantine_metadata_never_leaks_raw_filename_or_pii(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            input_dir = Path(tmp)
            secret_file = input_dir / "John_Doe_MRN998877_CANARY_LEAK.csv"
            secret_file.write_text("patient_name,mrn\nJohn Doe,998877\n", encoding="utf-8")

            files_report = [
                {
                    "rel": secret_file.name,
                    "input_sha256": "abc123def4567890" * 4,
                    "status": "quarantined",
                    "reason": "Malformed CSV structure near John Doe MRN998877",
                }
            ]
            records = _build_safe_quarantine_records(
                job_id="job-test-001",
                dataset_id="ds-001",
                organisation_id="org-001",
                files_report=files_report,
                files_quarantined=1,
                input_dir=input_dir,
                now=time.time(),
            )
            self.assertEqual(len(records), 1)
            rec = records[0]
            serialized = json.dumps(rec)
            self.assertNotIn("John_Doe", serialized)
            self.assertNotIn("John Doe", serialized)
            self.assertNotIn("998877", serialized)
            self.assertNotIn("CANARY_LEAK", serialized)
            self.assertTrue(rec["opaque_ref"].startswith("QRN-"))
            self.assertEqual(rec["file_type"], "csv")
            self.assertEqual(rec["error_code"], "ERR_MALFORMED_STRUCTURE")
            self.assertEqual(rec["stage_failed"], "INGESTION_PARSE")
            self.assertTrue(rec["retry_safe"])
            self.assertFalse(rec["download_allowed"])
            self.assertTrue(rec["requires_manual_review"])

    def test_quarantine_summary_fallback_when_files_report_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            records = _build_safe_quarantine_records(
                job_id="job-legacy-02",
                dataset_id="ds-002",
                organisation_id="org-002",
                files_report=[],
                files_quarantined=2,
                input_dir=Path(tmp),
                now=time.time(),
            )
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["error_code"], "ERR_POLICY_QUARANTINE")
            self.assertFalse(records[0]["download_allowed"])

    def test_classify_quarantine_reason_categories(self) -> None:
        code, _, stage, retry, _ = _classify_quarantine_reason("Unsupported binary extension .exe")
        self.assertEqual(code, "ERR_UNSUPPORTED_FORMAT")
        self.assertEqual(stage, "FORMAT_VALIDATION")
        self.assertFalse(retry)

        code2, _, stage2, retry2, _ = _classify_quarantine_reason("Canary string detected in output")
        self.assertEqual(code2, "ERR_PRIVACY_GATE_QUARANTINE")
        self.assertEqual(stage2, "PRIVACY_GATE")
        self.assertFalse(retry2)

    def test_clinical_integrity_populates_category_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            in_dir = Path(tmp) / "in"
            out_dir = Path(tmp) / "out"
            in_dir.mkdir()
            out_dir.mkdir()

            note = "Patient prescribed Metformin 500mg. BP 120/80 mmHg, SpO2 98%, Temp 98.6 F."
            (in_dir / "note.txt").write_text(f"Name: Ravi Kumar. {note}", encoding="utf-8")
            (out_dir / "note.txt").write_text(f"Name: [PATIENT_1]. {note}", encoding="utf-8")

            res = _evaluate_clinical_integrity(in_dir, out_dir)
            self.assertGreater(res["expected_values"], 0)
            self.assertEqual(res["modified_values"], 0)
            self.assertEqual(res["missing_values"], 0)
            self.assertIn("categories", res)
            self.assertIn("blood_pressure", res["categories"])

    def test_verification_scripts_and_readme_present(self) -> None:
        ps1 = REPO_ROOT / "scripts" / "verify_submission.ps1"
        sh = REPO_ROOT / "scripts" / "verify_submission.sh"
        readme = REPO_ROOT / "README.md"
        self.assertTrue(ps1.is_file())
        self.assertTrue(sh.is_file())
        self.assertIn("MEDILOCKER VERIFICATION SUMMARY", ps1.read_text(encoding="utf-8"))
        self.assertIn("MEDILOCKER VERIFICATION SUMMARY", sh.read_text(encoding="utf-8"))
        self.assertIn("# One-Click Verification", readme.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
