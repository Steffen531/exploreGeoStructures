# Datenquellen: Endpunkte und Abfrageregeln

Kontext für Schritt 4 des `SKILL.md`-Prozesses. Landes-Referenzen können
abweichende, erprobte Quellen vorgeben – deren Vorrang gilt.

## OpenStreetMap (Overpass)

**Server (Fallback-Reihenfolge):**

1. `https://overpass-api.de/api/interpreter`
2. `https://overpass.kumi.systems/api/interpreter`
3. `https://maps.mail.ru/osm/tools/overpass/api/interpreter`
4. `https://overpass.private.coffee/api/interpreter`

**Regeln:**

- Overpass ist lastabhängig: 3 Runden mit Backoff pro Anfrage, erst danach den
  nächsten Server versuchen.
- Antwort per Query-Hash in `cache/` cachen – sonst blockiert ein Lauf bei
  504/Timeout aller Server.
- Für `node`, `way` **und** `relation` abfragen, `out center`.

**Standardfilter:**

- `amenity=police|townhall|embassy|courthouse|public_building|fire_station`
- `office=government|diplomatic|tax`
- `building=government` (fast überall leer, trotzdem mitabfragen)

## Nominatim

- Endpoint: `https://nominatim.openstreetmap.org`
- Max. 1 Anfrage/s; Ergebnisse in `cache/geocode.json` cachen.
- Stadtgrenze: `polygon_geojson=1`, Ergebnis als shapely-Polygon für den
  Regionsfilter in Schritt 3/5 von `SKILL.md`.
- Auch für fehlende Koordinaten (Geocoding) nutzen.

## Wikidata (SPARQL)

- Endpoint: `https://query.wikidata.org/sparql`, `format=json`,
  Accept-Header `application/sparql-results+json`.
- **Klassen-QIDs nie raten:** vorher verifizieren mit
  `SELECT ?x WHERE { ?x wdt:P31 wd:QID } LIMIT 3` – keine Instanzen = keine
  Klasse. Erprobte Klassenlisten stehen in den Landes-Referenzen (NL:
  `reference/niederlande.md` §3) und gelten als Vorlage auch für andere Länder.
- **Abfrage in zwei Schritten:** erst den Ort auflösen (per QID
  `?item wdt:P131* wd:Q…` oder Label-Suche mit Länder-Constraint `wdt:P17`,
  Orts-QID nie raten), dann die Klassen mit `VALUES ?klasse { … }` abfragen.
  Ohne QID-Ortsangabe kommen Fremdtreffer aus anderen Städten ins Ergebnis.
- **Rauschfilter vor dem Merge:** Landes-Referenz hat Vorrang (NL:
  `reference/niederlande.md` §3). Ohne Referenz mindestens: Item-Name ==
  Regionsname verwerfen; Beschreibung enthält `voormalig|former|opgeheven`;
  unaufgelöste Labels (nur `Q<nummer>`) verwerfen.
- Koordinaten kommen als WKT **`Point(lon lat)`** – Länge vor Breite.
- Ergebnisse pro QID gruppieren: ein Item kann mehrere Klassen haben →
  sonst Duplikate.

## Offizielles Register / Open Data

- Zuerst nach Open-Data-Portal oder Landesregister der Stadt/des Landes suchen
  (CKAN, WFS, CSV, GeoJSON, API).
- Beispiele: Wien `data.gv.at`, Berlin `daten.berlin.de`, London `data.gov.uk`,
  New York `opendata.cityofnewyork.us`.
- Niederlande: `reference/niederlande.md` §1 (Register van
  Overheidsorganisaties, XML-Export).
- Vorhandenes Register hat Vorrang vor OSM/Wikidata als Namens- und
  Adressquelle.
