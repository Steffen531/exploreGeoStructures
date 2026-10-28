#!/usr/bin/env python3
"""Deterministic spatial and temporal constraints for geo workflows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from typing import Any

from pyproj import CRS, Transformer
from shapely.geometry import Point, shape
from shapely.ops import transform


SPATIAL_TYPES = {
    "near",
    "within",
    "intersects",
    "starts_near",
    "ends_near",
    "starts_at",
    "ends_at",
    "passes_through",
    "avoids",
    "sequence_continuity",
}
TEMPORAL_TYPES = {
    "starts_between",
    "ends_between",
    "duration_between",
    "before",
    "after",
    "overlaps",
    "gap_between",
    "active_at",
    "sequence_time",
}
SUPPORTED_TYPES = SPATIAL_TYPES | TEMPORAL_TYPES


@dataclass(frozen=True)
class ConstraintResult:
    passed: bool
    reason: str
    value: float | str | None = None
    penalty: float = 0.0


def _properties(feature: dict[str, Any]) -> dict[str, Any]:
    return feature.get("properties") or {}


def _geometry(feature: dict[str, Any]):
    geometry = feature.get("geometry")
    if not geometry:
        raise ValueError("Kandidat besitzt keine Geometrie")
    return shape(geometry)


def _declared_point(feature: dict[str, Any], key: str) -> Point | None:
    value = _properties(feature).get(key)
    if not value:
        return None
    try:
        return Point(float(value["lon"]), float(value["lat"]))
    except (KeyError, TypeError, ValueError):
        return None


def _endpoint(feature: dict[str, Any], key: str) -> Point:
    declared = _declared_point(feature, key)
    if declared is not None:
        return declared
    geom = _geometry(feature)
    if geom.geom_type == "Point":
        return geom
    if geom.geom_type == "LineString":
        coord = geom.coords[0 if key == "start" else -1]
        return Point(coord)
    if geom.geom_type == "MultiLineString":
        line = geom.geoms[0 if key == "start" else -1]
        coord = line.coords[0 if key == "start" else -1]
        return Point(coord)
    return geom.representative_point()


def _project_pair(first, second):
    center = first.union(second).centroid
    local = CRS.from_proj4(
        f"+proj=aeqd +lat_0={center.y:.10f} +lon_0={center.x:.10f} "
        "+datum=WGS84 +units=m +no_defs"
    )
    transformer = Transformer.from_crs("EPSG:4326", local, always_xy=True)
    project = transformer.transform
    return transform(project, first), transform(project, second)


def distance_metres(first, second) -> float:
    """Return minimum geodetic-local distance between WGS84 geometries."""
    projected_first, projected_second = _project_pair(first, second)
    value = float(projected_first.distance(projected_second))
    if not isfinite(value):
        raise ValueError("Nicht endlicher Geometrieabstand")
    return value


def proximity_fraction(
    line, other, threshold_m: float, sample_step_m: float = 25
) -> float:
    """Fraction of interior line samples that are within threshold of another geometry."""
    projected_line, projected_other = _project_pair(line, other)
    if projected_line.length <= 0:
        return 0.0
    if projected_line.length <= sample_step_m * 2:
        samples = [projected_line.interpolate(0.5, normalized=True)]
    else:
        count = max(1, int(projected_line.length // sample_step_m) - 1)
        samples = [
            projected_line.interpolate((index + 1) * sample_step_m)
            for index in range(count)
        ]
    close = sum(point.distance(projected_other) <= threshold_m for point in samples)
    return close / len(samples)


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"Zeit ohne Zeitzone: {value}")
    return parsed


def _temporal(feature: dict[str, Any]) -> dict[str, Any]:
    return _properties(feature).get("temporal") or {}


def _time(feature: dict[str, Any], key: str) -> datetime | None:
    return _parse_time(_temporal(feature).get(key))


def _duration(feature: dict[str, Any]) -> float | None:
    value = _temporal(feature).get("duration_minutes")
    if value is not None:
        return float(value)
    start, end = _time(feature, "start"), _time(feature, "end")
    if start and end:
        return (end - start).total_seconds() / 60
    return None


def _range_result(
    value: float, minimum: float, maximum: float, label: str
) -> ConstraintResult:
    passed = minimum <= value <= maximum
    return ConstraintResult(
        passed,
        f"{label} {value:.2f} liegt "
        + ("im" if passed else "außerhalb des")
        + f" Fensters {minimum:.2f}–{maximum:.2f}",
        value,
    )


def _required(assignments: dict[str, dict[str, Any]], node_id: str | None):
    if not node_id or node_id not in assignments:
        raise KeyError(f"Kandidat für Knoten '{node_id}' fehlt")
    return assignments[node_id]


def evaluate_constraint(
    constraint: dict[str, Any], assignments: dict[str, dict[str, Any]]
) -> ConstraintResult:
    """Evaluate one constraint against a complete-enough assignment."""
    kind = constraint.get("type")
    if kind not in SUPPORTED_TYPES:
        raise ValueError(f"Unbekannter Constraint-Typ: {kind}")
    source = _required(assignments, constraint.get("from"))
    target_id = constraint.get("to")
    target = _required(assignments, target_id) if target_id else None
    params = constraint.get("parameters") or {}

    if kind in SPATIAL_TYPES:
        if kind in {"starts_near", "starts_at"}:
            first = _endpoint(source, "start")
            second = _endpoint(target, params.get("target_endpoint", "start"))
        elif kind in {"ends_near", "ends_at", "sequence_continuity"}:
            first = _endpoint(source, "end")
            second = _endpoint(target, params.get("target_endpoint", "start"))
        else:
            first, second = _geometry(source), _geometry(target)

        if second.is_empty:
            if kind == "avoids":
                return ConstraintResult(True, "Ausschlussmenge ist leer")
            return ConstraintResult(False, "Zielgeometrie ist leer")

        if kind == "within":
            passed = first.within(second) or first.covered_by(second)
            return ConstraintResult(
                passed,
                "Geometrie liegt innerhalb"
                if passed
                else "Geometrie liegt nicht innerhalb",
            )
        if kind == "intersects":
            passed = first.intersects(second)
            return ConstraintResult(
                passed,
                "Geometrien schneiden sich"
                if passed
                else "Geometrien schneiden sich nicht",
            )

        distance = distance_metres(first, second)
        if kind == "avoids":
            threshold = float(params["min_distance_m"])
            passed = distance >= threshold
            return ConstraintResult(
                passed,
                f"Mindestabstand {distance:.1f} m "
                + ("eingehalten" if passed else f"kleiner als {threshold:.1f} m"),
                distance,
            )
        threshold = float(
            params.get(
                "max_distance_m", 1.0 if kind in {"starts_at", "ends_at"} else 150.0
            )
        )
        passed = distance <= threshold
        return ConstraintResult(
            passed,
            f"Abstand {distance:.1f} m "
            + ("zulässig" if passed else f"größer als {threshold:.1f} m"),
            distance,
        )

    if kind in {"starts_between", "ends_between"}:
        key = "start" if kind == "starts_between" else "end"
        value = _time(source, key)
        if value is None:
            return ConstraintResult(False, f"{key}-Zeit fehlt")
        minimum, maximum = _parse_time(params["start"]), _parse_time(params["end"])
        passed = minimum <= value <= maximum
        return ConstraintResult(
            passed,
            f"{key}-Zeit {value.isoformat()} "
            + ("im" if passed else "außerhalb des")
            + " Fenster",
            value.isoformat(),
        )

    if kind == "duration_between":
        value = _duration(source)
        if value is None:
            return ConstraintResult(False, "Dauer fehlt")
        return _range_result(
            value, float(params["min_minutes"]), float(params["max_minutes"]), "Dauer"
        )

    if kind == "active_at":
        moment = _parse_time(params["at"])
        start, end = _time(source, "start"), _time(source, "end")
        if not start or not end:
            return ConstraintResult(False, "Aktivitätszeitraum fehlt")
        passed = start <= moment <= end
        return ConstraintResult(
            passed,
            "Zum Zeitpunkt aktiv" if passed else "Zum Zeitpunkt nicht aktiv",
            moment.isoformat(),
        )

    source_start, source_end = _time(source, "start"), _time(source, "end")
    target_start, target_end = _time(target, "start"), _time(target, "end")
    if kind == "overlaps":
        if not all((source_start, source_end, target_start, target_end)):
            return ConstraintResult(False, "Zeitintervall für Überlappung fehlt")
        passed = source_start <= target_end and target_start <= source_end
        return ConstraintResult(
            passed,
            "Zeitintervalle überlappen"
            if passed
            else "Zeitintervalle überlappen nicht",
        )

    if kind in {"before", "sequence_time", "gap_between"}:
        first, second = source_end, target_start
    else:  # after
        first, second = target_end, source_start
    if not first or not second:
        return ConstraintResult(False, "Zeitpunkt für Reihenfolge fehlt")
    gap = (second - first).total_seconds() / 60
    minimum = float(params.get("min_minutes", 0))
    maximum = float(params.get("max_minutes", float("inf")))
    passed = minimum <= gap <= maximum
    maximum_text = "∞" if maximum == float("inf") else f"{maximum:.2f}"
    return ConstraintResult(
        passed,
        f"Zeitabstand {gap:.2f} min liegt "
        + ("im" if passed else "außerhalb des")
        + f" Fensters {minimum:.2f}–{maximum_text}",
        gap,
    )


def evaluate_ready_constraints(
    constraints: list[dict[str, Any]], assignments: dict[str, dict[str, Any]]
) -> list[tuple[dict[str, Any], ConstraintResult]]:
    """Evaluate only constraints whose referenced nodes are assigned."""
    evaluated = []
    for constraint in constraints:
        references = [constraint.get("from")]
        if constraint.get("to"):
            references.append(constraint["to"])
        if all(reference in assignments for reference in references):
            result = evaluate_constraint(constraint, assignments)
            if not result.passed and not constraint.get("hard", True):
                weight = float(constraint.get("weight", 1.0))
                result = ConstraintResult(False, result.reason, result.value, weight)
            evaluated.append((constraint, result))
    return evaluated
