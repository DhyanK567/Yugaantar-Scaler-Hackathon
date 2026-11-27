"""Tests for M22 Homepage & Dashboard 4 Metric Cards + Unavailable States."""
from __future__ import annotations

import gc
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


class M22MetricCardsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self._old_dir = os.environ.get("MEDILOCKER_DATA_DIR")
        os.environ["MEDILOCKER_DATA_DIR"] = self._tmpdir.name
        from backend.database import init_db

        init_db()

    def tearDown(self) -> None:
        gc.collect()
        if self._old_dir is None:
            os.environ.pop("MEDILOCKER_DATA_DIR", None)
        else:
            os.environ["MEDILOCKER_DATA_DIR"] = self._old_dir
        self._tmpdir.cleanup()

    def test_01_empty_state_returns_not_measured_never_zero(self) -> None:
        from backend.dashboard_metrics import get_dashboard_metrics_summary
        from backend.database import get_db

        with get_db() as conn:
            res = get_dashboard_metrics_summary(conn, ["org-1"], scope="latest")

        self.assertEqual(res["scope"], "EMPTY")
        m = res["metrics"]
        self.assertEqual(m["files_protected"]["status"], "NOT_MEASURED")
        self.assertIsNone(m["files_protected"]["count"])
        self.assertEqual(m["identifiers_protected"]["status"], "NOT_MEASURED")
        self.assertIsNone(m["identifiers_protected"]["transformed"])
        self.assertEqual(m["clinical"]["status"], "NOT_MEASURED")
        self.assertIsNone(m["clinical"]["preservation_percentage"])
        self.assertEqual(m["privacy_tests"]["status"], "NOT_TESTED")
        self.assertEqual(m["privacy_tests"]["total_executed"], 0)

    def test_02_completed_job_computes_all_four_cards_accurately(self) -> None:
        from backend.dashboard_metrics import get_dashboard_metrics_summary
        from backend.database import get_db

        now = time.time()
        with get_db() as conn:
            conn.execute(
                "INSERT INTO organisations (id, name, org_type, region, status, records_contributed, joined_at) VALUES ('org-1', 'Org 1', 'Hospital', 'IN', 'Active', 0, ?)",
                (now,),
            )
            conn.execute(
                "INSERT INTO datasets (id, organisation_id, name, description, format, file_count, total_bytes, status, created_at) VALUES ('ds-1', 'org-1', 'Ward Alpha', '', 'CSV', 10, 1000, 'PROCESSED', ?)",
                (now,),
            )
            conn.execute(
                """
                INSERT INTO jobs (id, dataset_id, organisation_id, input_name, status, current_stage,
                    files_total, files_sanitized, files_quarantined, records_processed, duration_secs, release_decision, created_at, completed_at)
                VALUES ('job-1', 'ds-1', 'org-1', 'ds-1', 'COMPLETED_WITH_WARNINGS', 'COMPLETED_WITH_WARNINGS',
                    10, 8, 2, 100, 1.25, 'APPROVED_WITH_WARNINGS', ?, ?)
                """,
                (now, now),
            )
            conn.execute(
                """
                INSERT INTO privacy_assessments (id, job_id, dataset_id, organisation_id, pii_detected, residual_leakage,
                    canary_planted, canary_leaks, canary_status, qi_risk_score, reid_risk_level, release_eligible, created_at)
                VALUES ('pa-1', 'job-1', 'ds-1', 'org-1', 42, 2, 4, 0, 'PASS', 5.0, 'LOW', 1, ?)
                """,
                (now,),
            )
            conn.execute(
                """
                INSERT INTO clinical_reports (id, job_id, organisation_id, expected_values, preserved_values,
                    modified_values, missing_values, fhir_integrity, created_at)
                VALUES ('clin-1', 'job-1', 'org-1', 200, 198, 0, 2, 'PASS', ?)
                """,
                (now,),
            )
            conn.execute(
                """
                INSERT INTO identity_clusters (id, job_id, organisation_id, precision, recall, f05, false_merges, total_patients, created_at)
                VALUES ('idc-1', 'job-1', 'org-1', 1.0, 0.8, 0.95, 0, 50, ?)
                """,
                (now,),
            )
            conn.execute(
                """
                INSERT INTO attack_runs (id, job_id, dataset_id, organisation_id, profile, risk_score, blocked_count, total_count, results_json, created_at)
                VALUES ('atk-1', 'job-1', 'ds-1', 'org-1', 'standard-7-vector', 0.0, 7, 7, '[]', ?)
                """,
                (now,),
            )
            conn.execute(
                """
                INSERT INTO passports (id, job_id, dataset_id, organisation_id, manifest_hash, signature_status, passport_json, created_at)
                VALUES ('psp-1', 'job-1', 'ds-1', 'org-1', 'abc123', 'UNSIGNED', '{}', ?)
                """,
                (now,),
            )

            res = get_dashboard_metrics_summary(conn, ["org-1"], scope="latest")

        m = res["metrics"]
        # Card 1: only 8 sanitized files (not 10 total, not 2 quarantined)
        self.assertEqual(m["files_protected"]["count"], 8)
        self.assertEqual(m["files_protected"]["files_quarantined"], 2)
        # Card 2: 42 detected - 2 remaining leaks = 40 transformed
        self.assertEqual(m["identifiers_protected"]["detected"], 42)
        self.assertEqual(m["identifiers_protected"]["transformed"], 40)
        self.assertEqual(m["identifiers_protected"]["remaining_leaks"], 2)
        # Card 3: 198 / 200 * 100 = 99.0%
        self.assertAlmostEqual(m["clinical"]["preservation_percentage"], 99.0, places=2)
        # Card 4: 4 passed (canary, clinical, attack, passport), 1 failed (residual_leakage=2)
        self.assertEqual(m["privacy_tests"]["passed"], 4)
        self.assertEqual(m["privacy_tests"]["failed"], 1)
        self.assertEqual(m["privacy_tests"]["total_executed"], 5)
        # Identity recall & F0.5 preserved
        self.assertEqual(m["identity"]["recall"], 0.8)
        self.assertEqual(m["identity"]["f05"], 0.95)


if __name__ == "__main__":
    unittest.main()
