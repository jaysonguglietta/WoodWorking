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
