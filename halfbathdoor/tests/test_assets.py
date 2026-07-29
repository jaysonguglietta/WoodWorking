import csv, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class AssetTests(unittest.TestCase):
    def test_registered_figures_exist(self):
        with (ROOT/"project/illustration-register.csv").open() as handle:
            rows=list(csv.DictReader(handle))
        self.assertGreaterEqual(len(rows),36)
        for r in rows:
            self.assertTrue((ROOT/"illustrations/technical"/f"{r['Slug']}.svg").exists())

    def test_moulding_guide_diagrams_exist_in_both_formats(self):
        diagram_dir=ROOT/"moulding-guide"/"illustrations"
        slugs=[
            "01-installed-anatomy","02-field-measurements","03-profile-register",
            "04-length-formulas","05-stock-milling","06-profile-machining",
            "07-jamb-wall-section","08-head-joint-options","09-stop-install",
            "10-side-casing-fit","11-head-casing-fit","12-backband-install",
            "13-cap-plinth","14-scribe-corners","15-fastener-map","16-finish-qc",
        ]
        for slug in slugs:
            for suffix in (".svg",".png"):
                asset=diagram_dir/f"{slug}{suffix}"
                self.assertTrue(asset.exists(), str(asset))
                self.assertGreater(asset.stat().st_size,100)

    def test_cabinetmaker_render_register_matches_both_formats(self):
        register=ROOT/"project"/"cabinetmakers-render-register.csv"
        with register.open(newline="",encoding="utf-8") as handle:
            rows=list(csv.DictReader(handle))
        expected={row["Slug"] for row in rows}
        self.assertEqual(len(rows),27)
        self.assertEqual(len(expected),27)
        render_dir=ROOT/"cabinetmakers-guide"/"renderings"
        clarity = {
            "03b-door-lamination-map",
            "03c-board-a-o-allocation-map",
            "03d-wide-rail-seam-map",
            "03e-datum-marking-map",
            "04b-panel-glue-map",
            "04c-spacer-placement-map",
            "07b-two-stage-glue-storyboard",
            "08b-post-cure-surfacing-map",
            "09d-prefit-finished-overlay",
        }
        self.assertEqual(
            {path.stem for path in render_dir.glob("*.svg")},
            expected | {"03b-door-lamination-map"},
        )
        self.assertEqual(
            {path.stem for path in render_dir.glob("*.png")},
            expected | clarity,
        )
        for slug in expected:
            self.assertGreater((render_dir/f"{slug}.svg").stat().st_size,5000)
            self.assertGreater((render_dir/f"{slug}.png").stat().st_size,10000)

    def test_cabinetmaker_guide_source_and_builder_exist(self):
        source=ROOT/"cabinetmakers-guide"/"DC-1916-001_Cabinetmakers_Builder_Guide.md"
        builder=ROOT/"scripts"/"build_cabinetmakers_guide.py"
        self.assertGreater(source.stat().st_size,1000)
        self.assertGreater(builder.stat().st_size,1000)
        source_text=source.read_text(encoding="utf-8").lower()
        for required in ["d-101a","df 500","m-201","backband","field release"]:
            self.assertIn(required,source_text)

    def test_project_plans_source_and_builder_exist(self):
        source=ROOT/"project-plans"/"DC-1916-001_Five_Panel_Door_Project_Plans.md"
        builder=ROOT/"scripts"/"build_project_plans_booklet.py"
        self.assertGreater(source.stat().st_size,1000)
        self.assertGreater(builder.stat().st_size,1000)
        source_text=source.read_text(encoding="utf-8").lower()
        for required in [
            "23-3/4 x 80-1/2 x 1-3/8",
            "no-resaw",
            "3/4-inch-long foam",
            "thickness x width x length",
        ]:
            self.assertIn(required,source_text)
