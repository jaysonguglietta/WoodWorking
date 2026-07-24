import csv, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class DominoTests(unittest.TestCase):
    def test_joint_families(self):
        with (ROOT/"project/domino-setup-register.csv").open() as handle:
            rows=list(csv.DictReader(handle))
        self.assertEqual(len(rows),12)
        self.assertTrue(all("first tight" in r["Mortise-width setting"] for r in rows))
