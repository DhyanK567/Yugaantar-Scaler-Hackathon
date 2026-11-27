"""M23 End-to-End Regression Suite: Judge Mode Stale-Cookie Isolation, Organisation RBAC & Edge Cases."""
from __future__ import annotations

import gc
import io
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


class M23RemediationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self._saved_env = {
            k: os.environ.get(k)
            for k in ("MEDILOCKER_DATA_DIR", "MEDILOCKER_MODE", "MEDILOCKER_ENV", "RAKSHA_SECRET")
        }
        os.environ["MEDILOCKER_DATA_DIR"] = self._tmpdir.name
        os.environ["RAKSHA_SECRET"] = "m23-test-secret-2026"

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

    def test_01_judge_mode_ignores_stale_researcher_cookie_and_uploads_cleanly(self) -> None:
        from backend.auth import ROLE_RESEARCHER, SESSION_COOKIE_NAME, create_session
        from backend.database import get_db

        # Seed a stale RESEARCHER session from an earlier Organisation Mode login
        now = time.time()
        with get_db() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO organisations (id, name, org_type, region, status, records_contributed, joined_at) VALUES ('org-legacy', 'Legacy Hospital', 'Hospital', 'IN', 'Active', 0, ?)",
                (now,),
            )
            conn.execute(
                "INSERT OR IGNORE INTO users (id, email, full_name, status, platform_role, created_at) VALUES ('u-res', 'res@legacy.org', 'Legacy Researcher', 'ACTIVE', 'USER', ?)",
                (now,),
            )
            conn.execute(
                "INSERT OR IGNORE INTO memberships (id, user_id, organisation_id, role, created_at) VALUES ('m-res', 'u-res', 'org-legacy', ?, ?)",
                (ROLE_RESEARCHER, now),
            )
        stale_tok, _ = create_session(user_id="u-res", active_org_id="org-legacy")
        self.client.cookies.set(SESSION_COOKIE_NAME, stale_tok)

        # Switch to Judge Mode: stale RESEARCHER cookie must NOT cause 403 Insufficient role permissions
        os.environ["MEDILOCKER_MODE"] = "judge"
        os.environ["MEDILOCKER_ENV"] = "development"

        me = self.client.get("/api/auth/me")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["user"]["full_name"], "Local Evaluator")
        self.assertEqual(me.json()["user"]["active_role"], "LOCAL_EVALUATOR")

        csv_data = (
            "patient_id,name,age,diagnosis,medication,dosage\n"
            "P1,रमेश कुमार,48,Diabetes,Metformin,500 mg\n"
        ).encode("utf-8")
        up = self.client.post(
            "/api/datasets",
            data={"organisation_id": "org-legacy", "name": "Judge Hindi Batch", "auto_process": "true", "sync": "true"},
            files=[("files", ("../../traversal_ward.csv", io.BytesIO(csv_data), "text/csv"))],
        )
        self.assertEqual(up.status_code, 200, up.text)
        body = up.json()
        job = body["job"]
        self.assertEqual(body.get("organisation_id") or job.get("organisation_id"), "org-judge-eval")
        self.assertIn(job["status"], ("COMPLETED", "COMPLETED_WITH_WARNINGS"))
        self.assertEqual(self.client.get(f"/api/jobs/{job['id']}/mapping").status_code, 403)

    def test_02_organisation_mode_enforces_researcher_upload_restriction(self) -> None:
        from backend.auth import ROLE_RESEARCHER, SESSION_COOKIE_NAME, create_session
        from backend.database import get_db

        os.environ["MEDILOCKER_MODE"] = "organisation"
        os.environ["MEDILOCKER_ENV"] = "development"
        now = time.time()
        with get_db() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO organisations (id, name, org_type, region, status, records_contributed, joined_at) VALUES ('org-x', 'Org X', 'Hospital', 'IN', 'Active', 0, ?)",
                (now,),
            )
            conn.execute(
                "INSERT OR IGNORE INTO users (id, email, full_name, status, platform_role, created_at) VALUES ('u-x', 'x@org.local', 'Researcher X', 'ACTIVE', 'USER', ?)",
                (now,),
            )
            conn.execute(
                "INSERT OR IGNORE INTO memberships (id, user_id, organisation_id, role, created_at) VALUES ('m-x', 'u-x', 'org-x', ?, ?)",
                (ROLE_RESEARCHER, now),
            )
        tok, _ = create_session(user_id="u-x", active_org_id="org-x")
        self.client.cookies.set(SESSION_COOKIE_NAME, tok)

        res = self.client.post(
            "/api/datasets",
            data={"organisation_id": "org-x", "name": "Blocked Upload"},
            files=[("files", ("test.csv", io.BytesIO(b"a,b\n1,2\n"), "text/csv"))],
        )
        self.assertEqual(res.status_code, 403)

    def test_03_edge_cases_empty_and_unsupported_files(self) -> None:
        os.environ["MEDILOCKER_MODE"] = "judge"
        os.environ["MEDILOCKER_ENV"] = "development"

        empty_res = self.client.post(
            "/api/datasets",
            data={"name": "Empty"},
            files=[("files", ("empty.csv", io.BytesIO(b""), "text/csv"))],
        )
        self.assertEqual(empty_res.status_code, 400)

        bad_ext = self.client.post(
            "/api/datasets",
            data={"name": "Executable"},
            files=[("files", ("malware.exe", io.BytesIO(b"MZ"), "application/octet-stream"))],
        )
        self.assertEqual(bad_ext.status_code, 400)


if __name__ == "__main__":
    unittest.main()
