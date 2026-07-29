"""Cross-artifact regression checks for the Rev. G production release.

These tests intentionally inspect both authoritative data and the human-facing
source that feeds the PDFs.  They catch wording regressions that ordinary
geometry tests cannot, and generate only the three relevant SVGs in temporary
directories so the test run never dirties release assets.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import re
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

COMBINED_GUIDE = ROOT / "cabinetmakers-guide/DC-1916-001_Cabinetmakers_Builder_Guide.md"
QUICK_GUIDE = ROOT / "quick-guide/DC-1916-001_Quick_Cut_and_Assembly_Guide.md"
MOULDING_GUIDE = ROOT / "moulding-guide/DC-1916-001_Custom_Moulding_Shop_Manual.md"
SPECIFICATION = ROOT / "project/specification.yaml"
PROJECT_BUILDER = ROOT / "scripts/build_project.py"
COMBINED_BUILDER = ROOT / "scripts/build_cabinetmakers_guide.py"
MOULDING_BUILDER = ROOT / "scripts/build_moulding_guide.py"
QUICK_DIAGRAM_GENERATOR = ROOT / "scripts/generate_quick_assembly_diagrams.py"
CABINET_RENDER_GENERATOR = ROOT / "scripts/generate_cabinetmakers_3d.py"

DIMENSION_24_BY_81 = r"24\s*(?:x|×)\s*81(?:\s*(?:x|×)\s*1[- ]?3/8)?"
ACTIVE_24_BY_81_SLAB_PATTERNS = (
    re.compile(
        rf"{DIMENSION_24_BY_81}.{{0,18}}\btarget\b"
    ),
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


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _plain(text: str) -> str:
    """Normalize prose without erasing dimension operators."""

    replacements = {
        "\u00a0": " ",
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\u2265": ">=",
        "\u2264": "<=",
        "_": " ",
        "`": "",
        "*": "",
    }
    normalized = text
    for old, new in replacements.items():
        normalized = normalized.replace(old, new)
    return re.sub(r"\s+", " ", normalized).strip().lower()


def _nonempty_lines(text: str) -> list[str]:
    return [_plain(line) for line in text.splitlines() if line.strip()]


def _has_gate(
    text: str,
    *,
    subjects: tuple[str, ...],
    relations: tuple[str, ...],
    value_pattern: str,
) -> bool:
    """Return true when one source line states one complete numeric gate."""

    subject_terms = tuple(_plain(term) for term in subjects)
    relation_terms = tuple(_plain(term) for term in relations)
    value = re.compile(value_pattern)
    for line in _nonempty_lines(text):
        if (
            any(term in line for term in subject_terms)
            and any(term in line for term in relation_terms)
            and value.search(line)
        ):
            return True
    return False


def _production_text_paths() -> list[Path]:
    paths = [
        COMBINED_GUIDE,
        QUICK_GUIDE,
        MOULDING_GUIDE,
        COMBINED_BUILDER,
        ROOT / "scripts/build_quick_guide.py",
        MOULDING_BUILDER,
        PROJECT_BUILDER,
        QUICK_DIAGRAM_GENERATOR,
        CABINET_RENDER_GENERATOR,
    ]
    paths.extend(sorted((ROOT / "project").glob("*.md")))
    paths.extend(sorted((ROOT / "project").glob("*.csv")))
    paths.append(SPECIFICATION)
    return paths


def _active_24_by_81_slab_controls(text: str) -> list[str]:
    """Return active lines that incorrectly use the jamb size as a slab control."""

    violations: list[str] = []
    for line in _nonempty_lines(text):
        if any(marker in line for marker in HISTORICAL_CONTROL_MARKERS):
            continue
        for pattern in ACTIVE_24_BY_81_SLAB_PATTERNS:
            match = pattern.search(line)
            if match is None:
                continue
            if re.search(r"\b(?:jamb|opening)\b", match.group()):
                continue
            prefix = line[max(0, match.start() - 60) : match.start()]
            if re.search(
                r"\b(?:clear|confirmed|finished|installed)\s+"
                r"(?:finished\s+)?jamb(?:\s+opening)?\b",
                prefix,
            ):
                continue
            violations.append(line)
            break
    return violations


def _load_generator(module_name: str, path: Path):
    """Load a project generator without invoking its command-line entrypoint."""

    scripts = str(ROOT / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to import generator: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _svg_text_nodes(svg_path: Path) -> list[tuple[str, float | None, float | None]]:
    root = ET.fromstring(_read(svg_path))
    nodes: list[tuple[str, float | None, float | None]] = []
    for element in root.iter():
        if not element.tag.endswith("text"):
            continue
        value = "".join(element.itertext()).strip()
        x = element.attrib.get("x")
        y = element.attrib.get("y")
        nodes.append(
            (
                value,
                float(x) if x is not None else None,
                float(y) if y is not None else None,
            )
        )
    return nodes


class ReleaseConsistencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = json.loads(_read(SPECIFICATION))
        cls.combined = _read(COMBINED_GUIDE)
        cls.quick = _read(QUICK_GUIDE)
        cls.moulding = _read(MOULDING_GUIDE)
        cls.project_builder = _read(PROJECT_BUILDER)

    def test_24_by_81_semantic_guard_preserves_jamb_and_history_context(self):
        accepted = [
            (
                "The confirmed installed jamb opening is 24 x 81. "
                "The fitted slab is 23-3/4 x 80-1/2."
            ),
            "The old 24 x 81 slab instruction is obsolete under Rev. G.",
            (
                "Rev. G supersedes the former 24 x 81 glue-up target with "
                "the jamb-derived fitted slab."
            ),
            "The clear jamb remains fixed at 24 x 81 while the fitted slab swings.",
        ]
        rejected = [
            "The finished slab is 24 x 81.",
            "Confirm 24 x 81 as the glue-up target.",
            "Repeat the full-door check at 24 x 81.",
        ]
        for statement in accepted:
            with self.subTest(accepted=statement):
                self.assertEqual(_active_24_by_81_slab_controls(statement), [])
        for statement in rejected:
            with self.subTest(rejected=statement):
                self.assertNotEqual(_active_24_by_81_slab_controls(statement), [])

    def test_rev_g_jamb_prefit_and_fitted_slab_controls_are_consistent(self):
        self.assertEqual(self.spec["project"]["revision"], "Rev. G")

        opening = self.spec["opening"]
        self.assertAlmostEqual(opening["clear_width"], 24.0)
        self.assertAlmostEqual(opening["clear_height"], 81.0)
        self.assertAlmostEqual(opening["hinge_side_reveal"], 0.125)
        self.assertAlmostEqual(opening["lock_side_reveal"], 0.125)
        self.assertAlmostEqual(opening["head_reveal"], 0.125)
        self.assertAlmostEqual(opening["bottom_gap"], 0.375)

        slab = self.spec["slab"]
        self.assertAlmostEqual(slab["finished_width"], 23.75)
        self.assertAlmostEqual(slab["finished_height"], 80.5)
        self.assertAlmostEqual(slab["finished_thickness"], 1.375)
        self.assertAlmostEqual(
            slab["finished_width"],
            opening["clear_width"]
            - opening["hinge_side_reveal"]
            - opening["lock_side_reveal"],
        )
        self.assertAlmostEqual(
            slab["finished_height"],
            opening["clear_height"]
            - opening["head_reveal"]
            - opening["bottom_gap"],
        )
        self.assertAlmostEqual(slab["manufacturing_trim_reserve_per_edge"], 0.0625)
        self.assertAlmostEqual(slab["finished_size_tolerance"]["width_plus"], 0.0)
        self.assertAlmostEqual(slab["finished_size_tolerance"]["height_plus"], 0.0)

        milling = self.spec["milling"]
        self.assertAlmostEqual(milling["prefit_assembly_width"], 23.875)
        self.assertAlmostEqual(milling["prefit_assembly_height"], 80.625)
        self.assertAlmostEqual(
            milling["prefit_assembly_width"] - slab["finished_width"],
            2 * slab["manufacturing_trim_reserve_per_edge"],
        )
        self.assertAlmostEqual(
            milling["prefit_assembly_height"] - slab["finished_height"],
            2 * slab["manufacturing_trim_reserve_per_edge"],
        )

        for label, text in [
            ("combined guide", self.combined),
            ("quick guide", self.quick),
            ("project generator", self.project_builder),
            ("combined-guide builder", _read(COMBINED_BUILDER)),
            ("quick-guide builder", _read(ROOT / "scripts/build_quick_guide.py")),
        ]:
            with self.subTest(source=label):
                normalized = _plain(text)
                self.assertIn("ls-05", normalized)
                self.assertIn("24 x 81", normalized)
                self.assertIn("23-7/8 x 80-5/8", normalized)
                self.assertIn("23-3/4 x 80-1/2", normalized)
                self.assertRegex(normalized, r"1/8.{0,45}(?:side|both sides)")
                self.assertRegex(normalized, r"3/8.{0,35}bottom")
                self.assertNotIn("24 x 79", normalized)
                self.assertEqual(
                    _active_24_by_81_slab_controls(text),
                    [],
                    f"{label} assigns the 24 x 81 jamb size to the slab",
                )

        for label, text in [
            ("combined guide", self.combined),
            ("quick guide", self.quick),
            ("project generator", self.project_builder),
            ("quick-guide builder", _read(ROOT / "scripts/build_quick_guide.py")),
        ]:
            with self.subTest(revision_source=label):
                self.assertIn("rev. g", _plain(text))
        self.assertIn(
            'REVISION = SPEC["project"]["revision"]',
            _read(COMBINED_BUILDER),
            "combined-guide builder must inherit the authoritative spec revision",
        )

        stale_patterns = [
            re.compile(r"24\s*x\s*79"),
            re.compile(r"\b79[- ]inch\s+(?:slab|stack|stiles?|target)\b"),
            re.compile(r"\b(?:height|stack)\s+(?:is\s+|totals?\s+)?79\b"),
            re.compile(r"\bto\s+79\s+inches\b"),
        ]
        allowed_history = HISTORICAL_CONTROL_MARKERS + (
            "rev. c",
            "previously cut",
        )
        for path in _production_text_paths():
            violations = _active_24_by_81_slab_controls(_read(path))
            self.assertEqual(
                violations,
                [],
                f"{path.relative_to(ROOT)} assigns the 24 x 81 jamb size "
                f"to an active slab/door/glue-up control: {violations}",
            )
            for line_number, line in enumerate(_nonempty_lines(_read(path)), 1):
                if any(pattern.search(line) for pattern in stale_patterns):
                    self.assertTrue(
                        any(marker in line for marker in allowed_history),
                        f"{path.relative_to(ROOT)}:{line_number} retains an active 79-inch control: {line}",
                    )

        components = {
            item["id"]: item for item in self.spec["components"]
        }
        self.assertAlmostEqual(components["D-101A"]["l"], 80.5)
        self.assertAlmostEqual(components["D-101B"]["l"], 80.5)
        self.assertAlmostEqual(components["D-101H"]["l"], 15.0625)
        self.assertAlmostEqual(components["D-101J"]["l"], 15.5625)
        self.assertAlmostEqual(components["D-101N"]["l"], 10.3125)
        self.assertAlmostEqual(components["D-101K"]["w"], 6.875)
        self.assertAlmostEqual(components["D-101K"]["l"], 11.8125)
        self.assertAlmostEqual(components["D-101L"]["w"], 6.875)
        self.assertAlmostEqual(components["D-101L"]["l"], 11.8125)
        self.assertAlmostEqual(
            self.spec["slab"]["finished_height"]
            - self.spec["hardware"]["nominal_lock_center_above_slab_bottom"],
            40.5,
        )

    def test_rev_g_stack_and_domino_stations_are_authoritative(self):
        frame = self.spec["frame"]
        self.assertAlmostEqual(frame["stile_width"], 4.25)
        self.assertAlmostEqual(frame["rail_shoulder_length"], 15.25)
        self.assertAlmostEqual(frame["muntin_width"], 3.0)
        self.assertEqual(
            frame["vertical_openings"],
            {
                "P-01 upper": 14.25,
                "P-02 center": 14.75,
                "P-03 lower-center": 9.5,
                "P-04 bottom": 11.0,
            },
        )
        self.assertAlmostEqual(frame["bottom_opening_each"], 6.125)

        domino = self.spec["domino"]
        self.assertEqual(
            domino["stile_centers_from_slab_top_in"],
            {
                "D-101C": [1.25, 2.75],
                "D-101M": [19.5, 21.0],
                "D-101D": [38.25, 40.5, 42.75],
                "D-101E": [54.75, 56.25],
                "D-101F": [69.75, 72.5, 76.0, 79.25],
            },
        )
        self.assertEqual(
            domino["muntin_centers_in"],
            {
                "D-101G from left reference edge": [1.0, 2.0],
                "D-101E and D-101F from hinge-side shoulder": [7.125, 8.125],
            },
        )
        self.assertEqual(
            self.spec["groove"]["muntin_footprint_from_hinge_side_rail_shoulder"],
            [6.125, 9.125],
        )
        expected_segments = [[0.0, 6.125], [9.125, 15.25]]
        for edge in ("D-101E bottom", "D-101F top"):
            with self.subTest(edge=edge):
                self.assertEqual(
                    self.spec["groove"]["segmented_rail_edges"][edge],
                    expected_segments,
                )

    def test_rev_g_no_resaw_lamination_and_ls05_are_cross_artifact_controls(self):
        construction = self.spec["frame"]["construction"]
        self.assertAlmostEqual(
            construction["show_face_preglue_thickness"]
            + construction["core_preglue_thickness"]
            + construction["back_face_preglue_thickness"],
            1.5,
        )
        self.assertAlmostEqual(
            construction["show_face_finished_thickness"]
            + construction["core_preglue_thickness"]
            + construction["back_face_finished_thickness"],
            1.375,
        )
        for label, text in [
            ("combined guide", self.combined),
            ("quick guide", self.quick),
            ("project generator", self.project_builder),
            ("combined-guide builder", _read(COMBINED_BUILDER)),
            ("quick-guide builder", _read(ROOT / "scripts/build_quick_guide.py")),
        ]:
            normalized = _plain(text)
            with self.subTest(source=label):
                self.assertIn("ls-05", normalized)
                self.assertRegex(normalized, r"5/16.{0,20}7/8.{0,20}5/16")
                self.assertRegex(normalized, r"1/4.{0,20}7/8.{0,20}1/4")
                self.assertRegex(normalized, r"(?:no[- ]resaw|through[- ]thickness)")

    def test_two_face_moulding_order_is_separate_and_complete(self):
        procurement = self.spec["trim"]["procurement"]
        self.assertEqual(procurement["casing_and_stop"]["quantity_boards"], 7)
        self.assertIn("4/4", procurement["casing_and_stop"]["description"])
        self.assertEqual(
            procurement["backband_and_optional_caps"]["quantity_boards"],
            2,
        )
        self.assertIn(
            "6/4",
            procurement["backband_and_optional_caps"]["description"],
        )
        self.assertAlmostEqual(procurement["dealer_volume_board_feet"], 40.0)
        self.assertIn("excluded", procurement["plinths"].lower())

        for label, text in [
            ("combined guide", self.combined),
            ("moulding guide", self.moulding),
            ("project generator", self.project_builder),
            ("moulding builder", _read(MOULDING_BUILDER)),
        ]:
            normalized = _plain(text)
            with self.subTest(source=label):
                for required in ["s4s", "4/4", "6/4", "40 dealer", "plinth"]:
                    self.assertIn(required, normalized)
                self.assertRegex(
                    normalized,
                    r"\b(?:7|seven)\b.{0,80}\bs4s\b",
                )
                self.assertRegex(
                    normalized,
                    r"\b(?:2|two)\b.{0,80}\bs4s\b",
                )
                self.assertRegex(
                    normalized,
                    r"\b(?:no|exclude[ds]?|not included)\b.{0,80}\bplinth",
                )

    def assert_distinct_web_gates(self, text: str, label: str):
        self.assertTrue(
            _has_gate(
                text,
                subjects=("D-101G", "G-side", "G groove", "G to groove"),
                relations=(
                    "side groove",
                    "groove-to-mortise",
                    "mortise-to-side-groove",
                    "groove web",
                    "to groove",
                ),
                value_pattern=r"(?<!\d)(?:0?\.)?100(?!\d)",
            ),
            f"{label} omits the D-101G side-groove web >=0.100-inch gate",
        )
        self.assertTrue(
            _has_gate(
                text,
                subjects=(
                    "D-101G",
                    "G inter-mortise",
                    "G's two tight mortises",
                    "G between mortises",
                ),
                relations=(
                    "inter-mortise",
                    "between its two mortises",
                    "between mortises",
                ),
                value_pattern=r"(?<!\d)(?:0?\.)?220(?!\d)",
            ),
            f"{label} omits the D-101G inter-mortise web >=0.220-inch gate",
        )
        self.assertTrue(
            _has_gate(
                text,
                subjects=(
                    "mating rail",
                    "mating-rail",
                    "rail receiver",
                    "rail-receiver",
                    "receiver between mortises",
                    "E/F rail",
                ),
                relations=(
                    "inter-mortise",
                    "between the mortises",
                    "between mortises",
                ),
                value_pattern=r"(?<!\d)(?:0?\.)?100(?!\d)",
            ),
            f"{label} omits the mating-rail inter-mortise web >=0.100-inch gate",
        )

    def test_d101g_web_gates_are_distinct_in_spec_and_release_sources(self):
        tolerances = self.spec["fabrication_tolerances"]
        expected = {
            "muntin_tight_mortise_web_to_side_groove_min": 0.100,
            "muntin_tight_inter_mortise_web_min": 0.220,
            "muntin_rail_inter_mortise_web_min": 0.100,
        }
        for key, value in expected.items():
            with self.subTest(key=key):
                self.assertAlmostEqual(tolerances[key], value, places=6)

        self.assert_distinct_web_gates(self.combined, "combined guide")
        self.assert_distinct_web_gates(self.quick, "quick guide")
        self.assert_distinct_web_gates(self.project_builder, "project generator")
        self.assert_distinct_web_gates(_read(COMBINED_BUILDER), "combined-guide builder")

        generated_engineering = "\n".join(
            _read(path)
            for path in [
                ROOT / "project/modern-construction-standard.md",
                ROOT / "project/engineering-audit.md",
                ROOT / "project/domino-joint-engineering.md",
                ROOT / "project/decisions.md",
                ROOT / "project/domino-setup-register.csv",
            ]
        )
        self.assert_distinct_web_gates(
            generated_engineering,
            "generated engineering records",
        )

    def test_no_generic_point_one_web_rule_collapses_the_g_system(self):
        bad_patterns = [
            re.compile(
                r"d-101g\s+and\s+(?:the\s+)?mating[- ]rail(?:\s+critical)?\s+"
                r"webs?\s*(?:>=|at least)\s*0?\.100"
            ),
            re.compile(
                r"d-101g\s+and\s+(?:the\s+)?mating\s+rail\s+retain\s+at\s+least"
                r"\s*0?\.100\s+inch\s+(?:of\s+)?(?:actual\s+)?web"
            ),
            re.compile(
                r"(?:all|every)\s+(?:d-101g|g-system).{0,50}webs?.{0,30}"
                r"(?:>=|at least)\s*0?\.100"
            ),
            re.compile(
                r"0?\.100\s+inch\s+actual\s+web\s+at\s+both\s+outer\s+grooves"
                r"\s+and\s+between\s+the\s+mating[- ]rail"
            ),
        ]
        for path in _production_text_paths():
            for line_number, line in enumerate(_nonempty_lines(_read(path)), 1):
                for pattern in bad_patterns:
                    self.assertIsNone(
                        pattern.search(line),
                        f"{path.relative_to(ROOT)}:{line_number} collapses distinct G-system gates: {line}",
                    )

    def test_adhesive_gate_uses_only_published_open_time(self):
        forbidden = re.compile(
            r"\bopen(?:[- ]time)?\s*(?:or|/)\s*assembly(?:[- ]time)?\b"
        )
        for path in _production_text_paths():
            self.assertIsNone(
                forbidden.search(_plain(_read(path))),
                f"{path.relative_to(ROOT)} permits an assembly-time substitute",
            )

        adhesive = self.spec.get("adhesive")
        self.assertIsInstance(
            adhesive,
            dict,
            "specification needs an authoritative adhesive timing block",
        )
        adhesive_text = _plain(json.dumps(adhesive, sort_keys=True))
        for required in [
            "published open time",
            "rehearsal",
            "live",
            "final geometry",
            "clamp complete",
            "checkpoint",
        ]:
            with self.subTest(spec_term=required):
                self.assertIn(required, adhesive_text)
        self.assertRegex(adhesive_text, r"panel[- ]movement")
        self.assertRegex(adhesive_text, r"(?:0\.75|75\s*(?:percent|%))")

        for label, text in [
            ("combined guide", self.combined),
            ("quick guide", self.quick),
            ("project generator", self.project_builder),
        ]:
            normalized = _plain(text)
            with self.subTest(source=label):
                self.assertIn("published open time", normalized)
                self.assertRegex(normalized, r"(?:0\.75|75\s*(?:percent|%))")
                self.assertRegex(normalized, r"\brehears")
                self.assertRegex(
                    normalized,
                    r"(?:\blive.{0,30}\btimer\b|\btimer.{0,30}\blive\b)",
                )
                self.assertIn("final geometry", normalized)
                self.assertRegex(normalized, r"panel[- ]movement")
                self.assertRegex(
                    normalized,
                    r"(?:clamp complete.{0,100}checkpoint|"
                    r"checkpoint.{0,100}clamp complete)",
                )

    def test_rehearsal_tenons_cannot_mask_shallow_mortises(self):
        for label, text in [
            ("combined guide", self.combined),
            ("quick guide", self.quick),
            ("project generator", self.project_builder),
        ]:
            normalized = _plain(text)
            with self.subTest(source=label):
                self.assertRegex(normalized, r"paired.{0,80}production[- ]thickness")
                self.assertRegex(
                    normalized,
                    r"(?:first.{0,120})?untouched.{0,50}full[- ]length"
                    r".{0,40}factory\s+tenons?",
                )
                self.assertRegex(
                    normalized,
                    r"(?:minimal(?:ly)?|lightly).{0,80}"
                    r"(?:ribs?(?:bed)?(?:\s+faces?)?\s*(?:/|and)\s*ends?|"
                    r"faces?\s*(?:/|and)\s*ends?)",
                )
                self.assertRegex(
                    normalized,
                    r"(?:never|do not|must not)\s+(?:be\s+)?shorten(?:ed)?",
                )

        for path in _production_text_paths():
            for line_number, raw_line in enumerate(_read(path).splitlines(), 1):
                line = _plain(raw_line)
                if (
                    "tenon" not in line
                    or not re.search(r"\bshorten(?:ed|ing)?\b", line)
                ):
                    continue
                self.assertRegex(
                    line,
                    r"\b(?:never|do not|must not|without)\b",
                    f"{path.relative_to(ROOT)}:{line_number} allows tenon shortening: {line}",
                )

    def test_optional_cap_is_sized_from_completed_head_backband(self):
        trim = self.spec["trim"]
        expected = "actual fitted head-backband outside width + 2p"
        self.assertEqual(_plain(trim["length_formulas"]["optional_head_cap"]), expected)
        head_cap = trim.get("head_cap") or trim.get("optional_head_cap")
        self.assertIsInstance(head_cap, dict)
        self.assertEqual(_plain(head_cap["finished_length"]), expected)
        self.assertIn(
            "actual fitted head-backband outside width + 2p",
            _plain(head_cap["rough_length"]),
        )

        for label, text in [
            ("moulding guide", self.moulding),
            ("project generator", self.project_builder),
            ("moulding builder", _read(MOULDING_BUILDER)),
        ]:
            with self.subTest(source=label):
                self.assertIn(expected, _plain(text))

        old_formula = re.compile(
            r"(?:optional\s+head\s+cap|m-204|cap(?:\s+finished)?\s+length)"
            r".{0,160}(?:actual\s+fitted\s+)?head[- ]casing"
            r"(?:\s+outside\s+width)?\s*\+\s*2p"
        )
        for path in _production_text_paths():
            for line_number, line in enumerate(_nonempty_lines(_read(path)), 1):
                self.assertIsNone(
                    old_formula.search(line),
                    f"{path.relative_to(ROOT)}:{line_number} still sizes M-204 from head casing",
                )

    def test_permanent_trim_order_is_unambiguous(self):
        sequence = self.spec["trim"]["permanent_installation_sequence"]
        self.assertGreaterEqual(len(sequence), 5)
        required_by_step = [
            ("plinth", "first"),
            ("casing",),
            ("backband", "return"),
            ("cap",),
            ("stop", "last"),
        ]
        for index, terms in enumerate(required_by_step):
            step = _plain(sequence[index])
            with self.subTest(step=index + 1):
                for term in terms:
                    self.assertIn(term, step)

        for label, text in [
            ("combined guide", self.combined),
            ("moulding guide", self.moulding),
            ("project generator", self.project_builder),
        ]:
            normalized = _plain(text)
            starts = list(re.finditer(r"\bplinths?\s+first\b", normalized))
            ordered = False
            for start in starts:
                window = normalized[start.start() : start.start() + 1000]
                positions = [
                    window.find("plinth"),
                    window.find("casing"),
                    window.find("backband"),
                    window.find("cap"),
                ]
                stop_match = re.search(r"\bstops?\s+last\b|\bdoor\s+stop\b.{0,30}\blast\b", window)
                if (
                    all(position >= 0 for position in positions)
                    and positions == sorted(positions)
                    and stop_match is not None
                    and stop_match.start() > positions[-1]
                ):
                    ordered = True
                    break
            self.assertTrue(
                ordered,
                f"{label} needs an explicit plinth -> casing -> backband/returns -> cap -> stop-last sequence",
            )

    def test_standalone_moulding_field_gate_records_jamb_geometry(self):
        match = re.search(
            r"^##\s+Field release gate\s*$\n(?P<body>.*?)(?=^##\s+)",
            self.moulding,
            flags=re.IGNORECASE | re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(match, "standalone moulding guide has no field-release section")
        field_gate = _plain(match.group("body"))
        for required in ["plumb", "level", "diagonal", "square", "twist"]:
            with self.subTest(term=required):
                self.assertIn(required, field_gate)
        self.assertRegex(field_gate, r"winding\s+sticks?")

    def test_worksheet_source_produces_separate_four_page_face_registers(self):
        source = _read(MOULDING_BUILDER)
        tree = ast.parse(source)
        function = next(
            (
                node
                for node in tree.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == "build_worksheet"
            ),
            None,
        )
        self.assertIsNotNone(function, "build_worksheet() is missing")
        show_page_calls = [
            node
            for node in ast.walk(function)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "showPage"
        ]
        self.assertEqual(
            len(show_page_calls),
            4,
            "worksheet source must close exactly four physical pages",
        )

        normalized = _plain(source)
        for required in [
            "face a - full production length register",
            "face b - full production length register",
            "face b omit",
            "expected 4 worksheet pages",
        ]:
            with self.subTest(term=required):
                self.assertIn(required, normalized)
        self.assertRegex(
            source,
            r"draw_face_register\(\s*3\s*,\s*[\"']A[\"']",
        )
        self.assertRegex(
            source,
            r"draw_face_register\(\s*4\s*,\s*[\"']B[\"']"
            r"\s*,\s*allow_omit\s*=\s*True",
        )

    def test_quick_diagrams_show_spacers_and_module_before_n(self):
        generator = _load_generator(
            "_release_consistency_quick_diagrams",
            QUICK_DIAGRAM_GENERATOR,
        )
        with tempfile.TemporaryDirectory(prefix="dc1916-quick-svg-") as temp_dir:
            generator.OUT = Path(temp_dir)
            generator.bottom_module()
            generator.load_hinge_stile()
            generator.close_lock_stile()

            lower_nodes = _svg_text_nodes(generator.OUT / "03-bottom-module.svg")
            load_nodes = _svg_text_nodes(generator.OUT / "04-load-panels.svg")
            close_nodes = _svg_text_nodes(generator.OUT / "05-close-lock-stile.svg")

            for label, nodes in [
                ("lower-module", lower_nodes),
                ("hinge-stile loading", load_nodes),
                ("lock-stile closure", close_nodes),
            ]:
                normalized = _plain(" ".join(value for value, _, _ in nodes))
                self.assertIn("foam", normalized, f"{label} omits foam spacer material")
                self.assertRegex(
                    normalized,
                    r"3/4[- ]in(?:ch)?[- ]long",
                    f"{label} omits the 3/4-inch longitudinal spacer callout",
                )

            load_text = _plain(" ".join(value for value, _, _ in load_nodes))
            self.assertIn("d-101n - staged right", load_text)
            module_steps = [
                (value, y)
                for value, _, y in load_nodes
                if re.search(r"\b4\b.*\blower module\b", _plain(value))
            ]
            n_steps = [
                (value, y)
                for value, _, y in load_nodes
                if re.search(r"\b5\b.*\bslide n\b", _plain(value))
            ]
            self.assertTrue(module_steps, "diagram 04 lacks a numbered lower-module step")
            self.assertTrue(n_steps, "diagram 04 lacks a later numbered D-101N step")
            self.assertIsNotNone(module_steps[0][1])
            self.assertIsNotNone(n_steps[0][1])
            self.assertLess(
                module_steps[0][1],
                n_steps[0][1],
                "diagram 04 visually lists D-101N before the lower module",
            )

            close_text = _plain(" ".join(value for value, _, _ in close_nodes))
            self.assertIn("8 b-side foam spacers", close_text)
            self.assertRegex(close_text, r"h\s*/\s*j\s*/\s*n\s*/\s*l\s*[x×]\s*2")
            numbered_spacers = {
                value
                for value, x, _ in close_nodes
                if value in {str(number) for number in range(1, 9)}
                and x is not None
                and x > 800
            }
            self.assertEqual(
                numbered_spacers,
                {str(number) for number in range(1, 9)},
                "diagram 05 must visibly identify all eight B-side spacers",
            )

    def test_three_quarter_foam_spacer_control_is_explicit_and_calculated(self):
        panels = self.spec["panels"]
        spacer = panels["panel_spacers"]
        candidate = spacer["reference_candidate"]
        groove = self.spec["groove"]
        tolerances = self.spec["fabrication_tolerances"]

        self.assertAlmostEqual(spacer["mandatory_longitudinal_length"], 0.75)
        self.assertAlmostEqual(candidate["longitudinal_length"], 0.75)
        self.assertAlmostEqual(candidate["nominal_cross_section_width"], 0.265)
        self.assertAlmostEqual(candidate["nominal_cross_section_depth"], 0.265)
        self.assertEqual(candidate["manufacturer_groove_range"], [0.22, 0.25])
        self.assertAlmostEqual(candidate["manufacturer_compression_guidance"], 0.50)
        self.assertIn("candidate", _plain(candidate["status"]))
        self.assertIn("not approved", _plain(candidate["status"]))
        self.assertIn("longitudinal", _plain(spacer["dimension_note"]))
        self.assertIn("not the groove width", _plain(spacer["dimension_note"]))
        self.assertEqual(spacer["installed_quantity"], 5 * 2 * 2)
        self.assertEqual(spacer["test_spare_quantity"], 10)
        self.assertIn("vertical side groove", _plain(spacer["placement"]))
        self.assertIn("no spacers in horizontal", _plain(spacer["placement"]))

        depth_tol = tolerances["groove_depth"]
        groove_depth_min = depth_tol["target"] - depth_tol["minus"]
        groove_depth_max = depth_tol["target"] + depth_tol["plus"]
        tongue_depth_min = (
            panels["tongue_depth"]
            - panels["tongue_depth_tolerance_plus_minus"]
        )
        tongue_depth_max = (
            panels["tongue_depth"]
            + panels["tongue_depth_tolerance_plus_minus"]
        )
        foam_depth = candidate["nominal_cross_section_depth"]

        families = [
            (
                "full_width_family",
                panels["full_width_clearance_across_grain_total"],
                0.1875,
                (0.1825, 0.2025),
            ),
            (
                "lower_family",
                panels["small_width_clearance_across_grain_total"],
                0.1250,
                (0.1200, 0.1400),
            ),
        ]
        analysis = spacer["compression_analysis"]
        for family, movement_clearance, expected_nominal_gap, expected_gap_range in families:
            with self.subTest(family=family):
                nominal_gap = (
                    groove["depth"]
                    - panels["tongue_depth"]
                    + movement_clearance / 2
                )
                min_gap = (
                    groove_depth_min - tongue_depth_max + movement_clearance / 2
                )
                max_gap = (
                    groove_depth_max - tongue_depth_min + movement_clearance / 2
                )
                compression_nominal = 1 - nominal_gap / foam_depth
                compression_range = (
                    1 - max_gap / foam_depth,
                    1 - min_gap / foam_depth,
                )
                governed = analysis[family]
                self.assertAlmostEqual(nominal_gap, expected_nominal_gap, places=6)
                self.assertAlmostEqual(min_gap, expected_gap_range[0], places=6)
                self.assertAlmostEqual(max_gap, expected_gap_range[1], places=6)
                self.assertAlmostEqual(
                    governed["centered_tongue_end_gap_nominal"],
                    nominal_gap,
                    places=6,
                )
                self.assertAlmostEqual(
                    governed["candidate_compression_nominal"],
                    compression_nominal,
                    places=6,
                )
                self.assertAlmostEqual(
                    governed["candidate_compression_tolerance_range"][0],
                    compression_range[0],
                    places=6,
                )
                self.assertAlmostEqual(
                    governed["candidate_compression_tolerance_range"][1],
                    compression_range[1],
                    places=6,
                )

        groove_width_tol = tolerances["groove_width"]
        permitted_groove_max = (
            groove_width_tol["target"] + groove_width_tol["plus"]
        )
        self.assertGreater(
            permitted_groove_max,
            candidate["manufacturer_groove_range"][1],
            "test expects the documented PB265 groove-range hold to remain material",
        )
        release_condition = _plain(candidate["groove_release_condition"])
        self.assertIn("0.250", release_condition)
        self.assertIn("written approval", release_condition)

        for label, text in [
            ("combined guide", self.combined),
            ("quick guide", self.quick),
            ("project generator", self.project_builder),
        ]:
            normalized = _plain(text)
            for required in [
                "3/4-inch",
                "foam",
                "pb265-750xf-1m",
                "candidate",
                "h/j/n",
                "k/l",
                "50 percent",
            ]:
                with self.subTest(label=label, required=required):
                    self.assertIn(required, normalized)
            self.assertNotIn("exact approved equivalent", normalized)

        source_register = _read(ROOT / "project/source-register.csv")
        self.assertIn(
            "https://panelbuddies.com/products/pb265-750xf-1m",
            source_register,
        )
        self.assertIn("https://panelbuddies.com/", source_register)

    def test_groove_cutaway_renders_tongue_projection_tolerance(self):
        generator = _load_generator(
            "_release_consistency_cabinet_renders",
            CABINET_RENDER_GENERATOR,
        )
        with tempfile.TemporaryDirectory(prefix="dc1916-cutaway-svg-") as temp_dir:
            generator.OUT = Path(temp_dir)
            generator.groove_panel_cutaway()
            svg = _plain(_read(generator.OUT / "04-groove-panel-cutaway.svg"))
            self.assertRegex(
                svg,
                r"(?:7/16|0\.4375)\s*(?:\+/-|±)\s*0?\.005",
                "cutaway must show 7/16-inch tongue projection with +/-0.005 tolerance",
            )
            self.assertRegex(svg, r"0\.750\s+length")
            self.assertRegex(svg, r"0\.265\s*[x×]\s*0\.265")
            self.assertIn("spacer does not set panel cut size", svg)
            self.assertIn("sample-test both clearance families", svg)

        self.assertAlmostEqual(self.spec["panels"]["tongue_depth"], 7 / 16, places=8)
        self.assertAlmostEqual(
            self.spec["panels"]["tongue_depth_tolerance_plus_minus"],
            0.005,
            places=8,
        )
        generator_source = _plain(_read(CABINET_RENDER_GENERATOR))
        self.assertRegex(
            generator_source,
            r"(?:7/16|0\.4375)\s*(?:\+/-|±)\s*0?\.005",
        )

    def test_fastener_sound_embedment_gates_are_numeric(self):
        gates = self.spec["trim"]["fastener_embedment_minimums"]
        expected = {
            "inner_casing_into_sound_jamb": 0.75,
            "door_stop_into_sound_jamb": 0.75,
            "outer_casing_into_verified_framing": 1.0,
            "backband_into_casing": 0.50,
        }
        self.assertEqual(set(gates), set(expected))
        for key, value in expected.items():
            with self.subTest(key=key):
                self.assertAlmostEqual(gates[key], value, places=6)

        textual_gates = [
            (
                ("inner casing", "casing inner", "m-201 inner", "inner/stop"),
                ("jamb",),
                r"(?:0?\.75|3/4)",
            ),
            (
                ("door stop", "door-stop", "m-203", "inner/stop"),
                ("jamb",),
                r"(?:0?\.75|3/4)",
            ),
            (
                ("outer casing", "casing outer", "outer zones", "outer >="),
                ("framing",),
                r"(?:1(?:\.0+)?)(?!\d)",
            ),
            (
                ("backband", "m-202", "band >="),
                ("casing",),
                r"(?:0?\.50|1/2)",
            ),
        ]
        for label, text in [
            ("combined guide", self.combined),
            ("moulding guide", self.moulding),
            ("moulding builder", _read(MOULDING_BUILDER)),
        ]:
            lines = _nonempty_lines(text)
            for subjects, objects, value_pattern in textual_gates:
                found = any(
                    any(subject in line for subject in subjects)
                    and all(obj in line for obj in objects)
                    and re.search(value_pattern, line)
                    for line in lines
                )
                self.assertTrue(
                    found,
                    f"{label} omits numeric sound-embedment gate for {subjects[0]}",
                )


if __name__ == "__main__":
    unittest.main()
