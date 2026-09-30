# Strategie: Suche nach isolierten Fußwegen in Hamburg

## Ziel
Einen Fußweg in Hamburg finden, der folgende Eigenschaften erfüllt:

| Eigenschaft | Beschreibung |
|---|---|
| **Dauer** | ~10 Minuten Gehzeit (~700-800m) |
| **Zugänglichkeit** | Nur zu Fuß begehbar |
| **Parallelwege** | Keine Straßen, Radwege oder Straßenbahntrassen |
| **Abzweigungen** | Keine (gerader Weg) |

## Datenquelle
**OpenStreetMap (OSM)** — Overpass API

OSM enthält detaillierte Informationen über Wege, ihre Tags und Geometrien.

## Vorgehensweise

### 1. Daten abrufen
- **Overpass API** abfragen
- Filter: `highway=footway` oder `highway=path`
- Region: Hamburg, Deutschland

### 2. Nach Länge filtern
- Geometrie analysieren
- Länge berechnen (~700-800m für 10 Minuten)
- Wege außerhalb des Bereichs aussortieren

### 3. Nach Geradheit prüfen
- Geometrie analysieren
- Krümmung berechnen
- Nur gerade Wege behalten

### 4. Umgebung analysieren
- Puffer um den Weg erstellen (~50m)
- Prüfen, ob andere Verkehrswege im Puffer liegen
- Ausschluss von Wegen mit parallelen Straßen/Radwegen

### 5. Abzweigungen prüfen
- Topologie analysieren
- Wege mit Verbindungen zu anderen Wegen ausschließen
- Nur isolierte Wege behalten

## Technische Umsetzung

### Python-Bibliotheken
```python
import osmnx as ox
import geopandas as gpd
from shapely.geometry import LineString
```

### Overpass API Query
```python
tags = {"highway": ["footway", "path"]}
footways = ox.features_from_place("Hamburg, Germany", tags)
```

### Geometrie-Analyse
- Länge: `gdf.length`
- Geradheit: Krümmung berechnen
- Puffer: `gdf.buffer(50)`
- Topologie: `gdf.intersects()`

## Nächste Schritte
1. Python-Skript erstellen
2. OSM-Daten abrufen
3. Filter anwenden
4. Ergebnisse validieren
5. Karte mit Ergebnissen erstellen

## Alternative Ansätze
- **Visuelle Suche**: Browser + OpenStreetMap/Google Maps
- **Manuelle Suche**: Satellitenbilder analysieren
