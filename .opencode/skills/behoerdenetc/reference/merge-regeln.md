# Merge-, Namens- und Kategorieregeln

Kontext für Schritt 6 des `SKILL.md`-Prozesses. Schwellen und Kategorien aus
einer Landes-Referenz haben Vorrang.

## Deduplizierung

- **Gleiche Adresse ≠ gleiche Organisation** – getrennte Träger sitzen oft auf
  identischen Koordinaten. → **Nur bei Namensähnlichkeit und Distanz mergen,
  nie allein über Distanz.** NL-Beispiele: `reference/niederlande.md` §5.
- Erprobte Schwellen (Name normalisiert, Stopwörter wie
  `gemeente/stichting/van/het/der/...`, Tokens sortiert), in NL verifiziert –
  für neue Länder erst bestätigen:
  - sim ≥ 0.88 und ≤ 250 m, **oder**
  - ≤ 150 m und sim ≥ 0.45 (fängt „Gemeente Leiden" ↔ „Stadskantoor Leiden"
    und „Stadhuis Leiden" ↔ „Stadhuis met woningen")

## Name

- Offizieller Register-/Behördenname ist kanonisch.
- OSM-/Wikidata-Namen als `alias` mitführen und in der KML-/GPX-Beschreibung
  ausgeben.

## Kategorie beim Merge

- Konkrete Kategorie (Polizei, Diplomatie) schlägt allgemeine.
- Offizielle Registertypen schlagen die Wikidata-Klassifikation.

## Koordinaten und Adressen

- Priorität: OSM > Wikidata > Nominatim-Geocoding > keine.
- Echte Besuchsadresse vor Postadresse (Postfächer liefern schlechte
  Geocoding-Treffer).
- Koordinatenlose Treffer behalten (`geometry: null`) und in
  `zusammenfassung.json` zählen.

## Kategorien

| Kategorie | Merkmale |
|---|---|
| Behörde & Regierungsgebäude | `office=government`, `amenity=townhall|courthouse`, Register-Typen „Gemeente/Behörde" |
| Polizeidienststelle | `amenity=police`, Wikidata-Klasse Q861951 |
| Botschaft & Konsulat | `amenity=embassy`, `office=diplomatic`, Klassen Q3917681/Q372690 – in vielen Städten 0 → sofort sagen statt leer zu erklären |
| Öffentliche Einrichtung | Stiftungen/Verbände mit Staatsbezug – **nicht** als „Behörde" labeln |
| Internationale Einrichtung | internationale Organe; in mittelgroßen Städten i. d. R. 0 |

**Außerhalb des Scopes** (auch wenn OSM sie stark hat): Universitäten,
Kliniken, Bibliotheken, Schulen – offizielle Register führen sie ebenfalls
nicht.
