#!/usr/bin/env python3
"""M25 Regression Tests for Generalisable Engine Hardening."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "starter"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from raksha_engine.names import CorpusNameIndex
from raksha_engine.sanitizer import sanitize_filename, sanitize_free_text
from run_m25_eval import (
    eval_adversarial_15,
    eval_clinical_1000,
    eval_filename_privacy,
    eval_identity_stress,
)


class M25EngineRegressionTests(unittest.TestCase):
    def test_01_uppercase_care_of_and_kinship_cues(self) -> None:
        idx = CorpusNameIndex()
        txt = "Patient: Farhan Siddiqui. S/O Tariq Siddiqui. Accompanied by brother Imran Siddiqui who signed."
        out, _ = sanitize_free_text(txt, idx, None, b"")
        self.assertNotIn("Farhan Siddiqui", out)
        self.assertNotIn("Tariq Siddiqui", out)
        self.assertNotIn("Imran Siddiqui", out)

    def test_02_fullwidth_digits_and_nfd_devanagari(self) -> None:
        import unicodedata
        idx = CorpusNameIndex()
        fw = "".join(chr(0xFF10 + int(d)) for d in "9876543210")
        nfd = unicodedata.normalize("NFD", "कविता देशमुख")
        txt = f"रोगी का नाम: {nfd}\nPhone: {fw}\nSpO2 98%."
        out, _ = sanitize_free_text(txt, idx, None, b"")
        self.assertNotIn("9876543210", out)
        self.assertNotIn(fw, out)
        self.assertNotIn("कविता", out)
        self.assertIn("SpO2 98%", out)

    def test_03_short_mrn_filename_and_adversarial_15(self) -> None:
        idx = CorpusNameIndex()
        out_fn = sanitize_filename("discharge/jeevanjyoti_ds_IP-26-00134.txt", idx, "abc123", secret=b"sec")
        self.assertNotIn("IP-26-00134", out_fn)

        adv = eval_adversarial_15()
        self.assertEqual(adv["contract"], "CONTRACT OK")
        for cat, res in adv["categories"].items():
            leaked = res.get("pii_leaked")
            if isinstance(leaked, int):
                self.assertEqual(leaked, 0, cat)
            else:
                self.assertEqual(leaked, [], cat)
            fps = res.get("false_positives")
            if isinstance(fps, int):
                self.assertEqual(fps, 0, cat)
            else:
                self.assertEqual(fps, [], cat)

    def test_04_identity_stress_zero_false_merges_and_clinical_1000(self) -> None:
        id_res = eval_identity_stress()
        self.assertEqual(id_res["fp_false_merges"], 0)
        self.assertEqual(id_res["pairwise_precision"], 1.0)

        clin_res = eval_clinical_1000()
        self.assertEqual(clin_res["changed_count"], 0)
        self.assertEqual(clin_res["total_clinical_values"], 1000)

        fn_res = eval_filename_privacy()
        self.assertEqual(fn_res["path_leaks"], [])
        self.assertEqual(fn_res["report_leaks"], [])
        self.assertEqual(fn_res["records_leaks"], [])


if __name__ == "__main__":
    unittest.main()
