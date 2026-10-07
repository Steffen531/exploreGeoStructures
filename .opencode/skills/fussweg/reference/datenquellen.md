# Datenquellen und Abfrageregeln

Kontext für Schritt 4 des `SKILL.md`-Prozesses.

## OpenStreetMap (Overpass API)

**Server (Fallback-Reihenfolge):**

1. `https://overpass-api.de/api/interpreter`
2. `https://overpass.kumi.systems/api/interpreter`
3. `https://maps.mail.ru/osm/tools/overpass/api/interpreter`
4. `https://overpass.private.coffee/api/interpreter`

**Filter (Kandidaten):** `highway=footway|path|pedestrian|steps`

**Abfrageregeln** (erprobt, Lauf München-Giesing 07.10.2026):

- **Eigenen User-Agent mitsenden** (`headers={"User-Agent": "..."}`) – der
  python-requests-Default bringt von `overpass-api.de` ein **HTTP 406**.
- **Keine rekursiven Abfragen** (`...; >; out skel qt;`) über größere BBoxen –
  es endet mit 504/500 auf allen Servern. Stattdessen **zwei kleine
  Abfragen** mit `out geom;` (Kandidaten getrennt von Verkehrs-/Bahnwegen);
  Knoten werden über identische Koordinaten erkannt, nicht über Node-IDs.
- **429 = Rate-Limit**: Backoff mit steigender Wartezeit, nach einem Durchlauf
  den nächsten Server; nie dieselbe Abfrage im Kreis wiederholen.
- **BBox klein halten** (Stadtteil/Kandidat, nicht die ganze Stadt).

## Nominatim

- Endpoint: `https://nominatim.openstreetmap.org`, max. 1 Anfrage/s,
  eigenen User-Agent mitsenden, Ergebnisse cachen.
- Ortsnamen in eine BBox/Auflösung überführen (`accept-language` setzen).
- Für die Stadtgrenze: `polygon_geojson=1` (dann shapely `contains()` als
  Regionsfilter).
