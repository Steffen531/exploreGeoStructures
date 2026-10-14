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
- **Keine rekursiven Großabfragen** über große BBoxen – es endet mit 504/500
  auf allen Servern. Stattdessen **zwei kleine Abfragen** mit `out geom;`.
- **429 = Rate-Limit**: Backoff mit steigender Wartezeit, nach einem Durchlauf
  den nächsten Server; nie dieselbe Abfrage im Kreis wiederholen.
- **BBox klein halten** (Stadtteil/Suchfeld, nicht die ganze Stadt).

## GTFS-Feeds

**Suche:**

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
- `calendar.txt` – Wochentage je Service

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
