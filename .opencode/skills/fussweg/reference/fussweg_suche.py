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
import heapq
import json
import math
import sys
from pathlib import Path

from pyproj import CRS, Transformer
from shapely.geometry import LineString, Point, shape
from shapely.ops import transform as shapely_transform
from shapely.strtree import STRtree

OPENCODE_DIR = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(OPENCODE_DIR / "lib"))
sys.path.insert(0, str(OPENCODE_DIR / "skills" / "geo-workflow" / "reference"))
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
    """Weglänge in Metern berechnen (WGS84-Varianten (lat, lon), Legacy-API)."""
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


class _MetricFrame:
    """Einmalige metrische Projektion (aeqd) für alle Wege einer Abfrage.

    Statt pro Kandidat/Weg-Paar neu zu projizieren (schwach skaliert),
    werden alle Geometrien einmal in dieselbe metrische Ebene überführt.
    """

    def __init__(self, ways):
        lon_min = lat_min = float("inf")
        lon_max = lat_max = float("-inf")
        counted = 0
        for way in ways:
            for point in way.get("geometry") or []:
                lon = float(point["lon"])
                lat = float(point["lat"])
                lon_min = min(lon_min, lon)
                lon_max = max(lon_max, lon)
                lat_min = min(lat_min, lat)
                lat_max = max(lat_max, lat)
                counted += 1
        if counted < 2:
            raise ValueError("Keine Weggeometrien zur Projektion vorhanden")
        center_crs = CRS.from_proj4(
            f"+proj=aeqd +lat_0={(lat_min + lat_max) / 2:.10f} "
            f"+lon_0={(lon_min + lon_max) / 2:.10f} "
            "+datum=WGS84 +units=m +no_defs"
        )
        self._transformer = Transformer.from_crs(
            "EPSG:4326", center_crs, always_xy=True
        )

    def project(self, x, y):
        """Koordinate(n) (lon, lat) metrisch projizieren."""
        return self._transformer.transform(x, y)

    def project_line(self, way):
        """Weggeometrie metrisch projizieren (None bei unter 2 Punkten)."""
        geometry = way.get("geometry") or []
        if len(geometry) < 2:
            return None
        xs = [float(point["lon"]) for point in geometry]
        ys = [float(point["lat"]) for point in geometry]
        mx, my = self.project(xs, ys)
        return LineString(zip(mx, my))

    def project_point(self, lon, lat):
        """Einzelnen Punkt metrisch projizieren."""
        mx, my = self.project(float(lon), float(lat))
        return (float(mx), float(my))

    def project_shape(self, geometry):
        """Beliebige Shapely-Geometrie metrisch projizieren."""
        return shapely_transform(self.project, geometry)


def _parallel_share(candidate_line, traffic_line, buffer_m, sample_step_m=25):
    """Anteil der Probe-Punkte (metrisch, alle 25 m) mit Verkehr im Puffer.

    Anteilsschwelle: <= 35 % mit Verkehr im Puffer bedeutet isoliert,
    mehr bedeutet: parallel belastet (reference/kriterien.md).
    """
    length = candidate_line.length
    if length <= 0:
        return 0.0
    if length <= sample_step_m * 2:
        samples = [candidate_line.interpolate(0.5, normalized=True)]
    else:
        count = max(1, int(length // sample_step_m) - 1)
        samples = [
            candidate_line.interpolate((index + 1) * sample_step_m)
            for index in range(count)
        ]
    close = sum(point.distance(traffic_line) <= buffer_m for point in samples)
    return close / len(samples)


def find_parallel_ways(candidate, all_ways, buffer_m=50, metric=None, tree=None):
    """Parallele Verkehrsmengen im Puffer finden (metrischer Fast-Pfad).

    candidate: dict mit "metric_line" (metrische Linie) und optional "way";
    all_ways: Verkehrsweg-Dicts mit angehängter "_metric_line";
    tree: STRtree über die metrischen Verkehrslinien (Index in all_ways).
    """
    if metric is None or tree is None:
        return []
    competing = []
    buffered = candidate["metric_line"].buffer(buffer_m)
    for index in tree.query(buffered):
        way = all_ways[int(index)]
        if way is candidate.get("way"):
            continue
        fraction = _parallel_share(
            candidate["metric_line"], way["_metric_line"], buffer_m
        )
        if fraction > 0.35:
            competing.append({"id": way.get("id"), "proximity_fraction": fraction})
    return competing


def build_node_owner_index(all_ways):
    """Knoten-ID -> Weg-Dicts Index (einmalig, statt O(N*M)-Vergleiche)."""
    owners = {}
    for way in all_ways:
        for node in way.get("nodes") or []:
            owners.setdefault(node, []).append(way)
    return owners


def find_connections(candidate, all_ways, node_owner=None):
    """Abzweigungen finden (innere Knoten, die mit anderen Wegen geteilt werden).

    Start-/Endknoten (Zugang zur Straße) zählen nicht als Abzweigung.
    candidate: Weg-Dict (oder {"way": obj, "nodes": [...]}) mit Knotenliste.
    """
    own_nodes = candidate.get("nodes") or []
    inner_nodes = set(own_nodes[1:-1])
    if not inner_nodes:
        return []
    if node_owner is None:
        node_owner = build_node_owner_index(all_ways)
    self_reference = candidate.get("way", candidate)
    connections = set()
    for node in inner_nodes:
        for owner in node_owner.get(node, []):
            if owner is not self_reference:
                connections.add(node)
    return sorted(connections)


def _point(value):
    """Start-/Endangabe normalisieren (dict lat/lon, Feature oder Geometrie)."""
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
    """Fußweg-Kandidaten find_filtern (metrischer Fast-Pfad).

    Alle Wege werden einmal in ein gemeinsames metrisches System (aeqd)
    projiziert; Parallelweg-Prüfung läuft danach über einen STRtree.
    Rückgabe: (Kandidaten, Abgelehnte mit Gründen).
    """
    pedestrian = {"footway", "path", "pedestrian", "steps"}
    start_target, end_target = _point(start_near), _point(end_near)
    avoid_shapes = [
        shape(item.get("geometry", item)) for item in (avoid_geometries or [])
    ]

    metric = _MetricFrame(ways)
    wrapped, pedestrian_ways, traffic_ways = [], [], []
    for original in ways:
        highway = original.get("tags", {}).get("highway")
        if not highway:
            continue
        way = dict(original)
        way["_metric_line"] = metric.project_line(way)
        if way["_metric_line"] is None:
            continue
        wrapped.append(way)
        if highway in pedestrian:
            pedestrian_ways.append(way)
        else:
            traffic_ways.append(way)
    traffic_tree = (
        STRtree([way["_metric_line"] for way in traffic_ways]) if traffic_ways else None
    )
    node_owner = build_node_owner_index(wrapped)
    projected_avoids = [metric.project_shape(avoid) for avoid in avoid_shapes]
    end_target_metric = None
    if end_target is not None:
        end_target_metric = metric.project_point(end_target.x, end_target.y)
    start_target_metric = None
    if start_target is not None:
        start_target_metric = metric.project_point(start_target.x, start_target.y)

    candidates, rejected = [], []
    for way in pedestrian_ways:
        candidate_dict = {"way": way, "nodes": way.get("nodes") or []}
        coordinates = [
            (float(point["lon"]), float(point["lat"]))
            for point in way.get("geometry") or []
        ]
        met_line = way["_metric_line"]
        length = float(met_line.length)
        metric_straight = _metric_straightness(met_line)
        reasons = []
        if not min_length <= length <= max_length:
            reasons.append("Länge außerhalb des Fensters")
        if metric_straight < straightness:
            reasons.append("Geradheit unterschritten")
        if not _is_simple(coordinates, met_line):
            reasons.append("Weg besucht einen Punkt mehrfach")
        branches = find_connections(candidate_dict, wrapped, node_owner)
        if branches:
            reasons.append(f"{len(branches)} innere Abzweigungen")
        parallel = find_parallel_ways(
            {"way": way, "metric_line": met_line},
            traffic_ways,
            buffer_m,
            metric,
            traffic_tree,
        )
        if parallel:
            reasons.append(f"Verkehrsweg innerhalb {buffer_m} m")

        # Orientierung: nächstgelegenes Ende soll das Ende sein und im Radius liegen
        if end_target_metric is not None:
            first, last = met_line.coords[0], met_line.coords[-1]
            if point_distance(first, end_target_metric) < point_distance(
                last, end_target_metric
            ):
                coordinates = coordinates[::-1]
                met_line = LineString(
                    [metric.project_point(lon, lat) for lon, lat in coordinates]
                )
            last = met_line.coords[-1]
            if point_distance(last, end_target_metric) > endpoint_radius_m:
                reasons.append("Ende liegt nicht nahe genug am Ziel")
        if (
            start_target_metric is not None
            and point_distance(met_line.coords[0], start_target_metric)
            > endpoint_radius_m
        ):
            reasons.append("Start liegt nicht nahe genug am Ausgangspunkt")
        for avoid in projected_avoids:
            if met_line.distance(avoid) < avoid_distance_m:
                reasons.append(f"Ausschlussobjekt näher als {avoid_distance_m} m")
                break
        if reasons:
            rejected.append({"osm_id": way.get("id"), "reasons": reasons})
            continue
        candidates.append(
            {
                "way": way,
                "metric_line": met_line,
                "coordinates": coordinates,
                "length_m": length,
                "straightness": metric_straight,
                "branches": len(branches),
                "parallel_count": len(parallel),
            }
        )
    candidates.sort(key=lambda item: (item["parallel_count"], -item["straightness"]))
    return candidates, rejected


def _is_simple(coordinates, met_line):
    """Keine doppelten Stützpunkte, keine Selbstüberschneidung (metrisch)."""
    tuples = [(lon, lat) for lon, lat in coordinates]
    if len(set(tuples)) != len(tuples):
        return False
    if met_line.length <= 0:
        return False
    return bool(met_line.is_simple)


def _metric_straightness(met_line):
    """Geradheit auf metrischer Linie: Luftraum / Weglänge."""
    if met_line.length <= 0:
        return 0.0
    first, last = met_line.coords[0], met_line.coords[-1]
    direct = ((last[0] - first[0]) ** 2 + (last[1] - first[1]) ** 2) ** 0.5
    return direct / met_line.length


def point_distance(a, b):
    """Metrische Distanz zweier Koordinatentupel."""
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def find_network_walks(
    ways,
    min_length,
    max_length,
    anchor_points,
    straightness_min=0.6,
    avoid_geometries=None,
    avoid_distance_m=100,
    max_per_anchor=4,
):
    """Topologischer Fußwegegraph: Netzwerkrouten zwischen Wegknoten.

    Einzeln gespeicherte OSM-Ways sind durch Kreuzungen gesplittet, daher
    existieren kaum einzelne Fußwege ab ca. 1 km. Dieser Modus verbindet
    Fußwege über gemeinsame Knoten zu Routen (Dijkstra pro Startanker) und
    wendet danach dieselben Grundkriterien an (einfache Linie, Geradheit,
    Ausschlussgeometrien). Precision bleibt daher "estimated".

    anchor_points: Liste {"lat", "lon", optional "label"} – Startpunkte der
    Routen (z.B. Ride-Hailing-Ausstiegspunkte).
    """
    pedestrian = {"footway", "path", "pedestrian", "steps"}
    metric = _MetricFrame(ways)
    adjacency, node_wgs, node_metric = {}, {}, {}
    for original in ways:
        if original.get("tags", {}).get("highway") not in pedestrian:
            continue
        nodes = original.get("nodes") or []
        geometry = original.get("geometry") or []
        if len(nodes) < 2 or len(nodes) != len(geometry):
            continue
        xs = [float(point["lon"]) for point in geometry]
        ys = [float(point["lat"]) for point in geometry]
        mx, my = metric.project(xs, ys)
        for index, node in enumerate(nodes):
            node_wgs[node] = (xs[index], ys[index])
            node_metric[node] = (mx[index], my[index])
        for index in range(len(nodes) - 1):
            start, end = nodes[index], nodes[index + 1]
            length = math.hypot(mx[index + 1] - mx[index], my[index + 1] - my[index])
            adjacency.setdefault(start, []).append((end, length))
            adjacency.setdefault(end, []).append((start, length))
    if not adjacency:
        return [], [{"reason": "Kein Fußwegenetz im Ausschnitt"}]

    projected_avoids = [
        metric.project_shape(shape(geom))
        for geom in avoid_shapes_list(avoid_geometries)
    ]
    candidates, rejected = [], []
    for anchor in anchor_points:
        label = anchor.get("label") or f"anchor"
        start_metric = metric.project_point(float(anchor["lon"]), float(anchor["lat"]))
        best_node, best_dist = None, float("inf")
        for node, coordinate in node_metric.items():
            delta = (coordinate[0] - start_metric[0], coordinate[1] - start_metric[1])
            delta_sq = delta[0] * delta[0] + delta[1] * delta[1]
            if delta_sq < best_dist:
                best_node, best_dist = node, delta_sq
        if best_node is None:
            rejected.append({"anchor": label, "reason": "Kein Netzwerkknoten gefunden"})
            continue
        dist, pred = _dijkstra_bounded(adjacency, best_node, max_length)
        terminals = [
            node
            for node, value in dist.items()
            if min_length <= value <= max_length and node != best_node
        ]
        scored = []
        for node in terminals:
            path = _reconstruct_path(pred, best_node, node)
            coords_metric = [node_metric[node] for node in path]
            met_line = LineString(coords_metric)
            straight = _metric_straightness(met_line)
            if straight < straightness_min:
                continue
            if not bool(met_line.is_simple):
                continue
            too_close = any(
                met_line.distance(avoid) < avoid_distance_m
                for avoid in projected_avoids
            )
            if too_close:
                continue
            scored.append(
                {
                    "straightness": straight,
                    "length_m": dist[node],
                    "end_node": node,
                    "path": path,
                }
            )
        scored.sort(key=lambda item: -item["straightness"])
        for item in scored[:max_per_anchor]:
            coordinates = [node_wgs[node] for node in item["path"]]
            candidates.append(
                {
                    "candidate_id": f"osm:route:{label}-{item['end_node']}",
                    "way": None,
                    "anchor": label,
                    "coordinates": coordinates,
                    "length_m": item["length_m"],
                    "straightness": item["straightness"],
                    "branches": 0,
                    "parallel_count": 0,
                    "mode": "network",
                }
            )
    candidates.sort(key=lambda item: -item["straightness"])
    return candidates, rejected


def avoid_shapes_list(avoid_geometries):
    """Ausschlussgeometrien als Shapely-Objekte normalisieren."""
    return [shape(item.get("geometry", item)) for item in (avoid_geometries or [])]


def _dijkstra_bounded(adjacency, start, max_length):
    """Dijkstra mit Längen-Obergrenze; Rückgabe (dist, pred)."""
    dist = {start: 0.0}
    pred = {}
    heap = [(0.0, start)]
    while heap:
        current, node = heapq.heappop(heap)
        if current > dist.get(node, float("inf")):
            continue
        for neighbor, edge_length in adjacency.get(node, []):
            value = current + edge_length
            if value > max_length:
                continue
            if value < dist.get(neighbor, float("inf")):
                dist[neighbor] = value
                pred[neighbor] = node
                heapq.heappush(heap, (value, neighbor))
    return dist, pred


def _reconstruct_path(pred, start, end):
    """Pfadkette vom Startknoten zum Endknoten rekonstruieren."""
    path, node, guard = [], end, 0
    while node is not None and guard <= 100000:
        path.append(node)
        if node == start:
            break
        node = pred.get(node)
        guard += 1
    path.reverse()
    return path


def export_candidates(
    candidates, output, walking_speed_m_min=75, parameters=None, rejected=None
):
    """Kandidaten als GeoJSON/KML/GPX plus status.json exportieren."""
    features = []
    for item in candidates:
        coordinates = item["coordinates"]
        duration = item["length_m"] / walking_speed_m_min
        start = {"lat": coordinates[0][1], "lon": coordinates[0][0]}
        end = {"lat": coordinates[-1][1], "lon": coordinates[-1][0]}
        candidate_id = item.get("candidate_id") or f"osm:way:{item['way'].get('id')}"
        features.append(
            candidate_feature(
                candidate_id=candidate_id,
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
                confidence=0.6 if item.get("mode") == "network" else 0.7,
                sources=[
                    {
                        "name": "OpenStreetMap",
                        "id": (
                            f"way/{item['way'].get('id')}"
                            if item.get("way")
                            else item.get("candidate_id")
                        ),
                    }
                ],
                warnings=[f"Gehzeit mit {walking_speed_m_min} m/min geschätzt"],
                extra={
                    "length_m": item["length_m"],
                    "straightness": item["straightness"],
                    "branches": item["branches"],
                    "parallel_count": item["parallel_count"],
                    "walk_mode": item.get("mode", "isolated"),
                    "anchor": item.get("anchor"),
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
    if parameters.get("walk_mode") == "network":
        anchor_points = parameters.get("anchor_points") or []
        if not anchor_points:
            raise SystemExit(
                "Netzwerkmodus benötigt parameters.anchor_points "
                "(z.B. Ride-Hailing-Ausstiegspunkte)"
            )
        candidates, rejected = find_network_walks(
            ways,
            args.min_length,
            args.max_length,
            anchor_points,
            straightness_min=float(parameters.get("straightness_min", 0.6)),
            avoid_geometries=parameters.get("avoid_geometries"),
            avoid_distance_m=float(parameters.get("avoid_distance_m", 100)),
            max_per_anchor=int(parameters.get("max_per_anchor", 4)),
        )
    else:
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
