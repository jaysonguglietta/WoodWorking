#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
OUT="$ROOT/build/reports/page-images"
mkdir -p "$OUT"
if [ -n "${POPPLER_BIN:-}" ] && [ -x "$POPPLER_BIN/pdftoppm" ]; then
  PDFTOPPM="$POPPLER_BIN/pdftoppm"
elif command -v pdftoppm >/dev/null 2>&1; then
  PDFTOPPM=$(command -v pdftoppm)
else
  echo "pdftoppm not found; set POPPLER_BIN" >&2
  exit 1
fi
for pdf in "$ROOT"/release/*.pdf; do
  base=$(basename "$pdf" .pdf)
  mkdir -p "$OUT/$base"
  "$PDFTOPPM" -png -r 90 "$pdf" "$OUT/$base/page" >/dev/null 2>&1
done
echo "PASS: rendered PDF pages to $OUT"

