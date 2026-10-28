import unittest

from .common import ROOT, feature
from capability_registry import CapabilityRegistry
from planner import plan_node_order, solve, validate_workflow


class PlannerTests(unittest.TestCase):
    def setUp(self):
        self.registry = CapabilityRegistry(ROOT / ".opencode" / "skills").load()
        self.workflow = {
            "workflow_id": "offline",
            "nodes": [
                {
                    "id": "first",
                    "producer_skill": "geo-workflow",
                    "capability": "estimate_ride_hailing",
                    "parameters": {"start": {}, "end": {}},
                    "entity_types": ["ride_hailing_route"],
                },
                {
                    "id": "second",
                    "producer_skill": "geo-workflow",
                    "capability": "estimate_ride_hailing",
                    "parameters": {"start": {}, "end": {}},
                    "entity_types": ["ride_hailing_route"],
                    "depends_on": ["first"],
                },
            ],
            "constraints": [
                {
                    "type": "sequence_continuity",
                    "from": "first",
                    "to": "second",
                    "hard": True,
                    "parameters": {"max_distance_m": 100},
                }
            ],
            "limits": {
                "max_candidates_per_node": 10,
                "max_combinations": 100,
                "max_runtime_seconds": 5,
            },
        }

    def test_validation_and_order(self):
        validate_workflow(self.workflow, self.registry)
        self.assertEqual(["first", "second"], plan_node_order(self.workflow))

    def test_cycle_is_rejected(self):
        self.workflow["nodes"][0]["depends_on"] = ["second"]
        with self.assertRaisesRegex(ValueError, "Zyklische"):
            plan_node_order(self.workflow)

    def test_backtracking_rejects_disconnected_pair(self):
        first = feature(
            "a",
            {"type": "LineString", "coordinates": [[10, 53], [10.01, 53]]},
            entity_type="ride_hailing_route",
            end={"lat": 53, "lon": 10.01},
        )
        close = feature(
            "b",
            {"type": "LineString", "coordinates": [[10.0102, 53], [10.02, 53]]},
            entity_type="ride_hailing_route",
            start={"lat": 53, "lon": 10.0102},
        )
        far = feature(
            "c",
            {"type": "LineString", "coordinates": [[11, 54], [11.1, 54]]},
            entity_type="ride_hailing_route",
            start={"lat": 54, "lon": 11},
            score=2,
        )
        result = solve(self.workflow, {"first": [first], "second": [far, close]})
        self.assertEqual(1, len(result["complete_solutions"]))
        selected = result["complete_solutions"][0]["assignments"]["second"]
        self.assertEqual("b", selected["properties"]["candidate_id"])

    def test_unsatisfiable_workflow_returns_valid_prefix(self):
        first = feature(
            "a",
            {"type": "LineString", "coordinates": [[10, 53], [10.01, 53]]},
            entity_type="ride_hailing_route",
            end={"lat": 53, "lon": 10.01},
        )
        far = feature(
            "c",
            {"type": "LineString", "coordinates": [[11, 54], [11.1, 54]]},
            entity_type="ride_hailing_route",
            start={"lat": 54, "lon": 11},
        )
        result = solve(self.workflow, {"first": [first], "second": [far]})
        self.assertFalse(result["complete_solutions"])
        self.assertEqual(["first"], result["partial_solutions"][0]["assigned_nodes"])
        self.assertEqual(["second"], result["partial_solutions"][0]["missing_nodes"])

    def test_selection_all_checks_every_avoidance_candidate(self):
        workflow = {
            "workflow_id": "avoid-all",
            "nodes": [
                {
                    "id": "walk",
                    "producer_skill": "geo-workflow",
                    "capability": "estimate_ride_hailing",
                    "parameters": {"start": {}, "end": {}},
                    "entity_types": ["ride_hailing_route"],
                },
                {
                    "id": "excluded",
                    "producer_skill": "geo-workflow",
                    "capability": "estimate_ride_hailing",
                    "parameters": {"start": {}, "end": {}},
                    "entity_types": ["ride_hailing_route"],
                    "selection": "all",
                },
            ],
            "constraints": [
                {
                    "type": "avoids",
                    "from": "walk",
                    "to": "excluded",
                    "hard": True,
                    "parameters": {"min_distance_m": 100},
                }
            ],
        }
        walk = feature(
            "walk",
            {"type": "LineString", "coordinates": [[10, 53], [10.01, 53]]},
            entity_type="ride_hailing_route",
        )
        far = feature(
            "far",
            {"type": "Point", "coordinates": [11, 54]},
            entity_type="ride_hailing_route",
        )
        near = feature(
            "near",
            {"type": "Point", "coordinates": [10.005, 53]},
            entity_type="ride_hailing_route",
        )
        result = solve(workflow, {"walk": [walk], "excluded": [far, near]})
        self.assertFalse(result["complete_solutions"])


if __name__ == "__main__":
    unittest.main()
