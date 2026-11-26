"""M13.8 — Adversarial Clinical Integrity & Structured Medical Data Fidelity Test Suite."""
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

from raksha_engine.clinical_validator import (
    validate_clinical_probes,
    validate_fhir_r4_bundle,
    verify_date_interval_preserved,
)
from raksha_engine.names import CorpusNameIndex
from raksha_engine.privacy import shift_date_string
from raksha_engine.sanitizer import sanitize_free_text, sanitize_json_node


def _run_cli(inp: Path, out: Path, secret: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ, RAKSHA_SECRET=secret, HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    return subprocess.run(
        [sys.executable, str(STARTER / "main.py"), "--input", str(inp), "--output", str(out)],
        capture_output=True, text=True, env=env, timeout=120,
    )


class TestMilestone13ClinicalIntegrity(unittest.TestCase):
    def test_01_medical_eponyms_and_diagnoses_preserved(self) -> None:
        ni = CorpusNameIndex()
        ni.add_name("Parkinson Patel")  # adversarial corpus name collision
        ni.add_name("Crohn Verma")
        eponyms = [
            "Parkinson's disease",
            "Alzheimer's disease",
            "Hodgkin lymphoma",
            "Crohn's disease",
            "Type 2 diabetes",
            "Myocardial infarction",
            "Chronic kidney disease",
            "Hypertension",
            "Tuberculosis",
        ]
        note = "Diagnoses: " + ", ".join(eponyms) + ". Patient Name: Parkinson Patel."
        cleaned, _ = sanitize_free_text(note, ni, "cluster|p1", b"sec", 180)
        self.assertNotIn("Parkinson Patel", cleaned)
        rep = validate_clinical_probes(eponyms, cleaned, "test_01")
        self.assertTrue(rep.passed, f"Lost/modified eponyms: {rep.failures}")

    def test_02_professionals_orgs_and_asha_vs_patient_names(self) -> None:
        ni = CorpusNameIndex()
        ni.add_name("Asha Rajput")
        ni.add_name("Asha")
        ni.add_name("Ramesh")
        note = (
            "Patient Name: Asha Rajput. Referred by ASHA worker to Dr. Ramesh at Apollo Hospital, "
            "Department of Cardiology. Follow-up with ASHA workers."
        )
        cleaned, _ = sanitize_free_text(note, ni, "cluster|p2", b"sec", 180)
        self.assertNotIn("Asha Rajput", cleaned)
        for keep in ("ASHA worker", "ASHA workers", "Dr. Ramesh", "Apollo Hospital", "Department of Cardiology"):
            self.assertIn(keep, cleaned)

    def test_03_medication_and_dosage_integrity(self) -> None:
        ni = CorpusNameIndex()
        meds = [
            "Dolo 650 mg",
            "Metformin 500 mg twice daily",
            "Paracetamol 500 mg",
            "Insulin 10 units",
            "5 ml syrup",
            "1 tablet every 8 hours",
            "0.5 mg",
            "2.5 ml",
        ]
        note = "Rx: " + "; ".join(meds) + "."
        cleaned, _ = sanitize_free_text(note, ni, "cluster|p3", b"sec", 180)
        rep = validate_clinical_probes(meds, cleaned, "test_03")
        self.assertTrue(rep.passed, f"Medication integrity failed: {rep.failures}")

    def test_04_laboratory_and_vital_measurements_preserved(self) -> None:
        ni = CorpusNameIndex()
        labs = [
            "Blood pressure: 120/80 mmHg",
            "Temperature: 98.6°F",
            "Haemoglobin: 12.5 g/dL",
            "Blood glucose: 110 mg/dL",
            "SpO2: 98%",
            "Heart rate: 76 bpm",
            "Creatinine: 1.2 mg/dL",
            "Sodium: 140 mmol/L",
            "Height: 172 cm",
            "Weight: 68 kg",
            "Platelets: 175000 /uL",
            "Range: 150000-410000",
            "Delta: -2.5",
            "Count: 1.2e5",
        ]
        note = " | ".join(labs)
        cleaned, _ = sanitize_free_text(note, ni, "cluster|p4", b"sec", 180)
        rep = validate_clinical_probes(labs, cleaned, "test_04")
        self.assertTrue(rep.passed, f"Lab/vital integrity failed: {rep.failures}")

    def test_05_mixed_hindi_english_clinical_notes_with_relatives(self) -> None:
        ni = CorpusNameIndex()
        ni.add_name("Kamlesh Yadav")
        note = (
            "Patient Name: Kamlesh Yadav (S/o Ramprasad Yadav). "
            "kamlesh ko 3 din se bukhar 101.4 F, BP 118/76 mmHg. Dolo 650 mg BD diya."
        )
        cleaned, _ = sanitize_free_text(note, ni, "cluster|p5", b"sec", 180, local_first_names={"Kamlesh"})
        self.assertNotIn("Kamlesh Yadav", cleaned)
        self.assertNotIn("Ramprasad Yadav", cleaned)
        self.assertNotIn("kamlesh", cleaned.casefold())
        for keep in ("101.4 F", "118/76 mmHg", "Dolo 650 mg BD"):
            self.assertIn(keep, cleaned)

    def test_06_fhir_r4_all_14_resources_and_validator(self) -> None:
        ni = CorpusNameIndex()
        ni.add_name("Meera Devi")
        bundle = {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [
                {"fullUrl": "urn:uuid:pt1", "resource": {"resourceType": "Patient", "id": "pt1", "name": [{"text": "Meera Devi"}], "gender": "female", "birthDate": "1982-03-14", "contact": [{"name": {"text": "Suresh Devi"}, "telecom": [{"value": "9876543210"}]}]}},
                {"fullUrl": "urn:uuid:rp1", "resource": {"resourceType": "RelatedPerson", "id": "rp1", "patient": {"reference": "urn:uuid:pt1"}, "name": [{"text": "Suresh Devi"}]}},
                {"fullUrl": "urn:uuid:pr1", "resource": {"resourceType": "Practitioner", "id": "pr1", "name": [{"text": "Dr. Ramesh Srivastava"}]}},
                {"fullUrl": "urn:uuid:org1", "resource": {"resourceType": "Organization", "id": "org1", "name": "Apollo Hospital"}},
                {"fullUrl": "urn:uuid:loc1", "resource": {"resourceType": "Location", "id": "loc1", "name": "Department of Cardiology"}},
                {"fullUrl": "urn:uuid:enc1", "resource": {"resourceType": "Encounter", "id": "enc1", "status": "finished", "class": {"code": "IMP"}, "subject": {"reference": "urn:uuid:pt1"}, "period": {"start": "2026-02-01", "end": "2026-02-06"}}},
                {"fullUrl": "urn:uuid:obs1", "resource": {"resourceType": "Observation", "id": "obs1", "status": "final", "code": {"text": "Haemoglobin"}, "valueQuantity": {"value": 12.5, "unit": "g/dL"}}},
                {"fullUrl": "urn:uuid:cond1", "resource": {"resourceType": "Condition", "id": "cond1", "code": {"coding": [{"system": "http://snomed.info/sct", "code": "49049000", "display": "Parkinson's disease"}]}}},
                {"fullUrl": "urn:uuid:med1", "resource": {"resourceType": "Medication", "id": "med1", "code": {"text": "Metformin 500 mg"}}},
                {"fullUrl": "urn:uuid:mr1", "resource": {"resourceType": "MedicationRequest", "id": "mr1", "status": "active", "intent": "order", "medicationReference": {"reference": "urn:uuid:med1"}, "dosageInstruction": [{"text": "500 mg twice daily"}]}},
                {"fullUrl": "urn:uuid:ms1", "resource": {"resourceType": "MedicationStatement", "id": "ms1", "status": "active", "medicationCodeableConcept": {"text": "Insulin 10 units"}}},
                {"fullUrl": "urn:uuid:dr1", "resource": {"resourceType": "DiagnosticReport", "id": "dr1", "status": "final", "code": {"text": "CBC Panel"}}},
                {"fullUrl": "urn:uuid:proc1", "resource": {"resourceType": "Procedure", "id": "proc1", "status": "completed", "code": {"text": "Coronary angiography"}}},
                {"fullUrl": "urn:uuid:alg1", "resource": {"resourceType": "AllergyIntolerance", "id": "alg1", "code": {"text": "Penicillin"}}},
            ],
        }
        san_bundle, _, _ = sanitize_json_node(bundle, "", ni, "cluster|pt1", "PSN-TEST11", b"sec", 180)
        fres = validate_fhir_r4_bundle(san_bundle, "test_bundle")
        self.assertTrue(fres.valid, f"FHIR validation failed: {fres.failures}")
        self.assertEqual(fres.resources_checked, 14)

        san_text = json.dumps(san_bundle)
        self.assertNotIn("Meera Devi", san_text)
        self.assertNotIn("Suresh Devi", san_text)
        self.assertNotIn("9876543210", san_text)
        for keep in ("Dr. Ramesh Srivastava", "Apollo Hospital", "Department of Cardiology", "Parkinson's disease", "Metformin 500 mg", "Insulin 10 units", "Penicillin", "12.5"):
            self.assertIn(keep, san_text)

        # Negative test: broken reference & missing required field detected
        broken = {"resourceType": "Bundle", "type": "collection", "entry": [{"resource": {"resourceType": "Observation", "status": "final", "subject": {"reference": "urn:uuid:missing"}}}]}
        bres = validate_fhir_r4_bundle(broken, "broken")
        self.assertFalse(bres.valid)
        codes = {f.code for f in bres.failures}
        self.assertIn("FHIR_REQUIRED_FIELD_MISSING", codes)

    def test_07_nested_json_base64_colliding_keys_and_nulls(self) -> None:
        ni = CorpusNameIndex()
        ni.add_name("Sohan Lal")
        ni.add_name("Mohan Lal")
        b64_note = base64.b64encode(b"Patient Name: Sohan Lal. BP 120/80 mmHg. Temp 98.6 F.").decode("ascii")
        payload = {
            "nested": {"deep": {"attachment": b64_note, "empty": "", "null_val": None}},
            "by_name": {"Sohan Lal": {"dose": "0.5 mg"}, "Mohan Lal": {"dose": "2.5 ml"}},
        }
        san, _, _ = sanitize_json_node(payload, "", ni, "cluster|p7", "PSN-777", b"sec", 180)
        self.assertEqual(len(san["by_name"]), 2)  # colliding keys disambiguated, not overwritten
        self.assertIsNone(san["nested"]["deep"]["null_val"])
        decoded = base64.b64decode(san["nested"]["deep"]["attachment"]).decode("utf-8")
        self.assertNotIn("Sohan Lal", decoded)
        self.assertIn("120/80 mmHg", decoded)
        self.assertIn("98.6 F", decoded)

    def test_08_date_interval_preservation(self) -> None:
        s1 = shift_date_string("2026-03-01", "cluster|p8", b"sec-8", 180)
        s2 = shift_date_string("2026-03-09", "cluster|p8", b"sec-8", 180)
        ok, err = verify_date_interval_preserved("2026-03-01", "2026-03-09", s1, s2)
        self.assertTrue(ok, err)

    def test_09_csv_edge_cases_and_malformed_quarantine_e2e(self) -> None:
        work = Path(tempfile.mkdtemp(prefix="m13_e2e_"))
        try:
            inp, out = work / "inp", work / "out"
            inp.mkdir()
            (inp / "labs.csv").write_text(
                "UHID,Patient Name,Test,Result,Unit,Reference Range,Medication,Route\n"
                "JJH-101,Anita Verma,Haemoglobin,12.5,g/dL,12.0-16.0,Paracetamol 500 mg,Oral\n"
                "JJH-102,Sunita Verma,Platelets,175000,/uL,150000-410000,Insulin 10 units,SC\n",
                encoding="utf-8",
            )
            (inp / "malformed.json").write_text("{corrupt", encoding="utf-8")
            (inp / "empty.txt").write_text("", encoding="utf-8")

            res = _run_cli(inp, out, "m13-sec")
            self.assertEqual(res.returncode, 0)
            rep = json.loads((out / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(rep["counts"]["files_sanitized"], 1)
            self.assertEqual(rep["counts"]["files_quarantined"], 2)
            csv_out = (out / "sanitized" / "labs.csv").read_text(encoding="utf-8")
            for keep in ("12.5", "g/dL", "175000", "150000-410000", "Paracetamol 500 mg", "Insulin 10 units"):
                self.assertIn(keep, csv_out)
            self.assertNotIn("Anita Verma", csv_out)
            self.assertNotIn("Sunita Verma", csv_out)
        finally:
            shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
