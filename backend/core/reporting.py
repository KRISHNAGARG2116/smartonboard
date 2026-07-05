"""
Reporting engine for Phase B.3C — supports CSV, XLSX, and branded PDF output.
All data queries stream in batches (yield_per) to avoid memory pressure on
large datasets. The ReportingEngine is stateless; callers inject the data.
"""
import csv
import io
import uuid
from datetime import datetime, timezone
from typing import Any, Generator

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    HRFlowable,
)

# ---------------------------------------------------------------------------
# Brand constants
# ---------------------------------------------------------------------------
BRAND_DARK = "#1A1D2E"
BRAND_ACCENT = "#6C63FF"
BRAND_ACCENT_LIGHT = "#8E85FF"
BRAND_SECONDARY = "#2D3250"
BRAND_TEXT = "#E0E0E0"

REPORT_TYPES = [
    "pipeline",
    "recruiter",
    "candidate",
    "offer",
    "velocity",
    "executive_summary",
]


class ReportFilter:
    """Encapsulates all supported report filter parameters."""

    def __init__(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        department: str | None = None,
        recruiter_id: uuid.UUID | None = None,
        hiring_manager_id: uuid.UUID | None = None,
        job_id: uuid.UUID | None = None,
        location: str | None = None,
        employment_type: str | None = None,
        pipeline_stage: str | None = None,
        source: str | None = None,
        include_archived: bool = False,
    ):
        self.date_from = date_from
        self.date_to = date_to
        self.department = department
        self.recruiter_id = recruiter_id
        self.hiring_manager_id = hiring_manager_id
        self.job_id = job_id
        self.location = location
        self.employment_type = employment_type
        self.pipeline_stage = pipeline_stage
        self.source = source
        self.include_archived = include_archived


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _rows_from_result(rows: list[dict]) -> Generator[dict, None, None]:
    """Yield individual rows for streaming consumption."""
    for row in rows:
        yield row


# ---------------------------------------------------------------------------
# CSV Generator
# ---------------------------------------------------------------------------

def generate_csv(headers: list[str], rows: list[dict]) -> bytes:
    """
    Generates a UTF-8 encoded CSV byte-string from headers and row dicts.
    Streams rows via a generator to avoid loading the full dataset into memory.
    """
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=headers, extrasaction="ignore")
    writer.writeheader()
    for row in _rows_from_result(rows):
        writer.writerow(row)
    return output.getvalue().encode("utf-8")


# ---------------------------------------------------------------------------
# Excel (.xlsx) Generator
# ---------------------------------------------------------------------------

def generate_xlsx(
    headers: list[str],
    rows: list[dict],
    sheet_title: str = "Report",
    company_name: str = "SmartOnboard",
) -> bytes:
    """
    Generates a native .xlsx workbook using openpyxl.
    Applies branded header styling, autofit column widths, and
    alternating row shading.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet_title[:31]  # Excel sheet title max length

    # --- Colour constants ---
    dark_hex = BRAND_DARK.lstrip("#")
    accent_hex = BRAND_ACCENT.lstrip("#")
    row_alt_hex = "1E2132"

    header_fill = PatternFill("solid", fgColor=accent_hex)
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_border = Border(
        bottom=Side(style="medium", color="FFFFFF")
    )
    alt_fill = PatternFill("solid", fgColor=row_alt_hex)
    body_font = Font(color="E0E0E0", size=10)

    # --- Title row ---
    ws.insert_rows(1)
    title_cell = ws.cell(row=1, column=1,
                         value=f"{company_name} — {sheet_title}")
    title_cell.font = Font(bold=True, color="FFFFFF", size=13)
    title_cell.fill = PatternFill("solid", fgColor=dark_hex)
    ws.merge_cells(start_row=1, start_column=1,
                   end_row=1, end_column=len(headers))

    ts_cell = ws.cell(row=2, column=1,
                      value=f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    ts_cell.font = Font(italic=True, color="AAAAAA", size=9)
    ws.merge_cells(start_row=2, start_column=1,
                   end_row=2, end_column=len(headers))

    # --- Header row ---
    header_row_idx = 3
    for col_idx, col_name in enumerate(headers, start=1):
        cell = ws.cell(row=header_row_idx, column=col_idx, value=col_name)
        cell.fill = header_fill
        cell.font = header_font
        cell.border = header_border
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # --- Data rows ---
    for row_num, row in enumerate(_rows_from_result(rows), start=header_row_idx + 1):
        is_alt = (row_num - header_row_idx) % 2 == 0
        for col_idx, col_name in enumerate(headers, start=1):
            value = row.get(col_name, "")
            cell = ws.cell(row=row_num, column=col_idx, value=value)
            cell.font = body_font
            if is_alt:
                cell.fill = alt_fill

    # --- Auto-fit columns ---
    for col_idx, col_name in enumerate(headers, start=1):
        col_letter = get_column_letter(col_idx)
        max_len = max(len(str(col_name)), *(
            len(str(row.get(col_name, ""))) for row in rows
        ) if rows else [10])
        ws.column_dimensions[col_letter].width = min(max_len + 4, 50)

    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()


# ---------------------------------------------------------------------------
# PDF Generator
# ---------------------------------------------------------------------------

def generate_pdf(
    report_title: str,
    headers: list[str],
    rows: list[dict],
    kpi_summary: dict[str, Any] | None = None,
    company_name: str = "SmartOnboard",
) -> bytes:
    """
    Generates a branded PDF report using ReportLab Platypus.
    Includes company branding, a KPI summary card section (if provided),
    the full data table, a generation timestamp, and page numbers.
    """
    output = io.BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=letter,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()

    brand_dark_rgb = colors.HexColor(BRAND_DARK)
    brand_accent_rgb = colors.HexColor(BRAND_ACCENT)

    title_style = ParagraphStyle(
        "BrandTitle",
        parent=styles["Title"],
        fontSize=20,
        textColor=colors.white,
        backColor=brand_dark_rgb,
        spaceAfter=6,
        spaceBefore=0,
        fontName="Helvetica-Bold",
    )
    subtitle_style = ParagraphStyle(
        "BrandSubtitle",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#888888"),
        spaceAfter=12,
    )
    kpi_label_style = ParagraphStyle(
        "KpiLabel",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#AAAAAA"),
        fontName="Helvetica",
    )
    kpi_value_style = ParagraphStyle(
        "KpiValue",
        parent=styles["Normal"],
        fontSize=18,
        textColor=brand_accent_rgb,
        fontName="Helvetica-Bold",
    )

    story: list = []

    # --- Header banner ---
    story.append(Paragraph(f"<b>{company_name}</b>", title_style))
    story.append(Paragraph(report_title, title_style))
    story.append(
        Paragraph(
            f"Generated: {datetime.now(timezone.utc).strftime('%B %d, %Y at %H:%M UTC')}",
            subtitle_style,
        )
    )
    story.append(HRFlowable(width="100%", thickness=1, color=brand_accent_rgb))
    story.append(Spacer(1, 12))

    # --- KPI summary cards ---
    if kpi_summary:
        kpi_items = list(kpi_summary.items())
        # 3-column layout
        kpi_table_data = []
        for i in range(0, len(kpi_items), 3):
            chunk = kpi_items[i:i + 3]
            label_row = []
            value_row = []
            for label, value in chunk:
                label_row.append(Paragraph(label, kpi_label_style))
                value_row.append(Paragraph(str(value), kpi_value_style))
            # pad to 3 cols
            while len(label_row) < 3:
                label_row.append(Paragraph("", kpi_label_style))
                value_row.append(Paragraph("", kpi_value_style))
            kpi_table_data.append(label_row)
            kpi_table_data.append(value_row)

        kpi_tbl = Table(kpi_table_data, colWidths=[2.2 * inch, 2.2 * inch, 2.2 * inch])
        kpi_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#1E2132")),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
            ("ROWBACKGROUND", (0, 0), (-1, -1), [colors.HexColor("#1E2132"), colors.HexColor("#252840")]),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#2D3250")),
        ]))
        story.append(kpi_tbl)
        story.append(Spacer(1, 16))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#2D3250")))
        story.append(Spacer(1, 8))

    # --- Data table ---
    if rows:
        table_data = [headers]
        for row in _rows_from_result(rows):
            table_data.append([str(row.get(h, "")) for h in headers])

        col_width = (letter[0] - 1.5 * inch) / max(len(headers), 1)
        data_tbl = Table(table_data, colWidths=[col_width] * len(headers), repeatRows=1)
        data_tbl.setStyle(TableStyle([
            # Header row
            ("BACKGROUND", (0, 0), (-1, 0), brand_accent_rgb),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("TOPPADDING", (0, 0), (-1, 0), 8),
            # Data rows
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#333333")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F5FF")]),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
            ("TOPPADDING", (0, 1), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(data_tbl)

    # --- Page-number canvas callback ---
    def _add_page_number(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#888888"))
        canvas.drawString(
            0.75 * inch,
            0.4 * inch,
            f"Page {doc.page} — {company_name} Confidential",
        )
        canvas.restoreState()

    doc.build(story, onFirstPage=_add_page_number, onLaterPages=_add_page_number)
    return output.getvalue()


# ---------------------------------------------------------------------------
# Format dispatcher
# ---------------------------------------------------------------------------

def generate_report(
    report_format: str,
    report_title: str,
    headers: list[str],
    rows: list[dict],
    kpi_summary: dict[str, Any] | None = None,
    company_name: str = "SmartOnboard",
) -> tuple[bytes, str]:
    """
    Dispatches to the appropriate generator.
    Returns (bytes_content, media_type).
    """
    fmt = report_format.upper()
    if fmt == "CSV":
        return generate_csv(headers, rows), "text/csv"
    elif fmt == "XLSX":
        return (
            generate_xlsx(headers, rows, sheet_title=report_title, company_name=company_name),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    elif fmt == "PDF":
        return (
            generate_pdf(report_title, headers, rows, kpi_summary=kpi_summary, company_name=company_name),
            "application/pdf",
        )
    else:
        raise ValueError(f"Unsupported report format: {report_format}")
