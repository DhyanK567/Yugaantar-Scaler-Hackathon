"""Core sanitization engine for free text, CSV/TSV, JSON/FHIR R4, filenames, and base64."""
from __future__ import annotations

import base64
import binascii
import csv
import hashlib
import io
import json
import re
from pathlib import Path

from .crypto import pseudonymous_filename_token
from .names import CorpusNameIndex, redact_names_in_text
from .patterns import (
    RX_AADHAAR,
    RX_AADHAAR_MASKED,
    RX_ABHA_ADDR,
    RX_ABHA_NUM,
    RX_DOB_LABEL,
    RX_EMAIL,
    RX_HOUSE,
    RX_INSURANCE,
    RX_LANDMARK,
    RX_LOCALITY,
    RX_MRN,
    RX_PAN,
    RX_PHONE,
    RX_PHONE_MASKED,
    RX_PIN,
    RX_VILLAGE_BEFORE_TEHSIL,
    RX_VILLAGE_LABEL,
    classify_field,
    is_clinical_safe_field,
    normalize_digits,
)
from .privacy import age_band, generalize_pin, shift_date_string, shift_dates_in_text

_B64_RX = re.compile(r"[A-Za-z0-9+/]{24,}={0,2}")
_AGE_GENDER_RX = re.compile(r"\b(\d{1,3})(\s*(?:Y|yrs|years)\s*/\s*[MF])\b", re.IGNORECASE)
_AGE_LABEL_RX = re.compile(r"(?<![A-Za-z\u0900-\u097f])((?:Age|आयु|उम्र)\s*[:\-]?\s*)(\d{1,3})(\s*(?:yrs|years|वर्ष)?)", re.IGNORECASE)


def sanitize_base64_in_text(
    text: str,
    name_index: CorpusNameIndex,
    pkey: str | None,
    secret: bytes,
    max_days: int,
    local_first_names: set[str] | None = None,
) -> tuple[str, int]:
    """Decode base64 runs that contain UTF-8 text, sanitize them, and re-encode."""
    hits = 0

    def _rep_b64(m: re.Match[str]) -> str:
        nonlocal hits
        tok = m.group(0)
        try:
            raw = base64.b64decode(tok + "=" * (-len(tok) % 4), validate=False)
            decoded = raw.decode("utf-8", errors="strict")
        except (binascii.Error, UnicodeDecodeError, ValueError):
            return tok
        # Only treat as text attachment if mostly printable
        if not decoded or sum(ch.isprintable() or ch in "\r\n\t" for ch in decoded) / len(decoded) < 0.85:
            return tok
        cleaned, n = sanitize_free_text(
            decoded, name_index, pkey, secret, max_days, decode_b64=False, local_first_names=local_first_names
        )
        if n > 0 or cleaned != decoded:
            hits += n
            return base64.b64encode(cleaned.encode("utf-8")).decode("ascii")
        return tok

    return _B64_RX.sub(_rep_b64, text), hits


def sanitize_free_text(
    text: str,
    name_index: CorpusNameIndex,
    patient_key: str | None,
    secret: bytes,
    max_days: int = 180,
    decode_b64: bool = True,
    clinical_safe: bool = False,
    local_first_names: set[str] | None = None,
) -> tuple[str, int]:
    """Sanitize unstructured clinical/administrative text while preserving medical utility."""
    total = 0
    work = normalize_digits(text)

    if decode_b64 and len(work) >= 24:
        work, n_b64 = sanitize_base64_in_text(
            work, name_index, patient_key, secret, max_days, local_first_names=local_first_names
        )
        total += n_b64

    # 1. Names and relatives (with Dr. and clinical phrase protection)
    work, n_names = redact_names_in_text(work, name_index, local_first_names=local_first_names)
    total += n_names

    has_digit = any(ch.isdigit() for ch in work)
    has_at = "@" in work

    # 2. Direct identifiers (longest/most specific first)
    if has_at:
        for tag, rx in (("[ABHA_ADDRESS]", RX_ABHA_ADDR), ("[EMAIL]", RX_EMAIL)):
            work, n = rx.subn(tag, work)
            total += n
    if has_digit:
        for tag, rx in (
            ("[ABHA_NUMBER]", RX_ABHA_NUM),
            ("[AADHAAR]", RX_AADHAAR),
            ("[AADHAAR_MASKED]", RX_AADHAAR_MASKED),
            ("[INSURANCE_ID]", RX_INSURANCE),
            ("[MRN]", RX_MRN),
            ("[PHONE]", RX_PHONE),
            ("[PHONE_MASKED]", RX_PHONE_MASKED),
            ("[PAN]", RX_PAN),
        ):
            work, n = rx.subn(tag, work)
            total += n

        # 3. DOB labels
        def _sub_dob(m: re.Match[str]) -> str:
            nonlocal total
            total += 1
            return m.group(0).replace(m.group(1), "[DOB]")

        work = RX_DOB_LABEL.sub(_sub_dob, work)

    # 4. Address components & PIN generalization (skip Ward/PIN on clinical-safe fields)
    for tag, rx in (
        ("[HOUSE]", RX_HOUSE),
        ("[LANDMARK]", RX_LANDMARK),
    ):
        work, n = rx.subn(tag, work)
        total += n

    if not clinical_safe:
        work, n_loc = RX_LOCALITY.subn("[LOCALITY]", work)
        total += n_loc

        def _sub_village(m: re.Match[str]) -> str:
            nonlocal total
            total += 1
            return f"{m.group('prefix')}[VILLAGE]"

        work = RX_VILLAGE_LABEL.sub(_sub_village, work)

        def _sub_village_tehsil(m: re.Match[str]) -> str:
            nonlocal total
            total += 1
            return "[VILLAGE]"

        work = RX_VILLAGE_BEFORE_TEHSIL.sub(_sub_village_tehsil, work)

        if has_digit:
            def _sub_pin(m: re.Match[str]) -> str:
                nonlocal total
                total += 1
                return generalize_pin(m.group(0))

            work = RX_PIN.sub(_sub_pin, work)

    # 5. Age generalization in text (e.g., "48 Y / F" -> "45-49 Y / F", "आयु: 39 वर्ष" -> "आयु: 35-39 वर्ष")
    if has_digit:
        work = _AGE_GENDER_RX.sub(lambda m: f"{age_band(int(m.group(1)))}{m.group(2)}", work)
        work = _AGE_LABEL_RX.sub(lambda m: f"{m.group(1)}{age_band(int(m.group(2)))}{m.group(3)}", work)

        # 6. Per-patient date shifting (only if we have a key; fallback to deterministic record key)
        if patient_key:
            work = shift_dates_in_text(work, patient_key, secret, max_days)

    return work, total


_SAFE_FILENAME_PREFIXES = frozenset({
    "discharge", "summary", "lab", "labs", "report", "note", "notes", "visit",
    "rx", "prescription", "fhir", "bundle", "records", "record", "clinical",
    "patient", "patients", "hospital", "hosp", "encounter", "vitals", "doc",
    "admission", "referral", "diag", "diagnosis", "medication", "meds",
})
_UNSAFE_PATH_CHARS = re.compile(r"[^A-Za-z0-9._\-]")


def sanitize_filename(
    rel_posix: str,
    name_index: CorpusNameIndex,
    raw_sha256: str,
    secret: bytes = b"",
) -> str:
    """Replace PII and unsafe path components in a relative path deterministically.

    Uses domain-separated HMAC-SHA256 tokens derived from ``secret`` so output
    filenames are deterministic for identical (input, secret), change when
    ``RAKSHA_SECRET`` changes, prevent path traversal, and never expose raw PII.
    """
    normalized = (rel_posix or "").replace("\x00", "").replace("\\", "/")
    raw_parts = [seg for seg in normalized.split("/") if seg and seg not in (".", "..")]
    if raw_parts and ":" in raw_parts[0]:
        raw_parts[0] = raw_parts[0].split(":", 1)[-1]
        raw_parts = [seg for seg in raw_parts if seg and seg not in (".", "..")]
    if not raw_parts:
        tok = pseudonymous_filename_token("empty_fallback", raw_sha256, secret, length=12)
        return f"doc_{tok}.txt"

    changed = (normalized != rel_posix) or (".." in (rel_posix or "")) or normalized.startswith("/")
    new_parts: list[str] = []
    for idx, part in enumerate(raw_parts):
        is_last = idx == len(raw_parts) - 1
        stem = Path(part).stem if is_last else part
        raw_ext = Path(part).suffix if is_last else ""
        ext = raw_ext.lower() if (raw_ext and re.fullmatch(r"\.[A-Za-z0-9]{1,10}", raw_ext)) else ""

        # Check multiple tokenizations (underscore, hyphen, dot-separated, and raw)
        variants = (
            stem,
            stem.replace("_", " "),
            stem.replace("-", " "),
            re.sub(r"[_\-.]+", " ", stem),
        )
        pii_found = False
        for variant in variants:
            cleaned, n = sanitize_free_text(
                variant,
                name_index,
                None,
                b"",
                decode_b64=False,
                local_first_names=name_index.first_names,
            )
            if n > 0 or cleaned != variant:
                pii_found = True
                break

        has_non_ascii = any(ord(ch) > 127 for ch in stem)
        has_unsafe_chars = bool(_UNSAFE_PATH_CHARS.search(stem))
        # Also flag suspiciously long or multi-digit numeric tokens (>=6 digits) in filenames
        has_long_digits = bool(re.search(r"\d{6,}", stem))

        if pii_found or has_non_ascii or has_unsafe_chars or has_long_digits:
            changed = True
            token = pseudonymous_filename_token(f"{normalized}#{idx}", raw_sha256, secret, length=12)
            if is_last:
                first_tok = re.split(r"[_\-\s.]+", stem.lower())[0] if stem else ""
                prefix = first_tok if first_tok in _SAFE_FILENAME_PREFIXES else "doc"
                new_parts.append(f"{prefix}_{token}{ext}")
            else:
                new_parts.append(f"dir_{token}")
        else:
            new_parts.append(f"{stem}{ext}" if is_last else stem)

    if not changed:
        return "/".join(new_parts)
    return "/".join(new_parts)


def sanitize_structured_cell(
    kind: str | None,
    val: str,
    name_index: CorpusNameIndex,
    patient_key: str | None,
    pid: str | None,
    secret: bytes,
    max_days: int,
    rare_suppress: bool = False,
    clinical_safe: bool = False,
    local_first_names: set[str] | None = None,
) -> tuple[str, int, bool]:
    """Sanitize a CSV cell or JSON leaf string based on its semantic field kind.
    Returns (new_value, identifiers_count, was_generalized).
    """
    if not val or not val.strip():
        return val, 0, False

    if kind == "PATIENT_NAME":
        return "[PATIENT_NAME]", 1, False
    if kind == "RELATIVE_NAME":
        return "[RELATIVE_NAME]", 1, False
    if kind == "PHONE":
        return "[PHONE]", 1, False
    if kind == "EMAIL":
        return "[EMAIL]", 1, False
    if kind == "AADHAAR":
        return "[AADHAAR_MASKED]" if "X" in val.upper() else "[AADHAAR]", 1, False
    if kind == "ABHA_NUMBER":
        return "[ABHA_NUMBER]", 1, False
    if kind == "PAN":
        return "[PAN]", 1, False
    if kind == "INSURANCE_ID":
        return "[INSURANCE_ID]", 1, False
    if kind == "MRN":
        return pid if pid else "[MRN]", 1, False
    if kind == "DOB":
        return "[DOB]", 1, False
    if kind == "HOUSE":
        return "[HOUSE]", 1, False
    if kind == "LOCALITY":
        return "[LOCALITY]", 1, False
    if kind == "LANDMARK":
        return "[LANDMARK]", 1, False
    if kind == "SOURCE_PATH":
        return "[REDACTED_PATH]", 1, False
    if kind == "PIN":
        return ("[PIN]" if rare_suppress else generalize_pin(val)), 1, True
    if kind == "VILLAGE":
        return "[VILLAGE]", 1, True
    if kind == "TEHSIL":
        return ("[TEHSIL]" if rare_suppress else val), 0, rare_suppress
    if kind == "DISTRICT":
        return ("[DISTRICT]" if rare_suppress else val), 0, rare_suppress
    if kind == "AGE":
        m = re.search(r"\d+", normalize_digits(val))
        if m:
            w = 10 if rare_suppress else 5
            return age_band(int(m.group(0)), width=w), 0, True
        return val, 0, False
    if kind == "DATE":
        if patient_key:
            return shift_date_string(val, patient_key, secret, max_days), 0, True
        return val, 0, False
    if kind == "DOCTOR":
        return val, 0, False
    if kind == "ADDRESS":
        cleaned, n = sanitize_free_text(
            val, name_index, patient_key, secret, max_days, local_first_names=local_first_names
        )
        return cleaned, max(n, 1), True

    # Default: free-text sanitization
    cleaned, n = sanitize_free_text(
        val, name_index, patient_key, secret, max_days,
        clinical_safe=clinical_safe, local_first_names=local_first_names,
    )
    return cleaned, n, False


_NON_PERSON_FHIR_TYPES = {"Organization", "Location", "Practitioner", "Medication", "Substance", "Device"}


def sanitize_json_node(
    node,
    parent_key: str,
    name_index: CorpusNameIndex,
    patient_key: str | None,
    pid: str | None,
    secret: bytes,
    max_days: int,
    rare_suppress: bool = False,
    local_first_names: set[str] | None = None,
) -> tuple[object, int, bool]:
    """Recursively sanitize a JSON object/list/scalar while preserving types and FHIR R4 structure."""
    if isinstance(node, str):
        # Preserve FHIR URNs and resource references
        if node.startswith(("urn:uuid:", "http://", "https://")) and parent_key in ("reference", "fullUrl", "system", "profile"):
            return node, 0, False
        if parent_key in ("resourceType", "id", "status", "code", "system", "contentType"):
            return node, 0, False
        if parent_key == "birthDate":
            # Keep only year or [DOB] to prevent exact DOB leak while preserving age utility
            return "[DOB]", 1, True
        if parent_key == "source" and node.startswith("#"):
            return f"#{pid}" if pid else "#[MRN]", 1, False
        kind = classify_field(parent_key)
        csafe = is_clinical_safe_field(parent_key)
        return sanitize_structured_cell(
            kind, node, name_index, patient_key, pid, secret, max_days,
            rare_suppress, clinical_safe=csafe, local_first_names=local_first_names,
        )

    if isinstance(node, list):
        out = []
        tot = 0
        gen = False
        for item in node:
            c_item, n, g = sanitize_json_node(
                item, parent_key, name_index, patient_key, pid, secret, max_days,
                rare_suppress, local_first_names=local_first_names,
            )
            out.append(c_item)
            tot += n
            gen = gen or g
        return out, tot, gen

    if isinstance(node, dict):
        # Special FHIR Patient & RelatedPerson resource handling
        rtype = node.get("resourceType")
        if rtype == "Patient":
            return _sanitize_fhir_patient(
                node, name_index, patient_key, pid, secret, max_days, rare_suppress, local_first_names=local_first_names
            )
        if rtype == "RelatedPerson":
            return _sanitize_fhir_related_person(
                node, name_index, patient_key, secret, max_days, local_first_names=local_first_names
            )

        out_dict = {}
        tot = 0
        gen = False
        for k, v in node.items():
            # Sanitize key if it holds PII (e.g., patient_index.json "by_name" / "by_uhid")
            clean_k, nk = sanitize_free_text(
                k, name_index, None, b"", decode_b64=False, local_first_names=local_first_names
            )
            tot += nk
            if rtype in _NON_PERSON_FHIR_TYPES and k == "name":
                c_v, nv, gv = v, 0, False
            else:
                c_v, nv, gv = sanitize_json_node(
                    v, k, name_index, patient_key, pid, secret, max_days,
                    rare_suppress, local_first_names=local_first_names,
                )
            if clean_k in out_dict:
                dup = 2
                while f"{clean_k}_{dup}" in out_dict:
                    dup += 1
                clean_k = f"{clean_k}_{dup}"
            out_dict[clean_k] = c_v
            tot += nv
            gen = gen or gv
        return out_dict, tot, gen

    # int / float / bool / None
    if isinstance(node, int) and not isinstance(node, bool):
        kind = classify_field(parent_key)
        if kind == "AGE":
            w = 10 if rare_suppress else 5
            return age_band(node, width=w), 0, True
        if kind in ("PHONE", "AADHAAR", "ABHA_NUMBER"):
            return f"[{kind}]", 1, False
        if kind == "PIN":
            return ("[PIN]" if rare_suppress else generalize_pin(str(node))), 1, True
    return node, 0, False


def _sanitize_fhir_patient(
    node: dict,
    name_index: CorpusNameIndex,
    patient_key: str | None,
    pid: str | None,
    secret: bytes,
    max_days: int,
    rare_suppress: bool,
    local_first_names: set[str] | None = None,
) -> tuple[dict, int, bool]:
    """Sanitize a FHIR R4 Patient resource while keeping it valid R4."""
    out = dict(node)
    tot = 0
    if "name" in out and isinstance(out["name"], list):
        out["name"] = [{"text": pid if pid else "[PATIENT_NAME]"}]
        tot += 1
    if "telecom" in out:
        out["telecom"] = [{"system": "phone", "value": "[PHONE]"}]
        tot += 1
    if "contact" in out and isinstance(out["contact"], list):
        new_contacts = []
        for ct in out["contact"]:
            if isinstance(ct, dict):
                nc = dict(ct)
                if "name" in nc:
                    nc["name"] = {"text": "[RELATIVE_NAME]"}
                    tot += 1
                if "telecom" in nc:
                    nc["telecom"] = [{"system": "phone", "value": "[PHONE]"}]
                    tot += 1
                if "address" in nc:
                    nc["address"] = {}
                    tot += 1
                new_contacts.append(nc)
        out["contact"] = new_contacts
    if "extension" in out and isinstance(out["extension"], list):
        new_exts = []
        for ext in out["extension"]:
            if isinstance(ext, dict):
                ne = dict(ext)
                url = str(ne.get("url", "")).casefold()
                if "valueString" in ne and any(w in url for w in ("mother", "father", "spouse", "relative", "guardian", "kin", "name")):
                    ne["valueString"] = "[RELATIVE_NAME]"
                    tot += 1
                elif "valueString" in ne:
                    cv, nv, _ = sanitize_json_node(
                        ne["valueString"], "valueString", name_index, patient_key, pid, secret, max_days,
                        rare_suppress, local_first_names=local_first_names,
                    )
                    ne["valueString"] = cv
                    tot += nv
                new_exts.append(ne)
            else:
                new_exts.append(ext)
        out["extension"] = new_exts
    if "identifier" in out and isinstance(out["identifier"], list):
        new_ids = []
        for ident in out["identifier"]:
            if isinstance(ident, dict):
                ni = dict(ident)
                ni["value"] = pid if pid else "[MRN]"
                new_ids.append(ni)
                tot += 1
        out["identifier"] = new_ids
    if "address" in out and isinstance(out["address"], list):
        new_addrs = []
        for addr in out["address"]:
            if isinstance(addr, dict):
                na = {}
                if "district" in addr and not rare_suppress:
                    na["district"] = addr["district"]
                if "state" in addr:
                    na["state"] = addr["state"]
                if "postalCode" in addr and not rare_suppress:
                    na["postalCode"] = generalize_pin(str(addr["postalCode"]))
                new_addrs.append(na)
                tot += 1
        out["address"] = new_addrs
    if "birthDate" in out:
        if patient_key:
            out["birthDate"] = shift_date_string(str(out["birthDate"]), patient_key, secret, max_days)
        else:
            out["birthDate"] = "[DOB]"
        tot += 1
    if "text" in out:
        clean_txt, n_txt, _ = sanitize_json_node(
            out["text"], "text", name_index, patient_key, pid, secret, max_days,
            rare_suppress, local_first_names=local_first_names,
        )
        out["text"] = clean_txt
        tot += n_txt
    return out, tot, True


def _sanitize_fhir_related_person(
    node: dict,
    name_index: CorpusNameIndex,
    patient_key: str | None,
    secret: bytes,
    max_days: int,
    local_first_names: set[str] | None = None,
) -> tuple[dict, int, bool]:
    """Sanitize a FHIR R4 RelatedPerson resource."""
    out = dict(node)
    tot = 0
    if "name" in out and isinstance(out["name"], list):
        out["name"] = [{"text": "[RELATIVE_NAME]"}]
        tot += 1
    if "telecom" in out:
        out["telecom"] = [{"system": "phone", "value": "[PHONE]"}]
        tot += 1
    if "address" in out:
        out["address"] = []
        tot += 1
    if "text" in out:
        clean_txt, n_txt, _ = sanitize_json_node(
            out["text"], "text", name_index, patient_key, None, secret, max_days,
            False, local_first_names=local_first_names,
        )
        out["text"] = clean_txt
        tot += n_txt
    return out, tot, False
