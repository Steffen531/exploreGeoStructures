import unittest

from .common import feature
from constraint_engine import distance_metres, evaluate_constraint
from shapely.geometry import Point


class SpatialConstraintTests(unittest.TestCase):
    def setUp(self):
        self.walk = feature(
            "walk",
            {"type": "LineString", "coordinates": [[10.0, 53.0], [10.01, 53.0]]},
            start={"lat": 53.0, "lon": 10.0},
            end={"lat": 53.0, "lon": 10.01},
        )
        self.stop = feature(
            "stop",
            {"type": "Point", "coordinates": [10.0105, 53.0]},
            entity_type="stop",
            start={"lat": 53.0, "lon": 10.0105},
            end={"lat": 53.0, "lon": 10.0105},
        )

    def test_metric_distance(self):
        distance = distance_metres(Point(10.0, 53.0), Point(10.01, 53.0))
        self.assertGreater(distance, 600)
        self.assertLess(distance, 700)

    def test_end_near_uses_oriented_endpoint(self):
        result = evaluate_constraint(
            {
                "type": "ends_near",
                "from": "walk",
                "to": "stop",
                "hard": True,
                "parameters": {"max_distance_m": 50},
            },
            {"walk": self.walk, "stop": self.stop},
        )
        self.assertTrue(result.passed, result.reason)

    def test_avoids_checks_complete_line(self):
        authority = feature(
            "authority",
            {"type": "Point", "coordinates": [10.005, 53.0]},
            entity_type="authority_place",
        )
        result = evaluate_constraint(
            {
                "type": "avoids",
                "from": "walk",
                "to": "authority",
                "hard": True,
                "parameters": {"min_distance_m": 100},
            },
            {"walk": self.walk, "authority": authority},
        )
        self.assertFalse(result.passed)


if __name__ == "__main__":
    unittest.main()
