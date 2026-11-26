"""Security validation, XML escaping, and output scanning for MediLocker PDFs."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional
from xml.sax.saxutils import escape as xml_escape


class PdfSecurityError(ValueError):
    """Raised when report input or generated PDF fails security validation."""


_PROHIBITED_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("AADHAAR", re.compile(r"(?<!\d)\d{4}[ \t-]?\d{4}[ \t-]?\d{4}(?!\d)")),
    ("ABHA", re.compile(r"(?<!\d)91[ \t-]?\d{2}[ \t-]?\d{4}[ \t-]?\d{4}[ \t-]?\d{4}(?!\d)")),
    ("PAN", re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")),
    ("PHONE", re.compile(r"(?<!\d)(?:\+91[ \t-]?)?[6-9]\d{4}[ \t-]?\d{5}(?!\d)")),
    ("EMAIL", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("CANARY", re.compile(r"CANARY_[A-Z0-9_]+")),
    ("TRACEBACK", re.compile(r"Traceback \(most recent call last\)")),
]

_MARKUP_TAG_RE = re.compile(r"<\s*/?\s*(?:script|font|para|b|i|u|img|a|link|iframe)[^>]*>", re.IGNORECASE)


def sanitize_safe_text(value: object, max_len: int = 240) -> str:
    """Convert to clean single-line ASCII/printable text without untrusted markup."""
    raw = "" if value is None else str(value)
    # Strip any XML/HTML/ReportLab markup tags from untrusted strings
    cleaned = _MARKUP_TAG_RE.sub("", raw)
    cleaned = " ".join(cleaned.replace("\x00", "").split())
    if len(cleaned) > max_len:
        cleaned = cleaned[: max_len - 3] + "..."
    return cleaned


def escape_xml(value: object, max_len: int = 240) -> str:
    """Escape XML-sensitive characters for safe ReportLab Paragraph rendering."""
    return xml_escape(sanitize_safe_text(value, max_len=max_len))


def safe_filename(prefix: str, identifier: str) -> str:
    clean_id = re.sub(r"[^A-Za-z0-9_-]", "_", Path(identifier).name)[:48] or "report"
    clean_pre = re.sub(r"[^A-Za-z0-9_-]", "_", prefix)[:32] or "MediLocker"
    return f"{clean_pre}_{clean_id}.pdf"


_PDF_TEXT_RE = re.compile(r"\(([^()\\]*(?:\\.[^()\\]*)*)\)")
_SHA256_HEX_RE = re.compile(r"\b[0-9a-fA-F]{64}\b")


def scan_pdf_bytes_for_leaks(pdf_bytes: bytes, extra_forbidden: Optional[list[str]] = None) -> None:
    """Scan generated PDF text stream for prohibited PII, canaries, and secrets."""
    if not pdf_bytes.startswith(b"%PDF-"):
        raise PdfSecurityError("INVALID_PDF_HEADER")

    decoded = pdf_bytes.decode("latin-1", errors="ignore")
    text_chunks = [
        m.group(1).replace("\\(", "(").replace("\\)", ")").replace("\\\\", "\\")
        for m in _PDF_TEXT_RE.finditer(decoded)
    ]
    surface = "\n".join(text_chunks) if text_chunks else decoded
    surface_no_hash = _SHA256_HEX_RE.sub("[SHA256]", surface)

    raksha_secret = os.environ.get("RAKSHA_SECRET", "")
    if raksha_secret and len(raksha_secret) >= 4 and raksha_secret in surface:
        raise PdfSecurityError("SECRET_LEAK_DETECTED_IN_PDF")

    for label, rx in _PROHIBITED_PATTERNS:
        target = surface_no_hash if label in ("AADHAAR", "ABHA", "PHONE") else surface
        if rx.search(target):
            raise PdfSecurityError(f"PROHIBITED_{label}_PATTERN_IN_PDF")

    for forbidden in extra_forbidden or []:
        if forbidden and len(forbidden) >= 4 and forbidden in surface:
            raise PdfSecurityError("FORBIDDEN_TOKEN_IN_PDF")
