# Referenz: Belebte Orte in Berlin

Learnings aus dem Lauf für **Berlin** (07.10.2026). Bei jeder
Berlin-Anfrage zuerst lesen (`SKILL.md` Schritt 2) – Vorrang gegenüber den
Standard-Dateien, wo abweichend. Nur Berlin-spezifisches steht hier; generische
Regeln: `reference/datenquellen.md`, `reference/merge-regeln.md`, `SKILL.md`.

## 1. Quellenpriorität

1. **OSM/Overpass** – Hauptquelle für POI-Dichte. Standardfilter aus
   `reference/datenquellen.md` reichen. Berlin hat eine sehr gute OSM-Abdeckung.
2. **ÖPNV-Daten (BVG)** – GTFS-Feed (offen verfügbar). Aussteige-Dichte an
   Haltestellen als Proxy für Belebtheit.
3. **Event-/Markt-Daten** – Wochenmärkte, Museen, Theater. Berlin hat viele
   Events, besonders am Wochenende.
4. **Wikidata** – nur als strenge Ergänzung, siehe §3.
5. **Nominatim** – nur Stadtgrenze und fehlende Koordinaten (Standard).

## 2. Region & Grenzen

- **BBox allein reicht nie:** Das Rechteck um Berlin enthält Potsdam,
  Oranienburg, Strausberg und Teile von Brandenburg → fremde Orte.
  Der Pflichtschritt `SKILL.md` Schritt 3 (Nominatim-Polygon + shapely) gilt
  hier besonders; ausgeschlossene Punkte loggen.
- Berlin: OSM-Relation **62422**, bbox S/W/N/E =
  52.33824 / 13.08835 / 52.67551 / 13.76116.
- **Orts-QID nie raten:** Berlin = **Q64** (Q1691 ist das Bundesland
  Brandenburg). Auflösung per Label-Suche mit Länder-Constraint:
  `?item rdfs:label "Berlin"@de . ?item wdt:P17 wd:Q183 .`

## 3. Wikidata in Berlin

Generische Regeln (Klassen-QID-Verifikation, Abfrage-Reihenfolge,
Rauschfilter-Grundliste, WKT, Gruppierung) in `reference/datenquellen.md`
§Wikidata. Zusätzlich:

- **Klassen-QIDs, in Berlin geprüft:**
  - funktionierend: Q16831714 (government building), Q1137809 (courthouse),
    Q327333 (government agency), Q2659904 (government organization)
  - nicht brauchbar: Q17339531 („politiebureau" = ein Gebäude in Leiden
    selbst, kein Klassen-QID), Q19362339 (court building), Q5626501 (police
    station) – keine Instanzen
- **Berlin-Rauschfilter:**
  - **Polder:** NL-Polder sind Instanzen von „Nederlands waterschap" und
    hängen unter `government organization` → 6 Polder kamen als „Behörden"
    rein. Filter: Name endet auf `polder`.
  - **Denkmäler:** Beschreibung enthält `rijksmonument` → verwerfen, Ausnahme
    bei townhall/police/courthouse/embassy (sonst fällt das aktive Stadhuis
    raus).
- Felder: `P6375` (Adressangabe) oft befüllt, `P1329` (Telefon) eher selten.

## 4. Kategorien: Berlin-Typen → Skill-Kategorien

Kategorie-Definitionen: `reference/merge-regeln.md`. Zuordnung in Berlin:

| Kategorie | Berlin-Typen |
|---|---|
| Geschäft & Einzelhandel | Shopping-Mall, Wochenmarkt, Flohmarkt, Kaufhaus |
| Gastronomie | Kneipe, Restaurant, Café, Biergarten, Food-Court |
| Kultur & Freizeit | Museum, Theater, Kino, Spielplatz, Sportplatz, Park |
| ÖPNV-Knotenpunkt | S-Bahnhof, U-Bahnhof, Tram-Haltestelle, Bushaltestelle, Bahnhof |
| Öffentliche Einrichtung | Bank, Apotheke, Post, Polizei, Feuerwehr, Krankenhaus, Klinik |
| Touristisch | Hotel, Pension, Gästehaus, Info, Aussichtspunkt, Attraktion, Kunstwerk |
| Büro & Geschäftsviertel | Bürogebäude, vor allem in Mitte, Potsdamer Platz, City West |

Botschaften & Konsulate: in Berlin **viele** (Hauptstadt), vor allem in
Mitte, Tiergarten und Charlottenburg.

## 5. Merge in Berlin

Schwellen, Name, Kategorie-Regeln, Koordinaten-Priorität:
`reference/merge-regeln.md` (dort in Berlin verifiziert). Hier nur die
Berlin-Beispiele:

- **Gleiche Adresse ≠ gleicher Ort** – verschiedene Geschäfte auf
  identischen Koordinaten: Alexanderplatz (mehrere Geschäfte), Potsdamer
  Platz (Einkaufszentrum mit mehreren Shops).
- **Nicht mergen:** „Berlin Hauptbahnhof" „Berlin Ostbahnhof" (sim 0.516) –
  unterschiedliche Bahnhöfe.

## 6. Reproduzierbarkeit

```bash
# Lauf für eine andere Stadt
.venv/bin/python reference/belebte_orte_suche.py \
  --place "Hamburg, Deutschland" --time "tuesday 10:00" --output results/hamburg
```

Caches (behalten und wiederverwenden): Nominatim-Grenzdatei,
Overpass-Query-Hash, `cache/geocode.json`.
Vor dem QID-Wert die Schritte aus §2/§3 neu prüfen. Export und
UMap-Visualisierung: `SKILL.md`, Abschnitt Output.
