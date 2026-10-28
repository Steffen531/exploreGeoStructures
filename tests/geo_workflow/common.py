from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / ".opencode" / "skills" / "geo-workflow" / "reference"
if str(REFERENCE) not in sys.path:
    sys.path.insert(0, str(REFERENCE))


def feature(
    candidate_id,
    geometry,
    *,
    entity_type="path",
    start=None,
    end=None,
    temporal_start=None,
    temporal_end=None,
    duration=10,
    score=1,
):
    return {
        "type": "Feature",
        "geometry": geometry,
        "properties": {
            "candidate_id": candidate_id,
            "producer_skill": "test",
            "entity_type": entity_type,
            "start": start,
            "end": end,
            "temporal": {
                "start": temporal_start,
                "end": temporal_end,
                "duration_minutes": duration,
                "timezone": "Europe/Berlin",
                "precision": "scheduled",
            },
            "score": score,
            "confidence": 1,
            "sources": [{"name": "fixture"}],
            "warnings": [],
            "raw_reference": None,
        },
    }
