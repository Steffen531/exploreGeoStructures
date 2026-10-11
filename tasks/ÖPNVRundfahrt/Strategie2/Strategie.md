# Strategie 2: Generischer ÖPNV-Routen-Planner

## Überblick

Ein CLI-Tool, das in beliebigen Städten oder Gegenden auf der Welt eine ÖPNV-Fahrt zusammenstellt, die eine gewisse Zeit dauert und nicht an bereits besuchte Orte zurückkehrt.

## Kernanforderungen

### Vom Nutzer konfigurierbar
- **Stadt/Region**: Beliebig weltweit
- **Startpunkt**: Optional (wenn nicht gegeben, wählt der Skill)
- **Endpunkt**: Optional (wenn nicht gegeben, wählt der Skill)
- **Datum und Uhrzeit**: Wann die Fahrt beginnt
- **Dauer**: Mindestens und maximal Minuten
- **Umstiege**: Minimale und maximale Anzahl
- **Suchfeld**: Radius oder Begrenzungsrechteck

### Verhaltensregeln
- **Start ≠ Ende**: Keine Rundtouren
- **Keine Zwischenstopps**: Nur Start, Umstiege, Ende
- **Strikte Keine-Wiederholungen**: Jede Station, jeder Straßenabschnitt, jedeein Stadtteil nur einmal
- **Kurze Umstiegszeiten**: Fußwege + Wartezeit minimieren (Priorität 1)
- **Störungen/Absagen berücksichtigen**: Echtzeit-Daten, Alternativen suchen
- **Ride-Hailing als Brücke**: Ersatz für fehlende ÖPNV-Verbindungen (Uber, Bolt, Didi, Grab, Ola, etc.)
- **3 Routen-Vorschläge**: Am Ende werden 3 Optionen präsentiert
- **Kartenvisualisierung**: KML/GPX/HTML-Export
- **CLI-only**: Keine GUI

### Ausgeschlossene Anforderungen
- Kosten (gleichgültig)
- Schnellste Route (nicht das Ziel)

## Architektur

### Phase 1: Daten-Scout
Stadt erkennen -> Datenquellen finden -> Bewertung

```
Eingabe: Stadtname
|
1. Overpass API: OPNV-Linien, Stationen, Strassen extrahieren
2. GTFS-Feeds suchen: TransitFeeds, lokale Verkehrsbetreiber
3. OTP-Instanzen prufen
4. Echtzeit-APIs identifizieren
5. Ride-Hailing-Anbieter fur Region finden
|
Ausgabe: Verfugbare Datenquellen mit Qualitats-Score
```

### Phase 2: Netzwerk-Aufbau
```
1. OPNV-Graph: Knoten (Stationen), Kanten (Linienverlaufe)
2. Strassen-Graph: Fur Fuszege und Ride-Hailing (OSRM/OSM)
3. Gehwege: Zwischen nahegelegenen Stationen (OSRM)
4. Stadtteil-Zuordnung: Jeder Station einem Stadtteil zuordnen
```

### Phase 3: Routing
```
Algorithmus: Multi-Objective A* mit strikten Constraints

Kostenfunktion:
  Cost = w1 * (Fuszwegzeit) + w2 * (Wartezeit) + w3 * (Constraint-Strafen)

Constraints:
  - Keine Station zweimal
  - Kein Strassenabschnitt zweimal
  - Kein Stadtteil zweimal
  - Umstiegsanzahl zwischen min und max
  - Dauer zwischen min und max
  - Alle Abfahrtszeiten >= aktuelles Datum+Uhrzeit
  - Storungen/Absagen berucksichtigen
```

### Phase 4: Output
```
3 Routen mit:
  - Stationsfolge [S, S1, S2, ..., E]
  - Konkrete Abfahrts-/Ankunftszeiten
  - Verkehrsmittel-Linien
  - Fuszege und Wartezeiten
  - Storungen (farblich markiert)
  - Gesamtdauer

Formate:
  - JSON (maschinenlesbar)
  - KML/GPX (fur umap.openstreetmap.de)
  - HTML (interaktive Leaflet-Karte)
```

## CLI-Definition

```bash
python opnv_route.py \
  --stadt "Berlin" \
  --datum 2026-12-15 \
  --uhrzeit 18:30 \
  --start "Alexanderplatz" \
  --end "Tempelhofer Feld" \
  --dauer-min 60 \
  --dauer-max 120 \
  --umstiege-min 1 \
  --umstiege-max 5 \
  --suchfeld-radius 5km \
  --format json,kml,gpx,html
```

## Datenquellen-Prioritat

| Rang | Quelle | Vorteil |
|------|--------|---------|
| 1 | GTFS-Feed | Vollstandig, aktuell, Fahrplane |
| 2 | OTP-Instanz | GTFS + OSM, Routing-Algorithmen |
| 3 | Overpass API | Weltweit verfugbar, OSM-Daten |
| 4 | OSRM/GraphHopper | Strassenrouting fur Fuszege/Taxi |
| 5 | Ride-Hailing APIs | Dynamische Brucken |

## Ride-Hailing Anbieter

| Anbieter | Region | API |
|----------|--------|-----|
| Uber | Global | Entwickler-API |
| Bolt | Europa, Afrika | Bolt Business |
| Didi | China, Lateinamerika | Didi Open Platform |
| Grab | Sudostasien | Grab for Developers |
| Ola | Indien | Ola Developer |
| Yandex.Taxi | Russland | Yandex Maps |
| Gojek | Sudostasien | Gojek for Business |
| Free Now | Europa | Free Now API |
| InDriver | Russland, Lateinamerika | Eingeschrankt |

## Optimierungsziele (Priorisiert)

| Prioritat | Ziel |
|-----------|------|
| 1 | Kurze Umstiegszeiten (Fuszege + Wartezeit) |
| 2 | Strikte Keine-Wiederholungen |
| 3 | Storungen/Absagen berucksichtigen |
| 4 | Einhaltung der Dauer |
| 5 | Einhaltung der Umstiegsanzhalt |

## Nachste Schritte

1. Python-Prototyp fur Phase 1 (Daten-Scout)
2. Routing-Kern implementieren
3. GTFS/Echtzeit-Integration
4. Output-Formate und Visualisierung

## Referenz

Basierend auf Erfahrungen aus `tasks/OPNVRundfahrt/Strategie1/` (Achsenstrategie), aber mit algorithmischem Ansatz statt manueller Stadt-Strategie.
