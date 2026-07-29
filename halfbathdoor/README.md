# Building a Historically Appropriate Five-Panel Door

Project DC-1916-001 is the reproducible source for a complete illustrated shop manual covering one 23-3/4 x 80-1/2 x 1-3/8 inch fitted quarter-sawn white-oak interior door with concealed Festool Domino DF 500 joinery. It is designed for the owner-confirmed 24 x 81 inch finished jamb opening, with 1/8-inch side and head reveals and a 3/8-inch bottom gap. The door is a historically appropriate reproduction using modern concealed joinery; it is not represented as a museum-exact reconstruction.

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
make moulding-guide  # regenerate only the moulding guide package
make cabinetmakers-guide  # regenerate the unified door-and-moulding builder guide
make rough-length-cut-list  # regenerate the board-by-board first-crosscut guide
make clean      # remove reproducible build outputs
```

The authoritative specification is `project/specification.yaml`. Release artifacts are under `release/`.

For a bench-friendly version focused only on lumber preparation and assembly, use
`release/DC-1916-001_Quick_Cut_and_Assembly_Guide.pdf`. Its eight dimension-controlled
shop diagrams—including a six-step assembly sequence—are generated from
`scripts/generate_quick_assembly_diagrams.py`.

For the user's measured STOCK-A through STOCK-L inventory, use
`release/DC-1916-001_Labeled_Stock_Cut_Sheet.pdf` with
`release/DC-1916-001_Labeled_Stock_Cut_Sheet.csv` and the companion workbook.
Rev. G / LS-05 reserves every A-L board exclusively for the door, its balanced-layup
coupons, setup pieces, substitutions, and repair stock. The frame uses 5/16-inch
show-face + 7/8-inch core + 5/16-inch back-face blanks, surfaced equally to a final
1/4 + 7/8 + 1/4 = 1-3/8-inch section. All layers are made by jointing, ordinary
width ripping where assigned, staged thickness planing, resting, and rechecking;
none of the A-L stock is resawn. STOCK-I and STOCK-K are each ripped lengthwise into
two 4-3/8-inch lanes, one planed to a 7/8-inch stile core and one to a 5/16-inch
stile face. STOCK-B and STOCK-C each provide one additional continuous 5/16-inch
face. The general door-lumber purchase is zero only while the full-length stile,
short-member core, signed face-pool, panel, lamination-coupon, and seam gates pass. Raw rough-sawn
dimensions are envelopes, not proof of jointed, planed, and rested yield.
If a critical long layer fails, purchase a replacement continuous board rather than
splice or narrow a stile.

For the first crosscuts that make the rough stock easier to mill, use
`release/DC-1916-001_Rough_Length_Cut_List.pdf` with its companion Markdown and
CSV. RL-02 gives an explicit decision for every board A-L. B/C/I/K stay full length
through both continuous-stile gates; J/L remain uncut until the CM-05 core map is
signed; and every panel, FP-05 face-pool, knot-mapped reserve, coupon, and repair
billet remains governed by the full-board defect map and its released nesting row.

For the completed-jamb millwork, use
`release/DC-1916-001_Custom_Moulding_Shop_Manual.pdf` with the companion
`release/DC-1916-001_Moulding_Drawings.pdf` and
`release/DC-1916-001_Moulding_Field_Measurement_Worksheet.pdf`. The manual covers
field measurement, one- versus two-face quantities, conditional mitered and square-head
lengths, stock milling, stops, casing, backband, optional cap/plinth transitions,
fastening, finishing, and final functional QC. Its sixteen vector-first diagrams are
generated from `scripts/generate_moulding_diagrams.py`. For both faces, purchase seven
S4S quarter-sawn white-oak 4/4 x nominal 6-inch x 8-foot boards for casing and one
stop set, plus two S4S 6/4 x nominal 6-inch x 8-foot boards for the 1-inch finished
backband and optional evidence-supported caps. This is about 40 dealer board feet.
The intended thickness notation is 4/4, not 4 x 4; plinth stock is excluded until
field evidence supports it.

For the complete cabinetmaker workflow, use
`release/DC-1916-001_Cabinetmakers_Builder_Guide.pdf`. This Rev. G guide combines
door construction, fitting, hardware, stop, casing, backband, finishing, and final
release in one production sequence. Dimension-controlled isometric,
exploded, setup, and orthographic renderings are generated from
`scripts/generate_cabinetmakers_3d.py`; written
dimensions and the authoritative specification control fabrication. Their exact
source-archive manifest is `project/cabinetmakers-render-register.csv`.

## Field gate

The finished jamb opening has been confirmed as consistently 24 x 81 inches. Recheck its square, plumb, level, twist, floor datum, and full swing path before final fitting. Build the cured and surfaced pre-fit assembly to 23-7/8 x 80-5/8 inches, scribe the 23-3/4 x 80-1/2 final rectangle from the final-top and hinge-edge datums, and trim only after the hinge leaves, handing, stop, strike, and mortise lock are physically verified. The fitted slab may not exceed 23-3/4 x 80-1/2 inches; the installed reveals and 3/8-inch bottom gap govern acceptance.

## Source notes

Historical design decisions are documented in `project/historical-appearance-standard.md`. Manufacturer limits for the DF 500 and the provenance for period precedents are recorded in `project/source-register.csv`.
