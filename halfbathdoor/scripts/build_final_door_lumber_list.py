#!/usr/bin/env python3
"""Build a one-page printable final lumber list for the door."""

from pathlib import Path
import re
import shutil

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output/pdf"
OUTPUT = OUTPUT_DIR / "DC-1916-001_Final_Door_Lumber_List.pdf"
RELEASE = ROOT / "release/DC-1916-001_Final_Door_Lumber_List.pdf"

NAVY = colors.HexColor("#173A56")
TEAL = colors.HexColor("#2E6F73")
OAK = colors.HexColor("#9B6B2F")
INK = colors.HexColor("#20272D")
MID = colors.HexColor("#5F6B73")
RULE = colors.HexColor("#B8C2C8")
PALE_BLUE = colors.HexColor("#EAF1F5")
PALE_TEAL = colors.HexColor("#E8F2F0")
PALE_OAK = colors.HexColor("#F4EFE6")
PALE_GREEN = colors.HexColor("#E9F3EA")
PALE_AMBER = colors.HexColor("#FAF0DA")
PALE_GRAY = colors.HexColor("#F3F5F6")
WHITE = colors.white


ROWS = [
    ("A", "1 x 5-11/16 x 72-3/4", "Rough", "Keep full as emergency panel, face-stock, coupon, setup, or repair reserve.", "RESERVE"),
    ("B", "1 x 4-15/16 x 85", "Rough", "Continuous D-101A hinge-stile show-face layer.", "CRITICAL"),
    ("C", "1 x 5-3/4 x 83-1/8", "Rough", "Continuous D-101B lock-stile show-face layer; usable width offcuts enter the short-face pool.", "CRITICAL"),
    ("D", "1 x 5 x 73-3/4", "Rough", "Four staves for D-101K/L lower panels; conditional short-face billet from the remainder.", "PRIMARY"),
    ("E", "1 x 5-3/4 x 75-1/2", "Rough / knots", "Three clear short-member face billets, subject to the combined E/F knot and defect map.", "MAP FIRST"),
    ("F", "1 x 5-5/8 x 70-3/4", "Rough / knots", "Two clear short-member face billets, subject to the combined E/F knot and defect map.", "MAP FIRST"),
    ("G", "15/16 x 4-1/2 x 75", "S4S", "Four staves for D-101J center panel; size passes, CHK-P-01 still controls clear yield.", "PRIMARY"),
    ("H", "7/8 x 5-3/4 x 79", "Rough", "Three staves for D-101N lower-center panel; eligible tail stock for short faces.", "CRITICAL"),
    ("I", "1-1/2 x 9-1/4 x 84-3/4", "Rough", "D-101B lock-stile core and continuous back-face layer.", "CRITICAL"),
    ("J", "1-5/16 x 7 x 79-1/4", "Rough", "Cores for D-101C/M, D-101F wide stave, and D-101G center muntin.", "CRITICAL"),
    ("K", "1-3/8 x 9-1/2 x 82-1/2", "Rough", "D-101A hinge-stile core and continuous back-face layer.", "CRITICAL"),
    ("L", "1-5/16 x 6 x 80", "Edges cleaned", "Cores for D-101E, both D-101D staves, and the 5-3/4-inch D-101F stave.", "MAP FIRST"),
    ("M", "3/4 x 8-1/4 x 99", "Finished", "Primary D-101H upper-panel stock; tail may provide up to two short-face billets.", "PRIMARY"),
    ("N", "1-3/4 x 11 x 74", "Finished", "Keep full as short-member core, substitution, and repair reserve.", "RESERVE"),
    ("O", "1-3/4 x 11 x 74", "Finished", "Keep full as short-member core, coupon, setup, and repair reserve.", "RESERVE"),
]


def p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text, style)


def build() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    page_w, page_h = landscape(letter)
    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=(page_w, page_h),
        leftMargin=0.38 * inch,
        rightMargin=0.38 * inch,
        topMargin=0.30 * inch,
        bottomMargin=0.30 * inch,
        title="DC-1916-001 Final Door Lumber List",
        author="Jayson Guglietta",
        subject="Printable final lumber assignment for the five-panel half-bath door",
    )

    title = ParagraphStyle(
        "Title",
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=20,
        textColor=NAVY,
        spaceAfter=2,
    )
    deck = ParagraphStyle(
        "Deck",
        fontName="Helvetica",
        fontSize=8.2,
        leading=10,
        textColor=MID,
    )
    body = ParagraphStyle(
        "Body",
        fontName="Helvetica",
        fontSize=7.0,
        leading=8.5,
        textColor=INK,
        alignment=TA_LEFT,
    )
    body_bold = ParagraphStyle(
        "BodyBold",
        parent=body,
        fontName="Helvetica-Bold",
    )
    center = ParagraphStyle(
        "Center",
        parent=body,
        alignment=TA_CENTER,
    )
    center_bold = ParagraphStyle(
        "CenterBold",
        parent=center,
        fontName="Helvetica-Bold",
    )
    callout = ParagraphStyle(
        "Callout",
        fontName="Helvetica-Bold",
        fontSize=8.0,
        leading=9.8,
        textColor=NAVY,
    )
    footer = ParagraphStyle(
        "Footer",
        fontName="Helvetica",
        fontSize=6.6,
        leading=8,
        textColor=MID,
        alignment=TA_CENTER,
    )

    story = [
        p("FINAL DOOR LUMBER LIST", title),
        p(
            "DC-1916-001 | Rev. G / LS-05 | Dimensions are THICKNESS x WIDTH x LENGTH | "
            "Door slab: 23-3/4 x 80-1/2 x 1-3/8 inches",
            deck,
        ),
        Spacer(1, 5),
        Table(
            [[p(
                "<b>DOOR STOCK:</b> Boards A-O only. "
                "The seven new 2-1/2 x 11 x 148-inch rough boards are reserved for the table and are not assigned to this door.",
                callout,
            )]],
            colWidths=[10.24 * inch],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), PALE_GREEN),
                ("BOX", (0, 0), (-1, -1), 0.8, TEAL),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]),
        ),
        Spacer(1, 6),
    ]

    table_data = [[
        p("BOARD", center_bold),
        p("CURRENT SIZE", body_bold),
        p("SURFACE", body_bold),
        p("FINAL DOOR ASSIGNMENT", body_bold),
        p("STATUS", center_bold),
    ]]
    for board, size, surface, use, status in ROWS:
        table_data.append([
            p(board, center_bold),
            p(size, body_bold),
            p(surface, body),
            p(use, body),
            p(status, center_bold),
        ])

    status_backgrounds = {
        "PRIMARY": PALE_GREEN,
        "CRITICAL": PALE_AMBER,
        "MAP FIRST": PALE_OAK,
        "RESERVE": PALE_GRAY,
    }
    table_style = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("BOX", (0, 0), (-1, -1), 0.7, NAVY),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, RULE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3.2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.2),
    ]
    for index, row in enumerate(ROWS, start=1):
        table_style.append((
            "BACKGROUND",
            (0, index),
            (3, index),
            WHITE if index % 2 else PALE_BLUE,
        ))
        table_style.append((
            "BACKGROUND",
            (4, index),
            (4, index),
            status_backgrounds[row[4]],
        ))

    story.extend([
        Table(
            table_data,
            colWidths=[0.42 * inch, 1.65 * inch, 0.90 * inch, 6.05 * inch, 1.22 * inch],
            repeatRows=1,
            style=TableStyle(table_style),
        ),
        Spacer(1, 6),
        KeepTogether([
            Table(
                [[
                    p(
                        "<b>MOULDING:</b> Casing, backband, stop, cap, and other trim stock remain a separate purchase and are not included above.",
                        body,
                    ),
                    p(
                        "<b>SHOP GATE:</b> Verify moisture, straightness, defects, clear yield, and the applicable LS-05 check before crosscutting.",
                        body,
                    ),
                ]],
                colWidths=[5.05 * inch, 5.19 * inch],
                style=TableStyle([
                    ("BACKGROUND", (0, 0), (0, 0), PALE_OAK),
                    ("BACKGROUND", (1, 0), (1, 0), PALE_TEAL),
                    ("BOX", (0, 0), (-1, -1), 0.5, RULE),
                    ("INNERGRID", (0, 0), (-1, -1), 0.3, RULE),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]),
            ),
            Spacer(1, 4),
            p(
                "Use this sheet as a visual lumber-assignment reference. The controlled cut sheets, yield gates, and written dimensions govern fabrication.",
                footer,
            ),
        ]),
    ])

    doc.build(story)
    shutil.copy2(OUTPUT, RELEASE)

    reader = PdfReader(str(OUTPUT))
    assert len(reader.pages) == 1, f"Expected one page, got {len(reader.pages)}"
    text = reader.pages[0].extract_text() or ""
    for term in [
        "FINAL DOOR LUMBER LIST",
        "Boards A-O only",
        "2-1/2 x 11 x 148-inch",
        "reserved for the table",
        "Four staves for D-101J",
        "15/16 x 4-1/2 x 75",
        "MOULDING",
        "SHOP GATE",
    ]:
        assert term.lower() in text.lower(), f"Missing PDF term: {term}"
    for board in "ABCDEFGHIJKLMNO":
        assert re.search(rf"\b{board}\b", text), f"Missing board {board}"

    print(f"PASS: built {OUTPUT.name} (1 page) and release copy")


if __name__ == "__main__":
    build()
