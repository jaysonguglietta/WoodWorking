#!/usr/bin/env python3
import csv
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
rows=list(csv.DictReader((ROOT/"project/illustration-register.csv").open()))
assert len(rows)>=36
for row in rows:
    svg=ROOT/"illustrations/technical"/f"{row['Slug']}.svg"
    png=ROOT/"illustrations/technical"/f"{row['Slug']}.png"
    assert svg.stat().st_size>500 and png.stat().st_size>1000
    with Image.open(png) as im: assert im.width>=1200 and im.height>=800
cover=ROOT/"illustrations/renders/cover-finished-door.png"
with Image.open(cover) as im: assert im.height>im.width and im.width>=1000
print("PASS: cover and 36 SVG/PNG figure pairs")

