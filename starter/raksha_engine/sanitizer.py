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
    RX_VILLAGE_LABEL,
    classify_field,
    normalize_digits,
)
from .privacy import age_band, generalize_pin, shift_date_string, shift_dates_in_text

_B64_RX = re.compile(r"[A-Za-z0-9+/]{24,}={0,2}")


def sanitize_base64_in_text(text: str, name_index: CorpusNameIndex, pkey: str | None, secret: bytes, max_days: int) -> tuple[str, int]:
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
        cleaned, n = sanitize_free_text(decoded, name_index, pkey, secret, max_days, decode_b64=False)
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
) -> tuple[str, int]:
    """Sanitize unstructured clinical/administrative text while preserving medical utility."""
    total = 0
    work = normalize_digits(text)

    if decode_b64:
        work, n_b64 = sanitize_base64_in_text(work, name_index, patient_key, secret, max_days)
        total += n_b64

    # 1. Names and relatives (with Dr. and clinical phrase protection)
    work, n_names = redact_names_in_text(work, name_index)
    total += n_names

    # 2. Direct identifiers (longest/most specific first)
    for tag, rx in (
        ("[ABHA_NUMBER]", RX_ABHA_NUM),
        ("[ABHA_ADDRESS]", RX_ABHA_ADDR),
        ("[AADHAAR]", RX_AADHAAR),
        ("[AADHAAR_MASKED]", RX_AADHAAR_MASKED),
        ("[INSURANCE_ID]", RX_INSURANCE),
        ("[MRN]", RX_MRN),
        ("[PHONE]", RX_PHONE),
        ("[PHONE_MASKED]", RX_PHONE_MASKED),
        ("[EMAIL]", RX_EMAIL),
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

    # 4. Address components & PIN generalization
    for tag, rx in (
        ("[HOUSE]", RX_HOUSE),
        ("[LOCALITY]", RX_LOCALITY),
        ("[LANDMARK]", RX_LANDMARK),
    ):
        work, n = rx.subn(tag, work)
        total += n

    def _sub_village(m: re.Match[str]) -> str:
        nonlocal total
        total += 1
        return f"{m.group('prefix')}[VILLAGE]"

    work = RX_VILLAGE_LABEL.sub(_sub_village, work)

    def _sub_pin(m: re.Match[str]) -> str:
        nonlocal total
        total += 1
        return generalize_pin(m.group(0))

    work = RX_PIN.sub(_sub_pin, work)

    # 5. Age generalization in text (e.g., "48 Y / F" -> "45-49 Y / F", "आयु: 39 वर्ष" -> "आयु: 35-39 वर्ष")
    work = re.sub(
        r"\b(\d{1,3})(\s*(?:Y|yrs|years)\s*/\s*[MF])\b",
        lambda m: f"{age_band(int(m.group(1)))}{m.group(2)}",
        work,
        flags=re.IGNORECASE,
    )
    work = re.sub(
        r"((?:Age|आयु|उम्र)\s*[:\-]?\s*)(\d{1,3})(\s*(?:yrs|years|वर्ष)?)",
        lambda m: f"{m.group(1)}{age_band(int(m.group(2)))}{m.group(3)}",
        work,
        flags=re.IGNORECASE,
    )

    # 6. Per-patient date shifting (only if we have a key; fallback to deterministic record key)
    if patient_key:
        work = shift_dates_in_text(work, patient_key, secret, max_days)

    return work, total


def sanitize_filename(rel_posix: str, name_index: CorpusNameIndex, raw_sha256: str) -> str:
    """Replace PII in a relative file path (phones, MRNs, patient names) deterministically."""
    p = Path(rel_posix)
    parts = list(p.parts)
    changed = False
    new_parts: list[str] = []
    for idx, part in enumerate(parts):
        is_last = idx == len(parts) - 1
        stem = Path(part).stem if is_last else part
        ext = Path(part).suffix if is_last else ""
        cleaned, n = sanitize_free_text(stem, name_index, None, b"", decode_b64=False)
        # Also catch underscore-separated tokens (preserving '-' for MRNs like IP-26-00130)
        stem_spaces = stem.replace("_", " ")
        cleaned_sp, n2 = sanitize_free_text(stem_spaces, name_index, None, b"", decode_b64=False)
        if n > 0 or n2 > 0 or cleaned != stem or cleaned_sp != stem_spaces:
            changed = True
            # Replace with safe deterministic token
            prefix = "file" if not is_last else stem.split("_")[0].lower()
            if not prefix.isalpha() or len(prefix) > 12 or prefix in name_index.first_names:
                prefix = "doc"
            new_part = f"{prefix}_{raw_sha256[:8]}{ext}" if is_last else f"dir_{raw_sha256[:8]}"
            new_parts.append(new_part)
        else:
            new_parts.append(part)
    if not changed:
        return rel_posix
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
        cleaned, n = sanitize_free_text(val, name_index, patient_key, secret, max_days)
        return cleaned, max(n, 1), True

    # Default: free-text sanitization
    cleaned, n = sanitize_free_text(val, name_index, patient_key, secret, max_days)
    return cleaned, n, False


def sanitize_json_node(
    node,
    parent_key: str,
    name_index: CorpusNameIndex,
    patient_key: str | None,
    pid: str | None,
    secret: bytes,
    max_days: int,
    rare_suppress: bool = False,
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
        return sanitize_structured_cell(kind, node, name_index, patient_key, pid, secret, max_days, rare_suppress)

    if isinstance(node, list):
        out = []
        tot = 0
        gen = False
        for item in node:
            c_item, n, g = sanitize_json_node(item, parent_key, name_index, patient_key, pid, secret, max_days, rare_suppress)
            out.append(c_item)
            tot += n
            gen = gen or g
        return out, tot, gen

    if isinstance(node, dict):
        # Special FHIR Patient & RelatedPerson resource handling
        if node.get("resourceType") == "Patient":
            return _sanitize_fhir_patient(node, name_index, patient_key, pid, secret, max_days, rare_suppress)
        if node.get("resourceType") == "RelatedPerson":
            return _sanitize_fhir_related_person(node, name_index, patient_key, secret, max_days)

        out_dict = {}
        tot = 0
        gen = False
        for k, v in node.items():
            # Sanitize key if it holds PII (e.g., patient_index.json "by_name" / "by_uhid")
            clean_k, nk = sanitize_free_text(k, name_index, None, b"", decode_b64=False)
            tot += nk
            c_v, nv, gv = sanitize_json_node(v, k, name_index, patient_key, pid, secret, max_days, rare_suppress)
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
        clean_txt, n_txt, _ = sanitize_json_node(out["text"], "text", name_index, patient_key, pid, secret, max_days, rare_suppress)
        out["text"] = clean_txt
        tot += n_txt
    return out, tot, True


def _sanitize_fhir_related_person(
    node: dict,
    name_index: CorpusNameIndex,
    patient_key: str | None,
    secret: bytes,
    max_days: int,
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
        clean_txt, n_txt, _ = sanitize_json_node(out["text"], "text", name_index, patient_key, None, secret, max_days, False)
        out["text"] = clean_txt
        tot += n_txt
    return out, tot, False
