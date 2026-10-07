---
name: fussweg
description: Findet ungewöhnliche, isolierte Fußwege in beliebigen Städten, Stadtteilen oder Orten weltweit. Wird verwendet bei "suche Fussweg" oder "finde Fussweg".
---

# Skill: Isolierte Fußwege finden

## Beschreibung
Findet ungewöhnliche, isolierte Fußwege in beliebigen Städten, Stadtteilen oder Orten weltweit. Ein "isolierter Fußweg" ist ein Weg, der:
- Eine bestimmte Gehzeit hat (Standard: ~10 Minuten, konfigurierbar)
- Nur zu Fuß begehbar ist
- Keine parallel verlaufenden anderen Verkehrswege hat (Straßen, Radwege, Straßenbahntrassen)
- Keine Abzweigungen hat (man kann nicht abbiegen)

## Strategie: Kombinierter Ansatz (4 Phasen)

Der kombinierter Ansatz nutzt geografisches Vorwissen, um Kandidaten zu identifizieren, und verifiziert diese gezielt mit OSM-Daten. So wird die Suche effizient und die Ergebnisse präzise.

### Phase 1: Regionale Strukturtypen identifizieren
Geeignete Strukturtypen hängen von der **geografischen Region** ab. Wähle passende Typen:

| Region | Strukturtyp | Warum er passt |
|--------|-------------|----------------|
| **Küsten** | Strand-/Uferwege | Zwischen Wasser und Hang kein Platz für Straßen |
| **Küsten** | Deich-/Dammwege | Nur ein Weg auf dem Deich |
| **Bergregionen** | Treppenwege | Zu steil für andere Verkehrsmittel |
| **Bergregionen** | Bergpfade / Wanderwege | Abgelegene Lage, keine Straßen |
| **Flussufer** | Flussuferwege | Zwischen Wasser und Hang/Prallhang |
| **Flussufer** | Brücken-Zugänge | Nur ein Weg zur Brücke |
| **Parks / Grünflächen** | Parkkorridore | Grüne Schneisen ohne Straßen |
| **Parks / Grünflächen** | Botanische Gärten | Wege ohne parallelen Verkehr |
| **Historische Altstädte** | Historische Pfade | Gängeviertel, Wallgänge |
| **Historische Altstädte** | Gassen / Alleen | Ohne Straßenverkehr |
| **Inseln** | Küstenpfade | Uferweg ohne Straßen |
| **Wüsten / Trockenregionen** | Oasen-Pfade | Zwischen Palmen/Quellen |
| **Wüsten / Trockenregionen** | Wadis | Trockene Flussbetten ohne Straßen |
| **Lakenseen** | Uferpromenaden | Weg entlang des Ufers |
| **Lakenseen** | Inselverbindungen | Fußgängerbrücken |
| **Industriegebiete** | Hafenränder | Wege entlang von Kaianlagen |
| **Industriegebiete** | Eisenbahn-Parallelwege | Abgelegene Gleisbereiche |
| **Vororte** | Durchgangswege | Zwischen Nachbarschaften |
| **Vororte** | Schulwege | Direkte Verbindungen ohne Straßen |

**Hinweis:** Die Tabelle ist nicht vollständig. Passe die Strukturtypen an die spezifische Region an.

### Phase 2: Kandidaten gezielt mit OSM-Daten verifizieren
Nutze die **Overpass API** für OpenStreetMap-Daten:
- **Server** (Fallback-Reihenfolge):
  - `https://overpass-api.de/api/interpreter`
  - `https://overpass.kumi.systems/api/interpreter`
  - `https://maps.mail.ru/osm/tools/overpass/api/interpreter`
- **Filter**: `highway=footway`, `highway=path`, `highway=pedestrian`, `highway=steps`
- **Region**: Bounding Box um den Kandidaten (nicht die ganze Stadt!)

### Phase 3: Kriterien prüfen
- **Länge**: Berechne die Länge jedes Weges mit der Haversine-Formel
  - Standard: 600-900m (~10 Minuten bei 60-80m/min)
  - Anpassbar über Parameter
- **Geradheit**: Berechne das Verhältnis aus direkter Distanz (Start→Ende) zur tatsächlichen Weglänge
  - Standard-Schwelle: ≥ 0.95 (sehr gerade)
  - 1.0 = perfekt gerade
- **Parallelwege**: Erstelle einen Puffer um den Kandidaten (Standard: 50m)
  - Prüfe, ob andere Verkehrswege im Puffer liegen
  - Ausschluss von Wegen mit parallelen Straßen/Radwegen/Tram
- **Abzweigungen**: Topologische Analyse: Prüfe, ob Start- oder Endpunkte des Kandidaten mit anderen Wegen verbunden sind
  - Kandidaten ohne Verbindungen zu anderen Wegen sind isoliert

### Phase 4: Ergebnis exportieren
- **GeoJSON**: Alle Kandidaten mit Eigenschaften
- **KML**: Für Google Earth
- **GPX**: Für GPS-Geräte

## Umsetzung

### Python-Skriptstruktur

```python
#!/usr/bin/env python3
"""
Isolierte Fußwege finden – Kombinierter Ansatz
1. Regionale Strukturtypen identifizieren
2. Kandidaten gezielt mit OSM-Daten verifizieren
3. Kriterien prüfen (Länge, Geradheit, Parallelwege, Abzweigungen)
4. Ergebnis exportieren
"""

import requests
import json
import math
import argparse
from datetime import datetime

# Konfiguration
OVERPASS_SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

# Regionale Strukturtypen (Beispiel)
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
    # ... Implementierung: Nutze regionale Strukturtypen, um Kandidaten zu finden
    pass

def fetch_osm_data(bbox=None, place=None):
    """OSM-Daten von Overpass API abrufen."""
    if bbox:
        bbox_str = f"({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]})"
    elif place:
        # Nominatim für Geocoding
        bbox_str = f'area["name"="{place}"]->.searchArea;'
    
    query = f"""
    [out:json][timeout:60];
    (
      way["highway"="footway"]{bbox_str};
      way["highway"="path"]{bbox_str};
      way["highway"="pedestrian"]{bbox_str};
      way["highway"="steps"]{bbox_str};
    );
    out body;
    >;
    out skel qt;
    """
    # ... Anfrage senden und GeoJSON erstellen

def haversine_distance(coord1, coord2):
    """Distanz zwischen zwei Koordinaten in Metern."""
    R = 6371000
    lon1, lat1 = coord1
    lon2, lat2 = coord2
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def calculate_length(coords):
    """Weglänge in Metern berechnen."""
    return sum(haversine_distance(coords[i], coords[i+1]) for i in range(len(coords)-1))

def calculate_straightness(coords):
    """Geradheit berechnen (1.0 = perfekt gerade)."""
    if len(coords) < 2:
        return 0.0
    direct = haversine_distance(coords[0], coords[-1])
    actual = calculate_length(coords)
    return direct / actual if actual > 0 else 0.0

def find_parallel_ways(candidate, all_ways, buffer_m=50):
    """Parallele Wege im Puffer finden."""
    # ... Implementierung

def find_connections(candidate, all_ways):
    """Abzweigungen finden (gemeinsame Endpunkte)."""
    # ... Implementierung

def main():
    parser = argparse.ArgumentParser(description="Isolierte Fußwege finden – Kombinierter Ansatz")
    parser.add_argument("--place", type=str, help="Ort oder Stadt (z.B. 'Hamburg, Deutschland')")
    parser.add_argument("--bbox", type=float, nargs=4, metavar=("S", "W", "N", "E"), help="Bounding Box")
    parser.add_argument("--region-type", type=str, choices=["küste", "berg", "fluss", "park", "altstadt", "insel", "wüste", "see", "industrie", "vorort"], help="Geografischer Regionstyp")
    parser.add_argument("--min-length", type=int, default=600, help="Minimale Länge in Metern")
    parser.add_argument("--max-length", type=int, default=900, help="Maximale Länge in Metern")
    parser.add_argument("--straightness", type=float, default=0.95, help="Minimale Geradheit (0-1)")
    parser.add_argument("--buffer", type=int, default=50, help="Puffer für Parallelwege in Metern")
    parser.add_argument("--output", type=str, default="ergebnis", help="Ausgabeverzeichnis")
    
    args = parser.parse_args()
    # ... Hauplogik

if __name__ == "__main__":
    main()
```

### Verwendungsbeispiele

```bash
# Fußwege in Hamburg finden (kombinierter Ansatz)
python fussweg_suche.py --place "Hamburg, Deutschland" --region-type küste --output results/hamburg

# Fußwege in einem bestimmten Stadtteil
python fussweg_suche.py --place "Blankenese, Hamburg" --region-type küste --output results/blankenese

# Fußwege in einer Bounding Box
python fussweg_suche.py --bbox 53.575 10.00 53.595 10.04 --output results/stadtpark

# Andere Parameter
python fussweg_suche.py --place "München, Deutschland" --region-type park \
    --min-length 500 --max-length 1200 \
    --straightness 0.90 --buffer 30 \
    --output results/muenchen
```

## Parameter

| Parameter | Standard | Beschreibung |
|----------|----------|-------------|
| `--place` | – | Ort oder Stadt (z.B. "Hamburg, Deutschland") |
| `--bbox` | – | Bounding Box (Süd, West, Nord, Ost) |
| `--region-type` | – | Geografischer Regionstyp (küste, berg, fluss, park, altstadt, insel, wüste, see, industrie, vorort) |
| `--min-length` | 600 | Minimale Weglänge in Metern |
| `--max-length` | 900 | Maximale Weglänge in Metern |
| `--straightness` | 0.95 | Minimale Geradheit (0-1) |
| `--buffer` | 50 | Puffer für Parallelwege in Metern |
| `--output` | ergebnis | Ausgabeverzeichnis |

## Ausgabe

- `ergebnis.geojson` – Alle Kandidaten als GeoJSON
- `ergebnis.kml` – Für Google Earth
- `ergebnis.gpx` – Für GPS-Geräte
- `zusammenfassung.json` – Statistiken und Metadaten

## Tipps

1. **Für große Städte**: Nutze eine Bounding Box statt `--place`, um die Abfrage zu begrenzen
2. **Für bessere Ergebnisse**: Erhöhe `--straightness` auf 0.98 für sehr gerade Wege
3. **Für mehr Kandidaten**: Erhöhe `--buffer` auf 100m oder mehr
4. **Für andere Gehzeiten**: Passe `--min-length` und `--max-length` an (z.B. 300-500m für 5 Minuten)
5. **Regionale Anpassung**: Wähle den passenden `--region-type` für die geografische Region, um bessere Kandidaten zu erhalten
6. **Kombinierter Ansatz**: Nutze geografisches Vorwissen, um Kandidaten zu identifizieren, und verifiziere diese gezielt mit OSM-Daten

## Nächste Schritte

1. [ ] Python-Skript mit argparse erstellen
2. [ ] Regionale Strukturtypen identifizieren (Phase 1)
3. [ ] Overpass API Anfrage für Kandidaten implementieren (Phase 2)
4. [ ] Längenberechnung mit Haversine (Phase 3)
5. [ ] Geradheitsberechnung (Phase 3)
6. [ ] Parallelweg-Prüfung mit Puffer (Phase 3)
7. [ ] Abzweigungs-Prüfung (Topologie) (Phase 3)
8. [ ] GeoJSON/KML/GPX Export (Phase 4)
9. [ ] Parameter über Kommandozeile
