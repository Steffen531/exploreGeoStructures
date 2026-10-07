# Referenz: Behörden finden in den Niederlanden (NL)

Learnings aus dem Lauf für **Leiden** (07.10.2026, 39 Treffer). Bei jeder
NL-Anfrage zuerst lesen (`SKILL.md` Schritt 2) – Vorrang gegenüber den
Standard-Dateien, wo abweichend. Nur NL-spezifisches steht hier; generische
Regeln: `reference/datenquellen.md`, `reference/merge-regeln.md`, `SKILL.md`.

## 1. Quellenpriorität

1. **Register van Overheidsorganisaties** – Hauptquelle, schlägt OSM (Name,
   Typ, Adressen, Telefon, E-Mail, Web aller NL-Behörden):
   - Übersicht (CKAN): `https://data.overheid.nl/data/api/3/action/package_show?id=overheidsorganisaties-xml`,
     Suche: `…/package_search?q=<begriff>`
   - **XML-Export nutzen:** `https://organisaties.overheid.nl/archive/exportOO.xml`
     (~38 MB, täglich neu). `api-organisaties.overheid.nl` liefert 404 für
     übliche Pfade, Swagger-Spec nicht auffindbar → **API meiden**.
   - Streamen mit `xml.etree.ElementTree.iterparse` (ohne `with`-Kontext –
     iterparse unterstützt das nicht), nach `woonplaats == Stadt` filtern,
     nach `cache/exportOO.xml` legen (`max_age_days=7`).
   - **Parsing-Falle:** Nur Direktkinder von `<organisatie>` auswerten
     (`naam`, `types`, `adressen`, `contact`) – Adressen von Kontaktpersonen
     liegen unter `functie/medewerker`, sonst wandern fremde Behörden ins
     Ergebnis.
   - Adress-Felder im XML: `Bezoekadres`/`Vestigingsadres` = Besuchsadresse,
     `Postadres` = Postadresse (Regel: `reference/merge-regeln.md`;
     Postkästen wie `2300 PC LEIDEN` liefern schlechte Geocoding-Treffer).
2. **OSM/Overpass:** Standardfilter aus `reference/datenquellen.md` reichen;
   Haupttag in NL ist `office=government`. `amenity=fire_station` (Brandweer)
   gehört erkennbar dazu und ist im Standardfilter enthalten.
3. **Wikidata:** nur als strenge Ergänzung, siehe §3.
4. **Nominatim:** nur Stadtgrenze und fehlende Koordinaten (Standard).

## 2. Region & Grenzen

- **BBox allein reicht nie:** Das Rechteck um Leiden enthält Oegstgeest,
  Voorschoten, Zoeterwoude und Teile von Leiderdorp → fremde Gemeentehäuser,
  Polizeipunkte, Brandweerkaserne Voorschoten. Der Pflichtschritt
  `SKILL.md` Schritt 3 (Nominatim-Polygon + shapely) gilt hier besonders;
  ausgeschlossene Punkte loggen.
- Leiden: OSM-Relation **295092**, bbox S/W/N/E =
  52.11895 / 4.43887 / 52.18463 / 4.52407.
- **Orts-QID nie raten:** Leiden = **Q43631** (Q44083 ist die TLD `.pw`).
  Auflösung per Label-Suche mit Länder-Constraint:
  `?item rdfs:label "Leiden"@nl . ?item wdt:P17 wd:Q5 .`

## 3. Wikidata in NL

Generische Regeln (Klassen-QID-Verifikation, Abfrage-Reihenfolge,
Rauschfilter-Grundliste, WKT, Gruppierung) in `reference/datenquellen.md`
§Wikidata. Zusätzlich:

- **Klassen-QIDs, in Leiden geprüft:**
  - funktionierend: Q861951 (police station), Q3917681 (embassy), Q372690
    (consulate general), Q16831714 (government building), Q1137809
    (courthouse), Q327333 (government agency), Q2659904 (government
    organization)
  - nicht brauchbar: Q17339531 („politiebureau" = ein Gebäude in Leiden
    selbst, kein Klassen-QID), Q19362339 (court building), Q5626501 (police
    station) – keine Instanzen
- **NL-Rauschfilter:**
  - **Polder:** NL-Polder sind Instanzen von „Nederlands waterschap" und
    hängen unter `government organization` → 6 Polder kamen als „Behörden"
    rein. Filter: Name endet auf `polder`.
  - **Denkmäler:** Beschreibung enthält `rijksmonument` → verwerfen, Ausnahme
    bei townhall/police/courthouse/embassy (sonst fällt das aktive Stadhuis
    raus).
- Felder: `P6375` (Adressangabe) oft befüllt, `P1329` (Telefon) eher selten.

## 4. Kategorien: NL-Registertypen → Skill-Kategorien

Kategorie-Definitionen: `reference/merge-regeln.md`. Zuordnung in NL:

| Kategorie | NL-Registertypen |
|---|---|
| Behörde & Regierungsgebäude | Gemeente, ZBO, Waterschap, Regionaal samenwerkingsorgaan, Rechtspraak |
| Öffentliche Einrichtung | `Overheidsstichting of -vereniging`, `Organisatie met overheidsbemoeienis` – **nicht** als „Behörde" labeln |

Botschaften & Konsulate: in NL **nur in Den Haag** (nicht Amsterdam), in allen
anderen Städten 0 – das auch so kommunizieren.

## 5. Merge in NL

Schwellen, Name, Kategorie-Regeln, Koordinaten-Priorität:
`reference/merge-regeln.md` (dort in NL verifiziert). Hier nur die
NL-Beispiele:

- **Gleiche Adresse ≠ gleiche Organisation** – getrennte Träger auf
  identischen Koordinaten: GGD Hollands Midden & Hecht (Parmentierweg 49),
  Hoogheemraadschap Rijnland & Stichting Beheer van het Gemeeneland
  (Archimedesweg 1), UWV & Omgevingsdienst West-Holland (Vondellaan 55).
- **Nicht mergen:** „Regio Holland Rijnland" ↔ „Serviceorganisatie Zorg
  Holland Rijnland" (sim 0.516) – unterschiedliche Träger.

## 6. Reproduzierbarkeit

```bash
# Lauf für eine andere NL-Stadt
.venv/bin/python reference/behoerden_suche.py \
  --place "Utrecht, Niederlande" --qid Q26659 \
  --register-city Utrecht --output results/utrecht
```

Caches (behalten und wiederverwenden): `cache/exportOO.xml`,
Nominatim-Grenzdatei, Overpass-Query-Hash, `cache/geocode.json`.
Vor dem QID-Wert die Schritte aus §2/§3 neu prüfen. Export und
UMap-Visualisierung: `SKILL.md`, Abschnitt Output.
