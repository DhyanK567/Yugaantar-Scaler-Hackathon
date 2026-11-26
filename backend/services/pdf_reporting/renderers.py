"""Offline A4 PDF renderers (ReportLab when available, deterministic stdlib PDF-1.4 fallback)."""
from __future__ import annotations

import io
import os
import tempfile
import textwrap
from pathlib import Path
from typing import List

from .schemas import ReportDocument
from .security import escape_xml, sanitize_safe_text
from .templates import (
    A4_HEIGHT,
    A4_WIDTH,
    BRAND_NAME,
    MARGIN_BOTTOM,
    MARGIN_LEFT,
    MARGIN_RIGHT,
    MARGIN_TOP,
)

try:
    from reportlab.lib import colors as rl_colors  # type: ignore
    from reportlab.lib.pagesizes import A4 as RL_A4  # type: ignore
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # type: ignore
    from reportlab.platypus import (  # type: ignore
        HRFlowable,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


def _pdf_escape(text: str) -> str:
    ascii_safe = text.encode("latin-1", errors="replace").decode("latin-1")
    return ascii_safe.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _render_stdlib_pdf(doc: ReportDocument) -> bytes:
    """Pure Python standard-library multi-page A4 PDF 1.4 writer."""
    lines: list[tuple[str, str, int]] = []  # (font_key, text, size)
    lines.append(("F2", sanitize_safe_text(doc.title, 120), 15))
    lines.append(("F1", sanitize_safe_text(doc.subtitle, 140), 10))
    lines.append(("F1", f"Report ID: {sanitize_safe_text(doc.report_id)} | Org: {sanitize_safe_text(doc.organisation)}", 9))
    lines.append(("F1", f"Generated: {sanitize_safe_text(doc.generated_at)} | {sanitize_safe_text(doc.classification)}", 8))
    lines.append(("F1", "-" * 96, 8))

    for sec in doc.sections:
        lines.append(("F2", "", 6))
        lines.append(("F2", sanitize_safe_text(sec.title, 100), 11))
        for k, v in sec.key_values:
            wrapped = textwrap.wrap(f"{sanitize_safe_text(k)}: {sanitize_safe_text(v)}", width=92) or [""]
            for wline in wrapped:
                lines.append(("F1", wline, 9))
        if sec.table_headers:
            hdr = " | ".join(sanitize_safe_text(h, 30) for h in sec.table_headers)
            lines.append(("F2", hdr[:100], 8))
            if not sec.table_rows:
                lines.append(("F1", "(No rows recorded)", 8))
            for row in sec.table_rows:
                rtxt = " | ".join(sanitize_safe_text(c, 36) for c in row)
                for wline in textwrap.wrap(rtxt, width=96) or [""]:
                    lines.append(("F1", wline, 8))
        for note in sec.notes:
            for wline in textwrap.wrap(f"* {sanitize_safe_text(note, 220)}", width=94) or [""]:
                lines.append(("F1", wline, 8))

    # Paginate into A4 pages
    usable_height = A4_HEIGHT - MARGIN_TOP - MARGIN_BOTTOM
    pages: list[list[tuple[str, str, int, float]]] = []
    cur_page: list[tuple[str, str, int, float]] = []
    y = A4_HEIGHT - MARGIN_TOP

    for font_k, txt, sz in lines:
        step = sz + 4.5
        if y - step < MARGIN_BOTTOM and cur_page:
            pages.append(cur_page)
            cur_page = []
            y = A4_HEIGHT - MARGIN_TOP
        cur_page.append((font_k, txt, sz, y))
        y -= step
    if cur_page or not pages:
        pages.append(cur_page)

    total_pages = len(pages)
    # Build PDF objects: 1=Catalog, 2=Pages, 3=Font F1, 4=Font F2, then pairs of (Page, Content)
    objects: list[bytes] = []

    def add_obj(body: bytes) -> int:
        objects.append(body)
        return len(objects)

    catalog_id = add_obj(b"<< /Type /Catalog /Pages 2 0 R >>")
    pages_id = add_obj(b"PLACEHOLDER_PAGES")
    f1_id = add_obj(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    f2_id = add_obj(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")

    page_ids: list[int] = []
    for p_idx, items in enumerate(pages, 1):
        cmds: list[str] = ["BT"]
        # Header banner
        cmds.append(f"/F2 8 Tf {MARGIN_LEFT} {A4_HEIGHT - 28} Td ({_pdf_escape(BRAND_NAME)}) Tj ET BT")
        cmds.append(f"/F1 7 Tf {MARGIN_LEFT} {A4_HEIGHT - 39} Td ({_pdf_escape(doc.classification)}) Tj ET BT")
        for font_k, txt, sz, py in items:
            if txt:
                cmds.append(f"/{font_k} {sz} Tf {MARGIN_LEFT} {py:.1f} Td ({_pdf_escape(txt)}) Tj ET BT")
        # Footer with page numbers
        footer = f"Report {sanitize_safe_text(doc.report_id)} | Page {p_idx} of {total_pages}"
        cmds.append(f"/F1 8 Tf {MARGIN_LEFT} 24 Td ({_pdf_escape(footer)}) Tj ET")
        stream_bytes = "\n".join(cmds).encode("latin-1", errors="replace")
        content_id = add_obj(
            f"<< /Length {len(stream_bytes)} >>\nstream\n".encode("ascii") + stream_bytes + b"\nendstream"
        )
        page_id = add_obj(
            f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 {A4_WIDTH} {A4_HEIGHT}] "
            f"/Resources << /Font << /F1 {f1_id} 0 R /F2 {f2_id} 0 R >> >> /Contents {content_id} 0 R >>".encode("ascii")
        )
        page_ids.append(page_id)

    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    objects[pages_id - 1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode("ascii")

    buf = io.BytesIO()
    buf.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets: list[int] = [0]
    for idx, obj in enumerate(objects, 1):
        offsets.append(buf.tell())
        buf.write(f"{idx} 0 obj\n".encode("ascii"))
        buf.write(obj)
        buf.write(b"\nendobj\n")

    xref_pos = buf.tell()
    buf.write(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    buf.write(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        buf.write(f"{off:010d} 00000 n \n".encode("ascii"))
    buf.write(
        f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode("ascii")
    )
    return buf.getvalue()


def _render_reportlab_pdf(doc: ReportDocument) -> bytes:
    buf = io.BytesIO()
    pdf = SimpleDocTemplate(
        buf,
        pagesize=RL_A4,
        leftMargin=MARGIN_LEFT,
        rightMargin=MARGIN_RIGHT,
        topMargin=MARGIN_TOP,
        bottomMargin=MARGIN_BOTTOM,
    )
    styles = getSampleStyleSheet()
    title_st = ParagraphStyle("MLTitle", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=15, leading=19)
    sub_st = ParagraphStyle("MLSub", parent=styles["Normal"], fontName="Helvetica", fontSize=9.5, leading=13, textColor=rl_colors.HexColor("#475569"))
    h2_st = ParagraphStyle("MLH2", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=11, leading=14, spaceBefore=8, spaceAfter=4)
    body_st = ParagraphStyle("MLBody", parent=styles["Normal"], fontName="Helvetica", fontSize=8.5, leading=11)

    story = [
        Paragraph(escape_xml(doc.title, 120), title_st),
        Paragraph(escape_xml(doc.subtitle, 160), sub_st),
        Paragraph(
            f"Report ID: {escape_xml(doc.report_id)} | Organisation: {escape_xml(doc.organisation)} | Generated: {escape_xml(doc.generated_at)}",
            sub_st,
        ),
        Spacer(1, 6),
        HRFlowable(width="100%", thickness=0.8, color=rl_colors.HexColor("#CBD5E1")),
    ]

    for sec in doc.sections:
        story.append(Paragraph(escape_xml(sec.title, 100), h2_st))
        if sec.key_values:
            kv_rows = [[Paragraph(escape_xml(k), body_st), Paragraph(escape_xml(v), body_st)] for k, v in sec.key_values]
            tbl = Table(kv_rows, colWidths=[170, 340], repeatRows=0)
            tbl.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, rl_colors.HexColor("#E2E8F0")), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
            story.append(tbl)
            story.append(Spacer(1, 5))
        if sec.table_headers:
            rows = [[Paragraph(escape_xml(h), body_st) for h in sec.table_headers]]
            for r in sec.table_rows or [["(No rows recorded)"] + [""] * (len(sec.table_headers) - 1)]:
                rows.append([Paragraph(escape_xml(c), body_st) for c in r])
            col_w = 510 / max(1, len(sec.table_headers))
            tbl2 = Table(rows, colWidths=[col_w] * len(sec.table_headers), repeatRows=1)
            tbl2.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), rl_colors.HexColor("#F1F5F9")),
                    ("GRID", (0, 0), (-1, -1), 0.4, rl_colors.HexColor("#CBD5E1")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ])
            )
            story.append(tbl2)
            story.append(Spacer(1, 5))
        for note in sec.notes:
            story.append(Paragraph(f"- {escape_xml(note, 220)}", body_st))

    def _draw_chrome(canvas, doc_obj):
        canvas.saveState()
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawString(MARGIN_LEFT, A4_HEIGHT - 28, BRAND_NAME)
        canvas.setFont("Helvetica", 7)
        canvas.drawString(MARGIN_LEFT, A4_HEIGHT - 38, sanitize_safe_text(doc.classification))
        canvas.drawString(MARGIN_LEFT, 24, f"Report {sanitize_safe_text(doc.report_id)} | Page {doc_obj.page}")
        canvas.restoreState()

    pdf.build(story, onFirstPage=_draw_chrome, onLaterPages=_draw_chrome)
    return buf.getvalue()


def render_report_pdf(doc: ReportDocument) -> bytes:
    """Render a validated ReportDocument to A4 PDF bytes."""
    if HAS_REPORTLAB:
        return _render_reportlab_pdf(doc)
    return _render_stdlib_pdf(doc)


def write_pdf_atomic(dest: Path, pdf_bytes: bytes) -> None:
    """Atomically write PDF bytes to disk without leaving partial files."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".pdf_tmp_", suffix=".pdf", dir=str(dest.parent))
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(pdf_bytes)
        os.replace(tmp_name, dest)
    except Exception:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise
