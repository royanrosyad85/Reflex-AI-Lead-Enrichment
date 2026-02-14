from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.pdfgen import canvas as pdf_canvas


def safe_value(value: Any) -> str:
    if value is None:
        return "-"
    value = str(value).strip()
    return value if value else "-"


def _get_styles():
    base_color = HexColor("#111827")
    muted_color = HexColor("#6B7280")

    return {
        "title": ParagraphStyle(
            "Title",
            fontName="Helvetica-Bold",
            fontSize=16,
            textColor=base_color,
            spaceAfter=8,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            fontName="Helvetica",
            fontSize=9,
            textColor=muted_color,
            spaceAfter=12,
        ),
        "metadata": ParagraphStyle(
            "Metadata",
            fontName="Helvetica",
            fontSize=9,
            textColor=muted_color,
            spaceAfter=16,
        ),
        "company_title": ParagraphStyle(
            "CompanyTitle",
            fontName="Helvetica-Bold",
            fontSize=12,
            textColor=base_color,
            spaceBefore=12,
            spaceAfter=6,
        ),
        "label": ParagraphStyle(
            "Label",
            fontName="Helvetica-Bold",
            fontSize=9,
            textColor=muted_color,
            spaceAfter=2,
        ),
        "value": ParagraphStyle(
            "Value",
            fontName="Helvetica",
            fontSize=10,
            textColor=base_color,
            spaceAfter=6,
        ),
        "long_text": ParagraphStyle(
            "LongText",
            fontName="Helvetica",
            fontSize=10,
            textColor=base_color,
            spaceAfter=10,
        ),
    }


def _resolve_logo_path() -> str | None:
    project_root = Path(__file__).resolve().parent.parent
    logo_path = project_root / "assets" / "zurich-logo-update.png"
    if logo_path.exists():
        return str(logo_path)
    return None


def _draw_first_page_header(
    canvas: pdf_canvas.Canvas,
    export_datetime: datetime,
    logo_path: str | None,
):
    canvas.saveState()

    width, height = A4
    left_margin = 2 * cm
    right_margin = width - 2 * cm

    title_y = height - 1.7 * cm
    subtitle_y = height - 2.3 * cm
    divider_y = height - 2.8 * cm

    if logo_path:
        try:
            canvas.drawImage(
                logo_path,
                right_margin - (2.8 * cm),
                height - 2.25 * cm,
                width=2.8 * cm,
                height=1.1 * cm,
                preserveAspectRatio=True,
                mask="auto",
                anchor="ne",
            )
        except Exception:
            pass

    canvas.setFont("Helvetica-Bold", 14)
    canvas.drawString(left_margin, title_y, "Company Enrichment Export")

    canvas.setFont("Helvetica", 9)
    canvas.drawString(
        left_margin,
        subtitle_y,
        f"Exported on: {export_datetime.strftime('%d %B %Y, %H:%M WIB')}",
    )

    canvas.setLineWidth(0.5)
    canvas.line(left_margin, divider_y, right_margin, divider_y)

    canvas.restoreState()


def _draw_later_pages(canvas: pdf_canvas.Canvas, _doc):
    return


def _build_company_section(company: dict, index: int, styles: dict) -> list:
    elements = []

    elements.append(
        Paragraph(f"{index}. {safe_value(company.get('Nama Perusahaan'))}", styles["company_title"])
    )

    def field(label: str, key: str):
        elements.append(Paragraph(label, styles["label"]))
        elements.append(Paragraph(safe_value(company.get(key)), styles["value"]))

    field("Sector", "Sektor Perusahaan")
    field("Address", "Alamat")
    field("Contact", "Kontak")
    field("Insurance", "Potensi Polis")
    field("Employees", "Jumlah Karyawan")

    elements.append(Paragraph("Short Description", styles["label"]))
    elements.append(Paragraph(safe_value(company.get("Short Description")), styles["long_text"]))

    elements.append(Paragraph("Kantor Cabang", styles["label"]))
    elements.append(Paragraph(safe_value(company.get("Kantor Cabang")), styles["long_text"]))

    elements.append(Paragraph("PIC Perusahaan", styles["label"]))
    elements.append(Paragraph(safe_value(company.get("PIC Perusahaan")), styles["long_text"]))

    elements.append(Paragraph("Laporan Keuangan", styles["label"]))
    elements.append(Paragraph(safe_value(company.get("Laporan Keuangan")), styles["long_text"]))

    elements.append(Spacer(1, 6))
    elements.append(HRFlowable(width="100%", thickness=0.5, spaceBefore=6, spaceAfter=6))

    return elements


def generate_company_enrichment_pdf(companies: list[dict], export_datetime: datetime) -> bytes:
    buffer = BytesIO()
    styles = _get_styles()
    logo_path = _resolve_logo_path()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=3.5 * cm,
        bottomMargin=2.5 * cm,
    )

    story = []

    story.append(
        Paragraph(f"Total companies: {len(companies)}", styles["metadata"])
    )

    if not companies:
        story.append(Paragraph("No company data available.", styles["value"]))
    else:
        for idx, company in enumerate(companies, start=1):
            story.extend(_build_company_section(company, idx, styles))

    doc.build(
        story,
        onFirstPage=lambda c, d: _draw_first_page_header(c, export_datetime, logo_path),
        onLaterPages=_draw_later_pages,
    )

    return buffer.getvalue()
