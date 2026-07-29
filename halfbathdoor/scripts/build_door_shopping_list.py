#!/usr/bin/env python3
"""Build the controlled Rev. G / LS-05 no-resaw door-only shopping list."""

from __future__ import annotations

import csv
import json
import math
import shutil
from pathlib import Path

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
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
SPEC_PATH = ROOT / "project" / "specification.yaml"
STOCK_PLAN_PATH = ROOT / "project" / "labeled-stock-plan.json"
BUY_LIST_PATH = ROOT / "build" / "reports" / "buy-list.csv"
CUT_LIST_PATH = ROOT / "build" / "reports" / "cut-list.csv"
SOURCE = ROOT / "shopping-list" / "DC-1916-001_Door_Shopping_List.md"
OUTPUT_DIR = ROOT / "output" / "pdf"
OUTPUT = OUTPUT_DIR / "DC-1916-001_Door_Shopping_List.pdf"
RELEASE_PDF = ROOT / "release" / OUTPUT.name
RELEASE_MD = ROOT / "release" / SOURCE.name

BLUE = colors.HexColor("#173A56")
TEAL = colors.HexColor("#2E6F73")
OAK = colors.HexColor("#9A6B2F")
PALE_BLUE = colors.HexColor("#EAF1F5")
PALE_TEAL = colors.HexColor("#E9F2F1")
PALE_OAK = colors.HexColor("#F4F0E8")
INK = colors.HexColor("#20272D")
GRAY = colors.HexColor("#65717A")
RULE = colors.HexColor("#B9C2C7")
WHITE = colors.white


def load_inputs():
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    stock_plan = json.loads(STOCK_PLAN_PATH.read_text(encoding="utf-8"))
    with BUY_LIST_PATH.open(newline="", encoding="utf-8") as handle:
        buy_rows = list(csv.DictReader(handle))
    with CUT_LIST_PATH.open(newline="", encoding="utf-8") as handle:
        cut_rows = list(csv.DictReader(handle))
    return spec, stock_plan, buy_rows, cut_rows


def row_by_item(rows, item, specification=None):
    matches = [
        row
        for row in rows
        if row["Item"] == item
        and (specification is None or row["Specification"] == specification)
    ]
    if len(matches) != 1:
        raise ValueError(f"expected one buy-list row for {item!r}, found {len(matches)}")
    return matches[0]


def cut_row(rows, part_id):
    matches = [row for row in rows if row["Part identifier"] == part_id]
    if len(matches) != 1:
        raise ValueError(f"expected one cut-list row for {part_id}, found {len(matches)}")
    return matches[0]


def rough_board_feet(rows, ids):
    total = 0.0
    for part_id in ids:
        row = cut_row(rows, part_id)
        total += (
            float(row["Rough thickness"])
            * float(row["Rough width"])
            * float(row["Rough length"])
            * int(row["Quantity"])
            / 144.0
        )
    return total


def validate_inputs(spec, stock_plan, buy_rows, cut_rows):
    assert spec["project"]["revision"] == "Rev. G"
    assert math.isclose(spec["opening"]["clear_height"], 81.0)
    assert math.isclose(spec["opening"]["clear_width"], 24.0)
    assert math.isclose(spec["opening"]["hinge_side_reveal"], 0.125)
    assert math.isclose(spec["opening"]["lock_side_reveal"], 0.125)
    assert math.isclose(spec["opening"]["head_reveal"], 0.125)
    assert math.isclose(spec["opening"]["bottom_gap"], 0.375)
    assert math.isclose(spec["slab"]["finished_height"], 80.5)
    assert math.isclose(spec["slab"]["finished_width"], 23.75)
    assert math.isclose(spec["milling"]["prefit_assembly_height"], 80.625)
    assert math.isclose(spec["milling"]["prefit_assembly_width"], 23.875)
    assert math.isclose(spec["frame"]["stile_width"], 4.25)
    assert math.isclose(spec["frame"]["rail_shoulder_length"], 15.25)
    assert stock_plan["document"]["stock_plan"] == "LS-05"
    assert stock_plan["document"]["supersedes"] == "LS-04"
    assert stock_plan["document"]["revision"] == "Rev. G"
    assert stock_plan["assumptions"]["dimensions_are_dressed_not_nominal"] is False
    assert stock_plan["assumptions"]["reported_dimensions_are_raw"] is False
    assert "reserved exclusively for the door" in stock_plan["assumptions"][
        "scope_rule"
    ].lower()

    construction = spec["frame"]["construction"]
    assert construction["type"] == (
        "balanced three-layer, all-long-grain solid-oak lamination"
    )
    assert math.isclose(construction["show_face_preglue_thickness"], 0.3125)
    assert math.isclose(construction["core_preglue_thickness"], 0.875)
    assert math.isclose(construction["back_face_preglue_thickness"], 0.3125)
    assert math.isclose(construction["show_face_finished_thickness"], 0.25)
    assert math.isclose(construction["back_face_finished_thickness"], 0.25)

    assert {row["label"] for row in stock_plan["inventory"]} == set("ABCDEFGHIJKLMNO")
    allocations = {
        row["part"]: row for row in stock_plan["component_allocations"]
    }
    frame_ids = {
        "D-101A",
        "D-101B",
        "D-101C",
        "D-101M",
        "D-101D",
        "D-101E",
        "D-101F",
        "D-101G",
    }
    for part_id in frame_ids:
        assert "CONDITIONAL" in allocations[part_id]["status"]
        assert allocations[part_id]["stock"] != "NEW"

    assert stock_plan["purchase_requirements"] == []
    assert (
        stock_plan["purchase_summary"]["status"]
        == "NO DOOR LUMBER PURCHASE RELEASED"
    )
    assert stock_plan["purchase_summary"]["planning_quantity_bf"] == 0
    assert "buy only a failed layer" in stock_plan[
        "purchase_summary"
    ]["conditional_credit"].lower()

    checks = {row["id"]: row for row in stock_plan["critical_checks"]}
    assert set(checks) == {
        "CHK-RS-01",
        "CHK-ST-01",
        "CHK-ST-02",
        "CHK-SM-01",
        "CHK-FP-01",
        "CHK-P-01",
        "CHK-LAM-01",
        "CHK-SEAM-01",
    }
    assert "replacement" in checks["CHK-ST-01"]["fallback"].lower()
    assert "replacement" in checks["CHK-ST-02"]["fallback"].lower()
    assert "purchase only the failed core stock" in checks["CHK-SM-01"][
        "fallback"
    ].lower()

    door_stock = row_by_item(buy_rows, "Owner-labeled door stock A-O")
    assert "71.52" in door_stock["Quantity"]
    assert "STOCK-G confirmed 15/16 x 4-1/2 x 75" in door_stock["Quantity"]
    assert "no door-lumber purchase released" in door_stock["Quantity"].lower()
    assert "all frame layers" in door_stock["Purpose"].lower()
    assert "no transfer to moulding" in door_stock["Substitution constraints"].lower()
    assert "CHK-ST-01/02" in door_stock["Field verification"]
    assert not any(
        row["Item"] in {"Door frame stock", "Panel stock"} for row in buy_rows
    )
    assert len(
        [row for row in buy_rows if row["Category"] == "Moulding stock"]
    ) == 2, "door list must point to, but not reproduce, the separate moulding order"
    assert (
        row_by_item(buy_rows, "Factory beech tenons", "10 x 50 mm")["Quantity"]
        == "60 total: 26 final + 26 retained test + 8 spare"
    )
    assert (
        row_by_item(buy_rows, "Factory beech tenons", "6 x 40 mm")["Quantity"]
        == "12 total: 4 final + 4 retained test + 4 spare"
    )
    foam_quantity = row_by_item(
        buy_rows, "3/4-inch-long foam panel spacers"
    )["Quantity"]
    assert foam_quantity.startswith("30 controlled minimum:")
    assert "order 40" in foam_quantity
    pva = row_by_item(buy_rows, "Type II PVA")
    assert pva["Quantity"].startswith("32 oz minimum")
    assert "actual layup area" in pva["Quantity"].lower()
    assert "full-area oak lamination" in pva["Specification"].lower()
    assert row_by_item(buy_rows, "Mortise lock set")["Quantity"] == "1 set"
    assert row_by_item(buy_rows, "Butt hinges")["Quantity"] == "3"

    expected_rough = {
        "D-101A": (1.5, 4.375, 81.125),
        "D-101A-CORE": (0.875, 4.375, 81.0),
        "D-101A-SF": (0.3125, 4.375, 81.125),
        "D-101B": (1.5, 4.375, 81.125),
        "D-101B-CORE": (0.875, 4.375, 81.0),
        "D-101B-BF": (0.3125, 4.375, 81.125),
        "D-101F": (1.5, 12.25, 16.25),
        "D-101F-CORE": (0.875, 12.25, 16.25),
        "D-101F-SF": (0.3125, 12.25, 16.25),
        "D-101H": (0.625, 16.375, 15.5625),
        "D-101J": (0.625, 16.375, 16.0625),
        "D-101N": (0.625, 16.375, 10.8125),
        "D-101K": (0.625, 7.375, 12.3125),
        "D-101L": (0.625, 7.375, 12.3125),
    }
    for part_id, expected in expected_rough.items():
        row = cut_row(cut_rows, part_id)
        actual = tuple(
            float(row[key])
            for key in ("Rough thickness", "Rough width", "Rough length")
        )
        assert actual == expected, f"{part_id}: expected rough {expected}, got {actual}"


def styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ShoppingTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=23,
            leading=25,
            textColor=BLUE,
            alignment=TA_LEFT,
            spaceAfter=4,
        ),
        "eyebrow": ParagraphStyle(
            "ShoppingEyebrow",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.2,
            leading=8.5,
            textColor=TEAL,
            tracking=0.8,
            spaceAfter=3,
        ),
        "deck": ParagraphStyle(
            "ShoppingDeck",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8.6,
            leading=11,
            textColor=GRAY,
            spaceAfter=6,
        ),
        "h2": ParagraphStyle(
            "ShoppingH2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11.5,
            leading=13,
            textColor=BLUE,
            spaceBefore=5,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "ShoppingBody",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=7.4,
            leading=9.2,
            textColor=INK,
        ),
        "body_bold": ParagraphStyle(
            "ShoppingBodyBold",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=7.4,
            leading=9.2,
            textColor=INK,
        ),
        "micro": ParagraphStyle(
            "ShoppingMicro",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=6.6,
            leading=8.1,
            textColor=GRAY,
        ),
        "micro_white": ParagraphStyle(
            "ShoppingMicroWhite",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=6.8,
            leading=8.1,
            textColor=WHITE,
        ),
        "right": ParagraphStyle(
            "ShoppingRight",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=7.1,
            leading=8.8,
            textColor=INK,
            alignment=TA_RIGHT,
        ),
        "center": ParagraphStyle(
            "ShoppingCenter",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=7.1,
            leading=8.8,
            textColor=INK,
            alignment=TA_CENTER,
        ),
    }


def p(text, style):
    return Paragraph(text, style)


def write_markdown(spec, stock_plan, buy_rows, cut_rows):
    door_stock = row_by_item(buy_rows, "Owner-labeled door stock A-O")
    foam = row_by_item(buy_rows, "3/4-inch-long foam panel spacers")
    pva = row_by_item(buy_rows, "Type II PVA")
    lines = [
        "# DC-1916-001 Door Shopping List",
        "",
        "**Revision:** Rev. G  ",
        "**Stock plan:** LS-05 (supersedes LS-04)  ",
        "**Confirmed jamb:** 24 x 81-inch installed jamb; clear dimensions confirmed consistent throughout  ",
        "**Prefit assembly:** 23-7/8 x 80-5/8 inches  ",
        "**Final geometry:** 23-3/4 x 80-1/2-inch finished fitted slab, 1-3/8 inches thick; 1/8-inch reveals at both sides and head, 3/8-inch bottom gap  ",
        "**Scope:** Door slab only. Moulding is not purchased from this list. Use the separate controlled two-face moulding order and never transfer STOCK-A through STOCK-O to casing, backband, stop, cap, or plinth.",
        "",
        "## Door lumber status - LS-05",
        "",
        "| Buy | Quantity / status | Controlled specification and gate |",
        "|---|---|---|",
        f"| General door lumber | **0 BF - NO PURCHASE RELEASED** | {door_stock['Quantity']}. Reserve all A-O stock exclusively for the door, its same-layup coupons, setup pieces, substitutions, and repair stock. This is conditional inventory, not proven yield. |",
        "| Gate-specific replacement only | **BUY ONLY AFTER A SIGNED FAILURE** | CHK-RS-01, CHK-ST-01/02, CHK-SM-01, CHK-FP-01, CHK-P-01, CHK-LAM-01, or CHK-SEAM-01 identifies the failed layer, short-member family, face pool, panel stock, or seam-controlled assembly. Buy only that replacement; never shorten, narrow, end-splice, or consume a critical stile layer to solve another shortage. |",
        "",
        "The complete recorded on-hand inventory totals approximately 71.52 current-envelope board feet. STOCK-G is confirmed S4S at 15/16 x 4-1/2 x 75 inches; its thickness exceeds the 5/8-inch D-101J rough-panel minimum by 5/16 inch, and its four-stave width/length plan fits. CHK-P-01 still controls clear physical yield before crosscutting. STOCK-M carries D-101H; A remains intact; STOCK-N/O remain uncut short-member core reserve. The zero-purchase status remains conditional.",
        "",
        "> **Separate moulding order:** Obtain casing, backband, stop, and any field-approved cap from the controlled two-face moulding schedule in the Custom Moulding Shop Manual. No moulding purchase row is part of this door-only list, and no A-O stock may be reassigned to moulding before final door release.",
        "",
        "## Other buy quantities",
        "",
        "| Quantity | Item | Controlled specification |",
        "|---:|---|---|",
        "| 60 pieces | Factory beech Domino tenons, 10 x 50 mm | 26 final, 26 retained setup/test, and 8 spare; segregate all three groups. |",
        "| 12 pieces | Factory beech Domino tenons, 6 x 40 mm | 4 final, 4 retained setup/test, and 4 spare for D-101G-to-D-101E/F. |",
        f"| {foam['Quantity']} | 3/4-inch-long foam panel spacers | {foam['Specification']}; {foam['Selection notes']} |",
        f"| {pva['Quantity']} | Type II PVA adhesive | Fresh, within shelf life, and manufacturer-approved for full-area oak lamination. Verify spread rate, open time, clamp pressure, temperature, cure, and actual coverage on same-layup coupons. |",
        "| 1 complete set | Traditional brass privacy mortise lock | Include body, faceplate, strike, spindle, knobs/levers, escutcheons, final screws, and same-size steel setup screws plus spares. Physical sample controls machining. |",
        "| 3 | 3-1/2-inch brass butt hinges | Confirm load rating; include final brass screws and same-size steel setup screws plus spares. Physical sample controls machining. |",
        "| 1 x 350 mL set | Rubio Monocoat Oil Plus 2C, Pure | Make and approve a complete finish sample before finishing the door. |",
        "| 1 shop pack | Abrasives | P80, P100, and P120 discs plus hand sheets. |",
        "| As required | Stable plywood jig stock | Dimensioned 1/2- and 3/4-inch Baltic-birch offcuts; if unavailable, buy one half-sheet of each thickness. |",
        "| 1 | Oily-waste safety container | Lidded metal can or water-filled sealed metal container suitable for local disposal requirements. |",
        "",
        "## Balanced frame lamination schedule",
        "",
        "Every frame member is an all-long-grain, balanced solid-oak lamination. Prepare the core and both faces separately, press both faces simultaneously, cure and rest on a flat platen, then surface equally before any groove, Domino, hinge, or lock machining.",
        "",
        "| Part(s) / layer | Quantity | Minimum controlled post-selection billet |",
        "|---|---:|---|",
        "| D-101A/B continuous stile cores | 2 | 7/8 x 4-3/8 x 81 inches; K for A and I for B |",
        "| D-101A/B continuous stile faces | 4 | 5/16 x 4-3/8 x 81-1/8 inches; B and C provide one face each, and the parallel I/K lanes provide the other two |",
        "| D-101C/M/E/G cores and faces | 4 members | J/L supply the one-piece cores; staged-planed faces come from the signed A/D/H/C/J/L plus knot-mapped E/F face pool |",
        "| D-101D/F cores and faces | 2 members | Stave-built sheets from the signed no-resaw face-pool map; preserve the staggered CHK-SEAM-01 locations |",
        "",
        "**Preglue:** 5/16 show face + 7/8 core + 5/16 back face = 1-1/2 inches.  ",
        "**Finished:** remove 1/16 inch equally from each outer face to produce 1/4 + 7/8 + 1/4 = 1-3/8 inches.",
        "**No-resaw rule:** staged-plane every face layer from a whole long lane or short mother billet; ordinary rips divide width only.",
        "",
        "## Panel yield held inside A-O",
        "",
        "| Part(s) | Quantity | Minimum controlled rough blank |",
        "|---|---:|---|",
        "| D-101H upper panel | 1 | 5/8 x 16-3/8 x 15-9/16 inches |",
        "| D-101J center panel | 1 | 5/8 x 16-3/8 x 16-1/16 inches |",
        "| D-101N lower-center panel | 1 | 5/8 x 16-3/8 x 10-13/16 inches |",
        "| D-101K/L lower panels | 2 | 5/8 x 7-3/8 x 12-5/16 inches |",
        "",
        "STOCK-M/G/H/D are the primary panel sources for H/J/N/K-L; STOCK-A is the first upper-panel fallback. CHK-RS-01 and CHK-P-01 must prove post-preparation thickness, aggregate clean width, clear squared length, grain, color, and defect placement. E/F and uncommitted J/L remain door-only reserves after the structural short-member map passes.",
        "",
        "## Receiving and release checklist",
        "",
        "- [ ] Moisture is 6-9% at receipt and after acclimation.",
        "- [ ] CHK-RS-01 records actual milled yield, bow, cup, twist, checks, and defects; no rough face or edge is a datum.",
        "- [ ] CHK-ST-01 proves B/C each yield one continuous 5/16-inch stile face.",
        "- [ ] CHK-ST-02 proves I/K each yield two 4-3/8-inch lanes: one continuous 7/8-inch core and one continuous 5/16-inch face.",
        "- [ ] CHK-SM-01 yields every J/L short-member core and the full no-resaw face pool, including at least five clear 16-1/4-inch E/F mother billets.",
        "- [ ] CHK-FP-01 signs every short-member show/back face strip and the D/F seam maps.",
        "- [ ] CHK-P-01 conditionally releases M/G/H/D for H/J/N/K-L; A remains reserve.",
        "- [ ] CHK-LAM-01 destructively releases every same-layup structural member family.",
        "- [ ] CHK-SEAM-01 verifies the staggered D-101D/F core, show-face, and back-face seams before mortising.",
        "- [ ] No A-O stock is released to the separate moulding order.",
        "- [ ] The released 3/4-inch-long foam is proven separately on full-size H/J/N and K/L samples.",
        "- [ ] Physical lock, strike, hinges, and screws are present before hardware machining.",
        "",
        "## Shop-owned tool readiness - buy only if missing or worn",
        "",
        "- [ ] DF 500 with sharp 10 mm and 6 mm cutters.",
        "- [ ] Sharp 1/4-inch dado stack for supported through-rail grooves only.",
        "- [ ] Plunge router, sharp 1/4-inch cutter, guide or jig, and positive stops.",
        "- [ ] Moisture meter, calipers, accurate rules, winding sticks, and two diagonal tapes.",
        "- [ ] At least five clamps with more than 24 inches of capacity, plus padded cauls and supports.",
        "",
        "Written dimensions, the Rev. G specification, and LS-05 govern. LS-05 supersedes LS-04. The confirmed jamb dimensions, final hung clearances, and physical hardware govern perimeter acceptance and hardware machining.",
    ]
    SOURCE.parent.mkdir(parents=True, exist_ok=True)
    SOURCE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def header(story, s, page_label, title, deck):
    story.extend(
        [
            p(f"DC-1916-001 | REV. G | LS-05 | DOOR-ONLY PROCUREMENT | {page_label}", s["eyebrow"]),
            p(title, s["title"]),
            p(deck, s["deck"]),
            Table(
                [
                    [
                        p("<b>PROJECT / ROOM</b><br/>____________________________", s["micro"]),
                        p("<b>BUYER</b><br/>________________", s["micro"]),
                        p("<b>DATE</b><br/>____________", s["micro"]),
                        p("<b>SUPPLIER</b><br/>____________________", s["micro"]),
                    ]
                ],
                colWidths=[2.5 * inch, 1.35 * inch, 1.05 * inch, 1.85 * inch],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), PALE_BLUE),
                        ("BOX", (0, 0), (-1, -1), 0.5, RULE),
                        ("INNERGRID", (0, 0), (-1, -1), 0.35, RULE),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ]
                ),
            ),
            Spacer(1, 5),
        ]
    )


def shopping_table(rows, s, widths=None):
    if widths is None:
        widths = [0.32 * inch, 0.80 * inch, 1.45 * inch, 3.57 * inch, 0.60 * inch]
    data = [
        [
            p("OK", s["micro_white"]),
            p("QTY", s["micro_white"]),
            p("BUY", s["micro_white"]),
            p("SPECIFICATION / GATE", s["micro_white"]),
            p("COST", s["micro_white"]),
        ]
    ]
    for qty, item, detail in rows:
        data.append(
            [
                p("[ ]", s["center"]),
                p(qty, s["center"]),
                p(item, s["body_bold"]),
                p(detail, s["body"]),
                p("$____", s["right"]),
            ]
        )
    return Table(
        data,
        colWidths=widths,
        repeatRows=1,
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), BLUE),
                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE_OAK]),
                ("BOX", (0, 0), (-1, -1), 0.6, RULE),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, RULE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, 0), 4),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
                ("TOPPADDING", (0, 1), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
            ]
        ),
    )


def blank_table(rows, s):
    data = [
        [
            p("OK", s["micro_white"]),
            p("PART(S)", s["micro_white"]),
            p("QTY", s["micro_white"]),
            p("CONTROLLED BLANK / BILLET", s["micro_white"]),
            p("RECEIVED / BOARD", s["micro_white"]),
        ]
    ]
    for part, qty, blank in rows:
        data.append(
            [
                p("[ ]", s["center"]),
                p(part, s["body_bold"]),
                p(qty, s["center"]),
                p(blank, s["body"]),
                p("________________", s["micro"]),
            ]
        )
    return Table(
        data,
        colWidths=[0.38 * inch, 2.45 * inch, 0.45 * inch, 1.75 * inch, 1.7 * inch],
        repeatRows=1,
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), TEAL),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE_TEAL]),
                ("BOX", (0, 0), (-1, -1), 0.6, RULE),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, RULE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
            ]
        ),
    )


def checklist_table(items, s, columns=2):
    cells = [
        Table(
            [[p("[ ]", s["center"]), p(item, s["body"])]],
            colWidths=[0.26 * inch, 3.0 * inch],
            style=TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 1),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ]
            ),
        )
        for item in items
    ]
    if columns == 2:
        rows = []
        for index in range(0, len(cells), 2):
            pair = cells[index : index + 2]
            if len(pair) == 1:
                pair.append("")
            rows.append(pair)
        return Table(
            rows,
            colWidths=[3.35 * inch, 3.35 * inch],
            style=TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ]
            ),
        )
    return Table([[cell] for cell in cells], colWidths=[6.7 * inch])


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(OAK)
    canvas.setLineWidth(0.8)
    canvas.line(0.52 * inch, 0.43 * inch, 8.0 * inch, 0.43 * inch)
    canvas.setFillColor(BLUE)
    canvas.setFont("Helvetica", 6.6)
    canvas.drawString(0.52 * inch, 0.25 * inch, "DC-1916-001 | DOOR SHOPPING LIST | REV. G / LS-05")
    canvas.setFillColor(GRAY)
    canvas.drawRightString(8.0 * inch, 0.25 * inch, f"PAGE {doc.page} OF 2")
    canvas.restoreState()


def build_pdf(spec, stock_plan, buy_rows, cut_rows):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (ROOT / "release").mkdir(parents=True, exist_ok=True)
    s = styles()
    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=letter,
        leftMargin=0.52 * inch,
        rightMargin=0.52 * inch,
        topMargin=0.42 * inch,
        bottomMargin=0.52 * inch,
        title="DC-1916-001 Door Shopping List",
        author=spec["project"]["copyright_holder"],
        subject="Rev. G / LS-05 no-resaw door-only procurement and receiving checklist; supersedes LS-04",
    )
    story = []

    header(
        story,
        s,
        "PAGE 1 OF 2",
        "Door Shopping List",
        "Rev. G fitted slab: 23-3/4 x 80-1/2 x 1-3/8 inches from the confirmed 24 x 81 jamb; prefit 23-7/8 x 80-5/8. Equal 4-1/4-inch stiles and 15-1/4-inch rails permit a no-resaw layer plan from A-O.",
    )
    story.append(p("Door lumber status - LS-05 (supersedes LS-04)", s["h2"]))
    story.append(
        shopping_table(
            [
                (
                    "0 BF",
                    "General door lumber - NOT RELEASED",
                    "All STOCK-A through STOCK-O are in hand and reserved for the door. The complete recorded inventory totals about 71.52 BF. G is confirmed S4S at 15/16 x 4-1/2 x 75 inches; its thickness/width/length fit D-101J, while CHK-P-01 still controls clear yield. M carries D-101H; A remains intact; STOCK-N/O remain full-length short-member reserve. This remains conditional inventory, not proven physical yield.",
                ),
                (
                    "As gated",
                    "Specific replacement stock only",
                    "Buy only after a signed RS/ST/SM/FP/P/LAM/SEAM gate identifies the failed layer, member family, face pool, panel source, or seam assembly. Never shorten, narrow, splice, or consume a critical stile layer to solve another shortage.",
                ),
            ],
            s,
        )
    )
    story.append(p("Joinery, panel control, and adhesive", s["h2"]))
    story.append(
        shopping_table(
            [
                (
                    "60 pc",
                    "10 x 50 mm Domino",
                    "Factory beech: 26 final, 26 retained setup/test, and 8 spare. Keep the three groups separated.",
                ),
                (
                    "12 pc",
                    "6 x 40 mm Domino",
                    "Factory beech: 4 final, 4 retained setup/test, and 4 spare for D-101G-to-D-101E/F.",
                ),
                (
                    "40 rec.",
                    "3/4-inch foam spacers",
                    "Oil- and silicone-free open-cell foam. Controlled minimum is 30; order 40 for 20 installed, both family tests, and a practical spare/alternate reserve. PB265-750XF-1M is reference-only.",
                ),
                (
                    "32 oz minimum",
                    "Type II PVA",
                    "Fresh and manufacturer-approved for full-area oak lamination. Planning minimum only: verify actual layup-area coverage, spread rate, open time, pressure, temperature, and cure on same-layup coupons.",
                ),
            ],
            s,
        )
    )
    story.append(p("Hardware, finish, and shop supplies", s["h2"]))
    story.append(
        shopping_table(
            [
                (
                    "1 set",
                    "Brass mortise lock",
                    "Complete privacy set with lock body, strike, knobs/spindle, escutcheons, faceplate, and final screws. Buy same-size steel setup screws for every hole plus spares.",
                ),
                (
                    "3",
                    "3-1/2-inch butt hinges",
                    "Period-compatible brass leaves with matching final screws. Buy same-size steel setup screws for every hole plus spares; confirm load rating.",
                ),
                (
                    "350 mL",
                    "Rubio Oil Plus 2C",
                    "Pure. Approve a complete color, sheen, and adhesion sample; follow the current product data sheet.",
                ),
                (
                    "1 pack",
                    "P80/P100/P120 abrasives",
                    "Discs and hand sheets; use clean abrasives and stop at P120 unless the current finish data sheet differs.",
                ),
                (
                    "As needed",
                    "Plywood jig stock",
                    "Flat 1/2- and 3/4-inch Baltic-birch offcuts for story sticks, stops, supports, and templates; jigs only.",
                ),
                (
                    "1",
                    "Oily-waste container",
                    "Lidded metal can or water-filled sealed metal container suitable for finish waste and local disposal rules.",
                ),
            ],
            s,
        )
    )
    story.extend(
        [
            Spacer(1, 5),
            Table(
                [
                    [
                        p("<b>SUBTOTAL</b><br/>$______________", s["center"]),
                        p("<b>TAX / DELIVERY</b><br/>$______________", s["center"]),
                        p("<b>TOTAL</b><br/>$______________", s["center"]),
                    ]
                ],
                colWidths=[2.25 * inch, 2.25 * inch, 2.25 * inch],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), PALE_OAK),
                        ("BOX", (0, 0), (-1, -1), 0.6, OAK),
                        ("INNERGRID", (0, 0), (-1, -1), 0.35, OAK),
                        ("LEFTPADDING", (0, 0), (-1, -1), 5),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ]
                ),
            ),
            Spacer(1, 4),
            Table(
                [
                    [
                        p(
                            "<b>LS-05 PURCHASE RULE</b>  No general door-lumber purchase is released while every A-O yield and coupon gate passes. A failed gate authorizes only the specifically documented replacement. Moulding uses a separate controlled order; never transfer A-O stock to it before final door release.",
                            s["micro"],
                        )
                    ]
                ],
                colWidths=[6.75 * inch],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), PALE_TEAL),
                        ("BOX", (0, 0), (-1, -1), 0.5, TEAL),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                ),
            ),
            PageBreak(),
        ]
    )

    header(
        story,
        s,
        "PAGE 2 OF 2",
        "Lamination and Release Checklist",
        "LS-05 supersedes LS-04, reserves A-O for the door, and conditionally maps a no-resaw balanced laminated frame. Reported finished, rough-sawn, or unspecified-surface dimensions never prove dressed, staged-planed, coupon, or seam-controlled yield.",
    )
    story.append(p("Balanced frame lamination - controlled billets", s["h2"]))
    story.append(
        blank_table(
            [
                ("D-101A/B - continuous stile cores", "2", "7/8 x 4-3/8 x 81 in"),
                ("D-101A/B - continuous stile faces", "4", "5/16 x 4-3/8 x 81-1/8 in"),
                ("D-101C/M/E/G - core + paired faces", "4", "J/L cores + signed no-resaw face pool"),
                ("D-101D/F - staggered sheet seams", "2", "Per CHK-SM-01 + CHK-SEAM-01"),
            ],
            s,
        )
    )
    story.append(
        Table(
            [
                [
                    p(
                        "<b>PREGLUE</b><br/>5/16 show face + 7/8 core + 5/16 back face = 1-1/2 in",
                        s["body"],
                    ),
                    p(
                        "<b>FINISHED</b><br/>Surface equally to 1/4 + 7/8 + 1/4 = 1-3/8 in",
                        s["body"],
                    ),
                ]
            ],
            colWidths=[3.37 * inch, 3.38 * inch],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, 0), PALE_OAK),
                    ("BACKGROUND", (1, 0), (1, 0), PALE_TEAL),
                    ("BOX", (0, 0), (-1, -1), 0.55, RULE),
                    ("INNERGRID", (0, 0), (-1, -1), 0.35, RULE),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            ),
        )
    )
    story.append(p("Panel yield held inside A-O", s["h2"]))
    story.append(
        blank_table(
            [
                ("D-101H - upper panel", "1", "5/8 x 16-3/8 x 15-9/16 in"),
                ("D-101J - center panel", "1", "5/8 x 16-3/8 x 16-1/16 in"),
                ("D-101N - lower-center panel", "1", "5/8 x 16-3/8 x 10-13/16 in"),
                ("D-101K/L - lower panels", "2", "5/8 x 7-3/8 x 12-5/16 in"),
            ],
            s,
        )
    )
    story.append(p("Receiving and release gates", s["h2"]))
    story.append(
        checklist_table(
            [
                "Moisture is 6-9% at receipt and is rechecked after acclimation.",
                "CHK-RS-01 records minimum thickness, width, bow, cup, twist, checks, and defects; no rough face or edge is a datum.",
                "CHK-ST-01 proves B/C each yield one continuous 5/16-inch stile face with no taper, defect, or end joint.",
                "CHK-ST-02 proves I/K each yield two continuous 4-3/8-inch lanes: one 7/8-inch core and one 5/16-inch face.",
                "CHK-SM-01 maps every J/L core and every staged-planed face, including at least five clear 16-1/4-inch E/F mother billets.",
                "CHK-FP-01 signs every short-member face strip, seam position, coupon, and repair reserve.",
                "CHK-P-01 conditionally releases M/G/H/D for H/J/N/K-L, with A kept intact as reserve, vertical grain, and a matched lower pair.",
                "CHK-LAM-01 destructively proves every same-layup family, 1/4-inch finished faces, core clearance, and wood failure.",
                "CHK-SEAM-01 verifies D/F core/show/back seams and mortise clearance before machining.",
                "Every A-O remnant remains door-only; no material transfers to the separate moulding order.",
                "Factory tenons remain full length; final, setup/test, and spare stock are separated.",
                "Selected 3/4-inch-long foam is released separately on full-size H/J/N and K/L samples.",
                "Physical lock, strike, hinges, and screws are present before hardware machining.",
                "Finish color, sheen, adhesion, and application sample is approved on project offcut.",
            ],
            s,
        )
    )
    story.append(p("Shop-owned tool readiness - buy only if missing or worn", s["h2"]))
    story.append(
        checklist_table(
            [
                "DF 500 with sharp 10 mm and 6 mm cutters.",
                "Dado stack for supported through-rail grooves only.",
                "Plunge router, 1/4-inch cutter, guide/jig, and positive stops for stopped or segmented grooves.",
                "Moisture meter, calipers, accurate rules, winding sticks, and two diagonal tapes.",
                "At least five clamps with more than 24 inches of capacity, plus padded cauls, supports, and non-marring pads.",
                "Labeled test stock for every groove, mortise, spacer, adhesive, and finish setup.",
            ],
            s,
        )
    )
    story.extend(
        [
            Spacer(1, 5),
            Table(
                [
                    [
                        p(
                            "<b>LS-05 DOOR-STOCK DISPOSITION</b><br/>All STOCK-A through STOCK-O is reserved for the door, same-layup coupons, setup pieces, substitutions, and repair stock. STOCK-N/O remain full-length short-core reserve. General door-lumber purchase remains zero only while RS/ST/SM/FP/P/LAM/SEAM gates pass.",
                            s["micro"],
                        ),
                        p(
                            "<b>FIELD HOLD</b><br/>The completed jamb, floor, handing, swing, physical hardware, final perimeter, hinge gains, lock machining, strike, and all room-specific moulding lengths remain field-controlled.",
                            s["micro"],
                        ),
                    ]
                ],
                colWidths=[3.37 * inch, 3.38 * inch],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (0, 0), PALE_OAK),
                        ("BACKGROUND", (1, 0), (1, 0), PALE_BLUE),
                        ("BOX", (0, 0), (-1, -1), 0.55, RULE),
                        ("INNERGRID", (0, 0), (-1, -1), 0.35, RULE),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ]
                ),
            ),
            Spacer(1, 4),
            p(
                "Written dimensions and project/specification.yaml govern. The shopping list does not authorize final slab fitting or hardware machining.",
                s["micro"],
            ),
        ]
    )

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    shutil.copy2(OUTPUT, RELEASE_PDF)
    shutil.copy2(SOURCE, RELEASE_MD)


def validate_output():
    reader = PdfReader(str(OUTPUT))
    assert len(reader.pages) == 2, f"expected 2 pages, got {len(reader.pages)}"
    text = " ".join(
        "\n".join(page.extract_text() or "" for page in reader.pages).split()
    )
    required = [
        "24 x 81",
        "23-7/8 x 80-5/8",
        "23-3/4 x 80-1/2 x 1-3/8",
        "3/8",
        "REV. G",
        "LS-05",
        "supersedes LS-04",
        "0 BF",
        "rough-sawn",
        "General door lumber",
        "No general door-lumber purchase is released",
        "STOCK-A through STOCK-O",
        "71.52",
        "G is confirmed S4S at 15/16 x 4-1/2 x 75",
        "conditional inventory",
        "specific replacement stock",
        "signed RS/ST/SM/FP/P/LAM/SEAM",
        "32 oz minimum",
        "actual layup-area coverage",
        "5/16 show face + 7/8 core + 5/16 back face",
        "1/4 + 7/8 + 1/4",
        "CHK-ST-01",
        "CHK-ST-02",
        "CHK-SM-01",
        "CHK-FP-01",
        "CHK-P-01",
        "CHK-LAM-01",
        "CHK-SEAM-01",
        "separate moulding order",
        "60 pc",
        "controlled minimum is 30",
        "order 40",
        "3/4-inch-long foam",
        "Dado stack",
        "Plunge router",
        "FIELD HOLD",
    ]
    for term in required:
        assert term.lower() in text.lower(), f"shopping list missing required term: {term}"
    assert "Moulding stock" not in text
    for forbidden in [
        "26 BF",
        "8 BF",
        "16 oz",
        "LS-02",
        "Complete frame - REQUIRED NOW",
        "one-piece D-101F",
    ]:
        assert forbidden.lower() not in text.lower(), (
            f"shopping list retains obsolete purchase language: {forbidden}"
        )
    assert not any(term in text for term in ("TODO", "TBD", "Lorem ipsum"))


def main():
    spec, stock_plan, buy_rows, cut_rows = load_inputs()
    validate_inputs(spec, stock_plan, buy_rows, cut_rows)
    frame_ids = {
        "D-101A",
        "D-101B",
        "D-101C",
        "D-101M",
        "D-101D",
        "D-101E",
        "D-101F",
        "D-101G",
    }
    panel_ids = {"D-101H", "D-101J", "D-101N", "D-101K", "D-101L"}
    assert rough_board_feet(cut_rows, frame_ids) > 13.0
    assert rough_board_feet(cut_rows, panel_ids) > 3.5
    raw_inventory_bf = sum(
        row["thickness"] * row["width"] * row["length"] / 144
        for row in stock_plan["inventory"]
        if row["thickness"] is not None
    )
    assert math.isclose(raw_inventory_bf, 71.5234375, abs_tol=0.001)
    write_markdown(spec, stock_plan, buy_rows, cut_rows)
    build_pdf(spec, stock_plan, buy_rows, cut_rows)
    validate_output()
    print(f"PASS: built Rev. G / LS-05 {OUTPUT.name} (2 pages) and release copy")


if __name__ == "__main__":
    main()
