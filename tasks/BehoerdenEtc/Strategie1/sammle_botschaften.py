"""
Sammelt Botschaften und Konsulate in Wien aus OSM (office=diplomatic)
"""

import requests
import json
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "daten"
OUTPUT_DIR.mkdir(exist_ok=True)

OVERPASS_SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

def fetch_botschaften():
    """Botschaften aus OSM abrufen"""
    print("=== Lade Botschaften aus OSM ===")
    
    query = """
    [out:json][timeout:60];
    (
      node["office"="diplomatic"](48.11,16.17,48.33,16.58);
      way["office"="diplomatic"](48.11,16.17,48.33,16.58);
    );
    out center;
    """
    
    headers = {
        "User-Agent": "GeoStructuresBot/1.0 (research project)"
    }
    
    data = None
    for server in OVERPASS_SERVERS:
        try:
            response = requests.post(server, data={"data": query}, headers=headers, timeout=120)
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
    
    elements = data.get('elements', [])
    results = []
    
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
        if tags.get('diplomatic') == 'embassy':
            kategorie = 'Botschaft'
        elif tags.get('diplomatic') == 'consulate':
            kategorie = 'Konsulat'
        else:
            kategorie = 'Botschaft'
        
        results.append({
            'name': tags.get('name', 'Unbekannt'),
            'kategorie': kategorie,
            'lat': lat,
            'lon': lon,
            'quelle': 'OSM',
            'tags': tags
        })
    
    print(f"  {len(results)} Botschaften/Konsulate gefunden")
    
    # Speichern
    with open(OUTPUT_DIR / "botschaften.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    return results

if __name__ == "__main__":
    fetch_botschaften()
