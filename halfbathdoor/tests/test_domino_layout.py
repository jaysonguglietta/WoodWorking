import unittest

from scripts.validate_domino_layout import (
    FRAME_JOINT_PARTS,
    MUNTIN_JOINTS,
    load_inputs,
    parse_centers,
    parse_measurement,
    validate,
)


class DominoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec, cls.rows = load_inputs()
        cls.by_id = {row["Joint ID"]: row for row in cls.rows}
        cls.metrics = validate(cls.spec, cls.rows)

    def test_register_centers_equal_governing_specification(self):
        domino = self.spec["domino"]
        for joint_id, part in FRAME_JOINT_PARTS.items():
            row = self.by_id[joint_id]
            with self.subTest(joint_id=joint_id, member="rail"):
                self.assertEqual(
                    parse_centers(
                        row["Tenon centerline Part A from reference edge"]
                    ),
                    domino["frame_centers_from_rail_top_in"][part],
                )
            with self.subTest(joint_id=joint_id, member="stile"):
                self.assertEqual(
                    parse_centers(
                        row["Tenon centerline Part B from reference edge"]
                    ),
                    domino["stile_centers_from_slab_top_in"][part],
                )

        for joint_id in MUNTIN_JOINTS:
            row = self.by_id[joint_id]
            with self.subTest(joint_id=joint_id, member="muntin"):
                self.assertEqual(
                    parse_centers(
                        row["Tenon centerline Part A from reference edge"]
                    ),
                    domino["muntin_centers_in"][
                        "D-101G from left reference edge"
                    ],
                )
            with self.subTest(joint_id=joint_id, member="mating rail"):
                self.assertEqual(
                    parse_centers(
                        row["Tenon centerline Part B from reference edge"]
                    ),
                    domino["muntin_centers_in"][
                        "D-101E and D-101F from hinge-side shoulder"
                    ],
                )

    def test_stile_centers_independently_follow_the_cumulative_stack(self):
        frame = self.spec["frame"]
        domino = self.spec["domino"]
        rail_ids = ("D-101C", "D-101M", "D-101D", "D-101E", "D-101F")
        opening_ids = (
            "P-01 upper",
            "P-02 center",
            "P-03 lower-center",
            "P-04 bottom",
        )
        cursor = 0.0
        rail_tops = {}
        opening_intervals = []
        for index, rail_id in enumerate(rail_ids):
            rail_tops[rail_id] = cursor
            cursor += frame["rail_widths"][rail_id]
            if index < len(opening_ids):
                opening_start = cursor
                cursor += frame["vertical_openings"][opening_ids[index]]
                opening_intervals.append((opening_start, cursor))
        self.assertAlmostEqual(cursor, self.spec["slab"]["finished_height"])
        self.assertEqual(
            opening_intervals,
            [(4.0, 18.25), (22.25, 37.0), (44.0, 53.5), (57.5, 68.5)],
        )
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
        for rail_id in rail_ids:
            expected = [
                rail_tops[rail_id] + center
                for center in domino["frame_centers_from_rail_top_in"][rail_id]
            ]
            with self.subTest(rail_id=rail_id):
                self.assertEqual(
                    domino["stile_centers_from_slab_top_in"][rail_id],
                    expected,
                )

    def test_every_registered_setup_uses_valid_presets_on_both_members(self):
        domino = self.spec["domino"]
        for row in self.rows:
            with self.subTest(joint_id=row["Joint ID"]):
                cutter = parse_measurement(row["Cutter diameter"], "mm")
                plunge_a = parse_measurement(row["Plunge depth Part A"], "mm")
                plunge_b = parse_measurement(row["Plunge depth Part B"], "mm")
                self.assertIn(cutter, domino["cutters_mm"])
                self.assertIn(plunge_a, domino["plunge_presets_mm"])
                self.assertIn(plunge_b, domino["plunge_presets_mm"])
                self.assertLessEqual(plunge_a, domino["maximum_plunge_mm"])
                self.assertLessEqual(plunge_b, domino["maximum_plunge_mm"])
                self.assertAlmostEqual(
                    parse_measurement(row["Fence height"], "mm"),
                    domino["fence_height_mm"],
                )
                self.assertAlmostEqual(
                    parse_measurement(row["Fence angle"], "deg"),
                    domino["fence_angle_degrees"],
                )

    def test_worst_case_frame_rail_webs_remain_positive(self):
        limits = self.spec["fabrication_tolerances"]
        self.assertGreaterEqual(
            self.metrics["minimum_frame_groove_web"],
            limits["frame_medium_mortise_web_to_panel_groove_min"],
        )
        self.assertGreater(self.metrics["minimum_frame_inter_mortise_web"], 0)
        self.assertGreater(self.metrics["minimum_face_web"], 0)

    def test_worst_case_muntin_and_mating_rail_webs_meet_limits(self):
        limits = self.spec["fabrication_tolerances"]
        self.assertGreaterEqual(
            self.metrics["minimum_muntin_groove_web"],
            limits["muntin_tight_mortise_web_to_side_groove_min"],
        )
        self.assertGreaterEqual(
            self.metrics["muntin_inter_mortise_web"],
            limits["muntin_tight_inter_mortise_web_min"],
        )
        self.assertGreaterEqual(
            self.metrics["rail_inter_mortise_web"],
            limits["muntin_rail_inter_mortise_web_min"],
        )

    def test_j06_register_carries_numeric_lock_clearance_gate(self):
        required = self.spec["hardware"]["lock_to_joinery_clear_wood_min"]
        note = self.by_id["J-06"]["Notes"]
        numeric_tokens = [
            float(token)
            for token in note.replace(";", " ").split()
            if token.replace(".", "", 1).isdigit()
        ]
        self.assertIn(required, numeric_tokens)


if __name__ == "__main__":
    unittest.main()
