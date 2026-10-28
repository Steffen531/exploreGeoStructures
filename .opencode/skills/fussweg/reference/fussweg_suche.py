#!/usr/bin/env python3
"""
Isolierte Fußwege finden – Kombinierter Ansatz (Skill: fussweg)
1. Regionale Strukturtypen identifizieren   -> reference/strukturtypen.md
2. Kandidaten gezielt mit OSM-Daten verifizieren -> reference/datenquellen.md
3. Kriterien prüfen (Länge, Geradheit, kein Punkt zweimal,
   Parallelwege, Abzweigungen)              -> reference/kriterien.md
4. Ergebnis exportieren                     -> SKILL.md "Output"

Ablauf: SKILL.md (Prozess, Schritte 1-8, inkl. Learnings-Loop).
"""

import argparse
import json
import math
import sys
from pathlib import Path

from shapely.geometry import LineString, Point, shape

OPENCODE_DIR = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(OPENCODE_DIR / "lib"))
sys.path.insert(0, str(OPENCODE_DIR / "skills" / "geo-workflow" / "reference"))
from constraint_engine import distance_metres, proximity_fraction  # noqa: E402
from exporter import write_gpx, write_kml  # noqa: E402
from workflow_adapter import (  # noqa: E402
    candidate_feature,
    load_node_request,
    overpass,
    resolve_region,
    write_adapter_output,
)

# Konfiguration
OVERPASS_SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]

HEADERS = {"User-Agent": "exploreGeoStructures-fussweg/1.0 (OpenCode skill)"}

# Regionale Strukturtypen (Beispiel, vollständig in reference/strukturtypen.md)
REGIONAL_STRUCTURE_TYPES = {
    "küste": ["strand", "ufer", "deich", "damm"],
    "berg": ["treppe", "pfad", "wanderweg"],
    "fluss": ["ufer", "brücke", "deich"],
    "park": ["korridor", "garten", "allee"],
    "altstadt": ["gang", "gasse", "wall"],
    "insel": ["küstenpfad", "ufer"],
    "wüste": ["oase", "wadi"],
    "see": ["ufer", "promenade", "brücke"],
    "industrie": ["hafen", "gleis"],
    "vorort": ["durchgang", "schulweg"],
}


def identify_regional_candidates(region_type, place):
    """Kandidaten basierend auf regionalen Strukturtypen identifizieren."""
    if region_type:
        return {
            "place": place,
            "region_type": region_type,
            "structure_hints": REGIONAL_STRUCTURE_TYPES.get(region_type, []),
        }
    return {"place": place, "region_type": None, "structure_hints": []}


def fetch_osm_data(bbox=None, place=None):
    """OSM-Daten von der Overpass API abrufen.

    Regeln: eigener User-Agent, keine rekursiven Abfragen großer BBoxen,
    zwei kleine Queries mit `out geom;` (reference/datenquellen.md).
    """
    if not bbox and place:
        bbox, _ = resolve_region(place)
    if not bbox:
        raise ValueError("--place oder --bbox erforderlich")
    bbox_str = f"({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]})"

    query = f"""
    [out:json][timeout:90];
    way["highway"]{bbox_str};
    out geom;
    """
    return overpass(query).get("elements", [])


def haversine_distance(coord1, coord2):
    """Distanz zwischen zwei Koordinaten in Metern."""
    R = 6371000
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def calculate_length(coords):
    """Weglänge in Metern berechnen."""
    return sum(
        haversine_distance(coords[i], coords[i + 1]) for i in range(len(coords) - 1)
    )


def calculate_straightness(coords):
    """Geradheit berechnen (1.0 = perfekt gerade). Harter Filter: >= 0.95."""
    if len(coords) < 2:
        return 0.0
    direct = haversine_distance(coords[0], coords[-1])
    actual = calculate_length(coords)
    return direct / actual if actual > 0 else 0.0


def visits_no_point_twice(coords):
    """True, wenn kein Punkt zweimal besucht wird (keine Schlaufe/Selbstkreuzung)."""
    if len(set(coords)) != len(coords):  # doppelte Stützpunkte
        return False
    return LineString(coords).is_simple  # keine Selbstüberschneidung


def find_parallel_ways(candidate, all_ways, buffer_m=50):
    """Parallele Wege im Puffer finden.

    WICHTIG: Puffer/Entfernung nur in metrischem CRS berechnen
    (z.B. UTM 32N via pyproj) – Grad sind keine Meter.
    Anteilsschwellen: <= 35 % der Probe-Punkte (alle 25 m) mit
    Verkehr im Puffer (reference/kriterien.md).
    """
    competing = []
    for way in all_ways:
        if way is candidate or way.get("tags", {}).get("highway") in {
            "footway",
            "path",
            "pedestrian",
            "steps",
        }:
            continue
        geometry = way.get("geometry") or []
        if len(geometry) < 2:
            continue
        line = LineString([(point["lon"], point["lat"]) for point in geometry])
        fraction = proximity_fraction(candidate["line"], line, buffer_m)
        if fraction > 0.35:
            competing.append({"id": way.get("id"), "proximity_fraction": fraction})
    return competing


def find_connections(candidate, all_ways):
    """Abzweigungen finden (innere Knoten, die mit anderen Fußwegen geteilt werden).

    Start-/Endknoten (Zugang zur Straße) zählen nicht als Abzweigung.
    """
    own_nodes = candidate.get("nodes") or []
    inner_nodes = set(own_nodes[1:-1])
    if not inner_nodes:
        return []
    connections = []
    for way in all_ways:
        if way is candidate:
            continue
        shared = inner_nodes.intersection(way.get("nodes") or [])
        connections.extend(shared)
    return sorted(set(connections))


def _point(value):
    if not value:
        return None
    if isinstance(value, dict) and "lat" in value and "lon" in value:
        return Point(float(value["lon"]), float(value["lat"]))
    if isinstance(value, dict) and value.get("type") == "Feature":
        return shape(value["geometry"]).representative_point()
    if isinstance(value, dict) and "type" in value:
        return shape(value).representative_point()
    return None


def find_candidates(
    ways,
    min_length,
    max_length,
    straightness,
    buffer_m,
    start_near=None,
    end_near=None,
    endpoint_radius_m=150,
    avoid_geometries=None,
    avoid_distance_m=100,
):
    pedestrian = {"footway", "path", "pedestrian", "steps"}
    start_target, end_target = _point(start_near), _point(end_near)
    avoid_shapes = [
        shape(item.get("geometry", item)) for item in (avoid_geometries or [])
    ]
    candidates, rejected = [], []
    for way in ways:
        if way.get("tags", {}).get("highway") not in pedestrian:
            continue
        geometry = way.get("geometry") or []
        if len(geometry) < 2:
            continue
        coordinates = [(float(point["lon"]), float(point["lat"])) for point in geometry]
        line = LineString(coordinates)
        candidate = dict(way)
        candidate["line"] = line
        lat_lon = [(lat, lon) for lon, lat in coordinates]
        length = calculate_length(lat_lon)
        reasons = []
        if not min_length <= length <= max_length:
            reasons.append("Länge außerhalb des Fensters")
        straight = calculate_straightness(lat_lon)
        if straight < straightness:
            reasons.append("Geradheit unterschritten")
        if not visits_no_point_twice(coordinates):
            reasons.append("Weg besucht einen Punkt mehrfach")
        branches = find_connections(candidate, ways)
        if branches:
            reasons.append(f"{len(branches)} innere Abzweigungen")
        parallel = find_parallel_ways(candidate, ways, buffer_m)
        if parallel:
            reasons.append(f"Verkehrsweg innerhalb {buffer_m} m")

        start_point, end_point = Point(coordinates[0]), Point(coordinates[-1])
        if end_target:
            # Orientiere die Linie so, dass das nähere Ende wirklich das Ende ist.
            if distance_metres(start_point, end_target) < distance_metres(
                end_point, end_target
            ):
                coordinates.reverse()
                line = LineString(coordinates)
                start_point, end_point = end_point, start_point
            if distance_metres(end_point, end_target) > endpoint_radius_m:
                reasons.append("Ende liegt nicht nahe genug am Ziel")
        if (
            start_target
            and distance_metres(start_point, start_target) > endpoint_radius_m
        ):
            reasons.append("Start liegt nicht nahe genug am Ausgangspunkt")
        for avoid in avoid_shapes:
            if distance_metres(line, avoid) < avoid_distance_m:
                reasons.append(f"Ausschlussobjekt näher als {avoid_distance_m} m")
                break
        if reasons:
            rejected.append({"osm_id": way.get("id"), "reasons": reasons})
            continue
        candidates.append(
            {
                "way": way,
                "coordinates": coordinates,
                "length_m": length,
                "straightness": straight,
                "branches": len(branches),
                "parallel_count": len(parallel),
            }
        )
    candidates.sort(key=lambda item: (item["parallel_count"], -item["straightness"]))
    return candidates, rejected


def export_candidates(
    candidates, output, walking_speed_m_min=75, parameters=None, rejected=None
):
    features = []
    for item in candidates:
        coordinates = item["coordinates"]
        duration = item["length_m"] / walking_speed_m_min
        start = {"lat": coordinates[0][1], "lon": coordinates[0][0]}
        end = {"lat": coordinates[-1][1], "lon": coordinates[-1][0]}
        features.append(
            candidate_feature(
                candidate_id=f"osm:way:{item['way'].get('id')}",
                producer_skill="fussweg",
                entity_type="path",
                geometry={"type": "LineString", "coordinates": coordinates},
                start=start,
                end=end,
                temporal={
                    "start": None,
                    "end": None,
                    "duration_minutes": duration,
                    "timezone": None,
                    "precision": "estimated",
                },
                score=item["straightness"],
                confidence=0.7,
                sources=[
                    {"name": "OpenStreetMap", "id": f"way/{item['way'].get('id')}"}
                ],
                warnings=[f"Gehzeit mit {walking_speed_m_min} m/min geschätzt"],
                extra={
                    "length_m": item["length_m"],
                    "straightness": item["straightness"],
                    "branches": item["branches"],
                    "parallel_count": item["parallel_count"],
                },
            )
        )
    warnings = [f"Gehzeit basiert auf {walking_speed_m_min} m/min"]
    write_adapter_output(
        output,
        features,
        warnings=warnings,
        sources=[{"name": "OpenStreetMap"}],
        parameters=parameters or {},
    )
    directory = Path(output)
    (directory / "ergebnis.geojson").write_text(
        (directory / "kandidaten.geojson").read_text(encoding="utf-8"), encoding="utf-8"
    )
    write_kml(features, directory / "ergebnis.kml")
    write_gpx(features, directory / "ergebnis.gpx")
    summary = {
        "candidate_count": len(features),
        "rejected_count": len(rejected or []),
        "rejected": rejected or [],
        "walking_speed_m_min": walking_speed_m_min,
    }
    (directory / "zusammenfassung.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Isolierte Fußwege finden – Kombinierter Ansatz"
    )
    parser.add_argument(
        "--place", type=str, help="Ort oder Stadt (z.B. 'Hamburg, Deutschland')"
    )
    parser.add_argument(
        "--bbox", type=float, nargs=4, metavar=("S", "W", "N", "E"), help="Bounding Box"
    )
    parser.add_argument(
        "--region-type",
        type=str,
        choices=[
            "küste",
            "berg",
            "fluss",
            "park",
            "altstadt",
            "insel",
            "wüste",
            "see",
            "industrie",
            "vorort",
        ],
        help="Geografischer Regionstyp",
    )
    parser.add_argument(
        "--min-length", type=int, default=600, help="Minimale Länge in Metern"
    )
    parser.add_argument(
        "--max-length", type=int, default=900, help="Maximale Länge in Metern"
    )
    parser.add_argument(
        "--straightness",
        type=float,
        default=0.95,
        help="Minimale Geradheit (0-1), harter Filter",
    )
    parser.add_argument(
        "--buffer", type=int, default=50, help="Puffer für Parallelwege in Metern"
    )
    parser.add_argument(
        "--output", type=str, default="ergebnis", help="Ausgabeverzeichnis"
    )
    parser.add_argument(
        "--duration-min", type=float, help="Minimale Gehzeit in Minuten"
    )
    parser.add_argument(
        "--duration-max", type=float, help="Maximale Gehzeit in Minuten"
    )
    parser.add_argument(
        "--walking-speed", type=float, default=75, help="Gehgeschwindigkeit in m/min"
    )
    parser.add_argument("--request", help="Workflow-Knoten als JSON")
    parser.add_argument(
        "--orchestrated",
        action="store_true",
        help="Normalisierten Adaptermodus verwenden",
    )

    args = parser.parse_args()
    request = load_node_request(args.request)
    parameters = request["parameters"] if request else {}
    if request:
        bbox, place = resolve_region(parameters["region"])
        args.bbox, args.place = bbox, place
        args.duration_min = parameters.get("duration_min", args.duration_min)
        args.duration_max = parameters.get("duration_max", args.duration_max)
        args.walking_speed = float(
            parameters.get("walking_speed_m_min", args.walking_speed)
        )
    if not args.place and not args.bbox:
        parser.error("--place, --bbox oder --request erforderlich")
    if args.duration_min is not None:
        args.min_length = int(args.duration_min * args.walking_speed)
    if args.duration_max is not None:
        args.max_length = int(args.duration_max * args.walking_speed)
    ways = fetch_osm_data(args.bbox, args.place)
    candidates, rejected = find_candidates(
        ways,
        args.min_length,
        args.max_length,
        args.straightness,
        args.buffer,
        parameters.get("start_near"),
        parameters.get("end_near"),
        float(parameters.get("endpoint_radius_m", 150)),
        parameters.get("avoid_geometries"),
        float(parameters.get("avoid_distance_m", 100)),
    )
    export_candidates(
        candidates,
        args.output,
        args.walking_speed,
        parameters=parameters,
        rejected=rejected,
    )


if __name__ == "__main__":
    main()
