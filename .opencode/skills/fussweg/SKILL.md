---
name: fussweg
description: Findet ungewöhnliche, isolierte Fußwege in beliebigen Städten, Stadtteilen oder Orten weltweit. Wird verwendet bei "suche Fussweg" oder "finde Fussweg".
---

# Skill: Isolierte Fußwege finden

Findet ungewöhnliche, isolierte Fußwege in einer vom Nutzer genannten Region.
Ein isolierter Fußweg: bestimmte Gehzeit (Standard ~10 Minuten), nur zu Fuß
begehbar, keine parallel verlaufenden Verkehrswege, keine Abzweigungen,
möglichst geradlinig und ohne einen Punkt zweimal zu besuchen.

## Eingaben

- **Region** (Pflicht): Stadt, Stadtteil, Ort oder Bounding Box (S, W, N, E)
- Optional: Gehzeitfenster (`--min-length`/`--max-length`), Geradheitsschwelle
  (`--straightness`), Puffer (`--buffer`), Abzweigungen (`--allow-branches`),
  `--output`

**Dateien dieses Skills** (Pfade relativ zum Skill-Verzeichnis):

| Datei | Inhalt |
|---|---|
| `reference/learnings.md` | Erfahrungsspeicher – vor Schritt 1 lesen, nach Schritt 8 ergänzen |
| `reference/strukturtypen.md` | Regionale Strukturtypen als Suchvorwissen |
| `reference/datenquellen.md` | Overpass/Nominatim: Server, Filter, Abfrageregeln |
| `reference/kriterien.md` | Prüfkriterien, Schwellen, Entschärfungsreihenfolge |
| `reference/fussweg_suche.py` | Skriptvorlage |

## Prozess

1. **Learnings lesen.** `reference/learnings.md` komplett lesen und Hinweise
   für die Ziel-Region übernehmen (bewährte Strukturtypen, Serverbesonderheiten,
   Schwellen) – sie gelten als Kontext für die Schritte 2–7.
2. **Region analysieren.** `reference/strukturtypen.md` laden und passende
   Strukturtypen für die Region wählen (z. B. Küste → Deichwege, Vorort →
   Durchgangswege) – das ist das Suchvorwissen für Schritt 4.
3. **Region eingrenzen.** BBox um den Kandidaten bzw. den Stadtteil legen
   (nie die ganze Stadt abfragen); Ortsnamen gemäß `reference/datenquellen.md`
   (§Nominatim) auflösen.
4. **OSM-Daten abrufen.** `reference/datenquellen.md` laden und deren
   Abschnitte anwenden: Overpass mit Fallback-Servern und den Filtern
   `highway=footway|path|pedestrian|steps`, eigener User-Agent, keine
   rekursiven Großabfragen. Als Vorlage: `reference/fussweg_suche.py`.
5. **Kriterien prüfen.** `reference/kriterien.md` laden und **alle**
   Kriterien anwenden: Länge (Haversine), Geradheit (harter Filter ≥ 0.95),
   kein Punkt zweimal (`LineString.is_simple` + eindeutige Stützpunkte),
   Parallelwege (metrischer Puffer, ≤ 35 %), Abzweigungen (0 innere).
   Nicht bestandene Kandidaten verwerfen und mit Grund protokollieren.
6. **Rangieren und exportieren.** Verbliebene Kandidaten nach Isolation und
   Geradheit ranken (geradeste/wegeisolierteste zuerst) und wie in „Output"
   beschrieben nach `--output` schreiben.
7. **Bei Problemen** (0 Treffer, Overpass-Fehler): `reference/kriterien.md`
   (§Ohne Treffer) konsultieren und dort gereiht entschärfen – Kriterien
   nicht stillschweigend aufweichen. Reihenfolge: 1) Länge ±10 %,
   2) Geradheit 0.95→0.90, 3) Puffer 50→30 m, 4) Abzweigungen bis zu 5 zulassen.
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

- `ergebnis.geojson` – alle bestandenen Kandidaten mit Eigenschaften
  (Länge, Gehzeit, Geradheit, Parallel-Anteil, Abzweigungen)
- `ergebnis.kml` – Linien je Kandidat, Style-Block, für Google Earth
- `ergebnis.gpx` – Tracks für GPS-Geräte
- `zusammenfassung.json` – Statistik, verworfene Kandidaten mit Grund

Danach dem Nutzer die Kartenanleitung geben: [umap.openstreetmap.de](https://umap.openstreetmap.de)
→ ☰ → „Daten importieren" → GeoJSON wählen (oder Drag & Drop) → „als neue
Ebene" → Karte teilen.
