# Prüfkriterien

Kontext für Schritt 5 des `SKILL.md`-Prozesses. Alle Kriterien sind
**Ausschlusskriterien** – nicht erfüllt = Kandidat verwerfen und in
`zusammenfassung.json` mit Grund protokollieren. Rangierung erst danach
(Schritt 6).

## Länge (Gehzeit)

- Haversine-Summe über alle Segmente.
- Standard **600–900 m ≈ 10 Minuten** (Annahme 60–80 m/min, Rechnung mit
  75 m/min).
- Andere Gehzeiten: z. B. 300–500 m für 5 Minuten, 1200–1800 m für 20 Minuten
  – über `--min-length`/`--max-length` setzen.

## Geradheit (Muss: möglichst geradlinig)

- Verhältnis **direkte Distanz (Start→Ende) / tatsächliche Weglänge**.
- **Harter Filter: Standard ≥ 0.95.** Kandidaten darunter verwerfen, nicht
  nur schlechter rangieren. 1.0 = perfekt gerade.
- Bei Konkurrenzen die geraderen Wege zuerst anbieten; für sehr gerade Wege
  `--straightness 0.98`.

## Kein Punkt zweimal (Muss)

- Der Weg darf keinen Punkt mehrfach besuchen – keine Schlaufen, keine
  Selbstüberschneidung, kein Zurücklaufen auf sich selbst.
- Prüfung 1: alle Stützpunkte eindeutig (keine doppelten Koordinaten).
- Prüfung 2: Geometrie simpel – `LineString(coords).is_simple` (shapely).
- **Kein Parameter, immer aktiv.**

## Parallelwege

- Puffer (Standard 50 m) um die Mittenlinie; andere Verkehrswege (Straßen,
  Radwege, Bahn-/Tramtrassen) im Puffer zählen.
- **Nur in metrischem Koordinatensystem prüfen** (z. B. UTM 32N via
  `pyproj.Transformer`) – Grad sind keine Meter, ein Puffer in Grad ist
  wertlos.
- Messung: alle 25 m einen Probe-Punkt; Anteil mit Verkehr ≤ 50 m.
  **Schwelle: ≤ 35 %** (eine querende Straße am Zugang bleibt darunter).
- Für große Städte: `--buffer 30`, wenn sonst 0 Treffer – nicht die
  Schwelle aufweichen.

## Abzweigungen

- Topologie: innere Knoten des Kandidaten, die er mit **anderen Fußwegen**
  teilt = Abzweigung (man könnte abbiegen). **Isoliert = 0 innere
  Abzweigungen.**
- Knoten am Start/Ende (Zugang zur Straße, ggf. Abschneiden an der
  BBox-Kante) zählen nicht als Abzweigung.

## Ohne Treffer

Erst in dieser Reihenfolge entschärfen, nichts anderes:

1. Länge um ±10 % erweitern (`--min-length`/`--max-length`),
2. Geradheit 0.95 → 0.90 (`--straightness`),
3. Puffer 50 → 30 m (`--buffer`).
4. Abzweigungen zulassen (`--allow-branches`): Kandidaten mit bis zu 5 inneren
   Abzweigungen akzeptieren, wenn alle anderen Kriterien erfüllt sind.

**Niemals** „kein Punkt zweimal" oder das Längenfenster abschalten. Jede
Anpassung mit Region und Datum in `reference/learnings.md` notieren.
