#!/usr/bin/env python3
"""Build the RL-02 first-crosscut guide for the Rev. G no-resaw door."""

from __future__ import annotations

import csv
import json
import math
import shutil
from fractions import Fraction
from pathlib import Path

from pypdf import PdfReader
from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
ROUGH_PLAN_PATH = ROOT / "project" / "rough-length-cut-plan.json"
STOCK_PLAN_PATH = ROOT / "project" / "labeled-stock-plan.json"
SPEC_PATH = ROOT / "project" / "specification.yaml"
SOURCE_DIR = ROOT / "stock-plan"
OUTPUT_PDF_DIR = ROOT / "output" / "pdf"
OUTPUT_CSV_DIR = ROOT / "output" / "csv"
RELEASE_DIR = ROOT / "release"
NAME = "DC-1916-001_Rough_Length_Cut_List"
SOURCE_MD = SOURCE_DIR / f"{NAME}.md"
OUTPUT_PDF = OUTPUT_PDF_DIR / f"{NAME}.pdf"
OUTPUT_CSV = OUTPUT_CSV_DIR / f"{NAME}.csv"

BLUE = colors.HexColor("#173A56")
TEAL = colors.HexColor("#2E6F73")
OAK = colors.HexColor("#9A6B2F")
OAK_LIGHT = colors.HexColor("#D7B47B")
OAK_PALE = colors.HexColor("#F4F0E8")
BLUE_PALE = colors.HexColor("#EAF1F5")
GREEN_PALE = colors.HexColor("#EAF2EC")
RED_PALE = colors.HexColor("#F7E9E7")
GRAY_PALE = colors.HexColor("#EEF0F1")
INK = colors.HexColor("#20272D")
GRAY = colors.HexColor("#65717A")
RULE = colors.HexColor("#B9C2C7")
RED = colors.HexColor("#A33B32")
GREEN = colors.HexColor("#3D7452")
WHITE = colors.white


def fraction(value: float | None, denominator: int = 32) -> str:
    if value is None:
        return "-"
    item = Fraction(value).limit_denominator(denominator)
    whole, remainder = divmod(item.numerator, item.denominator)
    if remainder == 0:
        return str(whole)
    return f"{whole}-{remainder}/{item.denominator}" if whole else f"{remainder}/{item.denominator}"


def decimal(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.4f}".rstrip("0").rstrip(".")


def load() -> tuple[dict, dict, dict]:
    return (
        json.loads(ROUGH_PLAN_PATH.read_text(encoding="utf-8")),
        json.loads(STOCK_PLAN_PATH.read_text(encoding="utf-8")),
        json.loads(SPEC_PATH.read_text(encoding="utf-8")),
    )


def first_cut_text(board: dict) -> str:
    if not board["cut_now"]:
        return board["action"]
    return "; ".join(
        f"{row['quantity']} x {fraction(row['shop_length'])}"
        for row in board["cut_now"]
    )


def validate(rough: dict, stock: dict, spec: dict) -> tuple[dict, dict]:
    assert rough["document"]["project"] == stock["document"]["project"] == "DC-1916-001"
    assert rough["document"]["revision"] == stock["document"]["revision"] == spec["project"]["revision"] == "Rev. G"
    assert rough["document"]["stock_plan"] == stock["document"]["stock_plan"] == "LS-05"
    assert rough["document"]["rough_length_plan"] == "RL-02"
    assert math.isclose(spec["opening"]["clear_width"], 24.0)
    assert math.isclose(spec["opening"]["clear_height"], 81.0)
    assert math.isclose(spec["slab"]["finished_width"], 23.75)
    assert math.isclose(spec["slab"]["finished_height"], 80.5)
    assert math.isclose(spec["opening"]["bottom_gap"], 0.375)
    assert math.isclose(spec["frame"]["stile_width"], 4.25)
    assert math.isclose(spec["frame"]["rail_shoulder_length"], 15.25)

    inventory = {row["label"]: row for row in stock["inventory"]}
    boards = {row["label"]: row for row in rough["boards"]}
    assert list(inventory) == list("ABCDEFGHIJKLMNO")
    assert list(boards) == list("ABCDEFGHIJKLMNO")
    assert math.isclose(inventory["A"]["length"], 72.75)
    assert "72-3/4" in boards["A"]["raw_dimensions"]
    assert "6-inch damage removal" in boards["A"]["raw_dimensions"]
    assert math.isclose(inventory["M"]["thickness"], 0.75)
    assert math.isclose(inventory["M"]["width"], 8.25)
    assert math.isclose(inventory["M"]["length"], 99.0)
    assert "finished white oak" in boards["M"]["raw_dimensions"]
    for label in ("N", "O"):
        assert math.isclose(inventory[label]["thickness"], 1.75)
        assert math.isclose(inventory[label]["width"], 11.0)
        assert math.isclose(inventory[label]["length"], 74.0)
        assert "KEEP FULL 74" in boards[label]["action"]
    assert math.isclose(inventory["L"]["width"], 6.0)
    assert "1-5/16 x 6 x 80" in boards["L"]["raw_dimensions"]
    assert math.isclose(inventory["G"]["thickness"], 0.9375)
    assert math.isclose(inventory["G"]["width"], 4.5)
    assert math.isclose(inventory["G"]["length"], 75.0)
    assert "S4S" in boards["G"]["raw_dimensions"]
    assert "THICKNESS/WIDTH/LENGTH PASS" in boards["G"]["action"]
    assert "6-1/2-inch D-101F" in boards["J"]["later_pattern"]
    assert "not authorized for any 6-1/2-inch billet" in boards["L"]["later_pattern"]
    assert math.isclose(
        rough["rules"]["saw_kerf"],
        stock["assumptions"]["saw_kerf"],
    )
    assert math.isclose(rough["rules"]["total_board_end_reserve"], 2.0)

    cut_now_labels = {
        label for label, row in boards.items() if row["cut_now"]
    }
    assert cut_now_labels == {"D", "G", "H", "M"}
    assert all(not boards[label]["cut_now"] for label in "ABCEF IJKL".replace(" ", ""))

    component = {row["id"]: row for row in spec["components"]}
    panel_part = {
        "M": "D-101H",
        "D": "D-101K",
        "G": "D-101J",
        "H": "D-101N",
    }
    expected_shop = {
        "M": 16.0625,
        "D": 12.8125,
        "G": 16.5625,
        "H": 11.3125,
    }
    expected_controlled = {
        "M": 15.5625,
        "D": 12.3125,
        "G": 16.0625,
        "H": 10.8125,
    }
    for label in cut_now_labels:
        row = boards[label]
        segment = row["cut_now"][0]
        finished = component[panel_part[label]]["l"]
        assert math.isclose(segment["shop_length"], expected_shop[label])
        assert math.isclose(segment["controlled_rough_length"], expected_controlled[label])
        assert math.isclose(segment["finished_reference_length"], finished)
        assert math.isclose(segment["shop_length"], finished + 1.0)
        assert math.isclose(
            segment["controlled_rough_length"],
            finished + 0.5,
        )
        used_now = (
            segment["quantity"] * segment["shop_length"]
            + row["cuts_now"] * rough["rules"]["saw_kerf"]
        )
        tail_before = inventory[label]["length"] - used_now
        assert math.isclose(tail_before, row["tail_before_end_reserve"])
        assert math.isclose(
            tail_before - rough["rules"]["total_board_end_reserve"],
            row["planning_tail_after_end_reserve"],
        )

    expected_now_remainders = {
        "M": 48.4375,
        "D": 20.0,
        "G": 6.25,
        "H": 42.6875,
    }
    for label, expected in expected_now_remainders.items():
        assert math.isclose(
            boards[label]["planning_tail_after_end_reserve"],
            expected,
        )
    for label, board in boards.items():
        remainder = board["full_pattern_paper_remainder"]
        if remainder is not None:
            assert remainder >= 0, f"STOCK-{label} has a negative paper remainder"
    assert "face" in boards["B"]["later_pattern"].lower()
    assert "face" in boards["C"]["later_pattern"].lower()
    assert "4-3/8" in boards["I"]["later_pattern"]
    assert "4-3/8" in boards["K"]["later_pattern"]
    assert "width" in boards["I"]["hold_reason"].lower()
    assert "width" in boards["K"]["hold_reason"].lower()
    return inventory, boards


def write_csv(rough: dict, inventory: dict, boards: dict) -> None:
    OUTPUT_CSV_DIR.mkdir(parents=True, exist_ok=True)
    headers = [
        "Stock label",
        "Raw thickness",
        "Raw width",
        "Raw length",
        "First-crosscut status",
        "Billet IDs",
        "Quantity",
        "First-crosscut length",
        "Mill-to controlled rough length",
        "Finished length reference",
        "Purpose",
        "Cuts now",
        "Nominal uncut length before end reserve",
        "Planning tail after shared end reserve",
        "Later pattern",
        "Full-pattern paper remainder",
        "Hold / risk",
    ]
    rows = []
    for label in "ABCDEFGHIJKLMNO":
        inv = inventory[label]
        board = boards[label]
        segments = board["cut_now"] or [{
            "quantity": 0,
            "shop_length": None,
            "controlled_rough_length": None,
            "finished_reference_length": None,
            "purpose": "Keep the original board intact",
            "billet_ids": "",
        }]
        for segment in segments:
            rows.append([
                f"STOCK-{label}",
                decimal(inv["thickness"]),
                decimal(inv["width"]),
                decimal(inv["length"]),
                board["action"],
                segment["billet_ids"],
                segment["quantity"],
                decimal(segment["shop_length"]),
                decimal(segment["controlled_rough_length"]),
                decimal(segment["finished_reference_length"]),
                segment["purpose"],
                board["cuts_now"],
                decimal(board["tail_before_end_reserve"]),
                decimal(board["planning_tail_after_end_reserve"]),
                board["later_pattern"],
                decimal(board["full_pattern_paper_remainder"]),
                board["hold_reason"],
            ])
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)


def write_markdown(rough: dict, inventory: dict, boards: dict) -> None:
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    doc = rough["document"]
    rules = rough["rules"]
    lines = [
        "# DC-1916-001 Rough-Length Cut List",
        "",
        f"**Revision:** {doc['revision']}  ",
        f"**Stock plan:** {doc['stock_plan']}  ",
        f"**Rough-length plan:** {doc['rough_length_plan']}  ",
        f"**Date:** {doc['date']}  ",
        f"**Status:** {doc['status']}",
        "",
        "This is the first-crosscut guide for STOCK-A through STOCK-O. STOCK-M is reported finished white oak at 3/4 x 8-1/4 x 99 inches and carries D-101H. Keep STOCK-A intact at 72-3/4 inches after damage removal. STOCK-N/O are each confirmed finished white oak at 1-3/4 x 11 x 74 inches; keep both full as short-member reserve while CHK-RS-01 records physical clear yield. Door geometry remains 23-3/4 x 80-1/2 x 1-3/8 inches for the confirmed 24 x 81-inch jamb with a 3/8-inch bottom gap.",
        "",
        "> **CONTROLLED-RESERVE RELEASE:** Do not start by cutting every board smaller. Complete CHK-RS-01 on all A-O, then prove CHK-ST-01 on full-length B/C and CHK-ST-02 on full-length I/K. Only after all four critical stile boards pass may M, D, G, and H receive panel crosscuts. Keep A, N, and O intact; E/F remain knot-mapped reserve; J/L wait for CHK-SM-01.",
        "",
        "## At-a-glance first-crosscut list",
        "",
        "| Stock | Raw T x W x L | First action | Cut now | Protected planning tail / next step |",
        "|---|---|---|---|---|",
    ]
    for label in "ABCDEFGHIJKLMNO":
        inv = inventory[label]
        board = boards[label]
        raw = f"{fraction(inv['thickness'])} x {fraction(inv['width'])} x {fraction(inv['length'])}"
        if board["cut_now"]:
            tail = (
                f"{fraction(board['planning_tail_after_end_reserve'])} after the one shared "
                f"{fraction(rules['total_board_end_reserve'])}-inch end allowance; {board['later_pattern']}"
            )
        else:
            tail = board["later_pattern"]
        lines.append(
            f"| STOCK-{label} | {raw} | {board['action']} | "
            f"{first_cut_text(board)} | {tail} |"
        )

    lines += [
        "",
        "## Exact first-stage panel cuts",
        "",
        "The four shop-billet lengths below are each exactly 1 inch longer than the corresponding finished panel length. After the shorter billet is flattened, jointed, rested, and squared, trim it only to the LS-05 controlled rough length shown—not to final panel size.",
        "",
        "| Stock | Billet IDs | First crosscut | Mill-to controlled rough | Finished reference | Planning tail after kerfs + shared 2-inch end allowance |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for label in ["M", "D", "G", "H"]:
        board = boards[label]
        segment = board["cut_now"][0]
        lines.append(
            f"| STOCK-{label} | {segment['billet_ids']} | "
            f"{segment['quantity']} x {fraction(segment['shop_length'])} | "
            f"{fraction(segment['controlled_rough_length'])} | "
            f"{fraction(segment['finished_reference_length'])} | "
            f"{fraction(board['planning_tail_after_end_reserve'])} |"
        )

    lines += [
        "",
        "### Length arithmetic",
        "",
        f"- **M:** reported finished length 99. Three 16-1/16 billets + three 1/8 kerfs + 2 total end allowance = 50-9/16; protected planning tail = 48-7/16. After the panel passes, up to two 16-1/4-inch face-stock mother billets remain conditional, leaving 15-11/16 on the full rough-length pattern.",
        f"- **D:** 4 x 12-13/16 + 4 x 1/8 kerf + 2 total end allowance = 53-3/4; protected planning tail = 20. After both lower panels pass, the tail can provide one 16-1/4-inch face-stock mother billet.",
        f"- **G:** 4 x 16-9/16 + 4 x 1/8 kerf + 2 total end allowance = 68-3/4; protected planning remainder = 9-1/2.",
        f"- **H:** 3 x 11-5/16 + 3 x 1/8 kerf + 2 total end allowance = 36-5/16; protected planning remainder = 42-11/16.",
        "",
        "## Full-length holds and later cuts",
        "",
    ]
    for label in ["A", "B", "C", "E", "F", "I", "J", "K", "L"]:
        board = boards[label]
        lines += [
            f"### STOCK-{label}: {board['action']}",
            "",
            f"- Why: {board['hold_reason']}",
            f"- Later: {board['later_pattern']}",
            "",
        ]

    lines += [
        "## Safe first-crosscut procedure",
        "",
        "1. Acclimate and complete CHK-RS-01 at full board length. Record moisture, metal scan, minimum raw thickness/width, bow, cup, twist, checks, knots, pith, grain runout, and usable clear envelopes.",
        "2. Before any panel or short-member production crosscut, prove B/C at 5/16 THICK x 4-3/8 WIDE x 81-1/8 LONG and prove I/K each have at least 8-7/8 clear jointed width for the two continuous stile lanes.",
        "3. Survey M and H separately. M is reported finished but must still prove at least 5/8 recoverable thickness and three clear upper-panel envelopes; H must remain at least 5/8 thick after flattening and rest.",
        "4. For an end check, mark its visible termination, move at least 1 inch farther into sound wood, cut there, and inspect the fresh end. Repeat if the check remains.",
        "5. Only after Steps 1-3 pass, lay out M/D/G/H billets inside clear envelopes. Keep A intact as reserve. The diagram order is representative; defect-free yield controls the real position.",
        "6. Mark the exact billet length on both edges. Put the full saw kerf on the waste or held-tail side, never inside the billet. Label both faces before separating it.",
        "7. Mill in stages: flatten one face; rest and recheck; plane the opposite face parallel; joint one edge; record actual dressed thickness, width, and clear length; rest again; then square only to the controlled rough length.",
        "8. Never surface a billet shorter or thinner than the machine manufacturer's safe minimum. Keep a longer mother piece or use a verified carrier/sled and guarded procedure when required.",
        "9. Do not trim to finished panel size until after glue-up, flattening, tongue/groove sample release, and the relevant panel gate.",
        "",
        "## Non-negotiable controls",
        "",
        f"- {rules['end_reserve_rule']}",
        f"- {rules['layout_rule']}",
        f"- {rules['kerf_rule']}",
        f"- {rules['label_rule']}",
        f"- {rules['scope_rule']}",
        f"- {rules['zero_spare_release_rule']}",
        f"- {rules['staged_milling_rule']}",
        f"- {rules['machine_minimum_rule']}",
        "",
    ]
    SOURCE_MD.write_text("\n".join(lines), encoding="utf-8")


def styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "RLTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=21,
            leading=23,
            textColor=BLUE,
            alignment=TA_LEFT,
            spaceAfter=3,
        ),
        "eyebrow": ParagraphStyle(
            "RLEyebrow",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.2,
            leading=8.5,
            textColor=TEAL,
            spaceAfter=2,
        ),
        "deck": ParagraphStyle(
            "RLDeck",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8.2,
            leading=10.2,
            textColor=GRAY,
            spaceAfter=5,
        ),
        "h2": ParagraphStyle(
            "RLH2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11.2,
            leading=12.6,
            textColor=BLUE,
            spaceBefore=5,
            spaceAfter=3,
        ),
        "h3": ParagraphStyle(
            "RLH3",
            parent=base["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=9.5,
            textColor=TEAL,
            spaceBefore=3,
            spaceAfter=2,
        ),
        "body": ParagraphStyle(
            "RLBody",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=7.1,
            leading=8.7,
            textColor=INK,
        ),
        "bold": ParagraphStyle(
            "RLBold",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=7.1,
            leading=8.7,
            textColor=INK,
        ),
        "micro": ParagraphStyle(
            "RLMicro",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=6.2,
            leading=7.3,
            textColor=GRAY,
        ),
        "white": ParagraphStyle(
            "RLWhite",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=6.2,
            leading=7.2,
            textColor=WHITE,
        ),
        "center": ParagraphStyle(
            "RLCenter",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=6.7,
            leading=8,
            textColor=INK,
            alignment=TA_CENTER,
        ),
    }


def p(text: object, style: ParagraphStyle) -> Paragraph:
    return Paragraph(str(text), style)


def header(
    story: list,
    s: dict[str, ParagraphStyle],
    rough: dict,
    page: int,
    title: str,
    deck: str,
    status: str | None = None,
) -> None:
    doc = rough["document"]
    story += [
        p(
            f"DC-1916-001 | {doc['revision'].upper()} | {doc['stock_plan']} | "
            f"{doc['rough_length_plan']} | PAGE {page} OF 4",
            s["eyebrow"],
        ),
        p(title, s["title"]),
        p(deck, s["deck"]),
    ]
    if status:
        story += [
            Table(
                [[p(f"<b>STATUS:</b> {status}", s["body"])]],
                colWidths=[9.82 * inch],
                style=TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), RED_PALE),
                    ("BOX", (0, 0), (-1, -1), 0.65, RED),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]),
            ),
            Spacer(1, 4),
        ]


def base_table(
    data: list[list],
    widths: list[float],
    header_color=BLUE,
    font_size: float = 6.4,
) -> Table:
    return Table(
        data,
        colWidths=widths,
        repeatRows=1,
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), header_color),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, OAK_PALE]),
            ("BOX", (0, 0), (-1, -1), 0.5, RULE),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, RULE),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 2.6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.6),
            ("FONTSIZE", (0, 1), (-1, -1), font_size),
        ]),
    )


def workflow_strip(s: dict[str, ParagraphStyle]) -> Table:
    cells = [
        p("<b>1  CONTROLLED-RESERVE RELEASE</b><br/>Map every full board; moisture, metal, defects, warp and clear envelopes.", s["body"]),
        p("<b>2  PROVE B/C</b><br/>Full-length 5/16 x 4-3/8 x 81-1/8 faces.", s["body"]),
        p("<b>3  PROVE I/K + M/H</b><br/>Two-lane stile yield; M/H remain at least 5/8 thick.", s["body"]),
        p("<b>4  RELEASE M/D/G/H</b><br/>2-inch reserve is total per board; keep A/N/O.", s["body"]),
    ]
    return Table(
        [cells],
        colWidths=[2.455 * inch] * 4,
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), BLUE_PALE),
            ("BOX", (0, 0), (-1, -1), 0.5, RULE),
            ("INNERGRID", (0, 0), (-1, -1), 0.3, RULE),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]),
    )


def board_diagram(board: dict, inv: dict, width: float = 700, height: float = 105) -> Drawing:
    drawing = Drawing(width, height)
    raw_length = inv["length"]
    x0, y0, bar_w, bar_h = 10, 35, width - 20, 30
    drawing.add(
        String(
            10,
            height - 14,
            f"STOCK-{board['label']}   RAW {fraction(inv['thickness'])} x "
            f"{fraction(inv['width'])} x {fraction(inv['length'])} IN",
            fontName="Helvetica-Bold",
            fontSize=9,
            fillColor=BLUE,
        )
    )
    drawing.add(
        String(
            width - 10,
            height - 14,
            board["action"],
            fontName="Helvetica-Bold",
            fontSize=7.2,
            textAnchor="end",
            fillColor=GREEN if board["cut_now"] else RED,
        )
    )

    if not board["cut_now"]:
        drawing.add(
            Rect(
                x0,
                y0,
                bar_w,
                bar_h,
                fillColor=GRAY_PALE,
                strokeColor=BLUE,
                strokeWidth=1,
            )
        )
        drawing.add(
            String(
                x0 + bar_w / 2,
                y0 + 11,
                f"KEEP STOCK-{board['label']} FULL LENGTH - {fraction(raw_length)} IN",
                fontName="Helvetica-Bold",
                fontSize=9,
                textAnchor="middle",
                fillColor=RED,
            )
        )
        drawing.add(
            String(
                10,
                12,
                "No saw line is authorized in RL-02. Complete the named release gate first.",
                fontName="Helvetica",
                fontSize=7,
                fillColor=GRAY,
            )
        )
        return drawing

    segment = board["cut_now"][0]
    billet_ids = [item.strip() for item in segment["billet_ids"].split(",")]
    assert len(billet_ids) == segment["quantity"]
    cursor = x0
    unit = bar_w / raw_length
    colors_cycle = [OAK_LIGHT, colors.HexColor("#C99A58")]
    for index in range(segment["quantity"]):
        piece_w = segment["shop_length"] * unit
        drawing.add(
            Rect(
                cursor,
                y0,
                piece_w,
                bar_h,
                fillColor=colors_cycle[index % 2],
                strokeColor=INK,
                strokeWidth=0.6,
            )
        )
        drawing.add(
            String(
                cursor + piece_w / 2,
                y0 + 12,
                f"{billet_ids[index]}  {fraction(segment['shop_length'])}",
                fontName="Helvetica-Bold",
                fontSize=6.5,
                textAnchor="middle",
                fillColor=INK,
            )
        )
        cursor += piece_w
        kerf_w = max(1.1, 0.125 * unit)
        drawing.add(
            Rect(
                cursor,
                y0 - 3,
                kerf_w,
                bar_h + 6,
                fillColor=RED,
                strokeColor=RED,
                strokeWidth=0,
            )
        )
        cursor += 0.125 * unit

    tail_w = max(0, x0 + bar_w - cursor)
    drawing.add(
        Rect(
            cursor,
            y0,
            tail_w,
            bar_h,
            fillColor=BLUE_PALE,
            strokeColor=BLUE,
            strokeWidth=0.7,
        )
    )
    if tail_w > 65:
        drawing.add(
            String(
                cursor + tail_w / 2,
                y0 + 12,
                f"HOLD TAIL  {fraction(board['tail_before_end_reserve'])}",
                fontName="Helvetica-Bold",
                fontSize=7,
                textAnchor="middle",
                fillColor=BLUE,
            )
        )
    drawing.add(
        String(
            10,
            12,
            f"Representative nesting after defect map. Planning tail after one shared 2-in end allowance: "
            f"{fraction(board['planning_tail_after_end_reserve'])} in.",
            fontName="Helvetica",
            fontSize=7,
            fillColor=GRAY,
        )
    )
    return drawing


def math_box(text: str, s: dict[str, ParagraphStyle], color=GREEN_PALE) -> Table:
    return Table(
        [[p(text, s["body"])]],
        colWidths=[9.82 * inch],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), color),
            ("BOX", (0, 0), (-1, -1), 0.55, GREEN if color == GREEN_PALE else RULE),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]),
    )


def footer(canvas, doc) -> None:
    canvas.saveState()
    page_w, _ = landscape(letter)
    canvas.setStrokeColor(OAK)
    canvas.line(0.48 * inch, 0.40 * inch, page_w - 0.48 * inch, 0.40 * inch)
    canvas.setFillColor(BLUE)
    canvas.setFont("Helvetica", 6.4)
    canvas.drawString(
        0.48 * inch,
        0.23 * inch,
        "DC-1916-001 | ROUGH-LENGTH CUT LIST | REV. G | LS-05 | RL-02",
    )
    canvas.setFillColor(GRAY)
    canvas.drawRightString(
        page_w - 0.48 * inch,
        0.23 * inch,
        f"PAGE {doc.page} OF 4",
    )
    canvas.restoreState()


def build_pdf(rough: dict, stock: dict, spec: dict, inventory: dict, boards: dict) -> None:
    OUTPUT_PDF_DIR.mkdir(parents=True, exist_ok=True)
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    s = styles()
    doc = SimpleDocTemplate(
        str(OUTPUT_PDF),
        pagesize=landscape(letter),
        leftMargin=0.48 * inch,
        rightMargin=0.48 * inch,
        topMargin=0.36 * inch,
        bottomMargin=0.48 * inch,
        title="DC-1916-001 Rough-Length Cut List",
        author=spec["project"]["copyright_holder"],
        subject="RL-02 first-crosscut control for STOCK-A through STOCK-O under Rev. G / LS-05",
    )
    story: list = []

    # Page 1: working list
    header(
        story,
        s,
        rough,
        1,
        "Rough-Length First-Crosscut List",
        "A bench-ready plan for STOCK-A through STOCK-O. M = 3/4 x 8-1/4 x 99 inches finished white oak and carries D-101H; keep A full at 72-3/4 inches. N/O are each confirmed finished white oak at 1-3/4 x 11 x 74 inches and remain full-length short-member reserve. Door remains 23-3/4 x 80-1/2 x 1-3/8 in the 24 x 81 jamb with 3/8-inch bottom gap.",
        rough["document"]["status"],
    )
    story.append(workflow_strip(s))
    story.append(p("Every board at a glance", s["h2"]))
    summary = [[p(x, s["white"]) for x in [
        "STOCK",
        "RAW T x W x L",
        "FIRST-CROSSCUT STATUS",
        "CUT / KEEP NOW",
        "PROTECTED TAIL OR NEXT GATE",
    ]]]
    for label in "ABCDEFGHIJKLMNO":
        inv = inventory[label]
        board = boards[label]
        if board["cut_now"]:
            next_step = (
                f"{fraction(board['planning_tail_after_end_reserve'])} planning tail "
                f"after shared 2-in end allowance"
            )
        else:
            next_step = board["hold_reason"]
        summary.append([
            p(f"<b>{label}</b>", s["center"]),
            p(
                f"{fraction(inv['thickness'])} x {fraction(inv['width'])} x "
                f"{fraction(inv['length'])}",
                s["body"],
            ),
            p(board["action"], s["micro"]),
            p(first_cut_text(board), s["bold"]),
            p(next_step, s["micro"]),
        ])
    story.append(
        base_table(
            summary,
            [0.48 * inch, 1.35 * inch, 2.05 * inch, 1.62 * inch, 4.32 * inch],
            TEAL,
            6.0,
        )
    )
    story.append(PageBreak())

    # Page 2: M and D
    header(
        story,
        s,
        rough,
        2,
        "Cut-Now Details: STOCK-M and STOCK-D",
        "Complete CHK-RS-01 first. These diagrams show representative clear-zone nesting, not blind cumulative marks from a rough end.",
        "CUT ONLY WHEN EVERY NAMED BILLET AND THE PROTECTED TAIL ARE VISIBLE INSIDE THE DEFECT MAP.",
    )
    for label in ["M", "D"]:
        board = boards[label]
        segment = board["cut_now"][0]
        story.append(board_diagram(board, inventory[label]))
        story.append(
            math_box(
                (
                    f"<b>STOCK-{label} CUT:</b> {segment['quantity']} x "
                    f"{fraction(segment['shop_length'])} in ({segment['billet_ids']}). "
                    f"After milling and rest, each must still reach "
                    f"{fraction(segment['controlled_rough_length'])} in controlled rough "
                    f"length; finished reference {fraction(segment['finished_reference_length'])} in. "
                    f"<b>Later:</b> {board['later_pattern']}"
                ),
                s,
            )
        )
        story.append(Spacer(1, 6))
    story.append(p("Board-specific arithmetic", s["h2"]))
    arithmetic = [
        [
            p("<b>M</b>", s["center"]),
            p("3 x 16-1/16 + 3 x 1/8 kerf + 2 shared end allowance = 50-9/16.", s["body"]),
            p("Protected tail 48-7/16. After panel release, up to two 16-1/4 face-stock billets are conditional on clear signed zones; full-pattern paper remainder 15-11/16.", s["body"]),
        ],
        [
            p("<b>D</b>", s["center"]),
            p("4 x 12-13/16 + 4 x 1/8 kerf + 2 shared end allowance = 53-3/4.", s["body"]),
            p("Protected tail 20. After both lower panels pass, cut one 16-1/4 face-stock mother billet from a clear zone.", s["body"]),
        ],
    ]
    story.append(
        Table(
            arithmetic,
            colWidths=[0.45 * inch, 4.35 * inch, 5.02 * inch],
            style=TableStyle([
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, OAK_PALE]),
                ("BOX", (0, 0), (-1, -1), 0.5, RULE),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, RULE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]),
        )
    )
    story.append(PageBreak())

    # Page 3: G and H
    header(
        story,
        s,
        rough,
        3,
        "Cut-Now Details: STOCK-G and STOCK-H",
        "G is confirmed S4S at 15/16 x 4-1/2 x 75. H remains rough and thickness-critical; a positive length remainder does not release a failed billet.",
        "G THICKNESS/WIDTH/LENGTH PASS; CHK-P-01 STILL CONTROLS. H MUST PROVE THE COMPLETE 5/8-INCH YIELD ENVELOPE.",
    )
    for label in ["G", "H"]:
        board = boards[label]
        segment = board["cut_now"][0]
        story.append(board_diagram(board, inventory[label]))
        story.append(
            math_box(
                (
                    f"<b>STOCK-{label} CUT:</b> {segment['quantity']} x "
                    f"{fraction(segment['shop_length'])} in ({segment['billet_ids']}). "
                    f"After milling and rest, each must still reach "
                    f"{fraction(segment['controlled_rough_length'])} in controlled rough "
                    f"length; finished reference {fraction(segment['finished_reference_length'])} in. "
                    f"<b>Tail:</b> {board['later_pattern']}"
                ),
                s,
            )
        )
        story.append(Spacer(1, 6))
    story.append(p("Board-specific arithmetic and yield gate", s["h2"]))
    yield_rows = [
        [
            p("<b>G</b>", s["center"]),
            p("4 x 16-9/16 + 4 x 1/8 kerf + 2 shared end allowance = 68-3/4.", s["body"]),
            p("6-1/4 remains after the shared reserve. The 15/16-inch thickness passes; four jointed staves must retain 16-3/8 aggregate width.", s["body"]),
        ],
        [
            p("<b>H</b>", s["center"]),
            p("3 x 11-5/16 + 3 x 1/8 kerf + 2 shared end allowance = 36-5/16.", s["body"]),
            p("42-11/16 remains on paper. Each billet must finish at least 5/8 thick; use minimal passes.", s["body"]),
        ],
    ]
    story.append(
        Table(
            yield_rows,
            colWidths=[0.45 * inch, 4.35 * inch, 5.02 * inch],
            style=TableStyle([
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, OAK_PALE]),
                ("BOX", (0, 0), (-1, -1), 0.5, RULE),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, RULE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]),
        )
    )
    story.append(PageBreak())

    # Page 4: holds and staged release
    header(
        story,
        s,
        rough,
        4,
        "Full-Length Holds and Later Cut Map",
        "Board M carries the upper panel; Boards N/O add uncut short-core reserve. Continuous stile yield still controls before consuming a panel or short-member board. Shortening a held board destroys the flexibility that makes the complete door feasible.",
        "CONTROLLED-RESERVE ORDER: SURVEY A-O; PROVE B/C; PROVE I/K; SURVEY M/H; KEEP N/O FULL; ONLY THEN RELEASE PANEL CUTS.",
    )
    holds = [[p(x, s["white"]) for x in [
        "STOCK",
        "KEEP NOW",
        "WHY IT STAYS LONG",
        "AUTHORIZED LATER PATTERN",
        "PAPER REMAINDER",
    ]]]
    for label in ["B", "C", "E", "F", "I", "J", "K", "L"]:
        board = boards[label]
        inv = inventory[label]
        remainder = (
            "unassigned reserve"
            if board["full_pattern_paper_remainder"] is None
            else f"{fraction(board['full_pattern_paper_remainder'])} in"
        )
        holds.append([
            p(f"<b>{label}</b>", s["center"]),
            p(f"FULL {fraction(inv['length'])} IN", s["bold"]),
            p(board["hold_reason"], s["micro"]),
            p(board["later_pattern"], s["micro"]),
            p(remainder, s["center"]),
        ])
    story.append(
        base_table(
            holds,
            [0.45 * inch, 1.03 * inch, 2.75 * inch, 4.72 * inch, 0.87 * inch],
            RED,
            5.75,
        )
    )
    story.append(p("Release sequence for the held boards", s["h2"]))
    release_steps = [
        [
            p("<b>1  SURVEY A-O</b>", s["body"]),
            p("Acclimate, metal scan, and record minimum raw thickness/width, cup, bow, twist, defects, and usable clear length before any saw cut.", s["body"]),
        ],
        [
            p("<b>2  PROVE B + C</b>", s["body"]),
            p("Keep full. Each must yield one continuous 5/16 THICK x 4-3/8 WIDE x 81-1/8 LONG face after flatten, rest, staged planing, and recheck.", s["body"]),
        ],
        [
            p("<b>3  PROVE I + K</b>", s["body"]),
            p("Keep full. Prove at least 8-7/8 inches clear jointed width, then rip two 4-3/8-inch lanes. One finishes 7/8; one finishes 5/16; both stay continuous.", s["body"]),
        ],
        [
            p("<b>4  PROVE M/H; CUT PANELS</b>", s["body"]),
            p("M and H must remain at least 5/8 thick after preparation and rest. Then release only the mapped M/D/G/H panel billets; keep A intact as reserve and stop at controlled rough size.", s["body"]),
        ],
        [
            p("<b>5  SHORT MEMBERS</b>", s["body"]),
            p("Map E/F knots, sign J/L core map and FP-05, then cut named billets only. Retain every tail and offcut until the completed door passes.", s["body"]),
        ],
    ]
    story.append(
        Table(
            release_steps,
            colWidths=[1.25 * inch, 8.57 * inch],
            style=TableStyle([
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [BLUE_PALE, WHITE]),
                ("BOX", (0, 0), (-1, -1), 0.5, RULE),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, RULE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]),
        )
    )
    story.append(Spacer(1, 5))
    story.append(
        math_box(
            "<b>STOP RULE:</b> If actual combined end loss exceeds the listed reserve, "
            "or any billet cannot yield its controlled thickness, width, and clear length, "
            "stop and remap before processing another board. Do not shorten a stile, hide "
            "an end splice, narrow the door, or borrow critical stock for moulding. Never "
            "measure only after all boards have been milled. Never surface below the machine "
            "manufacturer's safe minimum length or thickness; keep a longer mother piece or "
            "use a verified carrier/sled and guarded procedure.",
            s,
            RED_PALE,
        )
    )

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    shutil.copy2(OUTPUT_PDF, RELEASE_DIR / OUTPUT_PDF.name)
    shutil.copy2(OUTPUT_CSV, RELEASE_DIR / OUTPUT_CSV.name)
    shutil.copy2(SOURCE_MD, RELEASE_DIR / SOURCE_MD.name)


def validate_outputs() -> None:
    reader = PdfReader(str(OUTPUT_PDF))
    assert len(reader.pages) == 4, f"expected 4 pages, got {len(reader.pages)}"
    raw_text = "\n".join(page.extract_text() or "" for page in reader.pages).lower()
    text = " ".join(raw_text.split())
    required = [
        "rough-length first-crosscut list",
        "rev. g",
        "ls-05",
        "rl-02",
        "stock-a",
        "stock-m",
        "1-5/16 x 6 x 80",
        "3 x 16-1/16",
        "3/4 x 8-1/4 x 99",
        "48-7/16",
        "15-11/16",
        "4 x 12-13/16",
        "4 x 16-9/16",
        "3 x 11-5/16",
        "keep full 85 inches",
        "no crosscut - keep full 82-1/2 inches",
        "4-3/8-inch lanes",
        "3/8-inch bottom gap",
        "controlled-reserve release",
        "prove b + c",
        "prove i + k",
        "machine manufacturer's safe minimum",
    ]
    for term in required:
        assert term in text, f"PDF missing required term: {term}"
    for prohibited in [
        "cut every board now",
        "rough length b to",
        "rough length c to",
        "rough length i to",
        "rough length k to",
        "2 inches per billet",
    ]:
        assert prohibited not in text, f"PDF contains prohibited direction: {prohibited}"


def main() -> None:
    rough, stock, spec = load()
    inventory, boards = validate(rough, stock, spec)
    write_csv(rough, inventory, boards)
    write_markdown(rough, inventory, boards)
    build_pdf(rough, stock, spec, inventory, boards)
    validate_outputs()
    print(
        f"PASS: built {OUTPUT_PDF.name} (4 pages), Markdown, and CSV "
        f"for Rev. G / LS-05 / RL-02"
    )


if __name__ == "__main__":
    main()
