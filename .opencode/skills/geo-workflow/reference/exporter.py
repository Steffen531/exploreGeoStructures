#!/usr/bin/env python3
"""Export combined workflow solutions to GeoJSON, KML, GPX and JSON."""

from __future__ import annotations

import argparse
import json
from html import escape
from pathlib import Path
from typing import Any, Iterable


def solution_features(result: dict[str, Any], limit: int = 3) -> list[dict[str, Any]]:
    features = []
    for solution_index, solution in enumerate(
        result.get("complete_solutions", [])[:limit], 1
    ):
        for sequence, (node_id, feature) in enumerate(
            solution["assignments"].items(), 1
        ):
            item = json.loads(json.dumps(feature))
            properties = item.setdefault("properties", {})
            properties.update(
                {
                    "workflow_solution": solution_index,
                    "workflow_node": node_id,
                    "workflow_sequence": sequence,
                    "workflow_score": solution["score"],
                }
            )
            features.append(item)
    return features


def _coordinates(geometry: dict[str, Any]) -> Iterable[list[float]]:
    kind = geometry["type"]
    if kind == "GeometryCollection":
        for part in geometry.get("geometries", []):
            yield from _coordinates(part)
        return
    coordinates = geometry["coordinates"]
    if kind == "Point":
        yield coordinates
    elif kind == "LineString":
        yield from coordinates
    elif kind == "MultiLineString":
        for line in coordinates:
            yield from line
    elif kind == "Polygon":
        if coordinates:
            yield from coordinates[0]
    elif kind == "MultiPolygon":
        for polygon in coordinates:
            if polygon:
                yield from polygon[0]
    elif kind == "GeometryCollection":
        for part in coordinates.get("geometries", []):
            yield from _coordinates(part)


def _kml_geometry(geometry: dict[str, Any]) -> str:
    kind = geometry["type"]
    if kind == "GeometryCollection":
        parts = "".join(_kml_geometry(part) for part in geometry.get("geometries", []))
        return f"<MultiGeometry>{parts}</MultiGeometry>" if parts else ""
    coordinates = geometry["coordinates"]

    def coordinate_text(values):
        return " ".join(f"{point[0]},{point[1]},0" for point in values)

    if kind == "Point":
        return f"<Point><coordinates>{coordinate_text([coordinates])}</coordinates></Point>"
    if kind == "LineString":
        return f"<LineString><tessellate>1</tessellate><coordinates>{coordinate_text(coordinates)}</coordinates></LineString>"
    if kind == "Polygon":
        return (
            "<Polygon><outerBoundaryIs><LinearRing><coordinates>"
            + coordinate_text(coordinates[0])
            + "</coordinates></LinearRing></outerBoundaryIs></Polygon>"
        )
    if kind == "MultiLineString":
        parts = "".join(
            _kml_geometry({"type": "LineString", "coordinates": line})
            for line in coordinates
        )
        return f"<MultiGeometry>{parts}</MultiGeometry>"
    if kind == "MultiPolygon":
        parts = "".join(
            _kml_geometry({"type": "Polygon", "coordinates": polygon})
            for polygon in coordinates
        )
        return f"<MultiGeometry>{parts}</MultiGeometry>"
    if kind == "GeometryCollection":
        parts = "".join(
            _kml_geometry(part) for part in coordinates.get("geometries", [])
        )
        return f"<MultiGeometry>{parts}</MultiGeometry>" if parts else ""
    return ""


def write_geojson(features: list[dict[str, Any]], path: Path) -> None:
    path.write_text(
        json.dumps(
            {"type": "FeatureCollection", "features": features},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def write_kml(features: list[dict[str, Any]], path: Path) -> None:
    placemarks = []
    for feature in features:
        geometry = feature.get("geometry")
        if not geometry:
            continue
        properties = feature.get("properties") or {}
        name = escape(str(properties.get("candidate_id", "Kandidat")))
        description = escape(json.dumps(properties, ensure_ascii=False))
        placemarks.append(
            f"<Placemark><name>{name}</name><description>{description}</description>"
            f"{_kml_geometry(geometry)}</Placemark>"
        )
    path.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>'
        '<Style id="route"><LineStyle><color>ffef7d00</color><width>5</width></LineStyle>'
        "<IconStyle><scale>1.1</scale></IconStyle></Style>"
        + "".join(placemarks)
        + "</Document></kml>",
        encoding="utf-8",
    )


def write_gpx(features: list[dict[str, Any]], path: Path) -> None:
    elements = []
    for feature in features:
        geometry = feature.get("geometry")
        if not geometry:
            continue
        properties = feature.get("properties") or {}
        name = escape(str(properties.get("candidate_id", "Kandidat")))
        if geometry["type"] == "Point":
            lon, lat = geometry["coordinates"][:2]
            elements.append(f'<wpt lat="{lat}" lon="{lon}"><name>{name}</name></wpt>')
        else:
            points = "".join(
                f'<trkpt lat="{coordinate[1]}" lon="{coordinate[0]}" />'
                for coordinate in _coordinates(geometry)
            )
            if points:
                elements.append(
                    f"<trk><name>{name}</name><trkseg>{points}</trkseg></trk>"
                )
    path.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<gpx version="1.1" creator="exploreGeoStructures geo-workflow" '
        'xmlns="http://www.topografix.com/GPX/1/1">' + "".join(elements) + "</gpx>",
        encoding="utf-8",
    )


def export_result(
    result: dict[str, Any], output_directory: str | Path, limit: int = 3
) -> None:
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    features = solution_features(result, limit)
    write_geojson(features, output / "ergebnis.geojson")
    write_kml(features, output / "ergebnis.kml")
    write_gpx(features, output / "ergebnis.gpx")
    summary = {
        "workflow_id": result.get("workflow_id"),
        "complete_solution_count": len(result.get("complete_solutions", [])),
        "partial_solutions": result.get("partial_solutions", []),
        "rejections": result.get("rejections", {}),
        "warnings": result.get("warnings", []),
        "explored": result.get("explored", 0),
        "exported_solution_count": min(
            limit, len(result.get("complete_solutions", []))
        ),
    }
    (output / "zusammenfassung.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Geo-Workflow-Ergebnisse exportieren")
    parser.add_argument("--result", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--limit", type=int, default=3)
    args = parser.parse_args()
    result = json.loads(Path(args.result).read_text(encoding="utf-8"))
    export_result(result, args.output, args.limit)


if __name__ == "__main__":
    main()
