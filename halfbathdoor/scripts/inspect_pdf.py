#!/usr/bin/env python3
"""Inspect every controlled release PDF for page count and semantic drift."""

import re
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "release"
EXPECTED_PDFS = {
    "DC-1916-001_Illustrated_Shop_Manual_Print.pdf",
    "DC-1916-001_Illustrated_Shop_Manual_Screen.pdf",
    "DC-1916-001_Printable_Templates.pdf",
    "DC-1916-001_Moulding_Drawings.pdf",
    "DC-1916-001_Moulding_Field_Measurement_Worksheet.pdf",
    "DC-1916-001_Quick_Cut_and_Assembly_Guide.pdf",
    "DC-1916-001_Visual_Assembly_Guide.pdf",
    "DC-1916-001_Five_Panel_Door_Project_Plans.pdf",
    "DC-1916-001_Custom_Moulding_Shop_Manual.pdf",
    "DC-1916-001_Cabinetmakers_Builder_Guide.pdf",
    "DC-1916-001_Final_Door_Lumber_List.pdf",
    "DC-1916-001_Door_Shopping_List.pdf",
    "DC-1916-001_Labeled_Stock_Cut_Sheet.pdf",
    "DC-1916-001_Rough_Length_Cut_List.pdf",
}
DIMENSION_24_BY_81 = r"24\s*(?:x|×)\s*81(?:\s*(?:x|×)\s*1[- ]?3/8)?"
ACTIVE_24_BY_81_SLAB_PATTERNS = (
    re.compile(rf"{DIMENSION_24_BY_81}.{{0,18}}\btarget\b"),
    re.compile(
        rf"\btarget(?:\s+of|\s+is|:)?\s*.{{0,18}}{DIMENSION_24_BY_81}"
    ),
    re.compile(
        rf"{DIMENSION_24_BY_81}\s*(?:-?inch(?:es)?)?\s+"
        r"(?:slab|door(?!\s+opening))\b"
    ),
    re.compile(
        r"\b(?:slab|door(?!\s+opening))\s*(?:is|=|:)?\s*"
        rf"{DIMENSION_24_BY_81}"
    ),
    re.compile(
        rf"{DIMENSION_24_BY_81}.{{0,45}}"
        r"\b(?:nominal\s+)?glue[- ]?up\s+slab\b"
    ),
    re.compile(
        rf"{DIMENSION_24_BY_81}.{{0,45}}"
        r"\b(?:design|glue[- ]?up|overall|slab|door)\s+target\b"
    ),
    re.compile(
        rf"\b(?:design|glue[- ]?up|overall|slab|door)\s+target\b"
        rf".{{0,45}}{DIMENSION_24_BY_81}"
    ),
    re.compile(
        rf"\b(?:full|final)[- ]door\s+(?:dry[- ]?fit\s+)?check\b"
        rf".{{0,55}}{DIMENSION_24_BY_81}"
    ),
    re.compile(
        r"\b(?:finished|fitted|nominal)\s+"
        r"(?:slab|door(?!\s+opening)|frame)\b"
        rf".{{0,55}}{DIMENSION_24_BY_81}"
    ),
    re.compile(
        rf"{DIMENSION_24_BY_81}.{{0,35}}"
        r"\b(?:finished|fitted|nominal)\s+"
        r"(?:slab|door(?!\s+opening)|frame)\b"
    ),
)
HISTORICAL_CONTROL_MARKERS = (
    "obsolete",
    "supersed",
    "historical",
    "formerly",
    "former",
    "previous",
    "provisional",
    "initially",
    "replaced",
    "old 24",
    "do not",
    "never use",
)
MISSING_REQUIRED_TERMS: list[str] = []


def normalized(text: str) -> str:
    """Make extracted PDF text stable across line wrapping and dash glyphs."""

    return re.sub(
        r"\s+",
        " ",
        text.lower()
        .replace("\u2010", "-")
        .replace("\u2011", "-")
        .replace("\u2012", "-")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u00d7", "x"),
    ).strip()


def read_pdf(name: str, expected_pages: int | None = None) -> tuple[PdfReader, str]:
    path = RELEASE / name
    reader = PdfReader(str(path))
    raw_text = "\n".join((page.extract_text() or "") for page in reader.pages)
    assert reader.pages and len(raw_text) > 200, f"{name}: insufficient searchable text"
    if expected_pages is not None:
        assert len(reader.pages) == expected_pages, (
            f"{name}: expected {expected_pages} pages, got {len(reader.pages)}"
        )
    return reader, normalized(raw_text)


def require_terms(name: str, text: str, terms: list[str]) -> None:
    for term in terms:
        if normalized(term) not in text:
            MISSING_REQUIRED_TERMS.append(
                f"{name}: missing required term: {term}"
            )


def assert_no_active_24_by_81_slab_control(name: str, text: str) -> None:
    """Reject using the confirmed jamb size as an active slab or glue-up target."""

    for pattern in ACTIVE_24_BY_81_SLAB_PATTERNS:
        for match in pattern.finditer(text):
            if re.search(r"\b(?:jamb|opening)\b", match.group()):
                continue
            local = text[max(0, match.start() - 80) : match.end() + 40]
            if re.search(
                rf"{DIMENSION_24_BY_81}\s+(?:clear\s+)?jamb\b",
                local,
            ):
                continue
            prefix = text[max(0, match.start() - 60) : match.start()]
            if re.search(
                r"\b(?:clear|confirmed|finished|installed)\s+"
                r"(?:finished\s+)?jamb(?:\s+opening)?\b",
                prefix,
            ):
                continue
            if re.search(
                r"\b(?:jamb\s+clear\s+opening|jamb\s+opening|clear\s+jamb)"
                r"\s*:?\s*$",
                prefix,
            ):
                continue
            if re.search(
                r"\bconfirmed\s+(?:jamb\s+)?opening\s*(?:is|:)\s*$",
                prefix,
            ):
                continue
            context = text[max(0, match.start() - 140) : match.end() + 140]
            if any(marker in context for marker in HISTORICAL_CONTROL_MARKERS):
                continue
            raise AssertionError(
                f"{name}: 24 x 81 is the confirmed jamb opening, not an active "
                f"slab/door/glue-up target: {context}"
            )


def assert_no_active_24_by_79_control(name: str, text: str) -> None:
    """Reject the obsolete 24 x 79 control while permitting labeled history."""

    for match in re.finditer(r"24\s*x\s*79", text):
        context = text[max(0, match.start() - 140) : match.end() + 140]
        if any(marker in context for marker in HISTORICAL_CONTROL_MARKERS):
            continue
        raise AssertionError(f"{name}: active stale 24 x 79 control: {context}")


pdf_paths = sorted(RELEASE.glob("*.pdf"))
assert {path.name for path in pdf_paths} == EXPECTED_PDFS

report = []
all_text: dict[str, str] = {}
for path in pdf_paths:
    reader, text = read_pdf(path.name)
    all_text[path.name] = text
    assert not re.search(
        r"\b(todo|tbd|lorem ipsum|insert image|placeholder)\b", text, re.I
    ), f"{path.name}: placeholder text remains"
    assert not re.search(
        r"published\s+open\s*(?:or|/)\s*assembly\s*time", text, re.I
    ), f"{path.name}: obsolete adhesive timing basis"
    assert "tenons shortened and edge-sanded" not in text, (
        f"{path.name}: obsolete rehearsal-tenon instruction"
    )
    assert_no_active_24_by_79_control(path.name, text)
    assert_no_active_24_by_81_slab_control(path.name, text)
    for stale in [
        "LS-01 conditionally assigns",
        "STOCK-I is conditional for D-101A/B",
        "STOCK-K is conditional for D-101C/M/D/E/G",
        "two 4-9/16-inch blanks",
    ]:
        assert normalized(stale) not in text, f"{path.name}: stale instruction: {stale}"
    report.append(
        f"- {path.name}: {len(reader.pages)} pages; searchable text and "
        "global prohibited-string checks PASS"
    )


print_manual, _ = read_pdf("DC-1916-001_Illustrated_Shop_Manual_Print.pdf")
screen_manual, _ = read_pdf("DC-1916-001_Illustrated_Shop_Manual_Screen.pdf")
assert 45 <= len(print_manual.pages) <= 70
assert 45 <= len(screen_manual.pages) <= 70
for manual_name in (
    "DC-1916-001_Illustrated_Shop_Manual_Print.pdf",
    "DC-1916-001_Illustrated_Shop_Manual_Screen.pdf",
):
    require_terms(
        manual_name,
        all_text[manual_name],
        [
            "Rev. G",
            "LS-05",
            "24 x 81",
            "23-7/8 x 80-5/8",
            "23-3/4 x 80-1/2 x 1-3/8",
            "3/8-inch bottom gap",
        ],
    )
read_pdf("DC-1916-001_Printable_Templates.pdf", 14)
read_pdf("DC-1916-001_Moulding_Drawings.pdf", 12)

moulding_name = "DC-1916-001_Custom_Moulding_Shop_Manual.pdf"
_, moulding_text = read_pdf(moulding_name, 19)
require_terms(
    moulding_name,
    moulding_text,
    [
        "head-backband outside width",
        "plinths first",
        "stops last",
        "winding sticks",
        "sound jamb",
        "procurement | two-face order",
        "S4S 4/4",
        "S4S 6/4",
        "40 dealer BF",
        "no plinth stock",
        "4 side casings",
        "2 head casings",
    ],
)

worksheet_name = "DC-1916-001_Moulding_Field_Measurement_Worksheet.pdf"
_, worksheet_text = read_pdf(worksheet_name, 4)
require_terms(
    worksheet_name,
    worksheet_text,
    ["face a", "face b", "omit", "h-l", "h-r", "m-202c"],
)

quick_name = "DC-1916-001_Quick_Cut_and_Assembly_Guide.pdf"
_, quick_text = read_pdf(quick_name, 17)
require_terms(
    quick_name,
    quick_text,
    [
        "Rev. G",
        "LS-05",
        "supersedes LS-04",
        "24 x 81",
        "23-7/8 x 80-5/8",
        "23-3/4 x 80-1/2",
        "3/8 bottom gap",
        "all A-O stock stays with the door",
        "N/O",
        "no door-lumber purchase",
        "5/16 + 7/8 + 5/16",
        "1/4 + 7/8 + 1/4",
        "no-resaw",
        "CHK-LAM-01",
        "CHK-SEAM-01",
        "0.200",
        "0.220",
        "published open time",
        "clamp complete",
        "full-length factory",
        "3/4-inch-long foam spacers",
        "Record STOCK-G separately as",
        "S4S: 15/16 x 4-1/2 x 75",
        "CHK-P-01 proves all four clear billet zones",
    ],
)

visual_name = "DC-1916-001_Visual_Assembly_Guide.pdf"
_, visual_text = read_pdf(visual_name, 23)
require_terms(
    visual_name,
    visual_text,
    [
        "Rev. G",
        "NO RESAWING",
        "23-3/4 x 80-1/2 x 1-3/8",
        "Break down only four boards",
        "5/16",
        "7/8",
        "1/4 wide x 1/2 deep",
        "10 x 50 mm",
        "6 x 40 mm",
        "20 foam spacers",
        "Diagonals within 1/16",
        "23-7/8 x 80-5/8",
        "BOARD A",
        "BOARD M",
        "BOARD N",
        "BOARD O",
        "BOARD L",
        "BOARD = YOUR TAPE LABEL",
        "PART / PANEL = FINISHED DOOR PIECE",
        "Board-to-part visual reference",
        "VISUAL REFERENCE ONLY",
        "PANEL H | BOARD M",
        "PART A | BOARDS B + K",
        "PART B | BOARDS C + I",
        "PART F | CORES J + L",
        "L | BOARD D",
        "SIZE ORDER: THICK x WIDE x LONG",
        '5/16" THICK x 4-3/8" WIDE x 81-1/8" LONG',
        "Controlled-reserve release order",
        "SURVEY EVERY FULL BOARD A-O",
        "PROVE FULL-LENGTH BOARD B + BOARD C",
        "PROVE FULL-LENGTH BOARD I + BOARD K",
        "Mill one board at a time",
        "CRITICAL DRESSED-YIELD RECORD",
        "machine's safe length/thickness",
        "RELEASE AFTER LONG GATES",
        "SURVEY + LONG GATES",
        "KEEP FULL",
        "MAP KNOTS",
        "LAYOUT FIRST",
        '1-5/16 x 6 x 80" CURRENT',
        '1 x 5-11/16 x 72-3/4" CURRENT',
        "Six inches are already removed",
        '3/4 x 8-1/4 x 99" FINISHED',
        '1-3/4 x 11 x 74" FINISHED WHITE OAK',
        'S4S: 15/16 x 4-1/2 x 75"',
        "SIZE PASSES",
        "6-1/4 planning tail",
        "48-7/16",
        'Prove one clear 6-1/2" width envelope',
    ],
)

project_plans_name = "DC-1916-001_Five_Panel_Door_Project_Plans.pdf"
_, project_plans_text = read_pdf(project_plans_name, 13)
require_terms(
    project_plans_name,
    project_plans_text,
    [
        "Five-Panel White Oak Door",
        "Project Plans",
        "Rev. G",
        "LS-05",
        "24 x 81",
        "23-3/4 x 80-1/2 x 1-3/8",
        "NO RESAWING",
        "D-101A",
        "D-101L",
        "1/4 x 1/2",
        "3/4-inch-long foam",
        "3/8-inch bottom gap",
        "G: S4S 15/16 x 4-1/2 x 75",
        "15/16 thickness/width/length fit PANEL J",
    ],
)

cabinet_name = "DC-1916-001_Cabinetmakers_Builder_Guide.pdf"
_, cabinet_text = read_pdf(cabinet_name, 64)
require_terms(
    cabinet_name,
    cabinet_text,
    [
        "Rev. G",
        "LS-05",
        "supersedes LS-04",
        "24 x 81",
        "23-7/8 x 80-5/8",
        "23-3/4 x 80-1/2",
        "3/8 at bottom",
        "No purchase currently released",
        "A now 72-3/4 in",
        "5/16 + 7/8 + 5/16",
        "1/4 + 7/8 + 1/4",
        "D-101D core/show/back seams",
        "D-101F seams",
        "19.500",
        "38.250",
        "54.750",
        "69.750",
        "7.125",
        "8.125",
        "6-1/8",
        "9-1/8",
        "DF 500",
        "0.200",
        "0.220",
        "published open time",
        "full-length factory",
        "Casing + stop",
        "7 boards",
        "Backband",
        "2 boards",
        "40 dealer BF total",
        "no plinth stock",
        "N/O",
        "1-3/4 x 11 x 74",
        "G confirmed S4S",
        "15/16 x 4-1/2 x 75",
        "G thickness/width/length fit four J staves",
        "CHK-P-01 still controls",
    ],
)

shopping_name = "DC-1916-001_Door_Shopping_List.pdf"
_, shopping_text = read_pdf(shopping_name, 2)
require_terms(
    shopping_name,
    shopping_text,
    [
        "door shopping list",
        "Rev. G",
        "LS-05",
        "supersedes LS-04",
        "24 x 81",
        "23-7/8 x 80-5/8",
        "23-3/4 x 80-1/2 x 1-3/8",
        "3/8",
        "0 BF",
        "71.52",
        "G is confirmed S4S at 15/16 x 4-1/2 x 75 inches",
        "thickness/width/length fit D-101J",
        "M carries D-101H",
        "A remains intact",
        "all STOCK-A through STOCK-O is reserved for the door",
        "STOCK-N/O remain full-length",
        "32 oz minimum",
        "order 40",
        "dado stack",
        "rough-sawn",
        "CHK-RS-01",
        "CHK-ST-01",
        "CHK-ST-02",
        "CHK-SM-01",
        "CHK-P-01",
        "CHK-LAM-01",
        "CHK-SEAM-01",
    ],
)
for stale in [
    "26 BF",
    "8 BF",
    "heavy 6/4",
    "otherwise use 8/4",
    "no on-hand frame production credit",
]:
    assert normalized(stale) not in shopping_text, (
        f"{shopping_name}: obsolete purchase instruction remains: {stale}"
    )
assert "s4s 4/4" not in shopping_text and "s4s 6/4" not in shopping_text, (
    f"{shopping_name}: door-only list contains moulding purchase rows"
)

stock_name = "DC-1916-001_Labeled_Stock_Cut_Sheet.pdf"
_, stock_text = read_pdf(stock_name, 5)
require_terms(
    stock_name,
    stock_text,
    [
        "door-only labeled lumber inventory",
        "Rev. G",
        "LS-05",
        "supersedes LS-04",
        "24 x 81",
        "23-7/8 x 80-5/8",
        "23-3/4 x 80-1/2",
        "3/8 bottom gap",
        "Rough-sawn",
        "balanced laminated frame",
        "5/16",
        "7/8",
        "no-resaw",
        "no door lumber purchase released",
        "STOCK-B",
        "STOCK-C",
        "STOCK-I",
        "STOCK-K",
        "CHK-LAM-01",
        "CHK-SEAM-01",
        "BUY-MOULD-4Q",
        "7 boards",
        "BUY-MOULD-6Q",
        "2 boards",
        "AFTER EDGE CLEANUP",
        "6-1/2-inch F core stave",
        "M = 3/4 x 8-1/4 x 99 inches finished white oak",
        "N/O are each confirmed finished white oak at 1-3/4 x 11 x 74 inches",
        "STOCK-N or STOCK-O short-core remap",
        "keep damaged A intact at 72-3/4 inches",
        "49-15/16-inch controlled tail",
        "CURRENT S4S: 15/16 X 4 1/2 X 75",
        "CONDITIONAL - CHK-P-01 PANEL MAP",
    ],
)
for stale in [
    "zero on-hand frame credit",
    "BUY-FRAME-01",
    "26 BF",
    "one-piece bottom rail",
]:
    assert normalized(stale) not in stock_text, (
        f"{stock_name}: obsolete LS-02 instruction remains: {stale}"
    )

rough_name = "DC-1916-001_Rough_Length_Cut_List.pdf"
_, rough_text = read_pdf(rough_name, 4)
require_terms(
    rough_name,
    rough_text,
    [
        "rough-length first-crosscut list",
        "Rev. G",
        "LS-05",
        "RL-02",
        "STOCK-A through STOCK-O",
        "3 x 16-1/16",
        "4 x 12-13/16",
        "4 x 16-9/16",
        "3 x 11-5/16",
        "NO CROSSCUT - KEEP FULL 85 INCHES",
        "NO CROSSCUT - KEEP FULL 83-1/8 INCHES",
        "NO CROSSCUT - KEEP FULL 84-3/4 INCHES",
        "NO CROSSCUT - KEEP FULL 82-1/2 INCHES",
        "4-3/8-inch lanes",
        "2-inch reserve is total per board",
        "3/8-inch bottom gap",
        "M = 3/4 x 8-1/4 x 99 inches finished white oak",
        "N/O are each confirmed finished white oak at 1-3/4 x 11 x 74 inches",
        "48-7/16",
        "full-pattern paper remainder 15-11/16",
        "L 1-5/16 x 6 x 80",
        "original 7-inch width is obsolete",
        "only no-purchase source for the 6-1/2-inch F core stave",
        "G NOW S4S 15/16 X 4-1/2 X 75",
        "G THICKNESS/WIDTH/LENGTH FIT D-101J",
        "THICKNESS/WIDTH/LENGTH PASS",
        "6-1/4",
    ],
)

assert not MISSING_REQUIRED_TERMS, "\n".join(MISSING_REQUIRED_TERMS)

(ROOT / "build/reports/pdf-inspection.md").write_text(
    "# PDF Inspection\n\n"
    "Automated page-count, searchable-text, controlled-term, and semantic-drift "
    "inspection after the final build.\n\n"
    + "\n".join(report)
    + "\n",
    encoding="utf-8",
)
print("PASS: PDF count, page targets, controlled terms, and semantic-drift checks")
