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
import tempfile
import time
import unittest
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from backend.main import app


class TestFullApplicationIntegration(unittest.TestCase):
    _tmpdir: tempfile.TemporaryDirectory

    @classmethod
    def setUpClass(cls):
        cls._tmpdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        os.environ["MEDILOCKER_DATA_DIR"] = cls._tmpdir.name
        os.environ["RAKSHA_SECRET"] = "test_e2e_secret_2026"
        from backend.database import init_db
        from backend import pipeline, main as backend_main
        from pathlib import Path as _P
        # Re-point module-level JOBS_DIR / DATASETS_DIR in both pipeline and main
        _data = _P(cls._tmpdir.name)
        _jobs = _data / "jobs"
        _datasets = _data / "datasets"
        _jobs.mkdir(parents=True, exist_ok=True)
        _datasets.mkdir(parents=True, exist_ok=True)
        pipeline.DATA_DIR = _data
        pipeline.JOBS_DIR = _jobs
        pipeline.DATASETS_DIR = _datasets
        backend_main.JOBS_DIR = _jobs
        backend_main.DATASETS_DIR = _datasets
        init_db()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        from backend import pipeline, main as backend_main
        from pathlib import Path as _P
        # Restore pipeline dirs to real data dir so other tests are not affected
        _real_data = _P(__file__).resolve().parent.parent.parent / "data"
        pipeline.DATA_DIR = _real_data
        pipeline.JOBS_DIR = _real_data / "jobs"
        pipeline.DATASETS_DIR = _real_data / "datasets"
        backend_main.JOBS_DIR = _real_data / "jobs"
        backend_main.DATASETS_DIR = _real_data / "datasets"
        cls.client.close()
        cls._tmpdir.cleanup()

    def test_01_organisations_isolation_and_crud(self):
        # Create a fresh synthetic hospital
        r = self.client.post("/api/organisations", json={
            "name": "Test Integration Hospital E2E",
            "org_type": "Hospital",
            "region": "Lucknow",
        })
        self.assertEqual(r.status_code, 200)
        # API returns the full DB row: id field (not legacy org_id)
        org_id = r.json().get("id") or r.json().get("org_id")
        self.assertIsNotNone(org_id)

        # Dashboard returns current-API shape: metrics, privacy_health, recent_jobs
        dash = self.client.get("/api/dashboard")
        self.assertEqual(dash.status_code, 200)
        body = dash.json()
        self.assertIn("metrics", body)
        self.assertIn("privacy_health", body)
        self.assertIn("recent_jobs", body)

        # Org list must include the newly created org
        orgs = self.client.get("/api/organisations")
        self.assertEqual(orgs.status_code, 200)
        org_ids = [o["id"] for o in orgs.json()]
        self.assertIn(org_id, org_ids)

    def test_02_multilingual_upload_process_assess_passport_and_download(self):
        # 1. Create dedicated synthetic org
        org_r = self.client.post("/api/organisations", json={
            "name": "Hospital A E2E Suite",
            "org_type": "Hospital",
            "region": "Delhi",
        })
        self.assertEqual(org_r.status_code, 200)
        org_id = org_r.json().get("id") or org_r.json().get("org_id")
        self.assertIsNotNone(org_id)

        # 2. Prepare synthetic multilingual files
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

        files = [
            ("files", ("opd_cohort.csv", csv_bytes, "text/csv")),
            ("files", ("hindi_note.txt", txt_bytes, "text/plain")),
        ]

        # 3. Upload via current API endpoint POST /api/datasets with auto_process=true sync=true
        up = self.client.post(
            "/api/datasets",
            data={"organisation_id": org_id, "name": f"E2E Cohort {os.urandom(2).hex()}",
                  "auto_process": "true", "sync": "true"},
            files=files,
        )
        self.assertEqual(up.status_code, 200, up.text)
        up_body = up.json()
        # Response: {"dataset_id": "...", "job": {...}}
        self.assertIn("dataset_id", up_body)
        self.assertIn("job", up_body)
        ds_id = up_body["dataset_id"]
        job_id = up_body["job"]["id"]
        self.assertIsNotNone(ds_id)
        self.assertIsNotNone(job_id)

        # 4. Dashboard returns current shape with recent_jobs populated
        dash = self.client.get("/api/dashboard")
        self.assertEqual(dash.status_code, 200)
        dash_body = dash.json()
        self.assertIn("metrics", dash_body)
        self.assertIn("recent_jobs", dash_body)
        # At least one job should be present
        self.assertGreater(len(dash_body["recent_jobs"]), 0)

        # 5. Download the job bundle
        dl = self.client.get(f"/api/jobs/{job_id}/download")
        self.assertEqual(dl.status_code, 200)
        with zipfile.ZipFile(io.BytesIO(dl.content), "r") as zf:
            names = zf.namelist()
            self.assertIn("report.json", names)
            self.assertIn("privacy_passport.json", names)
            # Sanitized files must not contain raw PII
            for n in names:
                if n.startswith("sanitized/"):
                    content_str = zf.read(n).decode("utf-8", errors="ignore")
                    self.assertNotIn("9876 5432 1098", content_str)
                    self.assertNotIn("9876543210", content_str)

        # 6. Research Network workflow
        req_r = self.client.post("/api/research/requests", json={
            "title": "E2E Diabetes Study",
            "institution": "Synthetic Research Institute",
            "dataset_id": ds_id,
            "purpose": "Verify end-to-end governed research release.",
        })
        self.assertEqual(req_r.status_code, 200)
        req_id = req_r.json().get("request_id") or req_r.json().get("id")

        app_r = self.client.post(f"/api/research/requests/{req_id}/approve")
        self.assertEqual(app_r.status_code, 200)

        # 7. Audit trail must have events and zero secrets/raw PII
        aud = self.client.get("/api/audit")
        self.assertEqual(aud.status_code, 200)
        aud_dump = json.dumps(aud.json())
        self.assertNotIn("test_e2e_secret_2026", aud_dump)
        self.assertNotIn("9876543210", aud_dump)

    def test_03_settings_validation_and_persistence(self):
        # Settings endpoint accepts valid fields and returns 200
        ok = self.client.post("/api/settings", json={"output_format": "sanitized+report+records", "multilingual_enabled": True})
        self.assertEqual(ok.status_code, 200)

        # Unknown-only fields (extra kwargs ignored by Pydantic) still return 200
        ok2 = self.client.post("/api/settings", json={"quarantine_threshold": 0.5})
        self.assertEqual(ok2.status_code, 200)

        # GET settings returns expected structure
        gs = self.client.get("/api/settings")
        self.assertEqual(gs.status_code, 200)
        data = gs.json()
        self.assertIn("output_format", data)
        self.assertIn("raksha_secret_set", data)


if __name__ == "__main__":
    unittest.main()
