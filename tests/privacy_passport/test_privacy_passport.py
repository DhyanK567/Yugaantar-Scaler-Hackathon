"""Adversarial & Regression Test Suite for GuptKavach Privacy Passport (Milestone 15.5)."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
STARTER_DIR = REPO_ROOT / "starter"
if str(STARTER_DIR) not in sys.path:
    sys.path.insert(0, str(STARTER_DIR))

from raksha_engine.passport import (  # noqa: E402
    HAS_ED25519,
    NOT_MEASURED,
    NOT_RUN,
    PassportEvidenceInput,
    PassportSecurityError,
    assert_no_sensitive_data,
    build_dataset_manifest,
    build_privacy_passport,
    compute_manifest_root_hash,
    generate_ed25519_keypair_pem,
    load_signing_key,
)
from raksha_engine.passport_report import render_passport_html  # noqa: E402
from verify_passport import verify_passport_bundle  # noqa: E402


def _make_evidence(
    files_report: list[dict] | None = None,
    fhir_bundles: int = 1,
    fhir_passed: bool = True,
    canaries_exposed: int | None = None,
    residual_leaks: int | None = None,
) -> PassportEvidenceInput:
    fr = files_report if files_report is not None else [
        {"input_sha256": "a" * 64, "output": "sanitized/note_01.txt", "status": "sanitized"}
    ]
    return PassportEvidenceInput(
        files_report=fr,
        records_processed=1,
        records_linked=1,
        identifiers_detected=2,
        generalizations_applied=1,
        suppressions_applied=0,
        pre_attack={"strategies": ["exact_combination"], "pre_uniquely_distinguishable": 1, "pre_attack_successes": {"exact_combination": 1}},
        post_attack={"post_uniquely_distinguishable": 0, "post_attack_successes": {"exact_combination": 0}},
        pre_risk={"pre_categories": {"LOW": 0, "MODERATE": 1, "HIGH": 0, "CRITICAL": 0}, "records_below_min_group_pre": 0},
        post_risk={"post_categories": {"LOW": 1, "MODERATE": 0, "HIGH": 0, "CRITICAL": 0}, "records_below_min_group_post": 0, "unique_candidate_groups_post": 1},
        release_gate={"status": "PASS", "reason_codes": ["ALL_POLICY_GATES_SATISFIED"]},
        fhir_bundles_checked=fhir_bundles,
        fhir_resources_checked=5 if fhir_bundles else 0,
        fhir_validation_passed=fhir_passed,
        fhir_failures=[] if fhir_passed else [{"code": "FHIR_REQUIRED_FIELD_MISSING", "location": "doc", "detail": "missing code"}],
        policy={"policy_version": "m15.5-v1", "require_fhir_validation": True, "require_security_checks": True, "require_cryptographic_integrity": True},
        raksha_secret_configured=True,
        residual_leaks_detected=residual_leaks,
        canaries_exposed=canaries_exposed,
        canaries_total=4 if canaries_exposed is not None else None,
    )


class TestPrivacyPassport(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="gk_pp_test_"))
        self.out_dir = self.tmp / "out"
        self.san_dir = self.out_dir / "sanitized"
        self.san_dir.mkdir(parents=True)
        (self.san_dir / "note_01.txt").write_text("Patient: PSN-ABC123\nBP 120/80\n", encoding="utf-8")
        (self.san_dir / "sub").mkdir()
        (self.san_dir / "sub" / "labs.csv").write_text("id,hb\nPSN-ABC123,12.5\n", encoding="utf-8")

        self.priv_pem, self.pub_pem = generate_ed25519_keypair_pem()
        self.priv_path = self.tmp / "signing_key.pem"
        self.pub_path = self.tmp / "signing_pub.pem"
        self.priv_path.write_bytes(self.priv_pem)
        self.pub_path.write_bytes(self.pub_pem)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _emit_bundle(self, signed: bool = True, evidence: PassportEvidenceInput | None = None) -> tuple[Path, Path]:
        manifest = build_dataset_manifest(self.san_dir)
        ev = evidence or _make_evidence()
        key = load_signing_key(self.priv_path) if signed else None
        passport = build_privacy_passport(ev, manifest, signing_key=key)
        m_path = self.out_dir / "dataset_manifest.json"
        p_path = self.out_dir / "privacy_passport.json"
        h_path = self.out_dir / "privacy_passport.html"
        m_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        p_path.write_text(json.dumps(passport, indent=2), encoding="utf-8")
        h_path.write_text(render_passport_html(passport), encoding="utf-8")
        return p_path, m_path

    # 1. Valid certificate and unchanged dataset
    def test_01_valid_signed_certificate_and_dataset(self) -> None:
        p_path, _ = self._emit_bundle(signed=True)
        res = verify_passport_bundle(p_path, self.out_dir, public_key_path=self.pub_path)
        self.assertEqual(res["status"], "VERIFIED")
        self.assertTrue(res["valid"])

    # 2. Modified output file
    def test_02_modified_output_file_detected(self) -> None:
        p_path, _ = self._emit_bundle(signed=True)
        (self.san_dir / "note_01.txt").write_text("TAMPERED CONTENT\n", encoding="utf-8")
        res = verify_passport_bundle(p_path, self.out_dir)
        self.assertEqual(res["status"], "TAMPERED")
        self.assertFalse(res["valid"])

    # 3. Deleted output file
    def test_03_deleted_output_file_detected(self) -> None:
        p_path, _ = self._emit_bundle(signed=True)
        (self.san_dir / "sub" / "labs.csv").unlink()
        res = verify_passport_bundle(p_path, self.out_dir)
        self.assertEqual(res["status"], "INCOMPLETE")
        self.assertFalse(res["valid"])

    # 4. Unexpected additional file
    def test_04_unexpected_additional_file_detected(self) -> None:
        p_path, _ = self._emit_bundle(signed=True)
        (self.san_dir / "rogue.txt").write_text("extra", encoding="utf-8")
        res = verify_passport_bundle(p_path, self.out_dir)
        self.assertEqual(res["status"], "TAMPERED")
        self.assertFalse(res["valid"])

    # 5. Modified certificate
    def test_05_modified_certificate_detected(self) -> None:
        p_path, _ = self._emit_bundle(signed=True)
        data = json.loads(p_path.read_text(encoding="utf-8"))
        data["release_decision"]["status"] = "PASS"
        data["release_decision"]["explanation"] = "Forged explanation"
        p_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        res = verify_passport_bundle(p_path, self.out_dir)
        self.assertEqual(res["status"], "INVALID_SIGNATURE")
        self.assertFalse(res["valid"])

    # 6. Invalid signature
    def test_06_invalid_signature_rejected(self) -> None:
        p_path, _ = self._emit_bundle(signed=True)
        data = json.loads(p_path.read_text(encoding="utf-8"))
        data["signature"]["value"] = "AAAA" + data["signature"]["value"][4:]
        p_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        res = verify_passport_bundle(p_path, self.out_dir)
        self.assertEqual(res["status"], "INVALID_SIGNATURE")
        self.assertFalse(res["valid"])

    # 7. Missing signing key (UNSIGNED mode)
    def test_07_unsigned_mode_clearly_identified(self) -> None:
        p_path, _ = self._emit_bundle(signed=False)
        res = verify_passport_bundle(p_path, self.out_dir, require_signature=False)
        self.assertEqual(res["status"], "UNSIGNED")
        self.assertTrue(res["valid"])
        res_strict = verify_passport_bundle(p_path, self.out_dir, require_signature=True)
        self.assertEqual(res_strict["status"], "UNSIGNED")
        self.assertFalse(res_strict["valid"])

    # 8. Unsupported certificate version
    def test_08_unsupported_certificate_version(self) -> None:
        p_path, _ = self._emit_bundle(signed=False)
        data = json.loads(p_path.read_text(encoding="utf-8"))
        data["certificate_identity"]["schema_version"] = "guptkavach-passport/99.0"
        p_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        res = verify_passport_bundle(p_path, self.out_dir)
        self.assertEqual(res["status"], "INVALID_CERTIFICATE")
        self.assertFalse(res["valid"])

    # 9. Malformed manifest
    def test_09_malformed_manifest_rejected(self) -> None:
        p_path, m_path = self._emit_bundle(signed=True)
        m_path.write_text("{not valid json", encoding="utf-8")
        res = verify_passport_bundle(p_path, self.out_dir)
        self.assertEqual(res["status"], "INVALID_CERTIFICATE")
        self.assertFalse(res["valid"])

    # 10. Incorrect file hash in manifest
    def test_10_incorrect_file_hash_in_manifest(self) -> None:
        p_path, m_path = self._emit_bundle(signed=True)
        m_data = json.loads(m_path.read_text(encoding="utf-8"))
        m_data["files"][0]["sha256"] = "0" * 64
        m_path.write_text(json.dumps(m_data, indent=2), encoding="utf-8")
        res = verify_passport_bundle(p_path, self.out_dir)
        self.assertEqual(res["status"], "TAMPERED")
        self.assertFalse(res["valid"])

    # 11. Reordered manifest entries (canonical root hash remains valid)
    def test_11_reordered_manifest_entries_still_verified(self) -> None:
        p_path, m_path = self._emit_bundle(signed=True)
        m_data = json.loads(m_path.read_text(encoding="utf-8"))
        m_data["files"] = list(reversed(m_data["files"]))
        m_path.write_text(json.dumps(m_data, indent=2), encoding="utf-8")
        res = verify_passport_bundle(p_path, self.out_dir)
        self.assertEqual(res["status"], "VERIFIED")
        self.assertTrue(res["valid"])

    # 12. Empty dataset
    def test_12_empty_dataset_verified(self) -> None:
        empty_out = self.tmp / "empty_out"
        (empty_out / "sanitized").mkdir(parents=True)
        manifest = build_dataset_manifest(empty_out / "sanitized")
        ev = _make_evidence(files_report=[], fhir_bundles=0)
        passport = build_privacy_passport(ev, manifest, signing_key=load_signing_key(self.priv_path))
        p_path = empty_out / "privacy_passport.json"
        (empty_out / "dataset_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        p_path.write_text(json.dumps(passport), encoding="utf-8")
        res = verify_passport_bundle(p_path, empty_out)
        self.assertEqual(res["status"], "VERIFIED")
        self.assertEqual(manifest["file_count"], 0)

    # 13 & 14. Quarantined input & partial failure
    def test_13_14_quarantined_input_and_partial_failure(self) -> None:
        fr = [
            {"input_sha256": "a" * 64, "output": "sanitized/note_01.txt", "status": "sanitized"},
            {"input_sha256": "b" * 64, "output": None, "status": "quarantined", "reason": "JSONDecodeError"},
        ]
        p_path, _ = self._emit_bundle(signed=True, evidence=_make_evidence(files_report=fr))
        data = json.loads(p_path.read_text(encoding="utf-8"))
        self.assertEqual(data["dataset_provenance"]["files_sanitised"], 1)
        self.assertEqual(data["dataset_provenance"]["files_quarantined"], 1)
        # Honest NOT_MEASURED / NOT_RUN checks
        self.assertEqual(data["identity_assessment"]["identity_precision"], NOT_MEASURED)
        self.assertEqual(data["privacy_assessment"]["canary_test"]["status"], NOT_RUN)
        res = verify_passport_bundle(p_path, self.out_dir)
        self.assertEqual(res["status"], "VERIFIED")

    # 15. Sensitive information accidentally entering certificate fields
    def test_15_sensitive_info_guardrail(self) -> None:
        with self.assertRaises(PassportSecurityError):
            assert_no_sensitive_data("secret=my-super-secret-key", secret=b"my-super-secret-key")
        with self.assertRaises(PassportSecurityError):
            assert_no_sensitive_data("aadhaar 2345 6789 0123")
        with self.assertRaises(PassportSecurityError):
            assert_no_sensitive_data("phone +91 9876543210")
        with self.assertRaises(PassportSecurityError):
            assert_no_sensitive_data("email patient@example.org")

    # 16. Unicode filenames
    def test_16_unicode_filenames(self) -> None:
        (self.san_dir / "रिपोर्ट_०१.txt").write_text("Patient: PSN-UNI01\n", encoding="utf-8")
        p_path, _ = self._emit_bundle(signed=True)
        res = verify_passport_bundle(p_path, self.out_dir)
        self.assertEqual(res["status"], "VERIFIED")

    # 17. Windows path normalization in manifest
    def test_17_windows_path_handling(self) -> None:
        entries = [
            {"path": "sub\\labs.csv", "sha256": "a" * 64, "size_bytes": 10},
            {"path": "note_01.txt", "sha256": "b" * 64, "size_bytes": 20},
        ]
        entries_posix = [
            {"path": "sub/labs.csv", "sha256": "a" * 64, "size_bytes": 10},
            {"path": "note_01.txt", "sha256": "b" * 64, "size_bytes": 20},
        ]
        self.assertEqual(compute_manifest_root_hash(entries), compute_manifest_root_hash(entries_posix))

    # 18. Repeated verification
    def test_18_repeated_verification_idempotent(self) -> None:
        p_path, _ = self._emit_bundle(signed=True)
        for _ in range(3):
            res = verify_passport_bundle(p_path, self.out_dir)
            self.assertEqual(res["status"], "VERIFIED")

    # 19. Different output directory (relocated copy)
    def test_19_relocated_output_directory(self) -> None:
        p_path, _ = self._emit_bundle(signed=True)
        relocated = self.tmp / "relocated_copy"
        shutil.copytree(self.out_dir, relocated)
        res = verify_passport_bundle(relocated / "privacy_passport.json", relocated)
        self.assertEqual(res["status"], "VERIFIED")

    # 20. Offline CLI verification & release gate blocking rules
    def test_20_offline_cli_and_blocking_rules(self) -> None:
        p_path, _ = self._emit_bundle(signed=True)
        env = dict(os.environ, HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
        proc = subprocess.run(
            [sys.executable, str(STARTER_DIR / "verify_passport.py"), "--passport", str(p_path), "--output", str(self.out_dir)],
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("STATUS: VERIFIED", proc.stdout)

        # Canary exposure must block release
        ev_canary = _make_evidence(canaries_exposed=1)
        p_canary = build_privacy_passport(ev_canary, build_dataset_manifest(self.san_dir))
        self.assertEqual(p_canary["release_decision"]["status"], "BLOCKED")
        self.assertIn("CANARY_EXPOSURE_DETECTED", p_canary["release_decision"]["blocking_reasons"])

        # Offline HTML has no external links/CDNs
        html_text = (self.out_dir / "privacy_passport.html").read_text(encoding="utf-8")
        self.assertNotIn("http://", html_text)
        self.assertNotIn("https://", html_text)


if __name__ == "__main__":
    unittest.main()
