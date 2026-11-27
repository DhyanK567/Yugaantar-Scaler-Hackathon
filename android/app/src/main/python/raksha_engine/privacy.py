"""Privacy transformations: HMAC pseudonyms, per-patient date shifting, age bands,
location & PIN generalisation, and rare-group k-anonymity suppression.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import re

from .crypto import (
    HKDF_DOMAIN_DATE_SHIFT,
    HKDF_DOMAIN_IDENTITY_LINK,
    HKDF_DOMAIN_MANIFEST,
    HKDF_DOMAIN_PASSPORT_AUTH,
    HKDF_DOMAIN_PSEUDONYM,
    InvalidSecretError,
    hkdf_sha256,
)

_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"  # Crockford base32


def _require_secret(secret: bytes) -> bytes:
    if not secret:
        raise InvalidSecretError("RAKSHA_SECRET must be non-empty for cryptographic operations.")
    return secret


def pseudonym(patient_key: str, secret: bytes) -> str:
    """Stable, non-reversible ID: HMAC-SHA256 keyed with HKDF-derived pseudonym subkey."""
    subkey = hkdf_sha256(_require_secret(secret), info=HKDF_DOMAIN_PSEUDONYM)
    digest = hmac.new(subkey, patient_key.encode("utf-8"), hashlib.sha256).digest()
    n = int.from_bytes(digest[:5], "big")
    code = "".join(_ALPHABET[(n >> (5 * i)) & 31] for i in range(6))
    return f"PSN-{code}"


def identity_linking_token(clue: str, secret: bytes) -> str:
    """Deterministic cross-record linking token using an independent HKDF domain subkey."""
    subkey = hkdf_sha256(_require_secret(secret), info=HKDF_DOMAIN_IDENTITY_LINK)
    return hmac.new(subkey, clue.encode("utf-8"), hashlib.sha256).hexdigest()


def manifest_hmac(manifest_root_hash: str, secret: bytes) -> str:
    """Deterministic manifest authentication tag using an independent HKDF domain subkey."""
    subkey = hkdf_sha256(_require_secret(secret), info=HKDF_DOMAIN_MANIFEST)
    return hmac.new(subkey, manifest_root_hash.encode("utf-8"), hashlib.sha256).hexdigest()


def passport_auth_hmac(canonical_passport_bytes: bytes, secret: bytes) -> str:
    """Deterministic passport HMAC tag using an independent HKDF domain subkey."""
    subkey = hkdf_sha256(_require_secret(secret), info=HKDF_DOMAIN_PASSPORT_AUTH)
    return hmac.new(subkey, canonical_passport_bytes, hashlib.sha256).hexdigest()


def date_shift_days(patient_key: str, secret: bytes, max_days: int = 180) -> int:
    """Per-patient deterministic shift in [-max_days, +max_days], never 0."""
    subkey = hkdf_sha256(_require_secret(secret), info=HKDF_DOMAIN_DATE_SHIFT)
    d = hmac.new(subkey, b"shift|" + patient_key.encode("utf-8"), hashlib.sha256).digest()
    v = int.from_bytes(d[:4], "big") % (2 * max_days) - max_days
    return v if v != 0 else 1


def shift_date(value: dt.date, patient_key: str, secret: bytes, max_days: int = 180) -> dt.date:
    return value + dt.timedelta(days=date_shift_days(patient_key, secret, max_days))


_ISO_DATE_RX = re.compile(r"(19\d{2}|20\d{2})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])")
_SLASH_DATE_RX = re.compile(r"(\d{1,2})/(\d{1,2})/(19\d{2}|20\d{2})")
_DASH_DATE_RX = re.compile(r"(\d{1,2})-(\d{1,2})-(19\d{2}|20\d{2})")
_TEXT_ISO_RX = re.compile(r"\b(?:19\d{2}|20\d{2})-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])\b")
_TEXT_DMY_RX = re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-](?:19\d{2}|20\d{2})\b")


def parse_date_str(s: str) -> tuple[dt.date, str] | None:
    """Parse common date formats and return (date, fmt_style)."""
    s = s.strip()
    m = _ISO_DATE_RX.fullmatch(s)
    if m:
        try:
            return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3))), "iso"
        except ValueError:
            return None
    m = _SLASH_DATE_RX.fullmatch(s)
    if m:
        a, b, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        # Disambiguate DD/MM/YYYY vs MM/DD/YYYY
        if a > 12 and 1 <= b <= 12:
            try:
                return dt.date(y, b, a), "dmy_slash"
            except ValueError:
                return None
        if b > 12 and 1 <= a <= 12:
            try:
                return dt.date(y, a, b), "mdy_slash"
            except ValueError:
                return None
        try:
            return dt.date(y, b, a), "dmy_slash"
        except ValueError:
            return None
    m = _DASH_DATE_RX.fullmatch(s)
    if m:
        a, b, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if b > 12 and 1 <= a <= 12:
            try:
                return dt.date(y, a, b), "mdy_dash"
            except ValueError:
                return None
        try:
            return dt.date(y, b, a), "dmy_dash"
        except ValueError:
            return None
    return None


def format_date(d: dt.date, style: str) -> str:
    if style == "iso":
        return d.strftime("%Y-%m-%d")
    if style == "mdy_slash":
        return d.strftime("%m/%d/%Y")
    if style == "dmy_dash":
        return d.strftime("%d-%m-%Y")
    if style == "mdy_dash":
        return d.strftime("%m-%d-%Y")
    return d.strftime("%d/%m/%Y")


def shift_date_string(s: str, patient_key: str, secret: bytes, max_days: int = 180) -> str:
    parsed = parse_date_str(s)
    if not parsed:
        return s
    d, style = parsed
    return format_date(shift_date(d, patient_key, secret, max_days), style)


def shift_dates_in_text(text: str, patient_key: str, secret: bytes, max_days: int = 180) -> str:
    """Shift ISO and slash/dash dates in free text using the same per-patient offset."""
    if len(text) < 8 or not any(c.isdigit() for c in text):
        return text

    def _rep_iso(m: re.Match[str]) -> str:
        return shift_date_string(m.group(0), patient_key, secret, max_days)

    def _rep_dmy(m: re.Match[str]) -> str:
        return shift_date_string(m.group(0), patient_key, secret, max_days)

    text = _TEXT_ISO_RX.sub(_rep_iso, text)
    text = _TEXT_DMY_RX.sub(_rep_dmy, text)
    return text


def age_band(age: int, width: int = 5) -> str:
    """Return age band containing true age; 85+ for >= 85."""
    if age >= 85:
        return "85+"
    lo = max(0, (age // width) * width)
    return f"{lo}-{lo + width - 1}"


def generalize_pin(pin: str) -> str:
    digits = re.sub(r"\D", "", pin)
    if len(digits) == 6:
        return f"{digits[:3]}***"
    return "[PIN]"
