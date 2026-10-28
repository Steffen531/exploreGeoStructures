#!/usr/bin/env python3
"""Provider-neutral ride-hailing estimate using an explicit driving router."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

OPENCODE_DIR = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(OPENCODE_DIR / "lib"))
from workflow_adapter import cached_get_json  # noqa: E402


OSRM_URL = "https://router.project-osrm.org/route/v1/driving"


def estimate_route(
    start: dict[str, float],
    end: dict[str, float],
    departure_time: str | None = None,
    router_url: str = OSRM_URL,
) -> dict[str, Any]:
    """Return a road-routed estimate; never implies provider availability."""
    url = (
        f"{router_url}/{start['lon']},{start['lat']};{end['lon']},{end['lat']}"
        "?overview=full&geometries=geojson&steps=false"
    )
    data = cached_get_json(
        url,
        namespace="ride-hailing-osrm",
        ttl_seconds=24 * 60 * 60,
        timeout=30,
    )
    if data.get("code") != "Ok" or not data.get("routes"):
        raise RuntimeError(
            f"Straßenrouter lieferte keine Route: {data.get('code', 'unknown')}"
        )
    route = data["routes"][0]
    duration_minutes = float(route["duration"]) / 60
    start_time = (
        datetime.fromisoformat(departure_time.replace("Z", "+00:00"))
        if departure_time
        else None
    )
    if start_time and (start_time.tzinfo is None or start_time.utcoffset() is None):
        raise ValueError("departure_time benötigt eine Zeitzone")
    end_time = start_time + timedelta(minutes=duration_minutes) if start_time else None
    return {
        "type": "Feature",
        "geometry": route["geometry"],
        "properties": {
            "candidate_id": "ride-hailing:osrm-estimate",
            "producer_skill": "geo-workflow",
            "entity_type": "ride_hailing_route",
            "mode": "estimated_ride_hailing",
            "provider": None,
            "availability_confirmed": False,
            "price": None,
            "start": start,
            "end": end,
            "temporal": {
                "start": start_time.isoformat() if start_time else None,
                "end": end_time.isoformat() if end_time else None,
                "duration_minutes": duration_minutes,
                "timezone": str(start_time.tzinfo) if start_time else None,
                "precision": "estimated",
            },
            "distance_m": float(route["distance"]),
            "score": 0.5,
            "confidence": 0.45,
            "sources": [{"name": "OSRM", "profile": "driving", "url": router_url}],
            "warnings": [
                "Straßenrouting ist keine Bestätigung realer Taxi-/Ride-Hailing-Verfügbarkeit"
            ],
            "raw_reference": None,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ride-Hailing-Segment transparent schätzen"
    )
    parser.add_argument(
        "--start", type=float, nargs=2, metavar=("LAT", "LON"), required=True
    )
    parser.add_argument(
        "--end", type=float, nargs=2, metavar=("LAT", "LON"), required=True
    )
    parser.add_argument("--departure-time")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    start = {"lat": args.start[0], "lon": args.start[1]}
    end = {"lat": args.end[0], "lon": args.end[1]}
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    try:
        feature = estimate_route(start, end, args.departure_time)
        collection = {"type": "FeatureCollection", "features": [feature]}
        status = {
            "status": "degraded",
            "timestamp": datetime.now().astimezone().isoformat(),
            "candidate_count": 1,
            "warnings": feature["properties"]["warnings"],
            "sources": feature["properties"]["sources"],
            "error_class": None,
            "parameters": {"start": start, "end": end},
        }
    except Exception as error:
        collection = {"type": "FeatureCollection", "features": []}
        status = {
            "status": "error",
            "timestamp": datetime.now().astimezone().isoformat(),
            "candidate_count": 0,
            "warnings": [str(error)],
            "sources": [{"name": "OSRM", "profile": "driving"}],
            "error_class": type(error).__name__,
            "parameters": {"start": start, "end": end},
        }
    (output / "kandidaten.geojson").write_text(
        json.dumps(collection, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output / "status.json").write_text(
        json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if status["status"] == "error":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
