# DC-1916-001 Build Report

## Created

Complete Markdown manuscript; JSON-compatible YAML specification; historical, engineering, and modern-construction standards; procurement and cut lists; labeled-stock plan and five-page cut sheet; RL-02 four-page rough-length cut list; DF 500 register; matched SVG/PNG technical figures and 3D renderings; self-contained HTML; print and screen manuals; visual cut-and-assembly guide; 23-page image-led visual assembly guide with a front-of-guide A-O board-to-part reference; 13-page widescreen project-plans booklet; integrated cabinetmaker guide; custom-moulding manual; template package; moulding drawings; field worksheet; source archive; and SHA-256 checksums.

## Rev. G controlled fitted geometry

- The confirmed installed finished jamb opening is 24 x 81 inches. Required gaps are 1/8 inch at both sides, 1/8 inch at the head, and 3/8 inch at the bottom.
- The finished fitted slab is 23-3/4 x 80-1/2 x 1-3/8 inches. The cured and surfaced pre-fit assembly is 23-7/8 x 80-5/8 inches, carrying 1/16 inch removable stock outside each final perimeter edge.
- LS-05 stile cores are 81 inches and continuous face lamellae are 81-1/8 inches. Finished stile width is 4-1/4 inches from 4-3/8-inch layer lanes. Rail mother billets are 16-1/4 inches; finished rail shoulder length is 15-1/4 inches.
- Rail widths remain unchanged. P-01 is 14-1/4 inches and P-02 is 14-3/4 inches; P-03 and P-04 remain 9-1/2 and 11 inches. The two lower bays are 6-1/8 inches each.
- The lock center remains 40 inches above the slab bottom and is 40-1/2 inches below the finished slab top.
- D-101H is 15-7/8 x 15-1/16 inches finished / 16-3/8 x 15-9/16 inches rough; D-101J is 15-7/8 x 15-9/16 inches finished / 16-3/8 x 16-1/16 inches rough.
- All five floating panels retain the controlled 3/4-inch-long foam spacer system.

## LS-05 no-resaw door-only rough-stock and balanced-lamination revision

- The owner confirmed that STOCK-A through STOCK-L began as raw rough-sawn, unjointed, and unplaned stock. A's current usable length is 72-3/4 inches after the required 6-inch damage removal. STOCK-G is now confirmed S4S at 15/16 x 4-1/2 x 75 inches. Its thickness exceeds the 5/8-inch D-101J rough-panel minimum by 5/16 inch, and its four-stave width/length plan leaves a 6-1/4-inch planning tail. CHK-P-01 still controls physical yield. L's current edge-cleaned width is 6 inches. STOCK-M was later added as reported finished white oak at 3/4 x 8-1/4 x 99 inches. STOCK-N/O are confirmed finished white oak at 1-3/4 x 11 x 74 inches each. Moisture, flatness, defects, and clear yield remain physical shop checks.
- Every A-O board is reserved exclusively for the door, its same-layup coupons, setup pieces, substitutions, and repair stock. STOCK-M carries D-101H, STOCK-A remains intact as panel reserve, and STOCK-N/O remain full as short-member core reserve. The present door-lumber purchase is zero only while all physical yield and coupon gates pass.
- Every frame member uses a balanced 5/16 + 7/8 + 5/16 all-long-grain glue blank, surfaced equally to 1/4 + 7/8 + 1/4 = 1-3/8 inches. Cores and faces are made by jointing, ordinary width ripping where assigned, staged thickness planing, resting, and rechecking; no A-O board is resawn.
- STOCK-I/K are each ripped by width into two continuous 4-3/8-inch stile lanes, one planed to a 7/8-inch core and one to a 5/16-inch face; STOCK-B/C each supply one additional continuous 5/16-inch face. The remaining boards provide the LS-05 panel, short-member, coupon, setup, and reserve map.
- D-101D and D-101F use the controlled staggered core/show/back seam maps. All other listed cores are one piece, and every structural layer is continuous for the member length.
- The separate both-face moulding order is seven S4S 4/4 x nominal 6-inch x 8-foot boards plus two S4S 6/4 x nominal 6-inch x 8-foot boards, approximately 40 dealer board feet. Plinths remain field-controlled and excluded.

## Toolchain and commands

Python 3.12.13, ReportLab, Pillow, pypdf, pdfplumber, and Poppler. Use `make validate`, `make all`, `make preview`, or `make release`.

## Validation

Dimensional identities, five-panel count, panel sizing, groove/mortise clearances, DF 500 plunge limits, component quantities, image links, searchable PDF text, calibration squares, prohibited placeholder strings, and release non-empty checks pass.

## Page counts

- Print manual: 56 pages
- Screen manual: 57 pages
- Printable templates: 14 pages
- Moulding drawings: 12 pages
- Moulding field worksheet: 4 pages
- Quick cut-and-assembly guide: 17 pages
- Image-led visual assembly guide: 23 pages
- Widescreen five-panel door project plans: 13 pages
- Custom moulding shop manual: 19 pages
- Cabinetmaker's builder guide: 64 pages
- Door shopping list: 2 pages
- Labeled-stock cut sheet: 5 pages
- Rough-length cut list: 4 pages
- Total controlled PDF pages: 290

## Visual QA

Status after generation: **PENDING RENDERED-PAGE INSPECTION.** A rebuild invalidates prior visual acceptance. Record the final page-by-page result in `build/reports/visual-qc.md` and add the release result here only after the final PDFs have been rendered and inspected.

## Field-verification items

- record and recheck the owner-confirmed 24 x 81-inch completed jamb at top/middle/bottom and left/center/right before fitting
- both jamb legs plumb in the opening plane and wall-normal plane, head level, both opening diagonals/square, and jamb-face twist checked with winding sticks
- finished-floor elevation and full swing path preserve the 3/8-inch bottom gap
- hung slab proves 1/8-inch hinge-side, lock-side, and head reveals plus the 3/8-inch bottom gap within the specified installed-gap tolerances
- door handing, swing, stop, strike, and any reusable hinge gains
- wall thickness and flatness
- adjacent casing, backband, baseboard, head treatment, and plinth evidence
- all physical mortise-lock, strike, hinge-leaf, and screw dimensions

## Genuine limitations

No original door, blueprint, or room-specific trim schedule was supplied; the design is historically appropriate, not an exact reproduction. Structural choices are conservative cabinetmaking practice, not stamped engineering. The completed-jamb and physical-hardware gates must be closed before irreversible milling. The generated cover is an illustrative visualization; technical drawings and specification control geometry.

## Exact release path

`/Users/jaysonguglietta/SynologyDrive/Drive/woodworking/HalfBath Door and Molding/WoodWorking/halfbathdoor/release`
## Integrated cabinetmaker guide

- Cabinetmaker’s builder guide: 64 pages
- Twenty-seven dimension-controlled isometric, exploded, setup, and orthographic renderings, each issued as SVG and PNG
- Door fabrication, completed-jamb fitting, hardware, custom moulding, finish, and final release are one gated workflow.
