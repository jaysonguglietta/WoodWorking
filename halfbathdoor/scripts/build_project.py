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
CABINET_RENDERINGS = ROOT / "cabinetmakers-guide" / "renderings"

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


_BOOTSTRAP_SPEC = {
    "project": {
        "number": "DC-1916-001",
        "title": "Building a Historically Appropriate Five-Panel Door",
        "classification": "Historically appropriate reproduction door using modern concealed joinery",
        "year": 2026,
        "edition": "First Edition",
        "revision": "Rev. G",
        "copyright_holder": "Jayson Guglietta",
    },
    "units": {"primary": "inch", "domino": "millimetre"},
    "opening": {
        "status": "confirmed installed finished jamb; dimensions reported consistent at every measured location",
        "clear_width": 24.0,
        "clear_height": 81.0,
        "hinge_side_reveal": 0.125,
        "lock_side_reveal": 0.125,
        "head_reveal": 0.125,
        "bottom_gap": 0.375,
        "installed_gap_tolerance_plus_minus": {
            "side_reveals": 0.03125,
            "head_reveal": 0.03125,
            "bottom_gap": 0.0625,
        },
        "derivation": "finished slab width = jamb width - hinge-side reveal - lock-side reveal; finished slab height = jamb height - head reveal - bottom gap",
    },
    "slab": {
        "finished_width": 23.75,
        "finished_height": 80.5,
        "finished_thickness": 1.375,
        "target_status": "finished fitted slab target derived from the confirmed installed jamb",
        "dimensional_states": {
            "confirmed_jamb_opening": "24 x 81 inches, confirmed consistent throughout the installed finished jamb",
            "cured_surfaced_prefit_assembly": "23-7/8 x 80-5/8 inches, carrying 1/16 inch removable stock on each perimeter edge",
            "final_layout_rectangle": "scribe 23-3/4 x 80-1/2 inches inside the prefit assembly from the final-top and hinge-edge datums",
            "finished_fitted_slab": "23-3/4 x 80-1/2 x 1-3/8 inches; maximum rectangular envelope before any handing-specific latch-edge bevel",
        },
        "manufacturing_trim_reserve_per_edge": 0.0625,
        "finished_size_tolerance": {
            "width_plus": 0.0,
            "width_minus": 0.03125,
            "height_plus": 0.0,
            "height_minus": 0.0625,
            "rule": "the fitted slab may not exceed 23-3/4 x 80-1/2; actual hung reveals and bottom gap govern acceptance",
        },
        "diagonal_difference_max": 0.0625,
        "twist_max": 0.03125,
    },
    "frame": {
        "stile_width": 4.25,
        "rail_shoulder_length": 15.25,
        "muntin_width": 3.0,
        "rail_widths": {
            "D-101C": 4.0,
            "D-101M": 4.0,
            "D-101D": 7.0,
            "D-101E": 4.0,
            "D-101F": 12.0,
        },
        "vertical_openings": {
            "P-01 upper": 14.25,
            "P-02 center": 14.75,
            "P-03 lower-center": 9.5,
            "P-04 bottom": 11.0,
        },
        "bottom_opening_each": 6.125,
        "construction": {
            "type": "balanced three-layer, all-long-grain solid-oak lamination",
            "core_preglue_thickness": 0.875,
            "show_face_preglue_thickness": 0.3125,
            "back_face_preglue_thickness": 0.3125,
            "glue_blank_thickness": 1.5,
            "symmetric_face_removal_each": 0.0625,
            "show_face_finished_thickness": 0.25,
            "back_face_finished_thickness": 0.25,
            "finished_glue_lines_from_show_face": [0.25, 1.125],
            "face_glue_line_location_tolerance_plus_minus": 0.010,
            "grain_rule": "core, face lamellae, and every edge-glued stave run continuously parallel with the member length; no cross-grain layer and no end joint",
            "one_piece_core_members": ["D-101A", "D-101B", "D-101C", "D-101M", "D-101E", "D-101G"],
            "stave_built_members": {
                "D-101D": {
                    "core_seams_from_finished_top": [2.25],
                    "show_face_seams_from_finished_top": [4.375],
                    "back_face_seams_from_finished_top": [4.875],
                },
                "D-101F": {
                    "core_seams_from_finished_top": [5.75],
                    "show_face_seams_from_finished_top": [3.0, 6.5, 9.5],
                    "back_face_seams_from_finished_top": [2.5, 5.0, 9.0],
                },
            },
            "seam_position_tolerance_plus_minus": 0.03125,
            "core_to_face_seam_offset_min": 0.5,
            "face_seam_to_end_mortise_planform_min": 0.25,
            "seam_to_mortise_validation": {
                "basis": "nearest face seam to a medium DF 500 mortise planform; 29 mm total slot width gives a 0.5709-inch half-width",
                "D-101D_min_clearance": 0.3041,
                "D-101F_min_clearance": 0.4291,
                "required_minimum": 0.25,
                "status": "PASS at specified seam stations and retained Domino centers",
            },
            "df_cutter_to_face_glue_line_core_clearance_min": 0.2,
            "lock_body_to_face_glue_line_clearance_min": 0.0625,
            "thickness_slicing_prohibited": True,
            "face_preparation_rule": "prepare every 5/16-inch face lamella by flattening, staged planing, resting, and carrier-supported finishing from one whole-thickness board or billet; do not divide a board through its thickness",
            "no_resaw_rule": "No resaw operation is permitted in Rev. G; every face lamella is prepared from one whole-thickness board or billet by staged planing.",
            "stile_lane_gate": "STOCK-I and STOCK-K must each yield at least 8-7/8 inches of clear jointed width for two 4-3/8-inch full-length lanes plus one 1/8-inch width-rip kerf; the core lane must yield 81 inches clear and the back-face lane 81-1/8 inches clear",
            "stile_layer_allocation": {
                "D-101A": "STOCK-K 7/8-inch core lane + STOCK-B continuous 5/16-inch show face + STOCK-K parallel continuous 5/16-inch back face",
                "D-101B": "STOCK-I 7/8-inch core lane + STOCK-C continuous 5/16-inch show face + STOCK-I parallel continuous 5/16-inch back face",
            },
            "lamination_rule": "prepare core and face sheets separately; plane every face lamella from a whole-thickness board or billet; laminate both faces simultaneously against a flat platen with rigid cauls; cure, rest, then remove 1/16 inch from each outside face in alternating staged passes before grooves, Domino mortises, hinges, or lock machining",
            "coupon_rule": "make a full-thickness same-layup coupon for every pressing family; section after representative groove and DF operations and reject voids, adhesive-line separation, under-thickness faces, or insufficient core clearance",
        },
    },
    "components": [
        {"id": "D-101A", "name": "Hinge stile", "qty": 1, "t": 1.375, "w": 4.25, "l": 80.5},
        {"id": "D-101B", "name": "Lock stile", "qty": 1, "t": 1.375, "w": 4.25, "l": 80.5},
        {"id": "D-101C", "name": "Top rail", "qty": 1, "t": 1.375, "w": 4.0, "l": 15.25},
        {"id": "D-101M", "name": "Upper intermediate rail", "qty": 1, "t": 1.375, "w": 4.0, "l": 15.25},
        {"id": "D-101D", "name": "Lock rail", "qty": 1, "t": 1.375, "w": 7.0, "l": 15.25},
        {"id": "D-101E", "name": "Lower intermediate rail", "qty": 1, "t": 1.375, "w": 4.0, "l": 15.25},
        {"id": "D-101F", "name": "Bottom rail", "qty": 1, "t": 1.375, "w": 12.0, "l": 15.25},
        {"id": "D-101G", "name": "Center muntin", "qty": 1, "t": 1.375, "w": 3.0, "l": 11.0},
        {"id": "D-101H", "name": "Upper panel", "qty": 1, "t": 0.5, "w": 15.875, "l": 15.0625},
        {"id": "D-101J", "name": "Center panel", "qty": 1, "t": 0.5, "w": 15.875, "l": 15.5625},
        {"id": "D-101N", "name": "Lower-center panel", "qty": 1, "t": 0.5, "w": 15.875, "l": 10.3125},
        {"id": "D-101K", "name": "Lower-left panel", "qty": 1, "t": 0.5, "w": 6.875, "l": 11.8125},
        {"id": "D-101L", "name": "Lower-right panel", "qty": 1, "t": 0.5, "w": 6.875, "l": 11.8125},
    ],
    "panels": {
        "material": "FAS quarter-sawn white oak",
        "grain": "vertical",
        "field_thickness": 0.5,
        "tongue_thickness": 0.21875,
        "tongue_thickness_tolerance_plus_minus": 0.005,
        "tongue_depth": 0.4375,
        "tongue_depth_tolerance_plus_minus": 0.005,
        "tongue_bottom_clearance_nominal": 0.0625,
        "full_width_clearance_across_grain_total": 0.25,
        "small_width_clearance_across_grain_total": 0.125,
        "clearance_parallel_to_grain_total": 0.0625,
        "panel_spacers": {
            "mandatory_longitudinal_length": 0.75,
            "dimension_note": "0.750 inch (3/4 inch) is the mandatory longitudinal length along the groove, not the groove width, spacer compression thickness, or panel movement clearance",
            "target_groove_width": 0.25,
            "target_groove_depth": 0.5,
            "material_requirements": "oil- and silicone-free open-cell foam with documented groove range, firmness or force-deflection, recovery, and finish compatibility",
            "reference_candidate": {
                "product": "Panel Buddies PB265-750XF-1M",
                "status": "reference candidate only; not approved until both panel-family sample gates pass",
                "nominal_cross_section_width": 0.265,
                "nominal_cross_section_depth": 0.265,
                "longitudinal_length": 0.75,
                "manufacturer_groove_range": [0.22, 0.25],
                "manufacturer_compression_guidance": 0.5,
                "groove_release_condition": "measure the actual spacer-zone groove; use this candidate only from 0.220 through 0.250 inch unless the manufacturer gives written approval for the measured groove, otherwise qualify another 3/4-inch-long foam spacer",
            },
            "compression_analysis": {
                "basis": "candidate compression compares the 0.265-inch foam dimension with the centered tongue-end gap: nominal tongue-bottom clearance plus one-half of total panel side clearance",
                "full_width_family": {
                    "panels": ["D-101H", "D-101J", "D-101N"],
                    "centered_tongue_end_gap_nominal": 0.1875,
                    "candidate_compression_nominal": 0.292453,
                    "candidate_compression_tolerance_range": [0.235849, 0.311321],
                    "release_gate": "dedicated full-size H/J/N-family sample must prevent rattle while preserving residual travel and zero spacer-induced joint stress",
                },
                "lower_family": {
                    "panels": ["D-101K", "D-101L"],
                    "centered_tongue_end_gap_nominal": 0.125,
                    "candidate_compression_nominal": 0.528302,
                    "candidate_compression_tolerance_range": [0.471698, 0.547170],
                    "release_gate": "dedicated full-size K/L-family sample must prevent rattle while preserving residual travel and zero spacer-induced joint stress",
                },
            },
            "placement": "two spacers in each vertical side groove near the upper and lower thirds; no spacers in horizontal grooves or structural glue zones",
            "installed_quantity": 20,
            "test_spare_quantity": 10,
            "acceptance": "approve the selected 3/4-inch-long foam separately for the full-width H/J/N family and lower K/L family; both full-size gates must prove residual horizontal panel travel, no joint stress, recovery without crushing, no finish or glue-surface contamination, and no change to calculated panel clearance; PB265 additionally requires an actual 0.220-0.250-inch spacer-zone groove or written manufacturer approval",
        },
        "anti_rattle": "use 3/4-inch-long oil- and silicone-free open-cell foam panel spacers; Panel Buddies PB265-750XF-1M is a reference candidate, not a preapproved product; install two in each vertical side groove only and preserve calculated panel clearances; release the selected product separately on full-size H/J/N and K/L samples",
    },
    "groove": {
        "width": 0.25,
        "depth": 0.5,
        "centerline_from_show_face": 0.6875,
        "stile_type": "stopped at every rail joint; opening-only segments",
        "rail_type": "through along panel-facing edges except the D-101E bottom and D-101F top edges",
        "segmented_rail_edges": {
            "D-101E bottom": [[0.0, 6.125], [9.125, 15.25]],
            "D-101F top": [[0.0, 6.125], [9.125, 15.25]],
        },
        "muntin_footprint_from_hinge_side_rail_shoulder": [6.125, 9.125],
        "machining_split": {
            "dado_stack": "conventionally fed through grooves on supported rail edges only",
            "plunge_router": "opening-only stile grooves, segmented D-101E/D-101F grooves, and both D-101G side grooves; use an edge guide or captured jig with positive start and stop blocks",
        },
        "panel_tongue_corner_relief": "after forming the 7/16-inch-deep tongues, remove the complete 7/16 x 7/16-inch tongue corner square at all four corners without cutting into the 1/2-inch panel field",
    },
    "milling": {
        "frame_rough_thickness": 1.5,
        "frame_rough_width_allowance": 0.25,
        "stile_glue_blank_width_allowance": 0.125,
        "stile_core_length": 81.0,
        "stile_face_length": 81.125,
        "prefit_assembly_width": 23.875,
        "prefit_assembly_height": 80.625,
        "stile_rough_length_allowance_total": 0.5,
        "rail_rough_length_allowance_total": 1.0,
        "muntin_rough_length_allowance_total": 1.0,
        "rail_rough_length": 16.25,
        "panel_rough_thickness": 0.625,
        "panel_rough_width_allowance": 0.5,
        "panel_rough_length_allowance": 0.5,
        "panel_rough_dimensions": {
            "D-101H": {"t": 0.625, "w": 16.375, "l": 15.5625},
            "D-101J": {"t": 0.625, "w": 16.375, "l": 16.0625},
            "D-101N": {"t": 0.625, "w": 16.375, "l": 10.8125},
            "D-101K": {"t": 0.625, "w": 7.375, "l": 12.3125},
            "D-101L": {"t": 0.625, "w": 7.375, "l": 12.3125},
        },
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
        "frame_mortise_width_strategy": "first tight; remaining mortises medium on both members",
        "muntin_mortise_width_strategy": {
            "D-101G": ["tight", "tight"],
            "D-101E and D-101F": ["tight", "medium"],
        },
        "muntin_centers_in": {
            "D-101G from left reference edge": [1.0, 2.0],
            "D-101E and D-101F from hinge-side shoulder": [7.125, 8.125],
        },
        "frame_centers_from_rail_top_in": {
            "D-101C": [1.25, 2.75],
            "D-101M": [1.25, 2.75],
            "D-101D": [1.25, 3.5, 5.75],
            "D-101E": [1.25, 2.75],
            "D-101F": [1.25, 4.0, 7.5, 10.75],
        },
        "stile_centers_from_slab_top_in": {
            "D-101C": [1.25, 2.75],
            "D-101M": [19.5, 21.0],
            "D-101D": [38.25, 40.5, 42.75],
            "D-101E": [54.75, 56.25],
            "D-101F": [69.75, 72.5, 76.0, 79.25],
        },
        "mortise_centerline_tolerance_plus_minus": 0.010,
        "glue": "fresh Type II PVA; complete mortise walls and tenon faces without hydraulic overfill",
    },
    "adhesive": {
        "type": "fresh Type II PVA",
        "timing_basis": "manufacturer's current published open time at the measured shop temperature",
        "eligible_timing_label": "open time only",
        "rehearsal_final_gate_fraction_max": 0.75,
        "live_final_geometry_fraction_max": 0.75,
        "timer_start": "first adhesive contact",
        "timer_end": "final geometry and panel-movement acceptance",
        "clamp_complete_status": "checkpoint only; timer continues",
        "contingency_fraction_min": 0.25,
    },
    "fabrication_tolerances": {
        "frame_thickness": {"target": 1.375, "plus_minus": 0.010},
        "paired_member_thickness_difference_max": 0.005,
        "reference_edge_square_max_per_inch": 0.003,
        "groove_width": {"target": 0.250, "plus": 0.005, "minus": 0.0},
        "groove_depth": {"target": 0.500, "plus": 0.010, "minus": 0.0},
        "opposed_groove_centerline_mismatch_max": 0.010,
        "joint_shoulder_gap_max": 0.005,
        "joint_face_flush_max": 0.010,
        "frame_medium_mortise_web_to_panel_groove_min": 0.150,
        "muntin_tight_mortise_web_to_side_groove_min": 0.100,
        "muntin_tight_inter_mortise_web_min": 0.220,
        "muntin_rail_inter_mortise_web_min": 0.100,
    },
    "hardware": {
        "hinges": {"qty": 3, "nominal_size": "3-1/2 inch brass butt hinge", "locations": "field verify leaf thickness, screw sizes, and existing-jamb gains"},
        "lock": "traditional brass mortise lock; obtain and measure before any J-06 production mortise or lock machining",
        "nominal_lock_center_above_slab_bottom": 40.0,
        "lock_to_joinery_clear_wood_min": 0.25,
        "lock_envelope_gate": "Map the physical lock body, faceplate, spindle, key/privacy bore, machining allowance, and screw paths. Preserve the required 1/4-inch clear-wood buffer between that machining envelope and J-06 or any other structural joinery; evaluate intentional face and edge openings separately for hardware and escutcheon compatibility. Re-engineer J-06 if the structural envelopes conflict.",
        "required_measurements": [
            "manufacturer", "model", "backset", "body height", "body thickness",
            "faceplate height", "faceplate width", "spindle size", "key/privacy location",
            "strike dimensions", "hinge leaf thickness", "screw diameter", "screw length",
        ],
    },
    "trim": {
        "material": "quarter-sawn white oak",
        "trimmed_face_count": 2,
        "side_casing_finished": {"t": 0.75, "w": 4.5, "l": "field verify"},
        "head_casing_finished": {"t": 0.75, "w": 4.5, "l": "field verify"},
        "backband_finished": {"t": 1.0, "w": 1.125, "projection": 0.25, "l": "field verify"},
        "head_backband": {
            "part_id": "M-202C",
            "status": "mandatory on every trimmed face",
            "cap_relationship": "complete and fit M-202C before fitting optional M-204; M-204 sits atop the completed head backband",
        },
        "stop_finished": {"t": 0.375, "w": 1.25, "l": "field verify"},
        "reveal": 0.1875,
        "optional_head_cap": {
            "t": 0.875,
            "depth": 1.5,
            "side_overhang": 0.75,
            "support": "completed M-202C head backband",
            "finished_length": "actual fitted head-backband outside width + 2P",
            "rough_length": "actual fitted head-backband outside width + 2P + 2 inches total allowance",
        },
        "plinth": {
            "use": "only when adjacent original trim supports it",
            "nominal_thickness": 0.875,
            "status": "provisional shop default only; field evidence controls thickness, width, height, and profile",
        },
        "base_schedule_scope": "two trimmed faces plus one three-piece door-stop set",
        "two_face_rule": "four side casings, two head casings, four side backbands, two head backbands, and one three-piece stop set; double cap and plinth only where used",
        "procurement": {
            "basis": "one-trip order for two faces, no plinths; covers square-butt or mitered heads",
            "casing_and_stop": {
                "quantity_boards": 7,
                "description": "S4S quarter-sawn white oak, 4/4 x nominal 6 inches x 8 feet",
                "actual_minimum": "3/4 inch thick at thinnest point after final preparation, 5-1/2 inches wide, 96 inches long; 13/16-inch thickness preferred",
                "allocation": "four side-casing boards, one board for both head casings, one full-length casing spare/match board, and one stop mother blank",
            },
            "backband_and_optional_caps": {
                "quantity_boards": 2,
                "description": "S4S quarter-sawn white oak, 6/4 x nominal 6 inches x 8 feet",
                "actual_minimum": "1-1/4 inches thick, 5-1/2 inches wide, 96 inches long",
                "allocation": "one board per face yields two side backbands and one head backband; also yields one optional cap per face when the square-head treatment is evidence-supported",
            },
            "dealer_volume_board_feet": 40.0,
            "minimum_geometric_order_board_feet": 36.0,
            "plinths": "excluded; measure and order separately only when adjacent original work supports them",
        },
        "head_joint_schemes": ["mitered surround", "square-butt head"],
        "head_joint_selection": "match adjacent original openings; do not mix schemes on one face",
        "dado_blade_required": False,
        "default_machining": "standard ripping and crosscutting blades; plunge router or hand tools only for localized back relief",
        "rough_length_allowance_total": 2.0,
        "stock_order_waste_percent_min": 20,
        "length_formulas": {
            "mitered_head_inside_short": "W + 2R",
            "mitered_head_outside_long": "W + 2R + 2C",
            "mitered_left_leg_outside_long": "H-L + R + C",
            "mitered_right_leg_outside_long": "H-R + R + C",
            "square_left_leg": "H-L + R",
            "square_right_leg": "H-R + R",
            "square_head": "W + 2R + 2C",
            "head_backband_outside_target": "actual fitted head-casing outside width + 2B",
            "mitered_side_backband_outer_long": "actual fitted mitered side-casing outside long point + B",
            "square_side_backband": "actual fitted square side-casing length + C",
            "optional_head_cap": "actual fitted head-backband outside width + 2P",
        },
        "fastener_embedment_minimums": {
            "inner_casing_into_sound_jamb": 0.75,
            "door_stop_into_sound_jamb": 0.75,
            "outer_casing_into_verified_framing": 1.0,
            "backband_into_casing": 0.50,
        },
        "fastener_length_release": "Calculate each fastener length from the actual installed layer stack, prove the selected standard length on a matching offcut assembly, and hold installation if no standard length meets embedment without exit, split, or utility risk.",
        "permanent_installation_sequence": [
            "after full finish cure, install evidence-supported plinths first as the casing bottom datum without glue to floor or wall",
            "install casing",
            "install backband and glue approved self-returns",
            "install optional cap atop the completed head backband",
            "install door stop last after tack, cycle, label-reference, and functional checks",
        ],
        "post_cure_glue_boundaries": {
            "plinth": "masked approved plinth-to-trim joints only; no glue to floor or wall",
            "casing": "masked casing-to-casing joints only",
            "backband": "masked backband-to-casing lands, corner joints, and self-returns only",
            "cap": "masked approved cap-to-head-backband joint only",
        },
        "installation_qc": {
            "reveal_variation_max": 0.03125,
            "joint_gap_max": 0.010,
            "adjacent_face_flush_max": 0.010,
            "head_level_max_overall": 0.0625,
            "leg_plumb_max_overall": 0.0625,
            "backband_projection_variation_max": 0.03125,
            "wall_scribe_gap_max": 0.03125,
        },
    },
    "finish": {
        "product": "Rubio Monocoat Oil Plus 2C",
        "color": "Pure",
        "surface_grit": 120,
        "panel_edges_prefinish": True,
        "cure": "follow the current product technical data sheet; ventilation and oily-cloth controls required",
    },
    "field_verify": [
        "record and recheck the owner-confirmed 24 x 81-inch completed jamb at top/middle/bottom and left/center/right before fitting",
        "both jamb legs plumb in the opening plane and wall-normal plane, head level, both opening diagonals/square, and jamb-face twist checked with winding sticks",
        "finished-floor elevation and full swing path preserve the 3/8-inch bottom gap",
        "hung slab proves 1/8-inch hinge-side, lock-side, and head reveals plus the 3/8-inch bottom gap within the specified installed-gap tolerances",
        "door handing, swing, stop, strike, and any reusable hinge gains",
        "wall thickness and flatness",
        "adjacent casing, backband, baseboard, head treatment, and plinth evidence",
        "all physical mortise-lock, strike, hinge-leaf, and screw dimensions",
    ],
}

SPEC_PATH = PROJECT / "specification.yaml"
# The checked-in project specification is authoritative.  The embedded model
# remains only as a bootstrap for a genuinely new checkout with no spec file.
SPEC = (
    json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    if SPEC_PATH.exists()
    else _BOOTSTRAP_SPEC
)
LABELED_STOCK_PATH = PROJECT / "labeled-stock-plan.json"
LABELED_STOCK = json.loads(LABELED_STOCK_PATH.read_text(encoding="utf-8"))
if SPEC["project"]["revision"] != "Rev. G":
    raise ValueError(
        "project/specification.yaml is stale: Rev. G is required before generation"
    )
if LABELED_STOCK["document"]["stock_plan"] != "LS-05":
    raise ValueError(
        "project/labeled-stock-plan.json is stale: LS-05 is required before generation"
    )


def labeled_stock_assignment(part_id: str) -> str:
    """Return the controlled labeled-stock assignment without changing part sizes."""
    allocations = {
        row["part"]: row for row in LABELED_STOCK["component_allocations"]
    }
    stock_plan = LABELED_STOCK["document"]["stock_plan"]
    if part_id not in allocations:
        raise ValueError(f"{stock_plan} has no allocation for {part_id}")
    row = allocations[part_id]
    gate = {
        "D-101A": "CHK-ST-01/02; CHK-LAM-01",
        "D-101B": "CHK-ST-01/02; CHK-LAM-01",
        "D-101C": "CHK-SM-01; CHK-FP-01; CHK-LAM-01",
        "D-101M": "CHK-SM-01; CHK-FP-01; CHK-LAM-01",
        "D-101D": "CHK-SM-01; CHK-FP-01; CHK-LAM-01; CHK-SEAM-01",
        "D-101E": "CHK-SM-01; CHK-FP-01; CHK-LAM-01",
        "D-101F": "CHK-SM-01; CHK-FP-01; CHK-LAM-01; CHK-SEAM-01",
        "D-101G": "CHK-SM-01; CHK-FP-01; CHK-LAM-01",
        "D-101H": "CHK-RS-01; CHK-P-01; M-01",
        "D-101J": "CHK-RS-01; CHK-P-01; G-01",
        "D-101N": "CHK-RS-01; CHK-P-01; H-01",
        "D-101K": "CHK-RS-01; CHK-P-01; D-01",
        "D-101L": "CHK-RS-01; CHK-P-01; D-01",
    }[part_id]
    stock = " + ".join(f"STOCK-{label}" for label in row["stock"].replace("+", "/").split("/"))
    return f"{stock}; {row['allocation']}; {row['status']}; {stock_plan} {gate}"


JOINTS = [
    ("J-01", "Top rail to hinge stile", "D-101C", "D-101A", 10, "10 x 50", 2, 25, [1.25, 2.75]),
    ("J-02", "Top rail to lock stile", "D-101C", "D-101B", 10, "10 x 50", 2, 25, [1.25, 2.75]),
    ("J-03", "Upper intermediate rail to hinge stile", "D-101M", "D-101A", 10, "10 x 50", 2, 25, [1.25, 2.75]),
    ("J-04", "Upper intermediate rail to lock stile", "D-101M", "D-101B", 10, "10 x 50", 2, 25, [1.25, 2.75]),
    ("J-05", "Lock rail to hinge stile", "D-101D", "D-101A", 10, "10 x 50", 3, 25, [1.25, 3.5, 5.75]),
    ("J-06", "Lock rail to lock stile", "D-101D", "D-101B", 10, "10 x 50", 3, 25, [1.25, 3.5, 5.75]),
    ("J-07", "Lower intermediate rail to hinge stile", "D-101E", "D-101A", 10, "10 x 50", 2, 25, [1.25, 2.75]),
    ("J-08", "Lower intermediate rail to lock stile", "D-101E", "D-101B", 10, "10 x 50", 2, 25, [1.25, 2.75]),
    ("J-09", "Bottom rail to hinge stile", "D-101F", "D-101A", 10, "10 x 50", 4, 25, [1.25, 4.0, 7.5, 10.75]),
    ("J-10", "Bottom rail to lock stile", "D-101F", "D-101B", 10, "10 x 50", 4, 25, [1.25, 4.0, 7.5, 10.75]),
    ("J-11", "Center muntin to lower intermediate rail", "D-101G", "D-101E", 6, "6 x 40", 2, 20, [1.0, 2.0]),
    ("J-12", "Center muntin to bottom rail", "D-101G", "D-101F", 6, "6 x 40", 2, 20, [1.0, 2.0]),
]

PART_B_CENTERS = {
    "J-01": [1.25, 2.75],
    "J-02": [1.25, 2.75],
    "J-03": [19.5, 21.0],
    "J-04": [19.5, 21.0],
    "J-05": [38.25, 40.5, 42.75],
    "J-06": [38.25, 40.5, 42.75],
    "J-07": [54.75, 56.25],
    "J-08": [54.75, 56.25],
    "J-09": [69.75, 72.5, 76.0, 79.25],
    "J-10": [69.75, 72.5, 76.0, 79.25],
    "J-11": [7.125, 8.125],
    "J-12": [7.125, 8.125],
}

# Joint centerlines are governed by project/specification.yaml.  The tuple
# definitions above retain family identity and tooling metadata, while this
# normalization prevents a source build from silently restoring stale centers.
_frame_centers = SPEC["domino"]["frame_centers_from_rail_top_in"]
_muntin_centers = SPEC["domino"]["muntin_centers_in"]
JOINTS = [
    (
        jid,
        family,
        part_a,
        part_b,
        cutter,
        tenon,
        count,
        plunge,
        list(
            _muntin_centers["D-101G from left reference edge"]
            if jid in {"J-11", "J-12"}
            else _frame_centers[part_a]
        ),
    )
    for jid, family, part_a, part_b, cutter, tenon, count, plunge, _ in JOINTS
]
_stile_centers = SPEC["domino"]["stile_centers_from_slab_top_in"]
PART_B_CENTERS = {
    jid: list(
        _muntin_centers["D-101E and D-101F from hinge-side shoulder"]
        if jid in {"J-11", "J-12"}
        else _stile_centers[part_a]
    )
    for jid, _, part_a, _, _, _, _, _, _ in JOINTS
}


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


# The legacy manual remains useful as a prose reference, but its first-edition
# technical figures were intentionally generic. Reuse the dimension-controlled
# cabinetmaker renderings so every chapter opens with project-specific geometry.
# The technical-figure register remains the fallback for source-only builds.
LEGACY_CHAPTER_RENDERINGS = {
    "00-cover.md": "01-complete-system",
    "01-title-page.md": "01-complete-system",
    "02-copyright.md": "02-exploded-door",
    "03-safety.md": "04a-groove-setups",
    "04-how-to-use-this-manual.md": "02-exploded-door",
    "05-table-of-contents.md": "02-exploded-door",
    "10-project-overview.md": "01-complete-system",
    "20-historical-appearance.md": "13-final-release",
    "30-buy-list.md": "03-stock-milling",
    "40-cut-list.md": "02-exploded-door",
    "50-lumber-selection.md": "03-stock-milling",
    "60-shop-preparation.md": "03a-machine-calibration",
    "70-milling.md": "03-stock-milling",
    "80-layout-and-story-sticks.md": "03a-machine-calibration",
    "90-panel-grooves.md": "04a-groove-setups",
    "100-domino-engineering.md": "05-rail-stile-joint",
    "110-domino-test-pieces.md": "05a-df500-workholding",
    "120-stile-mortising.md": "05a-df500-workholding",
    "130-rail-mortising.md": "05-rail-stile-joint",
    "140-muntin-mortising.md": "06a-muntin-clearance",
    "150-panel-construction.md": "04-groove-panel-cutaway",
    "160-dry-assembly.md": "07a-full-dry-fit",
    "170-glue-up.md": "08a-glue-clock",
    "180-flush-and-surface.md": "08-clamp-geometry",
    "190-fit-to-completed-jamb.md": "09a-jamb-fit-map",
    "200-hinges.md": "09b-hinge-gain",
    "210-mortise-lock.md": "09c-lock-strike",
    "220-matching-millwork.md": "10-moulding-layers",
    "230-finish.md": "12b-finish-sequence",
    "240-final-installation.md": "09-hanging-system",
    "250-inspection-and-troubleshooting.md": "13-final-release",
    "260-maintenance.md": "13-final-release",
    "270-appendices.md": "02-exploded-door",
}


def legacy_chapter_rendering(filename: str) -> Path | None:
    """Return a project-specific chapter rendering when the asset is present."""

    slug = LEGACY_CHAPTER_RENDERINGS.get(filename)
    if not slug:
        return None
    path = CABINET_RENDERINGS / f"{slug}.png"
    return path if path.exists() else None


def exact_decimal(value: float) -> str:
    """Format controlled inch dimensions without discarding 1/32- or 1/64-inch data."""

    return f"{value:.6f}".rstrip("0").rstrip(".")


def rail_top_positions() -> dict[str, float]:
    """Derive every rail top from the controlled rail/opening stack."""

    frame = SPEC["frame"]
    rail_ids = ("D-101C", "D-101M", "D-101D", "D-101E", "D-101F")
    opening_ids = (
        "P-01 upper",
        "P-02 center",
        "P-03 lower-center",
        "P-04 bottom",
    )
    cursor = 0.0
    positions: dict[str, float] = {}
    for index, rail_id in enumerate(rail_ids):
        positions[rail_id] = cursor
        cursor += frame["rail_widths"][rail_id]
        if index < len(opening_ids):
            cursor += frame["vertical_openings"][opening_ids[index]]
    if not math.isclose(cursor, SPEC["slab"]["finished_height"], abs_tol=1e-9):
        raise ValueError(
            f"rail/opening stack is {cursor:g} inches, not "
            f"{SPEC['slab']['finished_height']:g}"
        )
    return positions


def story_stick_stations() -> list[tuple[float, str]]:
    """Return the complete top-datum shoulder register."""

    frame = SPEC["frame"]
    rail_ids = ("D-101C", "D-101M", "D-101D", "D-101E", "D-101F")
    positions = rail_top_positions()
    marks: list[tuple[float, str]] = [(0.0, "TOP DATUM")]
    for index, rail_id in enumerate(rail_ids):
        bottom = positions[rail_id] + frame["rail_widths"][rail_id]
        if index == len(rail_ids) - 1:
            marks.append((bottom, "BOTTOM DATUM"))
        else:
            marks.append((bottom, f"{rail_id} BOTTOM"))
            marks.append((positions[rail_ids[index + 1]], f"{rail_ids[index + 1]} TOP"))
    return marks


OP_DATA = {
    "milling": ("Produce stable balanced-laminated frame blanks without case-hardening, voids, bow, or twist.",
        ["jointer", "thickness planer", "planer carrier sled with positive trailing stop", "cabinet saw", "crosscut sled", "moisture meter", "flat platen", "rigid cauls"],
        ["Complete CHK-RS-01 before shortening any critical board. Record the minimum clear dimensions, defects, moisture, bow, cup, and twist of STOCK-A through STOCK-O. N/O are confirmed finished white oak at 1-3/4 x 11 x 74; record their moisture, grain, flatness, defects, and clear yield.",
         "Prove the staged-planing and lamination schedule on same-stock coupons. Prepare glue-ready cores at 7/8 inch and paired show/back lamellae at 5/16 inch; grain must run continuously with the member. Do not resaw any A-O board.",
         "Keep STOCK-B/C/I/K full length through both stile gates. Joint one face and one edge, then ordinarily rip I and K by width into two parallel 4-3/8-inch lanes each. Mark one lane from each for a 7/8-inch core and the other for a 5/16-inch face; B and C each supply one additional 5/16-inch face lane.",
         "Once both faces are flat and parallel, remove thickness symmetrically in shallow passes no heavier than 1/32 inch. For a 5/16-inch face lane, pause near 3/4 inch, 1/2 inch, and 11/32 inch before the final 5/16-inch pass; for a 7/8-inch core, pause near 1 inch and 29/32 inch. Sticker for at least one overnight shop cycle at each pause, then remeasure bow, cup, twist, and minimum thickness.",
         "If a rested lane moves, reflatten it only while enough thickness remains to reach the target; otherwise reject it. Use a flat carrier sled with a positive trailing stop when the planer maker requires it for thin work. Never trap a thin loose part beneath an unsecured carrier.",
         "Edge-glue any mapped width staves into the released core or face sheet, keeping D-101D and D-101F seams at their controlled three-plane locations. Flatten each sheet before the final layup.",
         "Laminate both faces onto the core at the same time on a flat platen with rigid cauls. The glue blank must measure 5/16 + 7/8 + 5/16 = 1-1/2 inches.",
         "After the adhesive reaches full cure, rest the blank and remove 1/16 inch equally from each outer face. The final balanced section is 1/4 + 7/8 + 1/4 = 1-3/8 inches.",
         "Joint the reference edge, rip to width, and crosscut to final length only after CHK-LAM-01 passes. Machine panel grooves, Domino mortises, hinge gains, and lock work after lamination and final symmetric surfacing.",
         "Mark show face, back face, core/face stock labels, reference edge, top, bottom, and D-101 identifier before stacking parts."],
        ["preglue layer thickness within 0.010 inch", "finished thickness within 0.010 inch", "paired rails within 0.005 inch", "edge square within 0.003 inch per inch", "sectioned coupon retains at least 0.200 inch actual core wood beyond every groove or DF cutter envelope"]),
    "grooves": ("Create centered floating-panel grooves without weakening Domino joint zones.",
        ["SawStop cabinet saw", "1/4-inch dado stack and correct dado cartridge/insert", "plunge router with 1/4-inch bit and edge guide", "positive stops", "push blocks", "dust extraction"],
        ["Prove the dado and router cuts at 1/4-inch width and at least 1/2-inch depth on production-thickness scrap; the 7/32 +/-0.005-inch tongue must slide without rocking or bottoming.",
         "Keep the production groove at 0.250 +0.005/-0.000 inch. The PB265 reference candidate is listed for 0.220-0.250-inch grooves and has a nominal 0.265 x 0.265-inch cross-section, but it is not preapproved; never widen a groove to match uncompressed foam.",
         "For supported through grooves only, stand each rail on its panel-facing narrow edge with the show face against a tall fence and feed conventionally through the approved dado setup.",
         "For every plunge-routed edge groove, place the panel-facing narrow edge up in a full-length captured cradle and span it with a wide auxiliary router bridge; use an edge guide or captured carriage and positive start/stop blocks.",
         "Rout the D-101E bottom and D-101F top segments from 0 to 6-1/8 inches and 9-1/8 to 15-1/4 inches; never lower or lift a member over a spinning dado stack.",
         "Use a chisel only to square a required termination; label and inspect every start/stop station before mortising.",
         "Label every opening and verify that opposed grooves share one centerline before mortising."],
        ["groove width 0.250 +0.005/-0.000 inch", "depth 0.500 +0.010/-0.000 inch", "centerline mismatch no more than 0.010 inch"]),
    "stiles": ("Cut all rail mortises from a single show-face and story-stick reference.",
        ["Domino DF 500", "10 mm cutter", "story stick", "parallel clamps", "dust extractor"],
        ["Clamp the stile inside edge up and show face toward the operator; support the full 80-1/2-inch finished length and hook every coordinate from the scribed final-top line, not the temporary pre-fit end.",
         "Fit the 10 mm cutter, set 25 mm plunge, 17.5 mm fence height, 90-degree fence, and tight width.",
         "Transfer rail shoulders and tenon centerlines from the verified story stick, never from chained measurements.",
         "Cut the first mortise of each joint tight; with the motor running change only the remaining mortises to the medium setting.",
         "Vacuum, inspect, and test every joint family with its labeled scrap before moving the story stick."],
        ["no mortise enters a stopped or segmented groove", "centerline within 0.010 inch", "test rail shoulders close under hand pressure"]),
    "rails": ("Match rail-end mortises to the stile mortises while preserving face registration.",
        ["Domino DF 500", "10 mm cutter", "bench vise or end-support jig", "setup blocks"],
        ["Clamp the rail with show face against the same fence reference used for the stiles.",
         "Square the rail end to the reference edge and support the machine so it cannot roll during plunge.",
         "Cut the first centerline tight and the remaining centerlines medium exactly as the setup register specifies; for J-11/J-12 this tight/medium pattern applies only to D-101E and D-101F.",
         "Use the specification centers: 4-inch rails 1.250/2.750; lock rail 1.250/3.500/5.750; bottom rail 1.250/4.000/7.500/10.750 inches.",
         "On each paired production-thickness sample, first prove shoulder closure with untouched full-length factory tenons. Only after that gate passes, minimally ease the ribs and ends of a clearly labeled rehearsal set enough for hand removal; never shorten a tenon."],
        ["rail face flush within 0.010 inch", "shoulder gap under 0.005 inch", "actual rail web to an adjacent groove at least 0.150 inch"]),
    "muntin": ("Join the narrow center muntin without intersecting its two panel grooves.",
        ["Domino DF 500", "6 mm cutter", "trim-stop style support jig", "calipers"],
        ["Confirm the muntin is exactly 3 inches wide and mark its future groove limits before either operation.",
         "Before routing its side grooves, set 20 mm plunge and cut two 6 mm mortises at 1.000 and 2.000 inches from the left reference edge.",
         "Cut both D-101G mortises tight. A medium follower would enter the right side groove and is prohibited.",
         "In D-101E and D-101F, cut at 7.125 and 8.125 inches from the hinge-side shoulder; use first tight and second medium inside the 6-1/8-to-9-1/8-inch groove-free footprint.",
         "Dry-fit with 6 x 40 mm factory beech tenons and confirm both bottom-panel openings remain 6-1/8 inches.",
         "Section the full-thickness TP-11/TP-12 samples after both operations; remake any part with a subminimum web, breakout, or merged mortise."],
        ["two 6-1/8-inch openings within 1/64 inch", "D-101G groove-to-mortise web at least 0.100 inch", "D-101G inter-mortise web at least 0.220 inch", "mating-rail inter-mortise web at least 0.100 inch", "muntin square within 0.010 inch"]),
    "panels": ("Build five solid panels that move seasonally without rattling.",
        ["jointer", "planer", "cabinet saw", "plunge router with edge guide", "smoother", "sander", "3/4-inch-long foam panel-spacer candidates"],
        ["Select vertical-grain quarter-sawn boards; book-match any edge glue-ups and pair D-101K with D-101L.",
         "Glue panel blanks oversize, flatten, and plane to a 1/2-inch field thickness.",
         "Cut full-width panels to 15-7/8 inches and lower panels to 6-7/8 inches; preserve the specified length clearance.",
         "Form 7/32 +/-0.005-inch-thick tongues projecting 7/16 inch, leaving nominal 1/16-inch bottom clearance in the approved groove.",
         "Remove the complete 7/16 x 7/16-inch tongue corner square at all four corners without cutting into the panel field.",
         "Use an oil- and silicone-free open-cell foam spacer with a mandatory 0.750-inch (3/4-inch) longitudinal length along the groove. Record manufacturer, SKU, cross-section, groove range, firmness or force-deflection, recovery, and finish compatibility. Panel Buddies PB265-750XF-1M (0.265 x 0.265 x 0.750 inch) is a reference candidate only, not a preapproved product.",
         "For the PB265 candidate, the centered tongue-end gap predicts about 29.2 percent nominal compression for full-width H/J/N (tolerance envelope about 23.6-31.1 percent) and 52.8 percent for lower K/L (about 47.2-54.7 percent). Because the manufacturer says its products are made for 50 percent compression, do not infer one-family approval from the other.",
         "Measure the actual groove at every candidate spacer zone. PB265 is published for 0.220-0.250-inch grooves; if any measured zone exceeds 0.250 inch, hold that candidate until the manufacturer approves the measured width in writing or qualify another 3/4-inch-long foam product.",
         "Build and release two full-size groove/panel samples: one for H/J/N and a separate one for K/L. In each sample place two candidates near the upper and lower thirds of each vertical side groove; keep spacers out of horizontal grooves and structural glue zones.",
         "Preserve the calculated 1/4-inch total side clearance in full-width panels and 1/8-inch total side clearance in lower panels. The spacers control rattle; they do not establish or replace clearance.",
         "Prefinish panel edges and tongues while keeping finish out of frame glue surfaces. Release a product for a family only if that family's cured full-size sample retains perceptible horizontal travel, closes without joint stress, prevents rattle, recovers without crushing, and leaves no oil, silicone, adhesive, or retention residue on finish or glue surfaces.",
         "After both family gates pass, bag two released spacers per vertical side groove: four per panel and 20 installed total. Retain 10 labeled test/spare pieces."],
        ["hand-pressure sliding fit", "at least 1/8 inch total cross-grain movement at lower panels", "no glue on tongues", "residual movement with no spacer-induced joint stress or finish contamination"]),
    "dry": ("Prove geometry, joint closure, and panel movement before adhesive is opened.",
        ["parallel clamps", "cauls", "tape measure", "engineer's square", "winding sticks"],
        ["Assemble the entire door on a flat platform with the lower module still unglued, labeled test tenons, all five panels installed, and two approved 3/4-inch-long foam spacers in each vertical side groove.",
         "Bring shoulders home with moderate clamp pressure; a joint requiring heavy pressure must be corrected, not forced.",
         "Measure both diagonals, overall width and height, and all rail positions from the top reference.",
         "Sight winding sticks and press each panel laterally to confirm independent movement. If spacer compression bows a member, resists shoulder closure, or eliminates residual travel, stop and reject the spacer/sample combination.",
         "Mark clamp locations and disassembly order directly on masking tape; only then release Stage A glue-up.",
         "After Stage A cures, repeat the complete-door dry fit with the cured module before releasing Stage B."],
        ["diagonal difference no more than 1/16 inch", "twist no more than 1/32 inch", "every shoulder gap under 0.005 inch"]),
    "glue": ("Assemble square and flat within the adhesive's open time.",
        ["Type II PVA", "parallel clamps", "cauls", "acid brush", "timer", "scraper"],
        ["Rehearse each glue-up stage with relieved, never-shortened test tenons and time from first simulated adhesive contact through the final geometry and panel-movement acceptance. The final rehearsal gate must finish at or below 75 percent of the selected adhesive manufacturer's current published OPEN time at the measured shop temperature; no differently labeled timing window qualifies.",
         "Stage A: glue the center muntin to D-101E and D-101F with four clean 6 x 40 mm tenons, capture D-101K/L dry with four approved 3/4-inch-long foam spacers, clamp square, and allow the module to reach full cure.",
         "Stage B: apply a controlled film to both mating mortise walls and every face of twenty-six clean 10 x 50 mm frame tenons; never fill the bottom of a mortise.",
         "Load the cured lower module, remaining rails, and panels between the stiles; never glue a panel tongue or groove.",
         "For each live stage, start the timer at first adhesive contact. Record clamp complete only as a checkpoint; keep timing through the final geometry and panel-movement acceptance, which must pass at or below 75 percent of current published open time. Then clean squeeze-out and allow full cure."],
        ["all shoulders closed", "diagonals within 1/16 inch", "twist within 1/32 inch", "final live geometry and panel-movement gate at or below 75 percent of published open time"]),
    "fit": ("Fit the cured slab to the existing completed jamb while retaining a final adjustment margin.",
        ["No. 4 plane", "block plane", "track-guided saw optional", "bevel gauge", "story stick"],
        ["Measure jamb width and height at three locations; record plumb, square, twist, floor, and swing.",
         "Plane the hinge edge straight first, then establish the head and lock-side reveals from that datum.",
         "Carry jamb bevel or out-of-square conditions to the slab with a story stick; do not average away a binding corner.",
         "Retain the floor allowance until finished floor, rug, and seasonal requirements are known.",
         "Stop when the unfitted slab has uniform planned reveals and remains at least 1/32 inch oversize for final hand fitting."],
        ["head and side reveal target 3/32 inch unless field evidence dictates otherwise", "no edge hollow over 12 inches", "swing path clear"]),
    "hinges": ("Fit three brass butt hinges from verified physical leaves while using steel screws for every setup and swing test.",
        ["marking knife", "hinge template", "plunge router", "chisels", "Vix bit", "steel setup screws"],
        ["Field-verify existing gains or establish three locations appropriate to the 80-1/2-inch fitted slab inside the confirmed 81-inch jamb.",
         "Knife the actual leaf, rout slightly shallow, then pare to a no-gap fit with the barrel clear of casing.",
         "Drill centered pilots sized to the screw root; establish threads with matching steel screws.",
         "Hang and cycle the slab using matching steel setup screws only; remove and retain them before finish.",
         "After the final finish reaches full cure, install the brass screws by hand with a correctly fitting driver.",
         "Replace any brass screw that twists or cams out; never drive it with an impact driver."],
        ["leaf flush within 0.005 inch", "barrels collinear", "steel used for setup", "final brass installed only after full finish cure"]),
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
        ["Complete and sign the four-page millwork field worksheet; record both legs plumb in both planes, head level, diagonals/square, winding-stick face twist, and whether one or both faces receive new trim.",
         "Choose either a mitered surround or square-butt head from adjacent evidence; do not mix joint schemes on one face.",
         "Calculate every rough blank from the longest required point plus at least 2 inches total allowance; never use jamb height alone for a mitered leg.",
         "Mill 3/4 x 4-1/2-inch flat casing, 1 x 1-1/8-inch edge-applied backband, and 3/8 x 1-1/4-inch stop unless field evidence controls; the default profiles require no dado stack.",
         "Scribe jamb projection and wall irregularity, then fit side casings and head casing, mandatory M-202C head backband, and only evidence-supported cap or plinth parts; the optional cap sits atop the completed head backband.",
         "Dry-fit, label, and remove all trim for finishing. After full cure install evidence-supported plinths first as the casing datum, then casing, backband/self-returns, cap, and the head/side stops last after tack-and-cycle proof."],
        ["reveal variation no more than 1/32 inch", "joint gaps under 0.010 inch and faces flush within 0.010 inch", "stop contact continuous without latch preload"]),
    "finish": ("Finish the fitted frame and trim while protecting fully cured prefinished floating panels.",
        ["vacuum", "white nonwoven pad", "lint-free cloths", "scale or marked mixing cup", "nitrile gloves"],
        ["Before assembly, sand the complete floating panels through P120, prefinish their faces, edges, and tongues with the approved Rubio Oil Plus 2C Pure schedule, and allow full cure while keeping all frame glue surfaces bare.",
         "After the frame glue-up reaches full cure, protect every prefinished panel and scrape and sand the frame only through P100; do not abrade the cured panel surfaces.",
         "Complete the jamb fit and dry-fit hinges, lock, strike, stops, casing, backband, and any evidence-supported trim using steel setup screws.",
         "Remove the hardware and final-sand only the frame and fitted removable trim to P120; vacuum thoroughly and mask the cured panels, hinge gains, lock mortise, and bores.",
         "Mix only the quantity that can be spread and buffed within the current product working time.",
         "Spread an exceptionally thin film on the frame and trim, allow the specified reaction time, then buff until no wet residue transfers to a clean cloth.",
         "Allow the finish to reach full cure under the current technical data sheet before installing final brass hardware.",
         "Lay oily cloths flat outdoors to cure or submerge them in water in a sealed metal container for compliant disposal."],
        ["prefinished panels remain unmarred", "no glossy pools", "uniform frame and trim color in raking light", "final brass installed only after full cure", "finish-release item: all oily waste controlled before leaving shop"]),
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

- Five recessed flat panels: three full-width panels over a paired lower row. The substantial 12-inch bottom rail, 7-inch lock rail, 4-inch intermediate rails, 4-1/4-inch stiles, and 3-inch muntin avoid modern equal-strip Shaker proportions.
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

The visible design remains traditional; modernization is concealed. Every frame member is a balanced three-layer, all-long-grain white-oak lamination. Prepare a 7/8-inch core and two 5/16-inch face layers entirely by jointing, ordinary width ripping where assigned, staged thickness planing, resting, and rechecking. Press both faces at the same time on a flat platen with rigid cauls, cure and rest, then remove 1/16 inch equally from each outside face. The released section is therefore 1/4 + 7/8 + 1/4 = 1-3/8 inches. No A-O board is resawn, and no layer may contain an end joint or cross-grain patch.

The two 4-1/4-inch finished stiles start as 4-3/8-inch-wide layer lanes. After full-length defect mapping, rip STOCK-I and STOCK-K lengthwise into two parallel 4-3/8-inch lanes each. Plane one lane from each board to a 7/8-inch continuous core and the other to a 5/16-inch continuous face. Plane one continuous 5/16 x 4-3/8 x 81-1/8-inch face from each of STOCK-B and STOCK-C. D-101A uses K core, B show face, and K parallel-lane back face; D-101B uses I core, C show face, and I parallel-lane back face. Once both faces are flat and parallel, alternate faces in matched shallow passes no heavier than 1/32 inch. Sticker for at least one overnight shop cycle near each staged thickness, then recheck bow, cup, twist, and minimum thickness; reject any lane that cannot be reflattened while retaining the released dimensions.

D-101A/B/C/M/E/G use one-piece cores and continuous-width faces. D-101D uses the controlled three-plane stave map: seams from the finished top are 2-1/4 core, 4-3/8 show face, and 4-7/8 back face. D-101F uses a core seam at 5-3/4, show-face seams at 3, 6-1/2, and 9-1/2, and back-face seams at 2-1/2, 5, and 9 inches from the finished top. Every seam station is controlled within +/-1/32 inch. Make and destructively section same-layup coupons before production. The centered 1/4-inch groove and all 6/10 mm DF cutter envelopes must retain at least 0.200 inch of actual core wood to either face glue line.

Rail-to-stile joints use multiple factory beech Domino tenons made with the DF 500. Stile grooves stop outside every rail joint. D-101E's bottom groove and D-101F's top groove are split into 0-to-6-1/8-inch and 9-1/8-to-15-1/4-inch segments so neither groove enters the 3-inch muntin footprint. The muntin uses two 6 x 40 mm tenons because its paired grooves leave less web than the frame rails.

Frame joints use a tight first mortise and medium followers on both members. Revised rail centers preserve at least 0.150 inch of actual wood beside every adjacent panel groove. J-11 and J-12 are member-specific: both mortises in D-101G are tight at 1 and 2 inches, retaining at least 0.100 inch from each mortise to its side groove and at least 0.220 inch between the two G mortises; the mating rail mortises are tight/medium at 7-1/8 and 8-1/8 inches inside the groove-free footprint and retain at least 0.100 inch between them. All mortises reference the same show face, a labeled datum edge, and the scribed final-top line on a verified story stick. Machine grooves, Domino mortises, hinge gains, and lock work only after lamination, full cure, rest, and symmetric surfacing. Pocket screws, biscuits, brads, and face screws are not structural door joinery. Solid panels float and are never glued into their grooves; 7/16-inch tongues retain bottom clearance and their complete corner squares are relieved to clear stopped-groove terminations.

Required work remains executable with the listed home-shop machines. The no-resaw thickness schedule uses a jointer, thickness planer, cabinet saw for ordinary width rips, moisture meter, flat platen, and rigid cauls. No bandsaw operation, router table, shaper, CNC, DF 700, industrial mortiser, or commercial door clamp is assumed.
"""
    write(PROJECT / "modern-construction-standard.md", modern)
    audit_lines = [
        "# Engineering Audit", "",
        "Status: **PASS for Rev. G fitted geometry and conditional LS-05 no-resaw nesting; fabrication remains on HOLD until the physical-yield, staged-planing, lamination-coupon, seam-map, panel, jamb, and hardware gates are completed.**", "",
        "## Dimensional reconciliation", "",
        "- Confirmed jamb opening: 24 x 81 inches. Required gaps are 1/8 inch at each side, 1/8 inch at the head, and 3/8 inch at the bottom.",
        "- Finished fitted slab: width 24 - 1/8 - 1/8 = 23-3/4 inches; height 81 - 1/8 - 3/8 = 80-1/2 inches; thickness 1-3/8 inches.",
        "- Prefit assembly: 23-7/8 x 80-5/8 inches after cure and thickness surfacing, carrying 1/16 inch removable stock outside every final perimeter edge. Story-stick coordinates hook from the scribed final-top line.",
        "- Frame width: 4.25 + 15.25 + 4.25 = 23.75 inches.",
        "- Frame height: rails 4 + 4 + 7 + 4 + 12 = 31 inches; openings 14.25 + 14.75 + 9.5 + 11 = 49.5 inches; total = 80.5 inches.",
        "- Bottom width: (15.25 - 3) / 2 = 6.125 inches per opening.",
        "- Five panels: D-101H, D-101J, added D-101N, D-101K, and D-101L. D-101M and D-101N resolve the source brief's four-panel identifier conflict without renaming frozen parts.",
        "- Full-width panel width: 15.25 + 2(0.4375) - 0.25 = 15.875 inches. Lower panel width: 6.125 + 2(0.4375) - 0.125 = 6.875 inches.",
        "- Panel lengths equal opening + two 7/16-inch tongue projections - 1/16 inch parallel-grain clearance.",
        "", "## Groove and mortise coordination", "",
        "- The 1/4 x 1/2-inch groove is centered 11/16 inch from either face.",
        "- Stile grooves are stopped in panel openings; no stile mortise intersects a groove.",
        "- The D-101E bottom and D-101F top grooves stop at 6.125 inches and restart at 9.125 inches from the hinge-side rail shoulder, leaving the complete 3-inch muntin footprint solid.",
        "- Four-inch rails use centers at 1.250 and 2.750 inches; the 7-inch rail uses 1.250, 3.500, and 5.750; the 12-inch rail uses 1.250, 4.000, 7.500, and 10.750. Worst-case web beside an adjacent groove remains above the 0.150-inch project minimum.",
        "- Lock and bottom rails distribute three and four tenons respectively. The 25 + 25 mm plunges accept 10 x 50 mm DF 500 tenons without exceeding the 28 mm machine maximum.",
        "- The 3-inch muntin uses tight 6 mm mortises at 1.000 and 2.000 inches with 20 mm plunges. With maximum groove depth and center error, each outer groove-to-mortise web remains about 0.106 inch and the inter-mortise web remains above 0.220 inch; the sectioned sample must retain at least 0.100 inch and 0.220 inch respectively.",
        "- Mating rail mortises are at 7.125 and 8.125 inches from the hinge-side shoulder. Their tight/medium pattern stays inside the 6.125-to-9.125-inch footprint and retains at least 0.100 inch actual inter-mortise web.",
        "- The 7/16-inch panel tongues leave nominal 1/16-inch groove-bottom clearance. Every complete 7/16 x 7/16-inch tongue corner square is relieved without cutting into the panel field.",
        "", "## Door-only labeled-stock reconciliation (LS-05)", "",
        "- Rev. G retains the verified 24 x 81 jamb opening and 23-3/4 x 80-1/2 x 1-3/8 fitted slab while changing the internal width allocation to fit the owner stock without resawing. LS-05 supersedes LS-04 for stock yield and procurement.",
        "- STOCK-A is now 72-3/4 inches long after the required 6-inch damage removal; its new end and every proposed billet remain subject to CHK-RS-01 and CHK-P-01. STOCK-B through STOCK-F and STOCK-H through STOCK-K remain reported rough-sawn, unjointed, and unplaned. STOCK-G is confirmed S4S at 15/16 x 4-1/2 x 75 inches; its thickness exceeds the 5/8-inch D-101J rough-panel minimum by 5/16 inch, and thickness/width/length pass. CHK-P-01 still controls flatness, moisture, grain, defects, glue-edge cleanup, and four clear billet zones before crosscutting. STOCK-L is now 6 inches wide after edge cleanup; its faces, thickness, length, and final dressed yield remain unverified. No unverified face or edge is a production datum.",
        "- All A-O stock is reserved exclusively for the door, its same-layup coupons, setup pieces, substitutions, and repair stock. STOCK-M is the primary D-101H upper-panel source, STOCK-A remains intact as panel reserve, and confirmed finished-white-oak STOCK-N/O remain full-length short-member core reserve. The current door-lumber purchase is zero only while every LS-05 gate passes.",
        "- STOCK-I and STOCK-K are each ordinarily ripped by width into two continuous 4-3/8-inch lanes: one lane is planed to a 7/8-inch stile core and the parallel lane is planed to a 5/16-inch stile face. STOCK-B and STOCK-C each provide one continuous 5/16-inch stile face by staged thickness planing. No A-O board is resawn. If a long layer fails, buy a replacement long board rather than splice or narrow the stile.",
        "- Revised CM-05 maps J to the C/M cores, the 6-1/2-inch F core stave, and G; 6-inch L carries E, both D core staves, and the 5-3/4-inch F core stave. The signed FP-05 face pool conditionally yields the face sheets by width ripping and staged thickness planing. D/F retain their controlled staggered seam maps.",
        "- STOCK-M/G/H/D are the primary panel sources for D-101H/J/N/K-L; STOCK-A is the first upper-panel fallback. CHK-RS-01 and CHK-P-01 must prove post-preparation 5/8-inch thickness, aggregate clean glue-up width, clear squared length, species, moisture, grain, color, and defect placement before production cutting.",
        "- Moulding is not cut from A-O. The separate two-face order is seven S4S 4/4 x nominal 6-inch x 8-foot boards for casing and one stop set plus two S4S 6/4 x nominal 6-inch x 8-foot boards for the 1-inch finished backband and optional evidence-supported caps.",
        "", "## Structural and fabrication review", "",
        "- The balanced 5/16 + 7/8 + 5/16 glue blank is made without resawing and surfaced equally to a final 1/4 + 7/8 + 1/4 section. Once both faces are parallel, each lane reaches preglue thickness through matched shallow passes with stickered rest and recheck gates; a moved lane is reflattened only while its target yield remains. This symmetric construction reduces bow risk and leaves the centered groove and DF 500 cutters in the core with the controlled clearance.",
        "- Multiple anti-rotation tenons, a 12-inch laminated bottom rail, full-height continuous-layer stiles, and the center muntin resist sag and racking. This is conservative cabinetmaking engineering, not stamped structural engineering.",
        "- Before J-06 is machined, map the physical lock body and machining allowance against its mortises and both face glue lines. Retain at least 1/4 inch clear wood to joinery and at least 1/16 inch to either core glue line; re-engineer J-06 if the envelopes conflict.",
        "- Dry-fit the entire door with Stage A still unglued. Then glue and cure the four-tenon lower module, recheck it, perform a second complete dry fit, and only then glue the twenty-six-tenon frame. For each stage, both rehearsal and live final geometry/panel-movement acceptance must finish at or below 75 percent of current published open time; clamp complete is only a checkpoint.",
        "- Solid-panel movement is across the vertical grain. Full-width panels receive 1/4 inch total side clearance; lower panels receive 1/8 inch. The 3/4-inch foam-spacer length is mandatory, but PB265-750XF-1M is a reference candidate only. Its nominal centered-gap compression is about 29.2 percent for H/J/N and 52.8 percent for K/L against the manufacturer's 50 percent guidance. Separate full-size family samples must prove residual travel, no joint stress, recovery, and finish compatibility; spacers never establish or replace calculated clearance. PB265 also requires an actual 0.220-0.250-inch spacer-zone groove or written manufacturer approval.",
        "- The verified 24 x 81-inch value describes the completed jamb opening. The fitted slab may not exceed 23-3/4 x 80-1/2 inches; installed side/head reveals and bottom gap govern acceptance.",
        "", "## Audit conclusion", "",
        "The Rev. G design is internally consistent and within published DF 500 cutter and plunge limits. No general door-lumber purchase is released, but that is a conditional planning result—not proof of yield. Fabrication is blocked at the documented field gates and at LS-05 CHK-RS-01, CHK-ST-01, CHK-ST-02, CHK-SM-01, CHK-FP-01, CHK-P-01, CHK-LAM-01, and CHK-SEAM-01.",
    ]
    write(PROJECT / "engineering-audit.md", "\n".join(audit_lines))
    joint_lines = [
        "# DF 500 Joint-Family Engineering", "",
        "All frame mortises are cut only after the balanced lamination cures, rests, and is surfaced to 1/4 + 7/8 + 1/4. Reference the show face with a 17.5 mm fence height and 90-degree fence. Every sectioned production-family coupon must retain at least 0.200 inch of actual core wood from the cutter envelope to either face glue line. Frame joints use a tight first mortise and medium followers on both members. J-11/J-12 use two tight mortises in D-101G and a tight/medium pair in the mating rail. Stile grooves and the two muntin-adjacent rail grooves stop outside their joint zones.", "",
    ]
    for jid, family, a, b, cutter, tenon, count, plunge, centers in JOINTS:
        widest = "bottom-rail racking resistance" if "Bottom" in family else ("lock-rail hardware and shear reserve" if "Lock rail" in family else ("narrow muntin groove-web control" if "muntin" in family else "face alignment and racking resistance"))
        is_muntin = jid in {"J-11", "J-12"}
        strategy = (
            "D-101G both tight; mating rail first tight and second medium"
            if is_muntin
            else f"first mortise tight, {max(0,count-1)} follower mortise(s) medium on both members"
        )
        groove_analysis = (
            "the sectioned test-piece gate requires D-101G groove-to-mortise web at least 0.100 inch, D-101G inter-mortise web at least 0.220 inch, and mating-rail inter-mortise web at least 0.100 inch; the mating rail groove is segmented around the 6-1/8-to-9-1/8-inch footprint"
            if is_muntin
            else "mating stile groove is stopped; groove-adjacent rail mortises retain at least 0.150 inch actual web"
        )
        joint_lines += [
            f"## {jid} - {family}", "",
            f"- Members: {a} to {b}. Cutter: {cutter} mm. Factory beech tenon: {tenon} mm. Quantity: {count}.",
            f"- Plunge: {plunge} mm in each member. Part A centerlines from its marked reference edge: {', '.join(str(x) for x in centers)} inches.",
            f"- Part B centerlines from {'the hinge-side rail shoulder' if is_muntin else 'the finished top of the stile'}: {', '.join(str(x) for x in PART_B_CENTERS[jid])} inches.",
            f"- Strategy: {strategy}. Primary rationale: {widest}.",
            f"- Groove analysis: {groove_analysis}.",
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

Acceptance gate before J-06: draw the physical lock body, machining allowance, faceplate, spindle and key/privacy bores at full scale against the proposed J-06 mortises and the finished face glue lines 1/4 and 1-1/8 inches from the show face. Retain at least 1/4 inch of clear wood between the lock envelope and joinery, and at least 1/16 inch from the body cavity plus machining allowance to either core glue line. The shallow faceplate recess is an intentional inspected edge opening. If the envelopes conflict, stop and issue a revised J-06 layout before mortising either D-101D or D-101B. Hinge-gain depth must remain within the nominal 1/4-inch face lamella and hinge screws must penetrate the core. Hinge leaves must fit the completed jamb or a documented new layout.
""")
    write(PROJECT / "decisions.md", """# Engineering Decisions

1. Added D-101M upper intermediate rail and D-101N lower-center panel to reconcile the frozen identifiers with the mandatory five-panel count.
2. Adopted a 3-plus-2 arrangement: three full-width panels above two paired lower panels.
3. Adopted stopped stile grooves to eliminate unavoidable groove-to-mortise intersection.
4. Selected 10 x 50 mm factory beech tenons for rail-to-stile joints; 6 x 40 mm for the narrower muntin.
5. Assigned two tenons to 4-inch rails, three to the lock rail, four to the bottom rail, and two to each muntin joint.
6. Initially classified 24 x 81 inches as a nominal glue-up slab target; this provisional decision is superseded by Rev. F after the completed jamb was confirmed.
7. Used a restrained 4-1/2-inch casing and modest backband as defaults, subordinate to surviving house evidence.
8. Require a complete unglued door dry fit before Stage A, then a cured four-tenon lower module, a second complete dry fit, and only then the twenty-six-tenon Stage B glue-up. For both stages, the timed rehearsal and live final geometry/panel-movement gate must finish at or below 75 percent of current published open time; clamp complete is only a checkpoint.
9. Defined the base moulding schedule as one trimmed face plus one three-piece stop set; a second face doubles casing and backband but not the stops.
10. Permitted either a mitered surround or square-butt head only when adjacent original openings support that joint language.
11. Replaced the insufficient `jamb height + 2` side-casing shortcut with conditional longest-point formulas that include casing width for mitered legs.
12. Defined backband as an edge-applied member standing 1/4 inch proud of the casing, glued only to the casing and fitted from the installed work.
13. Confirmed that the restrained default moulding profiles require no dado stack; standard ripping/crosscutting setups prepare the stock and local casing-back relief uses a plunge router or hand tools.
14. Initially segmented the D-101E bottom and D-101F top grooves at 6 and 9 inches from the hinge-side rail shoulder. Rev. F superseded those stations with 5-7/8 and 8-7/8 inches; Rev. G now supersedes the Rev. F stations with 6-1/8 and 9-1/8 inches while preserving the complete 3-inch muntin mortise footprint.
15. Initially set J-11/J-12 mating-rail centers at 7 and 8 inches. Rev. F recentered them to 6-7/8 and 7-7/8 inches; Rev. G now supersedes those receiver stations with 7-1/8 and 8-1/8 inches. D-101G retains two tight mortises at 1 and 2 inches. Sectioned samples must retain at least 0.100 inch from each G mortise to its side groove, at least 0.220 inch between the two G mortises, and at least 0.100 inch between the mating-rail mortises.
16. Moved groove-adjacent frame mortises inward: 4-inch rails use 1.250/2.750, the lock rail uses 1.250/3.500/5.750, and the bottom rail uses 1.250/4.000/7.500/10.750 inches. Actual rail web must remain at least 0.150 inch.
17. Reduced panel tongue projection to 7/16 inch, recalculated all five panels, and relieved the complete 7/16 x 7/16-inch tongue square at every corner so accepted grooves retain bottom clearance.
18. Formerly distinguished a nominal 24 x 81 glue-up target from a field-derived installed slab; Rev. F supersedes that provisional state with a verified 24 x 81 jamb opening and fixed 23-3/4 x 80-1/2 fitted slab.
19. Split the head backband from the side backbands so its rough blank includes 2B beyond the fitted head casing plus 2 inches total fitting allowance.
20. Added scheme-specific side-backband formulas: mitered side casing outer long + B, or square side casing length + C, before the 2-inch rough allowance.
21. Retained the dado stack for conventionally fed through rail grooves and assigned stopped, segmented, and narrow-muntin grooves to a plunge router with positive stops.
22. Made the physical lock envelope and a 1/4-inch clear-wood buffer a release gate before J-06 machining.
23. Require each production-thickness joint sample to close first with untouched full-length factory tenons. Only then may a separate, labeled rehearsal set have its ribs and ends minimally eased for hand removal; rehearsal tenons are never shortened.
24. Use only the adhesive maker's current published open time at measured shop conditions. Both rehearsal and live final geometry/panel-movement gates must finish at or below 75 percent; clamp complete is only a checkpoint.
25. Made M-202C mandatory on every trimmed face. An evidence-supported M-204 cap bears on the completed head backband and finishes at the actual M-202C outside width plus 2P.
26. Fixed permanent post-cure trim order as evidence-supported plinths, casing, backband/self-returns, optional cap, then the door stop last.
27. Added minimum sound-wood embedment gates of 0.75 inch for inner casing and stop, 1.00 inch for outer casing into verified framing, and 0.50 inch for backband into casing, all proven from the actual layer stack on a matching offcut.
28. Protect every fitted slab edge, gain, and hardware seat from final P120 sanding, then rehang on setup hardware and repeat the operating release before finish.
29. Standardized panel control on oil- and silicone-free open-cell foam spacers with a mandatory 3/4-inch longitudinal length, two per vertical side groove, 20 installed plus 10 test/spare. Panel Buddies PB265-750XF-1M, nominally 0.265 x 0.265 x 0.750 inch, is a reference candidate only, not a preapproved product. Its nominal centered-gap compression is about 29.2 percent for H/J/N and 52.8 percent for K/L, versus the manufacturer's 50 percent guidance, so the two panel families require separate full-size sample gates. PB265 additionally requires an actual 0.220-0.250-inch spacer-zone groove or written manufacturer approval. The released candidate or equivalent must match the groove range, firmness or force-deflection, recovery, and finish compatibility while proving residual movement, no joint stress, and no contamination; spacers never create or replace calculated clearance.
30. Issued Rev. D to supersede the former 79-inch nominal slab with an 81-inch nominal glue-up target. Added 1 inch to each opening above D-101D (P-01 = 14.5 and P-02 = 15), retained all rail widths and lower openings, kept the lock center 40 inches above the bottom, recalculated D-101H/J and all affected stile mortise centers, and made every earlier-height story stick and template obsolete.
31. Issued labeled-stock plan LS-01 without changing any Rev. D component size. STOCK-I is conditional for D-101A/B, STOCK-K is conditional for D-101C/M/D/E/G, STOCK-A/C/H/D are assigned to D-101H/J/N/K-L respectively, and D-101F requires a newly purchased one-piece clear 6/4 blank. A laminated bottom rail is not authorized.
32. Superseded LS-01 with LS-02 after the owner confirmed that all STOCK-A through STOCK-L dimensions describe rough-sawn, unjointed, and unplaned lumber. LS-02 withdraws all on-hand frame production credit, makes the complete 26-BF BUY-FRAME-01 package the active purchase, includes one-piece D-101F within that package, and holds STOCK-A/C/H/D as candidate panel stock until CHK-RS-01 and CHK-P-01 prove dressed yield. Rev. D geometry and all controlled component sizes remain unchanged.
33. Issued Rev. E and LS-03 after the owner reserved every STOCK-A through STOCK-L board exclusively for the door. Replaced the LS-02 solid-frame purchase with a conditional balanced three-layer all-long-grain frame: 7/8-inch core plus two 5/16-inch preglue faces, surfaced equally to 1/4 + 7/8 + 1/4 = 1-3/8 inches. D-101D and D-101F use controlled staggered three-plane stave seams; all other listed cores are one piece, and every structural layer is continuous for the member length. No door-lumber purchase is released unless a physical yield or coupon gate fails.
34. Separated the two-face moulding purchase from door stock. Order seven S4S 4/4 x nominal 6-inch x 8-foot quarter-sawn white-oak boards for four side casings, two heads, one full-length casing spare, and one stop mother blank; order two S4S 6/4 x nominal 6-inch x 8-foot boards for both faces of 1-inch finished backband and optional evidence-supported caps. The intended notation is 4/4, not 4 x 4. Plinths remain excluded until field evidence supports them.
35. Issued Rev. F and LS-04 after the owner confirmed the finished jamb opening is consistently 24 x 81 inches and selected a 3/8-inch bottom gap. With 1/8-inch hinge-side, lock-side, and head reveals, the fitted slab is 23-3/4 x 80-1/2 x 1-3/8 inches. The pre-fit assembly is 23-7/8 x 80-5/8 with 1/16 inch removable stock outside every final perimeter edge. Rails finish at 14-3/4 inches; P-01/P-02 become 14-1/4 and 14-3/4; the lower stack and 40-inch lock height remain unchanged. All Rev. E/LS-03 slab, story-stick, panel, and receiver dimensions are obsolete.
36. Issued first-crosscut control RL-01 for the owner-labeled rough stock. After full-length CHK-RS-01 mapping, A/D/G/H receive panel shop billets exactly 1 inch longer than the finished panel length; B/C/I/K remain full length through their continuous-stile gates; E/F remain knot-mapped reserve; and J/L wait for CHK-SM-01. The 2-inch end reserve is total per noncritical board, not per billet, and every tail remains door-only stock.
37. Issued Rev. G, labeled-stock plan LS-05, and first-crosscut control RL-02 as a clean-sheet stock-driven redesign that retains the fixed 23-3/4 x 80-1/2 x 1-3/8-inch slab but eliminates resawing. Finished stiles are 4-1/4 inches, rail shoulders are 15-1/4 inches, lower bays are 6-1/8 inches, full-width panels are 15-7/8 inches, and lower panels are 6-7/8 inches. Muntin footprint stations are 6-1/8 and 9-1/8 inches, with receiver centers at 7-1/8 and 8-1/8 inches. STOCK-I and STOCK-K are each ripped by width into two 4-3/8-inch lanes, one planed to a 7/8-inch core and one to a 5/16-inch face; STOCK-B and STOCK-C each provide one additional 5/16-inch face by staged thickness planing. The bottom-rail core seam remains 5-3/4 inches from the finished top; its show-face seams are 3, 6-1/2, and 9-1/2 inches and its back-face seams are 2-1/2, 5, and 9 inches. All active A-L preparation is jointing, ordinary width ripping, staged thickness planing, resting, and rechecking; Rev. F/LS-04/RL-01 production dimensions and any resaw workflow are obsolete.
38. Recorded STOCK-L at 6 inches wide after edge cleanup, superseding its original 7-inch raw-width entry. The door geometry and D-101F seam location remain unchanged. Revised CM-05 moves the 6-1/2-inch D-101F core stave to STOCK-J and moves the 5-inch D-101D core stave to STOCK-L. J must prove one clear 6-1/2-inch jointed-width envelope before J or L is crosscut; L supplies E, both D core staves, and the 5-3/4-inch F core stave.
39. Recorded STOCK-A at 72-3/4 inches of current usable length after the required removal of a damaged 6-inch section, superseding its original 78-3/4-inch cutting length. D-101H remains conditionally mapped to A without changing door geometry. The shortened plan leaves 22-3/16 inches after the first-stage panel billets and shared 2-inch allowance, and 5-13/16 inches after the conditional 16-1/4-inch A-FACE billet; the panel has priority and physical damage mapping controls.
40. Added owner-labeled STOCK-M, reported finished white oak at 3/4 x 8-1/4 x 99 inches. M becomes the primary D-101H upper-panel source and may provide up to two conditional 16-1/4-inch short-face mother billets after the panel passes. STOCK-A remains intact at its current 72-3/4-inch usable length as the first panel and face-stock reserve. Door geometry, joinery, and the no-resaw rule do not change.
41. Added owner-labeled STOCK-N and STOCK-O, each reported as oak at 1-3/4 x 11 x 74 inches. Because species and surface condition were not stated, both remain uncut under CHK-RS-01. Their 74-inch length cannot replace an 81-inch continuous stile layer; if confirmed compatible white oak, their preferred fallback is short-member 7/8-inch core stock. Door geometry, active A-M assignments, joinery, and the no-resaw rule do not change.
42. Owner confirmed STOCK-N and STOCK-O are finished white oak and the listed 1-3/4 x 11 x 74-inch dimensions are finished measurements. Remove the species/surfacing hold, retain routine moisture/flatness/defect inspection, and keep both full as preferred short-member 7/8-inch core reserve because 74 inches still cannot yield an 81-inch continuous stile layer.
43. Owner confirmed STOCK-G's finished S4S thickness is 15/16 inch, completing its current dimensions at 15/16 x 4-1/2 x 75 inches. The thickness exceeds the 5/8-inch D-101J rough-panel minimum by 5/16 inch; the previously proven width and length margins remain unchanged. Remove only the thickness-measurement hold. CHK-P-01 still controls flatness, moisture, grain, defects, glue-edge cleanup, and the four-billet clear-yield map before crosscutting.
""")
    write(PROJECT / "assumptions.md", """# Assumptions

- The jamb is installed, stable, and not part of fabrication.
- The room is conditioned and oak equilibrates to 6-9 percent moisture content.
- The finished jamb opening is owner-confirmed as consistently 24 x 81 inches. Square, plumb, level, twist, hinge-gain, strike, stop, finished-floor, and swing-path checks remain mandatory.
- The finished fitted slab is 23-3/4 x 80-1/2 x 1-3/8 inches, derived from 1/8-inch side/head reveals and a 3/8-inch bottom gap. It is the maximum rectangular envelope before any handing-specific latch bevel.
- The cured and surfaced pre-fit assembly is 23-7/8 x 80-5/8 inches, carrying 1/16 inch removable stock outside each final perimeter edge. Hook story-stick coordinates from the scribed final-top line.
- No fire-rating, egress, accessibility, or special code requirement has been represented.
- Physical hardware and adjacent trim will be available before irreversible machining.
- Quarter-sawn stock wide enough for the panels can be edge-glued where one-piece stock is unavailable.
- STOCK-A is now a 72-3/4-inch usable rough-sawn envelope after removing a damaged 6-inch section; the new end and any continuation of the defect remain unverified. STOCK-B through STOCK-F and STOCK-H through STOCK-K remain owner-reported rough-sawn envelopes. STOCK-G is confirmed S4S at 15/16 x 4-1/2 x 75 inches. Its thickness exceeds the 5/8-inch D-101J rough-panel minimum by 5/16 inch, and its four-stave width/length plan leaves 6-1/4 inches after the shared end reserve. CHK-P-01 still controls physical yield. STOCK-L is now 6 inches wide after edge cleanup; its faces, thickness, length, flatness, and final dressed yield remain unverified.
- LS-05 supersedes LS-04 for stock yield and procurement. It reserves every A-O board for the door and conditionally maps them to panels, continuous stile layers, short-member layers, same-layup coupons, setup pieces, substitutions, and repair stock without resawing. N/O are confirmed finished white oak and remain uncut short-member reserve.
- RL-02 controls first crosscuts: after CHK-RS-01, only its released panel and short-member billets may be cut; B/C/I/K remain full length until both continuous-stile gates pass, J/L remain uncut until revised CM-05 proves J's 6-1/2-inch F-core envelope and assigns L both D-core staves, and every face-pool or knot-mapped reserve remains on hold until FP-05 assigns it.
- Door-lumber purchase remains zero only while the full physical yield map and every lamination coupon pass. A failed continuous stile layer is replaced with a new long clear board; it is never end-spliced, narrowed, or patched.
- Every frame member uses the balanced 5/16 + 7/8 + 5/16 preglue schedule, finished symmetrically to 1/4 + 7/8 + 1/4. Cores and faces are produced by jointing, ordinary width ripping where assigned, staged thickness planing, resting, and rechecking; no A-O board is resawn. All grain runs with the member and no structural layer contains an end joint.
- Moulding uses a separate S4S order for both faces: seven 4/4 x nominal 6-inch x 8-foot boards and two 6/4 x nominal 6-inch x 8-foot boards. No A-O stock is credited to moulding.
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
- [ ] Actual 3/4-inch-long foam spacer manufacturer, SKU, cross-section, and firmness/force-deflection recorded; separate full-size H/J/N and K/L samples released before panel loading
- [ ] LS-05 CHK-RS-01 records species, moisture, minimum dimensions, bow, cup, twist, checks, knots, pith, grain runout, and clear squared-end limits for A-O before critical crosscuts; N/O are confirmed finished white oak and remain full until a signed short-core fallback is required
- [ ] LS-05 CHK-ST-01 proves STOCK-B/C each yield one continuous 5/16 x 4-3/8 x 81-1/8-inch stile show face by the coupon-proven staged plane/rest/carrier method; no A-O board is resawn
- [ ] LS-05 CHK-ST-02 proves STOCK-I/K each yield two continuous 4-3/8-inch lanes by ordinary width ripping: one 7/8 x 4-3/8 x 81-inch core and one 5/16 x 4-3/8 x 81-1/8-inch back face after staged planing and rest
- [ ] LS-05 CHK-SM-01 signs CM-05 before J/L are cut and proves every short-member core billet without consuming a critical stile lane
- [ ] LS-05 CHK-FP-01 signs FP-05 and assigns every C/M/D/E/F/G show/back face strip, all controlled D/F seam stations, coupons, and repair reserve from the released face pool
- [ ] LS-05 CHK-P-01 releases the mapped panel sources only after every planned stave proves post-flattening thickness, aggregate clean width, clear squared length, grain, color, and defect placement
- [ ] LS-05 CHK-LAM-01 destructively releases same-layup coupons at 5/16 + 7/8 + 5/16 preglue and 1/4 + 7/8 + 1/4 finished, with no void and at least 0.200 inch actual core wood beyond cutter envelopes
- [ ] LS-05 CHK-SEAM-01 verifies every released D-101D and D-101F core/show/back seam against the LS-05 map, within +/-1/32 inch and clear of the mortise planforms
- [ ] Separate moulding stock received: seven S4S 4/4 x 6 x 8-foot boards and two S4S 6/4 x 6 x 8-foot boards; no plinths unless field evidence releases them
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
        ["S-08", "OSHA 29 CFR 1910.213 Woodworking machinery requirements", "https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.213", "guards, push tools, machine controls, and woodworking-machine safety baseline", "2026-07-24"],
        ["S-09", "NIOSH Control of Wood Dust from Table Saws", "https://www.cdc.gov/niosh/docs/hazardcontrol/hc10.html", "local exhaust and wood-dust exposure control", "2026-07-24"],
        ["S-10", "Rubio Monocoat Oil Plus 2C Technical Data Sheet", "https://service.rubiomonocoat.com/hubfs/TDS%20Oil%20Plus%202C%20-%20EN-2.pdf?hsLang=en", "current surface preparation, mixing, application, dry, and cure controls", "2026-07-24"],
        ["S-11", "DEWALT DWFP72155 Finish Nailer Instruction Manual", "https://www.dewalt.com/GLOBALBOM/QU/DWFP72155/0/Instruction_Manual/EN/9R209197_DWFP72155.pdf", "representative sequential-actuation and jam-clearing controls; actual nailer manual governs", "2026-07-24"],
        ["S-12", "SawStop dado compatibility and safety FAQ", "https://www.sawstop.com/why-sawstop/faqs/", "8-inch stacked dado, dado brake cartridge, zero-clearance insert, and prohibited dado types; actual saw manual governs", "2026-07-24"],
        ["S-13", "Panel Buddies PB265-750XF-1M candidate", "https://panelbuddies.com/products/pb265-750xf-1m", "reference-candidate data only: 0.265 x 0.265 x 0.750-inch extra-firm open-cell foam spacer for 0.220-0.250-inch groove heights; project sample gates still control", "2026-07-24"],
        ["S-14", "Panel Buddies manufacturer home page", "https://panelbuddies.com/", "manufacturer states Panel Buddies products are made to be compressed 50 percent; project geometry therefore requires separate full-width and lower-panel sample gates", "2026-07-24"],
    ])
    domino_register()
    cut_lists()
    illustration_register()
    manuscript_sources()
    style_sources()
    template_sources()


def domino_register() -> None:
    header = [
        "Joint ID", "Joint family", "Part A", "Part B", "Domino model",
        "Cutter diameter", "Tenon dimensions", "Number of tenons",
        "Plunge depth Part A", "Plunge depth Part B", "Fence height", "Fence angle",
        "Mortise-width setting Part A", "Mortise-width setting Part B",
        "Tight or loose designation Part A", "Tight or loose designation Part B",
        "Tenon centerline Part A from reference edge",
        "Tenon centerline Part B from reference edge",
        "Reference face", "Reference edge Part A", "Reference edge Part B",
        "Test-piece identifier", "Dry-fit result", "Final verification status", "Notes",
    ]
    rows = [header]
    for jid, family, a, b, cutter, tenon, count, plunge, centers in JOINTS:
        is_muntin = jid in {"J-11", "J-12"}
        standard_widths = "first tight; remaining medium"
        designation = "T," + ",".join("L" for _ in range(count - 1)) if count > 1 else "T"
        width_a = "both tight" if is_muntin else standard_widths
        width_b = "first tight; second medium" if is_muntin else standard_widths
        designation_a = "T,T" if is_muntin else designation
        designation_b = "T,L" if is_muntin else designation
        reference_b = "hinge-side rail shoulder" if is_muntin else "finished top of stile"
        notes = (
            "balanced 1/4+7/8+1/4 finished layup; retain >=0.200 in actual core wood to each face glue line; D-101G groove-to-mortise web >=0.100 in; D-101G inter-mortise web >=0.220 in; mating-rail inter-mortise web >=0.100 in; groove segmented 0-6-1/8 and 9-1/8-15-1/4 in"
            if is_muntin
            else (
                "balanced 1/4+7/8+1/4 finished layup; retain >=0.200 in actual core wood to each face glue line; D-101D seams core/show/back 2.250/4.375/4.875 in from top +/-1/32; physical lock envelope plus 0.250 in clear wood must pass before J-06; frame rail web to groove >=0.150 in"
                if jid == "J-06"
                else (
                    "balanced 1/4+7/8+1/4 finished layup; retain >=0.200 in actual core wood to each face glue line; D-101F core seam 5.750, show seams 3.000/6.500/9.500, back seams 2.500/5.000/9.000 in from top +/-1/32; stile grooves stopped; frame rail web to groove >=0.150 in where applicable"
                    if jid in {"J-09", "J-10"}
                    else "balanced 1/4+7/8+1/4 finished layup; retain >=0.200 in actual core wood to each face glue line; stile grooves stopped; frame rail web to groove >=0.150 in where applicable"
                )
            )
        )
        rows.append([
            jid, family, a, b, "DF 500", f"{cutter} mm", f"{tenon} mm", str(count),
            f"{plunge} mm", f"{plunge} mm", "17.5 mm", "90 deg",
            width_a, width_b, designation_a, designation_b,
            "; ".join(f"{x:.4f} in" for x in centers),
            "; ".join(f"{x:.4f} in" for x in PART_B_CENTERS[jid]),
            "show face", "top/left marked reference", reference_b,
            f"TP-{jid[2:]}", "required before production",
            "design verified; shop verification pending", notes,
        ])
    csv_write(PROJECT / "domino-setup-register.csv", rows)


def cut_lists() -> None:
    header = ["Part identifier", "Part name", "Quantity", "Rough thickness", "Rough width", "Rough length", "Finished thickness", "Finished width", "Finished length", "Grain orientation", "Board assignment", "Domino-joint notes", "Groove notes", "Panel-opening relationship", "Field-fit status", "Chapter reference", "Figure reference"]
    rows = [header]
    lamination_by_part = {
        row["part"]: row for row in LABELED_STOCK["laminated_member_schedule"]
    }
    construction = SPEC["frame"]["construction"]
    for c in SPEC["components"]:
        panel = "panel" in c["name"].lower()
        if panel:
            rt = SPEC["milling"]["panel_rough_thickness"]
            rw = c["w"] + SPEC["milling"]["panel_rough_width_allowance"]
            rl = c["l"] + SPEC["milling"]["panel_rough_length_allowance"]
        else:
            is_stile = "stile" in c["name"].lower()
            is_muntin = "muntin" in c["name"].lower()
            rt = construction["glue_blank_thickness"]
            rw = c["w"] + (
                SPEC["milling"]["stile_glue_blank_width_allowance"]
                if is_stile
                else SPEC["milling"]["frame_rough_width_allowance"]
            )
            rl = (
                SPEC["milling"]["stile_face_length"]
                if is_stile
                else (
                    c["l"] + SPEC["milling"]["muntin_rough_length_allowance_total"]
                    if is_muntin
                    else c["l"] + SPEC["milling"]["rail_rough_length_allowance_total"]
                )
            )
        rows.append([c["id"], c["name"], str(c["qty"]), f"{rt:.4f}", f"{rw:.4f}", f"{rl:.4f}", f"{c['t']:.4f}", f"{c['w']:.4f}", f"{c['l']:.4f}", "vertical" if panel or "stile" in c["name"].lower() or "muntin" in c["name"].lower() else "horizontal", labeled_stock_assignment(c["id"]), "see Domino register after lamination" if not panel else "none", "floating tongue both applicable edges" if panel else "machine only after CHK-LAM-01; see groove schedule", "derived from specification", "fixed; slab perimeter field-fit only", "40 / 70 / 150", "Fig. 2 / Fig. 7"])
        if not panel:
            schedule = lamination_by_part[c["id"]]
            is_stile = "stile" in c["name"].lower()
            is_muntin = "muntin" in c["name"].lower()
            layer_width = rw
            core_length = (
                SPEC["milling"]["stile_core_length"]
                if is_stile
                else (
                    c["l"] + SPEC["milling"]["muntin_rough_length_allowance_total"]
                    if is_muntin
                    else c["l"] + SPEC["milling"]["rail_rough_length_allowance_total"]
                )
            )
            face_length = SPEC["milling"]["stile_face_length"] if is_stile else core_length
            for suffix, layer_name, thickness, length, stock in [
                ("CORE", "long-grain core sheet", construction["core_preglue_thickness"], core_length, schedule["core_stock"]),
                ("SF", "show-face lamella/sheet", construction["show_face_preglue_thickness"], face_length, schedule["show_face_stock"]),
                ("BF", "back-face lamella/sheet", construction["back_face_preglue_thickness"], face_length, schedule["back_face_stock"]),
            ]:
                rows.append([
                    f"{c['id']}-{suffix}",
                    f"{c['name']} {layer_name}",
                    "1",
                    f"{thickness:.4f}",
                    f"{layer_width:.4f}",
                    f"{length:.4f}",
                    f"{thickness:.4f}",
                    f"{layer_width:.4f}",
                    f"{length:.4f}",
                    "continuous with member",
                    f"{stock}; {schedule['seams']}",
                    "no joinery before lamination",
                    "no groove before lamination",
                    "lamination subpart for parent assembly",
                    "conditional on LS-05 no-resaw physical yield and coupon release",
                    "40 / 50 / 70",
                    "balanced-lamination section",
                ])
    csv_write(BUILD / "reports" / "cut-list.csv", rows)
    buy = [
        ["Category", "Item", "Specification", "Quantity", "Purpose", "Selection notes", "Substitution constraints", "Field verification", "Chapter"],
        ["Lumber", "Owner-labeled door stock A-O", "A current usable length 72-3/4 inches; B-F/H-K rough-sawn envelopes except G is confirmed S4S at 15/16 x 4-1/2 x 75; L width 6 inches; M finished 3/4 x 8-1/4 x 99; N/O each finished 1-3/4 x 11 x 74; LS-05 no-resaw map", "IN HAND - approximately 71.52 BF from all boards with recorded dimensions; STOCK-G confirmed 15/16 x 4-1/2 x 75; no door-lumber purchase released", "all frame layers, five panels, same-layup coupons, setup pieces, substitutions, and repair reserve", "preserve long boards until CHK-RS-01; G thickness/width/length pass, but CHK-P-01 still controls its four-stave panel map; verify M and use it for D-101H while keeping A intact; keep N/O full; prove every jointed, width-ripped, staged-planed, and rested billet", "no resawing, no end-jointed structural layer, no stile narrower than 4-1/4 inches, no cross-grain layer, and no transfer to moulding before final door release", "LS-05 CHK-RS-01, CHK-ST-01/02, CHK-SM-01, CHK-FP-01, CHK-P-01, CHK-LAM-01, and CHK-SEAM-01", "30/40/50/70"],
        ["Moulding stock", "Two-face casing and one stop set", "S4S quarter-sawn white oak, 4/4 x nominal 6 inches x 8 feet; 13/16-inch actual thickness preferred and never less than 3/4 inch at the thinnest point", "7 boards", "four side casings, both head casings, one full-length casing spare/match board, and one three-piece stop mother blank", "buy color- and grain-matched stock long enough for the completed-opening field formulas", "4/4 means four-quarter thickness, not 4 x 4; does not yield the 1-inch finished backband", "two trimmed faces; no plinths included; field worksheet controls final cuts", "220"],
        ["Moulding stock", "Two-face backband and optional square-head caps", "S4S quarter-sawn white oak, 6/4 x nominal 6 inches x 8 feet; minimum actual 1-1/4 x 5-1/2 x 96 inches", "2 boards", "four side backbands and two head backbands; also yields two optional caps only if square-head field evidence supports them", "one board per face; confirm 1-inch finished backband yield before purchase", "4/4 is too thin for the specified 1-inch backband; no plinth stock included", "two trimmed faces; field evidence controls caps", "220"],
        ["Domino", "Factory beech tenons", "10 x 50 mm", "60 total: 26 final + 26 retained test + 8 spare", "rail-to-stile joints", "segregate final, test, and spare stock", "DF 500 compatible only", "fit on test pieces", "100-140"],
        ["Domino", "Factory beech tenons", "6 x 40 mm", "12 total: 4 final + 4 retained test + 4 spare", "muntin joints", "segregate final, test, and spare stock", "no random scrap tenons", "fit on test pieces", "140"],
        ["Domino", "Cutters", "sharp 10 mm and 6 mm DF 500 cutters", "1 each", "mortising", "inspect edge and shank", "not DF 700 cutters", "test cut", "100"],
        ["Hardware", "Mortise lock set", "traditional brass, complete with strike and knobs", "1 set", "latching and privacy", "physical sample required", "no invented dimensions", "all dimensions", "210"],
        ["Hardware", "Butt hinges", "3-1/2-inch brass, loose-pin or period-compatible", "3", "hanging", "matching visible screws", "leaf thickness field-gated", "actual leaves/screws", "200"],
        ["Adhesive", "Type II PVA", "fresh, within shelf life; manufacturer-approved for full-area oak lamination", "32 oz minimum planning quantity; verify coverage against the actual layup area", "core/face-sheet edge glue-ups, balanced frame laminations, and panel edge glue-ups", "verify spread rate, open time, clamp pressure, temperature, and cure on same-layup coupons", "no polyurethane foaming adhesive; do not combine adhesive systems within a member", "shop temperature, moisture, coupon failure mode, and actual coverage", "50/70/170"],
        ["Panel control", "3/4-inch-long foam panel spacers", "oil- and silicone-free open-cell foam; record manufacturer/SKU/cross-section/firmness; PB265-750XF-1M is a reference candidate only, not preapproved", "30 controlled minimum: 20 installed + 10 test/spare; order 40 for a practical one-trip reserve", "anti-rattle control; two per vertical side groove only", "0.750 inch is longitudinal length; separately release full-size H/J/N and K/L samples for compression, residual travel, no joint stress, recovery, and finish compatibility", "do not widen the groove, replace calculated clearance, use rigid packing, or infer one-family approval from the other", "measure spacer-zone groove; PB265 requires 0.220-0.250 inch or written manufacturer approval, plus two-family gates", "150/160"],
        ["Finish", "Rubio Monocoat Oil Plus 2C", "Pure", "350 mL set", "door and trim", "make sample first", "follow current TDS", "color match", "230"],
        ["Consumables", "Abrasives", "P80/P100/P120 discs and hand sheets", "shop pack", "surface preparation", "fresh, clean abrasive", "stop at P120 unless current TDS differs", "surface sample", "180/230"],
        ["Jig materials", "MDF-free stable plywood", "1/2 and 3/4 inch Baltic birch", "dimensioned shop offcuts; if unavailable, buy one half-sheet of each required thickness", "story sticks, supports, templates", "flat and dry", "jigs only; not door components", "machine fit", "60/80"],
        ["Safety", "Oily-waste container", "lidded metal can or water-filled sealed metal container", "1", "combustion control", "label before finishing", "required", "local disposal rules", "230"],
    ]
    csv_write(BUILD / "reports" / "buy-list.csv", buy)
    mould = [
        ["Part identifier", "Part name", "Quantity", "Rough thickness", "Rough width", "Rough length", "Finished thickness", "Finished width", "Finished length", "Profile", "Grain orientation", "Field-fit allowance", "Installation location", "Fastener type", "Finish requirement"],
        ["M-201A/B", "Side casing", "2 per trimmed face", "1.0", "4.75", "longest required point + 2; mitered long point = H side + R + C + 2", "0.75", "4.5", "field transfer", "flat, visible arrises eased 1/32", "vertical paired grain", "2 inches total", "jamb sides", "18-ga inner: >=0.75 in sound jamb; 15-ga outer: >=1.0 in verified framing after actual layer-stack calculation and offcut proof", "Rubio Pure; approved sample controls"],
        ["M-201C", "Head casing", "1 per trimmed face", "1.0", "4.75", "W + 2R + 2C + 2", "0.75", "4.5", "field transfer", "flat, visible arrises eased 1/32", "horizontal", "2 inches total", "jamb head", "18-ga inner: >=0.75 in sound jamb; 15-ga outer: >=1.0 in verified framing after layer-stack/offcut proof", "Rubio Pure; approved sample controls"],
        ["M-202A/B", "Side backband", "2 per trimmed face", "1.25", "1.375", "mitered: fitted side-casing outer long + B + 2; square: fitted side-casing length + C + 2", "1.0", "1.125", "field transfer", "edge-applied; face 1/4 proud; arrises eased 1/32", "vertical", "2 inches beyond scheme-specific finished target", "casing sides", "18-ga >=0.50 in into casing without exit/split after offcut proof; returns remain dry until post-cure install", "Rubio Pure; approved sample controls"],
        ["M-202C", "Mandatory head backband", "1 per trimmed face", "1.25", "1.375", "fitted head-casing outside width + 2B + 2", "1.0", "1.125", "field transfer", "edge-applied; face 1/4 proud; arrises eased 1/32", "horizontal", "2 inches beyond finished target", "casing head; supports optional M-204 above", "18-ga >=0.50 in into casing without exit/split after offcut proof; glue only to casing after cure", "Rubio Pure; approved sample controls"],
        ["M-203A-C", "Door stop", "3 total per opening", "0.5", "1.5", "jamb member + 2; fit head first and sides beneath", "0.375", "1.25", "field transfer from operating door", "flat, door-side arris eased 1/16", "long grain", "2 inches total", "jamb stop line; install last", "18-ga >=0.75 in into sound jamb after layer-stack/offcut proof; complete only after cycling door", "Rubio Pure; approved sample controls"],
        ["M-204", "Optional head cap over M-202C", "1 per treated face", "1.0", "1.75", "actual fitted head-backband outside width + 2P + 2", "0.875", "1.5", "field transfer", "restrained 1/8 chamfer only after sample approval", "horizontal", "2 inches total", "atop completed M-202C on field-supported square-butt head", "masked cap-to-head-band glue joint after cure; released concealed/top fasteners", "Rubio Pure; approved sample controls"],
        ["M-205A/B", "Optional plinth blocks", "2 per treated face", "1.125", "field profile + 0.25", "field dimension + 0.25", "0.875", "field verify", "field verify", "flat, evidence-matched", "vertical", "1/4 inch", "install first after cure as casing bottom datum", "finish nails into verified substrate; masked plinth-to-trim glue only, never floor/wall", "Rubio Pure; approved sample controls"],
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
        "00-cover.md": f"# Building a Historically Appropriate Five-Panel Door\n\nA Complete Illustrated Shop Manual for Building a Historically Appropriate 1916 Dutch Colonial Revival Interior Door with Festool Domino DF 500 Loose-Tenon Joinery\n\nProject DC-1916-001 | First Edition | {SPEC['project']['revision']} | 2026",
        "01-title-page.md": f"# Title Page\n\n**Building a Historically Appropriate Five-Panel Door**\n\nA complete illustrated shop manual for one 23-3/4 x 80-1/2 x 1-3/8 inch quarter-sawn white-oak fitted slab for a confirmed 24 x 81 inch jamb opening.\n\nHistorically appropriate reproduction door using modern concealed joinery.\n\nJayson Guglietta | Project DC-1916-001 | First Edition | {SPEC['project']['revision']} | 2026",
        "02-copyright.md": "# Publication Data and Disclaimer\n\nCopyright (c) 2026 Jayson Guglietta. All rights reserved.\n\nThis manual is educational and project-specific. The completed jamb and opening must be measured before final fitting. Actual hardware must be measured before machining. Woodworking tools can cause serious injury; the builder is responsible for safe operation. Local code requirements remain the builder's responsibility. No ISBN, certification, endorsement, or exact historical provenance is claimed.",
        "03-safety.md": "# Safety Is a Build Requirement\n\n- Read and follow every machine manufacturer's current instructions.\n- Keep the jointer guard installed; never joint stock shorter than the machine maker permits.\n- Use push blocks and appropriate non-through-cut guarding for the dado stack. Confirm the cartridge/blade compatibility required by the SawStop manual.\n- Stand clear of planer kickback; support stock without pulling it through. Respect the planer's minimum work thickness and use a flat carrier sled with a positive trailing stop when required; never feed a loose thin strip on an unsecured carrier.\n- Unplug the DF 500 before cutter changes. Change mortise width only with the motor running and never during a plunge.\n- Clamp router and Domino work. Narrow work must be held by a jig, never by fingers.\n- White-oak dust is a respiratory irritant: use extraction and a suitable respirator.\n- Establish brass screw holes with matching steel screws; drive brass by hand.\n- Oily finish cloths can self-heat. Lay them flat outdoors to cure or place them under water in a sealed metal container for lawful disposal.",
        "04-how-to-use-this-manual.md": "# How to Use This Manual\n\nStart with the confirmed-jamb and hardware worksheets. Then read the Rev. G engineering audit, specification, labeled-stock plan LS-05, and first-crosscut plan RL-02 before buying or cutting lumber. The confirmed opening is 24 x 81 inches; the fitted slab is 23-3/4 x 80-1/2 x 1-3/8 inches with 1/8-inch side/head reveals and a 3/8-inch bottom gap. Dimensions in the specification are fixed unless labeled field verify. LS-05 reserves every owner-labeled A-O board for the door and maps a balanced laminated frame made without resawing. Board G is confirmed S4S at 15/16 x 4-1/2 x 75; Board M is the primary upper-panel source; damaged Board A remains intact; confirmed finished-white-oak Boards N/O remain uncut short-member reserve. Reported dimensions do not by themselves prove jointed, planed, rested, defect-free yield; all boards still require physical condition and clear-yield checks. No door-lumber purchase is released unless a signed yield or coupon gate fails. Moulding uses a separate two-face S4S order. The story stick controls rail location from the scribed final-top line; the Domino register controls mortises; the layer and component cut lists control parts. A failed stock, staged-planing, lamination, seam, panel, or hardware gate stops production. Blue callouts identify fixed dimensions, amber callouts identify field gates, and red callouts identify safety stop conditions.",
        "05-table-of-contents.md": "# Table of Contents\n\n1. Project overview and historical appearance\n2. Procurement, cut lists, lumber, and shop preparation\n3. Milling, story sticks, and panel grooves\n4. DF 500 engineering and mortising\n5. Solid panels, dry assembly, and glue-up\n6. Surfacing, completed-jamb fitting, hinges, and lock\n7. Matching millwork, finish, installation, inspection, and maintenance\n8. Appendices: registers, field gates, references, and tolerances",
    }
    overview = """# Project Overview

The result is one five-panel interior slab for a 1916 Dutch Colonial Revival context. The visible design uses quarter-sawn white oak, a substantial bottom rail, recessed solid panels, restrained profiles, and traditional brass hardware. Concealed 10 x 50 mm and 6 x 40 mm factory beech Domino tenons replace integral mortise-and-tenon construction.

The five panels are D-101H, D-101J, D-101N, D-101K, and D-101L. The top three span the 15-1/4-inch frame opening. D-101G divides the bottom opening into two 6-1/8-inch bays. D-101M is the additional upper intermediate rail required to make the source brief dimensionally possible.

The installed jamb opening is confirmed at 24 x 81 inches. With 1/8-inch reveals at both sides and the head plus a 3/8-inch bottom gap, the finished fitted slab is 23-3/4 x 80-1/2 x 1-3/8 inches. Build the cured/surfaced pre-fit assembly to 23-7/8 x 80-5/8 inches, then scribe and trim the final rectangle. Hinge gains, latch bevel, lock machining, strike location, stop placement, and trim lengths still depend on the installed jamb, floor, handing, and physical hardware.
"""
    special = {
        "10-project-overview.md": overview,
        "20-historical-appearance.md": (PROJECT / "historical-appearance-standard.md").read_text() if (PROJECT / "historical-appearance-standard.md").exists() else "",
        "30-buy-list.md": "# Buy List\n\n## Door lumber: in hand, conditional on LS-05\n\nReserve STOCK-A through STOCK-O exclusively for the door, same-layup coupons, setup pieces, substitutions, and repair stock. The complete recorded inventory totals approximately 71.52 current-envelope board feet. STOCK-G is confirmed S4S at 15/16 x 4-1/2 x 75 inches. Its thickness exceeds the 5/8-inch D-101J rough-panel minimum by 5/16 inch, and its four-stave width and length plan fits; CHK-P-01 still controls flatness, moisture, grain, defects, glue-edge cleanup, and four clear billet zones before crosscutting. STOCK-M is reported finished at 3/4 x 8-1/4 x 99 inches and carries D-101H; damaged STOCK-A remains intact at 72-3/4 inches. STOCK-N and STOCK-O are each confirmed finished white oak at 1-3/4 x 11 x 74 inches. Keep both full while CHK-RS-01 records moisture, grain, flatness, defects, and clear yield. Their preferred fallback is short-member core stock; neither can replace an 81-inch stile layer. The current general door-lumber purchase remains zero, but dimensions alone do not prove clear yield. Complete CHK-RS-01, CHK-ST-01/02, CHK-SM-01, CHK-FP-01, CHK-P-01, CHK-LAM-01, and CHK-SEAM-01 before production cutting. If a full-length stile core or face fails, buy a replacement continuous long board rather than splice or narrow the 4-1/4-inch stile. If CM-05 fails, first consider clear N/O short-core stock; if FP-05 fails, purchase only the missing face billet rather than planing 1-3/4-inch reserve to 5/16 without a signed waste review.\n\n## Separate two-face moulding order\n\nOrder seven S4S quarter-sawn white-oak boards, 4/4 x nominal 6 inches x 8 feet: four side-casing boards, one board for both heads, one full-length casing spare/match board, and one stop mother blank. Order two S4S quarter-sawn white-oak boards, 6/4 x nominal 6 inches x 8 feet: both faces of side/head backband and up to two optional caps if square-head field evidence supports them. This is approximately 40 dealer board feet. The intended notation is 4/4, not 4 x 4; four-quarter stock cannot yield the specified 1-inch finished backband. Plinths are excluded until field evidence supports them.\n\nObtain at least 30 oil- and silicone-free open-cell foam panel spacers with a mandatory 3/4-inch longitudinal length; 40 is the recommended one-trip purchase quantity. Record the actual manufacturer, SKU, cross-section, groove range, and firmness or force-deflection. PB265-750XF-1M (0.265 x 0.265 x 0.750 inch) is a reference candidate only; its published 50-percent compression guidance requires separate full-size H/J/N and K/L release samples in this geometry. Reserve 20 released production pieces, at least 8 for the two family tests, and additional pieces for spares or an alternate candidate.\n\nHardware, Domino tenons and cutters, at least 32 ounces of fresh manufacturer-approved Type II PVA subject to actual coverage, finish, abrasives, dimensioned 1/2- and 3/4-inch jig-plywood offcuts, and combustion-safe waste control are required before their operation begins.",
        "40-cut-list.md": "# Rough, Layer, and Finished Cut Lists\n\nThe release CSV derives every fixed part from the specification and adds traceable -CORE, -SF show-face, and -BF back-face blanks for the eight laminated frame members. Rev. G governs the 23-3/4 x 80-1/2 x 1-3/8-inch fitted slab while LS-05 controls how frame thickness and stock yield are produced without resawing. RL-02 is the separate first-crosscut guide: B/C/I/K remain full length through both continuous-stile gates, M/D/G/H are the only initial panel-crosscut boards, and A/N/O remain intact as reserve. N/O are only 74 inches long and cannot become continuous stile layers. Rails finish at the 15-1/4-inch shoulder length because loose-tenon construction has zero integral-tenon end allowance. Rail mother billets are 16-1/4 inches. Stile cores are 81 inches, continuous stile faces are 81-1/8 inches, and the final stile length is 80-1/2 inches after the pre-fit assembly is scribed and trimmed.\n\nEvery frame blank starts as 5/16 show face + 7/8 core + 5/16 back face = 1-1/2 inches and is surfaced equally to 1/4 + 7/8 + 1/4 = 1-3/8 inches. I/K are ordinarily width-ripped into paired 4-3/8-inch stile lanes; B/C each provide one continuous 4-3/8-inch face. All layer thicknesses are made by staged thickness planing with rest and recheck gates. The Board assignment column records the LS-05 A-O overlay and controlled D/F seam maps. Do not machine grooves, Domino mortises, hinges, or the lock until the relevant lamination has cured, rested, been surfaced symmetrically, and passed its destructive coupon.\n\nThe listed sizes are controlled post-selection billet targets, not descriptions of raw lumber. A reported-finished, rough-sawn, or unspecified-surface measurement never authorizes thinning or narrowing a part. Panel sizes include two 7/16-inch tongue projections, minus movement clearance. Never replace a calculated component with a vague field length.",
        "100-domino-engineering.md": "# DF 500 Joint Engineering\n\nThe DF 500 accepts 5, 6, 8, and 10 mm cutters and has 12, 15, 20, 25, and 28 mm plunge presets. Frame joints use 10 x 50 mm factory beech tenons with 25 mm plunges in each member. The center muntin uses 6 x 40 mm tenons with 20 mm plunges.\n\nAll mortises are cut after balanced lamination, cure, rest, and final 1/4 + 7/8 + 1/4 surfacing. The 17.5 mm show-face fence setting keeps both 10 mm and 6 mm cutter envelopes in the 7/8-inch core; sectioned production-family coupons must retain at least 0.200 inch actual core wood from the cutter envelope to either face glue line.\n\nFrame joints use one tight locating mortise and medium-width followers on both members. Four-inch rails receive two tenons, the 7-inch lock rail receives three, and the 12-inch bottom rail receives four. J-11/J-12 are deliberately different: both mortises in D-101G are tight, while the mating D-101E/D-101F pair is first tight and second medium. A medium follower in the 3-inch muntin would intersect its right side groove.\n\nStile grooves stop before every joint. The D-101E bottom and D-101F top grooves stop at 6-1/8 inches and restart at 9-1/8 inches from the hinge-side shoulder, leaving a solid muntin footprint. Receiver centers are 7-1/8 and 8-1/8 inches. Sectioned TP-11/TP-12 samples must retain at least 0.100 inch from each G mortise to its side groove, at least 0.220 inch between the G mortises, and at least 0.100 inch between the receiver mortises. Test pieces TP-01 through TP-12 are retained until final glue-up.",
        "110-domino-test-pieces.md": "# Domino Test Pieces\n\nMake a full-thickness labeled pair for every joint family, using the production cutter, plunge, fence height, reference face, and mortise-width strategy. Mark cutter size, date, joint ID, and operator. First prove that untouched full-length factory tenons seat by controlled hand pressure, close the shoulder without a clamp, and leave faces within 0.010 inch flush. Only after that gate passes, minimally ease the ribs and ends of a separate labeled rehearsal set enough for repeated hand removal; never shorten a tenon. A test mortise that intersects a groove, exposes the face, merges with another mortise, or requires hammering fails. Correct the setup and make a new test pair.",
        "180-flush-and-surface.md": "# Flush, Scrape, and Surface\n\nLet the adhesive reach full cure and mask or otherwise protect every fully cured prefinished panel. Remove squeeze-out with a scraper rather than washing oak pores with water. Use a finely set smoothing plane across frame joints only after checking grain direction; stop before changing the 1-3/8-inch perimeter reference. Scrape ray-flecked frame surfaces in raking light and sand the frame only through P100 before completed-jamb fitting and hardware machining; never abrade a cured panel surface. Joint faces must remain flush within 0.010 inch; any larger error requires documented correction or remake, not hollowing the surrounding face. Final P120 sanding is limited to unfitted frame faces and removable trim after completed-jamb fitting and all hardware/trim dry fitting. Do not sand the fitted hinge edge, lock bevel, head/bottom edges, hinge gains, faceplate seat, strike seat, or any other fitted register. Rehang with setup hardware after P120 and repeat the complete operating release before finish.",
        "240-final-installation.md": "# Final Installation\n\nProtect the fully cured finished slab. Remove the steel setup screws and install final brass hinge screws by hand only after the finish has reached full cure under the current technical data sheet. Hang the slab and confirm a free swing through the full arc. Fit the strike from the actual latch location. After the trim finish reaches full cure, install evidence-supported plinths first as the casing bottom datum without glue to floor or wall; then install casing, mandatory backband and post-cure-glued self-returns, optional cap atop M-202C, and the door stops last. With the door latched and reveals proven, tack and cycle the stops before completing their fasteners. Record final reveals, undercut, hinge screws, lock operation, fastener embedment proofs, and finish condition.",
        "250-inspection-and-troubleshooting.md": "# Inspection and Troubleshooting\n\nInspect in daylight and raking light. Confirm five panels, vertical panel grain, uniform reveals, free swing, continuous stop contact, latch engagement without lifting, flush hinge leaves, seated brass screws, aligned backband, tight casing joints, and an even low-sheen finish.\n\nA binding corner usually indicates jamb twist, an uncarried bevel, or a high slab edge. A door that falls open indicates jamb or hinge-axis error. A rattling panel needs the approved 3/4-inch-long foam spacer and a repeat movement check, never glue or rigid packing. A panel that sticks with the spacers installed requires correction of finish/glue bridging or rejection of the spacer/sample combination; never widen the groove or reduce the calculated movement clearance. A lock that requires lifting the door indicates strike or sag diagnosis before enlarging the strike.",
        "260-maintenance.md": "# Maintenance\n\nDust with a dry soft cloth. Clean only with products compatible with the finish maker's current guidance. Do not flood panel edges. Each heating and cooling season, check panel freedom, stop contact, brass screw tightness, and latch alignment. Correct moisture sources before planing a swollen edge. Retain labeled finish samples, hardware measurements, and the final field worksheet with the house records.",
        "270-appendices.md": "# Appendices\n\nThe release package contains the authoritative Rev. G specification, labeled-stock plan LS-05, first-crosscut plan RL-02, detailed layer cut sheet, Domino setup register, buy and cut lists, printable templates, two-face moulding drawings and field worksheet, build report, and checksums. LS-05 reserves all A-O stock for the door and replaces LS-04 with a conditional no-resaw balanced-lamination plan for the 23-3/4 x 80-1/2 fitted slab. RL-02 makes the safe cut-now versus full-length-hold decision for every owner-labeled board, including the confirmed finished-white-oak N/O short-core reserve. The source register distinguishes period evidence from modern manufacturer data. If any fixed dimension, layer schedule, seam location, or field-controlled trim choice changes, update the specification first, rebuild all outputs, and rerun validation.",
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
             "Read LS-05 and RL-02 before marking. Treat A's current usable length as 72-3/4 inches after the required 6-inch damage removal; inspect the new end and map any continuation before layout. Treat B-F and H-K as rough, unjointed, unplaned, and non-datum. G is confirmed S4S at 15/16 x 4-1/2 x 75 inches; thickness/width/length pass D-101J, but CHK-P-01 must still prove four clear billet zones before crosscutting. L's edges are cleaned to a current 6-inch width, but its faces, thickness, length, and final yield remain unverified. Reserve every board exclusively for the door, coupons, setup pieces, substitutions, and repair stock.",
             "At full length, map STOCK-I/K for two parallel 4-3/8-inch stile lanes each and STOCK-B/C for one continuous 4-3/8-inch stile-face lane each. Do not crosscut B/C/I/K until CHK-ST-01 and CHK-ST-02 pass.",
             "Joint one face and one edge, ordinarily width-rip I/K into their paired lanes, and use staged thickness planing to produce one 7/8-inch core plus one 5/16-inch face from each. Stage-plane the B/C face lanes to 5/16 inch. No A-O board is resawn.",
             "Sign revised CM-05 before cutting J/L short-member cores. J carries C, M, the 6-1/2-inch F core stave, and G; 6-inch L carries E, both D core staves, and the 5-3/4-inch F core stave. Retain every credited longitudinal offcut.",
             "After the core and panel priorities pass, sign FP-05 before cutting short-member faces. Assign clear D/H tails, eligible C/J/L width offcuts, and at least five clear 16-1/4-inch mother billets combined from knot-mapped E/F to every C/M/D/E/F/G show/back strip, coupon, and reserve. After D-101H passes, M's protected tail may add up to two 16-1/4-inch face mother billets. Keep A intact as fallback reserve and protect the controlled D/F seam locations.",
             "Hold the LS-05 panel-source boards for D-101H/J/N/K-L until CHK-RS-01 and CHK-P-01 prove post-flattening thickness, aggregate clean width, clear squared length, grain, color, and defects. Keep every mapped reserve door-only until released.",
             "Prepare same-species, parallel-grain 7/8-inch cores and paired 5/16-inch faces with layers within one moisture percentage point. Sticker and rest after staged planing; no layer may contain an end joint or cross-grain patch.",
             "Match D-101K and D-101L as a pair; lay out every panel with vertical grain.",
             "Sticker stock in the conditioned shop until consecutive moisture readings stabilize."],
            ["all parts traceable to STOCK label, D-101 part ID, and CORE/SF/BF layer", "LS-05 RS/ST/SM/P/LAM/SEAM gates signed", "stiles straight within 1/16 inch over the 80-1/2-inch finished length", "color sample approved"]),
        "shop": ("Prepare a repeatable and safe production cell", ["machine manuals", "squares", "dust extractor", "clamps", "flat assembly platform"],
            ["Verify guards, extraction, cutters, blades, and emergency clearance.", "Calibrate square, planer thickness, saw fence, and dado-stack test cut.", "Build long-work supports coplanar with the DF 500 and saw surfaces.", "Prepare labeled racks for milled parts and test pieces.", "Dry-run the clamp layout on the flat platform."],
            ["machines cut square on scrap", "assembly platform flat within 1/32 inch", "every long part independently supported"]),
        "layout": ("Transfer the complete vertical geometry without cumulative error", ["full-length plywood story sticks", "knife", "square", "fine pencil"],
            ["Scribe the final 23-3/4 x 80-1/2 rectangle inside the 23-7/8 x 80-5/8 pre-fit assembly.", "Mark one master final-top datum and all rail shoulders from specification coordinates.", "Create a paired mortise story stick with each joint ID and tight/loose designation.", "Transfer only from the master; never leapfrog a rule or hook from a temporary rough end.", "Check the complete stack against 80-1/2 inches and both bottom-opening widths against 6-1/8 inches.", "Destroy or conspicuously obsolete every Rev. F/LS-04 story stick before transferring Rev. G.", "Seal and label approved story sticks; retain them through installation."],
            ["stack totals exactly 80-1/2 inches", "paired marks agree within 0.010 inch", "all identifiers readable"]),
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
        ("story-stick/T-01-master-story-stick.md", "Master rail-location story stick", "Mark only from the scribed final-top datum; verify the complete 80-1/2-inch stack. Obsolete every Rev. F/LS-04 story stick before use."),
        ("domino-layout/T-02-wide-rail.md", "Wide-rail multiple-tenon layout", "Use registered centerlines; first tight, followers medium."),
        ("domino-layout/T-03-muntin.md", "Muntin joint layout", "D-101G: 6 mm cutter, 20 mm plunge, centers 1.000 and 2.000 inches, both tight. D-101E/F: centers 7.125 and 8.125 inches from hinge-side shoulder, tight then medium, inside the 6-1/8-to-9-1/8-inch footprint. Sectioned samples must retain the specified actual webs."),
        ("domino-setup/T-04-test-piece.md", "Domino test-piece worksheet", "Record joint ID, cutter, plunge, width, face, edge, and dry-fit result."),
        ("hinge-layout/T-05-hinge.md", "Hinge layout", "Transfer actual leaf; no universal gain dimensions are implied."),
        ("lock-verification/T-06-lock.md", "Lock verification", "Record physical hardware before machining."),
        ("glue-up/T-07-clamp-map.md", "Glue-up clamp map", "Rehearse sequence and open time."),
        ("millwork/T-08-jamb-measurement.md", "Completed-jamb measurement worksheet", "Measure width and height at three locations."),
    ]
    for path, title, body in entries:
        write(TEMPLATES / path, f"# {title}\n\nProject DC-1916-001 | {SPEC['project']['revision']} | Print at 100% / Actual Size\n\n{body}\n\nEvery printed sheet includes a 1-inch calibration square in the PDF package.")


def svg_text(slug: str, title: str, number: int) -> str:
    if slug == "finished-door-elevation":
        height = SPEC["slab"]["finished_height"]
        width = SPEC["slab"]["finished_width"]
        drawing_scale = 474 / height
        width_scale = 360 / width
        stile_px = SPEC["frame"]["stile_width"] * width_scale
        muntin_px = SPEC["frame"]["muntin_width"] * width_scale
        top_positions = rail_top_positions()
        rails = [
            (top_positions[part_id], SPEC["frame"]["rail_widths"][part_id], part_id)
            for part_id in ("D-101C", "D-101M", "D-101D", "D-101E", "D-101F")
        ]
        rects = [f'<rect x="120" y="{60+y*drawing_scale}" width="360" height="{h*drawing_scale}" fill="{OAK}" stroke="{INK}"/><text x="300" y="{72+(y+h/2)*drawing_scale}" text-anchor="middle">{label}</text>' for y,h,label in rails]
        rects += [f'<rect x="120" y="60" width="{stile_px}" height="474" fill="{OAK}" stroke="{INK}"/><rect x="{480-stile_px}" y="60" width="{stile_px}" height="474" fill="{OAK}" stroke="{INK}"/>']
        muntin_top = top_positions["D-101E"] + SPEC["frame"]["rail_widths"]["D-101E"]
        muntin_height = SPEC["frame"]["vertical_openings"]["P-04 bottom"]
        rects += [f'<rect x="{300-muntin_px/2}" y="{60+muntin_top*drawing_scale}" width="{muntin_px}" height="{muntin_height*drawing_scale}" fill="{OAK}" stroke="{INK}"/>']
        body = "".join(rects) + f'<text x="70" y="300" transform="rotate(-90 70 300)">{height:g} in</text><text x="300" y="565" text-anchor="middle">{SPEC["slab"]["finished_width"]:g} in fitted slab | five panels: 3 full-width + 2 lower</text>'
    elif "groove" in slug or "tongue" in slug:
        body = f'<rect x="100" y="180" width="400" height="180" fill="{OAK}" stroke="{INK}" stroke-width="3"/><rect x="260" y="180" width="80" height="70" fill="white" stroke="{INK}"/><path d="M230 410 L270 250 L330 250 L370 410" fill="{PALE}" stroke="{TEAL}" stroke-width="4"/><text x="300" y="155" text-anchor="middle">1/4 in groove x 1/2 in deep; 7/32 +/-0.005 in tongue</text><text x="300" y="455" text-anchor="middle">Panel floats - never glue the tongue</text>'
    elif slug == "muntin-joint":
        body = f'<rect x="70" y="170" width="200" height="230" fill="{OAK}" stroke="{INK}"/><rect x="330" y="170" width="200" height="230" fill="{OAK}" stroke="{INK}"/><rect x="235" y="225" rx="18" width="130" height="38" fill="{TEAL}"/><rect x="235" y="305" rx="18" width="130" height="38" fill="{TEAL}"/><path d="M300 100 V160" marker-end="url(#a)" stroke="{INK}" stroke-width="3"/><text x="300" y="80" text-anchor="middle">6 mm cutter; 20 mm plunge; show-face reference</text><text x="300" y="450" text-anchor="middle">D-101G: BOTH TIGHT</text><text x="300" y="480" text-anchor="middle">D-101E/F: TIGHT + MEDIUM IN SOLID FOOTPRINT</text>'
    elif "tenon" in slug or "domino" in slug or "df500" in slug or "rail-stile" in slug:
        body = f'<rect x="70" y="170" width="200" height="230" fill="{OAK}" stroke="{INK}"/><rect x="330" y="170" width="200" height="230" fill="{OAK}" stroke="{INK}"/><rect x="235" y="225" rx="18" width="130" height="38" fill="{TEAL}"/><rect x="235" y="305" rx="18" width="130" height="38" fill="{TEAL}"/><path d="M300 100 V160" marker-end="url(#a)" stroke="{INK}" stroke-width="3"/><text x="300" y="80" text-anchor="middle">Show-face reference; fence 17.5 mm</text><text x="300" y="455" text-anchor="middle">First mortise tight; remaining mortises medium</text>'
    elif "casing" in slug or "stop" in slug or "strike" in slug or "hinge" in slug or "lock" in slug:
        body = f'<rect x="130" y="120" width="90" height="330" fill="{OAK}" stroke="{INK}"/><rect x="220" y="150" width="75" height="270" fill="{PALE}" stroke="{INK}"/><rect x="295" y="160" width="38" height="250" fill="{OAK}" stroke="{INK}"/><rect x="333" y="160" width="140" height="250" fill="#D7B47B" stroke="{INK}"/><path d="M90 110 H240" stroke="{TEAL}" stroke-width="3"/><text x="300" y="90" text-anchor="middle">Field verify completed jamb and actual hardware</text><text x="300" y="485" text-anchor="middle">3/16 in casing reveal default; house evidence controls</text>'
    else:
        body = f'<rect x="80" y="160" width="130" height="150" rx="8" fill="{PALE}" stroke="{BLUE}" stroke-width="3"/><rect x="235" y="160" width="130" height="150" rx="8" fill="{PALE}" stroke="{BLUE}" stroke-width="3"/><rect x="390" y="160" width="130" height="150" rx="8" fill="{PALE}" stroke="{BLUE}" stroke-width="3"/><path d="M210 235 H230 M365 235 H385" stroke="{TEAL}" stroke-width="4" marker-end="url(#a)"/><text x="145" y="230" text-anchor="middle">Reference</text><text x="300" y="230" text-anchor="middle">Machine / fit</text><text x="455" y="230" text-anchor="middle">Measure / pass</text><text x="300" y="390" text-anchor="middle">Stop when measurable acceptance criteria pass</text>'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="600" height="520" viewBox="0 0 600 520">
<defs><marker id="a" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L0,6 L7,3 z" fill="{INK}"/></marker></defs>
<rect width="600" height="520" fill="white"/><text x="30" y="32" font-family="Helvetica" font-size="13" fill="{TEAL}">DC-1916-001 | FIG. {number} | {SPEC["project"]["revision"].upper()} | NTS</text>
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
        d.text((60, 55), f"DC-1916-001 | FIG. {i} | {SPEC['project']['revision'].upper()} | NTS", fill=TEAL, font=font)
        d.text((60, 100), title, fill=BLUE, font=font)
        if slug == "finished-door-elevation":
            x, y, w, h = 420, 145, 240, 590
            height = SPEC["slab"]["finished_height"]
            top_positions = rail_top_positions()
            d.rectangle((x, y, x+w, y+h), outline=INK, width=4)
            sw = w * SPEC["frame"]["stile_width"] / SPEC["slab"]["finished_width"]
            d.rectangle((x, y, x+sw, y+h), fill=OAK, outline=INK)
            d.rectangle((x+w-sw, y, x+w, y+h), fill=OAK, outline=INK)
            scale = h / height
            for part_id in ("D-101C", "D-101M", "D-101D", "D-101E", "D-101F"):
                pos = top_positions[part_id]
                rh = SPEC["frame"]["rail_widths"][part_id]
                d.rectangle((x+sw, y+pos*scale, x+w-sw, y+(pos+rh)*scale), fill=OAK, outline=INK)
            mx = x+w/2
            mw = w * SPEC["frame"]["muntin_width"] / SPEC["slab"]["finished_width"]
            muntin_top = top_positions["D-101E"] + SPEC["frame"]["rail_widths"]["D-101E"]
            muntin_bottom = top_positions["D-101F"]
            d.rectangle((mx-mw/2, y+muntin_top*scale, mx+mw/2, y+muntin_bottom*scale), fill=OAK, outline=INK)
            d.text((690, 200), f"{SPEC['slab']['finished_width']:g} x {height:g} x 1-3/8 in fitted slab", fill=INK, font=font)
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
    for idx, (filename, chapter_title, _) in enumerate(CHAPTERS):
        text = (MANUSCRIPT / filename).read_text()
        figure = figs[min(idx, len(figs)-1)]
        render = legacy_chapter_rendering(filename)
        if render:
            render_data = base64.b64encode(render.read_bytes()).decode()
            visual = (
                f'<img alt="{html.escape(chapter_title)} dimension-controlled rendering" '
                f'src="data:image/png;base64,{render_data}">'
            )
            caption = (
                f"{html.escape(chapter_title)}. Dimension-controlled cabinetmaker "
                "rendering; written dimensions control."
            )
        else:
            visual = (ILLUSTRATIONS / "technical" / f"{figure['Slug']}.svg").read_text()
            caption = f"{figure['Figure']}. {html.escape(figure['Purpose'])}"
        sections.append(
            f"<section>{markdown_to_html(text)}<figure>{visual}"
            f"<figcaption>{caption}</figcaption></figure></section>"
        )
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
    s.add(ParagraphStyle(name="H2x", parent=s["Heading2"], fontName="Helvetica-Bold", fontSize=13, leading=16, textColor=colors.HexColor(TEAL), spaceBefore=9, spaceAfter=5, keepWithNext=1))
    s.add(ParagraphStyle(name="Bodyx", parent=s["BodyText"], fontName="Helvetica", fontSize=10.2 if screen else 9.3, leading=14 if screen else 12.5, textColor=colors.HexColor(INK), spaceAfter=6))
    s.add(ParagraphStyle(name="Bulletx", parent=s["Bodyx"], leftIndent=15, firstLineIndent=-8, bulletIndent=2))
    s.add(ParagraphStyle(name="Smallx", parent=s["Bodyx"], fontSize=8, leading=10, textColor=colors.HexColor("#4E5A60")))
    s.add(ParagraphStyle(name="Registerx", parent=s["Bodyx"], fontSize=9.2, leading=11.5, spaceAfter=3.5))
    return s


def page_decor(canvas, doc):
    page = canvas.getPageNumber()
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor(OAK))
    canvas.line(0.72*inch, 0.55*inch, 7.78*inch, 0.55*inch)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#4E5A60"))
    canvas.drawString(0.72*inch, 0.38*inch, f"DC-1916-001 | First Edition | {SPEC['project']['revision']}")
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

    for line in text.splitlines():
        if line.startswith("|"):
            if "---" not in line:
                table_rows.append([x.strip() for x in line.strip("|").split("|")])
            continue
        flush_table()
        if line.startswith("# "):
            flows.append(Paragraph(html.escape(line[2:]), styles["H1"]))
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
        # Each generated plate already carries its figure title, control note, and
        # revision footer.  A separate trailing caption is redundant and can orphan
        # onto an otherwise blank page when a chapter finishes near the frame limit.
        flows.extend([Spacer(1, 6), img])
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
        png = legacy_chapter_rendering(filename)
        if png is None:
            png = ILLUSTRATIONS / "technical" / f"{fig['Slug']}.png"
        story.extend(md_flowables(text, styles, png))
        story.append(PageBreak())
    # Append the complete registers to make the manual operational and page-complete.
    story.append(Paragraph("Controlled Dimension Register", styles["H1"]))
    for c in SPEC["components"]:
        story.append(Paragraph(
            f"<b>{c['id']} - {c['name']}</b>: {c['qty']} at "
            f"{exact_decimal(c['t'])} x {exact_decimal(c['w'])} x "
            f"{exact_decimal(c['l'])} inches.",
            styles["Bodyx"],
        ))
    story.append(PageBreak())
    story.append(Paragraph("Complete DF 500 Joint Register", styles["H1"]))
    for j in JOINTS:
        jid,fam,a,b,cutter,tenon,count,plunge,centers=j
        is_muntin = jid in {"J-11", "J-12"}
        strategy = "D-101G both tight; mating rail tight then medium" if is_muntin else "first tight, remainder medium on both members"
        story.append(Paragraph(
            f"<b>{jid} - {fam}</b><br/>{a} to {b}; {count} factory beech {tenon} mm tenons; "
            f"{cutter} mm cutter; {plunge}/{plunge} mm plunge; Part A centerlines "
            f"{', '.join(str(x) for x in centers)} inches; Part B centerlines "
            f"{', '.join(str(x) for x in PART_B_CENTERS[jid])} inches; {strategy}.",
            styles["Registerx"],
        ))
    doc.build(story)
    return len(PdfReader(str(path)).pages)


def _template_fit_text(c, text, x, y, max_width, size=8, bold=False, color=INK):
    font = "Helvetica-Bold" if bold else "Helvetica"
    fitted = size
    while fitted > 5.5 and c.stringWidth(str(text), font, fitted) > max_width:
        fitted -= 0.25
    c.setFillColor(colors.HexColor(color))
    c.setFont(font, fitted)
    c.drawString(x, y, str(text))


def _template_wrapped_text(c, text, x, y, width, size=8, leading=10, bold=False, color=INK):
    font = "Helvetica-Bold" if bold else "Helvetica"
    chars = max(16, int(width / max(size * 0.52, 1)))
    c.setFillColor(colors.HexColor(color))
    c.setFont(font, size)
    for line in textwrap.wrap(text, chars):
        c.drawString(x, y, line)
        y -= leading
    return y


def _template_section(c, x, top, width, height, title, accent=TEAL):
    bottom = top - height
    c.setFillColor(colors.HexColor("#F8F6F1"))
    c.setStrokeColor(colors.HexColor(accent))
    c.setLineWidth(1.1)
    c.rect(x, bottom, width, height, fill=1, stroke=1)
    c.setFillColor(colors.HexColor(accent))
    c.rect(x, top - 20, width, 20, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x + 8, top - 14, title)
    return top - 32


def _template_field(c, label, x, y, width, value="", size=7.5):
    c.setFillColor(colors.HexColor(INK))
    c.setFont("Helvetica-Bold", size)
    c.drawString(x, y, label)
    label_width = min(width * .58, c.stringWidth(label, "Helvetica-Bold", size) + 6)
    start = x + label_width
    c.setStrokeColor(colors.HexColor("#65717A"))
    c.setLineWidth(.55)
    c.line(start, y - 2, x + width, y - 2)
    if value:
        _template_fit_text(c, value, start + 3, y, x + width - start - 4, size, False)


def _template_checkbox(c, x, y, label, checked=False, size=7.5):
    c.setStrokeColor(colors.HexColor(BLUE))
    c.setLineWidth(.75)
    c.rect(x, y - 7, 8, 8, fill=0, stroke=1)
    if checked:
        c.line(x + 1.5, y - 3, x + 3.5, y - 6)
        c.line(x + 3.5, y - 6, x + 7, y)
    _template_fit_text(c, label, x + 12, y - 5, 120, size)


def _template_table(c, x, top, widths, headers, rows, row_height=22, font_size=6.8):
    total_width = sum(widths)
    total_height = row_height * (len(rows) + 1)
    c.setStrokeColor(colors.HexColor("#8B969C"))
    c.setLineWidth(.5)
    c.setFillColor(colors.HexColor("#E7EFEE"))
    c.rect(x, top - row_height, total_width, row_height, fill=1, stroke=1)
    for row_index in range(len(rows)):
        row_top = top - row_height * (row_index + 1)
        c.setFillColor(colors.HexColor("#FCFBF8" if row_index % 2 == 0 else "#F4F0E8"))
        c.rect(x, row_top - row_height, total_width, row_height, fill=1, stroke=1)
    cursor = x
    for width in widths:
        c.line(cursor, top, cursor, top - total_height)
        cursor += width
    c.line(x + total_width, top, x + total_width, top - total_height)
    for row_index in range(len(rows) + 2):
        y = top - row_height * row_index
        c.line(x, y, x + total_width, y)
    cursor = x
    for header, width in zip(headers, widths):
        _template_fit_text(c, header, cursor + 3, top - row_height + 7, width - 6, font_size, True, BLUE)
        cursor += width
    for row_index, row in enumerate(rows):
        baseline = top - row_height * (row_index + 2) + 7
        cursor = x
        for value, width in zip(row, widths):
            _template_fit_text(c, value, cursor + 3, baseline, width - 6, font_size)
            cursor += width
    return top - total_height


def _template_header(c, number, title, subtitle):
    w, h = letter
    c.setFillColor(colors.HexColor(BLUE))
    c.rect(0, h - .68 * inch, w, .68 * inch, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 15)
    c.drawString(.5 * inch, h - .43 * inch, f"T-{number:02d}  {title}")
    c.setFillColor(colors.HexColor(INK))
    c.setFont("Helvetica", 8)
    c.drawString(.5 * inch, h - .91 * inch, f"DC-1916-001 | {SPEC['project']['revision']} | Sheet {number} of 14 | PRINT AT 100%")
    _template_fit_text(c, subtitle, .5 * inch, h - 1.16 * inch, 7.5 * inch, 8.2, False, TEAL)
    c.setStrokeColor(colors.HexColor(OAK))
    c.setLineWidth(1)
    c.line(.5 * inch, h - 1.30 * inch, 8.0 * inch, h - 1.30 * inch)


def _template_footer(c):
    c.setStrokeColor(colors.HexColor(BLUE))
    c.setLineWidth(.8)
    c.rect(7.05 * inch, .35 * inch, inch, inch, fill=0, stroke=1)
    c.setFillColor(colors.HexColor(INK))
    c.setFont("Helvetica", 6.5)
    c.drawCentredString(7.55 * inch, .22 * inch, "1-IN CALIBRATION SQUARE")
    c.drawString(.5 * inch, .56 * inch, "REFERENCE FACE: SHOW FACE   |   REFERENCE EDGE: TOP / LEFT")
    c.drawString(.5 * inch, .36 * inch, "Verify calibration, orientation, part ID, and written dimensions before transfer or cutting.")


def _draw_scaled_story_stick(c, x, top, bottom, marks):
    slab_height = SPEC["slab"]["finished_height"]
    scale = (top - bottom) / slab_height
    c.setStrokeColor(colors.HexColor(BLUE))
    c.setLineWidth(4)
    c.line(x, bottom, x, top)
    for index, (station, label) in enumerate(marks):
        y = top - station * scale
        c.setLineWidth(1.1)
        c.line(x - 12, y, x + 12, y)
        label_x = x + 18 if index % 2 else x - 104
        _template_fit_text(c, f'{station:g}"  {label}', label_x, y - 3, 96, 6.6, station in {0, slab_height}, BLUE)
    c.setFont("Helvetica-Bold", 7)
    c.drawCentredString(x, bottom - 18, "ORIENTATION MAP — NTS")


def _template_t01(c):
    left, right, width = 36, 314, 262
    y_left = _template_section(c, left, 684, width, 154, "OPENING DIMENSIONS — COMPLETED JAMB")
    for label, value in [
        ("W-TOP", '24" CONFIRMED'),
        ("W-MIDDLE", '24" CONFIRMED'),
        ("W-BOTTOM", '24" CONFIRMED'),
        ("H-LEFT", '81" CONFIRMED'),
        ("H-RIGHT", '81" CONFIRMED'),
        ("DIAGONAL A / B / DIFFERENCE", ""),
    ]:
        _template_field(c, label, left + 10, y_left, width - 20, value)
        y_left -= 19
    y_right = _template_section(c, right, 684, width, 154, "JAMB GEOMETRY")
    for label in ["THICKNESS L / HEAD / R", "PROJECTION L / HEAD / R", "LEFT PLUMB — 2 PLANES", "RIGHT PLUMB — 2 PLANES", "HEAD LEVEL", "WINDING-STICK FACE TWIST"]:
        _template_field(c, label, right + 10, y_right, width - 20)
        y_right -= 19
    y_left = _template_section(c, left, 516, width, 176, "FLOOR, SWING, AND DOOR FIT")
    for label, value in [
        ("FINISHED FLOOR / RUG DATUM", ""),
        ("BOTTOM GAP", '3/8" TARGET'),
        ("HANDING", ""),
        ("SWING IN / OUT", ""),
        ("LATCH-EDGE BEVEL", "FIELD VERIFY"),
        ("HEAD / SIDE REVEALS", '1/8" EACH'),
        ("STOP CONDITION / CONTACT", ""),
    ]:
        _template_field(c, label, left + 10, y_left, width - 20, value)
        y_left -= 19
    y_right = _template_section(c, right, 516, width, 176, "HARDWARE AND ADJACENT EVIDENCE")
    for label in ["HINGE GAINS / LEAF SIZE", "LOCK / BACKSET / STRIKE", "ADJACENT TRIM / BASEBOARD", "WALL FLATNESS / PROJECTION", "FRAMING / UTILITIES", "PHOTO / SAMPLE REFERENCES", "MEASURED FACE A / FACE B"]:
        _template_field(c, label, right + 10, y_right, width - 20)
        y_right -= 19
    y = _template_section(c, left, 324, 540, 150, "FIELD RELEASE")
    _template_checkbox(c, left + 10, y, "ALL VALUES RECORDED")
    _template_checkbox(c, left + 180, y, "OPENING RECHECKED")
    _template_checkbox(c, left + 350, y, "HOLD / CONFLICT")
    y -= 25
    _template_field(c, "MEASURED BY / DATE", left + 10, y, 248)
    _template_field(c, "VERIFIED BY / DATE", left + 278, y, 248)
    y -= 23
    _template_field(c, "HOLD REASON / FIELD NOTE", left + 10, y, 516)
    y -= 25
    _template_field(c, "APPROVED SLAB FIT TARGET", left + 10, y, 516, '23-3/4 x 80-1/2 x 1-3/8" MAX RECTANGLE')


def _template_t02(c):
    marks = story_stick_stations()
    _draw_scaled_story_stick(c, 132, 672, 182, marks)
    rows = [[f'{station:g}"', label, "____", "____"] for station, label in marks]
    _template_table(
        c, 244, 674, [48, 158, 55, 55],
        ["STATION", "MASTER MARK", "TRANSFER", "VERIFY"],
        rows, row_height=27, font_size=6.7,
    )
    y = _template_section(c, 244, 366, 316, 178, "MASTER-STICK RELEASE")
    for label in [
        "PHYSICAL STICK ID / MATERIAL", "TOP DATUM CONFIRMED",
        "SHOW FACE / REFERENCE EDGE", "HINGE STILE TRANSFER",
        "LOCK STILE TRANSFER", "OPERATOR / DATE",
    ]:
        _template_field(c, label, 254, y, 296)
        y -= 21
    c.setFillColor(colors.HexColor("#FFF1ED"))
    c.setStrokeColor(colors.HexColor("#A33B32"))
    c.rect(244, 136, 316, 38, fill=1, stroke=1)
    _template_fit_text(c, "DO NOT SCALE THE NTS MAP — TRANSFER WRITTEN STATIONS.", 254, 151, 296, 7.2, True, "#A33B32")


def _template_t03(c):
    member_labels = (
        "SLAB TOP",
        "TOP RAIL",
        "P-01 BOTTOM",
        "P-02 TOP",
        "P-02 BOTTOM",
        "P-03 TOP",
        "P-03 BOTTOM",
        "P-04 TOP",
        "P-04 BOTTOM",
        "SLAB BOTTOM",
    )
    rows = [
        [f'{station:g}"', label, member_label, "", ""]
        for (station, label), member_label in zip(story_stick_stations(), member_labels)
    ]
    _template_table(
        c, 38, 681, [48, 118, 160, 102, 102],
        ["STATION", "MARK", "OPENING / MEMBER", "HINGE STILE", "LOCK STILE"],
        rows, row_height=29, font_size=6.8,
    )
    y = _template_section(c, 38, 368, 532, 174, "TRANSFER CONTROL")
    _template_field(c, "APPROVED MASTER STICK ID", 48, y, 245)
    _template_field(c, "WORKING STICK ID", 315, y, 245)
    y -= 24
    for x, label in [
        (48, "SHOW FACE MARKED"), (185, "TOP DATUM MATCHED"),
        (335, "NO CHAINED MEASUREMENTS"), (485, "SECOND-PERSON CHECK"),
    ]:
        _template_checkbox(c, x, y, label, size=6.5)
    y -= 27
    _template_field(c, "DISCREPANCY / REMAKE NOTE", 48, y, 512)
    y -= 25
    _template_field(c, "TRANSFERRED BY / DATE", 48, y, 245)
    _template_field(c, "VERIFIED BY / DATE", 315, y, 245)
    y -= 25
    _template_wrapped_text(
        c,
        "Release only when both stile story sticks carry the same top datum, member IDs, shoulder lines, and opening labels.",
        48, y, 512, 7.4, 10, True, "#A33B32",
    )


def _draw_actual_bar(c, x, y, length_in, height, title, marks, start_station=0):
    width = length_in * inch
    c.setFillColor(colors.HexColor("#D7B47B"))
    c.setStrokeColor(colors.HexColor(BLUE))
    c.setLineWidth(1.2)
    c.rect(x, y, width, height, fill=1, stroke=1)
    _template_fit_text(c, title, x, y + height + 12, width, 8, True, BLUE)
    for station, label, color in marks:
        mark_x = x + (station - start_station) * inch
        c.setStrokeColor(colors.HexColor(color))
        c.setLineWidth(1.2)
        c.line(mark_x, y - 6, mark_x, y + height + 6)
        _template_fit_text(c, label, mark_x - 18, y - 17, 54, 6.5, True, color)
    c.setFont("Helvetica", 6.2)
    c.setFillColor(colors.HexColor("#65717A"))
    c.drawRightString(x + width, y + height + 3, "FULL SIZE AT 100%")


def _template_t04(c):
    _draw_actual_bar(
        c, 54, 590, 4, 46, '4-IN RAIL END — D-101C / M / E (J-01/02/03/04/07/08)',
        [(1.25, '1.250 TIGHT', BLUE), (2.75, '2.750 MED', TEAL)],
    )
    y = _template_section(c, 378, 646, 180, 154, "DF 500 SETUP")
    for label, value in [
        ("CUTTER", "10 mm"), ("PLUNGE A / B", "25 / 25 mm"),
        ("FENCE", "17.5 mm / 90 deg"), ("FACE", "SHOW FACE"),
        ("WIDTH A / B", "TIGHT, THEN MEDIUM"),
    ]:
        _template_field(c, label, 388, y, 160, value, 6.8)
        y -= 21
    rows = [
        ["J-01", "D-101C/A", "1.250 / 2.750", "", ""],
        ["J-02", "D-101C/B", "1.250 / 2.750", "", ""],
        ["J-03", "D-101M/A", "1.250 / 2.750", "", ""],
        ["J-04", "D-101M/B", "1.250 / 2.750", "", ""],
        ["J-07", "D-101E/A", "1.250 / 2.750", "", ""],
        ["J-08", "D-101E/B", "1.250 / 2.750", "", ""],
    ]
    _template_table(
        c, 54, 500, [54, 110, 128, 105, 105],
        ["JOINT", "PARTS", "CENTERLINES", "TEST ID", "RELEASE"],
        rows, row_height=29, font_size=6.8,
    )
    y = _template_section(c, 54, 286, 504, 132, "PRODUCTION GATE")
    for x, label in [
        (64, "UNTOUCHED FULL-LENGTH FACTORY TENONS SEAT"),
        (306, "SHOULDERS CLOSE BY HAND"),
        (64, "FACES FLUSH / NO BREAKOUT"),
        (306, "STANDARD RAIL WEB >= 0.150 IN"),
    ]:
        _template_checkbox(c, x, y, label, size=6.5)
        if x > 200:
            y -= 23
    _template_field(c, "TEST SAMPLE / OPERATOR / DATE", 64, y - 2, 484)


def _template_t05(c):
    _draw_actual_bar(
        c, 54, 604, 7, 42, "D-101D LOCK RAIL — 7 IN FULL SIZE",
        [(1.25, "1.250 T", BLUE), (3.5, "3.500 M", TEAL), (5.75, "5.750 M", TEAL)],
    )
    _draw_actual_bar(
        c, 72, 462, 6, 38, "D-101F BOTTOM RAIL — SEGMENT A (0–6 IN)",
        [(1.25, "1.250 T", BLUE), (4.0, "4.000 M", TEAL)],
    )
    _draw_actual_bar(
        c, 72, 346, 6, 38, "D-101F BOTTOM RAIL — SEGMENT B (6–12 IN)",
        [(7.5, "7.500 M", TEAL), (10.75, "10.750 M", TEAL)],
        start_station=6,
    )
    y = _template_section(c, 54, 282, 504, 132, "WIDE-RAIL RELEASE")
    _template_checkbox(c, 64, y, "SHOW FACE + REFERENCE EDGE MARKED", size=6.5)
    _template_checkbox(c, 320, y, "FIRST MORTISE TIGHT", size=6.5)
    y -= 23
    _template_checkbox(c, 64, y, "REMAINING MORTISES MEDIUM", size=6.5)
    _template_checkbox(c, 320, y, "25 / 25 MM PLUNGE", size=6.5)
    y -= 24
    _template_field(c, "J-05 / J-06 TEST IDS", 64, y, 230)
    _template_field(c, "J-09 / J-10 TEST IDS", 320, y, 228)
    y -= 24
    _template_field(c, "OPERATOR / DATE / SECOND CHECK", 64, y, 484)


def _template_t06(c):
    _draw_actual_bar(
        c, 54, 594, 3, 54, "D-101G END GRAIN — 3 IN FULL SIZE",
        [(1.0, "1.000 T", BLUE), (2.0, "2.000 T", BLUE)],
    )
    _template_wrapped_text(
        c,
        "6 mm cutter | 20 mm plunge into D-101G | BOTH mortises tight",
        298, 622, 260, 8, 11, True, TEAL,
    )
    _draw_actual_bar(
        c, 54, 450, 3, 48, "D-101E / D-101F GROOVE-FREE FOOTPRINT — STATIONS 6-1/8–9-1/8 IN",
        [(7.125, "7.125 T", BLUE), (8.125, "8.125 M", TEAL)],
        start_station=6.125,
    )
    _template_wrapped_text(
        c,
        "Receiver rail: 6 mm cutter | 20 mm plunge | groove segments remain 0–6-1/8 and 9-1/8–15-1/4 in",
        298, 480, 260, 8, 11, True, TEAL,
    )
    y = _template_section(c, 54, 372, 504, 214, "SECTIONED TP-11 / TP-12 WEB PROOF")
    rows = [
        ["D-101G LEFT GROOVE-TO-MORTISE", ">= 0.100 in", "", ""],
        ["D-101G RIGHT GROOVE-TO-MORTISE", ">= 0.100 in", "", ""],
        ["D-101G INTER-MORTISE WEB", ">= 0.220 in", "", ""],
        ["D-101E RECEIVER INTER-MORTISE", ">= 0.100 in", "", ""],
        ["D-101F RECEIVER INTER-MORTISE", ">= 0.100 in", "", ""],
    ]
    _template_table(
        c, 64, y + 5, [230, 92, 82, 80],
        ["MEASURED FEATURE", "MINIMUM", "ACTUAL", "PASS"],
        rows, row_height=25, font_size=6.6,
    )
    _template_field(c, "SECTIONED SAMPLE IDS / APPROVER", 64, 172, 484)


def _template_t07(c):
    y = _template_section(c, 38, 682, 532, 82, "MACHINE / OPERATOR CONTROL")
    _template_field(c, "DF 500 MACHINE ID", 48, y, 244)
    _template_field(c, "OPERATOR / DATE", 314, y, 246)
    y -= 23
    _template_field(c, "10 MM CUTTER ID / CONDITION", 48, y, 244)
    _template_field(c, "6 MM CUTTER ID / CONDITION", 314, y, 246)
    rows = []
    for jid, _, _, _, cutter, _, _, plunge, _ in JOINTS:
        widths = "T/T | T/M" if jid in {"J-11", "J-12"} else "T/M | T/M"
        rows.append([jid, f"{cutter} mm", f"{plunge}/{plunge}", "17.5/90", widths, f"TP-{jid[2:]}", "", ""])
    _template_table(
        c, 38, 582, [40, 47, 48, 58, 105, 60, 84, 84],
        ["JOINT", "CUTTER", "PLUNGE", "FENCE", "A | B WIDTHS", "TEST ID", "DRY FIT", "RELEASE"],
        rows, row_height=25, font_size=6.1,
    )
    y = _template_section(c, 38, 238, 532, 92, "REGISTER RELEASE")
    _template_field(c, "SCRAP STOCK / THICKNESS / MOISTURE", 48, y, 512)
    y -= 23
    _template_field(c, "FACE / EDGE / FENCE BLOCK ID", 48, y, 244)
    _template_field(c, "FINAL VERIFIER / DATE", 314, y, 246)


def _template_t08(c):
    y = _template_section(c, 38, 682, 532, 100, "TEST-PIECE IDENTIFICATION")
    _template_field(c, "JOINT FAMILY / TP ID", 48, y, 244)
    _template_field(c, "PARTS A / B", 314, y, 246)
    y -= 23
    _template_field(c, "STOCK THICKNESS / MC", 48, y, 244)
    _template_field(c, "CUTTER / PLUNGE / FENCE", 314, y, 246)
    y -= 23
    _template_field(c, "SHOW FACE / REFERENCE EDGE", 48, y, 512)
    y = _template_section(c, 38, 564, 260, 178, "FIRST GATE — UNTOUCHED FACTORY TENONS")
    for label in [
        "FULL-LENGTH FACTORY TENONS",
        "HAND-PRESSURE SEATING",
        "SHOULDERS CLOSED <= 0.005",
        "FACES FLUSH <= 0.010",
        "NO BREAKOUT / CRUSHING",
    ]:
        _template_checkbox(c, 48, y, label, size=6.8)
        y -= 22
    _template_field(c, "TENON LOT / RESULT", 48, y, 240)
    y = _template_section(c, 310, 564, 260, 178, "SECOND GATE — SEPARATE REHEARSAL SET")
    for label in [
        "SEPARATE SET LABELED",
        "RIBS / ENDS MINIMALLY EASED",
        "TENONS NEVER SHORTENED",
        "HAND REMOVABLE",
        "PRODUCTION TENONS UNTOUCHED",
    ]:
        _template_checkbox(c, 320, y, label, size=6.8)
        y -= 22
    _template_field(c, "SET ID / RESULT", 320, y, 240)
    y = _template_section(c, 38, 368, 532, 188, "MEASURED ACCEPTANCE")
    rows = [
        ["SHOULDER GAP", "<= 0.005 in", "", ""],
        ["FACE FLUSH", "<= 0.010 in", "", ""],
        ["STANDARD RAIL WEB TO GROOVE", ">= 0.150 in", "", ""],
        ["D-101G GROOVE WEB / INTER-WEB", ">= .100 / .220", "", ""],
        ["RECEIVER INTER-MORTISE WEB", ">= 0.100 in", "", ""],
    ]
    _template_table(
        c, 48, y + 5, [232, 98, 84, 78],
        ["FEATURE", "LIMIT", "ACTUAL", "PASS"],
        rows, row_height=25, font_size=6.5,
    )
    _template_field(c, "APPROVED / REMAKE / HOLD — SIGNATURE / DATE", 48, 164, 512)


def _template_t09(c):
    y = _template_section(c, 38, 682, 218, 420, "PHYSICAL LEAF TRACE / MEASURE")
    c.setFillColor(colors.white)
    c.setStrokeColor(colors.HexColor(BLUE))
    c.setLineWidth(1.1)
    c.rect(74, 360, 90, 3.5 * inch, fill=1, stroke=1)
    c.setFont("Helvetica", 6.5)
    c.setFillColor(colors.HexColor("#65717A"))
    c.drawCentredString(119, 348, "3-1/2 IN NOMINAL — TRACE ACTUAL LEAF")
    for cy in [400, 486, 570]:
        c.circle(119, cy, 3, fill=0, stroke=1)
    for label, field_y in [
        ("LEAF H / W / T", 330), ("KNUCKLE / PIN AXIS", 307),
        ("SCREW DIA / LENGTH", 284),
    ]:
        _template_field(c, label, 48, field_y, 198)
    y = _template_section(c, 274, 682, 296, 230, "HINGE POSITION REGISTER")
    rows = [
        ["TOP", "HEAD TO LEAF TOP", "", "", ""],
        ["MIDDLE", "TRANSFER / EQUALIZE", "", "", ""],
        ["BOTTOM", "FLOOR TO LEAF BOTTOM", "", "", ""],
    ]
    _template_table(
        c, 284, y + 4, [48, 118, 48, 48, 24],
        ["HINGE", "DATUM", "DOOR", "JAMB", "OK"],
        rows, row_height=32, font_size=6.2,
    )
    _template_field(c, "EXISTING GAIN / NEW LAYOUT BASIS", 284, 500, 276)
    _template_field(c, "BARREL CLEARANCE / THROW", 284, 476, 276)
    y = _template_section(c, 274, 434, 296, 172, "MACHINING AND RELEASE")
    for label in [
        "KNIFE ACTUAL LEAF — NO SCALE",
        "ROUT SHALLOW / PARE TO FIT",
        "PILOTS MATCH SCREW ROOT",
        "STEEL SETUP SCREWS FIRST",
        "BRASS ONLY AFTER FULL FINISH CURE",
    ]:
        _template_checkbox(c, 284, y, label, size=6.7)
        y -= 22
    _template_field(c, "CYCLE TEST / APPROVER", 284, y, 276)
    y = _template_section(c, 38, 244, 532, 86, "RELEASE NOTE")
    _template_field(c, "HINGE TEMPLATE / JIG ID", 48, y, 244)
    _template_field(c, "DATE / OPERATOR", 314, y, 246)
    y -= 24
    _template_field(c, "REMAKE / HOLD CONDITION", 48, y, 512)


def _template_t10(c):
    y = _template_section(c, 38, 682, 532, 100, "ACTUAL HARDWARE IDENTIFICATION")
    _template_field(c, "MANUFACTURER / MODEL", 48, y, 244)
    _template_field(c, "FUNCTION / HANDING", 314, y, 246)
    y -= 23
    _template_field(c, "LOCKSET ID / PHOTO REF", 48, y, 244)
    _template_field(c, "DATE / MEASURED BY", 314, y, 246)
    y -= 23
    _template_field(c, "DO NOT CUT FROM NOMINAL PRODUCT NAME", 48, y, 512)
    y_left = _template_section(c, 38, 564, 260, 210, "LOCK BODY / FACEPLATE")
    for label in [
        "BACKSET", "BODY HEIGHT", "BODY DEPTH", "BODY THICKNESS",
        "FACEPLATE W / H / T", "SPINDLE AXIS", "KEY / PRIVACY AXIS",
    ]:
        _template_field(c, label, 48, y_left, 240)
        y_left -= 22
    y_right = _template_section(c, 310, 564, 260, 210, "STRIKE / SCREWS / CLEARANCE")
    for label in [
        "LATCH PROJECTION", "STRIKE W / H / DEPTH", "LIP / RETURN",
        "CASE SCREW DIA / LENGTH", "STRIKE SCREW DIA / LENGTH",
        "J-06 CLEAR WOOD", "UTILITIES / PRIOR HOLES",
    ]:
        _template_field(c, label, 320, y_right, 240)
        y_right -= 22
    y = _template_section(c, 38, 336, 532, 174, "MACHINING RELEASE")
    for x, label in [
        (48, "BODY INSIDE D-101B"),
        (208, ">= 0.250 IN CLEAR OF J-06"),
        (395, "BORE BOTH FACES"),
        (48, "FACEPLATE FLUSH <= .005"),
        (208, "LATCH WORKS WITHOUT LIFT"),
        (395, "STEEL SETUP HARDWARE"),
    ]:
        _template_checkbox(c, x, y, label, size=6.2)
        if x > 350:
            y -= 24
    _template_field(c, "JIG / DEPTH STOP / TEST BLOCK ID", 48, y, 244)
    _template_field(c, "OPERATOR / APPROVER / DATE", 314, y, 246)
    y -= 25
    _template_field(c, "REMAKE / HOLD NOTE", 48, y, 512)


def _template_t11(c):
    y = _template_section(c, 38, 682, 532, 98, "PRECONDITION — HUNG OPERATING DOOR")
    for x, label in [
        (48, "HINGES RELEASED"), (185, "REVEALS RELEASED"),
        (330, "LOCK OPERATES"), (455, "STEEL SETUP SCREWS"),
    ]:
        _template_checkbox(c, x, y, label, size=6.3)
    y -= 25
    _template_field(c, "DOOR / JAMB REFERENCE", 48, y, 244)
    _template_field(c, "TRANSFER DATE / OPERATOR", 314, y, 246)
    y = _template_section(c, 38, 566, 532, 166, "TRANSFER SEQUENCE — NEVER LOCATE FROM NOMINAL DIMENSIONS")
    steps = [
        "1  CLOSE TO NATURAL LATCH",
        "2  MARK LATCH CENTER",
        "3  TRANSFER TO JAMB",
        "4  KNIFE ACTUAL STRIKE",
        "5  MORTISE / PILOT",
        "6  CYCLE AND RELEASE",
    ]
    for index, step in enumerate(steps):
        col = index % 3
        row = index // 3
        box_x = 52 + col * 170
        box_y = y - row * 54
        c.setFillColor(colors.HexColor("#E7EFEE"))
        c.setStrokeColor(colors.HexColor(TEAL))
        c.rect(box_x, box_y - 32, 152, 36, fill=1, stroke=1)
        _template_fit_text(c, step, box_x + 6, box_y - 18, 140, 6.5, True, BLUE)
    y = _template_section(c, 38, 380, 260, 210, "STRIKE MEASUREMENTS")
    for label in [
        "NATURAL LATCH HEIGHT", "STRIKE CENTER", "STRIKE W / H / DEPTH",
        "LIP / RETURN", "PILOT / SCREW", "JAMB SUBSTRATE",
        "QUIET CONTACT WITNESS",
    ]:
        _template_field(c, label, 48, y, 240)
        y -= 22
    y = _template_section(c, 310, 380, 260, 210, "FUNCTION RELEASE")
    for label in [
        "LATCHES WITHOUT PUSH",
        "NO DOOR LIFT",
        "NO RATTLE",
        "STOP CONTACT CONTINUOUS",
        "20 CYCLES COMPLETE",
        "FINAL STRIKE TRACE SAVED",
    ]:
        _template_checkbox(c, 320, y, label, size=6.8)
        y -= 23
    _template_field(c, "APPROVER / DATE", 320, y, 240)


def _template_t12(c):
    y = _template_section(c, 38, 682, 532, 170, "SIGNED ADHESIVE TIME BASIS")
    _template_field(c, "ADHESIVE / LOT / TDS REV", 48, y, 244)
    _template_field(c, "SHOP TEMP / RH", 314, y, 246)
    y -= 23
    _template_field(c, "CURRENT PUBLISHED OPEN TIME", 48, y, 244, "______ min")
    _template_field(c, "75% MAX = OPEN x 0.75", 314, y, 246, "______ min")
    y -= 23
    _template_field(c, "REHEARSAL FINAL GATE", 48, y, 244, "______ min")
    _template_field(c, "REHEARSAL <= 75%", 314, y, 246, "PASS / HOLD")
    y -= 23
    _template_field(c, "STAGE A LIVE FINAL GATE", 48, y, 244, "______ min")
    _template_field(c, "STAGE B LIVE FINAL GATE", 314, y, 246, "______ min")
    y -= 23
    _template_wrapped_text(
        c,
        "Timer starts at FIRST ADHESIVE CONTACT. Clamp complete is a CHECKPOINT ONLY; timing continues through final geometry and panel-movement acceptance.",
        48, y, 510, 7.2, 9.5, True, "#A33B32",
    )
    y = _template_section(c, 38, 494, 296, 280, "CLAMP MAP / STAGING")
    door_x, door_y, door_w, door_h = 154, 246, 72, 210
    c.setFillColor(colors.HexColor("#D7B47B"))
    c.setStrokeColor(colors.HexColor(BLUE))
    c.rect(door_x, door_y, door_w, door_h, fill=1, stroke=1)
    for index, clamp_y in enumerate([430, 392, 352, 310, 270], 1):
        color = BLUE if index % 2 else TEAL
        c.setStrokeColor(colors.HexColor(color))
        c.setLineWidth(2.5)
        c.line(102, clamp_y, 278, clamp_y)
        _template_fit_text(c, f"{index}", 90, clamp_y - 3, 10, 7, True, color)
        _template_field(c, f"CLAMP {index}", 48, y - (index - 1) * 23, 76)
        _template_field(c, "PRESSURE", 244, y - (index - 1) * 23, 80)
    _template_checkbox(c, 48, 236, "CAULS PRESET", size=6.5)
    _template_checkbox(c, 150, 236, "SPACERS STAGED", size=6.5)
    _template_checkbox(c, 260, 236, "K/L DRY", size=6.5)
    y = _template_section(c, 348, 494, 222, 280, "FINAL GATES — EACH LIVE STAGE")
    gates = [
        "SHOULDERS CLOSED",
        "DIAGONALS A-B <= 1/16",
        "TWIST <= 1/32",
        "ALL FIVE PANELS MOVE",
        "K/L MOVE IN STAGE A",
        "FINAL GEOMETRY + PANEL-MOVEMENT <= 75%",
        "CLAMP COMPLETE TIME RECORDED",
        "FINAL GATE TIME RECORDED",
    ]
    for label in gates:
        _template_checkbox(c, 358, y, label, size=6.2)
        y -= 24
    _template_field(c, "STAGE / OPERATOR", 358, y, 202)
    y -= 23
    _template_field(c, "APPROVER / DATE", 358, y, 202)
    c.setFillColor(colors.HexColor("#FFF1ED"))
    c.setStrokeColor(colors.HexColor("#A33B32"))
    c.rect(38, 150, 532, 42, fill=1, stroke=1)
    _template_fit_text(c, "HOLD if either rehearsal or live final gate exceeds 75% of CURRENT PUBLISHED OPEN TIME.", 48, 167, 512, 7.2, True, "#A33B32")


def _template_t13(c):
    y = _template_section(c, 38, 682, 532, 88, "USE THE FOUR-PAGE FIELD WORKSHEET FOR PRODUCTION RELEASE")
    _template_field(c, "WORKSHEET REV / PAGE SET", 48, y, 244)
    _template_field(c, "OPENING / ROOM", 314, y, 246)
    y -= 23
    _template_checkbox(c, 48, y, "FACE A", size=6.8)
    _template_checkbox(c, 118, y, "FACE B", size=6.8)
    _template_checkbox(c, 188, y, "FACE B OMIT", size=6.8)
    _template_checkbox(c, 310, y, "FIELD RELEASE SIGNED", size=6.8)
    left_y = _template_section(c, 38, 576, 260, 270, "FACE A QUICK TRANSFER")
    right_y = _template_section(c, 310, 576, 260, 270, "FACE B QUICK TRANSFER / OMIT")
    fields = [
        "W-T / W-M / W-B", "H-L / H-R", "HEAD SCHEME",
        "M-201 CASING", "M-202A/B/C BACKBAND", "M-203 STOP",
        "M-204 CAP EVIDENCE", "M-205 PLINTH EVIDENCE",
        "BASEBOARD / FLOOR DATUM", "WALL PROJECTION / SCRIBE",
    ]
    for label in fields:
        _template_field(c, label, 48, left_y, 240)
        _template_field(c, label, 320, right_y, 240)
        left_y -= 22
        right_y -= 22
    y = _template_section(c, 38, 288, 532, 126, "PERMANENT INSTALLATION ORDER — AFTER FULL FINISH CURE")
    order = ["1 PLINTHS", "2 CASING", "3 BACKBAND / RETURNS", "4 CAP", "5 STOPS LAST"]
    for index, label in enumerate(order):
        box_x = 48 + index * 102
        c.setFillColor(colors.HexColor("#E7EFEE" if index < 4 else "#FFF1ED"))
        c.setStrokeColor(colors.HexColor(TEAL if index < 4 else "#A33B32"))
        c.rect(box_x, y - 35, 92, 40, fill=1, stroke=1)
        _template_fit_text(c, label, box_x + 5, y - 19, 82, 6.2, True, BLUE if index < 4 else "#A33B32")
    _template_field(c, "TRANSFERRED BY / DATE / APPROVAL", 48, 183, 512)


def _template_t14(c):
    y = _template_section(c, 38, 682, 532, 78, "PROJECT / RELEASE IDENTIFICATION")
    _template_field(c, "OPENING / DOOR ID", 48, y, 244)
    _template_field(c, "INSPECTION DATE", 314, y, 246)
    y -= 23
    _template_field(c, "INSPECTOR / OWNER", 48, y, 244)
    _template_field(c, "FINISH CURE DATE", 314, y, 246)
    rows = [
        ["GEOMETRY", "HEAD LEVEL <= 1/16; LEGS PLUMB <= 1/16", "", ""],
        ["REVEALS", "HEAD / SIDES TO RELEASED TARGET", "", ""],
        ["UNDERCUT", "FLOOR / RUG CLEARANCE ACCEPTED", "", ""],
        ["SWING", "FULL ARC; NO RUB OR SPRING-BACK", "", ""],
        ["LATCH", "WORKS WITHOUT PUSH OR LIFT", "", ""],
        ["STOP", "QUIET, CONTINUOUS CONTACT", "", ""],
        ["HINGES", "BARRELS ALIGNED; BRASS AFTER CURE", "", ""],
        ["LOCK / STRIKE", "FACEPLATE FLUSH; JOINT GAP < .010", "", ""],
        ["PANELS", "ALL FIVE RETAIN MOVEMENT", "", ""],
        ["CASING", "REVEAL 3/16 +/- 1/32; SCRIBES CLOSED", "", ""],
        ["BACKBAND", "PROJECTION +/- 1/32; RETURNS CLOSED", "", ""],
        ["CAP / PLINTH", "EVIDENCE + ORDER VERIFIED OR OMIT", "", ""],
        ["FINISH", "UNIFORM; NO POOLS / CONTAMINATION", "", ""],
        ["HARDWARE", "FINAL FASTENERS / PILOTS / TORQUE PASS", "", ""],
    ]
    _template_table(
        c, 38, 582, [82, 286, 76, 88],
        ["SYSTEM", "ACCEPTANCE CRITERION", "PASS / HOLD", "INITIAL / DATE"],
        rows, row_height=23, font_size=6.25,
    )
    y = _template_section(c, 38, 232, 532, 82, "FINAL DISPOSITION")
    _template_checkbox(c, 48, y, "RELEASED", size=6.8)
    _template_checkbox(c, 135, y, "PUNCH LIST", size=6.8)
    _template_checkbox(c, 235, y, "REMAKE / HOLD", size=6.8)
    _template_field(c, "FINAL SIGNATURE / DATE", 344, y - 2, 216)
    y -= 24
    _template_field(c, "PUNCH / HOLD NOTE", 48, y, 512)


_TEMPLATE_RENDERERS = {
    1: _template_t01,
    2: _template_t02,
    3: _template_t03,
    4: _template_t04,
    5: _template_t05,
    6: _template_t06,
    7: _template_t07,
    8: _template_t08,
    9: _template_t09,
    10: _template_t10,
    11: _template_t11,
    12: _template_t12,
    13: _template_t13,
    14: _template_t14,
}


def draw_template_page(c, number, title, subtitle):
    _template_header(c, number, title, subtitle)
    _TEMPLATE_RENDERERS[number](c)
    _template_footer(c)


def build_templates_pdf(path: Path) -> int:
    from reportlab.pdfgen import canvas

    pages = [
        ("Completed-jamb measurement worksheet", "Record the completed opening, floor, swing, hardware, and adjacent evidence before slab fitting."),
        ("Master story stick", "Create one signed physical master; the plotted orientation map is NTS and written stations control."),
        ("Rail-location story stick", "Transfer every shoulder and opening ID from the approved master without chained measurements."),
        ("Domino joint centerlines", "Full-size 4-inch rail-end layout plus setup, test-piece, and release controls."),
        ("Wide-rail multiple-tenon layout", "Full-size lock-rail pattern and split full-size bottom-rail pattern for accurate transfer."),
        ("Muntin joint layout", "Full-size D-101G and receiver-footprint layouts with sectioned web acceptance records."),
        ("Domino setup register", "Record every J-01 through J-12 setup, test result, and release before production."),
        ("Domino test-piece worksheet", "Prove untouched factory tenons first; condition only a separate, never-shortened rehearsal set."),
        ("Hinge layout", "Trace and measure the actual leaf, transfer three gains, and release only on steel setup screws."),
        ("Lock verification worksheet", "Measure the actual lock, strike, screws, and J-06 clearance before any stile machining."),
        ("Strike transfer guide", "Transfer from the naturally latched hanging door; never locate the strike from nominal dimensions."),
        ("Glue-up clamp map", "Use current published OPEN time; both rehearsal and live final gates must finish at or below 75%."),
        ("Moulding measurement worksheet", "Quick-transfer card for the mandatory four-page Face A / Face B production worksheet."),
        ("Final inspection record", "Release geometry, function, movement, trim, finish, and hardware as one completed system."),
    ]
    c = canvas.Canvas(str(path), pagesize=letter)
    for number, (title, subtitle) in enumerate(pages, 1):
        draw_template_page(c, number, title, subtitle)
        c.showPage()
    c.save()
    return len(pages)


def build_moulding_pdf(path: Path) -> int:
    from reportlab.pdfgen import canvas
    titles = ["Door stop profile","Side casing elevation","Head casing elevation","Casing cross section","Backband cross section","Casing and backband assembly","Optional head-cap assembly","Plinth-block detail","Completed jamb/stop/door/wall section","Baseboard-to-plinth and corner conditions","Fastener locations and scribing allowance","Finished installed opening QC"]
    c=canvas.Canvas(str(path),pagesize=letter)
    for i,title in enumerate(titles,1):
        c.setFont("Helvetica-Bold",16); c.setFillColor(colors.HexColor(BLUE)); c.drawString(.6*inch,10.25*inch,f"M-{i:02d} {title}")
        c.setFont("Helvetica",8); c.setFillColor(colors.HexColor(INK)); c.drawString(.6*inch,10*inch,f"DC-1916-001 | {SPEC['project']['revision']} | Scale: NTS unless printed dimensions shown | Material: quarter-sawn white oak")
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
    page_fields = [
        [
            "Completed jamb W: top / middle / bottom; H: left / right",
            "Left jamb leg plumb: opening plane / wall-normal plane",
            "Right jamb leg plumb: opening plane / wall-normal plane",
            "Head level; diagonals A / B / difference; square; winding-stick twist",
        ],
        [
            "Jamb projection; wall flatness; framing; utilities; fastener layer stack",
            "Casing / backband / stop profile evidence; M-202C mandatory",
            "Optional cap evidence and plinth / baseboard evidence",
            "Head scheme, finish sample, corner, scribe, and self-return conditions",
        ],
        [
            "FACE A controls - W / H-L / H-R / datum / head scheme / cap / plinth",
            "FACE A full register - M-201; M-202A/B/C; M-203; M-204; M-205",
            "FACE A fastener proof - 0.75 jamb / 1.0 framing / 0.50 casing",
            "FACE A release - stock allowance; finish sample; photographs; notes",
        ],
        [
            "FACE B controls - W / H-L / H-R / datum / scheme / cap / plinth / OMIT",
            "FACE B full register - M-201; M-202A/B/C; M-203; M-204; M-205",
            "FACE B fastener proof - 0.75 jamb / 1.0 framing / 0.50 casing",
            "FINAL - cured plinths / casing / band + returns / cap / stops last",
        ],
    ]
    c=canvas.Canvas(str(path),pagesize=letter)
    for page, subset in enumerate(page_fields, 1):
        c.setFont("Helvetica-Bold",16); c.drawString(.6*inch,10.25*inch,"Moulding and Completed-Jamb Field Worksheet")
        c.setFont("Helvetica",9); c.drawString(.6*inch,10*inch,f"DC-1916-001 | {SPEC['project']['revision']} | Page {page} of 4 | FIELD VERIFY BEFORE MILLING")
        y=9.3*inch
        for field in subset:
            c.setFont("Helvetica-Bold",10); c.drawString(.7*inch,y,field)
            for k in range(5): c.line(.7*inch,y-(k+1)*.34*inch,7.8*inch,y-(k+1)*.34*inch)
            y-=2.05*inch
        c.showPage()
    c.save(); return 4


def build_report(counts: dict) -> None:
    companion_counts = {
        "quick": 17,
        "visual_assembly": 23,
        "project_plans": 13,
        "custom_moulding": 19,
        "cabinetmakers": 64,
        "shopping": 2,
        "labeled_stock": 5,
        "rough_length": 4,
    }
    total_pages = sum(counts.values()) + sum(companion_counts.values())
    text = f"""# DC-1916-001 Build Report

## Created

Complete Markdown manuscript; JSON-compatible YAML specification; historical, engineering, and modern-construction standards; procurement and cut lists; labeled-stock plan and five-page cut sheet; RL-02 four-page rough-length cut list; DF 500 register; matched SVG/PNG technical figures and 3D renderings; self-contained HTML; print and screen manuals; visual cut-and-assembly guide; 23-page image-led visual assembly guide with a front-of-guide A-O board-to-part reference; 13-page widescreen project-plans booklet; integrated cabinetmaker guide; custom-moulding manual; template package; moulding drawings; field worksheet; source archive; and SHA-256 checksums.

## Rev. G controlled fitted geometry

- The confirmed installed finished jamb opening is 24 x 81 inches. Required gaps are 1/8 inch at both sides, 1/8 inch at the head, and 3/8 inch at the bottom.
- The finished fitted slab is 23-3/4 x 80-1/2 x 1-3/8 inches. The cured and surfaced pre-fit assembly is 23-7/8 x 80-5/8 inches, carrying 1/16 inch removable stock outside each final perimeter edge.
- LS-05 stile cores are 81 inches and continuous face lamellae are 81-1/8 inches. Finished stile width is 4-1/4 inches from 4-3/8-inch layer lanes. Rail mother billets are 16-1/4 inches; finished rail shoulder length is 15-1/4 inches.
- Rail widths remain unchanged. P-01 is 14-1/4 inches and P-02 is 14-3/4 inches; P-03 and P-04 remain 9-1/2 and 11 inches. The two lower bays are 6-1/8 inches each.
- The lock center remains 40 inches above the slab bottom and is 40-1/2 inches below the finished slab top.
- D-101H is 15-7/8 x 15-1/16 inches finished / 16-3/8 x 15-9/16 inches rough; D-101J is 15-7/8 x 15-9/16 inches finished / 16-3/8 x 16-1/16 inches rough.
- All five floating panels retain the controlled 3/4-inch-long foam spacer system.

## LS-05 no-resaw door-only rough-stock and balanced-lamination revision

- The owner confirmed that STOCK-A through STOCK-L began as raw rough-sawn, unjointed, and unplaned stock. A's current usable length is 72-3/4 inches after the required 6-inch damage removal. STOCK-G is now confirmed S4S at 15/16 x 4-1/2 x 75 inches. Its thickness exceeds the 5/8-inch D-101J rough-panel minimum by 5/16 inch, and its four-stave width/length plan leaves a 6-1/4-inch planning tail. CHK-P-01 still controls physical yield. L's current edge-cleaned width is 6 inches. STOCK-M was later added as reported finished white oak at 3/4 x 8-1/4 x 99 inches. STOCK-N/O are confirmed finished white oak at 1-3/4 x 11 x 74 inches each. Moisture, flatness, defects, and clear yield remain physical shop checks.
- Every A-O board is reserved exclusively for the door, its same-layup coupons, setup pieces, substitutions, and repair stock. STOCK-M carries D-101H, STOCK-A remains intact as panel reserve, and STOCK-N/O remain full as short-member core reserve. The present door-lumber purchase is zero only while all physical yield and coupon gates pass.
- Every frame member uses a balanced 5/16 + 7/8 + 5/16 all-long-grain glue blank, surfaced equally to 1/4 + 7/8 + 1/4 = 1-3/8 inches. Cores and faces are made by jointing, ordinary width ripping where assigned, staged thickness planing, resting, and rechecking; no A-O board is resawn.
- STOCK-I/K are each ripped by width into two continuous 4-3/8-inch stile lanes, one planed to a 7/8-inch core and one to a 5/16-inch face; STOCK-B/C each supply one additional continuous 5/16-inch face. The remaining boards provide the LS-05 panel, short-member, coupon, setup, and reserve map.
- D-101D and D-101F use the controlled staggered core/show/back seam maps. All other listed cores are one piece, and every structural layer is continuous for the member length.
- The separate both-face moulding order is seven S4S 4/4 x nominal 6-inch x 8-foot boards plus two S4S 6/4 x nominal 6-inch x 8-foot boards, approximately 40 dealer board feet. Plinths remain field-controlled and excluded.

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
- Quick cut-and-assembly guide: {companion_counts['quick']} pages
- Image-led visual assembly guide: {companion_counts['visual_assembly']} pages
- Widescreen five-panel door project plans: {companion_counts['project_plans']} pages
- Custom moulding shop manual: {companion_counts['custom_moulding']} pages
- Cabinetmaker's builder guide: {companion_counts['cabinetmakers']} pages
- Door shopping list: {companion_counts['shopping']} pages
- Labeled-stock cut sheet: {companion_counts['labeled_stock']} pages
- Rough-length cut list: {companion_counts['rough_length']} pages
- Total controlled PDF pages: {total_pages}

## Visual QA

Status after generation: **PENDING RENDERED-PAGE INSPECTION.** A rebuild invalidates prior visual acceptance. Record the final page-by-page result in `build/reports/visual-qc.md` and add the release result here only after the final PDFs have been rendered and inspected.

## Field-verification items

{chr(10).join('- ' + x for x in SPEC['field_verify'])}

## Genuine limitations

No original door, blueprint, or room-specific trim schedule was supplied; the design is historically appropriate, not an exact reproduction. Structural choices are conservative cabinetmaking practice, not stamped engineering. The completed-jamb and physical-hardware gates must be closed before irreversible milling. The generated cover is an illustrative visualization; technical drawings and specification control geometry.

## Exact release path

`{RELEASE}`
"""
    write(RELEASE / "DC-1916-001_Build_Report.md", text)
    write(BUILD / "reports" / "visual-qc.md", f"""# Visual QC

Date: 2026-07-25

Status: **PENDING — rendered-page inspection required.**

Generated-output metadata lists {total_pages} pages: {counts['print']} print-manual pages, {counts['screen']} screen-manual pages, {counts['templates']} template pages, {counts['moulding']} moulding-drawing pages, {counts['worksheet']} worksheet pages, {companion_counts['quick']} quick-guide pages, {companion_counts['visual_assembly']} image-led visual-assembly-guide pages, {companion_counts['project_plans']} widescreen project-plans pages, {companion_counts['custom_moulding']} custom-moulding-manual pages, {companion_counts['cabinetmakers']} cabinetmaker-guide pages, {companion_counts['shopping']} door-shopping-list pages, {companion_counts['labeled_stock']} labeled-stock-cut-sheet pages, and {companion_counts['rough_length']} rough-length-cut-list pages. These counts are not visual acceptance.

- Clipped or overlapping text: requires rendered-page inspection.
- Broken tables, blank production pages, or failed figures: requires rendered-page inspection.
- Cover composition and five-panel arrangement: requires rendered-page inspection.
- Technical-figure legibility, labels, revision marks, and references: requires rendered-page inspection.
- Headers, footers, page numbers, margins, and chapter transitions: requires rendered-page inspection.
- Template calibration squares and Actual Size instructions: requires rendered-page inspection.
- Moulding drawings and field-verification language: requires rendered-page inspection.

Critical defects: not assessed. Major defects: not assessed. Release decision: **PENDING RENDERED QA**.
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
            relative = p.relative_to(ROOT)
            if (
                p.is_dir()
                or RELEASE in p.parents
                or BUILD in p.parents
                or relative.parts[0] in {"output", "outputs"}
                or "tmp" in relative.parts
                or "__pycache__" in p.parts
                or ".git" in p.parts
                or p.name == ".DS_Store"
            ):
                continue
            z.write(p, Path("halfbathdoor") / relative)


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
