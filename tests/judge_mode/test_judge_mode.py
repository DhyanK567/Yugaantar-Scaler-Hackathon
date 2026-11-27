#!/usr/bin/env python3
"""Direct Dashboard & Offline Workflow Tests (Zero Auth / Zero Login)."""
from __future__ import annotations

import io
import os
import sys
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))


class DirectDashboardWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self._old_dir = os.environ.get("MEDILOCKER_DATA_DIR")
        self._old_sec = os.environ.get("RAKSHA_SECRET")
        os.environ["MEDILOCKER_DATA_DIR"] = self._tmpdir.name
        os.environ["RAKSHA_SECRET"] = "direct-dashboard-secret"
        from backend.database import init_db
        from backend.main import app

        init_db()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        if self._old_dir is None:
            os.environ.pop("MEDILOCKER_DATA_DIR", None)
        else:
            os.environ["MEDILOCKER_DATA_DIR"] = self._old_dir
        if self._old_sec is None:
            os.environ.pop("RAKSHA_SECRET", None)
        else:
            os.environ["RAKSHA_SECRET"] = self._old_sec
        self._tmpdir.cleanup()

    def test_01_full_workflow_without_login_and_auth_endpoints_removed(self) -> None:
        # Obsolete auth endpoints must be gone
        self.assertEqual(self.client.get("/api/auth/config").status_code, 404)
        self.assertEqual(self.client.get("/api/auth/me").status_code, 404)

        # Dashboard and core workspace APIs work directly
        self.assertEqual(self.client.get("/api/health").status_code, 200)
        self.assertEqual(self.client.get("/api/dashboard/overview").status_code, 200)
        self.assertEqual(self.client.get("/api/dashboard/metrics-summary").status_code, 200)

        csv_bytes = b"patient_name,phone,diagnosis,medication\nKavita Nair,9823456712,Diabetes,Metformin 500 mg\n"
        up = self.client.post(
            "/api/datasets",
            data={"organisation_id": "org-hosp-a", "name": "Direct Workflow Batch", "auto_process": "true", "sync": "true"},
            files=[("files", ("ward.csv", io.BytesIO(csv_bytes), "text/csv"))],
        )
        self.assertEqual(up.status_code, 200, up.text)
        job_id = up.json()["job"]["id"]
        self.assertEqual(self.client.get(f"/api/jobs/{job_id}").status_code, 200)
        self.assertEqual(self.client.get(f"/api/jobs/{job_id}/results").status_code, 200)
        self.assertEqual(self.client.get("/api/reports/brief-pdf").status_code, 200)


if __name__ == "__main__":
    unittest.main()
