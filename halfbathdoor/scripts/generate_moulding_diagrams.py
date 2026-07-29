#!/usr/bin/env python3
"""Generate vector-first diagrams for the custom moulding shop manual."""
from __future__ import annotations

import html
from pathlib import Path

from PIL import Image, ImageDraw

from generate_quick_assembly_diagrams import (
    BLUE,
    GRAY,
    H,
    INK,
    OAK,
    OAK_DARK,
    PALE,
    RED,
    REVISION,
    TEAL,
    W,
    Scene,
    font,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "moulding-guide" / "illustrations"
OUT.mkdir(parents=True, exist_ok=True)

WALL = "#E9E5DE"
JAMB = "#D7B47B"
DOOR = "#C29359"
GREEN = "#547A58"
PALE_BLUE = "#EEF4F7"
PALE_TEAL = "#EDF5F4"


class MouldingScene(Scene):
    """Scene with a moulding-specific title bar and dimension helpers."""

    def __init__(self, number: int, title: str, subtitle: str, badge: str = "FIELD FIT"):
        self.image = Image.new("RGB", (W, H), "white")
        self.draw = ImageDraw.Draw(self.image)
        self.svg = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
            f'<rect width="{W}" height="{H}" fill="white"/>',
        ]
        self.rect(0, 0, W, 92, BLUE, BLUE, 0)
        self.circle(58, 46, 27, OAK, "white", 3)
        self.text(58, 46, str(number), 28, "white", True)
        self.text(105, 34, title, 34, "white", True, "lm")
        self.text(105, 69, subtitle, 20, "#DCE7EC", False, "lm")
        if badge:
            self.rect(1260, 18, 210, 56, TEAL, TEAL, 0)
            self.text(1365, 46, badge, 22, "white", True)
        self.text(
            30,
            975,
            f"DC-1916-001 | {REVISION} | quarter-sawn white oak | written dimensions control",
            17,
            GRAY,
            False,
            "lm",
        )

    def save(self, slug: str):
        self.svg.append("</svg>")
        self.image.save(OUT / f"{slug}.png", dpi=(150, 150))
        (OUT / f"{slug}.svg").write_text("\n".join(self.svg) + "\n")

    def dim_h(self, x1, x2, y, label, color=BLUE, ext1=None, ext2=None):
        if ext1 is not None:
            self.line([(x1, ext1), (x1, y + 8)], color, 2)
        if ext2 is not None:
            self.line([(x2, ext2), (x2, y + 8)], color, 2)
        self.line([(x1, y), (x2, y)], color, 3)
        self.polygon([(x1, y), (x1 + 13, y - 7), (x1 + 13, y + 7)], color, color, 0)
        self.polygon([(x2, y), (x2 - 13, y - 7), (x2 - 13, y + 7)], color, color, 0)
        label_box = self.draw.textbbox((0, 0), label, font=font(19, True))
        label_width = label_box[2] - label_box[0] + 24
        self.rect(
            (x1 + x2) / 2 - label_width / 2,
            y - 31,
            label_width,
            26,
            "white",
            "white",
            0,
        )
        self.text((x1 + x2) / 2, y - 18, label, 19, color, True)

    def dim_v(self, x, y1, y2, label, color=BLUE, ext1=None, ext2=None):
        if ext1 is not None:
            self.line([(ext1, y1), (x - 8, y1)], color, 2)
        if ext2 is not None:
            self.line([(ext2, y2), (x - 8, y2)], color, 2)
        self.line([(x, y1), (x, y2)], color, 3)
        self.polygon([(x, y1), (x - 7, y1 + 13), (x + 7, y1 + 13)], color, color, 0)
        self.polygon([(x, y2), (x - 7, y2 - 13), (x + 7, y2 - 13)], color, color, 0)
        self.rect(x + 10, (y1 + y2) / 2 - 14, 172, 28, "white", "white", 0)
        self.text(x + 18, (y1 + y2) / 2, label, 19, color, True, "lm")

    def callout(self, x, y, label, tx, ty, color=TEAL, align="lm"):
        self.text(x, y, label, 20, color, True, align)
        start_x = x - 8 if align == "rm" else x + 8
        self.arrow(start_x, y + 16, tx, ty, color, 4, 12)

    def step_badge(self, x, y, number, title):
        self.circle(x, y, 24, OAK, BLUE, 3)
        self.text(x, y, str(number), 22, "white", True)
        self.text(x + 38, y, title, 22, BLUE, True, "lm")


def five_panel_door(s: MouldingScene, x, y, w, h):
    stile = w * 0.19
    s.rect(x, y, w, h, DOOR, INK, 3)
    s.rect(x + stile, y + h * 0.05, w - 2 * stile, h * 0.16, "#E8D4AD", OAK_DARK, 2)
    s.rect(x + stile, y + h * 0.28, w - 2 * stile, h * 0.17, "#E8D4AD", OAK_DARK, 2)
    s.rect(x + stile, y + h * 0.54, w - 2 * stile, h * 0.12, "#E8D4AD", OAK_DARK, 2)
    lower_gap = 12
    lower_w = (w - 2 * stile - lower_gap) / 2
    s.rect(x + stile, y + h * 0.75, lower_w, h * 0.20, "#E8D4AD", OAK_DARK, 2)
    s.rect(x + stile + lower_w + lower_gap, y + h * 0.75, lower_w, h * 0.20, "#E8D4AD", OAK_DARK, 2)
    s.circle(x + w - stile / 2, y + h * 0.52, 7, "#C5A24C", INK, 2)


def trim_opening(
    s: MouldingScene,
    x,
    y,
    opening_w,
    opening_h,
    casing=72,
    band=24,
    reveal=8,
    door=True,
    cap=False,
    plinth=False,
):
    wall_x = x - casing - band - 45
    wall_y = max(105, y - casing - band - 45)
    wall_bottom = y + opening_h + 45
    s.rect(
        wall_x,
        wall_y,
        opening_w + 2 * (casing + band + 45),
        wall_bottom - wall_y,
        WALL,
        WALL,
        0,
    )
    if door:
        five_panel_door(s, x + 8, y + 8, opening_w - 16, opening_h - 16)
    # backband, then casing so the hierarchy is clear
    s.rect(x - reveal - casing - band, y - reveal - casing - band, opening_w + 2 * (reveal + casing + band), band, OAK_DARK, INK, 3)
    s.rect(x - reveal - casing - band, y - reveal - casing, band, opening_h + reveal + casing, OAK_DARK, INK, 3)
    s.rect(x + opening_w + reveal + casing, y - reveal - casing, band, opening_h + reveal + casing, OAK_DARK, INK, 3)
    s.rect(x - reveal - casing, y - reveal - casing, opening_w + 2 * (reveal + casing), casing, OAK, INK, 3)
    s.rect(x - reveal - casing, y - reveal, casing, opening_h + reveal, OAK, INK, 3)
    s.rect(x + opening_w + reveal, y - reveal, casing, opening_h + reveal, OAK, INK, 3)
    if cap:
        cap_w = opening_w + 2 * (reveal + casing + band) + 34
        s.rect(x + opening_w / 2 - cap_w / 2, y - reveal - casing - band - 24, cap_w, 24, JAMB, INK, 3)
    if plinth:
        pw, ph = casing + band + 12, 105
        s.rect(x - reveal - casing - band - 6, y + opening_h - ph, pw, ph, JAMB, INK, 3)
        s.rect(x + opening_w + reveal - 6, y + opening_h - ph, pw, ph, JAMB, INK, 3)


def system_overview():
    s = MouldingScene(1, "Installed moulding anatomy", "The default package is restrained, flat, and subordinate to surviving house evidence.", "SYSTEM")
    trim_opening(s, 420, 245, 340, 580, casing=78, band=26, cap=True, plinth=False)
    s.callout(95, 180, "M-204 OPTIONAL CAP", 590, 112, TEAL)
    s.callout(88, 315, "M-202 BACKBAND", 322, 300, BLUE)
    s.callout(88, 430, "M-201 SIDE CASING", 350, 430, TEAL)
    s.callout(88, 755, "BASEBOARD INTERFACE", 315, 790, BLUE)
    s.callout(950, 185, "M-201 HEAD CASING", 630, 145, TEAL, "lm")
    s.callout(950, 335, "3/16 REVEAL", 760, 290, BLUE, "lm")
    s.callout(950, 500, "M-203 STOP (BEHIND SLAB)", 748, 515, TEAL, "lm")
    s.note(
        920,
        610,
        500,
        250,
        "Base release",
        [
            "One trimmed face: 2 legs + 1 head",
            "Three-piece backband on that face",
            "One three-piece stop set total",
            "Duplicate face trim for the other room",
            "Cap and plinth require field evidence",
        ],
    )
    s.save("01-installed-anatomy")


def field_measurements():
    s = MouldingScene(2, "Field measurement gate", "Measure the completed jamb and trim footprint before any production blank is sized.", "HOLD")
    x, y, ow, oh = 465, 165, 430, 650
    s.rect(x - 100, y - 65, ow + 200, oh + 130, WALL, GRAY, 3)
    s.rect(x, y, ow, oh, "white", INK, 5)
    s.line([(x + 18, y + 48), (x + ow - 18, y + oh - 48)], "#9CA8AD", 2)
    s.line([(x + ow - 18, y + 48), (x + 18, y + oh - 48)], "#9CA8AD", 2)
    s.text(x + ow / 2, y + oh / 2 - 45, "DIAGONAL A / B", 18, GRAY, True)
    s.text(x + ow / 2, y - 34, "HEAD LEVEL", 18, RED, True)
    for idx, yy in enumerate((y + 30, y + oh / 2, y + oh - 30), 1):
        s.dim_h(x, x + ow, yy, f"W{idx}", BLUE)
    s.dim_v(x - 110, y, y + oh, "H-L", TEAL, x, x)
    s.dim_v(x + ow + 110, y, y + oh, "H-R", TEAL, x + ow, x + ow)
    for px, py, label in [
        (x - 10, y + 20, "JP1"),
        (x + ow + 10, y + 20, "JP2"),
        (x - 10, y + oh / 2, "JP3"),
        (x + ow + 10, y + oh / 2, "JP4"),
        (x - 10, y + oh - 20, "JP5"),
        (x + ow + 10, y + oh - 20, "JP6"),
    ]:
        s.circle(px, py, 10, OAK, RED, 2)
        label_y = py + 27 if label in {"JP3", "JP4"} else py
        s.text(px + (-18 if px < x else 18), label_y, label, 17, RED, True, "rm" if px < x else "lm")
    s.line([(x - 75, y + 500), (x + ow + 75, y + 475)], TEAL, 7)
    s.text(x + ow / 2, y + 535, "STRAIGHTEDGE: record wall gap", 20, TEAL, True)
    s.note(
        1060,
        150,
        365,
        305,
        "Record before milling",
        [
            "Trimmed faces: one or two",
            "Mitered or square-butt head",
            "Each leg: plumb in both planes",
            "Head level; diagonals A and B",
            "Backband width B and projection",
            "Floor / plinth bottom datum",
        ],
    )
    s.note(
        1060,
        505,
        365,
        270,
        "Stop work",
        [
            "Any leg fails either plumb plane",
            "Head not level; diagonals differ",
            "Winding sticks show face twist",
            "Projection exceeds relief limit",
            "Cap / plinth evidence unresolved",
            "Utility may cross fastener path",
        ],
    )
    s.line([(400, 845), (920, 845)], BLUE, 7)
    s.line([(420, 872), (940, 872)], TEAL, 7)
    s.text(670, 910, "WINDING STICKS: HEAD / MID / BOTTOM - RECORD FACE TWIST", 19, BLUE, True)
    s.rect(1035, 810, 390, 100, "#FAEFEC", RED, 3)
    s.text(1230, 842, "FIELD RELEASE HOLD", 20, RED, True)
    s.text(1230, 877, "until every geometry value is recorded", 17, INK, True)
    s.save("02-field-measurements")


def profile_register():
    s = MouldingScene(3, "Finished profile register", "Mill one labeled sample of every selected profile before production stock.", "PROFILES")
    # casing
    s.rect(75, 170, 575, 260, PALE_BLUE, BLUE, 3)
    s.text(105, 205, "M-201 CASING", 26, BLUE, True, "lm")
    s.rect(160, 290, 360, 60, OAK, INK, 3)
    s.dim_h(160, 520, 385, "4-1/2 in", BLUE, 350, 350)
    s.dim_v(565, 290, 350, "3/4 in", TEAL, 520, 520)
    s.text(105, 405, "Visible arrises: ease about 1/32 in", 20, INK, False, "lm")
    # backband relationship
    s.rect(700, 170, 725, 260, PALE_TEAL, TEAL, 3)
    s.text(730, 205, "M-202 BACKBAND / CASING", 26, BLUE, True, "lm")
    s.rect(800, 300, 330, 50, OAK, INK, 3)
    s.rect(1130, 283, 105, 67, OAK_DARK, INK, 3)
    s.dim_h(1130, 1235, 390, "1-1/8 in", BLUE, 350, 350)
    s.dim_v(1270, 283, 350, "1 in", TEAL, 1235, 1235)
    s.text(850, 262, "CASING 3/4", 18, INK, True)
    s.text(1182, 255, "1/4 PROUD", 18, RED, True)
    # stop
    s.rect(75, 480, 390, 390, PALE, OAK_DARK, 3)
    s.text(105, 515, "M-203 STOP", 26, BLUE, True, "lm")
    s.rect(155, 660, 220, 64, JAMB, INK, 3)
    s.dim_h(155, 375, 765, "1-1/4 in", BLUE, 724, 724)
    s.dim_v(405, 660, 724, "3/8 in", TEAL, 375, 375)
    s.text(115, 820, "Door-side arris: ease about 1/16 in", 19, INK, False, "lm")
    # cap
    s.rect(505, 480, 440, 390, PALE_BLUE, BLUE, 3)
    s.text(535, 515, "M-204 OPTIONAL CAP", 26, BLUE, True, "lm")
    s.rect(610, 635, 240, 88, JAMB, INK, 3)
    s.polygon([(610, 635), (634, 635), (610, 659)], PALE_BLUE, INK, 2)
    s.polygon([(850, 635), (826, 635), (850, 659)], PALE_BLUE, INK, 2)
    s.dim_h(610, 850, 765, "1-1/2 in deep", BLUE, 723, 723)
    s.dim_v(875, 635, 723, "7/8 in", TEAL, 850, 850)
    s.text(555, 820, "1/8-in chamfer only after sample approval", 19, INK, False, "lm")
    # plinth
    s.rect(985, 480, 440, 390, PALE_TEAL, TEAL, 3)
    s.text(1015, 515, "M-205 OPTIONAL PLINTH", 26, BLUE, True, "lm")
    s.rect(1095, 610, 220, 165, JAMB, INK, 3)
    s.dim_v(1340, 610, 775, "HEIGHT: FIELD", TEAL, 1315, 1315)
    s.dim_h(1095, 1315, 815, "WIDTH: FIELD", BLUE, 775, 775)
    s.text(1080, 850, "7/8 thick; adjacent evidence controls", 19, RED, True, "lm")
    s.save("03-profile-register")


def length_formulas():
    s = MouldingScene(4, "Transfer formulas", "Arithmetic sets rough stock; the fitted opening controls every final cut.", "FORMULAS")
    # mitered scheme
    s.rect(55, 135, 675, 720, PALE_BLUE, BLUE, 3)
    s.text(90, 175, "A  MITERED SURROUND", 27, BLUE, True, "lm")
    x, y, ow, oh, c = 270, 335, 245, 410, 48
    s.rect(x, y, ow, oh, "white", INK, 3)
    s.polygon([(x - c, y), (x, y), (x + c, y - c), (x - c, y - c)], OAK, INK, 3)
    s.polygon([(x + ow, y), (x + ow + c, y), (x + ow + c, y - c), (x + ow - c, y - c)], OAK, INK, 3)
    s.rect(x - c, y, c, oh, OAK, INK, 3)
    s.rect(x + ow, y, c, oh, OAK, INK, 3)
    s.rect(x, y - c, ow, c, OAK, INK, 3)
    s.dim_h(x, x + ow, 270, "HEAD SHORT = W + 2R", BLUE, y - c, y - c)
    s.dim_h(x - c, x + ow + c, 235, "HEAD LONG = W + 2R + 2C", TEAL, y - c, y - c)
    s.dim_v(200, y, y + oh, "LEG SHORT = H + R", BLUE, x - c, x - c)
    s.line([(x - c, y), (x, y - c)], RED, 4)
    s.line([(x + ow, y - c), (x + ow + c, y)], RED, 4)
    s.text(100, 780, "Leg long point = H + R + C", 20, INK, True, "lm")
    s.text(100, 810, "Side band finished = fitted leg long + B", 19, TEAL, True, "lm")
    s.text(100, 840, "Add 2 in total rough allowance", 20, RED, True, "lm")
    # square scheme
    s.rect(770, 135, 675, 720, PALE_TEAL, TEAL, 3)
    s.text(805, 165, "B  SQUARE-BUTT HEAD", 27, BLUE, True, "lm")
    x2, y2, b, oh2 = 985, 405, 20, 340
    s.rect(x2, y2, ow, oh2, "white", INK, 3)
    s.rect(x2 - c, y2, c, oh2, OAK, INK, 3)
    s.rect(x2 + ow, y2, c, oh2, OAK, INK, 3)
    s.rect(x2 - c, y2 - c, ow + 2 * c, c, OAK, INK, 3)
    s.dim_v(915, y2, y2 + oh2, "LEGS = H + R", TEAL, x2 - c, x2 - c)
    s.rect(x2 - c - b, y2 - c - b, ow + 2 * (c + b), b, OAK_DARK, INK, 3)
    s.rect(x2 - c - b - 25, y2 - c - b - 22, ow + 2 * (c + b + 25), 22, JAMB, INK, 3)
    s.dim_h(x2 - c, x2 + ow + c, 295, "HEAD = W + 2R + 2C", BLUE, y2 - c, y2 - c)
    s.dim_h(x2 - c - b, x2 + ow + c + b, 255, "M-202C = FITTED HEAD + 2B", OAK_DARK, y2 - c - b, y2 - c - b)
    s.dim_h(x2 - c - b - 25, x2 + ow + c + b + 25, 215, "CAP = FITTED M-202C + 2P", TEAL, y2 - c - b - 22, y2 - c - b - 22)
    s.text(815, 775, "Side band finished = fitted leg + C", 19, TEAL, True, "lm")
    s.text(815, 805, "Measure H-L and H-R independently", 20, INK, True, "lm")
    s.text(815, 835, "Choose one scheme from house evidence", 20, RED, True, "lm")
    s.text(150, 910, "R = 3/16 reveal  |  C = 4-1/2 casing  |  B = 1-1/8 backband  |  P = 3/4 cap overhang", 22, BLUE, True, "lm")
    s.save("04-length-formulas")


def stock_milling():
    s = MouldingScene(5, "Mill stable profile families", "Work from wide, supported mother blanks; rest stock before final dimensions.", "MILLING")
    cards = [
        (55, "1", "ROUGH CUT", ["Add 2 in length", "Place defects", "Pair ray figure"]),
        (350, "2", "FLATTEN", ["Joint one face", "Joint one edge", "Plane as family"]),
        (645, "3", "REST", ["Sticker flat", "Recheck bow", "Return to final T"]),
        (940, "4", "RIP + LABEL", ["Reference edge", "Final width", "ID / face / top"]),
    ]
    for x, num, title, lines in cards:
        s.rect(x, 155, 255, 275, PALE_BLUE if int(num) % 2 else PALE_TEAL, BLUE if int(num) % 2 else TEAL, 3)
        s.circle(x + 35, 190, 22, OAK, BLUE, 2)
        s.text(x + 35, 190, num, 20, "white", True)
        s.text(x + 70, 190, title, 23, BLUE, True, "lm")
        yy = 240
        for line in lines:
            s.text(x + 28, yy, "- " + line, 20, INK, False, "lm")
            yy += 42
        if x < 940:
            s.arrow(x + 260, 292, x + 288, 292, TEAL, 5, 12)
    s.rect(55, 500, 1370, 360, PALE, OAK_DARK, 3)
    s.text(85, 535, "SAFE STOP-BLANK METHOD", 27, BLUE, True, "lm")
    s.rect(120, 635, 500, 95, OAK, INK, 3)
    for xx in (245, 370, 495):
        s.line([(xx, 635), (xx, 730)], RED, 3)
    s.text(370, 610, "Plane one wide mother blank to 3/8 in", 21, BLUE, True)
    s.dim_h(120, 245, 775, "RIP 1-1/4", TEAL, 730, 730)
    s.arrow(665, 680, 780, 680, TEAL, 8, 22)
    for i in range(3):
        s.rect(820 + i * 175, 645, 135, 70, JAMB, INK, 3)
    s.text(1080, 610, "Then rip supported strips to 1-1/4 in", 21, BLUE, True)
    s.text(1080, 760, "Never plane a loose 1-1/4 x 3/8 strip.", 23, RED, True)
    s.text(85, 825, "Use infeed/outfeed support, guards, extraction, push blocks, and a zero-clearance strategy suited to the machine.", 20, INK, False, "lm")
    s.save("05-stock-milling")


def profile_machining():
    s = MouldingScene(6, "Profile machining card", "Keep reference faces consistent and approve a labeled sample before repeating a setup.", "SETUPS")
    families = [
        (70, 150, 640, 320, "M-201 CASING", "3/4 x 4-1/2", "1/32 ease", OAK),
        (790, 150, 640, 320, "M-202 BACKBAND", "1 x 1-1/8", "1/32 ease", OAK_DARK),
        (70, 520, 640, 320, "M-203 STOP", "3/8 x 1-1/4", "1/16 door-side ease", JAMB),
        (790, 520, 640, 320, "M-204 CAP", "7/8 x 1-1/2", "1/8 chamfer if approved", JAMB),
    ]
    for x, y, w, h, title, size, edge, color in families:
        s.rect(x, y, w, h, PALE_BLUE if x < 500 else PALE_TEAL, BLUE if x < 500 else TEAL, 3)
        s.text(x + 30, y + 38, title, 25, BLUE, True, "lm")
        s.rect(x + 70, y + 125, 285, 70 if "CASING" in title else (95 if "BACKBAND" in title else 58), color, INK, 3)
        s.text(x + 395, y + 135, size, 23, INK, True, "lm")
        s.text(x + 395, y + 180, edge, 20, TEAL, False, "lm")
        s.text(x + 35, y + 260, "SHOW FACE", 18, BLUE, True, "lm")
        s.arrow(x + 165, y + 260, x + 165, y + 205, BLUE, 5, 12)
        s.text(x + 355, y + 260, "REFERENCE EDGE", 18, TEAL, True, "lm")
        s.arrow(x + 530, y + 260, x + 345, y + 175, TEAL, 5, 12)
    s.text(110, 900, "Router use: clamp the work, use a plunge base plus edge guide, and keep narrow pieces in the mother blank.", 22, RED, True, "lm")
    s.save("06-profile-machining")


def wall_section():
    s = MouldingScene(7, "Completed jamb and trim section", "The casing bridges the jamb-to-wall interface without being pulled hollow.", "SECTION")
    # plan section through one jamb leg
    s.rect(610, 260, 750, 380, WALL, GRAY, 3)
    s.text(1050, 445, "WALL / FRAMING", 26, GRAY, True)
    s.rect(530, 225, 95, 450, JAMB, INK, 4)
    s.text(578, 710, "JAMB", 21, BLUE, True)
    s.rect(300, 395, 230, 92, DOOR, INK, 4)
    s.text(415, 441, "DOOR 1-3/8", 21, INK, True)
    s.rect(485, 330, 45, 170, OAK_DARK, INK, 3)
    s.text(420, 315, "STOP", 20, TEAL, True)
    s.arrow(455, 320, 505, 350, TEAL, 4, 12)
    # front-room face at top
    s.rect(565, 178, 520, 72, OAK, INK, 4)
    s.rect(1085, 154, 130, 96, OAK_DARK, INK, 4)
    s.text(820, 130, "CASING 3/4 x 4-1/2", 23, BLUE, True)
    s.text(1150, 120, "BACKBAND 1 x 1-1/8", 21, TEAL, True)
    s.dim_v(1260, 154, 250, "1/4 PROUD", RED, 1215, 1215)
    s.dim_h(625, 1085, 285, "4-1/2 CASING", BLUE, 250, 250)
    s.dim_h(1085, 1215, 320, "1-1/8 BAND", TEAL, 250, 250)
    s.dim_h(530, 565, 165, "R = 3/16", RED, 225, 178)
    s.note(
        70,
        690,
        590,
        200,
        "Bearing rule",
        [
            "Casing back lies flat on jamb + wall",
            "Relieve a locally proud jamb only",
            "Shim a recessed jamb continuously",
            "Preserve at least 1/2 in sound casing",
        ],
    )
    s.note(
        760,
        690,
        660,
        200,
        "Glue and fastener boundary",
        [
            "Glue casing-to-casing and band-to-casing only",
            "Never glue natural-finish trim to drywall",
            "Inner brads enter jamb; outer nails enter framing",
            "Verify utilities and substrate before fastening",
        ],
    )
    s.save("07-jamb-wall-section")


def head_joint_options():
    s = MouldingScene(8, "Choose one head-joint language", "Match adjacent original openings; do not combine schemes on one face.", "DECISION")
    s.rect(55, 140, 680, 720, PALE_BLUE, BLUE, 3)
    s.text(90, 180, "A  MITERED CASING + BACKBAND", 26, BLUE, True, "lm")
    x, y, ow, oh, c, b = 270, 315, 250, 420, 55, 22
    s.rect(x - c - b, y - c - b, ow + 2 * (c + b), b, OAK_DARK, INK, 3)
    s.rect(x - c - b, y - c, b, oh + c, OAK_DARK, INK, 3)
    s.rect(x + ow + c, y - c, b, oh + c, OAK_DARK, INK, 3)
    s.rect(x - c, y - c, ow + 2 * c, c, OAK, INK, 3)
    s.rect(x - c, y, c, oh, OAK, INK, 3)
    s.rect(x + ow, y, c, oh, OAK, INK, 3)
    s.line([(x - c, y), (x, y - c)], RED, 5)
    s.line([(x + ow, y - c), (x + ow + c, y)], RED, 5)
    # Keep the joint labels off the oak fills so they remain legible in print.
    s.rect(260, 205, 270, 28, "white", "white", 0)
    s.text(395, 219, "45-DEGREE VISIBLE JOINTS", 18, RED, True)
    s.text(105, 805, "Tune on a shooting board; both faces close by hand.", 20, INK, True, "lm")
    s.rect(765, 140, 680, 720, PALE_TEAL, TEAL, 3)
    s.text(800, 180, "B  SQUARE-BUTT HEAD + OPTIONAL CAP", 26, BLUE, True, "lm")
    x2 = 985
    s.rect(x2 - c, y, c, oh, OAK, INK, 3)
    s.rect(x2 + ow, y, c, oh, OAK, INK, 3)
    s.rect(x2 - c, y - c, ow + 2 * c, c, OAK, INK, 3)
    s.rect(x2 - c - b, y - c - b, ow + 2 * (c + b), b, OAK_DARK, INK, 3)
    s.rect(x2 - c - b - 30, y - c - b - 42, ow + 2 * (c + b + 30), 24, JAMB, INK, 3)
    s.line([(x2 - c, y), (x2 + ow + c, y)], RED, 4)
    s.rect(1000, 246, 220, 28, "white", "white", 0)
    s.text(1110, 260, "SQUARE SHOULDERS", 18, RED, True)
    s.rect(940, 202, 340, 26, "white", "white", 0)
    s.text(1110, 215, "CAP BEARS ON COMPLETED M-202C", 17, TEAL, True)
    s.text(1105, 786, "Head spans the legs. M-202C is mandatory.", 18, INK, True)
    s.text(1105, 818, "Install a cap only when supported by house evidence.", 18, INK, True)
    s.text(95, 910, "PASS: joint gap <0.010 in, faces flush <=0.010 in, no clamp pressure required to hide error.", 22, RED, True, "lm")
    s.save("08-head-joint-options")


def stop_install():
    s = MouldingScene(9, "Fit the three-piece door stop", "The hung, latched door is the locating fixture; fit the head stop first.", "DRY FIT 01")
    x, y, ow, oh = 345, 165, 420, 675
    s.rect(x, y, ow, oh, "white", INK, 5)
    five_panel_door(s, x + 12, y + 12, ow - 24, oh - 24)
    # visible stop line around the closed door
    s.rect(x + 4, y + 4, ow - 8, 25, OAK_DARK, INK, 3)
    s.rect(x + 4, y + 29, 25, oh - 33, OAK_DARK, INK, 3)
    s.rect(x + ow - 29, y + 29, 25, oh - 33, OAK_DARK, INK, 3)
    s.step_badge(125, 240, 1, "Fit head stop")
    s.arrow(320, 240, x + ow / 2, y + 18, TEAL, 6, 16)
    s.step_badge(125, 415, 2, "Fit side stops")
    s.arrow(320, 415, x + 18, y + 390, TEAL, 6, 16)
    s.step_badge(125, 590, 3, "TEMP tack + cycle")
    s.text(85, 635, "Label; pull tacks; remove", 18, RED, True, "lm")
    s.arrow(315, 650, x + ow - 18, y + 560, TEAL, 6, 16)
    # inset section
    s.rect(860, 170, 530, 420, PALE_BLUE, BLUE, 3)
    s.text(890, 205, "CONTACT SECTION", 25, BLUE, True, "lm")
    s.rect(930, 300, 90, 210, JAMB, INK, 3)
    s.rect(1020, 345, 205, 92, DOOR, INK, 3)
    s.rect(990, 270, 30, 190, OAK_DARK, INK, 3)
    s.rect(1020, 332, 12, 118, "#F4C96B", RED, 2)
    s.text(1055, 305, "0.010-0.020 paper/card shim", 19, RED, True, "lm")
    s.arrow(1060, 320, 1026, 345, RED, 4, 11)
    s.text(890, 540, "Dry fit only: label, pull tacks, remove.", 20, TEAL, True, "lm")
    s.note(
        860,
        640,
        530,
        220,
        "Pass / stop",
        [
            "Quiet, continuous contact",
            "Latch works without push or lift",
            "No slab bow or spring-back",
            "Label shim points; remove all stops",
        ],
    )
    s.save("09-stop-install")


def side_casing_fit():
    s = MouldingScene(10, "Lay out and fit the side casings", "Reference the inside jamb edge, then transfer top and bottom cuts from the opening.", "DRY FIT 02")
    x, y, ow, oh = 490, 185, 400, 640
    s.rect(x - 65, y - 55, ow + 130, oh + 110, WALL, GRAY, 3)
    s.rect(x, y, ow, oh, "white", INK, 5)
    # reveal lines
    s.line([(x - 8, y), (x - 8, y + oh)], RED, 4)
    s.line([(x + ow + 8, y), (x + ow + 8, y + oh)], RED, 4)
    s.line([(x, y - 8), (x + ow, y - 8)], RED, 4)
    # floating legs
    s.rect(330, y, 70, oh, OAK, INK, 3)
    s.rect(1032, y, 78, oh, OAK, INK, 3)
    s.arrow(410, 545, x - 10, 545, TEAL, 8, 22)
    s.arrow(1020, 545, x + ow + 10, 545, TEAL, 8, 22)
    s.dim_h(x - 8, x, 145, "R = 3/16", RED, y, y)
    s.step_badge(90, 235, 1, "Mark 3/16 reveal")
    s.step_badge(90, 365, 2, "Scribe each bottom")
    s.step_badge(90, 495, 3, "Transfer head mark")
    s.step_badge(90, 625, 4, "Cut long; tune fit")
    s.note(
        1140,
        200,
        300,
        300,
        "Temporary tack",
        [
            "Three brads only",
            "Reveal <= 1/32 variation",
            "Leg bears flat",
            "Plumb <= 1/16 full height",
            "Keep grain pair oriented",
        ],
    )
    # bottom scribe
    s.line([(330, y + oh - 10), (400, y + oh - 28)], RED, 5)
    s.line([(1032, y + oh - 30), (1110, y + oh - 8)], RED, 5)
    s.rect(335, 835, 710, 55, "#FAEFEC", RED, 2)
    s.text(690, 863, "Floor or plinth top is the datum - measure both sides.", 20, RED, True)
    s.save("10-side-casing-fit")


def head_casing_fit():
    s = MouldingScene(11, "Transfer and fit the head casing", "Tune one end, return to the opening, and mark the second end from the actual work.", "DRY FIT 03")
    x, y, ow, oh, c = 420, 290, 430, 505, 75
    s.rect(x, y, ow, oh, "white", INK, 4)
    s.rect(x - c, y, c, oh, OAK, INK, 3)
    s.rect(x + ow, y, c, oh, OAK, INK, 3)
    # exploded head
    s.rect(x - c, 155, ow + 2 * c, c, OAK, INK, 3)
    s.arrow(x + ow / 2, 245, x + ow / 2, y - 12, TEAL, 9, 24)
    s.line([(x - c, y), (x, y - c)], RED, 4)
    s.line([(x + ow, y - c), (x + ow + c, y)], RED, 4)
    s.text(705, 125, "CUT LONG - TRANSFER BOTH JOINTS", 22, RED, True)
    s.step_badge(85, 250, 1, "Fit first end")
    s.step_badge(85, 390, 2, "Return to opening")
    s.step_badge(85, 530, 3, "Scribe second end")
    # Keep the label inside the left instruction lane; the longer wording
    # collided with the casing leg at production render scale.
    s.step_badge(85, 670, 4, "Dry-fit head + legs")
    # shooting board inset
    s.rect(1030, 175, 370, 360, PALE_BLUE, BLUE, 3)
    s.text(1060, 210, "TUNE, DO NOT FORCE", 24, BLUE, True, "lm")
    s.polygon([(1100, 435), (1290, 245), (1340, 295), (1150, 485)], OAK, INK, 3)
    s.rect(1080, 455, 260, 30, OAK_DARK, INK, 2)
    s.arrow(1300, 400, 1220, 330, TEAL, 7, 18)
    s.text(1070, 515, "Shooting board or fine hand plane", 19, INK, False, "lm")
    s.note(
        1010,
        610,
        410,
        220,
        "Release",
        [
            "Head level <= 1/16",
            "Reveal within 1/32",
            "Gap < 0.010",
            "Faces flush <= 0.010",
        ],
    )
    s.save("11-head-casing-fit")


def backband_install():
    s = MouldingScene(12, "Wrap the fitted casing with backband", "Transfer from fitted casing; keep glue faces dry until post-cure installation.", "DRY FIT 04")
    x, y, ow, oh, c, b = 440, 300, 360, 570, 72, 27
    s.rect(x, y, ow, oh, "white", INK, 4)
    s.rect(x - c, y - c, ow + 2 * c, c, OAK, INK, 3)
    s.rect(x - c, y, c, oh, OAK, INK, 3)
    s.rect(x + ow, y, c, oh, OAK, INK, 3)
    # exploded band
    s.rect(x - c - b - 95, y - c, b, oh, OAK_DARK, INK, 3)
    s.rect(x + ow + c + 95, y - c, b, oh, OAK_DARK, INK, 3)
    s.rect(x - c - 25, y - c - b - 90, ow + 2 * c + 50, b, OAK_DARK, INK, 3)
    s.arrow(x - c - 55, y + oh / 2, x - c - 5, y + oh / 2, TEAL, 8, 22)
    s.arrow(x + ow + c + 55, y + oh / 2, x + ow + c + 5, y + oh / 2, TEAL, 8, 22)
    s.arrow(x + ow / 2, y - c - 55, x + ow / 2, y - c - 5, TEAL, 8, 22)
    # glue line
    s.line([(x - c - 3, y - c), (x - c - 3, y + oh)], GREEN, 8)
    s.line([(x + ow + c + 3, y - c), (x + ow + c + 3, y + oh)], GREEN, 8)
    s.line([(x - c, y - c - 3), (x + ow + c, y - c - 3)], GREEN, 8)
    s.text(620, 915, "GREEN = POST-CURE GLUE AT CASING EDGE / RETURNS ONLY", 19, GREEN, True)
    # cross section
    s.rect(990, 185, 410, 340, PALE_BLUE, BLUE, 3)
    s.text(1020, 220, "FACE PROJECTION", 24, BLUE, True, "lm")
    s.rect(1040, 335, 220, 55, OAK, INK, 3)
    s.rect(1260, 315, 90, 75, OAK_DARK, INK, 3)
    s.dim_v(1375, 315, 390, "1/4 PROUD", RED, 1350, 1350)
    s.note(
        990,
        575,
        410,
        240,
        "Fasten",
        [
            "18-ga into casing at 8-12 in OC",
            "Embed >= 1/2 in; no exit or split",
            "Offset from casing fasteners",
            "No glue to plaster or drywall",
            "Returns stay dry until post-cure install",
        ],
    )
    s.save("12-backband-install")


def cap_plinth():
    s = MouldingScene(13, "Optional cap, plinth, and baseboard", "M-202C is mandatory; cap and plinth remain evidence-supported options.", "OPTIONS")
    # Completed head stack: casing, mandatory backband, then optional cap.
    s.rect(60, 140, 1365, 360, PALE_BLUE, BLUE, 3)
    s.text(90, 176, "CAP STACK - FIT ONLY AFTER THE COMPLETE HEAD BACKBAND", 24, BLUE, True, "lm")
    s.rect(430, 345, 640, 74, OAK, INK, 3)
    s.rect(390, 310, 720, 35, OAK_DARK, INK, 3)
    s.rect(340, 270, 820, 28, JAMB, INK, 3)
    s.text(750, 382, "M-201C HEAD CASING", 20, INK, True)
    s.text(750, 328, "M-202C MANDATORY HEAD BACKBAND", 18, "white", True)
    s.text(750, 284, "M-204 OPTIONAL CAP", 18, INK, True)
    s.dim_h(340, 390, 235, "P = 3/4", TEAL, 270, 310)
    s.dim_h(1110, 1160, 235, "P = 3/4", TEAL, 310, 270)
    s.text(105, 452, "Finished cap = actual fitted head-backband outside width + 2P", 20, TEAL, True, "lm")
    s.text(885, 452, "Rough blank = finished target + 2 in", 20, RED, True, "lm")

    # No-plinth condition.
    s.rect(60, 545, 650, 325, PALE_TEAL, TEAL, 3)
    s.text(90, 582, "NO PLINTH - WHEN EVIDENCE IS ABSENT", 22, BLUE, True, "lm")
    s.rect(155, 635, 95, 190, OAK, INK, 3)
    s.rect(250, 650, 32, 175, OAK_DARK, INK, 3)
    s.rect(282, 735, 300, 90, JAMB, INK, 3)
    s.line([(282, 735), (282, 825)], RED, 4)
    s.text(430, 780, "BASEBOARD BUTTS TO TRIM", 18, INK, True)
    s.text(90, 845, "Floor is casing bottom datum; do not notch casing.", 18, RED, True, "lm")

    # Evidence-supported plinth condition.
    s.rect(760, 545, 665, 325, PALE, OAK_DARK, 3)
    s.text(790, 582, "PLINTH - EVIDENCE REQUIRED", 22, BLUE, True, "lm")
    s.rect(850, 690, 135, 135, JAMB, INK, 3)
    s.rect(880, 620, 75, 70, OAK, INK, 3)
    s.rect(985, 745, 300, 80, OAK_DARK, INK, 3)
    s.text(1135, 786, "BASEBOARD", 18, INK, True)
    s.text(1020, 630, "1  Install cured plinth first", 18, TEAL, True, "lm")
    s.text(1020, 666, "2  Use plinth top as casing datum", 18, TEAL, True, "lm")
    s.text(1020, 702, "3  No glue to floor or wall", 18, RED, True, "lm")
    s.text(1020, 844, "WIDTH / HEIGHT / PROFILE: FIELD VERIFY", 18, RED, True, "lm")
    s.text(750, 915, "Post-cure glue only at masked plinth-to-trim and cap-to-head-band joints.", 20, RED, True)
    s.save("13-cap-plinth")


def scribe_corners():
    s = MouldingScene(14, "Scribing and corner conditions", "Resolve the substrate deliberately; never use fasteners to bend stain-grade casing into place.", "DETAILS")
    boxes = [
        (55, 140, "A  PROUD JAMB", ("Route shallow", "back relief"), ("Keep >= 1/2 in", "sound casing")),
        (770, 140, "B  RECESSED JAMB", ("Fit a continuous", "wood shim"), ("Do not bridge", "a hollow")),
        (55, 515, "C  INSIDE CORNER", ("Scribe the", "terminating edge"), ("Keep casing reveal", "unchanged")),
        (770, 515, "D  EXPOSED END", ("Dry-fit / label", "self-return"), ("Glue only after", "finish cure")),
    ]
    for index, (x, y, title, action_lines, gate_lines) in enumerate(boxes):
        s.rect(x, y, 675, 330, PALE_BLUE if index % 2 == 0 else PALE_TEAL, BLUE if index % 2 == 0 else TEAL, 3)
        s.text(x + 28, y + 40, title, 25, BLUE, True, "lm")
        if index == 0:
            s.rect(x + 75, y + 135, 300, 70, OAK, INK, 3)
            s.rect(x + 75, y + 190, 95, 15, "white", RED, 2)
            s.rect(x + 75, y + 208, 95, 38, JAMB, INK, 2)
        elif index == 1:
            s.rect(x + 75, y + 125, 300, 70, OAK, INK, 3)
            s.rect(x + 75, y + 198, 110, 20, JAMB, INK, 2)
            s.rect(x + 75, y + 195, 110, 8, GREEN, GREEN, 0)
        elif index == 2:
            s.rect(x + 95, y + 100, 45, 170, WALL, GRAY, 2)
            s.polygon([(x + 85, y + 125), (x + 335, y + 105), (x + 335, y + 205), (x + 85, y + 225)], OAK, INK, 3)
            s.line([(x + 85, y + 125), (x + 85, y + 225)], RED, 5)
        else:
            s.rect(x + 75, y + 135, 260, 70, OAK_DARK, INK, 3)
            s.polygon([(x + 335, y + 135), (x + 385, y + 170), (x + 335, y + 205)], OAK_DARK, INK, 3)
            s.line([(x + 335, y + 135), (x + 385, y + 170), (x + 335, y + 205)], RED, 4)
        text_x = x + 405
        for line_index, value in enumerate(action_lines):
            s.text(text_x, y + 127 + 24 * line_index, value, 18, TEAL, True, "lm")
        for line_index, value in enumerate(gate_lines):
            s.text(text_x, y + 190 + 23 * line_index, value, 17, RED, True, "lm")
        s.text(text_x, y + 255, "Prove on scrap / dry fit", 16, INK, False, "lm")
    s.text(120, 910, "STOP when projection > 1/8 in or substrate damage prevents full bearing - repair the condition first.", 22, RED, True, "lm")
    s.save("14-scribe-corners")


def fastener_map():
    s = MouldingScene(15, "Fastener and glue map", "Calculate the actual layer stack; prove the selected standard length on a matching offcut.", "FASTEN")
    x, y, ow, oh = 520, 225, 360, 595
    trim_opening(s, x, y, ow, oh, casing=75, band=25, door=False)
    # dots: inner casing 18g blue, outer casing 15g red, band green, stop amber
    for yy in range(y + 65, y + oh - 10, 105):
        s.circle(x - 10, yy, 8, BLUE, "white", 2)
        s.circle(x + ow + 10, yy, 8, BLUE, "white", 2)
    for yy in range(y + 80, y + oh - 10, 135):
        s.circle(x - 62, yy, 9, RED, "white", 2)
        s.circle(x + ow + 62, yy, 9, RED, "white", 2)
    for yy in range(y + 55, y + oh - 10, 90):
        s.circle(x - 94, yy, 7, GREEN, "white", 2)
        s.circle(x + ow + 94, yy, 7, GREEN, "white", 2)
    for xx in range(x + 35, x + ow - 20, 85):
        s.circle(xx, y - 10, 8, BLUE, "white", 2)
        s.circle(xx, y - 62, 9, RED, "white", 2)
        s.circle(xx, y - 94, 7, GREEN, "white", 2)
    s.line([(x - 75, y - 75), (x + ow + 75, y - 75)], GREEN, 6)
    s.line([(x - 75, y - 75), (x - 75, y + oh)], GREEN, 6)
    s.line([(x + ow + 75, y - 75), (x + ow + 75, y + oh)], GREEN, 6)
    s.note(
        55,
        180,
        380,
        340,
        "Legend",
        [
            "BLUE: inner >= 3/4 sound jamb",
            "RED: outer >= 1 verified framing",
            "GREEN: band >= 1/2 sound casing",
            "STOP: >= 3/4 sound jamb",
            "Offset rows; avoid corners",
        ],
    )
    s.note(
        1015,
        180,
        405,
        340,
        "Typical spacing",
        [
            "Inner casing: 12-16 in OC",
            "Outer casing: about 16 in OC",
            "Backband: 8-12 in OC",
            "No band point exit or split",
            "Cycle door before stop pattern",
        ],
    )
    s.rect(55, 600, 380, 220, "#FAEFEC", RED, 3)
    s.text(85, 635, "NAILER SAFETY", 25, RED, True, "lm")
    s.text(85, 690, "Sequential-fire mode", 20, INK, False, "lm")
    s.text(85, 730, "Hands outside fastener path", 20, INK, False, "lm")
    s.text(85, 770, "Disconnect before adjustment", 20, INK, False, "lm")
    s.rect(1015, 600, 405, 220, PALE, OAK_DARK, 3)
    s.text(1045, 635, "GLUE BOUNDARY", 25, BLUE, True, "lm")
    s.text(1045, 685, "Masked wood joints only", 20, INK, False, "lm")
    s.text(1045, 725, "Returns glue only after finish cure", 18, INK, False, "lm")
    s.text(1045, 765, "No glue to jamb, wall, or floor", 20, RED, True, "lm")
    s.text(750, 905, "HOLD if no standard length passes the offcut proof without exit, split, or utility risk.", 20, RED, True)
    s.save("15-fastener-map")


def finish_qc():
    s = MouldingScene(16, "Finish and final release", "Approve a sample, protect crisp edges, then inspect the working door - not just the trim.", "QC")
    steps = [
        (55, "1", "SCRAPE / SAND", "Uniform P100 to P120"),
        (330, "2", "APPROVE SAMPLE", "Compare in the actual room"),
        (605, "3", "CLEAN", "Vacuum; current TDS"),
        (880, "4", "APPLY / WIPE", "Thin coat; wipe dry"),
        (1155, "5", "CURE", "Current TDS controls"),
    ]
    for x, num, title, body in steps:
        s.rect(x, 145, 235, 205, PALE_BLUE if int(num) % 2 else PALE_TEAL, BLUE if int(num) % 2 else TEAL, 3)
        s.circle(x + 34, 180, 22, OAK, BLUE, 2)
        s.text(x + 34, 180, num, 20, "white", True)
        s.text(x + 25, 230, title, 21, BLUE, True, "lm")
        s.text(x + 25, 285, body, 18, INK, False, "lm")
        if x < 1155:
            s.arrow(x + 238, 245, x + 266, 245, TEAL, 5, 12)
    x, y, ow, oh = 575, 500, 300, 360
    trim_opening(s, x, y, ow, oh, casing=58, band=20, door=True)
    s.rect(275, 365, 950, 44, "#FAEFEC", RED, 2)
    s.text(750, 387, "POST-CURE ORDER: PLINTHS -> CASING -> BACKBAND / RETURNS -> CAP -> STOPS LAST", 18, RED, True)
    s.callout(110, 465, "REVEAL 3/16 +/-1/32", x - 5, y + 90, BLUE)
    s.callout(110, 565, "LEGS PLUMB <=1/16", x - 55, y + 240, TEAL)
    s.callout(110, 665, "SCRIBE GAP <=1/32", x - 80, y + 315, BLUE)
    s.callout(1030, 465, "HEAD LEVEL <=1/16", x + ow / 2, y - 58, TEAL)
    s.callout(1030, 565, "JOINT GAP <0.010", x + ow + 55, y - 20, BLUE)
    s.callout(1030, 665, "BAND PROJECTION +/-1/32", x + ow + 78, y + 220, TEAL)
    s.text(750, 925, "FINAL FUNCTION: free swing, easy latch, quiet stop contact, no springing or rattle.", 22, RED, True)
    s.save("16-finish-qc")


def generate():
    system_overview()
    field_measurements()
    profile_register()
    length_formulas()
    stock_milling()
    profile_machining()
    wall_section()
    head_joint_options()
    stop_install()
    side_casing_fit()
    head_casing_fit()
    backband_install()
    cap_plinth()
    scribe_corners()
    fastener_map()
    finish_qc()
    contact_dir = ROOT / "build" / "reports" / "contact-sheets"
    contact_dir.mkdir(parents=True, exist_ok=True)
    sheet = Image.new("RGB", (1200, 840), "white")
    for index, path in enumerate(sorted(OUT.glob("*.png"))):
        with Image.open(path) as image:
            image.thumbnail((290, 190))
            col, row = index % 4, index // 4
            x = col * 300 + (300 - image.width) // 2
            y = row * 210 + 5
            sheet.paste(image, (x, y))
            ImageDraw.Draw(sheet).text(
                (col * 300 + 8, row * 210 + 192),
                path.stem,
                fill=INK,
                font=font(14),
            )
    sheet.save(contact_dir / "DC-1916-001_Custom_Moulding_Diagrams.jpg", quality=90)
    print(f"PASS: generated 16 moulding diagrams in {OUT}")


if __name__ == "__main__":
    generate()
