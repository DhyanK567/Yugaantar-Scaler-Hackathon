"""M15.2, M15.4, M15.5, M15.6 & M15.8 — Full-System Integration & Failure-Injection Suite."""
from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STARTER = ROOT / "starter"
if str(STARTER) not in sys.path:
    sys.path.insert(0, str(STARTER))

from raksha_engine.crypto import (
    DecryptionAuthenticationError,
    GuptKavachKeyRing,
    InvalidSecretError,
    decrypt_payload,
    encrypt_payload,
)
from raksha_engine.secure_fs import PathSecurityError, verify_path_containment


def _run_cli(inp: Path, out: Path, secret: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ, RAKSHA_SECRET=secret, HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    return subprocess.run(
        [sys.executable, str(STARTER / "main.py"), "--input", str(inp), "--output", str(out)],
        capture_output=True, text=True, env=env, timeout=120,
    )


class TestMilestone15Integration(unittest.TestCase):
    def test_01_end_to_end_stage_trace_and_peak_memory(self) -> None:
        work = Path(tempfile.mkdtemp(prefix="m15_int_"))
        try:
            inp, out = work / "inp", work / "out"
            inp.mkdir()
            (inp / "ward.csv").write_text(
                "UHID,Patient Name,Gender,Age,Village,District,PIN,Diagnosis,BP,Medication\n"
                "HA-1001,Arvind Kulkarni,M,52,Kothrud,Pune,411038,Hypertension,138/88,Amlodipine 5 mg\n"
                "HA-1002,Savita Kulkarni,F,49,Kothrud,Pune,411038,Type 2 diabetes,122/78,Metformin 500 mg\n",
                encoding="utf-8",
            )
            res = _run_cli(inp, out, "m15-integration-secret")
            self.assertEqual(res.returncode, 0, res.stderr)
            rep = json.loads((out / "report.json").read_text(encoding="utf-8"))
            self.assertIn("privacy_intelligence", rep)
            self.assertIn("clinical_integrity", rep)
            pi = rep["privacy_intelligence"]
            self.assertGreater(len(pi.get("stage_trace", [])), 0)
            self.assertGreater(sum(pi.get("field_tier_counts", {}).values()), 0)
            self.assertGreater(rep["resources"]["peak_rss_mb"], 0.0)
            # Validate output contract
            v = subprocess.run(
                [sys.executable, str(ROOT / "validate_output.py"), "--input", str(inp), "--output", str(out)],
                capture_output=True, text=True, timeout=60,
            )
            self.assertIn("CONTRACT OK", v.stdout)
        finally:
            shutil.rmtree(work, ignore_errors=True)

    def test_02_failure_injection_and_recovery(self) -> None:
        # 1. Invalid / empty secret rejected
        with self.assertRaises(InvalidSecretError):
            GuptKavachKeyRing(b"")

        # 2. Tampered intermediate AEAD data rejected
        kr = GuptKavachKeyRing(b"valid-secret-key-m15")
        ct = encrypt_payload(b"sensitive-intermediate", kr.storage_encryption_key, b"ctx")
        tampered = bytearray(ct)
        tampered[-1] ^= 0xFF
        with self.assertRaises(DecryptionAuthenticationError):
            decrypt_payload(bytes(tampered), kr.storage_encryption_key, b"ctx")

        # 3. Path traversal rejected
        work = Path(tempfile.mkdtemp(prefix="m15_fail_"))
        try:
            inp, out = work / "inp", work / "out"
            inp.mkdir()
            with self.assertRaises(PathSecurityError):
                verify_path_containment(work / "outside.txt", inp)

            # 4. Corrupted JSON, empty file, unsupported binary, malformed FHIR
            (inp / "corrupt.json").write_text("{bad json", encoding="utf-8")
            (inp / "empty.txt").write_text("", encoding="utf-8")
            (inp / "raw_image.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00")
            (inp / "bad_fhir.json").write_text(json.dumps({
                "resourceType": "Bundle",
                "type": "collection",
                "entry": [{"resource": {"resourceType": "Observation", "status": "final"}}],
            }), encoding="utf-8")

            res = _run_cli(inp, out, "m15-fail-secret")
            self.assertEqual(res.returncode, 0)
            rep = json.loads((out / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(rep["counts"]["files_quarantined"], 3)
            self.assertFalse((out / "sanitized" / "raw_image.png").exists())
            self.assertFalse(rep["clinical_integrity"]["fhir_validation_passed"])
        finally:
            shutil.rmtree(work, ignore_errors=True)

    def test_03_combined_adversarial_attacks_and_no_pii_in_logs(self) -> None:
        work = Path(tempfile.mkdtemp(prefix="m15_adv_"))
        try:
            inp, out = work / "inp", work / "out"
            inp.mkdir()
            b64_payload = base64.b64encode(b"Witnessed by Zulfiqar Qureshi, mobile 9811223344.").decode("ascii")
            (inp / "Zulfiqar_Qureshi_9811223344.txt").write_text(
                "Patient Name: Zulfiqar Qureshi\n"
                "DOB: 14-07-1975\n"
                "Address: House 19, Gram Chandpur, Tehsil Barabanki, Distt. Barabanki - 225001\n"
                "Diagnosis: Crohn's disease. Rx: Prednisolone 10 mg daily.\n"
                f"Attachment: {b64_payload}\n",
                encoding="utf-8",
            )
            secret = "m15-adv-secret-99"
            res = _run_cli(inp, out, secret)
            self.assertEqual(res.returncode, 0)
            logs = res.stdout + res.stderr
            rep_text = (out / "report.json").read_text(encoding="utf-8")
            for forbidden in ("Zulfiqar Qureshi", "9811223344", "14-07-1975", "Chandpur", secret):
                self.assertNotIn(forbidden, logs)
                self.assertNotIn(forbidden, rep_text)
            # Check sanitized output & decoded base64
            san_files = list((out / "sanitized").glob("*.txt"))
            self.assertEqual(len(san_files), 1)
            self.assertNotIn("Zulfiqar", san_files[0].name)
            txt = san_files[0].read_text(encoding="utf-8")
            self.assertNotIn("Zulfiqar Qureshi", txt)
            self.assertNotIn("9811223344", txt)
            self.assertIn("Crohn's disease", txt)
            self.assertIn("Prednisolone 10 mg", txt)
        finally:
            shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
