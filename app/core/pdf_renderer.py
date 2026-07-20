"""Overlays attendance field values onto a form's template PDF using PyMuPDF.

Ported line-for-line from the capidoc-tauri desktop app's
`core/text_box_renderer.py` + `core/pdf_generator.py` so that a `TemplateBox`
list renders identically on both platforms — this is the same engine, not a
reimplementation, ahead of the two apps' planned integration.
"""

import fitz

from app.modules.forms.domain.entities import TemplateBox, TemplateConditionalRule

_MM_TO_POINTS = 2.83465
_POINTS_TO_MM = 0.352778
_MIN_SHRINK_FONT_SIZE = 6


def _hex_to_rgb(hex_color: str) -> tuple[float, float, float]:
    hex_color = (hex_color or "").lstrip("#")
    if len(hex_color) != 6:
        return (0, 0, 0)
    try:
        r, g, b = (int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
        return (r / 255, g / 255, b / 255)
    except ValueError:
        return (0, 0, 0)


def _fitz_font(font_family: str, bold: bool, italic: bool) -> str:
    if font_family in ("Helvetica", "Arial", "Georgia", "Verdana"):
        if bold and italic:
            return "hebi"
        if bold:
            return "hebo"
        if italic:
            return "heit"
        return "helv"
    if font_family in ("Times New Roman", "Times-Roman", "Times"):
        if bold and italic:
            return "tibi"
        if bold:
            return "tibo"
        if italic:
            return "tiit"
        return "tirom"
    if font_family in ("Courier", "Courier New"):
        if bold and italic:
            return "cobi"
        if bold:
            return "cobo"
        if italic:
            return "coit"
        return "cour"
    return "helv"


def apply_conditional_rules(value: str, rules: list[TemplateConditionalRule]) -> str:
    """A box with rules only ever shows a rule's configured text — never the raw
    value — matching the Tauri app's `apply_conditional_rules` semantics."""
    if not rules:
        return value
    value_lower = (value or "").strip().lower()
    for rule in rules:
        rule_value = (rule.value or "").strip().lower()
        if rule.operator == "not_empty" and value_lower:
            return rule.text
        if rule.operator == "equals" and value_lower == rule_value:
            return rule.text
        if rule.operator == "contains" and rule_value in value_lower:
            return rule.text
    return ""


def _wrap_text(text: str, font_name: str, font_size: float, max_width: float) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        if not paragraph.strip():
            lines.append("")
            continue
        current_line = ""
        for word in paragraph.split():
            test_line = f"{current_line} {word}".strip() if current_line else word
            if fitz.get_text_length(test_line, fontname=font_name, fontsize=font_size) <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
    return lines or [""]


def _handle_overflow(
    lines: list[str],
    font_name: str,
    font_size: float,
    max_width: float,
    max_height: float,
    behavior: str,
    word_wrap: bool,
    line_spacing: float,
    original_text: str,
) -> tuple[list[str], float]:
    line_height = font_size * line_spacing
    if len(lines) * line_height <= max_height:
        return lines, font_size

    if behavior == "overflow":
        return lines, font_size

    if behavior == "truncate":
        max_lines = max(1, int(max_height / line_height))
        return lines[:max_lines], font_size

    if behavior == "ellipsis":
        max_lines = max(1, int(max_height / line_height))
        truncated = lines[:max_lines]
        if len(lines) > max_lines and truncated:
            last_line = truncated[-1]
            while last_line:
                candidate = last_line + "..."
                if fitz.get_text_length(candidate, fontname=font_name, fontsize=font_size) <= max_width:
                    truncated[-1] = candidate
                    break
                last_line = last_line[:-1]
            if not last_line:
                truncated[-1] = "..."
        return truncated, font_size

    if behavior == "shrink_to_fit":
        current_size = font_size
        while current_size >= _MIN_SHRINK_FONT_SIZE:
            test_lines = _wrap_text(original_text, font_name, current_size, max_width) if word_wrap else [original_text]
            if len(test_lines) * (current_size * line_spacing) <= max_height:
                return test_lines, current_size
            current_size -= 0.5
        final_lines = _wrap_text(original_text, font_name, _MIN_SHRINK_FONT_SIZE, max_width) if word_wrap else [original_text]
        max_lines = max(1, int(max_height / (_MIN_SHRINK_FONT_SIZE * line_spacing)))
        return final_lines[:max_lines], _MIN_SHRINK_FONT_SIZE

    return lines, font_size


def _render_box(page: "fitz.Page", box: TemplateBox, value: str) -> None:
    if not value.strip():
        return
    if box.text_options.uppercase:
        value = value.upper()

    bounds = box.bounds
    padding = box.text_options.padding
    x_pt = bounds.x * _MM_TO_POINTS
    y_pt = bounds.y * _MM_TO_POINTS
    inner_x = x_pt + padding.left * _MM_TO_POINTS
    inner_y = y_pt + padding.top * _MM_TO_POINTS
    inner_width = bounds.width * _MM_TO_POINTS - (padding.left + padding.right) * _MM_TO_POINTS
    inner_height = bounds.height * _MM_TO_POINTS - (padding.top + padding.bottom) * _MM_TO_POINTS
    if inner_width <= 0 or inner_height <= 0:
        return

    style = box.style
    font_name = _fitz_font(style.font_family, style.bold, style.italic)
    font_size = style.font_size
    color = _hex_to_rgb(style.color)
    line_spacing = box.text_options.line_spacing

    lines = _wrap_text(value, font_name, font_size, inner_width) if box.text_options.word_wrap else [value]
    lines, font_size = _handle_overflow(
        lines, font_name, font_size, inner_width, inner_height,
        box.text_options.overflow_behavior, box.text_options.word_wrap, line_spacing, value,
    )

    line_height = font_size * line_spacing
    total_height = len(lines) * line_height
    vertical = box.alignment.vertical
    if vertical == "top":
        start_y = inner_y + font_size
    elif vertical == "bottom":
        start_y = inner_y + inner_height - total_height + font_size
    else:
        start_y = inner_y + (inner_height - total_height) / 2 + font_size

    for index, line in enumerate(lines):
        if not line.strip():
            continue
        line_y = start_y + index * line_height
        text_width = fitz.get_text_length(line, fontname=font_name, fontsize=font_size)
        horizontal = box.alignment.horizontal
        if horizontal == "center":
            line_x = inner_x + (inner_width - text_width) / 2
        elif horizontal == "right":
            line_x = inner_x + inner_width - text_width
        else:
            line_x = inner_x

        page.insert_text(fitz.Point(line_x, line_y), line, fontsize=font_size, fontname=font_name, color=color)
        if style.underline:
            underline_y = line_y + 2
            page.draw_line(fitz.Point(line_x, underline_y), fitz.Point(line_x + text_width, underline_y), color=color, width=0.5)


def render_document_pdf(
    base_pdf_bytes: bytes,
    template_boxes: list[TemplateBox],
    field_values: dict[str, str],
    header_logo_bytes: bytes | None = None,
    footer_text: str = "",
    validation_code: str | None = None,
) -> bytes:
    doc = fitz.open(stream=base_pdf_bytes, filetype="pdf")

    boxes_by_page: dict[int, list[TemplateBox]] = {}
    for box in template_boxes:
        boxes_by_page.setdefault(box.page_index, []).append(box)

    for page_index in range(len(doc)):
        page = doc[page_index]
        for box in boxes_by_page.get(page_index, []):
            raw_value = field_values.get(box.field_id, "")
            value = apply_conditional_rules(raw_value, box.conditional_rules)
            if value:
                _render_box(page, box, value)

        page_height_mm = page.rect.height * _POINTS_TO_MM
        if page_index == 0 and header_logo_bytes:
            page.insert_image(fitz.Rect(10 * _MM_TO_POINTS, 10 * _MM_TO_POINTS, 50 * _MM_TO_POINTS, 25 * _MM_TO_POINTS), stream=header_logo_bytes)
        if footer_text:
            footer_y = (page_height_mm - 10) * _MM_TO_POINTS
            page.insert_text(fitz.Point(10 * _MM_TO_POINTS, footer_y), footer_text, fontsize=8, fontname="helv", color=(0.4, 0.4, 0.4))
        if validation_code:
            code_y = (page_height_mm - 5) * _MM_TO_POINTS
            code_text = f"Código de validação: {validation_code}"
            text_width = fitz.get_text_length(code_text, fontname="helv", fontsize=7)
            page.insert_text(
                fitz.Point(page.rect.width - text_width - 10 * _MM_TO_POINTS, code_y),
                code_text, fontsize=7, fontname="helv", color=(0.4, 0.4, 0.4),
            )

    result = doc.tobytes(garbage=3, deflate=True)
    doc.close()
    return result
