import json, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class SpecificationTests(unittest.TestCase):
    def test_project_identity(self):
        s=json.loads((ROOT/"project/specification.yaml").read_text())
        self.assertEqual(s["project"]["number"],"DC-1916-001")
        self.assertEqual(s["domino"]["model"],"Festool Domino DF 500")

