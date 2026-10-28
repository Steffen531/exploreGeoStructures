import unittest

from .common import feature
from constraint_engine import evaluate_constraint


class TemporalConstraintTests(unittest.TestCase):
    def setUp(self):
        self.first = feature(
            "first",
            {"type": "Point", "coordinates": [10, 53]},
            temporal_start="2026-12-14T10:00:00+01:00",
            temporal_end="2026-12-14T11:00:00+01:00",
            duration=60,
        )
        self.second = feature(
            "second",
            {"type": "Point", "coordinates": [10, 53]},
            temporal_start="2026-12-14T11:10:00+01:00",
            temporal_end="2026-12-14T12:00:00+01:00",
            duration=50,
        )

    def test_duration_window(self):
        result = evaluate_constraint(
            {
                "type": "duration_between",
                "from": "first",
                "hard": True,
                "parameters": {"min_minutes": 55, "max_minutes": 65},
            },
            {"first": self.first},
        )
        self.assertTrue(result.passed)

    def test_sequence_gap(self):
        result = evaluate_constraint(
            {
                "type": "sequence_time",
                "from": "first",
                "to": "second",
                "hard": True,
                "parameters": {"min_minutes": 5, "max_minutes": 15},
            },
            {"first": self.first, "second": self.second},
        )
        self.assertTrue(result.passed, result.reason)

    def test_naive_time_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_constraint(
                {
                    "type": "starts_between",
                    "from": "first",
                    "hard": True,
                    "parameters": {
                        "start": "2026-12-14T09:00:00",
                        "end": "2026-12-14T11:00:00+01:00",
                    },
                },
                {"first": self.first},
            )


if __name__ == "__main__":
    unittest.main()
