import json
import unittest
from pathlib import Path

from .common import ROOT


class SchemaTests(unittest.TestCase):
    def test_all_schemas_are_json_and_have_required_contract(self):
        schema_dir = ROOT / ".opencode" / "skills" / "geo-workflow" / "schemas"
        paths = sorted(schema_dir.glob("*.schema.json"))
        self.assertEqual(5, len(paths))
        for path in paths:
            schema = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual("object", schema["type"], path.name)
            self.assertIn("required", schema, path.name)

    def test_capability_manifests_are_valid_json(self):
        manifests = sorted((ROOT / ".opencode" / "skills").glob("*/capabilities.json"))
        self.assertGreaterEqual(len(manifests), 1)
        for path in manifests:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertTrue(data["skill_id"])
            self.assertIsInstance(data["capabilities"], list)


if __name__ == "__main__":
    unittest.main()
