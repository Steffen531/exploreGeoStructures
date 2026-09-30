# Strategie: Belebte Orte in Städten (Berlin, Dienstag Vormittag)

## Ziel

Identifizieren, an welchen öffentlichen Orten in Berlin dienstag vormittags (~9–12 Uhr) viele Menschen sind.

## Herausforderung

Es gibt keine einzige Datenquelle, die direkt zeigt "wo sind dienstag vormittags viele Menschen". Gefragt ist eine **Schlussfolgerung aus mehreren Datenquellen**.

---

## Kombinierter Ansatz (4 Schritte)

### Schritt 1: POI-Typologie + Öffnungszeiten aus OpenStreetMap

**Ziel:** Kandidaten identifizieren, die dienstag vormittag geöffnet sind und viele Menschen anziehen.

**Datenquelle:** Overpass API (OpenStreetMap)

**Vorgehen:**
1. Alle POIs in Berlin abfragen mit Tags: `shop`, `amenity`, `office`, `tourism`, `leisure`, `building`
2. Öffnungszeiten (`opening_hours`) parsen — filtern auf "Di 09:00–12:00" oder "Mo–Fr 09:00–12:00"
3. POIs nach Typ gruppieren und Dichte berechnen (z.B. Anzahl pro 100m × 100m Grid)
4. Hotspots identifizieren: Bereiche mit hoher Dichte von dienstag-vormittag-geöffneten POIs

**Erwartete Kandidaten:**
- Einkaufszentren und Einkaufsstraßen (öffnen meist 10 Uhr)
- Universitäten und Fachhochschulen (Vorlesungszeit)
- Museen und Galerien (oft dienstag geöffnet)
- Behörden und Ämter (Sprechzeiten vormittags)
- Wochenmärkte (manche dienstag + samstag)
- Großraumbüros und Coworking-Spaces

**Tools:** `osmnx`, `geopandas`, `shapely`, `pandas`

---

### Schritt 2: Google Popular Times (falls verfügbar)

**Ziel:** Besucherzahlen für identifizierte Kandidaten prüfen.

**Datenquelle:** Google Maps Popular Times (indirekt, z.B. über Drittanbieter-APIs oder manuelle Abfrage)

**Vorgehen:**
1. Für Top-Kandidaten aus Schritt 1: Google Maps öffnen
2. Popular Times für "Dienstag 10–11 Uhr" prüfen
3. Orte mit "Sehr beschäftigt" oder "Meistbesucht" markieren

**Hinweis:** Google blockiert Scraping. Mögliche Alternativen:
- SerpAPI (kostenpflichtig, aber legal)
- Manuelle Abfrage für Top-20-Kandidaten
- Google Places API (nur POI-Infos, keine Popular Times)

**Fallback:** Wenn nicht verfügbar, mit Schritt 3 und 4 arbeiten.

---

### Schritt 3: ÖPNV-Aussteigedaten (BVG)

**Ziel:** Validierung — wo steigen dienstag vormittag viele Menschen aus?

**Datenquelle:** BVG GTFS-Daten (offen verfügbar)

**Vorgehen:**
1. GTFS-Feed der BVG laden (https://www.vbb.de/unsere-themen/digitales/open-data/)
2. Haltestellen mit Koordinaten extrahieren
3. Aussteige-Dichte schätzen (basierend auf Linienfrequenz + Haltestellentyp)
4. Dienstag-Vormittags-Frequenz berechnen (GTFS `calendar.txt` + `stop_times.txt`)
5. Hotspots identifizieren: Haltestellen mit hoher vormittäglicher Frequenz

**Korrelation:** Hohe ÖPNV-Frequenz korreliert oft mit hoher Fußgänger-Dichte in der Umgebung.

**Tools:** `partridge` (GTFS-Python-Library), `geopandas`

---

### Schritt 4: Visuelle Prüfung

**Ziel:** Bestätigung der Top-Kandidaten.

**Vorgehen:**
1. Top-10-Orte aus Schritten 1–3 sammeln
2. Satellitenbilder (Google Maps / Bing) prüfen — sieht man Menschen?
3. Streetview prüfen — wirkt der Ort wie ein "dienstag vormittags voller Ort"?
4. Ggf. Fotos von Google Maps / Panoramio prüfen

---

## Bewertungskriterien

Ein Ort gilt als "dienstag vormittags stark belebt", wenn er:

| Kriterium | Gewicht | Quelle |
|---|---|---|
| Hohe POI-Dichte (geschäftlich/öffentlich) | Hoch | OSM (Schritt 1) |
| Öffnungszeit dienstag 9–12 Uhr | Hoch | OSM (Schritt 1) |
| Hohe Besucherzahl (Popular Times) | Mittel | Google (Schritt 2) |
| Hohe ÖPNV-Frequenz vormittags | Mittel | BVG (Schritt 3) |
| Visuell bestätigt | Niedrig | Karte (Schritt 4) |

---

## Erwartete Ergebnis

Eine **rangierte Liste von Orten** in Berlin, die dienstag vormittags viele Menschen aufweisen, z.B.:

1. **Alexanderplatz / Alexa** — Einkaufszentrum, hohe ÖPNV-Frequenz
2. **Friedrichstraße** — Einkaufsmeile, viele Geschäfte
3. **Universitätsbereiche (FU, TU, HU)** — Vorlesungszeit
4. **Behördenzentren (Mitte)** — Sprechzeiten
5. **Museen (Museumsinsel)** — Touristen + Schulklassen
6. **Wochenmärkte** — je nach Tag

---

## Nächste Schritte (wenn ausgeführt)

1. Overpass API-Abfrage für Berlin-POIs schreiben
2. Öffnungszeiten parsen und filtern
3. GTFS-Daten der BVG laden und auswerten
4. Ergebnisse zusammenführen und rangieren

---

## Offene Fragen

- Soll die Analyse ganz Berlin abdecken oder nur bestimmte Bezirke?
- Welche Rolle spielt Wetter? (Regen → weniger Menschen draußen)
- Sollen Events (z.B. Messen, Demonstrationen) berücksichtigt werden?
- Wie groß darf ein "Ort" sein? (einzelner Platz vs. ganzes Viertel)
