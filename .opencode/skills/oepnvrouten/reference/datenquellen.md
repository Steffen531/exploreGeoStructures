# Datenquellen und Abfrageregeln

Kontext für Schritte 2–4 des `SKILL.md`-Prozesses.

## OpenStreetMap (Overpass API)

**Server (Fallback-Reihenfolge):**

1. `https://overpass-api.de/api/interpreter`
2. `https://overpass.kumi.systems/api/interpreter`
3. `https://maps.mail.ru/osm/tools/overpass/api/interpreter`
4. `https://overpass.private.coffee/api/interpreter`

**Filter (ÖPNV-Stationen & Linien):**

- `node["public_transport"="station"]`
- `node["public_transport"="stop_position"]`
- `node["highway"="bus_stop"]`
- `node["railway"="station"]`
- `node["railway"="halt"]`
- `node["amenity"="ferry_terminal"]`
- `relation["type"="route"]["route"="bus|subway|tram|train|light_rail|ferry"]`

**Abfrageregeln:**

- **Eigenen User-Agent mitsenden** – der python-requests-Default bringt von
  `overpass-api.de` ein **HTTP 406**.
- **`out body;` für Linien-Relationen** – `out members;` lässt den
  Overpass-Backend crashen (**502 Bad Gateway**). `out body;` liefert
  Relationen samt Member-Liste (Stationenfolge) inkl. Rollen.
- **Echte Fahrwege separat holen:** `relation(ID); way(r); out geom;` – so
  bekommt man die Strecken-Segmente (Wege mit Geometrie) einer Linie. Ohne
  das zeigt die Karte nur Luftlinien zwischen den Haltestellen.
- **Station-Clustering ist Pflicht:** S-Bahn/U-Bahn/Bus/Tram an einem Bahnhof
  sind in OSM getrennte Knoten. Ohne Clustering zerfällt der Graph in hunderte
  Komponenten und es gibt keine Routen (Berlin: 1209 Komponenten ohne,
  1180 Verkehrsknoten mit 150-m-Clustering). Cluster-Radius 150 m.
- **Keine rekursiven Großabfragen** über große BBoxen – es endet mit 504/500
  auf allen Servern. Stattdessen **pro route_type einzeln** abfragen.
- **429 = Rate-Limit**: Backoff mit steigender Wartezeit, nach einem Durchlauf
  den nächsten Server; nie dieselbe Abfrage im Kreis wiederholen.
- **BBox klein halten** (Stadtteil/Suchfeld, nicht die ganze Stadt).
- **OTP-Instanz prüfen, aber nicht verlassen:** `https://otp.bbnavi.de` (Berlin)
  war am 16.10.2026 nicht erreichbar – Overpass + eigene Routing-Implementierung
  ist der zuverlässigere Weg.

## GTFS-Feeds

**Bewährte Quelle (Deutschland):** `https://download.gtfs.de/germany/nv_free/latest.zip`
(gtfs.de, aus dem DELFI/NeTEx-Datensatz generiert). Enthält den gesamten
deutschen **Nahverkehr** (U-Bahn, S-Bahn, Tram, Bus) – 278 MB ZIP,
`stop_times.txt` ~2,2 GB. Der Feed `fv_free` enthält nur DB-Fernverkehr
(EC/ICE) und ist für Nahverkehr-Routing unbrauchbar.

**Suche (andere Regionen):**

1. Bekannte Feed-URLs direkt verwenden (Berlin→VBB, Hamburg→HVV, München→MVV,
   Wien→Wiener Linien, Zürich→opentransportdata.swiss, Paris→Île-de-France,
   London→TfL, New York→MTA, Tokyo→ODPT, Sydney→Transport for NSW).
2. TransitFeeds.com API als Fallback (braucht API-Key).
3. Lokale Verkehrsbetreiber kontaktieren.

**GTFS-Standard-Dateien:**

- `stops.txt` – Haltestellen mit Koordinaten
- `routes.txt` – Linien (route_type: 0=Tram, 1=U-Bahn, 2=S-Bahn, 3=Bus, 4=Fähre)
- `trips.txt` – Fahrten mit Service-IDs
- `stop_times.txt` – Abfahrts-/Ankunftszeiten je Haltestelle
- `calendar.txt` / `calendar_dates.txt` – Wochentage/Ausnahmen je Service
- `shapes.txt` – Streckengeometrie (für echte Fahrwege auf der Karte)

**Extraktion (bewährt, Berlin 16.10.2026):**

- Feed herunterladen und in `cache/gtfs_nv.zip` ablegen (nicht erneut laden).
- Nur die **Region** extrahieren: `stops.txt` auf die BBox filtern, dann
  `stop_times.txt` **zweimal** streamen (1. Trip-IDs mit Region-Stopps,
  2. Haltestellenfolgen). Kalender anhand des Datums prüfen
  (`calendar.txt` Wochentag + `calendar_dates.txt` Ausnahmen).
- Ergebnis als Pickle in `cache/gtfs_<datum>_<bbox-hash>.pkl` cachen.
- 2,2 GB `stop_times.txt` streamen dauert pro Durchlauf einige Minuten –
  nur einmal pro Region/Datum.

**Hinweis:** GTFS-ZIPs können groß sein (>100 MB). Nach dem Download cachen
und lokal parsen.

## OpenTripPlanner (OTP)

**Bekannte Instanzen:**

- Berlin: `https://otp.bbnavi.de`
- Hamburg: `https://otp.hamburg.de`
- München: `https://otp.mvv-muenchen.de`
- Frankfurt: `https://otp.rmv.de`

**Verwendung:** OTP kombiniert GTFS + OSM und bietet Routing-Algorithmen
out-of-the-box. Fallback auf eigene Routing-Implementierung
(`reference/routing-regeln.md`), falls keine Instanz verfügbar.

## Nominatim

- Endpoint: `https://nominatim.openstreetmap.org`, max. 1 Anfrage/s,
  eigenen User-Agent mitsenden, Ergebnisse cachen.
- Ortsnamen in eine BBox/Auflösung überführen (`accept-language` setzen).
- Für die Stadtgrenze: `polygon_geojson=1` (dann shapely `contains()` als
  Regionsfilter).

## OSRM (Straßenrouting)

- Endpoint: `https://router.project-osrm.org`
- Für Fußwege zwischen nahegelegenen Stationen und Ride-Hailing-Brücken.
- Route: `GET /route/v1/{profile}/{coords}?overview=false`

## Ride-Hailing Anbieter

| Anbieter | Region | API |
|----------|--------|-----|
| Uber | Global | Entwickler-API |
| Bolt | Europa, Afrika | Bolt Business |
| Didi | China, Lateinamerika | Didi Open Platform |
| Grab | Südostasien | Grab for Developers |
| Ola | Indien | Ola Developer |
| Yandex.Taxi | Russland | Yandex Maps |
| Gojek | Südostasien | Gojek for Business |
| Free Now | Europa | Free Now API |
| InDriver | Russland, Lateinamerika | Eingeschränkt |

**Verwendung:** Als Brücke für fehlende ÖPNV-Verbindungen. Preise variieren,
API-Keys erforderlich. Im Routing mit niedriger Priorität (Score-Strafe).
