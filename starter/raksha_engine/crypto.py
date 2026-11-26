"""GuptKavach Cryptographic Engine & Key Management Subsystem.
Implements:
- Standard Key Derivation Function (scrypt / PBKDF2-HMAC-SHA256) with domain separation
- Purpose-separated subkeys: Pseudonyms, Date-Shifting, Encryption-At-Rest, Integrity Verification
- Authenticated Encryption at Rest (AES-256-GCM / ChaCha20-Poly1305) with CSPRNG nonces
- Envelope encryption format with key versioning and authentication tag verification
- Zero plaintext fallback: tampered or corrupted ciphertexts are strictly rejected
- Standard library fallback for environments without external packages
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import struct
from typing import Dict, Optional, Tuple

# Try importing standard cryptography library for AES-256-GCM / ChaCha20-Poly1305
# Silence any deprecation warning emitted by cryptography library on legacy runtimes
import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM, ChaCha20Poly1305
        HAS_CRYPTOGRAPHY = True
    except (ImportError, Exception):
        HAS_CRYPTOGRAPHY = False



# Version identifier for encrypted envelope payloads
ENVELOPE_MAGIC = b"GKENC"
ENVELOPE_VERSION = 1

# Cryptographic purpose separation domains
KEY_PURPOSE_PSEUDONYM = b"guptkavach:v1:pseudonymization"
KEY_PURPOSE_DATE_SHIFT = b"guptkavach:v1:date-shifting"
KEY_PURPOSE_ENCRYPTION = b"guptkavach:v1:aes-256-gcm-storage"
KEY_PURPOSE_INTEGRITY = b"guptkavach:v1:hmac-integrity-check"
KEY_PURPOSE_QUARANTINE = b"guptkavach:v1:quarantine-vault"

# RFC 5869 HKDF-SHA256 domain separation labels
HKDF_DOMAIN_PSEUDONYM = b"medilocker:v1:patient-pseudonym"
HKDF_DOMAIN_DATE_SHIFT = b"medilocker:v1:date-shift"
HKDF_DOMAIN_IDENTITY_LINK = b"medilocker:v1:identity-linking"
HKDF_DOMAIN_MANIFEST = b"medilocker:v1:manifest-integrity"
HKDF_DOMAIN_PASSPORT_AUTH = b"medilocker:v1:passport-auth"
HKDF_DOMAIN_FILENAME = b"medilocker:v1:filename-pseudonym"


def hkdf_extract(salt: Optional[bytes], ikm: bytes) -> bytes:
    """RFC 5869 HKDF-Extract using HMAC-SHA256."""
    effective_salt = salt if salt else b"\x00" * 32
    return hmac.new(effective_salt, ikm, hashlib.sha256).digest()


def hkdf_expand(prk: bytes, info: bytes, length: int = 32) -> bytes:
    """RFC 5869 HKDF-Expand using HMAC-SHA256."""
    if length <= 0 or length > 255 * 32:
        raise ValueError("Invalid HKDF output length.")
    okm = b""
    t = b""
    counter = 1
    while len(okm) < length:
        t = hmac.new(prk, t + info + bytes([counter]), hashlib.sha256).digest()
        okm += t
        counter += 1
    return okm[:length]


def hkdf_sha256(ikm: bytes, info: bytes, salt: Optional[bytes] = None, length: int = 32) -> bytes:
    """Derives an independent purpose-specific key using RFC 5869 HKDF-SHA256."""
    if not ikm:
        raise InvalidSecretError("Input keying material (RAKSHA_SECRET) cannot be empty.")
    prk = hkdf_extract(salt or b"medilocker:hkdf:salt:v1", ikm)
    return hkdf_expand(prk, info, length=length)


def pseudonymous_filename_token(rel_posix: str, raw_sha256: str, secret: bytes, length: int = 12) -> str:
    """Derive a deterministic, domain-separated pseudonymous filename token.

    Uses HKDF-SHA256 with HKDF_DOMAIN_FILENAME when secret is present so
    output filenames never use an unsalted hash of patient identifiers and
    change whenever RAKSHA_SECRET changes.
    """
    if secret:
        fn_key = hkdf_sha256(secret, HKDF_DOMAIN_FILENAME)
    else:
        fn_key = hmac.new(b"medilocker:v1:filename-ephemeral", HKDF_DOMAIN_FILENAME, hashlib.sha256).digest()
    msg = f"{rel_posix}|{raw_sha256}".encode("utf-8", errors="replace")
    raw = hmac.new(fn_key, msg, hashlib.sha256).hexdigest()
    # Format with 'fn' prefix and 'x' separator so >=6 consecutive digits can never occur
    # (prevents false positives in Aadhaar/phone digit-pattern guards on passport artifacts).
    token = f"fn{raw[:5]}x{raw[5:10]}"
    return token[:length] if length <= len(token) else f"{token}{raw[10:10 + (length - len(token))]}"


def validate_secret(secret: bytes | str, min_length: int = 8) -> bytes:
    """Validate that a secret is non-empty, well-formed, and meets minimum length."""
    if isinstance(secret, str):
        secret_bytes = secret.encode("utf-8")
    elif isinstance(secret, (bytes, bytearray)):
        secret_bytes = bytes(secret)
    else:
        raise InvalidSecretError("Secret must be bytes or str.")
    if not secret_bytes or not secret_bytes.strip():
        raise InvalidSecretError("Secret is missing or empty.")
    if len(secret_bytes) < min_length:
        raise InvalidSecretError(f"Secret is too weak (minimum {min_length} bytes required).")
    if len(set(secret_bytes)) < 3:
        raise InvalidSecretError("Secret has insufficient character diversity.")
    return secret_bytes


class CryptographicError(Exception):
    """Base exception for all cryptographic failures."""
    pass


class DecryptionAuthenticationError(CryptographicError):
    """Raised when ciphertext authentication fails (tampering detected)."""
    pass


class InvalidSecretError(CryptographicError):
    """Raised when master secret fails security criteria or is missing."""
    pass


def derive_key(
    master_secret: bytes,
    purpose: bytes,
    length: int = 32,
    salt: Optional[bytes] = None,
) -> bytes:
    """Derives a purpose-specific key using standard KDF with explicit domain separation.
    Uses scrypt (or PBKDF2-HMAC-SHA256 if scrypt unavailable) with purpose domain.
    """
    if not master_secret:
        raise InvalidSecretError("Master secret cannot be empty.")

    # Fixed domain salt combined with purpose for strict cryptographic isolation
    effective_salt = (salt or b"guptkavach:kdf:salt:v1") + b":" + purpose

    # Prefer scrypt for high memory-hardness against offline brute-force attacks
    if hasattr(hashlib, "scrypt"):
        try:
            return hashlib.scrypt(
                password=master_secret,
                salt=effective_salt,
                n=16384,  # CPU/memory cost
                r=8,      # Block size
                p=1,      # Parallelization
                maxmem=32 * 1024 * 1024,
                dklen=length,
            )
        except (ValueError, AttributeError):
            pass

    # Standard high-iteration PBKDF2 fallback
    return hashlib.pbkdf2_hmac(
        "sha256",
        master_secret,
        effective_salt,
        iterations=100000,
        dklen=length,
    )


class GuptKavachKeyRing:
    """Manages hierarchical purpose-separated cryptographic keys derived from RAKSHA_SECRET."""

    def __init__(self, master_secret: bytes | str, key_version: int = ENVELOPE_VERSION):
        if isinstance(master_secret, str):
            master_secret = master_secret.encode("utf-8")
        if not master_secret:
            raise InvalidSecretError("RAKSHA_SECRET must be set and non-empty.")

        self.key_version = key_version
        self._master_secret = master_secret
        self._keys: Dict[bytes, bytes] = {}

    @property
    def key_fingerprint(self) -> str:
        """Non-reversible public key fingerprint for audit logging (never exposes secret)."""
        return hashlib.sha256(b"fingerprint:" + self._master_secret).hexdigest()[:16]

    def get_key(self, purpose: bytes, length: int = 32) -> bytes:
        """Retrieves or derives the isolated 256-bit key for the specified purpose."""
        if purpose not in self._keys:
            self._keys[purpose] = derive_key(self._master_secret, purpose, length=length)
        return self._keys[purpose]

    @property
    def pseudonym_key(self) -> bytes:
        return self.get_key(KEY_PURPOSE_PSEUDONYM)

    @property
    def date_shift_key(self) -> bytes:
        return self.get_key(KEY_PURPOSE_DATE_SHIFT)

    @property
    def storage_encryption_key(self) -> bytes:
        return self.get_key(KEY_PURPOSE_ENCRYPTION)

    @property
    def integrity_key(self) -> bytes:
        return self.get_key(KEY_PURPOSE_INTEGRITY)

    @property
    def quarantine_key(self) -> bytes:
        return self.get_key(KEY_PURPOSE_QUARANTINE)


# ==============================================================================
# Authenticated Symmetric Encryption (AES-256-GCM / ChaCha20-Poly1305)
# ==============================================================================

def encrypt_payload(
    plaintext: bytes,
    key: bytes,
    associated_data: Optional[bytes] = None,
    cipher_type: str = "aes_gcm",
) -> bytes:
    """Encrypts plaintext with authenticated symmetric encryption.
    Format of envelope:
    [5 bytes magic: b'GKENC']
    [1 byte version: 1]
    [1 byte cipher_id: 1 for AESGCM, 2 for ChaCha20Poly1305, 3 for HMAC-CTR fallback]
    [2 bytes aad_len: unsigned short]
    [aad bytes: associated data]
    [12 bytes nonce: CSPRNG]
    [variable bytes: ciphertext + 16 bytes auth tag]
    """
    if len(key) != 32:
        raise ValueError("Key must be 32 bytes (256-bit).")

    nonce = secrets.token_bytes(12)  # 96-bit CSPRNG nonce, never reused
    aad = associated_data or b""

    if HAS_CRYPTOGRAPHY and cipher_type == "aes_gcm":
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, plaintext, aad)
        cipher_id = 1
    elif HAS_CRYPTOGRAPHY and cipher_type == "chacha20":
        chacha = ChaCha20Poly1305(key)
        ciphertext = chacha.encrypt(nonce, plaintext, aad)
        cipher_id = 2
    else:
        # Standard library deterministic AEAD construct: AES-CTR equivalent + HMAC-SHA256 Encrypt-then-MAC
        ciphertext, cipher_id = _std_encrypt_then_mac(plaintext, key, nonce, aad)

    aad_len = len(aad)
    header = struct.pack("!5sBBH", ENVELOPE_MAGIC, ENVELOPE_VERSION, cipher_id, aad_len)
    return header + aad + nonce + ciphertext


def decrypt_payload(
    envelope: bytes,
    key: bytes,
    associated_data: Optional[bytes] = None,
) -> bytes:
    """Authenticates and decrypts an encrypted envelope.
    Raises DecryptionAuthenticationError if the ciphertext or authentication tag has been tampered with.
    """
    if len(envelope) < 21:  # 5 magic + 1 ver + 1 cipher_id + 2 aad_len + 12 nonce
        raise DecryptionAuthenticationError("Envelope payload truncated or corrupt.")

    magic, ver, cipher_id, aad_len = struct.unpack("!5sBBH", envelope[:9])
    if magic != ENVELOPE_MAGIC:
        raise DecryptionAuthenticationError("Invalid magic header: not a GuptKavach encrypted envelope.")
    if ver != ENVELOPE_VERSION:
        raise DecryptionAuthenticationError(f"Unsupported envelope version: {ver}")

    offset = 9
    stored_aad = envelope[offset : offset + aad_len]
    offset += aad_len

    if associated_data is not None and stored_aad != associated_data:
        raise DecryptionAuthenticationError("Associated data mismatch: header integrity verification failed.")

    nonce = envelope[offset : offset + 12]
    offset += 12
    ciphertext = envelope[offset:]

    if cipher_id == 1 and HAS_CRYPTOGRAPHY:
        aesgcm = AESGCM(key)
        try:
            return aesgcm.decrypt(nonce, ciphertext, stored_aad)
        except Exception as exc:
            raise DecryptionAuthenticationError(f"AES-GCM authentication failed: {exc}") from exc

    elif cipher_id == 2 and HAS_CRYPTOGRAPHY:
        chacha = ChaCha20Poly1305(key)
        try:
            return chacha.decrypt(nonce, ciphertext, stored_aad)
        except Exception as exc:
            raise DecryptionAuthenticationError(f"ChaCha20-Poly1305 authentication failed: {exc}") from exc

    elif cipher_id == 3:
        return _std_decrypt_then_mac(ciphertext, key, nonce, stored_aad)

    else:
        raise DecryptionAuthenticationError(f"Unknown or unsupported cipher ID: {cipher_id}")


# ==============================================================================
# Standard Library Encrypt-then-MAC Construct (Fallback when cryptography is absent)
# ==============================================================================

def _std_encrypt_then_mac(
    plaintext: bytes,
    key: bytes,
    nonce: bytes,
    aad: bytes,
) -> Tuple[bytes, int]:
    """Standard-library stream cipher using SHA256-CTR keystream + HMAC-SHA256 Encrypt-then-MAC."""
    # Split key into enc_key and mac_key
    enc_key = hashlib.sha256(key + b":enc").digest()
    mac_key = hashlib.sha256(key + b":mac").digest()

    # Generate keystream via CTR mode with counter
    ct_chunks = []
    block_size = 32
    pt_len = len(plaintext)
    for block_idx in range((pt_len + block_size - 1) // block_size):
        ctr_val = struct.pack("!12sQ", nonce, block_idx)
        ks_block = hmac.new(enc_key, ctr_val, hashlib.sha256).digest()
        start = block_idx * block_size
        chunk = plaintext[start : start + block_size]
        ct_chunks.append(bytes(a ^ b for a, b in zip(chunk, ks_block)))

    ciphertext_body = b"".join(ct_chunks)

    # Compute HMAC-SHA256 authentication tag over AAD || Nonce || Ciphertext
    tag = hmac.new(mac_key, aad + nonce + ciphertext_body, hashlib.sha256).digest()
    return ciphertext_body + tag, 3


def _std_decrypt_then_mac(
    ciphertext_with_tag: bytes,
    key: bytes,
    nonce: bytes,
    aad: bytes,
) -> bytes:
    if len(ciphertext_with_tag) < 32:
        raise DecryptionAuthenticationError("Payload missing HMAC authentication tag.")

    ciphertext_body = ciphertext_with_tag[:-32]
    expected_tag = ciphertext_with_tag[-32:]

    enc_key = hashlib.sha256(key + b":enc").digest()
    mac_key = hashlib.sha256(key + b":mac").digest()

    computed_tag = hmac.new(mac_key, aad + nonce + ciphertext_body, hashlib.sha256).digest()
    if not hmac.compare_digest(expected_tag, computed_tag):
        raise DecryptionAuthenticationError("HMAC authentication verification failed: data tampered.")

    # Keystream decryption
    pt_chunks = []
    block_size = 32
    ct_len = len(ciphertext_body)
    for block_idx in range((ct_len + block_size - 1) // block_size):
        ctr_val = struct.pack("!12sQ", nonce, block_idx)
        ks_block = hmac.new(enc_key, ctr_val, hashlib.sha256).digest()
        start = block_idx * block_size
        chunk = ciphertext_body[start : start + block_size]
        pt_chunks.append(bytes(a ^ b for a, b in zip(chunk, ks_block)))

    return b"".join(pt_chunks)
