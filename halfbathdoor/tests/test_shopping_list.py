import csv
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ShoppingListTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = json.loads(
            (ROOT / "project" / "specification.yaml").read_text(encoding="utf-8")
        )
        cls.stock_plan = json.loads(
            (ROOT / "project" / "labeled-stock-plan.json").read_text(encoding="utf-8")
        )
        with (ROOT / "build" / "reports" / "buy-list.csv").open(
            newline="", encoding="utf-8"
        ) as handle:
            cls.buy_rows = list(csv.DictReader(handle))
        cls.source = (
            ROOT / "shopping-list" / "DC-1916-001_Door_Shopping_List.md"
        ).read_text(encoding="utf-8")

    def test_door_quantities_match_rev_g_ls05_controls(self):
        self.assertEqual(self.spec["project"]["revision"], "Rev. G")
        self.assertEqual(self.spec["opening"]["clear_height"], 81.0)
        self.assertEqual(self.spec["slab"]["finished_height"], 80.5)

        by_item = {row["Item"]: row for row in self.buy_rows}
        door = by_item["Owner-labeled door stock A-O"]
        self.assertIn("71.52", door["Quantity"])
        self.assertIn("STOCK-G confirmed 15/16 x 4-1/2 x 75", door["Quantity"])
        self.assertIn("no door-lumber purchase released", door["Quantity"].lower())
        self.assertIn("all frame layers", door["Purpose"].lower())
        self.assertIn("no end-jointed structural layer", door["Substitution constraints"])
        self.assertIn("CHK-ST-01/02", door["Field verification"])

        adhesive = by_item["Type II PVA"]
        self.assertIn("32 oz minimum", adhesive["Quantity"])
        self.assertIn("actual layup area", adhesive["Quantity"])
        self.assertIn(
            "order 40",
            by_item["3/4-inch-long foam panel spacers"]["Quantity"],
        )

    def test_ls05_allocates_every_door_part_to_owner_labeled_stock(self):
        plan = self.stock_plan
        self.assertEqual(plan["document"]["stock_plan"], "LS-05")
        self.assertEqual(plan["document"]["supersedes"], "LS-04")
        self.assertFalse(plan["assumptions"]["dimensions_are_dressed_not_nominal"])
        self.assertFalse(plan["assumptions"]["dimensions_are_rough_sawn"])
        self.assertFalse(plan["assumptions"]["reported_dimensions_are_raw"])
        self.assertIn("reserved exclusively for the door", plan["assumptions"]["scope_rule"])

        self.assertEqual(plan["purchase_requirements"], [])
        self.assertEqual(plan["purchase_summary"]["planning_quantity_bf"], 0)
        self.assertEqual(
            plan["purchase_summary"]["status"],
            "NO DOOR LUMBER PURCHASE RELEASED",
        )
        for gate in [
            "CHK-RS-01",
            "CHK-ST-01",
            "CHK-ST-02",
            "CHK-SM-01",
            "CHK-FP-01",
            "CHK-P-01",
            "CHK-LAM-01",
            "CHK-SEAM-01",
        ]:
            self.assertIn(gate, plan["purchase_summary"]["conditional_credit"])

        allocations = {row["part"]: row for row in plan["component_allocations"]}
        self.assertEqual(
            set(allocations),
            {
                "D-101A",
                "D-101B",
                "D-101C",
                "D-101M",
                "D-101D",
                "D-101E",
                "D-101F",
                "D-101G",
                "D-101H",
                "D-101J",
                "D-101N",
                "D-101K",
                "D-101L",
            },
        )
        for part_id, allocation in allocations.items():
            with self.subTest(part_id=part_id):
                self.assertNotEqual(allocation["stock"], "NEW")
                self.assertIn("CONDITIONAL", allocation["status"])

    def test_shopping_source_contains_layer_and_release_controls(self):
        source_lower = self.source.lower()
        for required in [
            "rev. g",
            "ls-05",
            "24 x 81-inch installed jamb",
            "23-3/4 x 80-1/2-inch finished fitted slab",
            "3/8-inch bottom gap",
            "0 bf - no purchase released",
            "approximately 71.52 current-envelope board feet",
            "stock-g is confirmed s4s at 15/16 x 4-1/2 x 75 inches",
            "thickness exceeds the 5/8-inch",
            "reserve all a-o stock exclusively for the door",
            "stock-m",
            "stock-n/o",
            "5/16 show face + 7/8 core + 5/16 back face",
            "1/4 + 7/8 + 1/4 = 1-3/8 inches",
            "no-resaw rule",
            "32 oz minimum",
            "3/4-inch-long foam panel spacers",
            "dado stack for supported through-rail grooves only",
            "physical sample controls machining",
            "chk-lam-01",
            "chk-fp-01",
            "chk-seam-01",
            "separate controlled two-face moulding order",
        ]:
            self.assertIn(required, source_lower)

        for stale in [
            "26 board feet",
            "complete frame package",
            "heavy 6/4",
            "otherwise use 8/4",
            "1-1/2 x 4-3/4 x 83 inches",
        ]:
            self.assertNotIn(stale, source_lower)

    def test_door_shopping_list_excludes_moulding_purchase_rows(self):
        self.assertNotIn("| Moulding stock |", self.source)
        self.assertNotIn("| 7 boards | S4S", self.source)
        self.assertNotIn("| 2 boards | S4S", self.source)
        self.assertIn("Door slab only", self.source)
        self.assertIn(
            "no A-O stock may be reassigned to moulding",
            self.source,
        )

    def test_general_buy_list_contains_separate_two_face_moulding_order(self):
        by_item = {row["Item"]: row for row in self.buy_rows}
        casing = by_item["Two-face casing and one stop set"]
        backband = by_item["Two-face backband and optional square-head caps"]
        self.assertEqual(casing["Quantity"], "7 boards")
        self.assertIn("4/4", casing["Specification"])
        self.assertEqual(backband["Quantity"], "2 boards")
        self.assertIn("6/4", backband["Specification"])
        self.assertIn("no plinth", backband["Substitution constraints"].lower())


if __name__ == "__main__":
    unittest.main()
