"""
Strategie 4: Kombination mehrerer Datenquellen
Sammelt Behörden, Polizeidienststellen und Botschaften in Wien aus:
1. OpenStreetMap (Overpass API)
2. Open Data Wien
3. Wikidata
"""

import requests
import json
import os
from pathlib import Path

# Ausgabeverzeichnis
OUTPUT_DIR = Path(__file__).parent / "daten"
OUTPUT_DIR.mkdir(exist_ok=True)

WIEN_BOUNDS = {
    "south": 48.11,
    "west": 16.17,
    "north": 48.33,
    "east": 16.58
}

HEADERS = {
    "User-Agent": "GeoStructuresBot/1.0 (research project; contact: localhost)"
}

OVERPASS_SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

def fetch_osm_data():
    """Daten aus OpenStreetMap via Overpass API abrufen"""
    print("=== Lade OSM-Daten ===")
    
    # Overpass QL Query für Polizei, Botschaften, Behörden in Wien
    query = f"""
    [out:json][timeout:60];
    (
      node["amenity"="police"]({WIEN_BOUNDS['south']},{WIEN_BOUNDS['west']},{WIEN_BOUNDS['north']},{WIEN_BOUNDS['east']});
      way["amenity"="police"]({WIEN_BOUNDS['south']},{WIEN_BOUNDS['west']},{WIEN_BOUNDS['north']},{WIEN_BOUNDS['east']});
      node["amenity"="embassy"]({WIEN_BOUNDS['south']},{WIEN_BOUNDS['west']},{WIEN_BOUNDS['north']},{WIEN_BOUNDS['east']});
      way["amenity"="embassy"]({WIEN_BOUNDS['south']},{WIEN_BOUNDS['west']},{WIEN_BOUNDS['north']},{WIEN_BOUNDS['east']});
      node["office"="government"]({WIEN_BOUNDS['south']},{WIEN_BOUNDS['west']},{WIEN_BOUNDS['north']},{WIEN_BOUNDS['east']});
      way["office"="government"]({WIEN_BOUNDS['south']},{WIEN_BOUNDS['west']},{WIEN_BOUNDS['north']},{WIEN_BOUNDS['east']});
      node["building"="government"]({WIEN_BOUNDS['south']},{WIEN_BOUNDS['west']},{WIEN_BOUNDS['north']},{WIEN_BOUNDS['east']});
      way["building"="government"]({WIEN_BOUNDS['south']},{WIEN_BOUNDS['west']},{WIEN_BOUNDS['north']},{WIEN_BOUNDS['east']});
    );
    out center;
    """
    
    data = None
    for server in OVERPASS_SERVERS:
        try:
            response = requests.post(
                server, 
                data={"data": query}, 
                headers=HEADERS,
                timeout=120
            )
            response.raise_for_status()
            data = response.json()
            print(f"  Erfolg mit Server: {server}")
            break
        except Exception as e:
            print(f"  Fehler mit {server}: {e}")
            continue
    
    if data is None:
        print("  Alle Overpass-Server fehlgeschlagen!")
        return []
    
    # Speichern
    with open(OUTPUT_DIR / "osm_rohdaten.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"  {len(data.get('elements', []))} Elemente gefunden")
    return data.get('elements', [])

def parse_osm_elements(elements):
    """OSM-Elemente in einheitliches Format umwandeln"""
    parsed = []
    
    for elem in elements:
        tags = elem.get('tags', {})
        elem_type = elem.get('type')
        
        # Koordinaten bestimmen
        if elem_type == 'node':
            lat, lon = elem.get('lat'), elem.get('lon')
        else:  # way
            center = elem.get('center', {})
            lat, lon = center.get('lat'), center.get('lon')
        
        if lat is None or lon is None:
            continue
        
        # Kategorie bestimmen
        if tags.get('amenity') == 'police':
            kategorie = 'Polizei'
        elif tags.get('amenity') == 'embassy':
            kategorie = 'Botschaft'
        elif tags.get('office') == 'government' or tags.get('building') == 'government':
            kategorie = 'Behörde'
        else:
            continue
        
        parsed.append({
            'name': tags.get('name', 'Unbekannt'),
            'kategorie': kategorie,
            'lat': lat,
            'lon': lon,
            'quelle': 'OSM',
            'tags': tags
        })
    
    return parsed

def fetch_wikidata_botschaften():
    """Botschaften aus Wikidata abrufen"""
    print("=== Lade Wikidata-Botschaften ===")
    
    wikidata_url = "https://query.wikidata.org/sparql"
    
    # SPARQL Query für Botschaften in Wien (diplomatic missions)
    query = """
    SELECT ?item ?itemLabel ?coord WHERE {
      ?item wdt:P31/wdt:P279* wd:Q7843791 .
      ?item wdt:P131* wd:Q1741 .
      ?item wdt:P625 ?coord .
      SERVICE wikibase:label { bd:serviceParam wikibase:language "de,en". }
    }
    LIMIT 500
    """
    
    headers = {
        "User-Agent": "GeoStructuresBot/1.0 (research project)",
        "Accept": "application/sparql-results+json"
    }
    
    try:
        response = requests.get(wikidata_url, params={"query": query}, headers=headers, timeout=60)
        response.raise_for_status()
        data = response.json()
        
        results = []
        for binding in data.get('results', {}).get('bindings', []):
            coord = binding.get('coord', {}).get('value', '')
            # Parse Point(lon lat) Format
            if coord.startswith('Point('):
                parts = coord.replace('Point(', '').replace(')', '').split()
                lon, lat = float(parts[0]), float(parts[1])
                results.append({
                    'name': binding.get('itemLabel', {}).get('value', 'Unbekannt'),
                    'kategorie': 'Botschaft',
                    'lat': lat,
                    'lon': lon,
                    'quelle': 'Wikidata'
                })
        
        print(f"  {len(results)} Botschaften gefunden")
        return results
    except Exception as e:
        print(f"  Fehler: {e}")
        return []

def fetch_open_data_wien():
    """Open Data von data.wien.gv.at prüfen"""
    print("=== Prüfe Open Data Wien ===")
    
    # Bekannte Datensätze auf data.wien.gv.at
    # Polizeidienststellen: https://www.data.gv.at/katalog/dataset/polizeidienststellen-wien
    datasets = {
        'polizei': 'https://www.wien.gv.at/ogd/polizeidienststellen.csv',
    }
    
    results = []
    
    # Polizeidienststellen versuchen
    try:
        response = requests.get(datasets['polizei'], timeout=30)
        if response.status_code == 200:
            print("  Polizeidienststellen-Daten gefunden")
            # CSV parsen würde hier folgen
        else:
            print(f"  Polizei-Daten nicht verfügbar (Status: {response.status_code})")
    except Exception as e:
        print(f"  Fehler bei Open Data: {e}")
    
    return results

def main():
    print("Starte Datensammlung für Strategie 4\n")
    
    # 1. OSM-Daten
    osm_elements = fetch_osm_data()
    osm_parsed = parse_osm_elements(osm_elements)
    print(f"  OSM: {len(osm_parsed)} relevante Einrichtungen\n")
    
    # 2. Wikidata-Botschaften
    wikidata_results = fetch_wikidata_botschaften()
    print()
    
    # 3. Open Data Wien
    open_data_results = fetch_open_data_wien()
    print()
    
    # Zusammenführen
    alle_daten = osm_parsed + wikidata_results + open_data_results
    
    # Duplikatbereinigung (einfach: gleiche Name + ähnliche Koordinaten)
    gesehen = set()
    eindeutig = []
    for eintrag in alle_daten:
        schluessel = (eintrag['name'].lower().strip(), round(eintrag['lat'], 4), round(eintrag['lon'], 4))
        if schluessel not in gesehen:
            gesehen.add(schluessel)
            eindeutig.append(eintrag)
    
    # Speichern
    with open(OUTPUT_DIR / "einrichtungen_gesamt.json", "w", encoding="utf-8") as f:
        json.dump(eindeutig, f, ensure_ascii=False, indent=2)
    
    # Statistik
    kategorien = {}
    for eintrag in eindeutig:
        kategorien[eintrag['kategorie']] = kategorien.get(eintrag['kategorie'], 0) + 1
    
    print("=== Zusammenfassung ===")
    print(f"Gesamt: {len(eindeutig)} Einrichtungen")
    for kat, count in sorted(kategorien.items()):
        print(f"  {kat}: {count}")
    print(f"\nDaten gespeichert in: {OUTPUT_DIR / 'einrichtungen_gesamt.json'}")

if __name__ == "__main__":
    main()
