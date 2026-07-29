#!/usr/bin/env python3
"""Build the 13-page, image-led five-panel door project-plans booklet."""

from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
SPEC = json.loads((ROOT / "project/specification.yaml").read_text(encoding="utf-8"))
OUT = ROOT / "release/DC-1916-001_Five_Panel_Door_Project_Plans.pdf"
TMP = ROOT / "tmp/pdfs/project-plans-assets"
PAGE_W, PAGE_H = 960, 540
PAGES = 13

GOLD = colors.HexColor("#B77A05")
GOLD_DARK = colors.HexColor("#8E5D00")
INK = colors.HexColor("#3F4143")
MID = colors.HexColor("#737577")
RULE = colors.HexColor("#D9D6CF")
PALE = colors.HexColor("#F4F1EB")
OAK = colors.HexColor("#C49A63")
OAK_LIGHT = colors.HexColor("#E7D3B4")
OAK_DARK = colors.HexColor("#95632E")
PANEL = colors.HexColor("#EFE2CB")
WHITE = colors.white


def controls() -> None:
    assert SPEC["project"]["revision"] == "Rev. G"
    assert SPEC["opening"]["clear_width"] == 24
    assert SPEC["opening"]["clear_height"] == 81
    assert SPEC["slab"]["finished_width"] == 23.75
    assert SPEC["slab"]["finished_height"] == 80.5
    assert SPEC["slab"]["finished_thickness"] == 1.375
    assert SPEC["groove"]["width"] == 0.25
    assert SPEC["groove"]["depth"] == 0.5
    assert SPEC["panels"]["tongue_depth"] == 0.4375
    assert SPEC["frame"]["construction"]["thickness_slicing_prohibited"] is True
    assert len(SPEC["components"]) == 13
    stock = json.loads((ROOT / "project/labeled-stock-plan.json").read_text(encoding="utf-8"))
    board_g = next(row for row in stock["inventory"] if row["label"] == "G")
    assert board_g["thickness"] == 0.9375
    assert board_g["width"] == 4.5
    assert board_g["length"] == 75


def rule(c: canvas.Canvas, y: float, x1: float = 44, x2: float = PAGE_W - 44) -> None:
    c.setStrokeColor(RULE)
    c.setLineWidth(0.8)
    c.line(x1, y, x2, y)


def footer(c: canvas.Canvas, page: int) -> None:
    rule(c, 28)
    c.setFont("Helvetica", 7.2)
    c.setFillColor(MID)
    c.drawString(44, 15, "DC-1916-001  •  REV. G / LS-05  •  FIVE-PANEL WHITE OAK DOOR")
    c.drawRightString(PAGE_W - 44, 15, f"{page:02d} / {PAGES:02d}")


def title(c: canvas.Canvas, text: str, page: int, subtitle: str | None = None) -> None:
    rule(c, PAGE_H - 37)
    c.setFillColor(GOLD)
    c.setFont("Times-Roman", 38 if len(text) < 25 else 34)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 91, text)
    if subtitle:
        c.setFillColor(MID)
        c.setFont("Helvetica", 9.5)
        c.drawCentredString(PAGE_W / 2, PAGE_H - 112, subtitle.upper())
    rule(c, PAGE_H - 126)
    footer(c, page)


def wrap(c: canvas.Canvas, text: str, x: float, y: float, width: float,
         font: str = "Times-Roman", size: float = 16, leading: float = 21,
         color=INK, max_lines: int | None = None) -> float:
    words = text.split()
    rows: list[str] = []
    row = ""
    for word in words:
        trial = f"{row} {word}".strip()
        if stringWidth(trial, font, size) <= width:
            row = trial
        else:
            if row:
                rows.append(row)
            row = word
    if row:
        rows.append(row)
    if max_lines is not None:
        rows = rows[:max_lines]
    c.setFont(font, size)
    c.setFillColor(color)
    for item in rows:
        c.drawString(x, y, item)
        y -= leading
    return y


def bullets(c: canvas.Canvas, items: list[str], x: float = 62, y: float = 365,
            width: float = 325, size: float = 15.2, leading: float = 19.2) -> None:
    for item in items:
        c.setFillColor(GOLD)
        c.circle(x, y + 4, 2.6, fill=1, stroke=0)
        y = wrap(c, item, x + 15, y, width - 15, "Times-Roman", size, leading, INK)
        y -= 15


def label(c: canvas.Canvas, x: float, y: float, text: str, size: float = 8.5,
          fill=GOLD_DARK) -> None:
    w = stringWidth(text, "Helvetica-Bold", size) + 14
    c.setFillColor(fill)
    c.roundRect(x, y - 7, w, 16, 3, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", size)
    c.drawString(x + 7, y - 2, text)


def dim_h(c: canvas.Canvas, x1: float, x2: float, y: float, text: str) -> None:
    c.saveState()
    c.setStrokeColor(INK)
    c.setFillColor(INK)
    c.setLineWidth(0.8)
    c.line(x1, y, x2, y)
    c.line(x1, y - 6, x1, y + 6)
    c.line(x2, y - 6, x2, y + 6)
    for x, direction in ((x1, 1), (x2, -1)):
        p = c.beginPath()
        p.moveTo(x, y)
        p.lineTo(x + 7 * direction, y + 3)
        p.lineTo(x + 7 * direction, y - 3)
        p.close()
        c.drawPath(p, fill=1, stroke=0)
    tw = stringWidth(text, "Helvetica-Bold", 9) + 10
    c.setFillColor(WHITE)
    c.rect((x1 + x2 - tw) / 2, y - 7, tw, 14, fill=1, stroke=0)
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString((x1 + x2) / 2, y - 3, text)
    c.restoreState()


def dim_v(c: canvas.Canvas, x: float, y1: float, y2: float, text: str) -> None:
    c.saveState()
    c.setStrokeColor(INK)
    c.setFillColor(INK)
    c.setLineWidth(0.8)
    c.line(x, y1, x, y2)
    c.line(x - 6, y1, x + 6, y1)
    c.line(x - 6, y2, x + 6, y2)
    for y, direction in ((y1, 1), (y2, -1)):
        p = c.beginPath()
        p.moveTo(x, y)
        p.lineTo(x + 3, y + 7 * direction)
        p.lineTo(x - 3, y + 7 * direction)
        p.close()
        c.drawPath(p, fill=1, stroke=0)
    c.translate(x - 8, (y1 + y2) / 2)
    c.rotate(90)
    tw = stringWidth(text, "Helvetica-Bold", 9) + 10
    c.setFillColor(WHITE)
    c.rect(-tw / 2, -7, tw, 14, fill=1, stroke=0)
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(0, -3, text)
    c.restoreState()


def crop_asset(name: str, crop=(0, 74, 1600, 1010)) -> Path:
    source = ROOT / "cabinetmakers-guide/renderings" / name
    TMP.mkdir(parents=True, exist_ok=True)
    target = TMP / f"{source.stem}-crop.png"
    with Image.open(source) as image:
        x1, y1, x2, y2 = crop
        x2 = min(x2, image.width)
        y2 = min(y2, image.height)
        image.crop((x1, y1, x2, y2)).save(target)
    return target


def place_image(c: canvas.Canvas, path: Path, x: float, y: float, w: float, h: float,
                contain: bool = True) -> None:
    with Image.open(path) as image:
        iw, ih = image.size
    if contain:
        scale = min(w / iw, h / ih)
        dw, dh = iw * scale, ih * scale
        x += (w - dw) / 2
        y += (h - dh) / 2
    else:
        dw, dh = w, h
    c.drawImage(ImageReader(str(path)), x, y, dw, dh, preserveAspectRatio=False,
                mask="auto")


def door_geometry(x: float, y: float, scale: float):
    stile = 4.25 * scale
    inner = 15.25 * scale
    widths = [12, 4, 7, 4, 4]  # bottom through top
    openings = [11, 9.5, 14.75, 14.25]
    return stile, inner, widths, openings


def draw_door(c: canvas.Canvas, x: float, y: float, scale: float,
              exploded: bool = False, part_labels: bool = False) -> tuple[float, float]:
    sw, sh = 23.75 * scale, 80.5 * scale
    stile, inner, rails, openings = door_geometry(x, y, scale)
    c.saveState()
    c.setStrokeColor(OAK_DARK)
    c.setLineWidth(1.2)
    gap = 12 if exploded else 0
    # Stiles
    c.setFillColor(OAK)
    c.rect(x - gap, y, stile, sh, fill=1, stroke=1)
    c.rect(x + sw - stile + gap, y, stile, sh, fill=1, stroke=1)
    if part_labels:
        label(c, x - gap + 4, y + sh - 15, "D-101A", 7.5)
        label(c, x + sw - stile + gap + 4, y + sh - 15, "D-101B", 7.5)
    current = y
    rail_ids = ["D-101F", "D-101E", "D-101D", "D-101M", "D-101C"]
    for idx, rw in enumerate(rails):
        rh = rw * scale
        ry = current + (idx * gap * 0.25 if exploded else 0)
        c.setFillColor(OAK_LIGHT if idx % 2 else OAK)
        c.rect(x + stile, ry, inner, rh, fill=1, stroke=1)
        if part_labels:
            label(c, x + stile + 5, ry + rh / 2, rail_ids[idx], 7.2)
        current += rh
        if idx < len(openings):
            oh = openings[idx] * scale
            if idx == 0:
                mw = 3 * scale
                pw = 6.125 * scale
                c.setFillColor(PANEL)
                c.rect(x + stile, current, pw, oh, fill=1, stroke=1)
                c.rect(x + stile + pw + mw, current, pw, oh, fill=1, stroke=1)
                c.setFillColor(OAK_LIGHT)
                c.rect(x + stile + pw, current, mw, oh, fill=1, stroke=1)
                if part_labels:
                    label(c, x + stile + 2, current + oh / 2, "K", 7)
                    label(c, x + stile + pw + mw + 2, current + oh / 2, "L", 7)
                    label(c, x + stile + pw + 1, current + 8, "G", 7)
            else:
                c.setFillColor(PANEL)
                c.rect(x + stile, current, inner, oh, fill=1, stroke=1)
                if part_labels:
                    pid = ["", "N", "J", "H"][idx]
                    label(c, x + stile + 7, current + oh / 2, pid, 7)
            current += oh
    c.restoreState()
    return sw, sh


def cover(c: canvas.Canvas) -> None:
    c.setFillColor(WHITE)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    rule(c, PAGE_H - 42, 72, PAGE_W - 72)
    c.setFillColor(GOLD)
    c.setFont("Times-Roman", 50)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 104, "Five-Panel White Oak Door")
    c.setFillColor(MID)
    c.setFont("Helvetica", 12)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 132, "PROJECT PLANS  •  DC-1916-001  •  REV. G / LS-05")
    rule(c, PAGE_H - 151, 72, PAGE_W - 72)
    place_image(c, ROOT / "illustrations/renders/cover-finished-door.png",
                305, 30, 350, 350, True)
    c.setFillColor(INK)
    c.setFont("Times-Italic", 12)
    c.drawCentredString(PAGE_W / 2, 23,
                       "A no-resaw, balanced-lamination interior door for a confirmed 24 x 81 jamb")
    c.showPage()


def page_tools(c: canvas.Canvas) -> None:
    title(c, "What You’ll Need", 2, "TOOLS, MATERIALS & FIXED BUILD ENVELOPE")
    bullets(c, [
        "Jointer, planer, table saw with dado stack, bandsaw or jigsaw, and a flat assembly surface.",
        "DF 500 with 10 x 50 mm and 6 x 40 mm loose tenons; router and hinge-mortising setup.",
        "Water-resistant wood glue, rigid cauls, clamps, winding sticks, and 20 foam panel spacers.",
        "Finished target: 23-3/4 x 80-1/2 x 1-3/8 inches. Dimensions read THICKNESS x WIDTH x LENGTH.",
    ], x=58, y=360, width=385, size=14.5, leading=18)
    # compact tool silhouettes
    base_x = 555
    for i, (name, glyph) in enumerate([
        ("MILL", "J/P"), ("JOIN", "DF"), ("GROOVE", "DADO"),
        ("CLAMP", "□"), ("FIT", "1/8")
    ]):
        col, row = i % 2, i // 2
        x, y = base_x + col * 155, 340 - row * 105
        c.setFillColor(PALE)
        c.setStrokeColor(RULE)
        c.roundRect(x, y, 130, 78, 9, fill=1, stroke=1)
        c.setFillColor(GOLD)
        c.setFont("Helvetica-Bold", 23)
        c.drawCentredString(x + 65, y + 40, glyph)
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(x + 65, y + 14, name)
    c.showPage()


def page_parts(c: canvas.Canvas) -> None:
    title(c, "Parts List", 3, "FINISHED COMPONENTS • THICKNESS x WIDTH x LENGTH")
    rows = [(p["id"], p["name"], p["qty"], p["t"], p["w"], p["l"])
            for p in SPEC["components"]]
    x0, y0, row_h = 50, 365, 26
    widths = [58, 145, 28, 52, 56, 62]
    headings = ["PART", "DESCRIPTION", "QTY", "THICK", "WIDTH", "LENGTH"]
    for block in range(2):
        bx = x0 + block * 455
        subset = rows[:7] if block == 0 else rows[7:]
        c.setFillColor(PALE)
        c.rect(bx, y0, sum(widths), 25, fill=1, stroke=0)
        xx = bx
        for heading, width in zip(headings, widths):
            c.setFillColor(GOLD_DARK)
            c.setFont("Helvetica-Bold", 6.8)
            c.drawString(xx + 4, y0 + 8, heading)
            xx += width
        for r, (pid, name, qty, thick, width, length) in enumerate(subset):
            yy = y0 - (r + 1) * row_h
            if r % 2:
                c.setFillColor(colors.HexColor("#FAF8F4"))
                c.rect(bx, yy, sum(widths), row_h, fill=1, stroke=0)
            values = [
                pid, name, str(qty),
                _fraction(thick), _fraction(width), _fraction(length)
            ]
            xx = bx
            for val, cell_w in zip(values, widths):
                c.setFillColor(INK)
                c.setFont("Helvetica-Bold" if val == pid else "Helvetica", 7.1)
                c.drawString(xx + 4, yy + 9, val)
                xx += cell_w
            c.setStrokeColor(RULE)
            c.line(bx, yy, bx + sum(widths), yy)
    c.setFillColor(MID)
    c.setFont("Times-Italic", 11)
    c.drawString(48, 72, "Panel sizes include their tongues. Frame member lengths are finished shoulder-to-shoulder dimensions.")
    c.showPage()


def _fraction(value: float) -> str:
    whole = int(value)
    frac = round((value - whole) * 16)
    names = {0: "", 1: "1/16", 2: "1/8", 3: "3/16", 4: "1/4",
             5: "5/16", 6: "3/8", 7: "7/16", 8: "1/2", 9: "9/16",
             10: "5/8", 11: "11/16", 12: "3/4", 13: "13/16",
             14: "7/8", 15: "15/16"}
    if frac == 16:
        whole += 1
        frac = 0
    return f"{whole}-{names[frac]}" if whole and frac else (str(whole) if whole else names[frac])


def page_overview(c: canvas.Canvas) -> None:
    title(c, "Overview", 4, "FINISHED DOOR ELEVATION")
    x, y, scale = 560, 68, 4.55
    sw, sh = draw_door(c, x, y, scale)
    dim_h(c, x, x + sw, y - 17, '23-3/4"')
    dim_v(c, x + sw + 25, y, y + sh, '80-1/2"')
    c.setFillColor(OAK_LIGHT)
    c.setStrokeColor(OAK_DARK)
    c.rect(815, 176, 26, 182, fill=1, stroke=1)
    dim_h(c, 815, 841, 155, '1-3/8"')
    bullets(c, [
        "The confirmed jamb opening is 24 x 81 inches and is consistent across the opening.",
        "Final fitted slab is 23-3/4 x 80-1/2 x 1-3/8 inches.",
        "Installed gaps: 1/8 inch at the head and both sides; 3/8-inch bottom gap.",
        "Build the prefit assembly at 23-7/8 x 80-5/8, then scribe and fit from the hinge edge and final top.",
    ], x=58, y=360, width=390, size=14.8, leading=18.5)
    c.showPage()


def page_exploded(c: canvas.Canvas) -> None:
    title(c, "Overview Continued", 5, "THIRTEEN FINISHED COMPONENTS")
    bullets(c, [
        "A/B are the full-length stiles; C/M/D/E/F are the rails.",
        "G divides the lower opening. H/J/N/K/L are floating panels.",
        "Dry-fit every frame joint and panel before glue is mixed.",
    ], x=55, y=355, width=330, size=15, leading=19)
    image = crop_asset("02-exploded-door.png")
    place_image(c, image, 390, 48, 520, 370, True)
    c.showPage()


def page_stock(c: canvas.Canvas) -> None:
    title(c, "Stock & Milling Plan", 6, "BOARD LETTERS A–O • RELEASE ONLY AFTER YIELD IS PROVEN")
    groups = [
        ("B + K", "D-101A hinge stile", "continuous 81-inch layers"),
        ("C + I", "D-101B lock stile", "continuous 81-inch layers"),
        ("J + L", "C/M/D/E/F/G cores", "short frame members"),
        ("M + G + H + D", "H/J/N/K/L panels", "G: S4S 15/16 x 4-1/2 x 75"),
        ("E + F + tails", "frame face pool", "signed after long gates"),
        ("A + N + O", "controlled reserve", "keep intact until released"),
    ]
    for i, (boards, use, note) in enumerate(groups):
        col, row = i % 2, i // 2
        x, y = 58 + col * 445, 345 - row * 86
        c.setFillColor(PALE)
        c.setStrokeColor(RULE)
        c.roundRect(x, y, 405, 64, 6, fill=1, stroke=1)
        label(c, x + 12, y + 45, boards, 9)
        c.setFillColor(INK)
        c.setFont("Times-Roman", 15)
        c.drawString(x + 105, y + 39, use)
        c.setFillColor(MID)
        c.setFont("Helvetica", 8.5)
        c.drawString(x + 105, y + 20, note.upper())
    c.setFillColor(GOLD_DARK)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(58, 74, "ROUGH STOCK GATE")
    c.setFillColor(INK)
    c.setFont("Times-Italic", 12)
    c.drawString(58, 55, "G 15/16 thickness/width/length fit PANEL J; CHK-P-01 still controls. Prove B/C/I/K. Mill one board at a time.")
    c.showPage()


def page_lamination(c: canvas.Canvas) -> None:
    title(c, "Balanced Frame Blanks", 7, "NO RESAW • ALL GRAIN RUNS WITH THE MEMBER")
    bullets(c, [
        "Flatten, joint, stage-plane, rest, and recheck every layer before pressing.",
        "Press both face lamellae at once: 5/16 + 7/8 + 5/16 = 1-1/2 inches preglue.",
        "After cure, alternate equal passes from both faces to 1/4 + 7/8 + 1/4 = 1-3/8 inches.",
        "Make and section a same-layup coupon before grooves or Domino mortises.",
    ], x=55, y=355, width=400, size=14.6, leading=18)
    x, y, w = 560, 210, 305
    layers = [(OAK_LIGHT, '5/16" SHOW FACE'), (OAK_DARK, '7/8" CORE'),
              (OAK_LIGHT, '5/16" BACK FACE')]
    heights = [42, 116, 42]
    current = y
    for (fill, text), h in zip(layers, heights):
        c.setFillColor(fill)
        c.setStrokeColor(OAK_DARK)
        c.rect(x, current, w, h, fill=1, stroke=1)
        c.setFillColor(WHITE if fill == OAK_DARK else INK)
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(x + w / 2, current + h / 2 - 3, text)
        current += h + 10
    dim_v(c, x + w + 31, y, current - 10, '1-1/2" PREGLUE')
    c.setFillColor(GOLD)
    c.setFont("Times-Roman", 27)
    c.drawCentredString(x + w / 2, 151, "NO RESAWING")
    c.showPage()


def page_panels(c: canvas.Canvas) -> None:
    title(c, "Panels & Grooves", 8, "FLOATING PANELS • DO NOT GLUE PANEL EDGES")
    panels = [
        ("H", '1/2 x 15-7/8 x 15-1/16"'),
        ("J", '1/2 x 15-7/8 x 15-9/16"'),
        ("N", '1/2 x 15-7/8 x 10-5/16"'),
        ("K / L", '1/2 x 6-7/8 x 11-13/16" each'),
    ]
    for i, (pid, size) in enumerate(panels):
        x, y = 55, 360 - i * 65
        label(c, x, y + 6, pid, 9)
        c.setFillColor(INK)
        c.setFont("Times-Roman", 15)
        c.drawString(x + 80, y, size)
    c.setFillColor(MID)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(55, 85, "ALL DIMENSIONS: THICKNESS x WIDTH x LENGTH")
    # section detail
    x, y = 545, 150
    c.setFillColor(OAK)
    c.setStrokeColor(OAK_DARK)
    c.rect(x, y, 280, 155, fill=1, stroke=1)
    c.setFillColor(WHITE)
    c.rect(x + 116, y + 44, 48, 111, fill=1, stroke=0)
    c.setFillColor(PANEL)
    c.rect(x + 127, y + 71, 26, 84, fill=1, stroke=1)
    dim_h(c, x + 116, x + 164, y + 26, '1/4" GROOVE')
    dim_v(c, x + 95, y + 44, y + 155, '1/2" DEEP')
    c.setFillColor(GOLD)
    for yy in (y + 82, y + 126):
        c.circle(x + 140, yy, 6, fill=1, stroke=0)
    c.setFillColor(INK)
    c.setFont("Times-Roman", 12.5)
    c.drawString(525, 105, 'Tongue: 7/32" thick x 7/16" projection')
    c.drawString(525, 84, 'Use 3/4-inch-long foam panel spacers')
    c.showPage()


def page_domino(c: canvas.Canvas) -> None:
    title(c, "Loose-Tenon Layout", 9, "DF 500 • MORTISE AFTER LAMINATION AND GROOVING")
    bullets(c, [
        "Reference every mortise from the same show face and clearly mark top, hinge, and lock orientation.",
        "Use paired 10 x 50 mm tenons at the principal rail-to-stile joints; use 6 x 40 mm where the controlled schedule calls for them.",
        "Cut the 1/4 x 1/2 groove first. Preserve the specified cutter clearance from both face glue lines.",
        "Rehearse with full-length factory tenons; glue only after the complete dry fit closes without force.",
    ], x=55, y=355, width=380, size=14.5, leading=18)
    place_image(c, crop_asset("05-rail-stile-joint.png"),
                450, 60, 465, 350, True)
    c.showPage()


def page_lower(c: canvas.Canvas) -> None:
    title(c, "Lower Module", 10, "STAGE A • BUILD THE BOTTOM SUBASSEMBLY FIRST")
    bullets(c, [
        "Dry-fit D-101F bottom rail, D-101G muntin, and panels K/L.",
        "Confirm both lower openings are 6-1/8 inches wide before loading panels.",
        "Install foam spacers in the grooves; panels remain unglued and centered.",
        "Glue the muntin-to-bottom-rail joint and keep the module square while it cures.",
    ], x=55, y=355, width=350, size=14.7, leading=18.5)
    place_image(c, crop_asset("06-lower-module.png"), 405, 54, 510, 360, True)
    c.showPage()


def page_assembly(c: canvas.Canvas) -> None:
    title(c, "Door Assembly", 11, "STAGE B • LOAD FROM THE HINGE STILE")
    bullets(c, [
        "Lay D-101A hinge stile flat. Add C/M/D/E rails and the cured lower module in order.",
        "Load H, J, and N with their spacers as each opening closes.",
        "Apply glue only inside the loose-tenon mortises and on frame-joint shoulders—never in panel grooves.",
        "Install D-101B lock stile last, then close the assembly evenly from bottom to top.",
    ], x=55, y=355, width=350, size=14.5, leading=18)
    place_image(c, crop_asset("07-frame-loading.png"), 400, 54, 515, 360, True)
    c.showPage()


def page_clamp(c: canvas.Canvas) -> None:
    title(c, "Clamp, Fit & Hardware", 12, "SQUARE FIRST • FIT FROM CONTROLLED DATUMS")
    bullets(c, [
        "Clamp across every rail line with rigid cauls. Equalize diagonals to within 1/16 inch and hold twist within 1/32 inch.",
        "After cure, surface the prefit assembly to 23-7/8 x 80-5/8 inches.",
        "Scribe the final 23-3/4 x 80-1/2 rectangle from the hinge edge and final top; field-fit the latch edge last.",
        "Mortise hinges and lockset only after the slab fits the jamb with 1/8-inch head/side reveals and a 3/8-inch bottom gap.",
    ], x=55, y=355, width=380, size=14.1, leading=17.5)
    place_image(c, crop_asset("08-clamp-geometry.png"), 455, 64, 460, 345, True)
    c.showPage()


def page_complete(c: canvas.Canvas) -> None:
    title(c, "Complete", 13, "FINAL SURFACING, FINISH & HANGING")
    place_image(c, crop_asset("13-final-release.png"), 45, 55, 530, 355, True)
    bullets(c, [
        "Ease only the edges required for comfort and finish; preserve the fitted perimeter.",
        "Sand uniformly, remove dust, and finish all six faces—including top, bottom, hinge gains, and lock mortise.",
        "Hang on the verified jamb, confirm free swing, then fit strike and stop to the closed door.",
        "Final acceptance: even reveals, 3/8-inch bottom gap, panels floating, latch operating, and no bind.",
    ], x=610, y=350, width=300, size=14.4, leading=18)
    c.showPage()


def build() -> None:
    controls()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(OUT), pagesize=(PAGE_W, PAGE_H),
                      pageCompression=1, invariant=1)
    c.setTitle("DC-1916-001 Five-Panel White Oak Door Project Plans")
    c.setAuthor(SPEC["project"]["copyright_holder"])
    c.setSubject("Thirteen-page image-led construction plan for a five-panel white oak door")
    cover(c)
    page_tools(c)
    page_parts(c)
    page_overview(c)
    page_exploded(c)
    page_stock(c)
    page_lamination(c)
    page_panels(c)
    page_domino(c)
    page_lower(c)
    page_assembly(c)
    page_clamp(c)
    page_complete(c)
    c.save()
    reader = PdfReader(str(OUT))
    assert len(reader.pages) == PAGES
    text = " ".join((page.extract_text() or "") for page in reader.pages)
    for term in [
        "Five-Panel White Oak Door", "Project Plans", "Rev. G", "LS-05",
        "24 x 81", "23-3/4 x 80-1/2 x 1-3/8", "NO RESAWING",
        "D-101A", "D-101L", "1/4 x 1/2", "3/4-inch-long foam",
        "3/8-inch bottom gap",
    ]:
        assert term.lower() in text.lower(), term
    print(f"PASS: {OUT.name} ({PAGES} pages)")


if __name__ == "__main__":
    build()
