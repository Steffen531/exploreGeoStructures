# Learnings: belebteOrte

Erfahrungsspeicher des Skills. **Vor dem Lauf lesen** (`SKILL.md` Schritt 1),
**nach dem Lauf ergänzen** (`SKILL.md` Schritt 9: Rating 1–5 + Hinweise des
Nutzters).

Pflegen:

- Einträge kurz halten: 1–3 Sätze je Beobachtung, mit Region und Datum.
- Nur handlungsrelevante Beobachtungen aufnehmen (was funktioniert, was
  nicht, was als Nächstes anders machen).
- Bei ~20 Einträgen aufräumen: Doppeltes verschmelzen, Veraltetes löschen,
  nach Themen sortieren.

## Was gut lief

- Potsdam (08.10.2026): Overpass-Filter pro Gruppe einzeln abfragen + Server-
  Rotation mit Backoff war robust (alle Grellen trotz 429/500/504 beantwortet).

## Was nicht lief

- Potsdam (08.10.2026): GPX/KML enthielten alle 4444 Orte statt nur der
  hochbewerteten + Cluster – Export für KML/GPX künftig auf Score ≥ 7 und
  250-m-Cluster beschränken (GeoJSON bleibt vollständig).
- Potsdam (08.10.2026): Cluster als einzelne Pins waren bei der Visualisierung
  nicht erkennbar → KML als Kreis-Polygon (transparente Füllung + dicke
  Kontur), GPX als geschlossenen Track exportieren.
- Potsdam (08.10.2026): Selbst Score≥7 (247 Orte) war noch zu viele für die
  Kartenansicht → KML/GPX zeigen nur Cluster + Top 10 Einzelorte (Sortierung:
  Score, dann POI-Dichte); Cluster weiter aus allen Score≥7-Orten berechnen.

## Offene Fragen
