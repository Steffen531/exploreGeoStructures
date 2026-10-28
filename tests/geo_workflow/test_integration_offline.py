import unittest

from .common import feature
from planner import solve


REGION = {
    "name": "Fixture City",
    "bbox": [52.9, 9.9, 53.2, 10.3],
    "timezone": "Europe/Berlin",
}


def node(node_id, skill, capability, entity_type, depends_on=None):
    parameters = {"region": REGION}
    if skill == "oepnvrouten":
        parameters.update({"date": "2026-12-14", "start": "fixture", "end": "fixture"})
    elif skill == "belebteOrte":
        parameters["at"] = "2026-12-14T12:00:00+01:00"
    elif capability == "estimate_ride_hailing":
        parameters = {"start": {}, "end": {}}
    return {
        "id": node_id,
        "producer_skill": skill,
        "capability": capability,
        "parameters": parameters,
        "entity_types": [entity_type],
        "depends_on": depends_on or [],
    }


def point(candidate_id, lon, lat, entity_type, start, end, score=1):
    return feature(
        candidate_id,
        {"type": "Point", "coordinates": [lon, lat]},
        entity_type=entity_type,
        start={"lat": lat, "lon": lon},
        end={"lat": lat, "lon": lon},
        temporal_start=start,
        temporal_end=end,
        duration=0,
        score=score,
    )


def line(candidate_id, coordinates, entity_type, start, end, score=1):
    return feature(
        candidate_id,
        {"type": "LineString", "coordinates": coordinates},
        entity_type=entity_type,
        start={"lat": coordinates[0][1], "lon": coordinates[0][0]},
        end={"lat": coordinates[-1][1], "lon": coordinates[-1][0]},
        temporal_start=start,
        temporal_end=end,
        duration=(
            __import__("datetime").datetime.fromisoformat(end)
            - __import__("datetime").datetime.fromisoformat(start)
        ).total_seconds()
        / 60,
        score=score,
    )


class OfflineIntegrationTests(unittest.TestCase):
    def test_walk_transit_busy_place(self):
        workflow = {
            "workflow_id": "scenario-1",
            "nodes": [
                node("walk", "fussweg", "find_foot_paths", "path"),
                node(
                    "transit",
                    "oepnvrouten",
                    "find_transit_routes",
                    "transit_route",
                    ["walk"],
                ),
                node(
                    "busy", "belebteOrte", "find_busy_places", "busy_place", ["transit"]
                ),
            ],
            "constraints": [
                {
                    "type": "sequence_continuity",
                    "from": "walk",
                    "to": "transit",
                    "hard": True,
                    "parameters": {"max_distance_m": 100},
                },
                {
                    "type": "sequence_continuity",
                    "from": "transit",
                    "to": "busy",
                    "hard": True,
                    "parameters": {"max_distance_m": 300},
                },
                {
                    "type": "duration_between",
                    "from": "walk",
                    "hard": True,
                    "parameters": {"min_minutes": 18, "max_minutes": 22},
                },
                {
                    "type": "active_at",
                    "from": "busy",
                    "hard": True,
                    "parameters": {"at": "2026-12-14T12:00:00+01:00"},
                },
            ],
        }
        candidates = {
            "walk": [
                line(
                    "walk",
                    [[10, 53], [10.01, 53]],
                    "path",
                    "2026-12-14T09:35:00+01:00",
                    "2026-12-14T09:55:00+01:00",
                )
            ],
            "transit": [
                line(
                    "transit",
                    [[10.0102, 53], [10.1, 53.1]],
                    "transit_route",
                    "2026-12-14T10:00:00+01:00",
                    "2026-12-14T11:55:00+01:00",
                )
            ],
            "busy": [
                point(
                    "busy",
                    10.1002,
                    53.1,
                    "busy_place",
                    "2026-12-14T11:30:00+01:00",
                    "2026-12-14T12:30:00+01:00",
                )
            ],
        }
        self.assertEqual(1, len(solve(workflow, candidates)["complete_solutions"]))

    def test_busy_transit_walk_ride_transit_avoids_authority(self):
        ids = ["busy", "transit-1", "walk", "ride", "transit-2"]
        workflow = {
            "workflow_id": "scenario-2",
            "nodes": [
                node("busy", "belebteOrte", "find_busy_places", "busy_place"),
                node(
                    "transit-1",
                    "oepnvrouten",
                    "find_transit_routes",
                    "transit_route",
                    ["busy"],
                ),
                node("walk", "fussweg", "find_foot_paths", "path", ["transit-1"]),
                node(
                    "ride",
                    "geo-workflow",
                    "estimate_ride_hailing",
                    "ride_hailing_route",
                    ["walk"],
                ),
                node(
                    "transit-2",
                    "oepnvrouten",
                    "find_transit_routes",
                    "transit_route",
                    ["ride"],
                ),
                {
                    **node(
                        "authority",
                        "behoerdenetc",
                        "find_authorities",
                        "authority_place",
                    ),
                    "selection": "all",
                },
            ],
            "constraints": [
                *[
                    {
                        "type": "sequence_continuity",
                        "from": left,
                        "to": right,
                        "hard": True,
                        "parameters": {"max_distance_m": 120},
                    }
                    for left, right in zip(ids, ids[1:])
                ],
                {
                    "type": "avoids",
                    "from": "walk",
                    "to": "authority",
                    "hard": True,
                    "parameters": {"min_distance_m": 100},
                },
            ],
        }
        candidates = {
            "busy": [
                point(
                    "busy",
                    10.0,
                    53.0,
                    "busy_place",
                    "2026-12-14T09:00:00+01:00",
                    "2026-12-14T10:00:00+01:00",
                )
            ],
            "transit-1": [
                line(
                    "t1",
                    [[10.0, 53.0], [10.02, 53.0]],
                    "transit_route",
                    "2026-12-14T10:00:00+01:00",
                    "2026-12-14T10:30:00+01:00",
                )
            ],
            "walk": [
                line(
                    "walk",
                    [[10.0201, 53.0], [10.03, 53.0]],
                    "path",
                    "2026-12-14T10:30:00+01:00",
                    "2026-12-14T10:45:00+01:00",
                )
            ],
            "ride": [
                line(
                    "ride",
                    [[10.0301, 53.0], [10.05, 53.0]],
                    "ride_hailing_route",
                    "2026-12-14T10:45:00+01:00",
                    "2026-12-14T11:00:00+01:00",
                )
            ],
            "transit-2": [
                line(
                    "t2",
                    [[10.0501, 53.0], [10.1, 53.0]],
                    "transit_route",
                    "2026-12-14T11:05:00+01:00",
                    "2026-12-14T12:00:00+01:00",
                )
            ],
            "authority": [
                point("authority-1", 11.0, 54.0, "authority_place", None, None),
                point("authority-2", 11.1, 54.1, "authority_place", None, None),
            ],
        }
        self.assertEqual(1, len(solve(workflow, candidates)["complete_solutions"]))

    def test_transit_busy_mall_transit_walk_ride(self):
        workflow = {
            "workflow_id": "scenario-3",
            "nodes": [
                node(
                    "transit-1", "oepnvrouten", "find_transit_routes", "transit_route"
                ),
                node(
                    "busy",
                    "belebteOrte",
                    "find_busy_places",
                    "busy_place",
                    ["transit-1"],
                ),
                node(
                    "mall",
                    "mallsetc",
                    "find_urban_structures",
                    "urban_structure",
                    ["busy"],
                ),
                node(
                    "transit-2",
                    "oepnvrouten",
                    "find_transit_routes",
                    "transit_route",
                    ["mall"],
                ),
                node("walk", "fussweg", "find_foot_paths", "path", ["transit-2"]),
                node(
                    "ride",
                    "geo-workflow",
                    "estimate_ride_hailing",
                    "ride_hailing_route",
                    ["walk"],
                ),
            ],
            "constraints": [
                {
                    "type": "sequence_continuity",
                    "from": "transit-1",
                    "to": "busy",
                    "hard": True,
                    "parameters": {"max_distance_m": 200},
                },
                {
                    "type": "near",
                    "from": "busy",
                    "to": "mall",
                    "hard": True,
                    "parameters": {"max_distance_m": 100},
                },
                {
                    "type": "sequence_continuity",
                    "from": "mall",
                    "to": "transit-2",
                    "hard": True,
                    "parameters": {"max_distance_m": 200},
                },
                {
                    "type": "sequence_continuity",
                    "from": "transit-2",
                    "to": "walk",
                    "hard": True,
                    "parameters": {"max_distance_m": 120},
                },
                {
                    "type": "sequence_continuity",
                    "from": "walk",
                    "to": "ride",
                    "hard": True,
                    "parameters": {"max_distance_m": 120},
                },
            ],
        }
        candidates = {
            "transit-1": [
                line(
                    "t1",
                    [[10, 53], [10.02, 53]],
                    "transit_route",
                    "2026-12-14T09:00:00+01:00",
                    "2026-12-14T09:30:00+01:00",
                )
            ],
            "busy": [
                point(
                    "busy",
                    10.0201,
                    53,
                    "busy_place",
                    "2026-12-14T09:00:00+01:00",
                    "2026-12-14T10:30:00+01:00",
                )
            ],
            "mall": [point("mall", 10.0202, 53, "urban_structure", None, None)],
            "transit-2": [
                line(
                    "t2",
                    [[10.0203, 53], [10.04, 53]],
                    "transit_route",
                    "2026-12-14T10:30:00+01:00",
                    "2026-12-14T11:00:00+01:00",
                )
            ],
            "walk": [
                line(
                    "walk",
                    [[10.0401, 53], [10.05, 53]],
                    "path",
                    "2026-12-14T11:00:00+01:00",
                    "2026-12-14T11:15:00+01:00",
                )
            ],
            "ride": [
                line(
                    "ride",
                    [[10.0501, 53], [10.08, 53]],
                    "ride_hailing_route",
                    "2026-12-14T11:15:00+01:00",
                    "2026-12-14T11:30:00+01:00",
                )
            ],
        }
        self.assertEqual(1, len(solve(workflow, candidates)["complete_solutions"]))

    def test_incompatible_constraints_have_no_invented_solution(self):
        workflow = {
            "workflow_id": "scenario-4",
            "nodes": [
                node("walk", "fussweg", "find_foot_paths", "path"),
                node(
                    "target",
                    "mallsetc",
                    "find_urban_structures",
                    "urban_structure",
                    ["walk"],
                ),
            ],
            "constraints": [
                {
                    "type": "sequence_continuity",
                    "from": "walk",
                    "to": "target",
                    "hard": True,
                    "parameters": {"max_distance_m": 10},
                }
            ],
        }
        candidates = {
            "walk": [
                line(
                    "walk",
                    [[10, 53], [10.01, 53]],
                    "path",
                    "2026-12-14T10:00:00+01:00",
                    "2026-12-14T10:20:00+01:00",
                )
            ],
            "target": [point("target", 11, 54, "urban_structure", None, None)],
        }
        result = solve(workflow, candidates)
        self.assertFalse(result["complete_solutions"])
        self.assertTrue(result["partial_solutions"])
        self.assertTrue(result["rejections"])


if __name__ == "__main__":
    unittest.main()
