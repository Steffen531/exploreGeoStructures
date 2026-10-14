# Prüfkriterien

Kontext für Schritt 5 des `SKILL.md`-Prozesses. Alle Kriterien sind
**Ausschlusskriterien** – nicht erfüllt = Kandidat verwerfen und in
`zusammenfassung.json` mit Grund protokollieren. Rangierung erst danach
(Schritt 6).

## Eingänge (Muss: mind. 2)

- Eingänge werden am **Gebäudepolygon** gematcht (Spatial Join, nicht am
  Zentrions-Puffer), mit **10 m Toleranz** an der Gebäudekante – Eingänge
  liegen meist genau auf der Wand.
- Punkt-Kandidaten (z. B. `railway=station` ohne Gebäudepolygon): **60 m
  Radius** um den Punkt.
- Zählweise: Anzahl der `entrance`-Nodes im Puffer je Gebäude.

## ÖPNV-Anbindung (Muss: mind. 1 in 200 m)

- ÖPNV-Zentroide im **200-m-Puffer** um das Gebäude zählen.
- **Nur in metrischem CRS prüfen** (z. B. UTM via `ox.projection.project_gdf`)
  – Grad sind keine Meter, ein Puffer in Grad ist wertlos.
- Puffer: 200 m um die Gebäudegeometrie (nicht nur den Zentrions).

## Ebenen (Muss: ≥ 2 verschiedene Eingangsebenen)

- `level`-Tags der Eingänge je Gebäude sammeln; verschiedene Ebenen zählen.
- Level-Syntax verarbeiten: `"0;1"`, `"0-2"` (Bereich), `"G;1"`.
- **Nur anwenden, wenn im Datensatz überhaupt Level-Daten vorhanden sind** –
  sonst das Kriterien weglassen und **warnen** (Datenqualität, keine
  Aussage über die Gebäude).
- In OSM sind Eingänge nur selten mit `level` getaggt (Dresden: 3,3 %) →
  Kriterium ist streng; bei 0 Level-Daten im Datensatz nicht anwenden.

## Spatial Join technisch

- Auf eine explizite **Positions-Spalte `bidx`** gruppieren, nicht auf
  `index_right` von `sjoin` – die Spalten hängen von den Index-Namen ab
  (benannter MultiIndex → KeyError).
- Alle Puffer metrisch (UTM) berechnen, Ergebnis zum Export in EPSG:4326
  zurückrechnen (KML/GPX nutzen immer lat/lon).

## Ohne Treffer

Erst in dieser Reihenfolge entschärfen, nichts anderes:

1. Eingangstoleranz 10 → 20 m,
2. ÖPNV-Radius 200 → 300 m,
3. Ebenen-Kriterium weglassen (nur wenn keine Level-Daten vorhanden).

**Niemals** die ÖPNV-Anbindung abschalten oder Eingänge unter 2 zulassen. Jede
Anpassung mit Region und Datum in `reference/learnings.md` notieren.
