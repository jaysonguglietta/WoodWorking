#!/usr/bin/env python3
"""Build the integrated cabinetmaker's door-and-millwork guide."""
from __future__ import annotations

import csv
import json
import re
import shutil
from fractions import Fraction
from pathlib import Path

from PIL import Image as PILImage
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    Image as RLImage,
    KeepInFrame,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from build_quick_guide import (
    BLUE,
    GRAY,
    INK,
    OAK,
    OAK_DARK,
    PALE,
    PALE_BLUE,
    PALE_TEAL,
    RULE,
    TEAL,
    inline,
    note_cards,
    page_heading,
    styles,
    svg_figure,
)
from generate_cabinetmakers_3d import generate as generate_3d
from generate_visual_clarity_maps import generate as generate_clarity_maps

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "cabinetmakers-guide" / "DC-1916-001_Cabinetmakers_Builder_Guide.md"
RELEASE = ROOT / "release"
OUT = RELEASE / "DC-1916-001_Cabinetmakers_Builder_Guide.pdf"
RENDERINGS = ROOT / "cabinetmakers-guide" / "renderings"
SPEC = json.loads((ROOT / "project" / "specification.yaml").read_text(encoding="utf-8"))
REVISION = SPEC["project"]["revision"]
RED = colors.HexColor("#A33B32")
GREEN = colors.HexColor("#547A58")


def rel(path: str) -> Path:
    return ROOT / path


PAGES = [
    ("Opening system", "Cabinetmaker’s Door & Millwork Builder’s Guide", f"A controlled {REVISION} workflow for the five-panel slab, completed jamb, physical hardware, stops, casing, backband, and evidence-supported trim.", "cabinetmakers-guide/renderings/01-complete-system.svg", 7.05),
    ("Document control", "Revision and governing records", "The checked-in specification, signed field records, physical samples, and released registers govern every production decision.", None, None),
    ("Guide method", "How to use gates and dispositions", "Read in order. Each operation defines setup, action, acceptance, hold, correction, and remake conditions.", None, None),
    ("System anatomy", "The completed opening", "Treat slab, completed jamb, stop, casing, backband, and optional details as separate fitted layers.", "cabinetmakers-guide/renderings/01-complete-system.svg", 6.65),
    ("Production control", "Master workflow and release gates", "No operation advances until its incoming measurements, tooling, samples, and records are accepted.", None, None),
    ("Field evidence", "Existing conditions and historic fit", "Document both faces, adjacent original millwork, floor, wall, hardware, and finish before choosing trim details.", "moulding-guide/illustrations/02-field-measurements.svg", 6.15),
    ("Field survey", "Measure the completed jamb", "Record limiting widths and heights, plumb, square, twist, projection, floor datum, handing, and swing.", "cabinetmakers-guide/renderings/09a-jamb-fit-map.svg", 6.60),
    ("Dimension control", "Jamb, prefit, and fitted-slab states", "Keep the confirmed 24 x 81 jamb, 23-7/8 x 80-5/8 prefit assembly, and 23-3/4 x 80-1/2 fitted slab distinct.", None, None),
    ("Shop safety", "Operation-specific safety and PPE", "Match guarding, extraction, support, workholding, and emergency controls to each operation.", None, None),
    ("Machine readiness", "Calibrate before touching project stock", "Prove saw, jointer, planer, router, DF 500, squares, and assembly platform on scrap.", "cabinetmakers-guide/renderings/03a-machine-calibration.svg", 6.65),
    ("Procurement", "Materials, test stock, and consumables", "Reserve A-O for the door; use finished M for the upper panel, keep damaged A intact, keep 74-inch N/O full as short-core reserve, and release continuous layers, coupons, and seam maps before replacement stock.", None, None),
    ("Cut schedule", "Door frame members", "Build the eight structural members as balanced three-layer families while preserving every finished dimension.", "quick-guide/illustrations/01-parts-map.svg", 5.58),
    ("Cut schedule", "Panels and field-fit moulding", "Panel sizes include 7/16-inch tongue projection; moulding lengths remain scheme- and field-dependent.", None, None),
    ("Material control", "Board allocation, moisture, and grain", "Follow the A-O map in order: prove continuous stile layers first, then release panels, cores, and the short-face pool.", "cabinetmakers-guide/renderings/03c-board-a-o-allocation-map.png", 6.45),
    ("Rough milling", "Plane, rest, press, and prove the balanced layup", "Thickness-plane whole mother billets to 5/16 faces without resawing, retain a 7/8 core, and distinguish the eight frame laminations from the five edge-glued floating panels.", "cabinetmakers-guide/renderings/03b-door-lamination-map.png", 5.50),
    ("Final milling", "Rest, surface symmetrically, and verify seams", "Remove 1/16 from each outer face, retain a 1/4 + 7/8 + 1/4 section, and mark the D-101D/F seams exactly as shown.", "cabinetmakers-guide/renderings/03d-wide-rail-seam-map.png", 6.30),
    ("Datums", "Component marks and face discipline", "Mark ID, SF, RF, RE, top, bottom, and direction before any groove or Domino operation.", "cabinetmakers-guide/renderings/03e-datum-marking-map.png", 6.25),
    ("Layout", "Story stick and rail stack", "Transfer every shoulder and stile mortise center from the slab-top master datum.", "quick-guide/illustrations/00-rail-stack.svg", 6.35),
    ("Groove engineering", "Geometry and machining split", "Use the dado only for supported through rail grooves; route stopped, segmented, and muntin grooves.", "cabinetmakers-guide/renderings/04-groove-panel-cutaway.svg", 6.55),
    ("Dado operation", "Supported through rail grooves", "Prove the SawStop-compatible dado setup and conventionally feed only stable, fully supported rail edges.", "cabinetmakers-guide/renderings/04a-groove-setups.svg", 6.60),
    ("Router operation", "Opening-only stile grooves", "Use a clamped plunge router, edge guide, and positive start/stop blocks—never a freehand drop cut.", "cabinetmakers-guide/renderings/04a-groove-setups.svg", 6.60),
    ("Critical grooves", "Segmented lower rails and muntin", "Preserve the full 6-1/8-to-9-1/8-inch joint footprint and machine D-101G only in a captured support fixture.", "cabinetmakers-guide/renderings/04a-groove-setups.svg", 6.60),
    ("Panel making", "Prepare and glue solid panel blanks", "Arrange, joint, dry-check, edge-glue, clamp lightly, cure, and flatten the five panel blanks.", "cabinetmakers-guide/renderings/04b-panel-glue-map.png", 6.40),
    ("Panel machining", "Size, tongue, and relieve corners", "Form a 7/32 +/-0.005 x 7/16 +/-0.005 tongue with bottom clearance and remove each complete tongue corner square.", "cabinetmakers-guide/renderings/04-groove-panel-cutaway.svg", 5.85),
    ("Panel release", "Spacer compression and edge prefinish", "Use four spacers per panel in vertical grooves only; test H/J/N separately from K/L and keep every panel movable.", "cabinetmakers-guide/renderings/04c-spacer-placement-map.png", 6.35),
    ("Hardware gate", "Map the physical lock before J-06", "Overlay the actual lock and preserve 1/4 inch of clear wood to J-06 and other structural joinery.", "cabinetmakers-guide/renderings/05b-lock-envelope.svg", 6.60),
    ("DF 500 setup", "Cutter, fence, width, and workholding", "Prove cutter, plunge, 17.5 mm fence height, 90-degree fence, datum face, support, and extraction.", "cabinetmakers-guide/renderings/05a-df500-workholding.svg", 6.60),
    ("Test-piece gate", "Production samples and relieved assembly tenons", "Retain full-thickness joint samples; reserve untouched factory tenons for final adhesive stages.", "cabinetmakers-guide/renderings/05a-df500-workholding.svg", 6.55),
    ("Frame joinery", "Four-inch rail-to-stile joints", "Use revised 1.250 and 2.750-inch centers, one tight locator, and one medium follower.", "cabinetmakers-guide/renderings/05-rail-stile-joint.svg", 6.60),
    ("Lock rail", "J-05 and hardware-gated J-06", "Use 1.250, 3.500, and 5.750-inch centers only after the physical lock envelope passes.", "cabinetmakers-guide/renderings/05b-lock-envelope.svg", 6.60),
    ("Bottom rail", "J-09 and J-10", "Use four tenons at the revised centers while preserving shoulder, face, and edge integrity.", "cabinetmakers-guide/renderings/05-rail-stile-joint.svg", 6.55),
    ("Critical joint", "Muntin J-11 and J-12", "Use D-101G centers 1 and 2 inches, mating-rail centers 7-1/8 and 8-1/8 inches, and actual web gates.", "cabinetmakers-guide/renderings/06a-muntin-clearance.svg", 6.60),
    ("Joint control", "Complete setup register and section tests", "Check all twelve joint families, member-specific datums, mortise widths, and measured web before assembly.", None, None),
    ("Assembly inventory", "Exploded five-panel door", "Reconcile thirteen wood parts, thirty final tenons, five panels, spacers, clamps, and measurement tools.", "cabinetmakers-guide/renderings/02-exploded-door.svg", 6.60),
    ("Dry fit 1", "Prove the whole door before Stage A", "Keep D-101E/G/F unglued and prove the complete slab, all panels, sequence, square, and twist.", "cabinetmakers-guide/renderings/07a-full-dry-fit.svg", 6.60),
    ("Glue-up overview", "Two-stage glue-up at a glance", "Dry-fit first, glue the lower module, cure and dry-fit again, then glue the full frame while every panel remains dry.", "cabinetmakers-guide/renderings/07b-two-stage-glue-storyboard.png", 6.40),
    ("Stage A glue", "Time and assemble the lower module", "Glue only E/G/F joinery, capture K/L dry, close shoulders, square, and record elapsed time.", "cabinetmakers-guide/renderings/08a-glue-clock.svg", 6.60),
    ("Stage A release", "Cure and inspect the lower module", "Verify size, square, flatness, web integrity, panel travel, and full cure before reuse.", "cabinetmakers-guide/renderings/06-lower-module.svg", 6.55),
    ("Dry fit 2", "Repeat with the cured lower module", "Reassemble the complete door and release the exact Stage B loading and clamp sequence.", "cabinetmakers-guide/renderings/07a-full-dry-fit.svg", 6.60),
    ("Stage B glue", "Timed adhesive application and loading", "Load from the hinge stile, keep every panel dry, and close D-101B parallel across all joints.", "cabinetmakers-guide/renderings/07-frame-loading.svg", 6.60),
    ("Geometry control", "Clamp, square, and remove twist", "Work from light pressure, correct the long diagonal, and verify winding sticks before final pressure.", "cabinetmakers-guide/renderings/08-clamp-geometry.svg", 6.60),
    ("Post-cure surfacing", "Scrape, flush, and sand through P100", "Recheck geometry, remove glue, level accepted offsets, and stop at P100 until fitting and hardware machining pass.", "cabinetmakers-guide/renderings/08b-post-cure-surfacing-map.png", 6.25),
    ("Field fit", "Calculate the installed slab", "Move from the 24 x 81 jamb to the prefit slab and then the 23-3/4 x 80-1/2 fitted slab without mixing the three states.", "cabinetmakers-guide/renderings/09d-prefit-finished-overlay.png", 6.15),
    ("Field fit", "Fit the hinge edge and head", "Establish the hinge datum first, then transfer the head condition and test frequently.", "cabinetmakers-guide/renderings/09a-jamb-fit-map.svg", 6.55),
    ("Field fit", "Fit lock edge, bevel, and undercut", "Carry the measured closing bevel and floor datum while staying inside the released removal allowance.", "cabinetmakers-guide/renderings/09a-jamb-fit-map.svg", 6.55),
    ("Hinges", "Lay out and fit the actual leaves", "Knife physical leaves, rout slightly shallow, pare to flush, drill centered pilots, and use steel setup screws.", "cabinetmakers-guide/renderings/09b-hinge-gain.svg", 6.60),
    ("Temporary hang", "Diagnose swing and reveals", "Cycle the unfinished slab through the full arc and correct hinge-axis or edge geometry by cause.", "cabinetmakers-guide/renderings/09-hanging-system.svg", 6.60),
    ("Mortise lock", "Cut body mortise and faceplate", "Machine incrementally from the physical lock, protect J-06 clearance, and fit the faceplate flush.", "cabinetmakers-guide/renderings/09c-lock-strike.svg", 6.60),
    ("Lock and strike", "Bore from both faces and transfer the latch", "Prevent breakout, locate the strike from the operating latch, and correct sag before enlarging anything.", "cabinetmakers-guide/renderings/09c-lock-strike.svg", 6.60),
    ("Functional gate", "Release the operating door before finish", "Confirm full swing, clearances, latch, strike, hardware fit, and panel freedom; then remove hardware.", "cabinetmakers-guide/renderings/09-hanging-system.svg", 6.55),
    ("Millwork scope", "Profiles and layer relationships", "Separate the one stop set from face-dependent casing, backband, cap, plinth, and base transitions.", "cabinetmakers-guide/renderings/10-moulding-layers.svg", 6.60),
    ("Millwork production", "Mill matched moulding families", "Machine casing, backband, stop, and optional parts as labeled families with full-size approved samples.", "cabinetmakers-guide/renderings/10a-moulding-milling.svg", 6.60),
    ("Casing lengths", "Face-specific formula register", "Calculate each face from its own W, H-L, H-R, reveal, casing width, joint scheme, and datum.", "moulding-guide/illustrations/04-length-formulas.svg", 5.90),
    ("Backband lengths", "Scheme-specific side and head formulas", "Mitered sides add B; square sides add C; the head adds 2B—then each rough blank receives allowance.", "cabinetmakers-guide/renderings/11a-backband-corners.svg", 6.60),
    ("Mitered head", "Fit a true mitered surround", "Transfer both legs, tune miters on a shooting board, and dry-fit the complete casing and backband corners.", "cabinetmakers-guide/renderings/11-head-joint-options.svg", 6.60),
    ("Square head", "Fit a square-butt surround", "Fit independent legs, span them with the head, and add a cap only when field evidence supports it.", "cabinetmakers-guide/renderings/11-head-joint-options.svg", 6.60),
    ("Stops", "Fit the operating-door stop set", "Fit head first, sides beneath, tack through removable shims, cycle, then complete fasteners.", "cabinetmakers-guide/renderings/12-stop-casing-section.svg", 6.60),
    ("Casing", "Fit, scribe, and dry-assemble each face", "Establish the casing-to-jamb reveal, fit both bottoms independently, transfer the head, and bear flat.", "cabinetmakers-guide/renderings/12a-casing-scribe.svg", 6.60),
    ("Outer trim", "Backband, cap, plinth, and returns", "Transfer from fitted casing, preserve the chosen joint language, and close every visible termination.", "cabinetmakers-guide/renderings/11a-backband-corners.svg", 6.60),
    ("Fastening", "Fastener paths and glue boundaries", "Test depth and angle, verify substrate and utilities, and keep adhesive off jamb, wall, plaster, floor, and slab.", "cabinetmakers-guide/renderings/12-stop-casing-section.svg", 6.55),
    ("Final finish", "P120 preparation, Rubio application, and cure", "After all fitting and dry machining, final-sand, clean, apply the accepted sample system, and control oily waste.", "cabinetmakers-guide/renderings/12b-finish-sequence.svg", 6.60),
    ("Final installation", "Brass hardware and complete system", "After full cure, install brass hardware by hand, hang, fit trim layers, touch up, and cycle again.", None, None),
    ("Quality control", "Troubleshooting and numeric acceptance", "Diagnose geometry, joinery, panels, hardware, trim, fasteners, and finish against controlled thresholds.", "cabinetmakers-guide/renderings/13-final-release.svg", 6.55),
    ("Release", "Field release, record, and maintenance", "Pass the work only when measured geometry, operation, movement, historic fit, finish, documentation, and owner handoff agree.", None, None),
]


RENDER_SLUGS = [
    "01-complete-system",
    "02-exploded-door",
    "03a-machine-calibration",
    "04-groove-panel-cutaway",
    "04a-groove-setups",
    "05-rail-stile-joint",
    "05a-df500-workholding",
    "05b-lock-envelope",
    "06-lower-module",
    "06a-muntin-clearance",
    "07-frame-loading",
    "07a-full-dry-fit",
    "08-clamp-geometry",
    "08a-glue-clock",
    "09-hanging-system",
    "09a-jamb-fit-map",
    "09b-hinge-gain",
    "09c-lock-strike",
    "10-moulding-layers",
    "10a-moulding-milling",
    "11-head-joint-options",
    "11a-backband-corners",
    "12-stop-casing-section",
    "12a-casing-scribe",
    "12b-finish-sequence",
    "13-final-release",
]


def page_decor(canvas, doc):
    canvas.saveState()
    canvas.setTitle("DC-1916-001 Cabinetmaker's Door and Millwork Builder's Guide")
    canvas.setAuthor("DC-1916-001 Project Team")
    canvas.setSubject("Integrated fabrication, hanging, and matching-millwork instructions")
    canvas.setStrokeColor(OAK)
    canvas.setLineWidth(1.2)
    canvas.line(0.65 * inch, 0.52 * inch, 7.85 * inch, 0.52 * inch)
    canvas.setFont("Helvetica-Bold", 7.1)
    canvas.setFillColor(BLUE)
    canvas.drawString(
        0.65 * inch,
        0.36 * inch,
        f"DC-1916-001  |  CABINETMAKER'S GUIDE  |  {REVISION.upper()}",
    )
    canvas.setFont("Helvetica", 7.1)
    canvas.setFillColor(GRAY)
    canvas.drawRightString(
        7.85 * inch,
        0.36 * inch,
        f"PAGE {canvas.getPageNumber():02d} OF {len(PAGES)}",
    )
    canvas.restoreState()


def make_doc():
    doc = BaseDocTemplate(
        str(OUT),
        pagesize=letter,
        leftMargin=0.68 * inch,
        rightMargin=0.68 * inch,
        topMargin=0.48 * inch,
        bottomMargin=0.65 * inch,
    )
    frame = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        letter[0] - doc.leftMargin - doc.rightMargin,
        letter[1] - doc.topMargin - doc.bottomMargin,
        id="cabinetmakers-guide",
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
    )
    doc.addPageTemplates(PageTemplate(id="cabinetmakers-guide", frames=frame, onPage=page_decor))
    return doc


def source_pages(text: str) -> dict[int, list[str]]:
    pages: dict[int, list[str]] = {}
    for block in re.split(r"(?=^## )", text, flags=re.M):
        lines = block.splitlines()
        if not lines or not lines[0].startswith("## "):
            continue
        match = re.match(r"##\s+(\d{1,2})\b", lines[0])
        if match:
            pages[int(match.group(1))] = lines[1:]
    return pages


def figure_asset(path: Path, width):
    """Use native vectors for generated SVGs and a high-resolution fallback for legacy SVGs."""
    if path.suffix.lower() == ".svg":
        return svg_figure(path, width)
    with PILImage.open(path) as image:
        height = width * image.height / image.width
    return RLImage(str(path), width=width, height=height)


def compact_table(rows, s, widths=None):
    data = []
    for row_index, row in enumerate(rows):
        style = s["QTableHead"] if row_index == 0 else s["QTable"]
        data.append([Paragraph(inline(str(value)), style) for value in row])
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), BLUE),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]),
                ("GRID", (0, 0), (-1, -1), 0.4, RULE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
            ]
        )
    )
    return table


def parse_markdown(lines: list[str], s, include_tables=True):
    out, rows = [], []

    def flush():
        nonlocal rows
        if rows:
            if include_tables:
                column_width = 6.80 * inch / len(rows[0])
                out.extend([compact_table(rows, s, [column_width] * len(rows[0])), Spacer(1, 5)])
            rows = []

    for line in lines:
        value = line.strip()
        if value.startswith("|"):
            if "---" not in value:
                rows.append([cell.strip() for cell in value.strip("|").split("|")])
            continue
        flush()
        if not value or value.startswith("# "):
            continue
        if value.startswith("### "):
            out.append(Paragraph(inline(value[4:]), s["QH2"]))
        elif value.startswith("- [ ] "):
            out.append(Paragraph("&#9633; " + inline(value[6:]), s["QBullet"]))
        elif value.startswith("- "):
            out.append(Paragraph("&#8226; " + inline(value[2:]), s["QBullet"]))
        elif re.match(r"^\d+\.\s", value):
            number, body = value.split(". ", 1)
            out.append(Paragraph(f"<b>{number}.</b> {inline(body)}", s["QNumber"]))
        elif value.startswith("> "):
            out.append(
                Table(
                    [[Paragraph(inline(value[2:]), s["QStop"])]],
                    colWidths=[6.80 * inch],
                    style=TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAEFEC")),
                            ("BOX", (0, 0), (-1, -1), 0.65, RED),
                            ("LEFTPADDING", (0, 0), (-1, -1), 7),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                            ("TOPPADDING", (0, 0), (-1, -1), 5),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                        ]
                    ),
                )
            )
        else:
            out.append(Paragraph(inline(value), s["QBody"]))
    flush()
    return out


def fmt(value) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if number.is_integer():
        return str(int(number))
    return f"{number:.4f}".rstrip("0").rstrip(".")


def inch_fraction(value) -> str:
    number = float(value)
    whole = int(number)
    fraction = Fraction(number - whole).limit_denominator(64)
    if fraction.numerator == 0:
        return str(whole)
    part = f"{fraction.numerator}/{fraction.denominator}"
    return f"{whole}-{part}" if whole else part


def read_csv(path: Path):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def schedule_blocks(page_number: int, s):
    visual_steps = {
        14: [
            ["Step", "Action", "Release check"],
            ["1", "Keep A full; keep N/O at 1-3/4 x 11 x 74.", "Reserve labels remain attached."],
            ["2", "Prove B/C show faces and I/K two-lane yield.", "All four continuous stile layers pass."],
            ["3", "Map M/G/H/D panel billets.", "Five panel blanks have clear, stable yield."],
            ["4", "Map J/L cores.", "C, M, D, E, F, and G cores are accounted for."],
            ["5", "Release FP-05 face billets from E/F and eligible offcuts.", "Every face is clear, traceable, and long enough."],
        ],
        16: [
            ["Step", "Action", "Check"],
            ["1", "Rest every cured lamination.", "Moisture and shape are stable."],
            ["2", "Plane 1/16 from each outside face in alternating passes.", "Finished section is 1/4 + 7/8 + 1/4."],
            ["3", "Mark D-101D core/show/back seams and D-101F seams.", "Measure from finished top; every station is within +/-1/32."],
            ["4", "Verify seam offsets before Domino machining.", "Core-to-face offset is at least 1/2."],
        ],
        17: [
            ["Step", "Action", "Check"],
            ["1", "Lay the part in door orientation with SF up.", "ID and arrows read normally."],
            ["2", "Mark ID, SF, RF, RE, top, and bottom.", "Marks are permanent or on blue tape."],
            ["3", "Mark the hinge-side shoulder as rail zero.", "All length coordinates use the same end."],
            ["4", "Transfer from the story stick and knife mating lines.", "Never measure from an unfinished or rounded edge."],
        ],
        23: [
            ["Step", "Action", "Check"],
            ["1", "Arrange the labeled staves for grain and color.", "Grain runs vertically in door orientation."],
            ["2", "Joint mating edges as pairs.", "Dry seams close by hand."],
            ["3", "Mark SF and stave order.", "The layout cannot be reversed."],
            ["4", "Glue edges with a thin Type II PVA film.", "No dry spots or heavy flooding."],
            ["5", "Clamp lightly between flat cauls.", "Blank stays flat; fine squeeze line appears."],
            ["6", "Cure fully, then flatten and size.", "No open seam and full finished size remains."],
        ],
        25: [
            ["Step", "Action", "Check"],
            ["1", "Measure every spacer-zone groove.", "Candidate foam matches the actual groove range."],
            ["2", "Test H/J/N and K/L as separate families.", "Both full-size samples pass independently."],
            ["3", "Place two spacers in each vertical side groove.", "Four spacers per panel; none in horizontal grooves."],
            ["4", "Prefinish panel edges and tongues only.", "No finish enters frame glue surfaces."],
            ["5", "Close the sample and move the panel sideways.", "Shoulders close; no rattle, stress, or binding."],
        ],
        36: [
            ["Step", "Action", "Check"],
            ["1", "Dry-fit the complete unglued door.", "Square, twist, shoulders, and panels pass."],
            ["2", "Glue Stage A: E/G/F only.", "Use four 6 x 40 tenons; K/L remain dry."],
            ["3", "Cure and inspect the lower module.", "K/L still move; module is square and flat."],
            ["4", "Dry-fit the full door again and time it.", "Finish inside 75% of open time, keeping a 25 percent buffer."],
            ["5", "Glue Stage B frame joints.", "Use 26 large tenons; all panel grooves stay dry."],
            ["6", "Complete the final timed geometry check.", "All five panels move before the time gate."],
        ],
        42: [
            ["Step", "Action", "Check"],
            ["1", "Allow full cure on a flat support.", "Temperature and humidity are recorded."],
            ["2", "Remove clamps and recheck geometry.", "Size, diagonals, twist, shoulders, and panels pass."],
            ["3", "Scrape glue in raking light.", "Do not flood white oak with water."],
            ["4", "Level only accepted minor offsets.", "No hollow or rounded datum edge."],
            ["5", "Sand uniformly through P100 and stop.", "P120 waits for fitting and hardware release."],
        ],
    }
    if page_number in visual_steps:
        return [
            compact_table(
                visual_steps[page_number],
                s,
                [0.45 * inch, 3.45 * inch, 2.90 * inch],
            )
        ]
    if page_number == 2:
        rows = [
            ["Control", "Authority", "Bench use", "Hold condition"],
            ["Specification", "Fixed geometry", "Dimensions and tolerances", "Any unsynchronized change"],
            ["Field record", "Completed opening", "Final fit and trim formulas", "Unsigned or conflicting value"],
            ["Test piece", "Actual setup", "Cutter, fit, and web proof", "Breakout, bind, or mismatch"],
            ["Rendering", "Sequence only", "Orientation and relationships", "Never used as a cutting template"],
        ]
        return [
            compact_table(
                rows,
                s,
                [1.22 * inch, 1.45 * inch, 2.05 * inch, 2.08 * inch],
            ),
            Spacer(1, 7),
            note_cards(
                [
                    ("Blue", "Fixed shop control from the project specification.", BLUE, PALE_BLUE),
                    ("Amber", "Field value, sample, or physical hardware required.", OAK_DARK, PALE),
                    ("Red", "Stop; correct and revalidate before continuing.", RED, colors.HexColor("#FAEFEC")),
                ],
                s,
            ),
        ]
    if page_number == 5:
        rows = [
            ["Gate", "Incoming evidence", "Release test", "Retained record"],
            ["1 Opening", "Jamb, floor, handing, trim", "Geometry and scope signed", "Field worksheet"],
            ["2 Hardware", "Physical hinges, lock, strike", "Every dependent dimension known", "Hardware sheet"],
            ["3 Material", "Moisture, defects, grain pairs", "Board allocation accepted", "Cut map"],
            ["4 Machine", "Cutter, guard, fence, stops", "Labeled sample passes", "Setup sample"],
            ["5 Dry fit", "All parts and relieved tenons", "Square, flat, free panels", "Dry-fit sheet"],
            ["6 Glue-up", "Timed rehearsal and clamps", "Inside open time; geometry held", "Glue record"],
            ["7 Hung slab", "Final fit and hardware", "Swing, reveal, latch pass", "Install record"],
            ["8 Millwork", "Face formulas and dry fit", "Joints and bearing pass", "Face register"],
            ["9 Final", "Finish and full system", "Every acceptance item passes", "Build record"],
        ]
        return [
            compact_table(
                rows,
                s,
                [0.86 * inch, 2.05 * inch, 2.15 * inch, 1.74 * inch],
            )
        ]
    if page_number == 9:
        rows = [
            ["Operation", "Primary setup", "Required control", "Stop if"],
            ["Through rail grooves", "1/4-in dado stack", "Correct cartridge/insert, guard strategy, push blocks, full support", "Feed or support is uncertain"],
            ["Stopped/segmented grooves", "Plunge router + edge guide", "Clamped stock and positive start/stop blocks", "A drop cut or freehand start is proposed"],
            ["Domino", "DF 500 only", "Clamped stock, fixed fence, extraction", "Machine rocks or slot breaks out"],
            ["Trim profile", "Saw / plunge router / planes", "Wide mother blank and stable support", "Default profile needs a dado"],
            ["Hardware", "Guided router / chisels", "Physical part and steel setup screws", "Template differs from hardware"],
            ["Nailing", "Sequential-actuation nailer", "Verified substrate and utility path", "Fastener path is uncertain"],
            ["Finish", "Rubio system", "Ventilation and safe rag disposal", "Sample or disposal plan is absent"],
        ]
        return [
            compact_table(
                rows,
                s,
                [1.00 * inch, 1.38 * inch, 2.52 * inch, 1.90 * inch],
            )
        ]
    if page_number == 11:
        rows = [
            ["Family", "Controlled specification", "Planning quantity", "Selection rule"],
            ["Door lumber", "A now 72-3/4 in; B-F/H-K rough QS oak; G confirmed S4S at 15/16 x 4-1/2 x 75; L now 6 in wide; balanced frame layup", "No purchase currently released", "LS-05 / RL-02; no resaw; G thickness/width/length pass; prove B/C faces, K/I lanes, J's 6-1/2-in F-core envelope, revised J/L map, coupons, and D/F seams"],
            ["Panels", "STOCK-M/G/H/D primary; A is first upper-panel fallback", "G thickness/width/length fit four J staves; CHK-P-01 still controls; all A-O milling-gated", "CHK-RS-01 + CHK-P-01; vertical grain and matched lower pair"],
            ["Casing + stop", "S4S QS white oak, 4/4 x nominal 6 in x 8 ft", "7 boards; about 28 dealer BF", "Four sides, both heads, full-length spare; mill stop from a wide mother blank"],
            ["Backband", "S4S QS white oak, 6/4 x nominal 6 in x 8 ft", "2 boards; about 12 dealer BF", "All backband; optional caps only when field-supported"],
            ["Order control", "Correct notation is 4/4, not 4 x 4", "About 40 dealer BF total", "No plinth stock; no A-O stock credited to moulding"],
            ["10 x 50 tenons", "Factory beech", "60: 26 final + 26 test + 8 spare", "Segregate and label each group"],
            ["6 x 40 tenons", "Factory beech", "12: 4 final + 4 test + 4 spare", "Segregate and label each group"],
            ["Panel spacers", "3/4-in-long oil/silicone-free foam", "30: 20 installed + 10 test/spare", "PB265 is candidate only; release H/J/N and K/L separately"],
            ["Hardware", "Brass visible set", "Physical project set", "Measure before machining"],
            ["Adhesive + shop kit", "Fresh Type II PVA; timer, cauls, clamps, P120 abrasives", "One controlled production set", "Same-layup coupon and timed rehearsal must pass"],
            ["Finish", "Rubio Oil Plus 2C Pure", "Coverage + sample allowance", "Room-approved sample controls"],
        ]
        return [
            compact_table(
                rows,
                s,
                [1.00 * inch, 1.75 * inch, 1.75 * inch, 2.30 * inch],
            )
        ]
    if page_number == 7:
        rows = [
            ["Completed-jamb field", "Top", "Middle", "Bottom / left / right"],
            ["Width", "________", "________", "________"],
            ["Height", "Left ________", "Center ________", "Right ________"],
            ["Door clearance", "Head ________", "Hinge ________", "Lock ________ / floor ________"],
            ["Geometry", "Plumb ________", "Square ________", "Twist / projection ________"],
        ]
        return [
            compact_table(rows, s, [1.60 * inch, 1.60 * inch, 1.60 * inch, 2.00 * inch]),
        ]
    if page_number == 8:
        return [
            note_cards(
                [
                    ("Confirmed jamb", "24 x 81 inches clear and reported consistent throughout the installed finished jamb.", BLUE, PALE_BLUE),
                    ("Prefit assembly", "23-7/8 x 80-5/8 x 1-3/8 inches after cure and surfacing; retain 1/16 on every perimeter edge.", TEAL, PALE_TEAL),
                    (
                        "Finished fitted slab",
                        "23-3/4 x 80-1/2 x 1-3/8 inches: 1/8 at both sides and head, 3/8 at bottom; any latch-edge bevel stays inside that maximum rectangle.",
                        OAK_DARK,
                        PALE,
                    ),
                ],
                s,
            )
        ]
    if page_number == 14:
        rows = [
            ["Family", "Allocation objective", "Required grain relationship", "Reject / relocate"],
            ["D-101A/B", "B show / K core / K back; C show / I core / I back", "I/K ordinary-ripped to two 4-3/8 lanes each; B/C whole-billet show faces; no resaw", "End joint, runout, bow, or hardware-zone defect"],
            ["C/M/E/G", "J/L cores; D/H tails, C/J/L offcuts, E/F pool; M tail after H passes", "One-piece cores; five clear 16-1/4 E/F billets; A intact; N/O short-core reserve", "Short grain, knot boundary, or seam in one-piece core"],
            ["D-101D/F", "Mapped stave cores and staggered faces", "Released seam coordinates; full-length staves", "Unmapped seam or mortise conflict"],
            ["H/J/N/K/L", "STOCK-M/G/H/D after LS-05 gates; A reserved for H fallback", "Vertical grain; K/L paired", "Failed dressed yield or mixed color"],
            ["M-201/202", "Pair each face independently", "Leg pair plus closest head", "Face mixing without record"],
        ]
        return [
            compact_table(
                rows,
                s,
                [0.95 * inch, 1.85 * inch, 2.10 * inch, 1.90 * inch],
            ),
            Spacer(1, 7),
            note_cards(
                [
                    ("Moisture", "Accept 6-9 percent after acclimation.", BLUE, PALE_BLUE),
                    ("LS-05 basis", "A is 72-3/4 in; B-F/H-K remain rough; G is confirmed S4S at 15/16 x 4-1/2 x 75; L is 6 in wide; M is finished 3/4 x 8-1/4 x 99; N/O are each finished white oak 1-3/4 x 11 x 74 and held full. All physical yield remains conditional.", TEAL, PALE_TEAL),
                    ("Priority", "Physical yield and structural soundness first; visual pairing second.", OAK_DARK, PALE),
                ],
                s,
            ),
        ]
    if page_number == 12:
        frame_ids = {"D-101A", "D-101B", "D-101C", "D-101M", "D-101D", "D-101E", "D-101F", "D-101G"}
        records = [
            row
            for row in read_csv(ROOT / "build" / "reports" / "cut-list.csv")
            if row["Part identifier"] in frame_ids
        ]
        rows = [["ID", "Member", "Qty", "Glue blank T x W x L", "Finished T x W x L"]]
        for row in records:
            rough = " x ".join(fmt(row[key]) for key in ("Rough thickness", "Rough width", "Rough length"))
            finished = " x ".join(fmt(row[key]) for key in ("Finished thickness", "Finished width", "Finished length"))
            rows.append([row["Part identifier"], row["Part name"], row["Quantity"], rough, finished])
        return [
            compact_table(
                rows,
                s,
                [0.62 * inch, 1.48 * inch, 0.38 * inch, 2.15 * inch, 2.15 * inch],
            ),
            Spacer(1, 6),
            note_cards(
                [
                    ("Section", "Preglue 5/16 + 7/8 + 5/16; finish 1/4 + 7/8 + 1/4. Plane faces in staged passes; never resaw.", BLUE, PALE_BLUE),
                    ("Stiles", "D-101A B/K/K; D-101B C/I/I (show/core/back). I/K ordinary-ripped into one core and one back-face lane; no end joints.", TEAL, PALE_TEAL),
                    ("Hold", "Coupons and D/F seam map pass before joinery; perimeter fitting waits for the jamb.", OAK_DARK, PALE),
                ],
                s,
            ),
        ]
    if page_number == 13:
        panel_ids = {"D-101H", "D-101J", "D-101N", "D-101K", "D-101L"}
        cut_records = [
            row
            for row in read_csv(ROOT / "build" / "reports" / "cut-list.csv")
            if row["Part identifier"] in panel_ids
        ]
        panel_rows = [["Panel", "Qty", "Rough T x W x L", "Finished T x W x L"]]
        for row in cut_records:
            rough = " x ".join(fmt(row[key]) for key in ("Rough thickness", "Rough width", "Rough length"))
            finished = " x ".join(fmt(row[key]) for key in ("Finished thickness", "Finished width", "Finished length"))
            panel_rows.append([row["Part identifier"], row["Quantity"], rough, finished])
        moulding = read_csv(ROOT / "build" / "reports" / "moulding-cut-list.csv")
        moulding_rows = [["Moulding", "Qty", "Finished section", "Length control"]]
        for row in moulding:
            section = f'{fmt(row["Finished thickness"])} x {fmt(row["Finished width"])}'
            moulding_rows.append(
                [row["Part identifier"], row["Quantity"], section, row["Finished length"]]
            )
        return [
            Paragraph("Floating-panel shop schedule", s["QH2"]),
            compact_table(panel_rows, s, [0.82 * inch, 0.54 * inch, 2.72 * inch, 2.72 * inch]),
            Spacer(1, 5),
            Paragraph("Field-fit moulding schedule", s["QH2"]),
            compact_table(moulding_rows, s, [0.82 * inch, 1.12 * inch, 1.14 * inch, 3.72 * inch]),
        ]
    if page_number == 24:
        components = {item["id"]: item for item in SPEC["components"]}
        full_opening_width = SPEC["frame"]["rail_shoulder_length"]
        lower_opening_width = SPEC["frame"]["bottom_opening_each"]
        openings = {
            "D-101H": (full_opening_width, SPEC["frame"]["vertical_openings"]["P-01 upper"]),
            "D-101J": (full_opening_width, SPEC["frame"]["vertical_openings"]["P-02 center"]),
            "D-101N": (full_opening_width, SPEC["frame"]["vertical_openings"]["P-03 lower-center"]),
            "D-101K": (lower_opening_width, SPEC["frame"]["vertical_openings"]["P-04 bottom"]),
            "D-101L": (lower_opening_width, SPEC["frame"]["vertical_openings"]["P-04 bottom"]),
        }
        rows = [["Panel", "Clear frame opening", "Finished panel", "Across-grain clear.", "Parallel clear."]]
        for panel_id in ("D-101H", "D-101J", "D-101N", "D-101K", "D-101L"):
            opening_w, opening_h = openings[panel_id]
            panel = components[panel_id]
            across = (
                SPEC["panels"]["small_width_clearance_across_grain_total"]
                if panel_id in {"D-101K", "D-101L"}
                else SPEC["panels"]["full_width_clearance_across_grain_total"]
            )
            rows.append(
                [
                    panel_id,
                    f"{inch_fraction(opening_w)} x {inch_fraction(opening_h)}",
                    f'{inch_fraction(panel["w"])} x {inch_fraction(panel["l"])}',
                    f"{inch_fraction(across)} total",
                    f'{inch_fraction(SPEC["panels"]["clearance_parallel_to_grain_total"])} total',
                ]
            )
        return [
            compact_table(
                rows,
                s,
                [0.84 * inch, 1.24 * inch, 1.50 * inch, 1.70 * inch, 1.52 * inch],
            ),
            Spacer(1, 7),
            note_cards(
                [
                    ("Tongue", "7/32 +/-0.005 thick x 7/16 projection +/-0.005; relieve the complete 7/16 corner square.", BLUE, PALE_BLUE),
                    ("Spacer", "3/4-in longitudinal length; two per vertical groove after the two-family Page 25 release.", TEAL, PALE_TEAL),
                    ("Release", "Every dry panel moves laterally by hand.", OAK_DARK, PALE),
                ],
                s,
            ),
        ]
    if page_number == 33:
        records = read_csv(ROOT / "project" / "domino-setup-register.csv")
        pairs = [(0, 1), (2, 3), (4, 5), (6, 7), (8, 9), (10, 11)]
        rows = [["Joints", "Part A to Part B", "Tenon", "A centers + datum", "B centers + datum", "Width A / B"]]
        for left, right in pairs:
            row = records[left]
            width = (
                f'{row["Mortise-width setting Part A"]} / '
                f'{row["Mortise-width setting Part B"]}'
            )
            rows.append(
                [
                    f'{records[left]["Joint ID"]}/{records[right]["Joint ID"]}',
                    f'{row["Part A"]} to {row["Part B"]}',
                    row["Tenon dimensions"],
                    f'{row["Tenon centerline Part A from reference edge"]}; {row["Reference edge Part A"]}',
                    f'{row["Tenon centerline Part B from reference edge"]}; {row["Reference edge Part B"]}',
                    width,
                ]
            )
        return [
            compact_table(
                rows,
                s,
                [0.60 * inch, 0.92 * inch, 0.62 * inch, 1.70 * inch, 1.82 * inch, 1.14 * inch],
            ),
            Spacer(1, 6),
            note_cards(
                [
                    ("Reference", "Register the DF 500 fence on the same marked show face for both members; never flip a part.", BLUE, PALE_BLUE),
                    ("Frame", "10 mm cutter; 25 mm plunge in both members; first tight, followers medium.", TEAL, PALE_TEAL),
                    ("Web gates", "Frame rail to groove >=0.150; G to groove >=0.100; G between mortises >=0.220; receiver between mortises >=0.100.", OAK_DARK, PALE),
                ],
                s,
            ),
        ]
    if page_number == 43:
        rows = [
            ["Fitted-slab control", "Confirmed / shop input", "Calculation / transfer", "Acceptance"],
            ["Width", "24-in clear jamb; 1/8 each side", "24 - 1/8 - 1/8 = 23-3/4", "Maximum rectangle; even reveals"],
            ["Height", "81-in clear jamb; 1/8 head; 3/8 bottom", "81 - 1/8 - 3/8 = 80-1/2", "Head and bottom clearances pass"],
            ["Prefit rectangle", "Cured assembly 23-7/8 x 80-5/8", "Scribe from final top and hinge datums", "1/16 removable stock per edge"],
            ["Hinge edge", "Jamb plumb/twist", "Fit first; preserve reference face", "Full leaf bearing"],
            ["Lock edge", "Handing and swing", "Apply bevel inside 23-3/4 maximum width", "1/8 reveal through swing"],
        ]
        return [
            compact_table(
                rows,
                s,
                [1.30 * inch, 1.70 * inch, 2.50 * inch, 1.30 * inch],
            ),
            Spacer(1, 7),
            note_cards(
                [
                    ("Order", "Hinge edge, head, lock edge, then bottom.", BLUE, PALE_BLUE),
                    ("Allowance", "Remove no more than the controlled 1/16 inch per prefit edge.", TEAL, PALE_TEAL),
                    ("Redesign", "A larger change requires geometry revalidation.", OAK_DARK, PALE),
                ],
                s,
            ),
        ]
    if page_number == 53:
        moulding = read_csv(ROOT / "build" / "reports" / "moulding-cut-list.csv")
        rows = [["Part", "Production rough-length formula"]]
        for row in moulding:
            rows.append([row["Part identifier"], row["Rough length"]])
        return [
            compact_table(rows, s, [1.15 * inch, 5.65 * inch]),
            Spacer(1, 7),
            note_cards(
                [
                    ("Face A", "Use its own W, H-L, H-R, joint, cap, plinth, and floor datum.", BLUE, PALE_BLUE),
                    ("Face B", "Recalculate independently; do not copy Face A leg lengths.", TEAL, PALE_TEAL),
                    ("Transfer", "Final cuts come from installed work after each preceding layer is fitted.", OAK_DARK, PALE),
                ],
                s,
            ),
        ]
    if page_number == 54:
        rows = [
            ["Backband member", "Finished target", "Production rough length"],
            ["M-202A/B, mitered", "Fitted side-casing outside long + B", "Target + 2 inches"],
            ["M-202A/B, square", "Fitted square side-casing length + C", "Target + 2 inches"],
            ["M-202C head", "Fitted head-casing outside width + 2B", "Target + 2 inches"],
        ]
        return [
            compact_table(rows, s, [1.55 * inch, 2.75 * inch, 2.50 * inch]),
            Spacer(1, 7),
            note_cards(
                [
                    ("Do not copy", "Mitered and square side-band lengths are not interchangeable.", RED, colors.HexColor("#FAEFEC")),
                    ("Final transfer", "Fit the casing first; transfer every backband joint from installed work.", TEAL, PALE_TEAL),
                    ("Datums", "Use B = 1-1/8 and C = 4-1/2 only after profile samples pass.", OAK_DARK, PALE),
                ],
                s,
            ),
        ]
    if page_number == 64:
        checks = [
            ["Final release", "Pass / value", "Inspector"],
            ["Door size and reveals", "________________________", "____________"],
            ["Swing, latch, and strike", "________________________", "____________"],
            ["Panel movement", "________________________", "____________"],
            ["Stop contact", "________________________", "____________"],
            ["Casing / backband geometry", "________________________", "____________"],
            ["Finish sample match", "________________________", "____________"],
            ["Build record complete", "________________________", "____________"],
        ]
        return [
            compact_table(checks, s, [2.40 * inch, 2.95 * inch, 1.45 * inch]),
            Spacer(1, 6),
            note_cards(
                [
                    ("Release", "All gates closed; measurements and test-piece results retained.", BLUE, PALE_BLUE),
                    ("Record", "Installed slab, face formulas, finish sample, and hardware IDs entered.", TEAL, PALE_TEAL),
                    ("Maintenance", "Owner advised that floating panels must never be caulked or glued.", OAK_DARK, PALE),
                ],
                s,
            ),
        ]
    if page_number == 62:
        rows = [
            ["Step", "Installed condition", "Release before next step"],
            ["1", "Fitted and hardware-machined slab fully cured", "Finish, edges, and masked areas pass"],
            ["2", "Final brass hardware installed by hand", "Leaf, lock, screws, and faceplate pass"],
            ["3", "Slab rehung and cycled", "Full swing, signed clearances, latch, strike pass"],
            ["4", "Head stop fitted and lightly tacked", "Paper-shim contact test passes"],
            ["5", "Side stops fitted beneath head", "Quiet continuous contact passes"],
            ["6", "M-201 casing fitted and fastened", "Reveal, plumb, level, joints pass"],
            ["7", "M-202 and approved optional details fitted", "Projection, transitions, returns pass"],
            ["8", "Fill and sample-controlled touch-up complete", "Color, sheen, fasteners pass"],
            ["9", "Opening cleaned and cycled again", "Complete-system release signed"],
        ]
        return [
            compact_table(rows, s, [0.48 * inch, 3.06 * inch, 3.26 * inch])
        ]
    return []


def cover_page(s):
    return [
        Paragraph(
            f"DC-1916-001  /  INTEGRATED SHOP EDITION  /  {REVISION.upper()}",
            s["QKicker"],
        ),
        Paragraph("Cabinetmaker’s Door &amp;<br/>Millwork Builder’s Guide", s["QTitle"]),
        Paragraph(
            "Five-panel quarter-sawn white-oak interior door, concealed DF 500 joinery, "
            "completed-jamb fitting, and matching custom moulding.",
            s["QCoverDeck"],
        ),
        HRFlowable(width="100%", thickness=2.0, color=OAK, spaceBefore=2, spaceAfter=8),
        svg_figure(RENDERINGS / "01-complete-system.svg", 7.05 * inch),
        Spacer(1, 7),
        note_cards(
            [
                ("Door build", "13 wood parts, 12 joints, 30 final factory tenons, five floating panels.", BLUE, PALE_BLUE),
                ("Millwork build", "Stops, casing, backband, and only evidence-supported cap or plinth details.", TEAL, PALE_TEAL),
                ("Control rule", "Written dimensions and signed field values control every rendering.", OAK_DARK, PALE),
            ],
            s,
        ),
        Spacer(1, 4),
        Paragraph(
            "<b>SCOPE GATE:</b> The existing completed jamb is not fabricated. Before cutting, identify the "
            f"opening, handing, swing, trim-face count, physical hardware, builder, date, and {REVISION} traveler.",
            s["QMicro"],
        ),
    ]


def upsert_markdown_section(text: str, heading: str, body: str) -> str:
    section = f"\n## {heading}\n\n{body.strip()}\n"
    pattern = re.compile(
        rf"\n## {re.escape(heading)}\n.*?(?=\n## |\Z)",
        re.S,
    )
    if pattern.search(text):
        return pattern.sub(section.rstrip(), text).rstrip() + "\n"
    return text.rstrip() + section


def update_build_notes():
    report = RELEASE / "DC-1916-001_Build_Report.md"
    if report.exists():
        text = report.read_text()
        text = upsert_markdown_section(
            text,
            "Integrated cabinetmaker guide",
            """
- Cabinetmaker’s builder guide: 64 pages
- Twenty-seven dimension-controlled isometric, exploded, setup, and orthographic renderings, each issued as SVG and PNG
- Door fabrication, completed-jamb fitting, hardware, custom moulding, finish, and final release are one gated workflow.
""",
        )
        report.write_text(text)

    visual_qc = ROOT / "build" / "reports" / "visual-qc.md"
    if visual_qc.exists():
        text = visual_qc.read_text()
        text = upsert_markdown_section(
            text,
            "Integrated cabinetmaker guide",
            """
- Guide: 64 pages; render program: 27 matched SVG/PNG scenes.
- Every PDF page and every rendering must be inspected after the final build; written dimensions control.
""",
        )
        visual_qc.write_text(text)


def build():
    generate_3d()
    generate_clarity_maps()
    RELEASE.mkdir(exist_ok=True)
    text = SOURCE.read_text()
    sections = source_pages(text)
    assert len(sections) == 64, f"Expected 64 numbered source sections, got {len(sections)}"
    assert set(sections) == set(range(1, 65)), "Source page numbers must be exactly 1 through 64"
    assert len(PAGES) == 64

    for _, _, _, asset, _ in PAGES:
        if asset:
            assert rel(asset).exists(), f"Missing guide asset: {asset}"
    used_render_slugs = {
        Path(asset).stem for _, _, _, asset, _ in PAGES if asset and "cabinetmakers-guide/renderings/" in asset
    }
    assert set(RENDER_SLUGS) <= used_render_slugs, "Every registered 3D rendering must be used"

    s = styles()
    doc = make_doc()
    story = []
    page_frames = []
    for page_number, (kicker, title, deck, asset, width) in enumerate(PAGES, start=1):
        if page_number == 1:
            page_content = cover_page(s)
        else:
            page_content = []
            page_heading(page_content, s, f"{kicker} | {page_number:02d}", title, deck)
            if asset:
                page_content.extend(
                    [
                        figure_asset(rel(asset), width * inch),
                        Spacer(1, 5),
                    ]
                )
            special = schedule_blocks(page_number, s)
            if special:
                page_content.extend(special)
                source_lines = sections[page_number]
                if page_number in {11, 12, 14, 16, 17, 23, 25, 36, 42, 43}:
                    # The schedule and note cards above carry the detailed production data.
                    # Retain the source's disposition rules without duplicating the entire
                    # long-form narrative at an unreadably reduced scale.
                    source_lines = [
                        line
                        for line in source_lines
                        if line.strip().startswith(("**Inspection:**", "**Accept:**", "**STOP:**", "**REMAKE:**"))
                    ]
                source_flow = parse_markdown(source_lines, s, include_tables=False)
                page_content.extend(source_flow)
            else:
                page_content.extend(parse_markdown(sections[page_number], s))
        page_frame = KeepInFrame(
            6.82 * inch,
            9.62 * inch,
            page_content,
            mode="shrink",
            mergeSpace=True,
        )
        page_frames.append(page_frame)
        story.append(page_frame)
        if page_number != len(PAGES):
            story.append(PageBreak())

    doc.build(story)
    shrink_scales = [getattr(frame, "_scale", 1.0) for frame in page_frames]
    oversize_pages = [
        (index + 1, scale)
        for index, scale in enumerate(shrink_scales)
        if scale > 1.08
    ]
    assert max(shrink_scales) <= 1.08, (
        f"Page content shrank below the 92.5% readability floor: "
        + ", ".join(
            f"page {page}, scale divisor {scale:.3f}"
            for page, scale in oversize_pages
        )
    )
    reader = PdfReader(str(OUT))
    extracted = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert len(reader.pages) == 64, f"Expected 64 pages, got {len(reader.pages)}"
    required = [
        "D-101A",
        "D-101G",
        "J-11",
        "J-12",
        "M-201",
        "M-202C",
        "M-203",
        "both tight",
        "0–6-1/8",
        "9-1/8–15-1/4",
        "1.250",
        "7/16",
        "0.150",
        "0.100",
        "0.220",
        "published open time",
        "lock envelope",
        "25 percent",
        "tongue",
        "24 x 81",
        "23-7/8 x 80-5/8",
        "23-3/4 x 80-1/2",
        "3/8 at bottom",
        "finished fitted slab",
        "dado",
        "default moulding",
        "completed jamb",
        "field release",
        "final release",
        "LS-05",
        "RL-02",
        "5/16 + 7/8 + 5/16",
        "1/4 + 7/8 + 1/4",
        "0.200",
    ]
    extracted_lower = extracted.lower()
    for term in required:
        assert term.lower() in extracted_lower, f"Missing required guide term: {term}"
    assert not re.search(r"\b(TODO|TBD|placeholder|lorem ipsum)\b", extracted, re.I)

    shutil.copy2(SOURCE, RELEASE / SOURCE.name)
    update_build_notes()
    print(f"PASS: built {OUT.name} ({len(reader.pages)} pages, {len(RENDER_SLUGS)} 3D scenes)")


if __name__ == "__main__":
    build()
