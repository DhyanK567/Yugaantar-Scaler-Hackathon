#!/usr/bin/env python3
"""Phase 2 — Clinical Fidelity & Drift Engine Test Suite."""

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "starter"))

from raksha_engine.clinical_validator import analyze_clinical_drift, _safe_pct


class TestClinicalDriftEngine(unittest.TestCase):
    def test_exact_preservation_with_redacted_patient_name(self):
        inp = [
            "Patient Amit Kumar (Aadhaar 9876 5432 1098) diagnosed with Dengue fever. "
            "BP 120/80 mmHg, HR 78 bpm, Temp 101.4 F, SpO2 98 %, Hb 13.2 g/dL, RBS 110 mg/dL, "
            "Creatinine 0.9 mg/dL. Tab Paracetamol 500 mg PO TDS for 5 days."
        ]
        san = [
            "Patient [PATIENT_NAME] (Aadhaar [AADHAAR]) diagnosed with Dengue fever. "
            "BP 120/80 mmHg, HR 78 bpm, Temp 101.4 F, SpO2 98 %, Hb 13.2 g/dL, RBS 110 mg/dL, "
            "Creatinine 0.9 mg/dL. Tab Paracetamol 500 mg PO TDS for 5 days."
        ]
        res = analyze_clinical_drift(inp, san)
        self.assertTrue(res["passed"])
        self.assertEqual(res["overall"]["missing"], 0)
        self.assertEqual(res["overall"]["modified"], 0)
        self.assertEqual(res["overall"]["exact_fidelity_pct"], 100.0)
        # Ensure patient name is not in report
        dumped = json.dumps(res)
        self.assertNotIn("Amit Kumar", dumped)
        self.assertNotIn("9876 5432 1098", dumped)

    def test_dosage_mutation_5mg_to_50mg_is_critical_failure(self):
        inp = ["Tab Amlodipine 5 mg PO OD for 30 days."]
        san = ["Tab Amlodipine 50 mg PO OD for 30 days."]
        res = analyze_clinical_drift(inp, san)
        self.assertFalse(res["passed"])
        self.assertEqual(res["categories"]["dosages"]["modified"], 1)
        self.assertTrue(any(f["code"] == "CLINICAL_VALUE_DRIFT" for f in res["critical_failures"]))

    def test_missing_clinical_value_detected(self):
        inp = ["Hb 11.4 g/dL, Metformin 500 mg BD."]
        san = ["Metformin 500 mg BD."]
        res = analyze_clinical_drift(inp, san)
        self.assertFalse(res["passed"])
        self.assertGreaterEqual(res["categories"]["haemoglobin"]["missing"], 1)

    def test_never_round_99_96_or_4853_of_4855_to_100(self):
        pct = _safe_pct(4853, 4855)
        self.assertEqual(pct, 99.96)
        self.assertLess(pct, 100.0)
        pct2 = _safe_pct(49999, 50000)
        self.assertLess(pct2, 100.0)

    def test_fhir_bundle_validation_in_drift(self):
        valid_bundle = {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [
                {"fullUrl": "urn:uuid:p1", "resource": {"resourceType": "Patient", "id": "p1"}},
                {"fullUrl": "urn:uuid:o1", "resource": {"resourceType": "Observation", "id": "o1", "status": "final", "code": {"text": "BP"}, "subject": {"reference": "urn:uuid:p1"}}},
            ],
        }
        res = analyze_clinical_drift(["BP 120/80"], ["BP 120/80"], fhir_bundles=[valid_bundle])
        self.assertTrue(res["passed"])
        self.assertEqual(res["fhir_bundles_checked"], 1)
        self.assertEqual(res["fhir_bundles_valid"], 1)


if __name__ == "__main__":
    unittest.main()
