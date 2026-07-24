#!/usr/bin/env python3
"""Build the bench-ready cut-and-assembly shop manual."""
from pathlib import Path
import html
import re
import xml.etree.ElementTree as ET

from pypdf import PdfReader
from reportlab.graphics.shapes import (
    Circle as VectorCircle,
    Drawing,
    Polygon as VectorPolygon,
    PolyLine as VectorPolyLine,
    Rect as VectorRect,
    String as VectorString,
)
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from generate_quick_assembly_diagrams import generate as generate_assembly_diagrams

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "quick-guide/DC-1916-001_Quick_Cut_and_Assembly_Guide.md"
RELEASE = ROOT / "release"
OUT = RELEASE / "DC-1916-001_Quick_Cut_and_Assembly_Guide.pdf"

BLUE = colors.HexColor("#173A56")
TEAL = colors.HexColor("#2E6F73")
OAK = colors.HexColor("#B98A52")
OAK_DARK = colors.HexColor("#8F642F")
INK = colors.HexColor("#20272D")
GRAY = colors.HexColor("#5E686E")
PALE = colors.HexColor("#F4F0E8")
PALE_BLUE = colors.HexColor("#EEF4F7")
PALE_TEAL = colors.HexColor("#EDF5F4")
RULE = colors.HexColor("#B9B3A8")


def page_decor(canvas, doc):
    canvas.saveState()
    canvas.setTitle("DC-1916-001 Quick Cut and Assembly Shop Manual")
    canvas.setAuthor("DC-1916-001 Project Team")
    canvas.setSubject("Bench-ready cutting, joinery, dry-fit, and glue-up instructions")
    canvas.setStrokeColor(OAK)
    canvas.setLineWidth(1.2)
    canvas.line(0.65 * inch, 0.52 * inch, 7.85 * inch, 0.52 * inch)
    canvas.setFont("Helvetica-Bold", 7.1)
    canvas.setFillColor(BLUE)
    canvas.drawString(0.65 * inch, 0.36 * inch, "DC-1916-001  |  SHOP MANUAL  |  REV. A")
    canvas.setFont("Helvetica", 7.1)
    canvas.setFillColor(GRAY)
    canvas.drawRightString(7.85 * inch, 0.36 * inch, f"PAGE {canvas.getPageNumber():02d}")
    canvas.restoreState()


def styles():
    s = getSampleStyleSheet()
    s.add(
        ParagraphStyle(
            name="QTitle",
            parent=s["Title"],
            fontName="Helvetica-Bold",
            fontSize=26,
            leading=29,
            textColor=BLUE,
            alignment=0,
            spaceAfter=8,
        )
    )
    s.add(
        ParagraphStyle(
            name="QCoverDeck",
            parent=s["BodyText"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=14.5,
            textColor=INK,
            spaceAfter=8,
        )
    )
    s.add(
        ParagraphStyle(
            name="QKicker",
            parent=s["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=7.8,
            leading=9,
            tracking=1.05,
            textColor=TEAL,
            spaceAfter=4,
        )
    )
    s.add(
        ParagraphStyle(
            name="QH1",
            parent=s["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=17.5,
            leading=20.5,
            textColor=BLUE,
            spaceBefore=0,
            spaceAfter=5,
        )
    )
    s.add(
        ParagraphStyle(
            name="QH2",
            parent=s["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11.5,
            leading=14,
            textColor=TEAL,
            spaceBefore=6,
            spaceAfter=4,
        )
    )
    s.add(
        ParagraphStyle(
            name="QDeck",
            parent=s["BodyText"],
            fontName="Helvetica",
            fontSize=9.2,
            leading=12.2,
            textColor=GRAY,
            spaceAfter=5,
        )
    )
    s.add(
        ParagraphStyle(
            name="QBody",
            parent=s["BodyText"],
            fontName="Helvetica",
            fontSize=9.2,
            leading=12.1,
            textColor=INK,
            spaceAfter=4,
        )
    )
    s.add(
        ParagraphStyle(
            name="QBullet",
            parent=s["QBody"],
            leftIndent=13,
            firstLineIndent=-7,
            bulletIndent=0,
            spaceAfter=3,
        )
    )
    s.add(
        ParagraphStyle(
            name="QNumber",
            parent=s["QBody"],
            leftIndent=16,
            firstLineIndent=-12,
            spaceAfter=3.5,
        )
    )
    s.add(
        ParagraphStyle(
            name="QTable",
            parent=s["QBody"],
            fontSize=8.35,
            leading=10.2,
            spaceAfter=0,
        )
    )
    s.add(
        ParagraphStyle(
            name="QTableHead",
            parent=s["QTable"],
            fontName="Helvetica-Bold",
            textColor=colors.white,
            leading=10,
        )
    )
    s.add(
        ParagraphStyle(
            name="QCardHead",
            parent=s["QBody"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=9,
            textColor=colors.white,
            spaceAfter=0,
        )
    )
    s.add(
        ParagraphStyle(
            name="QCardBody",
            parent=s["QBody"],
            fontSize=8.1,
            leading=10.2,
            spaceAfter=0,
        )
    )
    s.add(
        ParagraphStyle(
            name="QMicro",
            parent=s["QBody"],
            fontSize=7.3,
            leading=8.8,
            textColor=GRAY,
            spaceAfter=0,
        )
    )
    s.add(
        ParagraphStyle(
            name="QStop",
            parent=s["QBody"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=10.5,
            textColor=colors.HexColor("#8D312B"),
            spaceAfter=0,
        )
    )
    return s


def inline(text):
    text = html.escape(text)
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)


def svg_color(value):
    if not value or value == "none":
        return None
    return colors.toColor(value)


def svg_figure(path, width):
    """Convert the project's simple SVG figures to native ReportLab vectors."""
    root = ET.parse(path).getroot()
    view_box = [float(value) for value in root.attrib["viewBox"].split()]
    source_width, source_height = view_box[2], view_box[3]
    height = width * source_height / source_width
    sx, sy = width / source_width, height / source_height
    stroke_scale = (sx + sy) / 2
    drawing = Drawing(width, height)

    def points(value):
        pairs = re.findall(r"(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)", value)
        flattened = []
        for x_value, y_value in pairs:
            flattened.extend([float(x_value) * sx, height - float(y_value) * sy])
        return flattened

    def walk(element, inherited=None):
        inherited = dict(inherited or {})
        inherited.update(element.attrib)
        tag = element.tag.rsplit("}", 1)[-1]
        if tag == "defs":
            return
        if tag in {"svg", "g"}:
            for child in element:
                walk(child, inherited)
            return

        fill = svg_color(inherited.get("fill"))
        stroke = svg_color(inherited.get("stroke"))
        stroke_width = float(inherited.get("stroke-width", 0)) * stroke_scale

        if tag == "rect":
            x = float(element.attrib.get("x", 0)) * sx
            raw_y = float(element.attrib.get("y", 0))
            rect_width = float(element.attrib["width"]) * sx
            rect_height = float(element.attrib["height"]) * sy
            y = height - (raw_y * sy) - rect_height
            radius = float(element.attrib.get("rx", 0)) * sx
            drawing.add(
                VectorRect(
                    x,
                    y,
                    rect_width,
                    rect_height,
                    rx=radius,
                    ry=radius,
                    fillColor=fill,
                    strokeColor=stroke,
                    strokeWidth=stroke_width,
                )
            )
        elif tag == "circle":
            drawing.add(
                VectorCircle(
                    float(element.attrib["cx"]) * sx,
                    height - float(element.attrib["cy"]) * sy,
                    float(element.attrib["r"]) * sx,
                    fillColor=fill,
                    strokeColor=stroke,
                    strokeWidth=stroke_width,
                )
            )
        elif tag == "polyline":
            drawing.add(
                VectorPolyLine(
                    points(element.attrib["points"]),
                    fillColor=None,
                    strokeColor=stroke,
                    strokeWidth=stroke_width,
                )
            )
        elif tag == "polygon":
            drawing.add(
                VectorPolygon(
                    points(element.attrib["points"]),
                    fillColor=fill,
                    strokeColor=stroke,
                    strokeWidth=stroke_width,
                )
            )
        elif tag == "path":
            raw_points = re.findall(r"[ML]\s*(-?\d+(?:\.\d+)?)\s*,?\s*(-?\d+(?:\.\d+)?)", element.attrib.get("d", ""))
            path_points = []
            for x_value, y_value in raw_points:
                path_points.extend([float(x_value) * sx, height - float(y_value) * sy])
            if len(path_points) >= 6:
                shape = VectorPolygon if re.search(r"[zZ]\s*$", element.attrib.get("d", "")) else VectorPolyLine
                drawing.add(
                    shape(
                        path_points,
                        fillColor=fill if shape is VectorPolygon else None,
                        strokeColor=stroke,
                        strokeWidth=stroke_width,
                    )
                )
        elif tag == "text":
            font_size = float(inherited.get("font-size", 12)) * sy
            weight = inherited.get("font-weight", "400")
            font_name = "Helvetica-Bold" if weight in {"bold", "700"} else "Helvetica"
            anchor = inherited.get("text-anchor", "start")
            x = float(element.attrib.get("x", 0)) * sx
            center_y = height - float(element.attrib.get("y", 0)) * sy
            baseline_y = center_y - font_size * 0.34
            drawing.add(
                VectorString(
                    x,
                    baseline_y,
                    element.text or "",
                    fontName=font_name,
                    fontSize=font_size,
                    fillColor=fill or INK,
                    textAnchor=anchor,
                )
            )

    walk(root)
    return drawing


def source_sections(text):
    sections = {}
    for block in re.split(r"(?=^## )", text, flags=re.M):
        lines = block.splitlines()
        if lines and lines[0].startswith("## "):
            sections[lines[0][3:].strip()] = lines[1:]
    return sections


def table_widths(column_count):
    return {
        5: [0.68 * inch, 1.31 * inch, 0.36 * inch, 2.30 * inch, 2.30 * inch],
        4: [0.78 * inch, 1.58 * inch, 0.42 * inch, 3.96 * inch],
        3: [2.34 * inch, 0.60 * inch, 4.00 * inch],
    }.get(column_count)


def markdown_table(rows, s, widths=None):
    data = []
    for row_index, row in enumerate(rows):
        style = s["QTableHead"] if row_index == 0 else s["QTable"]
        data.append([Paragraph(inline(cell), style) for cell in row])
    table = Table(data, colWidths=widths or table_widths(len(rows[0])), repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), BLUE),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
                ("GRID", (0, 0), (-1, -1), 0.45, RULE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
            ]
        )
    )
    return table


def parse_section(lines, s, include_heading=False):
    out, rows = [], []

    def flush():
        nonlocal rows
        if rows:
            out.extend([markdown_table(rows, s), Spacer(1, 6)])
            rows = []

    for line in lines:
        if line.startswith("|"):
            if "---" not in line:
                rows.append([cell.strip() for cell in line.strip("|").split("|")])
            continue
        flush()
        if line.startswith("## "):
            if include_heading:
                out.append(Paragraph(inline(line[3:]), s["QH1"]))
        elif line.startswith("- "):
            out.append(Paragraph("&#8226; " + inline(line[2:]), s["QBullet"]))
        elif re.match(r"^\d+\. ", line):
            number, body = line.split(". ", 1)
            out.append(Paragraph(f"<b>{number}.</b> {inline(body)}", s["QNumber"]))
        elif line.strip() and not line.startswith("# "):
            out.append(Paragraph(inline(line), s["QBody"]))
    flush()
    return out


def page_heading(story, s, kicker, title, deck):
    story.extend(
        [
            Paragraph(inline(kicker.upper()), s["QKicker"]),
            Paragraph(inline(title), s["QH1"]),
            Paragraph(inline(deck), s["QDeck"]),
            HRFlowable(width="100%", thickness=0.8, color=OAK, spaceBefore=2, spaceAfter=7),
        ]
    )


def note_cards(cards, s, widths=None):
    """Build compact header/body cards.

    Each card is (heading, body, header_color, body_color).
    """
    widths = widths or [2.27 * inch] * len(cards)
    headers = [Paragraph(inline(card[0]).upper(), s["QCardHead"]) for card in cards]
    bodies = [Paragraph(inline(card[1]), s["QCardBody"]) for card in cards]
    table = Table([headers, bodies], colWidths=widths, hAlign="LEFT")
    style = [
        ("GRID", (0, 0), (-1, -1), 0.45, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    for index, card in enumerate(cards):
        style.extend(
            [
                ("BACKGROUND", (index, 0), (index, 0), card[2]),
                ("BACKGROUND", (index, 1), (index, 1), card[3]),
            ]
        )
    table.setStyle(TableStyle(style))
    return table


def workflow_strip(s):
    labels = [
        ("01", "FIELD VERIFY"),
        ("02", "MILL + REST"),
        ("03", "LABEL"),
        ("04", "GROOVE"),
        ("05", "MORTISE"),
        ("06", "DRY FIT"),
        ("07", "GLUE + QC"),
    ]
    cells = []
    for number, label in labels:
        cells.append(
            [
                Paragraph(f"<font color='#B98A52'><b>{number}</b></font>", s["QMicro"]),
                Paragraph(f"<b>{label}</b>", s["QMicro"]),
            ]
        )
    table = Table([cells], colWidths=[0.99 * inch] * 7, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PALE_BLUE),
                ("BOX", (0, 0), (-1, -1), 0.6, BLUE),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, RULE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return table


def assembly_page(story, s, number, title, deck, image_path, setup, action, pass_stop, note):
    page_heading(story, s, f"Assembly | {number:02d} of 06", title, deck)
    story.extend(
        [
            svg_figure(image_path.with_suffix(".svg"), 7.0 * inch),
            Spacer(1, 6),
            KeepTogether(
                [
                    note_cards(
                        [
                            ("Setup", setup, BLUE, PALE_BLUE),
                            ("Action", action, TEAL, PALE_TEAL),
                            ("Pass / stop", pass_stop, OAK_DARK, PALE),
                        ],
                        s,
                    ),
                    Spacer(1, 5),
                    Table(
                        [[Paragraph("<b>CABINETMAKER NOTE:</b> " + inline(note), s["QMicro"])]],
                        colWidths=[6.81 * inch],
                        style=TableStyle(
                            [
                                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7F8F8")),
                                ("BOX", (0, 0), (-1, -1), 0.45, RULE),
                                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                                ("TOPPADDING", (0, 0), (-1, -1), 5),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                            ]
                        ),
                    ),
                ]
            ),
        ]
    )


def section_panel(title, content, s, fill=colors.white, width=3.34 * inch):
    body = [Paragraph(inline(title).upper(), s["QH2"])] + content
    table = Table([[body]], colWidths=[width])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), fill),
                ("BOX", (0, 0), (-1, -1), 0.55, RULE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return table


def build():
    generate_assembly_diagrams()
    RELEASE.mkdir(exist_ok=True)
    text = SOURCE.read_text()
    sections = source_sections(text)
    s = styles()

    doc = BaseDocTemplate(
        str(OUT),
        pagesize=letter,
        leftMargin=0.68 * inch,
        rightMargin=0.68 * inch,
        topMargin=0.52 * inch,
        bottomMargin=0.65 * inch,
    )
    frame = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        letter[0] - doc.leftMargin - doc.rightMargin,
        letter[1] - doc.topMargin - doc.bottomMargin,
        id="shop-manual",
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
    )
    doc.addPageTemplates(PageTemplate(id="shop-manual", frames=frame, onPage=page_decor))

    illustration_dir = ROOT / "quick-guide/illustrations"
    story = []

    # 01 — Cover
    cover = ROOT / "illustrations/renders/cover-finished-door.png"
    story.extend(
        [
            Paragraph("DC-1916-001  /  BENCH EDITION  /  REV. A", s["QKicker"]),
            Table(
                [
                    [
                        Image(str(cover), width=3.37 * inch, height=5.05 * inch),
                        [
                            Spacer(1, 8),
                            Paragraph("Quick Cut &amp;<br/>Assembly<br/>Shop Manual", s["QTitle"]),
                            HRFlowable(width="70%", thickness=2.2, color=OAK, spaceBefore=4, spaceAfter=12),
                            Paragraph(
                                "Five-panel quarter-sawn white-oak interior door with concealed Festool Domino DF 500 joinery.",
                                s["QCoverDeck"],
                            ),
                            Paragraph(
                                "<b>TARGET SLAB</b><br/>24 x 79 x 1-3/8 inches",
                                s["QCoverDeck"],
                            ),
                            Paragraph(
                                "<font color='#8D312B'><b>FIELD HOLD:</b> Verify the completed jamb, floor, handing, and hardware before final sizing.</font>",
                                s["QCoverDeck"],
                            ),
                        ],
                    ]
                ],
                colWidths=[3.62 * inch, 3.18 * inch],
                style=TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ]
                ),
            ),
            Spacer(1, 15),
            note_cards(
                [
                    ("Scope", "Cut list, milling order, grooves, Domino layouts, dry fit, glue-up, and final QC.", BLUE, PALE_BLUE),
                    ("Shop rule", "Written dimensions control. Illustrations explain sequence and are not cutting templates.", TEAL, PALE_TEAL),
                ],
                s,
                widths=[3.40 * inch, 3.40 * inch],
            ),
            PageBreak(),
        ]
    )

    # 02 — Before cutting
    page_heading(
        story,
        s,
        "Preflight | Hold points",
        "Measure first. Establish the workpiece.",
        "A precise door begins with a verified opening, stable stock, and a consistent reference system.",
    )
    story.extend(
        [
            workflow_strip(s),
            Spacer(1, 10),
            Paragraph("Before any joinery", s["QH2"]),
            *parse_section(sections["Before cutting"], s),
            Spacer(1, 6),
            note_cards(
                [
                    (
                        "Release to milling",
                        "Completed jamb measured; undercut recorded; stock at 6-9% moisture; defects placed away from joints.",
                        BLUE,
                        PALE_BLUE,
                    ),
                    (
                        "Reference system",
                        "Show face, reference face, reference edge, top, bottom, and part ID remain visible through dry fit.",
                        TEAL,
                        PALE_TEAL,
                    ),
                    (
                        "Stop work",
                        "If verified width is not exactly 24 inches, recalculate rails, openings, and panels before any rail is crosscut.",
                        OAK_DARK,
                        PALE,
                    ),
                ],
                s,
            ),
            Spacer(1, 8),
            Table(
                [[Paragraph("<b>QUALITY STANDARD</b>  Work from one datum. Measure accumulated dimensions from the top of the slab—never from the previous mark.", s["QStop"])]],
                colWidths=[6.81 * inch],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAEFEC")),
                        ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#A33B32")),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                        ("TOPPADDING", (0, 0), (-1, -1), 7),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ]
                ),
            ),
            PageBreak(),
        ]
    )

    # 03 — Frame schedule
    page_heading(
        story,
        s,
        "Cut schedule | Frame",
        "Mill the frame as one matched set.",
        "Rough sizes include working allowance. Finished sizes control after the stock has rested and been final-planed.",
    )
    story.extend(
        [
            *parse_section(sections["Frame cut list"], s),
            Spacer(1, 8),
            note_cards(
                [
                    (
                        "Milling rule",
                        "Joint one face and edge, plane to about 1-7/16 inches, sticker and rest, then final-plane every frame member together.",
                        BLUE,
                        PALE_BLUE,
                    ),
                    (
                        "Length rule",
                        "Rails finish at 15 inches between 4-1/2-inch stiles. Keep both stiles long until the completed jamb is verified.",
                        TEAL,
                        PALE_TEAL,
                    ),
                    (
                        "Accept",
                        "Thickness +/-0.010 inch; paired rails within 0.005; reference edges square within 0.003 inch per inch.",
                        OAK_DARK,
                        PALE,
                    ),
                ],
                s,
            ),
            PageBreak(),
        ]
    )

    # 04 — Panel schedule
    page_heading(
        story,
        s,
        "Cut schedule | Panels",
        "Size floating panels for movement—not a press fit.",
        "Panel grain runs vertically. Mill the complete panel set together and verify each tongue in a sample groove.",
    )
    panel_content = parse_section(sections["Panel cut list"], s)
    groove_figure = ROOT / "illustrations/technical/panel-groove-section.svg"
    story.extend(panel_content)
    story.extend(
        [
            Spacer(1, 5),
            Table(
                [
                    [
                        svg_figure(groove_figure, 2.35 * inch),
                        [
                            Paragraph("PANEL FIT STANDARD", s["QH2"]),
                            Paragraph(
                                "<b>Field:</b> 1/2 inch thick.<br/>"
                                "<b>Tongue:</b> 7/32 inch thick x 1/2 inch deep.<br/>"
                                "<b>Groove:</b> 1/4 inch wide x 1/2 inch deep.<br/>"
                                "<b>Full-width panels:</b> 1/4 inch total side clearance.<br/>"
                                "<b>Lower pair:</b> 1/8 inch total side clearance.<br/>"
                                "<b>Before assembly:</b> Prefinish edges and tongues; add two silicone space balls per long edge.",
                                s["QBody"],
                            ),
                            Paragraph(
                                "<font color='#8D312B'><b>STOP:</b> A panel must enter by hand and move laterally after the frame is clamped. Never glue a tongue or groove.</font>",
                                s["QBody"],
                            ),
                        ],
                    ]
                ],
                colWidths=[2.60 * inch, 4.20 * inch],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), PALE),
                        ("BOX", (0, 0), (-1, -1), 0.55, RULE),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                        ("TOPPADDING", (0, 0), (-1, -1), 7),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ]
                ),
            ),
            PageBreak(),
        ]
    )

    # 05 — Story stick and milling sequence
    page_heading(
        story,
        s,
        "Layout | One datum",
        "Build the rail stack from a master story stick.",
        "Hook every location from the finished top edge. The accumulated stack—not isolated openings—controls the door.",
    )
    story.extend(
        [
            svg_figure(illustration_dir / "00-rail-stack.svg", 7.0 * inch),
            Spacer(1, 5),
            Paragraph("Controlled cutting sequence", s["QH2"]),
            *parse_section(sections["Cutting sequence"], s),
            PageBreak(),
        ]
    )

    # 06 — Groove and mortise coordination
    page_heading(
        story,
        s,
        "Joinery | Setup card",
        "Coordinate grooves and Domino mortises.",
        "Machine panel grooves first. Prove the fence, plunge depth, mortise width, and groove clearance on labeled test stock.",
    )
    story.extend(
        [
            svg_figure(illustration_dir / "00-groove-domino.svg", 7.0 * inch),
            Spacer(1, 6),
            note_cards(
                [
                    (
                        "Panel grooves",
                        "1/4 wide x 1/2 deep; centerline 11/16 from show face. Use stopped stile grooves only inside the openings.",
                        BLUE,
                        PALE_BLUE,
                    ),
                    (
                        "Frame DF 500",
                        "10 mm cutter; 10 x 50 tenons; 25 mm each side; 17.5 mm fence; 90 degrees. First tight, followers medium.",
                        TEAL,
                        PALE_TEAL,
                    ),
                    (
                        "Muntin DF 500",
                        "6 mm cutter; 6 x 40 tenons; 20 mm each side. G: 15/16 + 2-1/16. E/F: 6-15/16 + 8-1/16 from hinge-side shoulder.",
                        OAK_DARK,
                        PALE,
                    ),
                ],
                s,
            ),
            PageBreak(),
        ]
    )

    # 07–12 — Six assembly pages
    assembly_specs = [
        (
            1,
            "Inventory and orient the parts.",
            "Establish a complete, readable set before a mortise receives a tenon.",
            "01-parts-map.png",
            "Flat bench, cut schedules, pencil, and all parts show-face up.",
            "Lay out 2 stiles, 5 rails, 1 muntin, and 5 panels. Match every ID to the schedule.",
            "13 pieces present; K/L visually paired. Stop if any face, edge, top, or ID mark is missing.",
            "Carry the reference marks onto blue tape if a machining operation will remove the pencil line.",
        ),
        (
            2,
            "Dry-lay the frame at final coordinates.",
            "Transfer the rail stack from the story stick before introducing panels.",
            "02-exploded-frame.png",
            "Master story stick hooked at top; dry-fit tenons only; stiles parallel.",
            "Place C, M, D, E, and F at the controlled top coordinates; center G between E/F. Keep A left and B right.",
            "Stack totals 79 inches; openings are 13-1/2, 14, 9-1/2, and 11 inches; bottom bays are 6 inches.",
            "Mark mating joint IDs across each shoulder. A joint should only be able to return to one location.",
        ),
        (
            3,
            "Build the lower rail-and-muntin module.",
            "The lower module establishes two equal openings and captures panels K and L.",
            "03-bottom-module.png",
            "Proven 6 mm mortises; E, G, F, K, and L staged; panel tongues dry.",
            "Seat K and L in their grooves, then join G between E and F with four 6 x 40 tenons.",
            "Two 6 x 11 openings; shoulders close by hand; panels slide. Stop if the muntin bows either rail.",
            "Dry-fit this module as a unit before the full door. It is the only subassembly with a center member.",
        ),
        (
            4,
            "Load rails and panels from the hinge stile.",
            "Use D-101A as the registration spine while the door remains flat and show-face up.",
            "04-load-panels.png",
            "D-101A supported flat; rails, panels, and lower module staged in order.",
            "Seat rails in A. Slide H, J, N, then the complete lower module leftward from the open lock-stile end.",
            "Every tongue captured; grooves aligned; no panel forced. Stop if a panel cannot move laterally.",
            "Support long rails so their weight does not lever against partially engaged Domino tenons.",
        ),
        (
            5,
            "Close the lock stile over all rail ends.",
            "Start every exposed tenon before applying clamp pressure.",
            "05-close-lock-stile.png",
            "D-101B parallel to A; all exposed tenons started; padded caul ready.",
            "Bring B inward evenly. Tap only through the caul, alternating top and bottom.",
            "All shoulders nearly close by hand. Stop at the first hung joint—do not drive one rail ahead of the others.",
            "A stile that will not close evenly usually signals a missed tongue, reversed part, or misregistered mortise.",
        ),
        (
            6,
            "Clamp, square, and verify movement.",
            "Close shoulders with moderate pressure, correct geometry, then make the final check.",
            "06-clamp-square.png",
            "Alternating-face clamps at rail locations; padded cauls; two tapes; winding sticks.",
            "Snug shoulders, compare diagonals, remove twist, then apply only the pressure needed to hold closure.",
            "Diagonal difference <= 1/16; twist <= 1/32; gaps <= 0.005; all five panels move.",
            "Recheck geometry after five minutes. Clamp pressure can creep the frame after the first reading.",
        ),
    ]
    for index, spec in enumerate(assembly_specs):
        number, title, deck, filename, setup, action, pass_stop, note = spec
        assembly_page(
            story,
            s,
            number,
            title,
            deck,
            illustration_dir / filename,
            setup,
            action,
            pass_stop,
            note,
        )
        story.append(PageBreak())

    # 13 — Dry-fit and timed rehearsal
    page_heading(
        story,
        s,
        "Assembly | Rehearsal",
        "Prove the fit, sequence, and clock.",
        "Use relieved test tenons for rehearsal. Keep all 30 clean factory tenons untouched until adhesive is opened.",
    )
    story.extend(
        [
            section_panel(
                "Dry assembly",
                parse_section(sections["Dry assembly"], s),
                s,
                PALE_BLUE,
                6.81 * inch,
            ),
            Spacer(1, 10),
            note_cards(
                [
                    (
                        "Test tenons",
                        "Shorten slightly and edge-sand only the labeled rehearsal set. Never substitute them for the 30 clean glue-up tenons.",
                        BLUE,
                        PALE_BLUE,
                    ),
                    (
                        "Geometry gate",
                        "24 x 79 target; diagonals within 1/16; twist within 1/32; shoulders <=0.005; five panels move.",
                        TEAL,
                        PALE_TEAL,
                    ),
                    (
                        "Time gate",
                        "Rehearsal time + 25% margin must fit the adhesive's published open/assembly time at measured shop temperature.",
                        OAK_DARK,
                        PALE,
                    ),
                ],
                s,
            ),
            Spacer(1, 10),
            Paragraph("Rehearsal record", s["QH2"]),
            Table(
                [
                    [
                        Paragraph("<b>SHOP TEMP.</b><br/><br/>________", s["QMicro"]),
                        Paragraph("<b>ADHESIVE / LOT</b><br/><br/>____________________", s["QMicro"]),
                        Paragraph("<b>PUBLISHED LIMIT</b><br/><br/>________ min", s["QMicro"]),
                    ],
                    [
                        Paragraph("<b>STAGE A DRY TIME</b><br/><br/>________ min", s["QMicro"]),
                        Paragraph("<b>STAGE B DRY TIME</b><br/><br/>________ min", s["QMicro"]),
                        Paragraph("<b>TIME + 25% / PASS</b><br/><br/>________ / ________", s["QMicro"]),
                    ],
                ],
                colWidths=[1.60 * inch, 2.80 * inch, 2.40 * inch],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                        ("BOX", (0, 0), (-1, -1), 0.55, RULE),
                        ("INNERGRID", (0, 0), (-1, -1), 0.35, RULE),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                        ("TOPPADDING", (0, 0), (-1, -1), 7),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ]
                ),
            ),
            Spacer(1, 9),
            Table(
                [[Paragraph("<b>STOP:</b> If either timed stage plus margin exceeds the selected adhesive limit, revise the sequence, add help, or select a suitable longer-open-time Type II PVA before proceeding.", s["QStop"])]],
                colWidths=[6.81 * inch],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAEFEC")),
                        ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#A33B32")),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                        ("TOPPADDING", (0, 0), (-1, -1), 7),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ]
                ),
            ),
            PageBreak(),
        ]
    )

    # 14 — Two-stage glue-up
    page_heading(
        story,
        s,
        "Adhesive | Two-stage runbook",
        "Glue the lower module. Cure it. Then glue the frame.",
        "The staged plan reduces the final operation from 30 tenons to 26 and preserves a controlled correction window.",
    )
    story.extend(
        [
            section_panel(
                "Glue-up",
                parse_section(sections["Glue-up"], s),
                s,
                PALE_TEAL,
                6.81 * inch,
            ),
            Spacer(1, 10),
            Paragraph("Controlled sequence", s["QH2"]),
            Table(
                [
                    [
                        Paragraph("<b>1</b><br/>TIME DRY RUN", s["QMicro"]),
                        Paragraph("<b>2</b><br/>GLUE MODULE", s["QMicro"]),
                        Paragraph("<b>3</b><br/>CURE STAGE A", s["QMicro"]),
                        Paragraph("<b>4</b><br/>GLUE FRAME", s["QMicro"]),
                        Paragraph("<b>5</b><br/>SQUARE + TWIST", s["QMicro"]),
                        Paragraph("<b>6</b><br/>CLEAN + CURE", s["QMicro"]),
                    ]
                ],
                colWidths=[1.13 * inch] * 6,
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), PALE),
                        ("BOX", (0, 0), (-1, -1), 0.6, OAK_DARK),
                        ("INNERGRID", (0, 0), (-1, -1), 0.35, RULE),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("TOPPADDING", (0, 0), (-1, -1), 7),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ]
                ),
            ),
            Spacer(1, 8),
            note_cards(
                [
                    (
                        "Tenon inventory",
                        "Stage A: 4 x 6 x 40 mm. Stage B: 26 x 10 x 50 mm. Reserve all 30 clean factory tenons for glue.",
                        BLUE,
                        PALE_BLUE,
                    ),
                    (
                        "Clamp kit",
                        "At least 5 rail-location clamps, padded cauls, 2 tapes, winding sticks, brushes, timer, plus a spare clamp.",
                        TEAL,
                        PALE_TEAL,
                    ),
                    (
                        "Time gate",
                        "Timed rehearsal + 25% margin must fit the adhesive's published open/assembly time at measured shop temperature.",
                        OAK_DARK,
                        PALE,
                    ),
                ],
                s,
            ),
            Spacer(1, 8),
            Table(
                [[Paragraph("<b>ADHESIVE BOUNDARY:</b> Type II PVA belongs on mortise walls and tenon faces only. Keep every panel tongue and groove dry.", s["QStop"])]],
                colWidths=[6.81 * inch],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAEFEC")),
                        ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#A33B32")),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                        ("TOPPADDING", (0, 0), (-1, -1), 7),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ]
                ),
            ),
            PageBreak(),
        ]
    )

    # 15 — Final QC, field gates, and safety
    page_heading(
        story,
        s,
        "Quality control | Release",
        "Do not release the slab on appearance alone.",
        "Record the geometry, verify free panel movement, and keep perimeter and hardware machining on field hold.",
    )
    final_checks = parse_section(sections["Final assembly checks"], s)
    production_tolerances = parse_section(sections["Production tolerances"], s)
    safety = parse_section(sections["Essential safety"], s)
    story.extend(
        [
            Table(
                [
                    [
                        section_panel("Final assembly checks", final_checks, s, PALE_BLUE),
                        section_panel("Production tolerances", production_tolerances, s, PALE),
                    ]
                ],
                colWidths=[3.40 * inch, 3.40 * inch],
                style=TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ]
                ),
            ),
            Spacer(1, 10),
            Paragraph("Field release gates", s["QH2"]),
            note_cards(
                [
                    (
                        "Opening",
                        "Completed jamb measured at top, middle, and bottom; head checked for level; floor and finished undercut recorded.",
                        BLUE,
                        PALE_BLUE,
                    ),
                    (
                        "Hardware",
                        "Handing confirmed in the room; actual hinge leaves, lock case, backset, strike, and fasteners in hand.",
                        TEAL,
                        PALE_TEAL,
                    ),
                    (
                        "Perimeter",
                        "Final width, height, bevel, clearances, hinge mortises, and lock machining remain on hold until field data is signed off.",
                        OAK_DARK,
                        PALE,
                    ),
                ],
                s,
            ),
            Spacer(1, 9),
            Table(
                [[Paragraph("<b>ESSENTIAL SAFETY</b>  " + " ".join(flowable.getPlainText() for flowable in safety), s["QMicro"])]],
                colWidths=[6.81 * inch],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), PALE),
                        ("BOX", (0, 0), (-1, -1), 0.55, RULE),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ]
                ),
            ),
            Spacer(1, 8),
            Table(
                [
                    [
                        Paragraph("<b>INSPECTED BY</b><br/><br/>____________________________", s["QMicro"]),
                        Paragraph("<b>DATE</b><br/><br/>________________", s["QMicro"]),
                        Paragraph("<b>SLAB SIZE</b><br/><br/>_______ x _______ x _______", s["QMicro"]),
                    ]
                ],
                colWidths=[2.75 * inch, 1.55 * inch, 2.50 * inch],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                        ("BOX", (0, 0), (-1, -1), 0.55, RULE),
                        ("INNERGRID", (0, 0), (-1, -1), 0.35, RULE),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                        ("TOPPADDING", (0, 0), (-1, -1), 7),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ]
                ),
            ),
        ]
    )

    doc.build(story)
    reader = PdfReader(str(OUT))
    extracted = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert len(reader.pages) == 15, f"Expected 15 pages, got {len(reader.pages)}"
    extracted_lower = extracted.lower()
    for required in ["D-101A", "DF 500", "Glue-up", "Field release gates", "ASSEMBLY"]:
        assert required.lower() in extracted_lower, f"Missing required term: {required}"
    assert not re.search(r"\b(TODO|TBD|placeholder)\b", extracted, re.I)
    (RELEASE / SOURCE.name).write_text(text)
    print(f"PASS: built {OUT.name} ({len(reader.pages)} pages)")


if __name__ == "__main__":
    build()
