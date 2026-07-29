import ast
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def evaluate_length_formula(formula, values):
    """Evaluate the small arithmetic language used by the trim schedule."""

    aliases = {
        "actual fitted mitered side-casing outside long point": "mitered_side",
        "actual fitted square side-casing length": "square_side",
        "actual fitted head-backband outside width": "head_band_outside",
        "actual fitted head-casing outside width": "head_outside",
        "H-L": "H_left",
        "H-R": "H_right",
    }
    expression = formula
    for phrase, identifier in sorted(
        aliases.items(), key=lambda item: len(item[0]), reverse=True
    ):
        expression = expression.replace(phrase, identifier)
    expression = re.sub(
        r"(?<![\w.])(\d+(?:\.\d+)?)\s*([A-Za-z_]\w*)",
        r"\1*\2",
        expression,
    )
    tree = ast.parse(expression, mode="eval")

    def calculate(node):
        if isinstance(node, ast.Expression):
            return calculate(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.Name) and node.id in values:
            return float(values[node.id])
        if isinstance(node, ast.BinOp) and isinstance(
            node.op, (ast.Add, ast.Sub, ast.Mult)
        ):
            left = calculate(node.left)
            right = calculate(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            return left * right
        raise ValueError(f"unsupported formula element: {ast.dump(node)}")

    return calculate(tree)


class SpecificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = json.loads(
            (ROOT / "project/specification.yaml").read_text(encoding="utf-8")
        )

    def test_rev_g_project_identity(self):
        project = self.spec["project"]
        self.assertEqual(project["number"], "DC-1916-001")
        self.assertEqual(project["revision"], "Rev. G")
        self.assertEqual(self.spec["domino"]["model"], "Festool Domino DF 500")

    def test_confirmed_jamb_controls_fitted_slab_and_prefit_envelope(self):
        opening = self.spec["opening"]
        slab = self.spec["slab"]
        milling = self.spec["milling"]
        self.assertIn("confirmed installed finished jamb", opening["status"])
        self.assertEqual((opening["clear_width"], opening["clear_height"]), (24, 81))
        self.assertEqual(
            (
                opening["hinge_side_reveal"],
                opening["lock_side_reveal"],
                opening["head_reveal"],
                opening["bottom_gap"],
            ),
            (0.125, 0.125, 0.125, 0.375),
        )
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
        self.assertEqual(
            (slab["finished_width"], slab["finished_height"]),
            (23.75, 80.5),
        )
        reserve = slab["manufacturing_trim_reserve_per_edge"]
        self.assertEqual(reserve, 0.0625)
        self.assertEqual(
            (
                milling["prefit_assembly_width"],
                milling["prefit_assembly_height"],
            ),
            (
                slab["finished_width"] + 2 * reserve,
                slab["finished_height"] + 2 * reserve,
            ),
        )
        self.assertEqual(slab["finished_size_tolerance"]["width_plus"], 0)
        self.assertEqual(slab["finished_size_tolerance"]["height_plus"], 0)

    def test_balanced_frame_lamination_is_dimensionally_closed(self):
        frame = self.spec["frame"]
        construction = frame["construction"]
        self.assertEqual(
            construction["type"],
            "balanced three-layer, all-long-grain solid-oak lamination",
        )
        preglue = (
            construction["show_face_preglue_thickness"]
            + construction["core_preglue_thickness"]
            + construction["back_face_preglue_thickness"]
        )
        finished = (
            construction["show_face_finished_thickness"]
            + construction["core_preglue_thickness"]
            + construction["back_face_finished_thickness"]
        )
        self.assertAlmostEqual(preglue, construction["glue_blank_thickness"])
        self.assertAlmostEqual(preglue, 1.5)
        self.assertAlmostEqual(finished, self.spec["slab"]["finished_thickness"])
        self.assertAlmostEqual(
            construction["show_face_preglue_thickness"]
            - construction["symmetric_face_removal_each"],
            construction["show_face_finished_thickness"],
        )
        self.assertEqual(
            construction["finished_glue_lines_from_show_face"], [0.25, 1.125]
        )
        self.assertAlmostEqual(
            construction["face_glue_line_location_tolerance_plus_minus"], 0.01
        )
        self.assertIn("no end joint", construction["grain_rule"])
        self.assertAlmostEqual(
            construction["df_cutter_to_face_glue_line_core_clearance_min"], 0.2
        )
        self.assertTrue(construction["thickness_slicing_prohibited"])
        self.assertIn(
            "whole-thickness", construction["face_preparation_rule"].lower()
        )

    def test_two_face_moulding_procurement_uses_4q_and_6q_stock(self):
        trim = self.spec["trim"]
        procurement = trim["procurement"]
        self.assertEqual(trim["trimmed_face_count"], 2)
        self.assertEqual(trim["base_schedule_scope"], "two trimmed faces plus one three-piece door-stop set")
        self.assertEqual(
            procurement["casing_and_stop"]["quantity_boards"], 7
        )
        self.assertIn("4/4", procurement["casing_and_stop"]["description"])
        self.assertEqual(
            procurement["backband_and_optional_caps"]["quantity_boards"], 2
        )
        self.assertIn(
            "6/4", procurement["backband_and_optional_caps"]["description"]
        )
        self.assertAlmostEqual(procurement["dealer_volume_board_feet"], 40.0)
        self.assertIn("excluded", procurement["plinths"])

    def test_moulding_formulas_are_scheme_specific_and_numerically_sound(self):
        trim = self.spec["trim"]
        formulas = trim["length_formulas"]
        expected_formula_keys = {
            "mitered_head_inside_short",
            "mitered_head_outside_long",
            "mitered_left_leg_outside_long",
            "mitered_right_leg_outside_long",
            "square_left_leg",
            "square_right_leg",
            "square_head",
            "head_backband_outside_target",
            "mitered_side_backband_outer_long",
            "square_side_backband",
            "optional_head_cap",
        }
        self.assertEqual(set(formulas), expected_formula_keys)
        self.assertEqual(
            set(trim["head_joint_schemes"]),
            {"mitered surround", "square-butt head"},
        )

        values = {
            "W": 31.75,
            "R": 0.1875,
            "C": 4.5,
            "B": 1.125,
            "P": 0.75,
            "H_left": 82.25,
            "H_right": 82.0,
            "mitered_side": 86.9375,
            "square_side": 82.4375,
            "head_outside": 41.125,
            "head_band_outside": 43.375,
        }
        expected_results = {
            "mitered_head_inside_short": values["W"] + 2 * values["R"],
            "mitered_head_outside_long": values["W"]
            + 2 * values["R"]
            + 2 * values["C"],
            "mitered_left_leg_outside_long": values["H_left"]
            + values["R"]
            + values["C"],
            "mitered_right_leg_outside_long": values["H_right"]
            + values["R"]
            + values["C"],
            "square_left_leg": values["H_left"] + values["R"],
            "square_right_leg": values["H_right"] + values["R"],
            "square_head": values["W"] + 2 * values["R"] + 2 * values["C"],
            "head_backband_outside_target": values["head_outside"]
            + 2 * values["B"],
            "mitered_side_backband_outer_long": values["mitered_side"]
            + values["B"],
            "square_side_backband": values["square_side"] + values["C"],
            "optional_head_cap": values["head_band_outside"] + 2 * values["P"],
        }
        for formula_id, expected in expected_results.items():
            with self.subTest(formula_id=formula_id):
                self.assertAlmostEqual(
                    evaluate_length_formula(formulas[formula_id], values),
                    expected,
                )
        self.assertNotAlmostEqual(
            expected_results["mitered_side_backband_outer_long"],
            expected_results["square_side_backband"],
        )

    def test_moulding_does_not_require_a_dado_but_door_grooves_are_routed_by_scope(self):
        trim = self.spec["trim"]
        machining_split = self.spec["groove"]["machining_split"]
        self.assertFalse(trim["dado_blade_required"])
        self.assertEqual(
            set(machining_split),
            {"dado_stack", "plunge_router"},
        )
        self.assertTrue(all(value.strip() for value in machining_split.values()))

    def test_j06_lock_envelope_is_a_numeric_hold_point(self):
        hardware = self.spec["hardware"]
        domino = self.spec["domino"]
        clear_wood = hardware["lock_to_joinery_clear_wood_min"]
        self.assertAlmostEqual(clear_wood, 0.25)

        lock_center_from_top = (
            self.spec["slab"]["finished_height"]
            - hardware["nominal_lock_center_above_slab_bottom"]
        )
        self.assertAlmostEqual(
            lock_center_from_top,
            domino["stile_centers_from_slab_top_in"]["D-101D"][1],
        )

        gate = hardware["lock_envelope_gate"]
        self.assertEqual(set(re.findall(r"J-\d{2}", gate)), {"J-06"})
        fraction = re.search(
            r"required\s+(\d+)/(\d+)-inch clear-wood buffer", gate
        )
        self.assertIsNotNone(fraction)
        numerator, denominator = map(float, fraction.groups())
        self.assertAlmostEqual(numerator / denominator, clear_wood)

        required_measurements = set(hardware["required_measurements"])
        self.assertTrue(
            {
                "manufacturer",
                "model",
                "backset",
                "body height",
                "body thickness",
                "faceplate height",
                "faceplate width",
                "spindle size",
                "key/privacy location",
                "strike dimensions",
            }.issubset(required_measurements)
        )

    def test_domino_and_groove_controls_have_explicit_numeric_tolerances(self):
        domino = self.spec["domino"]
        tolerances = self.spec["fabrication_tolerances"]
        self.assertEqual(
            domino["muntin_mortise_width_strategy"]["D-101G"],
            ["tight", "tight"],
        )
        self.assertEqual(
            domino["muntin_mortise_width_strategy"]["D-101E and D-101F"],
            ["tight", "medium"],
        )
        self.assertGreater(domino["mortise_centerline_tolerance_plus_minus"], 0)
        self.assertEqual(
            set(tolerances["groove_depth"]), {"target", "plus", "minus"}
        )
        self.assertGreaterEqual(tolerances["groove_depth"]["plus"], 0)
        self.assertGreaterEqual(tolerances["groove_depth"]["minus"], 0)
        self.assertGreater(
            self.spec["panels"]["tongue_thickness_tolerance_plus_minus"], 0
        )
        self.assertGreater(
            tolerances["frame_medium_mortise_web_to_panel_groove_min"], 0
        )
        self.assertGreater(
            tolerances["muntin_tight_inter_mortise_web_min"], 0
        )
        self.assertGreater(tolerances["muntin_rail_inter_mortise_web_min"], 0)

    def test_adhesive_timing_uses_open_time_and_preserves_contingency(self):
        adhesive = self.spec["adhesive"]
        self.assertEqual(adhesive["eligible_timing_label"], "open time only")
        self.assertIn("published open time", adhesive["timing_basis"].lower())
        self.assertAlmostEqual(
            adhesive["rehearsal_final_gate_fraction_max"], 0.75
        )
        self.assertAlmostEqual(
            adhesive["live_final_geometry_fraction_max"], 0.75
        )
        self.assertAlmostEqual(adhesive["contingency_fraction_min"], 0.25)
        self.assertEqual(adhesive["timer_start"], "first adhesive contact")
        self.assertIn("final geometry", adhesive["timer_end"])
        self.assertIn("timer continues", adhesive["clamp_complete_status"])

    def test_trim_fasteners_have_numeric_sound_embedment_gates(self):
        gates = self.spec["trim"]["fastener_embedment_minimums"]
        self.assertEqual(
            gates,
            {
                "inner_casing_into_sound_jamb": 0.75,
                "door_stop_into_sound_jamb": 0.75,
                "outer_casing_into_verified_framing": 1.0,
                "backband_into_casing": 0.5,
            },
        )
        release = self.spec["trim"]["fastener_length_release"].lower()
        for term in ("actual installed layer stack", "matching offcut", "hold"):
            self.assertIn(term, release)


if __name__ == "__main__":
    unittest.main()
