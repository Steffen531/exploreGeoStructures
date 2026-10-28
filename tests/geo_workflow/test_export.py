import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from .common import feature
from exporter import export_result


class ExportTests(unittest.TestCase):
    def test_all_formats_are_written_and_parseable(self):
        result = {
            "workflow_id": "export-test",
            "complete_solutions": [
                {
                    "assignments": {
                        "walk": feature(
                            "walk",
                            {
                                "type": "LineString",
                                "coordinates": [[10, 53], [10.1, 53.1]],
                            },
                        )
                    },
                    "score": 1,
                    "soft_violations": [],
                }
            ],
            "partial_solutions": [],
            "rejections": {},
            "warnings": [],
            "explored": 1,
        }
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            export_result(result, output)
            geojson = json.loads(
                (output / "ergebnis.geojson").read_text(encoding="utf-8")
            )
            self.assertEqual(1, len(geojson["features"]))
            ET.parse(output / "ergebnis.kml")
            ET.parse(output / "ergebnis.gpx")
            summary = json.loads(
                (output / "zusammenfassung.json").read_text(encoding="utf-8")
            )
            self.assertEqual(1, summary["complete_solution_count"])


if __name__ == "__main__":
    unittest.main()
