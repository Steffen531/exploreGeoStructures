---
name: geo-workflow
description: Plant und kombiniert mehrere räumlich oder zeitlich voneinander abhängige Geo-Skills, Wege, Orte und Verkehrsmittel zu einem gemeinsamen Workflow.
---

# Skill: Räumlich-zeitliche Geo-Workflows

Verwende diesen Skill, sobald eine Anfrage mindestens zwei voneinander
abhängige Geo-Aufgaben enthält. Der Skill ist ein Orchestrator: Fachliche
Kandidaten kommen weiterhin aus `fussweg`, `oepnvrouten`, `belebteOrte`,
`mallsetc` und `behoerdenetc`.

## Ablauf

1. Lies `reference/contracts.md`, `reference/implementation-status.md` und
   `reference/learnings.md`.
2. Zerlege die Anfrage in Knoten und explizite räumliche/zeitliche Constraints.
3. Frage nur nach Angaben, deren Fehlen das Ergebnis wesentlich verändert,
   etwa einem Ausschlussradius. Erfinde keine versteckten Toleranzen.
4. Lies die `capabilities.json` aller benötigten Skills. Verwende nur dort als
   implementiert ausgewiesene Fähigkeiten.
5. Erzeuge und validiere `workflow.json` nach `schemas/workflow.schema.json`.
6. Lade die benötigten Fach-Skills mit dem `skill`-Tool. Bei orchestrierten
   Läufen entfallen deren einzelne Feedbackrunden.
7. Erzeuge je Knoten normalisierte Kandidaten nach
   `schemas/candidate.schema.json` und einen `status.json`. Ein Fehler ist kein
   leeres Ergebnis.
8. Plane mit `reference/planner.py` und verbinde Kandidaten mit
   `reference/constraint_engine.py`. Harte Constraints nie still lockern.
   Verwende für Ausschlussmengen wie „alle Behörden vermeiden“ am Zielknoten
   zwingend `selection: all`.
9. Kennzeichne Ride-Hailing ohne Providerdaten als
   `estimated_ride_hailing`; behaupte weder Anbieter noch Preis oder reale
   Verfügbarkeit.
10. Exportiere die Gesamtlösung mit `reference/exporter.py`. Das erzeugt:
    Gesamtlösung als `ergebnis.geojson`, `ergebnis.kml`, `ergebnis.gpx`,
    `zusammenfassung.json`, dazu einen menschenlesbaren `zeitplan.md`
    (plus `zeitplan.json`) mit Linien, Abfahrts-/Ankunftszeiten und
    Umstiegsstationen je Lösung (so weit der Datenstand das hergibt) und
    Karten je Route unter `karten/route-N/` (GeoJSON, KML, GPX).
11. Frage genau einmal nach Feedback zum Gesamtworkflow und ergänze danach
    `reference/learnings.md`.

## Ausführung

Die natürlichsprachliche Zerlegung übernimmt das LLM. Python übernimmt
Schema-/Capability-Prüfung, räumliche und zeitliche Joins, Backtracking und
Export. Die Reihenfolge wird aus Abhängigkeiten und festen Zeit-/Ortsankern
ermittelt; sie ist nicht im Skill fest codiert.

## Ausgabe

Schreibe nach `results/<workflow-id>/`:

- `workflow.json` und `plan.json`
- `candidates/<node-id>/kandidaten.geojson` und `status.json`
- `ergebnis.geojson`, `ergebnis.kml`, `ergebnis.gpx`
- `zusammenfassung.json`
- `zeitplan.md` und `zeitplan.json` (menschenlesbar: Linien, Zeiten,
  Umstiegsstationen je Top-Route, soweit verfügbar)
- `karten/route-N/ergebnis.geojson|.kml|.gpx` (Karte je Top-Route)

Erkläre anschließend den Import auf
[umap.openstreetmap.de](https://umap.openstreetmap.de): „Erstelle eine Karte“
→ Symbol „Daten importieren“ (dunkler Pfeil nach oben, rechte Symbolleiste) →
GeoJSON-Datei wählen → „In eine neue Ebene importieren“ → „Importieren“.
