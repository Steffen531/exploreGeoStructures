import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from .common import ROOT


def load_script(name, relative_path):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.foot = load_script(
            "foot_adapter", ".opencode/skills/fussweg/reference/fussweg_suche.py"
        )
        cls.busy = load_script(
            "busy_adapter",
            ".opencode/skills/belebteOrte/reference/belebte_orte_suche.py",
        )
        cls.authority = load_script(
            "authority_adapter",
            ".opencode/skills/behoerdenetc/reference/behoerden_suche.py",
        )
        cls.transit = load_script(
            "transit_adapter",
            ".opencode/skills/oepnvrouten/reference/oepnvrouten_suche.py",
        )

    def test_foot_adapter_generates_normalized_candidate(self):
        way = {
            "type": "way",
            "id": 1,
            "nodes": [1, 2],
            "tags": {"highway": "footway"},
            "geometry": [{"lat": 53.0, "lon": 10.0}, {"lat": 53.0, "lon": 10.01}],
        }
        candidates, rejected = self.foot.find_candidates([way], 600, 800, 0.95, 50)
        self.assertEqual([], rejected)
        with tempfile.TemporaryDirectory() as directory:
            self.foot.export_candidates(candidates, directory)
            data = json.loads(
                (Path(directory) / "kandidaten.geojson").read_text(encoding="utf-8")
            )
            self.assertEqual("path", data["features"][0]["properties"]["entity_type"])
            self.assertTrue((Path(directory) / "status.json").exists())

    def test_busy_adapter_marks_proxy_as_estimated(self):
        elements = [
            {
                "id": 1,
                "lat": 53.0,
                "lon": 10.0,
                "tags": {"amenity": "cafe", "name": "A"},
            },
            {
                "id": 2,
                "lat": 53.0001,
                "lon": 10.0001,
                "tags": {"shop": "mall", "name": "B"},
            },
        ]
        clusters = self.busy.merge_and_deduplicate(elements, None, None, None)
        features = self.busy.normalized_features(clusters, "2026-12-14T12:00:00+01:00")
        self.assertEqual(
            "estimated", features[0]["properties"]["temporal"]["precision"]
        )
        self.assertIn("osm_poi_density", features[0]["properties"]["score_components"])

    def test_authority_adapter_preserves_category(self):
        elements = [
            {
                "type": "node",
                "id": 7,
                "lat": 53,
                "lon": 10,
                "tags": {"amenity": "police", "name": "Polizei"},
            }
        ]
        merged = self.authority.merge_and_deduplicate(elements, None, None)
        features = self.authority.normalized_features(merged)
        self.assertEqual("police", features[0]["properties"]["category"])

    def test_gtfs_duration_and_arrival_filters_use_actual_departure(self):
        connections = [
            {
                "zeit": 720,
                "abschnitte": [{"abfahrt": "10:00", "ankunft": "12:00", "walk": False}],
            }
        ]
        filtered = self.transit._filter_gtfs_connections(
            connections,
            115,
            125,
            {"start": "11:55", "end": "12:05"},
            {"start": "09:55", "end": "10:05"},
        )
        self.assertEqual(1, len(filtered))
        self.assertEqual(120, filtered[0]["duration"])


if __name__ == "__main__":
    unittest.main()
