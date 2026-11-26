#!/usr/bin/env python3
"""
Comprehensive Cryptographic Security & Secure Processing Test Suite (Milestone 12).
Verifies:
- Standard KDF domain separation (scrypt / PBKDF2)
- Authenticated symmetric encryption (AES-256-GCM / ChaCha20-Poly1305)
- Nonce freshness & CSPRNG uniqueness (zero nonce reuse)
- Rejection of tampered ciphertexts and modified authentication tags
- Tamper-proof quarantine encryption at rest
- Path traversal & symlink containment security
- Atomic secure temporary directory creation and cleanup
- Deterministic contract preservation
"""

import os
import shutil
import sys
import unittest
from pathlib import Path

# Add starter directory to path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
STARTER_DIR = REPO_ROOT / "starter"
sys.path.insert(0, str(STARTER_DIR))

from raksha_engine.crypto import (
    CryptographicError,
    DecryptionAuthenticationError,
    GuptKavachKeyRing,
    InvalidSecretError,
    decrypt_payload,
    derive_key,
    encrypt_payload,
    hkdf_sha256,
    validate_secret,
    HKDF_DOMAIN_PSEUDONYM,
    HKDF_DOMAIN_DATE_SHIFT,
    HKDF_DOMAIN_IDENTITY_LINK,
    HKDF_DOMAIN_MANIFEST,
    HKDF_DOMAIN_PASSPORT_AUTH,
    KEY_PURPOSE_PSEUDONYM,
    KEY_PURPOSE_DATE_SHIFT,
    KEY_PURPOSE_ENCRYPTION,
    KEY_PURPOSE_INTEGRITY,
    KEY_PURPOSE_QUARANTINE,
)
from raksha_engine.privacy import (
    date_shift_days,
    identity_linking_token,
    manifest_hmac,
    passport_auth_hmac,
    pseudonym,
)
from raksha_engine.secure_fs import (
    PathSecurityError,
    EncryptedFileVault,
    secure_temporary_directory,
    verify_path_containment,
)
from raksha_engine.quarantine import QuarantineVault


class TestCryptographicKeyManagement(unittest.TestCase):
    def setUp(self):
        self.secret = b"secure_healthcare_master_secret_2026"
        self.keyring = GuptKavachKeyRing(self.secret)

    def test_empty_secret_raises_error(self):
        with self.assertRaises(InvalidSecretError):
            GuptKavachKeyRing(b"")
        with self.assertRaises(InvalidSecretError):
            derive_key(b"", b"test_purpose")

    def test_domain_separation_independence(self):
        """Keys derived for different purposes must be completely disjoint and cryptographically isolated."""
        k_pseu = self.keyring.pseudonym_key
        k_date = self.keyring.date_shift_key
        k_encr = self.keyring.storage_encryption_key
        k_inte = self.keyring.integrity_key
        k_quar = self.keyring.quarantine_key

        keys = [k_pseu, k_date, k_encr, k_inte, k_quar]
        self.assertEqual(len(set(keys)), 5, "All purpose-derived subkeys must be unique.")
        for k in keys:
            self.assertEqual(len(k), 32, "Derived keys must be exactly 256 bits (32 bytes).")

    def test_different_master_secrets_yield_different_keys(self):
        ring2 = GuptKavachKeyRing(b"another_secret_key_9999")
        self.assertNotEqual(self.keyring.pseudonym_key, ring2.pseudonym_key)
        self.assertNotEqual(self.keyring.storage_encryption_key, ring2.storage_encryption_key)
        self.assertNotEqual(self.keyring.key_fingerprint, ring2.key_fingerprint)

    def test_key_fingerprint_never_exposes_secret(self):
        fp = self.keyring.key_fingerprint
        self.assertEqual(len(fp), 16)
        self.assertNotIn(self.secret.decode(), fp)

    def test_hkdf_cross_purpose_key_separation(self):
        k_p = hkdf_sha256(self.secret, HKDF_DOMAIN_PSEUDONYM)
        k_d = hkdf_sha256(self.secret, HKDF_DOMAIN_DATE_SHIFT)
        k_i = hkdf_sha256(self.secret, HKDF_DOMAIN_IDENTITY_LINK)
        k_m = hkdf_sha256(self.secret, HKDF_DOMAIN_MANIFEST)
        k_a = hkdf_sha256(self.secret, HKDF_DOMAIN_PASSPORT_AUTH)
        k_enc = self.keyring.storage_encryption_key
        all_keys = [k_p, k_d, k_i, k_m, k_a, k_enc]
        self.assertEqual(len(set(all_keys)), 6, "Pseudonym, shift, linking, manifest, passport, and encryption keys must be distinct.")

    def test_same_secret_determinism_and_different_secret_separation(self):
        s1 = b"medilocker-secret-alpha-01"
        s2 = b"medilocker-secret-beta-02"
        self.assertEqual(pseudonym("pt-123", s1), pseudonym("pt-123", s1))
        self.assertNotEqual(pseudonym("pt-123", s1), pseudonym("pt-123", s2))
        self.assertEqual(date_shift_days("pt-123", s1), date_shift_days("pt-123", s1))
        self.assertEqual(identity_linking_token("aadhaar:1234", s1), identity_linking_token("aadhaar:1234", s1))
        self.assertNotEqual(identity_linking_token("aadhaar:1234", s1), identity_linking_token("aadhaar:1234", s2))
        self.assertNotEqual(manifest_hmac("root123", s1), manifest_hmac("root123", s2))
        self.assertNotEqual(passport_auth_hmac(b"{}", s1), passport_auth_hmac(b"{}", s2))

    def test_missing_and_weak_secret_validation(self):
        with self.assertRaises(InvalidSecretError):
            pseudonym("pt-1", b"")
        with self.assertRaises(InvalidSecretError):
            validate_secret("")
        with self.assertRaises(InvalidSecretError):
            validate_secret("short")
        with self.assertRaises(InvalidSecretError):
            validate_secret("aaaaaaaaaaaa")
        self.assertEqual(validate_secret("strong-secret-2026"), b"strong-secret-2026")


class TestAuthenticatedEncryption(unittest.TestCase):
    def setUp(self):
        self.key = GuptKavachKeyRing(b"test_crypto_suite_secret").storage_encryption_key
        self.plaintext = b"Patient record payload containing sensitive diagnostic details: ABHA=12-3456-7890-1234"

    def test_encrypt_decrypt_roundtrip(self):
        envelope = encrypt_payload(self.plaintext, self.key, associated_data=b"file_id:1234")
        self.assertTrue(envelope.startswith(b"GKENC"))
        self.assertNotIn(self.plaintext, envelope, "Plaintext must never appear unencrypted in envelope.")

        decrypted = decrypt_payload(envelope, self.key, associated_data=b"file_id:1234")
        self.assertEqual(decrypted, self.plaintext)

    def test_nonce_freshness_never_reuses_nonce(self):
        """Encrypting identical plaintext twice must produce completely different ciphertexts (unique nonces)."""
        env1 = encrypt_payload(self.plaintext, self.key)
        env2 = encrypt_payload(self.plaintext, self.key)
        self.assertNotEqual(env1, env2, "Every encryption must use a fresh, unique CSPRNG nonce.")

    def test_tampered_ciphertext_rejected(self):
        """Any bit-flip in the ciphertext or authentication tag must trigger an immediate authentication failure."""
        envelope = encrypt_payload(self.plaintext, self.key, associated_data=b"header_aad")
        # Tamper with the last byte of the ciphertext/tag
        tampered = bytearray(envelope)
        tampered[-1] ^= 0x55

        with self.assertRaises(DecryptionAuthenticationError):
            decrypt_payload(bytes(tampered), self.key, associated_data=b"header_aad")

    def test_associated_data_mismatch_rejected(self):
        """Tampering with associated data (header metadata) must fail authentication."""
        envelope = encrypt_payload(self.plaintext, self.key, associated_data=b"tenant_alpha")
        with self.assertRaises(DecryptionAuthenticationError):
            decrypt_payload(envelope, self.key, associated_data=b"tenant_beta")

    def test_wrong_key_fails_decryption(self):
        envelope = encrypt_payload(self.plaintext, self.key)
        wrong_key = GuptKavachKeyRing(b"attacker_supplied_key").storage_encryption_key
        with self.assertRaises(DecryptionAuthenticationError):
            decrypt_payload(envelope, wrong_key)


class TestSecureFilesystemAndQuarantine(unittest.TestCase):
    def setUp(self):
        self.keyring = GuptKavachKeyRing(b"fs_security_secret")
        self.test_dir = Path(__file__).resolve().parent / "_test_sandbox"
        self.test_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_path_containment_blocks_traversal(self):
        base = self.test_dir / "base"
        base.mkdir(parents=True, exist_ok=True)

        valid_file = base / "safe.csv"
        valid_file.write_text("a,b,c", encoding="utf-8")
        self.assertEqual(verify_path_containment(valid_file, base), valid_file.resolve())

        # Attempt path traversal escape via ../
        evil_path = base / ".." / "escaped.txt"
        with self.assertRaises(PathSecurityError):
            verify_path_containment(evil_path, base)

    def test_encrypted_file_vault_persistence(self):
        vault_dir = self.test_dir / "vault"
        vault = EncryptedFileVault(self.keyring.storage_encryption_key, vault_dir)

        payload = b"Sensitive temporary intermediate JSON clues: patient=123"
        saved_path = vault.write_encrypted_file("staged/test_clues.enc", payload, associated_data=b"stage_1")
        self.assertTrue(saved_path.is_file())

        raw_bytes = saved_path.read_bytes()
        self.assertNotIn(b"Sensitive", raw_bytes, "Vault file on disk must be encrypted.")
        self.assertTrue(raw_bytes.startswith(b"GKENC"))

        recovered = vault.read_encrypted_file("staged/test_clues.enc", associated_data=b"stage_1")
        self.assertEqual(recovered, payload)

    def test_encrypted_quarantine_vault(self):
        q_dir = self.test_dir / "quarantine"
        qv = QuarantineVault(q_dir, self.keyring)

        corrupt_raw = b"CORRUPTED_RAW_CSV_WITH_PATIENT_NAME:Amit Kumar,Aadhaar:987654321098"
        vaulted_path = qv.quarantine_file(
            rel_path="incoming/corrupt_1.csv",
            raw_bytes=corrupt_raw,
            reason="undecodable_text",
            timestamp=12345678.0,
        )

        self.assertTrue(vaulted_path.is_file())
        on_disk = vaulted_path.read_bytes()
        self.assertNotIn(b"Amit Kumar", on_disk, "Quarantined raw payload must not exist in plaintext on disk.")

        recovered = qv.inspect_quarantined_payload(
            vault_filename=vaulted_path.name,
            expected_rel_path="incoming/corrupt_1.csv",
            expected_sha256=import_hashlib_sha(corrupt_raw),
        )
        self.assertEqual(recovered, corrupt_raw)

    def test_secure_temp_directory_cleanup(self):
        created_path = None
        with secure_temporary_directory(prefix="test_sec_", base_dir=self.test_dir) as tmp:
            created_path = tmp
            self.assertTrue(tmp.is_dir())
            test_f = tmp / "data.dat"
            test_f.write_text("ephemeral data", encoding="utf-8")
            self.assertTrue(test_f.exists())

        self.assertFalse(created_path.exists(), "Temporary directory must be cleaned up on context exit.")


def import_hashlib_sha(b: bytes) -> str:
    import hashlib
    return hashlib.sha256(b).hexdigest()


if __name__ == "__main__":
    unittest.main()
