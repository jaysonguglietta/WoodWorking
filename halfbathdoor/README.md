# Building a Historically Appropriate Five-Panel Door

Project DC-1916-001 is the reproducible source for a complete illustrated shop manual covering one 24 x 79 x 1-3/8 inch quarter-sawn white-oak interior door with concealed Festool Domino DF 500 joinery. The door is a historically appropriate reproduction using modern concealed joinery; it is not represented as a museum-exact reconstruction.

The installed jamb is complete and outside the fabrication scope. Hardware and house-dependent dimensions remain field-verification items.

## Quick start

The build uses Python 3, ReportLab, Pillow, pypdf, pdfplumber, and Poppler. Codex Desktop's bundled artifact runtime already contains these dependencies.

On another Mac:

```sh
brew install python poppler make
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements.txt
make all
```

Useful commands:

```sh
make validate   # specification, dimensions, assets, links, and tests
make all        # regenerate source-derived assets and all editions
make preview    # render PDFs to page images
make release    # validate, build, inspect, package, and checksum
make clean      # remove reproducible build outputs
```

The authoritative specification is `project/specification.yaml`. Release artifacts are under `release/`.

For a bench-friendly version focused only on lumber preparation and assembly, use
`release/DC-1916-001_Quick_Cut_and_Assembly_Guide.pdf`. Its six dimension-controlled
assembly illustrations are generated from `scripts/generate_quick_assembly_diagrams.py`.

## Field gate

Before final milling, complete the jamb and hardware worksheets. The fixed 24 x 79 inch slab is the design target, not permission to skip measuring the completed opening. Preserve a small fitting allowance until the opening, floor, handing, hinge leaves, and mortise lock are physically verified.

## Source notes

Historical design decisions are documented in `project/historical-appearance-standard.md`. Manufacturer limits for the DF 500 and the provenance for period precedents are recorded in `project/source-register.csv`.
