"""Regression checks for the Rev. G / LS-05 no-resaw stock plan."""

from __future__ import annotations

import json
import unittest
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class LabeledStockPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = json.loads(
            (ROOT / "project/labeled-stock-plan.json").read_text(
                encoding="utf-8"
            )
        )
        cls.spec = json.loads(
            (ROOT / "project/specification.yaml").read_text(encoding="utf-8")
        )
        cls.inventory = {row["label"]: row for row in cls.plan["inventory"]}
        cls.allocations = {
            row["part"]: row for row in cls.plan["component_allocations"]
        }
        cls.operations = {
            row["operation_id"]: row for row in cls.plan["operations"]
        }
        cls.layers = {
            row["part"]: row for row in cls.plan["laminated_member_schedule"]
        }
        cls.checks = {
            row["id"]: row for row in cls.plan["critical_checks"]
        }

    def test_inventory_preserves_all_fifteen_owner_measurements(self):
        expected = {
            "A": (1.0, 5.6875, 72.75),
            "B": (1.0, 4.9375, 85.0),
            "C": (1.0, 5.75, 83.125),
            "D": (1.0, 5.0, 73.75),
            "E": (1.0, 5.75, 75.5),
            "F": (1.0, 5.625, 70.75),
            "G": (0.9375, 4.5, 75.0),
            "H": (0.875, 5.75, 79.0),
            "I": (1.5, 9.25, 84.75),
            "J": (1.3125, 7.0, 79.25),
            "K": (1.375, 9.5, 82.5),
            "L": (1.3125, 6.0, 80.0),
            "M": (0.75, 8.25, 99.0),
            "N": (1.75, 11.0, 74.0),
            "O": (1.75, 11.0, 74.0),
        }
        self.assertEqual(set(self.inventory), set(expected))
        for label, dimensions in expected.items():
            with self.subTest(stock=label):
                row = self.inventory[label]
                self.assertEqual(
                    (row["thickness"], row["width"], row["length"]),
                    dimensions,
                )
        self.assertIn("6-inch damaged section", self.inventory["A"]["condition"])
        self.assertIn("ORIGINAL 78 3/4", self.inventory["A"]["original_entry"])
        self.assertIn("finished white oak", self.inventory["M"]["condition"])
        self.assertIn("S4S", self.inventory["G"]["condition"])
        self.assertIn("15/16-inch thickness", self.inventory["G"]["condition"])
        for label in ("N", "O"):
            self.assertIn("Finished white oak", self.inventory[label]["condition"])
            self.assertIn("Keep full length", self.inventory[label]["planned_use"])

    def test_board_m_replaces_damaged_a_as_primary_upper_panel_stock(self):
        self.assertEqual(self.allocations["D-101H"]["stock"], "M")
        self.assertEqual(self.operations["M-01"]["segment_count"], 3)
        self.assertAlmostEqual(self.operations["M-01"]["segment_length"], 15.5625)
        self.assertEqual(self.operations["M-02"]["segment_count"], 2)
        self.assertAlmostEqual(self.operations["M-02"]["segment_length"], 16.25)
        self.assertIn("Keep intact", self.inventory["A"]["planned_use"])
        self.assertIn("Primary three-stave", self.inventory["M"]["planned_use"])

    def test_boards_n_and_o_are_uncut_short_member_reserve(self):
        for label in ("N", "O"):
            with self.subTest(stock=label):
                row = self.inventory[label]
                self.assertEqual((row["thickness"], row["width"], row["length"]), (1.75, 11.0, 74.0))
                self.assertIn("short-member", row["planned_use"])
                self.assertIn("SHORT-CORE FALLBACK", row["disposition"])
        self.assertIn("STOCK-N/O", self.plan["fallback"]["if_short_member_plan_fails"])

    def test_document_is_current_rough_sawn_door_only_control(self):
        document = self.plan["document"]
        assumptions = self.plan["assumptions"]
        self.assertEqual(document["stock_plan"], "LS-05")
        self.assertEqual(document["supersedes"], "LS-04")
        self.assertEqual(document["revision"], "Rev. G")
        self.assertTrue(assumptions["dimensions_are_actual"])
        self.assertFalse(assumptions["dimensions_are_dressed_not_nominal"])
        self.assertFalse(assumptions["dimensions_are_rough_sawn"])
        self.assertFalse(assumptions["reported_dimensions_are_raw"])
        self.assertIn("STOCK-G is confirmed S4S", assumptions["surface_condition"])
        self.assertIn("reserved exclusively for the door", assumptions["scope_rule"])
        self.assertIn("B/C", assumptions["zero_spare_release_rule"])
        self.assertIn("I/K", assumptions["zero_spare_release_rule"])
        self.assertIn("controlled rough size", assumptions["staged_milling_rule"])
        self.assertIn("manufacturer's safe minimum", assumptions["machine_minimum_rule"])

    def test_every_component_has_one_owner_stock_allocation(self):
        expected = {row["id"] for row in self.spec["components"]}
        actual = [row["part"] for row in self.plan["component_allocations"]]
        self.assertEqual(set(actual), expected)
        self.assertEqual(len(actual), len(set(actual)))
        self.assertNotIn("NEW", {row["stock"] for row in self.plan["component_allocations"]})

    def test_balanced_stack_is_made_without_thickness_slicing(self):
        assumptions = self.plan["assumptions"]
        construction = self.spec["frame"]["construction"]
        preglue = (
            assumptions["frame_face_preglue_thickness"]
            + assumptions["frame_core_preglue_thickness"]
            + assumptions["frame_face_preglue_thickness"]
        )
        finished = (
            assumptions["frame_face_finished_thickness"]
            + assumptions["frame_core_preglue_thickness"]
            + assumptions["frame_face_finished_thickness"]
        )
        self.assertAlmostEqual(preglue, 1.5)
        self.assertAlmostEqual(finished, 1.375)
        self.assertAlmostEqual(preglue, construction["glue_blank_thickness"])
        self.assertEqual(
            construction["finished_glue_lines_from_show_face"], [0.25, 1.125]
        )
        self.assertTrue(construction["thickness_slicing_prohibited"])
        self.assertIn("no resaw", assumptions["no_resaw_rule"].lower())
        self.assertIn("staged planing", assumptions["milling_rule"].lower())
        for operation in self.plan["operations"]:
            active = " ".join(
                str(operation[key])
                for key in ("rip_plan", "yield", "status", "notes")
            ).lower()
            self.assertNotIn("resaw once", active)
            self.assertNotIn("resawn", active)

    def test_continuous_stile_layer_allocation_is_exact(self):
        self.assertEqual(
            (
                self.layers["D-101A"]["core_stock"],
                self.layers["D-101A"]["show_face_stock"],
                self.layers["D-101A"]["back_face_stock"],
            ),
            ("K", "B", "K parallel lane"),
        )
        self.assertEqual(
            (
                self.layers["D-101B"]["core_stock"],
                self.layers["D-101B"]["show_face_stock"],
                self.layers["D-101B"]["back_face_stock"],
            ),
            ("I", "C", "I parallel lane"),
        )
        for part in ("D-101A", "D-101B"):
            self.assertIn("continuous faces", self.layers[part]["seams"])
            self.assertIn("4-3/8", self.layers[part]["core_blank"])
            self.assertIn("4-3/8", self.layers[part]["face_blanks"])

    def test_i_and_k_two_lane_width_math_closes(self):
        kerf = self.plan["assumptions"]["saw_kerf"]
        required = 2 * 4.375 + kerf
        self.assertAlmostEqual(required, 8.875)
        self.assertAlmostEqual(self.inventory["I"]["width"] - required, 0.375)
        self.assertAlmostEqual(self.inventory["K"]["width"] - required, 0.625)
        self.assertIn("8-7/8", self.checks["CHK-ST-02"]["pass"])

    def test_j_and_l_short_core_map_is_explicit(self):
        self.assertEqual(self.operations["J-01"]["segment_count"], 3)
        self.assertAlmostEqual(self.operations["J-01"]["segment_length"], 16.25)
        self.assertEqual(self.operations["J-02"]["segment_count"], 1)
        self.assertAlmostEqual(self.operations["J-02"]["segment_length"], 12.0)
        self.assertEqual(self.operations["L-01"]["segment_count"], 4)
        self.assertAlmostEqual(self.operations["L-01"]["segment_length"], 16.25)
        for part in ("D-101C", "D-101M", "D-101D", "D-101E", "D-101F", "D-101G"):
            self.assertNotEqual(self.layers[part]["core_stock"], "signed FP-05")

    def test_six_inch_l_width_uses_revised_j_l_core_swap(self):
        self.assertEqual(self.inventory["L"]["width"], 6.0)
        self.assertIn("after edge cleanup", self.inventory["L"]["condition"])
        self.assertIn("no 6-1/2-inch billet is assigned to L", self.inventory["L"]["planned_use"])
        self.assertIn("6-1/2-inch D-101F wide core stave", self.inventory["J"]["planned_use"])
        self.assertEqual(self.layers["D-101D"]["core_stock"], "L-DW-CORE + L-DN-CORE")
        self.assertEqual(self.layers["D-101F"]["core_stock"], "L-F1-CORE + J-F2-CORE")
        self.assertIn("6-1/2-inch jointed width", self.checks["CHK-SM-01"]["pass"])

    def test_short_face_pool_has_a_quantified_knot_gate(self):
        pool = self.plan["short_face_pool_control"]
        self.assertEqual(pool["map_id"], "FP-05")
        source_text = " ".join(pool["required_sources"])
        self.assertIn("at least five clear 16-1/4-inch", source_text)
        self.assertIn("STOCK-E and STOCK-F", source_text)
        self.assertIn("both 5/16-inch faces", pool["release_rule"])
        self.assertIn("No face contains an end joint", pool["release_rule"])
        self.assertIn("whole-thickness", pool["planing_rule"])
        self.assertIn("CHK-FP-01", self.checks)

    def test_controlled_lock_and_bottom_rail_seams_match_spec(self):
        construction = self.spec["frame"]["construction"]["stave_built_members"]
        self.assertEqual(
            construction["D-101D"],
            {
                "core_seams_from_finished_top": [2.25],
                "show_face_seams_from_finished_top": [4.375],
                "back_face_seams_from_finished_top": [4.875],
            },
        )
        self.assertEqual(
            construction["D-101F"],
            {
                "core_seams_from_finished_top": [5.75],
                "show_face_seams_from_finished_top": [3.0, 6.5, 9.5],
                "back_face_seams_from_finished_top": [2.5, 5.0, 9.0],
            },
        )
        seam_gate = self.checks["CHK-SEAM-01"]["pass"]
        self.assertIn("0.3041", seam_gate)
        self.assertIn("0.4291", seam_gate)

    def test_operation_lengths_fit_every_used_board(self):
        kerf = self.plan["assumptions"]["saw_kerf"]
        consumed = defaultdict(float)
        reserves = defaultdict(float)
        for operation in self.plan["operations"]:
            consumed[operation["stock"]] += (
                operation["segment_count"] * operation["segment_length"]
                + operation["crosscuts"] * kerf
            )
            reserves[operation["stock"]] += operation["end_reserve"]
        for stock, used in consumed.items():
            with self.subTest(stock=stock):
                remainder = (
                    self.inventory[stock]["length"] - used - reserves[stock]
                )
                self.assertGreaterEqual(remainder, 0)

    def test_door_lumber_purchase_is_conditionally_zero(self):
        self.assertEqual(self.plan["purchase_requirements"], [])
        summary = self.plan["purchase_summary"]
        self.assertEqual(summary["planning_quantity_bf"], 0)
        self.assertEqual(summary["status"], "NO DOOR LUMBER PURCHASE RELEASED")
        for gate in (
            "CHK-ST-01",
            "CHK-ST-02",
            "CHK-SM-01",
            "CHK-FP-01",
            "CHK-P-01",
            "CHK-LAM-01",
            "CHK-SEAM-01",
        ):
            self.assertIn(gate, summary["conditional_credit"])

    def test_separate_two_face_moulding_order_is_unchanged(self):
        order = {
            row["id"]: row for row in self.plan["moulding_purchase_requirements"]
        }
        self.assertEqual(set(order), {"BUY-MOULD-4Q", "BUY-MOULD-6Q"})
        self.assertEqual(order["BUY-MOULD-4Q"]["quantity"], "7 boards")
        self.assertEqual(order["BUY-MOULD-6Q"]["quantity"], "2 boards")


if __name__ == "__main__":
    unittest.main()
