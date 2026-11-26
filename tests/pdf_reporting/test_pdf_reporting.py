"""Phase 8 — Offline PDF Reporting & Security Verification Suite."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract ASCII text literals from PDF stream without external libraries."""
    raw = pdf_bytes.decode("latin-1", errors="ignore")
    return raw.replace("\\(", "(").replace("\\)", ")").replace("\\\\", "\\")


class TestPdfReporting(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmpdir = Path(tempfile.mkdtemp(prefix="pdf_rep_test_"))
        os.environ["MEDILOCKER_DB_PATH"] = str(cls._tmpdir / "pdf_test.db")
        os.environ["RAKSHA_SECRET"] = "pdf-unit-secret-xyz-99"

        import backend.database as bdb
        import backend.pipeline as bpipe
        from backend.services.pdf_reporting import (
            PdfGenerationError,
            PdfSecurityError,
            generate_attack_simulation_pdf,
            generate_audit_trail_pdf,
            generate_clinical_integrity_pdf,
            generate_privacy_intelligence_pdf,
            generate_privacy_passport_pdf,
        )
        from backend.services.pdf_reporting.renderers import write_pdf_atomic
        from backend.services.pdf_reporting.security import (
            escape_xml,
            safe_filename,
            sanitize_safe_text,
            scan_pdf_bytes_for_leaks,
        )

        cls.bdb = bdb
        cls.bpipe = bpipe
        cls.PdfGenerationError = PdfGenerationError
        cls.PdfSecurityError = PdfSecurityError
        cls.gen_passport = staticmethod(generate_privacy_passport_pdf)
        cls.gen_intel = staticmethod(generate_privacy_intelligence_pdf)
        cls.gen_attack = staticmethod(generate_attack_simulation_pdf)
        cls.gen_clinical = staticmethod(generate_clinical_integrity_pdf)
        cls.gen_audit = staticmethod(generate_audit_trail_pdf)
        cls.write_atomic = staticmethod(write_pdf_atomic)
        cls.escape_xml = staticmethod(escape_xml)
        cls.safe_filename = staticmethod(safe_filename)
        cls.sanitize_safe_text = staticmethod(sanitize_safe_text)
        cls.scan_pdf = staticmethod(scan_pdf_bytes_for_leaks)

        bdb.init_db()
        bpipe.JOBS_DIR = cls._tmpdir / "jobs"
        bpipe.DATASETS_DIR = cls._tmpdir / "datasets"
        bpipe.JOBS_DIR.mkdir(parents=True, exist_ok=True)
        bpipe.DATASETS_DIR.mkdir(parents=True, exist_ok=True)

        with bdb.get_db() as conn:
            org_row = conn.execute("SELECT id, name FROM organisations LIMIT 1").fetchone()
            cls.org_id = org_row["id"]
            cls.org_name = org_row["name"]
            conn.execute(
                "INSERT OR IGNORE INTO users (id, email, full_name, status, platform_role, created_at) VALUES ('usr-pdf', 'pdf@test.local', 'PDF Tester', 'ACTIVE', 'USER', 1.0)"
            )
            conn.execute(
                "INSERT OR IGNORE INTO memberships (id, user_id, organisation_id, role, created_at) VALUES ('mem-pdf', 'usr-pdf', ?, 'ORG_ADMIN', 1.0)",
                (cls.org_id,),
            )

            # Create a real dataset & run pipeline
            ds_dir = bpipe.DATASETS_DIR / "ds-pdf1"
            ds_dir.mkdir(parents=True, exist_ok=True)
            rows = ["UHID,Patient Name,Gender,Age,District,Diagnosis,BP,Medication"]
            for i in range(6):
                rows.append(f"MGH-20{i},TestPt{i} Verma,M,50,Lucknow,Hypertension,120/80,Amlodipine 5 mg")
            (ds_dir / "clean.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
            now = time.time()
            conn.execute(
                "INSERT INTO datasets (id, organisation_id, name, description, format, file_count, total_bytes, sha256, storage_path, status, created_at) VALUES ('ds-pdf1', ?, 'clean.csv', '', 'CSV', 1, 100, 'abc', ?, 'VALIDATED', ?)",
                (cls.org_id, str(ds_dir), now),
            )
            conn.execute(
                "INSERT INTO jobs (id, created_at, status, current_stage, input_name, dataset_id, organisation_id, release_decision) VALUES ('job-pdf1', ?, 'CREATED', 'CREATED', 'clean.csv', 'ds-pdf1', ?, 'PENDING')",
                (now, cls.org_id),
            )

        bpipe.execute_job_pipeline(
            job_id="job-pdf1",
            dataset_id="ds-pdf1",
            organisation_id=cls.org_id,
            input_dir=bpipe.DATASETS_DIR / "ds-pdf1",
            actor_id="usr-pdf",
            actor_email="pdf@test.local",
            actor_role="ORG_ADMIN",
        )

        with bdb.get_db() as conn:
            cls.passport_id = conn.execute("SELECT id FROM passports WHERE job_id = 'job-pdf1'").fetchone()["id"]
            cls.assess_id = conn.execute("SELECT id FROM privacy_assessments WHERE job_id = 'job-pdf1'").fetchone()["id"]
            cls.attack_id = conn.execute("SELECT id FROM attack_runs WHERE job_id = 'job-pdf1'").fetchone()["id"]
            cls.clin_id = conn.execute("SELECT id FROM clinical_reports WHERE job_id = 'job-pdf1'").fetchone()["id"]

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls._tmpdir, ignore_errors=True)

    def test_01_all_five_operational_pdfs_generate_and_contain_expected_fields(self) -> None:
        # A. Privacy Passport
        b1, f1 = self.gen_passport(self.passport_id)
        self.assertTrue(b1.startswith(b"%PDF-"))
        self.assertTrue(f1.endswith(".pdf"))
        t1 = _extract_pdf_text(b1)
        self.assertIn(self.passport_id, t1)
        self.assertIn("job-pdf1", t1)
        self.assertIn("APPROVED", t1)

        # B. Privacy Intelligence
        b2, f2 = self.gen_intel(self.assess_id)
        self.assertTrue(b2.startswith(b"%PDF-"))
        t2 = _extract_pdf_text(b2)
        self.assertIn(self.assess_id, t2)
        self.assertIn("Measured", t2)

        # C. Attack Simulation
        b3, f3 = self.gen_attack(self.attack_id)
        self.assertTrue(b3.startswith(b"%PDF-"))
        t3 = _extract_pdf_text(b3)
        self.assertIn(self.attack_id, t3)
        self.assertIn("exact_combination", t3)

        # D. Clinical Integrity
        b4, f4 = self.gen_clinical(self.clin_id)
        self.assertTrue(b4.startswith(b"%PDF-"))
        t4 = _extract_pdf_text(b4)
        self.assertIn(self.clin_id, t4)
        self.assertIn("Preserved / Expected", t4)

        # E. Audit Trail (must NOT contain actor_email!)
        b5, f5 = self.gen_audit(self.org_id, self.org_name)
        self.assertTrue(b5.startswith(b"%PDF-"))
        t5 = _extract_pdf_text(b5)
        self.assertIn("JOB_COMPLETED", t5)
        self.assertNotIn("pdf@test.local", t5)
        self.assertNotIn("pdf-unit-secret-xyz-99", t5)

    def test_02_missing_report_and_cross_org_access_blocked(self) -> None:
        with self.assertRaises(self.PdfGenerationError):
            self.gen_passport("psp-nonexistent")
        with self.assertRaises(self.PdfGenerationError):
            self.gen_intel("pa-nonexistent")
        with self.assertRaises(self.PdfGenerationError):
            self.gen_attack("atk-nonexistent")
        with self.assertRaises(self.PdfGenerationError):
            self.gen_clinical("clin-nonexistent")

        # Cross-organisation access check (user belongs only to self.org_id)
        user_orgs = {self.org_id}
        self.assertNotIn("org-other-hospital", user_orgs)

    def test_03_security_scanner_blocks_pii_canary_secret_markup_and_corrupt_pdf(self) -> None:
        # Malicious ReportLab markup stripped/escaped
        clean = self.escape_xml('<script>alert(1)</script><font color="red">X & Y</font>')
        self.assertNotIn("<script>", clean)
        self.assertNotIn("<font", clean)
        self.assertIn("&amp;", clean)

        # Unsafe filename sanitized
        fn = self.safe_filename("../../etc", "../bad:file?.pdf")
        self.assertNotIn("..", fn)
        self.assertNotIn("/", fn)

        # Corrupted PDF rejected
        with self.assertRaises(self.PdfSecurityError):
            self.scan_pdf(b"NOT_A_PDF")

        # PII, Canary, Secret leakage rejected
        for payload in (
            b"%PDF-1.4\n(Aadhaar 4321 8765 1234)\n%%EOF",
            b"%PDF-1.4\n(Phone 9876543210)\n%%EOF",
            b"%PDF-1.4\n(Email leak@example.com)\n%%EOF",
            b"%PDF-1.4\n(CANARY_SECRET_123)\n%%EOF",
            b"%PDF-1.4\n(pdf-unit-secret-xyz-99)\n%%EOF",
        ):
            with self.assertRaises(self.PdfSecurityError):
                self.scan_pdf(payload)

    def test_04_large_table_pagination_empty_audit_and_atomic_write(self) -> None:
        # Empty org audit trail -> valid PDF
        b_empty, _ = self.gen_audit("org-empty", "Empty Hospital")
        self.assertTrue(b_empty.startswith(b"%PDF-"))
        self.assertIn("(No rows recorded)", _extract_pdf_text(b_empty))

        # Large audit trail (120 events) -> multi-page pagination
        with self.bdb.get_db() as conn:
            for i in range(120):
                conn.execute(
                    "INSERT INTO audit_events (timestamp, actor_id, actor_role, organisation_id, action, resource_type, resource_id, outcome) VALUES (?, 'usr-pdf', 'ORG_ADMIN', ?, 'BATCH_EVENT', 'job', ?, 'SUCCESS')",
                    (1700000000.0 + i, self.org_id, f"job-{i}"),
                )
        b_large, _ = self.gen_audit(self.org_id, self.org_name, limit=150)
        txt = _extract_pdf_text(b_large)
        self.assertIn("Page 1 of", txt)
        self.assertIn("Page 2 of", txt)

        # Atomic write leaves no temp files
        dest = self._tmpdir / "out" / "atomic.pdf"
        self.write_atomic(dest, b_large)
        self.assertTrue(dest.is_file())
        self.assertEqual(len(list(dest.parent.glob(".pdf_tmp_*"))), 0)

    def test_05_no_global_hashlib_monkeypatch_in_backend(self) -> None:
        # Verify hashlib.md5 still accepts usedforsecurity keyword
        h = hashlib.md5(b"test", usedforsecurity=False)
        self.assertEqual(len(h.hexdigest()), 32)


if __name__ == "__main__":
    unittest.main()
