#!/usr/bin/env python3
"""Build the detailed custom-moulding manual, drawing set, and field worksheet."""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas as pdfcanvas
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

from build_quick_guide import (
    BLUE,
    GRAY,
    INK,
    OAK,
    OAK_DARK,
    PALE,
    PALE_BLUE,
    PALE_TEAL,
    RULE,
    TEAL,
    inline,
    markdown_table,
    note_cards,
    page_heading,
    section_panel,
    source_sections,
    styles,
    svg_figure,
)
from generate_moulding_diagrams import generate as generate_moulding_diagrams

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "moulding-guide" / "DC-1916-001_Custom_Moulding_Shop_Manual.md"
ILLUSTRATIONS = ROOT / "moulding-guide" / "illustrations"
RELEASE = ROOT / "release"
GUIDE_OUT = RELEASE / "DC-1916-001_Custom_Moulding_Shop_Manual.pdf"
DRAWINGS_OUT = RELEASE / "DC-1916-001_Moulding_Drawings.pdf"
WORKSHEET_OUT = RELEASE / "DC-1916-001_Moulding_Field_Measurement_Worksheet.pdf"
SPECIFICATION = ROOT / "project" / "specification.yaml"

PROJECT_SPEC = json.loads(SPECIFICATION.read_text())["project"]
PROJECT_NUMBER = PROJECT_SPEC["number"]
REVISION = PROJECT_SPEC["revision"]
REVISION_CODE = REVISION.rsplit(" ", 1)[-1]

RED = colors.HexColor("#A33B32")
GREEN = colors.HexColor("#547A58")


def moulding_page_decor(canvas, doc):
    canvas.saveState()
    canvas.setTitle("DC-1916-001 Custom Moulding Shop Manual")
    canvas.setAuthor("DC-1916-001 Project Team")
    canvas.setSubject("Detailed cutting, fitting, assembly, installation, and QC for custom oak moulding")
    canvas.setStrokeColor(OAK)
    canvas.setLineWidth(1.2)
    canvas.line(0.65 * inch, 0.52 * inch, 7.85 * inch, 0.52 * inch)
    canvas.setFont("Helvetica-Bold", 7.1)
    canvas.setFillColor(BLUE)
    canvas.drawString(0.65 * inch, 0.36 * inch, f"{PROJECT_NUMBER}  |  CUSTOM MOULDING  |  {REVISION.upper()}")
    canvas.setFont("Helvetica", 7.1)
    canvas.setFillColor(GRAY)
    canvas.drawRightString(7.85 * inch, 0.36 * inch, f"PAGE {canvas.getPageNumber():02d}")
    canvas.restoreState()


def drawing_page_decor(canvas, doc):
    canvas.saveState()
    canvas.setTitle("DC-1916-001 Moulding Drawings")
    canvas.setAuthor("DC-1916-001 Project Team")
    canvas.setSubject("Dimensioned custom-moulding technical drawing set")
    canvas.setStrokeColor(OAK)
    canvas.setLineWidth(1.0)
    canvas.line(0.55 * inch, 0.48 * inch, 7.95 * inch, 0.48 * inch)
    canvas.setFont("Helvetica-Bold", 7)
    canvas.setFillColor(BLUE)
    canvas.drawString(0.55 * inch, 0.31 * inch, f"{PROJECT_NUMBER}  |  MOULDING DRAWING SET  |  {REVISION.upper()}  |  NTS")
    canvas.setFillColor(GRAY)
    canvas.drawRightString(7.95 * inch, 0.31 * inch, f"SHEET {canvas.getPageNumber():02d} OF 12")
    canvas.restoreState()


def make_doc(path: Path, decorator, frame_id: str):
    doc = BaseDocTemplate(
        str(path),
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
        id=frame_id,
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
    )
    doc.addPageTemplates(PageTemplate(id=frame_id, frames=frame, onPage=decorator))
    return doc


def workflow_strip(s):
    labels = [
        ("01", "FIELD VERIFY"),
        ("02", "CHOOSE JOINT"),
        ("03", "CALCULATE"),
        ("04", "MILL PROFILES"),
        ("05", "DRY-FIT + LABEL"),
        ("06", "P120 + FINISH"),
        ("07", "CURE / INSTALL"),
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
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return table


def diagram(path_name: str, width=7.0 * inch):
    return svg_figure(ILLUSTRATIONS / f"{path_name}.svg", width)


def stop_banner(text, s):
    return Table(
        [[Paragraph("<b>STOP:</b> " + inline(text), s["QStop"])]],
        colWidths=[6.81 * inch],
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAEFEC")),
                ("BOX", (0, 0), (-1, -1), 0.75, RED),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        ),
    )


def operation_page(story, s, number, title, deck, slug, setup, action, pass_stop, note=None):
    page_heading(story, s, f"Field sequence | {number}", title, deck)
    story.extend(
        [
            diagram(slug),
            Spacer(1, 6),
            note_cards(
                [
                    ("Setup", setup, BLUE, PALE_BLUE),
                    ("Action", action, TEAL, PALE_TEAL),
                    ("Pass / stop", pass_stop, OAK_DARK, PALE),
                ],
                s,
            ),
        ]
    )
    if note:
        story.extend(
            [
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
        )


def extract_table(section_lines):
    rows = []
    for line in section_lines:
        if line.startswith("|") and "---" not in line:
            rows.append([cell.strip() for cell in line.strip("|").split("|")])
    return rows


def build_guide() -> int:
    text = SOURCE.read_text()
    sections = source_sections(text)
    s = styles()
    doc = make_doc(GUIDE_OUT, moulding_page_decor, "moulding-manual")
    story = []

    # 01 - cover
    cover = ROOT / "illustrations" / "renders" / "cover-finished-door.png"
    story.extend(
        [
            Paragraph(f"{PROJECT_NUMBER}  /  COMPANION SHOP MANUAL  /  {REVISION.upper()}", s["QKicker"]),
            Table(
                [
                    [
                        Image(str(cover), width=3.42 * inch, height=5.15 * inch),
                        [
                            Spacer(1, 6),
                            Paragraph("Custom Moulding<br/>Cut, Fit &amp;<br/>Installation<br/>Shop Manual", s["QTitle"]),
                            HRFlowable(width="72%", thickness=2.2, color=OAK, spaceBefore=4, spaceAfter=11),
                            Paragraph(
                                "Quarter-sawn white-oak casing, backband, door stops, and field-supported cap or plinth treatment.",
                                s["QCoverDeck"],
                            ),
                            Paragraph(
                                "<b>DEFAULT PROFILE</b><br/>3/4 x 4-1/2 casing<br/>1 x 1-1/8 backband<br/>3/8 x 1-1/4 stop",
                                s["QCoverDeck"],
                            ),
                            Paragraph(
                                "<font color='#8D312B'><b>FIELD HOLD:</b> Measure the completed jamb and adjacent original trim before milling.</font>",
                                s["QCoverDeck"],
                            ),
                        ],
                    ]
                ],
                colWidths=[3.65 * inch, 3.15 * inch],
                style=TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ]
                ),
            ),
            Spacer(1, 12),
            note_cards(
                [
                    (
                        "Scope",
                        "Measure, mill, dry-fit and label, final-sand, finish and fully cure, then permanently install and inspect.",
                        BLUE,
                        PALE_BLUE,
                    ),
                    (
                        "Drawing rule",
                        "Written dimensions and measured field values control. Illustrations are explanatory, not cutting templates.",
                        TEAL,
                        PALE_TEAL,
                    ),
                ],
                s,
                widths=[3.40 * inch, 3.40 * inch],
            ),
            PageBreak(),
        ]
    )

    # 02 - scope and anatomy
    page_heading(
        story,
        s,
        "System | Scope",
        "Understand the installed assembly.",
        "The base schedule covers one trimmed face and one three-piece stop set; trim quantities change when both faces are renewed.",
    )
    story.extend(
        [
            workflow_strip(s),
            Spacer(1, 6),
            diagram("01-installed-anatomy", 6.75 * inch),
            Spacer(1, 6),
            note_cards(
                [
                    (
                        "One face",
                        "2 side casings, 1 head casing, 3 backbands, and 1 stop set.",
                        BLUE,
                        PALE_BLUE,
                    ),
                    (
                        "Two faces",
                        "4 side casings, 2 heads, and 6 backbands. The stop set remains three pieces.",
                        TEAL,
                        PALE_TEAL,
                    ),
                    (
                        "Conditional",
                        "Cap and plinth parts exist only when adjacent original trim supports them.",
                        OAK_DARK,
                        PALE,
                    ),
                ],
                s,
            ),
            Spacer(1, 6),
            Table(
                [[Paragraph(
                    "<b>TOOL NOTE:</b> No dado blade is required. Use ordinary ripping/crosscutting setups for straight stock and a plunge router or hand tools only for localized casing-back relief.",
                    s["QMicro"],
                )]],
                colWidths=[6.81 * inch],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7F8F8")),
                        ("BOX", (0, 0), (-1, -1), 0.55, TEAL),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ]
                ),
            ),
            PageBreak(),
        ]
    )

    # 03 - measurement gate
    page_heading(
        story,
        s,
        "Field work | Release gate",
        "Measure the opening and the house evidence.",
        "Profiles, joint language, quantities, and final lengths remain on hold until the worksheet is complete.",
    )
    story.extend(
        [
            diagram("02-field-measurements"),
            Spacer(1, 6),
            note_cards(
                [
                    (
                        "Measure",
                        "W1/W2/W3, H-L/H-R, both legs in both plumb planes, head level, diagonals/square, winding-stick twist, projection, wall, and floor.",
                        BLUE,
                        PALE_BLUE,
                    ),
                    (
                        "Decide",
                        "One or two faces; mitered or square-butt head; cap, plinth, baseboard, and corner treatment.",
                        TEAL,
                        PALE_TEAL,
                    ),
                    (
                        "Release",
                        "Photographs attached, fastener paths checked, finish sample planned, and field worksheet signed.",
                        OAK_DARK,
                        PALE,
                    ),
                ],
                s,
            ),
            Spacer(1, 6),
            stop_banner("Do not use nominal door size as a substitute for the completed-jamb measurements.", s),
            PageBreak(),
        ]
    )

    # 04 - profiles
    page_heading(
        story,
        s,
        "Fabrication | Profiles",
        "Approve the complete profile family on samples.",
        "The restrained rectangular profiles preserve a 1916-compatible appearance without requiring a router table, shaper, or CNC.",
    )
    story.extend(
        [
            diagram("03-profile-register"),
            Spacer(1, 6),
            note_cards(
                [
                    (
                        "Fixed defaults",
                        "Casing 3/4 x 4-1/2; backband 1 x 1-1/8; stop 3/8 x 1-1/4; reveal 3/16.",
                        BLUE,
                        PALE_BLUE,
                    ),
                    (
                        "Edge work",
                        "Casing/backband 1/32 ease; stop 1/16 door-side ease; cap 1/8 chamfer only after approval.",
                        TEAL,
                        PALE_TEAL,
                    ),
                    (
                        "Field controlled",
                        "All lengths, plinth width/height/profile, cap use, and any departure from the defaults.",
                        OAK_DARK,
                        PALE,
                    ),
                ],
                s,
            ),
            PageBreak(),
        ]
    )

    # 05 - production schedule
    page_heading(
        story,
        s,
        "Cut schedule | Quantities",
        "Rough-cut for the selected face count and joint scheme.",
        "Every rough blank includes field-fit stock. Mitered legs require their full outside long point, not merely jamb height.",
    )
    schedule_rows = extract_table(sections["Base production schedule"])
    schedule_widths = [0.62 * inch, 0.93 * inch, 0.52 * inch, 1.02 * inch, 1.18 * inch, 2.55 * inch]
    story.extend(
        [
            markdown_table(schedule_rows, s, schedule_widths),
            Spacer(1, 8),
            note_cards(
                [
                    (
                        "One-face base",
                        "2 M-201 legs + 1 head; 3 M-202 backbands; one 3-piece M-203 stop set.",
                        BLUE,
                        PALE_BLUE,
                    ),
                    (
                        "Two-face multiplier",
                        "Double M-201/M-202. Double M-204/M-205 only when used on both faces. Do not double M-203.",
                        TEAL,
                        PALE_TEAL,
                    ),
                    (
                        "Stock allowance",
                        "Calculate linear footage by profile, then add at least 20% for matching, checks, scribes, and samples.",
                        OAK_DARK,
                        PALE,
                    ),
                ],
                s,
            ),
            Spacer(1, 8),
            stop_banner(
                "The former 'jamb height + 2' shortcut is not sufficient for a mitered leg. Use the longest-point formula plus allowance.",
                s,
            ),
            Spacer(1, 8),
            Table(
                [
                    [
                        Paragraph("<b>FACE COUNT</b><br/><br/>1 / 2", s["QMicro"]),
                        Paragraph("<b>HEAD SCHEME</b><br/><br/>MITER / SQUARE", s["QMicro"]),
                        Paragraph("<b>CAP</b><br/><br/>YES / NO", s["QMicro"]),
                        Paragraph("<b>PLINTH</b><br/><br/>YES / NO", s["QMicro"]),
                    ]
                ],
                colWidths=[1.70 * inch] * 4,
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
            PageBreak(),
        ]
    )

    # 06 - separate two-face moulding purchase order
    page_heading(
        story,
        s,
        "Procurement | Two-face order",
        "Buy a separate S4S package for the complete opening.",
        "This order preserves the owner-labeled A-O stock for the door and covers casing and backband on both faces plus one three-piece stop set.",
    )
    purchase_rows = [
        [
            Paragraph("<font color='#FFFFFF'><b>QTY</b></font>", s["QMicro"]),
            Paragraph("<font color='#FFFFFF'><b>DEALER DESCRIPTION</b></font>", s["QMicro"]),
            Paragraph("<font color='#FFFFFF'><b>ACTUAL ACCEPTANCE GATE</b></font>", s["QMicro"]),
            Paragraph("<font color='#FFFFFF'><b>ALLOCATION</b></font>", s["QMicro"]),
        ],
        [
            Paragraph("<b>7</b>", s["QMicro"]),
            Paragraph("S4S 4/4 QS white oak<br/>nominal 6 in x 8 ft", s["QMicro"]),
            Paragraph(
                "At least 3/4 in thick at the thinnest point, 5-1/2 in wide, and 96 in long. "
                "Stock at exactly 3/4 in must already be flat.",
                s["QMicro"],
            ),
            Paragraph(
                "4 side casings; 2 heads from 1 board; 1 full-length casing contingency; "
                "1 wide stop mother blank.",
                s["QMicro"],
            ),
        ],
        [
            Paragraph("<b>2</b>", s["QMicro"]),
            Paragraph("S4S 6/4 QS white oak<br/>nominal 6 in x 8 ft", s["QMicro"]),
            Paragraph(
                "At least 1-1/4 in thick, 5-1/2 in wide, and 96 in long; clear through every required lane.",
                s["QMicro"],
            ),
            Paragraph(
                "One board per face: 2 side backbands + 1 head backband; optional cap also fits "
                "when a square head is field-supported.",
                s["QMicro"],
            ),
        ],
        [
            Paragraph("<b>9</b>", s["QMicro"]),
            Paragraph("<b>Separate moulding package</b>", s["QMicro"]),
            Paragraph("<b>About 40 dealer BF</b><br/>28 BF 4/4 + 12 BF 6/4", s["QMicro"]),
            Paragraph("Both faces + one stop set; no plinth stock.", s["QMicro"]),
        ],
    ]
    purchase_table = Table(
        purchase_rows,
        colWidths=[0.42 * inch, 1.45 * inch, 2.33 * inch, 2.60 * inch],
        repeatRows=1,
    )
    purchase_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), BLUE),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BACKGROUND", (0, 1), (-1, -2), colors.white),
                ("BACKGROUND", (0, -1), (-1, -1), PALE_BLUE),
                ("BOX", (0, 0), (-1, -1), 0.6, BLUE),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, RULE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    length_rows = [
        [
            Paragraph("<font color='#FFFFFF'><b>HEAD</b></font>", s["QMicro"]),
            Paragraph("<font color='#FFFFFF'><b>SIDE CASING</b></font>", s["QMicro"]),
            Paragraph("<font color='#FFFFFF'><b>SIDE BACKBAND</b></font>", s["QMicro"]),
            Paragraph("<font color='#FFFFFF'><b>SOUND-LENGTH GATE</b></font>", s["QMicro"]),
        ],
        [
            Paragraph("Square", s["QMicro"]),
            Paragraph("4 @ 83-3/16 in", s["QMicro"]),
            Paragraph("4 @ 87-11/16 in", s["QMicro"]),
            Paragraph("Casing 85-3/16; band 89-11/16 in", s["QMicro"]),
        ],
        [
            Paragraph("Miter", s["QMicro"]),
            Paragraph("4 @ 87-11/16 in", s["QMicro"]),
            Paragraph("4 @ 88-13/16 in", s["QMicro"]),
            Paragraph("Casing 89-11/16; band 90-13/16 in", s["QMicro"]),
        ],
    ]
    length_table = Table(
        length_rows,
        colWidths=[0.78 * inch, 1.34 * inch, 1.44 * inch, 3.24 * inch],
        repeatRows=1,
    )
    length_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), OAK_DARK),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.55, OAK_DARK),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, RULE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.extend(
        [
            purchase_table,
            Spacer(1, 7),
            note_cards(
                [
                    (
                        "Correct notation",
                        "Specify S4S 4/4, spoken four-quarter. Do not order 'S4 4x4.' Nominal 6-inch stock must measure at least 5-1/2 inches wide.",
                        BLUE,
                        PALE_BLUE,
                    ),
                    (
                        "Backband thickness",
                        "4/4 S4S is normally about 3/4 thick and cannot finish at 1 inch. Use 6/4 S4S measuring at least 1-1/4.",
                        TEAL,
                        PALE_TEAL,
                    ),
                    (
                        "Scope hold",
                        "No plinths are included. Add them only after adjacent original trim establishes profile, width, and height.",
                        OAK_DARK,
                        PALE,
                    ),
                ],
                s,
            ),
            Spacer(1, 7),
            length_table,
            Spacer(1, 6),
            Paragraph(
                "<b>COMMON ROUGH BLANKS:</b> 2 head casings @ 35-3/8 in; 2 mandatory head backbands @ 37-5/8 in; "
                "2 side stops @ 83 in; 1 head stop @ 26 in. Optional square-head caps: 2 @ 39-1/8 in. "
                "Rough lengths already include field-fit allowance; sound-length gates add 2 in for board-end cleanup.",
                s["QMicro"],
            ),
            Spacer(1, 6),
            stop_banner(
                "Use these dimensions to buy and reserve stock only. Completed-jamb measurements and adjacent-trim evidence control every final cut.",
                s,
            ),
            PageBreak(),
        ]
    )

    # 07 - formulas
    page_heading(
        story,
        s,
        "Layout | Length formulas",
        "Calculate rough stock, then transfer final cuts.",
        "W, H-L, and H-R come from the completed jamb. R, C, B, and P are approved profile values.",
    )
    story.extend(
        [
            diagram("04-length-formulas"),
            Spacer(1, 6),
            note_cards(
                [
                    (
                        "Mitered",
                        "Head short = W + 2R; head long = W + 2R + 2C; each leg long = H + R + C.",
                        BLUE,
                        PALE_BLUE,
                    ),
                    (
                        "Square-butt",
                        "Each leg = H + R; head = W + 2R + 2C. Fit mandatory M-202C; cap = actual fitted head-backband outside width + 2P.",
                        TEAL,
                        PALE_TEAL,
                    ),
                    (
                        "Backband",
                        "Rough sides: miter = fitted casing outside long + B + 2; square = fitted casing length + C + 2. Mandatory head = fitted head-casing outside + 2B + 2.",
                        OAK_DARK,
                        PALE,
                    ),
                ],
                s,
            ),
            Spacer(1, 7),
            stop_banner("Add at least 2 inches total rough allowance and never final-cut a part from arithmetic alone.", s),
            PageBreak(),
        ]
    )

    # 08 - milling
    page_heading(
        story,
        s,
        "Fabrication | Stable stock",
        "Mill the profiles as matched families.",
        "Straight, stable, color-matched stock is cheaper than correcting bowed stain-grade trim at the wall.",
    )
    story.extend(
        [
            diagram("05-stock-milling"),
            Spacer(1, 6),
            note_cards(
                [
                    (
                        "Sequence",
                        "Rough-cut, joint, plane as a family, sticker/rest, final-plane, rip, then label.",
                        BLUE,
                        PALE_BLUE,
                    ),
                    (
                        "Stop stock",
                        "Plane a wide mother blank to 3/8 before ripping 1-1/4 strips. Never plane loose narrow stops.",
                        TEAL,
                        PALE_TEAL,
                    ),
                    (
                        "Acceptance",
                        "Profiles straight; paired casing thickness within 0.005; reference edges square and clean.",
                        OAK_DARK,
                        PALE,
                    ),
                ],
                s,
            ),
            Spacer(1, 7),
            stop_banner("Support long stock at both ends and keep hands out of the narrow-rip path.", s),
            PageBreak(),
        ]
    )

    # 09 - profiling
    page_heading(
        story,
        s,
        "Fabrication | Setup card",
        "Form restrained profiles without a router table.",
        "Reference every operation from the labeled face and edge; preserve samples until the installed finish is accepted.",
    )
    story.extend(
        [
            diagram("06-profile-machining"),
            Spacer(1, 6),
            note_cards(
                [
                    (
                        "Hand work",
                        "Use a finely set block plane, scraper, or controlled abrasive block for the small eased arrises.",
                        BLUE,
                        PALE_BLUE,
                    ),
                    (
                        "Router work",
                        "Clamp wide stock; use a plunge base plus edge guide. Keep narrow profiles in a mother blank.",
                        TEAL,
                        PALE_TEAL,
                    ),
                    (
                        "Sample gate",
                        "Approve dimension, edge shape, ray figure, and finish response before production.",
                        OAK_DARK,
                        PALE,
                    ),
                ],
                s,
            ),
            PageBreak(),
        ]
    )

    # 10 - section
    page_heading(
        story,
        s,
        "Fit | Jamb and wall section",
        "Make the casing bear flat.",
        "The casing bridges two field surfaces. Relief or shimming corrects the interface; fastener pressure does not.",
    )
    story.extend(
        [
            diagram("07-jamb-wall-section"),
            Spacer(1, 6),
            note_cards(
                [
                    (
                        "Proud jamb",
                        "Transfer the local projection and cut only the required back relief; keep at least 1/2 inch sound casing.",
                        BLUE,
                        PALE_BLUE,
                    ),
                    (
                        "Recessed jamb",
                        "Install a continuous fitted wood shim or approved extension. Never span a void with the casing.",
                        TEAL,
                        PALE_TEAL,
                    ),
                    (
                        "Substrate stop",
                        "Projection >1/8, loose plaster, moisture, or an abrupt hump requires repair before trim.",
                        OAK_DARK,
                        PALE,
                    ),
                ],
                s,
            ),
            PageBreak(),
        ]
    )

    # 11 - joint decision
    page_heading(
        story,
        s,
        "Joinery | Head condition",
        "Match one historic joint language.",
        "A mitered surround and a square-butt head are both buildable; adjacent original openings determine the correct choice.",
    )
    story.extend(
        [
            diagram("08-head-joint-options"),
            Spacer(1, 6),
            note_cards(
                [
                    (
                        "Mitered surround",
                        "Use when original openings are mitered. Tune visible faces on a shooting board.",
                        BLUE,
                        PALE_BLUE,
                    ),
                    (
                        "Square-butt head",
                        "Use when adjacent work has square heads, caps, or related entablature. Head spans both legs.",
                        TEAL,
                        PALE_TEAL,
                    ),
                    (
                        "Alignment aid",
                        "A biscuit or 5 x 30 Domino is optional after a scrap test; it must not break through either face.",
                        OAK_DARK,
                        PALE,
                    ),
                ],
                s,
            ),
            PageBreak(),
        ]
    )

    # 12-18 - installation pages
    operation_page(
        story,
        s,
        "01 of 07",
        "Dry-fit and label the door stops.",
        "Head stop first; side stops butt beneath it; paper shims prevent latch preload.",
        "09-stop-install",
        "Door fully fitted, hung, latched, and operating freely; paper shims; minimum temporary 18-ga tacks.",
        "Fit head, then sides through 0.010-0.020 shims. Tack only, cycle and latch, label all three pieces, then remove.",
        "Quiet continuous contact; easy latch; no slab bow or rattle. No permanent fastener pattern at dry fit.",
        "The operating door is the locating fixture. Record shim points so the cured stops return to the proven position.",
    )
    story.append(PageBreak())

    operation_page(
        story,
        s,
        "02 of 07",
        "Fit and label the side casings.",
        "Use a rigid reveal gauge and treat the two floor conditions independently.",
        "10-side-casing-fit",
        "3/16 reveal gauge, paired M-201 legs, level, straightedge, scribe, and three temporary brads per leg.",
        "Mark reveal, scribe bottoms, hold each leg, transfer the head mark, cut long, and tune to the line.",
        "Reveal variation <=1/32; plumb <=1/16 full height; casing bears flat; grain pair remains oriented.",
        "Temporary tacks hold the dry fit only. Preserve face, side, bottom-datum, and joint labels through finish cure.",
    )
    story.append(PageBreak())

    operation_page(
        story,
        s,
        "03 of 07",
        "Dry-fit and label the head casing.",
        "Fit one end first, then mark the second from the temporarily tacked legs.",
        "11-head-casing-fit",
        "Tacked side casings, approved head scheme, sharp saw, shooting board, level, and light.",
        "Cut long, tune one joint, scribe the second, dry-fit all three pieces, then label the head and both mating joints.",
        "Head level <=1/16; reveal <=1/32 variation; joint gap <0.010; faces flush <=0.010.",
        "Do not glue or permanently nail now. The cured parts return to this proven fit before final fastening.",
    )
    story.append(PageBreak())

    operation_page(
        story,
        s,
        "04 of 07",
        "Fit and label the backband.",
        "Transfer each length from the work and preserve the 1/4-inch face projection.",
        "12-backband-install",
        "Approved M-202 sample, temporarily fitted casing, selected head language, and labeled matching offcuts.",
        "Fit head and legs, close joints by hand, dry-fit any return, mark future glue lands, label, and remove.",
        "Projection 1/4 +/-1/32; joints <0.010; no exposed end grain; no glue or permanent brads at dry fit.",
        "After full finish cure, glue only band-to-casing edges and joints, then brad at 8-12 inches OC.",
    )
    story.append(PageBreak())

    operation_page(
        story,
        s,
        "05 of 07",
        "Dry-fit optional cap, plinth, and baseboard transitions.",
        "These optional parts must agree with adjacent original millwork.",
        "13-cap-plinth",
        "Field photographs, recorded profile dimensions, completed M-202C head backband, baseboard sample, and selected bottom datum.",
        "Fit any cap atop the completed head backband at 3/4 overhang per end; dry-fit plinths, label masked trim-joint glue faces, and remove.",
        "Cap flat and centered over M-202C; plinth receives the full composition; baseboard butts without notching casing.",
        "When evidence is absent, omit them. Do not glue or permanently nail any optional part before finish cure.",
    )
    story.append(PageBreak())

    operation_page(
        story,
        s,
        "06 of 07",
        "Complete scribes, label, and remove the trim.",
        "Correct the interface while preserving the reveal and visible profile.",
        "14-scribe-corners",
        "Straightedge, compass, block plane, approved relief setup, fitted shims, and matching offcuts.",
        "Relieve proud jambs, shim recesses, scribe corners, dry-fit returns, photograph the accepted fit, then remove; returns stay dry through finish cure.",
        "Full bearing; reveal unchanged; no visible end grain; no relief leaves <1/2-inch sound casing.",
        "Every piece and mating joint must remain labeled. Projection over 1/8 inch is a repair condition.",
    )
    story.append(PageBreak())

    operation_page(
        story,
        s,
        "07 of 07",
        "Plan the permanent fastening sequence.",
        "Mark verified fastener paths now; drive permanent fasteners only after final P120, finish, and full cure.",
        "15-fastener-map",
        "Labeled parts removed; framing and utilities verified; fastener lengths and glue boundaries recorded.",
        "Calculate the actual layer stack and offcut-prove: inner/stop >=3/4 sound jamb, outer >=1 framing, backband >=1/2 casing.",
        "HOLD: no permanent glue or nails until full cure; hold again if no standard fastener length passes without exit or split.",
        "After cure install plinths first, then casing, backband/returns, cap, and stops last; never use nails to close a bad joint.",
    )
    story.append(PageBreak())

    # 19 - finish and release
    page_heading(
        story,
        s,
        "Finish, cure, install | Release",
        "Finish off the opening; permanently fasten only after full cure.",
        "Mandatory order: accepted dry fit, label and remove, final P120, approved finish, full cure, plinths, casing, backband/returns, cap, stops last, then functional QC.",
    )
    story.extend(
        [
            diagram("16-finish-qc"),
            Spacer(1, 5),
            Table(
                [
                    [
                        section_panel(
                            "Mandatory sequence",
                            [
                                Paragraph("&#8226; Dry-fit, photograph, label, and remove every part.", s["QBullet"]),
                                Paragraph("&#8226; Final P120; preserve and mask proven glue faces.", s["QBullet"]),
                                Paragraph("&#8226; Apply approved finish; wait for full cure.", s["QBullet"]),
                                Paragraph("&#8226; Then plinths / casing / band + returns / cap / stops last.", s["QBullet"]),
                            ],
                            s,
                            PALE_BLUE,
                        ),
                        section_panel(
                            "Post-install release",
                            [
                                Paragraph("&#8226; Reveal, joints, plumb, level, and projection pass.", s["QBullet"]),
                                Paragraph("&#8226; Door swings and latches without push or lift.", s["QBullet"]),
                                Paragraph("&#8226; Stop contact is quiet; no springing or rattle.", s["QBullet"]),
                                Paragraph("&#8226; Finish matches the approved room sample.", s["QBullet"]),
                            ],
                            s,
                            PALE_TEAL,
                        ),
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
            Spacer(1, 6),
            Table(
                [
                    [
                        Paragraph("<b>INSPECTED BY</b><br/><br/>________________________", s["QMicro"]),
                        Paragraph("<b>DATE</b><br/><br/>______________", s["QMicro"]),
                        Paragraph("<b>FACE(S)</b><br/><br/>A / B / BOTH", s["QMicro"]),
                        Paragraph("<b>RELEASE</b><br/><br/>PASS / HOLD", s["QMicro"]),
                    ]
                ],
                colWidths=[2.45 * inch, 1.45 * inch, 1.45 * inch, 1.45 * inch],
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
    reader = PdfReader(str(GUIDE_OUT))
    extracted = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert len(reader.pages) == 19, f"Expected 19 guide pages, got {len(reader.pages)}"
    for required in [
        "M-201",
        "M-202",
        "M-203",
        "S4S 4/4",
        "40 dealer BF",
        "no plinth stock",
        "mitered surround",
        "square-butt",
        "Fastener",
        "Final function",
    ]:
        assert required.lower() in extracted.lower(), f"Missing guide term: {required}"
    assert not re.search(r"\b(TODO|TBD|placeholder|insert image)\b", extracted, re.I)
    return len(reader.pages)


def build_drawings() -> int:
    s = styles()
    doc = make_doc(DRAWINGS_OUT, drawing_page_decor, "moulding-drawings")
    sheets = [
        (
            "M-01",
            "Door stop and profile register",
            "03-profile-register",
            "Stop 3/8 x 1-1/4; ease door-side arris 1/16.",
            "Mill as a wide mother blank before ripping.",
            "Fit from the hung and latched door.",
        ),
        (
            "M-02",
            "Side casing elevation and field fit",
            "10-side-casing-fit",
            "Casing 3/4 x 4-1/2; reveal 3/16.",
            "Measure H-L and H-R independently.",
            "Plumb <=1/16; reveal variation <=1/32.",
        ),
        (
            "M-03",
            "Head casing joint options",
            "08-head-joint-options",
            "Match adjacent mitered or square-butt evidence.",
            "Do not mix joint languages on one face.",
            "Joint gap <0.010; faces flush <=0.010.",
        ),
        (
            "M-04",
            "Casing cross section",
            "07-jamb-wall-section",
            "Casing back bears on jamb and wall.",
            "Relieve proud jamb or shim recess continuously.",
            "Preserve at least 1/2-inch sound casing.",
        ),
        (
            "M-05",
            "Backband cross section",
            "03-profile-register",
            "Backband 1 x 1-1/8; face 1/4 proud.",
            "Edge-apply outside the fitted casing.",
            "Projection variation <=1/32.",
        ),
        (
            "M-06",
            "Casing and backband assembly",
            "12-backband-install",
            "M-202C head backband is mandatory.",
            "Dry-fit and label; returns stay dry through finish cure.",
            "After cure: glue band/returns; brads embed >=1/2 in casing.",
        ),
        (
            "M-07",
            "Optional head-cap assembly",
            "13-cap-plinth",
            "Cap 7/8 thick x 1-1/2 deep.",
            "Length = fitted head-backband outside + 1-1/2 total.",
            "Seat atop M-202C; glue masked cap-to-head-band joint after cure.",
        ),
        (
            "M-08",
            "Plinth block and baseboard transition",
            "13-cap-plinth",
            "Plinth width, height, and profile are field values.",
            "After cure install first as casing bottom datum.",
            "No glue to floor/wall; baseboard butts without casing notch.",
        ),
        (
            "M-09",
            "Completed jamb, stop, door, and wall section",
            "07-jamb-wall-section",
            "Jamb is complete and outside fabrication scope.",
            "Stop references the operating door.",
            "Casing reveal is measured from jamb edge.",
        ),
        (
            "M-10",
            "Corner, scribe, and exposed-end conditions",
            "14-scribe-corners",
            "Scribe inside corners without changing reveal.",
            "Dry-fit returns; glue only during post-cure install.",
            "Repair projection >1/8 before trim.",
        ),
        (
            "M-11",
            "Fastener locations and glue boundaries",
            "15-fastener-map",
            "Inner/stop >=3/4 jamb; outer >=1 framing; band >=1/2 casing.",
            "Calculate actual layer stack and prove on matching offcut.",
            "HOLD if no safe standard length; no glue to wall/floor.",
        ),
        (
            "M-12",
            "Finished installed opening QC",
            "16-finish-qc",
            "Inspect reveal, joints, plumb, level, and projection.",
            "Confirm swing, latch, and quiet stop contact.",
            "Finish matches the approved room sample.",
        ),
    ]
    story = []
    for index, (number, title, slug, note_a, note_b, note_c) in enumerate(sheets):
        story.extend(
            [
                Paragraph(f"{number}  {inline(title)}", s["QH1"]),
                Paragraph(
                    f"{PROJECT_NUMBER} | {REVISION} | Scale: NTS | Material: quarter-sawn white oak | Written dimensions control",
                    s["QDeck"],
                ),
                HRFlowable(width="100%", thickness=0.8, color=OAK, spaceBefore=2, spaceAfter=6),
                diagram(slug, 7.0 * inch),
                Spacer(1, 6),
                note_cards(
                    [
                        ("Geometry", note_a, BLUE, PALE_BLUE),
                        ("Method", note_b, TEAL, PALE_TEAL),
                        ("QC / hold", note_c, OAK_DARK, PALE),
                    ],
                    s,
                ),
                Spacer(1, 6),
                Table(
                    [
                        [
                            Paragraph(f"<b>DRAWN</b>  {PROJECT_NUMBER}", s["QMicro"]),
                            Paragraph(f"<b>REVISION</b>  {REVISION_CODE}", s["QMicro"]),
                            Paragraph("<b>FIELD VERIFIED BY</b>  ____________________", s["QMicro"]),
                            Paragraph(f"<b>SHEET</b>  {number}", s["QMicro"]),
                        ]
                    ],
                    colWidths=[1.55 * inch, 1.15 * inch, 2.80 * inch, 1.30 * inch],
                    style=TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                            ("BOX", (0, 0), (-1, -1), 0.55, RULE),
                            ("INNERGRID", (0, 0), (-1, -1), 0.35, RULE),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 6),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                            ("TOPPADDING", (0, 0), (-1, -1), 6),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                        ]
                    ),
                ),
            ]
        )
        if index < len(sheets) - 1:
            story.append(PageBreak())
    doc.build(story)
    reader = PdfReader(str(DRAWINGS_OUT))
    extracted = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert len(reader.pages) == 12, f"Expected 12 drawing sheets, got {len(reader.pages)}"
    for required in ["M-01", "M-12", "Backband", "Fastener", "FIELD VERIFIED"]:
        assert required.lower() in extracted.lower(), f"Missing drawing term: {required}"
    return len(reader.pages)


def _form_header(c, page, title, subtitle):
    c.setTitle("DC-1916-001 Moulding Field Measurement Worksheet")
    c.setAuthor("DC-1916-001 Project Team")
    c.setFillColor(BLUE)
    c.rect(0, 10.42 * inch, 8.5 * inch, 0.58 * inch, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(0.55 * inch, 10.66 * inch, title)
    c.setFont("Helvetica", 8)
    c.drawRightString(7.95 * inch, 10.67 * inch, f"PAGE {page} OF 4")
    c.setFillColor(INK)
    c.setFont("Helvetica", 8)
    c.drawString(0.55 * inch, 10.24 * inch, subtitle)
    c.setStrokeColor(OAK)
    c.line(0.55 * inch, 0.50 * inch, 7.95 * inch, 0.50 * inch)
    c.setFillColor(GRAY)
    c.drawString(0.55 * inch, 0.32 * inch, f"{PROJECT_NUMBER} | {REVISION} | FIELD VERIFY BEFORE MILLING")
    c.drawRightString(7.95 * inch, 0.32 * inch, "Written field values control")


def _box(c, x, y, w, h, title, fill=colors.white):
    c.setStrokeColor(RULE)
    c.setFillColor(fill)
    c.roundRect(x, y, w, h, 4, fill=1, stroke=1)
    c.setFillColor(BLUE)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x + 8, y + h - 14, title)


def _line_field(c, x, y, label, width, value_width=None):
    c.setFillColor(INK)
    c.setFont("Helvetica", 8)
    c.drawString(x, y, label)
    start = x + (value_width if value_width is not None else 95)
    c.setStrokeColor(GRAY)
    c.line(start, y - 2, x + width, y - 2)


def _checkbox(c, x, y, label):
    c.setStrokeColor(GRAY)
    c.rect(x, y - 1, 9, 9, fill=0, stroke=1)
    c.setFillColor(INK)
    c.setFont("Helvetica", 8)
    c.drawString(x + 14, y, label)


def build_worksheet() -> int:
    c = pdfcanvas.Canvas(str(WORKSHEET_OUT), pagesize=letter)

    # Page 1 - field geometry
    _form_header(
        c,
        1,
        "Moulding Field Worksheet - Jamb and Wall",
        "Complete at the installed opening. Attach photographs of every adjacent original trim condition.",
    )
    _box(c, 0.55 * inch, 9.45 * inch, 7.40 * inch, 0.62 * inch, "PROJECT IDENTIFICATION", PALE_BLUE)
    _line_field(c, 0.70 * inch, 9.73 * inch, "Room / opening:", 3.10 * inch)
    _line_field(c, 4.10 * inch, 9.73 * inch, "Measured by:", 2.05 * inch)
    _line_field(c, 6.35 * inch, 9.73 * inch, "Date:", 1.45 * inch, 35)
    _box(c, 0.55 * inch, 8.40 * inch, 7.40 * inch, 0.88 * inch, "DECISION GATES", PALE_TEAL)
    _checkbox(c, 0.72 * inch, 8.86 * inch, "One trimmed face")
    _checkbox(c, 2.05 * inch, 8.86 * inch, "Two trimmed faces")
    _checkbox(c, 3.62 * inch, 8.86 * inch, "Mitered head")
    _checkbox(c, 4.95 * inch, 8.86 * inch, "Square-butt head")
    _checkbox(c, 6.42 * inch, 8.86 * inch, "Decision pending - HOLD")
    _checkbox(c, 0.72 * inch, 8.57 * inch, "Head cap supported")
    _checkbox(c, 2.35 * inch, 8.57 * inch, "Plinth supported")
    _checkbox(c, 3.80 * inch, 8.57 * inch, "No cap / plinth evidence")
    _checkbox(c, 5.75 * inch, 8.57 * inch, "Photos attached")

    _box(c, 0.55 * inch, 5.72 * inch, 3.58 * inch, 2.50 * inch, "COMPLETED JAMB OPENING", colors.white)
    for idx, (label, ypos) in enumerate(
        [
            ("W1 - head width", 7.83),
            ("W2 - middle width", 7.52),
            ("W3 - bottom width", 7.21),
            ("H-L - left height", 6.90),
            ("H-R - right height", 6.59),
            ("Jamb thickness", 6.28),
            ("Wall thickness", 5.97),
        ]
    ):
        _line_field(c, 0.75 * inch, ypos * inch, label + ":", 3.12 * inch, 112)
    _box(c, 4.35 * inch, 5.72 * inch, 3.60 * inch, 2.50 * inch, "JAMB PROJECTION FROM WALL", colors.white)
    for col, x in enumerate((4.58, 6.25)):
        for row, y in enumerate((7.83, 7.43, 7.03)):
            label = f"JP{col * 3 + row + 1}:"
            _line_field(c, x * inch, y * inch, label, 1.40 * inch, 30)
    c.setFont("Helvetica", 7.5)
    c.setFillColor(GRAY)
    c.drawString(4.58 * inch, 6.52 * inch, "Positive = jamb proud; negative = jamb recessed.")
    _line_field(c, 4.58 * inch, 6.18 * inch, "Maximum abrupt change:", 3.02 * inch, 118)
    _line_field(c, 4.58 * inch, 5.89 * inch, "Repair required:", 3.02 * inch, 86)

    _box(c, 0.55 * inch, 3.75 * inch, 7.40 * inch, 1.77 * inch, "WALL, FLOOR, AND FASTENER PATH", PALE_BLUE)
    _line_field(c, 0.75 * inch, 5.12 * inch, "Max wall gap / location:", 3.30 * inch, 112)
    _line_field(c, 4.35 * inch, 5.12 * inch, "Floor L-R difference / datum:", 3.30 * inch, 138)
    _line_field(c, 0.75 * inch, 4.76 * inch, "Baseboard H / T / profile:", 3.30 * inch, 127)
    _line_field(c, 4.35 * inch, 4.76 * inch, "Inside / outside corners:", 3.30 * inch, 120)
    _line_field(c, 0.75 * inch, 4.40 * inch, "Verified framing / actual layer stack:", 3.30 * inch, 180)
    _line_field(c, 4.35 * inch, 4.40 * inch, "Utility scan / risk:", 3.30 * inch, 92)
    _line_field(c, 0.75 * inch, 4.04 * inch, "Substrate repair or shim plan:", 6.85 * inch, 145)

    _box(c, 0.55 * inch, 2.20 * inch, 7.40 * inch, 1.35 * inch, "JAMB GEOMETRY RELEASE - RECORD VALUES, DO NOT CHECK BY EYE", PALE_TEAL)
    _line_field(c, 0.75 * inch, 3.19 * inch, "Left leg plumb: opening plane:", 3.30 * inch, 165)
    _line_field(c, 4.35 * inch, 3.19 * inch, "Left leg plumb: wall-normal plane:", 3.30 * inch, 180)
    _line_field(c, 0.75 * inch, 2.88 * inch, "Right leg plumb: opening plane:", 3.30 * inch, 170)
    _line_field(c, 4.35 * inch, 2.88 * inch, "Right leg plumb: wall-normal plane:", 3.30 * inch, 185)
    _line_field(c, 0.75 * inch, 2.57 * inch, "Head level:", 1.55 * inch, 58)
    _line_field(c, 2.55 * inch, 2.57 * inch, "Diagonal A / B / difference:", 2.85 * inch, 140)
    _line_field(c, 5.63 * inch, 2.57 * inch, "Square status:", 1.98 * inch, 70)
    _line_field(c, 0.75 * inch, 2.29 * inch, "Winding sticks at head / mid / bottom; maximum face twist:", 6.85 * inch, 285)

    _box(c, 0.55 * inch, 0.82 * inch, 7.40 * inch, 1.18 * inch, "FIELD SKETCH / PHOTO REFERENCES", colors.white)
    c.setFont("Helvetica", 7.5)
    c.setFillColor(GRAY)
    c.drawString(0.75 * inch, 1.72 * inch, "Sketch projection, wall humps, floor slope, winding-stick result, baseboard, and corners; reference photo files.")
    for y in (1.43, 1.12):
        c.setStrokeColor(colors.HexColor("#D8D4CC"))
        c.line(0.75 * inch, y * inch, 7.75 * inch, y * inch)
    c.showPage()

    # Page 2 - profile evidence
    _form_header(
        c,
        2,
        "Moulding Field Worksheet - Profile Evidence",
        "Adjacent original work controls every departure from the default rectangular profile family.",
    )
    _box(c, 0.55 * inch, 7.65 * inch, 7.40 * inch, 2.40 * inch, "ADJACENT TRIM REGISTER", PALE_BLUE)
    headers = ["Component", "Existing / intended", "Project default", "Photo / sample ref."]
    widths = [1.45, 2.25, 2.05, 1.35]
    x0, y0 = 0.70, 9.61
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(BLUE)
    xx = x0
    for header, width in zip(headers, widths):
        c.drawString(xx * inch, y0 * inch, header)
        xx += width
    rows = [
        ("Casing T x W", "3/4 x 4-1/2"),
        ("Backband T x W", "1 x 1-1/8"),
        ("Backband projection", "1/4"),
        ("Door stop T x W", "3/8 x 1-1/4"),
        ("Reveal", "3/16"),
        ("Head treatment / M-202C", "M-202C mandatory"),
    ]
    for ridx, (label, default) in enumerate(rows):
        yy = (9.28 - ridx * 0.27) * inch
        c.setFont("Helvetica", 7.7)
        c.setFillColor(INK)
        c.drawString(0.70 * inch, yy, label)
        c.setStrokeColor(GRAY)
        c.line(2.17 * inch, yy - 2, 4.24 * inch, yy - 2)
        c.drawString(4.43 * inch, yy, default)
        c.line(6.42 * inch, yy - 2, 7.70 * inch, yy - 2)

    _box(c, 0.55 * inch, 5.55 * inch, 3.58 * inch, 1.85 * inch, "HEAD CAP OVER M-202C - IF SUPPORTED", PALE_TEAL)
    _line_field(c, 0.75 * inch, 6.98 * inch, "Thickness:", 3.05 * inch, 58)
    _line_field(c, 0.75 * inch, 6.64 * inch, "Depth:", 3.05 * inch, 42)
    _line_field(c, 0.75 * inch, 6.30 * inch, "End overhang:", 3.05 * inch, 77)
    _line_field(c, 0.75 * inch, 5.96 * inch, "Edge profile / chamfer:", 3.05 * inch, 116)
    _checkbox(c, 0.75 * inch, 5.67 * inch, "Approved")
    _checkbox(c, 1.70 * inch, 5.67 * inch, "Omit")
    _box(c, 4.35 * inch, 5.55 * inch, 3.60 * inch, 1.85 * inch, "PLINTH - IF SUPPORTED", PALE_TEAL)
    _line_field(c, 4.58 * inch, 6.98 * inch, "Thickness:", 3.05 * inch, 58)
    _line_field(c, 4.58 * inch, 6.64 * inch, "Width:", 3.05 * inch, 42)
    _line_field(c, 4.58 * inch, 6.30 * inch, "Height:", 3.05 * inch, 42)
    _line_field(c, 4.58 * inch, 5.96 * inch, "Baseboard transition:", 3.05 * inch, 112)
    _checkbox(c, 4.58 * inch, 5.67 * inch, "Approved")
    _checkbox(c, 5.55 * inch, 5.67 * inch, "Omit")

    _box(c, 0.55 * inch, 3.47 * inch, 7.40 * inch, 1.82 * inch, "FACE-SPECIFIC CONFIGURATION", colors.white)
    _line_field(c, 0.75 * inch, 4.88 * inch, "Face A room:", 3.05 * inch, 70)
    _checkbox(c, 0.75 * inch, 4.53 * inch, "Mitered")
    _checkbox(c, 1.65 * inch, 4.53 * inch, "Square-butt")
    _checkbox(c, 2.85 * inch, 4.53 * inch, "Cap")
    _checkbox(c, 3.48 * inch, 4.53 * inch, "Plinth")
    _line_field(c, 0.75 * inch, 4.18 * inch, "Face A bottom datum / H-L / H-R:", 3.05 * inch, 168)
    _line_field(c, 4.35 * inch, 4.88 * inch, "Face B room:", 3.20 * inch, 70)
    _checkbox(c, 4.35 * inch, 4.53 * inch, "Mitered")
    _checkbox(c, 5.25 * inch, 4.53 * inch, "Square-butt")
    _checkbox(c, 6.45 * inch, 4.53 * inch, "Cap")
    _checkbox(c, 7.08 * inch, 4.53 * inch, "Plinth")
    _checkbox(c, 6.45 * inch, 4.28 * inch, "Face B OMIT")
    _line_field(c, 4.35 * inch, 4.02 * inch, "Face B bottom datum / H-L / H-R:", 3.20 * inch, 168)
    _line_field(c, 0.75 * inch, 3.76 * inch, "Backband termination / corner condition:", 6.85 * inch, 208)
    _line_field(c, 0.75 * inch, 3.52 * inch, "Reason for any face-to-face difference:", 6.85 * inch, 190)

    _box(c, 0.55 * inch, 0.82 * inch, 7.40 * inch, 2.35 * inch, "PROFILE SKETCH / RUBBING / SAMPLE NOTES", colors.white)
    c.setFont("Helvetica", 7.5)
    c.setFillColor(GRAY)
    c.drawString(0.75 * inch, 2.82 * inch, "Draw full-size cross sections when possible. Record show face, wall face, projection, edge ease, and grain.")
    for y in (2.55, 2.15, 1.75, 1.35):
        c.setStrokeColor(colors.HexColor("#D8D4CC"))
        c.line(0.75 * inch, y * inch, 7.75 * inch, y * inch)
    c.showPage()

    def draw_face_register(page, face, allow_omit=False):
        _form_header(
            c,
            page,
            f"Moulding Field Worksheet - Face {face} Production Register",
            "Use this face's measured values. Add at least 2 inches total allowance to each production blank.",
        )
        _box(c, 0.55 * inch, 8.87 * inch, 7.40 * inch, 1.18 * inch, f"FACE {face} CONTROL VALUES", PALE_BLUE)
        _line_field(c, 0.72 * inch, 9.67 * inch, f"Face {face} room:", 2.35 * inch, 72)
        if allow_omit:
            _checkbox(c, 3.25 * inch, 9.67 * inch, "FACE B OMIT - no new trim")
        _line_field(c, 5.55 * inch, 9.67 * inch, "Bottom datum:", 2.05 * inch, 78)
        for x, label in [(0.72, "W"), (1.68, "H-L"), (2.75, "H-R"), (3.86, "R"), (4.72, "C"), (5.58, "B"), (6.44, "P")]:
            _line_field(c, x * inch, 9.31 * inch, label + ":", 0.72 * inch, 20)
        _checkbox(c, 0.72 * inch, 8.98 * inch, "Mitered head")
        _checkbox(c, 1.92 * inch, 8.98 * inch, "Square-butt head")
        _checkbox(c, 3.42 * inch, 8.98 * inch, "Cap approved")
        _checkbox(c, 4.62 * inch, 8.98 * inch, "Cap OMIT")
        _checkbox(c, 5.65 * inch, 8.98 * inch, "Plinth approved")
        _checkbox(c, 7.05 * inch, 8.98 * inch, "OMIT")

        _box(c, 0.55 * inch, 4.92 * inch, 7.40 * inch, 3.72 * inch, f"FACE {face} - FULL PRODUCTION LENGTH REGISTER", colors.white)
        headers = ["Part", "Formula / transfer source", "Rough L", "Final L", "Qty", "Pass"]
        xs = [0.72, 1.67, 4.34, 5.18, 6.08, 6.82]
        c.setFont("Helvetica-Bold", 7.5)
        c.setFillColor(BLUE)
        for x, header in zip(xs, headers):
            c.drawString(x * inch, 8.29 * inch, header)
        rows = [
            ("M-201A", "H-L + R (+ C if miter) + 2"),
            ("M-201B", "H-R + R (+ C if miter) + 2"),
            ("M-201C", "W + 2R + 2C + 2"),
            ("M-202A", "Fitted left casing + scheme add + 2"),
            ("M-202B", "Fitted right casing + scheme add + 2"),
            ("M-202C", "MANDATORY: fitted head casing + 2B + 2"),
            ("M-203 head", "Opening set only: between jamb legs + 2"),
            ("M-203 sides", "Opening set only: under fitted head + 2"),
            ("M-204", "Optional: fitted head-band outside + 2P + 2"),
            ("M-205A/B", "Optional: fitted field profile + allowance"),
        ]
        for idx, (part, formula) in enumerate(rows):
            yy = (7.98 - idx * 0.285) * inch
            c.setFont("Helvetica", 7.0)
            c.setFillColor(INK)
            c.drawString(xs[0] * inch, yy, part)
            c.drawString(xs[1] * inch, yy, formula)
            for start, end in [(4.34, 5.04), (5.18, 5.94), (6.08, 6.62), (6.82, 7.52)]:
                c.setStrokeColor(GRAY)
                c.line(start * inch, yy - 2, end * inch, yy - 2)

        _box(c, 0.55 * inch, 2.43 * inch, 7.40 * inch, 2.24 * inch, f"FACE {face} FASTENER LENGTH / OFFCUT PROOF", PALE_TEAL)
        c.setFillColor(GRAY)
        c.setFont("Helvetica", 7)
        c.drawString(0.75 * inch, 4.35 * inch, "Record actual layer stack, selected standard length, resulting embedment, and matching-offcut PASS. HOLD if no safe length.")
        fastener_rows = [
            ("Inner casing stack (>=0.75 jamb):", 4.00, 175),
            ("Outer casing stack (>=1.00 framing):", 3.65, 185),
            ("Backband stack (>=0.50 casing):", 3.30, 165),
            ("Door-stop stack (>=0.75 jamb):", 2.95, 165),
        ]
        for label, yy, label_width in fastener_rows:
            _line_field(c, 0.75 * inch, yy * inch, label, 3.25 * inch, label_width)
            _line_field(c, 4.28 * inch, yy * inch, "Std. L / embed / offcut:", 3.32 * inch, 120)
        _line_field(c, 0.75 * inch, 2.61 * inch, "Framing / utility evidence and test offcut ID:", 6.85 * inch, 222)

    # Page 3 - Face A
    draw_face_register(3, "A")
    _box(c, 0.55 * inch, 0.82 * inch, 7.40 * inch, 1.36 * inch, "FACE A MATERIAL / FINISH RELEASE", colors.white)
    _line_field(c, 0.75 * inch, 1.82 * inch, "Linear footage / >=20% order:", 3.25 * inch, 145)
    _line_field(c, 4.30 * inch, 1.82 * inch, "Finish sample ID:", 3.30 * inch, 95)
    _checkbox(c, 0.75 * inch, 1.43 * inch, "Grain pair approved")
    _checkbox(c, 2.28 * inch, 1.43 * inch, "Profiles approved")
    _checkbox(c, 3.72 * inch, 1.43 * inch, "Finish approved in room")
    _checkbox(c, 5.62 * inch, 1.43 * inch, "Every Face A length complete")
    _line_field(c, 0.75 * inch, 1.06 * inch, "Face A notes:", 6.85 * inch, 72)
    c.showPage()

    # Page 4 - Face B and final release
    draw_face_register(4, "B", allow_omit=True)
    _box(c, 0.55 * inch, 0.82 * inch, 7.40 * inch, 1.36 * inch, "FINAL FIELD RELEASE", colors.white)
    checks = [
        (0.75, 1.84, "Jamb geometry gate complete"),
        (3.03, 1.84, "Cap / plinth resolved"),
        (5.03, 1.84, "Fastener offcuts pass"),
        (0.75, 1.47, "Face A register complete"),
        (3.03, 1.47, "Face B complete or OMIT"),
        (5.03, 1.47, "Photos / samples retained"),
    ]
    for x, y, label in checks:
        _checkbox(c, x * inch, y * inch, label)
    _line_field(c, 0.75 * inch, 1.08 * inch, "Released by / date / PASS or HOLD:", 6.85 * inch, 178)
    c.setFillColor(RED)
    c.setFont("Helvetica-Bold", 6.8)
    c.drawString(0.75 * inch, 0.88 * inch, "Post-cure order: evidence-supported plinths / casing / mandatory backband + returns / cap / stops last.")
    c.showPage()
    c.save()

    reader = PdfReader(str(WORKSHEET_OUT))
    extracted = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert len(reader.pages) == 4, f"Expected 4 worksheet pages, got {len(reader.pages)}"
    for required in [
        "W1",
        "JP6",
        "opening plane",
        "wall-normal plane",
        "Diagonal A / B",
        "Winding sticks",
        "PROFILE EVIDENCE",
        "FACE A - FULL PRODUCTION LENGTH REGISTER",
        "FACE B - FULL PRODUCTION LENGTH REGISTER",
        "FACE B OMIT",
        "FINAL FIELD RELEASE",
    ]:
        assert required.lower() in extracted.lower(), f"Missing worksheet term: {required}"
    return len(reader.pages)


def upsert_markdown_section(text: str, heading: str, body: str) -> str:
    section = f"\n## {heading}\n\n{body.strip()}\n"
    pattern = re.compile(
        rf"\n## {re.escape(heading)}\n.*?(?=\n## |\Z)",
        re.S,
    )
    if pattern.search(text):
        return pattern.sub(section.rstrip(), text).rstrip() + "\n"
    return text.rstrip() + section


def update_build_notes(guide_pages, drawing_pages, worksheet_pages):
    build_report = RELEASE / "DC-1916-001_Build_Report.md"
    if build_report.exists():
        text = build_report.read_text()
        text = upsert_markdown_section(
            text,
            "Detailed custom-moulding companion",
            f"""
- Custom moulding shop manual: {guide_pages} pages
- Rebuilt moulding drawing set: {drawing_pages} sheets
- Rebuilt moulding field worksheet: {worksheet_pages} pages
- Sixteen vector-first diagrams cover field measurement, profiles, calculations, milling, fitting, fastening, and QC.
""",
        )
        build_report.write_text(text)

    visual_qc = ROOT / "build" / "reports" / "visual-qc.md"
    if visual_qc.exists():
        text = visual_qc.read_text()
        text = upsert_markdown_section(
            text,
            "Custom moulding companion",
            f"""
- Manual: {guide_pages} pages; drawing set: {drawing_pages} sheets; worksheet: {worksheet_pages} pages.
- Vector diagrams, tables, headers, footers, page numbers, and field-hold language require rendered-page inspection before release.
""",
        )
        visual_qc.write_text(text)


def build():
    generate_moulding_diagrams()
    RELEASE.mkdir(exist_ok=True)
    guide_pages = build_guide()
    drawing_pages = build_drawings()
    worksheet_pages = build_worksheet()
    shutil.copy2(SOURCE, RELEASE / SOURCE.name)
    update_build_notes(guide_pages, drawing_pages, worksheet_pages)
    print(
        "PASS: built custom moulding package "
        f"({guide_pages}-page guide, {drawing_pages}-sheet drawings, {worksheet_pages}-page worksheet)"
    )


if __name__ == "__main__":
    build()
