# Ansätze: Belebte Orte in Städten

**Frage:** An welchen öffentlichen Orten halten sich in Berlin dienstag vormittags viele Menschen auf?

---

## Vergleichsübersicht

| # | Ansatz | Datenquelle | Stärke | Schwäche | Aufwand |
|---|---|---|---|---|---|
| 1 | Google Popular Times | Google Maps | Direkte Besucherzahlen, Wochentag + Uhrzeit | Kein Scraping, keine API, nur POIs | Mittel |
| 2 | Geotagged Social Media | Twitter/X, Instagram | Echtzeit, deckt Straßen/Plätze ab | API stark limitiert, Bias, nicht repräsentativ | Hoch |
| 3 | Mobilfunk-Daten | Telekom, Vodafone | Sehr präzise, gesamte Stadt | Propriär, teuer, Datenschutz | Hoch |
| 4 | ÖPNV-Daten (BVG) | GTFS-Feed (offen) | Repräsentativ für Pendler, offen verfügbar | Indirekt, nur ÖPNV-Nutzer | Mittel |
| 5 | Event-/Markt-Daten | Kalender, Webseiten | Erklärbar, logisch | Nicht systematisch, qualitativ | Niedrig |
| 6 | OSM POI-Dichte | Overpass API (offen) | Systematisch, reproduzierbar, gesamte Stadt | Keine Besucherzahlen, unvollständig | Mittel |
| 7 | **Kombiniert** | OSM + Google + BVG | Validiert, robust, deckt Lücken auf | Mehrere Quellen nötig | Hoch |

---

## Detailansichten

### 1. Google Popular Times
- **Idee:** Besucherzahlen pro Stunde/Wochentag für einzelne POIs abfragen
- **Problem:** Google blockiert Scraping; keine offizielle API für Popular Times
- **Alternative:** SerpAPI (kostenpflichtig) oder manuelle Abfrage

### 2. Geotagged Social Media
- **Idee:** Posts mit Geotags aus Berlin, gefiltert auf Dienstag Vormittag
- **Problem:** Twitter/X API teuer, Instagram API stark limitiert
- **Nutzlich:** Ergänzung für Trends, nicht für repräsentative Analyse

### 3. Mobilfunk-Daten
- **Idee:** Anonymisierte Bewegungsdaten zeigen tatsächliche Dichte
- **Problem:** Meist proprietär, teuer, Datenschutzbedenken
- **Alternative:** Forschungsdaten, z.B. aus dem T-Labor (TU Berlin)

### 4. ÖPNV-Daten (BVG)
- **Idee:** Aussteige-Dichte an Haltestellen als Proxy für Belebtheit
- **Vorteil:** Offene GTFS-Daten, einfach verfügbar
- **Nachteil:** Zeigt nur ÖPNV-Nutzer, nicht alle Menschen

### 5. Event-/Markt-Daten
- **Idee:** Wochenmärkte, Museen, Behörden, Universitäten — wer hat dienstag vormittag geöffnet?
- **Vorteil:** Sofort umsetzbar, nutzt Vorwissen
- **Nachteil:** Keine systematische Datenquelle

### 6. OSM POI-Dichte
- **Idee:** Dichte von Geschäften, Ämtern, Museen etc. in Berlin berechnen
- **Vorteil:** Offen, reproduzierbar, systematisch
- **Nachteil:** Keine tatsächlichen Besucherzahlen

### 7. Kombiniert (empfohlen)
- **Schritt 1:** OSM POI-Dichte + Öffnungszeiten → Kandidaten
- **Schritt 2:** Google Popular Times → Besucherzahlen
- **Schritt 3:** BVG GTFS → ÖPNV-Frequenz
- **Schritt 4:** Visuelle Prüfung → Bestätigung
- **Vorteil:** Validiert, robust, deckt Lücken einzelner Quellen auf
- **Nachteil:** Höchster Aufwand

---

## Empfehlung

**Ansatz 7 (Kombiniert)** ist der robusteste Weg, da er die Schwächen einzelner Quellen ausgleicht. Wenn nur ein Ansatz gewählt werden kann, ist **Ansatz 6 (OSM POI-Dichte)** der beste Einstieg — offen, systematisch und sofort umsetzbar.
