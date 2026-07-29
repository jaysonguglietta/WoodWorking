"""Regression checks for the Rev. G / LS-05 / RL-02 first-crosscut plan."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RoughLengthCutListTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rough = json.loads(
            (ROOT / "project/rough-length-cut-plan.json").read_text(
                encoding="utf-8"
            )
        )
        cls.stock = json.loads(
            (ROOT / "project/labeled-stock-plan.json").read_text(
                encoding="utf-8"
            )
        )
        cls.spec = json.loads(
            (ROOT / "project/specification.yaml").read_text(encoding="utf-8")
        )
        cls.boards = {row["label"]: row for row in cls.rough["boards"]}
        cls.inventory = {row["label"]: row for row in cls.stock["inventory"]}
        cls.components = {row["id"]: row for row in cls.spec["components"]}

    def test_document_controls_are_current(self):
        document = self.rough["document"]
        self.assertEqual(document["project"], "DC-1916-001")
        self.assertEqual(document["revision"], "Rev. G")
        self.assertEqual(document["stock_plan"], "LS-05")
        self.assertEqual(document["rough_length_plan"], "RL-02")
        self.assertIn("CHK-RS-01", document["status"])

    def test_every_owner_board_has_one_first_crosscut_decision(self):
        self.assertEqual(list(self.boards), list("ABCDEFGHIJKLMNO"))
        self.assertEqual(set(self.boards), set(self.inventory))

    def test_only_panel_boards_receive_first_stage_crosscuts(self):
        cut_now = {
            label for label, row in self.boards.items() if row["cut_now"]
        }
        self.assertEqual(cut_now, {"D", "G", "H", "M"})
        for label in {"A", "B", "C", "E", "F", "I", "J", "K", "L", "N", "O"}:
            with self.subTest(stock=label):
                self.assertEqual(self.boards[label]["cuts_now"], 0)
                self.assertIn("NO ", self.boards[label]["action"])

    def test_boards_n_and_o_remain_full_length_reserve(self):
        for label in ("N", "O"):
            with self.subTest(stock=label):
                board = self.boards[label]
                self.assertEqual(self.inventory[label]["length"], 74.0)
                self.assertFalse(board["cut_now"])
                self.assertIn("KEEP FULL 74", board["action"])
                self.assertIn("cannot replace an 81-inch stile", board["hold_reason"])
                self.assertIn("short-member", board["later_pattern"])

    def test_panel_shop_billets_are_finished_plus_one_inch(self):
        part_by_stock = {
            "M": "D-101H",
            "D": "D-101K",
            "G": "D-101J",
            "H": "D-101N",
        }
        expected = {
            "M": (3, 16.0625, 15.5625),
            "D": (4, 12.8125, 12.3125),
            "G": (4, 16.5625, 16.0625),
            "H": (3, 11.3125, 10.8125),
        }
        for label, (quantity, shop, controlled) in expected.items():
            with self.subTest(stock=label):
                segment = self.boards[label]["cut_now"][0]
                finished = self.components[part_by_stock[label]]["l"]
                self.assertEqual(segment["quantity"], quantity)
                self.assertAlmostEqual(segment["shop_length"], shop)
                self.assertAlmostEqual(
                    segment["controlled_rough_length"], controlled
                )
                self.assertAlmostEqual(segment["shop_length"], finished + 1)
                self.assertAlmostEqual(
                    segment["controlled_rough_length"], finished + 0.5
                )

    def test_board_g_current_s4s_envelope_still_fits_center_panel(self):
        inventory = self.inventory["G"]
        board = self.boards["G"]
        self.assertEqual(inventory["thickness"], 0.9375)
        self.assertEqual((inventory["width"], inventory["length"]), (4.5, 75.0))
        self.assertIn("S4S", board["raw_dimensions"])
        self.assertIn("THICKNESS/WIDTH/LENGTH PASS", board["action"])
        self.assertAlmostEqual(inventory["thickness"] - 0.625, 0.3125)
        self.assertAlmostEqual(4 * inventory["width"] - 16.375, 1.625)
        self.assertAlmostEqual(board["tail_before_end_reserve"], 8.25)
        self.assertAlmostEqual(board["planning_tail_after_end_reserve"], 6.25)

    def test_cut_now_arithmetic_includes_kerf_and_shared_end_reserve(self):
        kerf = self.rough["rules"]["saw_kerf"]
        end_reserve = self.rough["rules"]["total_board_end_reserve"]
        self.assertAlmostEqual(kerf, 0.125)
        self.assertAlmostEqual(end_reserve, 2.0)
        for label in {"M", "D", "G", "H"}:
            board = self.boards[label]
            segment = board["cut_now"][0]
            used = (
                segment["quantity"] * segment["shop_length"]
                + board["cuts_now"] * kerf
            )
            tail = self.inventory[label]["length"] - used
            self.assertAlmostEqual(tail, board["tail_before_end_reserve"])
            self.assertAlmostEqual(
                tail - end_reserve,
                board["planning_tail_after_end_reserve"],
            )

    def test_board_a_is_preserved_and_board_m_carries_upper_panel(self):
        board = self.boards["A"]
        self.assertAlmostEqual(self.inventory["A"]["length"], 72.75)
        self.assertIn("72-3/4", board["raw_dimensions"])
        self.assertIn("6-inch damage removal", board["raw_dimensions"])
        self.assertFalse(board["cut_now"])
        self.assertIn("KEEP FULL", board["action"])
        self.assertIn("STOCK-M now carries D-101H", board["hold_reason"])

        board_m = self.boards["M"]
        self.assertAlmostEqual(self.inventory["M"]["length"], 99.0)
        self.assertIn("3/4 x 8-1/4 x 99", board_m["raw_dimensions"])
        self.assertAlmostEqual(board_m["planning_tail_after_end_reserve"], 48.4375)
        self.assertAlmostEqual(board_m["full_pattern_paper_remainder"], 15.6875)
        self.assertIn("5/8-inch recoverable thickness", board_m["hold_reason"])

    def test_no_resaw_continuous_stile_boards_remain_full_length(self):
        for label in ("B", "C", "I", "K"):
            with self.subTest(stock=label):
                board = self.boards[label]
                self.assertFalse(board["cut_now"])
                self.assertIn("FULL", board["action"])
                self.assertNotIn("resaw", board["later_pattern"].lower())
        self.assertIn("5/16", self.boards["B"]["later_pattern"])
        self.assertIn("5/16", self.boards["C"]["later_pattern"])
        self.assertIn("4-3/8", self.boards["I"]["later_pattern"])
        self.assertIn("4-3/8", self.boards["K"]["later_pattern"])
        self.assertIn("8-7/8", self.boards["I"]["hold_reason"])
        self.assertIn("8-7/8", self.boards["K"]["hold_reason"])

    def test_knot_face_pool_and_short_core_holds_remain_intact(self):
        for label in ("E", "F"):
            board = self.boards[label]
            self.assertFalse(board["cut_now"])
            self.assertIn("knot", board["hold_reason"].lower())
            self.assertIn("16-1/4", board["later_pattern"])
        for label in ("J", "L"):
            board = self.boards[label]
            self.assertFalse(board["cut_now"])
            self.assertIn("CHK-SM-01", board["action"])
            self.assertIn("16-1/4", board["later_pattern"])

    def test_six_inch_l_forces_revised_j_l_core_swap(self):
        self.assertIn("1-5/16 x 6 x 80", self.boards["L"]["raw_dimensions"])
        self.assertIn("5-inch and 2-1/4-inch D-101D", self.boards["L"]["later_pattern"])
        self.assertIn("not authorized for any 6-1/2-inch billet", self.boards["L"]["later_pattern"])
        self.assertIn("6-1/2-inch D-101F", self.boards["J"]["later_pattern"])
        self.assertIn("only no-purchase source", self.boards["J"]["hold_reason"])

    def test_rules_explicitly_prohibit_through_thickness_sawing(self):
        rules_text = " ".join(str(value) for value in self.rough["rules"].values())
        self.assertIn("no resaw", rules_text.lower())
        self.assertIn("thickness", rules_text.lower())
        self.assertIn("ordinary", rules_text.lower())

    def test_zero_spare_sequence_proves_long_stile_stock_first(self):
        rules = self.rough["rules"]
        release = rules["zero_spare_release_rule"]
        staged = rules["staged_milling_rule"]
        self.assertIn("B/C", release)
        self.assertIn("I/K", release)
        self.assertIn("before releasing any M/D/G/H", release)
        self.assertIn("rest and recheck", staged)
        self.assertIn("controlled rough size", staged)
        self.assertIn("manufacturer's safe minimum", rules["machine_minimum_rule"])

    def test_source_plan_and_panel_gate_are_synchronized(self):
        checks = {row["id"]: row for row in self.stock["critical_checks"]}
        self.assertIn("RL-02", checks["CHK-P-01"]["check"])
        self.assertIn(
            "controlled rough length", checks["CHK-P-01"]["pass"]
        )
        self.assertIn("five", checks["CHK-SM-01"]["pass"].lower())
        self.assertIn("16-1/4", checks["CHK-SM-01"]["pass"])


if __name__ == "__main__":
    unittest.main()
