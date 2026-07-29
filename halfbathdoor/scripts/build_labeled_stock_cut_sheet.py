#!/usr/bin/env python3
"""Build the Rev. G / LS-05 no-resaw door-only labeled-stock cut sheet."""

from __future__ import annotations

import csv
import json
import math
import shutil
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

from pypdf import PdfReader
from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = ROOT / "project" / "labeled-stock-plan.json"
SPEC_PATH = ROOT / "project" / "specification.yaml"
OUTPUT_PDF_DIR = ROOT / "output" / "pdf"
OUTPUT_CSV_DIR = ROOT / "output" / "csv"
SOURCE_DIR = ROOT / "stock-plan"
NAME = "DC-1916-001_Labeled_Stock_Cut_Sheet"
TOTAL_PAGES = 5
OUTPUT_PDF = OUTPUT_PDF_DIR / f"{NAME}.pdf"
OUTPUT_CSV = OUTPUT_CSV_DIR / f"{NAME}.csv"
SOURCE_MD = SOURCE_DIR / f"{NAME}.md"
RELEASE = ROOT / "release"

BLUE = colors.HexColor("#173A56")
TEAL = colors.HexColor("#2E6F73")
OAK = colors.HexColor("#9A6B2F")
OAK_LIGHT = colors.HexColor("#D7B47B")
PALE_BLUE = colors.HexColor("#EAF1F5")
PALE_OAK = colors.HexColor("#F4F0E8")
PALE_RED = colors.HexColor("#F7E9E7")
PALE_GREEN = colors.HexColor("#EAF2EC")
INK = colors.HexColor("#20272D")
GRAY = colors.HexColor("#65717A")
RULE = colors.HexColor("#B9C2C7")
RED = colors.HexColor("#A33B32")
GREEN = colors.HexColor("#3D7452")
WHITE = colors.white


def fraction(value: float, denominator: int = 32) -> str:
    item = Fraction(value).limit_denominator(denominator)
    whole, remainder = divmod(item.numerator, item.denominator)
    if remainder == 0:
        return str(whole)
    return f"{whole}-{remainder}/{item.denominator}" if whole else f"{remainder}/{item.denominator}"


def decimal(value: float) -> str:
    return f"{value:.4f}".rstrip("0").rstrip(".")


def load():
    return (
        json.loads(PLAN_PATH.read_text(encoding="utf-8")),
        json.loads(SPEC_PATH.read_text(encoding="utf-8")),
    )


def operation_length(op, kerf):
    return op["segment_count"] * op["segment_length"] + op["crosscuts"] * kerf


def validate_plan(plan, spec):
    document = plan["document"]
    assumptions = plan["assumptions"]
    assert document["revision"] == spec["project"]["revision"] == "Rev. G"
    assert document["stock_plan"] == "LS-05"
    assert document["supersedes"] == "LS-04"
    assert math.isclose(spec["opening"]["clear_width"], 24.0)
    assert math.isclose(spec["opening"]["clear_height"], 81.0)
    assert math.isclose(spec["opening"]["hinge_side_reveal"], 0.125)
    assert math.isclose(spec["opening"]["lock_side_reveal"], 0.125)
    assert math.isclose(spec["opening"]["head_reveal"], 0.125)
    assert math.isclose(spec["opening"]["bottom_gap"], 0.375)
    assert math.isclose(spec["slab"]["finished_width"], 23.75)
    assert math.isclose(spec["slab"]["finished_height"], 80.5)
    assert math.isclose(spec["milling"]["prefit_assembly_width"], 23.875)
    assert math.isclose(spec["milling"]["prefit_assembly_height"], 80.625)
    assert math.isclose(spec["frame"]["stile_width"], 4.25)
    assert math.isclose(spec["frame"]["rail_shoulder_length"], 15.25)
    assert math.isclose(spec["frame"]["bottom_opening_each"], 6.125)
    assert assumptions["reported_dimensions_are_raw"] is False
    assert assumptions["scope_rule"].startswith("STOCK-A through STOCK-O are reserved exclusively for the door")
    assert "CHK-ST-01" in assumptions["zero_spare_release_rule"]
    assert "CHK-ST-02" in assumptions["zero_spare_release_rule"]
    assert "controlled rough size" in assumptions["staged_milling_rule"]
    assert math.isclose(assumptions["frame_core_preglue_thickness"], 0.875)
    assert math.isclose(assumptions["frame_face_preglue_thickness"], 0.3125)
    assert math.isclose(assumptions["frame_glue_blank_thickness"], 1.5)
    assert math.isclose(assumptions["frame_face_finished_thickness"], 0.25)
    assert math.isclose(assumptions["frame_finished_thickness"], 1.375)
    assert math.isclose(
        assumptions["frame_core_preglue_thickness"]
        + 2 * assumptions["frame_face_preglue_thickness"],
        assumptions["frame_glue_blank_thickness"],
    )
    assert math.isclose(
        assumptions["frame_core_preglue_thickness"]
        + 2 * assumptions["frame_face_finished_thickness"],
        assumptions["frame_finished_thickness"],
    )
    assert [row["label"] for row in plan["inventory"]] == list("ABCDEFGHIJKLMNO")
    assert not plan["purchase_requirements"]
    assert plan["purchase_summary"]["planning_quantity_bf"] == 0
    assert {(row["id"], row["quantity"]) for row in plan["moulding_purchase_requirements"]} == {
        ("BUY-MOULD-4Q", "7 boards"),
        ("BUY-MOULD-6Q", "2 boards"),
    }
    assert {row["part"] for row in plan["component_allocations"]} == {
        row["id"] for row in spec["components"]
    }

    inventory = {row["label"]: row for row in plan["inventory"]}
    layers = {row["part"]: row for row in plan["laminated_member_schedule"]}
    checks = {row["id"]: row for row in plan["critical_checks"]}
    assert math.isclose(inventory["A"]["length"], 72.75)
    assert "6-inch damaged section" in inventory["A"]["condition"]
    assert "72-3/4" in assumptions["stock_a_length_update"]
    assert math.isclose(inventory["L"]["width"], 6.0)
    assert "after edge cleanup" in inventory["L"]["condition"]
    assert math.isclose(inventory["G"]["thickness"], 0.9375)
    assert math.isclose(inventory["G"]["width"], 4.5)
    assert math.isclose(inventory["G"]["length"], 75.0)
    assert "S4S" in inventory["G"]["condition"]
    assert "15/16-inch thickness" in inventory["G"]["condition"]
    assert math.isclose(inventory["M"]["thickness"], 0.75)
    assert math.isclose(inventory["M"]["width"], 8.25)
    assert math.isclose(inventory["M"]["length"], 99.0)
    assert "finished white oak" in inventory["M"]["condition"]
    for label in ("N", "O"):
        assert math.isclose(inventory[label]["thickness"], 1.75)
        assert math.isclose(inventory[label]["width"], 11.0)
        assert math.isclose(inventory[label]["length"], 74.0)
        assert "Finished white oak" in inventory[label]["condition"]
    allocations = {row["part"]: row for row in plan["component_allocations"]}
    assert allocations["D-101H"]["stock"] == "M"
    assert layers["D-101D"]["core_stock"] == "L-DW-CORE + L-DN-CORE"
    assert layers["D-101F"]["core_stock"] == "L-F1-CORE + J-F2-CORE"
    assert "6-1/2-inch jointed width" in checks["CHK-SM-01"]["pass"]
    kerf = assumptions["saw_kerf"]
    consumed = defaultdict(float)
    reserved = defaultdict(float)
    for op in plan["operations"]:
        assert op["stock"] in inventory
        consumed[op["stock"]] += operation_length(op, kerf)
        reserved[op["stock"]] += op.get(
            "end_reserve", assumptions["default_end_trim_reserve"]
        )
    for label, used in consumed.items():
        remainder = inventory[label]["length"] - used - reserved[label]
        assert remainder >= -1e-8, f"STOCK-{label} overallocated by {-remainder:g} in"

    schedule = {row["part"]: row for row in plan["laminated_member_schedule"]}
    assert schedule.keys() == {
        "D-101A", "D-101B", "D-101C", "D-101M",
        "D-101D", "D-101E", "D-101F", "D-101G",
    }
    assert "2-1/4" in schedule["D-101D"]["seams"]
    assert "5-3/4" in schedule["D-101F"]["seams"]
    return consumed, reserved


def write_csv(plan):
    OUTPUT_CSV_DIR.mkdir(parents=True, exist_ok=True)
    kerf = plan["assumptions"]["saw_kerf"]
    headers = [
        "Stock label", "Sequence", "Operation ID", "Target part(s)",
        "Segment count", "Segment length", "Crosscuts", "Saw kerf",
        "Operation length", "End reserve", "Total planned length",
        "Rip / milling plan", "Required yield", "Status", "Notes",
    ]
    rows = []
    for op in plan["operations"]:
        cut_length = operation_length(op, kerf)
        end_reserve = op.get("end_reserve", plan["assumptions"]["default_end_trim_reserve"])
        rows.append([
            f"STOCK-{op['stock']}", op["sequence"], op["operation_id"], op["target"],
            op["segment_count"], decimal(op["segment_length"]), op["crosscuts"],
            decimal(kerf), decimal(cut_length), decimal(end_reserve),
            decimal(cut_length + end_reserve), op["rip_plan"], op["yield"],
            op["status"], op["notes"],
        ])
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)


def write_markdown(plan, consumed, reserved):
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    inv = {row["label"]: row for row in plan["inventory"]}
    a = plan["assumptions"]
    lines = [
        "# DC-1916-001 Labeled Stock Cut Sheet",
        "",
        f"**Revision:** {plan['document']['revision']}  ",
        f"**Stock plan:** {plan['document']['stock_plan']}  ",
        f"**Supersedes:** {plan['document']['supersedes']}  ",
        f"**Date:** {plan['document']['date']}  ",
        f"**Status:** {plan['document']['status']}",
        "",
        "STOCK-A through STOCK-O are reserved exclusively for the 23-3/4 x 80-1/2 x 1-3/8-inch fitted five-panel slab for the confirmed 24 x 81-inch jamb. The prefit assembly is 23-7/8 x 80-5/8 inches; final reveals are 1/8 inch at both sides and head with a 3/8-inch bottom gap. A-O are not moulding stock. This Rev. G design uses no resawing. STOCK-M is reported finished white oak at 3/4 x 8-1/4 x 99 inches and carries D-101H; STOCK-A remains intact at 72-3/4 inches as reserve. STOCK-N/O are confirmed finished white oak at 1-3/4 x 11 x 74 inches each and remain uncut short-member reserve.",
        "",
        "## Reserve-controlled release order",
        "",
        f"1. {a['zero_spare_release_rule']}",
        f"2. {a['staged_milling_rule']}",
        f"3. {a['machine_minimum_rule']}",
        "",
        "## Balanced laminated-frame section",
        "",
        f"- Preglue: {fraction(a['frame_face_preglue_thickness'])} face + {fraction(a['frame_core_preglue_thickness'])} core + {fraction(a['frame_face_preglue_thickness'])} face = {fraction(a['frame_glue_blank_thickness'])}.",
        f"- Finished: {fraction(a['frame_face_finished_thickness'])} face + {fraction(a['frame_core_preglue_thickness'])} core + {fraction(a['frame_face_finished_thickness'])} face = {fraction(a['frame_finished_thickness'])}.",
        f"- Remove {fraction(a['symmetric_face_removal_each'])} equally from each outer face after cure and rest. Machine grooves, Domino mortises, hinges, and lock work only afterward.",
        "- Make every 5/16-inch face by staged thickness planing of a whole lane or mother billet. Ordinary rips divide board width; no board is divided through its thickness.",
        "- All layers run with the member. No cross-grain layer, end splice, butt joint, or hidden short block is permitted.",
        "",
        "## Inventory disposition",
        "",
        "| Stock | Raw T x W x L | Planned door use | Disposition |",
        "|---|---|---|---|",
    ]
    for row in plan["inventory"]:
        lines.append(
            f"| STOCK-{row['label']} | {row['original_entry']} | {row['planned_use']} | {row['disposition']} |"
        )
    lines += [
        "",
        "## Kerf-aware operations",
        "",
        f"Saw kerf is {fraction(a['saw_kerf'])} inch. End reserves are operation-specific; the actual clear squared-end loss controls.",
        "",
        "| Stock / op | Target | Segment plan | End reserve | Required yield | Status |",
        "|---|---|---|---:|---|---|",
    ]
    for op in plan["operations"]:
        lines.append(
            f"| STOCK-{op['stock']} / {op['operation_id']} | {op['target']} | "
            f"{op['segment_count']} x {fraction(op['segment_length'])}; {op['crosscuts']} kerf(s) | "
            f"{fraction(op.get('end_reserve', a['default_end_trim_reserve']))} | "
            f"{op['yield']} | {op['status']} |"
        )
    lines += [
        "",
        "## Board-length reconciliation",
        "",
        "| Stock | Available | Cuts + kerfs | End reserve | Paper remainder |",
        "|---|---:|---:|---:|---:|",
    ]
    for label in sorted(consumed):
        remainder = inv[label]["length"] - consumed[label] - reserved[label]
        lines.append(
            f"| STOCK-{label} | {fraction(inv[label]['length'])} | "
            f"{fraction(consumed[label])} | {fraction(reserved[label])} | {fraction(remainder)} |"
        )
    lines += [
        "",
        "## Laminated member schedule",
        "",
        "| Part | Core | Show face | Back face | Blanks | Seam control |",
        "|---|---|---|---|---|---|",
    ]
    for row in plan["laminated_member_schedule"]:
        lines.append(
            f"| {row['part']} {row['name']} | {row['core_stock']} | "
            f"{row['show_face_stock']} | {row['back_face_stock']} | "
            f"{row['core_blank']}; {row['face_blanks']} | {row['seams']} |"
        )
    lines += [
        "",
        "## Finished-part reconciliation",
        "",
        "| Part | Name | Door stock | Allocation | Status |",
        "|---|---|---|---|---|",
    ]
    for row in plan["component_allocations"]:
        lines.append(
            f"| {row['part']} | {row['name']} | {row['stock']} | {row['allocation']} | {row['status']} |"
        )
    lines += [
        "",
        "## Door lumber purchase",
        "",
        f"**{plan['purchase_summary']['status']}.** {plan['purchase_summary']['basis']} {plan['purchase_summary']['conditional_credit']}",
        "",
        "## Separate two-face moulding order",
        "",
        "| ID | Quantity | Material | Actual minimum | Allocation |",
        "|---|---:|---|---|---|",
    ]
    for row in plan["moulding_purchase_requirements"]:
        lines.append(
            f"| {row['id']} | {row['quantity']} | {row['material']} | {row['actual_minimum']} | {row['allocation']} |"
        )
    lines += ["", "## Critical release checks", ""]
    for row in plan["critical_checks"]:
        lines += [
            f"### {row['id']} - {row['severity']}",
            "",
            f"- Check: {row['check']}",
            f"- Pass: {row['pass']}",
            f"- Fallback: {row['fallback']}",
            "",
        ]
    lines += [
        "## Fallback rules",
        "",
        *[f"- **{key.replace('_', ' ').title()}:** {value}" for key, value in plan["fallback"].items()],
        "",
        "Do not rough-length B, C, I, or K before the full-length stile gates pass. Keep N/O full unless a signed short-core fallback is released. Do not transfer A-O remnants to moulding before the completed door, coupons, and repair reserve are released.",
        "",
    ]
    SOURCE_MD.write_text("\n".join(lines), encoding="utf-8")


def styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("Title2", parent=base["Title"], fontName="Helvetica-Bold", fontSize=22, leading=24, textColor=BLUE, alignment=TA_LEFT, spaceAfter=3),
        "eyebrow": ParagraphStyle("Eye", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=7.2, leading=8.5, textColor=TEAL, spaceAfter=2),
        "deck": ParagraphStyle("Deck", parent=base["Normal"], fontName="Helvetica", fontSize=8.2, leading=10.2, textColor=GRAY, spaceAfter=5),
        "h2": ParagraphStyle("H2x", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=11.2, leading=12.5, textColor=BLUE, spaceBefore=4, spaceAfter=3),
        "body": ParagraphStyle("Bodyx", parent=base["BodyText"], fontName="Helvetica", fontSize=6.8, leading=8.2, textColor=INK),
        "bold": ParagraphStyle("Boldx", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=6.8, leading=8.2, textColor=INK),
        "micro": ParagraphStyle("Microx", parent=base["BodyText"], fontName="Helvetica", fontSize=6.1, leading=7.2, textColor=GRAY),
        "ops": ParagraphStyle("Opsx", parent=base["BodyText"], fontName="Helvetica", fontSize=5.35, leading=6.05, textColor=INK),
        "white": ParagraphStyle("Whitex", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=6.2, leading=7.2, textColor=WHITE),
        "center": ParagraphStyle("Centerx", parent=base["BodyText"], fontName="Helvetica", fontSize=6.7, leading=8, textColor=INK, alignment=TA_CENTER),
    }


def p(text, style):
    return Paragraph(str(text), style)


def header(story, s, plan, page, title, deck, status=None):
    story += [
        p(f"DC-1916-001 | {plan['document']['revision'].upper()} | STOCK PLAN {plan['document']['stock_plan']} | PAGE {page} OF {TOTAL_PAGES}", s["eyebrow"]),
        p(title, s["title"]),
        p(deck, s["deck"]),
    ]
    if status:
        story += [
            Table([[p(f"<b>STATUS:</b> {status}", s["body"])]], colWidths=[9.82 * inch],
                  style=TableStyle([
                      ("BACKGROUND", (0, 0), (-1, -1), PALE_RED),
                      ("BOX", (0, 0), (-1, -1), .65, RED),
                      ("LEFTPADDING", (0, 0), (-1, -1), 7),
                      ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                      ("TOPPADDING", (0, 0), (-1, -1), 4),
                      ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                  ])),
            Spacer(1, 4),
        ]


def base_table(data, widths, s, header_color=BLUE, font_size=6.4):
    return Table(data, colWidths=widths, repeatRows=1, style=TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), header_color),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PALE_OAK]),
        ("BOX", (0, 0), (-1, -1), .5, RULE),
        ("INNERGRID", (0, 0), (-1, -1), .25, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2.6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.6),
        ("FONTSIZE", (0, 1), (-1, -1), font_size),
    ]))


def laminate_section(a, width=700, height=92):
    drawing = Drawing(width, height)
    x, y, w, h = 75, 27, 550, 35
    layers = [
        ("SHOW FACE 5/16 -> 1/4", a["frame_face_preglue_thickness"], OAK_LIGHT),
        ("CORE 7/8", a["frame_core_preglue_thickness"], colors.HexColor("#C49558")),
        ("BACK FACE 5/16 -> 1/4", a["frame_face_preglue_thickness"], OAK_LIGHT),
    ]
    cursor = x
    total = a["frame_glue_blank_thickness"]
    for label, thickness, fill in layers:
        lw = w * thickness / total
        drawing.add(Rect(cursor, y, lw, h, fillColor=fill, strokeColor=INK, strokeWidth=.7))
        drawing.add(String(cursor + lw / 2, y + 14, label, fontName="Helvetica-Bold", fontSize=7, textAnchor="middle", fillColor=INK))
        cursor += lw
    drawing.add(Line(x, y - 6, x + w, y - 6, strokeColor=BLUE, strokeWidth=.7))
    drawing.add(String(width / 2, 6, "Preglue 1-1/2 in; cure/rest; remove 1/16 equally from both outer faces; finished 1-3/8 in", fontName="Helvetica-Bold", fontSize=7.2, textAnchor="middle", fillColor=BLUE))
    drawing.add(String(6, height - 10, "BALANCED LONG-GRAIN FRAME SECTION", fontName="Helvetica-Bold", fontSize=8.2, fillColor=TEAL))
    return drawing


def footer(canvas, doc):
    canvas.saveState()
    page_w, _ = landscape(letter)
    canvas.setStrokeColor(OAK)
    canvas.line(.48 * inch, .40 * inch, page_w - .48 * inch, .40 * inch)
    canvas.setFillColor(BLUE)
    canvas.setFont("Helvetica", 6.4)
    canvas.drawString(.48 * inch, .23 * inch, "DC-1916-001 | LABELED STOCK CUT SHEET | REV. G | LS-05")
    canvas.setFillColor(GRAY)
    canvas.drawRightString(page_w - .48 * inch, .23 * inch, f"PAGE {doc.page} OF {TOTAL_PAGES}")
    canvas.restoreState()


def build_pdf(plan, spec, consumed, reserved):
    OUTPUT_PDF_DIR.mkdir(parents=True, exist_ok=True)
    RELEASE.mkdir(parents=True, exist_ok=True)
    s = styles()
    inv = {row["label"]: row for row in plan["inventory"]}
    a = plan["assumptions"]
    doc = SimpleDocTemplate(
        str(OUTPUT_PDF), pagesize=landscape(letter),
        leftMargin=.48 * inch, rightMargin=.48 * inch,
        topMargin=.36 * inch, bottomMargin=.48 * inch,
        title="DC-1916-001 Labeled Stock Cut Sheet",
        author=spec["project"]["copyright_holder"],
        subject="Rev. G / LS-05 no-resaw door-only rough-stock and balanced laminated-frame allocation; supersedes LS-04",
    )
    story = []

    # Page 1
    header(story, s, plan, 1, "Door-Only Labeled Lumber Inventory",
           "LS-05 supersedes LS-04. M = 3/4 x 8-1/4 x 99 inches finished white oak and carries D-101H; keep damaged A intact at 72-3/4 inches. N/O are each confirmed finished white oak at 1-3/4 x 11 x 74 inches and remain full-length short-member reserve. No-resaw slab 23-3/4 x 80-1/2 x 1-3/8; prefit 23-7/8 x 80-5/8 in the 24 x 81 jamb with 3/8 bottom gap.",
           plan["document"]["status"])
    data = [[p(x, s["white"]) for x in ["STOCK", "CURRENT / HISTORICAL T x W x L", "CONDITION", "DOOR-ONLY USE", "DISPOSITION"]]]
    for row in plan["inventory"]:
        data.append([
            p(row["label"], s["center"]), p(row["original_entry"], s["micro"]),
            p(row["condition"], s["micro"]), p(row["planned_use"], s["micro"]),
            p(row["disposition"], s["micro"]),
        ])
    story.append(base_table(data, [.5*inch, 1.35*inch, 1.55*inch, 4.6*inch, 1.82*inch], s, font_size=5.8))
    story.append(PageBreak())

    # Page 2
    header(story, s, plan, 2, "Balanced Laminated Frame Schedule",
           "The engineered layup keeps the centered groove and DF500 machining inside a continuous 7/8-inch core. Every 5/16-inch face is staged-planed from a whole lane or mother billet; there are no through-thickness saw cuts.",
           "NO DOOR LUMBER PURCHASE RELEASED; EVERY LAMINATED MEMBER REMAINS ON PHYSICAL-YIELD AND COUPON HOLD.")
    story.append(laminate_section(a))
    layer_notes = [
        [
            p("<b>PREGLUE</b><br/>5/16 face + 7/8 core + 5/16 face = 1-1/2 in.", s["body"]),
            p("<b>FINISHED</b><br/>1/4 face + 7/8 core + 1/4 face = 1-3/8 in.", s["body"]),
            p("<b>MACHINING</b><br/>Laminate, cure, rest, surface symmetrically, then cut grooves, Domino mortises, hinge gains, and lock work.", s["body"]),
        ]
    ]
    story.append(Table(layer_notes, colWidths=[3.27*inch]*3, style=TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), PALE_BLUE), ("BOX",(0,0),(-1,-1),.5,RULE),
        ("INNERGRID",(0,0),(-1,-1),.3,RULE), ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("LEFTPADDING",(0,0),(-1,-1),6), ("RIGHTPADDING",(0,0),(-1,-1),6),
        ("TOPPADDING",(0,0),(-1,-1),5), ("BOTTOMPADDING",(0,0),(-1,-1),5),
    ])))
    story.append(Spacer(1, 4))
    schedule = [[p(x, s["white"]) for x in ["PART", "CORE STOCK / BLANK", "FACE STOCK / BLANKS", "SEAM CONTROL"]]]
    for row in plan["laminated_member_schedule"]:
        schedule.append([
            p(f"<b>{row['part']}</b><br/>{row['name']}", s["body"]),
            p(f"{row['core_stock']}<br/>{row['core_blank']}", s["body"]),
            p(f"SF: {row['show_face_stock']}<br/>BF: {row['back_face_stock']}<br/>{row['face_blanks']}", s["body"]),
            p(row["seams"], s["body"]),
        ])
    story.append(base_table(schedule, [1.15*inch, 2.45*inch, 3.55*inch, 2.67*inch], s, OAK))
    story.append(PageBreak())

    # Page 3
    header(story, s, plan, 3, "Kerf-Aware Door Operations",
           "Preserve B, C, I, K, J, and L at full length. J must prove a 6-1/2-inch width envelope for the wide F core stave; 6-inch L carries both D core staves, E, and the 5-3/4-inch F stave.",
           "PAPER NESTING IS NOT A CUTTING RELEASE. MEASURE DRESSED YIELD BEFORE PROCESSING THE NEXT BOARD.")
    ops = [[p(x, s["white"]) for x in ["STOCK / OP", "TARGET", "SEGMENTS", "END", "RIP / MILLING PLAN", "REQUIRED YIELD", "STATUS"]]]
    for op in plan["operations"]:
        ops.append([
            p(f"<b>{op['stock']}</b><br/>{op['operation_id']}", s["ops"]),
            p(op["target"], s["ops"]),
            p(f"{op['segment_count']} x {fraction(op['segment_length'])}<br/>{op['crosscuts']} kerf(s)", s["center"]),
            p(fraction(op.get("end_reserve", a["default_end_trim_reserve"])), s["center"]),
            p(op["rip_plan"], s["ops"]),
            p(op["yield"], s["ops"]),
            p(op["status"], s["ops"]),
        ])
    story.append(base_table(ops, [.58*inch, 1.48*inch, .72*inch, .42*inch, 2.65*inch, 2.55*inch, 1.42*inch], s, TEAL, 5.8))
    story.append(PageBreak())

    # Page 4
    header(story, s, plan, 4, "Release Gates and Separate Moulding Order",
           "Run the gates in order: RS-01 on all boards, ST-01 on B/C, ST-02 on I/K, then P-01 panel cuts, short-member maps, coupons, and seam verification.",
           "CONTROLLED RESERVE: AT ANY FAILED GATE, STOP AND REMAP BEFORE PROCESSING ANOTHER BOARD. NEVER SPLICE A STILE.")
    checks = [[p(x, s["white"]) for x in ["GATE", "CHECK", "PASS CONDITION", "FALLBACK", "SIGNOFF"]]]
    for row in plan["critical_checks"]:
        checks.append([
            p(f"<b>{row['id']}</b><br/>{row['severity']}", s["body"]),
            p(row["check"], s["micro"]), p(row["pass"], s["micro"]),
            p(row["fallback"], s["micro"]), p("[ ] PASS<br/>[ ] HOLD<br/>____ / ____", s["center"]),
        ])
    story.append(base_table(checks, [.8*inch, 2.42*inch, 2.72*inch, 2.55*inch, 1.33*inch], s, RED, 5.8))
    story.append(PageBreak())

    # Page 5
    header(story, s, plan, 5, "Door Lumber Disposition and Separate Moulding Order",
           "The kerf-aware paper reconciliation is repeated here and remains editable in the companion workbook. A nonnegative remainder never overrides the signed physical-yield gates.",
           "NO GENERAL DOOR-LUMBER PURCHASE IS RELEASED. MOULDING IS A SEPARATE S4S ORDER.")
    story.append(p("Board-length reconciliation", s["h2"]))
    reconciliation = [[
        p(x, s["white"])
        for x in ["STOCK", "AVAILABLE", "CUTS + KERFS", "END RESERVE", "PAPER REMAINDER", "DISPOSITION"]
    ]]
    for label in sorted(consumed):
        remainder = inv[label]["length"] - consumed[label] - reserved[label]
        reconciliation.append([
            p(f"STOCK-{label}", s["bold"]),
            p(fraction(inv[label]["length"]), s["center"]),
            p(fraction(consumed[label]), s["center"]),
            p(fraction(reserved[label]), s["center"]),
            p(fraction(remainder), s["center"]),
            p("PAPER FIT ONLY - PHYSICAL GATE CONTROLS", s["micro"]),
        ])
    story.append(base_table(
        reconciliation,
        [1.05*inch, 1.12*inch, 1.35*inch, 1.25*inch, 1.40*inch, 3.65*inch],
        s,
        TEAL,
        5.9,
    ))
    story.append(p("Door lumber purchase", s["h2"]))
    story.append(Table([[p(
        f"<b>{plan['purchase_summary']['status']}</b><br/>{plan['purchase_summary']['basis']} "
        f"{plan['purchase_summary']['conditional_credit']}", s["body"]
    )]], colWidths=[9.82*inch], style=TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),PALE_GREEN), ("BOX",(0,0),(-1,-1),.55,GREEN),
        ("LEFTPADDING",(0,0),(-1,-1),7), ("RIGHTPADDING",(0,0),(-1,-1),7),
        ("TOPPADDING",(0,0),(-1,-1),5), ("BOTTOMPADDING",(0,0),(-1,-1),5),
    ])))
    story.append(p("Separate two-face moulding purchase", s["h2"]))
    moulding = [[p(x, s["white"]) for x in ["ID", "QTY", "MATERIAL", "ACTUAL MINIMUM / PURPOSE"]]]
    for row in plan["moulding_purchase_requirements"]:
        moulding.append([
            p(row["id"], s["bold"]), p(row["quantity"], s["center"]),
            p(row["material"], s["body"]),
            p(f"{row['actual_minimum']}<br/>{row['allocation']}", s["body"]),
        ])
    story.append(base_table(moulding, [1.25*inch, .75*inch, 2.85*inch, 4.97*inch], s, OAK))
    story.append(Spacer(1, 4))
    story.append(Table([[
        p("<b>RELEASED BY</b><br/>________________________", s["micro"]),
        p("<b>DATE</b><br/>____________", s["micro"]),
        p("<b>KERF</b><br/>________ in", s["micro"]),
        p("<b>MOISTURE</b><br/>________ %", s["micro"]),
        p("<b>LAYERS WITHIN 1%</b><br/>[ ] YES", s["micro"]),
    ]], colWidths=[2.6*inch, 1.5*inch, 1.55*inch, 1.75*inch, 2.42*inch], style=TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),PALE_BLUE), ("BOX",(0,0),(-1,-1),.5,RULE),
        ("INNERGRID",(0,0),(-1,-1),.3,RULE), ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("LEFTPADDING",(0,0),(-1,-1),6), ("TOPPADDING",(0,0),(-1,-1),5),
        ("BOTTOMPADDING",(0,0),(-1,-1),5),
    ])))

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    shutil.copy2(OUTPUT_PDF, RELEASE / OUTPUT_PDF.name)
    shutil.copy2(OUTPUT_CSV, RELEASE / OUTPUT_CSV.name)
    shutil.copy2(SOURCE_MD, RELEASE / SOURCE_MD.name)


def validate_outputs():
    reader = PdfReader(str(OUTPUT_PDF))
    assert len(reader.pages) == TOTAL_PAGES, (
        f"expected {TOTAL_PAGES} pages, got {len(reader.pages)}"
    )
    text = "\n".join(page.extract_text() or "" for page in reader.pages).lower()
    for required in [
        "rev. g", "ls-05", "supersedes ls-04", "door-only",
        "24 x 81", "23-7/8 x 80-5/8", "23-3/4 x 80-1/2",
        "72-3/4", "6-inch damage", "3/4 x 8-1/4 x 99", "stock-m", "17-3/16",
        "1 3/4 x 11 x 74", "stock-n", "stock-o", "short-member reserve",
        "3/8 bottom gap", "5/16 face", "7/8 core",
        "no door lumber purchase released", "buy-mould-4q", "7 boards",
        "buy-mould-6q", "2 boards", "chk-st-01", "chk-fp-01", "chk-lam-01",
        "stock-k", "7/8 x 4-3/8 x 81",
        "controlled reserve", "b/c/i/k",
        "s4s", "15/16", "4-1/2 x 75", "chk-p-01",
        "measure dressed yield before processing the next board",
    ]:
        assert required in text, f"PDF missing required term: {required}"
    for stale in ["buy-frame-01", "26 bf planning package", "zero on-hand frame credit"]:
        assert stale not in text, f"PDF contains obsolete stock-plan term: {stale}"


def main():
    plan, spec = load()
    consumed, reserved = validate_plan(plan, spec)
    write_csv(plan)
    write_markdown(plan, consumed, reserved)
    build_pdf(plan, spec, consumed, reserved)
    validate_outputs()
    print(
        f"PASS: built {OUTPUT_PDF.name} ({TOTAL_PAGES} pages), "
        "Markdown, and CSV for Rev. G / LS-05"
    )


if __name__ == "__main__":
    main()
