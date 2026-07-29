#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = json.loads((ROOT / "project/specification.yaml").read_text())
required = [
    "project",
    "opening",
    "slab",
    "frame",
    "components",
    "panels",
    "groove",
    "domino",
    "adhesive",
    "hardware",
    "trim",
    "finish",
    "field_verify",
]
missing = [x for x in required if x not in spec]
assert not missing, f"missing specification sections: {missing}"
ids = [x["id"] for x in spec["components"]]
assert len(ids) == len(set(ids)), "duplicate component identifier"
for frozen in ["D-101A","D-101B","D-101C","D-101D","D-101E","D-101F","D-101G","D-101H","D-101J","D-101K","D-101L"]:
    assert frozen in ids, f"missing frozen identifier {frozen}"
assert spec["project"]["classification"] == "Historically appropriate reproduction door using modern concealed joinery"
assert spec["project"]["revision"] == "Rev. G"
opening = spec["opening"]
slab = spec["slab"]
assert opening["clear_width"] == 24
assert opening["clear_height"] == 81
assert opening["hinge_side_reveal"] == 0.125
assert opening["lock_side_reveal"] == 0.125
assert opening["head_reveal"] == 0.125
assert opening["bottom_gap"] == 0.375
assert slab["finished_width"] == (
    opening["clear_width"]
    - opening["hinge_side_reveal"]
    - opening["lock_side_reveal"]
)
assert slab["finished_height"] == (
    opening["clear_height"] - opening["head_reveal"] - opening["bottom_gap"]
)
assert slab["finished_width"] == 23.75
assert slab["finished_height"] == 80.5
assert slab["manufacturing_trim_reserve_per_edge"] == 0.0625
assert spec["milling"]["prefit_assembly_width"] == 23.875
assert spec["milling"]["prefit_assembly_height"] == 80.625
assert spec["frame"]["stile_width"] == 4.25
assert spec["frame"]["rail_shoulder_length"] == 15.25
assert spec["frame"]["bottom_opening_each"] == 6.125
assert slab["finished_size_tolerance"]["width_plus"] == 0
assert slab["finished_size_tolerance"]["height_plus"] == 0
construction = spec["frame"]["construction"]
assert abs(
    construction["show_face_preglue_thickness"]
    + construction["core_preglue_thickness"]
    + construction["back_face_preglue_thickness"]
    - construction["glue_blank_thickness"]
) < 1e-9
assert abs(
    construction["show_face_finished_thickness"]
    + construction["core_preglue_thickness"]
    + construction["back_face_finished_thickness"]
    - spec["slab"]["finished_thickness"]
) < 1e-9
assert construction["finished_glue_lines_from_show_face"] == [0.25, 1.125]
assert construction["df_cutter_to_face_glue_line_core_clearance_min"] >= 0.2
assert construction["thickness_slicing_prohibited"] is True
assert "whole-thickness" in construction["face_preparation_rule"].lower()
procurement = spec["trim"]["procurement"]
assert procurement["casing_and_stop"]["quantity_boards"] == 7
assert "4/4" in procurement["casing_and_stop"]["description"]
assert procurement["backband_and_optional_caps"]["quantity_boards"] == 2
assert "6/4" in procurement["backband_and_optional_caps"]["description"]
print(
    "PASS: Rev. G no-resaw specification, 24 x 81 jamb-derived fitted slab, "
    "identifiers, balanced frame, and two-face trim order"
)
