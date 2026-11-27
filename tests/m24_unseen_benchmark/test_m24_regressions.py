"""M24 Automated Regression Tests for Unseen Schemas, Indian IDs, Hinglish Labels & Entity Layers."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
STARTER_DIR = REPO_ROOT / "starter"
if str(STARTER_DIR) not in sys.path:
    sys.path.insert(0, str(STARTER_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


class M24EngineRegressionTests(unittest.TestCase):
    def test_01_unseen_indian_ids_and_hinglish_labels(self) -> None:
        from raksha_engine.names import CorpusNameIndex
        from raksha_engine.sanitizer import sanitize_free_text

        idx = CorpusNameIndex()
        text = (
            "Mareez ka naam: Farhan Siddiqui\n"
            "Pita ka naam: Tariq Siddiqui\n"
            "Voter ID: UPK7712390\n"
            "Driving Licence: UP32 20190045123\n"
            "Passport: K4829104\n"
            "Seen by Dr. Ramesh Kumar. ASHA worker coordinated.\n"
            "Paracetamol 650 mg twice daily; BP 120/80 mmHg; HbA1c 7.2%; Parkinson's disease.\n"
        )
        cleaned, count = sanitize_free_text(text, idx, "k1", b"secret-m24", 30)
        self.assertGreaterEqual(count, 5)
        for leaked in ("Farhan Siddiqui", "Tariq Siddiqui", "UPK7712390", "UP32 20190045123", "K4829104"):
            self.assertNotIn(leaked, cleaned)
        for preserved in ("Dr. Ramesh Kumar", "ASHA worker", "Paracetamol 650 mg twice daily", "BP 120/80 mmHg", "HbA1c 7.2%", "Parkinson's disease"):
            self.assertIn(preserved, cleaned)

    def test_02_entity_layer_consolidation(self) -> None:
        from raksha_engine.entity_layers import EntityDetection, consolidate_detections

        dets = [
            EntityDetection("CLINICAL", "row:0:drug", "CONTEXTUAL", "Paracetamol 650 mg", 0.95, "LOW", "PRESERVE", True, "PRESERVE"),
            EntityDetection("PATIENT_NAME", "row:0:drug", "PATTERN", "Paracetamol", 0.50, "LOW", "REDACT", False, "TRANSFORM"),
            EntityDetection("VOTER_ID", "row:0:voter", "PATTERN", "UPK7712390", 0.98, "HIGH", "REDACT", False, "TRANSFORM"),
        ]
        res = consolidate_detections(dets)
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0].category, "CLINICAL")

    def test_03_unseen_benchmark_achieves_zero_leaks_and_full_clinical_fidelity(self) -> None:
        from tests.m24_unseen_benchmark.benchmark_m24 import run_benchmark

        m = run_benchmark()
        self.assertTrue(m["contract_ok"])
        self.assertEqual(m["pii_leaked_count"], 0)
        self.assertEqual(m["pii_precision"], 1.0)
        self.assertEqual(m["pii_recall"], 1.0)
        self.assertEqual(m["clinical_fidelity_pct"], 100.0)
        self.assertTrue(m["cross_language_kavita_linked"])


if __name__ == "__main__":
    unittest.main()
