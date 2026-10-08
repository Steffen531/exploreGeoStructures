# Merge-, Namens- und Kategorieregeln

Kontext für Schritt 6 des `SKILL.md`-Prozesses. Schwellen und Kategorien aus
einer Stadt-Referenz haben Vorrang.

## Deduplizierung

- **Gleiche Adresse ≠ gleicher Ort** – verschiedene Geschäfte oder Einrichtungen
  sitzen oft auf identischen Koordinaten (z. B. ein Einkaufszentrum mit mehreren
  Shops). → **Nur bei Namensähnlichkeit und Distanz mergen, nie allein über
  Distanz.**
- Erprobte Schwellen (Name normalisiert, Stopwörter wie
  `der/die/das/und/&`, Tokens sortiert), in Berlin verifiziert – für neue Städte
  erst bestätigen:
  - sim ≥ 0.88 und ≤ 250 m, **oder**
  - ≤ 150 m und sim ≥ 0.45

## Name

- Offizieller Name aus OSM oder Register ist kanonisch.
- Wikidata-Namen als `alias` mitführen und in der KML-/GPX-Beschreibung
  ausgeben.

## Kategorie beim Merge

- Konkrete Kategorie (Geschäft, Gastronomie, Kultur) schlägt allgemeine.
- Offizielle Registertypen schlagen die Wikidata-Klassifikation.

## Koordinaten und Adressen

- Priorität: OSM > Wikidata > Nominatim-Geocoding > keine.
- Echte Besuchsadresse vor Postadresse.
- Koordinatenlose Treffer behalten (`geometry: null`) und in
  `zusammenfassung.json` zählen.

## Kategorien

| Kategorie | Merkmale |
|---|---|
| Geschäft & Einzelhandel | `shop=*`, vor allem Supermärkte, Boutiquen, Einkaufszentren |
| Gastronomie | `amenity=cafe|restaurant|bar|pub|fast_food|ice_cream|food_court` |
| Kultur & Freizeit | `amenity=theatre|cinema|museum|library|arts_culture`, `leisure=park|stadium|sports_centre` |
| ÖPNV-Knotenpunkt | `public_transport=platform|stop_position`, `railway=station|tram_stop|subway_entrance` |
| Öffentliche Einrichtung | `amenity=bank|atm|pharmacy|post_office|police|fire_station|hospital|clinic` |
| Touristisch | `tourism=hotel|hostel|guest_house|information|viewpoint|attraction|artwork` |
| Büro & Geschäftsviertel | `office=*`, vor allem in Innenstadtlagen |

**Außerhalb des Scopes:** Wohngebiete, reine Straßen ohne POIs – diese sind
nicht „belebte Orte" im Sinne dieses Skills.
