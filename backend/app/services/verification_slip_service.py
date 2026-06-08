import logging
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.core.course_codes import course_label

logger = logging.getLogger(__name__)

_NAVY = colors.HexColor("#1B334E")
_LIGHT_GREY = colors.HexColor("#F0EFEB")
_MID_GREY = colors.HexColor("#9CA3AF")


def generate(record, analysis_id: str, out_dir: Path) -> Path:
    """Generate the verification slip PDF. Returns the output path."""
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "verification-slip.pdf"

    extracted = record.response.extracted
    confirmed_at_str = (
        record.confirmed_at.strftime("%d %b %Y, %H:%M UTC")
        if record.confirmed_at
        else "—"
    )

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()

    style_header_title = ParagraphStyle(
        "HeaderTitle",
        fontName="Helvetica-Bold",
        fontSize=15,
        textColor=colors.white,
        alignment=TA_LEFT,
        leading=18,
    )
    style_header_sub = ParagraphStyle(
        "HeaderSub",
        fontName="Helvetica",
        fontSize=9,
        textColor=colors.HexColor("#BAD4E8"),
        alignment=TA_LEFT,
        leading=13,
    )
    style_section = ParagraphStyle(
        "Section",
        fontName="Helvetica-Bold",
        fontSize=8,
        textColor=_NAVY,
        spaceBefore=14,
        spaceAfter=4,
        letterSpacing=1.2,
    )
    style_label = ParagraphStyle(
        "Label",
        fontName="Helvetica",
        fontSize=8,
        textColor=_MID_GREY,
        leading=11,
    )
    style_value = ParagraphStyle(
        "Value",
        fontName="Helvetica-Bold",
        fontSize=9,
        textColor=_NAVY,
        leading=12,
    )
    style_caption = ParagraphStyle(
        "Caption",
        fontName="Helvetica",
        fontSize=8,
        textColor=_MID_GREY,
        alignment=TA_CENTER,
        spaceBefore=3,
    )
    style_footer = ParagraphStyle(
        "Footer",
        fontName="Helvetica-Oblique",
        fontSize=7,
        textColor=_MID_GREY,
        leading=10,
        alignment=TA_CENTER,
    )
    style_fallback = ParagraphStyle(
        "Fallback",
        fontName="Helvetica-Oblique",
        fontSize=8,
        textColor=_MID_GREY,
        alignment=TA_CENTER,
        leading=11,
    )

    story = []

    # ── Header bar ────────────────────────────────────────────────────────────
    header_data = [[
        Paragraph("ORDER VERIFICATION SLIP", style_header_title),
        Paragraph("SIBC Copy Print · Bandar Seri Iskandar", style_header_sub),
    ]]
    header_table = Table(header_data, colWidths=["55%", "45%"])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), _NAVY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (0, 0), 12),
        ("RIGHTPADDING", (-1, 0), (-1, 0), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.4 * cm))

    # ── Confirmed Details ─────────────────────────────────────────────────────
    story.append(Paragraph("CONFIRMED DETAILS", style_section))

    course_name = course_label(extracted.course_code)

    fields = [
        ("Student Name", extracted.full_name),
        ("Thesis Title", extracted.thesis_title),
        ("Course", course_name),
        ("Graduation Month / Year", extracted.year),
        ("Student ID", extracted.student_id),
        ("Confirmed At", confirmed_at_str),
        ("Analysis ID", analysis_id),
    ]

    detail_rows = []
    for label, value in fields:
        detail_rows.append([
            Paragraph(label, style_label),
            Paragraph(value or "—", style_value),
        ])

    detail_table = Table(detail_rows, colWidths=["30%", "70%"])
    detail_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), _LIGHT_GREY),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, _LIGHT_GREY]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, -2), 0.3, colors.HexColor("#E5E3DF")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1CFCA")),
    ]))
    story.append(detail_table)

    # ── Approved Templates ────────────────────────────────────────────────────
    story.append(Paragraph("APPROVED TEMPLATES", style_section))

    thumb_cells = []
    thumb_widths = []

    has_cd = record.cd_pdf_path is not None

    cover_thumb = _pdf_thumbnail(record.cover_pdf_path, out_dir, "thumb_cover.png")
    cd_thumb = _pdf_thumbnail(record.cd_pdf_path, out_dir, "thumb_cd.png") if has_cd else None

    page_width = A4[0] - 4 * cm  # usable width
    if has_cd:
        thumb_w = (page_width - 0.5 * cm) / 2
    else:
        thumb_w = page_width * 0.55  # centred-ish for a single thumb

    def _thumb_cell(img_path: Optional[Path], caption: str, width: float):
        if img_path and img_path.exists():
            img = Image(str(img_path), width=width, height=width * 1.414)  # A4 ratio
            img.hAlign = "CENTER"
            return [img, Paragraph(caption, style_caption)]
        return [
            Paragraph(
                "Template preview not available.<br/>Refer to DOCX with Analysis ID above.",
                style_fallback,
            ),
            Paragraph(caption, style_caption),
        ]

    cover_cell = _thumb_cell(cover_thumb, "Hardbound Cover", thumb_w)
    thumb_cells.append(cover_cell)
    thumb_widths.append(thumb_w)

    if has_cd:
        cd_cell = _thumb_cell(cd_thumb, "CD Case", thumb_w)
        thumb_cells.append(cd_cell)
        thumb_widths.append(thumb_w)

    # Each cell is [image_or_text, caption] — build a 2-row table per column, then wrap in outer table
    inner_tables = []
    for cell in thumb_cells:
        inner = Table([[cell[0]], [cell[1]]])
        inner.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOX", (0, 0), (-1, 0), 0.5, colors.HexColor("#D1CFCA")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        inner_tables.append(inner)

    outer_row = [inner_tables] if len(inner_tables) == 1 else [inner_tables[0], inner_tables[1]]
    outer_table = Table([outer_row], colWidths=thumb_widths if has_cd else [thumb_w])
    outer_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0 if not has_cd else 8),
    ]))
    story.append(outer_table)

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(
        f"This slip confirms that the student reviewed and approved the above details on "
        f"{confirmed_at_str}. SIBC Copy Print is not liable for misprints arising from "
        "information confirmed here.",
        style_footer,
    ))

    doc.build(story)
    return out_path


def _pdf_thumbnail(pdf_path: Optional[Path], out_dir: Path, name: str) -> Optional[Path]:
    """Render first page of a PDF to a PNG thumbnail. Returns None on failure."""
    if pdf_path is None or not pdf_path.exists():
        return None
    try:
        doc = fitz.open(str(pdf_path))
        page = doc[0]
        mat = fitz.Matrix(1.4, 1.4)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        out = out_dir / name
        pix.save(str(out))
        doc.close()
        return out
    except Exception as exc:
        logger.warning("Thumbnail generation failed for %s: %s", pdf_path, exc)
        return None
