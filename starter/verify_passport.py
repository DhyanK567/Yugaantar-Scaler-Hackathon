#!/usr/bin/env python3
"""Independent Offline Verifier for GuptKavach Privacy Passport.

Usage:
  python3 verify_passport.py --passport path/to/privacy_passport.json --output path/to/sanitised_dataset

Exit codes:
  0 -> VERIFIED or UNSIGNED (unless --require-signature is set)
  1 -> TAMPERED, INCOMPLETE, INVALID_SIGNATURE, INVALID_CERTIFICATE, or UNSIGNED with --require-signature
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path
from typing import Any

from raksha_engine.passport import (
    MANIFEST_SCHEMA_VERSION,
    SUPPORTED_SCHEMA_VERSIONS,
    compute_manifest_root_hash,
    stream_sha256,
    verify_passport_signature,
)
from raksha_engine.secure_fs import PathSecurityError, verify_path_containment

REQUIRED_SECTIONS = (
    "certificate_identity",
    "dataset_provenance",
    "privacy_assessment",
    "identity_assessment",
    "clinical_integrity",
    "security_assessment",
    "release_decision",
    "signature",
)


def _resolve_sanitized_root(output_arg: Path) -> Path:
    resolved = output_arg.resolve()
    if (resolved / "sanitized").is_dir():
        return (resolved / "sanitized").resolve()
    return resolved


def _check_expiry(expires_at: Any) -> tuple[bool, str | None]:
    if not isinstance(expires_at, str) or not expires_at or expires_at in ("NOT_MEASURED", "NOT_SET"):
        return True, None
    try:
        exp_dt = dt.datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        if dt.datetime.now(tz=dt.timezone.utc) > exp_dt:
            return False, f"Certificate expired at {expires_at}."
        return True, None
    except ValueError:
        return False, f"Malformed expires_at timestamp: {expires_at}"


def verify_passport_bundle(
    passport_path: Path,
    output_dir: Path,
    manifest_path: Path | None = None,
    public_key_path: Path | None = None,
    require_signature: bool = False,
) -> dict[str, Any]:
    """Independently verify a Privacy Passport against a sanitised output directory."""
    if not passport_path.is_file():
        return {"status": "INVALID_CERTIFICATE", "valid": False, "details": [f"Passport file not found: {passport_path}"]}

    try:
        passport = json.loads(passport_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {"status": "INVALID_CERTIFICATE", "valid": False, "details": [f"Malformed passport JSON: {exc}"]}

    if not isinstance(passport, dict):
        return {"status": "INVALID_CERTIFICATE", "valid": False, "details": ["Passport root must be a JSON object."]}

    missing_sections = [s for s in REQUIRED_SECTIONS if not isinstance(passport.get(s), dict)]
    if missing_sections:
        return {
            "status": "INVALID_CERTIFICATE",
            "valid": False,
            "details": [f"Missing or invalid required sections: {', '.join(missing_sections)}"],
        }

    ci = passport["certificate_identity"]
    schema_ver = ci.get("schema_version")
    if schema_ver not in SUPPORTED_SCHEMA_VERSIONS:
        return {
            "status": "INVALID_CERTIFICATE",
            "valid": False,
            "details": [f"Unsupported schema_version: {schema_ver}"],
        }

    not_expired, exp_err = _check_expiry(ci.get("expires_at"))
    if not not_expired:
        return {"status": "INVALID_CERTIFICATE", "valid": False, "details": [exp_err or "Certificate expired."]}

    dp = passport["dataset_provenance"]
    expected_root_hash = dp.get("output_dataset_root_hash")
    if not isinstance(expected_root_hash, str) or len(expected_root_hash) != 64:
        return {
            "status": "INVALID_CERTIFICATE",
            "valid": False,
            "details": ["Invalid or missing output_dataset_root_hash in dataset_provenance."],
        }

    # Resolve manifest path
    manifest_file_name = str(dp.get("manifest_file") or "dataset_manifest.json")
    m_path = manifest_path.resolve() if manifest_path else (passport_path.resolve().parent / manifest_file_name)
    if not m_path.is_file():
        return {"status": "INVALID_CERTIFICATE", "valid": False, "details": [f"Manifest file not found: {m_path}"]}

    try:
        manifest = json.loads(m_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {"status": "INVALID_CERTIFICATE", "valid": False, "details": [f"Malformed manifest JSON: {exc}"]}

    if (
        not isinstance(manifest, dict)
        or manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION
        or not isinstance(manifest.get("files"), list)
    ):
        return {"status": "INVALID_CERTIFICATE", "valid": False, "details": ["Invalid manifest schema or missing files list."]}

    expected_entries: dict[str, dict[str, Any]] = {}
    for ent in manifest["files"]:
        if not isinstance(ent, dict) or "path" not in ent or "sha256" not in ent or "size_bytes" not in ent:
            return {"status": "INVALID_CERTIFICATE", "valid": False, "details": ["Malformed entry in dataset_manifest.json."]}
        norm_p = str(ent["path"]).replace("\\", "/")
        expected_entries[norm_p] = {
            "path": norm_p,
            "sha256": str(ent["sha256"]).lower(),
            "size_bytes": int(ent["size_bytes"]),
        }

    # Recompute manifest root hash from manifest entries (independent of order)
    recomputed_manifest_root = compute_manifest_root_hash(list(expected_entries.values()))
    if recomputed_manifest_root != expected_root_hash:
        return {
            "status": "TAMPERED",
            "valid": False,
            "details": ["Manifest root hash does not match certificate output_dataset_root_hash."],
        }

    # Verify digital signature before or alongside file checks
    pub_pem: bytes | None = None
    if public_key_path is not None:
        if not public_key_path.is_file():
            return {"status": "INVALID_SIGNATURE", "valid": False, "details": [f"Public key not found: {public_key_path}"]}
        pub_pem = public_key_path.read_bytes()

    sig_status, sig_detail = verify_passport_signature(passport, public_key_pem=pub_pem)
    if sig_status == "INVALID_SIGNATURE":
        return {"status": "INVALID_SIGNATURE", "valid": False, "details": [sig_detail]}

    # Walk output directory and recompute every file hash
    san_root = _resolve_sanitized_root(output_dir)
    if not san_root.is_dir():
        return {"status": "INCOMPLETE", "valid": False, "details": [f"Output directory not found: {san_root}"]}

    actual_entries: dict[str, dict[str, Any]] = {}
    for dirpath, dirnames, filenames in os.walk(san_root):
        dirnames.sort()
        for fname in sorted(filenames):
            fpath = Path(dirpath) / fname
            try:
                resolved = verify_path_containment(fpath, san_root)
            except PathSecurityError as exc:
                return {"status": "TAMPERED", "valid": False, "details": [str(exc)]}
            if not resolved.is_file():
                continue
            rel = resolved.relative_to(san_root).as_posix()
            sha, size = stream_sha256(resolved)
            actual_entries[rel] = {"path": rel, "sha256": sha, "size_bytes": size}

    missing_files = sorted(set(expected_entries) - set(actual_entries))
    unexpected_files = sorted(set(actual_entries) - set(expected_entries))
    modified_files = sorted(
        p for p in (set(expected_entries) & set(actual_entries))
        if expected_entries[p]["sha256"] != actual_entries[p]["sha256"]
        or expected_entries[p]["size_bytes"] != actual_entries[p]["size_bytes"]
    )

    if missing_files and not modified_files and not unexpected_files:
        return {
            "status": "INCOMPLETE",
            "valid": False,
            "details": [f"Missing {len(missing_files)} expected output file(s): {', '.join(missing_files[:5])}"],
            "missing_files": missing_files,
        }

    if missing_files or unexpected_files or modified_files:
        details: list[str] = []
        if modified_files:
            details.append(f"Modified files ({len(modified_files)}): {', '.join(modified_files[:5])}")
        if unexpected_files:
            details.append(f"Unexpected files ({len(unexpected_files)}): {', '.join(unexpected_files[:5])}")
        if missing_files:
            details.append(f"Missing files ({len(missing_files)}): {', '.join(missing_files[:5])}")
        return {
            "status": "TAMPERED",
            "valid": False,
            "details": details,
            "modified_files": modified_files,
            "unexpected_files": unexpected_files,
            "missing_files": missing_files,
        }

    actual_root_hash = compute_manifest_root_hash(list(actual_entries.values()))
    if actual_root_hash != expected_root_hash:
        return {
            "status": "TAMPERED",
            "valid": False,
            "details": ["Recomputed dataset root hash does not match certificate root hash."],
        }

    if sig_status == "UNSIGNED":
        if require_signature:
            return {
                "status": "UNSIGNED",
                "valid": False,
                "details": ["Integrity verified, but certificate is UNSIGNED and --require-signature was specified."],
                "root_hash": actual_root_hash,
                "files_verified": len(actual_entries),
            }
        return {
            "status": "UNSIGNED",
            "valid": True,
            "details": [
                "UNSIGNED: Output integrity verified (all hashes and root hash match), "
                "but no digital signature was supplied."
            ],
            "root_hash": actual_root_hash,
            "files_verified": len(actual_entries),
        }

    return {
        "status": "VERIFIED",
        "valid": True,
        "details": [
            f"VERIFIED: Certificate signature and all {len(actual_entries)} output file hashes match.",
            sig_detail,
        ],
        "root_hash": actual_root_hash,
        "files_verified": len(actual_entries),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Independent offline verifier for GuptKavach Privacy Passport")
    ap.add_argument("--passport", required=True, help="Path to privacy_passport.json")
    ap.add_argument("--output", required=True, help="Path to output directory (or sanitized/ subdirectory)")
    ap.add_argument("--manifest", default=None, help="Optional explicit path to dataset_manifest.json")
    ap.add_argument("--public-key", default=None, help="Optional Ed25519 public key PEM file")
    ap.add_argument("--require-signature", action="store_true", help="Fail if certificate is UNSIGNED")
    ap.add_argument("--json", action="store_true", help="Print verification result as JSON")
    a = ap.parse_args()

    res = verify_passport_bundle(
        passport_path=Path(a.passport),
        output_dir=Path(a.output),
        manifest_path=Path(a.manifest) if a.manifest else None,
        public_key_path=Path(a.public_key) if a.public_key else None,
        require_signature=a.require_signature,
    )

    if a.json:
        print(json.dumps(res, indent=2))
    else:
        print(f"STATUS: {res['status']}")
        for d in res.get("details", []):
            print(f"  - {d}")

    return 0 if res.get("valid") else 1


if __name__ == "__main__":
    sys.exit(main())
