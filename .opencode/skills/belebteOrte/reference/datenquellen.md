# Datenquellen: Endpunkte und Abfrageregeln

Kontext für Schritt 4 des `SKILL.md`-Prozesses. Stadt-Referenzen können
abweichende, erprobte Quellen vorgeben – deren Vorrang gilt.

## OpenStreetMap (Overpass) – POI-Dichte

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

**Standardfilter für belebte Orte:**

- `shop=*` (Geschäfte, Supermärkte, Boutiquen)
- `amenity=cafe|restaurant|bar|pub|fast_food|ice_cream|food_court` (Gastronomie)
- `amenity=marketplace|theatre|cinema|museum|library|community_culture|arts_culture`
  (Kultur & Märkte)
- `amenity=bank|atm|pharmacy|post_office|police|fire_station|hospital|clinic`
  (Öffentliche Einrichtungen)
- `public_transport=platform|stop_position` (ÖPNV-Haltestellen)
- `railway=station|tram_stop|subway_entrance` (Bahnhöfe, U-Bahnhöfe)
- `leisure=park|playground|stadium|sports_centre|track|pitch|golf_course|marina`
  (Freizeit & Sport)
- `tourism=hotel|hostel|guest_house|information|viewpoint|attraction|artwork`
  (Tourismus)
- `office=*` (Büros, vor allem in Geschäftsvierteln)

**POI-Dichte berechnen:**
- POIs in einer Umgebung (z. B. 200 m Radius) zählen
- Dichte = Anzahl POIs / Fläche
- Höhere Dichte → wahrscheinlich belebter

## Nominatim

- Endpoint: `https://nominatim.openstreetmap.org`
- Max. 1 Anfrage/s; Ergebnisse in `cache/geocode.json` cachen.
- Stadtgrenze: `polygon_geojson=1`, Ergebnis als shapely-Polygon für den
  Regionsfilter in Schritt 3/5 von `SKILL.md`.
- Auch für fehlende Koordinaten (Geocoding) nutzen.

## ÖPNV-Daten (GTFS)

- **Berlin:** BVG GTFS-Feed (offen verfügbar)
  - URL: `https://www.vbb.de/media/download/2024` (regelmäßig aktualisiert)
  - Alternativ: `https://www.bvg.de/de/verbindungen/fahrplanauskunft` (Web)
- **Allgemein:** GTFS-Feed der jeweiligen Verkehrsgesellschaft suchen
  (z. B. „<Stadt> GTFS feed" oder auf transitfeeds.com)

**GTFS-Analyse für Belebtheit:**
- `stop_times.txt` – Abfahrten pro Haltestelle und Tag
- `calendar.txt` – Wochentage, an denen Verkehre stattfinden
- `routes.txt` – Linien und deren Typ (Bus, Tram, U-Bahn, S-Bahn)
- Aussteige-Dichte als Proxy für Belebtheit: Haltestellen mit vielen Abfahrten
  zum Zeitfenster → wahrscheinlich belebter

## Event-/Markt-Daten

- **Berlin:** 
  - Wochenmärkte: `https://www.berlin.de/sen/verbraucherschutz/veranstaltungen/maerkte/`
  - Events: `https://www.berlin.de/events/`, `https://www.visitberlin.de`
  - Museen: `https://www.museumsportal-berlin.de`
- **Allgemein:** Event-Kalender der Stadt, Tourismus-Website, Webseiten von
  Veranstaltungsorten

**Vorgehen:**
- Liste der Events/Märkte zum Zeitfenstream erstellen
- Orte mit geplanten Events als „belebter" markieren
- Öffnungszeiten von Museen, Theatern etc. prüfen

## Google Popular Times

- **Problem:** Google blockiert Scraping; keine offizielle API für Popular Times
- **Alternative:** SerpAPI (kostenpflichtig) oder manuelle Abfrage
- **Nur als Ergänzung** – nicht als Hauptquelle nutzen
- Popular Times zeigt Besucherzahlen pro Stunde/Wochentag für einzelne POIs

## Wikidata (SPARQL)

- Endpoint: `https://query.wikidata.org/sparql`, `format=json`,
  Accept-Header `application/sparql-results+json`.
- **Klassen-QIDs nie raten:** vorher verifizieren mit
  `SELECT ?x WHERE { ?x wdt:P31 wd:QID } LIMIT 3` – keine Instanzen = keine
  Klasse.
- **Abfrage in zwei Schritten:** erst den Ort auflösen (per QID
  `?item wdt:P131* wd:Q…` oder Label-Suche mit Länder-Constraint `wdt:P17`,
  Orts-QID nie raten), dann die Klassen mit `VALUES ?klasse { … }` abfragen.
  Ohne QID-Ortsangabe kommen Fremdtreffer aus anderen Städten ins Ergebnis.
- **Rauschfilter vor dem Merge:** Stadt-Referenz hat Vorrang (Berlin:
  `reference/berlin.md`). Ohne Referenz mindestens: Item-Name ==
  Regionsname verwerfen; Beschreibung enthält `voormalig|former|opgeheven`;
  unaufgelöste Labels (nur `Q<nummer>`) verwerfen.
- Koordinaten kommen als WKT **`Point(lon lat)`** – Länge vor Breite.
- Ergebnisse pro QID gruppieren: ein Item kann mehrere Klassen haben →
  sonst Duplikate.

## Offizielles Register / Open Data

- Zuerst nach Open-Data-Portal oder Stadtregister suchen
  (CKAN, WFS, CSV, GeoJSON, API).
- Beispiele: Berlin `daten.berlin.de`, Wien `data.gv.at`, London `data.gov.uk`
- Vorhandenes Register hat Vorrang vor OSM/Wikidata als Namens- und
  Adressquelle.
