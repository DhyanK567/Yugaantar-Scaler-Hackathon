#!/usr/bin/env python3
"""Direct-Access Workspace E2E Tests (No Login, Path Traversal Guard, Mapping Restriction)."""
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


class DirectWorkspaceE2ETests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self._old_env = {k: os.environ.get(k) for k in ("MEDILOCKER_DATA_DIR", "RAKSHA_SECRET")}
        os.environ["MEDILOCKER_DATA_DIR"] = self._tmpdir.name
        os.environ["RAKSHA_SECRET"] = "m23-direct-workspace-secret"
        from backend.database import init_db
        from backend.main import app

        init_db()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        for k, v in self._old_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self._tmpdir.cleanup()

    def test_01_direct_upload_and_processing_without_login(self) -> None:
        csv_data = (
            "patient_id,name,age,diagnosis,medication,dosage\n"
            "P1,रमेश कुमार,48,Diabetes,Metformin,500 mg\n"
        ).encode("utf-8")
        up = self.client.post(
            "/api/datasets",
            data={"organisation_id": "org-hosp-a", "name": "Direct Hindi Batch", "auto_process": "true", "sync": "true"},
            files=[("files", ("../../traversal_ward.csv", io.BytesIO(csv_data), "text/csv"))],
        )
        self.assertEqual(up.status_code, 200, up.text)
        job = up.json()["job"]
        self.assertIn(job["status"], ("COMPLETED", "COMPLETED_WITH_WARNINGS"))
        self.assertEqual(self.client.get(f"/api/jobs/{job['id']}/mapping").status_code, 403)
        self.assertEqual(self.client.get("/api/dashboard/overview").status_code, 200)
        self.assertEqual(self.client.get("/api/audit/events").status_code, 200)
        self.assertEqual(self.client.get("/api/settings").status_code, 200)


if __name__ == "__main__":
    unittest.main()
