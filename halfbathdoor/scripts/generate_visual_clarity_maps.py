#!/usr/bin/env python3
"""Generate the shop-clarity diagrams used in the cabinetmaker guide."""
from __future__ import annotations

from pathlib import Path
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "cabinetmakers-guide" / "renderings"

W, H = 1800, 1000
INK = "#172331"
MUTED = "#5D6872"
BLUE = "#DCE9F1"
BLUE_DARK = "#1E526B"
OAK = "#E8DCC7"
OAK_DARK = "#A67939"
PALE = "#F4F7F9"
GREEN = "#DDEBDD"
GREEN_DARK = "#356B42"
RED = "#FAEFEC"
RED_DARK = "#A33B32"
RULE = "#8B969F"
WHITE = "#FFFFFF"
FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"


def font(size: int, bold: bool = False):
    return ImageFont.truetype(BOLD if bold else FONT, size)


def canvas(title: str, subtitle: str):
    image = Image.new("RGB", (W, H), WHITE)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((12, 12, W - 12, H - 12), 22, outline=RULE, width=3)
    draw.text((52, 42), title, font=font(38, True), fill=INK)
    draw.text((52, 92), subtitle, font=font(24), fill=MUTED)
    draw.line((52, 132, W - 52, 132), fill=OAK_DARK, width=3)
    return image, draw


def text(draw, xy, value, size=24, fill=INK, bold=False, anchor=None):
    draw.text(xy, value, font=font(size, bold), fill=fill, anchor=anchor)


def wrapped(draw, xy, value, width_chars, size=22, fill=INK, bold=False, gap=4):
    x, y = xy
    f = font(size, bold)
    for line in wrap(value, width=width_chars):
        draw.text((x, y), line, font=f, fill=fill)
        y += size + gap
    return y


def card(draw, box, fill=PALE, outline=RULE, radius=18):
    draw.rounded_rectangle(box, radius, fill=fill, outline=outline, width=3)


def arrow(draw, start, end, fill=BLUE_DARK, width=8):
    draw.line((start, end), fill=fill, width=width)
    x2, y2 = end
    x1, y1 = start
    if abs(x2 - x1) >= abs(y2 - y1):
        sign = 1 if x2 > x1 else -1
        points = [(x2, y2), (x2 - sign * 22, y2 - 15), (x2 - sign * 22, y2 + 15)]
    else:
        sign = 1 if y2 > y1 else -1
        points = [(x2, y2), (x2 - 15, y2 - sign * 22), (x2 + 15, y2 - sign * 22)]
    draw.polygon(points, fill=fill)


def save(image, name):
    OUT.mkdir(parents=True, exist_ok=True)
    image.save(OUT / name, "PNG", optimize=True)


def board_allocation():
    image, draw = canvas(
        "BOARD A-O: WHAT EACH BOARD BECOMES",
        "Do not start panel or short-member cuts until the continuous B/C/I/K stile-layer gates pass.",
    )
    groups = [
        [
            ("A", "KEEP FULL", "72-3/4 reserve: panel fallback, setup, repair"),
            ("B", "D-101A", "continuous hinge-stile show face"),
            ("C", "D-101B", "continuous lock-stile show face + eligible width offcuts"),
            ("D", "K + L", "four lower-panel staves; tail may enter FP-05"),
            ("E", "FP-05", "three clear 16-1/4 face billets; map knots first"),
        ],
        [
            ("F", "FP-05", "two clear 16-1/4 face billets; map knots first"),
            ("G", "D-101J", "four center-panel staves; follow controlled G-01 cuts"),
            ("H", "D-101N", "three lower-center panel staves; tail conditional"),
            ("I", "D-101B", "lock-stile core + continuous back face"),
            ("J", "C/M/F/G", "top and upper rail cores, wide F core, muntin core"),
        ],
        [
            ("K", "D-101A", "hinge-stile core + continuous back face"),
            ("L", "D/E/F", "lock-rail, lower-rail, and bottom-rail core staves"),
            ("M", "D-101H", "three upper-panel staves; tail may enter FP-05"),
            ("N", "KEEP FULL", "finished white-oak short-core reserve"),
            ("O", "KEEP FULL", "finished white-oak short-core and repair reserve"),
        ],
    ]
    x_positions = [52, 637, 1222]
    for group_index, rows in enumerate(groups):
        x = x_positions[group_index]
        for row_index, (label, target, detail) in enumerate(rows):
            y = 164 + row_index * 140
            card(draw, (x, y, x + 526, y + 118), WHITE)
            draw.rounded_rectangle((x + 14, y + 17, x + 90, y + 93), 14, fill=BLUE_DARK)
            text(draw, (x + 52, y + 55), label, 34, WHITE, True, "mm")
            text(draw, (x + 110, y + 24), target, 25, INK, True)
            wrapped(draw, (x + 110, y + 58), detail, 35, 20, MUTED)
    card(draw, (52, 884, W - 52, 948), fill=RED, outline=RED_DARK)
    text(
        draw,
        (W // 2, 916),
        "CUT ORDER: prove B/C/I/K -> map M/G/H/D panels -> map J/L cores -> release E/F and eligible offcuts.",
        24,
        RED_DARK,
        True,
        "mm",
    )
    save(image, "03c-board-a-o-allocation-map.png")


def seam_map():
    image, draw = canvas(
        "WIDE RAIL SEAM MAPS: D-101D AND D-101F",
        "Mark every seam on both ends after final width and before any Domino mortise.",
    )

    def rail_diagram(x, y, width, part, label, seams):
        card(draw, (x, y, x + width, y + 760), WHITE)
        text(draw, (x + 28, y + 26), f"{part}  {label}", 29, INK, True)
        layers = [("SHOW FACE", BLUE, seams["show"]), ("CORE", OAK, seams["core"]), ("BACK FACE", BLUE, seams["back"])]
        bar_x = x + 52
        bar_w = width - 104
        for idx, (name, fill, stations) in enumerate(layers):
            by = y + 110 + idx * 170
            text(draw, (bar_x, by - 38), name, 21, INK, True)
            draw.rounded_rectangle((bar_x, by, bar_x + bar_w, by + 82), 12, fill=fill, outline=RULE, width=3)
            for station, station_label in stations:
                sx = bar_x + station * bar_w
                draw.line((sx, by - 12, sx, by + 96), fill=RED_DARK, width=5)
                text(draw, (sx, by + 116), station_label, 19, RED_DARK, True, "ma")
        text(draw, (bar_x, y + 650), "All stations measured from the finished top edge.", 21, MUTED)
        text(draw, (bar_x, y + 686), "Required: seam position +/-1/32 in.", 21, INK, True)
        text(draw, (bar_x, y + 720), "Core-to-face seam offset: 1/2 in minimum.", 21, INK, True)

    rail_diagram(
        52,
        164,
        800,
        "D-101D",
        "LOCK RAIL - 7-1/4 in finished width",
        {
            "show": [(4.375 / 7.25, '4-3/8"')],
            "core": [(2.25 / 7.25, '2-1/4"')],
            "back": [(4.875 / 7.25, '4-7/8"')],
        },
    )
    rail_diagram(
        886,
        164,
        862,
        "D-101F",
        "BOTTOM RAIL - 12-1/4 in finished width",
        {
            "show": [(3 / 12.25, '3"'), (6.5 / 12.25, '6-1/2"'), (9.5 / 12.25, '9-1/2"')],
            "core": [(5.75 / 12.25, '5-3/4"')],
            "back": [(2.5 / 12.25, '2-1/2"'), (5 / 12.25, '5"'), (9 / 12.25, '9"')],
        },
    )
    save(image, "03d-wide-rail-seam-map.png")


def datum_map():
    image, draw = canvas(
        "MARK THE DATUMS BEFORE MACHINING",
        "Lay every part in door orientation with the show face up. If an arrow looks mirrored, stop.",
    )
    card(draw, (52, 164, 720, 900), WHITE)
    text(draw, (82, 194), "STILE: D-101A / D-101B", 28, INK, True)
    draw.rounded_rectangle((240, 270, 500, 820), 12, fill=BLUE, outline=RULE, width=4)
    text(draw, (370, 545), "SF", 54, BLUE_DARK, True, "mm")
    text(draw, (370, 596), "SHOW FACE", 21, INK, True, "mm")
    arrow(draw, (370, 790), (370, 315))
    text(draw, (390, 330), "TOP / slab datum", 22, INK, True)
    text(draw, (220, 850), "RE = panel-facing edge", 22, INK)
    text(draw, (515, 410), "RF = back face", 18, INK)
    text(draw, (515, 442), "DF fence = SF", 18, MUTED)

    card(draw, (750, 164, 1748, 500), WHITE)
    text(draw, (780, 194), "RAIL: C / M / D / E / F", 28, INK, True)
    draw.rounded_rectangle((870, 286, 1580, 410), 12, fill=OAK, outline=RULE, width=4)
    text(draw, (1225, 348), "SF UP", 34, INK, True, "mm")
    arrow(draw, (900, 448), (1540, 448))
    text(draw, (1220, 472), "Length measurements start at hinge-side shoulder = 0", 21, INK, True, "mm")
    text(draw, (810, 260), "TOP EDGE = mortise-coordinate datum", 21, BLUE_DARK, True)

    card(draw, (750, 530, 1748, 900), WHITE)
    text(draw, (780, 560), "MUNTIN: D-101G", 28, INK, True)
    draw.rounded_rectangle((1070, 625, 1420, 820), 12, fill=BLUE, outline=RULE, width=4)
    text(draw, (1245, 722), "SF UP", 34, BLUE_DARK, True, "mm")
    arrow(draw, (1020, 850), (1465, 850))
    text(draw, (1240, 878), "Read 1 in and 2 in mortise centers from LEFT edge", 21, INK, True, "mm")
    text(draw, (830, 663), "Mark:", 22, INK, True)
    text(draw, (830, 700), "ID / SF / RF / RE", 19, MUTED)
    text(draw, (830, 730), "TOP / BOTTOM / LEFT", 19, MUTED)
    save(image, "03e-datum-marking-map.png")


def panel_glue_map():
    image, draw = canvas(
        "PANEL BLANKS: EDGE-GLUE ONLY",
        "Dry-fit every seam first. Glue the stave edges, not the panel faces and not the frame grooves.",
    )
    panels = [
        ("D-101H", "M x 3", '5/8 x 16-3/8 x 15-9/16 rough', 3),
        ("D-101J", "G x 4", '5/8 x 16-3/8 x 16-1/16 rough', 4),
        ("D-101N", "H x 3", '5/8 x 16-3/8 x 10-13/16 rough', 3),
        ("D-101K", "D x 2", '5/8 x 7-3/8 x 12-5/16 rough', 2),
        ("D-101L", "D x 2", '5/8 x 7-3/8 x 12-5/16 rough', 2),
    ]
    card_w = 322
    for idx, (part, stock, dims, count) in enumerate(panels):
        x = 52 + idx * 342
        card(draw, (x, 164, x + card_w, 650), WHITE)
        text(draw, (x + card_w // 2, 202), part, 30, INK, True, "mm")
        text(draw, (x + card_w // 2, 241), stock, 23, BLUE_DARK, True, "mm")
        px1, py1, px2, py2 = x + 38, 290, x + card_w - 38, 500
        draw.rounded_rectangle((px1, py1, px2, py2), 10, fill=OAK, outline=RULE, width=3)
        stave_w = (px2 - px1) / count
        for seam in range(1, count):
            sx = int(px1 + stave_w * seam)
            draw.line((sx, py1, sx, py2), fill=GREEN_DARK, width=6)
        text(draw, (x + card_w // 2, 535), "GREEN LINES = GLUE EDGES", 17, GREEN_DARK, True, "mm")
        wrapped(draw, (x + 34, 572), dims, 27, 19, MUTED)
    steps = [
        ("1", "Arrange grain and color"),
        ("2", "Joint paired edges"),
        ("3", "Dry seams close by hand"),
        ("4", "Spread thin Type II PVA"),
        ("5", "Clamp lightly with cauls"),
        ("6", "Cure, flatten, then size"),
    ]
    for idx, (number, label) in enumerate(steps):
        x = 52 + idx * 286
        card(draw, (x, 700, x + 266, 870), fill=PALE)
        draw.ellipse((x + 18, 730, x + 74, 786), fill=BLUE_DARK)
        text(draw, (x + 46, 758), number, 27, WHITE, True, "mm")
        wrapped(draw, (x + 90, 730), label, 18, 21, INK, True)
    card(draw, (52, 900, W - 52, 952), fill=RED, outline=RED_DARK)
    text(draw, (W // 2, 926), "NO FACE LAMINATION. NO PANEL-TO-FRAME GLUE.", 25, RED_DARK, True, "mm")
    save(image, "04b-panel-glue-map.png")


def spacer_map():
    image, draw = canvas(
        "FOAM SPACERS: FOUR PER PANEL",
        "Two spacers in each vertical side groove. No spacers in horizontal grooves and no glue on any panel tongue.",
    )
    card(draw, (52, 164, 1050, 900), WHITE)
    draw.rounded_rectangle((180, 250, 920, 820), 18, fill=BLUE, outline=INK, width=8)
    draw.rectangle((285, 355, 815, 715), fill=WHITE, outline=INK, width=5)
    draw.rectangle((330, 400, 770, 670), fill=OAK, outline=RULE, width=4)
    text(draw, (550, 535), "FLOATING PANEL", 35, INK, True, "mm")
    spacer_y = [450, 620]
    for sy in spacer_y:
        for sx in [304, 796]:
            draw.rounded_rectangle((sx - 16, sy - 30, sx + 16, sy + 30), 10, fill=GREEN, outline=GREEN_DARK, width=4)
    for sx, sy, label in [(304, 430, "2 LEFT"), (796, 430, "2 RIGHT")]:
        text(draw, (sx, sy - 65), label, 19, GREEN_DARK, True, "mm")
    text(draw, (550, 288), "NO SPACERS - HORIZONTAL GROOVE", 20, RED_DARK, True, "mm")
    text(draw, (550, 785), "NO SPACERS - HORIZONTAL GROOVE", 20, RED_DARK, True, "mm")

    card(draw, (1090, 164, 1748, 485), fill=PALE)
    text(draw, (1120, 194), "FULL-WIDTH FAMILY", 28, INK, True)
    text(draw, (1120, 240), "H / J / N", 32, BLUE_DARK, True)
    text(draw, (1120, 290), 'Total side clearance: 1/4"', 23, INK)
    text(draw, (1120, 330), 'Centered tongue-end gap: 3/16"', 23, INK)
    text(draw, (1120, 380), "Test as TP-SP-FW", 23, GREEN_DARK, True)

    card(draw, (1090, 515, 1748, 836), fill=PALE)
    text(draw, (1120, 545), "LOWER PAIR FAMILY", 28, INK, True)
    text(draw, (1120, 591), "K / L", 32, BLUE_DARK, True)
    text(draw, (1120, 641), 'Total side clearance: 1/8"', 23, INK)
    text(draw, (1120, 681), 'Centered tongue-end gap: 1/8"', 23, INK)
    text(draw, (1120, 731), "Test separately as TP-SP-L", 23, GREEN_DARK, True)

    card(draw, (1090, 866, 1748, 934), fill=RED, outline=RED_DARK)
    text(draw, (1419, 900), "Panels must still move sideways by hand.", 23, RED_DARK, True, "mm")
    save(image, "04c-spacer-placement-map.png")


def glue_storyboard():
    image, draw = canvas(
        "TWO-STAGE GLUE-UP: THE WHOLE SEQUENCE",
        "Panels and grooves always stay dry. Glue only mortises, tenons, and structural shoulders.",
    )
    steps = [
        ("1", "FULL DRY FIT", "Assemble all 13 wood parts. Check square, twist, shoulders, and panel movement.", BLUE),
        ("2", "STAGE A", "Glue only E-G-F joints using four 6 x 40 tenons. Capture K/L dry. Clamp square.", GREEN),
        ("3", "CURE + CHECK", "Let Stage A fully cure. Check K/L movement, square, and flatness.", OAK),
        ("4", "DRY FIT AGAIN", "Reassemble complete door with cured lower module. Time the Stage B rehearsal.", BLUE),
        ("5", "STAGE B", "Glue 26 frame tenons. Load from hinge stile A, close lock stile B in parallel.", GREEN),
        ("6", "FINAL GATE", "Check dimensions, diagonals, twist, shoulders, and all five moving panels before time expires.", OAK),
    ]
    x_positions = [52, 627, 1202]
    y_positions = [170, 540]
    for idx, (number, heading, body, fill) in enumerate(steps):
        x = x_positions[idx % 3]
        y = y_positions[idx // 3]
        card(draw, (x, y, x + 530, y + 300), fill=fill)
        draw.ellipse((x + 22, y + 24, x + 92, y + 94), fill=BLUE_DARK)
        text(draw, (x + 57, y + 59), number, 32, WHITE, True, "mm")
        text(draw, (x + 116, y + 34), heading, 28, INK, True)
        wrapped(draw, (x + 28, y + 124), body, 42, 23, INK)
        if idx not in {2, 5}:
            arrow(draw, (x + 500, y + 150), (x + 558, y + 150))
    card(draw, (52, 882, W - 52, 948), fill=RED, outline=RED_DARK)
    text(
        draw,
        (W // 2, 915),
        "STOP if glue skins, a panel binds, a shoulder needs heavy force, or the final check exceeds 75% of open time.",
        23,
        RED_DARK,
        True,
        "mm",
    )
    save(image, "07b-two-stage-glue-storyboard.png")


def fit_overlay():
    image, draw = canvas(
        "FROM JAM OPENING TO FINISHED DOOR",
        "Keep the jamb, prefit slab, and fitted slab as three separate measurements.",
    )
    center_x = 560
    top = 190
    jamb_w, jamb_h = 560, 700
    draw.rounded_rectangle((center_x - jamb_w // 2, top, center_x + jamb_w // 2, top + jamb_h), 8, outline=INK, width=10)
    draw.rectangle((center_x - 270, top + 8, center_x + 270, top + 685), outline=BLUE_DARK, width=7)
    draw.rectangle((center_x - 260, top + 17, center_x + 260, top + 672), fill=OAK, outline=OAK_DARK, width=6)
    text(draw, (center_x, top - 28), 'JAMB: 24" x 81"', 26, INK, True, "mm")
    text(draw, (center_x, top + 320), "FINISHED SLAB", 32, INK, True, "mm")
    text(draw, (center_x, top + 360), '23-3/4" x 80-1/2"', 28, INK, True, "mm")
    text(draw, (center_x, top + 410), 'PREFIT OUTLINE: 23-7/8" x 80-5/8"', 21, BLUE_DARK, True, "mm")
    text(draw, (center_x, top + 460), '1/8" HEAD GAP', 21, RED_DARK, True, "mm")
    text(draw, (center_x, top + 505), '1/8" EACH SIDE', 21, RED_DARK, True, "mm")
    text(draw, (center_x, top + 550), '3/8" BOTTOM GAP', 21, RED_DARK, True, "mm")

    x = 930
    steps = [
        ("1", "REMEASURE", "Confirm the finished jamb is still 24 x 81 at all required locations."),
        ("2", "CALCULATE", 'Width: 24 - 1/8 - 1/8 = 23-3/4. Height: 81 - 1/8 - 3/8 = 80-1/2.'),
        ("3", "COMPARE", "Overlay the fitted rectangle on the 23-7/8 x 80-5/8 cured prefit slab."),
        ("4", "MARK", "Record hinge, head, lock, and bottom removal. No single edge may require more than 1/16."),
        ("5", "FIT IN ORDER", "Hinge edge -> head -> lock edge/bevel -> bottom."),
    ]
    for idx, (number, heading, body) in enumerate(steps):
        y = 168 + idx * 152
        card(draw, (x, y, 1748, y + 130), fill=PALE)
        draw.ellipse((x + 18, y + 29, x + 78, y + 89), fill=BLUE_DARK)
        text(draw, (x + 48, y + 59), number, 27, WHITE, True, "mm")
        text(draw, (x + 102, y + 20), heading, 23, INK, True)
        wrapped(draw, (x + 102, y + 54), body, 55, 20, MUTED)
    save(image, "09d-prefit-finished-overlay.png")


def post_cure_map():
    image, draw = canvas(
        "POST-CURE SURFACING: STOP AT P100",
        "The cured door is already structural. Remove glue and minor accepted offsets without changing the fitted envelope.",
    )
    steps = [
        ("1", "CURE FLAT", "Keep the slab fully supported until the adhesive reaches full cure.", BLUE),
        ("2", "RECHECK", "Measure size, diagonals, twist, shoulders, face flush, and panel movement.", PALE),
        ("3", "SCRAPE", "Use a sharp scraper in raking light. Keep water out of white-oak pores.", OAK),
        ("4", "LEVEL", "Plane or block-sand only accepted minor offsets along the grain.", PALE),
        ("5", "SAND P100", "Sand the complete frame evenly through P100. Preserve crisp datum edges.", BLUE),
        ("6", "STOP", "Do not use P120 or apply frame finish before fitting and hardware release.", RED),
    ]
    for idx, (number, heading, body, fill) in enumerate(steps):
        x = 52 + (idx % 3) * 575
        y = 170 + (idx // 3) * 310
        card(draw, (x, y, x + 535, y + 248), fill=fill)
        draw.ellipse((x + 24, y + 24, x + 92, y + 92), fill=BLUE_DARK)
        text(draw, (x + 58, y + 58), number, 30, WHITE, True, "mm")
        text(draw, (x + 116, y + 34), heading, 28, INK, True)
        wrapped(draw, (x + 28, y + 122), body, 42, 23, INK)
        if idx not in {2, 5}:
            arrow(draw, (x + 505, y + 124), (x + 560, y + 124))
    card(draw, (52, 824, W - 52, 930), fill=RED, outline=RED_DARK)
    text(draw, (W // 2, 855), "PRESERVE THESE DATUMS", 25, RED_DARK, True, "mm")
    text(
        draw,
        (W // 2, 895),
        '1-3/8" thickness  |  square hinge/lock/head edges  |  rail-stile boundaries  |  five freely moving panels',
        23,
        INK,
        True,
        "mm",
    )
    save(image, "08b-post-cure-surfacing-map.png")


def generate():
    board_allocation()
    seam_map()
    datum_map()
    panel_glue_map()
    spacer_map()
    glue_storyboard()
    fit_overlay()
    post_cure_map()
    print(f"PASS: generated 8 visual clarity maps in {OUT}")


if __name__ == "__main__":
    generate()
