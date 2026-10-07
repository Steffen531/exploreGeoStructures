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
from datetime import datetime

import requests
from shapely.geometry import LineString

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
    # ... Implementierung: Strukturtypen aus reference/strukturtypen.md
    #   als Suchvorwissen nutzen
    pass


def fetch_osm_data(bbox=None, place=None):
    """OSM-Daten von der Overpass API abrufen.

    Regeln: eigener User-Agent, keine rekursiven Abfragen großer BBoxen,
    zwei kleine Queries mit `out geom;` (reference/datenquellen.md).
    """
    if bbox:
        bbox_str = f"({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]})"
    elif place:
        # Nominatim für Geocoding (max. 1 Anfrage/s, eigenen UA)
        bbox_str = f'area["name"="{place}"]->.searchArea;'
    else:
        raise ValueError("--place oder --bbox erforderlich")

    query = f"""
    [out:json][timeout:90];
    (
      way["highway"="footway"]{bbox_str};
      way["highway"="path"]{bbox_str};
      way["highway"="pedestrian"]{bbox_str};
      way["highway"="steps"]{bbox_str};
    );
    out geom;
    """
    # TODO: Server-Fallback (OVERPASS_SERVERS) mit Backoff,
    #       Antwort nach GeoJSON konvertieren
    #   r = requests.post(server, data={"data": query}, headers=HEADERS, timeout=150)


def haversine_distance(coord1, coord2):
    """Distanz zwischen zwei Koordinaten in Metern."""
    R = 6371000
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def calculate_length(coords):
    """Weglänge in Metern berechnen."""
    return sum(haversine_distance(coords[i], coords[i + 1]) for i in range(len(coords) - 1))


def calculate_straightness(coords):
    """Geradheit berechnen (1.0 = perfekt gerade). Harter Filter: >= 0.95."""
    if len(coords) < 2:
        return 0.0
    direct = haversine_distance(coords[0], coords[-1])
    actual = calculate_length(coords)
    return direct / actual if actual > 0 else 0.0


def visits_no_point_twice(coords):
    """True, wenn kein Punkt zweimal besucht wird (keine Schlaufe/Selbstkreuzung)."""
    if len(set(coords)) != len(coords):      # doppelte Stützpunkte
        return False
    return LineString(coords).is_simple      # keine Selbstüberschneidung


def find_parallel_ways(candidate, all_ways, buffer_m=50):
    """Parallele Wege im Puffer finden.

    WICHTIG: Puffer/Entfernung nur in metrischem CRS berechnen
    (z.B. UTM 32N via pyproj) – Grad sind keine Meter.
    Anteilsschwellen: <= 35 % der Probe-Punkte (alle 25 m) mit
    Verkehr im Puffer (reference/kriterien.md).
    """
    # ... Implementierung


def find_connections(candidate, all_ways):
    """Abzweigungen finden (innere Knoten, die mit anderen Fußwegen geteilt werden).

    Start-/Endknoten (Zugang zur Straße) zählen nicht als Abzweigung.
    """
    # ... Implementierung


def main():
    parser = argparse.ArgumentParser(description="Isolierte Fußwege finden – Kombinierter Ansatz")
    parser.add_argument("--place", type=str, help="Ort oder Stadt (z.B. 'Hamburg, Deutschland')")
    parser.add_argument("--bbox", type=float, nargs=4, metavar=("S", "W", "N", "E"), help="Bounding Box")
    parser.add_argument("--region-type", type=str, choices=["küste", "berg", "fluss", "park", "altstadt", "insel", "wüste", "see", "industrie", "vorort"], help="Geografischer Regionstyp")
    parser.add_argument("--min-length", type=int, default=600, help="Minimale Länge in Metern")
    parser.add_argument("--max-length", type=int, default=900, help="Maximale Länge in Metern")
    parser.add_argument("--straightness", type=float, default=0.95, help="Minimale Geradheit (0-1), harter Filter")
    parser.add_argument("--buffer", type=int, default=50, help="Puffer für Parallelwege in Metern")
    parser.add_argument("--output", type=str, default="ergebnis", help="Ausgabeverzeichnis")

    args = parser.parse_args()
    # ... Hauplogik (Schritte 4-7 aus SKILL.md)

    # Phase 4: Export (ergebnis.geojson/kml/gpx + zusammenfassung.json)


if __name__ == "__main__":
    main()
