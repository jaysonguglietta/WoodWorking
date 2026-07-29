import csv
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


class CutListTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = json.loads(
            (ROOT / "project/specification.yaml").read_text(encoding="utf-8")
        )
        cls.door_rows = read_csv(ROOT / "build/reports/cut-list.csv")
        cls.moulding_rows = read_csv(ROOT / "build/reports/moulding-cut-list.csv")

    def test_door_cut_list_has_unique_component_and_layer_rows(self):
        expected_ids = {component["id"] for component in self.spec["components"]}
        actual_ids = [row["Part identifier"] for row in self.door_rows]
        self.assertEqual(len(actual_ids), len(set(actual_ids)))
        self.assertTrue(expected_ids.issubset(actual_ids))
        frame_ids = {
            component["id"]
            for component in self.spec["components"]
            if "panel" not in component["name"].lower()
        }
        expected_layers = {
            f"{part_id}-{suffix}"
            for part_id in frame_ids
            for suffix in ("CORE", "SF", "BF")
        }
        self.assertEqual(set(actual_ids) - expected_ids, expected_layers)

    def test_every_finished_door_dimension_equals_the_specification(self):
        by_id = {row["Part identifier"]: row for row in self.door_rows}
        for component in self.spec["components"]:
            row = by_id[component["id"]]
            with self.subTest(part_id=component["id"]):
                self.assertEqual(row["Part name"], component["name"])
                self.assertEqual(int(row["Quantity"]), component["qty"])
                self.assertAlmostEqual(
                    float(row["Finished thickness"]), component["t"]
                )
                self.assertAlmostEqual(
                    float(row["Finished width"]), component["w"]
                )
                self.assertAlmostEqual(
                    float(row["Finished length"]), component["l"]
                )

    def test_every_rough_door_dimension_uses_its_governing_allowance(self):
        milling = self.spec["milling"]
        by_id = {row["Part identifier"]: row for row in self.door_rows}
        for component in self.spec["components"]:
            name = component["name"].lower()
            is_panel = "panel" in name
            if is_panel:
                expected_thickness = milling["panel_rough_thickness"]
                expected_width = (
                    component["w"] + milling["panel_rough_width_allowance"]
                )
                expected_length = (
                    component["l"] + milling["panel_rough_length_allowance"]
                )
            else:
                expected_thickness = milling["frame_rough_thickness"]
                expected_width = (
                    component["w"]
                    + (
                        milling["stile_glue_blank_width_allowance"]
                        if "stile" in name
                        else milling["frame_rough_width_allowance"]
                    )
                )
                if "stile" in name:
                    expected_length = milling["stile_face_length"]
                elif "muntin" in name:
                    length_allowance = milling[
                        "muntin_rough_length_allowance_total"
                    ]
                    expected_length = component["l"] + length_allowance
                else:
                    length_allowance = milling[
                        "rail_rough_length_allowance_total"
                    ]
                    expected_length = component["l"] + length_allowance

            row = by_id[component["id"]]
            with self.subTest(part_id=component["id"]):
                self.assertAlmostEqual(
                    float(row["Rough thickness"]), expected_thickness
                )
                self.assertAlmostEqual(float(row["Rough width"]), expected_width)
                self.assertAlmostEqual(float(row["Rough length"]), expected_length)

    def test_each_frame_component_has_balanced_core_and_face_rows(self):
        by_id = {row["Part identifier"]: row for row in self.door_rows}
        construction = self.spec["frame"]["construction"]
        frame_components = [
            component
            for component in self.spec["components"]
            if "panel" not in component["name"].lower()
        ]
        for component in frame_components:
            with self.subTest(part_id=component["id"]):
                core = by_id[f"{component['id']}-CORE"]
                show = by_id[f"{component['id']}-SF"]
                back = by_id[f"{component['id']}-BF"]
                self.assertAlmostEqual(
                    float(core["Rough thickness"]),
                    construction["core_preglue_thickness"],
                )
                self.assertAlmostEqual(
                    float(show["Rough thickness"]),
                    construction["show_face_preglue_thickness"],
                )
                self.assertAlmostEqual(
                    float(back["Rough thickness"]),
                    construction["back_face_preglue_thickness"],
                )
                self.assertIn("LS-05", core["Field-fit status"])

    def test_moulding_finished_sections_equal_the_specification(self):
        trim = self.spec["trim"]
        by_id = {row["Part identifier"]: row for row in self.moulding_rows}
        self.assertEqual(
            set(by_id),
            {
                "M-201A/B",
                "M-201C",
                "M-202A/B",
                "M-202C",
                "M-203A-C",
                "M-204",
                "M-205A/B",
            },
        )
        expected_sections = {
            "M-201A/B": trim["side_casing_finished"],
            "M-201C": trim["head_casing_finished"],
            "M-202A/B": trim["backband_finished"],
            "M-202C": trim["backband_finished"],
            "M-203A-C": trim["stop_finished"],
            "M-204": {
                "t": trim["optional_head_cap"]["t"],
                "w": trim["optional_head_cap"]["depth"],
            },
        }
        for part_id, section in expected_sections.items():
            row = by_id[part_id]
            with self.subTest(part_id=part_id):
                self.assertAlmostEqual(
                    float(row["Finished thickness"]), section["t"]
                )
                self.assertAlmostEqual(float(row["Finished width"]), section["w"])
                self.assertGreater(
                    float(row["Rough thickness"]),
                    float(row["Finished thickness"]),
                )
                self.assertGreater(
                    float(row["Rough width"]), float(row["Finished width"])
                )
        self.assertAlmostEqual(
            float(by_id["M-205A/B"]["Finished thickness"]),
            trim["plinth"]["nominal_thickness"],
        )
        self.assertEqual(by_id["M-203A-C"]["Quantity"], "3 total per opening")

    def test_moulding_rough_lengths_preserve_scheme_specific_formulas(self):
        by_id = {row["Part identifier"]: row for row in self.moulding_rows}
        allowance = self.spec["trim"]["rough_length_allowance_total"]
        allowance_text = f"{allowance:g}"
        self.assertEqual(
            by_id["M-202A/B"]["Rough length"],
            (
                "mitered: fitted side-casing outer long + B + "
                f"{allowance_text}; square: fitted side-casing length + C + "
                f"{allowance_text}"
            ),
        )
        self.assertEqual(
            by_id["M-202C"]["Rough length"],
            (
                "fitted head-casing outside width + 2B + "
                f"{allowance_text}"
            ),
        )
        self.assertEqual(
            by_id["M-201C"]["Rough length"],
            f"W + 2R + 2C + {allowance_text}",
        )
        self.assertEqual(
            by_id["M-204"]["Rough length"],
            f"actual fitted head-backband outside width + 2P + {allowance_text}",
        )
        self.assertEqual(
            by_id["M-202A/B"]["Field-fit allowance"],
            (
                f"{allowance_text} inches beyond scheme-specific finished target"
            ),
        )


if __name__ == "__main__":
    unittest.main()
