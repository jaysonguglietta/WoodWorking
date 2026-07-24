#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
TMP="${TMPDIR:-/tmp}/dc1916-svg-raster"
mkdir -p "$TMP"
for svg in "$ROOT"/illustrations/technical/*.svg; do
  qlmanage -t -s 1200 -o "$TMP" "$svg" >/dev/null
done
for png in "$TMP"/*.svg.png; do
  base=$(basename "$png" .svg.png)
  cp -p "$png" "$ROOT/illustrations/technical/$base.png"
done
echo "PASS: rasterized dimensioned SVG figures with macOS Quick Look"
