#!/usr/bin/env python3
"""Generate dimension-controlled isometric renderings for the combined guide."""
from __future__ import annotations

import html
import json
import math
import csv
from fractions import Fraction
from pathlib import Path

from PIL import Image, ImageDraw

from generate_quick_assembly_diagrams import (
    BLUE,
    GRAY,
    INK,
    OAK,
    OAK_DARK,
    PALE,
    PANEL,
    RED,
    TEAL,
    font,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "cabinetmakers-guide" / "renderings"
SPEC_PATH = ROOT / "project" / "specification.yaml"
OUT.mkdir(parents=True, exist_ok=True)
MODEL = json.loads(SPEC_PATH.read_text())

W, H = 1600, 1050
WHITE = "#FFFFFF"
WALL = "#E7E4DE"
JAMB = "#D5AE72"
STOP = "#CDA36A"
BEECH = "#E2BE82"
SHADOW = "#D4D0C8"
TOP_LIGHT = "#E7C58F"
SIDE_DARK = "#875B2C"
PANEL_LIGHT = "#EAD7B1"
GREEN = "#547A58"
PALE_BLUE = "#EEF4F7"
PALE_TEAL = "#EDF5F4"
REVISION = MODEL["project"]["revision"]
OPENING = MODEL["opening"]
LABEL_SIZE = 24
DIMENSION_SIZE = 24


def shade(hex_color: str, factor: float) -> str:
    value = hex_color.lstrip("#")
    rgb = [int(value[i : i + 2], 16) for i in (0, 2, 4)]
    adjusted = [max(0, min(255, round(channel * factor))) for channel in rgb]
    return "#" + "".join(f"{channel:02X}" for channel in adjusted)


class IsoScene:
    """Matched PNG/SVG technical scene with an orthographic isometric projector."""

    def __init__(
        self,
        number: int | str,
        title: str,
        subtitle: str,
        badge: str,
        footer: str = "dimension-controlled isometric | written dimensions control",
    ):
        self.image = Image.new("RGB", (W, H), WHITE)
        self.draw = ImageDraw.Draw(self.image)
        self.svg = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
            f'<rect width="{W}" height="{H}" fill="{WHITE}"/>',
        ]
        self.rect(0, 0, W, 98, BLUE, BLUE, 0)
        self.circle(59, 49, 29, OAK, WHITE, 3)
        number_text = str(number)
        number_size = 23 if len(number_text) >= 3 else 28
        self.text(59, 49, number_text, number_size, WHITE, True)
        self.text(108, 35, title, 34, WHITE, True, "lm")
        self.text(108, 72, subtitle, 19, "#DCE7EC", False, "lm")
        self.rect(1320, 19, 245, 60, TEAL, TEAL, 0)
        self.text(1442, 49, badge, 21, WHITE, True)
        self.text(28, 1022, f"DC-1916-001 | {REVISION} | {footer}", 18, GRAY, False, "lm")

    def rect(self, x, y, w, h, fill, outline=INK, width=3):
        self.draw.rectangle((x, y, x + w, y + h), fill=fill, outline=outline, width=width)
        self.svg.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" '
            f'stroke="{outline}" stroke-width="{width}"/>'
        )

    def polygon(self, points, fill, outline=INK, width=3):
        clean = [(float(x), float(y)) for x, y in points]
        self.draw.polygon(clean, fill=fill)
        if outline and width:
            self.draw.line(clean + [clean[0]], fill=outline, width=width, joint="curve")
        data = " ".join(f"{x:.2f},{y:.2f}" for x, y in clean)
        self.svg.append(
            f'<polygon points="{data}" fill="{fill}" stroke="{outline}" '
            f'stroke-width="{width}" stroke-linejoin="round"/>'
        )

    def line(self, points, fill=INK, width=4, dash: str | None = None):
        clean = [(float(x), float(y)) for x, y in points]
        if dash:
            pattern = [max(1.0, float(value)) for value in dash.replace(",", " ").split()]
            if len(pattern) % 2:
                pattern *= 2
            for start, end in zip(clean, clean[1:]):
                dx, dy = end[0] - start[0], end[1] - start[1]
                length = math.hypot(dx, dy)
                if length <= 0:
                    continue
                distance = 0.0
                pattern_index = 0
                draw_segment = True
                while distance < length:
                    segment = min(pattern[pattern_index], length - distance)
                    if draw_segment:
                        a = (
                            start[0] + dx * distance / length,
                            start[1] + dy * distance / length,
                        )
                        b = (
                            start[0] + dx * (distance + segment) / length,
                            start[1] + dy * (distance + segment) / length,
                        )
                        self.draw.line([a, b], fill=fill, width=width)
                    distance += segment
                    pattern_index = (pattern_index + 1) % len(pattern)
                    draw_segment = not draw_segment
        else:
            self.draw.line(clean, fill=fill, width=width, joint="curve")
        data = " ".join(f"{x:.2f},{y:.2f}" for x, y in clean)
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        self.svg.append(
            f'<polyline points="{data}" fill="none" stroke="{fill}" '
            f'stroke-width="{width}" stroke-linejoin="round"{dash_attr}/>'
        )

    def circle(self, x, y, r, fill, outline=INK, width=3):
        self.draw.ellipse((x - r, y - r, x + r, y + r), fill=fill, outline=outline, width=width)
        self.svg.append(
            f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" '
            f'stroke="{outline}" stroke-width="{width}"/>'
        )

    def text(self, x, y, value, size=22, fill=INK, bold=False, anchor="mm"):
        chosen = font(size, bold)
        bbox = self.draw.textbbox((0, 0), value, font=chosen)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        if anchor == "mm":
            pos = (x - tw / 2, y - th / 2)
            svg_anchor, baseline = "middle", "middle"
        elif anchor == "lm":
            pos = (x, y - th / 2)
            svg_anchor, baseline = "start", "middle"
        else:
            pos = (x - tw, y - th / 2)
            svg_anchor, baseline = "end", "middle"
        self.draw.text(pos, value, font=chosen, fill=fill)
        weight = "700" if bold else "400"
        self.svg.append(
            f'<text x="{x}" y="{y}" fill="{fill}" font-family="Arial,Helvetica,sans-serif" '
            f'font-size="{size}" font-weight="{weight}" text-anchor="{svg_anchor}" '
            f'dominant-baseline="{baseline}">{html.escape(value)}</text>'
        )

    def arrow(self, x1, y1, x2, y2, fill=TEAL, width=6, head=18):
        self.line([(x1, y1), (x2, y2)], fill, width)
        angle = math.atan2(y2 - y1, x2 - x1)
        left = (x2 - head * math.cos(angle - 0.55), y2 - head * math.sin(angle - 0.55))
        right = (x2 - head * math.cos(angle + 0.55), y2 - head * math.sin(angle + 0.55))
        self.polygon([(x2, y2), left, right], fill, fill, 0)

    def note(
        self,
        x,
        y,
        w,
        h,
        title,
        lines,
        fill=PALE,
        body_size=20,
        line_height=33,
        title_size=25,
    ):
        self.rect(x, y, w, h, fill, TEAL, 3)
        self.text(x + 18, y + 30, title, title_size, BLUE, True, "lm")
        yy = y + 68
        for value in lines:
            self.text(x + 24, yy, "• " + value, body_size, INK, False, "lm")
            yy += line_height

    def callout(self, x, y, label, target, color=TEAL, align="lm"):
        self.text(x, y, label, LABEL_SIZE, color, True, align)
        start = (x + 8, y + 15) if align == "lm" else (x - 8, y + 15)
        self.arrow(start[0], start[1], target[0], target[1], color, 4, 13)

    def leader_label(self, x, y, label, target, color=BLUE, align="lm"):
        """External print-safe label with an elbow leader and no arrowhead."""
        self.text(x, y, label, LABEL_SIZE, color, True, align)
        start_x = x + 8 if align == "lm" else x - 8
        elbow_x = start_x + 48 if align == "lm" else start_x - 48
        self.line([(start_x, y + 14), (elbow_x, y + 14), target], color, 3)

    @staticmethod
    def project(
        point,
        origin=(760, 900),
        scale=9.0,
        angle_degrees=30.0,
        depth_factor=1.0,
    ):
        x, y, z = point
        angle = math.radians(angle_degrees)
        sx = origin[0] + scale * (x - y * depth_factor) * math.cos(angle)
        sy = origin[1] + scale * (x + y * depth_factor) * math.sin(angle) - scale * z
        return (sx, sy)

    def prism(
        self,
        x,
        y,
        z,
        width,
        depth,
        height,
        fill=OAK,
        origin=(760, 900),
        scale=9.0,
        depth_factor=1.0,
        outline=INK,
        line_width=2,
        label: str | None = None,
        label_color=INK,
    ):
        p = lambda xyz: self.project(xyz, origin, scale, 30, depth_factor)
        p000 = p((x, y, z))
        p100 = p((x + width, y, z))
        p110 = p((x + width, y + depth, z))
        p010 = p((x, y + depth, z))
        p001 = p((x, y, z + height))
        p101 = p((x + width, y, z + height))
        p111 = p((x + width, y + depth, z + height))
        p011 = p((x, y + depth, z + height))
        # Back/side first, front face last for crisp part identity.
        self.polygon([p100, p110, p111, p101], shade(fill, 0.72), outline, line_width)
        self.polygon([p001, p101, p111, p011], shade(fill, 1.16), outline, line_width)
        self.polygon([p000, p100, p101, p001], fill, outline, line_width)
        if label:
            center = p((x + width / 2, y - 0.01, z + height / 2))
            self.text(center[0], center[1], label, LABEL_SIZE, label_color, True)
        return {
            "front_center": p((x + width / 2, y, z + height / 2)),
            "top_center": p((x + width / 2, y + depth / 2, z + height)),
            "right_center": p((x + width, y + depth / 2, z + height / 2)),
            "corners": [p000, p100, p110, p010, p001, p101, p111, p011],
        }

    def arbitrary_prism(
        self,
        base_xy,
        z,
        height,
        fill,
        origin,
        scale,
        depth_factor=1.0,
        outline=INK,
        line_width=2,
    ):
        p = lambda xyz: self.project(xyz, origin, scale, 30, depth_factor)
        bottom = [p((x, y, z)) for x, y in base_xy]
        top = [p((x, y, z + height)) for x, y in base_xy]
        # Draw three likely visible side faces, then the top.
        for idx in (1, 2, 0):
            nxt = (idx + 1) % len(base_xy)
            self.polygon(
                [bottom[idx], bottom[nxt], top[nxt], top[idx]],
                shade(fill, 0.78 if idx == 1 else 1.0),
                outline,
                line_width,
            )
        self.polygon(top, shade(fill, 1.14), outline, line_width)
        return bottom, top

    def dimension(self, start, end, label, color=BLUE, offset=(0, 0)):
        x1, y1 = start[0] + offset[0], start[1] + offset[1]
        x2, y2 = end[0] + offset[0], end[1] + offset[1]
        self.line([(x1, y1), (x2, y2)], color, 3)
        angle = math.atan2(y2 - y1, x2 - x1)
        for x, y, reverse in [(x1, y1, False), (x2, y2, True)]:
            direction = angle + (math.pi if reverse else 0)
            left = (
                x + 13 * math.cos(direction - 0.55),
                y + 13 * math.sin(direction - 0.55),
            )
            right = (
                x + 13 * math.cos(direction + 0.55),
                y + 13 * math.sin(direction + 0.55),
            )
            self.polygon([(x, y), left, right], color, color, 0)
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        self.rect(mx - 72, my - 25, 144, 25, WHITE, WHITE, 0)
        self.text(mx, my - 13, label, DIMENSION_SIZE, color, True)

    def view_axes(self, x=1420, y=910):
        self.circle(x, y, 5, INK, INK, 0)
        self.arrow(x, y, x + 75, y + 42, BLUE, 4, 12)
        self.arrow(x, y, x - 70, y + 40, TEAL, 4, 12)
        self.arrow(x, y, x, y - 82, RED, 4, 12)
        self.text(x + 85, y + 48, "X", 17, BLUE, True)
        self.text(x - 82, y + 46, "Y", 17, TEAL, True)
        self.text(x, y - 96, "Z", 17, RED, True)

    def save(self, slug):
        self.svg.append("</svg>")
        self.image.save(OUT / f"{slug}.png", dpi=(180, 180))
        (OUT / f"{slug}.svg").write_text("\n".join(self.svg) + "\n")


def spec():
    return MODEL


def inch_label(value: float) -> str:
    """Return a shop-readable inch value at the project's 1/16-in resolution."""

    fraction = Fraction(value).limit_denominator(16)
    whole, remainder = divmod(fraction.numerator, fraction.denominator)
    if remainder == 0:
        return str(whole)
    if whole:
        return f"{whole}-{remainder}/{fraction.denominator}"
    return f"{remainder}/{fraction.denominator}"


def validate_installed_fit() -> None:
    """Fail if the fitted slab no longer resolves from the controlled jamb gaps."""

    expected_width = (
        OPENING["clear_width"]
        - OPENING["hinge_side_reveal"]
        - OPENING["lock_side_reveal"]
    )
    expected_height = (
        OPENING["clear_height"]
        - OPENING["head_reveal"]
        - OPENING["bottom_gap"]
    )
    if not math.isclose(
        expected_width, MODEL["slab"]["finished_width"], abs_tol=1e-9
    ):
        raise ValueError(
            f"installed fit derives {expected_width:g}-in slab width, not "
            f"{MODEL['slab']['finished_width']:g}"
        )
    if not math.isclose(
        expected_height, MODEL["slab"]["finished_height"], abs_tol=1e-9
    ):
        raise ValueError(
            f"installed fit derives {expected_height:g}-in slab height, not "
            f"{MODEL['slab']['finished_height']:g}"
        )


def rail_top_positions():
    """Derive rail top stations from the authoritative rail/opening stack."""

    frame = MODEL["frame"]
    rail_ids = ("D-101C", "D-101M", "D-101D", "D-101E", "D-101F")
    opening_ids = (
        "P-01 upper",
        "P-02 center",
        "P-03 lower-center",
        "P-04 bottom",
    )
    cursor = 0.0
    positions = {}
    for index, rail_id in enumerate(rail_ids):
        positions[rail_id] = cursor
        cursor += frame["rail_widths"][rail_id]
        if index < len(opening_ids):
            cursor += frame["vertical_openings"][opening_ids[index]]
    if not math.isclose(cursor, MODEL["slab"]["finished_height"], abs_tol=1e-9):
        raise ValueError(
            f"rail/opening stack is {cursor:g}, not "
            f"{MODEL['slab']['finished_height']:g}"
        )
    return positions


def panel_opening_tops():
    """Return top-origin opening stations for all five panels."""

    frame = MODEL["frame"]
    tops = rail_top_positions()
    return {
        "D-101H": tops["D-101C"] + frame["rail_widths"]["D-101C"],
        "D-101J": tops["D-101M"] + frame["rail_widths"]["D-101M"],
        "D-101N": tops["D-101D"] + frame["rail_widths"]["D-101D"],
        "D-101K": tops["D-101E"] + frame["rail_widths"]["D-101E"],
        "D-101L": tops["D-101E"] + frame["rail_widths"]["D-101E"],
    }


def panel_positions():
    """Return overall panel bounding boxes from the authoritative model."""
    components = {item["id"]: item for item in MODEL["components"]}
    frame = MODEL["frame"]
    groove_depth = MODEL["groove"]["depth"]
    full_clearance = MODEL["panels"]["full_width_clearance_across_grain_total"]
    small_clearance = MODEL["panels"]["small_width_clearance_across_grain_total"]
    end_clearance = MODEL["panels"]["clearance_parallel_to_grain_total"]
    stile = frame["stile_width"]
    bottom_each = frame["bottom_opening_each"]
    muntin = frame["muntin_width"]
    height = MODEL["slab"]["finished_height"]
    opening_keys = {
        "D-101H": "P-01 upper",
        "D-101J": "P-02 center",
        "D-101N": "P-03 lower-center",
        "D-101K": "P-04 bottom",
        "D-101L": "P-04 bottom",
    }
    opening_tops = panel_opening_tops()
    # Convert each opening's top-origin lower edge to bottom-origin coordinates.
    opening_bottoms = {
        pid: height - (
            opening_tops[pid] + frame["vertical_openings"][opening_keys[pid]]
        )
        for pid in opening_keys
    }
    rows = []
    for pid in ("D-101H", "D-101J", "D-101N", "D-101K", "D-101L"):
        item = components[pid]
        clearance = small_clearance if pid in {"D-101K", "D-101L"} else full_clearance
        opening_x = stile if pid != "D-101L" else stile + bottom_each + muntin
        x = opening_x - groove_depth + clearance / 2
        z = opening_bottoms[pid] - groove_depth + end_clearance / 2
        rows.append((pid, x, z, item["w"], item["l"]))
    return rows


def rail_geometry():
    frame = MODEL["frame"]
    rail_widths = frame["rail_widths"]
    height = MODEL["slab"]["finished_height"]
    top_positions = rail_top_positions()
    return [
        (
            pid,
            frame["stile_width"],
            height - top_positions[pid] - rail_widths[pid],
            frame["rail_shoulder_length"],
            rail_widths[pid],
        )
        for pid in ("D-101F", "D-101E", "D-101D", "D-101M", "D-101C")
    ]


def component(component_id: str) -> dict:
    return next(item for item in MODEL["components"] if item["id"] == component_id)


def rotate_xy(x: float, y: float, theta: float) -> tuple[float, float]:
    return (
        x * math.cos(theta) - y * math.sin(theta),
        x * math.sin(theta) + y * math.cos(theta),
    )


def rotated_rect(
    x: float,
    y: float,
    width: float,
    depth: float,
    theta: float,
) -> list[tuple[float, float]]:
    return [
        rotate_xy(x, y, theta),
        rotate_xy(x + width, y, theta),
        rotate_xy(x + width, y + depth, theta),
        rotate_xy(x, y + depth, theta),
    ]


def translated_rotated_rect(
    x: float,
    y: float,
    width: float,
    depth: float,
    theta: float,
    x_offset: float = 0.0,
    y_offset: float = 0.0,
) -> list[tuple[float, float]]:
    return [
        (px + x_offset, py + y_offset)
        for px, py in rotated_rect(x, y, width, depth, theta)
    ]


def draw_rotated_door(
    scene: IsoScene,
    theta_degrees: float,
    origin=(660, 920),
    scale=9.0,
    x_offset=0.0,
    y_offset=0.0,
    z_offset=0.0,
):
    """Draw the actual five-panel frame as rotated solids around the hinge edge."""
    theta = math.radians(theta_degrees)
    depth = MODEL["slab"]["finished_thickness"]
    frame = MODEL["frame"]

    # Floating panels are behind the show face and are therefore drawn first.
    for _, x, z, width, height in panel_positions():
        scene.arbitrary_prism(
            translated_rotated_rect(
                x, 0.44, width, 0.5, theta, x_offset, y_offset
            ),
            z + z_offset,
            height,
            PANEL_LIGHT,
            origin,
            scale,
            outline=OAK_DARK,
            line_width=2,
        )

    for x in (0.0, MODEL["slab"]["finished_width"] - frame["stile_width"]):
        scene.arbitrary_prism(
            translated_rotated_rect(
                x, 0.0, frame["stile_width"], depth, theta, x_offset, y_offset
            ),
            z_offset,
            MODEL["slab"]["finished_height"],
            OAK_DARK,
            origin,
            scale,
            outline=INK,
            line_width=2,
        )
    for _, x, z, width, height in rail_geometry():
        scene.arbitrary_prism(
            translated_rotated_rect(
                x, 0.0, width, depth, theta, x_offset, y_offset
            ),
            z + z_offset,
            height,
            OAK,
            origin,
            scale,
            outline=INK,
            line_width=2,
        )
    scene.arbitrary_prism(
        translated_rotated_rect(
            frame["stile_width"] + frame["bottom_opening_each"],
            0,
            frame["muntin_width"],
            depth,
            theta,
            x_offset,
            y_offset,
        ),
        frame["rail_widths"]["D-101F"] + z_offset,
        frame["vertical_openings"]["P-04 bottom"],
        OAK_DARK,
        origin,
        scale,
        outline=INK,
        line_width=2,
    )


def ortho_dimension(
    scene: IsoScene,
    start: tuple[float, float],
    end: tuple[float, float],
    label: str,
    text_offset=(0, -18),
    color=BLUE,
):
    """Print-safe two-ended dimension for orthographic insets."""
    scene.line([start, end], color, 3)
    x1, y1 = start
    x2, y2 = end
    angle = math.atan2(y2 - y1, x2 - x1)
    for x, y, reverse in ((x1, y1, False), (x2, y2, True)):
        direction = angle + (math.pi if reverse else 0)
        left = (
            x + 13 * math.cos(direction - 0.55),
            y + 13 * math.sin(direction - 0.55),
        )
        right = (
            x + 13 * math.cos(direction + 0.55),
            y + 13 * math.sin(direction + 0.55),
        )
        scene.polygon([(x, y), left, right], color, color, 0)
    if label:
        scene.text(
            (x1 + x2) / 2 + text_offset[0],
            (y1 + y2) / 2 + text_offset[1],
            label,
            DIMENSION_SIZE,
            color,
            True,
        )


def field_blank(scene: IsoScene, x: float, y: float, label: str, width=230):
    scene.text(x, y, label, 24, INK, True, "lm")
    scene.line([(x, y + 24), (x + width, y + 24)], GRAY, 3)


def scene_panel(
    scene: IsoScene,
    x: float,
    y: float,
    width: float,
    height: float,
    title: str,
    accent=BLUE,
    fill=WHITE,
):
    scene.rect(x, y, width, height, fill, accent, 3)
    scene.rect(x, y, width, 58, accent, accent, 0)
    scene.text(x + 22, y + 30, title, 27, WHITE, True, "lm")


def reference_marks(scene: IsoScene, x: float, y: float):
    scene.polygon([(x, y), (x + 24, y - 34), (x + 48, y)], BLUE, BLUE, 0)
    scene.arrow(x + 5, y + 38, x + 115, y + 38, TEAL, 5, 15)
    scene.text(x + 132, y + 38, "REF EDGE", 24, TEAL, True, "lm")


def draw_door(
    scene: IsoScene,
    origin=(665, 915),
    scale=9.6,
    exploded=False,
    show_labels=True,
    show_panels=True,
    show_tenons=False,
    include_lock_stile=True,
    x_offset=0.0,
    y_offset=0.0,
    z_offset=0.0,
):
    slab = MODEL["slab"]
    frame = MODEL["frame"]
    depth = slab["finished_thickness"]
    door_width = slab["finished_width"]
    door_height = slab["finished_height"]
    stile_width = frame["stile_width"]
    # Panels sit behind the show face; draw before the frame.
    if show_panels:
        for pid, x, z, width, height in panel_positions():
            px = x + x_offset
            py = y_offset + 0.44 + (-3.2 if exploded else 0)
            part = scene.prism(
                px,
                py,
                z + z_offset,
                width,
                0.5,
                height,
                PANEL_LIGHT,
                origin,
                scale,
                label=pid if show_labels else None,
                label_color=BLUE,
            )
            if exploded:
                target = scene.project(
                    (
                        x + x_offset + width / 2,
                        y_offset + 0.44,
                        z + z_offset + height / 2,
                    ),
                    origin,
                    scale,
                )
                scene.arrow(
                    part["front_center"][0],
                    part["front_center"][1],
                    target[0],
                    target[1],
                    BLUE,
                    4,
                    13,
                )

    stile_left_x = x_offset + (-4.0 if exploded else 0)
    stile_right_x = x_offset + (
        door_width - 0.5 if exploded else door_width - stile_width
    )
    scene.prism(
        stile_left_x,
        y_offset,
        z_offset,
        stile_width,
        depth,
        door_height,
        OAK_DARK,
        origin,
        scale,
        label="D-101A" if show_labels else None,
        label_color=WHITE,
    )
    if include_lock_stile:
        scene.prism(
            stile_right_x,
            y_offset,
            z_offset,
            stile_width,
            depth,
            door_height,
            OAK_DARK,
            origin,
            scale,
            label="D-101B" if show_labels else None,
            label_color=WHITE,
        )

    for pid, x, z, width, height in rail_geometry():
        rail_y = y_offset
        rail_x = x + x_offset
        part = scene.prism(
            rail_x,
            rail_y,
            z + z_offset,
            width,
            depth,
            height,
            OAK,
            origin,
            scale,
            label=pid if show_labels else None,
        )
        if exploded:
            left_target = scene.project(
                (
                    x_offset + stile_width,
                    y_offset + depth / 2,
                    z_offset + z + height / 2,
                ),
                origin,
                scale,
            )
            right_target = scene.project(
                (
                    x_offset + door_width - stile_width,
                    y_offset + depth / 2,
                    z_offset + z + height / 2,
                ),
                origin,
                scale,
            )
            scene.arrow(
                part["front_center"][0] - 55,
                part["front_center"][1],
                left_target[0] - 20,
                left_target[1],
                TEAL,
                3,
                11,
            )
            scene.arrow(
                part["front_center"][0] + 55,
                part["front_center"][1],
                right_target[0] + 20,
                right_target[1],
                TEAL,
                3,
                11,
            )
        if show_tenons:
            counts = {"D-101C": 2, "D-101M": 2, "D-101D": 3, "D-101E": 2, "D-101F": 4}
            for index in range(counts[pid]):
                tz = z + (index + 1) * height / (counts[pid] + 1) - 0.22
                scene.prism(
                    x_offset + x - 1.15,
                    y_offset + 0.35,
                    z_offset + tz,
                    1.15,
                    0.65,
                    0.44,
                    BEECH,
                    origin,
                    scale,
                    line_width=1,
                )
                scene.prism(
                    x_offset + x + width,
                    y_offset + 0.35,
                    z_offset + tz,
                    1.15,
                    0.65,
                    0.44,
                    BEECH,
                    origin,
                    scale,
                    line_width=1,
                )

    muntin_x = x_offset + stile_width + frame["bottom_opening_each"]
    scene.prism(
        muntin_x,
        y_offset,
        z_offset + frame["rail_widths"]["D-101F"],
        frame["muntin_width"],
        depth,
        frame["vertical_openings"]["P-04 bottom"],
        OAK_DARK,
        origin,
        scale,
        label="G" if show_labels else None,
        label_color=WHITE,
    )


def draw_installed_jamb(
    scene: IsoScene,
    origin,
    scale,
    y=0.65,
    jamb_thickness=0.75,
    jamb_depth=4.0,
    head_height=1.5,
):
    """Draw the installed 24 x 81 clear jamb independently of the fitted slab."""

    clear_width = OPENING["clear_width"]
    clear_height = OPENING["clear_height"]
    scene.prism(
        -jamb_thickness,
        y,
        0,
        jamb_thickness,
        jamb_depth,
        clear_height + head_height,
        JAMB,
        origin,
        scale,
    )
    scene.prism(
        clear_width,
        y,
        0,
        jamb_thickness,
        jamb_depth,
        clear_height + head_height,
        JAMB,
        origin,
        scale,
    )
    scene.prism(
        -jamb_thickness,
        y,
        clear_height,
        clear_width + 2 * jamb_thickness,
        jamb_depth,
        head_height,
        JAMB,
        origin,
        scale,
    )


def complete_system():
    s = IsoScene(
        1,
        "Complete door and millwork system",
        "The slab, jamb, stop, casing, backband, and optional cap are separate fitted layers.",
        "SYSTEM",
    )
    # Fit the complete wall/trim prism inside the drawing field with a clear
    # lower margin. The deeper wall solid extends farther down than the slab.
    origin, scale = (710, 835), 8.25
    door_width = MODEL["slab"]["finished_width"]
    door_height = MODEL["slab"]["finished_height"]
    opening_width = OPENING["clear_width"]
    opening_height = OPENING["clear_height"]
    door_x = OPENING["hinge_side_reveal"]
    door_z = OPENING["bottom_gap"]
    # Wall field behind everything.
    s.prism(
        -6.5,
        3.8,
        -2,
        opening_width + 13,
        0.6,
        opening_height + 7,
        WALL,
        origin,
        scale,
        outline=GRAY,
        line_width=1,
    )
    # Backband and casing.
    for x in (-5.625, opening_width + 4.5):
        s.prism(x, 2.2, 0, 1.125, 1.0, opening_height + 3.5, OAK_DARK, origin, scale)
    s.prism(
        -5.625,
        2.2,
        opening_height + 3.5,
        opening_width + 11.25,
        1.0,
        1.125,
        OAK_DARK,
        origin,
        scale,
    )
    for x in (-4.5, opening_width):
        s.prism(x, 1.45, 0, 4.5, 0.75, opening_height + 3.5, OAK, origin, scale)
    s.prism(
        -4.5,
        1.45,
        opening_height,
        opening_width + 9,
        0.75,
        4.5,
        OAK,
        origin,
        scale,
    )
    # Optional restrained cap.
    s.prism(
        -5.25,
        1.35,
        opening_height + 4.5,
        opening_width + 10.5,
        1.5,
        0.875,
        JAMB,
        origin,
        scale,
    )
    # The jamb controls a 24 x 81 clear opening; the slab is offset inside it
    # by the written 1/8-in side/head reveals and 3/8-in bottom gap.
    draw_installed_jamb(s, origin, scale)
    draw_door(
        s,
        origin,
        scale,
        exploded=False,
        show_labels=False,
        show_panels=True,
        x_offset=door_x,
        z_offset=door_z,
    )
    for x in (-0.35, opening_width - 0.05):
        s.prism(x, -0.3, 0.5, 0.375, 1.25, opening_height - 1.0, STOP, origin, scale)
    s.prism(0, -0.3, opening_height - 0.4, opening_width, 1.25, 0.375, STOP, origin, scale)
    s.callout(
        95,
        190,
        "M-204 CAP (OPTIONAL)",
        s.project((opening_width / 2, 2.1, opening_height + 5.4), origin, scale),
    )
    s.callout(85, 315, "M-202 BACKBAND", s.project((-5.1, 2.2, 59), origin, scale), BLUE)
    s.callout(80, 445, "M-201 CASING", s.project((-2.4, 1.45, 44), origin, scale))
    s.callout(
        1080,
        285,
        "24 × 81 CLEAR JAMB",
        s.project((opening_width + 0.3, 2.4, 67), origin, scale),
        BLUE,
    )
    s.callout(
        1080,
        415,
        "M-203 STOP",
        s.project((opening_width + 0.1, -0.1, 51), origin, scale),
    )
    s.callout(
        1085,
        560,
        "FITTED FIVE-PANEL SLAB",
        s.project((door_x + door_width - 4, 0, door_z + 37), origin, scale),
        BLUE,
    )
    s.note(
        1035,
        680,
        485,
        230,
        "Build boundary",
        [
            f"Jamb clear opening: {opening_width:g} × {opening_height:g}",
            f"Fitted slab: {inch_label(door_width)} × {inch_label(door_height)} × 1-3/8",
            "Side/head reveals: 1/8 each",
            "Bottom gap: 3/8 above finished floor",
        ],
        PALE_TEAL,
    )
    s.view_axes()
    s.save("01-complete-system")


def exploded_door():
    s = IsoScene(
        2,
        "Exploded five-panel door assembly",
        "Every part retains its project identifier; panels move forward and stiles move outward.",
        "13 PARTS",
    )
    origin, scale = (780, 850), 8.55
    draw_door(
        s,
        origin,
        scale,
        exploded=True,
        show_labels=False,
        show_panels=True,
        show_tenons=True,
    )

    door_height = MODEL["slab"]["finished_height"]
    rail_centers = {
        part_id: z + part_height / 2
        for part_id, _, z, _, part_height in rail_geometry()
    }
    muntin_center = (
        MODEL["frame"]["rail_widths"]["D-101F"]
        + MODEL["frame"]["vertical_openings"]["P-04 bottom"] / 2
    )
    door_width = MODEL["slab"]["finished_width"]
    door_center = door_width / 2
    targets = {
        "D-101A  HINGE STILE": s.project((-1.75, 0, door_height / 2), origin, scale),
        "D-101C  TOP RAIL": s.project((door_center, 0, rail_centers["D-101C"]), origin, scale),
        "D-101M  UPPER RAIL": s.project((door_center, 0, rail_centers["D-101M"]), origin, scale),
        "D-101D  LOCK RAIL": s.project((door_center, 0, rail_centers["D-101D"]), origin, scale),
        "D-101E  LOWER RAIL": s.project((door_center, 0, rail_centers["D-101E"]), origin, scale),
        "D-101F  BOTTOM RAIL": s.project((door_center, 0, rail_centers["D-101F"]), origin, scale),
        "D-101G  MUNTIN": s.project((door_center, 0, muntin_center), origin, scale),
        "D-101B  LOCK STILE": s.project((door_width + 1.75, 0, door_height / 2), origin, scale),
    }
    for pid, x, z, width, height in panel_positions():
        targets[f"{pid}  {component(pid)['name'].upper()}"] = s.project(
            (x + width / 2, -2.76, z + height / 2),
            origin,
            scale,
        )

    left_labels = [
        "D-101A  HINGE STILE",
        "D-101C  TOP RAIL",
        "D-101M  UPPER RAIL",
        "D-101D  LOCK RAIL",
        "D-101E  LOWER RAIL",
        "D-101F  BOTTOM RAIL",
        "D-101G  MUNTIN",
    ]
    right_labels = [
        "D-101B  LOCK STILE",
        "D-101H  UPPER PANEL",
        "D-101J  CENTER PANEL",
        "D-101N  LOWER-CENTER PANEL",
        "D-101K  LOWER-LEFT PANEL",
        "D-101L  LOWER-RIGHT PANEL",
    ]
    for index, label in enumerate(left_labels):
        s.leader_label(38, 170 + index * 108, label, targets[label], BLUE, "lm")
    for index, label in enumerate(right_labels):
        s.leader_label(1560, 170 + index * 118, label, targets[label], TEAL, "rm")

    s.rect(510, 875, 650, 82, PALE_TEAL, TEAL, 3)
    s.text(835, 904, "13 WOOD PARTS  |  30 FACTORY TENONS", 26, BLUE, True)
    s.text(835, 938, "Frame shoulders glue; all five panel tongues remain dry.", 24, INK)
    s.save("02-exploded-door")


def stock_milling():
    construction = MODEL["frame"]["construction"]
    s = IsoScene(
        3,
        "No-resaw frame lamination and seam control",
        "Width-rip I/K into one core and one back-face lane; plane whole B/C show-face billets, rest, press, and surface symmetrically.",
        "LS-05",
    )
    card_x = [40, 425, 810, 1195]
    for x, title in zip(
        card_x,
        (
            "1  RIP + PLANE LAYERS",
            "2  PRESS BOTH FACES",
            "3  SURFACE EQUALLY",
            "4  RELEASE D / F SEAMS",
        ),
    ):
        scene_panel(s, x, 145, 360, 620, title, TEAL if x in (425, 1195) else BLUE)

    # 1 — exploded preglue section.
    layer_x, layer_w = 105, 225
    layer_rows = (
        (255, 82, OAK_DARK, "SHOW FACE  5/16"),
        (375, 210, OAK, "CORE  7/8"),
        (623, 82, OAK_DARK, "BACK FACE  5/16"),
    )
    for y, height, color, label in layer_rows:
        s.rect(layer_x, y, layer_w, height, color, INK, 3)
        s.text(layer_x + layer_w / 2, y + height / 2, label, 21, WHITE if color == OAK_DARK else INK, True)
    s.text(
        220,
        228,
        "D-101A B/K/K • D-101B C/I/I (S/C/B)",
        14,
        TEAL,
        True,
    )
    s.text(220, 730, "STAGED PLANE • REST • NO RESAW", 18, RED, True)

    # 2 — simultaneous balanced press to a 1.500-inch glue blank.
    press_x, press_y, press_w, press_h = 500, 285, 210, 350
    pre_face_h = press_h * (
        construction["show_face_preglue_thickness"]
        / construction["glue_blank_thickness"]
    )
    pre_core_h = press_h * (
        construction["core_preglue_thickness"]
        / construction["glue_blank_thickness"]
    )
    s.rect(press_x, press_y, press_w, pre_face_h, OAK_DARK, INK, 3)
    s.rect(press_x, press_y + pre_face_h, press_w, pre_core_h, OAK, INK, 3)
    s.rect(
        press_x,
        press_y + pre_face_h + pre_core_h,
        press_w,
        pre_face_h,
        OAK_DARK,
        INK,
        3,
    )
    s.rect(press_x - 35, press_y - 28, press_w + 70, 22, "#42525C", INK, 2)
    s.rect(press_x - 35, press_y + press_h + 6, press_w + 70, 22, "#42525C", INK, 2)
    press_arrow_x = press_x + press_w + 35
    s.arrow(press_arrow_x, press_y - 75, press_arrow_x, press_y - 30, RED, 7, 18)
    s.arrow(press_arrow_x, press_y + press_h + 75, press_arrow_x, press_y + press_h + 30, RED, 7, 18)
    s.text(605, 230, "FLAT PLATEN + RIGID CAULS", 20, BLUE, True)
    s.text(605, 680, "1.500 GLUE BLANK", 24, TEAL, True)
    s.text(605, 720, "CURE • REST • AIR BOTH FACES", 18, RED, True)

    # 3 — final balanced section and equal removal.
    finish_x, finish_y, finish_w, finish_h = 885, 295, 210, 330
    final_face_h = finish_h * (
        construction["show_face_finished_thickness"]
        / MODEL["slab"]["finished_thickness"]
    )
    final_core_h = finish_h * (
        construction["core_preglue_thickness"]
        / MODEL["slab"]["finished_thickness"]
    )
    s.rect(finish_x, finish_y, finish_w, final_face_h, OAK_DARK, INK, 3)
    s.rect(finish_x, finish_y + final_face_h, finish_w, final_core_h, OAK, INK, 3)
    s.rect(
        finish_x,
        finish_y + final_face_h + final_core_h,
        finish_w,
        final_face_h,
        OAK_DARK,
        INK,
        3,
    )
    s.rect(finish_x, finish_y - 20, finish_w, 14, "#F3C6BF", RED, 2)
    s.rect(finish_x, finish_y + finish_h + 6, finish_w, 14, "#F3C6BF", RED, 2)
    s.text(990, 245, "REMOVE 1/16 EACH FACE", 20, RED, True)
    s.text(990, 670, "FINAL 1.375 ±0.010", 24, BLUE, True)
    s.text(990, 710, "1/4  +  7/8  +  1/4", 24, TEAL, True)

    # 4 — seam coordinates share the established rail-top datum. Each layer
    # gets its own band so every Rev. G bottom-rail seam remains legible.
    def seam_map(y, part_id, width_in, seam_layers):
        x, width, height = 1235, 280, 92
        s.text(x, y - 30, f"{part_id}  /  {width_in:g}-IN RAIL", 21, BLUE, True, "lm")
        band_height = height / 3
        layer_styles = (
            ("S", OAK_DARK, BLUE),
            ("C", OAK, TEAL),
            ("B", OAK_DARK, RED),
        )
        for index, ((layer_name, seams), (short_name, fill, seam_color)) in enumerate(
            zip(seam_layers.items(), layer_styles)
        ):
            band_y = y + index * band_height
            s.rect(x, band_y, width, band_height, fill, INK, 2)
            s.text(x + 12, band_y + band_height / 2, short_name, 14, WHITE, True, "lm")
            for seam in seams:
                sx = x + width * seam / width_in
                s.line([(sx, band_y), (sx, band_y + band_height)], seam_color, 5)
        centers = MODEL["domino"]["frame_centers_from_rail_top_in"][part_id]
        for center in centers:
            cx = x + width * center / width_in
            s.circle(cx, y + height / 2, 8, "#35454F", WHITE, 2)
        s.text(x + width / 2, y + height + 25, "● DF CENTER  |  S / C / B BANDS", 16, INK, True)

    stave_members = construction["stave_built_members"]
    seam_map(
        265,
        "D-101D",
        MODEL["frame"]["rail_widths"]["D-101D"],
        {
            "show": stave_members["D-101D"]["show_face_seams_from_finished_top"],
            "core": stave_members["D-101D"]["core_seams_from_finished_top"],
            "back": stave_members["D-101D"]["back_face_seams_from_finished_top"],
        },
    )
    seam_map(
        505,
        "D-101F",
        MODEL["frame"]["rail_widths"]["D-101F"],
        {
            "show": stave_members["D-101F"]["show_face_seams_from_finished_top"],
            "core": stave_members["D-101F"]["core_seams_from_finished_top"],
            "back": stave_members["D-101F"]["back_face_seams_from_finished_top"],
        },
    )
    s.text(1375, 730, "DOMINO CENTERS DO NOT MOVE", 19, RED, True)

    s.rect(100, 800, 1400, 160, PALE_TEAL, TEAL, 3)
    s.text(130, 835, "RELEASE CONTROLS", 26, BLUE, True, "lm")
    s.text(130, 874, "B/C: whole-billet 5/16 show faces. I/K: 4-3/8 core + back lanes. E/F: prove ≥5 clear 16-1/4 billets.", 19, INK, False, "lm")
    s.text(130, 910, "Coupon: void-free + wood failure  |  DF-to-glue line ≥0.200  |  seam ±1/32  |  paired thickness ≤0.005.", 19, RED, True, "lm")
    s.save("03-stock-milling")


def groove_panel_cutaway():
    s = IsoScene(
        4,
        "Panel groove and floating tongue cutaway",
        "The 7/32 +/-0.005-inch tongue enters a centered 1/4 x 1/2 groove without glue.",
        "CUTAWAY",
    )
    # Exact orthographic section; dimensions are read directly from the model.
    thickness = MODEL["slab"]["finished_thickness"]
    groove_w = MODEL["groove"]["width"]
    groove_d = MODEL["groove"]["depth"]
    groove_center = MODEL["groove"]["centerline_from_show_face"]
    tongue_t = MODEL["panels"]["tongue_thickness"]
    tongue_d = MODEL["panels"]["tongue_depth"]
    field_t = MODEL["panels"]["field_thickness"]
    bottom_clearance = MODEL["panels"]["tongue_bottom_clearance_nominal"]
    px = 320
    rail_x, rail_y = 230, 625
    rail_w, rail_h = thickness * px, 250
    groove_x = rail_x + (groove_center - groove_w / 2) * px
    groove_px_w = groove_w * px
    groove_px_d = groove_d * px

    s.text(450, 145, "EXACT CROSS-SECTION  /  SHOW FACE →", 27, BLUE, True)
    face_px = MODEL["frame"]["construction"]["show_face_finished_thickness"] * px
    core_px = MODEL["frame"]["construction"]["core_preglue_thickness"] * px
    s.rect(rail_x, rail_y, face_px, rail_h, OAK_DARK, INK, 3)
    s.rect(rail_x + face_px, rail_y, core_px, rail_h, OAK, INK, 3)
    s.rect(rail_x + face_px + core_px, rail_y, face_px, rail_h, OAK_DARK, INK, 3)
    s.line([(rail_x + face_px, rail_y), (rail_x + face_px, rail_y + rail_h)], TEAL, 3)
    s.line(
        [
            (rail_x + face_px + core_px, rail_y),
            (rail_x + face_px + core_px, rail_y + rail_h),
        ],
        TEAL,
        3,
    )
    s.rect(groove_x, rail_y, groove_px_w, groove_px_d, WHITE, BLUE, 4)
    foam_x = groove_x + 4
    foam_h = 52
    foam_y = rail_y + groove_px_d - foam_h
    foam_w = groove_px_w - 8
    s.rect(foam_x, foam_y, foam_w, foam_h, "#A8D2D0", TEAL, 3)
    for dot_x, dot_y in (
        (foam_x + 15, foam_y + 14),
        (foam_x + 36, foam_y + 29),
        (foam_x + 57, foam_y + 13),
        (foam_x + 20, foam_y + 42),
        (foam_x + 58, foam_y + 40),
    ):
        s.circle(dot_x, dot_y, 3, WHITE, WHITE, 1)
    s.text(rail_x + rail_w / 2, rail_y + 190, "1/4 + 7/8 CORE + 1/4", 23, INK, True)
    s.text(
        rail_x + rail_w / 2,
        rail_y + 226,
        "GROOVE STAYS IN 7/8 CORE",
        16,
        TEAL,
        True,
    )
    s.text(65, 585, "FOAM INSERT / COMPRESSED", 20, TEAL, True, "lm")
    s.line(
        [(70, 600), (180, 600), (foam_x + foam_w / 2, foam_y + foam_h / 2)],
        TEAL,
        3,
    )

    field_x = rail_x + (thickness - field_t) * px / 2
    field_w = field_t * px
    tongue_x = rail_x + (thickness - tongue_t) * px / 2
    tongue_w = tongue_t * px
    field_y, field_h = 240, 175
    tongue_y = field_y + field_h
    tongue_h = tongue_d * px
    s.rect(field_x, field_y, field_w, field_h, PANEL_LIGHT, BLUE, 4)
    s.rect(tongue_x, tongue_y, tongue_w, tongue_h, PANEL_LIGHT, BLUE, 4)
    s.text(field_x + field_w / 2, field_y + 75, "0.500 FIELD", 24, BLUE, True)
    s.arrow(
        tongue_x + tongue_w + 36,
        tongue_y + tongue_h - 25,
        groove_x + groove_px_w + 12,
        rail_y - 8,
        TEAL,
        7,
        20,
    )

    ortho_dimension(
        s,
        (rail_x, 925),
        (rail_x + rail_w, 925),
        "1.375",
        (0, -22),
    )
    ortho_dimension(
        s,
        (groove_x, rail_y - 38),
        (groove_x + groove_px_w, rail_y - 38),
        "0.250",
    )
    ortho_dimension(
        s,
        (groove_x + groove_px_w + 34, rail_y),
        (groove_x + groove_px_w + 34, rail_y + groove_px_d),
        "0.500",
        (70, 0),
    )
    ortho_dimension(
        s,
        (tongue_x, 220),
        (tongue_x + tongue_w, 220),
        "0.21875 ±0.005",
    )
    ortho_dimension(
        s,
        (tongue_x - 35, tongue_y),
        (tongue_x - 35, tongue_y + tongue_h),
        "0.4375 ±0.005",
        (-112, 0),
    )
    s.text(
        450,
        972,
        f"TONGUE BOTTOM CLEARANCE  {bottom_clearance:.4f}",
        24,
        RED,
        True,
    )

    # Corner-relief inset is a true plan view of the tongue perimeter.
    inset_x, inset_y = 840, 145
    s.rect(inset_x, inset_y, 650, 280, PALE_BLUE, BLUE, 3)
    s.text(inset_x + 24, inset_y + 38, "TONGUE CORNER RELIEF  /  PLAN", 27, BLUE, True, "lm")
    s.rect(inset_x + 60, inset_y + 85, 280, 150, PANEL_LIGHT, BLUE, 4)
    s.line(
        [
            (inset_x + 102, inset_y + 85),
            (inset_x + 102, inset_y + 127),
            (inset_x + 60, inset_y + 127),
        ],
        RED,
        7,
    )
    s.rect(inset_x + 60, inset_y + 85, 42, 42, WHITE, RED, 3)
    s.text(inset_x + 380, inset_y + 98, "REMOVE", 22, RED, True, "lm")
    s.text(inset_x + 380, inset_y + 138, "0.4375 × 0.4375", 20, RED, True, "lm")
    s.text(inset_x + 380, inset_y + 178, "ALL 4 CORNERS", 20, INK, True, "lm")
    s.text(inset_x + 420, inset_y + 258, "DO NOT CUT INTO 0.500 FIELD", 18, BLUE, True)

    # Separate longitudinal and cross-section views prevent the 0.750-inch
    # spacer length from being mistaken for a groove or panel dimension.
    spacer_inset_x, spacer_inset_y = 840, 455
    s.rect(spacer_inset_x, spacer_inset_y, 650, 210, PALE_TEAL, TEAL, 3)
    s.text(
        spacer_inset_x + 24,
        spacer_inset_y + 31,
        "FOAM PANEL SPACER  /  NOMINAL SIZE",
        25,
        BLUE,
        True,
        "lm",
    )
    spacer_x, spacer_y, spacer_w, spacer_h = 900, 550, 300, 54
    s.rect(spacer_x, spacer_y, spacer_w, spacer_h, "#A8D2D0", TEAL, 3)
    for dot_x in (930, 980, 1030, 1080, 1130, 1170):
        s.circle(dot_x, spacer_y + 27, 4, WHITE, WHITE, 1)
    ortho_dimension(
        s,
        (spacer_x, spacer_y - 14),
        (spacer_x + spacer_w, spacer_y - 14),
        "0.750 LENGTH",
        (0, -17),
        TEAL,
    )
    cross_x, cross_y, cross_size = 1290, 545, 62
    s.rect(cross_x, cross_y, cross_size, cross_size, "#A8D2D0", TEAL, 3)
    s.circle(cross_x + 21, cross_y + 19, 4, WHITE, WHITE, 1)
    s.circle(cross_x + 44, cross_y + 42, 4, WHITE, WHITE, 1)
    s.text(cross_x + cross_size / 2, 615, "0.265 × 0.265 NOM.", 17, BLUE, True)
    s.text(
        spacer_inset_x + 325,
        650,
        "COMPRESS; SAMPLE-TEST BOTH CLEARANCE FAMILIES",
        16,
        RED,
        True,
    )

    s.note(
        840,
        690,
        650,
        280,
        "Movement, spacer, and glue boundary",
        [
            "Full panels: 0.250 total side clearance",
            "Lower pair: 0.125 total side clearance",
            "Parallel clearance: 0.0625 total",
            "Prefinish edges; panel tongues remain dry",
            "Spacer does not set panel cut size",
        ],
        PALE_TEAL,
        body_size=22,
        line_height=37,
        title_size=26,
    )
    s.save("04-groove-panel-cutaway")


def rail_stile_joint():
    s = IsoScene(
        5,
        "DF 500 rail-to-stile joint",
        "The locator is tight and the follower medium; section and measure every relevant mortise-to-groove web.",
        "JOINT",
    )
    centers = MODEL["domino"]["frame_centers_from_rail_top_in"]["D-101C"]
    tight_width = (13 + 10) / 25.4
    medium_width = (19 + 10) / 25.4
    controlled_web = MODEL["fabrication_tolerances"][
        "frame_medium_mortise_web_to_panel_groove_min"
    ]
    scale = 120
    rail_x, rail_y = 230, 205
    rail_w, rail_h = 430, 4.0 * scale

    s.text(445, 150, "4-INCH RAIL  /  EDGE ELEVATION", 27, BLUE, True)
    s.rect(rail_x, rail_y, rail_w, rail_h, OAK, INK, 4)
    groove_px = MODEL["groove"]["depth"] * scale
    s.rect(rail_x, rail_y, rail_w, groove_px, PALE_BLUE, BLUE, 3)
    s.rect(rail_x, rail_y + rail_h - groove_px, rail_w, groove_px, PALE_BLUE, BLUE, 3)
    widths = [tight_width, medium_width]
    colors = [BLUE, TEAL]
    for index, (center, width_in, color) in enumerate(zip(centers, widths, colors)):
        cy = rail_y + center * scale
        h = width_in * scale
        s.rect(rail_x + 145, cy - h / 2, 140, h, "#35454F", WHITE, 2)
        s.text(
            rail_x + 315,
            cy,
            "TIGHT" if index == 0 else "MEDIUM",
            24,
            color,
            True,
            "lm",
        )
        ortho_dimension(
            s,
            (rail_x - 40, rail_y),
            (rail_x - 40, cy),
            f"{center:.2f}",
            (-58, 0),
            color,
        )
    s.line(
        [
            (rail_x + 120, rail_y + (centers[1] + medium_width / 2) * scale),
            (rail_x + 120, rail_y + rail_h - groove_px),
        ],
        RED,
        6,
    )
    s.text(
        rail_x + 115,
        rail_y + rail_h - 78,
        f"EACH RELEVANT WEB ≥ {controlled_web:.3f}",
        24,
        RED,
        True,
        "rm",
    )
    s.text(
        rail_x + rail_w / 2,
        rail_y + rail_h + 55,
        "PANEL GROOVES 0.250 W × 0.500 D",
        24,
        BLUE,
        True,
    )

    origin = (1010, 700)
    stile_width = MODEL["frame"]["stile_width"]
    s.prism(0, 0, 0, stile_width, 1.375, 15, OAK_DARK, origin, 18)
    rail = s.prism(7.4, 0, 5.5, 8.0, 1.375, 4, OAK, origin, 18)
    for center in (1.25, 2.75):
        z = 9.5 - center
        s.prism(
            stile_width - 0.35,
            0.35,
            z - 0.23,
            3.25,
            0.60,
            0.46,
            BEECH,
            origin,
            18,
            line_width=2,
        )
    s.arrow(
        rail["front_center"][0] - 15,
        rail["front_center"][1],
        s.project((stile_width + 0.2, 0.6, 7.5), origin, 18)[0],
        s.project((stile_width + 0.2, 0.6, 7.5), origin, 18)[1],
        TEAL,
        7,
        20,
    )
    s.leader_label(910, 190, "10 × 50 FACTORY TENONS", s.project((6.1, 0.6, 7.7), origin, 18))
    s.leader_label(
        910,
        265,
        "25 mm PLUNGE / MEMBER",
        s.project((stile_width, 0.6, 8.2), origin, 18),
        TEAL,
    )

    s.note(
        880,
        570,
        650,
        300,
        "DF 500 test-piece gate",
        [
            "10 mm cutter; fence 17.5 mm at 90°",
            "First position tight; follower medium",
            "Section both tight + medium groove webs",
            f"Every relevant measured web ≥{controlled_web:.3f}",
            "DF band to face glue line ≥0.200",
            "Shoulder gap ≤0.005; faces ≤0.010",
            "No groove intersection or breakout",
        ],
        PALE_TEAL,
        body_size=24,
        line_height=36,
        title_size=28,
    )
    s.save("05-rail-stile-joint")


def lower_module():
    s = IsoScene(
        6,
        "Lower rail-and-muntin module",
        "D-101E, D-101G, and D-101F form the only cured subassembly before the full frame glue-up.",
        "STAGE A",
    )
    origin, scale = (475, 900), 17
    frame = MODEL["frame"]
    depth = MODEL["slab"]["finished_thickness"]
    rail_length = frame["rail_shoulder_length"]
    bottom_each = frame["bottom_opening_each"]
    muntin_width = frame["muntin_width"]
    muntin_x = bottom_each
    module_center = rail_length / 2
    panel_clearance = MODEL["panels"]["clearance_parallel_to_grain_total"] / 2
    panel_z = frame["rail_widths"]["D-101F"] - MODEL["panels"]["tongue_depth"] + panel_clearance

    # Panels are drawn exploded forward; structural members retain true 12 + 11 + 4 stack.
    panel_targets = {}
    panel_x = {
        pid: x - MODEL["groove"]["depth"]
        + MODEL["panels"]["small_width_clearance_across_grain_total"] / 2
        for pid, x in (
            ("D-101K", 0.0),
            ("D-101L", bottom_each + muntin_width),
        )
    }
    for pid, x in panel_x.items():
        item = component(pid)
        panel = s.prism(
            x,
            -3.5,
            panel_z,
            item["w"],
            item["t"],
            item["l"],
            PANEL_LIGHT,
            origin,
            scale,
            label=None,
        )
        panel_targets[pid] = panel["front_center"]
        installed = s.project(
            (x + item["w"] / 2, 0.44, panel_z + item["l"] / 2),
            origin,
            scale,
        )
        s.arrow(panel["front_center"][0], panel["front_center"][1], installed[0], installed[1], BLUE, 5, 16)

    s.prism(0, 0, 23.0, rail_length, depth, 4, OAK, origin, scale)
    s.prism(0, 0, 0, rail_length, depth, 12, OAK, origin, scale)
    muntin = s.prism(
        muntin_x, -2.5, 12, muntin_width, depth, 11, OAK_DARK, origin, scale
    )
    receiver_centers = MODEL["domino"]["muntin_centers_in"][
        "D-101E and D-101F from hinge-side shoulder"
    ]
    for x in receiver_centers:
        s.prism(x, -1.25, 11.65, 0.50, 1.75, 0.38, BEECH, origin, scale, line_width=2)
        s.prism(x, -1.25, 22.95, 0.50, 1.75, 0.38, BEECH, origin, scale, line_width=2)
    installed_muntin = s.project(
        (muntin_x + muntin_width / 2, 0, 17.5), origin, scale
    )
    s.arrow(
        muntin["front_center"][0],
        muntin["front_center"][1],
        installed_muntin[0],
        installed_muntin[1],
        TEAL,
        7,
        20,
    )

    label_targets = {
        f"D-101E  {inch_label(rail_length)} × 4": s.project(
            (module_center, 0, 25), origin, scale
        ),
        f"D-101F  {inch_label(rail_length)} × 12": s.project(
            (module_center, 0, 6), origin, scale
        ),
        "D-101G  3 × 11": muntin["front_center"],
        (
            f"D-101K  {inch_label(component('D-101K')['w'])} × "
            f"{inch_label(component('D-101K')['l'])}"
        ): panel_targets["D-101K"],
        (
            f"D-101L  {inch_label(component('D-101L')['w'])} × "
            f"{inch_label(component('D-101L')['l'])}"
        ): panel_targets["D-101L"],
    }
    y_positions = [180, 285, 390, 495, 600]
    for (label, target), y in zip(label_targets.items(), y_positions):
        s.leader_label(45, y, label, target, BLUE if "101K" in label or "101L" in label else TEAL)

    s.note(
        965,
        155,
        555,
        330,
        "Stage A / controlled sequence",
        [
            "Four 6 × 40 mm factory tenons",
            "Glue E/G/F mortises and tenons only",
            "Preload 4 foam spacers - 3/4 in long; K/L dry",
            f"Clamp two clear {inch_label(bottom_each)} × 11 openings",
            "Cure fully; recheck panel travel",
        ],
        PALE_TEAL,
        body_size=24,
        line_height=43,
        title_size=28,
    )
    s.rect(965, 555, 555, 265, PALE_BLUE, BLUE, 3)
    s.text(995, 592, "VERTICAL STACK", 28, BLUE, True, "lm")
    s.text(995, 646, "BOTTOM RAIL  12.000", 24, INK, True, "lm")
    s.text(995, 690, "CLEAR OPENING  11.000", 24, INK, True, "lm")
    s.text(995, 734, "LOWER RAIL  4.000", 24, INK, True, "lm")
    s.text(995, 782, "TOTAL  27.000", 26, RED, True, "lm")
    s.save("06-lower-module")


def muntin_clearance():
    s = IsoScene(
        "6A",
        "Muntin mortise and groove clearance",
        "\u00a0\u00a0The corrected J-11/J-12 pattern preserves solid wood beside both panel grooves.",
        "CRITICAL JOINT",
    )
    tight_width = 19.0 / 25.4
    medium_width = 25.0 / 25.4
    cutter_height = 6.0 / 25.4
    groove_depth = MODEL["groove"]["depth"]
    groove_width = MODEL["groove"]["width"]
    centers_g = MODEL["domino"]["muntin_centers_in"]["D-101G from left reference edge"]
    centers_rail = MODEL["domino"]["muntin_centers_in"][
        "D-101E and D-101F from hinge-side shoulder"
    ]
    footprint = MODEL["groove"]["muntin_footprint_from_hinge_side_rail_shoulder"]

    # Enlarged D-101G end grain. Colored overlays lie directly on the end plane:
    # blue = panel groove; charcoal = Domino mortise.
    muntin_origin, muntin_scale, top_z = (365, 845), 66, 6.0
    s.prism(
        0,
        0,
        0,
        3.0,
        MODEL["slab"]["finished_thickness"],
        top_z,
        OAK_DARK,
        muntin_origin,
        muntin_scale,
        label="D-101G",
        label_color=WHITE,
    )

    def muntin_plane(x1, y1, x2, y2, z):
        return [
            s.project((x1, y1, z), muntin_origin, muntin_scale),
            s.project((x2, y1, z), muntin_origin, muntin_scale),
            s.project((x2, y2, z), muntin_origin, muntin_scale),
            s.project((x1, y2, z), muntin_origin, muntin_scale),
        ]

    groove_y1 = (MODEL["slab"]["finished_thickness"] - groove_width) / 2
    groove_y2 = groove_y1 + groove_width
    s.polygon(
        muntin_plane(0, groove_y1, groove_depth, groove_y2, top_z + 0.01),
        PALE_BLUE,
        BLUE,
        2,
    )
    s.polygon(
        muntin_plane(3.0 - groove_depth, groove_y1, 3.0, groove_y2, top_z + 0.01),
        PALE_BLUE,
        BLUE,
        2,
    )
    for center in centers_g:
        s.polygon(
            muntin_plane(
                center - tight_width / 2,
                0.6875 - cutter_height / 2,
                center + tight_width / 2,
                0.6875 + cutter_height / 2,
                top_z + 0.02,
            ),
            "#35454F",
            WHITE,
            1,
        )
    left_web = centers_g[0] - tight_width / 2 - groove_depth
    right_web = 3.0 - groove_depth - (centers_g[1] + tight_width / 2)
    center_tolerance = MODEL["domino"]["mortise_centerline_tolerance_plus_minus"]
    groove_depth_plus = MODEL["fabrication_tolerances"]["groove_depth"]["plus"]
    worst_side_web = min(left_web, right_web) - center_tolerance - groove_depth_plus
    nominal_g_inter_web = centers_g[1] - centers_g[0] - tight_width
    worst_g_inter_web = nominal_g_inter_web - 2 * center_tolerance
    left_target = s.project(
        ((groove_depth + centers_g[0] - tight_width / 2) / 2, 0.6875, top_z),
        muntin_origin,
        muntin_scale,
    )
    right_target = s.project(
        (
            (3.0 - groove_depth + centers_g[1] + tight_width / 2) / 2,
            0.6875,
            top_z,
        ),
        muntin_origin,
        muntin_scale,
    )
    s.callout(
        75,
        205,
        "1/2-DEEP PANEL GROOVE",
        s.project((0.2, 0.6875, top_z), muntin_origin, muntin_scale),
        BLUE,
    )
    s.callout(
        80,
        345,
        "TWO 19 mm TIGHT MORTISES",
        s.project((1.5, 0.6875, top_z), muntin_origin, muntin_scale),
    )
    s.text(85, 505, f"LEFT WEB  {left_web:.3f} in", 24, RED, True, "lm")
    s.arrow(310, 520, left_target[0], left_target[1], RED, 4, 13)
    s.text(85, 635, f"RIGHT WEB  {right_web:.3f} in", 24, RED, True, "lm")
    s.arrow(325, 650, right_target[0], right_target[1], RED, 4, 13)

    s.note(
        885,
        150,
        625,
        300,
        "D-101G end-grain rule",
        [
            "Mortise centers: 1.000 and 2.000",
            "Both mortises use the 19 mm tight setting",
            "6 mm cutter; 20 mm plunge into D-101G",
            f"Nominal side webs: {left_web:.3f} / {right_web:.3f}",
            f"Worst groove-to-mortise: {worst_side_web:.3f} ≥ 0.100",
            f"Worst G inter-mortise: {worst_g_inter_web:.3f} ≥ 0.220",
        ],
        PALE_BLUE,
        body_size=24,
        line_height=34,
        title_size=27,
    )

    # Mating rail region. The two groove runs stop at the controlled footprint
    # boundaries, leaving the full three-inch muntin landing intact.
    rail_origin, rail_scale, rail_top = (760, 555), 30, 2.6
    s.prism(
        0,
        0,
        0,
        MODEL["frame"]["rail_shoulder_length"],
        1.375,
        rail_top,
        OAK,
        rail_origin,
        rail_scale,
    )

    def rail_plane(x1, y1, x2, y2, z):
        return [
            s.project((x1, y1, z), rail_origin, rail_scale),
            s.project((x2, y1, z), rail_origin, rail_scale),
            s.project((x2, y2, z), rail_origin, rail_scale),
            s.project((x1, y2, z), rail_origin, rail_scale),
        ]

    s.polygon(
        rail_plane(footprint[0], 0, footprint[1], 1.375, rail_top + 0.01),
        "#E8F1E8",
        GREEN,
        2,
    )
    for start, end in MODEL["groove"]["segmented_rail_edges"]["D-101E bottom"]:
        s.polygon(
            rail_plane(start, groove_y1, end, groove_y2, rail_top + 0.02),
            PALE_BLUE,
            BLUE,
            2,
        )
    for index, (center, slot_width) in enumerate(
        zip(centers_rail, (tight_width, medium_width))
    ):
        s.polygon(
            rail_plane(
                center - slot_width / 2,
                0.6875 - cutter_height / 2,
                center + slot_width / 2,
                0.6875 + cutter_height / 2,
                rail_top + 0.03,
            ),
            "#35454F",
            WHITE,
            1,
        )
        point = s.project((center, 0.6875, rail_top), rail_origin, rail_scale)
        s.text(
            point[0],
            point[1] - 28,
            "T" if index == 0 else "M",
            24,
            BLUE,
            True,
        )
    s.callout(
        1070,
        500,
        (
            f"SOLID {inch_label(footprint[0])}–"
            f"{inch_label(footprint[1])} in FOOTPRINT"
        ),
        s.project(
            ((footprint[0] + footprint[1]) / 2, 0.95, rail_top),
            rail_origin,
            rail_scale,
        ),
        GREEN,
    )
    rail_inter_web = centers_rail[1] - centers_rail[0] - (tight_width + medium_width) / 2
    worst_rail_inter_web = rail_inter_web - 2 * center_tolerance
    s.rect(830, 795, 700, 175, PALE_TEAL, TEAL, 3)
    s.text(880, 838, "MATING RAIL CENTERS", 27, BLUE, True, "lm")
    s.text(
        880,
        884,
        (
            f"{centers_rail[0]:.3f} tight  |  {centers_rail[1]:.3f} medium  |  "
            f"groove: 0–{inch_label(footprint[0])} and "
            f"{inch_label(footprint[1])}–"
            f"{inch_label(MODEL['frame']['rail_shoulder_length'])}"
        ),
        24,
        INK,
        False,
        "lm",
    )
    s.text(
        880,
        922,
        "RAIL-RECEIVER INTER-MORTISE WEB",
        20,
        RED,
        True,
        "lm",
    )
    s.text(
        880,
        950,
        f"nominal {rail_inter_web:.3f}; worst {worst_rail_inter_web:.3f} ≥ 0.100",
        19,
        RED,
        True,
        "lm",
    )
    s.view_axes(760, 940)
    s.save("06a-muntin-clearance")


def frame_loading():
    s = IsoScene(
        7,
        "Load the frame from the hinge stile",
        "Stage 3/4-in-long foam panel spacers before loading parts; close D-101B evenly.",
        "STAGE B",
    )
    origin, scale = (700, 850), 8.8
    door_width = MODEL["slab"]["finished_width"]
    door_height = MODEL["slab"]["finished_height"]
    draw_door(
        s,
        origin,
        scale,
        exploded=False,
        show_labels=False,
        show_panels=True,
        show_tenons=True,
        include_lock_stile=False,
    )
    lock = s.prism(
        door_width + 3.5,
        -2.3,
        0,
        MODEL["frame"]["stile_width"],
        1.375,
        door_height,
        OAK_DARK,
        origin,
        scale,
    )
    lock_stile_center = door_width - MODEL["frame"]["stile_width"] / 2
    target_top = s.project((lock_stile_center, 0.3, door_height - 15), origin, scale)
    target_low = s.project((lock_stile_center, 0.3, 22), origin, scale)
    s.arrow(lock["front_center"][0] - 20, lock["front_center"][1] - 190, target_top[0], target_top[1], TEAL, 7, 20)
    s.arrow(lock["front_center"][0] - 20, lock["front_center"][1] + 180, target_low[0], target_low[1], TEAL, 7, 20)
    label_targets = [
        (
            "1  A + 8 FOAM SPACERS",
            s.project(
                (MODEL["frame"]["stile_width"] / 2, 0, door_height - 16),
                origin,
                scale,
            ),
            BLUE,
        ),
        ("2  C/M/D — THEN H/J", s.project((door_width / 2, 0.44, door_height - 28), origin, scale), TEAL),
        ("3  CURED E/G/F + K/L MODULE", s.project((door_width / 2, 0.2, 18), origin, scale), BLUE),
        ("4  N SLIDES THROUGH D/E", s.project((door_width / 2, 0.44, 31), origin, scale), TEAL),
        ("5  B + 8 FOAM SPACERS", lock["front_center"], RED),
    ]
    for index, (label, target, color) in enumerate(label_targets):
        s.leader_label(40, 180 + index * 123, label, target, color)

    s.rect(1030, 160, 500, 330, PALE_TEAL, TEAL, 3)
    s.text(1060, 198, "CONTROLLED CLOSURE", 28, BLUE, True, "lm")
    for index, line in enumerate(
        [
            "Stage 3/4-in-long foam spacers first.",
            "Seat the cured module as one unit.",
            "Start every lock-side tenon and tongue.",
            "Keep A and B parallel.",
            "No clamp force to start a joint.",
        ]
    ):
        s.text(1060, 250 + index * 48, "• " + line, 24, INK, False, "lm")
    s.rect(1050, 730, 460, 150, "#FAEFEC", RED, 3)
    s.text(1080, 770, "SECOND WHOLE-DOOR DRY FIT", 25, RED, True, "lm")
    s.text(1080, 818, "Required after Stage A has fully cured.", 24, INK, False, "lm")
    s.text(1080, 858, "Release only after panels move by hand.", 21, BLUE, True, "lm")
    s.save("07-frame-loading")


def clamp_geometry():
    s = IsoScene(
        8,
        "Clamp, square, and remove twist",
        "Keep the Stage B timer live through final geometry and five-panel movement; clamp complete is only a checkpoint.",
        "GEOMETRY",
    )
    origin, scale = (660, 930), 8.8
    door_height = MODEL["slab"]["finished_height"]
    draw_door(s, origin, scale, exploded=False, show_labels=False, show_panels=True)
    geometry = {part_id: (z, part_height) for part_id, _, z, _, part_height in rail_geometry()}
    rail_z = [
        geometry[part_id][0] + geometry[part_id][1] / 2
        for part_id in ("D-101C", "D-101M", "D-101D", "D-101E", "D-101F")
    ]
    for index, z in enumerate(rail_z):
        face_y = -1.1 if index % 2 == 0 else 2.6
        left = s.project((-5, face_y, z), origin, scale)
        right = s.project((29, face_y, z), origin, scale)
        color = BLUE if index % 2 == 0 else TEAL
        s.line([left, right], color, 7)
        s.rect(left[0] - 16, left[1] - 24, 18, 48, color, color, 0)
        s.rect(right[0] - 2, right[1] - 24, 18, 48, color, color, 0)
        s.text(
            right[0] + 26,
            right[1],
            f"{index + 1}  {'FRONT' if index % 2 == 0 else 'BACK'}",
            24,
            color,
            True,
            "lm",
        )
        s.arrow(left[0] - 44, left[1], left[0] - 2, left[1], color, 5, 14)
        s.arrow(right[0] + 44, right[1], right[0] + 2, right[1], color, 5, 14)
    a = s.project((0, -0.05, door_height), origin, scale)
    door_width = MODEL["slab"]["finished_width"]
    b = s.project((door_width, -0.05, 0), origin, scale)
    c = s.project((door_width, -0.05, door_height), origin, scale)
    d = s.project((0, -0.05, 0), origin, scale)
    s.line([a, b], RED, 4, "12 8")
    s.line([c, d], RED, 4, "12 8")
    # Keep the diagonal identifiers out of the door and alternating clamp paths.
    # A compact orientation key is easier to read than labels laid over the work.
    s.rect(50, 530, 500, 150, "#FAEFEC", RED, 3)
    s.text(75, 560, "DIAGONAL MAP", 24, RED, True, "lm")
    s.line([(78, 610), (132, 610)], RED, 4, "12 8")
    s.text(154, 610, "A  TOP HINGE TO BOTTOM LOCK", 20, INK, True, "lm")
    s.line([(78, 650), (132, 650)], RED, 4, "12 8")
    s.text(154, 650, "B  TOP LOCK TO BOTTOM HINGE", 20, INK, True, "lm")
    s.note(
        50,
        150,
        500,
        350,
        "Live final gate",
        [
            "Diagonal A - B <= 1/16",
            "Twist <= 1/32 with winding sticks",
            "Shoulder gaps <= 0.005",
            "All five panels move laterally",
            "Clamp complete = checkpoint only",
            "Final gate <=75% of published OPEN time",
        ],
        body_size=22,
        line_height=39,
        title_size=28,
    )
    # Winding-stick inset: the two top edges must read parallel from the viewing end.
    s.rect(1030, 630, 500, 270, PALE_BLUE, BLUE, 3)
    s.text(1060, 670, "WINDING-STICK CHECK", 28, BLUE, True, "lm")
    s.rect(1090, 735, 330, 25, BLUE, BLUE, 0)
    s.rect(1130, 815, 330, 25, TEAL, TEAL, 0)
    s.line([(1090, 725), (1420, 725)], GRAY, 3, "12 8")
    s.line([(1130, 805), (1460, 805)], GRAY, 3, "12 8")
    s.text(1280, 872, "PARALLEL EDGES = NO TWIST", 24, RED, True)
    s.save("08-clamp-geometry")


def hanging_system():
    s = IsoScene(
        9,
        "Fit, hinge, and dry-cycle the bare slab",
        "The completed jamb controls prefinish edge fit and hardware transfer; use steel setup screws.",
        "HARDWARE",
    )
    origin, scale = (660, 840), 9.0
    opening_width = OPENING["clear_width"]
    opening_height = OPENING["clear_height"]
    door_x = OPENING["hinge_side_reveal"]
    door_z = OPENING["bottom_gap"]
    door_height = MODEL["slab"]["finished_height"]
    # The clear jamb remains fixed at 24 x 81 while the fitted slab swings
    # around the offset hinge edge.
    draw_installed_jamb(s, origin, scale, y=1.8)
    theta = math.radians(28)
    draw_rotated_door(
        s,
        28,
        origin,
        scale,
        x_offset=door_x,
        z_offset=door_z,
    )
    illustrative_hinges = (7, door_height / 2, door_height - 7)
    for z in illustrative_hinges:
        hinge = s.project((door_x - 0.1, 0.0, door_z + z), origin, scale)
        s.rect(hinge[0] - 5, hinge[1] - 22, 10, 44, "#C5A24C", INK, 1)
    knob_radius = MODEL["slab"]["finished_width"] - 2.75
    knob = s.project(
        (
            door_x + knob_radius * math.cos(theta),
            knob_radius * math.sin(theta),
            door_z + MODEL["hardware"]["nominal_lock_center_above_slab_bottom"],
        ),
        origin,
        scale,
    )
    s.circle(knob[0], knob[1], 8, "#C5A24C", INK, 2)
    s.callout(
        90,
        225,
        "3 × 3-1/2 BRASS HINGE LEAVES",
        s.project((door_x, 0, door_z + illustrative_hinges[-1]), origin, scale),
        BLUE,
    )
    s.text(90, 275, "STEEL SETUP SCREWS • BRASS AFTER FULL CURE", 20, RED, True, "lm")
    s.text(90, 310, "HINGE SYMBOLS NTS • TRANSFER / FIELD VERIFY", 18, BLUE, True, "lm")
    s.callout(
        90,
        405,
        "1/8 HINGE-SIDE REVEAL",
        s.project((door_x / 2, 0, door_z + 52), origin, scale),
    )
    s.callout(1060, 260, "ACTUAL LOCKSET CONTROLS", knob, BLUE)
    s.note(
        1000,
        545,
        515,
        285,
        "Field-fit sequence",
        [
            f"Confirmed clear jamb: {opening_width:g} × {opening_height:g}",
            "Fitted slab: 23-3/4 × 80-1/2",
            "Plane hinge edge first",
            "Hold 1/8 at both sides and head",
            "Hold 3/8 above finished floor",
            "Knife actual hinge leaves",
            "Cycle the bare door before locating stops",
        ],
        PALE_TEAL,
        body_size=20,
        line_height=29,
        title_size=27,
    )
    s.view_axes()
    s.save("09-hanging-system")


def moulding_layers():
    s = IsoScene(
        10,
        "Installed door and millwork layer relationship",
        "The spaced layers show fit order and substrate relationships, not a literal exploded installation.",
        "MILLWORK",
    )
    # The backband's depth offset drives the lower-right projection. A modest
    # scale reduction keeps every layer inside the canvas without flattening
    # the isometric relationship.
    origin, scale = (620, 830), 8.4
    opening_width = OPENING["clear_width"]
    opening_height = OPENING["clear_height"]
    door_x = OPENING["hinge_side_reveal"]
    door_z = OPENING["bottom_gap"]
    offsets = {
        "door": -4.5,
        "stop": -2.2,
        "jamb": 0.0,
        "casing": 4.6,
        "band": 8.2,
    }
    # Door plane.
    draw_door(
        s,
        origin=origin,
        scale=scale,
        exploded=False,
        show_labels=False,
        show_panels=True,
        x_offset=door_x,
        y_offset=offsets["door"],
        z_offset=door_z,
    )
    # Stop frame.
    for x in (0, opening_width - 0.375):
        s.prism(x, offsets["stop"], 0.5, 0.375, 1.25, opening_height - 1.0, STOP, origin, scale)
    s.prism(
        0.375,
        offsets["stop"],
        opening_height - 0.9,
        opening_width - 0.75,
        1.25,
        0.375,
        STOP,
        origin,
        scale,
    )
    # Jamb.
    draw_installed_jamb(s, origin, scale, y=offsets["jamb"])
    # Casing.
    for x in (-4.5, opening_width):
        s.prism(x, offsets["casing"], 0, 4.5, 0.75, opening_height + 3.5, OAK, origin, scale)
    s.prism(-4.5, offsets["casing"], opening_height, opening_width + 9, 0.75, 4.5, OAK, origin, scale)
    # Backband.
    for x in (-5.625, opening_width + 4.5):
        s.prism(x, offsets["band"], 0, 1.125, 1.0, opening_height + 4.6, OAK_DARK, origin, scale)
    s.prism(
        -5.625,
        offsets["band"],
        opening_height + 3.5,
        opening_width + 11.25,
        1.0,
        1.125,
        OAK_DARK,
        origin,
        scale,
    )
    # Layer arrows.
    for start_y, end_y, z in [(-3.4, -1.4, 65), (-1.0, 0.8, 57), (2.8, 4.0, 49), (6.3, 7.5, 41)]:
        start = s.project((29, start_y, z), origin, scale)
        end = s.project((29, end_y, z), origin, scale)
        s.arrow(start[0], start[1], end[0], end[1], TEAL, 5, 14)
    external_labels = [
        ("1  FITTED 23-3/4 × 80-1/2 DOOR", (door_x + 21.5, offsets["door"], 66), BLUE),
        ("2  THREE-PIECE STOP", (opening_width - 0.2, offsets["stop"], 58), TEAL),
        ("3  24 × 81 CLEAR JAMB", (opening_width + 0.3, offsets["jamb"], 50), BLUE),
        ("4  M-201 CASING", (opening_width + 3, offsets["casing"], 42), TEAL),
        ("5  M-202 BACKBAND", (opening_width + 5, offsets["band"], 34), BLUE),
    ]
    for index, (label, xyz, color) in enumerate(external_labels):
        s.leader_label(55, 180 + index * 110, label, s.project(xyz, origin, scale), color)
    s.note(
        1035,
        155,
        470,
        290,
        "Layer anatomy / inside to out",
        [
            "1. Fitted slab: 23-3/4 × 80-1/2",
            "2. Three-piece stop set",
            "3. Clear jamb: 24 × 81",
            "4. M-201 casing at 3/16 reveal",
            "5. M-202 backband, 1/4 proud",
            "Fit gaps: 1/8 sides/head; 3/8 bottom",
        ],
    )
    s.note(
        1035,
        665,
        470,
        185,
        "Face-count rule",
        [
            "One face: 2 legs + head + 3 bands",
            "Two faces: double casing and band",
            "Do not double the three-piece stop set",
        ],
        PALE_BLUE,
    )
    s.view_axes()
    s.save("10-moulding-layers")


def head_joint_options():
    s = IsoScene(
        11,
        "Head casing joint options",
        "Match one adjacent historic joint language: mitered surround or square-butt head.",
        "FIELD CHOICE",
    )
    s.text(385, 145, "A  TRUE MITERED SURROUND", 28, BLUE, True)
    s.text(1190, 145, "B  SQUARE-BUTT HEAD", 28, TEAL, True)

    # True front-elevation polygons: the casing pieces share one diagonal and do not overlap.
    leg = [(190, 285), (350, 445), (350, 735), (190, 735)]
    head = [(190, 285), (690, 285), (690, 445), (350, 445)]
    for polygon in (leg, head):
        s.polygon([(x + 12, y + 12) for x, y in polygon], SHADOW, SHADOW, 0)
        s.polygon(polygon, OAK, INK, 4)
    s.line([(190, 285), (350, 445)], RED, 6)
    s.text(425, 510, "ONE 45° SEAM", 24, RED, True)
    s.line([(350, 445), (425, 510)], RED, 3)

    # Backband follows the outer casing arrises with a second true miter.
    band_leg = [(145, 240), (190, 285), (190, 735), (145, 735)]
    band_head = [(145, 240), (735, 240), (735, 285), (190, 285)]
    s.polygon(band_leg, OAK_DARK, INK, 3)
    s.polygon(band_head, OAK_DARK, INK, 3)
    s.line([(145, 240), (190, 285)], WHITE, 4)

    # Square head is a real butt joint with the head bearing on the leg.
    s.rect(960, 405, 160, 330, OAK, INK, 4)
    s.rect(820, 245, 620, 160, OAK, INK, 4)
    s.line([(960, 405), (1120, 405)], RED, 6)
    s.text(1200, 485, "SQUARE BUTT", 24, RED, True)
    s.line([(1120, 410), (1170, 470)], RED, 3)
    cap = MODEL["trim"]["optional_head_cap"]
    # The optional cap is a fourth layer above the mandatory M-202C head band.
    # It never substitutes for or bypasses that fitted backband member.
    s.rect(780, 205, 700, 45, OAK_DARK, INK, 3)
    s.rect(750, 170, 760, 35, JAMB, INK, 3)
    s.text(1130, 188, "M-204 OPTIONAL CAP / EVIDENCE ONLY", 17, BLUE, True)
    s.text(1130, 228, "M-202C HEAD BACKBAND — DO NOT OMIT", 17, WHITE, True)
    s.text(
        800,
        765,
        f"M-204 {cap['t']:.3f} × {cap['depth']:.3f} BEARS ON COMPLETED M-202C",
        22,
        RED,
        True,
    )
    s.text(
        800,
        805,
        f"CAP LENGTH = ACTUAL M-202C OUTSIDE + 2P  |  P = {cap['side_overhang']:.3f} EACH END",
        23,
        BLUE,
        True,
    )

    s.note(
        120,
        835,
        1360,
        130,
        "Length controls",
        [
            "Mitered head short = W + 2R; long = W + 2R + 2C.",
            "Square leg = H side + R; square head = W + 2R + 2C.",
        ],
        PALE_TEAL,
        body_size=24,
        line_height=40,
        title_size=28,
    )
    s.save("11-head-joint-options")


def stop_casing_section():
    s = IsoScene(
        12,
        "Door stop, casing, and backband section",
        "Prove each layer stack and sound-wood embedment on a matching offcut before field fastening.",
        "SECTION",
    )
    trim = MODEL["trim"]
    scale = 80
    wall_face_y = 420
    wall_left, wall_right = 125, 530
    jamb_left, jamb_right = 530, 590
    casing_inner = jamb_right - trim["reveal"] * scale
    casing_left = casing_inner - trim["side_casing_finished"]["w"] * scale
    band_left = casing_left - trim["backband_finished"]["w"] * scale
    casing_face_y = wall_face_y - trim["side_casing_finished"]["t"] * scale
    band_face_y = wall_face_y - trim["backband_finished"]["t"] * scale
    stop_x = jamb_right
    stop_w = trim["stop_finished"]["t"] * scale
    stop_y = 460
    stop_h = trim["stop_finished"]["w"] * scale
    shim = 0.015 * scale
    door_x = stop_x + stop_w
    door_y = stop_y + stop_h + shim
    door_h = MODEL["slab"]["finished_thickness"] * scale

    s.text(500, 145, "TRUE PLAN SECTION  /  ROOM FACE AT TOP", 28, BLUE, True)
    s.rect(wall_left, wall_face_y, wall_right - wall_left, 330, WALL, GRAY, 3)
    s.rect(jamb_left, wall_face_y, jamb_right - jamb_left, 330, JAMB, INK, 4)
    s.rect(casing_left, casing_face_y, casing_inner - casing_left, trim["side_casing_finished"]["t"] * scale, OAK, INK, 4)
    s.rect(band_left, band_face_y, casing_left - band_left, trim["backband_finished"]["t"] * scale, OAK_DARK, INK, 4)
    s.rect(stop_x, stop_y, stop_w, stop_h, STOP, INK, 4)
    s.rect(door_x, door_y, 310, door_h, OAK, INK, 4)

    s.text(300, 610, "WALL / FIELD THICKNESS", 24, GRAY, True)
    s.text(560, 660, "JAMB", 24, INK, True)
    s.text((casing_left + casing_inner) / 2, casing_face_y + 30, "CASING", 24, INK, True)
    s.text((band_left + casing_left) / 2, band_face_y + 35, "BAND", 24, WHITE, True)
    s.callout(
        700,
        470,
        "M-203 STOP",
        (stop_x + stop_w / 2, stop_y + stop_h / 2),
        BLUE,
    )
    s.text(door_x + 155, door_y + door_h / 2, "DOOR 1.375", 24, INK, True)

    s.line([(band_left, wall_face_y), (casing_inner, wall_face_y)], RED, 4, "12 8")
    s.text(330, 330, "COMMON BACK PLANE", 24, RED, True)
    s.line([(330, 350), (330, wall_face_y)], RED, 3)
    ortho_dimension(
        s,
        (casing_left - 35, band_face_y),
        (casing_left - 35, casing_face_y),
        "0.250 PROJECTION",
        (0, -62),
        BLUE,
    )
    ortho_dimension(
        s,
        (casing_inner, 315),
        (jamb_right, 315),
        "0.1875 REVEAL",
        (0, -22),
        TEAL,
    )
    ortho_dimension(
        s,
        (stop_x + stop_w + 35, stop_y + stop_h),
        (stop_x + stop_w + 35, door_y),
        "0.010–0.020 SHIM",
        (120, 0),
        RED,
    )

    # Fastener paths terminate in their intended substrates.
    for x1, y1, x2, y2, label, color in [
        (casing_inner - 35, casing_face_y + 12, jamb_left + 15, wall_face_y + 65, "INNER / STOP → ≥0.75 SOUND WOOD", BLUE),
        (casing_left + 70, casing_face_y + 12, wall_left + 220, wall_face_y + 105, "OUTER CASING → ≥1.00 FRAMING", TEAL),
        (band_left + 35, band_face_y + 12, casing_left + 35, casing_face_y + 40, "BACKBAND → ≥0.50 CASING", RED),
    ]:
        s.arrow(x1, y1, x2, y2, color, 5, 14)
        s.text(985, 205 + [BLUE, TEAL, RED].index(color) * 55, label, 20, color, True, "lm")

    s.note(
        950,
        400,
        580,
        325,
        "Fit and fastening",
        [
            "Dry-fit head stop first; sides butt below",
            "Stop bears through removable paper shims",
            "Calculate driven-axis layer stack",
            "Prove length + angle on matching offcut",
            "Permanent stop installs last",
            "No glue to jamb, wall, floor, or plaster",
        ],
        PALE_TEAL,
        body_size=24,
        line_height=38,
        title_size=28,
    )
    s.rect(950, 765, 580, 155, "#FAEFEC", RED, 3)
    s.text(980, 805, "SUBSTRATE HOLD", 27, RED, True, "lm")
    s.text(980, 855, "Hold for unknown layers, framing, utilities, or hazards.", 22, INK, False, "lm")
    s.text(980, 895, "No field drive until offcut embedment proof passes.", 22, BLUE, True, "lm")
    s.save("12-stop-casing-section")


def machine_calibration():
    s = IsoScene(
        "3A",
        "Machine calibration and matched-scrap release",
        "Calibrate thickness, reference geometry, groove, and DF 500 settings before a production member.",
        "SETUP GATE",
    )
    scene_panel(s, 45, 145, 355, 760, "1  STOCK FAMILY")
    scene_panel(s, 430, 145, 355, 760, "2  GROOVE SAMPLE", TEAL)
    scene_panel(s, 815, 145, 355, 760, "3  DF 500 SAMPLE")
    scene_panel(s, 1200, 145, 355, 760, "4  SIGN RELEASE", TEAL)

    calibration_face_h = 330 * (0.25 / 1.375)
    calibration_core_h = 330 * (0.875 / 1.375)
    s.rect(105, 265, 235, calibration_face_h, OAK_DARK, INK, 3)
    s.rect(105, 265 + calibration_face_h, 235, calibration_core_h, OAK, INK, 3)
    s.rect(
        105,
        265 + calibration_face_h + calibration_core_h,
        235,
        calibration_face_h,
        OAK_DARK,
        INK,
        3,
    )
    s.text(222, 294, "1/4 FACE", 18, WHITE, True)
    s.text(222, 475, "7/8 CORE", 22, INK, True)
    s.text(222, 566, "1/4 FACE", 18, WHITE, True)
    reference_marks(s, 115, 640)
    ortho_dimension(s, (85, 265), (85, 595), "1.375 ±0.010", (35, 0))
    s.text(222, 735, "PAIRED DIFFERENCE", 24, BLUE, True)
    s.text(222, 780, "≤0.005", 30, RED, True)
    s.text(222, 835, "MOISTURE 6–9%", 26, TEAL, True)

    gx, gy, scale = 510, 300, 170
    sample_face_w = 0.25 * scale
    sample_core_w = 0.875 * scale
    s.rect(gx, gy, sample_face_w, 250, OAK_DARK, INK, 3)
    s.rect(gx + sample_face_w, gy, sample_core_w, 250, OAK, INK, 3)
    s.rect(gx + sample_face_w + sample_core_w, gy, sample_face_w, 250, OAK_DARK, INK, 3)
    groove_x = gx + (0.6875 - 0.125) * scale
    s.rect(groove_x, gy, 0.25 * scale, 0.5 * scale, WHITE, BLUE, 4)
    ortho_dimension(s, (groove_x, gy - 32), (groove_x + 0.25 * scale, gy - 32), "0.250")
    ortho_dimension(
        s,
        (groove_x + 75, gy),
        (groove_x + 75, gy + 0.5 * scale),
        "0.500",
        (68, 0),
    )
    s.text(607, 660, "CENTER 0.6875", 26, BLUE, True)
    s.text(607, 710, "WIDTH +0.005 / −0", 24, RED, True)
    s.text(607, 755, "DEPTH +0.010 / −0", 24, RED, True)
    s.text(607, 820, "PROVE BOTH FACES", 24, TEAL, True)

    # Calibration block and fence geometry.
    s.rect(870, 540, 245, 145, OAK, INK, 4)
    s.polygon([(905, 540), (1000, 350), (1095, 540)], "#42525C", INK, 4)
    s.line([(855, 540), (1130, 540)], BLUE, 6)
    ortho_dimension(s, (840, 350), (840, 540), "17.5 mm", (70, 0))
    s.text(995, 315, "FENCE 90°", 26, BLUE, True)
    s.arrow(995, 405, 995, 505, TEAL, 7, 20)
    s.text(995, 735, "10 mm / 25 mm FRAME", 24, INK, True)
    s.text(995, 780, "6 mm / 20 mm MUNTIN", 24, INK, True)
    s.text(995, 825, "≥0.200 TO FACE GLUE LINES", 21, RED, True)
    s.text(995, 860, "TIGHT / MEDIUM VERIFIED", 21, BLUE, True)

    s.text(1245, 260, "OPERATOR", 24, BLUE, True, "lm")
    field_blank(s, 1245, 300, "INITIALS", 245)
    field_blank(s, 1245, 385, "DATE / TIME", 245)
    field_blank(s, 1245, 470, "MACHINE ID", 245)
    field_blank(s, 1245, 555, "CUTTER ID", 245)
    s.rect(1245, 660, 260, 90, PALE_TEAL, TEAL, 3)
    s.text(1375, 690, "SCRAP PASSES", 26, TEAL, True)
    s.text(1375, 728, "ALL LIMITS", 24, INK, True)
    s.rect(1245, 790, 260, 70, "#FAEFEC", RED, 3)
    s.text(1375, 825, "THEN PRODUCTION", 24, RED, True)
    s.save("03a-machine-calibration")


def groove_setups():
    s = IsoScene(
        "4A",
        "Safe groove setups by operation type",
        "Use the dado stack only for supported through-rail edges; route every stopped or segmented groove.",
        "SAFE SETUP",
    )
    scene_panel(s, 45, 145, 730, 780, "A  DADO — THROUGH RAIL EDGES ONLY")
    scene_panel(s, 825, 145, 730, 780, "B  PLUNGE ROUTER — STOPPED WORK", TEAL)

    # Supported through rail stands on its narrow panel edge; SF bears on a tall fence.
    s.rect(95, 600, 640, 75, "#D8DEE1", INK, 4)
    s.rect(135, 345, 35, 255, PALE_BLUE, BLUE, 3)
    s.rect(160, 370, 500, 230, OAK, INK, 4)
    s.circle(405, 630, 72, "#AEB8BD", INK, 4)
    s.rect(260, 315, 290, 48, PALE_TEAL, TEAL, 3)
    s.text(405, 339, "GUARDED HOLD-DOWN", 21, TEAL, True)
    s.text(410, 260, "RAIL STANDS ON PANEL-FACING EDGE", 23, BLUE, True)
    s.text(410, 300, "SF FLAT TO TALL FENCE", 23, TEAL, True)
    s.text(405, 515, "BROAD FACE VERTICAL", 24, BLUE, True)
    s.arrow(170, 705, 650, 705, BLUE, 8, 24)
    s.text(410, 748, "CONVENTIONAL FEED →", 25, BLUE, True)
    s.rect(95, 775, 250, 60, PALE_TEAL, TEAL, 3)
    s.text(220, 805, "INFEED SUPPORT", 21, TEAL, True)
    s.rect(475, 775, 250, 60, PALE_TEAL, TEAL, 3)
    s.text(600, 805, "OUTFEED SUPPORT", 21, TEAL, True)
    s.text(410, 858, "8-IN STACK + DADO CARTRIDGE / INSERT", 21, BLUE, True)
    s.text(410, 895, "NO STILES • NO SEGMENTS • NO MUNTIN • NEVER WOBBLE", 20, RED, True)

    # Edge-up work in a captured cradle with a wide, roll-resistant router bridge.
    s.rect(900, 630, 580, 75, "#D8DEE1", INK, 4)
    s.rect(955, 465, 470, 165, OAK, INK, 4)
    s.rect(900, 410, 55, 90, PALE_BLUE, BLUE, 3)
    s.rect(1425, 410, 55, 90, PALE_BLUE, BLUE, 3)
    s.line([(900, 440), (1480, 440)], TEAL, 9)
    s.rect(1085, 250, 210, 155, "#42525C", INK, 4)
    s.rect(1045, 400, 290, 45, TEAL, INK, 3)
    s.text(1190, 325, "ROUTER", 24, WHITE, True)
    s.arrow(1190, 405, 1190, 500, TEAL, 8, 22)
    s.line([(1000, 385), (1000, 535)], RED, 7)
    s.line([(1380, 385), (1380, 535)], RED, 7)
    s.text(1000, 565, "ENTRY", 22, RED, True)
    s.text(1380, 565, "EXIT", 22, RED, True)
    s.text(1190, 220, "WIDE AUXILIARY BRIDGE / CAPTURED SLED", 22, TEAL, True)
    s.text(1190, 600, "PANEL-FACING EDGE UP • SF VERTICAL", 22, BLUE, True)
    s.text(1190, 760, "CUTTER-TANGENT STOP OFFSETS", 24, BLUE, True)
    s.text(1190, 802, "PROVE ENTRY + EXIT ON SCRAP", 22, TEAL, True)
    s.text(1190, 844, "STILES • E/F SEGMENTS • BOTH G SIDES", 21, INK, True)
    s.text(1190, 885, "NEVER BALANCE ROUTER ON 1-3/8 EDGE", 21, RED, True)
    s.save("04a-groove-setups")


def df500_workholding():
    s = IsoScene(
        "5A",
        "DF 500 workholding and reference orientation",
        "Clamp and fully support the test piece exactly as the matching production member will be machined.",
        "WORKHOLDING",
    )
    scene_panel(s, 45, 145, 730, 780, "A  RAIL-END SETUP")
    scene_panel(s, 825, 145, 730, 780, "B  STILE-EDGE SETUP", TEAL)

    # Rail lies show-face up; the DF 500 approaches the square end horizontally.
    s.rect(110, 690, 600, 75, "#D8DEE1", INK, 4)
    s.rect(160, 500, 350, 130, OAK, INK, 4)
    s.rect(115, 480, 45, 170, PALE_BLUE, BLUE, 3)
    s.text(138, 450, "STOP", 22, BLUE, True)
    s.rect(560, 430, 160, 150, "#42525C", INK, 4)
    s.polygon([(560, 470), (510, 515), (560, 560)], "#42525C", INK, 3)
    s.text(640, 505, "DF 500", 26, WHITE, True)
    s.arrow(550, 515, 512, 515, TEAL, 8, 20)
    for cx in (225, 410):
        s.rect(cx, 465, 42, 165, RED, RED, 0)
        s.text(cx + 21, 435, "CLAMP", 22, RED, True)
    s.line([(160, 480), (560, 480)], BLUE, 5)
    s.text(360, 390, "SHOW FACE UP • FENCE ON SF", 24, BLUE, True)
    reference_marks(s, 440, 310)
    s.text(410, 815, "END SQUARE • FULL-LENGTH SUPPORT", 24, BLUE, True)
    s.text(410, 860, "PLUNGE NORMAL TO RAIL END", 24, RED, True)

    # Stile edge lies flat with a long coplanar support.
    s.rect(890, 690, 600, 75, "#D8DEE1", INK, 4)
    s.rect(930, 540, 520, 90, OAK_DARK, INK, 4)
    s.rect(1090, 350, 185, 150, "#42525C", INK, 4)
    s.polygon([(1125, 500), (1182, 540), (1238, 500)], "#42525C", INK, 3)
    s.text(1182, 420, "DF 500", 26, WHITE, True)
    s.arrow(1182, 500, 1182, 535, TEAL, 8, 22)
    for cx in (970, 1390):
        s.rect(cx, 485, 45, 145, RED, RED, 0)
        s.text(cx + 22, 455, "CLAMP", 24, RED, True)
    s.line([(930, 520), (1450, 520)], BLUE, 6)
    s.text(1190, 300, "FENCE 17.5 mm / 90°", 26, BLUE, True)
    reference_marks(s, 860, 310)
    s.text(1190, 815, "SHOW FACE UP • DF 500 FENCE ON SF", 24, BLUE, True)
    s.text(1190, 860, "DATUM VISIBLE • HOSE CLEAR OF PLUNGE", 24, RED, True)

    s.rect(455, 915, 690, 52, PALE_TEAL, TEAL, 3)
    s.text(800, 941, "TEST SCRAP FIRST  |  HANDS OUTSIDE RED CLAMP / CUT ZONES", 24, INK, True)
    s.save("05a-df500-workholding")


def lock_envelope():
    s = IsoScene(
        "5B",
        "J-06 joinery and physical lock-envelope gate",
        "The measured lock machining envelope must remain 0.250 inch clear of J-06 structural joinery.",
        "FIELD VERIFY",
    )
    centers = MODEL["domino"]["stile_centers_from_slab_top_in"]["D-101D"]
    clear_gate = MODEL["hardware"]["lock_to_joinery_clear_wood_min"]
    scale = 9.2
    top_y = 165
    stile_x, stile_w = 560, MODEL["frame"]["stile_width"] * 92
    door_height = MODEL["slab"]["finished_height"]
    stile_h = door_height * scale
    s.rect(stile_x, top_y, stile_w, stile_h, OAK_DARK, INK, 4)
    s.text(stile_x + stile_w / 2, 135, "D-101B EDGE ELEVATION / HARDWARE OVERLAY", 27, BLUE, True)
    s.text(stile_x + 35, 930, "INNER / RAIL EDGE", 24, WHITE, True, "lm")
    s.text(stile_x + stile_w - 35, 930, "OUTER / LOCK EDGE", 24, WHITE, True, "rm")

    mortise_widths = [(13 + 10) / 25.4, (19 + 10) / 25.4, (19 + 10) / 25.4]
    slot_x, slot_w = stile_x, 145
    for index, (center, mortise_width) in enumerate(zip(centers, mortise_widths)):
        cy = top_y + center * scale
        slot_h = max(8, mortise_width * scale)
        s.rect(slot_x, cy - slot_h / 2, slot_w, slot_h, "#35454F", WHITE, 1)
        s.line([(stile_x - 70, cy), (stile_x + stile_w + 70, cy)], BLUE, 2, "10 8")
        s.text(stile_x - 18, cy, f"{center:.3f}", 17, BLUE, True, "rm")
        s.text(slot_x + slot_w / 2, cy, f"J06-{index + 1}", 16, WHITE, True)

    lock_center_top = MODEL["slab"]["finished_height"] - MODEL["hardware"][
        "nominal_lock_center_above_slab_bottom"
    ]
    lock_cy = top_y + lock_center_top * scale
    s.line([(stile_x - 70, lock_cy), (stile_x + stile_w + 70, lock_cy)], RED, 3, "14 8")

    # Placeholder shows where the measured envelope is overlaid without encoding
    # an unverified lock-body size.
    ghost_x = stile_x + stile_w - 135
    ghost_y = lock_cy - 125
    s.rect(ghost_x, ghost_y, 135, 250, "#F8E7E2", RED, 4)
    s.text(ghost_x + 67, lock_cy - 76, "FIELD", 16, RED, True)
    s.text(ghost_x + 67, lock_cy - 45, "MEASURED", 16, RED, True)
    s.text(ghost_x + 67, lock_cy - 14, "BODY + CUT", 16, RED, True)
    s.text(ghost_x + 67, lock_cy + 22, "ENVELOPE", 17, RED, True)
    bracket_y = lock_cy - 82
    s.line([(slot_x + slot_w, bracket_y), (ghost_x, bracket_y)], GREEN, 6)
    s.line([(slot_x + slot_w, bracket_y - 10), (slot_x + slot_w, bracket_y + 10)], GREEN, 4)
    s.line([(ghost_x, bracket_y - 10), (ghost_x, bracket_y + 10)], GREEN, 4)
    s.text(
        (slot_x + slot_w + ghost_x) / 2,
        bracket_y - 24,
        f"REQUIRED ≥ {clear_gate:.3f}",
        18,
        GREEN,
        True,
    )
    s.text(
        stile_x + stile_w / 2,
        710,
        f"NOMINAL CL: {lock_center_top:g} FROM TOP / "
        f"{MODEL['hardware']['nominal_lock_center_above_slab_bottom']:g} ABOVE BOTTOM",
        17,
        RED,
        True,
    )
    s.text(stile_x + stile_w / 2, 746, "PHYSICAL HARDWARE CONTROLS", 18, RED, True)

    scene_panel(s, 45, 165, 430, 700, "HARDWARE MEASUREMENTS", TEAL)
    for index, label in enumerate(
        [
            "MANUFACTURER / MODEL",
            "BACKSET",
            "BODY HEIGHT",
            "BODY DEPTH",
            "BODY THICKNESS",
            "FACEPLATE H × W",
            "SPINDLE / KEY LOC.",
        ]
    ):
        field_blank(s, 80, 265 + index * 78, label, 350)
    s.text(260, 835, "LEAVE BLANK UNTIL MEASURED", 24, RED, True)

    scene_panel(s, 1085, 165, 470, 700, "RELEASE LOGIC")
    for index, line in enumerate(
        [
            "1  Map actual lock + allowance.",
            "2  Overlay J-06 mortise volume.",
            "3  Check ≥1/16 to face glue lines.",
            "4  Add 0.250 buffer toward J-06.",
            "5  PASS: envelopes remain separate.",
            "6  FAIL: re-engineer J-06.",
            "7  Never shift the lock by assumption.",
        ]
    ):
        s.text(1120, 255 + index * 70, line, 21, INK if index < 4 else RED, index >= 4, "lm")
    s.rect(1120, 765, 400, 70, "#FAEFEC", RED, 3)
    s.text(1320, 800, "NO HARDWARE = J-06 HOLD", 24, RED, True)
    s.save("05b-lock-envelope")


def full_dry_fit():
    s = IsoScene(
        "7A",
        "Two whole-door dry fits bracket Stage A",
        "The complete door is dry assembled once before lower-module glue and again after that module cures.",
        "TWO GATES",
    )
    steps = [
        ("1", "WHOLE-DOOR", "DRY FIT #1", "All 13 parts", "Stage A remains dry", BLUE),
        ("2", "STAGE A", "GLUE", "E/G/F joinery only", "K/L panels remain dry", TEAL),
        (
            "3",
            "FULL CURE",
            "+ MODULE QC",
            f"Two {inch_label(MODEL['frame']['bottom_opening_each'])} × 11 openings",
            "Both panels move",
            BLUE,
        ),
        ("4", "WHOLE-DOOR", "DRY FIT #2", "Cured module + frame", "Recheck every limit", TEAL),
        ("5", "RELEASE", "STAGE B GLUE", "Timed rehearsal passes", "Geometry released", RED),
    ]
    centers = [150, 470, 790, 1110, 1430]
    s.line([(centers[0], 320), (centers[-1], 320)], GRAY, 9)
    for index, ((number, title_a, title_b, detail_a, detail_b, color), cx) in enumerate(zip(steps, centers)):
        s.circle(cx, 320, 45, color, WHITE, 4)
        s.text(cx, 320, number, 30, WHITE, True)
        width = 260
        x = cx - width / 2
        s.rect(x, 405, width, 190, PALE_BLUE if index % 2 == 0 else PALE_TEAL, color, 3)
        s.text(cx, 440, title_a, 21, color, True)
        s.text(cx, 476, title_b, 21, color, True)
        s.text(cx, 528, detail_a, 19, INK, False)
        s.text(cx, 562, detail_b, 19, INK, False)
        if index < 4:
            s.arrow(cx + 52, 320, centers[index + 1] - 52, 320, color, 6, 18)

    scene_panel(s, 100, 660, 660, 270, "EACH WHOLE-DOOR DRY FIT")
    for index, line in enumerate(
        [
            "□ Diagonals differ ≤0.0625",
            "□ Twist ≤0.03125",
            "□ Shoulder gaps ≤0.005",
            "□ All five panels move by hand",
        ]
    ):
        s.text(140, 750 + index * 43, line, 24, INK, False, "lm")
    scene_panel(s, 840, 660, 660, 270, "TIMING RELEASE", TEAL)
    s.text(880, 750, "REHEARSED STAGE B TIME", 24, INK, True, "lm")
    field_blank(s, 880, 795, "MINUTES", 250)
    s.text(1170, 852, "FINAL REHEARSAL GATE", 22, RED, True)
    s.text(1170, 885, "≤ 0.75 × CURRENT PUBLISHED OPEN", 21, RED, True)
    s.save("07a-full-dry-fit")


def glue_clock():
    s = IsoScene(
        "8A",
        "Stage A glue clock and bench staging",
        "Record the adhesive limit; preload four 3/4-in-long foam panel spacers; keep K/L dry.",
        "STAGE A",
    )
    scene_panel(s, 45, 145, 620, 780, "A  SIGNED TIME GATE")
    clock_cx, clock_cy = 355, 465
    s.circle(clock_cx, clock_cy, 185, WHITE, BLUE, 7)
    for index in range(12):
        angle = math.radians(index * 30 - 90)
        x1 = clock_cx + 155 * math.cos(angle)
        y1 = clock_cy + 155 * math.sin(angle)
        x2 = clock_cx + 177 * math.cos(angle)
        y2 = clock_cy + 177 * math.sin(angle)
        s.line([(x1, y1), (x2, y2)], GRAY, 4)
    s.arrow(clock_cx, clock_cy, clock_cx, clock_cy - 125, RED, 8, 22)
    s.arrow(clock_cx, clock_cy, clock_cx + 110, clock_cy + 35, TEAL, 8, 22)
    field_blank(s, 110, 675, "CURRENT PUBLISHED OPEN TIME  ___ min", 470)
    field_blank(s, 110, 740, "REHEARSAL FINAL GATE  ___ min", 470)
    field_blank(s, 110, 805, "LIVE FINAL GATE  ___ min", 470)
    s.text(355, 865, "BOTH FINAL GATES ≤ 0.75 × PUBLISHED", 23, RED, True)
    s.text(355, 900, "CLAMP COMPLETE = CHECKPOINT; TIMER CONTINUES", 19, BLUE, True)

    scene_panel(s, 705, 145, 850, 780, "B  BENCH MAP / STAGE A", TEAL)
    # Simplified bench with ordered stations.
    s.rect(770, 320, 720, 330, "#E7E2D8", INK, 4)
    stations = [
        (790, 365, 150, 120, "1", "FOAM", "4 | 3/4-IN LONG", BLUE),
        (960, 365, 150, 120, "2", "J-11", "2 TENONS", TEAL),
        (1130, 365, 150, 120, "3", "K / L", "DRY", BLUE),
        (1300, 365, 150, 120, "4", "J-12 / F", "2 TENONS", TEAL),
    ]
    for x, y, w, h, number, label, qualifier, color in stations:
        s.rect(x, y, w, h, WHITE, color, 3)
        s.text(x + w / 2, y + 30, number, 27, color, True)
        s.text(x + w / 2, y + 68, label, 21, INK, True)
        if qualifier:
            s.text(x + w / 2, y + 98, qualifier, 16, color, True)
    s.rect(815, 535, 590, 82, OAK, INK, 3)
    s.text(1110, 557, "GLUE ONLY", 20, RED, True)
    s.text(1110, 590, "J-11 / J-12 MORTISES • TENON FACES", 20, RED, True)
    s.text(1130, 720, "BLUE = PANEL + GROOVE DRY", 24, BLUE, True)
    s.text(1130, 765, "GREEN = J-11 / J-12 ADHESIVE", 24, GREEN, True)
    s.text(1130, 800, "PRESET CAULS + G CLAMP • REHEARSE", 22, INK, True)
    s.text(1130, 842, "START TIMER AT FIRST GLUE APPLICATION", 22, RED, True)
    s.text(1130, 882, "STOP ONLY AFTER SQUARE + K/L MOVEMENT PASS", 20, RED, True)
    s.save("08a-glue-clock")


def jamb_fit_map():
    s = IsoScene(
        "9A",
        "Confirmed jamb and fitted-slab gap map",
        "The 24 x 81 clear jamb is fixed; the 23-3/4 x 80-1/2 slab resolves the written operating gaps.",
        "CONTROLLED FIT",
    )
    opening_width = OPENING["clear_width"]
    opening_height = OPENING["clear_height"]
    slab_width = MODEL["slab"]["finished_width"]
    slab_height = MODEL["slab"]["finished_height"]
    # Orthographic gap diagram (intentionally widened for legibility); written
    # dimensions, rather than the exaggerated gap graphics, control the build.
    left, top, width, height = 350, 165, 610, 745
    jamb_border = 18
    clear_left = left + jamb_border
    clear_top = top + jamb_border
    clear_width_px = width - 2 * jamb_border
    clear_height_px = height - jamb_border
    side_gap_px = 15
    head_gap_px = 15
    bottom_gap_px = 38
    slab_left = clear_left + side_gap_px
    slab_top = clear_top + head_gap_px
    slab_width_px = clear_width_px - 2 * side_gap_px
    slab_height_px = clear_height_px - head_gap_px - bottom_gap_px
    s.rect(left, top, width, height, JAMB, JAMB, 3)
    s.rect(clear_left, clear_top, clear_width_px, clear_height_px, WHITE, BLUE, 3)
    s.rect(
        slab_left,
        slab_top,
        slab_width_px,
        slab_height_px,
        PALE_BLUE,
        BLUE,
        4,
    )
    s.text(left + width / 2, 130, "CONFIRMED INSTALLED JAMB / FRONT ELEVATION", 25, BLUE, True)
    for yy, label in (
        (clear_top + 75, f"W-TOP  {opening_width:g}"),
        (clear_top + clear_height_px / 2, f"W-MID  {opening_width:g}"),
        (clear_top + clear_height_px - 75, f"W-BOTTOM  {opening_width:g}"),
    ):
        ortho_dimension(
            s,
            (clear_left + 28, yy),
            (clear_left + clear_width_px - 28, yy),
            label,
            (0, -22),
            TEAL,
        )
    for xx, label in (
        (clear_left + 70, f"H-L  {opening_height:g}"),
        (clear_left + clear_width_px / 2, f"H-C  {opening_height:g}"),
        (clear_left + clear_width_px - 70, f"H-R  {opening_height:g}"),
    ):
        ortho_dimension(
            s,
            (xx, clear_top + 30),
            (xx, clear_top + clear_height_px - 30),
            "",
            (0, 0),
            BLUE,
        )
        label_y = slab_top + slab_height_px * 0.72
        s.rect(xx - 47, label_y - 18, 94, 36, WHITE, WHITE, 0)
        s.text(xx, label_y, label, 18, BLUE, True)

    slab_label_y = slab_top + slab_height_px * 0.32
    s.rect(
        slab_left + slab_width_px / 2 - 170,
        slab_label_y - 47,
        340,
        94,
        WHITE,
        BLUE,
        2,
    )
    s.text(
        slab_left + slab_width_px / 2,
        slab_label_y - 18,
        "FITTED SLAB",
        25,
        BLUE,
        True,
    )
    s.text(
        slab_left + slab_width_px / 2,
        slab_label_y + 19,
        f"{inch_label(slab_width)} × {inch_label(slab_height)}",
        27,
        BLUE,
        True,
    )

    # Exact gap callouts. Graphics are exaggerated so the four distinct
    # operating clearances remain visible in print.
    s.text(clear_left + 6, slab_top + 120, "1/8", 20, RED, True, "lm")
    s.text(clear_left + clear_width_px - 6, slab_top + 120, "1/8", 20, RED, True, "rm")
    s.text(slab_left + slab_width_px / 2, clear_top + 8, "HEAD 1/8", 20, RED, True)
    s.text(
        slab_left + slab_width_px / 2,
        slab_top + slab_height_px + bottom_gap_px / 2,
        "BOTTOM 3/8",
        20,
        RED,
        True,
    )

    scene_panel(s, 1015, 165, 520, 745, "CONTROLLED FIT + ORDER", TEAL)
    fit_steps = [
        "1  VERIFY 24 × 81 AT 3 STATIONS",
        "2  HINGE EDGE / PLUMB DATUM",
        "3  HOLD 1/8 HEAD + BOTH SIDES",
        "4  HOLD 3/8 ABOVE FINISHED FLOOR",
        "5  REHANG + FULL-SWING TEST",
    ]
    for index, line in enumerate(fit_steps):
        s.circle(1060, 275 + index * 78, 22, TEAL if index < 4 else RED, WHITE, 3)
        s.text(1110, 275 + index * 78, line, 21, INK, True, "lm")
    s.rect(1055, 690, 440, 170, "#FAEFEC", RED, 3)
    s.text(1275, 730, "DO NOT REWORK AN OBSOLETE SLAB", 19, RED, True)
    s.text(1275, 774, "BUILD THE REV. G FRAME GEOMETRY", 22, RED, True)
    s.text(1275, 818, "23-3/4 × 80-1/2 MAX ENVELOPE", 22, BLUE, True)
    s.text(1275, 885, "GAP GRAPHICS EXAGGERATED / NTS", 20, BLUE, True)
    s.text(160, 570, "HINGE", 24, RED, True)
    s.arrow(215, 570, left - 12, 570, RED, 7, 20)
    s.text(
        800,
        965,
        "FINISHED FLOOR DATUM  |  3/8 BOTTOM GAP  |  WRITTEN DIMENSIONS CONTROL",
        23,
        INK,
        True,
    )
    s.save("09a-jamb-fit-map")


def hinge_gain():
    s = IsoScene(
        "9B",
        "Hinge-gain transfer from the physical leaf",
        "The measured brass leaf controls gain depth, screw pattern, pin axis, and barrel projection.",
        "HINGE DETAIL",
    )
    scene_panel(s, 45, 145, 730, 780, "A  EDGE ELEVATION / ACTUAL LEAF")
    scene_panel(s, 825, 145, 730, 780, "B  GAIN SECTION + PIN AXIS", TEAL)

    s.rect(170, 250, 300, 580, OAK_DARK, INK, 4)
    s.rect(470, 355, 105, 385, "#C5A24C", INK, 4)
    s.circle(600, 547, 30, "#C5A24C", INK, 4)
    for yy in (420, 545, 670):
        s.circle(520, yy, 12, WHITE, INK, 3)
    ortho_dimension(s, (620, 355), (620, 740), "3.500 NOMINAL", (95, 0), BLUE)
    s.text(322, 875, "KNIFE THE ACTUAL LEAF — DO NOT SCALE", 24, RED, True)

    # Plan section: measured leaf sits flush in a matching recess.
    s.rect(925, 390, 500, 260, OAK, INK, 4)
    s.rect(1110, 390, 170, 55, "#C5A24C", INK, 4)
    s.circle(1318, 417, 30, "#C5A24C", INK, 4)
    s.line([(1318, 250), (1318, 720)], RED, 5, "12 8")
    s.text(1318, 225, "PIN AXIS", 25, RED, True)
    s.arrow(1318, 740, 1318, 675, RED, 6, 18)
    field_blank(s, 900, 735, "MEASURED LEAF THICKNESS  ______", 540)
    field_blank(s, 900, 815, "GAIN DEPTH = LEAF THICKNESS  ______", 540)
    s.text(1180, 885, "LEAF FULLY BEARS • BARREL CLEARS", 24, BLUE, True)
    s.text(800, 955, "STEEL SETUP SCREWS FIRST  |  BRASS FINAL SCREWS AFTER FIT + FINISH", 24, RED, True)
    s.save("09b-hinge-gain")


def lock_strike():
    s = IsoScene(
        "9C",
        "Mortise lock and strike transfer",
        "Machine from measured hardware, hang the bare door, then locate the strike from the operating latch.",
        "LOCK + STRIKE",
    )
    scene_panel(s, 45, 145, 730, 780, "A  LOCK EDGE / MEASURED HARDWARE")
    scene_panel(s, 825, 145, 730, 780, "B  STRIKE FROM OPERATING LATCH", TEAL)

    s.rect(130, 250, 250, 580, OAK_DARK, INK, 4)
    s.rect(380, 385, 55, 310, "#C5A24C", INK, 4)
    s.rect(205, 430, 175, 220, "#F8E7E2", RED, 4)
    s.circle(292, 520, 22, WHITE, RED, 3)
    s.circle(292, 600, 16, WHITE, RED, 3)
    s.text(525, 340, "FACEPLATE H × W  ______", 24, BLUE, True)
    s.text(525, 400, "BODY H × D × T  ______", 24, BLUE, True)
    s.text(525, 460, "BACKSET  ______", 24, BLUE, True)
    s.text(525, 520, "SPINDLE  ______", 24, BLUE, True)
    s.text(525, 580, "KEY / PRIVACY  ______", 24, BLUE, True)
    s.text(405, 770, "BORE FROM BOTH FACES", 24, RED, True)
    s.text(405, 815, "RECHECK 05B J-06 GATE", 24, TEAL, True)

    # Latch transfers horizontally into strike; jamb and door do not overlap.
    s.rect(900, 310, 180, 480, OAK_DARK, INK, 4)
    s.rect(1280, 310, 180, 480, JAMB, INK, 4)
    s.rect(1080, 500, 130, 60, "#C5A24C", INK, 3)
    s.polygon([(1210, 500), (1280, 530), (1210, 560)], "#C5A24C", INK, 3)
    s.rect(1280, 465, 45, 130, "#C5A24C", INK, 3)
    s.arrow(1190, 530, 1270, 530, RED, 8, 24)
    s.text(1180, 430, "TRANSFER AT NATURAL LATCH", 24, RED, True)
    field_blank(s, 900, 825, "STRIKE H × W × DEPTH  ______", 520)
    s.text(1180, 885, "PASS: LATCHES WITHOUT PUSH OR LIFT", 24, BLUE, True)
    s.save("09c-lock-strike")


def moulding_milling():
    s = IsoScene(
        "10A",
        "Custom moulding stock and milling sequence",
        "Mill each profile family to its controlled rectangular section; final lengths remain field transfers.",
        "PROFILE MILLING",
    )
    trim = MODEL["trim"]
    profiles = [
        ("M-201 CASING", trim["side_casing_finished"], OAK),
        ("M-202 BACKBAND", trim["backband_finished"], OAK_DARK),
        ("M-203 STOP", trim["stop_finished"], STOP),
        ("M-204 CAP / OPTIONAL", trim["optional_head_cap"], JAMB),
    ]
    x_positions = [65, 450, 835, 1220]
    for x, (label, data, color) in zip(x_positions, profiles):
        scene_panel(s, x, 145, 330, 590, label, BLUE if x in (65, 835) else TEAL)
        t = data["t"]
        w = data.get("w", data.get("depth"))
        px = min(210 / max(t, 0.01), 210 / max(w, 0.01))
        draw_w = max(28, w * px)
        draw_h = max(28, t * px)
        cx, cy = x + 165, 430
        s.rect(cx - draw_w / 2, cy - draw_h / 2, draw_w, draw_h, color, INK, 4)
        s.text(cx, 300, f"{t:.3f} × {w:.3f}", 28, BLUE, True)
        if "projection" in data:
            s.text(cx, 580, f"FACE PROJECTION {data['projection']:.3f}", 24, RED, True)
        elif "CAP" in label:
            s.text(cx, 580, "FIELD EVIDENCE ONLY", 24, RED, True)
        else:
            s.text(cx, 580, "RECTILINEAR PROFILE", 24, TEAL, True)
        s.text(cx, 640, "FINAL LENGTH: FIELD FIT", 24, INK, True)

    s.rect(100, 785, 1400, 150, PALE_TEAL, TEAL, 3)
    s.text(130, 825, "SAFE MACHINING SPLIT", 28, BLUE, True, "lm")
    s.text(
        130,
        872,
        "Rip / crosscut with standard blades; plane broad mother blanks before ripping narrow stop strips.",
        24,
        INK,
        False,
        "lm",
    )
    s.text(
        130,
        912,
        "No dado blade is required for default moulding profiles. Local back relief uses router or hand tools.",
        24,
        RED,
        True,
        "lm",
    )
    s.save("10a-moulding-milling")


def backband_corners():
    s = IsoScene(
        "11A",
        "Backband corner formulas by head scheme",
        "A mitered side gains one band width B; a square-butt side gains one casing width C.",
        "CORNER LOGIC",
    )
    scene_panel(s, 45, 145, 730, 780, "A  MITERED SIDE + B")
    scene_panel(s, 825, 145, 730, 780, "B  SQUARE SIDE + C", TEAL)
    band = MODEL["trim"]["backband_finished"]["w"]
    casing = MODEL["trim"]["side_casing_finished"]["w"]

    # True mitered casing and backband fronts.
    casing_leg = [(190, 300), (350, 460), (350, 765), (190, 765)]
    casing_head = [(190, 300), (680, 300), (680, 460), (350, 460)]
    band_leg = [(145, 255), (190, 300), (190, 765), (145, 765)]
    band_head = [(145, 255), (725, 255), (725, 300), (190, 300)]
    for polygon, fill, width in (
        (casing_leg, OAK, 4),
        (casing_head, OAK, 4),
        (band_leg, OAK_DARK, 3),
        (band_head, OAK_DARK, 3),
    ):
        s.polygon(polygon, fill, INK, width)
    s.line([(145, 255), (190, 300)], WHITE, 4)
    s.line([(190, 300), (350, 460)], RED, 6)
    ortho_dimension(s, (155, 300), (155, 765), f"SIDE LONG + B ({band:.3f})", (150, 0), BLUE)
    s.text(410, 840, "MITERED SIDE BACKBAND", 24, BLUE, True)
    s.text(410, 882, "= FITTED CASING OUTER LONG + B", 24, RED, True)

    # Square head and band: side runs one full casing width beyond fitted side casing.
    s.rect(975, 450, 160, 315, OAK, INK, 4)
    s.rect(835, 290, 620, 160, OAK, INK, 4)
    s.rect(930, 405, 45, 360, OAK_DARK, INK, 3)
    s.rect(790, 245, 710, 45, OAK_DARK, INK, 3)
    s.line([(975, 450), (1135, 450)], RED, 6)
    ortho_dimension(s, (905, 450), (905, 765), f"SIDE + C ({casing:.3f})", (150, 0), TEAL)
    s.text(1175, 840, "SQUARE SIDE BACKBAND", 24, TEAL, True)
    s.text(1175, 882, "= FITTED CASING SIDE + C", 24, RED, True)
    s.save("11a-backband-corners")


def casing_scribe():
    s = IsoScene(
        "12A",
        "Casing wall-scribe and local bearing correction",
        "Preserve the jamb reveal while correcting only the back of the casing enough to bear on sound substrate.",
        "SCRIBE DETAIL",
    )
    gap_limit = MODEL["trim"]["installation_qc"]["wall_scribe_gap_max"]
    reveal = MODEL["trim"]["reveal"]
    scene_panel(s, 45, 145, 730, 780, "A  WALL HUMP / LOCAL RELIEF")
    scene_panel(s, 825, 145, 730, 780, "B  SHIMMED LOW AREA", TEAL)

    # Irregular wall and relieved casing in plan.
    wall_points = [(120, 340), (210, 330), (300, 360), (390, 315), (500, 345), (690, 330)]
    wall_polygon = wall_points + [(690, 720), (120, 720)]
    s.polygon(wall_polygon, WALL, GRAY, 4)
    s.rect(170, 245, 470, 70, OAK, INK, 4)
    s.polygon([(330, 315), (390, 315), (360, 350)], WHITE, RED, 3)
    s.line([(120, 315), (690, 315)], BLUE, 4, "12 8")
    s.text(405, 225, "CASING FACE REMAINS TRUE", 24, BLUE, True)
    s.text(405, 780, "RELIEVE BACK LOCALLY — NEVER FACE-PLANE", 24, RED, True)
    ortho_dimension(s, (650, 315), (650, 330), f"GAP ≤ {gap_limit:.4f}", (0, 45), TEAL)

    low_wall = [(900, 350), (1020, 350), (1120, 380), (1250, 380), (1460, 350)]
    low_polygon = low_wall + [(1460, 720), (900, 720)]
    s.polygon(low_polygon, WALL, GRAY, 4)
    s.rect(930, 245, 500, 70, OAK, INK, 4)
    s.polygon([(1080, 315), (1280, 315), (1250, 380), (1120, 380)], PALE_BLUE, BLUE, 3)
    s.text(1180, 430, "TAPERED SHIM", 24, BLUE, True)
    s.text(1180, 780, "FULL BEARING • NO ROCK • NO WALL GLUE", 24, RED, True)
    s.text(1180, 845, f"CASING-TO-JAMB REVEAL {reveal:.4f}", 26, TEAL, True)
    s.text(800, 955, "HOLD FOR MOISTURE, LOOSE PLASTER, OR UNSOUND SUBSTRATE", 24, RED, True)
    s.save("12a-casing-scribe")


def finish_sequence():
    s = IsoScene(
        "12B",
        "Integrated door and moulding finish sequence",
        "Protect every fitted boundary, re-release operation after P120, then finish, fully cure, and install in controlled order.",
        "FINISH",
    )
    finish = MODEL["finish"]
    steps = [
        ("1", "PANEL P120 + PREFINISH", "Tongues fully cured first", BLUE),
        ("2", "GLUE + FULL CURE", "Frame stops at P100", TEAL),
        ("3", "FIT JAMB + HARDWARE", "Steel setup release", BLUE),
        ("4", "DRY-FIT TRIM + RETURNS", "Label mask remove", TEAL),
        ("5", "FINAL P120 / NO-SAND", "Protect every fitted edge", BLUE),
        ("6", "REHANG + RE-RELEASE", "Setup hardware after P120", TEAL),
        ("7", "RUBIO + FULL CURE", "No return glue yet", BLUE),
        ("8", "PERMANENT INSTALL ORDER", "Plinth casing band returns cap stop-last", RED),
    ]
    xs = [95, 296, 497, 698, 899, 1100, 1301, 1502]
    for index, ((number, title, detail, color), x) in enumerate(zip(steps, xs)):
        s.circle(x, 300, 36, color, WHITE, 4)
        s.text(x, 300, number, 26, WHITE, True)
        if index < len(xs) - 1:
            s.arrow(x + 42, 300, xs[index + 1] - 42, 300, color, 5, 16)
        s.rect(x - 80, 390, 160, 250, PALE_BLUE if index % 2 == 0 else PALE_TEAL, color, 3)
        words = title.split(" ")
        split = max(1, len(words) // 2)
        s.text(x, 430, " ".join(words[:split]), 18, color, True)
        s.text(x, 470, " ".join(words[split:]), 18, color, True)
        detail_words = detail.split(" ")
        detail_split = max(1, len(detail_words) // 2)
        s.text(x, 545, " ".join(detail_words[:detail_split]), 16, INK, False)
        s.text(x, 585, " ".join(detail_words[detail_split:]), 16, INK, False)

    s.text(
        800,
        682,
        f"{finish['product']} / {finish['color']}  •  CURRENT CONTAINER + TDS CONTROL",
        23,
        BLUE,
        True,
    )
    scene_panel(s, 100, 720, 650, 205, "NO-SAND / MASK BOUNDARY")
    s.text(140, 790, "HINGE EDGE • LOCK BEVEL • HEAD / BOTTOM", 20, BLUE, True, "lm")
    s.text(140, 835, "GAINS • FACEPLATE / STRIKE SEATS • GLUE LANDS", 20, RED, True, "lm")
    s.text(140, 878, "REHANG + REPEAT OPERATING RELEASE BEFORE FINISH", 19, INK, True, "lm")
    scene_panel(s, 850, 720, 650, 205, "FULL CURE / PERMANENT ORDER", TEAL)
    s.text(890, 790, "A:B = 3:1 • THIN COAT • WIPE EXCESS • FULL CURE", 20, INK, True, "lm")
    s.text(890, 835, "PLINTH → CASING → BAND / RETURNS → CAP", 20, BLUE, True, "lm")
    s.text(890, 878, "DOOR STOP LAST • THEN FINAL OPERATING CYCLE", 20, RED, True, "lm")
    s.save("12b-finish-sequence")


def final_release():
    s = IsoScene(
        13,
        "Finished opening and quality release",
        "Inspect appearance, geometry, hardware, stop contact, and seasonal panel freedom as one system.",
        "FINAL QC",
    )
    origin, scale = (700, 835), 8.25
    opening_width = OPENING["clear_width"]
    opening_height = OPENING["clear_height"]
    door_width = MODEL["slab"]["finished_width"]
    door_height = MODEL["slab"]["finished_height"]
    door_x = OPENING["hinge_side_reveal"]
    door_z = OPENING["bottom_gap"]
    s.prism(
        -6.5,
        3.8,
        -2,
        opening_width + 13,
        0.6,
        opening_height + 7,
        WALL,
        origin,
        scale,
        outline=GRAY,
        line_width=1,
    )
    for x in (-5.625, opening_width + 4.5):
        s.prism(x, 2.2, 0, 1.125, 1.0, opening_height + 3.5, OAK_DARK, origin, scale)
    s.prism(
        -5.625,
        2.2,
        opening_height + 3.5,
        opening_width + 11.25,
        1.0,
        1.125,
        OAK_DARK,
        origin,
        scale,
    )
    for x in (-4.5, opening_width):
        s.prism(x, 1.45, 0, 4.5, 0.75, opening_height + 3.5, OAK, origin, scale)
    s.prism(-4.5, 1.45, opening_height, opening_width + 9, 0.75, 4.5, OAK, origin, scale)
    draw_installed_jamb(s, origin, scale)
    draw_door(
        s,
        origin,
        scale,
        exploded=False,
        show_labels=False,
        show_panels=True,
        x_offset=door_x,
        z_offset=door_z,
    )
    for x in (-0.35, opening_width - 0.05):
        s.prism(x, -0.3, 0.5, 0.375, 1.25, opening_height - 1.0, STOP, origin, scale)
    s.prism(0, -0.3, opening_height - 0.4, opening_width, 1.25, 0.375, STOP, origin, scale)
    s.callout(
        65,
        205,
        "HEAD LEVEL <=1/16",
        s.project((opening_width / 2, 1.45, opening_height + 4.5), origin, scale),
        BLUE,
    )
    s.callout(
        65,
        355,
        "CASING-TO-JAMB REVEAL 3/16 ±1/32",
        s.project((-0.2, 0, 65), origin, scale),
    )
    s.callout(65, 510, "LEGS PLUMB <=1/16", s.project((-2.2, 1.45, 42), origin, scale), BLUE)
    s.callout(
        1060,
        250,
        "JOINT GAP <0.010",
        s.project((opening_width + 3, 1.45, opening_height), origin, scale),
        RED,
    )
    s.callout(
        1060,
        415,
        "BAND PROJECTION +/-1/32",
        s.project((opening_width + 5, 2.2, 56), origin, scale),
        TEAL,
    )
    s.note(
        1015,
        620,
        495,
        230,
        "Functional release",
        [
            f"Jamb {opening_width:g} × {opening_height:g}; slab {inch_label(door_width)} × {inch_label(door_height)}",
            "Reveals 1/8 sides/head; bottom 3/8",
            "Full swing; latch works without push/lift",
            "Stop contact is quiet and continuous",
            "Panels retain independent movement",
        ],
        PALE_TEAL,
        body_size=20,
        line_height=31,
    )
    s.rect(120, 760, 690, 120, PALE_BLUE, TEAL, 3)
    s.text(150, 795, "PASS ONLY AS A COMPLETE SYSTEM", 23, BLUE, True, "lm")
    s.text(150, 838, "Geometry, operation, finish, and historic fit must all pass.", 19, INK, False, "lm")
    s.view_axes()
    s.save("13-final-release")


def contact_sheet(slugs):
    thumb_w, thumb_h = 390, 258
    columns = 4
    rows = math.ceil(len(slugs) / columns)
    sheet = Image.new("RGB", (columns * thumb_w, rows * (thumb_h + 34)), WHITE)
    draw = ImageDraw.Draw(sheet)
    for idx, slug in enumerate(slugs):
        with Image.open(OUT / f"{slug}.png") as image:
            image.thumbnail((thumb_w - 12, thumb_h - 12))
            x = (idx % columns) * thumb_w + (thumb_w - image.width) // 2
            y = (idx // columns) * (thumb_h + 34) + 4
            sheet.paste(image, (x, y))
            draw.text(
                ((idx % columns) * thumb_w + 8, y + thumb_h),
                slug,
                fill=INK,
                font=font(18, True),
            )
    output = ROOT / "build" / "reports" / "contact-sheets"
    output.mkdir(parents=True, exist_ok=True)
    sheet.save(output / "DC-1916-001_Cabinetmakers_3D_Renderings.jpg", quality=90)


def generate():
    # Load the authoritative model before generating; malformed/missing specs fail fast.
    model = spec()
    validate_installed_fit()
    assert model["opening"]["clear_width"] == 24.0
    assert model["opening"]["clear_height"] == 81.0
    assert model["slab"]["finished_width"] == 23.75
    assert model["slab"]["finished_height"] == 80.5
    assert len(model["components"]) == 13
    construction = model["frame"]["construction"]
    assert math.isclose(
        construction["show_face_preglue_thickness"]
        + construction["core_preglue_thickness"]
        + construction["back_face_preglue_thickness"],
        construction["glue_blank_thickness"],
    )
    assert math.isclose(
        construction["show_face_finished_thickness"]
        + construction["core_preglue_thickness"]
        + construction["back_face_finished_thickness"],
        model["slab"]["finished_thickness"],
    )
    renderers = [
        ("01-complete-system", complete_system),
        ("02-exploded-door", exploded_door),
        ("03-stock-milling", stock_milling),
        ("03a-machine-calibration", machine_calibration),
        ("04-groove-panel-cutaway", groove_panel_cutaway),
        ("04a-groove-setups", groove_setups),
        ("05-rail-stile-joint", rail_stile_joint),
        ("05a-df500-workholding", df500_workholding),
        ("05b-lock-envelope", lock_envelope),
        ("06-lower-module", lower_module),
        ("06a-muntin-clearance", muntin_clearance),
        ("07-frame-loading", frame_loading),
        ("07a-full-dry-fit", full_dry_fit),
        ("08-clamp-geometry", clamp_geometry),
        ("08a-glue-clock", glue_clock),
        ("09-hanging-system", hanging_system),
        ("09a-jamb-fit-map", jamb_fit_map),
        ("09b-hinge-gain", hinge_gain),
        ("09c-lock-strike", lock_strike),
        ("10-moulding-layers", moulding_layers),
        ("10a-moulding-milling", moulding_milling),
        ("11-head-joint-options", head_joint_options),
        ("11a-backband-corners", backband_corners),
        ("12-stop-casing-section", stop_casing_section),
        ("12a-casing-scribe", casing_scribe),
        ("12b-finish-sequence", finish_sequence),
        ("13-final-release", final_release),
    ]
    assert len(renderers) == 27, f"Expected 27 controlled renderings, got {len(renderers)}"
    for _, renderer in renderers:
        renderer()
    slugs = [slug for slug, _ in renderers]
    contact_sheet(slugs)
    register_path = ROOT / "project" / "cabinetmakers-render-register.csv"
    purposes = {
        "01-complete-system": "Complete installed door, jamb, stop, casing, backband, and cap anatomy",
        "02-exploded-door": "Exploded inventory and assembly relationships for all thirteen door parts",
        "03-stock-milling": "Exploded balanced frame layup, simultaneous pressing, symmetric surfacing, and D-101D/F seam maps",
        "03a-machine-calibration": "Same-layup calibration gate for finished layers, groove, and DF 500 core clearance",
        "04-groove-panel-cutaway": "Exact laminated-frame groove, tongue, bottom-clearance, corner-relief, and dry-panel geometry",
        "04a-groove-setups": "Safe machining split between supported through-rail dado cuts and routed stopped grooves",
        "05-rail-stile-joint": "Standard DF 500 frame centers, groove web, tenons, and test-piece criteria",
        "05a-df500-workholding": "Rail-end and stile-edge DF 500 support, clamping, and reference orientation",
        "05b-lock-envelope": "J-06 joinery overlay against field-measured mortise-lock envelope and clear-wood gate",
        "06-lower-module": "Stage A lower rail, muntin, and lower-panel subassembly",
        "06a-muntin-clearance": "J-11/J-12 nominal and worst-case mortise, web, and segmented-groove clearance",
        "07-frame-loading": "Stage B loading order and parallel lock-stile closure",
        "07a-full-dry-fit": "First and second whole-door dry-fit gates bracketing cured Stage A",
        "08-clamp-geometry": "Front/back clamp alternation, diagonal comparison, winding sticks, and acceptance",
        "08a-glue-clock": "Signed adhesive open-time gate and Stage A lower-module bench staging",
        "09-hanging-system": "Accurate five-panel slab orientation within the completed jamb",
        "09a-jamb-fit-map": "Three-width, three-height completed-jamb map and ordered slab fitting",
        "09b-hinge-gain": "Physical hinge-leaf transfer, gain depth, pin axis, and screw layout",
        "09c-lock-strike": "Measured mortise-lock machining fields and strike transfer from the operating latch",
        "10-moulding-layers": "Installed relationship among door, stop, jamb, casing, and backband layers",
        "10a-moulding-milling": "Controlled rectangular moulding sections and safe milling sequence",
        "11-head-joint-options": "True mitered and square-butt casing geometry with evidence-controlled cap",
        "11a-backband-corners": "Mitered side-plus-B and square side-plus-C backband corner logic",
        "12-stop-casing-section": "Non-overlapping plan section for wall, jamb, door, stop, casing, and backband",
        "12a-casing-scribe": "Local casing relief or shimming while retaining wall-scribe and reveal limits",
        "12b-finish-sequence": "Panel prefinish, sanding, masking, Rubio application, cure, and oily-cloth controls",
        "13-final-release": "Completed opening geometry, operation, finish, and final QC",
    }
    with register_path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "Rendering ID",
                "Slug",
                "SVG source",
                "PNG preview",
                "Purpose",
                "Dimensional status",
                "QC status",
            ]
        )
        for index, slug in enumerate(slugs, start=1):
            writer.writerow(
                [
                    f"R-{index:02d}",
                    slug,
                    f"cabinetmakers-guide/renderings/{slug}.svg",
                    f"cabinetmakers-guide/renderings/{slug}.png",
                    purposes[slug],
                    "Dimension-controlled from project/specification.yaml; field values remain blank where required",
                    f"{REVISION} generated; contact-sheet visual inspection required",
                ]
            )
    print(f"PASS: generated {len(renderers)} cabinetmaker 3D renderings in {OUT}")


if __name__ == "__main__":
    generate()
