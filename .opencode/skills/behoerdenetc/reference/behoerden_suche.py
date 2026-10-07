#!/usr/bin/env python3
"""
Behörden, Polizei & Botschaften finden – Kombinierte Quellen
1. Region analysieren und Datenquellen prüfen
2. Daten abrufen (OSM + Register/Open Data + Wikidata)
3. Daten zusammenführen und bereinigen
4. Ergebnis exportieren (GeoJSON, KML, GPX, JSON)

Skriptvorlage: Abruf-, Merge- und Export-Struktur.
- Ablauf: SKILL.md (Prozess, Schritte 1-9, inkl. Learnings-Loop)
- Endpunkte, Filter, Abfrageregeln: reference/datenquellen.md
- Merge, Name, Kategorie, Koordinaten: reference/merge-regeln.md
- Landesspezifisches: reference/<land>.md
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

# Standard-Filter (SKILL.md, Phase 2)
OSM_FILTERS = [
    ("amenity", "police"),
    ("amenity", "townhall"),
    ("amenity", "embassy"),
    ("amenity", "courthouse"),
    ("amenity", "public_building"),
    ("amenity", "fire_station"),
    ("office", "government"),
    ("office", "diplomatic"),
    ("office", "tax"),
    ("building", "government"),
]

# Open Data Portale (Beispiele, erweitern nach Bedarf)
OPEN_DATA_PORTALS = {
    "wien": "https://www.data.gv.at/katalog/dataset?tags=beh%C3%B6rden",
    "berlin": "https://daten.berlin.de/",
    "london": "https://data.gov.uk/",
    "new york": "https://opendata.cityofnewyork.us/",
    # Weitere Städte hier hinzufügen
}


def check_open_data_availability(city):
    """Prüfe, ob Open Data für die Stadt verfügbar ist."""
    city_lower = city.lower()
    for key, portal in OPEN_DATA_PORTALS.items():
        if key in city_lower:
            return portal
    return None


def fetch_osm_data(bbox=None, place=None):
    """OSM-Daten von der Overpass API abrufen."""
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


def fetch_wikidata(place, qid=None):
    """Wikidata via SPARQL abfragen.

    Klassen-QIDs nie raten – vorher verifizieren
    (`SELECT ?x WHERE { ?x wdt:P31 wd:QID } LIMIT 3`), erprobte Liste in
    reference/niederlande.md §3. Ort per --qid oder Labelsuche auflösen.
    """
    if qid:
        place_filter = f"      ?item wdt:P131* wd:{qid} ."
    else:
        place_filter = f'      ?item rdfs:label "{place}"@en .  # mit Länder-Constraint (wdt:P17)'
    query = f"""
    SELECT ?item ?itemLabel ?coord ?address WHERE {{
{place_filter}
      ?item wdt:P31/wdt:P279* ?klasse .
      VALUES ?klasse {{ wd:Q861951 wd:Q3917681 wd:Q372690 wd:Q16831714
                        wd:Q1137809 wd:Q327333 wd:Q2659904 }}
      OPTIONAL {{ ?item wdt:P625 ?coord . }}
      OPTIONAL {{ ?item wdt:P6375 ?address . }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "de,en,nl". }}
    }}
    LIMIT 200
    """
    # TODO: Anfrage senden (format=json), Rauschfilter anwenden
    #       (reference/niederlande.md §3), Koordinaten als Point(lon lat) parsen


def merge_and_deduplicate(osm_data, open_data, wikidata):
    """Daten zusammenführen und Duplikate entfernen.

    - Nur bei Namensähnlichkeit mergen, nie allein über Distanz
      (gleiche Adresse kann getrennte Träger haben).
    - Schwellen aus der Landes-Referenz, z. B. NL: sim >= 0.88 und <= 250 m,
      oder <= 150 m und sim >= 0.45.
    - Offizieller Registernamen kanonisch, OSM/Wikidata-Namen als alias.
    """
    # TODO: Implementierung


def main():
    parser = argparse.ArgumentParser(description="Behörden, Polizei & Botschaften finden")
    parser.add_argument("--place", type=str, help="Stadt oder Stadtteil (z.B. 'Wien, Österreich')")
    parser.add_argument("--bbox", type=float, nargs=4, metavar=("S", "W", "N", "E"), help="Bounding Box")
    parser.add_argument("--qid", type=str, help="Wikidata-QID des Ortes (nie raten, siehe Landes-Referenz)")
    parser.add_argument("--register-city", type=str, help="Stadtname für Register-/Open-Data-Filter")
    parser.add_argument("--output", type=str, default="ergebnis", help="Ausgabeverzeichnis")

    args = parser.parse_args()

    # Phase 1: Region analysieren (Referenz lesen, Stadtgrenze per Nominatim)
    open_data_portal = check_open_data_availability(args.place or "")

    # Phase 2: Daten abrufen
    osm_data = fetch_osm_data(args.bbox, args.place)
    wikidata = fetch_wikidata(args.place, args.qid)

    # Phase 3: Zusammenführen
    merged = merge_and_deduplicate(osm_data, open_data_portal, wikidata)

    # Phase 4: Export (ergebnis.geojson/kml/gpx + zusammenfassung.json)
    # ...


if __name__ == "__main__":
    main()
