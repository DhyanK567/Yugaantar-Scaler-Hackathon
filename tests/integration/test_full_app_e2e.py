#!/usr/bin/env python3
"""
Phase 15 — Full Application End-to-End Integration Test Suite.
Tests the complete MediLocker / GuptKavach stack (FastAPI + SQLite + Privacy Engine +
Attack Simulator + Clinical Validator + Privacy Passport + Research Network + Audit Trail)
using synthetic multi-hospital datasets (Hospital A, Hospital B, Hospital C, Lab D).
"""

import io
import json
import os
import sys
import unittest
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from backend.main import app


class TestFullApplicationIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["RAKSHA_SECRET"] = "test_e2e_secret_2026"
        cls.client = TestClient(app)

    def test_01_organisations_isolation_and_crud(self):
        # Create a fresh synthetic hospital (Hospital C custom)
        r = self.client.post("/api/organisations", json={
            "name": "Test Integration Hospital E2E",
            "org_type": "Hospital",
            "region": "Lucknow",
        })
        self.assertEqual(r.status_code, 200)
        org_id = r.json()["org_id"]

        # Dashboard for fresh org must show has_data=False and NOT leak another org's job
        dash = self.client.get(f"/api/dashboard?org_id={org_id}")
        self.assertEqual(dash.status_code, 200)
        self.assertFalse(dash.json()["has_data"])
        self.assertEqual(dash.json()["summary"]["release_readiness"], "NOT_EVALUATED")

        # Attack simulator for unrun org must show NOT_RUN
        atk = self.client.get(f"/api/attacks?org_id={org_id}")
        self.assertEqual(atk.status_code, 200)
        self.assertEqual(atk.json()["status"], "NOT_RUN")
        self.assertEqual(len(atk.json()["vectors"]), 7)

    def test_02_multilingual_upload_process_assess_passport_and_download(self):
        # 1. Create dedicated synthetic org
        org_r = self.client.post("/api/organisations", json={
            "name": "Hospital A E2E Suite",
            "org_type": "Hospital",
            "region": "Delhi",
        })
        org_id = org_r.json()["org_id"]

        # 2. Prepare synthetic multilingual files (CSV, FHIR JSON, TXT Hindi/Hinglish, corrupt JSON, unsupported XML)
        csv_bytes = (
            "patient_name,age,gender,district,aadhaar,diagnosis,medication\n"
            "Amit Kumar,42,M,Jaipur,9876 5432 1098,Dengue Fever,Paracetamol 500mg\n"
            "Sunita Devi,43,F,Jaipur,8765 4321 0987,Typhoid,Azithromycin 500mg\n"
            "Ramesh Sharma,41,M,Jaipur,7654 3210 9876,Hypertension,Amlodipine 5mg\n"
            "Priya Verma,44,F,Jaipur,6543 2109 8765,Diabetes,Metformin 500mg\n"
            "Mohan Lal,40,M,Jaipur,5432 1098 7654,Asthma,Salbutamol 100mcg\n"
        ).encode("utf-8")

        txt_bytes = (
            "मरीज: राजेश वर्मा, पिता: सुरेश वर्मा, मोबाइल: 9876543210।\n"
            "Chief complaint: C/O fever and cough. Tab Dolo 650 mg TDS.\n"
        ).encode("utf-8")

        fhir_bytes = json.dumps({
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [
                {
                    "fullUrl": "urn:uuid:pt-1",
                    "resource": {
                        "resourceType": "Patient",
                        "id": "pt-1",
                        "name": [{"text": "Vikram Singh"}],
                        "gender": "male",
                        "birthDate": "1982-05-14",
                        "address": [{"district": "Jaipur", "postalCode": "302001"}],
                    },
                },
                {
                    "fullUrl": "urn:uuid:obs-1",
                    "resource": {
                        "resourceType": "Observation",
                        "id": "obs-1",
                        "status": "final",
                        "code": {"text": "Blood Pressure"},
                        "subject": {"reference": "urn:uuid:pt-1"},
                    },
                },
            ],
        }).encode("utf-8")

        corrupt_json = b"{invalid_json_payload"
        unsupported_xml = b"<clinical><patient>Test</patient></clinical>"

        files = [
            ("files", ("opd_cohort.csv", csv_bytes, "text/csv")),
            ("files", ("hindi_note.txt", txt_bytes, "text/plain")),
            ("files", ("fhir_bundle.json", fhir_bytes, "application/json")),
            ("files", ("corrupt.json", corrupt_json, "application/json")),
            ("files", ("legacy.xml", unsupported_xml, "application/xml")),
        ]

        up = self.client.post(
            "/api/datasets/upload",
            data={"org_id": org_id, "name": f"E2E Cohort {os.urandom(2).hex()}"},
            files=files,
        )
        self.assertEqual(up.status_code, 200, up.text)
        ds_id = up.json()["dataset_id"]
        self.assertEqual(up.json()["validation_status"], "VALIDATED_WITH_WARNINGS")

        # Duplicate upload for same org must return 409 Conflict
        dup = self.client.post(
            "/api/datasets/upload",
            data={"org_id": org_id, "name": "Duplicate Cohort"},
            files=files,
        )
        self.assertEqual(dup.status_code, 409)

        # 3. Execute Privacy Engine Job
        job_r = self.client.post("/api/jobs", data={"dataset_id": ds_id, "org_id": org_id})
        self.assertEqual(job_r.status_code, 200, job_r.text)
        job_data = job_r.json()
        job_id = job_data["job_id"]
        self.assertEqual(job_data["status"], "Completed")
        self.assertEqual(job_data["result"]["files_total"], 5)
        self.assertEqual(job_data["result"]["files_sanitized"], 3)
        self.assertEqual(job_data["result"]["files_quarantined"], 2)

        # 4. Verify Dashboard, Privacy Intelligence, Clinical Integrity, Identity, Attacks, Passport all reference this job_id
        dash = self.client.get(f"/api/dashboard?org_id={org_id}&job_id={job_id}").json()
        self.assertTrue(dash["has_data"])
        self.assertEqual(dash["latest_job"]["id"], job_id)
        self.assertEqual(dash["summary"]["identity_precision"], "NOT_MEASURED")

        clin = self.client.get(f"/api/clinical-integrity?org_id={org_id}&job_id={job_id}").json()
        self.assertEqual(clin["status"], "MEASURED")
        self.assertGreaterEqual(clin["fhir_bundles_checked"], 1)
        self.assertTrue(clin["fhir_validation_passed"])
        self.assertEqual(clin["clinical_preservation_pct"], "NOT_MEASURED")

        ident = self.client.get(f"/api/identity-graph?org_id={org_id}&job_id={job_id}").json()
        self.assertEqual(ident["status"], "MEASURED")
        self.assertEqual(ident["precision"], "NOT_MEASURED")

        atk = self.client.post("/api/attacks/run", json={"job_id": job_id}).json()
        self.assertEqual(atk["status"], "EXECUTED")
        self.assertEqual(len(atk["vectors"]), 7)

        ver = self.client.post(f"/api/passports/{job_id}/verify").json()
        self.assertTrue(ver["valid"], ver)

        # 5. Approve release (if REVIEW_REQUIRED) and download bundle
        self.client.post(f"/api/jobs/{job_id}/release", json={"decision": "APPROVED", "reason": "E2E test approval"})
        dl = self.client.get(f"/api/jobs/{job_id}/download")
        self.assertEqual(dl.status_code, 200)
        with zipfile.ZipFile(io.BytesIO(dl.content), "r") as zf:
            names = zf.namelist()
            self.assertIn("report.json", names)
            self.assertIn("privacy_passport.json", names)
            # Ensure quarantined files are NOT in zip and raw PII is NOT in sanitized files
            for n in names:
                self.assertNotIn("corrupt.json", n)
                self.assertNotIn("legacy.xml", n)
                if n.startswith("sanitized/"):
                    content_str = zf.read(n).decode("utf-8", errors="ignore")
                    self.assertNotIn("9876 5432 1098", content_str)
                    self.assertNotIn("9876543210", content_str)
                    self.assertNotIn("Vikram Singh", content_str)

        # 6. Research Network workflow
        req_r = self.client.post("/api/research/requests", json={
            "title": "E2E Diabetes Study",
            "requestor_org": "Synthetic Research Institute",
            "target_orgs": ["Hospital A E2E Suite"],
            "dataset_id": ds_id,
            "purpose": "Verify end-to-end governed research release.",
        })
        self.assertEqual(req_r.status_code, 200)
        req_id = req_r.json()["request_id"]

        app_r = self.client.post(f"/api/research/requests/{req_id}/approve")
        self.assertEqual(app_r.status_code, 200)
        self.assertIn(job_id, app_r.json()["permitted_output_ref"])

        # 7. Audit trail must have events for this org and zero secrets/PII
        aud = self.client.get(f"/api/audit?org_id={org_id}").json()
        self.assertGreater(len(aud["audit_logs"]), 0)
        aud_dump = json.dumps(aud)
        self.assertNotIn("test_e2e_secret_2026", aud_dump)
        self.assertNotIn("9876543210", aud_dump)

    def test_03_settings_validation_and_persistence(self):
        bad = self.client.post("/api/settings", json={"date_shift_max_days": 999, "min_group_size": 5, "age_band_width": 5})
        self.assertEqual(bad.status_code, 400)

        ok = self.client.post("/api/settings", json={"date_shift_max_days": 180, "min_group_size": 5, "age_band_width": 5})
        self.assertEqual(ok.status_code, 200)


if __name__ == "__main__":
    unittest.main()
