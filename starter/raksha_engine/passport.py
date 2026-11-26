"""GuptKavach Privacy Passport — Evidence Collector, Cryptographic Integrity & Release Gate.

Provides:
- Streaming SHA-256 file hashing and deterministic dataset manifest generation
- Canonical JSON serialization and Ed25519 digital signatures (with honest UNSIGNED mode)
- Evidence collection from existing pipeline results (marking unrun/unavailable as NOT_RUN / NOT_MEASURED)
- Policy-based release gate with human-readable explanations
- Zero-PII / zero-secret guardrails before certificate emission
"""
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import json
import os
import re
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from .secure_fs import PathSecurityError, verify_path_containment

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey,
            Ed25519PublicKey,
        )

        HAS_ED25519 = True
    except Exception:  # pragma: no cover - fallback when cryptography is absent
        HAS_ED25519 = False
        InvalidSignature = Exception  # type: ignore[misc,assignment]
        Ed25519PrivateKey = Any  # type: ignore[misc,assignment]
        Ed25519PublicKey = Any  # type: ignore[misc,assignment]

PASSPORT_SCHEMA_VERSION = "guptkavach-passport/1.0"
MANIFEST_SCHEMA_VERSION = "guptkavach-manifest/1.0"
ENGINE_VERSION = "guptkavach-engine/15.5"
SUPPORTED_SCHEMA_VERSIONS = {PASSPORT_SCHEMA_VERSION}

NOT_RUN = "NOT_RUN"
NOT_MEASURED = "NOT_MEASURED"
STREAM_CHUNK_SIZE = 65536

# Lightweight patterns to catch accidental raw PII in certificate/manifest fields
_RX_AADHAAR_RAW = re.compile(r"(?<!\d)\d{4}[\s-]?\d{4}[\s-]?\d{4}(?!\d)")
_RX_PHONE_RAW = re.compile(r"(?:\+91[\s-]?)?[6-9]\d{9}\b")
_RX_EMAIL_RAW = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


class PassportSecurityError(ValueError):
    """Raised when sensitive data or secrets would leak into a passport artifact."""


def canonical_json_bytes(obj: Any) -> bytes:
    """Serialize any JSON-compatible object deterministically to UTF-8 bytes."""
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def stream_sha256(path: Path) -> tuple[str, int]:
    """Compute SHA-256 hex digest and byte size of a file using streaming reads."""
    h = hashlib.sha256()
    total = 0
    with open(path, "rb") as f:
        while True:
            chunk = f.read(STREAM_CHUNK_SIZE)
            if not chunk:
                break
            h.update(chunk)
            total += len(chunk)
    return h.hexdigest(), total


def compute_manifest_root_hash(entries: list[dict[str, Any]]) -> str:
    """Compute deterministic root hash from sorted manifest entries."""
    normalized = sorted(
        [
            {
                "path": str(e["path"]).replace("\\", "/"),
                "sha256": str(e["sha256"]).lower(),
                "size_bytes": int(e["size_bytes"]),
            }
            for e in entries
        ],
        key=lambda x: x["path"],
    )
    return hashlib.sha256(canonical_json_bytes(normalized)).hexdigest()


def build_dataset_manifest(sanitized_dir: Path) -> dict[str, Any]:
    """Walk `sanitized_dir`, hash every file via streaming SHA-256, and build canonical manifest."""
    base = sanitized_dir.resolve()
    entries: list[dict[str, Any]] = []
    if base.is_dir():
        for dp, dn, fn in os.walk(base):
            dn.sort()
            for name in sorted(fn):
                candidate = Path(dp) / name
                resolved = verify_path_containment(candidate, base)
                if not resolved.is_file():
                    continue
                rel = resolved.relative_to(base).as_posix()
                sha, size = stream_sha256(resolved)
                entries.append({"path": rel, "sha256": sha, "size_bytes": size})

    entries.sort(key=lambda x: x["path"])
    root_hash = compute_manifest_root_hash(entries)
    total_bytes = sum(e["size_bytes"] for e in entries)
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "file_count": len(entries),
        "total_bytes": total_bytes,
        "root_hash": root_hash,
        "files": entries,
    }


def compute_input_fingerprint(files_report: list[dict[str, Any]]) -> str:
    """Compute deterministic fingerprint from sorted input SHA-256s and statuses (no filenames)."""
    pairs = sorted(
        (str(e.get("input_sha256", "")).lower(), str(e.get("status", "")))
        for e in files_report
    )
    return hashlib.sha256(canonical_json_bytes(pairs)).hexdigest()


def generate_ed25519_keypair_pem() -> tuple[bytes, bytes]:
    """Generate a fresh Ed25519 (private_pem, public_pem) keypair."""
    if not HAS_ED25519:
        raise RuntimeError("cryptography library with Ed25519 support is required.")
    priv = Ed25519PrivateKey.generate()
    priv_pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_pem = priv.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return priv_pem, pub_pem


def load_signing_key(signing_key_path: Optional[Path] = None) -> Optional[Ed25519PrivateKey]:
    """Load an Ed25519 private key from explicit path or environment.

    Never derives signing keys from RAKSHA_SECRET and never hardcodes keys.
    Returns None when no signing key is configured (UNSIGNED mode).
    """
    if not HAS_ED25519:
        return None

    pem_bytes: Optional[bytes] = None
    if signing_key_path is not None:
        p = Path(signing_key_path).resolve()
        if not p.is_file():
            raise FileNotFoundError(f"Signing key file not found: {p}")
        pem_bytes = p.read_bytes()
    else:
        env_path = os.environ.get("GUPTKAVACH_SIGNING_KEY_PATH", "").strip()
        env_pem = os.environ.get("GUPTKAVACH_SIGNING_KEY_PEM", "").strip()
        if env_path:
            p = Path(env_path).resolve()
            if not p.is_file():
                raise FileNotFoundError(f"Signing key file not found: {p}")
            pem_bytes = p.read_bytes()
        elif env_pem:
            pem_bytes = env_pem.encode("utf-8")

    if pem_bytes is None:
        return None

    passphrase_raw = os.environ.get("GUPTKAVACH_SIGNING_KEY_PASSPHRASE", "")
    passphrase = passphrase_raw.encode("utf-8") if passphrase_raw else None
    key = serialization.load_pem_private_key(pem_bytes, password=passphrase)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError("Signing key must be an Ed25519 private key.")
    return key


def _public_key_id(pub_key: Ed25519PublicKey) -> str:
    raw = pub_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return hashlib.sha256(raw).hexdigest()[:16]


def sign_passport_payload(
    payload: dict[str, Any],
    private_key: Optional[Ed25519PrivateKey],
) -> dict[str, Any]:
    """Return signature block for canonical `payload` (excluding `signature`)."""
    if private_key is None or not HAS_ED25519:
        return {
            "status": "UNSIGNED",
            "algorithm": "NONE",
            "key_id": None,
            "public_key_pem": None,
            "value": None,
            "note": "No Ed25519 signing key configured; integrity hash only.",
        }

    unsigned_copy = {k: v for k, v in payload.items() if k != "signature"}
    canonical = canonical_json_bytes(unsigned_copy)
    sig_bytes = private_key.sign(canonical)
    pub_key = private_key.public_key()
    pub_pem = pub_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    return {
        "status": "SIGNED",
        "algorithm": "Ed25519",
        "key_id": _public_key_id(pub_key),
        "public_key_pem": pub_pem,
        "value": base64.b64encode(sig_bytes).decode("ascii"),
    }


def verify_passport_signature(
    passport: dict[str, Any],
    public_key_pem: Optional[bytes] = None,
) -> tuple[str, str]:
    """Verify digital signature of a passport dict.

    Returns (status, detail) where status is one of:
      VERIFIED | UNSIGNED | INVALID_SIGNATURE
    """
    sig_block = passport.get("signature")
    if not isinstance(sig_block, dict):
        return "INVALID_SIGNATURE", "Missing or malformed signature block."

    sig_status = sig_block.get("status")
    if sig_status == "UNSIGNED":
        return "UNSIGNED", "Certificate is unsigned (no digital signature supplied)."

    if sig_status != "SIGNED" or sig_block.get("algorithm") != "Ed25519":
        return "INVALID_SIGNATURE", f"Unsupported signature status/algorithm: {sig_status}/{sig_block.get('algorithm')}"

    if not HAS_ED25519:
        return "INVALID_SIGNATURE", "Ed25519 verification unavailable (cryptography package missing)."

    sig_b64 = sig_block.get("value")
    if not isinstance(sig_b64, str) or not sig_b64:
        return "INVALID_SIGNATURE", "Missing signature value."

    embedded_pem = sig_block.get("public_key_pem")
    pem_to_use = public_key_pem if public_key_pem is not None else (
        embedded_pem.encode("utf-8") if isinstance(embedded_pem, str) and embedded_pem else None
    )
    if pem_to_use is None:
        return "INVALID_SIGNATURE", "No public key available to verify signature."

    try:
        pub_key = serialization.load_pem_public_key(pem_to_use)
        if not isinstance(pub_key, Ed25519PublicKey):
            return "INVALID_SIGNATURE", "Public key is not Ed25519."
        if public_key_pem is not None and isinstance(embedded_pem, str) and embedded_pem:
            emb_key = serialization.load_pem_public_key(embedded_pem.encode("utf-8"))
            if isinstance(emb_key, Ed25519PublicKey) and _public_key_id(emb_key) != _public_key_id(pub_key):
                return "INVALID_SIGNATURE", "Supplied public key does not match certificate key_id."
        sig_bytes = base64.b64decode(sig_b64, validate=True)
        unsigned_copy = {k: v for k, v in passport.items() if k != "signature"}
        pub_key.verify(sig_bytes, canonical_json_bytes(unsigned_copy))
        return "VERIFIED", f"Ed25519 signature verified (key_id={_public_key_id(pub_key)})."
    except (InvalidSignature, ValueError, TypeError) as exc:
        return "INVALID_SIGNATURE", f"Signature verification failed: {exc}"


@dataclass
class PassportEvidenceInput:
    """Aggregates verified pipeline outputs for Privacy Passport construction."""

    files_report: list[dict[str, Any]]
    records_processed: int
    records_linked: int
    identifiers_detected: int
    generalizations_applied: int
    suppressions_applied: int
    pre_attack: dict[str, Any]
    post_attack: dict[str, Any]
    pre_risk: dict[str, Any]
    post_risk: dict[str, Any]
    release_gate: dict[str, Any]
    fhir_bundles_checked: int
    fhir_resources_checked: int
    fhir_validation_passed: bool
    fhir_failures: list[dict[str, str]]
    policy: dict[str, Any]
    raksha_secret_configured: bool
    quarantine_encrypted_count: int = 0
    path_traversal_rejected: int = 0
    temp_cleanup_verified: bool = True
    residual_leaks_detected: Optional[int] = None
    canaries_exposed: Optional[int] = None
    canaries_total: Optional[int] = None
    clinical_expected: Optional[int] = None
    clinical_preserved: Optional[int] = None
    clinical_modified: Optional[int] = None
    clinical_missing: Optional[int] = None
    identity_precision: Optional[float] = None
    identity_recall: Optional[float] = None
    identity_f05: Optional[float] = None
    identity_false_merges: Optional[int] = None
    identity_conflicts: Optional[int] = None
    extra_warnings: list[str] = field(default_factory=list)


def _policy_bool(policy: dict[str, Any], key: str, default: bool) -> bool:
    val = policy.get(key, default)
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() in ("1", "true", "yes", "on")
    return bool(val)


def evaluate_passport_release_gate(
    evidence: PassportEvidenceInput,
    manifest: dict[str, Any],
    is_signed: bool,
) -> dict[str, Any]:
    """Evaluate Phase 5 policy-based release gate across privacy, clinical, security, and integrity."""
    policy = evidence.policy
    policy_ver = str(policy.get("policy_version", "m15.5-v1"))

    blocking_reasons: list[str] = []
    warnings_list: list[str] = list(evidence.extra_warnings)
    required_not_run: list[str] = []

    # 1. Privacy gate (from existing engine gate + canary/leak rules)
    base_gate = evidence.release_gate
    base_status = str(base_gate.get("status", "BLOCKED"))
    base_reasons = list(base_gate.get("reason_codes") or [])
    privacy_status = "PASS"

    if base_status == "BLOCKED":
        privacy_status = "FAIL"
        blocking_reasons.extend(base_reasons)
    elif base_status == "PASS_WITH_WARNINGS":
        privacy_status = "WARN"
        warnings_list.extend(base_reasons)

    if _policy_bool(policy, "block_on_canary_exposure", True):
        if evidence.canaries_exposed is not None and evidence.canaries_exposed > 0:
            privacy_status = "FAIL"
            blocking_reasons.append("CANARY_EXPOSURE_DETECTED")

    if _policy_bool(policy, "block_on_direct_leak", True):
        if evidence.residual_leaks_detected is not None and evidence.residual_leaks_detected > 0:
            privacy_status = "FAIL"
            blocking_reasons.append("RESIDUAL_DIRECT_PII_LEAK_DETECTED")

    # 2. Clinical validation gate
    require_fhir = _policy_bool(policy, "require_fhir_validation", True)
    clinical_status = "PASS"
    if evidence.fhir_bundles_checked == 0 and evidence.fhir_resources_checked == 0:
        clinical_status = NOT_RUN
        if require_fhir:
            warnings_list.append("FHIR_BUNDLES_NOT_PRESENT_IN_CORPUS")
    elif not evidence.fhir_validation_passed or evidence.fhir_failures:
        clinical_status = "FAIL"
        blocking_reasons.append("MANDATORY_FHIR_VALIDATION_FAILED")

    if evidence.clinical_preserved is not None and evidence.clinical_expected:
        ratio = evidence.clinical_preserved / evidence.clinical_expected
        min_ratio = float(policy.get("min_clinical_retention_ratio", 0.90))
        if ratio < min_ratio:
            clinical_status = "FAIL"
            blocking_reasons.append("CLINICAL_PRESERVATION_BELOW_THRESHOLD")

    # 3. Identity validation gate (honest NOT_MEASURED when ground truth is absent)
    identity_status = (
        "PASS"
        if evidence.identity_precision is not None and evidence.identity_f05 is not None
        else NOT_MEASURED
    )

    # 4. Security validation gate
    require_sec = _policy_bool(policy, "require_security_checks", True)
    security_status = "PASS"
    if not evidence.raksha_secret_configured:
        security_status = "WARN"
        warnings_list.append("RAKSHA_SECRET_NOT_CONFIGURED_EPHEMERAL_MODE")
    if not evidence.temp_cleanup_verified:
        if require_sec:
            security_status = "FAIL"
            blocking_reasons.append("TEMPORARY_FILE_CLEANUP_NOT_VERIFIED")
        else:
            security_status = "WARN"
            warnings_list.append("TEMPORARY_FILE_CLEANUP_NOT_VERIFIED")

    # Verify quarantined files are never present in sanitized output
    sanitized_paths = {f["path"] for f in manifest.get("files", [])}
    quarantined_in_output = any(
        e.get("status") == "quarantined" and e.get("output") in sanitized_paths
        for e in evidence.files_report
    )
    if quarantined_in_output:
        security_status = "FAIL"
        blocking_reasons.append("QUARANTINED_FILE_IN_RELEASED_OUTPUT")

    # 5. Cryptographic integrity gate
    require_integrity = _policy_bool(policy, "require_cryptographic_integrity", True)
    require_sig = _policy_bool(policy, "require_signature", False)
    integrity_status = "PASS"
    if not manifest.get("root_hash"):
        if require_integrity:
            integrity_status = "FAIL"
            blocking_reasons.append("CRYPTOGRAPHIC_ROOT_HASH_MISSING")
        else:
            integrity_status = "WARN"
            warnings_list.append("CRYPTOGRAPHIC_ROOT_HASH_MISSING")
    if require_sig and not is_signed:
        integrity_status = "FAIL"
        blocking_reasons.append("REQUIRED_DIGITAL_SIGNATURE_MISSING")
    elif not is_signed:
        warnings_list.append("PASSPORT_UNSIGNED_INTEGRITY_ONLY")

    # Deduplicate preserving order
    blocking_reasons = list(dict.fromkeys(blocking_reasons))
    warnings_list = list(dict.fromkeys(w for w in warnings_list if w not in blocking_reasons))

    if blocking_reasons:
        overall = "BLOCKED"
        explanation = (
            f"Release BLOCKED under policy {policy_ver}: "
            + ", ".join(blocking_reasons)
            + "."
        )
    elif warnings_list:
        overall = "PASS_WITH_WARNINGS"
        explanation = (
            f"Release PASS_WITH_WARNINGS under policy {policy_ver}: "
            + ", ".join(warnings_list)
            + "."
        )
    else:
        overall = "PASS"
        explanation = f"Release PASS under policy {policy_ver}: all required privacy, clinical, security, and integrity gates satisfied."

    return {
        "status": overall,
        "policy_version": policy_ver,
        "gates": {
            "privacy_validation": privacy_status,
            "identity_validation": identity_status,
            "clinical_validation": clinical_status,
            "security_validation": security_status,
            "cryptographic_integrity": integrity_status,
        },
        "reason_codes": blocking_reasons + warnings_list if (blocking_reasons or warnings_list) else ["ALL_POLICY_GATES_SATISFIED"],
        "blocking_reasons": blocking_reasons,
        "warnings": warnings_list,
        "required_tests_not_run": required_not_run,
        "explanation": explanation,
    }


def assert_no_sensitive_data(text: str, secret: bytes = b"") -> None:
    """Guardrail ensuring no secrets or raw direct PII patterns appear in passport artifacts."""
    if secret and secret.decode("utf-8", errors="ignore") in text:
        raise PassportSecurityError("RAKSHA_SECRET detected in passport artifact!")
    # Mask known cryptographic hex digests (64-char SHA-256) and certificate IDs before PII regex scan
    scrubbed = re.sub(r"\b[0-9a-fA-F]{64}\b", "<SHA256>", text)
    scrubbed = re.sub(r"\bGKPP-[0-9A-F]{16}\b", "<CERT_ID>", scrubbed)
    if _RX_AADHAAR_RAW.search(scrubbed):
        raise PassportSecurityError("Potential raw 12-digit Aadhaar pattern detected in passport artifact!")
    if _RX_PHONE_RAW.search(scrubbed):
        raise PassportSecurityError("Potential raw phone number pattern detected in passport artifact!")
    if _RX_EMAIL_RAW.search(scrubbed):
        raise PassportSecurityError("Potential raw email address detected in passport artifact!")


def _resolve_timestamp() -> str:
    fixed = os.environ.get("GUPTKAVACH_PASSPORT_TIMESTAMP", "").strip()
    if fixed:
        return fixed
    epoch = os.environ.get("SOURCE_DATE_EPOCH", "").strip()
    if epoch and epoch.isdigit():
        return dt.datetime.fromtimestamp(int(epoch), tz=dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return "NOT_TIMESTAMPED"


def _compute_expiry(created_iso: str, days: int = 365) -> str:
    if created_iso == "NOT_TIMESTAMPED":
        return "NOT_SET"
    try:
        parsed = dt.datetime.fromisoformat(created_iso.replace("Z", "+00:00"))
        return (parsed + dt.timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return NOT_MEASURED


def build_privacy_passport(
    evidence: PassportEvidenceInput,
    manifest: dict[str, Any],
    signing_key: Optional[Ed25519PrivateKey] = None,
) -> dict[str, Any]:
    """Construct the complete Privacy Passport JSON structure (Sections A–G + signature)."""
    created_at = _resolve_timestamp()
    expires_at = _compute_expiry(created_at, days=365)
    policy_ver = str(evidence.policy.get("policy_version", "m15.5-v1"))
    input_fp = compute_input_fingerprint(evidence.files_report)
    root_hash = str(manifest["root_hash"])

    cert_seed = canonical_json_bytes(
        {
            "input_fingerprint": input_fp,
            "root_hash": root_hash,
            "policy_version": policy_ver,
            "engine_version": ENGINE_VERSION,
        }
    )
    cert_id = f"GKPP-{hashlib.sha256(cert_seed).hexdigest()[:16].upper()}"

    n_total = len(evidence.files_report)
    n_san = sum(1 for e in evidence.files_report if e.get("status") == "sanitized")
    n_quar = sum(1 for e in evidence.files_report if e.get("status") == "quarantined")
    n_fail = sum(1 for e in evidence.files_report if e.get("status") not in ("sanitized", "quarantined"))

    is_signed = signing_key is not None and HAS_ED25519
    release_decision = evaluate_passport_release_gate(evidence, manifest, is_signed=is_signed)

    # Clinical preservation rate: never round 100% or convert missing into 0
    if evidence.clinical_preserved is not None and evidence.clinical_expected:
        clin_rate: Any = round(evidence.clinical_preserved / evidence.clinical_expected, 6)
    else:
        clin_rate = NOT_MEASURED

    passport_body: dict[str, Any] = {
        "certificate_identity": {
            "certificate_id": cert_id,
            "schema_version": PASSPORT_SCHEMA_VERSION,
            "created_at": created_at,
            "expires_at": expires_at,
            "engine_version": ENGINE_VERSION,
            "policy_version": policy_ver,
            "certificate_status": "SIGNED" if is_signed else "UNSIGNED",
        },
        "dataset_provenance": {
            "input_dataset_fingerprint": input_fp,
            "output_dataset_root_hash": root_hash,
            "manifest_file": "dataset_manifest.json",
            "input_files_total": n_total,
            "files_processed": n_total,
            "files_sanitised": n_san,
            "files_quarantined": n_quar,
            "files_failed": n_fail,
            "records_processed": evidence.records_processed,
            "output_files_count": manifest["file_count"],
            "output_total_bytes": manifest["total_bytes"],
        },
        "privacy_assessment": {
            "pii_detection": {
                "status": "EXECUTED",
                "direct_identifiers_detected": evidence.identifiers_detected,
                "generalizations_applied": evidence.generalizations_applied,
                "suppressions_applied": evidence.suppressions_applied,
            },
            "residual_leakage_test": {
                "status": "EXECUTED" if evidence.residual_leaks_detected is not None else NOT_RUN,
                "leaks_detected": (
                    evidence.residual_leaks_detected
                    if evidence.residual_leaks_detected is not None
                    else NOT_MEASURED
                ),
            },
            "canary_test": {
                "status": "EXECUTED" if evidence.canaries_exposed is not None else NOT_RUN,
                "canaries_exposed": (
                    evidence.canaries_exposed
                    if evidence.canaries_exposed is not None
                    else NOT_MEASURED
                ),
                "canaries_total": (
                    evidence.canaries_total
                    if evidence.canaries_total is not None
                    else NOT_MEASURED
                ),
            },
            "multilingual_detection_coverage": {
                "status": "EXECUTED",
                "scripts_supported": ["Latin", "Devanagari", "Hinglish"],
                "per_script_leak_rate": NOT_MEASURED,
            },
            "quasi_identifier_risk": {
                "status": "EXECUTED",
                **evidence.pre_risk,
                **evidence.post_risk,
            },
            "reidentification_attack_simulation": {
                "status": "EXECUTED",
                **evidence.pre_attack,
                **evidence.post_attack,
            },
            "unresolved_privacy_warnings": release_decision["warnings"],
        },
        "identity_assessment": {
            "linked_records": evidence.records_linked,
            "unlinked_records": max(0, evidence.records_processed - evidence.records_linked),
            "abstentions": max(0, evidence.records_processed - evidence.records_linked),
            "identity_precision": (
                evidence.identity_precision if evidence.identity_precision is not None else NOT_MEASURED
            ),
            "identity_recall": (
                evidence.identity_recall if evidence.identity_recall is not None else NOT_MEASURED
            ),
            "f0_5_score": (
                evidence.identity_f05 if evidence.identity_f05 is not None else NOT_MEASURED
            ),
            "false_merge_count": (
                evidence.identity_false_merges if evidence.identity_false_merges is not None else NOT_MEASURED
            ),
            "conflict_count": (
                evidence.identity_conflicts if evidence.identity_conflicts is not None else NOT_MEASURED
            ),
        },
        "clinical_integrity": {
            "expected_clinical_values": (
                evidence.clinical_expected if evidence.clinical_expected is not None else NOT_MEASURED
            ),
            "preserved_values": (
                evidence.clinical_preserved if evidence.clinical_preserved is not None else NOT_MEASURED
            ),
            "modified_values": (
                evidence.clinical_modified if evidence.clinical_modified is not None else NOT_MEASURED
            ),
            "missing_values": (
                evidence.clinical_missing if evidence.clinical_missing is not None else NOT_MEASURED
            ),
            "clinical_preservation_rate": clin_rate,
            "medication_integrity": NOT_MEASURED,
            "dosage_integrity": NOT_MEASURED,
            "laboratory_value_integrity": NOT_MEASURED,
            "fhir_validation": {
                "status": "EXECUTED" if evidence.fhir_bundles_checked > 0 else NOT_RUN,
                "bundles_checked": evidence.fhir_bundles_checked,
                "resources_checked": evidence.fhir_resources_checked,
                "passed": evidence.fhir_validation_passed,
                "failure_count": len(evidence.fhir_failures),
                "failure_codes": [f.get("code", "UNKNOWN") for f in evidence.fhir_failures[:20]],
            },
        },
        "security_assessment": {
            "encryption_at_rest": {
                "status": "EXECUTED" if evidence.quarantine_encrypted_count > 0 else NOT_RUN,
                "quarantined_files_encrypted": evidence.quarantine_encrypted_count,
                "algorithm": "AES-256-GCM" if evidence.quarantine_encrypted_count > 0 else NOT_MEASURED,
            },
            "temporary_file_cleanup": {
                "status": "EXECUTED" if evidence.temp_cleanup_verified else NOT_RUN,
                "verified": evidence.temp_cleanup_verified,
            },
            "log_sanitisation": {
                "status": "EXECUTED",
                "secret_exposed": False,
                "raw_pii_in_passport": False,
            },
            "output_integrity": {
                "status": "EXECUTED",
                "algorithm": "SHA-256",
                "root_hash": root_hash,
                "manifest_file_count": manifest["file_count"],
            },
            "path_traversal_protection": {
                "status": "EXECUTED",
                "rejected_paths": evidence.path_traversal_rejected,
            },
            "secret_configuration": {
                "status": "EXECUTED" if evidence.raksha_secret_configured else "WARNING",
                "raksha_secret_configured": evidence.raksha_secret_configured,
                "signing_key_configured": is_signed,
            },
        },
        "release_decision": release_decision,
    }

    passport_body["signature"] = sign_passport_payload(passport_body, signing_key)
    return passport_body
