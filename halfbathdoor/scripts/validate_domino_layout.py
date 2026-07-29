#!/usr/bin/env python3
"""Validate the DF 500 register and worst-case mortise/groove geometry."""

import csv
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MM_PER_INCH = 25.4
ABS_TOL = 1e-8

FRAME_JOINT_PARTS = {
    "J-01": "D-101C",
    "J-02": "D-101C",
    "J-03": "D-101M",
    "J-04": "D-101M",
    "J-05": "D-101D",
    "J-06": "D-101D",
    "J-07": "D-101E",
    "J-08": "D-101E",
    "J-09": "D-101F",
    "J-10": "D-101F",
}
MUNTIN_JOINTS = {"J-11", "J-12"}
GROOVED_RAIL_EDGES = {
    "D-101C": {"bottom"},
    "D-101M": {"top", "bottom"},
    "D-101D": {"top", "bottom"},
    "D-101E": {"top", "bottom"},
    "D-101F": {"top"},
}


def close(actual, expected, tolerance=ABS_TOL):
    return abs(actual - expected) <= tolerance


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def parse_measurement(value, unit):
    match = re.fullmatch(
        rf"\s*(-?\d+(?:\.\d+)?)\s*{re.escape(unit)}\s*", value
    )
    require(match is not None, f"cannot parse {value!r} as a {unit} measurement")
    return float(match.group(1))


def parse_centers(value):
    return [parse_measurement(item, "in") for item in value.split(";")]


def mortise_length_in(specification, setting, cutter_mm):
    formula = specification["domino"]["mortise_widths"][setting]
    match = re.fullmatch(
        r"\s*(\d+(?:\.\d+)?)\s*mm\s*\+\s*cutter\s*", formula
    )
    require(
        match is not None,
        f"unsupported {setting!r} mortise-width formula {formula!r}",
    )
    return (float(match.group(1)) + cutter_mm) / MM_PER_INCH


def load_inputs():
    specification = json.loads(
        (ROOT / "project/specification.yaml").read_text(encoding="utf-8")
    )
    with (ROOT / "project/domino-setup-register.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        rows = list(csv.DictReader(handle))
    return specification, rows


def _validate_register(specification, rows):
    expected_ids = set(FRAME_JOINT_PARTS) | MUNTIN_JOINTS
    by_id = {row["Joint ID"]: row for row in rows}
    require(len(rows) == 12, f"register contains {len(rows)} rows, expected 12")
    require(len(by_id) == len(rows), "register contains duplicate joint identifiers")
    require(
        set(by_id) == expected_ids,
        f"register IDs are {sorted(by_id)}, expected {sorted(expected_ids)}",
    )

    domino = specification["domino"]
    expected_model = " ".join(domino["model"].split()[-2:])
    for joint_id in sorted(expected_ids):
        row = by_id[joint_id]
        cutter = parse_measurement(row["Cutter diameter"], "mm")
        plunge_a = parse_measurement(row["Plunge depth Part A"], "mm")
        plunge_b = parse_measurement(row["Plunge depth Part B"], "mm")
        fence_height = parse_measurement(row["Fence height"], "mm")
        fence_angle = parse_measurement(row["Fence angle"], "deg")
        count = int(row["Number of tenons"])
        centers_a = parse_centers(
            row["Tenon centerline Part A from reference edge"]
        )
        centers_b = parse_centers(
            row["Tenon centerline Part B from reference edge"]
        )

        require(row["Domino model"] == expected_model, f"{joint_id} model is wrong")
        require(cutter in domino["cutters_mm"], f"{joint_id} cutter is not permitted")
        require(
            plunge_a in domino["plunge_presets_mm"]
            and plunge_b in domino["plunge_presets_mm"],
            f"{joint_id} uses an unregistered plunge preset",
        )
        require(
            plunge_a <= domino["maximum_plunge_mm"]
            and plunge_b <= domino["maximum_plunge_mm"],
            f"{joint_id} exceeds the DF 500 plunge limit",
        )
        require(
            close(fence_height, domino["fence_height_mm"])
            and close(fence_angle, domino["fence_angle_degrees"]),
            f"{joint_id} fence setup differs from the specification",
        )
        require(
            count == len(centers_a) == len(centers_b),
            f"{joint_id} tenon count and centerline counts disagree",
        )
        require(
            all(right > left for left, right in zip(centers_a, centers_a[1:])),
            f"{joint_id} Part A centerlines are not strictly increasing",
        )
        require(
            all(right > left for left, right in zip(centers_b, centers_b[1:])),
            f"{joint_id} Part B centerlines are not strictly increasing",
        )

        tenon_match = re.fullmatch(
            r"\s*(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\s*mm\s*",
            row["Tenon dimensions"],
        )
        require(tenon_match is not None, f"{joint_id} tenon dimensions are malformed")
        tenon_thickness, tenon_length = map(float, tenon_match.groups())
        require(
            close(tenon_thickness, cutter),
            f"{joint_id} cutter and tenon thickness disagree",
        )
        require(
            close(tenon_length, plunge_a + plunge_b),
            f"{joint_id} paired plunges do not equal the factory tenon length",
        )

        if joint_id in MUNTIN_JOINTS:
            expected_a = domino["muntin_centers_in"][
                "D-101G from left reference edge"
            ]
            expected_b = domino["muntin_centers_in"][
                "D-101E and D-101F from hinge-side shoulder"
            ]
            require(row["Part A"] == "D-101G", f"{joint_id} Part A must be D-101G")
            require(
                row["Mortise-width setting Part A"] == "both tight"
                and row["Mortise-width setting Part B"]
                == "first tight; second medium",
                f"{joint_id} muntin width strategy is wrong",
            )
            require(
                row["Tight or loose designation Part A"] == "T,T"
                and row["Tight or loose designation Part B"] == "T,L",
                f"{joint_id} muntin tight/loose designations are wrong",
            )
        else:
            part = FRAME_JOINT_PARTS[joint_id]
            expected_a = domino["frame_centers_from_rail_top_in"][part]
            expected_b = domino["stile_centers_from_slab_top_in"][part]
            require(row["Part A"] == part, f"{joint_id} has the wrong rail Part A")
            expected_designation = "T," + ",".join(
                "L" for _ in range(count - 1)
            )
            require(
                row["Mortise-width setting Part A"]
                == "first tight; remaining medium"
                and row["Mortise-width setting Part B"]
                == "first tight; remaining medium",
                f"{joint_id} frame width strategy is wrong",
            )
            require(
                row["Tight or loose designation Part A"] == expected_designation
                and row["Tight or loose designation Part B"]
                == expected_designation,
                f"{joint_id} frame tight/loose designations are wrong",
            )

        require(
            len(expected_a) == len(centers_a)
            and all(close(a, b) for a, b in zip(centers_a, expected_a)),
            f"{joint_id} Part A register centers {centers_a} differ from {expected_a}",
        )
        require(
            len(expected_b) == len(centers_b)
            and all(close(a, b) for a, b in zip(centers_b, expected_b)),
            f"{joint_id} Part B register centers {centers_b} differ from {expected_b}",
        )

    return by_id


def _geometry_metrics(specification):
    domino = specification["domino"]
    frame = specification["frame"]
    groove = specification["groove"]
    tolerances = specification["fabrication_tolerances"]
    center_tolerance = domino["mortise_centerline_tolerance_plus_minus"]
    groove_depth_tolerance = tolerances["groove_depth"]
    require(
        close(groove["depth"], groove_depth_tolerance["target"]),
        "groove depth and its fabrication-tolerance target disagree",
    )
    maximum_groove_depth = (
        groove_depth_tolerance["target"] + groove_depth_tolerance["plus"]
    )

    frame_cutter = 10.0
    tight_frame = mortise_length_in(specification, "tight", frame_cutter)
    medium_frame = mortise_length_in(specification, "medium", frame_cutter)
    frame_webs = []
    frame_inter_mortise_webs = []
    for part, centers in domino["frame_centers_from_rail_top_in"].items():
        settings = ["tight"] + ["medium"] * (len(centers) - 1)
        lengths = [
            tight_frame if setting == "tight" else medium_frame
            for setting in settings
        ]
        edges = GROOVED_RAIL_EDGES[part]
        if "top" in edges:
            frame_webs.append(
                centers[0]
                - lengths[0] / 2
                - maximum_groove_depth
                - center_tolerance
            )
        if "bottom" in edges:
            frame_webs.append(
                frame["rail_widths"][part]
                - maximum_groove_depth
                - centers[-1]
                - lengths[-1] / 2
                - center_tolerance
            )
        for index in range(len(centers) - 1):
            frame_inter_mortise_webs.append(
                centers[index + 1]
                - centers[index]
                - lengths[index] / 2
                - lengths[index + 1] / 2
                - 2 * center_tolerance
            )

    minimum_frame_web = min(frame_webs)
    minimum_frame_inter_web = min(frame_inter_mortise_webs)
    require(
        minimum_frame_web
        >= tolerances["frame_medium_mortise_web_to_panel_groove_min"],
        (
            "worst-case rail mortise-to-groove web is "
            f"{minimum_frame_web:.4f} inches, below "
            f"{tolerances['frame_medium_mortise_web_to_panel_groove_min']:.4f}"
        ),
    )
    require(
        minimum_frame_inter_web > 0,
        "worst-case frame-rail mortises overlap after centerline tolerance",
    )

    muntin_cutter = 6.0
    tight_muntin = mortise_length_in(specification, "tight", muntin_cutter)
    medium_muntin = mortise_length_in(specification, "medium", muntin_cutter)
    muntin_centers = domino["muntin_centers_in"][
        "D-101G from left reference edge"
    ]
    left_muntin_web = (
        muntin_centers[0]
        - tight_muntin / 2
        - maximum_groove_depth
        - center_tolerance
    )
    right_muntin_web = (
        frame["muntin_width"]
        - maximum_groove_depth
        - muntin_centers[1]
        - tight_muntin / 2
        - center_tolerance
    )
    minimum_muntin_groove_web = min(left_muntin_web, right_muntin_web)
    muntin_inter_mortise_web = (
        muntin_centers[1]
        - muntin_centers[0]
        - tight_muntin
        - 2 * center_tolerance
    )
    require(
        minimum_muntin_groove_web
        >= tolerances["muntin_tight_mortise_web_to_side_groove_min"],
        (
            "worst-case muntin mortise-to-groove web is "
            f"{minimum_muntin_groove_web:.4f} inches, below "
            f"{tolerances['muntin_tight_mortise_web_to_side_groove_min']:.4f}"
        ),
    )
    require(
        muntin_inter_mortise_web
        >= tolerances["muntin_tight_inter_mortise_web_min"],
        (
            "worst-case muntin inter-mortise web is "
            f"{muntin_inter_mortise_web:.4f} inches, below "
            f"{tolerances['muntin_tight_inter_mortise_web_min']:.4f}"
        ),
    )

    rail_centers = domino["muntin_centers_in"][
        "D-101E and D-101F from hinge-side shoulder"
    ]
    rail_inter_mortise_web = (
        rail_centers[1]
        - rail_centers[0]
        - tight_muntin / 2
        - medium_muntin / 2
        - 2 * center_tolerance
    )
    require(
        rail_inter_mortise_web
        >= tolerances["muntin_rail_inter_mortise_web_min"],
        (
            "worst-case mating-rail inter-mortise web is "
            f"{rail_inter_mortise_web:.4f} inches, below "
            f"{tolerances['muntin_rail_inter_mortise_web_min']:.4f}"
        ),
    )

    solid_start, solid_end = groove[
        "muntin_footprint_from_hinge_side_rail_shoulder"
    ]
    require(
        rail_centers[0] - tight_muntin / 2 - center_tolerance >= solid_start,
        "the tight mating-rail mortise can enter the left groove segment",
    )
    require(
        rail_centers[1] + medium_muntin / 2 + center_tolerance <= solid_end,
        "the medium mating-rail mortise can enter the right groove segment",
    )
    expected_segments = [[0.0, solid_start], [solid_end, frame["rail_shoulder_length"]]]
    require(
        all(
            segments == expected_segments
            for segments in groove["segmented_rail_edges"].values()
        ),
        "segmented rail grooves do not terminate at the governed solid footprint",
    )

    thickness_tolerance = tolerances["frame_thickness"]
    minimum_frame_thickness = (
        thickness_tolerance["target"] - thickness_tolerance["plus_minus"]
    )
    fence_centerline = domino["fence_height_mm"] / MM_PER_INCH
    face_webs = []
    for cutter in (frame_cutter, muntin_cutter):
        cutter_radius = cutter / MM_PER_INCH / 2
        face_webs.extend(
            [
                fence_centerline - cutter_radius,
                minimum_frame_thickness - fence_centerline - cutter_radius,
            ]
        )
    minimum_face_web = min(face_webs)
    require(
        minimum_face_web > 0,
        "registered fence height and cutter diameter can break through a door face",
    )

    return {
        "minimum_frame_groove_web": minimum_frame_web,
        "minimum_frame_inter_mortise_web": minimum_frame_inter_web,
        "minimum_muntin_groove_web": minimum_muntin_groove_web,
        "muntin_inter_mortise_web": muntin_inter_mortise_web,
        "rail_inter_mortise_web": rail_inter_mortise_web,
        "minimum_face_web": minimum_face_web,
    }


def _validate_lock_gate(specification, by_id):
    hardware = specification["hardware"]
    note = by_id["J-06"]["Notes"]
    match = re.search(r"(\d+(?:\.\d+)?)\s*in clear wood", note)
    require(match is not None, "J-06 register note omits its clear-wood lock gate")
    require(
        close(float(match.group(1)), hardware["lock_to_joinery_clear_wood_min"]),
        "J-06 register note and hardware clear-wood requirement disagree",
    )
    require("J-06" in hardware["lock_envelope_gate"], "lock gate is not tied to J-06")


def validate(specification=None, rows=None):
    if specification is None or rows is None:
        loaded_specification, loaded_rows = load_inputs()
        if specification is None:
            specification = loaded_specification
        if rows is None:
            rows = loaded_rows
    by_id = _validate_register(specification, rows)
    metrics = _geometry_metrics(specification)
    _validate_lock_gate(specification, by_id)
    return metrics


if __name__ == "__main__":
    results = validate()
    print(
        "PASS: 12 DF 500 joint families match the specification; worst-case "
        f"rail groove web {results['minimum_frame_groove_web']:.4f} in, "
        f"muntin groove web {results['minimum_muntin_groove_web']:.4f} in"
    )
