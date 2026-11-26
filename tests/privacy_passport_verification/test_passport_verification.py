#!/usr/bin/env python3
"""Phase 4 — Live Verifiable Privacy Passport Verification Tests."""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
STARTER_DIR = REPO_ROOT / "starter"
sys.path.insert(0, str(STARTER_DIR))

from verify_passport import verify_passport_bundle


class TestLivePrivacyPassportVerification(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="m15_5_passport_"))
        self.inp = self.tmp / "input"
        self.out = self.tmp / "output"
        self.inp.mkdir()
        (self.inp / "note.txt").write_text(
            "Patient: Amit Kumar, Phone: 9876543210, Diagnosis: Dengue fever, Tab Paracetamol 500 mg.",
            encoding="utf-8",
        )
        res = subprocess.run(
            [sys.executable, str(STARTER_DIR / "main.py"), "--input", str(self.inp), "--output", str(self.out)],
            cwd=str(STARTER_DIR),
            env={"PATH": "", "RAKSHA_SECRET": "test_passport_secret_2026"},
            capture_output=True,
            text=True,
        )
        # Fallback with full env if PATH was empty on Windows
        if res.returncode != 0:
            import os
            env = dict(os.environ, RAKSHA_SECRET="test_passport_secret_2026")
            res = subprocess.run(
                [sys.executable, str(STARTER_DIR / "main.py"), "--input", str(self.inp), "--output", str(self.out)],
                cwd=str(STARTER_DIR),
                env=env,
                capture_output=True,
                text=True,
            )
        self.assertEqual(res.returncode, 0, res.stderr)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_valid_passport_verifies_and_contains_no_raw_pii(self):
        pp_path = self.out / "privacy_passport.json"
        self.assertTrue(pp_path.is_file())
        pp_text = pp_path.read_text(encoding="utf-8")
        self.assertNotIn("Amit Kumar", pp_text)
        self.assertNotIn("9876543210", pp_text)
        self.assertNotIn("test_passport_secret_2026", pp_text)

        ver = verify_passport_bundle(pp_path, self.out, manifest_path=self.out / "dataset_manifest.json")
        self.assertTrue(ver["valid"], ver)

    def test_altered_output_file_detected_and_rejected(self):
        san_file = next((self.out / "sanitized").rglob("*.txt"))
        san_file.write_text(san_file.read_text(encoding="utf-8") + "\nTAMPERED_LINE\n", encoding="utf-8")
        ver = verify_passport_bundle(self.out / "privacy_passport.json", self.out, manifest_path=self.out / "dataset_manifest.json")
        self.assertFalse(ver["valid"])
        self.assertEqual(ver["status"], "TAMPERED")

    def test_tampered_passport_hash_rejected(self):
        pp_path = self.out / "privacy_passport.json"
        pp = json.loads(pp_path.read_text(encoding="utf-8"))
        pp["dataset_provenance"]["output_dataset_root_hash"] = "0" * 64
        pp_path.write_text(json.dumps(pp), encoding="utf-8")
        ver = verify_passport_bundle(pp_path, self.out, manifest_path=self.out / "dataset_manifest.json")
        self.assertFalse(ver["valid"])


if __name__ == "__main__":
    unittest.main()
