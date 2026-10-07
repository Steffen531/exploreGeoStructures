---
name: behoerdenetc
description: Findet Behörden, Polizeidienststellen und Botschaften in beliebigen Städten oder Stadtteilen weltweit. Wird verwendet bei "suche Behörden", "finde Polizei", "finde Botschaften" oder ähnlichen Anfragen.
---

# Skill: Behörden, Polizei & Botschaften finden

Findet Behörden, Polizeidienststellen, Botschaften und Konsulate in einer vom
Nutzer genannten Region. Datenquellen (OSM, Register/Open Data, Wikidata) werden
kombiniert, auf die Stadtgrenze gefiltert, bereinigt und als Karte exportiert.
Das Verzeichnis `tasks/` ignorieren.

## Eingaben

- **Region** (Pflicht): Stadt, Stadtteil oder Bounding Box
- Optional: `--qid` (Wikidata-QID des Ortes), `--register-city`,
  `--output` (Ausgabeverzeichnis, Standard `ergebnis`)

**Dateien dieses Skills** (Pfade relativ zum Skill-Verzeichnis):

| Datei | Inhalt |
|---|---|
| `reference/learnings.md` | Erfahrungsspeicher – vor Schritt 1 lesen, nach Schritt 9 ergänzen |
| `reference/datenquellen.md` | Endpunkte, OSM-Filter, Abfrageregeln |
| `reference/merge-regeln.md` | Deduplizierung, Name, Kategorie, Koordinaten |
| `reference/fehlerbehandlung.md` | Edge Cases und Sonderfälle |
| `reference/niederlande.md` | Landes-Referenz NL (Vorrang vor den anderen) |
| `reference/behoerden_suche.py` | Skriptvorlage |

## Prozess

1. **Learnings lesen.** `reference/learnings.md` komplett lesen und alle
   Hinweise für die Ziel-Region übernehmen (bekannte Fallstricke, bewährte
   Quellen, offene Fragen) – sie gelten als Kontext für die Schritte 2–8.
2. **Landes-Referenz prüfen.** Für das Ziel-Land existiert eine Referenzdatei
   (NL → `reference/niederlande.md`), dann deren Quellen, QIDs, Filter und
   Rauschfilter laden – sie hat Vorrang gegenüber den Angaben in Schritt 4 und
   6, soweit abweichend (Merge-Schwellen für NL: `reference/merge-regeln.md`,
   dort verifiziert). Keine Referenz → normal weiter.
3. **Stadtgrenze bestimmen (Pflicht).** Nominatim-Regeln aus
   `reference/datenquellen.md` (§Nominatim) anwenden und die Grenze mit
   `polygon_geojson=1` holen. Die Bounding Box allein reicht nie – sie enthält
   Nachbarorte.
4. **Daten abrufen.** `reference/datenquellen.md` laden und deren Abschnitte
   anwenden: OSM/Overpass mit den Standardfiltern, vorhandenes Register bzw.
   Open Data ergänzend, Wikidata/SPARQL als Ergänzung. Fallback, Caching und
   QID-Verifikation wie dort beschrieben.
5. **Auf die Region filtern.** Jeden Treffer mit Koordinaten aus Schritt 4 mit
   shapely `contains()` gegen das Polygon aus Schritt 3 prüfen; ausgeschlossene
   Treffer loggen. Koordinatenlose Treffer behalten und später zählen.
6. **Zusammenführen.** `reference/merge-regeln.md` laden und alle Regeln
   anwenden: Deduplizierung mit den Schwellen der Landes-Referenz, kanonischer
   Name, Kategorie-Zuweisung, Koordinaten-Priorität.
7. **Exportieren** wie in „Output" beschrieben nach `--output` schreiben.
8. **Bei Problemen** (leere Treffer, fremde Treffer, unbekannte Region):
   `reference/fehlerbehandlung.md` laden und den passenden Eintrag ausführen.
9. **Feedback holen und Learnings schreiben (Wrap-up).** Nach dem Export dem
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
- `zusammenfassung.json` – Statistiken, Deduplizierung, ausgeschlossene Punkte

Danach dem Nutzer die Kartenanleitung geben: [umap.openstreetmap.de](https://umap.openstreetmap.de)
→ ☰ → „Daten importieren" → GeoJSON wählen (oder Drag & Drop) → „als neue
Ebene" → Karte teilen.

## Skript

`reference/behoerden_suche.py` ist die Vorlage für Schritt 4, 6 und 7:

```bash
# Stadt
.venv/bin/python reference/behoerden_suche.py \
  --place "Wien, Österreich" --output results/wien

# Stadtteil / Ausschnitt per Bounding Box (S W N E)
.venv/bin/python reference/behoerden_suche.py \
  --bbox 48.10 16.20 48.30 16.50 --output results/wien-west
```

| Parameter | Standard | Beschreibung |
|---|---|---|
| `--place` | – | Stadt oder Stadtteil (z. B. „Wien, Österreich") |
| `--bbox` | – | Bounding Box (S, W, N, E) – ergänzt, ersetzt nicht die Grenze |
| `--qid` | – | Wikidata-QID des Ortes (nie raten, siehe `reference/datenquellen.md`) |
| `--register-city` | – | Stadtname für Register-/Open-Data-Filter |
| `--output` | `ergebnis` | Ausgabeverzeichnis |
