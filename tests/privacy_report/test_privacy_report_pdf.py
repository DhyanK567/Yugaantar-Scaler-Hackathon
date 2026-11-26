"""Automated tests for MediLocker Healthcare Data Privacy & Integrity Report PDF."""
from __future__ import annotations

import base64
import gc
import io
import json
import os
import re
import sys
import tempfile
import time
import unittest
import zlib
from pathlib import Path

from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _extract_pdf_text_and_pages(pdf_bytes: bytes) -> tuple[int, str]:
    """Extract page count and readable text (including TTF ToUnicode CMaps) from PDF bytes."""
    pages = pdf_bytes.count(b"/Type /Page") - pdf_bytes.count(b"/Type /Pages")

    # Map object id -> decompressed stream text
    obj_streams: dict[int, str] = {}
    for om in re.finditer(rb"(\d+)\s+0\s+obj\b(.*?)endobj", pdf_bytes, re.DOTALL):
        obj_id = int(om.group(1))
        body = om.group(2)
        sm = re.search(rb"\bstream\r?\n(.*?)endstream", body, re.DOTALL)
        if not sm:
            continue
        candidate = sm.group(1).strip()
        if b"~>" in candidate:
            try:
                candidate = base64.a85decode(
                    candidate.split(b"~>")[0],
                    adobe=False,
                    ignorechars=b" \t\n\r\x0b\x0c",
                )
            except Exception:
                pass
        try:
            dec = zlib.decompress(candidate)
        except Exception:
            dec = candidate
        obj_streams[obj_id] = dec.decode("latin-1", errors="ignore")

    # Map /Fxx -> ToUnicode CMap dict
    font_cmaps: dict[str, dict[str, str]] = {}
    pdf_latin = pdf_bytes.decode("latin-1", errors="ignore")
    for fm in re.finditer(r"/(F\d+(?:\+\d+)?)\s+(\d+)\s+0\s+R", pdf_latin):
        fname, fobj_id = fm.group(1), int(fm.group(2))
        fobj_m = re.search(rf"\b{fobj_id}\s+0\s+obj\b(.*?)endobj", pdf_latin, re.DOTALL)
        if not fobj_m:
            continue
        tum = re.search(r"/ToUnicode\s+(\d+)\s+0\s+R", fobj_m.group(1))
        if not tum:
            continue
        cmap_txt = obj_streams.get(int(tum.group(1)), "")
        if "begincmap" not in cmap_txt:
            continue
        cmap: dict[str, str] = {}
        for bm in re.finditer(r"beginbfchar\s*(.*?)\s*endbfchar", cmap_txt, re.DOTALL):
            for pair in re.finditer(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", bm.group(1)):
                try:
                    cmap[pair.group(1).upper()] = bytes.fromhex(pair.group(2)).decode("utf-16-be", errors="ignore")
                except Exception:
                    pass
        for rm in re.finditer(r"beginbfrange\s*(.*?)\s*endbfrange", cmap_txt, re.DOTALL):
            for rng in re.finditer(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", rm.group(1)):
                start_g, end_g, start_u = int(rng.group(1), 16), int(rng.group(2), 16), int(rng.group(3), 16)
                width = len(rng.group(1))
                for offset in range(end_g - start_g + 1):
                    cmap[f"{start_g + offset:0{width}X}"] = chr(start_u + offset)
        font_cmaps[fname] = cmap

    text_parts: list[str] = []
    for s in obj_streams.values():
        if "begincmap" in s or "Tf" not in s:
            continue
        cur_font = ""
        for line in s.splitlines():
            tfm = re.search(r"/(F\d+(?:\+\d+)?)\s+[\d.]+\s+Tf", line)
            if tfm:
                cur_font = tfm.group(1)
            cmap = font_cmaps.get(cur_font, {})
            for lit in re.finditer(r"\(([^()\\]*(?:\\.[^()\\]*)*)\)", line):
                raw_s = lit.group(1).replace(r"\(", "(").replace(r"\)", ")").replace(r"\\", "\\")
                if cmap:
                    decoded = "".join(cmap.get(f"{ord(ch):02X}", cmap.get(f"{ord(ch):04X}", ch)) for ch in raw_s)
                    text_parts.append(decoded)
                else:
                    text_parts.append(raw_s)
            for hx in re.finditer(r"<([0-9A-Fa-f]{2,})>", line):
                h = hx.group(1).upper()
                step = 4 if any(len(k) == 4 for k in cmap) else 2
                decoded = "".join(cmap.get(h[i : i + step], "") for i in range(0, len(h), step))
                if decoded:
                    text_parts.append(decoded)

    text_parts.append(pdf_bytes[:2048].decode("latin-1", errors="ignore"))
    text_parts.append(pdf_bytes[-2048:].decode("latin-1", errors="ignore"))
    return pages, "\n".join(text_parts)


class PrivacyReportPdfTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self._old_data_dir = os.environ.get("MEDILOCKER_DATA_DIR")
        self._old_secret = os.environ.get("RAKSHA_SECRET")
        self._old_dev_login = os.environ.get("MEDILOCKER_DEV_EMAIL_LOGIN")
        os.environ["MEDILOCKER_DATA_DIR"] = self._tmpdir.name
        os.environ["RAKSHA_SECRET"] = "audit-test-secret-key-2026"
        os.environ["MEDILOCKER_DEV_EMAIL_LOGIN"] = "true"

        from backend.database import init_db
        from backend.main import app

        init_db()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()
        gc.collect()
        if self._old_data_dir is None:
            os.environ.pop("MEDILOCKER_DATA_DIR", None)
        else:
            os.environ["MEDILOCKER_DATA_DIR"] = self._old_data_dir
        if self._old_secret is None:
            os.environ.pop("RAKSHA_SECRET", None)
        else:
            os.environ["RAKSHA_SECRET"] = self._old_secret
        if self._old_dev_login is None:
            os.environ.pop("MEDILOCKER_DEV_EMAIL_LOGIN", None)
        else:
            os.environ["MEDILOCKER_DEV_EMAIL_LOGIN"] = self._old_dev_login
        self._tmpdir.cleanup()

    def _login_user(self, email: str, org_id: str, role: str = "ORG_ADMIN") -> None:
        from backend.auth import SESSION_COOKIE_NAME, create_session
        from backend.database import get_db

        uid = f"usr-{email.split('@')[0]}"
        with get_db() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO organisations (id, name, org_type, region, status, records_contributed, joined_at) VALUES (?, ?, ?, ?, 'Active', 0, ?)",
                (org_id, f"Org {org_id}", "Hospital", "India", time.time()),
            )
            conn.execute(
                "INSERT OR IGNORE INTO users (id, email, full_name, status, platform_role, created_at) VALUES (?, ?, ?, 'ACTIVE', 'USER', ?)",
                (uid, email, "Audit Tester", time.time()),
            )
            conn.execute(
                "INSERT OR IGNORE INTO memberships (id, user_id, organisation_id, role, created_at) VALUES (?, ?, ?, ?, ?)",
                (f"mem-{uid}-{org_id}", uid, org_id, role, time.time()),
            )

        token, _ = create_session(user_id=uid, active_org_id=org_id)
        self.client.cookies.set(SESSION_COOKIE_NAME, token)

    def _upload_sample_job(self, org_id: str = "org-city-general") -> str:
        sample_csv = (
            "patient_id,name,age,diagnosis,medication,dosage\n"
            "P001,Aarav Sharma,45,Type 2 Diabetes,Metformin,500 mg\n"
            "P002,Priya Nair,52,Hypertension,Amlodipine,5 mg\n"
        ).encode("utf-8")
        res = self.client.post(
            "/api/datasets",
            data={"organisation_id": org_id, "name": "Synthetic Ward Sample", "auto_process": "true", "sync": "true"},
            files=[("files", ("ward_sample.csv", io.BytesIO(sample_csv), "text/csv"))],
        )
        self.assertEqual(res.status_code, 200, res.text)
        return res.json()["job"]["id"]

    def test_01_successful_report_generation_and_consistency(self) -> None:
        self._login_user("auditor@medilocker.local", "org-city-general")
        job_id = self._upload_sample_job("org-city-general")

        results_res = self.client.get(f"/api/jobs/{job_id}/results")
        self.assertEqual(results_res.status_code, 200)
        results = results_res.json()

        pdf_res = self.client.get(f"/api/jobs/{job_id}/privacy-report.pdf")
        self.assertEqual(pdf_res.status_code, 200)
        self.assertEqual(pdf_res.headers.get("content-type"), "application/pdf")
        self.assertTrue(pdf_res.content.startswith(b"%PDF-"))

        pages, raw_text = _extract_pdf_text_and_pages(pdf_res.content)
        self.assertEqual(pages, 3)
        self.assertIn("Protecting identity.", raw_text)
        self.assertIn("Preserving clinical truth.", raw_text)
        self.assertIn(job_id, raw_text)
        self.assertIn(results["passport"]["id"], raw_text)
        self.assertNotIn(b"audit-test-secret-key-2026", pdf_res.content)

    def test_02_missing_assessment_data_and_review_required(self) -> None:
        from backend.privacy_report_pdf import generate_privacy_integrity_pdf

        pdf_bytes = generate_privacy_integrity_pdf(
            job={"id": "job-incomplete-1", "status": "PROCESSING", "created_at": time.time()},
            dataset={"id": "ds-1", "name": "Pending Dataset", "format": "CSV"},
            organisation={"id": "org-1", "name": "Synthetic Clinic"},
            privacy=None,
            clinical=None,
            identity=None,
            attack_run=None,
            passport=None,
        )
        pages, raw_text = _extract_pdf_text_and_pages(pdf_bytes)
        self.assertEqual(pages, 3)
        self.assertIn("Not measured", raw_text)
        self.assertIn("REVIEW REQUIRED", raw_text)

    def test_03_failed_clinical_and_blocked_decision(self) -> None:
        from backend.privacy_report_pdf import generate_privacy_integrity_pdf

        pdf_bytes = generate_privacy_integrity_pdf(
            job={"id": "job-blocked-1", "status": "BLOCKED", "release_decision": "BLOCKED", "created_at": time.time()},
            dataset={"id": "ds-2", "name": "Drift Dataset", "format": "CSV"},
            organisation={"id": "org-1", "name": "Synthetic Clinic"},
            privacy={"pii_detected": 5, "residual_leakage": 0, "canary_planted": 1, "canary_leaks": 0, "canary_status": "PASS", "reid_risk_level": "LOW"},
            clinical={"expected_values": 10, "preserved_values": 9, "missing_values": 0, "modified_values": 1, "fhir_integrity": "FAILED"},
            identity={"precision": 1.0, "recall": 0.9, "f05": 0.97, "total_patients": 4, "cross_hospital_links": 1, "false_merges": 0, "abstentions": 0},
            attack_run={"profile": "standard-7-vector", "blocked_count": 7, "total_count": 7, "risk_score": 0.0},
            passport={"id": "psp-1", "manifest_hash": "a" * 64, "signature_status": "UNSIGNED"},
        )
        pages, raw_text = _extract_pdf_text_and_pages(pdf_bytes)
        self.assertEqual(pages, 3)
        self.assertIn("BLOCKED", raw_text)
        self.assertIn("Drift detected", raw_text)
        self.assertIn("UNSIGNED", raw_text)

    def test_04_tampered_passport_detection(self) -> None:
        from backend.main import JOBS_DIR

        self._login_user("auditor@medilocker.local", "org-city-general")
        job_id = self._upload_sample_job("org-city-general")

        san_dir = JOBS_DIR / job_id / "output" / "sanitized"
        first_file = next(p for p in san_dir.rglob("*") if p.is_file())
        first_file.write_text("TAMPERED_CONTENT", encoding="utf-8")

        pdf_res = self.client.get(f"/api/jobs/{job_id}/privacy-report.pdf")
        self.assertEqual(pdf_res.status_code, 200)
        _, raw_text = _extract_pdf_text_and_pages(pdf_res.content)
        self.assertIn("TAMPERING DETECTED", raw_text)

    def test_05_unicode_hindi_quarantine_and_pii_redaction(self) -> None:
        from backend.privacy_report_pdf import generate_privacy_integrity_pdf

        pdf_bytes = generate_privacy_integrity_pdf(
            job={
                "id": "job-unicode-1",
                "status": "COMPLETED_WITH_WARNINGS",
                "release_decision": "APPROVED_WITH_WARNINGS",
                "files_quarantined": 2,
                "files_sanitized": 8,
                "records_processed": 120,
                "duration_secs": 1.42,
                "created_at": time.time(),
            },
            dataset={
                "id": "ds-uni",
                "name": "आरोग्य अस्पताल & Research <Ward> 9876543210 test@example.com",
                "format": "CSV, JSON",
            },
            organisation={"id": "org-hi", "name": "सिटी हॉस्पिटल (Synthetic)"},
            privacy={"pii_detected": 40, "residual_leakage": 0, "canary_planted": 2, "canary_leaks": 0, "canary_status": "PASS", "reid_risk_level": "LOW"},
            clinical={
                "expected_values": 50,
                "preserved_values": 50,
                "missing_values": 0,
                "modified_values": 0,
                "fhir_integrity": "PASS",
                "details_json": json.dumps({"categories": {"medication_names": {"expected": 20, "preserved": 20, "modified": 0}}}),
            },
            identity={"precision": 1.0, "recall": 0.85, "f05": 0.96, "total_patients": 30, "cross_hospital_links": 12, "false_merges": 0, "abstentions": 1},
            attack_run={"profile": "standard-7-vector", "blocked_count": 7, "total_count": 7, "risk_score": 0.0},
            passport={"id": "psp-uni", "manifest_hash": "b" * 64, "signature_status": "UNSIGNED"},
        )
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))
        _, raw_text = _extract_pdf_text_and_pages(pdf_bytes)
        self.assertNotIn("9876543210", raw_text)
        self.assertNotIn("test@example.com", raw_text)
        self.assertIn("[REDACTED_PHONE]", raw_text)
        self.assertIn("[REDACTED_EMAIL]", raw_text)

    def test_06_org_isolation_and_auth_enforcement(self) -> None:
        self._login_user("org1@medilocker.local", "org-one")
        job_id = self._upload_sample_job("org-one")

        self.client.cookies.clear()
        unauth = self.client.get(f"/api/jobs/{job_id}/privacy-report.pdf")
        self.assertEqual(unauth.status_code, 401)

        self._login_user("org2@medilocker.local", "org-two")
        cross_org = self.client.get(f"/api/jobs/{job_id}/privacy-report.pdf")
        self.assertEqual(cross_org.status_code, 403)


if __name__ == "__main__":
    unittest.main()
