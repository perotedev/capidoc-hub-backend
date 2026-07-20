"""Renders a generic (title, headers, rows) table into CSV/XLSX/PDF bytes.

Used by the Reports module to actually produce the file behind a report
request — CSV via the stdlib, XLSX via openpyxl, PDF via PyMuPDF (already a
dependency for `pdf_renderer.py`). All free/open-source, no paid services.
"""

import csv
import io

import fitz
from openpyxl import Workbook
from openpyxl.styles import Font

from app.modules.reports.domain.entities import ReportFormat

_PAGE_WIDTH, _PAGE_HEIGHT = fitz.paper_size("a4")
_MARGIN = 36.0
_ROW_HEIGHT = 16.0
_FONT_SIZE = 8
_TITLE_FONT_SIZE = 14


def render_csv(headers: list[str], rows: list[list[str]]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    writer.writerows(rows)
    # UTF-8 BOM so Excel opens accented characters correctly.
    return ("﻿" + buffer.getvalue()).encode("utf-8")


def render_xlsx(title: str, headers: list[str], rows: list[list[str]]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = (title or "Relatório")[:31]
    sheet.append(headers)
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    for row in rows:
        sheet.append(row)
    for column_cells in sheet.columns:
        length = max((len(str(cell.value)) for cell in column_cells if cell.value is not None), default=10)
        sheet.column_dimensions[column_cells[0].column_letter].width = min(max(length + 2, 10), 40)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _truncate(value: object, max_chars: int) -> str:
    text = str(value)
    return text if len(text) <= max_chars else text[: max_chars - 1] + "…"


def render_pdf(title: str, headers: list[str], rows: list[list[str]]) -> bytes:
    doc = fitz.open()
    usable_width = _PAGE_WIDTH - 2 * _MARGIN
    col_count = max(len(headers), 1)
    col_width = usable_width / col_count
    max_chars = max(int(col_width / 4.5), 4)

    state: dict = {"page": None}

    def new_page() -> float:
        page = doc.new_page(width=_PAGE_WIDTH, height=_PAGE_HEIGHT)
        state["page"] = page
        page.insert_text(fitz.Point(_MARGIN, _MARGIN), title, fontsize=_TITLE_FONT_SIZE, fontname="hebo")
        header_y = _MARGIN + 24
        for index, header in enumerate(headers):
            page.insert_text(
                fitz.Point(_MARGIN + index * col_width, header_y),
                _truncate(header, max_chars),
                fontsize=_FONT_SIZE,
                fontname="hebo",
            )
        return header_y + _ROW_HEIGHT

    y = new_page()
    if not rows:
        state["page"].insert_text(
            fitz.Point(_MARGIN, y), "Nenhum dado encontrado para os filtros selecionados.", fontsize=_FONT_SIZE, fontname="helv"
        )
    for row in rows:
        if y > _PAGE_HEIGHT - _MARGIN:
            y = new_page()
        for index, value in enumerate(row):
            state["page"].insert_text(
                fitz.Point(_MARGIN + index * col_width, y),
                _truncate(value, max_chars),
                fontsize=_FONT_SIZE,
                fontname="helv",
            )
        y += _ROW_HEIGHT

    result = doc.tobytes(garbage=3, deflate=True)
    doc.close()
    return result


def render_report_file(format_: ReportFormat, title: str, headers: list[str], rows: list[list[str]]) -> bytes:
    if format_ == ReportFormat.CSV:
        return render_csv(headers, rows)
    if format_ == ReportFormat.EXCEL:
        return render_xlsx(title, headers, rows)
    return render_pdf(title, headers, rows)
