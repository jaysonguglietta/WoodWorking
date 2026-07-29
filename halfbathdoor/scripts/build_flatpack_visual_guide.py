#!/usr/bin/env python3
"""Build a minimal, image-led flat-pack-style door assembly guide."""

from __future__ import annotations

import json
import math
from pathlib import Path

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
SPEC = json.loads((ROOT / "project/specification.yaml").read_text(encoding="utf-8"))
OUT = ROOT / "release/DC-1916-001_Visual_Assembly_Guide.pdf"
GUIDE_PAGES = 23

PAGE_W, PAGE_H = letter
BLUE = colors.HexColor("#173A56")
TEAL = colors.HexColor("#2E6F73")
OAK = colors.HexColor("#B98A52")
OAK_LIGHT = colors.HexColor("#E9D8BF")
INK = colors.HexColor("#20272D")
GRAY = colors.HexColor("#657078")
LIGHT = colors.HexColor("#F4F5F5")
PALE_BLUE = colors.HexColor("#EAF2F5")
PALE_TEAL = colors.HexColor("#EAF4F2")
YELLOW = colors.HexColor("#F2C94C")
RED = colors.HexColor("#B54036")
WHITE = colors.white


def assert_controls() -> None:
    assert SPEC["project"]["revision"] == "Rev. G"
    assert SPEC["opening"]["clear_width"] == 24
    assert SPEC["opening"]["clear_height"] == 81
    assert SPEC["slab"]["finished_width"] == 23.75
    assert SPEC["slab"]["finished_height"] == 80.5
    assert SPEC["slab"]["finished_thickness"] == 1.375
    assert SPEC["frame"]["stile_width"] == 4.25
    assert SPEC["frame"]["rail_shoulder_length"] == 15.25
    assert SPEC["frame"]["bottom_opening_each"] == 6.125
    assert SPEC["panels"]["field_thickness"] == 0.5
    assert SPEC["panels"]["tongue_depth"] == 0.4375
    assert SPEC["groove"]["width"] == 0.25
    assert SPEC["groove"]["depth"] == 0.5
    assert SPEC["panels"]["panel_spacers"]["installed_quantity"] == 20
    assert SPEC["frame"]["construction"]["thickness_slicing_prohibited"] is True


def line(c: canvas.Canvas, x1, y1, x2, y2, color=INK, width=1.4, dash=None):
    c.saveState()
    c.setStrokeColor(color)
    c.setLineWidth(width)
    if dash:
        c.setDash(dash)
    c.line(x1, y1, x2, y2)
    c.restoreState()


def arrow(c: canvas.Canvas, x1, y1, x2, y2, color=OAK, width=4, head=11):
    c.saveState()
    c.setStrokeColor(color)
    c.setFillColor(color)
    c.setLineWidth(width)
    c.setLineCap(1)
    c.line(x1, y1, x2, y2)
    a = math.atan2(y2 - y1, x2 - x1)
    p1 = (x2 - head * math.cos(a - 0.55), y2 - head * math.sin(a - 0.55))
    p2 = (x2 - head * math.cos(a + 0.55), y2 - head * math.sin(a + 0.55))
    c.drawPath(_triangle(c, (x2, y2), p1, p2), fill=1, stroke=0)
    c.restoreState()


def _triangle(c: canvas.Canvas, a, b, d):
    p = c.beginPath()
    p.moveTo(*a)
    p.lineTo(*b)
    p.lineTo(*d)
    p.close()
    return p


def label(c: canvas.Canvas, x, y, text, fill=BLUE, w=None):
    c.saveState()
    c.setFont("Helvetica-Bold", 8.5)
    if w is None:
        w = max(28, c.stringWidth(text, "Helvetica-Bold", 8.5) + 14)
    c.setFillColor(fill)
    c.roundRect(x, y - 7, w, 16, 4, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.drawCentredString(x + w / 2, y - 1.6, text)
    c.restoreState()
    return w


def note(c: canvas.Canvas, x, y, w, title, body, accent=TEAL):
    c.saveState()
    c.setFillColor(WHITE)
    c.setStrokeColor(colors.HexColor("#BCC5C9"))
    c.setLineWidth(1)
    c.roundRect(x, y, w, 55, 8, fill=1, stroke=1)
    c.setFillColor(accent)
    c.roundRect(x, y + 39, w, 16, 8, fill=1, stroke=0)
    c.rect(x, y + 39, w, 8, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 8.2)
    c.drawString(x + 9, y + 44, title.upper())
    c.setFillColor(INK)
    c.setFont("Helvetica", 8.4)
    _wrapped(c, body, x + 9, y + 27, w - 18, 10)
    c.restoreState()


def _wrapped(c: canvas.Canvas, text: str, x, y, width, leading, font="Helvetica", size=8.4):
    words = text.split()
    rows = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if c.stringWidth(trial, font, size) <= width:
            current = trial
        else:
            if current:
                rows.append(current)
            current = word
    if current:
        rows.append(current)
    c.setFont(font, size)
    for row in rows[:3]:
        c.drawString(x, y, row)
        y -= leading


def step_header(c: canvas.Canvas, number: int, title: str, subtitle: str):
    c.setFillColor(LIGHT)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    c.setFillColor(BLUE)
    c.circle(56, PAGE_H - 58, 27, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 25)
    c.drawCentredString(56, PAGE_H - 67, str(number))
    c.setFillColor(BLUE)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(98, PAGE_H - 54, title)
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 10.2)
    c.drawString(99, PAGE_H - 73, subtitle)
    line(c, 40, PAGE_H - 96, PAGE_W - 40, PAGE_H - 96, OAK, 1.5)


def footer(c: canvas.Canvas, page: int):
    line(c, 40, 32, PAGE_W - 40, 32, OAK, 1)
    c.setFillColor(BLUE)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(40, 19, "DC-1916-001  |  VISUAL ASSEMBLY GUIDE  |  REV. G")
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 7.5)
    c.drawRightString(PAGE_W - 40, 19, f"{page:02d} / {GUIDE_PAGES}")


def part(c: canvas.Canvas, x, y, w, h, name, fill=OAK_LIGHT, lw=1.8, radius=1):
    c.saveState()
    c.setFillColor(fill)
    c.setStrokeColor(INK)
    c.setLineWidth(lw)
    c.roundRect(x, y, w, h, radius, fill=1, stroke=1)
    c.restoreState()
    if name:
        label_w = max(28, c.stringWidth(name, "Helvetica-Bold", 8.5) + 14)
        if w < label_w + 10 and h >= label_w + 8:
            c.saveState()
            c.translate(x + w / 2, y + h / 2)
            c.rotate(90)
            label(c, -label_w / 2, 0, name, w=label_w)
            c.restoreState()
        else:
            label(c, x + 5, y + h - 12, name)


def panel(c: canvas.Canvas, x, y, w, h, name):
    c.saveState()
    c.setFillColor(PALE_BLUE)
    c.setStrokeColor(TEAL)
    c.setLineWidth(1.7)
    c.setDash(5, 3)
    c.rect(x, y, w, h, fill=1, stroke=1)
    c.setDash()
    c.setFillColor(TEAL)
    c.setFont("Helvetica-Bold", 10)
    text_w = c.stringWidth(name, "Helvetica-Bold", 10)
    if w < text_w + 8 and h >= text_w + 8:
        c.translate(x + w / 2, y + h / 2)
        c.rotate(90)
        c.drawCentredString(0, -3, name)
    else:
        c.drawCentredString(x + w / 2, y + h / 2 - 3, name)
    c.restoreState()


def dim_h(c: canvas.Canvas, x1, x2, y, text, color=GRAY):
    line(c, x1, y, x2, y, color, 0.8)
    line(c, x1, y - 4, x1, y + 4, color, 0.8)
    line(c, x2, y - 4, x2, y + 4, color, 0.8)
    c.setFillColor(WHITE)
    tw = c.stringWidth(text, "Helvetica-Bold", 8) + 8
    c.rect((x1 + x2 - tw) / 2, y - 6, tw, 12, fill=1, stroke=0)
    c.setFillColor(color)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString((x1 + x2) / 2, y - 2.5, text)


def dim_v(c: canvas.Canvas, x, y1, y2, text, color=GRAY):
    line(c, x, y1, x, y2, color, 0.8)
    line(c, x - 4, y1, x + 4, y1, color, 0.8)
    line(c, x - 4, y2, x + 4, y2, color, 0.8)
    c.saveState()
    c.translate(x - 5, (y1 + y2) / 2)
    c.rotate(90)
    c.setFillColor(WHITE)
    tw = c.stringWidth(text, "Helvetica-Bold", 8) + 8
    c.rect(-tw / 2, -5, tw, 11, fill=1, stroke=0)
    c.setFillColor(color)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(0, -2.5, text)
    c.restoreState()


def check(c: canvas.Canvas, x, y, size=20, good=True):
    c.saveState()
    color = TEAL if good else RED
    c.setStrokeColor(color)
    c.setLineWidth(3.2)
    c.circle(x, y, size / 2, fill=0, stroke=1)
    if good:
        c.line(x - 6, y, x - 1, y - 5)
        c.line(x - 1, y - 5, x + 7, y + 7)
    else:
        c.line(x - 6, y - 6, x + 6, y + 6)
        c.line(x - 6, y + 6, x + 6, y - 6)
    c.restoreState()


def foam(c: canvas.Canvas, x, y, r=5):
    c.saveState()
    c.setFillColor(YELLOW)
    c.setStrokeColor(INK)
    c.setLineWidth(1)
    c.circle(x, y, r, fill=1, stroke=1)
    c.restoreState()


def draw_door(c: canvas.Canvas, x, y, scale, panels=True, labels=True):
    sw = 23.75 * scale
    sh = 80.5 * scale
    stile = 4.25 * scale
    rail_l = 15.25 * scale
    rail_widths = [4, 4, 7, 4, 12]
    openings = [14.25, 14.75, 9.5, 11]
    part(c, x, y, stile, sh, "PART A" if labels else "", fill=OAK_LIGHT)
    part(c, x + sw - stile, y, stile, sh, "PART B" if labels else "", fill=OAK_LIGHT)
    cursor_top = y + sh
    rail_names = ["PART C", "PART M", "PART D", "PART E", "PART F"]
    panel_names = ["PANEL H", "PANEL J", "PANEL N", "PANELS K/L"]
    for idx, rw in enumerate(rail_widths):
        rh = rw * scale
        cursor_top -= rh
        part(c, x + stile, cursor_top, rail_l, rh, rail_names[idx] if labels else "", fill=OAK_LIGHT)
        if idx < 4:
            oh = openings[idx] * scale
            py = cursor_top - oh
            if idx < 3:
                if panels:
                    panel(c, x + stile + 4, py + 4, rail_l - 8, oh - 8, panel_names[idx])
            else:
                if panels:
                    gap = 6.125 * scale
                    mw = 3 * scale
                    panel(c, x + stile + 4, py + 4, gap - 8, oh - 8, "PANEL K")
                    panel(c, x + stile + gap + mw + 4, py + 4, gap - 8, oh - 8, "PANEL L")
                gap = 6.125 * scale
                mw = 3 * scale
                part(c, x + stile + gap, py, mw, oh, "PART G" if labels else "", fill=OAK_LIGHT)
            cursor_top = py
    return sw, sh


def stock_map_header(c: canvas.Canvas, group: str, title: str, subtitle: str):
    c.setFillColor(LIGHT)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    c.setFillColor(OAK)
    c.circle(58, PAGE_H - 58, 29, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(58, PAGE_H - 63, group)
    c.setFillColor(BLUE)
    c.setFont("Helvetica-Bold", 21)
    c.drawString(100, PAGE_H - 53, title)
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 9.5)
    c.drawString(101, PAGE_H - 72, subtitle)
    line(c, 40, PAGE_H - 96, PAGE_W - 40, PAGE_H - 96, OAK, 1.5)
    label(c, 42, PAGE_H - 117, "BOARD = YOUR TAPE LABEL", OAK, 144)
    label(c, 196, PAGE_H - 117, "PART / PANEL = FINISHED DOOR PIECE", BLUE, 211)
    label(c, 417, PAGE_H - 117, "SIZE ORDER: THICK x WIDE x LONG", TEAL, 153)


def board_card(
    c: canvas.Canvas,
    x: float,
    y: float,
    board: str,
    raw_size: str,
    status: str,
    action: str,
    destination: str,
    segments: int = 1,
    knots: bool = False,
    lanes: bool = False,
):
    w, h = 258, 250
    c.saveState()
    c.setFillColor(WHITE)
    c.setStrokeColor(colors.HexColor("#B8C1C6"))
    c.setLineWidth(1.2)
    c.roundRect(x, y, w, h, 9, fill=1, stroke=1)
    c.setFillColor(OAK)
    c.roundRect(x, y + h - 38, w, 38, 9, fill=1, stroke=0)
    c.rect(x, y + h - 38, w, 18, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(x + 13, y + h - 25, f"BOARD {board}")
    c.setFont("Helvetica-Bold", 8.3)
    c.drawRightString(x + w - 13, y + h - 24, raw_size)

    pill_w = max(65, c.stringWidth(status, "Helvetica-Bold", 7.4) + 18)
    c.setFillColor(PALE_TEAL if status not in {"MAP KNOTS", "SURVEY FIRST"} else colors.HexColor("#FFF2D8"))
    c.roundRect(x + 13, y + h - 62, pill_w, 15, 4, fill=1, stroke=0)
    c.setFillColor(TEAL if status not in {"MAP KNOTS", "SURVEY FIRST"} else RED)
    c.setFont("Helvetica-Bold", 7.4)
    c.drawCentredString(x + 13 + pill_w / 2, y + h - 57, status)

    # Simple board map: vertical split = length cuts; horizontal split = rip lanes.
    bar_x, bar_y, bar_w, bar_h = x + 13, y + h - 94, w - 26, 19
    c.setFillColor(OAK_LIGHT)
    c.setStrokeColor(INK)
    c.setLineWidth(1)
    c.roundRect(bar_x, bar_y, bar_w, bar_h, 3, fill=1, stroke=1)
    if lanes:
        line(c, bar_x, bar_y + bar_h / 2, bar_x + bar_w, bar_y + bar_h / 2, BLUE, 1.2)
    elif segments > 1:
        segment_w = bar_w * 0.82 / segments
        for idx in range(1, segments + 1):
            cut_x = bar_x + idx * segment_w
            line(c, cut_x, bar_y, cut_x, bar_y + bar_h, TEAL, 1.2)
        c.setFillColor(colors.HexColor("#E3E6E7"))
        c.rect(bar_x + bar_w * 0.82, bar_y + 1, bar_w * 0.18 - 1, bar_h - 2, fill=1, stroke=0)
    if knots:
        for px in (0.34, 0.68):
            c.setFillColor(RED)
            c.circle(bar_x + bar_w * px, bar_y + bar_h / 2, 3, fill=1, stroke=0)

    c.setFillColor(BLUE)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(x + 13, y + 125, "DO THIS")
    c.setFillColor(INK)
    _wrapped(c, action, x + 13, y + 111, w - 26, 10, size=8.2)
    line(c, x + 13, y + 84, x + w - 13, y + 84, colors.HexColor("#D2D7DA"), 0.8)
    c.setFillColor(TEAL)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(x + 13, y + 68, "BECOMES")
    c.setFillColor(INK)
    _wrapped(c, destination, x + 13, y + 53, w - 26, 10, font="Helvetica-Bold", size=8.1)
    c.restoreState()


def gate_card(c: canvas.Canvas, y: float, number: str, title: str, body: str, accent=TEAL):
    x, w, h = 55, 502, 78
    c.setFillColor(WHITE)
    c.setStrokeColor(colors.HexColor("#BBC4C8"))
    c.setLineWidth(1.1)
    c.roundRect(x, y, w, h, 8, fill=1, stroke=1)
    c.setFillColor(accent)
    c.circle(x + 31, y + h / 2, 20, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(x + 31, y + h / 2 - 5, number)
    c.setFillColor(BLUE)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x + 62, y + h - 25, title)
    c.setFillColor(INK)
    _wrapped(c, body, x + 62, y + h - 43, w - 78, 11, size=8.8)


def page_zero_spare_release(c: canvas.Canvas):
    step_header(c, "!", "Controlled-reserve release order", "Board M adds reserve, but the continuous stile gates still control.")
    gate_card(c, 573, "1", "SURVEY EVERY FULL BOARD A-O",
              "Acclimate and metal scan. Record minimum THICKNESS, WIDTH, clear LENGTH, cup, bow, twist, checks, knots, pith and grain runout.", RED)
    gate_card(c, 477, "2", "PROVE FULL-LENGTH BOARD B + BOARD C",
              'Each must yield one continuous face layer: 5/16" THICK x 4-3/8" WIDE x 81-1/8" LONG after flattening, rest and recheck.')
    gate_card(c, 381, "3", "PROVE FULL-LENGTH BOARD I + BOARD K",
              'Each must retain at least 8-7/8" of clear jointed width for two 4-3/8" lanes plus the 1/8" kerf. Do not rip before this passes.')
    gate_card(c, 285, "4", "PROVE BOARDS M + H; THEN RELEASE PANEL CUTS",
              'M and H must each remain at least 5/8" thick after preparation and rest. Release mapped M/D/G/H billets; keep A intact as reserve.')
    note(c, 55, 180, 502, "Pass before proceeding",
         "Record PASS or HOLD for each gate. If any gate fails, stop and remap before processing another board.", TEAL)
    note(c, 55, 94, 502, "Do not redesign yet",
         "Keep the 23-3/4 x 80-1/2 door geometry. Do not narrow stiles, shorten the slab or splice a layer without a new dressed-yield design.", RED)
    footer(c, 3)
    c.showPage()


def page_staged_milling(c: canvas.Canvas):
    step_header(c, "M", "Mill one board at a time", "Measure after each irreversible operation - not after all stock is processed.")
    note(c, 55, 575, 238, "1 - Map", "Mark defects and the high face. Write the BOARD label on both faces.", OAK)
    note(c, 319, 575, 238, "2 - Flatten", "Flatten one reference face with a jointer or verified sled/carrier.", TEAL)
    note(c, 55, 497, 238, "3 - Rest", "Sticker the piece. Recheck cup, bow and twist before removing more wood.", BLUE)
    note(c, 319, 497, 238, "4 - Plane", "Plane the opposite face parallel in shallow, alternating staged passes.", TEAL)
    note(c, 55, 419, 238, "5 - Joint", "Joint one edge; choose the second edge only after the best yield is visible.", OAK)
    note(c, 319, 419, 238, "6 - Record", "Write actual dressed T x W x clear L. Mark PASS or HOLD before the next board.", RED)

    c.setFillColor(BLUE)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(55, 377, "CRITICAL DRESSED-YIELD RECORD")
    rows = [
        ("BOARD B", '5/16 T x 4-3/8 W x 81-1/8 L', "_____ x _____ x _____", "[ ] PASS  [ ] HOLD"),
        ("BOARD C", '5/16 T x 4-3/8 W x 81-1/8 L', "_____ x _____ x _____", "[ ] PASS  [ ] HOLD"),
        ("BOARD I", '8-7/8 clear W; 7/8 core + 5/16 face', "W _____  L _____", "[ ] PASS  [ ] HOLD"),
        ("BOARD K", '8-7/8 clear W; 7/8 core + 5/16 face', "W _____  L _____", "[ ] PASS  [ ] HOLD"),
        ("BOARD M", '3/4 T x 8-1/4 W x 99 L; finished stock', "T _____  W _____", "[ ] PASS  [ ] HOLD"),
        ("BOARD H", 'at least 5/8 T after flatten + rest', "T _____  W _____", "[ ] PASS  [ ] HOLD"),
        ("BOARDS N/O", '1-3/4 T x 11 W x 74 L; finished white oak', "MOISTURE _____", "[ ] PASS  [ ] HOLD"),
    ]
    x0, y0 = 55, 336
    widths = [72, 210, 123, 97]
    headers = ["STOCK", "PASS CONDITION", "ACTUAL DRESSED YIELD", "DECISION"]
    c.setFillColor(BLUE)
    c.rect(x0, y0, sum(widths), 25, fill=1, stroke=0)
    xx = x0
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 7.2)
    for text, width in zip(headers, widths):
        c.drawCentredString(xx + width / 2, y0 + 8, text)
        xx += width
    y = y0 - 34
    for idx, row in enumerate(rows):
        c.setFillColor(WHITE if idx % 2 == 0 else PALE_BLUE)
        c.setStrokeColor(colors.HexColor("#C7CDD0"))
        c.rect(x0, y, sum(widths), 34, fill=1, stroke=1)
        xx = x0
        for col, (text, width) in enumerate(zip(row, widths)):
            c.setFillColor(BLUE if col == 0 else INK)
            c.setFont("Helvetica-Bold" if col in (0, 3) else "Helvetica", 7.4)
            c.drawCentredString(xx + width / 2, y + 12, text)
            xx += width
        y -= 34
    note(c, 55, 68, 502, "Machine safety and final sizing",
         "Never surface below your machine's safe length/thickness. Use a longer mother piece or verified carrier. Stop at controlled rough size; final-size only after rest and the next gate.", RED)
    footer(c, 4)
    c.showPage()


def page_boards_ad(c: canvas.Canvas):
    stock_map_header(c, "A-D", "Your lumber: boards A-D", "Read each card before making the first crosscut.")
    board_card(c, 42, 408, "A", '1 x 5-11/16 x 72-3/4" CURRENT', "DAMAGE REMOVED",
               'Six inches are already removed. Verify the new end, then keep this board full unless a signed substitution is needed.',
               "Door-only reserve for PANEL H, face stock, coupons or repair.", 1)
    board_card(c, 312, 408, "B", '1 x 4-15/16 x 85"', "KEEP FULL",
               'Joint and plane full length. Do not crosscut. Mill one face layer: 5/16" THICK x 4-3/8" WIDE x 81-1/8" LONG.',
               "PART A hinge-stile show face.", lanes=True)
    board_card(c, 42, 128, "C", '1 x 5-3/4 x 83-1/8"', "KEEP FULL",
               'Joint and plane full length. Do not crosscut. Mill one face layer: 5/16" THICK x 4-3/8" WIDE x 81-1/8" LONG.',
               "PART B lock-stile show face; save the width offcut.", lanes=True)
    board_card(c, 312, 128, "D", '1 x 5 x 73-3/4"', "RELEASE AFTER LONG GATES",
               'Do not cut yet. After B/C/I/K pass, cut 4 billets at 12-13/16". Keep and label the tail.',
               "Two staves for PANEL K + two staves for PANEL L.", 4)
    footer(c, 5)
    c.showPage()


def page_boards_eh(c: canvas.Canvas):
    stock_map_header(c, "E-H", "Your lumber: boards E-H", "Map knots and defects on all four faces before choosing cuts.")
    board_card(c, 42, 408, "E", '1 x 5-3/4 x 75-1/2"', "MAP KNOTS",
               'Keep full while mapping. Mark clear 16-1/4" face billets; do not assign until E and F are mapped together.',
               "Shared short rail/muntin face-billet pool.", knots=True)
    board_card(c, 312, 408, "F", '1 x 5-5/8 x 70-3/4"', "MAP KNOTS",
               'Keep full while mapping. Together E + F must yield at least five clear 16-1/4" face billets.',
               "Shared short rail/muntin face-billet pool.", knots=True)
    board_card(c, 42, 128, "G", 'S4S: 15/16 x 4-1/2 x 75"', "SIZE PASSES",
               'Thickness exceeds the 5/8" minimum by 5/16"; after B/C/I/K + CHK-P-01 pass, cut 4 x 16-9/16".',
               "Four staves for PANEL J; 6-1/4 planning tail after shared reserve.", 4)
    board_card(c, 312, 128, "H", '7/8 x 5-3/4 x 79"', "SURVEY + LONG GATES",
               'Do not cut yet. After B/C/I/K pass, prove at least 5/8" dressed thickness; then cut 3 x 11-5/16".',
               "Three staves for PANEL N; tail may become face stock.", 3)
    footer(c, 6)
    c.showPage()


def page_boards_il(c: canvas.Canvas):
    stock_map_header(c, "I-L", "Your lumber: boards I-L", "Long stile stock stays full; core stock waits for a signed layout.")
    board_card(c, 42, 408, "I", '1-1/2 x 9-1/4 x 84-3/4"', "KEEP FULL",
               'Joint to at least 8-7/8" clear width. Rip two 4-3/8" full-length lanes; plane after ripping.',
               "PART B lock-stile core (7/8) + back face (5/16).", lanes=True)
    board_card(c, 312, 408, "J", '1-5/16 x 7 x 79-1/4"', "LAYOUT FIRST",
               'Prove one clear 6-1/2" width envelope. Then cut 3 x 16-1/4" + 1 x 12" under revised CM-05.',
               "C/M cores + wide F core stave + PART G muntin core.", 4)
    board_card(c, 42, 128, "K", '1-3/8 x 9-1/2 x 82-1/2"', "KEEP FULL",
               'Joint to at least 8-7/8" clear width. Rip two 4-3/8" full-length lanes; plane after ripping.',
               "PART A hinge-stile core (7/8) + back face (5/16).", lanes=True)
    board_card(c, 312, 128, "L", '1-5/16 x 6 x 80" CURRENT', "REVISED MAP",
               'Edges cleaned to 6". Keep full. After revised CM-05, cut 4 billets at 16-1/4".',
               "Both D core staves + E core + 5-3/4 F core; never rip 6-1/2.", 4)
    footer(c, 7)
    c.showPage()


def page_board_m(c: canvas.Canvas):
    stock_map_header(c, "M", "Your lumber: board M", "Finished stock still requires a moisture, straightness, grain, and clear-envelope survey.")
    board_card(c, 170, 365, "M", '3/4 x 8-1/4 x 99" FINISHED', "PRIMARY PANEL STOCK",
               'After B/C/I/K pass, cut 3 x 16-1/16" for PANEL H. Rip each billet above 5.4584" wide, then joint and plane to at least 5/8".',
               "Three staves for PANEL H; tail may yield two 16-1/4 face billets.", 3)
    note(c, 55, 214, 502, "Protect the tail",
         'The three first-stage cuts leave a 48-7/16" planning tail after kerfs and the shared 2" end allowance. Do not cut the two optional face billets until PANEL H passes and FP-05 assigns them.', TEAL)
    note(c, 55, 124, 502, "Board A becomes reserve",
         'Keep BOARD A at its full current 72-3/4" usable length after damage removal. Cut it only under a signed remap if M or another assigned source fails.', OAK)
    footer(c, 8)
    c.showPage()


def page_boards_no(c: canvas.Canvas):
    stock_map_header(c, "N-O", "Your lumber: boards N and O", "These thick, wide boards are valuable reserve; do not cut them just because they are available.")
    board_card(c, 42, 365, "N", '1-3/4 x 11 x 74" FINISHED WHITE OAK', "KEEP FULL - SHORT-CORE RESERVE",
               'Finished dimensions and white-oak species are confirmed. Record moisture, grain, flatness, defects and clear yield. Do not crosscut.',
               "Preferred fallback: short-member 7/8-inch cores.", lanes=True)
    board_card(c, 312, 365, "O", '1-3/4 x 11 x 74" FINISHED WHITE OAK', "KEEP FULL - SHORT-CORE RESERVE",
               'Finished dimensions and white-oak species are confirmed. Record moisture, grain, flatness, defects and clear yield. Do not crosscut.',
               "Preferred fallback: short-member cores, coupons or repair stock.", lanes=True)
    note(c, 55, 214, 502, "Why these do not become stiles",
         'Each board is 74" long. A continuous stile core is 81" and a continuous stile face is 81-1/8"; never splice a stile layer.', RED)
    note(c, 55, 124, 502, "Avoid unnecessary waste",
         'At 1-3/4" thick, planing N/O to a 5/16" face or 5/8" panel billet would discard most of the thickness. Prefer 7/8" short cores under a signed fallback map.', TEAL)
    footer(c, 9)
    c.showPage()


def page_cover(c: canvas.Canvas):
    c.setFillColor(LIGHT)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    c.setFillColor(BLUE)
    c.rect(0, PAGE_H - 195, PAGE_W, 195, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(48, PAGE_H - 48, "DC-1916-001  /  REV. G  /  LS-05")
    c.setFont("Helvetica-Bold", 30)
    c.drawString(48, PAGE_H - 91, "VISUAL BUILD")
    c.drawString(48, PAGE_H - 126, "INSTRUCTIONS")
    c.setFont("Helvetica", 12)
    c.drawString(49, PAGE_H - 154, "Five-panel white-oak door")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(49, PAGE_H - 176, "23-3/4 x 80-1/2 x 1-3/8 in")
    draw_door(c, 372, 72, 7.0, panels=True, labels=False)
    c.setFillColor(BLUE)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(48, 96, "NO RESAWING")
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 9.5)
    c.drawString(48, 78, "Pictures show sequence. Printed dimensions control.")
    footer(c, 1)
    c.showPage()


def page_board_part_reference(c: canvas.Canvas):
    """Front-of-guide orientation map from the owner's A-O labels to door parts."""
    c.setFillColor(LIGHT)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    c.setFillColor(BLUE)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(42, PAGE_H - 53, "Board-to-part visual reference")
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 9.5)
    c.drawString(43, PAGE_H - 72, "Your tape labels A-O mapped to the finished five-panel door.")
    line(c, 40, PAGE_H - 94, PAGE_W - 40, PAGE_H - 94, OAK, 1.5)

    c.setFillColor(colors.HexColor("#FFF3DF"))
    c.setStrokeColor(OAK)
    c.setLineWidth(1)
    c.roundRect(42, 642, 528, 42, 7, fill=1, stroke=1)
    c.setFillColor(RED)
    c.setFont("Helvetica-Bold", 8.8)
    c.drawString(53, 666, "VISUAL REFERENCE ONLY - THIS PAGE DOES NOT AUTHORIZE CUTTING.")
    c.setFillColor(INK)
    c.setFont("Helvetica", 8.1)
    c.drawString(53, 651, "LS-05, RL-02, the signed yield gates, and printed dimensions control every cut.")

    # Door elevation. Each badge gives the finished part first and its source
    # board letter(s) second. Rail and muntin badges identify core stock.
    x, y, scale = 55, 128, 5.25
    sw = 23.75 * scale
    sh = 80.5 * scale
    stile = 4.25 * scale
    rail = 15.25 * scale
    rail_widths = [4, 4, 7, 4, 12]
    openings = [14.25, 14.75, 9.5, 11]
    part(c, x, y, stile, sh, "", fill=OAK_LIGHT, lw=1.4)
    part(c, x + sw - stile, y, stile, sh, "", fill=OAK_LIGHT, lw=1.4)

    def badge(cx: float, cy: float, text: str, width: float, rotate: bool = False):
        c.saveState()
        c.translate(cx, cy)
        if rotate:
            c.rotate(90)
        c.setFillColor(BLUE)
        c.roundRect(-width / 2, -7, width, 15, 4, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 6.6)
        c.drawCentredString(0, -1.7, text)
        c.restoreState()

    badge(x + stile / 2, y + sh / 2, "PART A | BOARDS B + K", 92, rotate=True)
    badge(x + sw - stile / 2, y + sh / 2, "PART B | BOARDS C + I", 92, rotate=True)

    cursor_top = y + sh
    rail_badges = [
        "PART C | CORE J",
        "PART M | CORE J",
        "PART D | CORE L",
        "PART E | CORE L",
        "PART F | CORES J + L",
    ]
    panel_badges = [
        "PANEL H | BOARD M",
        "PANEL J | BOARD G",
        "PANEL N | BOARD H",
    ]
    for idx, rw in enumerate(rail_widths):
        rh = rw * scale
        cursor_top -= rh
        part(c, x + stile, cursor_top, rail, rh, "", fill=OAK_LIGHT, lw=1.2)
        badge(x + stile + rail / 2, cursor_top + rh / 2, rail_badges[idx], 71)
        if idx < 4:
            oh = openings[idx] * scale
            py = cursor_top - oh
            if idx < 3:
                panel(c, x + stile + 3, py + 3, rail - 6, oh - 6, "")
                badge(x + stile + rail / 2, py + oh / 2, panel_badges[idx], 75)
            else:
                gap = 6.125 * scale
                muntin = 3 * scale
                panel(c, x + stile + 3, py + 3, gap - 6, oh - 6, "")
                panel(c, x + stile + gap + muntin + 3, py + 3, gap - 6, oh - 6, "")
                part(c, x + stile + gap, py, muntin, oh, "", fill=OAK_LIGHT, lw=1.2)
                badge(x + stile + gap / 2, py + oh / 2, "K | BOARD D", 48, rotate=True)
                badge(x + stile + gap + muntin / 2, py + oh / 2, "G | CORE J", 48, rotate=True)
                badge(x + stile + gap + muntin + gap / 2, py + oh / 2, "L | BOARD D", 48, rotate=True)
            cursor_top = py

    c.setFillColor(TEAL)
    c.setFont("Helvetica-Bold", 7.2)
    c.drawCentredString(x + sw / 2, 108, "RAIL/MUNTIN BADGES SHOW CORE STOCK")
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 6.9)
    c.drawCentredString(x + sw / 2, 96, "5/16 faces come from the signed M/C/D/E/F/H pool; A is reserve.")

    # Compact A-O shop legend.
    rows = [
        ("A", "72-3/4 current; keep full as door-only reserve"),
        ("B", "PART A hinge-stile show face"),
        ("C", "PART B lock-stile show face; offcut to face pool"),
        ("D", "Lower PANELS K/L; remaining stock to face pool"),
        ("E", "Short rail and muntin face layers"),
        ("F", "Short rail and muntin face layers"),
        ("G", "Center PANEL J"),
        ("H", "Lower-center PANEL N; tail to short-face pool"),
        ("I", "PART B lock-stile core and back face"),
        ("J", "C/M/G cores and PART F 6-1/2-inch core stave"),
        ("K", "PART A hinge-stile core and back face"),
        ("L", "D/E cores and PART F 5-3/4-inch core stave"),
        ("M", "Upper PANEL H; 3/4 x 8-1/4 x 99 finished"),
        ("N", "Keep full; 1-3/4 x 11 x 74 oak; short-core reserve"),
        ("O", "Keep full; 1-3/4 x 11 x 74 oak; short-core reserve"),
    ]
    tx, ty, tw, row_h = 225, 603, 345, 34
    c.setFillColor(BLUE)
    c.roundRect(tx, ty, tw, 25, 6, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(tx + 12, ty + 8, "BOARD")
    c.drawString(tx + 66, ty + 8, "PRIMARY USE")
    for idx, (board, use) in enumerate(rows):
        ry = ty - (idx + 1) * row_h
        c.setFillColor(WHITE if idx % 2 == 0 else PALE_BLUE)
        c.setStrokeColor(colors.HexColor("#C4CDD1"))
        c.rect(tx, ry, tw, row_h, fill=1, stroke=1)
        c.setFillColor(OAK)
        c.circle(tx + 27, ry + row_h / 2, 13, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(tx + 27, ry + row_h / 2 - 3.5, board)
        c.setFillColor(INK)
        _wrapped(c, use, tx + 55, ry + 21, tw - 67, 8, size=7.3)

    footer(c, 2)
    c.showPage()


def page_parts(c: canvas.Canvas):
    step_header(c, 1, "Identify the parts", "Label every member before machining.")
    # Exploded frame
    x0, y0 = 92, 146
    scale = 5.4
    sh = 80.5 * scale
    stile = 4.25 * scale
    rail = 15.25 * scale
    part(c, x0, y0, stile, sh, "PART A")
    part(c, x0 + 300, y0, stile, sh, "PART B")
    top_positions = [y0 + sh - 4 * scale, y0 + sh - 22.25 * scale,
                     y0 + sh - 44 * scale, y0 + sh - 57.5 * scale, y0]
    heights = [4, 4, 7, 4, 12]
    names = ["C", "M", "D", "E", "F"]
    for yy, hh, name in zip(top_positions, heights, names):
        part(c, x0 + 72, yy, rail, hh * scale, f"PART {name}")
        arrow(c, x0 + 61, yy + hh * scale / 2, x0 + 71, yy + hh * scale / 2, OAK, 2.5, 7)
        arrow(c, x0 + 72 + rail + 12, yy + hh * scale / 2, x0 + 72 + rail + 2, yy + hh * scale / 2, OAK, 2.5, 7)
    part(c, x0 + 72 + 6.125 * scale, y0 + 12 * scale, 3 * scale, 11 * scale, "PART G")
    note(c, 55, 66, 238, "Frame", "PART A/B stiles; PART C/M/D/E/F rails; PART G muntin.")
    note(c, 319, 66, 238, "Panels", "PANEL H, J and N are full width. PANEL K/L form the lower pair.", BLUE)
    footer(c, 10)
    c.showPage()


def page_rough_lengths(c: canvas.Canvas):
    step_header(c, 2, "Break down only four boards", "Only after the controlled-reserve long-stock gates pass.")
    cuts = [
        ("M", "3 x 16-1/16", 0.51, TEAL),
        ("D", "4 x 12-13/16", 0.72, TEAL),
        ("G", "4 x 16-9/16", 0.84, TEAL),
        ("H", "3 x 11-5/16", 0.55, TEAL),
    ]
    y = 610
    for name, text, used, color in cuts:
        label(c, 58, y + 8, f"BOARD {name}", OAK, 62)
        c.setFillColor(WHITE)
        c.setStrokeColor(INK)
        c.setLineWidth(1.5)
        c.roundRect(128, y, 374, 25, 4, fill=1, stroke=1)
        c.setFillColor(PALE_TEAL)
        c.roundRect(128, y, 374 * used, 25, 4, fill=1, stroke=0)
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(138, y + 8, text)
        c.setFillColor(GRAY)
        c.setFont("Helvetica", 8)
        c.drawRightString(494, y + 8, "retain tail")
        y -= 67
    c.setFillColor(WHITE)
    c.setStrokeColor(colors.HexColor("#BCC5C9"))
    c.roundRect(55, 184, 502, 132, 8, fill=1, stroke=1)
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(BLUE)
    c.drawString(72, 286, "KEEP FULL LENGTH")
    full = [("B", "85"), ("C", "83-1/8"), ("E", "75-1/2"), ("F", "70-3/4"),
            ("I", "84-3/4"), ("J", "79-1/4"), ("K", "82-1/2"), ("L", "80")]
    for idx, (name, length) in enumerate(full):
        col = idx % 4
        row = idx // 4
        xx = 75 + col * 119
        yy = 244 - row * 43
        label(c, xx, yy, f"BOARD {name}", OAK, 58)
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(xx + 65, yy - 2, length)
    check(c, 77, 139, 24, good=False)
    c.setFillColor(RED)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(99, 135, "Do not make these panel cuts until BOARD B, C, I and K are recorded PASS.")
    footer(c, 11)
    c.showPage()


def page_lamination(c: canvas.Canvas):
    step_header(c, 3, "Make balanced frame blanks", "Plane whole boards or billets. Do not resaw.")
    layers = [
        (510, "SHOW FACE", "5/16", OAK_LIGHT),
        (420, "CORE", "7/8", colors.HexColor("#D2AD78")),
        (330, "BACK FACE", "5/16", OAK_LIGHT),
    ]
    for yy, name, thick, fill in layers:
        part(c, 103, yy, 280, 44, "", fill=fill, lw=1.6)
        label(c, 115, yy + 23, name, BLUE, 88)
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 13)
        c.drawString(410, yy + 16, thick)
        arrow(c, 245, yy - 12, 245, yy - 48, OAK, 3, 9)
    part(c, 103, 184, 280, 92, "", fill=colors.HexColor("#D2AD78"), lw=2)
    c.setFillColor(OAK_LIGHT)
    c.rect(103, 250, 280, 26, fill=1, stroke=0)
    c.rect(103, 184, 280, 26, fill=1, stroke=0)
    c.setStrokeColor(INK)
    c.rect(103, 184, 280, 92, fill=0, stroke=1)
    label(c, 115, 227, "GLUE BLANK", TEAL, 82)
    dim_v(c, 407, 184, 276, "1-1/2")
    arrow(c, 437, 230, 496, 230, OAK, 4, 11)
    part(c, 504, 194, 36, 72, "", fill=colors.HexColor("#D2AD78"), lw=2)
    c.setFillColor(OAK_LIGHT)
    c.rect(504, 253, 36, 13, fill=1, stroke=0)
    c.rect(504, 194, 36, 13, fill=1, stroke=0)
    c.setStrokeColor(INK)
    c.rect(504, 194, 36, 72, fill=0, stroke=1)
    dim_v(c, 560, 194, 266, "1-3/8")
    note(c, 55, 77, 502, "Sequence", "Glue both faces at once. Cure. Rest. Remove 1/16 from each outside face.", TEAL)
    footer(c, 12)
    c.showPage()


def page_frame_cuts(c: canvas.Canvas):
    step_header(c, 4, "Cut the frame members", "Finish internal edges; retain 1/16 perimeter trim stock.")
    rows = [
        ("PART A/B", "STILES", "4-1/4 x 80-1/2", 4.25, 80.5),
        ("PART C/M/E", "RAILS", "4 x 15-1/4", 4, 15.25),
        ("PART D", "LOCK RAIL", "7 x 15-1/4", 7, 15.25),
        ("PART F", "BOTTOM RAIL", "12 x 15-1/4", 12, 15.25),
        ("PART G", "MUNTIN", "3 x 11", 3, 11),
    ]
    y = 603
    for code, name, dims, width, length in rows:
        label(c, 56, y + 13, code, BLUE, 48)
        scale = min(210 / length, 38 / width)
        w = length * scale
        h = width * scale
        part(c, 128, y, w, h, "", fill=OAK_LIGHT, lw=1.5)
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(366, y + 19, name)
        c.setFillColor(TEAL)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(448, y + 17, dims)
        y -= 95
    note(c, 55, 74, 502, "Finished targets", "All frame members finish at 1-3/8 in. Keep each slab end and outer stile edge 1/16 oversize through glue-up.", RED)
    footer(c, 13)
    c.showPage()


def page_panels(c: canvas.Canvas):
    step_header(c, 5, "Make five floating panels", "Grain vertical. Panel field thickness: 1/2 in.")
    items = [
        ("H", "15-7/8 x 15-1/16", 146, 477, 150, 142),
        ("J", "15-7/8 x 15-9/16", 319, 477, 150, 147),
        ("N", "15-7/8 x 10-5/16", 146, 290, 150, 98),
        ("K", "6-7/8 x 11-13/16", 345, 286, 65, 112),
        ("L", "6-7/8 x 11-13/16", 429, 286, 65, 112),
    ]
    for name, dims, x, y, w, h in items:
        panel(c, x, y, w, h, f"PANEL {name}")
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 8.5)
        c.drawCentredString(x + w / 2, y - 14, dims)
        arrow(c, x + w / 2, y + 15, x + w / 2, y + h - 15, TEAL, 2.2, 7)
    # Tongue detail
    part(c, 76, 139, 214, 43, "", fill=OAK_LIGHT, lw=1.5)
    part(c, 290, 151, 53, 19, "", fill=OAK_LIGHT, lw=1.5)
    dim_h(c, 290, 343, 129, "7/16 projection")
    dim_v(c, 362, 151, 170, "7/32")
    c.setFillColor(BLUE)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(76, 196, "CENTERED TONGUE")
    note(c, 373, 119, 184, "Corners", "Remove the 7/16 x 7/16 tongue square at all four corners.", RED)
    footer(c, 14)
    c.showPage()


def page_grooves(c: canvas.Canvas):
    step_header(c, 6, "Cut the panel grooves", "Blue lines show the groove path.")
    x, y, scale = 179, 135, 4.8
    draw_door(c, x, y, scale, panels=False, labels=True)
    sw, sh = 23.75 * scale, 80.5 * scale
    stile = 4.25 * scale
    rail = 15.25 * scale
    # Stile opening segments
    segment_tops = [y + sh - 4 * scale, y + sh - 22.25 * scale,
                    y + sh - 44 * scale, y + sh - 57.5 * scale]
    opening_heights = [14.25, 14.75, 9.5, 11]
    for top, oh in zip(segment_tops, opening_heights):
        line(c, x + stile, top - oh * scale, x + stile, top, TEAL, 3)
        line(c, x + sw - stile, top - oh * scale, x + sw - stile, top, TEAL, 3)
    # Full-width rail grooves
    ys = [y + sh - 4 * scale, y + sh - 18.25 * scale,
          y + sh - 22.25 * scale, y + sh - 37 * scale,
          y + sh - 44 * scale, y + sh - 53.5 * scale]
    for yy in ys:
        line(c, x + stile, yy, x + stile + rail, yy, TEAL, 3)
    # Lower split groove
    yy_top_e = y + sh - 57.5 * scale
    yy_f = y + 12 * scale
    gap = 6.125 * scale
    mw = 3 * scale
    for yy in [yy_top_e, yy_f]:
        line(c, x + stile, yy, x + stile + gap, yy, TEAL, 3)
        line(c, x + stile + gap + mw, yy, x + stile + rail, yy, TEAL, 3)
    line(c, x + stile + gap, yy_f, x + stile + gap, yy_top_e, TEAL, 3)
    line(c, x + stile + gap + mw, yy_f, x + stile + gap + mw, yy_top_e, TEAL, 3)
    note(c, 48, 559, 118, "Groove", "1/4 wide x 1/2 deep.", TEAL)
    note(c, 48, 486, 118, "Datum", "Centerline 11/16 from show face.", BLUE)
    note(c, 435, 559, 129, "Dado", "Through grooves only.", OAK)
    note(c, 435, 486, 129, "Router", "Stopped and split grooves.", RED)
    footer(c, 15)
    c.showPage()


def domino_pair(c: canvas.Canvas, x, y, rail_h, centers, name):
    part(c, x, y, 180, rail_h, name, fill=OAK_LIGHT)
    for cx in centers:
        c.setFillColor(colors.HexColor("#D89C43"))
        c.setStrokeColor(INK)
        c.roundRect(x + cx, y + rail_h / 2 - 5, 20, 10, 5, fill=1, stroke=1)


def page_dominos(c: canvas.Canvas):
    step_header(c, 7, "Cut the Domino joints", "Frame: 10 x 50 mm. Muntin: 6 x 40 mm.")
    # Exploded joint
    part(c, 79, 438, 62, 188, "PART A/B", fill=OAK_LIGHT)
    part(c, 296, 493, 191, 78, "RAIL PART", fill=OAK_LIGHT)
    centers = [515, 548]
    for yy in centers:
        c.setFillColor(colors.HexColor("#D89C43"))
        c.setStrokeColor(INK)
        c.roundRect(187, yy - 6, 56, 12, 6, fill=1, stroke=1)
    arrow(c, 288, 532, 248, 532, OAK, 4, 11)
    arrow(c, 180, 532, 146, 532, OAK, 4, 11)
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(215, 583, "25 mm + 25 mm")
    # Station table
    c.setFillColor(WHITE)
    c.setStrokeColor(colors.HexColor("#BCC5C9"))
    c.roundRect(55, 157, 502, 225, 8, fill=1, stroke=1)
    c.setFillColor(BLUE)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(72, 353, "TENON CENTERS FROM RAIL TOP EDGE")
    rows = [
        ("C", "1-1/4, 2-3/4"),
        ("M", "1-1/4, 2-3/4"),
        ("D", "1-1/4, 3-1/2, 5-3/4"),
        ("E", "1-1/4, 2-3/4"),
        ("F", "1-1/4, 4, 7-1/2, 10-3/4"),
        ("G ends", "1, 2  |  receiver: 7-1/8, 8-1/8"),
    ]
    y = 320
    for code, centers_text in rows:
        label(c, 75, y, f"PART {code}", TEAL, 68)
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(143, y - 2, centers_text)
        y -= 31
    note(c, 55, 75, 243, "Width setting", "First frame mortise tight; remaining mortises medium.", BLUE)
    note(c, 314, 75, 243, "Muntin", "Both on G tight; first receiver tight, second medium.", TEAL)
    footer(c, 16)
    c.showPage()


def page_lower_exploded(c: canvas.Canvas):
    step_header(c, 8, "Build the lower module", "PART E + PART G + PART F capture PANEL K and PANEL L.")
    # Exploded components
    part(c, 130, 581, 352, 42, "PART E", fill=OAK_LIGHT)
    panel(c, 161, 365, 106, 150, "PANEL K")
    panel(c, 345, 365, 106, 150, "PANEL L")
    part(c, 292, 350, 28, 180, "PART G", fill=OAK_LIGHT)
    part(c, 130, 230, 352, 95, "PART F", fill=OAK_LIGHT)
    # Arrows
    arrow(c, 306, 566, 306, 535, OAK, 4, 10)
    arrow(c, 214, 352, 214, 329, OAK, 4, 10)
    arrow(c, 398, 352, 398, 329, OAK, 4, 10)
    # Foam dots on G sides
    for yy in [400, 475]:
        foam(c, 282, yy)
        foam(c, 330, yy)
    c.setFillColor(BLUE)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(58, 473, "2 foam spacers")
    c.drawString(58, 459, "per side groove")
    arrow(c, 147, 461, 276, 438, TEAL, 2.5, 8)
    note(c, 55, 95, 502, "Glue", "Glue only the four 6 x 40 mm Domino joints. Panels remain dry. Use 20 foam spacers total.", RED)
    footer(c, 17)
    c.showPage()


def page_lower_clamp(c: canvas.Canvas):
    step_header(c, 9, "Clamp the lower module", "Close PART E/G/F first. Cure completely.")
    x, y = 126, 222
    part(c, x, y + 308, 360, 42, "PART E")
    part(c, x, y, 360, 96, "PART F")
    panel(c, x + 34, y + 108, 112, 188, "PANEL K")
    panel(c, x + 214, y + 108, 112, 188, "PANEL L")
    part(c, x + 166, y + 96, 28, 212, "PART G")
    # Clamp bars
    for xx in [162, 306, 450]:
        line(c, xx, y - 18, xx, y + 370, INK, 3)
        c.setFillColor(INK)
        c.rect(xx - 16, y - 23, 32, 8, fill=1, stroke=0)
        c.rect(xx - 16, y + 367, 32, 8, fill=1, stroke=0)
    check(c, 91, 620, 25, True)
    c.setFillColor(TEAL)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(112, 616, "Equal 6-1/8 openings")
    note(c, 55, 91, 243, "Square", "Compare diagonals before cure.", TEAL)
    note(c, 314, 91, 243, "Panels", "K and L must move laterally.", BLUE)
    footer(c, 18)
    c.showPage()


def page_full_layout(c: canvas.Canvas):
    step_header(c, 10, "Lay out the full door", "Show faces up. Keep PART B off to the right.")
    x, y, scale = 83, 132, 5.35
    sh = 80.5 * scale
    stile = 4.25 * scale
    rail = 15.25 * scale
    part(c, x, y, stile, sh, "PART A")
    part(c, x + 390, y, stile, sh, "PART B", fill=colors.HexColor("#E0E4E6"))
    rail_data = [
        ("C", y + sh - 4 * scale, 4),
        ("M", y + sh - 22.25 * scale, 4),
        ("D", y + sh - 44 * scale, 7),
    ]
    for name, yy, h in rail_data:
        part(c, x + 76, yy, rail, h * scale, f"PART {name}")
    # Lower cured module
    module_y = y
    part(c, x + 76, module_y + 23 * scale, rail, 4 * scale, "PART E")
    part(c, x + 76, module_y, rail, 12 * scale, "PART F")
    part(c, x + 76 + 6.125 * scale, module_y + 12 * scale, 3 * scale, 11 * scale, "PART G")
    panel(c, x + 80, module_y + 12 * scale + 3, 6.125 * scale - 8, 11 * scale - 6, "PANEL K")
    panel(c, x + 76 + 9.125 * scale + 4, module_y + 12 * scale + 3,
          6.125 * scale - 8, 11 * scale - 6, "PANEL L")
    # Loose panels
    panel(c, x + 92, y + sh - 18.25 * scale + 5, rail - 32, 14.25 * scale - 10, "PANEL H")
    panel(c, x + 92, y + sh - 37 * scale + 5, rail - 32, 14.75 * scale - 10, "PANEL J")
    panel(c, x + 92, y + sh - 53.5 * scale + 4, rail - 32, 9.5 * scale - 8, "PANEL N")
    arrow(c, x + 378, y + sh / 2, x + 303, y + sh / 2, OAK, 5, 13)
    note(c, 55, 75, 502, "Order", "PART C/M/D + PANEL H/J first; lower module second; PANEL N third; PART B last.", BLUE)
    footer(c, 19)
    c.showPage()


def page_load_left(c: canvas.Canvas):
    step_header(c, 11, "Load the hinge stile", "Work from PART A toward the open lock side.")
    x, y = 89, 133
    scale = 5.45
    sh = 80.5 * scale
    stile = 4.25 * scale
    rail = 15.25 * scale
    part(c, x, y, stile, sh, "PART A")
    # rails seated
    rail_info = [("C", 4, 0), ("M", 4, 18.25), ("D", 7, 37)]
    for name, h, top in rail_info:
        yy = y + sh - (top + h) * scale
        part(c, x + stile, yy, rail, h * scale, f"PART {name}")
        arrow(c, x + stile + rail + 55, yy + h * scale / 2,
              x + stile + rail + 4, yy + h * scale / 2, OAK, 4, 11)
    # panels H/J
    panel(c, x + stile + 5, y + sh - 18.25 * scale + 4, rail - 10, 14.25 * scale - 8, "PANEL H")
    panel(c, x + stile + 5, y + sh - 37 * scale + 4, rail - 10, 14.75 * scale - 8, "PANEL J")
    arrow(c, x + stile + rail + 68, y + sh - 11 * scale,
          x + stile + rail + 5, y + sh - 11 * scale, TEAL, 4, 11)
    arrow(c, x + stile + rail + 68, y + sh - 29.5 * scale,
          x + stile + rail + 5, y + sh - 29.5 * scale, TEAL, 4, 11)
    note(c, 55, 71, 502, "Foam first", "Place two approved spacers in each PART A-side panel groove before loading.", TEAL)
    footer(c, 20)
    c.showPage()


def page_load_module(c: canvas.Canvas):
    step_header(c, 12, "Add the lower module and N", "Slide the module into PART A; slide PANEL N through PART D/E.")
    x, y = 76, 131
    scale = 5.25
    sh = 80.5 * scale
    stile = 4.25 * scale
    rail = 15.25 * scale
    part(c, x, y, stile, sh, "PART A")
    # upper fixed frame
    for name, h, top in [("C", 4, 0), ("M", 4, 18.25), ("D", 7, 37)]:
        yy = y + sh - (top + h) * scale
        part(c, x + stile, yy, rail, h * scale, f"PART {name}")
    panel(c, x + stile + 4, y + sh - 18.25 * scale + 3, rail - 8, 14.25 * scale - 6, "PANEL H")
    panel(c, x + stile + 4, y + sh - 37 * scale + 3, rail - 8, 14.75 * scale - 6, "PANEL J")
    # lower module offset right
    mx = x + stile + 104
    part(c, mx, y + 23 * scale, rail, 4 * scale, "PART E")
    part(c, mx, y, rail, 12 * scale, "PART F")
    part(c, mx + 6.125 * scale, y + 12 * scale, 3 * scale, 11 * scale, "PART G")
    panel(c, mx + 4, y + 12 * scale + 4, 6.125 * scale - 8, 11 * scale - 8, "PANEL K")
    panel(c, mx + 9.125 * scale + 4, y + 12 * scale + 4, 6.125 * scale - 8, 11 * scale - 8, "PANEL L")
    arrow(c, mx - 10, y + 11 * scale, x + stile + 5, y + 11 * scale, OAK, 5, 13)
    # N panel above module
    panel(c, mx + 22, y + 28.5 * scale, rail - 44, 9.5 * scale - 8, "PANEL N")
    arrow(c, mx + 5, y + 33.25 * scale, x + stile + 5, y + 33.25 * scale, TEAL, 4, 11)
    note(c, 55, 68, 502, "One module", "Do not add loose duplicate E or F parts.", RED)
    footer(c, 21)
    c.showPage()


def page_close_b(c: canvas.Canvas):
    step_header(c, 13, "Close the lock stile", "Bring PART B in parallel over all rails and panel tongues.")
    x, y, scale = 139, 128, 5.45
    sw = 23.75 * scale
    sh = 80.5 * scale
    draw_door(c, x, y, scale, panels=True, labels=True)
    # Overlay moved B to the right and hide assembled B with pale guide
    c.setFillColor(LIGHT)
    c.setStrokeColor(colors.HexColor("#AAB2B6"))
    c.setDash(5, 3)
    c.rect(x + sw - 4.25 * scale, y, 4.25 * scale, sh, fill=1, stroke=1)
    c.setDash()
    part(c, x + sw + 87, y, 4.25 * scale, sh, "PART B")
    for yy in [y + 75, y + 175, y + 275, y + 375, y + sh - 40]:
        arrow(c, x + sw + 77, yy, x + sw + 8, yy, OAK, 4, 11)
    note(c, 55, 68, 502, "Foam first", "Load all PART B-side spacers before panel tongues enter PART B.", TEAL)
    footer(c, 22)
    c.showPage()


def page_clamp_trim(c: canvas.Canvas):
    step_header(c, 14, "Clamp, cure and trim", "Close shoulders with moderate pressure.")
    x, y, scale = 204, 154, 4.45
    sw, sh = draw_door(c, x, y, scale, panels=True, labels=False)
    # clamps at rail centerlines
    rail_centers = [2, 20.25, 40.5, 55.5, 74.5]
    for station in rail_centers:
        yy = y + sh - station * scale
        line(c, x - 43, yy, x + sw + 43, yy, INK, 2.6)
        c.setFillColor(INK)
        c.rect(x - 48, yy - 9, 10, 18, fill=1, stroke=0)
        c.rect(x + sw + 38, yy - 9, 10, 18, fill=1, stroke=0)
    # diagonal checks
    line(c, x + 5, y + 5, x + sw - 5, y + sh - 5, RED, 1.8, [6, 4])
    line(c, x + 5, y + sh - 5, x + sw - 5, y + 5, RED, 1.8, [6, 4])
    note(c, 50, 555, 126, "Square", "Diagonals within 1/16.", TEAL)
    note(c, 50, 480, 126, "Twist", "Maximum 1/32.", BLUE)
    note(c, 436, 555, 126, "Panels", "All five move.", TEAL)
    note(c, 436, 480, 126, "Cure", "Then trim perimeter.", OAK)
    note(c, 55, 75, 502, "Final size", "Trim the 23-7/8 x 80-5/8 prefit slab to 23-3/4 x 80-1/2 in.", BLUE)
    footer(c, 23)
    c.showPage()


def build() -> None:
    assert_controls()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(OUT), pagesize=letter, pageCompression=1)
    c.setTitle("DC-1916-001 Visual Assembly Guide")
    c.setAuthor("DC-1916-001 Project Team")
    c.setSubject("Rev. G image-led no-resaw cutting and assembly sequence")
    page_cover(c)
    page_board_part_reference(c)
    page_zero_spare_release(c)
    page_staged_milling(c)
    page_boards_ad(c)
    page_boards_eh(c)
    page_boards_il(c)
    page_board_m(c)
    page_boards_no(c)
    page_parts(c)
    page_rough_lengths(c)
    page_lamination(c)
    page_frame_cuts(c)
    page_panels(c)
    page_grooves(c)
    page_dominos(c)
    page_lower_exploded(c)
    page_lower_clamp(c)
    page_full_layout(c)
    page_load_left(c)
    page_load_module(c)
    page_close_b(c)
    page_clamp_trim(c)
    c.save()

    reader = PdfReader(str(OUT))
    text = " ".join((page.extract_text() or "") for page in reader.pages)
    assert len(reader.pages) == GUIDE_PAGES
    for term in [
        "Rev. G",
        "NO RESAWING",
        "23-3/4 x 80-1/2 x 1-3/8",
        "1/4 wide x 1/2 deep",
        "10 x 50 mm",
        "6 x 40 mm",
        "20 foam spacers",
        "Diagonals within 1/16",
        "BOARD A",
        "BOARD M",
        "BOARD N",
        "BOARD O",
        "BOARD L",
        "BOARD = YOUR TAPE LABEL",
        "PART / PANEL = FINISHED DOOR PIECE",
        "Board-to-part visual reference",
        "VISUAL REFERENCE ONLY",
        "PANEL H | BOARD M",
        '1 x 5-11/16 x 72-3/4" CURRENT',
        "Six inches are already removed",
        "PART A | BOARDS B + K",
        "PART B | BOARDS C + I",
        "PART F | CORES J + L",
        "L | BOARD D",
        "SIZE ORDER: THICK x WIDE x LONG",
        '5/16" THICK x 4-3/8" WIDE x 81-1/8" LONG',
        "Controlled-reserve release order",
        "SURVEY EVERY FULL BOARD A-O",
        "PROVE FULL-LENGTH BOARD B + BOARD C",
        "PROVE FULL-LENGTH BOARD I + BOARD K",
        "Mill one board at a time",
        "CRITICAL DRESSED-YIELD RECORD",
        "machine's safe length/thickness",
        "RELEASE AFTER LONG GATES",
        "SURVEY + LONG GATES",
        "KEEP FULL",
        "MAP KNOTS",
        "LAYOUT FIRST",
        '1-3/4 x 11 x 74" FINISHED WHITE OAK',
        "KEEP FULL - SHORT-CORE RESERVE",
    ]:
        assert term.lower() in text.lower(), f"missing controlled term: {term}"
    print(f"PASS: built {OUT.name} ({len(reader.pages)} pages)")


if __name__ == "__main__":
    build()
