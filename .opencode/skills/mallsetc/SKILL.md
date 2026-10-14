---
name: mallsetc
description: Findet besondere städtische Strukturen – große Malls, Bahnhöfe und Passagen mit mehreren Ausgängen, Ausgängen auf unterschiedlichen Ebenen und Anbindung an öffentliche Verkehrsmittel. Wird verwendet bei "suche Malls", "finde Einkaufszentren", "besondere städtische Strukturen" oder ähnlichen Anfragen.
---

# Skill: Besondere städtische Strukturen (Malls, Bahnhöfe, Passagen) finden

Findet in einer vom Nutzer genannten Region Einkaufszentren, Bahnhöfe und
Passagen, die folgende Eigenschaften erfüllen:

- **mehrere Ausgänge**
- **Ausgänge auf unterschiedlichen Ebenen**
- **Anbindung an öffentliche Verkehrsmittel**

Datenquellen (OSM/Overpass) werden abfragen, per Spatial Join in metrischem
Koordinatensystem analysiert und als Karte exportiert.
Das Verzeichnis `tasks/` ignorieren.

## Eingaben

- **Region** (Pflicht): Stadt, Stadtteil oder Bounding Box (S, W, N, E)
- Optional: `--output` (Ausgabeverzeichnis, Standard `ergebnis`),
  `--refresh` (Cache ignorieren und neu abrufen)

**Dateien dieses Skills** (Pfade relativ zum Skill-Verzeichnis):

| Datei | Inhalt |
|---|---|
| `reference/learnings.md` | Erfahrungsspeicher – vor Schritt 1 lesen, nach Schritt 8 ergänzen |
| `reference/datenquellen.md` | Overpass/Nominatim: Server, Filter, Abfrageregeln |
| `reference/kriterien.md` | Prüfkriterien, Schwellen, Entschärfungsreihenfolge |
| `reference/fehlerbehandlung.md` | Edge Cases und Sonderfälle |
| `reference/malls_suche.py` | Skriptvorlage |

## Prozess

1. **Learnings lesen.** `reference/learnings.md` komplett lesen und alle
   Hinweise für die Ziel-Region übernehmen (bewährte Server, Schwellen,
   Datenqualität) – sie gelten als Kontext für die Schritte 2–7.
2. **Region eingrenzen.** BBox um die Stadt/den Stadtteil legen (nie eine
   große Stadt ganz abfragen); Ortsnamen gemäß `reference/datenquellen.md`
   (§Nominatim) auflösen.
3. **OSM-Daten abrufen.** `reference/datenquellen.md` laden und deren
   Abschnitte anwenden: Overpass mit Fallback-Servern und den Filtern für
   Gebäude, ÖPNV und Eingänge. Als Vorlage: `reference/malls_suche.py`.
4. **Eingänge und ÖPNV den Gebäuden zuordnen.** Spatial Join in
   **metrischem CRS** (UTM): Eingänge am Gebäudepolygon (10 m Toleranz,
   60 m für Punkt-Kandidaten), ÖPNV-Zentroide im 200-m-Puffer. Auf die
   Positions-Spalte `bidx` gruppieren, nicht auf `index_right` (hängt von den
   Index-Namen ab).
5. **Kriterien prüfen.** `reference/kriterien.md` laden und **alle**
   Kriterien anwenden: ≥2 Eingänge, ≥1 ÖPNV in 200 m, ≥2 verschiedene
   Eingangsebenen (nur wenn Level-Daten vorhanden). Nicht bestandene
   Kandidaten verwerfen und mit Grund protokollieren.
6. **Rangieren und exportieren.** Verbliebene Kandidaten nach Ebenen- und
   Einganzahl ranken und wie in „Output" beschrieben nach `--output`
   schreiben.
7. **Bei Problemen** (0 Treffer, Overpass-Fehler, fehlende Level-Daten):
   `reference/fehlerbehandlung.md` laden und dort gereiht entschärfen –
   Kriterien nicht stillschweigend aufweichen. Reihenfolge:
   1) Eingangstoleranz 10→20 m, 2) ÖPNV-Radius 200→300 m,
   3) Ebenen-Kriterium weglassen (nur wenn keine Level-Daten vorhanden).
8. **Feedback holen und Learnings schreiben (Wrap-up).** Nach dem Export dem
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

- `kandidaten.geojson` – alle bestandenen Kandidaten mit Eigenschaften
  (Eingänge, Ebenen, ÖPNV-Anzahl)
- `kandidaten.kml` – Gebäudeumrisse je Kandidat als `<Placemark>`/`<Polygon>`,
  Style-Block, für Google Earth
- `kandidaten.gpx` – Waypoints mit Beschreibung („Eingänge: … | Ebenen: … |
  ÖPNV: …"), für GPS-Geräte
- `zusammenfassung.json` – Statistik, verworfene Kandidaten mit Grund

Danach dem Nutzer die Kartenanleitung geben: [umap.openstreetmap.de](https://umap.openstreetmap.de)
→ ☰ → „Daten importieren" → GeoJSON wählen (oder Drag & Drop) → „als neue
Ebene" → Karte teilen.

## Skript

`reference/malls_suche.py` ist die Vorlage für Schritte 3–6:

```bash
# Stadt
.venv/bin/python reference/malls_suche.py \
  --place "Dresden, Deutschland" --output results/dresden

# Stadtteil / Ausschnitt per Bounding Box (S W N E)
.venv/bin/python reference/malls_suche.py \
  --bbox 50.97 13.57 51.17 13.96 --output results/dresden-mitte
```

| Parameter | Standard | Beschreibung |
|---|---|---|
| `--place` | – | Stadt oder Stadtteil (z. B. „Dresden, Deutschland") |
| `--bbox` | – | Bounding Box (S, W, N, E) |
| `--output` | `ergebnis` | Ausgabeverzeichnis |
| `--refresh` | aus | Cache ignorieren und neu abrufen |
