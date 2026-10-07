# Strategie: Besondere städtische Strukturen finden

## Ziel
Suche nach besonderen städtischen Strukturen (große Malls, Bahnhöfe, Passagen) mit folgenden Eigenschaften:
- **Mehrere Ausgänge**
- **Ausgänge auf unterschiedlichen Ebenen**
- **Anbindung an öffentliche Verkehrsmittel**

---

## Strategie 1: Overpass API Direktabfrage

### Beschreibung
Nutze die Overpass API, um direkt OpenStreetMap-Daten mit spezifischen Filtern abzufragen.

### Umsetzung
- **Overpass Turbo** (Web-UI) oder **Overpass API** direkt
- Filter für Gebäudetypen:
  - `building=mall` (Einkaufszentren)
  - `building=train_station` (Bahnhöfe)
  - `building=retail` + `shop=department_store` (Kaufhäuser)
- Zusätzliche Filter:
  - `public_transport=station` oder `public_transport=stop_position` in der Nähe
  - `entrance` Nodes an Gebäudepolygonen
  - `level` Tags für Ebenen

### Vorteile
- Sehr detaillierte Daten
- Community-gepflegt
- Kostenlos
- Echtzeit-Daten

### Nachteile
- Begrenzte Abfragegröße
- Erfordert OSM-Kenntnisse
- Datenqualität variiert

---

## Strategie 2: OSMNX + Python

### Beschreibung
Nutze die `osmnx` Bibliothek, um Gebäudepolygonen und Straßennetzwerk programmatisch zu analysieren.

### Umsetzung
```python
import osmnx as ox

# Gebäude in einer Stadt abrufen
place = "Berlin, Deutschland"
tags = {"building": ["mall", "train_station", "retail"]}
buildings = ox.features_from_place(place, tags)

# ÖPNV-Haltestellen abrufen
transit = ox.features_from_place(place, tags={"public_transport": "station"})

# Analyse: Eingänge, Ebenen, Nähe zu ÖPNV
```

### Vorteile
- Vollständige Kontrolle über Analyse
- Automatisierbar
- Gute Integration mit GeoPandas/Shapely
- Einfach erweiterbar

### Nachteile
- Erfordert Python-Kenntnisse
- Abhängig von OSM-Datenqualität
- Rechenintensiv für große Städte

---

## Strategie 3: Kombinierte Filter-Logik

### Beschreibung
Mehrschrittige Analyse, die verschiedene Datenquellen und Filter kombiniert.

### Umsetzung
1. **Schritt 1**: Alle Gebäude mit relevanten `building`-Tags extrahieren
2. **Schritt 2**: Prüfen, ob `public_transport=station`/`stop` in der Nähe liegt (Pufferanalyse)
3. **Schritt 3**: Anzahl der `entrance`-Nodes an den Gebäudepolygonen zählen
4. **Schritt 4**: `level`-Tags analysieren für unterschiedliche Ebenen
5. **Schritt 5**: Ergebnisse als KML/GPX exportieren

### Vorteile
- Sehr präzise Ergebnisse
- Anpassbar an spezifische Anforderungen
- Dokumentierbar

### Nachteile
- Komplexer
- Erfordert mehrere Abfragen

---

## Strategie 4: Alternative Datenquellen

### Beschreibung
Nutzung kommerzieller oder kommunaler Datenquellen ergänzend zu OSM.

### Optionen
- **Google Places API**: Malls und Einkaufszentren mit Bewertungen
- **Kommunale Geodaten**: Oft detaillierter für bestimmte Städte
- **Bing Maps**: Gebäudedaten

### Vorteile
- Oft höhere Datenqualität
- Zusätzliche Informationen (Bewertungen, Öffnungszeiten)

### Nachteile
- Kostenpflichtig
- API-Limits
- Nicht überall verfügbar

---

## Empfohlener Workflow

1. **Datenquelle**: OSM via Overpass API oder OSMNX
2. **Region**: Stadt- oder Landesebene wählbar
3. **Filter**: Kombination aus Gebäudetyp, ÖPNV-Anbindung, Eingängen, Ebenen
4. **Export**: KML/GPX für Visualisierung auf umap.openstreetmap.de

---

## Nächste Schritte

1. [ ] Region festlegen (z.B. Berlin, München, ganz Deutschland)
2. [ ] Python-Skript mit OSMNX entwickeln
3. [ ] Filter-Logik implementieren
4. [ ] Ergebnisse als KML/GPX exportieren
5. [ ] Visualisierung auf umap.openstreetmap.de testen
