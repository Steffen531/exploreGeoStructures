# Learnings: oepnvrouten

Erfahrungsspeicher des Skills. **Vor dem Lauf lesen** (`SKILL.md` Schritt 1),
**nach dem Lauf ergänzen** (`SKILL.md` Schritt 8: Rating 1–5 + Hinweise des
Nutzers).

Pflegen:

- Einträge kurz halten: 1–3 Sätze je Beobachtung, mit Region und Datum.
- Nur handlungsrelevante Beobachtungen aufnehmen: funktionierende
  Datenquellen/Regionen, GTFS-Besonderheiten, Routing-Ergebnisse,
  bewährte Verkehrsmittel-Prioritäten, OTP-Spezialitäten.
- Bei ~20 Einträgen aufräumen: Doppeltes verschmelzen, Veraltetes löschen,
  nach Themen sortieren.

## Was gut lief

- Stuttgart Hbf → Bad Cannstatt, 15.10.2026: 621 Stationen und 84 Linien (light_rail, bus) via Overpass-API im Hbf/Cannstatt-Bereich erfolgreich abgefragt. Abfrage in 5 Teile nach route_type aufgeteilt.
- Berlin Zoo → Ostkreuz, 16.10.2026: Netzwerk aus 5067 Stationen und 657 Linienrelationen (subway/train/tram/light_rail/bus) in ~4 Minuten aufgebaut; mit 150-m-Station-Clustering 1180 Verkehrsknoten, 6530 Kanten. 3 unterschiedliche Routen (66/76/110 Min) mit echten Fahrweg-Geometrien.

## Was nicht lief

- S-Bahn- und Tram-Relationsabfragen (route_type=train, tram) über Overpass lieferten 504 Timeouts.
- Ranking war falsch: Bus wurde über S-Bahn bevorzugt, weil die ersten 3 gefundenen Routen zurückgegeben wurden statt alle zu sammeln und nach Score zu rangieren.
- Verkehrsmittel-Prioritäten falsch: Bus hatte bessere Priorität als S-Bahn. Nutzer-Feedback 15.10.2026: Dauer ist hartes Fenster kein Ranking; Schienenverkehr (Straßenbahn, Regionalzug, U-Bahn, S-Bahn) muss Bus bevorzugen.
- Berlin 16.10.2026: **ohne Station-Clustering 0 Routen** – 1209 Zusammenhangskomponenten, weil S-Bahn/U-Bahn/Bus/Tram an einem Bahnhof getrennte OSM-Knoten sind. Erst Clustering (150 m) macht das Routing überhaupt möglich.
- Berlin 16.10.2026: `out members;` auf Linien-Relationen crasht den Overpass-Backend (502) – stattdessen `out body;`.
- Berlin 16.10.2026: OTP-Instanz Berlin (otp.bbnavi.de) nicht erreichbar.
- Berlin 16.10.2026: deterministischer DFS lieferte 3× dieselbe Route (alle 107 Min) – Kanten-Ausschluss pro Runde nötig.
- Berlin 16.10.2026: **Karte zeigte nur Luftlinien** zwischen den Haltestellen (Nur-Stationen-Knoten, linear interpoliert) – echte Fahrwege erst mit `relation(ID); way(r); out geom;` + BFS im Liniennetz.
- Berlin 16.10.2026: **OSM-Linien-Zuordnung zu ungenau für echte Zeiten** – der DFS wählt bei Kanten mit mehreren Linien beliebig eine aus, GTFS-Stops sind bahnsteiggenau → Zuordnung der OSM-Route an GTFS schlug fehl. Lösung: **zeitabhängiges GTFS-Routing** (früheste Ankunft) statt Anreicherung der OSM-Route. GTFS-Feed gtfs.de `nv_free` (Nahverkehr); `fv_free` ist nur Fernverkehr.

## Offene Fragen

- Fahrtzeiten aktuell geschätzt (Distanz / Modus-Geschwindigkeit) **nur noch im OSM-Fallback** – der GTFS-Pfad liefert echte Zeiten. GTFS-Extraktion (~8 Min pro Region) könnte per `shapes.txt` auch echte Streckengeometrien liefern (aktuell Stationen-Punkte).
