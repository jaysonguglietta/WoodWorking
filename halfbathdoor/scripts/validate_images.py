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

render_register=ROOT/"project"/"cabinetmakers-render-register.csv"
with render_register.open(newline="",encoding="utf-8") as handle:
    render_rows=list(csv.DictReader(handle))
assert len(render_rows)==27
render_slugs=[row["Slug"] for row in render_rows]
assert len(render_slugs)==len(set(render_slugs))
render_dir=ROOT/"cabinetmakers-guide"/"renderings"
clarity_slugs = {
    "03b-door-lamination-map",
    "03c-board-a-o-allocation-map",
    "03d-wide-rail-seam-map",
    "03e-datum-marking-map",
    "04b-panel-glue-map",
    "04c-spacer-placement-map",
    "07b-two-stage-glue-storyboard",
    "08b-post-cure-surfacing-map",
    "09d-prefit-finished-overlay",
}
assert {path.stem for path in render_dir.glob("*.svg")} == (
    set(render_slugs) | {"03b-door-lamination-map"}
)
assert {path.stem for path in render_dir.glob("*.png")} == (
    set(render_slugs) | clarity_slugs
)
for slug in render_slugs:
    svg=render_dir/f"{slug}.svg"
    png=render_dir/f"{slug}.png"
    assert svg.stat().st_size>5000 and png.stat().st_size>10000
    with Image.open(png) as im:
        assert im.width>=1600 and im.height>=1050
        assert im.mode in {"RGB","RGBA"}
        # A technical scene that paints into the final raster rows is clipped
        # even when the guide's scaled page placement makes it look acceptable.
        # Keep a small white safety band below every source rendering.
        bottom_band=im.convert("RGB").crop((0,im.height-4,im.width,im.height))
        assert all(
            min(pixel)>=250 for pixel in bottom_band.get_flattened_data()
        ), f"{slug} reaches the bottom canvas edge"
for slug in clarity_slugs:
    png=render_dir/f"{slug}.png"
    assert png.stat().st_size>10000
    with Image.open(png) as im:
        assert im.width>=1200 and im.height>=800
        assert im.mode in {"RGB","RGBA"}

guide_source=ROOT/"cabinetmakers-guide"/"DC-1916-001_Cabinetmakers_Builder_Guide.md"
guide_builder=ROOT/"scripts"/"build_cabinetmakers_guide.py"
assert guide_source.stat().st_size>1000
assert guide_builder.stat().st_size>1000
print("PASS: cover, 36 technical pairs, 27 cabinetmaker rendering pairs, and 9 clarity maps")
