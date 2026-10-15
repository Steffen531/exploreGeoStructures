---
name: oepnvrouten
description: Findet ÖPNV-Routen in beliebigen Städten weltweit – kombiniert GTFS-Fahrpläne, OSM-Daten, OpenTripPlanner und Ride-Hailing zu einem 3-Routen-Vorschlag mit konkreten Abfahrtszeiten. Wird verwendet bei "suche ÖPNV", "finde ÖPNV-Route", "ÖPNV planen" oder ähnlichen Anfragen.
---

# Skill: ÖPNV-Routen finden

Findet in einer vom Nutzer genannten Region eine ÖPNV-Fahrt, die eine gewisse
Zeit dauert, keine bereits besuchten Orte zurückkehrt und strikte
Keine-Wiederholungen-Garantien einhält. Datenquellen (GTFS, OSM/Overpass,
OpenTripPlanner, Ride-Hailing) werden kombiniert, in ein Netzwerk überführt,
mit Multi-Objective-Algorithmen geroutet und als 3 Routen-Vorschläge exportiert.
Das Verzeichnis `tasks/` ignorieren.

## Eingaben

- **Region** (Pflicht): Stadt, Stadtteil oder Bounding Box (S, W, N, E)
- **Datum** (Pflicht): Startdatum (ISO-Format, z. B. `2026-11-01`)
- **Uhrzeit** (Pflicht): Startzeit (HH:MM, z. B. `18:30`)
- Optional: `--start` (Startpunkt), `--end` (Endpunkt),
  `--dauer-min`/`--dauer-max` (Minutenfenster, Standard 60–120),
  `--umstiege-min`/`--umstiege-max` (Standard 1–5),
  `--qid` (Wikidata-QID des Ortes),
  `--output` (Ausgabeverzeichnis, Standard `ergebnis`)

**Dateien dieses Skills** (Pfade relativ zum Skill-Verzeichnis):

| Datei | Inhalt |
|---|---|
| `reference/learnings.md` | Erfahrungsspeicher – vor Schritt 1 lesen, nach Schritt 8 ergänzen |
| `reference/datenquellen.md` | GTFS, Overpass, OTP, Ride-Hailing: Server, Filter, Abfrageregeln |
| `reference/routing-regeln.md` | Constraints, Kostenfunktion, Diversitäts-Regeln |
| `reference/fehlerbehandlung.md` | Edge Cases und Sonderfälle |
| `reference/oepnvrouten_suche.py` | Skriptvorlage |

## Prozess

1. **Learnings lesen.** `reference/learnings.md` komplett lesen und alle
   Hinweise für die Ziel-Region übernehmen (bewährte Datenquellen,
   Routing-Besonderheiten, offene Fragen) – sie gelten als Kontext für die
   Schritte 2–7.
2. **Datenquellen scoutern.** `reference/datenquellen.md` laden und deren
   Abschnitte anwenden: GTFS-Feeds suchen (TransitFeeds, lokale Verkehrsbetreiber),
   Overpass für OSM-Stationen, OTP-Instanzen prüfen, Ride-Hailing-Anbieter
   identifizieren. Datenquellen mit Qualitäts-Score bewerten.
3. **Region eingrenzen.** BBox um den Stadtteil bzw. das Suchfeld legen
   (nie die ganze Stadt abfragen); Ortsnamen gemäß `reference/datenquellen.md`
   (§Nominatim) mit `polygon_geojson=1` auflösen. Start- und Endpunkt
   bestimmen (vom Nutzer oder durch den Skill gewählt).
4. **Netzwerk aufbauen.** `reference/datenquellen.md` laden und deren
   Abschnitte anwenden: ÖPNV-Graph aus OSM/GTFS (Knoten = Stationen,
   Kanten = Linienverläufe), Straßen-Graph für Fußwege/Ride-Hailing (OSRM),
   Stadtteil-Zuordnung für jede Station. Nominatim-Geocoding für Start-/
   Endpunkt. Als Vorlage: `reference/oepnvrouten_suche.py`.
5. **Routing durchführen.** `reference/routing-regeln.md` laden und alle
   Constraints anwenden:
   - **Start ≠ Ende**: Keine Rundtouren (harte Constraint)
   - **Keine Zwischenstopps**: Nur Start, Umstiege und Ende
   - **Strikte Keine-Wiederholungen**: Jede Station, jeder Straßenabschnitt,
     jeder Stadtteil nur einmal
   - **Kurze Umstiegszeiten**: Fußwege + Wartezeit minimieren (Priorität 1)
   - **Störungen/Absagen berücksichtigen**: Echtzeit-Daten, Alternativen suchen
   - **Ride-Hailing als Brücke**: Ersatz für fehlende ÖPNV-Verbindungen
   - **3 Routen-Vorschläge**: Multi-Objective-Algorithmus findet genau 3 Optionen
   - **Kartenvisualisierung**: KML/GPX-Export für umap.openstreetmap.de
6. **Rangieren und exportieren.** Verbliebene Routen nach Score ranken
   (kurze Umstiegszeiten + schienengebundene Verkehrsmittel bevorzugt) und wie in
   "Output" beschrieben nach `--output` schreiben.
7. **Bei Problemen** (0 Treffer, GTFS-Fehler, keine erreichbare Route):
   `reference/fehlerbehandlung.md` laden und den passenden Eintrag ausführen.
   Constraints nacheinander entschärfen (NUR in dieser Reihenfolge):
   1) Dauer ±10 % erweitern, 2) Umstiegs-Max +2, 3) Ride-Hailing als
   Brücke erlauben, 4) Nur-Stationen-Constraint lockern.
8. **Feedback holen und Learnings schreiben (Wrap-up).** Nach dem Export dem
   Nutzer mit dem `question`-Tool zwei Fragen stellen:
   - Bewertung: **1–5** (Optionen „1 – sehr schlecht" bis „5 – sehr gut")
   - „Was war nicht gut? Was soll beim nächsten Lauf anders machen?"
     (Freitext, optional)
   Dann `reference/learnings.md` aktualisieren: **1–3 Sätze** unter
   „Was nicht lief" (bei konkreten Hinweisen) bzw. „Was gut lief" (bei
   Rating 5 ohne Einwände), immer mit Region und Datum. Bewertung 2–4 ohne
   Freitext → den Grund als offene Frage eintragen. Einträge nie löschen,
   nur bei ~20 Einträgen aufräumen (Regeln in `reference/learnings.md`).

## Output

Im Ausgabeverzeichnis (`--output`):

- `routen.geojson` – alle Routen als LineStrings mit Eigenschaften (Stationenfolge,
  Linien, Abfahrts-/Ankunftszeiten, Umstiege, Dauer, Score, Verkehrsmittel).
  Importierbar auf umap.openstreetmap.de (AGENTS.md: ☰ → „Daten importieren")
- `routen.kml` – Linien je Route als `<Placemark>`/`<LineString>` mit Style-Block je
  Verkehrsmitteltyp, Start/Ziel/Umstiege als Pins, für Google Earth
- `routen.gpx` – Tracks je Route als `<trk>`/`<trkseg>` für GPS-Geräte
- `zusammenfassung.json` – Statistik, Score-Vergleich der 3 Routen, Optionen-Übersicht

Danach dem Nutzer die Kartenanleitung geben: [umap.openstreetmap.de](https://umap.openstreetmap.de)
→ ☰ → „Daten importieren" → GeoJSON wählen (oder Drag & Drop) → „als neue
Ebene" → Karte teilen.

## Skript

`reference/oepnvrouten_suche.py` ist die Vorlage für Schritte 2–6:

```bash
# Stadt mit Start und Ende
.venv/bin/python reference/oepnvrouten_suche.py \
  --stadt "Berlin" \
  --datum 2026-11-01 --uhrzeit 18:30 \
  --start "Alexanderplatz" --end "Tempelhofer Feld" \
  --dauer-min 60 --dauer-max 120 \
  --umstiege-min 1 --umstiege-max 5 \
  --output results/berlin

# Stadtteil / Ausschnitt per Bounding Box (S W N E)
.venv/bin/python reference/oepnvrouten_suche.py \
  --bbox 52.45 13.25 52.55 13.45 \
  --datum 2026-11-01 --uhrzeit 18:30 \
  --output results/berlin-mitte
```

| Parameter | Standard | Beschreibung |
|---|---|---|
| `--stadt` | – | Stadt oder Stadtteil (z. B. „Berlin, Deutschland") |
| `--bbox` | – | Bounding Box (S, W, N, E) |
| `--datum` | – | Startdatum (ISO, z. B. `2026-11-01`) |
| `--uhrzeit` | – | Startzeit (HH:MM, z. B. `18:30`) |
| `--start` | – | Startpunkt (Name oder Station-ID) |
| `--end` | – | Endpunkt (Name oder Station-ID) |
| `--dauer-min` | 60 | Mindestdauer in Minuten |
| `--dauer-max` | 120 | Maximale Dauer in Minuten |
| `--umstiege-min` | 1 | Mindestanzahl Umstiege |
| `--umstiege-max` | 5 | Maximale Anzahl Umstiege |
| `--qid` | – | Wikidata-QID des Ortes (nie raten) |
| `--output` | `ergebnis` | Ausgabeverzeichnis |
