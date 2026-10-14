# Datenquellen: Endpunkte und Abfrageregeln

Kontext für Schritt 3 des `SKILL.md`-Prozesses.

## OpenStreetMap (Overpass)

**Server (Fallback-Reihenfolge):**

1. `https://overpass-api.de/api` (Hauptserver; TLS-Front brockelt oft)
2. `http://overpass-api.de/api` (Fallback, wenn 443 verweigert)
3. `https://maps.mail.ru/osm/tools/overpass/api`
4. `https://overpass.kumi.systems/api`
5. `https://overpass.private.coffee/api`

Hinweise:

- Basis-URLs angeben – osmnx hängt selbst `/interpreter` an; volle
  Interpreter-URLs erzeugen `…/api/interpreter/interpreter` → ConnectionError.
- **DNS-Pinning abschalten** (`ox_http._config_dns = lambda url: None`):
  osmnx pinnt sonst eine feste IP; ist diese IP des Round-Robins tot, scheitern
  alle Abfragen mit „Connection refused", obwohl der Server läuft.
- `settings.overpass_rate_limit = False` – osmnx wartet sonst vor jedem
  Request am `/status`-Endpunkt (60 s, bei 504 zusätzlich 55 s, ggf. endlos).
  Stattdessen eigenes Backoff + hartes Zeitlimit (`SIGALRM`, 120 s).

**Filter (je Datensatz getrennt abfragen):**

- Gebäude: `building=mall|train_station|retail|supermarket`,
  `shop=department_store|mall`, `railway=station`
- ÖPNV: `public_transport=station|stop_position|platform`,
  `railway=station|halt|tram_stop`, `amenity=bus_station`
- Eingänge: `entrance=yes|main|exit|secondary|service|staircase|elevator`

**Abfrageregeln:**

- **Eigenen User-Agent mitsenden** – der requests-Default wird von
  overpass-api.de mit HTTP 406 abgelehnt.
- **Bbox statt Stadtgrenze:** die Stadtgrenze als Polygon hat tausende
  Knoten → osmnx baut einen ~2,5 MB großen Query-Body → Mirrors antworten mit
  413. `features_from_bbox` erzeugt einen ~3 KB großen Body und liefert
  praktisch dieselben Treffer.
- **Nominatim für die BBox** nutzen (`geocode_to_gdf`), nicht für die
  Abfrage selbst.
- Antworten als Pickle in `cache/` cachen (`REFRESH=1` / `--refresh`
  umgeht den Cache) – GPKG verträgt Spaltennamen mit Doppelpunkt nicht.
- **429 = Rate-Limit:** Backoff mit steigender Wartezeit, danach nächster
  Server; nie dieselbe Abfrage im Kreis wiederholen.
- **413 = Body zu groß:** Query auf Bbox umstellen oder Filter splitten.
- **504/500:** nicht als „leeres Ergebnis" werten – prüfen, ob ein anderer
  Server antwortet.

## Nominatim

- Endpoint: `https://nominatim.openstreetmap.org`, max. 1 Anfrage/s,
  eigenen User-Agent mitsenden, Ergebnisse cachen.
- Für die BBox der Region (`accept-language` setzen); für die exakte
  Stadtgrenze `polygon_geojson=1` (optional – siehe `SKILL.md` Schritt 7).
