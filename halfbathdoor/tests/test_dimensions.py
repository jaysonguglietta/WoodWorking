import json, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class DimensionTests(unittest.TestCase):
    def setUp(self): self.s=json.loads((ROOT/"project/specification.yaml").read_text())
    def test_width(self): self.assertEqual(2*self.s["frame"]["stile_width"]+self.s["frame"]["rail_shoulder_length"],24)
    def test_height(self): self.assertEqual(sum(self.s["frame"]["rail_widths"].values())+sum(self.s["frame"]["vertical_openings"].values()),79)

