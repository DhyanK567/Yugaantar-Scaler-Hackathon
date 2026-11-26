# MEDILOCKER — MILESTONE 15.5 CRYPTOGRAPHIC ASSURANCE
**Phase 1 Cryptographic Architecture & Threat Model**

---

## 1. Cryptographic Construction

MediLocker / GuptKavach uses standard, peer-reviewed cryptographic primitives via Python's `hashlib`, `hmac`, `secrets`, and `cryptography` (OpenSSL-backed AEAD and Ed25519):

1. **Key Derivation & Domain Separation (RFC 5869 HKDF-SHA256)**:
   - Master secret (`RAKSHA_SECRET`) is never reused across independent cryptographic domains.
   - `hkdf_sha256(ikm, info=...)` derives isolated 256-bit subkeys for:
     - `medilocker:v1:patient-pseudonym`: Keying `HMAC-SHA256` for `PSN-XXXXXX` Crockford Base32 pseudonyms.
     - `medilocker:v1:date-shift`: Keying `HMAC-SHA256` for deterministic per-patient date shifts.
     - `medilocker:v1:identity-linking`: Keying `HMAC-SHA256` for cross-record identity-linking tokens.
     - `medilocker:v1:manifest-integrity`: Keying `HMAC-SHA256` for manifest root authentication.
     - `medilocker:v1:passport-auth`: Keying `HMAC-SHA256` for passport authentication tags.
2. **Encryption-at-Rest (Separate Key Schedule)**:
   - Storage and quarantine encryption keys are derived separately via `scrypt` ($N=16384, r=8, p=1$) with distinct purpose domains (`guptkavach:v1:aes-256-gcm-storage`, `guptkavach:v1:quarantine-vault`).
   - Uses **AES-256-GCM** (or **ChaCha20-Poly1305**) with 96-bit CSPRNG nonces (`secrets.token_bytes(12)`) and authenticated associated data (AAD).
   - Encryption keys are never reused as pseudonymisation keys.
3. **Privacy Passport Digital Signatures**:
   - Uses **Ed25519** asymmetric signatures over canonicalized JSON (`sort_keys=True, separators=(",", ":")`) when an explicit signing key (`GUPTKAVACH_SIGNING_KEY_PATH` / `GUPTKAVACH_SIGNING_KEY_PEM`) is configured; otherwise honestly marks `UNSIGNED`.

---

## 2. Threat Assumptions & Guarantees

- **HMAC-SHA256 Security**: HMAC-SHA256 is inherently immune to length-extension attacks due to its nested inner/outer padding construction. HKDF-SHA256 provides cryptographic **domain separation** so compromise or correlation of one derived purpose key does not compromise other domains.
- **Deterministic Pseudonymisation**: Identical `(patient_key, RAKSHA_SECRET)` always yields identical `PSN-XXXXXX` and date shift; distinct secrets yield computationally independent outputs.
- **Fail-Safe Secret Handling**: Missing or empty `RAKSHA_SECRET` raises `InvalidSecretError`. `validate_secret()` rejects empty, short (< 8 bytes), or low-diversity secrets. Secret bytes are never logged or written to reports/passports.
- **Non-Goals / Honest Boundaries**: Local file deletion does not guarantee physical flash wear-leveling erasure; no external KMS/HSM is claimed in offline mode.
