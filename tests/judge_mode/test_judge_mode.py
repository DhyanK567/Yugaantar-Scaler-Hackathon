"""Tests for Offline Judge Mode (MEDILOCKER_MODE=judge) and Organisation Mode."""
from __future__ import annotations

import gc
import io
import os
import sys
import tempfile
import time
import unittest
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


class JudgeAndOrganisationModeTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self._saved_env = {
            k: os.environ.get(k)
            for k in (
                "MEDILOCKER_DATA_DIR",
                "MEDILOCKER_MODE",
                "MEDILOCKER_ENV",
                "MEDILOCKER_OFFLINE_MODE",
                "RAKSHA_SECRET",
            )
        }
        os.environ["MEDILOCKER_DATA_DIR"] = self._tmpdir.name
        os.environ["RAKSHA_SECRET"] = "judge-mode-test-secret-2026"

        from backend.database import init_db
        from backend.main import app

        init_db()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()
        gc.collect()
        for k, v in self._saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self._tmpdir.cleanup()

    def test_01_judge_mode_full_workflow_without_login(self) -> None:
        os.environ["MEDILOCKER_MODE"] = "judge"
        os.environ["MEDILOCKER_ENV"] = "development"

        cfg = self.client.get("/api/auth/config")
        self.assertEqual(cfg.status_code, 200)
        self.assertEqual(cfg.json()["mode"], "judge")
        self.assertTrue(cfg.json()["judge_mode"])

        # Dashboard opens directly without login
        dash = self.client.get("/api/dashboard/overview")
        self.assertEqual(dash.status_code, 200, dash.text)

        # Upload synthetic dataset (valid CSV + quarantined PDF)
        csv_bytes = (
            "patient_id,name,age,diagnosis,medication,dosage\n"
            "P101,Rohan Verma,44,Hypertension,Amlodipine,5 mg\n"
            "P102,Meera Iyer,51,Type 2 Diabetes,Metformin,500 mg\n"
        ).encode("utf-8")
        up = self.client.post(
            "/api/datasets",
            data={"name": "Judge Mode Synthetic Batch", "auto_process": "true", "sync": "true"},
            files=[
                ("files", ("patients.csv", io.BytesIO(csv_bytes), "text/csv")),
                ("files", ("scan.pdf", io.BytesIO(b"%PDF-1.4\nfake"), "application/pdf")),
            ],
        )
        self.assertEqual(up.status_code, 200, up.text)
        job = up.json()["job"]
        job_id = job["id"]
        self.assertIn(job["status"], ("COMPLETED", "COMPLETED_WITH_WARNINGS"))
        self.assertEqual(job["files_quarantined"], 1)

        # Verify output files on disk
        from backend.main import JOBS_DIR

        out_dir = JOBS_DIR / job_id / "output"
        self.assertTrue((out_dir / "sanitized").is_dir())
        self.assertTrue((out_dir / "report.json").is_file())
        self.assertTrue((out_dir / "records.jsonl").is_file())

        # Verify results endpoints
        res = self.client.get(f"/api/jobs/{job_id}/results")
        self.assertEqual(res.status_code, 200)
        payload = res.json()
        self.assertIsNotNone(payload["privacy_assessment"])
        self.assertIsNotNone(payload["clinical_report"])
        self.assertIsNotNone(payload["identity_cluster"])
        self.assertIsNotNone(payload["passport"])

        # Download sanitized bundle (must NOT include records.jsonl)
        dl = self.client.get(f"/api/jobs/{job_id}/download")
        self.assertEqual(dl.status_code, 200)
        with zipfile.ZipFile(io.BytesIO(dl.content)) as zf:
            names = zf.namelist()
            self.assertIn("report.json", names)
            self.assertNotIn("records.jsonl", names)

        # Restricted mapping file must be blocked in Judge Mode
        mapping_res = self.client.get(f"/api/jobs/{job_id}/mapping")
        self.assertEqual(mapping_res.status_code, 403)

        # Privacy & Integrity PDF report works in Judge Mode
        pdf_res = self.client.get(f"/api/jobs/{job_id}/privacy-report.pdf")
        self.assertEqual(pdf_res.status_code, 200)
        self.assertTrue(pdf_res.content.startswith(b"%PDF-"))

    def test_02_production_cannot_bypass_auth_with_judge_mode(self) -> None:
        os.environ["MEDILOCKER_MODE"] = "judge"
        os.environ["MEDILOCKER_ENV"] = "production"

        cfg = self.client.get("/api/auth/config")
        self.assertEqual(cfg.status_code, 200)
        self.assertEqual(cfg.json()["mode"], "organisation")
        self.assertFalse(cfg.json()["judge_mode"])

        dash = self.client.get("/api/dashboard/overview")
        self.assertEqual(dash.status_code, 401)

    def test_03_organisation_mode_preserves_auth_and_isolation(self) -> None:
        os.environ["MEDILOCKER_MODE"] = "organisation"
        os.environ["MEDILOCKER_ENV"] = "development"

        cfg = self.client.get("/api/auth/config")
        self.assertEqual(cfg.status_code, 200)
        self.assertEqual(cfg.json()["mode"], "organisation")
        self.assertFalse(cfg.json()["judge_mode"])

        # Unauthenticated access rejected
        self.assertEqual(self.client.get("/api/dashboard/overview").status_code, 401)

        # Create org-a user session
        from backend.auth import ROLE_ORG_ADMIN, SESSION_COOKIE_NAME, create_session
        from backend.database import get_db

        with get_db() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO organisations (id, name, org_type, region, status, records_contributed, joined_at) VALUES ('org-a', 'Org A', 'Hospital', 'IN', 'Active', 0, ?)",
                (time.time(),),
            )
            conn.execute(
                "INSERT OR IGNORE INTO organisations (id, name, org_type, region, status, records_contributed, joined_at) VALUES ('org-b', 'Org B', 'Hospital', 'IN', 'Active', 0, ?)",
                (time.time(),),
            )
            conn.execute(
                "INSERT OR IGNORE INTO users (id, email, full_name, status, platform_role, created_at) VALUES ('u-a', 'a@org.local', 'User A', 'ACTIVE', 'USER', ?)",
                (time.time(),),
            )
            conn.execute(
                "INSERT OR IGNORE INTO memberships (id, user_id, organisation_id, role, created_at) VALUES ('m-a', 'u-a', 'org-a', ?, ?)",
                (ROLE_ORG_ADMIN, time.time()),
            )

        tok, _ = create_session(user_id="u-a", active_org_id="org-a")
        self.client.cookies.set(SESSION_COOKIE_NAME, tok)
        self.assertEqual(self.client.get("/api/dashboard/overview").status_code, 200)

        # Cross-org upload blocked with 403
        cross = self.client.post(
            "/api/datasets",
            data={"organisation_id": "org-b", "name": "Cross Org"},
            files=[("files", ("a.csv", io.BytesIO(b"a,b\n1,2\n"), "text/csv"))],
        )
        self.assertEqual(cross.status_code, 403)


if __name__ == "__main__":
    unittest.main()
