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

## Was nicht lief

- S-Bahn- und Tram-Relationsabfragen (route_type=train, tram) über Overpass lieferten 504 Timeouts.
- Ranking war falsch: Bus wurde über S-Bahn bevorzugt, weil die ersten 3 gefundenen Routen zurückgegeben wurden statt alle zu sammeln und nach Score zu rangieren.
- Verkehrsmittel-Prioritäten falsch: Bus hatte bessere Priorität als S-Bahn. Nutzer-Feedback 15.10.2026: Dauer ist hartes Fenster kein Ranking; Schienenverkehr (Straßenbahn, Regionalzug, U-Bahn, S-Bahn) muss Bus bevorzugen.

## Offene Fragen

- Fahrtzeiten aktuell geschätzt (3 Min/Segment), keine echten GTFS-Fahrpländaten. Könnte mit VVS-GTFS-Feed verbessert werden.
