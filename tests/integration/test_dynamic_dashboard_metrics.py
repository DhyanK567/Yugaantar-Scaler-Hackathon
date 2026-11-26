"""Automated tests for MediLocker Dynamic Dashboard Metrics & Data Integrity.

Covers all 15 Phase 8 scenarios plus frontend hardcoded-metric guard.
"""
from __future__ import annotations

import json
import sqlite3
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.dashboard_metrics import (  # noqa: E402
    get_dashboard_metrics_summary,
    get_runtime_execution_compliance,
)


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE organisations (id TEXT PRIMARY KEY, name TEXT);
        CREATE TABLE datasets (id TEXT PRIMARY KEY, organisation_id TEXT, name TEXT);
        CREATE TABLE jobs (
            id TEXT PRIMARY KEY,
            dataset_id TEXT,
            organisation_id TEXT,
            input_name TEXT,
            status TEXT,
            release_decision TEXT,
            files_total INTEGER DEFAULT 0,
            created_at REAL,
            completed_at REAL
        );
        CREATE TABLE privacy_assessments (
            id TEXT PRIMARY KEY,
            job_id TEXT UNIQUE,
            canary_planted INTEGER DEFAULT 0,
            canary_leaks INTEGER DEFAULT 0,
            canary_status TEXT DEFAULT 'NOT_RUN'
        );
        CREATE TABLE clinical_reports (
            id TEXT PRIMARY KEY,
            job_id TEXT UNIQUE,
            expected_values INTEGER DEFAULT 0,
            preserved_values INTEGER DEFAULT 0,
            modified_values INTEGER DEFAULT 0,
            missing_values INTEGER DEFAULT 0
        );
        CREATE TABLE identity_clusters (
            id TEXT PRIMARY KEY,
            job_id TEXT UNIQUE,
            precision REAL,
            false_merges INTEGER DEFAULT 0,
            total_patients INTEGER DEFAULT 0,
            graph_json TEXT
        );
        """
    )


class DynamicDashboardMetricsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.conn = sqlite3.connect(":memory:")
        _create_schema(self.conn)
        self.conn.execute("INSERT INTO organisations VALUES ('org-a', 'Hospital A'), ('org-b', 'Hospital B')")
        self.conn.execute("INSERT INTO datasets VALUES ('ds-1', 'org-a', 'Cohort Alpha'), ('ds-2', 'org-a', 'Cohort Beta'), ('ds-b', 'org-b', 'Other Org Cohort')")

    def tearDown(self) -> None:
        self.conn.close()

    def test_01_empty_database_returns_empty_and_no_fake_metrics(self) -> None:
        res = get_dashboard_metrics_summary(self.conn, ["org-a"], scope="latest")
        self.assertEqual(res["scope"], "EMPTY")
        self.assertEqual(res["metrics"]["canary"]["status"], "NOT_TESTED")
        self.assertIsNone(res["metrics"]["canary"]["leaked"])
        self.assertEqual(res["metrics"]["identity"]["status"], "NOT_MEASURED")
        self.assertIsNone(res["metrics"]["identity"]["precision"])
        self.assertEqual(res["metrics"]["clinical"]["status"], "NOT_MEASURED")
        self.assertIsNone(res["metrics"]["clinical"]["preservation_percentage"])

    def test_02_two_datasets_job_switching_and_latest_excludes_failed(self) -> None:
        # Job 1 (older completed)
        self.conn.execute(
            "INSERT INTO jobs VALUES ('job-1', 'ds-1', 'org-a', 'a.csv', 'COMPLETED', 'APPROVED', 12, 100.0, 110.0)"
        )
        self.conn.execute("INSERT INTO privacy_assessments VALUES ('pa-1', 'job-1', 6, 0, 'PASS')")
        self.conn.execute("INSERT INTO clinical_reports VALUES ('cr-1', 'job-1', 1000, 995, 2, 3)")
        self.conn.execute(
            "INSERT INTO identity_clusters VALUES ('id-1', 'job-1', 1.0, 0, 50, ?)",
            (json.dumps({"stats": {"true_positives": 40, "false_positives": 0, "total_records": 50}}),),
        )

        # Job 2 (newer completed, fractional clinical & canary leak)
        self.conn.execute(
            "INSERT INTO jobs VALUES ('job-2', 'ds-2', 'org-a', 'b.csv', 'COMPLETED_WITH_WARNINGS', 'BLOCKED', 8, 200.0, 210.0)"
        )
        self.conn.execute("INSERT INTO privacy_assessments VALUES ('pa-2', 'job-2', 2, 1, 'FAILED')")
        self.conn.execute("INSERT INTO clinical_reports VALUES ('cr-2', 'job-2', 300, 290, 5, 5)")
        self.conn.execute(
            "INSERT INTO identity_clusters VALUES ('id-2', 'job-2', 0.9, 1, 20, ?)",
            (json.dumps({"stats": {"true_positives": 18, "false_positives": 2, "total_records": 20}}),),
        )

        # Job 3 (newest, FAILED -> must be excluded from default 'latest')
        self.conn.execute(
            "INSERT INTO jobs VALUES ('job-3', 'ds-2', 'org-a', 'c.csv', 'FAILED', 'BLOCKED', 4, 300.0, 305.0)"
        )

        latest = get_dashboard_metrics_summary(self.conn, ["org-a"], scope="latest")
        self.assertEqual(latest["job_id"], "job-2")
        self.assertEqual(latest["metrics"]["canary"]["leaked"], 1)
        self.assertEqual(latest["metrics"]["canary"]["planted"], 2)
        self.assertEqual(latest["metrics"]["canary"]["outcome"], "LEAKAGE_DETECTED")
        self.assertAlmostEqual(latest["metrics"]["clinical"]["preservation_percentage"], 96.6667, places=3)
        self.assertEqual(latest["metrics"]["identity"]["precision"], 0.9)

        # Switch to historical job-1
        hist = get_dashboard_metrics_summary(self.conn, ["org-a"], scope="job-1")
        self.assertEqual(hist["job_id"], "job-1")
        self.assertEqual(hist["metrics"]["canary"]["leaked"], 0)
        self.assertEqual(hist["metrics"]["canary"]["planted"], 6)
        self.assertEqual(hist["metrics"]["clinical"]["preservation_percentage"], 99.5)
        self.assertEqual(hist["metrics"]["identity"]["precision"], 1.0)

        # Aggregate: sums numerators/denominators, NEVER averages percentages!
        agg = get_dashboard_metrics_summary(self.conn, ["org-a"], scope="aggregate")
        self.assertEqual(agg["scope"], "AGGREGATE")
        self.assertEqual(agg["jobs_included"], 2)
        self.assertEqual(agg["metrics"]["canary"]["leaked"], 1)
        self.assertEqual(agg["metrics"]["canary"]["planted"], 8)
        # (995 + 290) / (1000 + 300) = 1285 / 1300 = 98.8462%
        self.assertAlmostEqual(agg["metrics"]["clinical"]["preservation_percentage"], 98.8462, places=3)
        # (40 + 18) / (40 + 18 + 0 + 2) = 58 / 60 = 0.9667
        self.assertAlmostEqual(agg["metrics"]["identity"]["precision"], 0.9667, places=3)

    def test_03_missing_and_zero_denominators_never_fabricate_zero_leaks(self) -> None:
        self.conn.execute(
            "INSERT INTO jobs VALUES ('job-zero', 'ds-1', 'org-a', 'z.csv', 'COMPLETED', 'APPROVED', 5, 100.0, 105.0)"
        )
        # Zero canaries planted
        self.conn.execute("INSERT INTO privacy_assessments VALUES ('pa-z', 'job-zero', 0, 0, 'NOT_RUN')")
        # Zero expected clinical values
        self.conn.execute("INSERT INTO clinical_reports VALUES ('cr-z', 'job-zero', 0, 0, 0, 0)")
        # Zero identity denominator
        self.conn.execute(
            "INSERT INTO identity_clusters VALUES ('id-z', 'job-zero', NULL, 0, 0, ?)",
            (json.dumps({"stats": {"true_positives": 0, "false_positives": 0}}),),
        )
        res = get_dashboard_metrics_summary(self.conn, ["org-a"], scope="job-zero")
        self.assertEqual(res["metrics"]["canary"]["status"], "NOT_TESTED")
        self.assertEqual(res["metrics"]["clinical"]["status"], "NOT_MEASURED")
        self.assertEqual(res["metrics"]["identity"]["status"], "NOT_MEASURED")

    def test_04_cross_organisation_access_denied(self) -> None:
        self.conn.execute(
            "INSERT INTO jobs VALUES ('job-b', 'ds-b', 'org-b', 'b.csv', 'COMPLETED', 'APPROVED', 2, 100.0, 105.0)"
        )
        with self.assertRaises(PermissionError):
            get_dashboard_metrics_summary(self.conn, ["org-a"], scope="job-b")
        with self.assertRaises(LookupError):
            get_dashboard_metrics_summary(self.conn, ["org-a"], scope="job-missing")

    def test_05_refresh_picks_up_newly_completed_job(self) -> None:
        self.conn.execute(
            "INSERT INTO jobs VALUES ('job-old', 'ds-1', 'org-a', 'a.csv', 'COMPLETED', 'APPROVED', 3, 100.0, 110.0)"
        )
        r1 = get_dashboard_metrics_summary(self.conn, ["org-a"], scope="latest")
        self.assertEqual(r1["job_id"], "job-old")

        self.conn.execute(
            "INSERT INTO jobs VALUES ('job-new', 'ds-2', 'org-a', 'b.csv', 'COMPLETED', 'APPROVED', 9, 200.0, 220.0)"
        )
        r2 = get_dashboard_metrics_summary(self.conn, ["org-a"], scope="latest")
        self.assertEqual(r2["job_id"], "job-new")

    def test_06_execution_compliance_and_frontend_no_hardcoded_metrics(self) -> None:
        comp = get_runtime_execution_compliance()
        self.assertEqual(comp["scope"], "REPOSITORY_AUDIT")
        self.assertEqual(comp["llm_dependency"], "NONE")
        self.assertEqual(comp["device"], "CPU")

        for rel in (
            "frontend/src/app/page.tsx",
            "frontend/src/components/landing/LiveTrustMetrics.tsx",
            "frontend/src/components/dashboard/PrivacyPerformanceOverview.tsx",
        ):
            txt = (REPO_ROOT / rel).read_text(encoding="utf-8")
            self.assertNotIn("4,449", txt, f"Hardcoded 4,449 found in {rel}")
            self.assertNotIn("823 records", txt, f"Hardcoded 823 records found in {rel}")
            self.assertNotIn("dev/input · 200 files", txt, f"Hardcoded dev/input caption found in {rel}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
