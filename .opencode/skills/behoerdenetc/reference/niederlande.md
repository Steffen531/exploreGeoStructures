# Referenz: Behörden finden in den Niederlanden (NL)

Learnings aus dem Lauf für **Leiden** (07.10.2026, 39 Treffer). Diese Datei bei
jeder NL-Anfrage zuerst lesen – sie spart die gesamte Phasen-1-/-2-Probiererei.

---

## 1. Datenquellen-Priorität für NL

**1. Offizielles Register (Hauptquelle, schlägt OSM):**
`Register van Overheidsorganisaties` – offizielles Register aller niederländischen
Behörden mit Name, Typ, Bezoek-/Post-/Vestigungsadresse, Telefon, E-Mail, Web.

- Übersicht (CKAN-API von data.overheid.nl):
  - `https://data.overheid.nl/data/api/3/action/package_show?id=overheidsorganisaties-xml`
  - Suche: `https://data.overheid.nl/data/api/3/action/package_search?q=<begriff>`
- **XML-Export nutzen (nicht die JSON-API):**
  `https://organisaties.overheid.nl/archive/exportOO.xml` (~38 MB, täglich neu)
  - `api-organisaties.overheid.nl` liefert 404 für übliche Pfade, Swagger-Spec
    nicht auffindbar, Swagger-UI leer → **API meiden**.
  - Mit `xml.etree.ElementTree.iterparse` streamen (nicht `with`-Kontext,
    iterparse unterstützt das nicht), nach `woonplaats == Stadt` filtern,
    Datei nach `cache/exportOO.xml` legen (`max_age_days=7`).
- **Parsing-Falle:** Nur **Direktkinder** von `<organisatie>` auswerten
  (`naam`, `types`, `adressen`, `contact`). Adressen von Kontaktpersonen liegen
  unter `functie/medewerker` – sonst wandern fremde Behörden ins Ergebnis.
- Adress-Ranking: `Bezoekadres`/`Vestigingsadres` vor `Postadres`
  (Postkästen wie `2300 PC LEIDEN` liefern schlechte Geocoding-Treffer).

**2. OpenStreetMap (Overpass)** – Haupttag in NL ist `office=government`:
`amenity=police|townhall|embassy|courthouse|public_building|fire_station`,
`office=government|diplomatic|tax`, `building=government` (fast leer).
`amenity=fire_station` (Brandweer) in den Skill-Standardfilter aufnehmen –
fehlte sonst, gehört aber erkennbar dazu.
Overpass ist lastabhängig → 3 Runden mit Backoff, 4. Server
`https://overpass.private.coffee/api/interpreter`, Antwort per Query-Hash
in `cache/` cachen (sonst blockiert ein Lauf bei 504/Timeout aller Server).

**3. Wikidata (SPARQL)** – nur als Ergänzung, streng filtern (siehe §3).

**4. Nominatim** – nur für Stadtgrenze und fehlende Koordinaten,
1 Anfrage/s + Geocode-Cache (`cache/geocode.json`).

---

## 2. Region & Grenzen

- **Bounding Box allein reicht nie.** Das Rechteck um Leiden enthält
  Oegstgeest, Voorschoten, Zoeterwoude und Teile von Leiderdorp → fremde
  Gemeentehäuser, Polizeipunkte, Brandweerkaserne Voorschoten.
  **Pflicht-Schritt:** Nominatim `polygon_geojson=1` + shapely `contains()`
  auf alle Koordinaten (OSM **und** Wikidata), Ergebnisse loggen.
- Referenz Leiden: OSM-Relation **295092**, bbox S/W/N/E =
  52.11895 / 4.43887 / 52.18463 / 4.52407.
- **Wikidata-QID nie raten:** Leiden = **Q43631** (Q44083 ist die TLD `.pw`).
  Auflösung per Label-Suche mit Länder-Constraint:
  `?item rdfs:label "Leiden"@nl . ?item wdt:P17 wd:Q5 .`

---

## 3. Wikidata-Fallen (vor jeder SPARQL-Abfrage prüfen)

- **Klassen-QID verifizieren:** `SELECT ?x WHERE { ?x wdt:P31 wd:QID } LIMIT 3`
  → keine Instanzen = keine Klasse. Die Label-Suche liefert sonst Instanzen mit:
  - Q17339531 „politiebureau" = ein Gebäude in Leiden selbst (kein Klassen-QID)
  - Q19362339 „court building", Q5626501 „police station" = keine Instanzen
  - **Funktionierend:** Q861951 (police station), Q3917681 (embassy),
    Q372690 (consulate general), Q16831714 (government building),
    Q1137809 (courthouse), Q327333 (government agency),
    Q2659904 (government organization)
- **Rauschfilter (Pflicht):**
  - **Polder/Wasserstände:** NL-Polder sind Instanzen von „Nederlands
    waterschap" und hängen unter `government organization` → 6 Polder kamen als
    „Behörden" rein. Filter: Name endet auf `polder`.
  - **Ort selbst:** Item-Name == Regionsname („Leiden") verwerfen.
  - **Ehemaliges:** Beschreibung enthält `voormalig|former|opgeheven`.
  - **Denkmäler:** Beschreibung enthält `rijksmonument` – Ausnahme bei
    townhall/police/courthouse/embassy (sonst fällt das aktive Stadhuis raus).
  - Unaufgelöste Labels (nur `Q<nummer>`) verwerfen.
- Abfrage-Reihenfolge: erst Ort (`wdt:P131*` / `wdt:P276*`), dann
  `wdt:P31/wdt:P279*` mit `VALUES ?klass {...}`; Ergebnisse **pro QID gruppieren**
  (ein Item kann mehrere Klassen haben → sonst Duplikate).
- Koordinaten kommen als WKT **`Point(lon lat)`** – Reihenfolge beachten.
- NL-spezifisch: `P6375` (Adressangabe) ist oft befüllt, `P1329` (Telefon) eher selten.

---

## 4. Kategorien (Skill-Kategorien für NL konkretisiert)

| Kategorie | NL-Quellen |
|---|---|
| Behörde & Regierungsgebäude | `office=government`, `amenity=townhall`, Registertypen Gemeente/ZBO/Waterschap/Regionaal samenwerkingsorgaan/Rechtspraak, `amenity=fire_station` |
| Polizeidienststelle | `amenity=police`, Wikidata-Klasse Q861951 |
| Botschaft & Konsulat | **in NL fast immer 0 außerhalb Den Haags** – sofort kommunizieren statt leer zu erklären |
| Öffentliche Einrichtung (eigene Kategorie!) | Registertypen `Overheidsstichting of -vereniging` und `Organisatie met overheidsbemoeienis` – Museen/Stiftungen **nicht** als „Behörde" labeln |
| Internationale Einrichtung | in mittelgroßen NL-Städten i. d. R. 0 |

Bewusst **außerhalb** des Scopes (auch wenn OSM sie stark hat): Universitäten,
Kliniken, Bibliotheken, Schulen – das NL-Register führt sie ebenfalls nicht.

---

## 5. Zusammenführen / Deduplizierung

- **Gleiche Adresse ≠ gleiche Organisation.** In Leiden saßen getrennte Träger
  auf identischen Koordinaten: GGD Hollands Midden & Hecht (Parmentierweg 49),
  Hoogheemraadschap Rijnland & Stichting Beheer van het Gemeeneland
  (Archimedesweg 1), UWV & Omgevingsdienst West-Holland (Vondellaan 55).
  → **Nur bei Namensähnlichkeit mergen, nie allein über Distanz.**
- Bewährte Schwellen (Name normalisiert, Stopwörter `gemeente/stichting/van/
  het/der/...`, Tokens sortiert):
  - sim ≥ 0.88 und ≤ 250 m, **oder**
  - ≤ 150 m und sim ≥ 0.45 (fängt „Gemeente Leiden" ↔ „Stadskantoor Leiden"
    0.48 und „Stadhuis Leiden" ↔ „Stadhuis met woningen" 0.556)
  - **Nicht mergen** (zu riskant): „Regio Holland Rijnland" ↔
    „Serviceorganisatie Zorg Holland Rijnland" (0.516) – unterschiedliche Träger.
- **Offizieller Registernamen als kanonischer Name**, OSM-/Wikidata-Namen als
  `alias` mitführen (auch in KML/GPX-Beschreibung ausgeben).
- Kategorie beim Merge: konkreter (Polizei/Diplomatie) schlägt allgemein;
  offizielle Registertypen schlagen Wikidata-Klassifikation.
- Koordinaten-Priorität: OSM > Wikidata > Nominatim-Geocoding > keine.

---

## 6. Ausgabe / Visualisierung

- Export wie im Skill: `ergebnis.geojson` (inkl. `geometry: null` für
  Koordinatenlose), `ergebnis.kml` (Ordner je Kategorie, Style-Block `#pin`),
  `ergebnis.gpx`, `zusammenfassung.json` (inkl. ausgeschlossene Punkte außerhalb
  der Stadtgrenze und Deduplizierungs-Statistik).
- Visualisierung für den Nutzer: umap.openstreetmap.de → ☰ → „Daten importieren"
  → GeoJSON wählen (oder Drag & Drop) → „als neue Ebene" → Karte teilen.

---

## 7. Reproduzierbarkeit

```bash
# Lauf für eine andere NL-Stadt
.venv/bin/python results/<stadt>/behoerden_suche.py \
  --place "Utrecht, Niederlande" --qid Q26659 \
  --register-city Utrecht --output results/utrecht
```

Caches (behalten und wiederverwenden): `cache/exportOO.xml`,
Nominatim-Grenzdatei, Overpass-Query-Hash, `cache/geocode.json`.
Vor dem QID-Wert immer die Schritte aus §2/§3 neu prüfen.
