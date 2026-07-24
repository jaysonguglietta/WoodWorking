import csv, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class CutListTests(unittest.TestCase):
    def test_component_count(self):
        with (ROOT/"build/reports/cut-list.csv").open() as handle:
            rows=list(csv.DictReader(handle))
        self.assertEqual(len(rows),13)
        self.assertEqual(sum(1 for r in rows if "panel" in r["Part name"].lower()),5)
