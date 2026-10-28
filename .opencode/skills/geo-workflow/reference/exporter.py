#!/usr/bin/env python3
"""Export combined workflow solutions to GeoJSON, KML, GPX and JSON."""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime
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


def _zeitplan_rows(result: dict[str, Any], solution: dict[str, Any]) -> list[dict]:
    """Zeilen für eine Lösung, zeitlich sortiert (ohne Bytes, humanoid)."""
    order = {node: index for index, node in enumerate(result.get("node_order", []))}
    rows = []
    for node_id, feature in solution["assignments"].items():
        p = feature.get("properties") or {}
        temporal = p.get("temporal") or {}
        start_point = p.get("start") or {}
        end_point = p.get("end") or {}

        def _punekt(punkt):
            if punkt.get("lat") is None or punkt.get("lon") is None:
                return None
            return f"({punkt['lat']:.5f}, {punkt['lon']:.5f})"

        rows.append(
            {
                "node": node_id,
                "candidate_id": p.get("candidate_id"),
                "entity_type": p.get("entity_type"),
                "name": p.get("name"),
                "start": temporal.get("start"),
                "end": temporal.get("end"),
                "duration_minutes": temporal.get("duration_minutes"),
                "precision": temporal.get("precision"),
                "timezone": temporal.get("timezone"),
                "mode": p.get("mode"),
                "score": p.get("score"),
                "distance_m": p.get("distance_m"),
                "anchor": p.get("anchor"),
                "transfers": p.get("transfers"),
                "segments": p.get("segments") or [],
                "warnings": p.get("warnings") or [],
                "start_point": _punekt(start_point),
                "end_point": _punekt(end_point),
                "order_rank": order.get(node_id, 999),
            }
        )
    rows.sort(
        key=lambda row: (
            row["start"] is not None,
            row["start"] or "",
            row["order_rank"],
        )
    )
    return rows


def _linie_code(name: str | None) -> str:
    """Kurzname der Linie ("RE6: Hamburg => Westerland" → "RE6")."""
    return (name or "").split(":", 1)[0].strip() or (name or "").strip()


def _de_zahl(value: float, stellen: int = 1) -> str:
    return f"{float(value):.{stellen}f}".replace(".", ",")


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def zeitplan_markdown(
    result: dict[str, Any], solution: dict[str, Any], number: int
) -> str:
    """Kompakte Bullet-Zeitkette im Nutzerformat (Mall-Aufenthalt & Fußwege inklusive)."""
    rows = _zeitplan_rows(result, solution)
    assignments = solution["assignments"]
    timed = sorted([row for row in rows if row["start"]], key=lambda r: r["start"])
    untimed = [row for row in rows if not row["start"]]

    mall_row = next(
        (
            row
            for row in untimed
            if row["entity_type"] == "urban_structure" and row["name"]
        ),
        None,
    )

    def mall_punkt():
        if not mall_row:
            return None
        feature = assignments.get(mall_row["node"]) or {}
        geometry = feature.get("geometry") or {}
        if geometry.get("type") == "Point":
            lon, lat = geometry["coordinates"][:2]
            return (float(lat), float(lon))
        punkte = list(_coordinates(geometry))
        if not punkte:
            return None
        return (
            sum(point[1] for point in punkte) / len(punkte),
            sum(point[0] for point in punkte) / len(punkte),
        )

    lines = [f"## Route {number} – Score {solution['score']:.2f}", ""]
    previous_end = None
    ride_row = None
    for row in timed:
        if row["entity_type"] == "transit_route":
            hh, mm = row["start"][11:16].split(":")
            minute = int(hh) * 60 + int(mm)
            for leg in row["segments"]:
                code = _linie_code(leg.get("linie"))
                von = leg.get("von") or "?"
                nach = leg.get("nach") or "?"
                dauer = leg.get("dauer_min") or leg.get("dauer") or 0
                lines.append(
                    f"- {minute // 60:02d}:{minute % 60:02d} ab {von} – {code} "
                    f"(→ {nach}, ~{_de_zahl(dauer, 0)} Min)"
                )
                minute += int(dauer)
            last_leg = row["segments"][-1] if row["segments"] else {}
            name = last_leg.get("nach") or row.get("name") or ""
            ankunft = f"- Ankunft {row['end'][11:16]} {name}".rstrip()
            endpunkt = row.get("end_point")
            punkt = mall_punkt()
            if mall_row and endpunkt and punkt:
                lat, lon = (float(t) for t in endpunkt.strip("()").split(","))
                abstand = _haversine_m(lat, lon, punkt[0], punkt[1])
                ankunft += f" (♀ {_de_zahl(abstand, 0)} m vor {mall_row['name']})"
            lines.append(ankunft)
        elif row["entity_type"] == "ride_hailing_route":
            gap = None
            if previous_end:
                gap = (
                    datetime.fromisoformat(row["start"])
                    - datetime.fromisoformat(previous_end)
                ).total_seconds() / 60
            prefix = (
                f"Mall-Aufenthalt {_de_zahl(gap, 0)} Min"
                if mall_row and gap is not None
                else "Pause"
            )
            lines.append(
                f"- {prefix} → Ride startet {row['start'][11:16]} "
                f"(est., {_de_zahl(row['duration_minutes'])} Min, "
                f"{_de_zahl((row['distance_m'] or 0) / 1000)} km)"
            )
            ride_row = row
        previous_end = row["end"]

    for walk in untimed:
        if walk["entity_type"] != "path":
            continue
        start_text = "–"
        if ride_row and ride_row.get("end"):
            start_text = ride_row["end"][11:16]
        end_text = (walk.get("end_point") or "?").replace(", ", " / ")
        lines.append(
            f"- Fußweg ab {start_text}, {_de_zahl(walk['duration_minutes'])} Min bis {end_text}"
        )
    lines.append("")
    lines.append(
        "> ⓘ Zeiten teils geschätzt (OSM-Fallback); Ride `estimated_ride_hailing` "
        "ohne Anbieter-/Preisangabe."
    )
    return "\n".join(lines) + "\n"


def write_itinerary(result: dict[str, Any], output: Path, limit: int = 3) -> None:
    """Zeitplan (Markdown + JSON) für die Top-Lösungen schreiben."""
    solutions = result.get("complete_solutions", [])[:limit]
    if not solutions:
        return
    blocks = [
        f"# Zeitplan – Top-Routen für Workflow {result.get('workflow_id', '?')}",
        "",
        "> Geschätzte Abschnitte basieren auf OSM-Fallback-Daten; echte "
        "Abfahrts-/Ankunftszeiten erscheinen hier, wenn ein GTFS-Fahrplan "
        "vorliegt. Alle Angaben ohne Gewähr.",
        "",
    ]
    structured = []
    for number, solution in enumerate(solutions, 1):
        blocks.append(zeitplan_markdown(result, solution, number))
        structured.append(
            {
                "route": number,
                "score": solution["score"],
                "schritte": _zeitplan_rows(result, solution),
            }
        )
    (output / "zeitplan.md").write_text("\n".join(blocks), encoding="utf-8")
    (output / "zeitplan.json").write_text(
        json.dumps(structured, ensure_ascii=False, indent=1), encoding="utf-8"
    )


def write_solution_maps(result: dict[str, Any], output: Path, limit: int = 3) -> None:
    """Pro top-Lösung eigene Karte (GeoJSON, KML, GPX) exportieren."""
    for number, solution in enumerate(result.get("complete_solutions", [])[:limit], 1):
        directory = output / "karten" / f"route-{number}"
        directory.mkdir(parents=True, exist_ok=True)
        features = []
        for node_id, feature in solution["assignments"].items():
            if feature.get("geometry", {}).get("type") == "GeometryCollection":
                continue  # Ausschlussmengen bleiben den Karten fern
            item = json.loads(json.dumps(feature))
            item.setdefault("properties", {}).update(
                {"workflow_node": node_id, "workflow_route": number}
            )
            features.append(item)
        write_geojson(features, directory / "ergebnis.geojson")
        write_kml(features, directory / "ergebnis.kml")
        write_gpx(features, directory / "ergebnis.gpx")


def export_result(
    result: dict[str, Any], output_directory: str | Path, limit: int = 3
) -> None:
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    features = solution_features(result, limit)
    write_geojson(features, output / "ergebnis.geojson")
    write_kml(features, output / "ergebnis.kml")
    write_gpx(features, output / "ergebnis.gpx")
    write_itinerary(result, output, limit)
    write_solution_maps(result, output, limit)
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
