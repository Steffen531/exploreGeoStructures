"""
Wikidata-Botschaften abrufen (einfachere Query)
"""

import requests
import json
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "daten"
OUTPUT_DIR.mkdir(exist_ok=True)

def fetch_wikidata_botschaften():
    """Botschaften aus Wikidata abrufen"""
    print("=== Lade Wikidata-Botschaften ===")
    
    wikidata_url = "https://query.wikidata.org/sparql"
    
    # Einfachere Query: Botschaften in Österreich
    query = """
    SELECT ?item ?itemLabel ?coord WHERE {
      ?item wdt:P31 wd:Q7843791 .
      ?item wdt:P17 wd:Q40 .
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
        response = requests.get(wikidata_url, params={"query": query}, headers=headers, timeout=120)
        response.raise_for_status()
        data = response.json()
        
        results = []
        for binding in data.get('results', {}).get('bindings', []):
            coord = binding.get('coord', {}).get('value', '')
            # Parse Point(lon lat) Format
            if coord.startswith('Point('):
                parts = coord.replace('Point(', '').replace(')', '').split()
                lon, lat = float(parts[0]), float(parts[1])
                # Nur Wien filtern (grobe Grenzen)
                if 48.0 <= lat <= 48.4 and 16.0 <= lon <= 16.7:
                    results.append({
                        'name': binding.get('itemLabel', {}).get('value', 'Unbekannt'),
                        'kategorie': 'Botschaft',
                        'lat': lat,
                        'lon': lon,
                        'quelle': 'Wikidata'
                    })
        
        print(f"  {len(results)} Botschaften in Wien gefunden")
        
        # Speichern
        with open(OUTPUT_DIR / "wikidata_botschaften.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        return results
    except Exception as e:
        print(f"  Fehler: {e}")
        return []

if __name__ == "__main__":
    fetch_wikidata_botschaften()
