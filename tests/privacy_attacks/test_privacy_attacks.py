"""M10.8 — Adversarial Privacy Attack & Clinical Utility Test Suite (standard library unittest)."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STARTER = ROOT / "starter"
if str(STARTER) not in sys.path:
    sys.path.insert(0, str(STARTER))

from raksha_engine.attacker import RecordProfile, simulate_attacks
from raksha_engine.mitigation import plan_record_mitigation
from raksha_engine.names import CorpusNameIndex
from raksha_engine.privacy import parse_date_str, shift_date_string
from raksha_engine.privacy_utility import (
    ClinicalUtilityMetrics,
    PrivacyMetrics,
    evaluate_release_gate,
)
from raksha_engine.qi_classifier import FieldCategory, classify_field_tier
from raksha_engine.risk_engine import evaluate_corpus_risk
from raksha_engine.sanitizer import sanitize_free_text

POLICY = {
    "policy_version": "m10-v1",
    "age_band_years": 5,
    "min_group_size": 5,
    "weight_group_size": 35,
    "weight_qi_uniqueness": 25,
    "weight_geo_rarity": 15,
    "weight_temporal": 10,
    "weight_rare_dx": 10,
    "weight_linkage": 5,
    "risk_threshold_moderate": 25,
    "risk_threshold_high": 50,
    "risk_threshold_critical": 75,
    "max_critical_records_for_pass": 0,
    "max_high_risk_ratio_for_pass": 0.15,
    "min_clinical_retention_ratio": 0.90,
}


def _run_cli(inp: Path, out: Path, secret: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ, RAKSHA_SECRET=secret, HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    return subprocess.run(
        [sys.executable, str(STARTER / "main.py"), "--input", str(inp), "--output", str(out)],
        capture_output=True, text=True, env=env, timeout=120,
    )


def _tree_digest(out: Path) -> str:
    h = hashlib.sha256()
    for name in ("sanitized", "records.jsonl"):
        p = out / name
        items = sorted(p.rglob("*")) if p.is_dir() else ([p] if p.exists() else [])
        for f in items:
            if f.is_file():
                h.update(f.relative_to(out).as_posix().encode() + b"\0" + f.read_bytes() + b"\0")
    return h.hexdigest()


class TestMilestone10PrivacyAttacks(unittest.TestCase):
    def test_01_qi_classification_multilingual_and_clinical_preservation(self) -> None:
        self.assertEqual(classify_field_tier("Patient Name").category, FieldCategory.DIRECT_IDENTIFIER)
        self.assertEqual(classify_field_tier("Janm Tithi").category, FieldCategory.DIRECT_IDENTIFIER)
        self.assertEqual(classify_field_tier("Umar").category, FieldCategory.QUASI_IDENTIFIER)
        self.assertEqual(classify_field_tier("Gaon").category, FieldCategory.QUASI_IDENTIFIER)
        self.assertEqual(classify_field_tier("length_of_stay").category, FieldCategory.QUASI_IDENTIFIER)
        self.assertEqual(classify_field_tier("department").category, FieldCategory.QUASI_IDENTIFIER)
        self.assertEqual(classify_field_tier("diagnosis").category, FieldCategory.SENSITIVE_CLINICAL)
        self.assertEqual(classify_field_tier("medication").category, FieldCategory.SENSITIVE_CLINICAL)
        self.assertEqual(classify_field_tier("blood_pressure").category, FieldCategory.CLINICAL_UTILITY)
        self.assertEqual(classify_field_tier("resourceType").category, FieldCategory.SAFE_METADATA)

    def test_02_unique_age_gender_village_attack_and_mitigation(self) -> None:
        pre = [
            RecordProfile("r1", "p1", age_val="91", gender="F", district="sitapur", village_or_loc="bhimnagar", pin="261001"),
            RecordProfile("r2", "p2", age_val="35", gender="M", district="sitapur", village_or_loc="rampur", pin="261002"),
            RecordProfile("r3", "p3", age_val="35", gender="M", district="sitapur", village_or_loc="rampur", pin="261002"),
        ]
        pre_sim = simulate_attacks(pre, min_group_size=5)
        self.assertGreater(pre_sim.strategy_success_counts["age_gender_location"], 0)
        risk = evaluate_corpus_risk(pre, POLICY)
        self.assertIn(risk.assessments["r1"].risk_category, ("HIGH", "CRITICAL"))
        plan = plan_record_mitigation(risk.assessments["r1"], POLICY, has_age=True, has_pin=True, has_district=True, has_village=True)
        self.assertEqual(plan.age_band_width, 10)
        self.assertTrue(plan.suppress_village)

        post = [
            RecordProfile("r1", "p1", age_val="85+", gender="F", district="", village_or_loc="", pin=""),
            RecordProfile("r2", "p2", age_val="30-39", gender="M", district="sitapur", village_or_loc="", pin="261***"),
            RecordProfile("r3", "p3", age_val="30-39", gender="M", district="sitapur", village_or_loc="", pin="261***"),
        ]
        post_sim = simulate_attacks(post, min_group_size=5)
        self.assertEqual(post_sim.strategy_success_counts["geographic_narrowing"], 0)

    def test_03_rare_diagnosis_and_exact_date_preserves_diagnosis(self) -> None:
        pre = [
            RecordProfile("r1", "p1", age_val="62", gender="M", district="unnao", village_or_loc="amardih", admission_date="2026-04-12", los_days="7", diagnosis="parkinsons disease"),
            RecordProfile("r2", "p2", age_val="40", gender="F", district="unnao", village_or_loc="purwa", admission_date="2026-04-18", los_days="3", diagnosis="dengue"),
        ]
        sim = simulate_attacks(pre, min_group_size=5)
        self.assertGreater(sim.strategy_success_counts["rare_diagnosis_location"], 0)
        self.assertGreater(sim.strategy_success_counts["admission_los"], 0)

        # Sanitization preserves diagnosis while shifting dates
        ni = CorpusNameIndex()
        txt = "Diagnosis: Parkinson's disease. Admitted: 2026-04-12, Discharged: 2026-04-19."
        cleaned, _ = sanitize_free_text(txt, ni, "cluster|p1", b"sec-1", 180)
        self.assertIn("Parkinson's disease", cleaned)
        self.assertNotIn("2026-04-12", cleaned)

    def test_04_small_department_and_rare_attribute_combination(self) -> None:
        pre = [
            RecordProfile("r1", "p1", age_val="74", gender="F", hospital_dept="pediatric_oncology", treatment="cisplatin"),
            RecordProfile("r2", "p2", age_val="30", gender="M", hospital_dept="general_medicine", treatment="paracetamol"),
        ]
        sim = simulate_attacks(pre, min_group_size=5)
        self.assertGreater(sim.strategy_success_counts["rare_attribute_combination"], 0)
        risk = evaluate_corpus_risk(pre, POLICY)
        self.assertIn("SMALL_DEPARTMENT", risk.assessments["r1"].contributing_factors)

    def test_05_rare_age_group_and_pin_prefix(self) -> None:
        pre = [RecordProfile("r1", "p1", age_val="88", gender="M", district="barabanki", pin="225362")]
        risk = evaluate_corpus_risk(pre, POLICY)
        self.assertIn("GEOGRAPHIC_RARITY", risk.assessments["r1"].contributing_factors)
        plan = plan_record_mitigation(risk.assessments["r1"], POLICY, has_age=True, has_pin=True, has_district=True)
        self.assertEqual(plan.age_band_width, 10)

    def test_06_cross_hospital_identity_correlation(self) -> None:
        pre = [
            RecordProfile("r1", "p1", gender="F", district="bahraich", hospital_count=3, record_count=5),
            RecordProfile("r2", "p2", gender="M", district="bahraich", hospital_count=1, record_count=1),
        ]
        sim = simulate_attacks(pre, min_group_size=5)
        self.assertGreater(sim.strategy_success_counts["cross_record_linkage"], 0)
        risk = evaluate_corpus_risk(pre, POLICY)
        self.assertIn("CROSS_RECORD_LINKABLE", risk.assessments["r1"].contributing_factors)

    def test_07_individually_safe_qis_combined_and_zero_risk_record(self) -> None:
        # 5 records share each individual attribute, but r1 is unique in combination
        pre = [
            RecordProfile("r1", "p1", age_val="40", gender="M", district="d1", pin="226001"),
            RecordProfile("r2", "p2", age_val="40", gender="F", district="d2", pin="226002"),
            RecordProfile("r3", "p3", age_val="50", gender="M", district="d2", pin="226002"),
            RecordProfile("r4", "p4", age_val="50", gender="F", district="d1", pin="226001"),
            RecordProfile("r5", "p5", age_val="60", gender="M", district="d1", pin="226002"),
        ]
        risk = evaluate_corpus_risk(pre, POLICY)
        self.assertTrue(risk.assessments["r1"].measured_is_unique)
        self.assertIn("MULTI_QI_UNIQUE", risk.assessments["r1"].contributing_factors)

        # Record with no QI fields has LOW risk and 0 score
        no_qi = [RecordProfile("r_clean", "p_clean")]
        risk_clean = evaluate_corpus_risk(no_qi, POLICY)
        self.assertEqual(risk_clean.assessments["r_clean"].risk_category, "LOW")
        self.assertEqual(risk_clean.assessments["r_clean"].estimated_risk_score, 0)

    def test_08_clinical_values_untouched_and_date_interval_preserved(self) -> None:
        ni = CorpusNameIndex()
        note = "BP 120/80 mmHg, Temp 98.6 F, Dolo 650 mg BD, Parkinson's disease. Adm: 2026-01-10, Disch: 2026-01-15."
        cleaned, _ = sanitize_free_text(note, ni, "cluster|pt1", b"secret-key", 180)
        for must_keep in ("120/80", "98.6", "Dolo 650 mg", "Parkinson's disease"):
            self.assertIn(must_keep, cleaned)
        d1 = parse_date_str(shift_date_string("2026-01-10", "cluster|pt1", b"secret-key", 180))
        d2 = parse_date_str(shift_date_string("2026-01-15", "cluster|pt1", b"secret-key", 180))
        self.assertIsNotNone(d1)
        self.assertIsNotNone(d2)
        self.assertEqual((d2[0] - d1[0]).days, 5)

    def test_09_release_gate_blocks_critical_risk_and_direct_leaks(self) -> None:
        pre = [RecordProfile("r1", "p1", age_val="91", gender="F", district="sitapur", village_or_loc="bhimnagar", pin="261001", admission_date="2026-01-01", diagnosis="rare_dx")]
        sim = simulate_attacks(pre, min_group_size=5)
        risk = evaluate_corpus_risk(pre, POLICY)
        priv = PrivacyMetrics(1, 1, 1, 1, 1, 1, 1, 0, 0, 0)
        util = ClinicalUtilityMetrics(1, 0, 10, 10)
        gate_crit = evaluate_release_gate(priv, util, risk, sim, sim, POLICY, direct_leaks_observed=0)
        self.assertEqual(gate_crit.status, "BLOCKED")
        self.assertIn("CRITICAL_REIDENTIFICATION_RISK_EXCEEDED", gate_crit.reason_codes)

        gate_leak = evaluate_release_gate(priv, util, risk, sim, sim, POLICY, direct_leaks_observed=1)
        self.assertEqual(gate_leak.status, "BLOCKED")
        self.assertIn("DIRECT_PII_LEAK_DETECTED", gate_leak.reason_codes)
        # Verify exact fraction never rounds 4853/4855 to 100%
        u2 = ClinicalUtilityMetrics(10, 10, 4853, 4855)
        self.assertEqual(u2.exact_fraction_str(), "4853/4855")

    def test_10_end_to_end_determinism_fhir_malformed_and_no_pii_leaks(self) -> None:
        work = Path(tempfile.mkdtemp(prefix="m10_e2e_"))
        try:
            inp = work / "inp"
            inp.mkdir()
            (inp / "patients.csv").write_text(
                "UHID,Patient Name,Gender,Age,Village,District,PIN,Diagnosis,BP\n"
                "JJH-001,Ramesh Kumar,M,47,Rampur,Sitapur,261001,Dengue,120/80\n"
                "JJH-002,Sita Devi,F,92,Bhimnagar,Sitapur,261001,Parkinson's disease,130/84\n",
                encoding="utf-8",
            )
            (inp / "broken.json").write_text("{bad json", encoding="utf-8")
            (inp / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00")
            (inp / "bundle.json").write_text(json.dumps({
                "resourceType": "Bundle",
                "type": "collection",
                "entry": [
                    {"resource": {"resourceType": "Patient", "id": "p1", "name": [{"text": "Ramesh Kumar"}], "gender": "male", "birthDate": "1979-05-12"}},
                    {"resource": {"resourceType": "Organization", "id": "o1", "name": "Jeevan Jyoti Charitable Hospital"}},
                    {"resource": {"resourceType": "Condition", "id": "c1", "code": {"text": "Dengue fever"}}},
                ],
            }), encoding="utf-8")

            out1, out2, out3 = work / "o1", work / "o2", work / "o3"
            sec_a, sec_b = "secret-one-xyz", "secret-two-abc"
            r1 = _run_cli(inp, out1, sec_a)
            r2 = _run_cli(inp, out2, sec_a)
            r3 = _run_cli(inp, out3, sec_b)
            self.assertEqual(r1.returncode, 0)
            self.assertEqual(_tree_digest(out1), _tree_digest(out2))
            self.assertNotEqual(_tree_digest(out1), _tree_digest(out3))

            # No raw PII or secret in logs, report.json, or sanitized output
            all_logs = r1.stdout + r1.stderr
            rep_text = (out1 / "report.json").read_text(encoding="utf-8")
            for forbidden in ("Ramesh Kumar", "Sita Devi", "Bhimnagar", "Rampur", sec_a):
                self.assertNotIn(forbidden, all_logs)
                self.assertNotIn(forbidden, rep_text)
            csv_out = (out1 / "sanitized" / "patients.csv").read_text(encoding="utf-8")
            self.assertIn("Parkinson's disease", csv_out)
            self.assertIn("120/80", csv_out)
            self.assertNotIn("Ramesh Kumar", csv_out)

            # Quarantine & FHIR integrity checks
            rep = json.loads(rep_text)
            self.assertEqual(rep["counts"]["files_sanitized"], 2)
            self.assertEqual(rep["counts"]["files_quarantined"], 2)
            self.assertIn("privacy_intelligence", rep)
            self.assertFalse((out1 / "sanitized" / "image.png").exists())
            bundle = json.loads((out1 / "sanitized" / "bundle.json").read_text(encoding="utf-8"))
            self.assertEqual(bundle["resourceType"], "Bundle")
            self.assertEqual(bundle["entry"][1]["resource"]["name"], "Jeevan Jyoti Charitable Hospital")
        finally:
            shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
