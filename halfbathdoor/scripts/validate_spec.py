#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = json.loads((ROOT / "project/specification.yaml").read_text())
required = ["project", "slab", "frame", "components", "panels", "groove", "domino", "hardware", "trim", "finish", "field_verify"]
missing = [x for x in required if x not in spec]
assert not missing, f"missing specification sections: {missing}"
ids = [x["id"] for x in spec["components"]]
assert len(ids) == len(set(ids)), "duplicate component identifier"
for frozen in ["D-101A","D-101B","D-101C","D-101D","D-101E","D-101F","D-101G","D-101H","D-101J","D-101K","D-101L"]:
    assert frozen in ids, f"missing frozen identifier {frozen}"
assert spec["project"]["classification"] == "Historically appropriate reproduction door using modern concealed joinery"
print("PASS: authoritative specification structure and identifiers")

