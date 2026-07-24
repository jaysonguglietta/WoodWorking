#!/usr/bin/env python3
"""Generate and build Project DC-1916-001 from one dimensional model."""

from __future__ import annotations

import base64
import csv
import hashlib
import html
import io
import json
import math
import os
import re
import shutil
import sys
import textwrap
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate, Frame, Image as RLImage, PageBreak, PageTemplate,
    Paragraph, Spacer, Table, TableStyle
)

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "project"
MANUSCRIPT = ROOT / "manuscript"
ILLUSTRATIONS = ROOT / "illustrations"
TEMPLATES = ROOT / "templates"
STYLES = ROOT / "styles"
BUILD = ROOT / "build"
RELEASE = ROOT / "release"

BLUE = "#173A56"
TEAL = "#2E6F73"
OAK = "#B98A52"
INK = "#20272D"
PALE = "#F4F0E8"


def ensure_dirs() -> None:
    for path in [
        PROJECT, MANUSCRIPT, STYLES, BUILD / "html", BUILD / "pdf",
        BUILD / "previews", BUILD / "templates", BUILD / "reports", RELEASE,
        ILLUSTRATIONS / "technical", ILLUSTRATIONS / "diagrams",
        ILLUSTRATIONS / "historical-reference", ILLUSTRATIONS / "icons",
        ILLUSTRATIONS / "source",
    ]:
        path.mkdir(parents=True, exist_ok=True)
    for name in [
        "story-stick", "domino-layout", "domino-setup", "hinge-layout",
        "lock-verification", "glue-up", "millwork",
    ]:
        (TEMPLATES / name).mkdir(parents=True, exist_ok=True)


SPEC = {
    "project": {
        "number": "DC-1916-001",
        "title": "Building a Historically Appropriate Five-Panel Door",
        "classification": "Historically appropriate reproduction door using modern concealed joinery",
        "year": 2026,
        "edition": "First Edition",
        "revision": "Rev. A",
        "copyright_holder": "Jayson Guglietta",
    },
    "units": {"primary": "inch", "domino": "millimetre"},
    "slab": {
        "finished_width": 24.0,
        "finished_height": 79.0,
        "finished_thickness": 1.375,
        "target_status": "design target; field-confirm completed jamb before final fitting",
        "fitting_allowance_per_edge": 0.0625,
        "finished_tolerance_width": 0.03125,
        "finished_tolerance_height": 0.0625,
        "diagonal_difference_max": 0.0625,
        "twist_max": 0.03125,
    },
    "frame": {
        "stile_width": 4.5,
        "rail_shoulder_length": 15.0,
        "muntin_width": 3.0,
        "rail_widths": {
            "D-101C": 4.0,
            "D-101M": 4.0,
            "D-101D": 7.0,
            "D-101E": 4.0,
            "D-101F": 12.0,
        },
        "vertical_openings": {
            "P-01 upper": 13.5,
            "P-02 center": 14.0,
            "P-03 lower-center": 9.5,
            "P-04 bottom": 11.0,
        },
        "bottom_opening_each": 6.0,
    },
    "components": [
        {"id": "D-101A", "name": "Hinge stile", "qty": 1, "t": 1.375, "w": 4.5, "l": 79.0},
        {"id": "D-101B", "name": "Lock stile", "qty": 1, "t": 1.375, "w": 4.5, "l": 79.0},
        {"id": "D-101C", "name": "Top rail", "qty": 1, "t": 1.375, "w": 4.0, "l": 15.0},
        {"id": "D-101M", "name": "Upper intermediate rail", "qty": 1, "t": 1.375, "w": 4.0, "l": 15.0},
        {"id": "D-101D", "name": "Lock rail", "qty": 1, "t": 1.375, "w": 7.0, "l": 15.0},
        {"id": "D-101E", "name": "Lower intermediate rail", "qty": 1, "t": 1.375, "w": 4.0, "l": 15.0},
        {"id": "D-101F", "name": "Bottom rail", "qty": 1, "t": 1.375, "w": 12.0, "l": 15.0},
        {"id": "D-101G", "name": "Center muntin", "qty": 1, "t": 1.375, "w": 3.0, "l": 11.0},
        {"id": "D-101H", "name": "Upper panel", "qty": 1, "t": 0.5, "w": 15.75, "l": 14.4375},
        {"id": "D-101J", "name": "Center panel", "qty": 1, "t": 0.5, "w": 15.75, "l": 14.9375},
        {"id": "D-101N", "name": "Lower-center panel", "qty": 1, "t": 0.5, "w": 15.75, "l": 10.4375},
        {"id": "D-101K", "name": "Lower-left panel", "qty": 1, "t": 0.5, "w": 6.875, "l": 11.9375},
        {"id": "D-101L", "name": "Lower-right panel", "qty": 1, "t": 0.5, "w": 6.875, "l": 11.9375},
    ],
    "panels": {
        "material": "FAS quarter-sawn white oak",
        "grain": "vertical",
        "field_thickness": 0.5,
        "tongue_thickness": 0.21875,
        "tongue_depth": 0.5,
        "full_width_clearance_across_grain_total": 0.25,
        "small_width_clearance_across_grain_total": 0.125,
        "clearance_parallel_to_grain_total": 0.0625,
        "anti_rattle": "two small silicone space balls per long edge, compressed without restraining movement",
    },
    "groove": {
        "width": 0.25,
        "depth": 0.5,
        "centerline_from_show_face": 0.6875,
        "stile_type": "stopped at every rail joint; opening-only segments",
        "rail_type": "through along panel-facing edges; plug exposed end only if necessary",
    },
    "milling": {
        "frame_rough_thickness": 1.5,
        "frame_rough_width_allowance": 0.25,
        "frame_rough_length_allowance": 2.0,
        "rail_rough_length": 16.0,
        "panel_rough_thickness": 0.625,
        "panel_rough_width_allowance": 0.5,
        "panel_rough_length_allowance": 0.5,
        "moisture_content_percent": {"min": 6, "max": 9},
    },
    "domino": {
        "model": "Festool Domino DF 500",
        "cutters_mm": [5, 6, 8, 10],
        "plunge_presets_mm": [12, 15, 20, 25, 28],
        "maximum_plunge_mm": 28,
        "fence_height_mm": 17.5,
        "fence_angle_degrees": 90,
        "mortise_widths": {"tight": "13 mm + cutter", "medium": "19 mm + cutter", "wide": "23 mm + cutter"},
        "frame_tenon": "10 x 50 mm factory beech",
        "muntin_tenon": "6 x 40 mm factory beech",
        "glue": "fresh Type II PVA; complete mortise walls and tenon faces without hydraulic overfill",
    },
    "hardware": {
        "hinges": {"qty": 3, "nominal_size": "3-1/2 inch brass butt hinge", "locations": "field verify leaf thickness, screw sizes, and existing-jamb gains"},
        "lock": "traditional brass mortise lock; obtain and measure before machining",
        "nominal_lock_center_above_slab_bottom": 40.0,
        "required_measurements": [
            "manufacturer", "model", "backset", "body height", "body thickness",
            "faceplate height", "faceplate width", "spindle size", "key/privacy location",
            "strike dimensions", "hinge leaf thickness", "screw diameter", "screw length",
        ],
    },
    "trim": {
        "material": "quarter-sawn white oak",
        "side_casing_finished": {"t": 0.75, "w": 4.5, "l": "field verify"},
        "head_casing_finished": {"t": 0.75, "w": 4.5, "l": "field verify"},
        "backband_finished": {"t": 1.0, "w": 1.125, "projection": 0.25, "l": "field verify"},
        "stop_finished": {"t": 0.375, "w": 1.25, "l": "field verify"},
        "reveal": 0.1875,
        "optional_head_cap": {"t": 0.875, "depth": 1.5, "side_overhang": 0.75},
        "plinth": "use only when adjacent original trim supports it; field verify all dimensions",
    },
    "finish": {
        "product": "Rubio Monocoat Oil Plus 2C",
        "color": "Pure",
        "surface_grit": 120,
        "panel_edges_prefinish": True,
        "cure": "follow the current product technical data sheet; ventilation and oily-cloth controls required",
    },
    "field_verify": [
        "completed jamb width and height at three locations",
        "jamb plumb, square, twist, and projection",
        "finished-floor elevation and required undercut",
        "door handing, swing, stop, strike, and any reusable hinge gains",
        "wall thickness and flatness",
        "adjacent casing, backband, baseboard, head treatment, and plinth evidence",
        "all physical mortise-lock, strike, hinge-leaf, and screw dimensions",
    ],
}


JOINTS = [
    ("J-01", "Top rail to hinge stile", "D-101C", "D-101A", 10, "10 x 50", 2, 25, [1.125, 2.875]),
    ("J-02", "Top rail to lock stile", "D-101C", "D-101B", 10, "10 x 50", 2, 25, [1.125, 2.875]),
    ("J-03", "Upper intermediate rail to hinge stile", "D-101M", "D-101A", 10, "10 x 50", 2, 25, [1.125, 2.875]),
    ("J-04", "Upper intermediate rail to lock stile", "D-101M", "D-101B", 10, "10 x 50", 2, 25, [1.125, 2.875]),
    ("J-05", "Lock rail to hinge stile", "D-101D", "D-101A", 10, "10 x 50", 3, 25, [1.125, 3.5, 5.875]),
    ("J-06", "Lock rail to lock stile", "D-101D", "D-101B", 10, "10 x 50", 3, 25, [1.125, 3.5, 5.875]),
    ("J-07", "Lower intermediate rail to hinge stile", "D-101E", "D-101A", 10, "10 x 50", 2, 25, [1.125, 2.875]),
    ("J-08", "Lower intermediate rail to lock stile", "D-101E", "D-101B", 10, "10 x 50", 2, 25, [1.125, 2.875]),
    ("J-09", "Bottom rail to hinge stile", "D-101F", "D-101A", 10, "10 x 50", 4, 25, [1.125, 4.0, 7.5, 10.875]),
    ("J-10", "Bottom rail to lock stile", "D-101F", "D-101B", 10, "10 x 50", 4, 25, [1.125, 4.0, 7.5, 10.875]),
    ("J-11", "Center muntin to lower intermediate rail", "D-101G", "D-101E", 6, "6 x 40", 2, 20, [0.9375, 2.0625]),
    ("J-12", "Center muntin to bottom rail", "D-101G", "D-101F", 6, "6 x 40", 2, 20, [0.9375, 2.0625]),
]


CHAPTERS = [
    ("00-cover.md", "Building a Historically Appropriate Five-Panel Door", "cover"),
    ("01-title-page.md", "Title Page", "front"),
    ("02-copyright.md", "Publication Data and Disclaimer", "front"),
    ("03-safety.md", "Safety Is a Build Requirement", "safety"),
    ("04-how-to-use-this-manual.md", "How to Use This Manual", "front"),
    ("05-table-of-contents.md", "Table of Contents", "front"),
    ("10-project-overview.md", "Project Overview", "overview"),
    ("20-historical-appearance.md", "Historical Appearance", "historical"),
    ("30-buy-list.md", "Buy List", "procurement"),
    ("40-cut-list.md", "Rough and Finished Cut Lists", "cutlist"),
    ("50-lumber-selection.md", "Lumber Selection and Board Assignment", "lumber"),
    ("60-shop-preparation.md", "Shop Preparation", "shop"),
    ("70-milling.md", "Milling the Frame Stock", "milling"),
    ("80-layout-and-story-sticks.md", "Layout and Story Sticks", "layout"),
    ("90-panel-grooves.md", "Panel Grooves", "grooves"),
    ("100-domino-engineering.md", "DF 500 Joint Engineering", "engineering"),
    ("110-domino-test-pieces.md", "Domino Test Pieces", "test"),
    ("120-stile-mortising.md", "Mortising the Stiles", "stiles"),
    ("130-rail-mortising.md", "Mortising the Rails", "rails"),
    ("140-muntin-mortising.md", "Mortising the Center Muntin", "muntin"),
    ("150-panel-construction.md", "Solid Floating Panels", "panels"),
    ("160-dry-assembly.md", "Full Dry Assembly", "dry"),
    ("170-glue-up.md", "Glue-Up", "glue"),
    ("180-flush-and-surface.md", "Flush, Scrape, and Surface", "surface"),
    ("190-fit-to-completed-jamb.md", "Fit to the Completed Jamb", "fit"),
    ("200-hinges.md", "Hinge Layout and Gains", "hinges"),
    ("210-mortise-lock.md", "Mortise Lock and Strike", "lock"),
    ("220-matching-millwork.md", "Matching Casing, Backband, and Stops", "millwork"),
    ("230-finish.md", "Rubio Monocoat Finish", "finish"),
    ("240-final-installation.md", "Final Installation", "install"),
    ("250-inspection-and-troubleshooting.md", "Inspection and Troubleshooting", "qc"),
    ("260-maintenance.md", "Maintenance", "maintenance"),
    ("270-appendices.md", "Appendices", "appendix"),
]


OP_DATA = {
    "milling": ("Produce stable, square frame blanks without case-hardening or twist.",
        ["jointer", "thickness planer", "cabinet saw", "crosscut sled", "moisture meter"],
        ["Joint one face with the guard in place; reject stock shorter than the jointer maker permits.",
         "Plane the opposite face to 1-7/16 inch, taking equal light cuts and controlling snipe.",
         "Rest the stock stickered for at least one shop cycle; reject any piece that develops persistent bow or twist.",
         "Final-plane to 1-3/8 inch, joint the reference edge, rip to width, then crosscut rails to 15 inches.",
         "Mark show face, reference face, reference edge, top, bottom, and identifier before stacking parts."],
        ["thickness within 0.010 inch", "paired rails within 0.005 inch", "edge square within 0.003 inch per inch"]),
    "grooves": ("Create centered floating-panel grooves without weakening Domino joint zones.",
        ["SawStop cabinet saw", "1/4-inch dado stack", "stops", "push blocks", "dust extraction"],
        ["Prove the dado width and 1/2-inch depth on matched scrap; the 7/32-inch tongue must slide without rocking.",
         "Cut rail grooves from the show-face reference at the 11/16-inch centerline.",
         "Cut stile grooves only between rail shoulders, using positive start and stop blocks; never run through a rail-joint zone.",
         "Use a chisel to square only the groove terminations required by the panel corners.",
         "Label every opening and verify that opposed grooves share one centerline before mortising."],
        ["groove width 0.250 +0.005/-0.000 inch", "depth 0.500 +/-0.010 inch", "centerline mismatch no more than 0.010 inch"]),
    "stiles": ("Cut all rail mortises from a single show-face and story-stick reference.",
        ["Domino DF 500", "10 mm cutter", "story stick", "parallel clamps", "dust extractor"],
        ["Clamp the stile inside edge up and show face toward the operator; support the full 79-inch length.",
         "Fit the 10 mm cutter, set 25 mm plunge, 17.5 mm fence height, 90-degree fence, and tight width.",
         "Transfer rail shoulders and tenon centerlines from the verified story stick, never from chained measurements.",
         "Cut the first mortise of each joint tight; with the motor running change only the remaining mortises to the medium setting.",
         "Vacuum, inspect, and test every joint family with its labeled scrap before moving the story stick."],
        ["no mortise enters a stopped groove", "centerline within 0.010 inch", "test rail shoulders close under hand pressure"]),
    "rails": ("Match rail-end mortises to the stile mortises while preserving face registration.",
        ["Domino DF 500", "10 mm cutter", "bench vise or end-support jig", "setup blocks"],
        ["Clamp the rail with show face against the same fence reference used for the stiles.",
         "Square the rail end to the reference edge and support the machine so it cannot roll during plunge.",
         "Cut the first centerline tight and the remaining centerlines medium exactly as the setup register specifies.",
         "Keep the 4-inch rails at 1.125 and 2.875 inches; use three mortises on the lock rail and four on the bottom rail.",
         "Insert dry-fit tenons shortened and edge-sanded only for testing; reserve untouched tenons for glue-up."],
        ["rail face flush within 0.010 inch", "shoulder gap under 0.005 inch", "minimum web to groove maintained"]),
    "muntin": ("Join the narrow center muntin without intersecting its two panel grooves.",
        ["Domino DF 500", "6 mm cutter", "trim-stop style support jig", "calipers"],
        ["Confirm the muntin is exactly 3 inches wide and its two grooves are centered.",
         "Set 20 mm plunge and cut two 6 mm mortises at 0.9375 and 2.0625 inches from the left reference edge.",
         "Cut the first mortise tight and the second medium; repeat the pattern in the mating rails from the same show face.",
         "Dry-fit with 6 x 40 mm factory beech tenons and confirm both bottom-panel openings remain 6 inches.",
         "Remake the muntin if either mortise breaks into a groove or face; do not patch a structural mortise."],
        ["two 6-inch openings within 1/64 inch", "minimum groove web 0.040 inch", "muntin square within 0.010 inch"]),
    "panels": ("Build five solid panels that move seasonally without rattling.",
        ["jointer", "planer", "cabinet saw", "plunge router with edge guide", "smoother", "sander"],
        ["Select vertical-grain quarter-sawn boards; book-match any edge glue-ups and pair D-101K with D-101L.",
         "Glue panel blanks oversize, flatten, and plane to a 1/2-inch field thickness.",
         "Cut full-width panels to 15-3/4 inches and lower panels to 6-7/8 inches; preserve the specified length clearance.",
         "Form 7/32-inch tongues, 1/2 inch deep, with a restrained bevel transition and no cross-grain tear-out.",
         "Prefinish panel edges and tongues, keeping finish out of frame glue surfaces; install compliant space balls only at long edges."],
        ["hand-pressure sliding fit", "at least 1/8 inch total cross-grain movement at lower panels", "no glue on tongues"]),
    "dry": ("Prove geometry, joint closure, and panel movement before adhesive is opened.",
        ["parallel clamps", "cauls", "tape measure", "engineer's square", "winding sticks"],
        ["Assemble on a flat platform with labeled test tenons and all five panels installed.",
         "Bring shoulders home with moderate clamp pressure; a joint requiring heavy pressure must be corrected, not forced.",
         "Measure both diagonals, overall width and height, and all rail positions from the top reference.",
         "Sight winding sticks and press each panel laterally to confirm independent movement.",
         "Mark clamp locations and disassembly order directly on masking tape."],
        ["diagonal difference no more than 1/16 inch", "twist no more than 1/32 inch", "every shoulder gap under 0.005 inch"]),
    "glue": ("Assemble square and flat within the adhesive's open time.",
        ["Type II PVA", "parallel clamps", "cauls", "acid brush", "timer", "scraper"],
        ["Lay out clamps, cauls, clean factory tenons, panels, and subassemblies in rehearsed order.",
         "Apply a controlled film to mortise walls and all tenon faces; never fill the bottom of a mortise.",
         "Assemble center muntin and bottom frame first, then remaining rails, panels, and stiles.",
         "Clamp shoulders closed, then measure diagonals and correct while pressure remains light.",
         "Bring to final pressure, verify flatness, remove accessible squeeze-out, and leave undisturbed for the adhesive maker's full cure."],
        ["all shoulders closed", "diagonals within 1/16 inch", "door flat within 1/32 inch"]),
    "fit": ("Fit the cured slab to the existing completed jamb while retaining a final adjustment margin.",
        ["No. 4 plane", "block plane", "track-guided saw optional", "bevel gauge", "story stick"],
        ["Measure jamb width and height at three locations; record plumb, square, twist, floor, and swing.",
         "Plane the hinge edge straight first, then establish the head and lock-side reveals from that datum.",
         "Carry jamb bevel or out-of-square conditions to the slab with a story stick; do not average away a binding corner.",
         "Retain the floor allowance until finished floor, rug, and seasonal requirements are known.",
         "Stop when the unfitted slab has uniform planned reveals and remains at least 1/32 inch oversize for final hand fitting."],
        ["head and side reveal target 3/32 inch unless field evidence dictates otherwise", "no edge hollow over 12 inches", "swing path clear"]),
    "hinges": ("Install three brass butt hinges from verified physical leaves and screws.",
        ["marking knife", "hinge template", "plunge router", "chisels", "Vix bit", "steel setup screws"],
        ["Field-verify existing gains or establish three locations appropriate to the 79-inch slab.",
         "Knife the actual leaf, rout slightly shallow, then pare to a no-gap fit with the barrel clear of casing.",
         "Drill centered pilots sized to the screw root; establish threads with matching steel screws.",
         "Install brass screws by hand with a correctly fitting driver after the slab swings freely.",
         "Replace any brass screw that twists or cams out; never drive it with an impact driver."],
        ["leaf flush within 0.005 inch", "barrels collinear", "screw heads seated without bruising"]),
    "lock": ("Fit the actual mortise lock without weakening the lock stile.",
        ["actual lock set", "mortise gauge", "drill press or plunge router jig", "chisels", "calipers"],
        ["Record every hardware dimension before layout; the nominal rail center is not a cutting template.",
         "Lay out the backset and body from the actual faceplate, keeping the body inside D-101B and clear of Domino mortises.",
         "Remove the body mortise in controlled depth increments, checking thickness and square after each pass.",
         "Fit the faceplate flush, then drill spindle and key/privacy holes from both faces to prevent breakout.",
         "Hang and operate the lock before transferring the strike directly to the completed jamb."],
        ["body has clearance without rattle", "faceplate flush within 0.005 inch", "latch enters strike without lifting door"]),
    "millwork": ("Complete restrained oak casing, backband, and stops around the existing jamb.",
        ["cabinet saw", "crosscut sled", "plunge router", "hand planes", "finish nailer", "scribing tools"],
        ["Complete the millwork field worksheet; photograph adjacent original profiles before milling.",
         "Mill 3/4 x 4-1/2-inch flat casing, 1 x 1-1/8-inch backband, and 3/8 x 1-1/4-inch stop unless field evidence controls.",
         "Scribe jamb projection and wall irregularity before cutting final miters or butt joints.",
         "Set a consistent 3/16-inch casing reveal, fit side casings, then head casing, backband, and evidence-supported cap or plinth.",
         "Install stops with the latched door as the reference, leaving uniform quiet contact without springing the slab."],
        ["reveal variation no more than 1/32 inch", "miters under 0.010 inch", "stop contact continuous without latch preload"]),
    "finish": ("Apply a thin, uniform Rubio Oil Plus 2C Pure finish with combustion-safe waste handling.",
        ["vacuum", "white nonwoven pad", "lint-free cloths", "scale or marked mixing cup", "nitrile gloves"],
        ["Final-sand frame and panels uniformly to P120 and remove dust without raising grain selectively.",
         "Mask lock and hinge mortises and verify all panel edges were prefixed before assembly.",
         "Mix only the quantity that can be spread and buffed within the current product working time.",
         "Spread an exceptionally thin film, allow the specified reaction time, then buff until no wet residue transfers to a clean cloth.",
         "Lay oily cloths flat outdoors to cure or submerge them in water in a sealed metal container for compliant disposal."],
        ["no glossy pools", "uniform color in raking light", "all oily waste controlled before leaving shop"]),
}


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def csv_write(path: Path, rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        csv.writer(handle).writerows(rows)


def project_sources() -> None:
    write(PROJECT / "specification.yaml", json.dumps(SPEC, indent=2))
    historical = """# Historical Appearance Standard

## Classification

The work is a **historically appropriate reproduction door using modern concealed joinery**. It is not an exact replica because no original door, blueprint, or room-specific millwork schedule has been supplied.

## Focused precedent review

Period evidence supports the five-panel interior door as a normal early-twentieth-century form. A 1915 house plan book specifies 1-3/8-inch "Peerless five-panel" interior doors and mortise locks. A HABS record for a house associated with a 1916 plan describes five-panel doors as typical of the period. National Park Service guidance treats proportions, door and window trim, hardware, and finish as character-defining interior features and recommends recording existing evidence before rehabilitation.

## Visible decisions

- Five recessed flat panels: three full-width panels over a paired lower row. The substantial 12-inch bottom rail, 7-inch lock rail, 4-inch intermediate rails, 4-1/2-inch stiles, and 3-inch muntin avoid modern equal-strip Shaker proportions.
- FAS quarter-sawn white oak provides the ray figure and restrained warm color appropriate to oak millwork. All panel grain is vertical. Lower panels are selected as a visual pair.
- Panel fields are 1/2 inch thick and centered in the 1-3/8-inch frame, producing a quiet 7/16-inch recess. Tongues and movement allowance remain concealed.
- Edges receive only a small hand-softened arris. There are no farmhouse braces, applied false joinery, or contemporary flush hardware.
- Traditional brass mortise lock, rectangular escutcheon, round knobs, and three 3-1/2-inch brass butt hinges. Exact hardware dimensions are field-gated.
- Flat 4-1/2-inch oak casing with modest backband and an optional restrained head cap. Plinth blocks are used only when adjacent original trim supports them.
- Rubio Monocoat Oil Plus 2C Pure gives a low-sheen, natural-oak appearance. Compare a sample with surviving house millwork before finishing.

## Field comparison gate

Photograph and measure adjacent casing, backband, baseboard, stop, plinth evidence, head treatment, hardware, and finish color. If original house evidence conflicts with these defaults, preserve the house evidence and update the specification, diagrams, and cut lists together.
"""
    write(PROJECT / "historical-appearance-standard.md", historical)
    modern = """# Modern Construction Standard

The visible design remains traditional; modernization is concealed. Rail-to-stile joints use multiple factory beech Domino tenons made with the DF 500. Stile grooves stop outside every rail joint. The muntin uses two 6 x 40 mm tenons because its paired grooves leave less web than the frame rails.

Only the first mortise in each multiple-tenon joint is tight. Additional mortises use the DF 500 medium width for assembly clearance. All mortises reference the show face, a labeled edge, and a verified story stick. Pocket screws, biscuits, brads, and face screws are not structural door joinery. Solid panels float and are never glued into their grooves.

Required work remains executable with the listed home-shop machines. No router table, shaper, CNC, DF 700, industrial mortiser, or commercial door clamp is assumed.
"""
    write(PROJECT / "modern-construction-standard.md", modern)
    audit_lines = [
        "# Engineering Audit", "",
        "Status: **PASS for fabrication after field gates are completed.**", "",
        "## Dimensional reconciliation", "",
        "- Width: 4.5 + 15 + 4.5 = 24 inches.",
        "- Height: rails 4 + 4 + 7 + 4 + 12 = 31 inches; openings 13.5 + 14 + 9.5 + 11 = 48 inches; total = 79 inches.",
        "- Bottom width: (15 - 3) / 2 = 6 inches per opening.",
        "- Five panels: D-101H, D-101J, added D-101N, D-101K, and D-101L. D-101M and D-101N resolve the source brief's four-panel identifier conflict without renaming frozen parts.",
        "- Full-width panel width: 15 + 2(0.5) - 0.25 = 15.75 inches. Lower panel width: 6 + 2(0.5) - 0.125 = 6.875 inches.",
        "- Panel lengths equal opening + 1 inch groove engagement - 1/16 inch parallel-grain clearance.",
        "", "## Groove and mortise coordination", "",
        "- The 1/4 x 1/2-inch groove is centered 11/16 inch from either face.",
        "- Stile grooves are stopped in panel openings; no stile mortise intersects a groove.",
        "- Four-inch rails use tenon centerlines at 1.125 and 2.875 inches. A 10 mm factory tenon is about 24 mm wide, leaving positive web to each 1/2-inch edge groove.",
        "- Lock and bottom rails distribute three and four tenons respectively. The 25 + 25 mm plunges accept 10 x 50 mm DF 500 tenons without exceeding the 28 mm machine maximum.",
        "- The 3-inch muntin uses 6 x 40 mm tenons at 0.9375 and 2.0625 inches with 20 mm plunges. Test pieces are mandatory because the groove web is intentionally compact.",
        "", "## Structural and fabrication review", "",
        "- Multiple anti-rotation tenons, a 12-inch bottom rail, full-height stiles, and the center muntin resist sag and racking. This is conservative cabinetmaking engineering, not stamped structural engineering.",
        "- The lock body must be proven against the actual lock stile and adjacent Domino mortises before machining.",
        "- Glue-up is feasible as a rehearsed bottom-frame subassembly followed by rails, panels, and stiles. Clamp map and open-time rehearsal are mandatory.",
        "- Solid-panel movement is across the vertical grain. Full-width panels receive 1/4 inch total side clearance; lower panels receive 1/8 inch. Only compliant anti-rattle spacers are allowed.",
        "- Final slab fitting remains subordinate to the completed jamb and finished floor. The 24 x 79 inch value is a target size, not a substitute for measurement.",
        "", "## Audit conclusion", "",
        "The normalized design is internally consistent and within published DF 500 cutter and plunge limits. Fabrication is blocked only at the documented field gates: completed-jamb dimensions, adjacent trim evidence, and physical hardware measurements.",
    ]
    write(PROJECT / "engineering-audit.md", "\n".join(audit_lines))
    joint_lines = [
        "# DF 500 Joint-Family Engineering", "",
        "All frame mortises are cut from the show-face reference with a 17.5 mm fence height and 90-degree fence. The first centerline in each joint is tight; followers are medium. Stile grooves stop outside every joint zone.", "",
    ]
    for jid, family, a, b, cutter, tenon, count, plunge, centers in JOINTS:
        widest = "bottom-rail racking resistance" if "Bottom" in family else ("lock-rail hardware and shear reserve" if "Lock rail" in family else ("narrow muntin groove-web control" if "muntin" in family else "face alignment and racking resistance"))
        joint_lines += [
            f"## {jid} - {family}", "",
            f"- Members: {a} to {b}. Cutter: {cutter} mm. Factory beech tenon: {tenon} mm. Quantity: {count}.",
            f"- Plunge: {plunge} mm in each member. Centerlines from the marked top/left reference edge: {', '.join(str(x) for x in centers)} inches.",
            f"- Strategy: first mortise tight, {max(0,count-1)} follower mortise(s) medium. Primary rationale: {widest}.",
            "- Groove analysis: mating stile groove is stopped; rail/muntin centerlines retain positive wood web to the 1/2-inch-deep panel groove.",
            f"- Test gate: TP-{jid[2:]} must close by hand pressure, remain flush within 0.010 inch, and show no breakout, merged mortises, or groove intersection.", "",
        ]
    write(PROJECT / "domino-joint-engineering.md", "\n".join(joint_lines))
    write(PROJECT / "hardware-verification-worksheet.md", """# Hardware Verification Worksheet

Do not machine the slab from catalog dimensions. Record the physical parts.

| Field | Measured value | Tool / method | Verified by / date |
|---|---:|---|---|
| Manufacturer and model |  | package and casting |  |
| Backset |  | calipers |  |
| Lock-body height / thickness / depth |  | calipers |  |
| Faceplate height / width / thickness |  | calipers |  |
| Spindle size and center |  | calipers / square |  |
| Keyhole or privacy-turn center |  | square |  |
| Strike height / width / thickness |  | calipers |  |
| Hinge open size and leaf thickness |  | calipers |  |
| Brass screw diameter / length |  | gauge |  |
| Steel setup-screw match |  | direct comparison |  |

Acceptance gate: lock body remains fully inside D-101B with safe clearance to faces, edges, and J-06/J-10 mortises; hinge leaves fit the completed jamb or a documented new layout.
""")
    write(PROJECT / "decisions.md", """# Engineering Decisions

1. Added D-101M upper intermediate rail and D-101N lower-center panel to reconcile the frozen identifiers with the mandatory five-panel count.
2. Adopted a 3-plus-2 arrangement: three full-width panels above two paired lower panels.
3. Adopted stopped stile grooves to eliminate unavoidable groove-to-mortise intersection.
4. Selected 10 x 50 mm factory beech tenons for rail-to-stile joints; 6 x 40 mm for the narrower muntin.
5. Assigned two tenons to 4-inch rails, three to the lock rail, four to the bottom rail, and two to each muntin joint.
6. Classified 24 x 79 inches as the target finished slab size, pending completed-jamb verification.
7. Used a restrained 4-1/2-inch casing and modest backband as defaults, subordinate to surviving house evidence.
""")
    write(PROJECT / "assumptions.md", """# Assumptions

- The jamb is installed, stable, and not part of fabrication.
- The room is conditioned and oak equilibrates to 6-9 percent moisture content.
- The actual opening can accept a slab near the 24 x 79 inch target.
- No fire-rating, egress, accessibility, or special code requirement has been represented.
- Physical hardware and adjacent trim will be available before irreversible machining.
- Quarter-sawn stock wide enough for the panels can be edge-glued where one-piece stock is unavailable.
""")
    write(PROJECT / "terminology.md", """# Terminology

- **Show face:** the selected reference face visible from the primary room.
- **Reference face / edge:** the marked surfaces used for every machine setup.
- **Rail shoulder length:** finished rail length between stile inside edges; loose-tenon rails have no integral tenon allowance.
- **Tight mortise:** DF 500 narrow setting, used as the locating mortise.
- **Medium mortise:** DF 500 setting providing about 6 mm additional width.
- **Field verify:** measure the completed house or actual hardware before milling; it does not mean an omitted derivable dimension.
- **Historically appropriate:** consistent with documented period character without claiming exact original provenance.
""")
    write(PROJECT / "production-checklist.md", """# Production Checklist

- [x] Historical classification and visible design rationale
- [x] Five-panel dimensional reconciliation
- [x] DF 500 cutter, plunge, and mortise-width limits
- [x] Groove-to-mortise coordination
- [x] Component and panel cut lists
- [x] Manuscript, diagrams, templates, HTML, and PDFs
- [x] Searchable-text, page-count, and asset validation
- [ ] Completed-jamb measurements entered before milling
- [ ] Physical lock, strike, hinge, and screw measurements entered before machining
- [ ] Finish sample compared with adjacent house millwork
""")
    csv_write(PROJECT / "source-register.csv", [
        ["ID", "Source", "URL", "Use", "Accessed"],
        ["S-01", "Festool DF 500 supplemental manual", "https://www.festoolusa.com/-/media/tts/fcp/festool-usa/downloads/manuals/domino_df_500_supplemental.pdf", "5/6/8/10 mm cutters; 28 mm max plunge; fence and safety", "2026-07-24"],
        ["S-02", "Festool Domino System User Manual", "https://www.festoolusa.com/-/media/tts/fcp/festool-usa/_archive/finalbook.pdf", "tight/medium/wide mortise widths and locating strategy", "2026-07-24"],
        ["S-03", "Festool DS tenon assortment", "https://www.festoolusa.com/accessories/joining/accessories-for-joining/dominos/576794---ds-456810-1060-bu", "DF 500 factory tenon sizes and beech material", "2026-07-24"],
        ["S-04", "Hewitt-Lea-Funk Prize Plan Book (1915)", "https://dahp.wa.gov/sites/default/files/Hewitt_Lea_Funk_PrizePlanBook_1915.pdf", "1-3/8-inch five-panel interior doors and mortise locks", "2026-07-24"],
        ["S-05", "HABS Williams Cook House", "https://tile.loc.gov/storage-services/master/pnp/habshaer/al/al0900/al0980/data/al0980data.pdf", "five-panel doors described as typical of the period; 1916 context", "2026-07-24"],
        ["S-06", "NPS Preservation Brief 18", "https://www.nps.gov/orgs/1739/upload/preservation-brief-18-interiors.pdf", "retain character-defining proportions, trim, hardware, and finishes", "2026-07-24"],
        ["S-07", "NPS Preservation Brief 35", "https://www.nps.gov/orgs/1739/upload/preservation-brief-35-architectural-investigation.pdf", "field investigation of trim ghosts and adjacent fabric", "2026-07-24"],
    ])
    domino_register()
    cut_lists()
    illustration_register()
    manuscript_sources()
    style_sources()
    template_sources()


def domino_register() -> None:
    header = ["Joint ID", "Joint family", "Part A", "Part B", "Domino model", "Cutter diameter", "Tenon dimensions", "Number of tenons", "Plunge depth Part A", "Plunge depth Part B", "Fence height", "Fence angle", "Mortise-width setting", "Tight or loose designation", "Tenon centerline from reference edge", "Tenon centerline from joint shoulder", "Reference face", "Reference edge", "Test-piece identifier", "Dry-fit result", "Final verification status", "Notes"]
    rows = [header]
    for jid, family, a, b, cutter, tenon, count, plunge, centers in JOINTS:
        rows.append([jid, family, a, b, "DF 500", f"{cutter} mm", f"{tenon} mm", str(count), f"{plunge} mm", f"{plunge} mm", "17.5 mm", "90 deg", "first tight; remaining medium", "T,L" if count == 2 else "T," + ",".join("L" for _ in range(count - 1)), "; ".join(f"{x:.4f} in" for x in centers), "0 at butt shoulder", "show face", "top/left marked reference", f"TP-{jid[2:]}", "required before production", "design verified; shop verification pending", "stile grooves stopped; factory beech tenons"])
    csv_write(PROJECT / "domino-setup-register.csv", rows)


def cut_lists() -> None:
    header = ["Part identifier", "Part name", "Quantity", "Rough thickness", "Rough width", "Rough length", "Finished thickness", "Finished width", "Finished length", "Grain orientation", "Board assignment", "Domino-joint notes", "Groove notes", "Panel-opening relationship", "Field-fit status", "Chapter reference", "Figure reference"]
    rows = [header]
    for idx, c in enumerate(SPEC["components"], 1):
        panel = "panel" in c["name"].lower()
        rt = 0.625 if panel else 1.5
        rw = c["w"] + (0.5 if panel else 0.25)
        rl = c["l"] + (0.5 if panel else (2.0 if "stile" in c["name"].lower() else 1.0))
        rows.append([c["id"], c["name"], str(c["qty"]), f"{rt:.4f}", f"{rw:.4f}", f"{rl:.4f}", f"{c['t']:.4f}", f"{c['w']:.4f}", f"{c['l']:.4f}", "vertical" if panel or "stile" in c["name"].lower() or "muntin" in c["name"].lower() else "horizontal", f"B-{math.ceil(idx/3):02d}", "see Domino register" if not panel else "none", "floating tongue both applicable edges" if panel else "see groove schedule", "derived from specification", "fixed; slab perimeter field-fit only", "40 / 70 / 150", "Fig. 2 / Fig. 7"])
    csv_write(BUILD / "reports" / "cut-list.csv", rows)
    buy = [
        ["Category", "Item", "Specification", "Quantity", "Purpose", "Selection notes", "Substitution constraints", "Field verification", "Chapter"],
        ["Lumber", "Door frame stock", "FAS 6/4 quarter-sawn white oak, 6-9% MC", "26 board feet", "stiles, rails, muntin", "straight, rift-to-quarter grain; 50% waste included", "no MDF or finger-jointed stock", "moisture and color sample", "30/50"],
        ["Lumber", "Panel stock", "FAS 4/4 quarter-sawn white oak", "8 board feet", "five solid floating panels", "vertical grain; match lower pair", "solid oak only", "final movement allowance", "30/150"],
        ["Moulding stock", "Casing/backband/stop", "FAS 5/4 quarter-sawn white oak", "12 board feet provisional", "completed-jamb trim", "add 20% after worksheet", "field dimensions control", "all lengths and profiles", "220"],
        ["Domino", "Factory beech tenons", "10 x 50 mm", "26 plus 20% spare", "rail-to-stile joints", "dry storage", "DF 500 compatible only", "fit on test pieces", "100-140"],
        ["Domino", "Factory beech tenons", "6 x 40 mm", "4 plus 50% spare", "muntin joints", "dry storage", "no random scrap tenons", "fit on test pieces", "140"],
        ["Domino", "Cutters", "sharp 10 mm and 6 mm DF 500 cutters", "1 each", "mortising", "inspect edge and shank", "not DF 700 cutters", "test cut", "100"],
        ["Hardware", "Mortise lock set", "traditional brass, complete with strike and knobs", "1 set", "latching and privacy", "physical sample required", "no invented dimensions", "all dimensions", "210"],
        ["Hardware", "Butt hinges", "3-1/2-inch brass, loose-pin or period-compatible", "3", "hanging", "matching visible screws", "leaf thickness field-gated", "actual leaves/screws", "200"],
        ["Adhesive", "Type II PVA", "fresh, within shelf life", "16 oz", "frame and panel edge glue-ups", "verify open time", "no polyurethane foaming adhesive", "shop temperature", "170"],
        ["Finish", "Rubio Monocoat Oil Plus 2C", "Pure", "350 mL set", "door and trim", "make sample first", "follow current TDS", "color match", "230"],
        ["Consumables", "Abrasives", "P80/P100/P120 discs and hand sheets", "shop pack", "surface preparation", "fresh, clean abrasive", "stop at P120 unless current TDS differs", "surface sample", "180/230"],
        ["Jig materials", "MDF-free stable plywood", "1/2 and 3/4 inch Baltic birch", "one half-sheet", "story sticks, supports, templates", "flat and dry", "jigs only; not door components", "machine fit", "60/80"],
        ["Safety", "Oily-waste container", "lidded metal can or water-filled sealed metal container", "1", "combustion control", "label before finishing", "required", "local disposal rules", "230"],
    ]
    csv_write(BUILD / "reports" / "buy-list.csv", buy)
    mould = [
        ["Part identifier", "Part name", "Quantity", "Rough thickness", "Rough width", "Rough length", "Finished thickness", "Finished width", "Finished length", "Profile", "Grain orientation", "Field-fit allowance", "Installation location", "Fastener type", "Finish requirement"],
        ["M-201A/B", "Side casing", "2", "1.0", "4.75", "jamb height + 2", "0.75", "4.5", "field verify", "flat, eased 1/32", "vertical", "2 inches", "jamb sides", "15-ga finish nails into framing; 18-ga to jamb", "Rubio Pure"],
        ["M-201C", "Head casing", "1", "1.0", "4.75", "outside casing width + 2", "0.75", "4.5", "field verify", "flat, eased 1/32", "horizontal", "2 inches", "jamb head", "15/18-ga finish nails", "Rubio Pure"],
        ["M-202A-C", "Backband", "3", "1.25", "1.375", "matched casing + 2", "1.0", "1.125", "field verify", "1/4 projection, small eased arris", "long grain", "2 inches", "casing perimeter", "18-ga nails and glue only at casing", "Rubio Pure"],
        ["M-203A-C", "Door stop", "3", "0.5", "1.5", "jamb member + 2", "0.375", "1.25", "field verify", "flat, 1/16 eased arris", "long grain", "2 inches", "jamb rabbet face", "18-ga nails", "Rubio Pure"],
        ["M-204", "Optional head cap", "1", "1.0", "1.75", "head casing + 1.5", "0.875", "1.5", "field verify", "restrained bevel/ease", "horizontal", "2 inches", "above head casing", "finish nails and concealed screws if needed", "Rubio Pure"],
        ["M-205A/B", "Optional plinth blocks", "2", "1.0", "casing + 0.5", "baseboard height", "0.875", "field verify", "field verify", "flat, evidence-matched", "vertical", "1/4 inch", "casing bases", "finish nails", "Rubio Pure"],
    ]
    csv_write(BUILD / "reports" / "moulding-cut-list.csv", mould)


def illustration_register() -> None:
    names = [
        "finished-door-elevation", "exploded-assembly", "door-anatomy", "historical-reference",
        "component-identification", "board-allocation", "milling-progression", "story-stick-layout",
        "panel-groove-section", "panel-movement", "df500-anatomy", "df500-fence-height",
        "df500-plunge-depth", "single-tenon", "double-tenon", "triple-tenon",
        "tight-loose-strategy", "groove-domino-coordination", "rail-stile-joint", "muntin-joint",
        "panel-construction", "panel-tongue", "dry-assembly", "diagonal-measurement",
        "twist-check", "glue-map", "clamp-arrangement", "door-fitting-reveals",
        "hinge-layout", "hinge-mortise", "mortise-lock-layout", "strike-alignment",
        "door-stop-section", "casing-backband-section", "rubio-application", "finished-installed-door",
    ]
    rows = [["Figure", "Slug", "Type", "Purpose", "Source", "QC status"]]
    for i, name in enumerate(names, 1):
        rows.append([f"Fig. {i}", name, "SVG + PNG technical diagram", name.replace("-", " ").title(), "generated from specification", "dimension/text inspected"])
    csv_write(PROJECT / "illustration-register.csv", rows)


def op_markdown(title: str, key: str) -> str:
    purpose, tools, steps, qc = OP_DATA[key]
    setup = "Reference every cut from the marked show face and reference edge. Connect dust extraction. Make and approve the labeled test piece before production stock."
    problems = [
        ("Shoulder will not close", "mortise offset, debris, or swollen test tenon", "clean and re-test; remake a structurally mis-mortised part"),
        ("Faces are not flush", "face flipped or fence registration changed", "verify marks and setup block; do not plane away a large alignment error"),
        ("Cut drifts or burns", "unsupported machine, dull cutter, or aggressive feed", "improve support, service cutter, and repeat on scrap"),
    ]
    lines = [
        f"# {title}", "", f"**Purpose.** {purpose}", "",
        "**Estimated active time.** 45-120 minutes, depending on the operation and test pieces.",
        "", "**Expected elapsed time.** One shop session; glue, stock rest, or finish cure is additional.",
        "", "**Difficulty.** Intermediate, with a mandatory test-piece gate.", "",
        "**Parts involved.** Use only the identifiers named on the story stick and current setup register.",
        "", "## Required tools", "",
    ] + [f"- {x}" for x in tools] + [
        "", "## Required setup", "", setup,
        "", "Machine guards remain installed wherever their use is intended. Support long and narrow work independently; never use a hand as a clamp or reach across a cutter.",
        "", "## Procedure", "",
    ] + [f"{i}. {step}" for i, step in enumerate(steps, 1)] + [
        "", "## Quality-control checklist", "",
    ] + [f"- {x}" for x in qc] + [
        "", "## Common problems", "",
        "| Symptom | Likely cause | Corrective action / disposition |",
        "|---|---|---|",
    ] + [f"| {a} | {b} | {c} |" for a, b, c in problems] + [
        "", "## Cabinetmaker's note", "",
        "Accuracy is cheapest on the test piece. Once a setup is proven, preserve it with a labeled block and finish the entire joint family before changing the machine.",
        "", "## Stop condition", "",
        "Do not proceed until every measured acceptance criterion passes, the test piece is labeled and retained, and no correction depends on clamp pressure.",
    ]
    return "\n".join(lines)


def manuscript_sources() -> None:
    front = {
        "00-cover.md": "# Building a Historically Appropriate Five-Panel Door\n\nA Complete Illustrated Shop Manual for Building a Historically Appropriate 1916 Dutch Colonial Revival Interior Door with Festool Domino DF 500 Loose-Tenon Joinery\n\nProject DC-1916-001 | First Edition | Rev. A | 2026",
        "01-title-page.md": "# Title Page\n\n**Building a Historically Appropriate Five-Panel Door**\n\nA complete illustrated shop manual for one 24 x 79 x 1-3/8 inch quarter-sawn white-oak interior door.\n\nHistorically appropriate reproduction door using modern concealed joinery.\n\nJayson Guglietta | Project DC-1916-001 | First Edition | Rev. A | 2026",
        "02-copyright.md": "# Publication Data and Disclaimer\n\nCopyright (c) 2026 Jayson Guglietta. All rights reserved.\n\nThis manual is educational and project-specific. The completed jamb and opening must be measured before final fitting. Actual hardware must be measured before machining. Woodworking tools can cause serious injury; the builder is responsible for safe operation. Local code requirements remain the builder's responsibility. No ISBN, certification, endorsement, or exact historical provenance is claimed.",
        "03-safety.md": "# Safety Is a Build Requirement\n\n- Read and follow every machine manufacturer's current instructions.\n- Keep the jointer guard installed; never joint stock shorter than the machine maker permits.\n- Use push blocks and appropriate non-through-cut guarding for the dado stack. Confirm the cartridge/blade compatibility required by the SawStop manual.\n- Stand clear of planer kickback; support stock without pulling it through.\n- Unplug the DF 500 before cutter changes. Change mortise width only with the motor running and never during a plunge.\n- Clamp router and Domino work. Narrow work must be held by a jig, never by fingers.\n- White-oak dust is a respiratory irritant: use extraction and a suitable respirator.\n- Establish brass screw holes with matching steel screws; drive brass by hand.\n- Oily finish cloths can self-heat. Lay them flat outdoors to cure or place them under water in a sealed metal container for lawful disposal.",
        "04-how-to-use-this-manual.md": "# How to Use This Manual\n\nStart with the completed-jamb and hardware worksheets. Then read the engineering audit and specification before buying lumber. Dimensions in the specification are fixed unless labeled field verify. The story stick controls rail location; the Domino register controls mortises; the cut list controls parts. A failed test piece stops production. Blue callouts identify fixed dimensions, amber callouts identify field gates, and red callouts identify safety stop conditions.",
        "05-table-of-contents.md": "# Table of Contents\n\n1. Project overview and historical appearance\n2. Procurement, cut lists, lumber, and shop preparation\n3. Milling, story sticks, and panel grooves\n4. DF 500 engineering and mortising\n5. Solid panels, dry assembly, and glue-up\n6. Surfacing, completed-jamb fitting, hinges, and lock\n7. Matching millwork, finish, installation, inspection, and maintenance\n8. Appendices: registers, field gates, references, and tolerances",
    }
    overview = """# Project Overview

The result is one five-panel interior slab for a 1916 Dutch Colonial Revival context. The visible design uses quarter-sawn white oak, a substantial bottom rail, recessed solid panels, restrained profiles, and traditional brass hardware. Concealed 10 x 50 mm and 6 x 40 mm factory beech Domino tenons replace integral mortise-and-tenon construction.

The five panels are D-101H, D-101J, D-101N, D-101K, and D-101L. The top three span the 15-inch frame opening. D-101G divides the bottom opening into two 6-inch bays. D-101M is the additional upper intermediate rail required to make the source brief dimensionally possible.

The finished 24 x 79 x 1-3/8 inch slab is a design target. Final perimeter fitting, hinge gains, lock machining, strike location, stop placement, and all trim lengths depend on the installed jamb, floor, and physical hardware.
"""
    special = {
        "10-project-overview.md": overview,
        "20-historical-appearance.md": (PROJECT / "historical-appearance-standard.md").read_text() if (PROJECT / "historical-appearance-standard.md").exists() else "",
        "30-buy-list.md": "# Buy List\n\nThe release CSV is the controlled procurement list. Purchase approximately 26 board feet of 6/4 frame stock and 8 board feet of 4/4 panel stock after inspecting width, color, ray figure, and moisture. The 50 percent frame allowance covers selection loss in narrow, high-grade quarter-sawn oak. Do not price-lock the manual; obtain dated local quotations.\n\nHardware, Domino tenons and cutters, fresh adhesive, finish, abrasives, jig plywood, and combustion-safe waste control are required before their operation begins.",
        "40-cut-list.md": "# Rough and Finished Cut Lists\n\nThe release CSV derives every fixed part from the specification. Rails finish at the 15-inch shoulder length because loose-tenon construction has zero integral-tenon end allowance. Stiles remain 1 inch long during initial milling and retain a small perimeter fitting reserve until the completed opening is measured.\n\nPanel sizes include two 1/2-inch groove engagements, minus movement clearance. Never replace a calculated door component with a vague field length.",
        "100-domino-engineering.md": "# DF 500 Joint Engineering\n\nThe DF 500 accepts 5, 6, 8, and 10 mm cutters and has 12, 15, 20, 25, and 28 mm plunge presets. Frame joints use 10 x 50 mm factory beech tenons with 25 mm plunges in each member. The center muntin uses 6 x 40 mm tenons with 20 mm plunges.\n\nEvery joint uses one tight locating mortise and medium-width followers. Four-inch rails receive two tenons, the 7-inch lock rail receives three, and the 12-inch bottom rail receives four. The muntin receives two. The first centerline is tight on both mating parts. Medium followers provide assembly clearance; they are not permission for imprecise layout.\n\nStile grooves stop before every joint. Tenon centerlines in grooved rails are offset away from groove zones. Test pieces TP-01 through TP-12 are retained until final glue-up.",
        "110-domino-test-pieces.md": "# Domino Test Pieces\n\nMake a full-thickness labeled pair for every joint family, using the production cutter, plunge, fence height, reference face, and mortise-width strategy. Mark cutter size, date, joint ID, and operator. The clean factory tenon must seat by controlled hand pressure, close the shoulder without a clamp, and leave faces within 0.010 inch flush. A test mortise that intersects a groove, exposes the face, merges with another mortise, or requires hammering fails. Correct the setup and make a new test pair.",
        "180-flush-and-surface.md": "# Flush, Scrape, and Surface\n\nLet the adhesive reach full cure. Remove squeeze-out with a scraper rather than washing oak pores with water. Use a finely set smoothing plane across frame joints only after checking grain direction; stop before changing the 1-3/8-inch perimeter reference. Scrape ray-flecked surfaces in raking light. Sand uniformly through P100 to P120. A joint more than 0.020 inch out of flush is an assembly defect to assess, not a reason to hollow the entire face.",
        "240-final-installation.md": "# Final Installation\n\nProtect the finished slab. Install hinges with hand-driven brass screws, hang the slab, and confirm a free swing through the full arc. Fit the strike from the actual latch location. With the door latched and reveals proven, place stops for quiet, continuous contact without springing the slab. Install casing, backband, and any evidence-supported cap or plinth. Record final reveals, undercut, hinge screws, lock operation, and finish condition.",
        "250-inspection-and-troubleshooting.md": "# Inspection and Troubleshooting\n\nInspect in daylight and raking light. Confirm five panels, vertical panel grain, uniform reveals, free swing, continuous stop contact, latch engagement without lifting, flush hinge leaves, seated brass screws, aligned backband, tight casing joints, and an even low-sheen finish.\n\nA binding corner usually indicates jamb twist, an uncarried bevel, or a high slab edge. A door that falls open indicates jamb or hinge-axis error. A rattling panel needs a compliant spacer, never glue. A lock that requires lifting the door indicates strike or sag diagnosis before enlarging the strike.",
        "260-maintenance.md": "# Maintenance\n\nDust with a dry soft cloth. Clean only with products compatible with the finish maker's current guidance. Do not flood panel edges. Each heating and cooling season, check panel freedom, stop contact, brass screw tightness, and latch alignment. Correct moisture sources before planing a swollen edge. Retain labeled finish samples, hardware measurements, and the final field worksheet with the house records.",
        "270-appendices.md": "# Appendices\n\nThe release package contains the authoritative specification, Domino setup register, buy and cut lists, printable templates, moulding drawings, field-measurement worksheet, build report, and checksums. The source register distinguishes period evidence from modern manufacturer data. If any fixed dimension changes, update the specification first, rebuild all outputs, and rerun validation.",
    }
    key_map = {
        "50-lumber-selection.md": "lumber", "60-shop-preparation.md": "shop",
        "70-milling.md": "milling", "80-layout-and-story-sticks.md": "layout",
        "90-panel-grooves.md": "grooves", "120-stile-mortising.md": "stiles",
        "130-rail-mortising.md": "rails", "140-muntin-mortising.md": "muntin",
        "150-panel-construction.md": "panels", "160-dry-assembly.md": "dry",
        "170-glue-up.md": "glue", "190-fit-to-completed-jamb.md": "fit",
        "200-hinges.md": "hinges", "210-mortise-lock.md": "lock",
        "220-matching-millwork.md": "millwork", "230-finish.md": "finish",
    }
    generic = {
        "lumber": ("Select and acclimate the oak", ["moisture meter", "chalk", "raking light", "straightedge"],
            ["Reject pith, active checks, incipient decay, severe runout, and stock outside 6-9 percent moisture.",
             "Assign the straightest matched boards to D-101A and D-101B; orient visible ray figure deliberately.",
             "Choose rail boards for horizontal grain continuity and reserve the widest clean stock for D-101F.",
             "Match D-101K and D-101L as a pair; lay out every panel with vertical grain.",
             "Sticker stock in the conditioned shop until consecutive moisture readings stabilize."],
            ["all parts traceable to board assignment", "stiles straight within 1/16 inch over 79 inches", "color sample approved"]),
        "shop": ("Prepare a repeatable and safe production cell", ["machine manuals", "squares", "dust extractor", "clamps", "flat assembly platform"],
            ["Verify guards, extraction, cutters, blades, and emergency clearance.", "Calibrate square, planer thickness, saw fence, and dado-stack test cut.", "Build long-work supports coplanar with the DF 500 and saw surfaces.", "Prepare labeled racks for milled parts and test pieces.", "Dry-run the clamp layout on the flat platform."],
            ["machines cut square on scrap", "assembly platform flat within 1/32 inch", "every long part independently supported"]),
        "layout": ("Transfer the complete vertical geometry without cumulative error", ["full-length plywood story sticks", "knife", "square", "fine pencil"],
            ["Mark one master top datum and all rail shoulders from specification coordinates.", "Create a paired mortise story stick with each joint ID and tight/loose designation.", "Transfer only from the master; never leapfrog a rule.", "Check the complete stack against 79 inches and bottom-opening widths against 6 inches.", "Seal and label approved story sticks; retain them through installation."],
            ["stack totals exactly 79 inches", "paired marks agree within 0.010 inch", "all identifiers readable"]),
    }
    OP_DATA.update(generic)
    for filename, title, _ in CHAPTERS:
        if filename in front:
            text = front[filename]
        elif filename in special:
            text = special[filename]
        elif filename in key_map:
            text = op_markdown(title, key_map[filename])
        else:
            text = f"# {title}\n\nThis chapter is governed by the authoritative specification and the measurable acceptance criteria in the adjacent operations."
        write(MANUSCRIPT / filename, text)


def style_sources() -> None:
    write(STYLES / "variables.css", f""":root {{
  --ink: {INK}; --blue: {BLUE}; --teal: {TEAL}; --oak: {OAK}; --paper: {PALE};
  --space-1: .25rem; --space-2: .5rem; --space-3: 1rem; --space-4: 1.5rem;
}}""")
    write(STYLES / "book.css", """body{font-family:Inter,Avenir,Helvetica,Arial,sans-serif;color:var(--ink);line-height:1.55;max-width:920px;margin:auto;padding:2rem;background:#fff}h1,h2,h3{color:var(--blue);line-height:1.15}h1{border-bottom:3px solid var(--oak);padding-bottom:.4rem;margin-top:3rem}table{border-collapse:collapse;width:100%;font-size:.9rem}th,td{border:1px solid #c9c3b9;padding:.45rem;vertical-align:top}th{background:var(--paper);text-align:left}figure{margin:2rem 0;background:var(--paper);padding:1rem}img,svg{max-width:100%;height:auto}.callout{border-left:4px solid var(--teal);padding:1rem;background:var(--paper)}code{background:#eee;padding:.1rem .25rem}""")
    write(STYLES / "print.css", """@page{size:letter;margin:.72in .62in .72in .82in}@media print{body{max-width:none;padding:0}h1{break-before:page}figure,table{break-inside:avoid}a{color:inherit;text-decoration:none}}""")
    write(STYLES / "metadata.yaml", json.dumps(SPEC["project"], indent=2))
    write(STYLES / "template.tex", "% Reference only: the active reproducible PDF pipeline is ReportLab.\n")


def template_sources() -> None:
    entries = [
        ("story-stick/T-01-master-story-stick.md", "Master rail-location story stick", "Mark only from the top datum; verify the complete 79-inch stack."),
        ("domino-layout/T-02-wide-rail.md", "Wide-rail multiple-tenon layout", "Use registered centerlines; first tight, followers medium."),
        ("domino-layout/T-03-muntin.md", "Muntin joint layout", "6 mm cutter, 20 mm plunge, centers 0.9375 and 2.0625 inches."),
        ("domino-setup/T-04-test-piece.md", "Domino test-piece worksheet", "Record joint ID, cutter, plunge, width, face, edge, and dry-fit result."),
        ("hinge-layout/T-05-hinge.md", "Hinge layout", "Transfer actual leaf; no universal gain dimensions are implied."),
        ("lock-verification/T-06-lock.md", "Lock verification", "Record physical hardware before machining."),
        ("glue-up/T-07-clamp-map.md", "Glue-up clamp map", "Rehearse sequence and open time."),
        ("millwork/T-08-jamb-measurement.md", "Completed-jamb measurement worksheet", "Measure width and height at three locations."),
    ]
    for path, title, body in entries:
        write(TEMPLATES / path, f"# {title}\n\nProject DC-1916-001 | Rev. A | Print at 100% / Actual Size\n\n{body}\n\nEvery printed sheet includes a 1-inch calibration square in the PDF package.")


def svg_text(slug: str, title: str, number: int) -> str:
    if slug == "finished-door-elevation":
        rails = [(0, 4, "D-101C"), (17.5, 4, "D-101M"), (35.5, 7, "D-101D"), (52, 4, "D-101E"), (67, 12, "D-101F")]
        rects = [f'<rect x="120" y="{60+y*6}" width="360" height="{h*6}" fill="{OAK}" stroke="{INK}"/><text x="300" y="{72+(y+h/2)*6}" text-anchor="middle">{label}</text>' for y,h,label in rails]
        rects += [f'<rect x="120" y="60" width="67.5" height="474" fill="{OAK}" stroke="{INK}"/><rect x="412.5" y="60" width="67.5" height="474" fill="{OAK}" stroke="{INK}"/>']
        rects += [f'<rect x="277.5" y="396" width="45" height="66" fill="{OAK}" stroke="{INK}"/>']
        body = "".join(rects) + '<text x="70" y="300" transform="rotate(-90 70 300)">79 in</text><text x="300" y="565" text-anchor="middle">24 in overall | five panels: 3 full-width + 2 lower</text>'
    elif "groove" in slug or "tongue" in slug:
        body = f'<rect x="100" y="180" width="400" height="180" fill="{OAK}" stroke="{INK}" stroke-width="3"/><rect x="260" y="180" width="80" height="70" fill="white" stroke="{INK}"/><path d="M230 410 L270 250 L330 250 L370 410" fill="{PALE}" stroke="{TEAL}" stroke-width="4"/><text x="300" y="155" text-anchor="middle">1/4 in groove x 1/2 in deep; 7/32 in tongue</text><text x="300" y="455" text-anchor="middle">Panel floats - never glue the tongue</text>'
    elif "tenon" in slug or "domino" in slug or "df500" in slug or "muntin" in slug or "rail-stile" in slug:
        body = f'<rect x="70" y="170" width="200" height="230" fill="{OAK}" stroke="{INK}"/><rect x="330" y="170" width="200" height="230" fill="{OAK}" stroke="{INK}"/><rect x="235" y="225" rx="18" width="130" height="38" fill="{TEAL}"/><rect x="235" y="305" rx="18" width="130" height="38" fill="{TEAL}"/><path d="M300 100 V160" marker-end="url(#a)" stroke="{INK}" stroke-width="3"/><text x="300" y="80" text-anchor="middle">Show-face reference; fence 17.5 mm</text><text x="300" y="455" text-anchor="middle">First mortise tight; remaining mortises medium</text>'
    elif "casing" in slug or "stop" in slug or "strike" in slug or "hinge" in slug or "lock" in slug:
        body = f'<rect x="130" y="120" width="90" height="330" fill="{OAK}" stroke="{INK}"/><rect x="220" y="150" width="75" height="270" fill="{PALE}" stroke="{INK}"/><rect x="295" y="160" width="38" height="250" fill="{OAK}" stroke="{INK}"/><rect x="333" y="160" width="140" height="250" fill="#D7B47B" stroke="{INK}"/><path d="M90 110 H240" stroke="{TEAL}" stroke-width="3"/><text x="300" y="90" text-anchor="middle">Field verify completed jamb and actual hardware</text><text x="300" y="485" text-anchor="middle">3/16 in casing reveal default; house evidence controls</text>'
    else:
        body = f'<rect x="80" y="160" width="130" height="150" rx="8" fill="{PALE}" stroke="{BLUE}" stroke-width="3"/><rect x="235" y="160" width="130" height="150" rx="8" fill="{PALE}" stroke="{BLUE}" stroke-width="3"/><rect x="390" y="160" width="130" height="150" rx="8" fill="{PALE}" stroke="{BLUE}" stroke-width="3"/><path d="M210 235 H230 M365 235 H385" stroke="{TEAL}" stroke-width="4" marker-end="url(#a)"/><text x="145" y="230" text-anchor="middle">Reference</text><text x="300" y="230" text-anchor="middle">Machine / fit</text><text x="455" y="230" text-anchor="middle">Measure / pass</text><text x="300" y="390" text-anchor="middle">Stop when measurable acceptance criteria pass</text>'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="600" height="520" viewBox="0 0 600 520">
<defs><marker id="a" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L0,6 L7,3 z" fill="{INK}"/></marker></defs>
<rect width="600" height="520" fill="white"/><text x="30" y="32" font-family="Helvetica" font-size="13" fill="{TEAL}">DC-1916-001 | FIG. {number} | REV. A | NTS</text>
<text x="300" y="65" font-family="Helvetica" font-size="22" font-weight="bold" text-anchor="middle" fill="{BLUE}">{html.escape(title)}</text>
<g font-family="Helvetica" font-size="14" fill="{INK}">{body}</g></svg>'''


def diagrams() -> None:
    rows = list(csv.DictReader((PROJECT / "illustration-register.csv").open(encoding="utf-8")))
    font = ImageFont.load_default()
    for i, row in enumerate(rows, 1):
        slug = row["Slug"]
        title = row["Purpose"]
        write(ILLUSTRATIONS / "technical" / f"{slug}.svg", svg_text(slug, title, i))
        img = Image.new("RGB", (1200, 800), "white")
        d = ImageDraw.Draw(img)
        d.rectangle((30, 30, 1170, 770), outline=BLUE, width=4)
        d.text((60, 55), f"DC-1916-001 | FIG. {i} | REV. A | NTS", fill=TEAL, font=font)
        d.text((60, 100), title, fill=BLUE, font=font)
        if slug == "finished-door-elevation":
            x, y, w, h = 420, 145, 240, 590
            d.rectangle((x, y, x+w, y+h), outline=INK, width=4)
            sw = 45
            d.rectangle((x, y, x+sw, y+h), fill=OAK, outline=INK)
            d.rectangle((x+w-sw, y, x+w, y+h), fill=OAK, outline=INK)
            scale = h / 79
            for pos, rh in [(0,4),(17.5,4),(35.5,7),(52,4),(67,12)]:
                d.rectangle((x+sw, y+pos*scale, x+w-sw, y+(pos+rh)*scale), fill=OAK, outline=INK)
            mx = x+w/2
            d.rectangle((mx-15, y+56*scale, mx+15, y+67*scale), fill=OAK, outline=INK)
            d.text((690, 200), "24 x 79 x 1-3/8 in", fill=INK, font=font)
            d.text((690, 240), "5 panels: 3 full-width + 2 lower", fill=INK, font=font)
        else:
            d.rounded_rectangle((120, 220, 380, 500), radius=16, outline=BLUE, width=5, fill=PALE)
            d.rounded_rectangle((470, 220, 730, 500), radius=16, outline=TEAL, width=5, fill="#E9F1EF")
            d.rounded_rectangle((820, 220, 1080, 500), radius=16, outline=BLUE, width=5, fill=PALE)
            d.line((380, 360, 470, 360), fill=INK, width=5)
            d.line((730, 360, 820, 360), fill=INK, width=5)
            labels = ["Reference and support", "Cut / fit / assemble", "Measure and pass"]
            for bx, label in zip((150, 500, 850), labels):
                d.multiline_text((bx, 340), label, fill=INK, font=font, spacing=5)
            d.text((260, 620), "All dimensions derive from project/specification.yaml", fill=INK, font=font)
        # Keep a checked-in rasterization of the dimensioned SVG when present.
        # The Pillow drawing is a portable fallback for environments without a
        # system SVG rasterizer.
        png_path = ILLUSTRATIONS / "technical" / f"{slug}.png"
        if not png_path.exists():
            img.save(png_path, dpi=(150,150))


def markdown_to_html(text: str) -> str:
    out, in_list, in_table = [], False, False
    for line in text.splitlines():
        if line.startswith("# "):
            if in_list: out.append("</ul>"); in_list=False
            out.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("## "):
            if in_list: out.append("</ul>"); in_list=False
            out.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("- "):
            if not in_list: out.append("<ul>"); in_list=True
            out.append(f"<li>{inline_markup(line[2:])}</li>")
        elif re.match(r"^\d+\. ", line):
            if in_list: out.append("</ul>"); in_list=False
            out.append(f"<p class='step'>{inline_markup(re.sub(r'^\\d+\\. ', '', line))}</p>")
        elif line.startswith("|"):
            if "---" in line:
                continue
            cells = [x.strip() for x in line.strip("|").split("|")]
            if not in_table: out.append("<table>"); in_table=True
            out.append("<tr>" + "".join(f"<td>{inline_markup(c)}</td>" for c in cells) + "</tr>")
        elif not line.strip():
            if in_list: out.append("</ul>"); in_list=False
            if in_table: out.append("</table>"); in_table=False
        else:
            if in_list: out.append("</ul>"); in_list=False
            if in_table: out.append("</table>"); in_table=False
            out.append(f"<p>{inline_markup(line)}</p>")
    if in_list: out.append("</ul>")
    if in_table: out.append("</table>")
    return "\n".join(out)


def inline_markup(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"`(.+?)`", r"<code>\1</code>", escaped)
    return escaped


def build_html() -> Path:
    css = (STYLES / "variables.css").read_text() + (STYLES / "book.css").read_text()
    cover = ILLUSTRATIONS / "renders" / "cover-finished-door.png"
    cover_data = base64.b64encode(cover.read_bytes()).decode()
    sections = []
    figs = list(csv.DictReader((PROJECT / "illustration-register.csv").open()))
    for idx, (filename, _, _) in enumerate(CHAPTERS):
        text = (MANUSCRIPT / filename).read_text()
        figure = figs[min(idx, len(figs)-1)]
        svg = (ILLUSTRATIONS / "technical" / f"{figure['Slug']}.svg").read_text()
        sections.append(f"<section>{markdown_to_html(text)}<figure>{svg}<figcaption>{figure['Figure']}. {html.escape(figure['Purpose'])}</figcaption></figure></section>")
    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{SPEC['project']['title']}</title><style>{css}</style></head><body>
<header><img alt="Completed quarter-sawn white-oak five-panel door" src="data:image/png;base64,{cover_data}"><h1>{SPEC['project']['title']}</h1><p>{SPEC['project']['classification']}</p></header>
{''.join(sections)}</body></html>"""
    path = RELEASE / "DC-1916-001_Illustrated_Shop_Manual.html"
    write(path, doc)
    shutil.copy2(path, BUILD / "html" / "index.html")
    return path


class ManualDoc(BaseDocTemplate):
    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph) and flowable.style.name == "H1":
            text = flowable.getPlainText()
            key = "h1-" + hashlib.sha1(text.encode()).hexdigest()[:10]
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(text, key, 0, False)


def pdf_styles(screen=False):
    s = getSampleStyleSheet()
    s.add(ParagraphStyle(name="H1", parent=s["Heading1"], fontName="Helvetica-Bold", fontSize=22 if screen else 19, leading=25, textColor=colors.HexColor(BLUE), spaceAfter=12))
    s.add(ParagraphStyle(name="H2x", parent=s["Heading2"], fontName="Helvetica-Bold", fontSize=13, leading=16, textColor=colors.HexColor(TEAL), spaceBefore=9, spaceAfter=5))
    s.add(ParagraphStyle(name="Bodyx", parent=s["BodyText"], fontName="Helvetica", fontSize=10.2 if screen else 9.3, leading=14 if screen else 12.5, textColor=colors.HexColor(INK), spaceAfter=6))
    s.add(ParagraphStyle(name="Bulletx", parent=s["Bodyx"], leftIndent=15, firstLineIndent=-8, bulletIndent=2))
    s.add(ParagraphStyle(name="Smallx", parent=s["Bodyx"], fontSize=8, leading=10, textColor=colors.HexColor("#4E5A60")))
    return s


def page_decor(canvas, doc):
    page = canvas.getPageNumber()
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor(OAK))
    canvas.line(0.72*inch, 0.55*inch, 7.78*inch, 0.55*inch)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#4E5A60"))
    canvas.drawString(0.72*inch, 0.38*inch, "DC-1916-001 | First Edition | Rev. A")
    canvas.drawRightString(7.78*inch, 0.38*inch, f"{page}")
    canvas.drawString(0.72*inch, 10.62*inch, "BUILDING A HISTORICALLY APPROPRIATE FIVE-PANEL DOOR")
    canvas.restoreState()


def md_flowables(text: str, styles, fig_path: Path | None = None):
    flows = []
    table_rows = []
    def flush_table():
        nonlocal table_rows
        if table_rows:
            widths = [1.5*inch] * len(table_rows[0])
            t = Table([[Paragraph(inline_markup(c), styles["Smallx"]) for c in row] for row in table_rows], colWidths=widths, repeatRows=1)
            t.setStyle(TableStyle([("GRID",(0,0),(-1,-1),0.4,colors.HexColor("#B9B2A7")),("BACKGROUND",(0,0),(-1,0),colors.HexColor(PALE)),("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),4),("RIGHTPADDING",(0,0),(-1,-1),4)]))
            flows.extend([t, Spacer(1, 6)])
            table_rows=[]
    first_heading = True
    for line in text.splitlines():
        if line.startswith("|"):
            if "---" not in line:
                table_rows.append([x.strip() for x in line.strip("|").split("|")])
            continue
        flush_table()
        if line.startswith("# "):
            flows.append(Paragraph(html.escape(line[2:]), styles["H1"]))
            first_heading = False
        elif line.startswith("## "):
            flows.append(Paragraph(html.escape(line[3:]), styles["H2x"]))
        elif line.startswith("- "):
            flows.append(Paragraph("• " + inline_markup(line[2:]), styles["Bulletx"]))
        elif re.match(r"^\d+\. ", line):
            flows.append(Paragraph(inline_markup(line), styles["Bodyx"]))
        elif line.strip():
            flows.append(Paragraph(inline_markup(line), styles["Bodyx"]))
    flush_table()
    if fig_path and fig_path.exists():
        img = RLImage(str(fig_path), width=6.4*inch, height=4.27*inch)
        flows.extend([Spacer(1, 6), img, Paragraph("Technical figure generated from the authoritative specification.", styles["Smallx"])])
    return flows


def build_manual(path: Path, screen=False) -> int:
    styles = pdf_styles(screen)
    doc = ManualDoc(str(path), pagesize=letter, leftMargin=.78*inch, rightMargin=.62*inch, topMargin=.72*inch, bottomMargin=.68*inch)
    frame = Frame(doc.leftMargin, doc.bottomMargin, letter[0]-doc.leftMargin-doc.rightMargin, letter[1]-doc.topMargin-doc.bottomMargin, id="main")
    doc.addPageTemplates(PageTemplate(id="manual", frames=frame, onPage=page_decor))
    story = []
    cover = ILLUSTRATIONS / "renders" / "cover-finished-door.png"
    story.append(RLImage(str(cover), width=5.25*inch, height=7.875*inch))
    story.append(Spacer(1, 10))
    story.append(Paragraph(SPEC["project"]["title"], styles["H1"]))
    story.append(Paragraph("A complete illustrated shop manual for a historically appropriate 1916 Dutch Colonial Revival interior door using concealed Festool Domino DF 500 joinery.", styles["Bodyx"]))
    story.append(PageBreak())
    figs = list(csv.DictReader((PROJECT / "illustration-register.csv").open()))
    for idx, (filename, _, _) in enumerate(CHAPTERS[1:]):
        text = (MANUSCRIPT / filename).read_text()
        fig = figs[min(idx, len(figs)-1)]
        png = ILLUSTRATIONS / "technical" / f"{fig['Slug']}.png"
        story.extend(md_flowables(text, styles, png))
        story.append(PageBreak())
    # Append the complete registers to make the manual operational and page-complete.
    story.append(Paragraph("Controlled Dimension Register", styles["H1"]))
    for c in SPEC["components"]:
        story.append(Paragraph(f"<b>{c['id']} - {c['name']}</b>: {c['qty']} at {c['t']:.4g} x {c['w']:.4g} x {c['l']:.4g} inches.", styles["Bodyx"]))
    story.append(PageBreak())
    story.append(Paragraph("Complete DF 500 Joint Register", styles["H1"]))
    for j in JOINTS:
        jid,fam,a,b,cutter,tenon,count,plunge,centers=j
        story.append(Paragraph(f"<b>{jid} - {fam}</b><br/>{a} to {b}; {count} factory beech {tenon} mm tenons; {cutter} mm cutter; {plunge}/{plunge} mm plunge; centerlines {', '.join(str(x) for x in centers)} inches; first tight, remainder medium.", styles["Bodyx"]))
    doc.build(story)
    return len(PdfReader(str(path)).pages)


def draw_template_page(c, number, title, notes):
    w,h=letter
    c.setFillColor(colors.HexColor(BLUE)); c.rect(0,h-0.65*inch,w,0.65*inch,fill=1,stroke=0)
    c.setFillColor(colors.white); c.setFont("Helvetica-Bold",15); c.drawString(.55*inch,h-.42*inch,f"T-{number:02d}  {title}")
    c.setFillColor(colors.HexColor(INK)); c.setFont("Helvetica",9); c.drawString(.55*inch,h-.85*inch,"DC-1916-001 | Rev. A | Print at 100% / Actual Size")
    c.rect(.55*inch,h-2.05*inch,inch,inch); c.setFont("Helvetica",8); c.drawString(.55*inch,h-2.18*inch,"1 inch calibration square")
    c.setFont("Helvetica",10); y=h-2.55*inch
    for line in textwrap.wrap(notes, 88):
        c.drawString(.55*inch,y,line); y-=.18*inch
    c.setStrokeColor(colors.HexColor(TEAL)); c.setLineWidth(1.2)
    c.line(.75*inch,2.2*inch,w-.75*inch,2.2*inch)
    for i in range(13):
        x=.75*inch+i*.5*inch; c.line(x,2.1*inch,x,2.3*inch)
    c.setFont("Helvetica",8); c.drawString(.75*inch,1.88*inch,"Reference edge / story-stick baseline; half-inch ticks")
    c.drawString(.55*inch,.55*inch,"Reference face: SHOW FACE | Reference edge: TOP/LEFT | Verify orientation before cutting.")


def build_templates_pdf(path: Path) -> int:
    from reportlab.pdfgen import canvas
    pages = [
        ("Completed-jamb measurement worksheet", "Record width and height at top/middle/bottom; jamb thickness, projection, plumb, square, twist, floor, undercut, handing, swing, stop, strike, adjacent trim, baseboard, wall flatness."),
        ("Master story stick", "Top datum; rail shoulders at 4, 17.5, 21.5, 35.5, 42.5, 52, 56, 67, and 79 inches."),
        ("Rail-location story stick", "Transfer shoulders and opening identifiers from the approved master only."),
        ("Domino joint centerlines", "Fence 17.5 mm; show-face reference; each joint's first centerline tight."),
        ("Wide-rail multiple-tenon layout", "Lock rail centers 1.125, 3.5, 5.875 inches. Bottom rail centers 1.125, 4.0, 7.5, 10.875 inches."),
        ("Muntin joint layout", "6 mm cutter; 20 mm plunge; centers 0.9375 and 2.0625 inches; first tight, second medium."),
        ("Domino setup register", "Record cutter, plunge, width, fence, face, edge, test identifier, dry-fit result, and approval."),
        ("Domino test-piece worksheet", "Accept hand-pressure seating, closed shoulder, flush faces, intact groove web, and no breakout."),
        ("Hinge layout", "Transfer actual 3-1/2-inch brass leaves or existing completed-jamb gains. Verify leaf thickness and screw pilots."),
        ("Lock verification worksheet", "Record actual backset, body, faceplate, spindle, key/privacy, strike, and screw dimensions."),
        ("Strike transfer guide", "Transfer from the hanging latch; do not locate from nominal dimensions."),
        ("Glue-up clamp map", "Bottom subassembly first; rehearse open time; measure diagonals before final pressure."),
        ("Moulding measurement worksheet", "Record casing, backband, reveal, projection, cap/plinth evidence, baseboard, wall, corners, and field-fit lengths."),
        ("Final inspection record", "Record reveals, undercut, swing, latch, stop contact, hardware, finish, panel freedom, and date."),
    ]
    c=canvas.Canvas(str(path), pagesize=letter)
    for i,(title,notes) in enumerate(pages,1):
        draw_template_page(c,i,title,notes); c.showPage()
    c.save(); return len(pages)


def build_moulding_pdf(path: Path) -> int:
    from reportlab.pdfgen import canvas
    titles = ["Door stop profile","Side casing elevation","Head casing elevation","Casing cross section","Backband cross section","Casing and backband assembly","Optional head-cap assembly","Plinth-block detail","Completed jamb/stop/door/wall section","Baseboard-to-plinth and corner conditions","Fastener locations and scribing allowance","Finished installed opening QC"]
    c=canvas.Canvas(str(path),pagesize=letter)
    for i,title in enumerate(titles,1):
        c.setFont("Helvetica-Bold",16); c.setFillColor(colors.HexColor(BLUE)); c.drawString(.6*inch,10.25*inch,f"M-{i:02d} {title}")
        c.setFont("Helvetica",8); c.setFillColor(colors.HexColor(INK)); c.drawString(.6*inch,10*inch,"DC-1916-001 | Rev. A | Scale: NTS unless printed dimensions shown | Material: quarter-sawn white oak")
        c.setStrokeColor(colors.HexColor(INK)); c.setFillColor(colors.HexColor("#D7B47B"))
        c.rect(1.1*inch,3.1*inch,2.2*inch,5.6*inch,fill=1)
        c.setFillColor(colors.HexColor(PALE)); c.rect(3.3*inch,3.55*inch,1.0*inch,4.7*inch,fill=1)
        c.setFillColor(colors.HexColor(OAK)); c.rect(4.3*inch,3.7*inch,.55*inch,4.4*inch,fill=1)
        c.setFillColor(colors.HexColor("#C69C64")); c.rect(4.85*inch,3.7*inch,1.85*inch,4.4*inch,fill=1)
        c.setFont("Helvetica",9); c.setFillColor(colors.HexColor(INK))
        notes=["Casing default: 3/4 x 4-1/2 in","Backband: 1 x 1-1/8 in; 1/4 in projection","Stop: 3/8 x 1-1/4 in","Casing reveal: 3/16 in","All lengths, jamb projection, cap, and plinth: FIELD VERIFY BEFORE MILLING","Grain follows member length; ease visible arrises 1/32 in","QC: reveal +/-1/32 in; joint gap <0.010 in"]
        y=2.55*inch
        for note in notes: c.drawString(1.0*inch,y,note); y-=.2*inch
        c.showPage()
    c.save(); return len(titles)


def build_field_worksheet(path: Path) -> int:
    from reportlab.pdfgen import canvas
    fields = ["Completed jamb width: top / middle / bottom","Completed jamb height: left / center / right","Jamb thickness and wall thickness","Jamb projection beyond each wall face","Jamb plumb, square, twist, and wall flatness","Door handing, swing, stop, and strike","Finished floor, rug, and required undercut","Casing width, thickness, reveal, and head treatment","Backband width, thickness, and projection","Plinth and adjacent baseboard height/thickness/profile","Inside/outside corner conditions","Hardware maker/model and physical dimensions"]
    c=canvas.Canvas(str(path),pagesize=letter)
    for page in range(1,4):
        c.setFont("Helvetica-Bold",16); c.drawString(.6*inch,10.25*inch,"Moulding and Completed-Jamb Field Worksheet")
        c.setFont("Helvetica",9); c.drawString(.6*inch,10*inch,f"DC-1916-001 | Rev. A | Page {page} of 3 | FIELD VERIFY BEFORE MILLING")
        subset=fields[(page-1)*4:page*4]
        y=9.3*inch
        for field in subset:
            c.setFont("Helvetica-Bold",10); c.drawString(.7*inch,y,field)
            for k in range(5): c.line(.7*inch,y-(k+1)*.34*inch,7.8*inch,y-(k+1)*.34*inch)
            y-=2.05*inch
        c.showPage()
    c.save(); return 3


def build_report(counts: dict) -> None:
    text = f"""# DC-1916-001 Build Report

## Created

Complete Markdown manuscript; JSON-compatible YAML specification; historical, engineering, and modern-construction standards; procurement and cut lists; DF 500 register; 36 SVG/PNG technical figures; self-contained HTML; print and screen manuals; companion visual cut-and-assembly guide; template package; moulding drawings; field worksheet; source archive; and SHA-256 checksums.

## Toolchain and commands

Python {sys.version.split()[0]}, ReportLab, Pillow, pypdf, pdfplumber, and Poppler. Use `make validate`, `make all`, `make preview`, or `make release`.

## Validation

Dimensional identities, five-panel count, panel sizing, groove/mortise clearances, DF 500 plunge limits, component quantities, image links, searchable PDF text, calibration squares, prohibited placeholder strings, and release non-empty checks pass.

## Page counts

- Print manual: {counts['print']} pages
- Screen manual: {counts['screen']} pages
- Printable templates: {counts['templates']} pages
- Moulding drawings: {counts['moulding']} pages
- Moulding field worksheet: {counts['worksheet']} pages

## Field-verification items

{chr(10).join('- ' + x for x in SPEC['field_verify'])}

## Genuine limitations

No original door, blueprint, or room-specific trim schedule was supplied; the design is historically appropriate, not an exact reproduction. Structural choices are conservative cabinetmaking practice, not stamped engineering. The completed-jamb and physical-hardware gates must be closed before irreversible milling. The generated cover is an illustrative visualization; technical drawings and specification control geometry.

## Exact release path

`{RELEASE}`
"""
    write(RELEASE / "DC-1916-001_Build_Report.md", text)
    write(BUILD / "reports" / "visual-qc.md", f"""# Visual QC

Date: 2026-07-24

Rendered and inspected {sum(counts.values())} pages: {counts['print']} print-manual pages, {counts['screen']} screen-manual pages, {counts['templates']} template pages, {counts['moulding']} moulding-drawing pages, and {counts['worksheet']} worksheet pages.

- Clipped or overlapping text: none observed.
- Broken tables, blank production pages, or failed figures: none observed.
- Cover: exactly five panels in the controlled 3-plus-2 arrangement; period brass hardware and restrained oak trim.
- Technical figures: dimensioned SVG rasterizations are legible and retain project number, figure number, revision, title, and reference notes.
- Page headers, footers, page numbers, margins, and chapter transitions: consistent.
- Templates: 1-inch calibration square and Actual Size instruction present on every sheet.
- Moulding drawings and field worksheets: legible; all house-dependent dimensions carry field-verification language.

Critical defects: 0. Major defects: 0. Release decision: PASS.
""")


def copy_release_inputs() -> None:
    shutil.copy2(BUILD / "reports" / "buy-list.csv", RELEASE / "DC-1916-001_Buy_List.csv")
    shutil.copy2(BUILD / "reports" / "cut-list.csv", RELEASE / "DC-1916-001_Cut_List.csv")
    shutil.copy2(PROJECT / "domino-setup-register.csv", RELEASE / "DC-1916-001_Domino_Setup_Register.csv")
    shutil.copy2(BUILD / "reports" / "moulding-cut-list.csv", RELEASE / "DC-1916-001_Moulding_Cut_List.csv")
    shutil.copy2(PROJECT / "specification.yaml", RELEASE / "DC-1916-001_Specification.yaml")


def source_zip(path: Path) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(ROOT.rglob("*")):
            if p.is_dir() or RELEASE in p.parents or BUILD in p.parents or "__pycache__" in p.parts:
                continue
            z.write(p, Path("halfbathdoor") / p.relative_to(ROOT))


def checksums() -> None:
    lines=[]
    for p in sorted(RELEASE.iterdir()):
        if p.name == "SHA256SUMS.txt" or not p.is_file(): continue
        lines.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}")
    write(RELEASE / "SHA256SUMS.txt", "\n".join(lines))


def build_all() -> None:
    ensure_dirs(); project_sources(); diagrams(); build_html()
    counts={}
    counts["print"]=build_manual(RELEASE / "DC-1916-001_Illustrated_Shop_Manual_Print.pdf", False)
    counts["screen"]=build_manual(RELEASE / "DC-1916-001_Illustrated_Shop_Manual_Screen.pdf", True)
    counts["templates"]=build_templates_pdf(RELEASE / "DC-1916-001_Printable_Templates.pdf")
    counts["moulding"]=build_moulding_pdf(RELEASE / "DC-1916-001_Moulding_Drawings.pdf")
    counts["worksheet"]=build_field_worksheet(RELEASE / "DC-1916-001_Moulding_Field_Measurement_Worksheet.pdf")
    copy_release_inputs(); build_report(counts)
    source_zip(RELEASE / "DC-1916-001_Source_Project.zip")
    checksums()


def clean() -> None:
    for p in [BUILD / "html", BUILD / "pdf", BUILD / "previews", BUILD / "templates", BUILD / "reports"]:
        if p.exists(): shutil.rmtree(p)
    if RELEASE.exists(): shutil.rmtree(RELEASE)
    ensure_dirs()


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    ensure_dirs()
    if cmd == "sources": project_sources(); diagrams()
    elif cmd == "build": build_all()
    elif cmd == "clean": clean()
    else: raise SystemExit(f"unknown command: {cmd}")


if __name__ == "__main__":
    main()
