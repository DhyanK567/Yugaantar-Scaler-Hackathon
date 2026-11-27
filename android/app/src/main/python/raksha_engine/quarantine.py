"""Encrypted Quarantine Subsystem.
Implements authenticated encryption at rest for unparseable, malformed, or malicious files.
Guarantees:
- Original file contents are encrypted with a dedicated quarantine key (AES-256-GCM)
- Cryptographic SHA-256 digest is generated for tamper detection and audit logging
- Stored records contain zero unencrypted patient information
- Quarantine reason codes and safe structural metadata are stored separately
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .crypto import (
    CryptographicError,
    GuptKavachKeyRing,
    decrypt_payload,
    encrypt_payload,
)
from .secure_fs import verify_path_containment


@dataclass
class QuarantineMetadata:
    rel_path: str
    original_sha256: str
    quarantine_reason: str
    timestamp: float
    file_size_bytes: int
    is_encrypted: bool = True
    cipher_algorithm: str = "AES-256-GCM"


class QuarantineVault:
    """Manages secure encrypted isolation of quarantined files."""

    def __init__(self, vault_dir: Path, keyring: GuptKavachKeyRing):
        self.vault_dir = Path(vault_dir).resolve()
        self.vault_dir.mkdir(parents=True, exist_ok=True)
        self.keyring = keyring
        self.records_file = self.vault_dir / "quarantine_manifest.jsonl"

    def quarantine_file(
        self,
        rel_path: str,
        raw_bytes: bytes,
        reason: str,
        timestamp: float,
    ) -> Path:
        """Encrypts and safely vaults an unparseable input file."""
        import hashlib

        orig_sha = hashlib.sha256(raw_bytes).hexdigest()
        safe_name = f"{orig_sha[:16]}.vault"
        dest_path = verify_path_containment(self.vault_dir / safe_name, self.vault_dir)

        # Encrypt with dedicated quarantine subkey
        aad = f"rel:{rel_path}|sha:{orig_sha}".encode("utf-8")
        encrypted_envelope = encrypt_payload(
            plaintext=raw_bytes,
            key=self.keyring.quarantine_key,
            associated_data=aad,
            cipher_type="aes_gcm",
        )

        with open(dest_path, "wb") as f:
            f.write(encrypted_envelope)

        # Record non-sensitive metadata in manifest
        meta = QuarantineMetadata(
            rel_path=rel_path,
            original_sha256=orig_sha,
            quarantine_reason=reason,
            timestamp=timestamp,
            file_size_bytes=len(raw_bytes),
        )
        with open(self.records_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(meta)) + "\n")

        return dest_path

    def inspect_quarantined_payload(
        self,
        vault_filename: str,
        expected_rel_path: str,
        expected_sha256: str,
    ) -> bytes:
        """Authenticates and decrypts a quarantined payload for security analysis."""
        vault_path = verify_path_containment(self.vault_dir / vault_filename, self.vault_dir)
        aad = f"rel:{expected_rel_path}|sha:{expected_sha256}".encode("utf-8")
        envelope = vault_path.read_bytes()
        return decrypt_payload(envelope, self.keyring.quarantine_key, associated_data=aad)
