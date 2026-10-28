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
import sys
from pathlib import Path

OPENCODE_DIR = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(OPENCODE_DIR / "lib"))
sys.path.insert(0, str(OPENCODE_DIR / "skills" / "geo-workflow" / "reference"))
from exporter import write_gpx, write_kml  # noqa: E402
from workflow_adapter import (  # noqa: E402
    candidate_feature,
    element_geometry,
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
    if not bbox and place:
        bbox, _ = resolve_region(place)
    if not bbox:
        raise ValueError("--place oder --bbox erforderlich")
    bbox_str = f"({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]})"

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
    return overpass(query).get("elements", [])


def fetch_wikidata(place, qid=None):
    """Wikidata via SPARQL abfragen.

    Klassen-QIDs nie raten – vorher verifizieren
    (`SELECT ?x WHERE { ?x wdt:P31 wd:QID } LIMIT 3`), erprobte Liste in
    reference/niederlande.md §3. Ort per --qid oder Labelsuche auflösen.
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
    merged = {}
    for element in osm_data or []:
        geometry = element_geometry(element)
        if not geometry:
            continue
        tags = element.get("tags") or {}
        key = (element.get("type"), element.get("id"))
        merged[key] = {
            "id": f"osm:{key[0]}:{key[1]}",
            "name": tags.get("name")
            or tags.get("operator")
            or "Unbenannte Einrichtung",
            "category": tags.get("amenity")
            or tags.get("office")
            or tags.get("building")
            or "government",
            "geometry": geometry,
            "tags": tags,
            "source": "OpenStreetMap",
        }
    # Register und Wikidata werden erst gemergt, wenn die jeweilige Quelle
    # strukturierte Datensätze geliefert hat. Ein Portal-Link ist kein Fund.
    return list(merged.values())


def normalized_features(items):
    features = []
    for item in items:
        tags = item["tags"]
        corroboration = int(bool(tags.get("website"))) + int(bool(tags.get("operator")))
        confidence = min(0.9, 0.55 + 0.1 * corroboration)
        features.append(
            candidate_feature(
                candidate_id=item["id"],
                producer_skill="behoerdenetc",
                entity_type="authority_place",
                geometry=item["geometry"],
                score=confidence,
                confidence=confidence,
                sources=[{"name": "OpenStreetMap", "id": item["id"]}],
                extra={
                    "name": item["name"],
                    "category": item["category"],
                    "opening_hours": tags.get("opening_hours"),
                    "public_access": tags.get("access"),
                },
            )
        )
    return features


def export_standalone(features, output, parameters=None):
    directory = Path(output)
    write_adapter_output(
        directory,
        features,
        sources=[{"name": "OpenStreetMap"}],
        parameters=parameters or {},
    )
    (directory / "ergebnis.geojson").write_text(
        (directory / "kandidaten.geojson").read_text(encoding="utf-8"), encoding="utf-8"
    )
    write_kml(features, directory / "ergebnis.kml")
    write_gpx(features, directory / "ergebnis.gpx")
    (directory / "zusammenfassung.json").write_text(
        json.dumps(
            {"candidate_count": len(features), "sources": ["OpenStreetMap"]},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def main():
    parser = argparse.ArgumentParser(
        description="Behörden, Polizei & Botschaften finden"
    )
    parser.add_argument(
        "--place", type=str, help="Stadt oder Stadtteil (z.B. 'Wien, Österreich')"
    )
    parser.add_argument(
        "--bbox", type=float, nargs=4, metavar=("S", "W", "N", "E"), help="Bounding Box"
    )
    parser.add_argument(
        "--qid",
        type=str,
        help="Wikidata-QID des Ortes (nie raten, siehe Landes-Referenz)",
    )
    parser.add_argument(
        "--register-city", type=str, help="Stadtname für Register-/Open-Data-Filter"
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
    if request:
        parameters = request["parameters"]
        bbox, place = resolve_region(parameters["region"])
        args.bbox = bbox
        args.place = place
    elif not args.place and not args.bbox:
        parser.error("--place, --bbox oder --request erforderlich")

    # Phase 1: Region analysieren (Referenz lesen, Stadtgrenze per Nominatim)
    open_data_portal = check_open_data_availability(args.place or "")

    # Phase 2: Daten abrufen
    osm_data = fetch_osm_data(args.bbox, args.place)
    wikidata = None

    # Phase 3: Zusammenführen
    merged = merge_and_deduplicate(osm_data, open_data_portal, wikidata)

    # Phase 4: normalisierter Export; Register-/Wikidata-Fallbacks werden im
    # Status nicht als Treffer ausgegeben, solange sie nicht implementiert sind.
    features = normalized_features(merged)
    categories = set((request or {}).get("parameters", {}).get("categories") or [])
    if categories:
        features = [
            feature
            for feature in features
            if feature["properties"]["category"] in categories
        ]
    export_standalone(features, args.output, (request or {}).get("parameters", {}))


if __name__ == "__main__":
    main()
