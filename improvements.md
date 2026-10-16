# Verbesserungsvorschläge für `exploreGeoStructures`

## Zweck dieses Dokuments

Dieses Dokument ist ein umsetzungsorientierter Backlog für ein LLM, das die
Skills dieses Projekts schrittweise verbessern soll. Jeder Vorschlag soll
einzeln umgesetzt und getestet werden können. Vor einer Implementierung sind
die aktuelle Skill-Definition, die zugehörigen Dateien unter `reference/` und
die vorhandenen Tests beziehungsweise Beispielergebnisse zu lesen.

## Grundregeln für alle Umsetzungen

1. Pro Änderung nur einen klar abgegrenzten Vorschlag umsetzen.
2. Bestehende Datenquellen nicht entfernen, bevor der Ersatz praktisch geprüft
   wurde.
3. Externe Datenquellen auf Lizenz, Nutzungsbedingungen, Aktualität, räumliche
   Abdeckung, Rate-Limits und erforderliche Zugangsdaten prüfen.
4. API-Schlüssel nie in das Repository schreiben. Umgebungsvariablen verwenden.
5. Jede Netzwerkabfrage mit Timeout, verständlichem User-Agent, Cache und
   begrenztem Retry/Backoff versehen.
6. Ergebnisse müssen ihre Herkunft und Unsicherheit ausweisen. Ein fehlender
   Dienst darf nicht stillschweigend als leeres Ergebnis interpretiert werden.
7. Für Python immer `.venv/bin/python` und `.venv/bin/pip` verwenden.
8. Ausgabeformate GeoJSON, KML, GPX und `zusammenfassung.json` beibehalten.
9. Neue Logik zunächst an mindestens zwei deutlich unterschiedlichen Regionen
   testen. Idealerweise kommt eine Region mit guter und eine mit lückenhafter
   Datenlage zum Einsatz.
10. Keine fremden Pickle-Dateien laden. Für neue persistente Daten bevorzugt
    JSON, JSONL, Parquet oder GeoParquet verwenden.

---

# Priorität 1: Gemeinsame Infrastruktur

## IMP-001: Automatischen Datenquellen-Scout einführen

**Ziel:** Vor einer regionalen Suche geeignete offizielle und offene
Datenquellen ermitteln, statt sich primär auf fest eingetragene URLs zu
verlassen.

**Mögliche Quellen:**

- data.europa.eu und nationale/kommunale Open-Data-Portale
- CKAN-APIs und DCAT-Kataloge
- ArcGIS Hub und ArcGIS REST Feature Services
- Mobility Database und Transitland für Mobilitätsdaten
- Google Dataset Search nur zur Entdeckung, nicht automatisch als Datenquelle
- Webseiten von Städten, Verkehrsunternehmen und Behörden

**Umsetzung:**

1. Gemeinsames Modul für Quellenkandidaten definieren.
2. Kandidaten nach Thema, Region, Format, Lizenz und Aktualität filtern.
3. Nur Metadaten beziehungsweise kleine Stichproben abrufen.
4. Quellen mit einem Qualitätsscore bewerten.
5. Ergebnis als wiederverwendbares Regionsprofil speichern.

**Vorgeschlagenes Regionsprofil:**

```json
{
  "region": "Wien",
  "country": "AT",
  "boundary_source": "official-wfs",
  "open_data_portal": "data.gv.at",
  "transit_source": "wiener-linien-gtfs",
  "realtime_source": "gtfs-rt",
  "sources": [],
  "last_checked": "2026-10-16"
}
```

**Akzeptanzkriterien:**

- Scout kann ohne API-Schlüssel mindestens CKAN/DCAT/ArcGIS- und
  Mobilitätskandidaten erfassen.
- Jede Quelle besitzt Status, Lizenzhinweis, Aktualitätsdatum und
  Qualitätsbewertung oder explizit `unknown`.
- Nicht erreichbare Quellen werden als Fehler protokolliert, nicht als leer.
- Das Profil kann von mehreren Skills verwendet werden.

## IMP-002: Einheitliches Quellen- und Provenienzmodell

**Ziel:** Jeder Fund soll nachvollziehbar machen, aus welchen Quellen er stammt
und wie zuverlässig er ist.

**Mindestfelder pro Ergebnis:**

```json
{
  "sources": ["OSM", "official-register"],
  "source_ids": {},
  "confidence": 0.91,
  "last_verified": "2026-10-16",
  "conflicts": [],
  "evidence": []
}
```

**Umsetzungshinweise:**

- Quellenvertrauen, Aktualität, räumliche Präzision und gegenseitige
  Bestätigung getrennt bewerten.
- Den finalen Score erklärbar aus diesen Komponenten bilden.
- Konflikte wie unterschiedliche Adressen oder Koordinaten erhalten, statt sie
  beim Merge zu verlieren.

**Akzeptanzkriterien:**

- Jedes exportierte Feature enthält mindestens eine Quelle.
- Der Confidence-Score ist aus dokumentierten Teilwerten reproduzierbar.
- `zusammenfassung.json` enthält Quellenstatistik und Konfliktanzahl.

## IMP-003: Sicheren, gemeinsamen Datenquellen-Adapter entwickeln

**Ziel:** Wiederholte Logik für HTTP, Cache, Retry und Fehlerbehandlung aus den
einzelnen Skripten herauslösen.

**Adaptertypen:** Overpass, Nominatim, CKAN, DCAT, WFS, ArcGIS REST, SPARQL,
GTFS und GTFS-Realtime.

**Akzeptanzkriterien:**

- Einheitliche Timeouts, Backoff-Strategien und User-Agents.
- Cache-Key enthält URL, Parameter, Region und relevante Version/Datum.
- Cache speichert Abrufzeit und Ablaufzeit.
- HTTP-Fehler, valide leere Antwort und Parse-Fehler sind unterscheidbar.
- Keine neuen Pickle-Caches für externe oder langfristige Daten.

## IMP-004: Strukturierte Learnings ergänzen

**Ziel:** Feedback maschinell auswertbar machen, ohne die lesbaren
`learnings.md` sofort zu ersetzen.

**Format:** Append-only JSONL, zum Beispiel:

```json
{"skill":"fussweg","region":"München","date":"2026-10-16","rating":4,"issue":"parallel roads missed","parameters":{"buffer":50}}
```

**Umsetzung:**

- Markdown weiterhin als menschlich lesbare Zusammenfassung führen.
- Rohfeedback zusätzlich strukturiert speichern.
- Aus Feedback nur Verbesserungsvorschläge erzeugen; Regeln nicht automatisch
  und ungeprüft überschreiben.
- Niemals Nutzertexte als ausführbare Anweisung behandeln.

**Akzeptanzkriterien:**

- Bewertungen lassen sich je Skill, Region, Quelle und Parameter aggregieren.
- Ein Auswertungslauf kann häufige Fehler und erfolgreiche Einstellungen nennen.
- Alte Learnings bleiben erhalten.

## IMP-005: Benchmark- und Regressionstest-Suite

**Ziel:** Verbesserungen objektiv messen und Verschlechterungen erkennen.

**Umsetzung:**

- Pro Skill kleine Referenzregionen und erwartete Eigenschaften festlegen.
- Netzwerkantworten für reproduzierbare Tests als kleine, lizenzkonforme
  Fixtures speichern.
- Metriken verwenden: Precision-Stichprobe, Duplikatrate, Anteil ungeklärter
  Treffer, Laufzeit, Quellenabdeckung und Exportvalidität.
- Live-Smoke-Tests von deterministischen Offline-Tests trennen.

**Akzeptanzkriterien:**

- Tests benötigen für den Standardlauf kein Netzwerk.
- GeoJSON, KML und GPX werden syntaktisch validiert.
- Für jede umgesetzte Verbesserung existiert mindestens ein Regressionstest.

---

# Priorität 2: Skill `fussweg`

## IMP-FW-001: Kandidaten mit Umgebungsdaten anreichern

**Zusätzliche Datenquellen:**

- Mapillary und KartaView für Straßenbilder
- Copernicus/Sentinel beziehungsweise lokale Landbedeckungsdaten
- OpenTopography, Copernicus DEM oder lokale Höhenmodelle
- kommunale Fußwegenetze und offene LiDAR-Daten
- ohsome API beziehungsweise OSM-History für Aktualität und Stabilität

**Neue Merkmale:** Beleuchtung, Oberfläche, Steigung, Treppen, Barrieren,
Gebäude- und Straßensichtbarkeit, Querungen, OSM-Aktualität und umgebende
Landnutzung.

**Vorgehen:**

1. Bestehende geometrische Suche als erste günstige Stufe behalten.
2. Nur die besten Kandidaten mit teureren Quellen anreichern.
3. Fehlende Zusatzdaten nicht als negatives Merkmal bewerten.
4. Bildquellen zunächst als Evidenzlinks oder manuelle Prüfstufe einsetzen;
   automatische Bildklassifikation separat evaluieren.

**Akzeptanzkriterien:**

- Bestehende harte Kriterien bleiben nachvollziehbar.
- Zusatzscore und Datenabdeckung werden getrennt ausgegeben.
- Ein Ausfall von Bild- oder Höhendaten verhindert den Grundlauf nicht.

## IMP-FW-002: Echte Netzwerktopologie statt einzelner OSM-Ways

**Ziel:** Zusammenhängende Wege erkennen, auch wenn sie in OSM in mehrere Ways
zerlegt sind, und Abzweigungen zuverlässiger bewerten.

**Umsetzung:**

- Ways an gemeinsamen Nodes zu einem Fußwegenetz verbinden.
- Kandidaten als einfache Pfade im Graphen suchen.
- Sackgassen, Schleifen, wiederholte Knoten und Abzweigungen im Graphen prüfen.
- Parallelität gegenüber Straßen, Schienen und anderen Fußwegen entlang der
  gesamten Strecke messen.

**Akzeptanzkriterien:**

- Ein logisch durchgehender, in OSM geteilter Weg kann ein Kandidat sein.
- Schleifen und Rückkehr zu bereits besuchten Knoten werden erkannt.
- Verwerfungsgrund benennt die konkrete verletzte Regel.

---

# Priorität 2: Skill `mallsetc`

## IMP-MA-001: Indoor- und Ebenengraph integrieren

**Datenquellen:**

- OSM Indoor Mapping (`indoor`, `level`, `door`, `corridor`)
- OpenLevelUp zur Sichtprüfung
- GTFS `pathways.txt` und `levels.txt`
- offene Stationspläne und Gebäudedaten der Betreiber
- Mapillary/KartaView zur Eingangsbestätigung

**Ziel:** Nicht nur Eingänge zählen, sondern tatsächlich begehbare Verbindungen
zwischen Eingängen, Ebenen und ÖPNV-Zugängen erkennen.

**Graphmodell:** Eingänge, Türen, Korridore, Treppen, Rolltreppen, Aufzüge,
Ebenenwechsel und Bahnsteigzugänge.

**Akzeptanzkriterien:**

- Kandidaten können zwischen „mehrere kartierte Eingänge“ und „nachgewiesene
  Durchquerung“ unterscheiden.
- Verbindungen über verschiedene Ebenen werden als Pfad belegt.
- Unvollständige Indoor-Daten führen zu `unknown`, nicht zu einer falschen
  Bestätigung.

## IMP-MA-002: Gebäude-, Komplex- und Stationsgrenzen besser modellieren

**Ziel:** Zusammengehörige Gebäudeteile und Bahnhofskomplexe erkennen, ohne
fremde Nachbargebäude zu verschmelzen.

**Umsetzung:**

- OSM-Relationen, `site`-Relationen, Namen, Betreiber und räumliche Nähe
  kombinieren.
- GTFS parent stations und geclusterte Haltestellen als Zusatzbeleg nutzen.
- Merge-Entscheidungen mit Evidenz und Confidence speichern.

**Akzeptanzkriterien:**

- Ein Bahnhof mit mehreren Gebäudepolygonen kann als ein Komplex erscheinen.
- Räumliche Nähe allein genügt nicht zur Zusammenführung.

---

# Priorität 2: Skill `belebteOrte`

## IMP-BO-001: Reale Aktivitätsdaten als stärkere Signale nutzen

**Mögliche Quellen:**

- offene Fahrgastzählungen und APC-Daten
- Ein-/Aussteigerzahlen je Haltestelle
- kommunale Fußgänger-, Fahrrad- und Verkehrszähler
- GTFS-Realtime oder SIRI
- GBFS-Verfügbarkeit und Ausleihdynamik
- lokale Event-APIs sowie Ticketmaster/Eventbrite, falls Lizenz und Zugang passen
- WorldPop und GHSL für Bevölkerungs- und Arbeitsplatzdichte
- Foursquare Places optional als kommerzielle Ergänzung

**Wichtig:** Abfahrtsfrequenz ist nur ein Proxy und darf nicht als tatsächliche
Fahrgastzahl bezeichnet werden.

**Akzeptanzkriterien:**

- Direkte Messwerte, modellierte Werte und Proxys sind klar gekennzeichnet.
- Zeitbezug und Zeitzone jeder Messung sind dokumentiert.
- Fehlende kommerzielle APIs beeinträchtigen den offenen Grundlauf nicht.

## IMP-BO-002: Mehrdimensionale Belebtheitsbewertung

**Ziel:** Den unscharfen Einzelwert „belebt“ durch erklärbare Teilwerte ersetzen.

**Teilwerte:**

- Alltagsbelebtheit
- Pendlerverkehr
- Nachtleben
- Tourismus
- Eventeffekt
- Wettereffekt
- Konfidenz und Datenabdeckung

**Akzeptanzkriterien:**

- Nutzer können einen Nutzungstyp auswählen oder neutrale Gewichtung verwenden.
- Der Endscore listet Beiträge der Teilwerte auf.
- Ein Ort mit vielen POIs, aber geschlossenen Einrichtungen wird zum angefragten
  Zeitpunkt abgewertet.

## IMP-BO-003: Öffnungszeiten, Wetter und Eventkapazität berücksichtigen

**Umsetzung:**

- OSM `opening_hours` mit einer etablierten Bibliothek auswerten.
- Offizielle Öffnungszeiten bevorzugen, Konflikte markieren.
- Eventkapazität, Beginn, Ende und erwartete Zu-/Abwanderungsphase modellieren.
- Wetter nur als konfigurierbaren Faktor nutzen, besonders für Außenorte.

**Akzeptanzkriterien:**

- Zeitberechnung berücksichtigt lokale Zeitzone, Feiertage und Datumswechsel.
- Ein Outdoor-Ort wird bei schlechtem Wetter nur dann abgewertet, wenn diese
  Modellannahme transparent aktiviert ist.

---

# Priorität 2: Skill `behoerdenetc`

## IMP-BE-001: Offizielle Register systematisch priorisieren

**Mögliche Quellen:**

- Organisationsregister von Staat, Ländern und Kommunen
- Außenministerien für Botschaften und Konsulate
- offizielle Polizei-, Feuerwehr- und Justizportale
- CKAN, DCAT, WFS und ArcGIS Feature Services
- strukturierte `schema.org/GovernmentOrganization`-Daten offizieller Webseiten

**Ziel:** OSM und Wikidata vor allem für Geometrie und Verknüpfung verwenden,
offizielle Register für Existenz, Namen und Zuständigkeit.

**Akzeptanzkriterien:**

- Offizielle Quelle ist erkennbar und mit Abrufdatum dokumentiert.
- Ehemalige oder geschlossene Stellen werden erkannt oder als unklar markiert.
- `office=diplomatic` und `diplomatic=embassy|consulate` werden unterstützt.

## IMP-BE-002: Organisation, Dienststelle und Besuchsort trennen

**Ziel:** Eine Behörde als Organisation nicht mit jeder ihrer Adressen oder dem
zugehörigen Gebäude gleichsetzen.

**Datenmodell:**

- Organisation
- Dienststelle/Niederlassung
- tatsächlicher Besuchsort
- Postanschrift
- Zuständigkeitsgebiet
- Öffnungszeiten und Publikumszugang

**Akzeptanzkriterien:**

- Postfach oder Hauptsitz wird nicht automatisch als öffentlich zugänglicher
  Besuchsort ausgegeben.
- Mehrere Dienststellen einer Organisation bleiben unterscheidbar.

---

# Priorität 2: Skill `oepnvrouten`

## IMP-OP-001: Mobility Database und Transitland für Feed-Discovery

**Ziel:** Veraltete oder schwer zugängliche Feed-Verzeichnisse durch aktuelle,
maschinenlesbare Discovery ergänzen.

**Umsetzung:**

- Mobility Database als bevorzugten Katalog prüfen.
- Transitland als alternative Quelle und Metadatenabgleich nutzen.
- Offizielle Betreiber-URL gegenüber Aggregatoren priorisieren.
- Feed-Gültigkeit, Enddatum und räumliche Abdeckung vor dem Routing testen.

**Akzeptanzkriterien:**

- Feed-Auswahl wird begründet und ist reproduzierbar.
- Abgelaufene Kalender werden vor dem Routing erkannt.
- Feed-Quelle und Prüfergebnis stehen in `zusammenfassung.json`.

## IMP-OP-002: GTFS-Realtime, SIRI und NeTEx ergänzen

**Ziel:** Verspätungen, Ausfälle, Fahrzeugpositionen und europäische
Fahrplandaten berücksichtigen.

**Umsetzung:**

- GTFS-RT Trip Updates und Service Alerts auf statisches GTFS abbilden.
- Vehicle Positions nur verwenden, wenn ihre Aussagekraft dokumentiert ist.
- SIRI/NeTEx als optionale Adapter implementieren.
- Bei fehlender Echtzeit klar „Planfahrplan“ ausgeben.

**Akzeptanzkriterien:**

- Ausgefallene Fahrt wird nicht vorgeschlagen, wenn ein aktueller, passender
  Echtzeit-Hinweis verfügbar ist.
- Alter der Echtzeitdaten wird angezeigt.
- Routing funktioniert weiterhin nur mit statischem GTFS.

## IMP-OP-003: Fußwege mit geeignetem Router berechnen

**Problem:** Der öffentliche OSRM-Dienst ist üblicherweise auf Autofahrten
ausgelegt. Ein Profilparameter garantiert dort kein verfügbares Fußprofil.

**Geeignete Alternativen:** Valhalla, GraphHopper, openrouteservice oder eine
lokale, explizit für Fußwege konfigurierte Routing-Instanz.

**Akzeptanzkriterien:**

- Router und aktives Profil werden dokumentiert.
- Fußwege benutzen keine Autobahnen oder unzulässigen Straßen.
- Luftlinien werden nur als klar markierter Notfall-Fallback verwendet.

## IMP-OP-004: Umstiege realistischer bewerten

**Zusätzliche Informationen:**

- GTFS `pathways.txt`, `transfers.txt` und `levels.txt`
- Barrierefreiheit und Aufzüge
- Echtzeit-Ausfälle von Aufzügen, sofern verfügbar
- Verspätung und historische beziehungsweise modellierte Umstiegsunsicherheit
- letzte Verbindung des Tages und Tarifgrenzen

**Akzeptanzkriterien:**

- Umstiegszeit beinhaltet interne Gehwege, sofern Daten vorhanden sind.
- Barrierefreie Suche ist als Option verfügbar.
- Knappes Umsteigen wird mit einem sichtbaren Risikowert versehen.

## IMP-OP-005: Mikromobilität als offener Fallback

**Ziel:** Vor kostenpflichtigem Ride-Hailing offene Bike-/Scooter-Sharing-Daten
über GBFS als First-/Last-Mile-Option prüfen.

**Akzeptanzkriterien:**

- Verfügbarkeit ist zeitbezogen und darf nicht langfristig garantiert werden.
- Fuß-, Sharing- und ÖPNV-Abschnitte sind in der Route getrennt gekennzeichnet.
- Ohne GBFS bleibt die bisherige Suche funktionsfähig.

---

# Priorität 3: Spezialisierte OpenCode-Agents

## IMP-AG-001: Agent `source-scout`

**Aufgabe:** Datenquellen, APIs, Lizenzen, Formate, Aktualität und Rate-Limits
recherchieren. Der Agent verändert keine Produktionsskripte.

**Ausgabe:** Strukturiertes Quellenprofil mit Empfehlungen und offenen Risiken.

## IMP-AG-002: Agent `source-inspector`

**Aufgabe:** Kleine Stichproben einer gefundenen Quelle prüfen: Schema,
Geometrien, CRS, Zeitbezug, Abdeckung und Datenqualität.

**Sicherheit:** Downloads begrenzen; keine unbekannten Pickles oder Programme
ausführen.

## IMP-AG-003: Agent `geo-validator`

**Aufgabe:** Stadtgrenzen, CRS, ungültige Geometrien, räumliche Joins,
Duplikate und Koordinatenreihenfolge kontrollieren.

**Besonderer Prüfpunkt:** Für Randpunkte ist `contains()` oft ungeeignet, weil
es die Grenze ausschließt. Je nach fachlicher Bedeutung `covers()` oder eine
dokumentierte Toleranz prüfen.

## IMP-AG-004: Agent `result-critic`

**Aufgabe:** Die höchstbewerteten und einige verworfene Kandidaten unabhängig
prüfen, Gegenbeweise suchen und mögliche False Positives melden. Standardmäßig
nur lesen und recherchieren, nicht editieren.

## IMP-AG-005: Agent `skill-improver`

**Aufgabe:** Strukturiertes Feedback und Benchmark-Ergebnisse analysieren und
einen konkreten Änderungsvorschlag erstellen. Keine automatische Änderung von
Schwellen oder Skill-Anweisungen ohne Review.

## IMP-AG-006: Agent `export-qa`

**Aufgabe:** GeoJSON, KML, GPX und Zusammenfassung validieren; Geometrien,
Encoding, Pflichtfelder und Kartenlesbarkeit prüfen.

---

# Kleinere technische Korrekturen und Prüfaufträge

## IMP-QA-001: Regionsfilter prüfen

`shapely.contains()` schließt Punkte exakt auf der Polygonbegrenzung aus.
Fachlich prüfen, ob `covers()` oder eine kleine metrische Toleranz geeigneter
ist. MultiPolygons, Inseln und ungültige Geometrien testen.

## IMP-QA-002: OSM-Tags regelmäßig validieren

Filter gegen aktuelle OSM-Tagging-Praxis und Taginfo prüfen. Veraltete oder
seltene Tags nicht kommentarlos entfernen, sondern Trefferzahlen und Ersatz
dokumentieren. Besonders diplomatische Einrichtungen, öffentliche Gebäude,
Kultur-POIs und Indoor-Tags prüfen.

## IMP-QA-003: Harte Serverlisten reduzieren

Overpass- und Routing-Endpunkte ändern sich. Health-Check, konfigurierbare
Endpunkte und zeitlich begrenzte Status-Caches einführen. HTTP-Fallbacks nur
verwenden, wenn das Sicherheitsrisiko ausdrücklich akzeptiert wurde; HTTPS
bevorzugen.

## IMP-QA-004: README und Installationshinweise angleichen

Das Repository verwendet laut Projektanweisung `.venv`, während die README an
einer Stelle `venv` nennt. Bei einer späteren Dokumentationsänderung auf einen
einheitlichen Pfad bringen.

---

# Empfohlene Umsetzungsreihenfolge

1. `IMP-005` Benchmark- und Regressionstest-Suite
2. `IMP-002` Provenienzmodell
3. `IMP-003` gemeinsamer Quellenadapter
4. `IMP-001` Datenquellen-Scout und Regionsprofile
5. `IMP-004` strukturierte Learnings
6. `IMP-OP-001` bis `IMP-OP-003`
7. `IMP-MA-001`
8. `IMP-BO-001` und `IMP-BO-002`
9. `IMP-BE-001` und `IMP-BE-002`
10. `IMP-FW-001` und `IMP-FW-002`
11. Spezialisierte Agents als unterstützende Qualitätsschicht

Der Benchmark sollte zuerst kommen, obwohl die gemeinsame Infrastruktur den
größten funktionalen Nutzen hat. Ohne reproduzierbare Messung kann ein LLM nur
schwer feststellen, ob eine Änderung die Skills tatsächlich verbessert hat.

---

# Arbeitsauftrag für ein umsetzendes LLM

Bei Auswahl eines Vorschlags:

1. Zugehörige `SKILL.md`, Referenzdateien, Skripte und vorhandene Ergebnisse
   untersuchen.
2. Annahmen und Abhängigkeiten nennen.
3. Einen minimalen, isolierten Implementierungsplan erstellen.
4. Lizenz und Nutzungsbedingungen neuer Quellen prüfen.
5. Implementierung mit Cache, Fehlerbehandlung und Provenienz vornehmen.
6. Offline-Tests und einen begrenzten Live-Test ausführen.
7. Vorher-/Nachher-Metriken berichten.
8. Dokumentation und Skill-Anweisungen nur soweit nötig aktualisieren.
9. Keine anderen Vorschläge nebenbei umsetzen.
10. Unsicherheiten und verbleibende Risiken ausdrücklich dokumentieren.
