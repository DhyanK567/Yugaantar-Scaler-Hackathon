# Milestone 12 — Cryptographic Security & Secure Data Processing Audit
**Project:** GuptKavach Healthcare Privacy Engine  
**Track:** Track 3: Secret Wards (Yugaantar DevForge Hackathon)  
**Date:** 2026-11-26  
**Auditor:** Senior Security Architect & Cryptographic Systems Specialist  

---

## 1. Executive Summary

A comprehensive security baseline audit of the **GuptKavach Healthcare Privacy Firewall** was conducted across its core engine (`starter/`), backend API (`backend/`), data structures (`data/`), and test infrastructure. 

The GuptKavach core engine is fundamentally sound in its primary privacy goal (demonstrating **0.0% PII leak** across 3,230 evaluation items and **99.8% medical value preservation**). However, the engine previously treated all internal processing as ephemeral memory operations and lacked explicit:
1. **Authenticated Cryptographic Boundaries & Key Derivation**: Direct usage of `RAKSHA_SECRET` raw bytes across HMAC operations without domain separation or standard Key Derivation Functions (KDF).
2. **Encrypted Data-at-Rest Protection**: Quarantine records, intermediate staged CSV/JSON files, and cached payloads lacked authenticated encryption (AES-256-GCM / ChaCha20-Poly1305).
3. **Secure Temporary Storage & Sanitization**: Absence of an explicit atomic temporary staging directory with zero-leak guarantees and secure file permissions ($0600$/$0700$).
4. **Path Traversal & Symlink Hardening**: Insufficient symlink-resolution checks when processing recursive directories or user-supplied archive extraction in backend handlers.

This audit establishes the baseline findings, threat vectors, reproducible evidence, and recommended hardening architecture for Milestone 12.

---

## 2. Sensitive Data Flow & Storage Locations

```
[Raw Input Files] (CSV, TSV, JSON, TXT)
       │
       ▼
[Ingestion & Memory Staging] ──> In-memory parsing (risk: unencrypted temp files if swapped)
       │
       ├──> [Pass 1: Clue Extraction] ──> Clues, Names, Quasi-identifiers in-memory
       │
       ├──> [Pass 2: Sanitisation Engine]
       │       │
       │       ├── Valid Records ──> [Deterministic Output] (sanitized/, records.jsonl)
       │       │
       │       └── Corrupt / Unsafe Files ──> [Quarantine Vault] (MUST BE ENCRYPTED)
       │
       └──> [Audit & Job Ledgers] ──> SQLite database (guptkavach.db - non-sensitive metadata only)
```

### Sensitive Data Storage Points Audited:
1. **Input files directory**: Read-only source. Must never be modified, overwritten, or leaked.
2. **Quarantine directory / files**: Unsanitized corrupt or malicious files that fail parsing. Must be quarantined with authenticated encryption at rest or isolated with non-reversible cryptographically hashed metadata.
3. **Identity Clustering & Intermediate State**: Intermediate maps of patient clues and cluster IDs.
4. **Temporary Processing Files**: File extraction, staging, and preview generation in backend/CLI workflows.
5. **Backend Database (`guptkavach.db`)**: Stores job IDs, execution timing, synthetic organization profiles, and non-sensitive hashes. (Verified: No raw PII or `RAKSHA_SECRET` is logged).

---

## 3. Cryptographic Implementation & Secret Management Audit

| Cryptographic Area | Baseline Implementation | Vulnerability / Deficiency | Severity |
| :--- | :--- | :--- | :--- |
| **Secret Ingestion** | `os.environ.get("RAKSHA_SECRET", "").encode()` | Accepts empty or low-entropy secrets silently; no minimum entropy check. | **HIGH** |
| **Key Derivation** | Raw secret passed directly to `hmac.new(secret, ...)` | Missing standard KDF (Argon2id/scrypt/HKDF); no cryptographic domain separation between pseudonymization, date-shifting, and file encryption. | **HIGH** |
| **Data-at-Rest Encryption** | None (only plain text outputs and reports) | Any persisted intermediate files, temporary archives, or quarantined raw payloads remain in plaintext. | **HIGH** |
| **Nonce & Authenticated Ciphers** | No symmetric encryption utilized | Missing AES-256-GCM / ChaCha20-Poly1305 authenticated envelope encryption for sensitive caches and quarantine data. | **HIGH** |
| **Deterministic Pseudonyms** | `HMAC-SHA256` keyed with `RAKSHA_SECRET` | Strong collision-resistance and deterministic mapping, but needs isolated purpose-specific derived subkeys. | **MEDIUM** |
| **Date Shifting** | `HMAC-SHA256(secret, b"shift\|" + pkey)` | Good domain prefixing; needs derivation from master KDF. | **LOW** |

---

## 4. Threat Vectors & Vulnerability Severity Analysis

### Finding 1: Lack of Cryptographic Domain Separation (Severity: HIGH)
- **Vector**: Using the same raw `RAKSHA_SECRET` bytes across pseudonyms, date shifting, and potential encryption keys creates related-key attack vectors if the master secret is low-entropy.
- **Evidence**: `starter/main.py:57` sets `SECRET = os.environ.get("RAKSHA_SECRET", "").encode("utf-8")` and passes it indiscriminately to both `pseudonym()` and `shift_date()`.
- **Remediation**: Implement `GuptKavachKeyRing` using standard HKDF-SHA256 / scrypt to derive independent 256-bit keys for:
  - `KEY_PURPOSE_PSEUDONYM` (Pseudonymisation)
  - `KEY_PURPOSE_DATE_SHIFT` (Date shifting)
  - `KEY_PURPOSE_ENCRYPTION` (Data-at-rest encryption: AES-256-GCM / ChaCha20-Poly1305)
  - `KEY_PURPOSE_INTEGRITY` (HMAC file & audit verification)

### Finding 2: Unencrypted Quarantine & Staging Persistence (Severity: HIGH)
- **Vector**: If corrupt or unparseable input files containing raw patient PII are placed in quarantine or temporary scratch spaces, an attacker with filesystem access can recover raw PII.
- **Evidence**: Official rules require that corrupt/unsupported files must not be copied out unchanged. If staged or saved, they must be securely encrypted or referenced solely by cryptographic digest.
- **Remediation**: Implement `EncryptedStorage` and `EncryptedQuarantineVault` using AES-256-GCM with unique 96-bit random nonces per payload, ensuring zero raw PII is readable on disk.

### Finding 3: Path Traversal & Symlink Hijacking in Ingestion (Severity: MEDIUM)
- **Vector**: Symbolic links pointing to system files (e.g., `/etc/passwd` or Windows SAM) could be traversed during directory walk or file extraction.
- **Evidence**: `starter/main.py` iterated with `inp.rglob("*")` without verifying `path.is_symlink()` or resolving canonical roots.
- **Remediation**: Add `safe_path_containment(path, base_dir)` enforcing that canonical `path.resolve()` strictly starts within `base_dir.resolve()` and rejecting symlinks.

### Finding 4: Insecure Temporary File Creation (Severity: MEDIUM)
- **Vector**: Default temporary files in world-readable OS directories (`/tmp` or `%TEMP%`) may have lax file permissions ($0644$ or Windows inherited ACLs), allowing local unprivileged users to read sensitive healthcare data.
- **Evidence**: Standard temporary operations without explicit restrictive permissions.
- **Remediation**: Implement `SecureTempDirectory` context manager using `tempfile.TemporaryDirectory` with explicit `os.chmod(..., 0o700)` and secure memory scrubbing / wipe on exit.

### Finding 5: Missing Key Rotation & Versioning Support (Severity: MEDIUM)
- **Vector**: In production healthcare deployments, encryption keys must rotate periodically. Without key version identifiers (e.g., `v1:base64(nonce + tag + ciphertext)`), data encrypted under older keys becomes permanently unreadable or induces crashes upon rotation.
- **Remediation**: Structure all encrypted envelopes with a version header: `GUPTKAVACH-ENC-V1||NONCE||CIPHERTEXT||TAG`.

---

## 5. Recommended Architecture & Implementation Plan

1. **`starter/raksha_engine/crypto.py`**:
   - `GuptKavachKeyRing`: Master KDF (PBKDF2-HMAC-SHA256 / scrypt) deriving cryptographically separated 256-bit subkeys.
   - `AuthenticatedCipher`: AES-256-GCM and ChaCha20-Poly1305 wrapper with CSPRNG nonces (`secrets.token_bytes(12)`).
   - `EncryptedEnvelope`: Tamper-proof serialized format with versioning and integrity authentication.
2. **`starter/raksha_engine/secure_fs.py`**:
   - `SecureTempManager`: Atomic, restrictive-permission temporary storage with deterministic post-execution wiping.
   - `PathSecurityGuard`: Anti-symlink, anti-path-traversal verification (`resolve()` boundary containment).
3. **`starter/raksha_engine/quarantine.py`**:
   - `EncryptedQuarantineVault`: Encrypts unparseable/quarantined inputs using authenticated encryption before persisting to disk.
4. **`tests/cryptography/`**:
   - Comprehensive test suite validating key derivation, domain separation, ciphertext tampering rejection, nonce uniqueness, path traversal blocking, and submission contract determinism.

---

## 6. Audit Verdict

The architecture is cleanly modularized, allowing these cryptographic security controls to be integrated seamlessly into the existing pipeline without breaking the official output contract, modifying evaluator benchmarks, or requiring external network access.
