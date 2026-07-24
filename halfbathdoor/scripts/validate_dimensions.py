#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
s = json.loads((ROOT / "project/specification.yaml").read_text())
near = lambda a,b,t=1e-8: abs(a-b) <= t
assert near(2*s["frame"]["stile_width"] + s["frame"]["rail_shoulder_length"], s["slab"]["finished_width"])
assert near(sum(s["frame"]["rail_widths"].values()) + sum(s["frame"]["vertical_openings"].values()), s["slab"]["finished_height"])
assert near((s["frame"]["rail_shoulder_length"] - s["frame"]["muntin_width"])/2, s["frame"]["bottom_opening_each"])
panels = {x["id"]:x for x in s["components"] if "panel" in x["name"].lower()}
assert len(panels) == 5
g=s["groove"]; p=s["panels"]
assert near(panels["D-101H"]["w"], 15 + 2*g["depth"] - p["full_width_clearance_across_grain_total"])
assert near(panels["D-101K"]["w"], 6 + 2*g["depth"] - p["small_width_clearance_across_grain_total"])
opening_map={"D-101H":13.5,"D-101J":14.0,"D-101N":9.5,"D-101K":11.0,"D-101L":11.0}
for pid, opening in opening_map.items():
    assert near(panels[pid]["l"], opening + 2*g["depth"] - p["clearance_parallel_to_grain_total"])
assert near(g["centerline_from_show_face"], s["slab"]["finished_thickness"]/2)
print("PASS: door, opening, groove, and panel dimensions")

