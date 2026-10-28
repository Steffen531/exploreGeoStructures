# Implementierungsstatus

Stand: 2026-10-28

## Implementiert

- Normalisierte Workflow-, Kandidaten-, Capability-, Status- und Ergebnisverträge
- Räumliche und zeitliche Constraint-Engine mit metrischen Berechnungen
- Harte und weiche Constraints, Backtracking, Limits und partielle Lösungen
- Capability Registry für alle fünf Fach-Skills
- Adaptermodus der Fach-Skills mit `kandidaten.geojson` und `status.json`
- Providerneutrales Ride-Hailing-Straßenrouting als klar markierte Schätzung
- Gemeinsamer GeoJSON-, KML-, GPX- und Zusammenfassungsexport
- Vier Offline-Integrationsszenarien

## Live-Smoke-Tests

- Berlin, kleine Bounding Box: `behoerdenetc` lieferte 60 normalisierte
  OSM-Kandidaten mit Status `success`.
- Hamburg, kurze Straßenroute: Ride-Hailing-Adapter lieferte eine
  OSRM-Fahrgeometrie mit Status `degraded` und korrektem Hinweis, dass keine
  reale Anbieter-Verfügbarkeit bestätigt wurde.

Temporäre Ergebnisse lagen ausschließlich unter `/tmp/opencode`.

## Bekannte Grenzen

- `belebteOrte` verwendet derzeit OSM-POI-Dichte als zeitlich schwachen Proxy.
  Fahrgastzählungen, Events und Popular Times sind noch keine verlässlichen
  Standardkomponenten.
- `behoerdenetc` normalisiert derzeit primär OSM. Offizielle Register und
  Wikidata sind noch nicht als belastbare Adapter implementiert.
- `fussweg` unterstützt zwei Modi: Weginstandbesonderheiten (einzeln gespeicherte
  Ways, Standard) und Netzwerkmodus (`walk_mode: network`): topologischer
  Fußwegegraph (Dijkstra pro Startanker, Längenfenster, Geradheit ≥ 0.6,
  Ausschlussgeometrien). Erstmals produktiv genutzt am 2026-10-28 (Hamburg).
- Koordinatenbasierte ÖPNV-Suche benötigt einen passenden GTFS-Feed. Der
  OSM-Fallback akzeptiert bei GTFS-Ausfall momentan nur Namen.
- Ride-Hailing ohne Provider-API bestätigt weder Anbieter, Verfügbarkeit noch
  Preis.
- Live-Smoke-Tests der vollständigen langen Integrationsketten sind wegen
  externer Datenabhängigkeiten noch nicht reproduzierbar automatisiert;
  am 2026-10-28 lief die erste vollständige Live-Kette:
  Hamburg (Altona, 14.12.2026) mit 24 vollständigen Lösungen
  (ÖPNV→Mall→Ride→Fußweg), unter `results/workflow-20261214-hamburg-altona/`.
- `oepnvrouten`-Overpass-Cache ist jetzt queryabhängig gekoppelt
  (SHA-1-Suffix), zuvor verseuchten Berlin-Daten Distrikt-Ergebnisse.
- Orchestrierter OSM-Fallback respektiert nun `uhrzeit`, `arrival_window`
  und `exclude_route_prefixes` (reiner Fernverkehr ICE/IC/EC wird ausgeschlossen;
  Regionalzüge RE/RB bleiben ausdrücklich erhalten). Der GTFS-Zweig bricht für
  Hamburg am fehlenden `shapes.txt` im Deutschland-Feed ab (weiter offen).
- `exporter.py` verarbeitet GeometryCollections (Ausschlussmengen `selection: all`).
