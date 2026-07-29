#!/usr/bin/env python3
"""Validate the governing door and floating-panel dimensions."""

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ABS_TOL = 1e-8


def close(actual, expected, tolerance=ABS_TOL):
    return abs(actual - expected) <= tolerance


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def load_specification():
    return json.loads((ROOT / "project/specification.yaml").read_text(encoding="utf-8"))


def validate(specification=None):
    """Return calculated clearance limits after validating the specification."""

    spec = specification or load_specification()
    opening = spec["opening"]
    slab = spec["slab"]
    frame = spec["frame"]
    panels = spec["panels"]
    groove = spec["groove"]
    domino = spec["domino"]
    milling = spec["milling"]
    tolerances = spec["fabrication_tolerances"]

    derived_fitted_width = (
        opening["clear_width"]
        - opening["hinge_side_reveal"]
        - opening["lock_side_reveal"]
    )
    derived_fitted_height = (
        opening["clear_height"]
        - opening["head_reveal"]
        - opening["bottom_gap"]
    )
    require(
        close(derived_fitted_width, slab["finished_width"]),
        (
            f"24-inch jamb width and specified side reveals derive "
            f"{derived_fitted_width}, not {slab['finished_width']} inches"
        ),
    )
    require(
        close(derived_fitted_height, slab["finished_height"]),
        (
            f"81-inch jamb height, head reveal, and bottom gap derive "
            f"{derived_fitted_height}, not {slab['finished_height']} inches"
        ),
    )
    trim_reserve = slab["manufacturing_trim_reserve_per_edge"]
    require(
        close(
            milling["prefit_assembly_width"],
            slab["finished_width"] + 2 * trim_reserve,
        )
        and close(
            milling["prefit_assembly_height"],
            slab["finished_height"] + 2 * trim_reserve,
        ),
        "prefit assembly does not carry the governed trim reserve on all four edges",
    )
    finished_size_tolerance = slab["finished_size_tolerance"]
    require(
        close(finished_size_tolerance["width_plus"], 0)
        and close(finished_size_tolerance["height_plus"], 0),
        "the fitted slab must not carry positive width or height tolerance",
    )
    installed_gap_tolerance = opening["installed_gap_tolerance_plus_minus"]
    require(
        all(value >= 0 for value in installed_gap_tolerance.values()),
        "installed reveal and bottom-gap tolerances must be non-negative",
    )

    calculated_width = 2 * frame["stile_width"] + frame["rail_shoulder_length"]
    require(
        close(calculated_width, slab["finished_width"]),
        f"frame width stack is {calculated_width}, not {slab['finished_width']} inches",
    )

    calculated_height = sum(frame["rail_widths"].values()) + sum(
        frame["vertical_openings"].values()
    )
    require(
        close(calculated_height, slab["finished_height"]),
        f"frame height stack is {calculated_height}, not {slab['finished_height']} inches",
    )

    calculated_bottom_opening = (
        frame["rail_shoulder_length"] - frame["muntin_width"]
    ) / 2
    require(
        close(calculated_bottom_opening, frame["bottom_opening_each"]),
        "bottom-panel openings do not divide equally around the center muntin",
    )

    components = {component["id"]: component for component in spec["components"]}
    panel_components = {
        part_id: component
        for part_id, component in components.items()
        if "panel" in component["name"].lower()
    }
    expected_panel_ids = {"D-101H", "D-101J", "D-101N", "D-101K", "D-101L"}
    require(
        set(panel_components) == expected_panel_ids,
        f"panel identifiers are {sorted(panel_components)}, expected {sorted(expected_panel_ids)}",
    )

    width_inputs = {
        "D-101H": (
            frame["rail_shoulder_length"],
            panels["full_width_clearance_across_grain_total"],
        ),
        "D-101J": (
            frame["rail_shoulder_length"],
            panels["full_width_clearance_across_grain_total"],
        ),
        "D-101N": (
            frame["rail_shoulder_length"],
            panels["full_width_clearance_across_grain_total"],
        ),
        "D-101K": (
            frame["bottom_opening_each"],
            panels["small_width_clearance_across_grain_total"],
        ),
        "D-101L": (
            frame["bottom_opening_each"],
            panels["small_width_clearance_across_grain_total"],
        ),
    }
    length_inputs = {
        "D-101H": frame["vertical_openings"]["P-01 upper"],
        "D-101J": frame["vertical_openings"]["P-02 center"],
        "D-101N": frame["vertical_openings"]["P-03 lower-center"],
        "D-101K": frame["vertical_openings"]["P-04 bottom"],
        "D-101L": frame["vertical_openings"]["P-04 bottom"],
    }
    tongue_depth = panels["tongue_depth"]
    parallel_clearance = panels["clearance_parallel_to_grain_total"]
    for part_id, (clear_opening, movement_clearance) in width_inputs.items():
        expected_width = clear_opening + 2 * tongue_depth - movement_clearance
        require(
            close(panel_components[part_id]["w"], expected_width),
            (
                f"{part_id} width is {panel_components[part_id]['w']}, but its "
                f"opening/tongue/clearance formula requires {expected_width} inches"
            ),
        )

    for part_id, clear_opening in length_inputs.items():
        expected_length = clear_opening + 2 * tongue_depth - parallel_clearance
        require(
            close(panel_components[part_id]["l"], expected_length),
            (
                f"{part_id} length is {panel_components[part_id]['l']}, but its "
                f"opening/tongue/clearance formula requires {expected_length} inches"
            ),
        )
        require(
            close(panel_components[part_id]["t"], panels["field_thickness"]),
            f"{part_id} thickness does not match the governed panel field thickness",
        )

    groove_width_tolerance = tolerances["groove_width"]
    groove_depth_tolerance = tolerances["groove_depth"]
    require(
        close(groove["width"], groove_width_tolerance["target"]),
        "nominal groove width and fabrication-tolerance target disagree",
    )
    require(
        close(groove["depth"], groove_depth_tolerance["target"]),
        "nominal groove depth and fabrication-tolerance target disagree",
    )
    require(
        groove_width_tolerance["minus"] >= 0
        and groove_width_tolerance["plus"] >= 0
        and groove_depth_tolerance["minus"] >= 0
        and groove_depth_tolerance["plus"] >= 0,
        "groove tolerances must use non-negative plus/minus magnitudes",
    )

    groove_width_min = (
        groove_width_tolerance["target"] - groove_width_tolerance["minus"]
    )
    tongue_thickness_tolerance = panels["tongue_thickness_tolerance_plus_minus"]
    require(
        tongue_thickness_tolerance > 0
        and panels["tongue_thickness"] - tongue_thickness_tolerance > 0,
        "panel tongue thickness tolerance must be positive and leave a positive minimum thickness",
    )
    tongue_thickness_min = panels["tongue_thickness"] - tongue_thickness_tolerance
    tongue_thickness_max = panels["tongue_thickness"] + tongue_thickness_tolerance
    tongue_side_clearance_min = groove_width_min - tongue_thickness_max
    require(
        tongue_side_clearance_min > 0,
        "the panel tongue can bind in the narrowest permitted groove",
    )

    tongue_depth_tolerance = panels["tongue_depth_tolerance_plus_minus"]
    tongue_depth_min = tongue_depth - tongue_depth_tolerance
    tongue_depth_max = tongue_depth + tongue_depth_tolerance
    groove_depth_min = (
        groove_depth_tolerance["target"] - groove_depth_tolerance["minus"]
    )
    groove_depth_max = (
        groove_depth_tolerance["target"] + groove_depth_tolerance["plus"]
    )
    nominal_bottom_clearance = groove["depth"] - tongue_depth
    minimum_bottom_clearance = groove_depth_min - tongue_depth_max
    maximum_bottom_clearance = groove_depth_max - tongue_depth_min
    require(
        close(nominal_bottom_clearance, panels["tongue_bottom_clearance_nominal"]),
        "the specified nominal tongue-bottom clearance does not equal groove depth minus tongue depth",
    )
    require(
        minimum_bottom_clearance > 0,
        (
            "the deepest permitted tongue bottoms out in the shallowest permitted "
            f"groove (calculated clearance {minimum_bottom_clearance:.4f} inches)"
        ),
    )

    corner_relief_match = re.search(
        r"(\d+)/(\d+)\s*x\s*(\d+)/(\d+)-inch tongue corner square",
        groove["panel_tongue_corner_relief"],
    )
    require(
        corner_relief_match is not None,
        "panel tongue-corner relief does not state two numeric relief dimensions",
    )
    first_numerator, first_denominator, second_numerator, second_denominator = map(
        float, corner_relief_match.groups()
    )
    require(
        close(first_numerator / first_denominator, tongue_depth)
        and close(second_numerator / second_denominator, tongue_depth),
        "panel tongue-corner relief does not match the governed tongue depth",
    )

    require(
        close(groove["centerline_from_show_face"], slab["finished_thickness"] / 2),
        "the panel groove is not centered through the finished door thickness",
    )
    expected_footprint = [
        frame["bottom_opening_each"],
        frame["bottom_opening_each"] + frame["muntin_width"],
    ]
    expected_segments = [
        [0.0, expected_footprint[0]],
        [expected_footprint[1], frame["rail_shoulder_length"]],
    ]
    require(
        groove["segmented_rail_edges"]
        == {
            "D-101E bottom": expected_segments,
            "D-101F top": expected_segments,
        },
        "the two bottom-opening rail edges do not preserve the governed muntin footprint",
    )
    require(
        groove["muntin_footprint_from_hinge_side_rail_shoulder"]
        == expected_footprint,
        "the stated muntin footprint does not match the segmented groove limits",
    )

    require(
        close(
            milling["rail_rough_length"],
            frame["rail_shoulder_length"]
            + milling["rail_rough_length_allowance_total"],
        ),
        "rail rough length does not equal finished shoulder length plus its allowance",
    )
    require(
        milling["stile_rough_length_allowance_total"] > 0
        and milling["muntin_rough_length_allowance_total"] > 0,
        "frame members require positive rough-length allowances",
    )

    construction = frame["construction"]
    preglue_stack = (
        construction["show_face_preglue_thickness"]
        + construction["core_preglue_thickness"]
        + construction["back_face_preglue_thickness"]
    )
    finished_stack = (
        construction["show_face_finished_thickness"]
        + construction["core_preglue_thickness"]
        + construction["back_face_finished_thickness"]
    )
    require(
        close(preglue_stack, construction["glue_blank_thickness"])
        and close(preglue_stack, milling["frame_rough_thickness"]),
        "balanced preglue layer stack does not equal the 1-1/2-inch glue blank",
    )
    require(
        close(finished_stack, slab["finished_thickness"]),
        "balanced finished layer stack does not equal the 1-3/8-inch slab",
    )
    glue_lines = construction["finished_glue_lines_from_show_face"]
    require(
        glue_lines == [
            construction["show_face_finished_thickness"],
            construction["show_face_finished_thickness"]
            + construction["core_preglue_thickness"],
        ],
        "finished frame glue lines do not bound the governed core",
    )
    groove_envelope = (
        groove["centerline_from_show_face"] - groove["width"] / 2,
        groove["centerline_from_show_face"] + groove["width"] / 2,
    )
    cutter_error = domino["mortise_centerline_tolerance_plus_minus"]
    glue_line_error = construction[
        "face_glue_line_location_tolerance_plus_minus"
    ]
    required_core_clearance = construction[
        "df_cutter_to_face_glue_line_core_clearance_min"
    ]
    cutter_envelopes = {"groove": groove_envelope}
    for cutter_mm in (10, 6):
        half_width_in = cutter_mm / 2 / 25.4
        centerline_in = domino["fence_height_mm"] / 25.4
        cutter_envelopes[f"{cutter_mm}mm"] = (
            centerline_in - half_width_in,
            centerline_in + half_width_in,
        )
    for feature, envelope in cutter_envelopes.items():
        worst_clearance = min(
            envelope[0] - glue_lines[0],
            glue_lines[1] - envelope[1],
        ) - cutter_error - glue_line_error
        require(
            worst_clearance >= required_core_clearance,
            f"{feature} worst-case envelope leaves only {worst_clearance:.4f} inch "
            "to a face glue line",
        )

    return {
        "calculated_width": calculated_width,
        "calculated_height": calculated_height,
        "derived_fitted_width": derived_fitted_width,
        "derived_fitted_height": derived_fitted_height,
        "prefit_width": milling["prefit_assembly_width"],
        "prefit_height": milling["prefit_assembly_height"],
        "nominal_bottom_clearance": nominal_bottom_clearance,
        "minimum_bottom_clearance": minimum_bottom_clearance,
        "maximum_bottom_clearance": maximum_bottom_clearance,
        "minimum_tongue_side_clearance": tongue_side_clearance_min,
        "minimum_tongue_thickness": tongue_thickness_min,
        "maximum_tongue_thickness": tongue_thickness_max,
    }


if __name__ == "__main__":
    results = validate()
    print(
        "PASS: door stack, five panel formulas, and tongue/groove tolerance "
        f"envelope (minimum bottom clearance {results['minimum_bottom_clearance']:.4f} in)"
    )
