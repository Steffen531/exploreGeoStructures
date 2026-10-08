---
name: belebteOrte
description: Findet belebte Orte in Städten – wo halten sich zu bestimmten Zeiten viele Menschen auf? Nutzt OSM POI-Dichte, ÖPNV-Daten, Event-Kalender und Google Popular Times. Wird verwendet bei "suche belebte Orte", "wo ist viel los", "belebte Plätze" oder ähnlichen Anfragen.
---

# Skill: Belebte Orte finden

Findet Orte in einer vom Nutzer genannten Region, an denen sich zu bestimmten
Zeiten (Wochentag, Uhrzeit) viele Menschen aufhalten. Datenquellen (OSM
POI-Dichte, ÖPNV/GTFS, Event-Kalender, Google Popular Times) werden kombiniert,
auf die Stadtgrenze gefiltert, nach Belebtheit bewertet und als Karte exportiert.
Das Verzeichnis `tasks/` ignorieren.

## Eingaben

- **Region** (Pflicht): Stadt, Stadtteil oder Bounding Box
- **Zeitfenster** (Pflicht): Wochentag und Uhrzeit (z. B. „Dienstag 10:00")
- Optional: `--qid` (Wikidata-QID des Ortes), `--output` (Ausgabeverzeichnis,
  Standard `ergebnis`)

**Dateien dieses Skills** (Pfade relativ zum Skill-Verzeichnis):

| Datei | Inhalt |
|---|---|
| `reference/learnings.md` | Erfahrungsspeicher – vor Schritt 1 lesen, nach Schritt 9 ergänzen |
| `reference/datenquellen.md` | Endpunkte, OSM-Filter, Abfrageregeln |
| `reference/merge-regeln.md` | Deduplizierung, Name, Kategorie, Koordinaten |
| `reference/fehlerbehandlung.md` | Edge Cases und Sonderfälle |
| `reference/berlin.md` | Stadt-Referenz Berlin (Vorrang vor den anderen) |
| `reference/belebte_orte_suche.py` | Skriptvorlage |

## Prozess

1. **Learnings lesen.** `reference/learnings.md` komplett lesen und alle
   Hinweise für die Ziel-Region übernehmen (bekannte Fallstricke, bewährte
   Quellen, offene Fragen) – sie gelten als Kontext für die Schritte 2–8.
2. **Stadt-Referenz prüfen.** Für die Ziel-Stadt existiert eine Referenzdatei
   (Berlin → `reference/berlin.md`), dann deren Quellen, QIDs, Filter und
   Rauschfilter laden – sie hat Vorrang gegenüber den Angaben in Schritt 4 und
   6, soweit abweichend. Keine Referenz → normal weiter.
3. **Stadtgrenze bestimmen (Pflicht).** Nominatim-Regeln aus
   `reference/datenquellen.md` (§Nominatim) anwenden und die Grenze mit
   `polygon_geojson=1` holen. Die Bounding Box allein reicht nie – sie enthält
   Nachbarorte.
4. **Daten abrufen.** `reference/datenquellen.md` laden und deren Abschnitte
   anwenden: OSM/Overpass mit den Standardfiltern für POI-Dichte, ÖPNV/GTFS
   für Haltestellen-Frequenz, Event-Kalender für geplante Veranstaltungen,
   Google Popular Times (falls verfügbar) für Besucherzahlen. Fallback,
   Caching und QID-Verifikation wie dort beschrieben.
5. **Auf die Region filtern.** Jeden Treffer mit Koordinaten aus Schritt 4 mit
   shapely `contains()` gegen das Polygon aus Schritt 3 prüfen; ausgeschlossene
   Treffer loggen. Koordinatenlose Treffer behalten und später zählen.
6. **Zusammenführen.** `reference/merge-regeln.md` laden und alle Regeln
   anwenden: Deduplizierung mit den Schwellen der Stadt-Referenz, kanonischer
   Name, Kategorie-Zuweisung, Koordinaten-Priorität.
7. **Belebtheit bewerten.** Jeden Treffer nach Belebtheit bewerten:
   - OSM POI-Dichte (Anzahl POIs in der Umgebung)
   - ÖPNV-Frequenz (GTFS-Daten)
   - Event-Kalender (ob zum Zeitfenster Events stattfinden)
   - Google Popular Times (falls verfügbar)
   Treffer ohne Belebtheitsdaten mit „unbekannt" markieren.
8. **Exportieren** wie in „Output" beschrieben nach `--output` schreiben.
9. **Bei Problemen** (leere Treffer, fremde Treffer, unbekannte Region):
   `reference/fehlerbehandlung.md` laden und den passenden Eintrag ausführen.
10. **Feedback holen und Learnings schreiben (Wrap-up).** Nach dem Export dem
    Nutzer mit dem `question`-Tool zwei Fragen stellen:
    - Bewertung: **1–5** (Optionen „1 – sehr schlecht" bis „5 – sehr gut")
    - „Was war nicht gut? Was soll beim nächsten Lauf anders machen?" (Freitext,
      optional)
    Dann `reference/learnings.md` aktualisieren: **1–3 Sätze** unter
    „Was nicht lief" (bei konkreten Hinweisen) bzw. „Was gut lief" (bei
    Rating 5 ohne Einwände), immer mit Region und Datum. Bewertung 2–4 ohne
    Freitext → den Grund als offene Frage eintragen. Einträge nie löschen,
    nur bei ~20 Einträgen aufräumen (Regeln in `reference/learnings.md`).

## Output

Im Ausgabeverzeichnis (`--output`):

- `ergebnis.geojson` – alle Funde, inkl. `geometry: null` für koordinatenlose
- `ergebnis.kml` – Ordner je Kategorie, Style-Block `#pin`, für Google Earth
- `ergebnis.gpx` – für GPS-Geräte
- `zusammenfassung.json` – Statistiken, Deduplizierung, ausgeschlossene Punkte,
  Belebtheitsbewertung

Danach dem Nutzer die Kartenanleitung geben: [umap.openstreetmap.de](https://umap.openstreetmap.de)
→ ☰ → „Daten importieren" → GeoJSON wählen (oder Drag & Drop) → „als neue
Ebene" → Karte teilen.

## Skript

`reference/belebte_orte_suche.py` ist die Vorlage für Schritt 4, 6 und 7:

```bash
# Stadt
.venv/bin/python reference/belebte_orte_suche.py \
  --place "Berlin, Deutschland" --time "tuesday 10:00" --output results/berlin

# Stadtteil / Ausschnitt per Bounding Box (S W N E)
.venv/bin/python reference/belebte_orte_suche.py \
  --bbox 52.45 13.25 52.55 13.45 --time "tuesday 10:00" --output results/berlin-mitte
```

| Parameter | Standard | Beschreibung |
|---|---|---|
| `--place` | – | Stadt oder Stadtteil (z. B. „Berlin, Deutschland") |
| `--bbox` | – | Bounding Box (S, W, N, E) – ergänzt, ersetzt nicht die Grenze |
| `--time` | – | Zeitfenster (z. B. „tuesday 10:00", „samstag 14:00") |
| `--qid` | – | Wikidata-QID des Ortes (nie raten, siehe `reference/datenquellen.md`) |
| `--output` | `ergebnis` | Ausgabeverzeichnis |
