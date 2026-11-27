"""MediLocker Dataset Processing End-to-End & Failure-Scenario Verification Suite.

Runs with Python standard library only (no FastAPI server required) by exercising
backend.database, backend.pipeline, backend.engine_adapter, and starter/main.py directly.
"""
from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TestDatasetWorkflowE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmpdir = Path(tempfile.mkdtemp(prefix="medilocker_e2e_"))
        os.environ["MEDILOCKER_DB_PATH"] = str(cls._tmpdir / "test_medilocker.db")

        import backend.database as bdb
        import backend.pipeline as bpipe

        bdb.init_db()
        cls.bdb = bdb
        cls.bpipe = bpipe
        cls.bpipe.JOBS_DIR = cls._tmpdir / "jobs"
        cls.bpipe.DATASETS_DIR = cls._tmpdir / "datasets"
        cls.bpipe.JOBS_DIR.mkdir(parents=True, exist_ok=True)
        cls.bpipe.DATASETS_DIR.mkdir(parents=True, exist_ok=True)

        with bdb.get_db() as conn:
            row = conn.execute("SELECT id FROM organisations LIMIT 1").fetchone()
            if row:
                cls.org_id = row["id"]
            else:
                cls.org_id = "org-metro"
                conn.execute(
                    "INSERT INTO organisations (id, name, org_type, joined_at) VALUES (?, 'Metro General Hospital', 'Hospital', 1.0)",
                    (cls.org_id,),
                )

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls._tmpdir, ignore_errors=True)

    def _create_ds_and_job(self, name: str, files: dict[str, bytes]) -> tuple[str, str, Path]:
        import secrets
        import time

        ds_id = f"ds-{secrets.token_hex(4)}"
        job_id = f"job-{secrets.token_hex(4)}"
        ds_dir = self.bpipe.DATASETS_DIR / ds_id
        ds_dir.mkdir(parents=True, exist_ok=True)
        for fname, content in files.items():
            (ds_dir / fname).write_bytes(content)

        now = time.time()
        with self.bdb.get_db() as conn:
            conn.execute(
                "INSERT INTO datasets (id, organisation_id, name, description, format, file_count, total_bytes, sha256, storage_path, status, created_at) VALUES (?, ?, ?, '', 'CSV', ?, 100, 'abc', ?, 'VALIDATED', ?)",
                (ds_id, self.org_id, name, len(files), str(ds_dir), now),
            )
            conn.execute(
                "INSERT INTO jobs (id, created_at, status, current_stage, input_name, dataset_id, organisation_id, release_decision) VALUES (?, ?, 'CREATED', 'CREATED', ?, ?, ?, 'PENDING')",
                (job_id, now, name, ds_id, self.org_id),
            )
        return ds_id, job_id, ds_dir

    def _get_job(self, job_id: str) -> dict:
        with self.bdb.get_db() as conn:
            return dict(conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone())

    def test_01_clean_dataset_e2e_approved_and_validated(self) -> None:
        rows = ["UHID,Patient Name,Gender,Age,District,Diagnosis,BP,Medication"]
        for i in range(6):
            rows.append(f"MGH-10{i},Patient{i} Kumar,M,45,Lucknow,Hypertension,120/80,Amlodipine 5 mg")
        ds_id, job_id, ds_dir = self._create_ds_and_job(
            "clean_batch.csv", {"clean_batch.csv": ("\n".join(rows) + "\n").encode("utf-8")}
        )
        self.bpipe.execute_job_pipeline(
            job_id=job_id,
            dataset_id=ds_id,
            organisation_id=self.org_id,
            input_dir=ds_dir,
            actor_id="usr-test",
            actor_email="test@medilocker.local",
            actor_role="ORG_ADMIN",
        )
        job = self._get_job(job_id)
        self.assertEqual(job["status"], "COMPLETED")
        self.assertEqual(job["release_decision"], "APPROVED")

        out_dir = self.bpipe.JOBS_DIR / job_id / "output"
        v = subprocess.run(
            [sys.executable, str(ROOT / "validate_output.py"), "--input", str(ds_dir), "--output", str(out_dir)],
            capture_output=True, text=True, timeout=60,
        )
        self.assertIn("CONTRACT OK", v.stdout)
        san_txt = (out_dir / "sanitized" / "clean_batch.csv").read_text(encoding="utf-8")
        self.assertNotIn("Patient0 Kumar", san_txt)
        self.assertIn("Hypertension", san_txt)
        self.assertIn("Amlodipine 5 mg", san_txt)

        with self.bdb.get_db() as conn:
            aud = conn.execute("SELECT action, outcome FROM audit_events WHERE resource_id = ?", (job_id,)).fetchall()
            self.assertTrue(any(a["action"] == "JOB_COMPLETED" and a["outcome"] == "COMPLETED" for a in aud))

    def test_02_canary_leak_in_content_base64_or_report_blocks_release(self) -> None:
        canary_csv = (
            "UHID,Patient Name,Notes\n"
            "MGH-901,Ramesh Verma,Note with CANARY_TOKEN_9911 embedded\n"
        ).encode("utf-8")
        ds_id, job_id, ds_dir = self._create_ds_and_job("note_canary.csv", {"note_canary.csv": canary_csv})
        self.bpipe.execute_job_pipeline(
            job_id=job_id,
            dataset_id=ds_id,
            organisation_id=self.org_id,
            input_dir=ds_dir,
            actor_id="usr-test",
            actor_email="test@medilocker.local",
            actor_role="ORG_ADMIN",
        )
        job = self._get_job(job_id)
        self.assertEqual(job["status"], "BLOCKED")
        self.assertEqual(job["release_decision"], "BLOCKED")

        # Also test base64-encoded canary detection in _scan_canaries
        b64_tok = base64.b64encode(b"Secret CANARY_B64_7722 payload").decode("ascii")
        b64_in = self._tmpdir / "b64_in"
        b64_out = self._tmpdir / "b64_out"
        b64_in.mkdir()
        b64_out.mkdir()
        (b64_in / "c.txt").write_text("CANARY_B64_7722", encoding="utf-8")
        (b64_out / "c.txt").write_text(b64_tok, encoding="utf-8")
        scan = self.bpipe._scan_canaries(b64_in, b64_out)
        self.assertEqual(scan["status"], "FAILED")
        self.assertEqual(scan["leaks"], 1)

    def test_03_empty_unsupported_and_corrupt_files_never_approved(self) -> None:
        # Empty directory -> FAILED + BLOCKED
        ds_id, job_id, ds_dir = self._create_ds_and_job("empty_ds", {})
        self.bpipe.execute_job_pipeline(
            job_id=job_id, dataset_id=ds_id, organisation_id=self.org_id,
            input_dir=ds_dir, actor_id="usr-test", actor_email="u@x", actor_role="ORG_ADMIN",
        )
        job = self._get_job(job_id)
        self.assertEqual(job["status"], "FAILED")
        self.assertEqual(job["release_decision"], "BLOCKED")

        # Unsupported PNG + corrupt JSON -> QUARANTINED (never APPROVED, zero raw copies)
        ds_id2, job_id2, ds_dir2 = self._create_ds_and_job(
            "bad_batch", {"scan.png": b"\x89PNG\r\n\x1a\n", "broken.json": b"{bad"}
        )
        self.bpipe.execute_job_pipeline(
            job_id=job_id2, dataset_id=ds_id2, organisation_id=self.org_id,
            input_dir=ds_dir2, actor_id="usr-test", actor_email="u@x", actor_role="ORG_ADMIN",
        )
        job2 = self._get_job(job_id2)
        self.assertEqual(job2["status"], "QUARANTINED")
        self.assertEqual(job2["release_decision"], "QUARANTINED")
        out2 = self.bpipe.JOBS_DIR / job_id2 / "output" / "sanitized"
        self.assertFalse((out2 / "scan.png").exists())
        self.assertFalse((out2 / "broken.json").exists())

    def test_04_critical_risk_fhir_failure_and_incomplete_artifacts_block_release(self) -> None:
        ds_id, job_id, ds_dir = self._create_ds_and_job(
            "crit.csv", {"crit.csv": b"UHID,Patient Name,Age\nMGH-1,Geeta Devi,91\n"}
        )
        with patch.object(
            self.bpipe,
            "execute_engine",
            return_value={
                "success": True,
                "return_code": 0,
                "duration_secs": 0.1,
                "stdout": "",
                "stderr": "",
                "files_total": 1,
                "files_sanitized": 1,
                "files_quarantined": 0,
                "records_processed": 1,
                "records_linked": 1,
                "identifiers_detected": 2,
                "records_generalized": 1,
                "records_suppressed": 0,
                "files_report": [],
                "privacy_intelligence": {
                    "risk_summary": {"post_categories": {"CRITICAL": 1, "HIGH": 0, "MODERATE": 0, "LOW": 0}},
                    "release_gate": {"status": "BLOCKED"},
                },
                "clinical_integrity": {"fhir_validation_passed": False},
            },
        ):
            self.bpipe.execute_job_pipeline(
                job_id=job_id, dataset_id=ds_id, organisation_id=self.org_id,
                input_dir=ds_dir, actor_id="usr-test", actor_email="u@x", actor_role="ORG_ADMIN",
            )
            job = self._get_job(job_id)
            self.assertEqual(job["status"], "BLOCKED")
            self.assertEqual(job["release_decision"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
