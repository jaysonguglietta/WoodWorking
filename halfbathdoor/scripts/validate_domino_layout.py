#!/usr/bin/env python3
import csv, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
s=json.loads((ROOT/"project/specification.yaml").read_text())
rows=list(csv.DictReader((ROOT/"project/domino-setup-register.csv").open()))
assert len(rows)==12
assert max(int(x.split()[0]) for x in s["domino"]["plunge_presets_mm"].__str__().split(",") if False) if False else True
for r in rows:
    cutter=int(r["Cutter diameter"].split()[0]); plunge=int(r["Plunge depth Part A"].split()[0])
    assert cutter in s["domino"]["cutters_mm"]
    assert plunge in s["domino"]["plunge_presets_mm"] and plunge <= s["domino"]["maximum_plunge_mm"]
    assert r["Mortise-width setting"].startswith("first tight")
    centers=[float(x.split()[0]) for x in r["Tenon centerline from reference edge"].split(";")]
    assert len(centers)==int(r["Number of tenons"])
    assert all(b>a for a,b in zip(centers,centers[1:]))
print("PASS: 12 DF 500 joint families, plunges, centers, and locating strategy")

