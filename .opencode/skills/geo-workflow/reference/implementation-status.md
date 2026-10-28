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
- `fussweg` bewertet einzelne OSM-Ways. Ein vollständiger topologischer
  Fußwegegraph für über mehrere Ways zusammengesetzte Wege fehlt noch.
- Koordinatenbasierte ÖPNV-Suche benötigt einen passenden GTFS-Feed. Der
  OSM-Fallback akzeptiert bei GTFS-Ausfall momentan nur Namen.
- Ride-Hailing ohne Provider-API bestätigt weder Anbieter, Verfügbarkeit noch
  Preis.
- Live-Smoke-Tests der vollständigen langen Integrationsketten sind wegen
  externer Datenabhängigkeiten noch nicht reproduzierbar automatisiert.
