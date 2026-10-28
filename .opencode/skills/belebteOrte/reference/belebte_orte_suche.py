#!/usr/bin/env python3
"""
Belebte Orte finden – Kombinierte Quellen
1. Region analysieren und Datenquellen prüfen
2. Daten abrufen (OSM POI-Dichte + ÖPNV/GTFS + Events + Wikidata)
3. Daten zusammenführen, nach Belebtheit bewerten und bereinigen
4. Ergebnis exportieren (GeoJSON, KML, GPX, JSON)

Skriptvorlage: Abruf-, Merge- und Export-Struktur.
- Ablauf: SKILL.md (Prozess, Schritte 1-10, inkl. Learnings-Loop)
- Endpunkte, Filter, Abfrageregeln: reference/datenquellen.md
- Merge, Name, Kategorie, Koordinaten: reference/merge-regeln.md
- Stadtspezifisches: reference/<stadt>.md
"""

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

OPENCODE_DIR = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(OPENCODE_DIR / "lib"))
sys.path.insert(0, str(OPENCODE_DIR / "skills" / "geo-workflow" / "reference"))
from exporter import write_gpx, write_kml  # noqa: E402
from workflow_adapter import (  # noqa: E402
    candidate_feature,
    element_point,
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

WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"

# Standard-Filter für belebte Orte (SKILL.md, Phase 2)
OSM_FILTERS = [
    ("shop", "*"),
    ("amenity", "cafe"),
    ("amenity", "restaurant"),
    ("amenity", "bar"),
    ("amenity", "pub"),
    ("amenity", "fast_food"),
    ("amenity", "ice_cream"),
    ("amenity", "food_court"),
    ("amenity", "marketplace"),
    ("amenity", "theatre"),
    ("amenity", "cinema"),
    ("amenity", "museum"),
    ("amenity", "library"),
    ("amenity", "community_culture"),
    ("amenity", "arts_culture"),
    ("amenity", "bank"),
    ("amenity", "atm"),
    ("amenity", "pharmacy"),
    ("amenity", "post_office"),
    ("amenity", "police"),
    ("amenity", "fire_station"),
    ("amenity", "hospital"),
    ("amenity", "clinic"),
    ("public_transport", "platform"),
    ("public_transport", "stop_position"),
    ("railway", "station"),
    ("railway", "tram_stop"),
    ("railway", "subway_entrance"),
    ("leisure", "park"),
    ("leisure", "playground"),
    ("leisure", "stadium"),
    ("leisure", "sports_centre"),
    ("leisure", "track"),
    ("leisure", "pitch"),
    ("leisure", "golf_course"),
    ("leisure", "marina"),
    ("tourism", "hotel"),
    ("tourism", "hostel"),
    ("tourism", "guest_house"),
    ("tourism", "information"),
    ("tourism", "viewpoint"),
    ("tourism", "attraction"),
    ("tourism", "artwork"),
    ("office", "*"),
]

# GTFS-Feeds (Beispiele, erweitern nach Bedarf)
GTFS_FEEDS = {
    "berlin": "https://www.vbb.de/media/download/2024",
    "hamburg": "https://www.hvv.de/de/fahrplaene/fahrplanauskunft/fahrplandaten",
    "wien": "https://www.wienerlinien.at/ogd_realtime/",
    # Weitere Städte hier hinzufügen
}

# Event-Portale (Beispiele, erweitern nach Bedarf)
EVENT_PORTALS = {
    "berlin": "https://www.berlin.de/events/",
    "wien": "https://www.wien.gv.at/veranstaltungen/",
    "hamburg": "https://www.hamburg.de/events/",
    # Weitere Städte hier hinzufügen
}


def check_gtfs_availability(city):
    """Prüfe, ob GTFS-Daten für die Stadt verfügbar sind."""
    city_lower = city.lower()
    for key, feed in GTFS_FEEDS.items():
        if key in city_lower:
            return feed
    return None


def check_event_portal_availability(city):
    """Prüfe, ob ein Event-Portal für die Stadt verfügbar ist."""
    city_lower = city.lower()
    for key, portal in EVENT_PORTALS.items():
        if key in city_lower:
            return portal
    return None


def fetch_osm_data(bbox=None, place=None):
    """OSM-Daten von der Overpass API abrufen (POI-Dichte)."""
    if not bbox and place:
        bbox, _ = resolve_region(place)
    if not bbox:
        raise ValueError("--place oder --bbox erforderlich")
    bbox_str = f"({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]})"

    selectors = "\n".join(
        (
            f'      {el}["{key}"]{bbox_str};'
            if value == "*"
            else f'      {el}["{key}"="{value}"]{bbox_str};'
        )
        for el in ("node", "way", "relation")
        for key, value in OSM_FILTERS
    )
    query = f"""
    [out:json][timeout:60];
    (
{selectors}
    );
    out center;
    """
    return overpass(query).get("elements", [])


def fetch_gtfs_data(city):
    """GTFS-Daten für ÖPNV-Frequenz abrufen."""
    gtfs_url = check_gtfs_availability(city)
    if not gtfs_url:
        return None
    # TODO: GTFS-Feed herunterladen, stop_times.txt und calendar.txt parsen,
    #       Abfahrten pro Haltestelle und Tag berechnen


def fetch_event_data(city, time_window):
    """Event-Daten für das Zeitfenster abrufen."""
    event_portal = check_event_portal_availability(city)
    if not event_portal:
        return None
    # TODO: Event-Kalender durchsuchen, Events zum Zeitfenster filtern


def fetch_wikidata(place, qid=None):
    """Wikidata via SPARQL abfragen.

    Klassen-QIDs nie raten – vorher verifizieren
    (`SELECT ?x WHERE { ?x wdt:P31 wd:QID } LIMIT 3`), erprobte Liste in
    reference/berlin.md §3. Ort per --qid oder Labelsuche auflösen.
    """
    if qid:
        place_filter = f"      ?item wdt:P131* wd:{qid} ."
    else:
        place_filter = (
            f'      ?item rdfs:label "{place}"@en .  # mit Länder-Constraint (wdt:P17)'
        )
    query = f"""
    SELECT ?item ?itemLabel ?coord ?address WHERE {{
{place_filter}
      ?item wdt:P31/wdt:P279* ?klasse .
      VALUES ?klasse {{ wd:Q16831714 wd:Q1137809 wd:Q327333 wd:Q2659904 }}
      OPTIONAL {{ ?item wdt:P625 ?coord . }}
      OPTIONAL {{ ?item wdt:P6375 ?address . }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "de,en". }}
    }}
    LIMIT 200
    """
    # TODO: Anfrage senden (format=json), Rauschfilter anwenden
    #       (reference/berlin.md §3), Koordinaten als Point(lon lat) parsen


def merge_and_deduplicate(osm_data, gtfs_data, event_data, wikidata):
    """Daten zusammenführen, Duplikate entfernen und Belebtheit bewerten.

    - Nur bei Namensähnlichkeit mergen, nie allein über Distanz
      (gleiche Adresse kann verschiedene Orte haben).
    - Schwellen aus der Stadt-Referenz, z. B. Berlin: sim >= 0.88 und <= 250 m,
      oder <= 150 m und sim >= 0.45.
    - Offizieller Name kanonisch, OSM/Wikidata-Namen als alias.
    - Belebtheit: OSM POI-Dichte + ÖPNV-Frequenz + Events + Google Popular Times
    """
    # Günstige erste Stufe: POIs in ungefähr 250-m-Zellen clustern. Das ist ein
    # Aktivitätsproxy, keine Besucherzählung. Teurere Quellen können später als
    # weitere Score-Komponenten ergänzt werden.
    cells = defaultdict(list)
    for element in osm_data or []:
        point = element_point(element)
        if not point:
            continue
        lon, lat = point
        lat_step = 0.00225
        lon_step = lat_step / max(0.2, math.cos(math.radians(lat)))
        key = (round(lat / lat_step), round(lon / lon_step))
        cells[key].append((element, point))
    clusters = []
    for members in cells.values():
        lon = sum(point[0] for _, point in members) / len(members)
        lat = sum(point[1] for _, point in members) / len(members)
        categories = Counter()
        names = []
        for element, _ in members:
            tags = element.get("tags") or {}
            category = next(
                (
                    tags[key]
                    for key in (
                        "amenity",
                        "shop",
                        "tourism",
                        "leisure",
                        "railway",
                        "office",
                    )
                    if tags.get(key)
                ),
                "other",
            )
            categories[category] += 1
            if tags.get("name"):
                names.append(tags["name"])
        clusters.append(
            {
                "lon": lon,
                "lat": lat,
                "poi_count": len(members),
                "category": categories.most_common(1)[0][0],
                "sample_names": names[:5],
            }
        )
    clusters.sort(key=lambda cluster: cluster["poi_count"], reverse=True)
    maximum = max((cluster["poi_count"] for cluster in clusters), default=1)
    for cluster in clusters:
        cluster["score"] = cluster["poi_count"] / maximum
    return clusters[:100]


def normalized_features(clusters, at):
    moment = parse_assessment_time(at)
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError("at benötigt ISO-8601 mit Zeitzone")
    start, end = moment - timedelta(minutes=30), moment + timedelta(minutes=30)
    features = []
    for index, cluster in enumerate(clusters, 1):
        features.append(
            candidate_feature(
                candidate_id=f"busy-cluster:{index}",
                producer_skill="belebteOrte",
                entity_type="busy_place",
                geometry={
                    "type": "Point",
                    "coordinates": [cluster["lon"], cluster["lat"]],
                },
                score=cluster["score"],
                confidence=0.45,
                sources=[{"name": "OpenStreetMap", "signal": "POI density"}],
                temporal={
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "duration_minutes": 60,
                    "timezone": str(moment.tzinfo),
                    "precision": "estimated",
                },
                warnings=[
                    "POI-Dichte ist ein zeitlich schwacher Aktivitätsproxy, keine Besucherzählung"
                ],
                extra={
                    "poi_count": cluster["poi_count"],
                    "dominant_category": cluster["category"],
                    "sample_names": cluster["sample_names"],
                    "score_components": {"osm_poi_density": cluster["score"]},
                },
            )
        )
    return features


def parse_assessment_time(value):
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("Zeit benötigt eine Zeitzone")
        return parsed
    except ValueError as iso_error:
        parts = value.lower().split()
        weekdays = {
            "monday": 0,
            "montag": 0,
            "tuesday": 1,
            "dienstag": 1,
            "wednesday": 2,
            "mittwoch": 2,
            "thursday": 3,
            "donnerstag": 3,
            "friday": 4,
            "freitag": 4,
            "saturday": 5,
            "samstag": 5,
            "sunday": 6,
            "sonntag": 6,
        }
        if len(parts) != 2 or parts[0] not in weekdays:
            raise ValueError(
                "Zeit muss ISO-8601 mit Zeitzone oder 'Wochentag HH:MM' sein"
            ) from iso_error
        hour, minute = map(int, parts[1].split(":"))
        now = datetime.now().astimezone()
        days = (weekdays[parts[0]] - now.weekday()) % 7
        return (now + timedelta(days=days)).replace(
            hour=hour, minute=minute, second=0, microsecond=0
        )


def export_features(features, output, parameters):
    warning = "Zeitbezogene Bewertung nutzt derzeit nur POI-Dichte als Proxy"
    write_adapter_output(
        output,
        features,
        status="degraded",
        warnings=[warning],
        sources=[{"name": "OpenStreetMap", "signal": "POI density"}],
        parameters=parameters,
    )
    directory = Path(output)
    (directory / "ergebnis.geojson").write_text(
        (directory / "kandidaten.geojson").read_text(encoding="utf-8"), encoding="utf-8"
    )
    write_kml(features[:30], directory / "ergebnis.kml")
    write_gpx(features[:30], directory / "ergebnis.gpx")
    (directory / "zusammenfassung.json").write_text(
        json.dumps(
            {
                "candidate_count": len(features),
                "status": "degraded",
                "score_components": ["osm_poi_density"],
                "missing_components": ["passenger_counts", "events", "popular_times"],
                "warning": warning,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def main():
    parser = argparse.ArgumentParser(description="Belebte Orte finden")
    parser.add_argument(
        "--place", type=str, help="Stadt oder Stadtteil (z.B. 'Berlin, Deutschland')"
    )
    parser.add_argument(
        "--bbox", type=float, nargs=4, metavar=("S", "W", "N", "E"), help="Bounding Box"
    )
    parser.add_argument(
        "--time", type=str, help="Zeitfenster (z.B. 'tuesday 10:00', 'samstag 14:00')"
    )
    parser.add_argument(
        "--qid",
        type=str,
        help="Wikidata-QID des Ortes (nie raten, siehe Stadt-Referenz)",
    )
    parser.add_argument(
        "--output", type=str, default="ergebnis", help="Ausgabeverzeichnis"
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
        args.bbox, args.place = resolve_region(parameters["region"])
        args.time = parameters["at"]
    if not args.place and not args.bbox:
        parser.error("--place, --bbox oder --request erforderlich")
    if not args.time:
        parser.error("--time oder parameters.at erforderlich")

    # Phase 1: Region analysieren (Referenz lesen, Stadtgrenze per Nominatim)
    gtfs_url = check_gtfs_availability(args.place or "")
    event_portal = check_event_portal_availability(args.place or "")

    # Phase 2: Daten abrufen
    osm_data = fetch_osm_data(args.bbox, args.place)
    gtfs_data = fetch_gtfs_data(args.place)
    event_data = fetch_event_data(args.place, args.time)
    wikidata = None

    # Phase 3: Zusammenführen und Belebtheit bewerten
    merged = merge_and_deduplicate(osm_data, gtfs_data, event_data, wikidata)

    # Phase 4: Export mit transparenter Proxy-Kennzeichnung
    features = normalized_features(merged, args.time)
    minimum_score = float(parameters.get("minimum_score", 0))
    features = [
        feature
        for feature in features
        if feature["properties"]["score"] >= minimum_score
    ]
    export_features(features, args.output, parameters)


if __name__ == "__main__":
    main()
