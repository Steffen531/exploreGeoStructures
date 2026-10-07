---
name: behoerdenetc
description: Findet Behörden, Polizeidienststellen und Botschaften in beliebigen Städten oder Stadtteilen weltweit. Wird verwendet bei "suche Behörden", "finde Polizei", "finde Botschaften" oder ähnlichen Anfragen.
---

# Skill: Behörden, Polizei & Botschaften finden

## Beschreibung
Findet Behörden, Polizeidienststellen und Botschaften in beliebigen Städten oder Stadtteilen weltweit. Der Nutzer gibt die geographische Region vor. Der Skill passt die Strategie automatisch an die verfügbaren Datenquellen an.

Ignoriere das Verzeichnis tasks.

## Landes-Referenzen (vor der Abfrage lesen!)

Bevor Phase 1 gestartet wird, prüfen, ob für das Ziel-Land eine Referenzdatei
unter `reference/` liegt – diese enthält die erprobten Datenquellen, Endpunkte,
QIDs, Filter und Merge-Schwellen und ersetzt das Probieren in Phase 1/2.

| Land | Datei |
|------|-------|
| Niederlande (NL), z. B. Leiden, Utrecht, Amsterdam, Den Haag | `reference/niederlande.md` |

## Strategie: Kombinierte Quellen (Strategie 4)

Der kombinierter Ansatz nutzt mehrere Datenquellen, um die bestmögliche Abdeckung zu erreichen. Die Strategie wird dynamisch an die Region angepasst.

### Phase 1: Region analysieren und Datenquellen prüfen

| Datenquelle | Verfügbarkeit | Relevante Tags/Felder |
|-------------|---------------|----------------------|
| **OpenStreetMap (Overpass API)** | Weltweit verfügbar | `amenity=police`, `amenity=embassy`, `office=government`, `building=government` |
| **Offizielle Open Data** | Stadt/Land-spezifisch | Variiert nach Stadt (z.B. data.wien.gv.at, data.gov.uk, etc.) |
| **Wikidata / Wikipedia** | Weltweit verfügbar | Strukturierte Daten, gut für Botschaften & internationale Einrichtungen |

**Anpassungslogik:**
- **Stadt mit Open Data Portal** → Nutze OSM + Open Data + Wikidata (volle Strategie 4)
- **Stadt ohne Open Data Portal** → Nutze OSM + Wikidata (Strategie 4 ohne Open Data)
- **Land mit nationalem Open Data** → Nutze OSM + nationales Open Data + Wikidata
- **Entwickeltes Land / keine Daten** → Nutze OSM + Wikidata, ggf. manuelle Recherche

### Phase 2: Daten abrufen

#### 2a: OpenStreetMap (Overpass API)
- **Server** (Fallback-Reihenfolge):
  - `https://overpass-api.de/api/interpreter`
  - `https://overpass.kumi.systems/api/interpreter`
  - `https://maps.mail.ru/osm/tools/overpass/api/interpreter`
- **Filter**: `amenity=police`, `amenity=embassy`, `office=government`, `building=government`
- **Region**: Bounding Box oder Stadtname

#### 2b: Offizielle Open Data (falls verfügbar)
- **Stadt-spezifische Portale**: Prüfe, ob die Stadt ein Open Data Portal hat
- **Beispiele**:
  - Wien: `data.wien.gv.at`
  - London: `data.gov.uk`
  - Berlin: `daten.berlin.de`
  - New York: `opendata.cityofnewyork.us`
- **API/Format**: CSV, GeoJSON, WFS, oder API-Abfrage

#### 2c: Wikidata (SPARQL)
- **Endpoint**: `https://query.wikidata.org/sparql`
- **Abfrage**: Suche nach Behörden, Polizei, Botschaften in der Region
- **Vorteile**: Gut für internationale Einrichtungen und Botschaften

### Phase 3: Daten zusammenführen und bereinigen

1. **Duplikatbereinigung**: Entferne doppelte Einträge (gleiche Adresse/Name)
2. **Geocodierung**: Fehlende Koordinaten ergänzen (Nominatim oder similar)
3. **Kategorisierung**: Einteilung in:
   - Behörden & Regierungsgebäude
   - Polizeidienststellen
   - Botschaften & Konsulate
   - Internationale Einrichtungen
4. **Qualitätsprüfung**: Vollständigkeit der Adressen und Kontaktdaten

### Phase 4: Ergebnis exportieren

- **GeoJSON**: Alle Funde mit Eigenschaften
- **KML**: Für Google Earth
- **GPX**: Für GPS-Geräte
- **JSON**: Strukturierte Daten mit Metadaten

## Umsetzung

### Python-Skriptstruktur

```python
#!/usr/bin/env python3
"""
Behörden, Polizei & Botschaften finden – Kombinierte Quellen
1. Region analysieren und Datenquellen prüfen
2. Daten abrufen (OSM + Open Data + Wikidata)
3. Daten zusammenführen und bereinigen
4. Ergebnis exportieren
"""

import requests
import json
import argparse
from datetime import datetime

# Konfiguration
OVERPASS_SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"

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
    """OSM-Daten von Overpass API abrufen."""
    if bbox:
        bbox_str = f"({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]})"
    elif place:
        bbox_str = f'area["name"="{place}"]->.searchArea;'
    
    query = f"""
    [out:json][timeout:60];
    (
      node["amenity"="police"]{bbox_str};
      node["amenity"="embassy"]{bbox_str};
      node["office"="government"]{bbox_str};
      node["building"="government"]{bbox_str};
      way["amenity"="police"]{bbox_str};
      way["amenity"="embassy"]{bbox_str};
      way["office"="government"]{bbox_str};
      way["building"="government"]{bbox_str};
    );
    out center;
    """
    # ... Anfrage senden und GeoJSON erstellen

def fetch_wikidata(place):
    """Wikidata via SPARQL abfragen."""
    query = f"""
    SELECT ?item ?itemLabel ?coord ?address WHERE {{
      ?item wdt:P31/wdt:P279* wd:Q2555642 .  # Behörden
      ?item wdt:P17 ?country .
      ?item wdt:P625 ?coord .
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "de,en". }}
    }}
    LIMIT 100
    """
    # ... Anfrage senden

def merge_and_deduplicate(osm_data, open_data, wikidata):
    """Daten zusammenführen und Duplikate entfernen."""
    # ... Implementierung

def main():
    parser = argparse.ArgumentParser(description="Behörden, Polizei & Botschaften finden")
    parser.add_argument("--place", type=str, required=True, help="Stadt oder Stadtteil (z.B. 'Wien, Österreich')")
    parser.add_argument("--bbox", type=float, nargs=4, metavar=("S", "W", "N", "E"), help="Bounding Box")
    parser.add_argument("--output", type=str, default="ergebnis", help="Ausgabeverzeichnis")
    
    args = parser.parse_args()
    
    # Phase 1: Region analysieren
    open_data_portal = check_open_data_availability(args.place)
    
    # Phase 2: Daten abrufen
    osm_data = fetch_osm_data(args.bbox, args.place)
    wikidata = fetch_wikidata(args.place)
    
    # Phase 3: Zusammenführen
    merged = merge_and_deduplicate(osm_data, open_data_portal, wikidata)
    
    # Phase 4: Exportieren
    # ...

if __name__ == "__main__":
    main()
```

### Verwendungsbeispiele

```bash
# Behörden in Wien finden
python behoerden_suche.py --place "Wien, Österreich" --output results/wien

# Behörden in einem Stadtteil
python behoerden_suche.py --place "Berlin-Mitte" --output results/berlin-mitte

# Behörden in einer Bounding Box
python behoerden_suche.py --bbox 48.10 16.20 48.30 16.50 --output results/wien-west
```

## Parameter

| Parameter | Standard | Beschreibung |
|----------|----------|-------------|
| `--place` | – | Stadt oder Stadtteil (z.B. "Wien, Österreich") |
| `--bbox` | – | Bounding Box (Süd, West, Nord, Ost) |
| `--output` | ergebnis | Ausgabeverzeichnis |

## Ausgabe

- `ergebnis.geojson` – Alle Funde als GeoJSON
- `ergebnis.kml` – Für Google Earth
- `ergebnis.gpx` – Für GPS-Geräte
- `zusammenfassung.json` – Statistiken und Metadaten

## Anpassungsstrategien

| Situation | Vorgehen |
|-----------|----------|
| **Kein Open Data Portal** | OSM + Wikidata als Hauptquellen |
| **Schlechte OSM-Abdeckung** | Wikidata priorisiert, ggf. manuelle Recherche |
| **Entwickeltes Land** | OSM + Wikidata, ggf. Wikipedia-Scraping |
| **Nur Stadtteil bekannt** | Bounding Box um Stadtteil, OSM + Wikidata |
| **Spezifische Einrichtung gesucht** | Fokussierte Abfrage auf eine Kategorie |

## Tipps

1. **Für große Städte**: Nutze eine Bounding Box statt `--place`, um die Abfrage zu begrenzen
2. **Für bessere Ergebnisse**: Kombiniere immer OSM mit Wikidata
3. **Für Städte mit Open Data**: Prüfe zuerst das offizielle Portal
4. **Für Entwicklungsländer**: Wikidata ist oft die beste Quelle
5. **Duplikatbereinigung**: Immer durchführen, da OSM und Wikidata oft dieselben Einträge haben
