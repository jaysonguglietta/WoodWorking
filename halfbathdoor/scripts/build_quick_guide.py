#!/usr/bin/env python3
"""Build the short cut-and-assembly shop guide."""
from pathlib import Path
import html
import re

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate, Frame, Image, PageBreak, PageTemplate, Paragraph,
    Spacer, Table, TableStyle
)
from generate_quick_assembly_diagrams import generate as generate_assembly_diagrams

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "quick-guide/DC-1916-001_Quick_Cut_and_Assembly_Guide.md"
RELEASE = ROOT / "release"
OUT = RELEASE / "DC-1916-001_Quick_Cut_and_Assembly_Guide.pdf"
BLUE = colors.HexColor("#173A56")
TEAL = colors.HexColor("#2E6F73")
OAK = colors.HexColor("#B98A52")
INK = colors.HexColor("#20272D")
PALE = colors.HexColor("#F4F0E8")


def page_decor(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#4E5A60"))
    canvas.drawString(.65*inch, .38*inch, "DC-1916-001 | QUICK CUT AND ASSEMBLY GUIDE | REV. A")
    canvas.drawRightString(7.85*inch, .38*inch, str(canvas.getPageNumber()))
    canvas.setStrokeColor(OAK)
    canvas.line(.65*inch, .52*inch, 7.85*inch, .52*inch)
    canvas.restoreState()


def styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle(name="QTitle", parent=s["Title"], fontName="Helvetica-Bold", fontSize=25, leading=29, textColor=BLUE, spaceAfter=12))
    s.add(ParagraphStyle(name="QH1", parent=s["Heading1"], fontName="Helvetica-Bold", fontSize=18, leading=21, textColor=BLUE, spaceBefore=8, spaceAfter=8))
    s.add(ParagraphStyle(name="QH2", parent=s["Heading2"], fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=TEAL, spaceBefore=8, spaceAfter=5))
    s.add(ParagraphStyle(name="QBody", parent=s["BodyText"], fontName="Helvetica", fontSize=9.5, leading=13, textColor=INK, spaceAfter=5))
    s.add(ParagraphStyle(name="QBullet", parent=s["QBody"], leftIndent=14, firstLineIndent=-7))
    s.add(ParagraphStyle(name="QSmall", parent=s["QBody"], fontSize=7.6, leading=9.2))
    return s


def inline(text):
    text = html.escape(text)
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)


def parse_section(lines, s):
    out, rows = [], []
    def flush():
        nonlocal out, rows
        if rows:
            widths = {
                4: [0.8*inch, 1.55*inch, .38*inch, 2.15*inch],
                5: [0.75*inch, 1.35*inch, .35*inch, 2.15*inch, 2.15*inch],
                3: [2.2*inch, .7*inch, 3.9*inch],
            }.get(len(rows[0]), None)
            data = [[Paragraph(inline(c), s["QSmall"]) for c in row] for row in rows]
            t = Table(data, colWidths=widths, repeatRows=1)
            t.setStyle(TableStyle([
                ("GRID",(0,0),(-1,-1),.4,colors.HexColor("#B7AFA3")),
                ("BACKGROUND",(0,0),(-1,0),PALE),
                ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
                ("VALIGN",(0,0),(-1,-1),"TOP"),
                ("LEFTPADDING",(0,0),(-1,-1),4),
                ("RIGHTPADDING",(0,0),(-1,-1),4),
            ]))
            out += [t, Spacer(1,6)]
            rows=[]
    for line in lines:
        if line.startswith("|"):
            if "---" not in line:
                rows.append([c.strip() for c in line.strip("|").split("|")])
            continue
        flush()
        if line.startswith("## "):
            out.append(Paragraph(inline(line[3:]), s["QH1"]))
        elif line.startswith("- "):
            out.append(Paragraph("• " + inline(line[2:]), s["QBullet"]))
        elif re.match(r"^\d+\. ", line):
            out.append(Paragraph(inline(line), s["QBody"]))
        elif line.strip() and not line.startswith("# "):
            out.append(Paragraph(inline(line), s["QBody"]))
    flush()
    return out


def build():
    generate_assembly_diagrams()
    RELEASE.mkdir(exist_ok=True)
    text = SOURCE.read_text()
    sections = re.split(r"(?=^## )", text, flags=re.M)
    s = styles()
    doc = BaseDocTemplate(str(OUT), pagesize=letter, leftMargin=.68*inch, rightMargin=.68*inch, topMargin=.58*inch, bottomMargin=.65*inch)
    frame = Frame(doc.leftMargin, doc.bottomMargin, letter[0]-doc.leftMargin-doc.rightMargin, letter[1]-doc.topMargin-doc.bottomMargin, id="quick")
    doc.addPageTemplates(PageTemplate(id="quick", frames=frame, onPage=page_decor))
    story = []
    cover = ROOT / "illustrations/renders/cover-finished-door.png"
    story += [
        Image(str(cover), width=3.4*inch, height=5.1*inch),
        Spacer(1, 10),
        Paragraph("Quick Cut and Assembly Guide", s["QTitle"]),
        Paragraph("Building one historically appropriate five-panel quarter-sawn white-oak door with concealed Festool Domino DF 500 joinery.", s["QBody"]),
        Paragraph("<b>24 x 79 x 1-3/8 inches target size - field verify the completed jamb before cutting.</b>", s["QBody"]),
        PageBreak(),
    ]
    intro_groups = [
        sections[1:4],
        sections[4:6],
        sections[6:8],
    ]
    figures = [None, "milling-progression.png", "panel-groove-section.png"]
    for idx, group in enumerate(intro_groups):
        for section in group:
            story += parse_section(section.splitlines(), s)
        if figures[idx]:
            fig = ROOT / "illustrations/technical" / figures[idx]
            if fig.exists():
                story += [Spacer(1,6), Image(str(fig), width=3.0*inch, height=3.0*inch)]
        story.append(PageBreak())

    visual_pages = [
        ("01-parts-map.png", "1. Confirm the complete cut-part set before assembly."),
        ("02-exploded-frame.png", "2. Dry-lay the stiles, rails, and muntin in final order."),
        ("03-bottom-module.png", "3. Assemble the lower rail-muntin module and capture the paired panels."),
        ("04-load-panels.png", "4. Seat rails in D-101A and load all five floating panels."),
        ("05-close-lock-stile.png", "5. Bring D-101B onto all exposed rail tenons together."),
        ("06-clamp-square.png", "6. Clamp at rail locations, compare diagonals, and verify panel movement."),
    ]
    illustration_dir = ROOT / "quick-guide/illustrations"
    for filename, caption in visual_pages:
        story += [
            Paragraph("Visual assembly sequence", s["QH1"]),
            Paragraph(caption, s["QBody"]),
            Image(str(illustration_dir / filename), width=7.0*inch, height=4.67*inch),
            PageBreak(),
        ]

    # Skip the prose-only visual-sequence section because the six illustrated
    # pages above present the same steps at useful scale.
    final_groups = [sections[9:11], sections[11:]]
    for idx, group in enumerate(final_groups):
        for section in group:
            story += parse_section(section.splitlines(), s)
        if idx != len(final_groups)-1:
            story.append(PageBreak())
    doc.build(story)
    reader = PdfReader(str(OUT))
    extracted = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert 11 <= len(reader.pages) <= 14
    assert "D-101A" in extracted and "DF 500" in extracted and "Glue-up" in extracted
    assert not re.search(r"\b(TODO|TBD|placeholder)\b", extracted, re.I)
    (RELEASE / SOURCE.name).write_text(text)
    print(f"PASS: built {OUT.name} ({len(reader.pages)} pages)")


if __name__ == "__main__":
    build()
