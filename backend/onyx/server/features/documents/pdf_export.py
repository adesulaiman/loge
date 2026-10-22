"""Render Markdown to PDF with reportlab, from the same mistune AST as the DOCX export."""

from io import BytesIO
from typing import Any
from xml.sax.saxutils import escape

import mistune
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    ListFlowable,
    ListItem,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.flowables import Flowable

Node = dict[str, Any]

_parser = mistune.create_markdown(
    renderer=None, plugins=["table", "strikethrough", "url"]
)
_styles = getSampleStyleSheet()
_CODE_STYLE = ParagraphStyle(
    "DocCode",
    parent=_styles["Code"],
    fontSize=8,
    leading=10,
    backColor=colors.whitesmoke,
    borderPadding=4,
)
_QUOTE_STYLE = ParagraphStyle(
    "DocQuote", parent=_styles["BodyText"], leftIndent=14, textColor=colors.grey
)


def _inline(nodes: list[Node]) -> str:
    out: list[str] = []
    for node in nodes:
        kind = node.get("type")
        children = node.get("children", [])
        if kind == "text":
            out.append(escape(str(node.get("raw", ""))))
        elif kind == "strong":
            out.append(f"<b>{_inline(children)}</b>")
        elif kind == "emphasis":
            out.append(f"<i>{_inline(children)}</i>")
        elif kind == "strikethrough":
            out.append(f"<strike>{_inline(children)}</strike>")
        elif kind == "codespan":
            out.append(
                f"<font face='Courier'>{escape(str(node.get('raw', '')))}</font>"
            )
        elif kind == "link":
            url = escape(str(node.get("attrs", {}).get("url", "")), {'"': "&quot;"})
            out.append(f'<a href="{url}" color="blue">{_inline(children)}</a>')
        elif kind in ("linebreak", "softbreak"):
            out.append("<br/>")
        elif kind == "image":
            out.append(escape(_plain(children)))
        else:
            out.append(
                _inline(children) if children else escape(str(node.get("raw", "")))
            )
    return "".join(out)


def _plain(nodes: list[Node]) -> str:
    return "".join(str(n.get("raw", "")) + _plain(n.get("children", [])) for n in nodes)


def _blocks(nodes: list[Node]) -> list[Flowable]:
    flow: list[Flowable] = []
    for node in nodes:
        kind = node.get("type")
        children = node.get("children", [])
        if kind == "heading":
            level = min(int(node.get("attrs", {}).get("level", 1)), 4)
            flow.append(Paragraph(_inline(children), _styles[f"Heading{level}"]))
        elif kind in ("paragraph", "block_text"):
            flow.append(Paragraph(_inline(children), _styles["BodyText"]))
        elif kind == "block_code":
            flow.append(
                Preformatted(str(node.get("raw", "")).rstrip("\n"), _CODE_STYLE)
            )
            flow.append(Spacer(1, 6))
        elif kind == "list":
            ordered = bool(node.get("attrs", {}).get("ordered"))
            items = [ListItem(_blocks(c.get("children", []))) for c in children]
            flow.append(
                ListFlowable(
                    items, bulletType="1" if ordered else "bullet", leftIndent=14
                )
            )
        elif kind == "block_quote":
            for inner in _blocks(children):
                if isinstance(inner, Paragraph):
                    flow.append(Paragraph(inner.text, _QUOTE_STYLE))
                else:
                    flow.append(inner)
        elif kind == "thematic_break":
            flow.append(HRFlowable(width="100%"))
        elif kind == "table":
            flow.append(_table(children))
            flow.append(Spacer(1, 6))
        elif children:
            flow.extend(_blocks(children))
    return flow


def _table(sections: list[Node]) -> Table:
    rows: list[list[Paragraph]] = []
    header_rows = 0
    for section in sections:
        if section.get("type") == "table_head":
            cells = section.get("children", [])
            rows.append(
                [
                    Paragraph(
                        f"<b>{_inline(c.get('children', []))}</b>", _styles["BodyText"]
                    )
                    for c in cells
                ]
            )
            header_rows = 1
        elif section.get("type") == "table_body":
            rows.extend(
                [
                    Paragraph(_inline(c.get("children", [])), _styles["BodyText"])
                    for c in row.get("children", [])
                ]
                for row in section.get("children", [])
            )
    table = Table(rows, repeatRows=header_rows)
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 0), (-1, header_rows - 1), colors.lightgrey)
                if header_rows
                else ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


def markdown_to_pdf_bytes(title: str, md_text: str) -> bytes:
    tokens = _parser(md_text)
    nodes: list[Node] = tokens if isinstance(tokens, list) else []
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        title=title,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    doc.build(_blocks(nodes) or [Paragraph(escape(title), _styles["Heading1"])])
    return buffer.getvalue()
