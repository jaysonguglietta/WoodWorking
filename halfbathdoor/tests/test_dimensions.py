import json
import unittest
from pathlib import Path

from scripts.validate_dimensions import validate


ROOT = Path(__file__).resolve().parents[1]


class DimensionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = json.loads(
            (ROOT / "project/specification.yaml").read_text(encoding="utf-8")
        )
        cls.results = validate(cls.spec)
        cls.components = {
            component["id"]: component for component in cls.spec["components"]
        }

    def test_complete_door_dimension_stack(self):
        opening = self.spec["opening"]
        slab = self.spec["slab"]
        milling = self.spec["milling"]
        self.assertAlmostEqual(
            self.results["calculated_width"], slab["finished_width"]
        )
        self.assertAlmostEqual(
            self.results["calculated_height"], slab["finished_height"]
        )
        self.assertEqual(
            set(slab["dimensional_states"]),
            {
                "confirmed_jamb_opening",
                "cured_surfaced_prefit_assembly",
                "final_layout_rectangle",
                "finished_fitted_slab",
            },
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
        self.assertAlmostEqual(
            milling["prefit_assembly_width"],
            slab["finished_width"]
            + 2 * slab["manufacturing_trim_reserve_per_edge"],
        )
        self.assertAlmostEqual(
            milling["prefit_assembly_height"],
            slab["finished_height"]
            + 2 * slab["manufacturing_trim_reserve_per_edge"],
        )

    def test_rev_g_fitted_geometry_and_ls05_layer_lengths(self):
        slab = self.spec["slab"]
        frame = self.spec["frame"]
        milling = self.spec["milling"]
        self.assertAlmostEqual(slab["finished_width"], 23.75)
        self.assertAlmostEqual(slab["finished_height"], 80.5)
        self.assertEqual(
            frame["vertical_openings"],
            {
                "P-01 upper": 14.25,
                "P-02 center": 14.75,
                "P-03 lower-center": 9.5,
                "P-04 bottom": 11.0,
            },
        )
        self.assertAlmostEqual(sum(frame["rail_widths"].values()), 31.0)
        self.assertAlmostEqual(sum(frame["vertical_openings"].values()), 49.5)
        for part_id in ("D-101A", "D-101B"):
            self.assertAlmostEqual(self.components[part_id]["l"], 80.5)
        self.assertAlmostEqual(milling["stile_core_length"], 81.0)
        self.assertAlmostEqual(milling["stile_face_length"], 81.125)
        self.assertAlmostEqual(frame["stile_width"], 4.25)
        self.assertAlmostEqual(frame["rail_shoulder_length"], 15.25)
        self.assertAlmostEqual(frame["bottom_opening_each"], 6.125)
        self.assertAlmostEqual(milling["rail_rough_length"], 16.25)
        self.assertAlmostEqual(
            milling["stile_rough_length_allowance_total"], 0.5
        )
        self.assertGreater(
            milling["stile_face_length"], milling["stile_core_length"]
        )
        self.assertAlmostEqual(self.components["D-101H"]["l"], 15.0625)
        self.assertAlmostEqual(self.components["D-101J"]["l"], 15.5625)

    def test_confirmed_jamb_reveals_and_bottom_gap_are_explicit(self):
        opening = self.spec["opening"]
        slab = self.spec["slab"]
        self.assertAlmostEqual(opening["clear_width"], 24.0)
        self.assertAlmostEqual(opening["clear_height"], 81.0)
        self.assertAlmostEqual(opening["hinge_side_reveal"], 0.125)
        self.assertAlmostEqual(opening["lock_side_reveal"], 0.125)
        self.assertAlmostEqual(opening["head_reveal"], 0.125)
        self.assertAlmostEqual(opening["bottom_gap"], 0.375)
        self.assertAlmostEqual(self.results["derived_fitted_width"], 23.75)
        self.assertAlmostEqual(self.results["derived_fitted_height"], 80.5)
        self.assertEqual(slab["finished_size_tolerance"]["width_plus"], 0)
        self.assertEqual(slab["finished_size_tolerance"]["height_plus"], 0)

    def test_all_five_panel_width_formulas(self):
        frame = self.spec["frame"]
        panels = self.spec["panels"]
        inputs = {
            "D-101H": (
                frame["rail_shoulder_length"],
                panels["full_width_clearance_across_grain_total"],
            ),
            "D-101J": (
                frame["rail_shoulder_length"],
                panels["full_width_clearance_across_grain_total"],
            ),
            "D-101N": (
                frame["rail_shoulder_length"],
                panels["full_width_clearance_across_grain_total"],
            ),
            "D-101K": (
                frame["bottom_opening_each"],
                panels["small_width_clearance_across_grain_total"],
            ),
            "D-101L": (
                frame["bottom_opening_each"],
                panels["small_width_clearance_across_grain_total"],
            ),
        }
        for part_id, (opening, clearance) in inputs.items():
            with self.subTest(part_id=part_id):
                expected = opening + 2 * panels["tongue_depth"] - clearance
                self.assertAlmostEqual(self.components[part_id]["w"], expected)

    def test_all_five_panel_length_formulas(self):
        frame = self.spec["frame"]
        panels = self.spec["panels"]
        openings = {
            "D-101H": frame["vertical_openings"]["P-01 upper"],
            "D-101J": frame["vertical_openings"]["P-02 center"],
            "D-101N": frame["vertical_openings"]["P-03 lower-center"],
            "D-101K": frame["vertical_openings"]["P-04 bottom"],
            "D-101L": frame["vertical_openings"]["P-04 bottom"],
        }
        for part_id, opening in openings.items():
            with self.subTest(part_id=part_id):
                expected = (
                    opening
                    + 2 * panels["tongue_depth"]
                    - panels["clearance_parallel_to_grain_total"]
                )
                self.assertAlmostEqual(self.components[part_id]["l"], expected)
                self.assertAlmostEqual(
                    self.components[part_id]["t"], panels["field_thickness"]
                )

    def test_seven_sixteenths_tongue_clearance_envelope(self):
        panels = self.spec["panels"]
        groove = self.spec["groove"]
        depth_tolerance = self.spec["fabrication_tolerances"]["groove_depth"]
        width_tolerance = self.spec["fabrication_tolerances"]["groove_width"]
        self.assertAlmostEqual(panels["tongue_depth"], 7 / 16)
        self.assertAlmostEqual(panels["tongue_thickness"], 7 / 32)
        self.assertAlmostEqual(
            self.results["minimum_tongue_thickness"],
            panels["tongue_thickness"]
            - panels["tongue_thickness_tolerance_plus_minus"],
        )
        self.assertAlmostEqual(
            self.results["maximum_tongue_thickness"],
            panels["tongue_thickness"]
            + panels["tongue_thickness_tolerance_plus_minus"],
        )
        self.assertAlmostEqual(
            groove["depth"] - panels["tongue_depth"],
            panels["tongue_bottom_clearance_nominal"],
        )
        expected_worst_case = (
            depth_tolerance["target"]
            - depth_tolerance["minus"]
            - panels["tongue_depth"]
            - panels["tongue_depth_tolerance_plus_minus"]
        )
        self.assertAlmostEqual(
            self.results["minimum_bottom_clearance"], expected_worst_case
        )
        self.assertGreater(self.results["minimum_bottom_clearance"], 0)
        expected_side_clearance = (
            width_tolerance["target"]
            - width_tolerance["minus"]
            - self.results["maximum_tongue_thickness"]
        )
        self.assertAlmostEqual(
            self.results["minimum_tongue_side_clearance"],
            expected_side_clearance,
        )
        self.assertGreater(expected_side_clearance, 0)

    def test_bottom_openings_and_segmented_grooves_share_one_footprint(self):
        frame = self.spec["frame"]
        groove = self.spec["groove"]
        expected_each = (
            frame["rail_shoulder_length"] - frame["muntin_width"]
        ) / 2
        self.assertAlmostEqual(frame["bottom_opening_each"], expected_each)
        footprint = groove["muntin_footprint_from_hinge_side_rail_shoulder"]
        self.assertEqual(
            groove["segmented_rail_edges"],
            {
                "D-101E bottom": [
                    [0.0, footprint[0]],
                    [footprint[1], frame["rail_shoulder_length"]],
                ],
                "D-101F top": [
                    [0.0, footprint[0]],
                    [footprint[1], frame["rail_shoulder_length"]],
                ],
            },
        )


if __name__ == "__main__":
    unittest.main()
