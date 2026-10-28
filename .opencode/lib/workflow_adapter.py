"""Shared helpers for orchestrated geo-skill adapters."""

from __future__ import annotations

import json
import hashlib
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests


USER_AGENT = "exploreGeoStructures-workflow/1.0"
OVERPASS_SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
CACHE_DIRECTORY = Path("cache/workflow-adapters")


def _cache_path(namespace: str, payload: str) -> Path:
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return CACHE_DIRECTORY / f"{namespace}-{digest}.json"


def _read_cache(path: Path, ttl_seconds: int) -> Any | None:
    if not path.exists() or time.time() - path.stat().st_mtime > ttl_seconds:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _write_cache(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def cached_get_json(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    namespace: str = "http",
    ttl_seconds: int = 3600,
    timeout: int = 30,
    attempts: int = 3,
) -> Any:
    cache_key = url + "?" + json.dumps(params or {}, sort_keys=True, ensure_ascii=False)
    cache_path = _cache_path(namespace, cache_key)
    cached = _read_cache(cache_path, ttl_seconds)
    if cached is not None:
        return cached
    last_error = None
    for attempt in range(attempts):
        try:
            response = requests.get(
                url,
                params=params,
                headers={"User-Agent": USER_AGENT},
                timeout=timeout,
            )
            response.raise_for_status()
            data = response.json()
            _write_cache(cache_path, data)
            return data
        except (requests.RequestException, ValueError) as error:
            last_error = error
            if attempt + 1 < attempts:
                time.sleep(1 + attempt * 2)
    raise RuntimeError(f"HTTP-Abruf fehlgeschlagen: {last_error}") from last_error


def load_node_request(path: str | None) -> dict[str, Any] | None:
    if not path:
        return None
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if "parameters" not in data:
        raise ValueError("Workflow-Knoten benötigt parameters")
    return data


def resolve_region(region: Any) -> tuple[tuple[float, float, float, float], str | None]:
    """Return bbox as (south, west, north, east) and optional label."""
    if isinstance(region, str):
        label = region
        bbox = None
    elif isinstance(region, dict):
        label = region.get("name")
        bbox = region.get("bbox")
        if bbox:
            if isinstance(bbox, dict):
                return (
                    float(bbox["south"]),
                    float(bbox["west"]),
                    float(bbox["north"]),
                    float(bbox["east"]),
                ), label
            return tuple(map(float, bbox)), label
    else:
        raise ValueError("region muss Name oder Objekt sein")
    if not label:
        raise ValueError("Region benötigt name oder bbox")
    matches = cached_get_json(
        "https://nominatim.openstreetmap.org/search",
        params={"q": label, "format": "jsonv2", "limit": 1},
        namespace="nominatim",
        ttl_seconds=30 * 24 * 60 * 60,
        timeout=30,
    )
    if not matches:
        raise ValueError(f"Region nicht gefunden: {label}")
    south, north, west, east = map(float, matches[0]["boundingbox"])
    return (south, west, north, east), label


def overpass(query: str, attempts: int = 3) -> dict[str, Any]:
    cache_path = _cache_path("overpass", query)
    cached = _read_cache(cache_path, 24 * 60 * 60)
    if cached is not None:
        return cached
    failures = []
    for server in OVERPASS_SERVERS:
        for attempt in range(attempts):
            try:
                response = requests.post(
                    server,
                    data={"data": query},
                    headers={"User-Agent": USER_AGENT},
                    timeout=120,
                )
                response.raise_for_status()
                data = response.json()
                _write_cache(cache_path, data)
                return data
            except (requests.RequestException, ValueError) as error:
                failures.append(f"{server}: {type(error).__name__}: {error}")
                if attempt + 1 < attempts:
                    time.sleep(1 + attempt * 2)
    raise RuntimeError(
        "Alle Overpass-Endpunkte fehlgeschlagen: " + " | ".join(failures)
    )


def element_point(element: dict[str, Any]) -> list[float] | None:
    if "lon" in element and "lat" in element:
        return [float(element["lon"]), float(element["lat"])]
    center = element.get("center")
    if center:
        return [float(center["lon"]), float(center["lat"])]
    geometry = element.get("geometry") or []
    if geometry:
        lon = sum(float(point["lon"]) for point in geometry) / len(geometry)
        lat = sum(float(point["lat"]) for point in geometry) / len(geometry)
        return [lon, lat]
    return None


def element_geometry(element: dict[str, Any]) -> dict[str, Any] | None:
    geometry = element.get("geometry") or []
    if geometry:
        coordinates = [[float(point["lon"]), float(point["lat"])] for point in geometry]
        if len(coordinates) >= 4 and coordinates[0] == coordinates[-1]:
            return {"type": "Polygon", "coordinates": [coordinates]}
        if len(coordinates) >= 2:
            return {"type": "LineString", "coordinates": coordinates}
    point = element_point(element)
    return {"type": "Point", "coordinates": point} if point else None


def candidate_feature(
    *,
    candidate_id: str,
    producer_skill: str,
    entity_type: str,
    geometry: dict[str, Any],
    score: float,
    confidence: float,
    sources: list[dict[str, Any]],
    temporal: dict[str, Any] | None = None,
    start: dict[str, float] | None = None,
    end: dict[str, float] | None = None,
    warnings: list[str] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    properties = {
        "candidate_id": candidate_id,
        "producer_skill": producer_skill,
        "entity_type": entity_type,
        "start": start,
        "end": end,
        "temporal": temporal
        or {
            "start": None,
            "end": None,
            "duration_minutes": None,
            "timezone": None,
            "precision": "unknown",
        },
        "score": float(score),
        "confidence": max(0.0, min(1.0, float(confidence))),
        "sources": sources,
        "warnings": warnings or [],
        "raw_reference": None,
    }
    if extra:
        properties.update(extra)
    return {"type": "Feature", "geometry": geometry, "properties": properties}


def write_adapter_output(
    output: str | Path,
    features: list[dict[str, Any]],
    *,
    status: str | None = None,
    warnings: list[str] | None = None,
    sources: list[dict[str, Any]] | None = None,
    parameters: dict[str, Any] | None = None,
    error: Exception | None = None,
) -> None:
    directory = Path(output)
    directory.mkdir(parents=True, exist_ok=True)
    collection = {"type": "FeatureCollection", "features": features}
    (directory / "kandidaten.geojson").write_text(
        json.dumps(collection, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if error:
        final_status = "error"
    elif status:
        final_status = status
    else:
        final_status = "success" if features else "empty"
    payload = {
        "status": final_status,
        "timestamp": datetime.now().astimezone().isoformat(),
        "candidate_count": len(features),
        "warnings": warnings or [],
        "sources": sources or [],
        "error_class": type(error).__name__ if error else None,
        "parameters": parameters or {},
    }
    if error:
        payload["error_message"] = str(error)
    (directory / "status.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
