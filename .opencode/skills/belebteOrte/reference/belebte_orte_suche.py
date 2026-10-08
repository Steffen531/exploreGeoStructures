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
from datetime import datetime

import requests

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
    if bbox:
        bbox_str = f"({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]})"
    elif place:
        bbox_str = f'area["name"="{place}"]->.searchArea;'
    else:
        raise ValueError("--place oder --bbox erforderlich")

    selectors = "\n".join(
        f'      {el}["{key}"="{value}"]{bbox_str};'
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
    # TODO: Server-Fallback (OVERPASS_SERVERS) mit Backoff, 3 Runden,
    #       Query-Hash in cache/ cachen, Antwort nach GeoJSON konvertieren


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
        place_filter = f'      ?item rdfs:label "{place}"@en .  # mit Länder-Constraint (wdt:P17)'
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
    # TODO: Implementierung


def main():
    parser = argparse.ArgumentParser(description="Belebte Orte finden")
    parser.add_argument("--place", type=str, help="Stadt oder Stadtteil (z.B. 'Berlin, Deutschland')")
    parser.add_argument("--bbox", type=float, nargs=4, metavar=("S", "W", "N", "E"), help="Bounding Box")
    parser.add_argument("--time", type=str, help="Zeitfenster (z.B. 'tuesday 10:00', 'samstag 14:00')")
    parser.add_argument("--qid", type=str, help="Wikidata-QID des Ortes (nie raten, siehe Stadt-Referenz)")
    parser.add_argument("--output", type=str, default="ergebnis", help="Ausgabeverzeichnis")

    args = parser.parse_args()

    # Phase 1: Region analysieren (Referenz lesen, Stadtgrenze per Nominatim)
    gtfs_url = check_gtfs_availability(args.place or "")
    event_portal = check_event_portal_availability(args.place or "")

    # Phase 2: Daten abrufen
    osm_data = fetch_osm_data(args.bbox, args.place)
    gtfs_data = fetch_gtfs_data(args.place)
    event_data = fetch_event_data(args.place, args.time)
    wikidata = fetch_wikidata(args.place, args.qid)

    # Phase 3: Zusammenführen und Belebtheit bewerten
    merged = merge_and_deduplicate(osm_data, gtfs_data, event_data, wikidata)

    # Phase 4: Export (ergebnis.geojson/kml/gpx + zusammenfassung.json)
    # ...


if __name__ == "__main__":
    main()
