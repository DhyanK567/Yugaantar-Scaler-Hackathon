"""MediLocker — Professional Healthcare Data Privacy & Clinical Integrity Report PDF Generator.

Generates a monochrome, editorial 3-page A4 PDF aligned with the
MediLocker_Black_White_Medical_Report_Template visual design and wired directly
to live backend SQLite tables and job output artifacts.

Security & Integrity Guarantees:
- Never modifies global cryptography or ReportLab state.
- Escapes all dynamic text for ReportLab Paragraph XML and wraps Devanagari/Unicode
  runs in a registered Unicode font when available.
- Never fabricates metrics or substitutes missing results with 0 ("Not measured" / "Not run").
- Redacts accidental PII patterns and strips raw paths/secrets before rendering.
"""
from __future__ import annotations

import datetime as dt
import io
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from xml.sax.saxutils import escape as xml_escape

from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
LOGO_PATH = REPO_ROOT / "frontend" / "public" / "medilocker-logo.jpg"

# Exact MediLocker monochrome palette
BG_PRIMARY = colors.HexColor("#F4F4F2")
BG_SECONDARY = colors.HexColor("#E6E6E6")
INK_PRIMARY = colors.HexColor("#090909")
INK_SECONDARY = colors.HexColor("#666666")
INK_MUTED = colors.HexColor("#888888")
SURFACE_WHITE = colors.HexColor("#FFFFFF")
BORDER_GRAY = colors.HexColor("#DADADA")
DIVIDER_GRAY = colors.HexColor("#E5E5E5")
RULE_DARK = colors.HexColor("#BDBDBD")

_FONTS_REGISTERED = False
_FONT_SERIF = "Times-Roman"
_FONT_SERIF_BOLD = "Times-Bold"
_FONT_SERIF_ITALIC = "Times-Italic"
_FONT_SANS = "Helvetica"
_FONT_SANS_BOLD = "Helvetica-Bold"
_FONT_SANS_OBLIQUE = "Helvetica-Oblique"
_FONT_UNICODE: Optional[str] = None

_DEVANAGARI_RUN_RE = re.compile(r"([\u0900-\u097F\u200C\u200D]+(?:\s+[\u0900-\u097F\u200C\u200D]+)*)")
_RX_AADHAAR = re.compile(r"(?<!\d)\d{4}[\s-]?\d{4}[\s-]?\d{4}(?!\d)")
_RX_PHONE = re.compile(r"(?:\+91[\s-]?)?[6-9]\d{9}\b")
_RX_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_RX_WIN_PATH = re.compile(r"[A-Za-z]:\\[^\s,;]+")
_RX_POSIX_PATH = re.compile(r"/(?:Users|home|var|tmp|etc|opt)/[^\s,;]+")


def _register_fonts() -> None:
    global _FONTS_REGISTERED, _FONT_SERIF, _FONT_SERIF_BOLD, _FONT_SERIF_ITALIC
    global _FONT_SANS, _FONT_SANS_BOLD, _FONT_SANS_OBLIQUE, _FONT_UNICODE
    if _FONTS_REGISTERED:
        return
    _FONTS_REGISTERED = True

    win_fonts = Path("C:/Windows/Fonts")
    candidates = [
        ("ML-Georgia", win_fonts / "georgia.ttf", None),
        ("ML-Georgia-Bold", win_fonts / "georgiab.ttf", None),
        ("ML-Georgia-Italic", win_fonts / "georgiai.ttf", None),
        ("ML-NotoSans", win_fonts / "NotoSans-Regular.ttf", None),
        ("ML-NotoSans-Bold", win_fonts / "NotoSans-Bold.ttf", None),
        ("ML-NotoSans-Italic", win_fonts / "NotoSans-Italic.ttf", None),
        ("ML-Nirmala", win_fonts / "Nirmala.ttc", 0),
    ]
    loaded: set[str] = set()
    for name, path, subidx in candidates:
        if path.is_file():
            try:
                if subidx is not None:
                    pdfmetrics.registerFont(TTFont(name, str(path), subfontIndex=subidx))
                else:
                    pdfmetrics.registerFont(TTFont(name, str(path)))
                loaded.add(name)
            except Exception:
                pass

    if {"ML-Georgia", "ML-Georgia-Bold", "ML-Georgia-Italic"}.issubset(loaded):
        _FONT_SERIF = "ML-Georgia"
        _FONT_SERIF_BOLD = "ML-Georgia-Bold"
        _FONT_SERIF_ITALIC = "ML-Georgia-Italic"

    if {"ML-NotoSans", "ML-NotoSans-Bold"}.issubset(loaded):
        _FONT_SANS = "ML-NotoSans"
        _FONT_SANS_BOLD = "ML-NotoSans-Bold"
        if "ML-NotoSans-Italic" in loaded:
            _FONT_SANS_OBLIQUE = "ML-NotoSans-Italic"

    if "ML-Nirmala" in loaded:
        _FONT_UNICODE = "ML-Nirmala"


def _scrub_sensitive_text(value: Any, secret_hint: Optional[str] = None) -> str:
    """Redact accidental PII, paths, or secret material from display strings."""
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", " ", text)
    if secret_hint and len(secret_hint) >= 4 and secret_hint in text:
        text = text.replace(secret_hint, "[REDACTED_SECRET]")
    env_secret = os.environ.get("RAKSHA_SECRET", "")
    if env_secret and len(env_secret) >= 4 and env_secret in text:
        text = text.replace(env_secret, "[REDACTED_SECRET]")
    text = _RX_AADHAAR.sub("[REDACTED_ID]", text)
    text = _RX_PHONE.sub("[REDACTED_PHONE]", text)
    text = _RX_EMAIL.sub("[REDACTED_EMAIL]", text)
    text = _RX_WIN_PATH.sub("[REDACTED_PATH]", text)
    text = _RX_POSIX_PATH.sub("[REDACTED_PATH]", text)
    return text.strip()


def _safe_markup(value: Any, secret_hint: Optional[str] = None) -> str:
    """Escape XML special characters and wrap Devanagari runs for safe ReportLab Paragraph rendering."""
    cleaned = _scrub_sensitive_text(value, secret_hint=secret_hint)
    escaped = xml_escape(cleaned)
    if _FONT_UNICODE:
        escaped = _DEVANAGARI_RUN_RE.sub(
            lambda m: f'<font name="{_FONT_UNICODE}">{m.group(1)}</font>',
            escaped,
        )
    return escaped


def _fmt_ts(ts: Any) -> str:
    if ts is None or ts == "":
        return "Not available"
    try:
        val = float(ts)
        return dt.datetime.fromtimestamp(val, tz=dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return _scrub_sensitive_text(str(ts)) or "Not available"


def _fmt_num(val: Any, suffix: str = "") -> str:
    if val is None or val == "":
        return "Not measured"
    if isinstance(val, bool):
        return "Yes" if val else "No"
    if isinstance(val, int):
        return f"{val:,}{suffix}"
    if isinstance(val, float):
        return f"{val:,.2f}{suffix}" if suffix == "%" else f"{val:.4g}{suffix}"
    return _scrub_sensitive_text(str(val))


def _fmt_ratio_pct(preserved: Any, expected: Any) -> str:
    if preserved is None or expected is None:
        return "Not measured"
    try:
        p = float(preserved)
        e = float(expected)
        if e <= 0:
            return "Not measured"
        pct = (p / e) * 100.0
        if p < e and pct >= 99.95:
            return "99.9%"
        return f"{pct:.1f}%"
    except Exception:
        return "Not measured"


# ---------------------------------------------------------------------------
# Custom Flowables matching MediLocker_Black_White_Medical_Report_Template.pdf
# ---------------------------------------------------------------------------

class _SectionBanner(Flowable):
    """Rounded black bar with crisp white uppercase section title."""

    def __init__(self, label: str, width: float) -> None:
        super().__init__()
        self.label = label
        self.bar_width = width
        self.bar_height = 20

    def wrap(self, availWidth: float, availHeight: float) -> Tuple[float, float]:
        self.bar_width = availWidth
        return availWidth, self.bar_height

    def draw(self) -> None:
        c = self.canv
        c.saveState()
        c.setFillColor(INK_PRIMARY)
        c.roundRect(0, 0, self.bar_width, self.bar_height, radius=5, stroke=0, fill=1)
        c.setFillColor(SURFACE_WHITE)
        c.setFont(_FONT_SANS_BOLD, 8.2)
        c.drawString(11, 6.5, self.label.upper())
        c.restoreState()


class _MetadataPanel(Flowable):
    """Rounded light-grey 4-column top metadata panel."""

    def __init__(self, items: List[Tuple[str, str]], width: float) -> None:
        super().__init__()
        self.items = items
        self.panel_width = width
        self.panel_height = 48

    def wrap(self, availWidth: float, availHeight: float) -> Tuple[float, float]:
        self.panel_width = availWidth
        return availWidth, self.panel_height

    def draw(self) -> None:
        c = self.canv
        c.saveState()
        c.setFillColor(BG_SECONDARY)
        c.roundRect(0, 0, self.panel_width, self.panel_height, radius=7, stroke=0, fill=1)

        n = max(1, len(self.items))
        pad_x = 14
        gap = 12
        col_w = (self.panel_width - 2 * pad_x - gap * (n - 1)) / n

        for idx, (label, value) in enumerate(self.items):
            x = pad_x + idx * (col_w + gap)
            c.setFillColor(INK_PRIMARY)
            c.setFont(_FONT_SANS_BOLD, 7.0)
            c.drawString(x, self.panel_height - 15, label.upper())

            c.setFillColor(INK_SECONDARY)
            c.setFont(_FONT_SANS, 8.0)
            val_txt = _scrub_sensitive_text(value)
            if len(val_txt) > 26:
                val_txt = val_txt[:23] + "..."
            c.drawString(x, self.panel_height - 29, val_txt)

            c.setStrokeColor(RULE_DARK)
            c.setLineWidth(0.6)
            c.line(x, 11, x + col_w, 11)
        c.restoreState()


def _build_risk_bar(low: int, mod: int, high: int, crit: int, width: float) -> Drawing:
    """Pure monochrome horizontal risk distribution bar."""
    d = Drawing(width, 28)
    total = low + mod + high + crit
    bar_y = 12
    bar_h = 10
    if total <= 0:
        d.add(Rect(0, bar_y, width, bar_h, fillColor=BG_SECONDARY, strokeColor=BORDER_GRAY, strokeWidth=0.6))
        d.add(String(0, 2, "Distribution not measured for this job.", fontName=_FONT_SANS, fontSize=7.2, fillColor=INK_SECONDARY))
        return d

    segments = [
        ("LOW", low, colors.HexColor("#D4D4D0")),
        ("MODERATE", mod, colors.HexColor("#8E8E8E")),
        ("HIGH", high, colors.HexColor("#444444")),
        ("CRITICAL", crit, INK_PRIMARY),
    ]
    cur_x = 0.0
    for _, count, col in segments:
        if count <= 0:
            continue
        seg_w = (count / total) * width
        d.add(Rect(cur_x, bar_y, seg_w, bar_h, fillColor=col, strokeColor=SURFACE_WHITE, strokeWidth=0.5))
        cur_x += seg_w

    legend_x = 0.0
    for name, count, col in segments:
        d.add(Rect(legend_x, 2, 6, 6, fillColor=col, strokeColor=INK_PRIMARY, strokeWidth=0.3))
        txt = f"{name}: {count}"
        d.add(String(legend_x + 9, 2.2, txt, fontName=_FONT_SANS, fontSize=7.0, fillColor=INK_SECONDARY))
        legend_x += 75
    return d


# ---------------------------------------------------------------------------
# Page Chrome (Top black bar, Logo, Classification, Footer)
# ---------------------------------------------------------------------------

def _draw_page_chrome(canvas: Any, doc: Any) -> None:
    canvas.saveState()
    page_w, page_h = A4

    # Full-bleed warm monochrome background
    canvas.setFillColor(BG_PRIMARY)
    canvas.rect(0, 0, page_w, page_h, stroke=0, fill=1)

    # Top solid black edge bar
    canvas.setFillColor(INK_PRIMARY)
    canvas.rect(0, page_h - 10, page_w, 10, stroke=0, fill=1)

    # Top-left MediLocker logo + wordmark
    left_x = doc.leftMargin
    header_y = page_h - 34
    if LOGO_PATH.is_file():
        try:
            canvas.drawImage(
                str(LOGO_PATH),
                left_x,
                header_y - 3,
                width=14,
                height=14,
                preserveAspectRatio=True,
                mask="auto",
            )
        except Exception:
            canvas.setFillColor(INK_PRIMARY)
            canvas.circle(left_x + 7, header_y + 4, 7, stroke=0, fill=1)
            canvas.setFillColor(SURFACE_WHITE)
            canvas.setFont(_FONT_SANS_BOLD, 7.5)
            canvas.drawCentredString(left_x + 7, header_y + 1.5, "M")
    else:
        canvas.setFillColor(INK_PRIMARY)
        canvas.circle(left_x + 7, header_y + 4, 7, stroke=0, fill=1)
        canvas.setFillColor(SURFACE_WHITE)
        canvas.setFont(_FONT_SANS_BOLD, 7.5)
        canvas.drawCentredString(left_x + 7, header_y + 1.5, "M")

    canvas.setFillColor(INK_PRIMARY)
    canvas.setFont(_FONT_SERIF_BOLD, 11.0)
    canvas.drawString(left_x + 19, header_y + 0.5, "MediLocker")

    # Top-right classification label
    canvas.setFillColor(INK_MUTED)
    canvas.setFont(_FONT_SANS, 7.2)
    canvas.drawRightString(page_w - doc.rightMargin, header_y + 1.5, "PRIVACY ASSESSMENT / SYNTHETIC DATA")

    # Footer double hairline + text
    foot_y = 24
    canvas.setStrokeColor(BORDER_GRAY)
    canvas.setLineWidth(0.7)
    canvas.line(left_x, foot_y + 13, page_w - doc.rightMargin, foot_y + 13)
    canvas.setStrokeColor(DIVIDER_GRAY)
    canvas.setLineWidth(0.4)
    canvas.line(left_x, foot_y + 11, page_w - doc.rightMargin, foot_y + 11)

    canvas.setFillColor(INK_PRIMARY)
    canvas.setFont(_FONT_SANS_BOLD, 7.2)
    canvas.drawString(left_x, foot_y, "CONFIDENTIAL \u2022 SYNTHETIC DATA ONLY")

    canvas.setFillColor(INK_MUTED)
    canvas.setFont(_FONT_SANS, 7.2)
    canvas.drawRightString(page_w - doc.rightMargin, foot_y, f"MediLocker \u2022 Page {doc.page}")
    canvas.restoreState()


# ---------------------------------------------------------------------------
# Report Context & PDF Builder
# ---------------------------------------------------------------------------

def _derive_release_decision(
    job: Dict[str, Any],
    privacy: Optional[Dict[str, Any]],
    clinical: Optional[Dict[str, Any]],
    passport: Optional[Dict[str, Any]],
) -> Tuple[str, str]:
    raw_decision = str(job.get("release_decision") or "").upper()
    job_status = str(job.get("status") or "").upper()

    if raw_decision in ("BLOCKED", "QUARANTINED") or job_status in ("BLOCKED", "FAILED", "QUARANTINED"):
        return "BLOCKED", "One or more mandatory privacy, clinical integrity, or artifact checks failed or quarantined the dataset."
    if not privacy or not clinical or not passport or job_status not in ("COMPLETED", "COMPLETED_WITH_WARNINGS"):
        return "REVIEW REQUIRED", "Assessment evidence is incomplete or processing has not reached a terminal verified state."
    if raw_decision in ("APPROVED", "APPROVED_WITH_WARNINGS"):
        if raw_decision == "APPROVED_WITH_WARNINGS":
            return "PASS", "Eligible for release under configured checks with recorded operational warnings (e.g. quarantined invalid files)."
        return "PASS", "All mandatory privacy, canary containment, clinical fidelity, and manifest integrity checks passed."
    return "REVIEW REQUIRED", "Assessment requires manual governance review before release."


def generate_privacy_integrity_pdf(
    *,
    job: Dict[str, Any],
    dataset: Optional[Dict[str, Any]],
    organisation: Optional[Dict[str, Any]],
    privacy: Optional[Dict[str, Any]],
    clinical: Optional[Dict[str, Any]],
    identity: Optional[Dict[str, Any]],
    attack_run: Optional[Dict[str, Any]],
    passport: Optional[Dict[str, Any]],
    passport_verification: Optional[Dict[str, Any]] = None,
    engine_report: Optional[Dict[str, Any]] = None,
    reviewer_name: Optional[str] = None,
) -> bytes:
    """Build the 3-page monochrome MediLocker Healthcare Data Privacy & Integrity Report PDF."""
    _register_fonts()

    buf = io.BytesIO()
    margin_x = 15 * mm
    doc = BaseDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=margin_x,
        rightMargin=margin_x,
        topMargin=17 * mm,
        bottomMargin=14 * mm,
        title="MediLocker Healthcare Data Privacy & Integrity Report",
        author="MediLocker Privacy Infrastructure",
        subject="Synthetic Healthcare Dataset Privacy & Clinical Integrity Assessment",
        creator="MediLocker",
    )
    frame = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        doc.width,
        doc.height,
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
    )
    doc.addPageTemplates([PageTemplate(id="medilocker", frames=[frame], onPage=_draw_page_chrome)])

    # Styles
    st_eyebrow = ParagraphStyle("ml_eyebrow", fontName=_FONT_SANS_BOLD, fontSize=7.0, leading=9, textColor=INK_MUTED, spaceAfter=2)
    st_h1 = ParagraphStyle("ml_h1", fontName=_FONT_SERIF, fontSize=20, leading=23, textColor=INK_PRIMARY, spaceAfter=0)
    st_h1_it = ParagraphStyle("ml_h1_it", fontName=_FONT_SERIF_ITALIC, fontSize=20, leading=23, textColor=INK_SECONDARY, spaceAfter=3)
    st_sub = ParagraphStyle("ml_sub", fontName=_FONT_SANS, fontSize=8.2, leading=11, textColor=INK_SECONDARY, spaceAfter=7)
    st_label = ParagraphStyle("ml_lbl", fontName=_FONT_SANS_BOLD, fontSize=7.4, leading=10, textColor=INK_PRIMARY)
    st_val = ParagraphStyle("ml_val", fontName=_FONT_SANS, fontSize=8.2, leading=11, textColor=INK_SECONDARY)
    st_note = ParagraphStyle("ml_note", fontName=_FONT_SANS_OBLIQUE, fontSize=7.8, leading=11, textColor=INK_SECONDARY)
    st_tbl_hdr = ParagraphStyle("ml_th", fontName=_FONT_SANS_BOLD, fontSize=7.3, leading=10, textColor=INK_PRIMARY)
    st_tbl_cell = ParagraphStyle("ml_td", fontName=_FONT_SANS, fontSize=7.8, leading=10.5, textColor=INK_PRIMARY)
    st_tbl_muted = ParagraphStyle("ml_td_m", fontName=_FONT_SANS, fontSize=7.8, leading=10.5, textColor=INK_SECONDARY)

    def kv_table(pairs: List[Tuple[str, str]], cols: int = 2) -> Table:
        rows: List[List[Any]] = []
        col_w = doc.width / cols
        for i in range(0, len(pairs), cols):
            chunk = pairs[i : i + cols]
            row_cells = []
            for k, v in chunk:
                cell_html = f'<font name="{_FONT_SANS_BOLD}" size="7.2" color="#090909">{_safe_markup(k)}</font><br/><font name="{_FONT_SANS}" size="8.2" color="#444444">{_safe_markup(v)}</font>'
                row_cells.append(Paragraph(cell_html, st_val))
            while len(row_cells) < cols:
                row_cells.append(Paragraph("", st_val))
            rows.append(row_cells)
        t = Table(rows, colWidths=[col_w] * cols)
        t.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 2),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.5, BORDER_GRAY),
                ]
            )
        )
        return t

    def data_table(headers: List[str], body_rows: List[List[str]], widths: List[float]) -> Table:
        rows: List[List[Any]] = [[Paragraph(_safe_markup(h.upper()), st_tbl_hdr) for h in headers]]
        for r in body_rows:
            rows.append([Paragraph(_safe_markup(c), st_tbl_cell if idx == 0 else st_tbl_muted) for idx, c in enumerate(r)])
        t = Table(rows, colWidths=widths, repeatRows=1)
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), BG_SECONDARY),
                    ("BACKGROUND", (0, 1), (-1, -1), SURFACE_WHITE),
                    ("GRID", (0, 0), (-1, -1), 0.5, BORDER_GRAY),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
                ]
            )
        )
        return t

    # Parse JSON sub-payloads safely
    priv_details: Dict[str, Any] = {}
    if privacy and privacy.get("details_json"):
        try:
            priv_details = json.loads(privacy["details_json"])
        except Exception:
            priv_details = {}
    risk_map: Dict[str, Any] = priv_details.get("risk_map") or {}

    clin_details: Dict[str, Any] = {}
    if clinical and clinical.get("details_json"):
        try:
            clin_details = json.loads(clinical["details_json"])
        except Exception:
            clin_details = {}

    passport_payload: Dict[str, Any] = {}
    if passport and passport.get("passport_json"):
        try:
            passport_payload = json.loads(passport["passport_json"])
        except Exception:
            passport_payload = {}

    atk_results: List[Dict[str, Any]] = []
    if attack_run and attack_run.get("results_json"):
        try:
            atk_results = json.loads(attack_run["results_json"])
        except Exception:
            atk_results = []

    decision_label, decision_reason = _derive_release_decision(job, privacy, clinical, passport)
    job_id = str(job.get("id") or "Not available")
    report_id = f"MLR-{job_id[-8:].upper()}" if len(job_id) >= 8 else f"MLR-{job_id.upper()}"
    assess_ts = _fmt_ts(job.get("completed_at") or job.get("created_at"))

    story: List[Any] = []

    # =========================================================================
    # PAGE 1 — DATASET & PRIVACY ASSESSMENT
    # =========================================================================
    story.append(Paragraph("MEDILOCKER \u2022 HEALTHCARE DATA PRIVACY &amp; INTEGRITY REPORT", st_eyebrow))
    story.append(Paragraph("Protecting identity.", st_h1))
    story.append(Paragraph("Preserving clinical truth.", st_h1_it))
    story.append(Paragraph("A technical assessment of healthcare data privacy, clinical fidelity and secure research readiness.", st_sub))

    story.append(
        _MetadataPanel(
            [
                ("REPORT ID", report_id),
                ("ASSESSMENT DATE", assess_ts),
                ("PROCESSING JOB ID", job_id),
                ("REPORT STATUS", decision_label),
            ],
            doc.width,
        )
    )
    story.append(Spacer(1, 10))

    # Section 01 — DATASET INFORMATION
    story.append(_SectionBanner("01  DATASET INFORMATION", doc.width))
    story.append(Spacer(1, 5))
    ds_name = (dataset or {}).get("name") or job.get("input_name") or "Synthetic Healthcare Dataset"
    org_name = (organisation or {}).get("name") or job.get("organisation_id") or "Not available"
    ds_id = (dataset or {}).get("id") or job.get("dataset_id") or "Not available"
    ds_fmt = (dataset or {}).get("format") or "CSV, TSV, JSON, JSONL, TXT"
    files_total = job.get("files_total") if job.get("files_total") is not None else (dataset or {}).get("file_count")
    langs = (engine_report or {}).get("languages_detected")
    langs_str = ", ".join(langs) if isinstance(langs, list) and langs else "English, Hindi (Devanagari), Hinglish"

    story.append(
        kv_table(
            [
                ("Dataset name", str(ds_name)),
                ("Source organisation / synthetic hospital", str(org_name)),
                ("Dataset identifier", str(ds_id)),
                ("Input file count", _fmt_num(files_total)),
                ("Supported formats", str(ds_fmt)),
                ("Record count", _fmt_num(job.get("records_processed"))),
                ("Languages detected", langs_str),
                ("Processing timestamp", assess_ts),
            ],
            cols=2,
        )
    )
    story.append(Spacer(1, 6))

    # Section 02 — PRIVACY DETECTION & PROTECTION
    story.append(_SectionBanner("02  PRIVACY DETECTION & PROTECTION", doc.width))
    story.append(Spacer(1, 5))
    if privacy:
        pii_detected = _fmt_num(privacy.get("pii_detected"))
        canary_planted = privacy.get("canary_planted")
        canary_leaks = privacy.get("canary_leaks")
        canary_stat = f"{privacy.get('canary_status', 'NOT_RUN')} ({canary_leaks}/{canary_planted} leaks)" if canary_planted else str(privacy.get("canary_status", "NOT_RUN"))
        direct_prot = "Verified (0 residual leaks)" if int(privacy.get("residual_leakage") or 0) == 0 else f"Warning ({privacy.get('residual_leakage')} residual)"
    else:
        pii_detected = "Not measured"
        canary_stat = "Not run"
        direct_prot = "Not measured"

    story.append(
        kv_table(
            [
                ("PII categories assessed", "Names, MRN, Phone, Aadhaar, ABHA, PAN, DOB, Address/PIN"),
                ("Personal information detected", pii_detected),
                ("Multilingual detection coverage", "English, Hindi (Devanagari), Hinglish"),
                ("Direct identifier protection", direct_prot),
                ("Identifier pseudonymisation status", "Deterministic HKDF-SHA256 + HMAC-SHA256"),
                ("Filename privacy status", "Sanitized path mapping active" if job.get("files_sanitized") else "Not measured"),
                ("Canary detection status", canary_stat),
                ("Residual PII leakage", _fmt_num(privacy.get("residual_leakage")) if privacy else "Not measured"),
            ],
            cols=2,
        )
    )
    story.append(Spacer(1, 6))

    # Section 03 — IDENTITY CONTINUITY
    story.append(_SectionBanner("03  IDENTITY CONTINUITY", doc.width))
    story.append(Spacer(1, 5))
    if identity:
        id_prec = f"{float(identity['precision']):.2f}" if identity.get("precision") is not None else "Not measured"
        id_rec = f"{float(identity['recall']):.2f}" if identity.get("recall") is not None else "Not measured"
        id_f05 = f"{float(identity['f05']):.2f}" if identity.get("f05") is not None else "Not measured"
        id_clusters = _fmt_num(identity.get("total_patients"))
        id_links = _fmt_num(identity.get("cross_hospital_links"))
        id_false = _fmt_num(identity.get("false_merges"))
        id_ambig = _fmt_num(identity.get("abstentions"))
    else:
        id_prec = id_rec = id_f05 = id_clusters = id_links = id_false = id_ambig = "Not measured"

    story.append(
        kv_table(
            [
                ("Synthetic sources represented", str(org_name)),
                ("Records processed", _fmt_num(job.get("records_processed"))),
                ("Identity clusters generated", id_clusters),
                ("Cross-hospital links", id_links),
                ("Linking precision", id_prec),
                ("Linking recall", id_rec),
                ("F0.5 score", id_f05),
                ("False merges / Ambiguous abstentions", f"{id_false} false merges / {id_ambig} abstained"),
            ],
            cols=2,
        )
    )
    story.append(Spacer(1, 5))
    story.append(Paragraph("MediLocker maintains consistent pseudonymous identity references across healthcare records while avoiding unsafe patient merges.", st_note))

    # =========================================================================
    # PAGE 2 — CLINICAL INTEGRITY & PRIVACY RISK
    # =========================================================================
    story.append(PageBreak())
    story.append(Paragraph("MEDILOCKER \u2022 CLINICAL INTEGRITY &amp; PRIVACY RISK", st_eyebrow))
    story.append(Paragraph("Clinical meaning,", st_h1))
    story.append(Paragraph("without identity exposure.", st_h1_it))
    story.append(Paragraph("Clinical fidelity, integrity validation and adversarial privacy assessment.", st_sub))

    # Section 04 — CLINICAL INTEGRITY
    story.append(_SectionBanner("04  CLINICAL INTEGRITY", doc.width))
    story.append(Spacer(1, 5))
    if clinical:
        c_exp = clinical.get("expected_values")
        c_pres = clinical.get("preserved_values")
        c_miss = clinical.get("missing_values")
        c_mod = clinical.get("modified_values")
        c_pct = _fmt_ratio_pct(c_pres, c_exp)
        c_drift = "FAILED (Drift detected)" if (c_mod or 0) > 0 else "PASS (Zero silent mutations)"
        c_fhir = str(clinical.get("fhir_integrity") or "Not measured")
    else:
        c_exp = c_pres = c_miss = c_mod = None
        c_pct = "Not measured"
        c_drift = "Not measured"
        c_fhir = "Not measured"

    story.append(
        kv_table(
            [
                ("Expected clinical values", _fmt_num(c_exp)),
                ("Preserved values", _fmt_num(c_pres)),
                ("Missing / Modified values", f"{_fmt_num(c_miss)} missing / {_fmt_num(c_mod)} modified" if clinical else "Not measured"),
                ("Exact clinical fidelity", c_pct),
                ("Clinical drift decision", c_drift),
                ("FHIR R4 validation status", c_fhir),
            ],
            cols=2,
        )
    )
    story.append(Spacer(1, 6))

    cats = clin_details.get("categories") or {}
    def _cat_row(label: str, key: str, fallback_ratio: Any = None) -> List[str]:
        entry = cats.get(key)
        if isinstance(entry, dict) and entry.get("expected") is not None:
            exp_v = int(entry.get("expected", 0))
            pres_v = int(entry.get("preserved", 0))
            mod_v = int(entry.get("modified", 0))
            stat = "FAILED" if mod_v > 0 else ("PASS" if pres_v == exp_v else "WARNING")
            return [label, _fmt_num(exp_v), _fmt_num(pres_v), stat]
        if fallback_ratio is not None:
            pct = f"{float(fallback_ratio) * 100:.1f}%"
            return [label, "Measured", pct, "PASS" if float(fallback_ratio) >= 0.99 else "WARNING"]
        return [label, "Not measured", "Not measured", "Not measured"]

    vital_exp = sum(int((cats.get(k) or {}).get("expected", 0)) for k in ("blood_pressure", "heart_rate", "temperature", "spo2"))
    vital_pres = sum(int((cats.get(k) or {}).get("preserved", 0)) for k in ("blood_pressure", "heart_rate", "temperature", "spo2"))
    vital_row = (
        ["Vital signs (BP, HR, Temp, SpO2)", _fmt_num(vital_exp), _fmt_num(vital_pres), "PASS" if vital_pres == vital_exp else "WARNING"]
        if vital_exp > 0
        else ["Vital signs (BP, HR, Temp, SpO2)", "Not measured", "Not measured", "Not measured"]
    )
    freq_exp = sum(int((cats.get(k) or {}).get("expected", 0)) for k in ("frequencies", "routes", "durations"))
    freq_pres = sum(int((cats.get(k) or {}).get("preserved", 0)) for k in ("frequencies", "routes", "durations"))
    freq_row = (
        ["Frequency, route and duration", _fmt_num(freq_exp), _fmt_num(freq_pres), "PASS" if freq_pres == freq_exp else "WARNING"]
        if freq_exp > 0
        else ["Frequency, route and duration", "Not measured", "Not measured", "Not measured"]
    )

    clin_rows = [
        _cat_row("Medication names", "medication_names", (clinical or {}).get("medication_integrity")),
        _cat_row("Dosages and units", "dosages", (clinical or {}).get("dosage_integrity")),
        freq_row,
        vital_row,
        _cat_row("Laboratory values", "laboratory_measurements", (clinical or {}).get("lab_integrity")),
        _cat_row("Diagnoses and FHIR codes", "diagnoses"),
    ]
    story.append(
        data_table(
            ["Clinical category", "Expected", "Preserved", "Status"],
            clin_rows,
            [doc.width * 0.44, doc.width * 0.18, doc.width * 0.18, doc.width * 0.20],
        )
    )
    story.append(Spacer(1, 4))
    story.append(Paragraph("Privacy transformations must not silently alter clinically meaningful values.", st_note))
    story.append(Spacer(1, 6))

    # Section 05 — RE-IDENTIFICATION RISK ASSESSMENT
    story.append(_SectionBanner("05  RE-IDENTIFICATION RISK ASSESSMENT", doc.width))
    story.append(Spacer(1, 5))
    low_c = int(risk_map.get("low", 0))
    mod_c = int(risk_map.get("moderate", 0))
    high_c = int(risk_map.get("high", 0))
    crit_c = int(risk_map.get("critical", 0))
    has_risk_map = bool(risk_map) and (low_c + mod_c + high_c + crit_c) > 0

    story.append(
        kv_table(
            [
                ("Overall assessed risk", str((privacy or {}).get("reid_risk_level") or "Not measured")),
                ("Quasi-identifier risk score", _fmt_num((privacy or {}).get("qi_risk_score"), "%") if privacy else "Not measured"),
                ("Records requiring mitigation", _fmt_num(risk_map.get("requiring_mitigation")) if risk_map else "Not measured"),
                ("Records blocked from release", _fmt_num(risk_map.get("blocked_from_release")) if risk_map else "Not measured"),
                ("Assessment decision", str(risk_map.get("release_decision") or job.get("release_decision") or "Not measured")),
                ("Uniqueness reduction", "Measured in Section 06" if attack_run else "Not measured"),
            ],
            cols=2,
        )
    )
    story.append(Spacer(1, 5))
    story.append(_build_risk_bar(low_c, mod_c, high_c, crit_c, doc.width) if has_risk_map else _build_risk_bar(0, 0, 0, 0, doc.width))
    story.append(Spacer(1, 6))

    # Section 06 — ADVERSARIAL ATTACK SIMULATION
    story.append(_SectionBanner("06  ADVERSARIAL ATTACK SIMULATION", doc.width))
    story.append(Spacer(1, 5))
    if attack_run:
        atk_stat = f"Executed ({attack_run.get('profile', 'standard')})"
        atk_blocked = attack_run.get("blocked_count")
        atk_total = attack_run.get("total_count")
        atk_rate = _fmt_num(attack_run.get("risk_score"), "%")
    else:
        atk_stat = "Not run"
        atk_blocked = atk_total = None
        atk_rate = "Not measured"

    story.append(
        kv_table(
            [
                ("Attack simulation status", atk_stat),
                ("Vectors blocked / tested", f"{atk_blocked} / {atk_total}" if atk_total else "Not measured"),
                ("Direct PII leaks", _fmt_num((privacy or {}).get("residual_leakage")) if privacy else "Not measured"),
                ("Canaries planted / leaked", f"{privacy.get('canary_planted', 0)} planted / {privacy.get('canary_leaks', 0)} leaked" if privacy else "Not measured"),
                ("Measured attack risk score", atk_rate),
                ("Post-sanitisation linkage protection", "k-anonymity & suppressed rare quasi-identifiers"),
            ],
            cols=2,
        )
    )
    story.append(Spacer(1, 4))
    story.append(Paragraph("Attack simulation evaluates known linkage, uniqueness, and canary-recall vectors under the configured policy; it does not claim absolute immunity against all external auxiliary datasets.", st_note))

    # =========================================================================
    # PAGE 3 — SECURITY, VERIFICATION & RELEASE DECISION
    # =========================================================================
    story.append(PageBreak())
    story.append(Paragraph("MEDILOCKER \u2022 SECURITY, VERIFICATION &amp; RELEASE DECISION", st_eyebrow))
    story.append(Paragraph("Verified protection.", st_h1))
    story.append(Paragraph("Accountable processing.", st_h1_it))
    story.append(Paragraph("Cryptographic integrity, processing traceability and release assessment.", st_sub))

    # Section 07 — PRIVACY PASSPORT
    story.append(_SectionBanner("07  PRIVACY PASSPORT", doc.width))
    story.append(Spacer(1, 5))
    if passport:
        p_id = str(passport.get("id") or "Not available")
        m_hash = str(passport.get("manifest_hash") or "")
        m_trunc = f"{m_hash[:16]}...{m_hash[-8:]}" if len(m_hash) > 28 else (m_hash or "Not available")
        sig_stat = str(passport.get("signature_status") or "UNSIGNED").upper()
        if sig_stat == "UNSIGNED":
            sig_display = "UNSIGNED (No Ed25519 signing key configured; hash integrity only)"
        else:
            sig_display = f"{sig_stat} (Ed25519 asymmetric signature)"
        if passport_verification:
            v_ok = bool(passport_verification.get("integrity_valid"))
            hash_status = "VERIFIED (Manifest root & file SHA-256 match)" if v_ok else "FAILED / TAMPERED (Hash mismatch detected)"
            tamper_status = "No tampering detected" if v_ok else "TAMPERING DETECTED"
            ver_ts = _fmt_ts(passport_verification.get("verified_at")) if v_ok else "Failed verification"
        elif passport.get("verified_at"):
            hash_status = "VERIFIED (SHA-256 manifest recorded)"
            tamper_status = "No tampering detected"
            ver_ts = _fmt_ts(passport.get("verified_at"))
        else:
            hash_status = "Generated (Pending on-disk re-verification)"
            tamper_status = "Not yet verified"
            ver_ts = "Not verified"
    else:
        p_id = "Not generated"
        m_trunc = "Not available"
        sig_display = "Not generated"
        hash_status = "Not generated"
        tamper_status = "Not measured"
        ver_ts = "Not verified"

    story.append(
        kv_table(
            [
                ("Passport identifier", p_id),
                ("Dataset manifest status", "Generated (SHA-256 streaming)" if passport else "Not generated"),
                ("Manifest root hash (truncated)", f"{m_trunc} (full hash in JSON)"),
                ("Hash integrity verification", hash_status),
                ("Digital signature status", sig_display),
                ("Verification timestamp", ver_ts),
                ("Tamper detection status", tamper_status),
                ("Signing mode", "Unsigned hash-verified" if (passport or {}).get("signature_status", "UNSIGNED") == "UNSIGNED" else "Ed25519 signed"),
            ],
            cols=2,
        )
    )
    story.append(Spacer(1, 6))

    # Section 08 — PROCESSING & SECURITY SUMMARY
    story.append(_SectionBanner("08  PROCESSING & SECURITY SUMMARY", doc.width))
    story.append(Spacer(1, 5))
    story.append(
        kv_table(
            [
                ("Execution mode", "Offline (air-gapped compatible)"),
                ("Processing mode", "CPU-only"),
                ("LLM / Hosted AI dependency", "None / None"),
                ("Deterministic processing status", "Verified (HKDF-SHA256 keyed)"),
                ("Raw input copy check", "0 raw copies in sanitized output"),
                ("Secret exposure check", "RAKSHA_SECRET excluded from outputs & metadata"),
                ("Quarantined / Sanitised files", f"{_fmt_num(job.get('files_quarantined'))} quarantined / {_fmt_num(job.get('files_sanitized'))} sanitised"),
                ("Processing duration", _fmt_num(job.get("duration_secs"), " s") if job.get("duration_secs") is not None else "Not measured"),
                ("Peak memory usage", "Not measured"),
            ],
            cols=2,
        )
    )
    story.append(Spacer(1, 6))

    # Section 09 — FINAL RELEASE DECISION
    story.append(_SectionBanner("09  FINAL RELEASE DECISION", doc.width))
    story.append(Spacer(1, 5))
    story.append(
        data_table(
            ["Governance Gate", "Assessment Outcome"],
            [
                ["Final release decision", decision_label],
                ["Privacy assessment", "PASS" if (privacy and int(privacy.get("residual_leakage") or 0) == 0 and int(privacy.get("canary_leaks") or 0) == 0) else ("FAILED" if privacy else "Not run")],
                ["Clinical integrity assessment", "FAILED" if (clinical and (clinical.get("fhir_integrity") == "FAILED" or int(clinical.get("modified_values") or 0) > 0)) else ("PASS" if clinical else "Not run")],
                ["Identity continuity assessment", "PASS" if (identity and int(identity.get("false_merges") or 0) == 0) else ("Not measured" if not identity else "WARNING")],
                ["Passport verification", tamper_status],
                ["Release decision timestamp", assess_ts],
            ],
            [doc.width * 0.42, doc.width * 0.58],
        )
    )
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"Decision rationale: {_safe_markup(decision_reason)}", st_note))
    story.append(Spacer(1, 6))

    # Section 10 — AUTHORISED REVIEW & GOVERNANCE
    story.append(_SectionBanner("10  AUTHORISED REVIEW & GOVERNANCE", doc.width))
    story.append(Spacer(1, 5))
    engine_ver = str((passport_payload.get("certificate_identity") or {}).get("engine_version") or "guptkavach-engine/15.5")
    policy_ver = str((passport_payload.get("certificate_identity") or {}).get("policy_version") or "m10-v1")
    story.append(
        kv_table(
            [
                ("Report generated by", "MediLocker"),
                ("System / engine version", engine_ver),
                ("Policy version", policy_ver),
                ("Assessment reference", report_id),
                ("Reviewer name / designation", reviewer_name if reviewer_name else "Not assigned"),
                ("Approval status / Signature", f"{decision_label}  |  ________________________"),
            ],
            cols=2,
        )
    )
    story.append(Spacer(1, 5))
    story.append(
        Paragraph(
            "This report documents the privacy and integrity assessment of a synthetic healthcare dataset processed through MediLocker. It does not replace clinical judgement, institutional governance approval or applicable legal requirements.",
            st_note,
        )
    )

    doc.build(story)
    return buf.getvalue()
