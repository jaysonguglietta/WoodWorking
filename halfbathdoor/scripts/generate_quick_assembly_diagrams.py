#!/usr/bin/env python3
"""Generate matched SVG and PNG assembly diagrams for the quick guide."""
from __future__ import annotations

import html
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "quick-guide/illustrations"
OUT.mkdir(parents=True, exist_ok=True)

W, H = 1500, 1000
INK = "#20272D"
BLUE = "#173A56"
TEAL = "#2E6F73"
OAK = "#C29359"
OAK_DARK = "#A46F36"
PANEL = "#E8D4AD"
PALE = "#F4F0E8"
RED = "#A33B32"
GRAY = "#65717A"


def font(size: int, bold: bool = False):
    choices = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
    ]
    for path in choices:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


class Scene:
    def __init__(self, number: int, title: str, subtitle: str):
        self.image = Image.new("RGB", (W, H), "white")
        self.draw = ImageDraw.Draw(self.image)
        self.svg = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
            '<rect width="1500" height="1000" fill="white"/>',
        ]
        self.rect(0, 0, W, 92, BLUE, BLUE, 0)
        self.circle(58, 46, 27, OAK, "white", 3)
        self.text(58, 46, str(number), 30, "white", True, "mm")
        self.text(105, 34, title, 34, "white", True, "lm")
        self.text(105, 69, subtitle, 20, "#DCE7EC", False, "lm")
        if number > 0:
            self.rect(1240, 18, 230, 56, RED, RED, 0)
            self.text(1355, 46, "DRY FIT / NO GLUE", 22, "white", True)
        self.text(30, 975, "DC-1916-001 | Rev. A | show face up | drawings not cutting templates", 17, GRAY, False, "lm")

    def rect(self, x, y, w, h, fill, outline=INK, width=3):
        self.draw.rectangle((x, y, x+w, y+h), fill=fill, outline=outline, width=width)
        self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{outline}" stroke-width="{width}"/>')

    def circle(self, x, y, r, fill, outline=INK, width=3):
        self.draw.ellipse((x-r, y-r, x+r, y+r), fill=fill, outline=outline, width=width)
        self.svg.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{outline}" stroke-width="{width}"/>')

    def line(self, points, fill=INK, width=4):
        self.draw.line(points, fill=fill, width=width, joint="curve")
        pts = " ".join(f"{x},{y}" for x, y in points)
        self.svg.append(f'<polyline points="{pts}" fill="none" stroke="{fill}" stroke-width="{width}" stroke-linejoin="round"/>')

    def polygon(self, points, fill, outline=INK, width=3):
        self.draw.polygon(points, fill=fill)
        if outline and width:
            self.draw.line(points + [points[0]], fill=outline, width=width, joint="curve")
        pts = " ".join(f"{x},{y}" for x, y in points)
        self.svg.append(f'<polygon points="{pts}" fill="{fill}" stroke="{outline}" stroke-width="{width}" stroke-linejoin="round"/>')

    def text(self, x, y, value, size=22, fill=INK, bold=False, anchor="mm"):
        f = font(size, bold)
        bbox = self.draw.textbbox((0, 0), value, font=f)
        tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
        if anchor == "mm":
            pos = (x-tw/2, y-th/2)
            svg_anchor, baseline = "middle", "middle"
        elif anchor == "lm":
            pos = (x, y-th/2)
            svg_anchor, baseline = "start", "middle"
        else:
            pos = (x-tw, y-th/2)
            svg_anchor, baseline = "end", "middle"
        self.draw.text(pos, value, font=f, fill=fill)
        weight = "700" if bold else "400"
        self.svg.append(f'<text x="{x}" y="{y}" fill="{fill}" font-family="Arial,Helvetica,sans-serif" font-size="{size}" font-weight="{weight}" text-anchor="{svg_anchor}" dominant-baseline="{baseline}">{html.escape(value)}</text>')

    def arrow(self, x1, y1, x2, y2, fill=TEAL, width=8, head=20):
        self.line([(x1, y1), (x2, y2)], fill, width)
        angle = math.atan2(y2-y1, x2-x1)
        left = (x2-head*math.cos(angle-.55), y2-head*math.sin(angle-.55))
        right = (x2-head*math.cos(angle+.55), y2-head*math.sin(angle+.55))
        self.draw.polygon([(x2, y2), left, right], fill=fill)
        pts = f"{x2},{y2} {left[0]},{left[1]} {right[0]},{right[1]}"
        self.svg.append(f'<polygon points="{pts}" fill="{fill}"/>')

    def domino(self, x, y, w=44, h=16):
        self.draw.rounded_rectangle((x, y, x+w, y+h), radius=h//2, fill=TEAL, outline=INK, width=2)
        self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{h/2}" fill="{TEAL}" stroke="{INK}" stroke-width="2"/>')

    def note(self, x, y, w, h, title, lines):
        self.rect(x, y, w, h, PALE, TEAL, 3)
        self.text(x+18, y+29, title, 25, BLUE, True, "lm")
        yy = y+67
        for value in lines:
            self.text(x+24, yy, "• " + value, 21, INK, False, "lm")
            yy += 34

    def save(self, slug):
        self.svg.append("</svg>")
        self.image.save(OUT / f"{slug}.png", dpi=(150, 150))
        (OUT / f"{slug}.svg").write_text("\n".join(self.svg) + "\n")


def door_frame(scene, x, y, scale=7.5, panels=True, labels=True, lock_stile=True):
    ow, oh = 24*scale, 79*scale
    sw = 4.5*scale
    scene.rect(x, y, sw, oh, OAK_DARK)
    if lock_stile:
        scene.rect(x+ow-sw, y, sw, oh, OAK_DARK)
    rail_data = [
        ("D-101C", 0, 4), ("D-101M", 17.5, 4), ("D-101D", 35.5, 7),
        ("D-101E", 52, 4), ("D-101F", 67, 12),
    ]
    for pid, top, height in rail_data:
        scene.rect(x+sw, y+top*scale, ow-2*sw, height*scale, OAK)
        if labels:
            scene.text(x+ow/2, y+(top+height/2)*scale, pid, 22, INK, True)
    scene.rect(x+ow/2-1.5*scale, y+56*scale, 3*scale, 11*scale, OAK_DARK)
    if labels:
        scene.text(x+ow/2, y+61.5*scale, "G", 22, INK, True)
    if panels:
        panel_rects = [
            ("D-101H", 4, 13.5, sw, ow-sw),
            ("D-101J", 21.5, 14, sw, ow-sw),
            ("D-101N", 42.5, 9.5, sw, ow-sw),
        ]
        for pid, top, height, left, right in panel_rects:
            scene.rect(x+left+5, y+top*scale+5, right-left-10, height*scale-10, PANEL, OAK_DARK, 2)
            scene.text(x+ow/2, y+(top+height/2)*scale, pid, 22, BLUE, True)
        bottom_w = 6*scale
        for pid, px in [("D-101K", x+sw), ("D-101L", x+sw+bottom_w+3*scale)]:
            scene.rect(px+5, y+56*scale+5, bottom_w-10, 11*scale-10, PANEL, OAK_DARK, 2)
            scene.text(px+bottom_w/2, y+61.5*scale, pid[-1], 21, BLUE, True)
    return ow, oh


def parts_map():
    s = Scene(1, "Lay out every cut part", "Confirm identifiers, orientation, and count before mortising.")
    door_frame(s, 90, 150, 8.7, True, True)
    s.note(370, 145, 440, 235, "Frame parts", [
        "D-101A/B: 4-1/2 x 79 stiles",
        "D-101C/M/E: 4 x 15 rails",
        "D-101D: 7 x 15 lock rail",
        "D-101F: 12 x 15 bottom rail",
        "D-101G: 3 x 11 muntin",
    ])
    s.note(370, 410, 440, 250, "Floating panels", [
        "D-101H/J/N: 15-3/4 wide",
        "D-101K/L: 6-7/8 wide",
        "All panel grain runs vertically",
        "Panel tongues are never glued",
    ])
    s.note(850, 145, 555, 515, "Mark before assembly", [
        "Show face on every frame member",
        "Reference face and reference edge",
        "Top and bottom of both stiles",
        "Top/reference edge of every rail",
        "Joint IDs at each rail end",
        "Panel ID on the back face",
        "Pair D-101K and D-101L visually",
        "Keep all show faces upward on bench",
    ])
    s.arrow(820, 735, 520, 735, TEAL, 7, 20)
    s.text(1110, 735, "If one label is missing, stop and remark the part.", 22, RED, True)
    s.save("01-parts-map")


def rail_stack_dimensions():
    s = Scene(0, "Story-stick rail stack", "All vertical locations originate at the top edge of the finished slab.")
    x, y, scale = 610, 135, 9.2
    ow, oh = door_frame(s, x, y, scale, True, True, True)
    positions = [
        (0, "0"),
        (4, "4"),
        (17.5, "17-1/2"),
        (21.5, "21-1/2"),
        (35.5, "35-1/2"),
        (42.5, "42-1/2"),
        (52, "52"),
        (56, "56"),
        (67, "67"),
        (79, "79"),
    ]
    dim_x = x - 125
    s.line([(dim_x, y), (dim_x, y+oh)], BLUE, 4)
    for pos, label in positions:
        yy = y + pos*scale
        s.line([(dim_x-12, yy), (x-8, yy)], BLUE, 3)
        s.text(dim_x-20, yy, label + " in", 18, BLUE, True, "rm")
    s.note(950, 170, 450, 290, "Use one master story stick", [
        "Hook the top of D-101A/B",
        "Knife every shoulder location",
        "Transfer to both stiles together",
        "Do not leapfrog a tape measure",
        "Stack must total exactly 79 inches",
    ])
    s.note(950, 510, 450, 250, "Opening checks", [
        "Upper: 13-1/2 inches",
        "Center: 14 inches",
        "Lower-center: 9-1/2 inches",
        "Bottom: 11 inches",
        "Bottom pair: 6 inches each",
    ])
    s.text(950, 830, "Top datum", 20, RED, True, "lm")
    s.arrow(1060, 830, x+ow/2, y, RED, 6, 18)
    s.save("00-rail-stack")


def groove_domino_register():
    s = Scene(0, "How the cut geometry nests", "Panel tongues float; shoulders close; concealed tenons remain in solid wood.")
    s.line([(500, 120), (500, 900)], GRAY, 2)
    s.line([(1000, 120), (1000, 900)], GRAY, 2)

    # Panel tongue entering a centered groove.
    s.text(250, 145, "PANEL / GROOVE", 28, BLUE, True)
    s.rect(70, 205, 360, 230, OAK)
    s.rect(215, 205, 70, 105, "white", INK, 4)
    panel_outline = [
        (130, 775), (370, 775), (370, 535), (305, 535),
        (278, 310), (222, 310), (195, 535), (130, 535),
    ]
    s.polygon(panel_outline, PANEL, TEAL, 4)
    s.arrow(250, 500, 250, 335, BLUE, 8, 22)
    s.text(250, 180, "1/4 W x 1/2 D GROOVE", 23, INK, True)
    s.text(250, 565, "7/32 TONGUE", 23, BLUE, True)
    s.text(250, 815, "NO GLUE ON TONGUE OR GROOVE", 22, RED, True)
    s.line([(205, 295), (295, 325)], RED, 6)
    s.line([(295, 295), (205, 325)], RED, 6)

    # Rail end, shoulder, tenons, and receiving stile mortises.
    s.text(750, 145, "RAIL / STILE", 28, BLUE, True)
    s.rect(525, 225, 125, 540, OAK_DARK)
    s.rect(610, 335, 40, 54, "white", TEAL, 4)
    s.rect(610, 565, 40, 54, "white", TEAL, 4)
    s.rect(805, 245, 150, 455, OAK)
    s.rect(805, 245, 150, 58, PALE, RED, 3)
    s.rect(805, 642, 150, 58, PALE, RED, 3)
    s.domino(735, 342, 70, 40)
    s.domino(735, 572, 70, 40)
    s.arrow(790, 470, 675, 470, TEAL, 9, 24)
    s.text(875, 475, "RAIL", 25, INK, True)
    s.text(588, 500, "STILE", 24, "white", True)
    s.text(880, 275, "GROOVE ZONE", 19, RED, True)
    s.text(880, 670, "GROOVE ZONE", 19, RED, True)
    s.text(750, 795, "GLUE: MORTISE WALLS + ALL TENON FACES", 20, TEAL, True)
    s.text(750, 835, "SHOULDER MUST CLOSE BY HAND", 21, RED, True)

    # Center muntin entering the lower intermediate and bottom rails.
    s.text(1250, 145, "MUNTIN / RAILS", 28, BLUE, True)
    s.rect(1040, 210, 420, 105, OAK)
    s.text(1250, 262, "D-101E", 24, INK, True)
    s.rect(1180, 410, 140, 245, OAK_DARK)
    s.text(1250, 532, "D-101G", 23, "white", True)
    s.rect(1040, 750, 420, 125, OAK)
    s.text(1250, 812, "D-101F", 24, INK, True)
    for xx in (1192, 1262):
        s.domino(xx, 350, 52, 24)
        s.domino(xx, 690, 52, 24)
    s.arrow(1250, 395, 1250, 325, TEAL, 8, 22)
    s.arrow(1250, 670, 1250, 738, TEAL, 8, 22)
    s.text(1085, 350, "2 x 6 x 40", 20, TEAL, True, "lm")
    s.text(1085, 705, "2 x 6 x 40", 20, TEAL, True, "lm")
    s.text(1250, 905, "G: 15/16 + 2-1/16 FROM G LEFT EDGE", 19, BLUE, True)
    s.text(1250, 938, "E/F: 6-15/16 + 8-1/16 FROM HINGE-SIDE SHOULDER", 18, RED, True)
    s.save("00-groove-domino")


def exploded_frame():
    s = Scene(2, "Dry-lay the frame in final order", "Use the master story stick; do not chain rail locations.")
    # stiles
    s.rect(105, 150, 62, 700, OAK_DARK)
    s.rect(1325, 150, 62, 700, OAK_DARK)
    rail_y = [(165, 44, "D-101C"), (320, 44, "D-101M"), (485, 75, "D-101D"), (655, 44, "D-101E"), (785, 100, "D-101F")]
    for yy, hh, pid in rail_y:
        s.rect(480, yy, 520, hh, OAK)
        s.text(740, yy+hh/2, pid, 22, INK, True)
        for j in range(2 if pid in ["D-101C","D-101M","D-101E"] else (3 if pid=="D-101D" else 4)):
            dy = yy+8+j*(hh-16)/max(1, (1 if pid in ["D-101C","D-101M","D-101E"] else (2 if pid=="D-101D" else 3)))
            s.domino(445, dy, 35, 13); s.domino(1000, dy, 35, 13)
        s.arrow(420, yy+hh/2, 180, yy+hh/2, TEAL, 6, 18)
        s.arrow(1060, yy+hh/2, 1310, yy+hh/2, TEAL, 6, 18)
    s.rect(716, 699, 48, 86, OAK_DARK)
    s.text(740, 742, "G", 16, "white", True)
    s.text(700, 742, "D-101G", 16, BLUE, True, "rm")
    s.domino(721, 690, 16, 9)
    s.domino(743, 690, 16, 9)
    s.domino(721, 785, 16, 9)
    s.domino(743, 785, 16, 9)
    s.text(136, 875, "D-101A / HINGE STILE", 17, BLUE, True)
    s.text(1356, 875, "D-101B / LOCK STILE", 17, BLUE, True)
    s.note(1080, 700, 340, 170, "Alignment rule", [
        "First mortise tight",
        "Followers medium",
        "All show faces up",
    ])
    s.save("02-exploded-frame")


def bottom_module():
    s = Scene(3, "Build the lower module first", "D-101E + D-101G + D-101F establish the paired bottom openings.")
    s.rect(250, 165, 1000, 78, OAK)
    s.text(750, 204, "D-101E  LOWER INTERMEDIATE RAIL", 24, INK, True)
    s.rect(250, 730, 1000, 150, OAK)
    s.text(750, 805, "D-101F  BOTTOM RAIL", 24, INK, True)
    s.rect(706, 290, 88, 390, OAK_DARK)
    s.text(750, 485, "D-101G", 20, "white", True)
    for x in (714, 758):
        s.domino(x, 250, 28, 18); s.domino(x, 690, 28, 18)
    s.arrow(750, 275, 750, 290, TEAL, 7, 18)
    s.arrow(750, 705, 750, 680, TEAL, 7, 18)
    s.rect(330, 325, 330, 330, PANEL, OAK_DARK, 3)
    s.text(495, 490, "D-101K", 28, BLUE, True)
    s.rect(840, 325, 330, 330, PANEL, OAK_DARK, 3)
    s.text(1005, 490, "D-101L", 28, BLUE, True)
    s.arrow(495, 300, 495, 325, BLUE, 7, 17)
    s.arrow(1005, 300, 1005, 325, BLUE, 7, 17)
    s.text(750, 920, "Panels float in grooves. Rehearse this subassembly dry before final glue-up.", 22, RED, True)
    s.save("03-bottom-module")


def load_hinge_stile():
    s = Scene(4, "Attach rails to the hinge stile and load panels", "Slide panels laterally from the open lock-stile end; keep the door show-face up.")
    s.rect(115, 135, 65, 745, OAK_DARK)
    s.text(100, 510, "D-101A", 18, BLUE, True, "rm")
    rails = [(160,40,"D-101C"),(310,40,"D-101M"),(470,70,"D-101D"),(640,40,"D-101E"),(780,100,"D-101F")]
    for yy,hh,pid in rails:
        s.rect(180, yy, 650, hh, OAK)
        s.text(505, yy+hh/2, pid, 20, INK, True)
    # bottom muntin already fitted
    s.rect(470, 680, 75, 100, OAK_DARK)
    # Panels are shown seated, with arrows indicating the required lateral
    # loading direction from the still-open lock-stile end.
    panels = [
        (235, 210, 530, 80, "D-101H"),
        (235, 370, 530, 80, "D-101J"),
        (235, 565, 530, 55, "D-101N"),
        (225, 690, 210, 70, "D-101K"),
        (580, 690, 210, 70, "D-101L"),
    ]
    for x,y,w,h,pid in panels:
        s.rect(x, y, w, h, PANEL, OAK_DARK, 3)
        s.text(x+w/2, y+h/2, pid, 20, BLUE, True)
    for yy in (250, 410, 592):
        s.arrow(1080, yy, 785, yy, BLUE, 7, 19)
    s.arrow(1080, 725, 830, 725, BLUE, 7, 19)
    s.text(1090, 165, "OPEN LOCK-STILE END", 20, RED, True)
    s.note(875, 650, 530, 230, "Loading order", [
        "Seat rails in D-101A",
        "Slide D-101H, J, and N leftward",
        "Slide lower module left as one unit",
        "Confirm every tongue is captured",
        "Do not use panel glue",
    ])
    s.save("04-load-panels")


def close_lock_stile():
    s = Scene(5, "Close the lock stile over every rail end", "Keep the stile parallel so the tenons enter together.")
    # assembled left portion
    door_frame(s, 180, 135, 8.8, True, False, False)
    # exposed tenons on right ends
    rail_top = [0,17.5,35.5,52,67]
    rail_h = [4,4,7,4,12]
    counts = [2,2,3,2,4]
    scale=8.8; x_end=180+(24-4.5)*scale
    for top, height, count in zip(rail_top, rail_h, counts):
        for j in range(count):
            yy=135+(top+(j+1)*height/(count+1))*scale
            s.domino(x_end-2, yy-7, 46, 14)
    stile_x=1110
    s.rect(stile_x, 135, 4.5*scale, 79*scale, OAK_DARK)
    s.text(stile_x+65, 480, "D-101B", 20, BLUE, True, "lm")
    s.arrow(stile_x-35, 330, x_end+60, 330, TEAL, 9, 24)
    s.arrow(stile_x-35, 650, x_end+60, 650, TEAL, 9, 24)
    s.note(850, 740, 540, 160, "Close evenly", [
        "Start every tenon by hand",
        "Tap only through a padded caul",
        "Stop if one shoulder hangs open",
    ])
    s.text(760, 115, "All panels already seated in their grooves", 22, BLUE, True)
    s.save("05-close-lock-stile")


def clamp_square():
    s = Scene(6, "Clamp, square, and verify movement", "Close shoulders first; use diagonal measurements to correct square.")
    x,y,scale=585,125,9.2
    ow,oh=door_frame(s,x,y,scale,True,False,True)
    # clamps
    clamp_ys=[y+35,y+185,y+355,y+520,y+690]
    for index, cy in enumerate(clamp_ys):
        clamp_color = BLUE if index % 2 == 0 else TEAL
        face_label = "FRONT" if index % 2 == 0 else "BACK"
        s.line([(x-170,cy),(x+ow+170,cy)], clamp_color, 9)
        s.rect(x-185,cy-28,24,56,clamp_color,clamp_color,0)
        s.rect(x+ow+161,cy-28,24,56,clamp_color,clamp_color,0)
        s.rect(x-14,cy-31,14,62,PALE,OAK_DARK,2)
        s.rect(x+ow,cy-31,14,62,PALE,OAK_DARK,2)
        s.arrow(x-130,cy-35,x-18,cy-35,clamp_color,6,17)
        s.arrow(x+ow+130,cy-35,x+ow+18,cy-35,clamp_color,6,17)
        s.text(x+ow+205, cy, face_label, 20, clamp_color, True, "lm")
    # diagonals
    s.line([(x,y),(x+ow,y+oh)],RED,5)
    s.line([(x+ow,y),(x,y+oh)],RED,5)
    s.text(x+ow/2,y+oh/2-20,"A",34,RED,True)
    s.text(x+ow/2,y+oh/2+25,"B",34,RED,True)
    # One visible side-play check; repeat at all five panels.
    panel_y = y + 27*scale
    s.arrow(x+ow/2, panel_y, x+55, panel_y, TEAL, 5, 14)
    s.arrow(x+ow/2, panel_y, x+ow-55, panel_y, TEAL, 5, 14)
    s.text(x+ow/2, panel_y-24, "SIDE PLAY", 18, TEAL, True)
    s.note(55, 155, 430, 265, "Acceptance", [
        "A - B <= 1/16 inch",
        "Twist <= 1/32 inch",
        "Shoulder gaps <= 0.005 inch",
        "Panels slide side-to-side",
        "Door remains 24 x 79 target",
    ])
    s.rect(55, 520, 430, 225, PALE, TEAL, 3)
    s.text(75, 550, "WINDING-STICK CHECK", 25, BLUE, True, "lm")
    s.rect(95, 600, 330, 22, BLUE, BLUE, 0)
    s.polygon([(95, 690), (425, 665), (425, 687), (95, 712)], TEAL, TEAL, 0)
    s.text(270, 655, "Sight across both sticks", 21, INK, True)
    s.text(270, 725, "Not parallel = twist - correct", 21, RED, True)
    s.save("06-clamp-square")


def generate():
    rail_stack_dimensions()
    groove_domino_register()
    parts_map()
    exploded_frame()
    bottom_module()
    load_hinge_stile()
    close_lock_stile()
    clamp_square()
    print(f"PASS: generated 8 shop diagrams in {OUT}")


if __name__ == "__main__":
    generate()
