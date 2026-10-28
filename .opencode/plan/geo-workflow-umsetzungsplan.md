# Umsetzungsplan: Generische räumlich-zeitliche Skill-Orchestrierung

## 1. Ziel

Das Projekt erhält den neuen OpenCode-Skill `geo-workflow`. Er kombiniert die
vorhandenen Fach-Skills anhand frei formulierter räumlicher und zeitlicher
Abhängigkeiten. Er darf weder das Hamburg-Beispiel noch eine bestimmte
Skill-Reihenfolge fest codieren.

Der Orchestrator soll insbesondere:

1. eine natürlichsprachliche Anfrage in einen validierbaren Constraint-Graphen
   übersetzen,
2. passende Fach-Skills auswählen und laden,
3. eine zweckmäßige Ausführungsreihenfolge bestimmen,
4. Ergebnisse über normalisierte räumliche und zeitliche Schnittstellen
   verbinden,
5. bei nicht passenden Kandidaten kontrolliert Alternativen ausprobieren,
6. unerfüllbare Anforderungen mit konkreten Gründen melden und
7. die vollständige Kombination gemeinsam als GeoJSON, KML, GPX und JSON
   exportieren.

## 2. Wichtige Rahmenbedingungen

- Python ausschließlich mit `.venv/bin/python` ausführen.
- Pakete ausschließlich mit `.venv/bin/pip` installieren.
- Keine API-Schlüssel in Dateien speichern; Umgebungsvariablen verwenden.
- Bestehende Standalone-Aufrufe der Fach-Skills kompatibel halten.
- Harte Constraints niemals stillschweigend lockern.
- Fehlende Daten und ausgefallene Dienste von einem validen leeren Ergebnis
  unterscheiden.
- Ergebnisse müssen Quellen, Konfidenz, Zeitbezug und verwendete Fallbacks
  ausweisen.
- Netzwerkabfragen benötigen Timeout, User-Agent, begrenzte Wiederholungen und
  Cache.
- Keine Taxi-/Uber-Verfügbarkeit, Preise oder Fahrzeiten behaupten, wenn keine
  entsprechende Provider-API vorliegt. Ein Routing-Fallback ist als
  `estimated_ride_hailing` zu kennzeichnen.
- Eine OpenCode-Skill-Datei ist eine Anweisung und kein direkt aufrufbares
  Softwaremodul. Deshalb arbeitet die Lösung hybrid: Das LLM lädt und steuert
  die Skills; deterministische Python-Programme validieren, filtern, verbinden
  und exportieren deren Kandidaten.

## 3. Festgestellter Ausgangszustand

Vor der Implementierung erneut prüfen, da sich der Stand geändert haben kann:

- `.opencode/skills/fussweg/reference/fussweg_suche.py` enthält wesentliche
  `pass`-/`TODO`-Stellen und unterstützt noch keine Haltestellen- oder
  Endpunktnähe.
- `.opencode/skills/belebteOrte/reference/belebte_orte_suche.py` enthält noch
  unimplementierte Merge-, Bewertungs- und Exportteile.
- `.opencode/skills/oepnvrouten/reference/oepnvrouten_suche.py` verlangt einen
  namentlich bekannten Start und ein namentlich bekanntes Ziel. Im primären
  GTFS-Zweig werden die Dauergrenzen derzeit nicht konsequent angewendet.
- Die Skills verwenden unterschiedliche Ausgabestrukturen und besitzen keinen
  maschinenlesbaren Fähigkeitsvertrag.
- Jeder Skill fordert momentan eigenes Nutzerfeedback an. In einem Workflow
  darf es nur eine gemeinsame Feedbackrunde geben.
- `opencode.jsonc` bindet `.opencode/skills` bereits ein. Für die Discovery des
  neuen Skills ist voraussichtlich keine Konfigurationsänderung nötig.

## 4. Zielarchitektur

### 4.1 Neuer Skill

Folgende Struktur anlegen:

```text
.opencode/skills/geo-workflow/
├── SKILL.md
├── capabilities.json
├── reference/
│   ├── contracts.md
│   ├── planner.py
│   ├── constraint_engine.py
│   ├── capability_registry.py
│   ├── ride_hailing.py
│   ├── exporter.py
│   └── learnings.md
└── schemas/
    ├── workflow.schema.json
    ├── candidate.schema.json
    ├── capabilities.schema.json
    ├── execution-status.schema.json
    └── result.schema.json
```

Die genaue Modulaufteilung darf an bestehende Projektkonventionen angepasst
werden. Verantwortlichkeiten und Schema-Trennung müssen erhalten bleiben.

### 4.2 Fähigkeitsdateien der Fach-Skills

In jedem vorhandenen Skill eine `capabilities.json` ergänzen:

```text
.opencode/skills/fussweg/capabilities.json
.opencode/skills/oepnvrouten/capabilities.json
.opencode/skills/belebteOrte/capabilities.json
.opencode/skills/mallsetc/capabilities.json
.opencode/skills/behoerdenetc/capabilities.json
```

Die Dateien beschreiben nur tatsächlich implementierte Fähigkeiten. Geplante,
aber noch nicht funktionsfähige Fähigkeiten dürfen nicht beworben werden.

### 4.3 Tests

Eine vom Produktionscode getrennte Testsuite anlegen:

```text
tests/geo_workflow/
├── fixtures/
├── test_schemas.py
├── test_spatial_constraints.py
├── test_temporal_constraints.py
├── test_planner.py
├── test_backtracking.py
├── test_adapters.py
├── test_export.py
└── test_integration_offline.py
```

## 5. Gemeinsame Verträge

### 5.1 Workflow

Das LLM übersetzt die Nutzeranfrage gemäß `geo-workflow/SKILL.md` in eine
`workflow.json`. Sie enthält mindestens:

```json
{
  "workflow_id": "stable-or-generated-id",
  "region": {
    "name": "Hamburg, Deutschland",
    "timezone": "Europe/Berlin",
    "geometry": null
  },
  "nodes": [],
  "constraints": [],
  "limits": {
    "max_candidates_per_node": 50,
    "max_combinations": 5000,
    "max_runtime_seconds": 900
  }
}
```

Jeder Knoten enthält mindestens `id`, `capability`, `producer_skill`,
`parameters` und erwartete `entity_types`. Knoten referenzieren keine
temporären Dateipfade als fachliche Identität.

### 5.2 Normalisierter Kandidat

Kandidaten werden als GeoJSON-Features ausgegeben. Pflichtfelder in
`properties`:

```json
{
  "candidate_id": "fussweg:123",
  "producer_skill": "fussweg",
  "entity_type": "path",
  "start": {"lat": 53.0, "lon": 10.0},
  "end": {"lat": 53.1, "lon": 10.1},
  "temporal": {
    "start": null,
    "end": null,
    "duration_minutes": 20,
    "timezone": "Europe/Berlin",
    "precision": "estimated"
  },
  "score": 0.8,
  "confidence": 0.7,
  "sources": [],
  "warnings": [],
  "raw_reference": null
}
```

Regeln:

- GeoJSON-Koordinaten immer in der Reihenfolge `[lon, lat]`.
- Zeiten als ISO-8601 mit Zeitzone speichern.
- Start und Ende müssen zur Orientierung der Liniengeometrie passen.
- `Point`, `LineString`, `MultiLineString`, `Polygon` und `MultiPolygon`
  unterstützen.
- Unbekannte Werte sind `null`, nicht erfundene Schätzwerte.
- Schätzungen müssen `precision` und Methode nennen.

### 5.3 Ausführungsstatus

Jeder Adapter schreibt `status.json` mit:

- `success`: verwertbare Kandidaten erzeugt,
- `empty`: Quelle funktionierte, aber keine Kandidaten erfüllten die Anfrage,
- `degraded`: nur Fallback oder unvollständige Quellen verfügbar,
- `error`: Ausführung oder Quelle fehlgeschlagen.

Zusätzlich: Zeitstempel, Quellenstatus, Fehlerklasse, Warnungen,
Kandidatenanzahl und angewandte Parameter.

## 6. Constraint-Modell

### 6.1 Räumliche Operatoren

Mindestens implementieren und testen:

- `near`: Abstand zweier Geometrien innerhalb eines Radius,
- `within`: Geometrie liegt in Region/Polygon,
- `intersects`: Geometrien schneiden sich,
- `starts_near` und `ends_near`,
- `starts_at` und `ends_at`,
- `passes_through`,
- `avoids`: Geometrie hält Abstand zu einer Kandidatenmenge,
- `sequence_continuity`: Ende eines Segments ist mit dem Start des nächsten
  Segments erreichbar.

Entfernungen ausschließlich in geeignetem metrischem CRS oder mit geodätischer
Berechnung bestimmen. Keine Puffer in Längen-/Breitengraden erzeugen.

Für `avoids`:

1. Ausschlussobjekte über einen anderen Skill, beispielsweise
   `behoerdenetc`, erzeugen.
2. Einen konfigurierbaren metrischen Puffer um Punkte oder Flächen bilden.
3. Gegen die vollständige Weggeometrie prüfen, nicht nur gegen Start und Ende.
4. Verwerfen oder als weiche Verletzung bewerten, abhängig vom Constraint.
5. Ohne angegebenen Radius beim Nutzer nachfragen oder einen ausdrücklich
   dokumentierten Workflow-Standard verwenden. Der Wert darf nicht verborgen
   sein.

### 6.2 Zeitliche Operatoren

Mindestens implementieren und testen:

- `starts_between`,
- `ends_between`,
- `duration_between`,
- `before`,
- `after`,
- `overlaps`,
- `gap_between`,
- `active_at`,
- `sequence_time`: Folgeabschnitt beginnt erst nach Ende plus Übergangszeit.

Lokale Zeitzone, Sommer-/Winterzeit, Tageswechsel und GTFS-Zeiten größer als
`24:00:00` korrekt behandeln.

### 6.3 Härte und Bewertung

Jeder Constraint besitzt:

```json
{
  "type": "ends_near",
  "from": "walk-1",
  "to": "transit-1",
  "hard": true,
  "parameters": {"max_distance_m": 150},
  "weight": 1.0
}
```

- Harte Verletzung: Kombination verwerfen.
- Weiche Verletzung: Strafwert und Begründung speichern.
- Score-Beiträge nachvollziehbar in `zusammenfassung.json` ausgeben.
- Automatische Lockerungen nur als neue, explizit dokumentierte Suchstufe;
  ursprüngliche und gelockerte Werte beide speichern.

## 7. Capability Registry und Planung

### 7.1 Fähigkeitsmodell

Jede `capabilities.json` beschreibt:

- erzeugte Entitätstypen,
- erforderliche und optionale Parameter,
- unterstützte räumliche und zeitliche Filter,
- ob Koordinaten, Namen oder Kandidatenmengen akzeptiert werden,
- Datenquellen und typische Präzision,
- bekannte Einschränkungen,
- Adapterbefehl und Ausgabeformat.

Erwartete Zielabdeckung:

| Skill | Erzeugte Typen | Benötigte Ergänzungen |
|---|---|---|
| `fussweg` | `path` | Dauerfenster, Start-/Endnähe, Ausschlussflächen |
| `oepnvrouten` | `transit_route` | Koordinaten/Kandidatenmengen, Abfahrts- und Ankunftsfenster, GTFS-Dauerfilter |
| `belebteOrte` | `busy_place`, `busy_area` | vollständiges Datum, Zeitzone, belastbarer Score |
| `mallsetc` | `urban_structure` | normalisierter Typ, Zugänge, ÖPNV-Nähe |
| `behoerdenetc` | `authority_place` | normalisierte Geometrie/Kategorie für Ziel- oder Ausschlussfilter |
| Ride-Hailing-Adapter | `ride_hailing_route` | Anbieter- oder transparent gekennzeichnetes Fahrschätzungs-Routing |

### 7.2 Planner

Der Planner soll keinen universellen NLP-Parser implementieren. Das LLM erzeugt
den Workflow-Graphen; `planner.py` validiert und plant ihn deterministisch.

Ablauf:

1. Schema validieren.
2. Fähigkeiten gegen Registry prüfen.
3. Nicht unterstützte Constraints vor Netzwerkzugriff melden.
4. Abhängigkeitsgraph auf Zyklen und fehlende Produzenten prüfen.
5. Mit festen Zeit-/Ortsankern und selektiven Produzenten beginnen.
6. Produzenten möglichst spät breit ausführen; Kandidaten früh filtern.
7. Unabhängige Knoten parallel ausführbar markieren.
8. Kandidaten über Backtracking/Constraint-Propagation verbinden.
9. Grenzen für Kandidaten, Kombinationen und Laufzeit beachten.
10. Vollständige und partielle Lösungen getrennt zurückgeben.

Für komplexe Ketten muss der Planner vorwärts und rückwärts planen können. Eine
feste Ankunftszeit kann beispielsweise zuerst Zielkandidaten bestimmen, danach
passende ÖPNV-Ursprünge und erst anschließend vorherige Fußwege.

## 8. Anpassung der Fach-Skills

### 8.1 Gemeinsamer Adaptermodus

Jedes Fachskript erhält zusätzlich zur bisherigen CLI:

```text
--request <workflow-node.json>
--output <node-output-directory>
--orchestrated
```

Im Adaptermodus entstehen mindestens:

```text
<node-output-directory>/kandidaten.geojson
<node-output-directory>/status.json
```

`--orchestrated` unterdrückt die jeweilige Feedbackfrage. Technische Warnungen
und Learnings werden an den Orchestrator zurückgegeben. Standalone-Verhalten
und bestehende Parameter bleiben erhalten.

### 8.2 `fussweg`

- Fehlende Kernlogik vervollständigen oder bestehende funktionierende Logik
  sauber anbinden.
- Gehzeit explizit aus Länge und dokumentierter Geschwindigkeit ableiten.
- Dauerbereich direkt akzeptieren.
- Start- und Endpunktnähe gegen Kandidatenmengen unterstützen.
- Ausschlussgeometrien einschließlich Behördenkorridoren berücksichtigen.
- Wegorientierung eindeutig exportieren.
- Verwerfungsgründe pro Kandidat speichern.

### 8.3 `oepnvrouten`

- Start und Ziel als Koordinate, Stations-ID, Name oder Kandidatenmenge
  akzeptieren.
- Stationen räumlich zu Koordinaten zuordnen; unscharfe Namenssuche nicht als
  einzige Methode verwenden.
- Abfahrts- und Ankunftsfenster unterstützen.
- Dauergrenzen auch im primären GTFS-Zweig anwenden.
- Mehrere Start-/Zielpaare effizient prüfen und früh beschneiden.
- Fuß-, ÖPNV- und gegebenenfalls Ride-Hailing-Abschnitte getrennt markieren.
- Planfahrplan und Echtzeitdaten klar unterscheiden.

### 8.4 `belebteOrte`

- Fehlende Merge-, Score- und Exportlogik vervollständigen.
- Ein vollständiges lokales Datum mit Uhrzeit statt nur Wochentag akzeptieren.
- Direkte Messwerte, modellierte Werte und Proxys getrennt kennzeichnen.
- Orte und Cluster als normalisierte Kandidaten ausgeben.
- Zukünftige Events nur bei belastbarer Datenquelle berücksichtigen; sonst
  Unsicherheit ausweisen.

### 8.5 `mallsetc` und `behoerdenetc`

- Bestehende Ergebnisse in das gemeinsame Kandidatenschema überführen.
- Kategorien und Geometriepräzision erhalten.
- Malls/Bahnhöfe/Passagen als auswählbare Untertypen ausgeben.
- Behördenpunkte als Zielobjekte und als Ausschlussmenge nutzbar machen.
- Öffnungszeiten nur als Constraint verwenden, wenn Quelle und Zeitbezug
  ausreichend belastbar sind.

### 8.6 Ride-Hailing

Ride-Hailing ist als allgemeiner Segmenttyp umzusetzen, nicht als festes
„Uber“-Versprechen:

1. Wenn eine erlaubte Provider-API konfiguriert und verfügbar ist, deren
   Verfügbarkeit und Provenienz verwenden.
2. Sonst ein geeignetes Straßenrouting verwenden und Ergebnis als
   `estimated_ride_hailing` markieren.
3. Ohne Preisdaten keine Preise schätzen.
4. Anbietername nur ausgeben, wenn die Anbieterquelle dies rechtfertigt.
5. Abhol-/Absetzpunkt, Fahrzeitpräzision und Übergangszeit separat modellieren.

## 9. Orchestrator-Skill-Anweisung

`geo-workflow/SKILL.md` muss mindestens folgenden Ablauf festlegen:

1. Nutzeranfrage in Knoten und Constraints zerlegen.
2. Mehrdeutigkeiten identifizieren, die das Ergebnis wesentlich verändern.
3. Nur dafür gezielt nachfragen, beispielsweise fehlender Ausschlussradius.
4. Capability Registry lesen und Machbarkeit prüfen.
5. Benötigte Fach-Skills mit dem Skill-Tool laden.
6. `workflow.json` erzeugen und validieren.
7. Fach-Skills im geplanten Adaptermodus ausführen.
8. Status jeder Stufe prüfen; Fehler nicht als leere Ergebnisse behandeln.
9. Kandidaten mit der Constraint Engine verbinden.
10. Falls nötig begrenzt backtracken oder eine explizite Lockerung vorschlagen.
11. Gemeinsames Ergebnis exportieren.
12. Nur eine Feedbackrunde für den gesamten Workflow durchführen.
13. Workflow-Learnings in `geo-workflow/reference/learnings.md` ergänzen;
    fachspezifische technische Erkenntnisse zusätzlich dem jeweiligen Skill
    zuordnen, ohne weitere Nutzerfragen zu stellen.

Die Skill-Beschreibung muss kombinierte Anfragen zuverlässig auslösen, etwa bei
mehreren verbundenen Orten, Wegen, Verkehrsmitteln oder Zeitbedingungen.

Zusätzlich `AGENTS.md` ergänzen: Bei mindestens zwei voneinander abhängigen
Geo-Fachaufgaben zuerst `geo-workflow` verwenden. README um Verwendung und ein
nicht fest codiertes Beispiel ergänzen.

## 10. Ausgabe

Jeder Lauf erhält ein eigenes Verzeichnis:

```text
results/<workflow-id>/
├── workflow.json
├── plan.json
├── candidates/
│   └── <node-id>/
│       ├── kandidaten.geojson
│       └── status.json
├── ergebnis.geojson
├── ergebnis.kml
├── ergebnis.gpx
└── zusammenfassung.json
```

Das Endergebnis enthält:

- geordnete Segmente und Aufenthalte,
- Übergänge zwischen Segmenten,
- lokale Start-/Endzeiten und Dauer,
- erfüllte und verletzte Constraints,
- Teil- und Gesamtscores,
- Quellen, Konfidenz und Aktualität,
- Fallbacks und Schätzungen,
- verworfene Kombinationen mit aggregierten Gründen,
- partielle Lösungen, wenn keine vollständige Lösung existiert.

GeoJSON soll die vollständigen Daten enthalten. KML und GPX müssen visuell
unterscheidbare Segmenttypen und wichtige Übergabepunkte darstellen. Dem Nutzer
anschließend den Import über `umap.openstreetmap.de` erklären.

## 11. Tests

### 11.1 Offline- und Unit-Tests

Vor Live-Tests implementieren:

- Validierung aller JSON-Schemas,
- Koordinatenreihenfolge und metrische Distanzberechnung,
- sämtliche räumlichen Operatoren,
- sämtliche zeitlichen Operatoren,
- Zeitzonen, Sommerzeit, Tageswechsel und GTFS `>24:00`,
- harte/weiche Constraints,
- Planner-Reihenfolge und Zyklenerkennung,
- Backtracking, Limits und partielle Lösungen,
- Status `success`/`empty`/`degraded`/`error`,
- Adapter-Kompatibilität,
- GeoJSON-, KML-, GPX- und JSON-Syntax,
- Offline-Fixtures für jeden Fach-Skill.

Netzwerkantworten für Standardtests durch kleine lizenzkonforme Fixtures oder
Mocks ersetzen. Live-Tests getrennt markieren.

### 11.2 Integrationsszenarien

1. **Fußweg → ÖPNV → belebter Ort in Hamburg.**
   Prüft Dauerfenster des Fußwegs, räumlichen Übergang zur Haltestelle,
   fahrplanbasierte Verbindung und zeitbezogene Belebtheit am Ziel.

2. **Belebter Ort → ÖPNV → Fußweg → Taxi/Uber-Fahrt → ÖPNV.**
   Randbedingung: Behörden und vergleichbare Einrichtungen entlang des Fußwegs
   vermeiden. Der Test setzt einen expliziten metrischen Ausschlussradius und
   prüft den vollständigen Fußwegkorridor. Ohne echte Provider-API muss das
   Taxi-Segment als `estimated_ride_hailing` erscheinen.

3. **ÖPNV → belebter Ort wie Mall o. ä. → ÖPNV → Fußweg → Taxifahrt.**
   Prüft die Verbindung von `belebteOrte` und `mallsetc`, einen zeitlich
   begrenzten Aufenthalt, zwei ÖPNV-Übergänge und ein abschließendes
   Ride-Hailing-Segment.

4. **Anfrage mit unvereinbaren Constraints.**
   Es darf keine erfundene vollständige Lösung entstehen. Erwartet werden eine
   verständliche Konfliktbeschreibung, Verwerfungsgründe und, soweit möglich,
   klar gekennzeichnete partielle Lösungen oder vorgeschlagene Lockerungen.

Szenario 5 ist ausdrücklich nicht vorgesehen.

Mindestens zwei deutlich unterschiedliche Regionen für begrenzte Live-Smoke-
Tests verwenden. Das Hamburg-Szenario allein genügt nicht.

## 12. Empfohlene Implementierungsreihenfolge

Jede Phase separat testen und nur bei grünen Tests fortfahren:

1. Aktuellen Stand und vorhandene Änderungen prüfen; Baseline dokumentieren.
2. Offline-Testgerüst und Fixtures anlegen.
3. Schemas und `contracts.md` erstellen.
4. Constraint Engine mit Unit-Tests implementieren.
5. Capability Registry und Planner mit Mock-Kandidaten implementieren.
6. Gemeinsamen Exporter implementieren und Formate validieren.
7. `behoerdenetc` und `mallsetc` als zunächst einfachere Punkt-/Flächen-
   Produzenten anbinden.
8. `fussweg` vervollständigen und Adaptermodus einschließlich `avoids`
   implementieren.
9. `belebteOrte` vervollständigen und zeitbezogenen Adapter implementieren.
10. `oepnvrouten` um koordinaten- und zeitfensterbasiertes Routing erweitern.
11. Ride-Hailing-Adapter mit transparentem Schätzfallback implementieren.
12. `geo-workflow/SKILL.md`, Feedbacksteuerung und Learnings ergänzen.
13. Vier Offline-Integrationsszenarien ausführen.
14. Zwei begrenzte Live-Smoke-Tests durchführen.
15. AGENTS.md und README aktualisieren.
16. Ergebnisse, Restunsicherheiten und bekannte Grenzen dokumentieren.

## 13. Abnahmekriterien

Die Umsetzung gilt nur dann als abgeschlossen, wenn:

1. keine Stadt, kein Datum und keine feste Skill-Reihenfolge im Planner fest
   codiert ist,
2. alle fünf bestehenden Fach-Skills über gemeinsame Verträge kombinierbar
   sind,
3. Ride-Hailing als transparenter Segmenttyp verfügbar ist,
4. räumliche und zeitliche Constraints deterministisch geprüft werden,
5. `avoids` die vollständige Weggeometrie und echte Ausschlusskandidaten prüft,
6. GTFS-Routen Abfahrts-, Ankunfts- und Dauerfenster berücksichtigen,
7. unlösbare Anforderungen nicht zu erfundenen Lösungen führen,
8. Quellen, Konfidenz, Fallbacks und Verwerfungsgründe exportiert werden,
9. bestehende Standalone-Aufrufe weiter funktionieren,
10. jeder kombinierte Lauf nur eine Nutzerfeedbackrunde auslöst,
11. GeoJSON, KML, GPX und Zusammenfassung automatisiert validiert werden,
12. alle Offline-Tests und die vier Integrationsszenarien erfolgreich sind und
13. Live-Abhängigkeiten und verbleibende Unsicherheiten ausdrücklich
    dokumentiert sind.

## 14. Bewusste Nicht-Ziele der ersten Version

- Kein allgemeiner natürlichsprachlicher Parser außerhalb des LLM-geführten
  Skill-Ablaufs.
- Keine Garantie realer Uber-/Taxi-Verfügbarkeit ohne autorisierte Provider-
  API.
- Keine automatische Änderung fachlicher Schwellen aufgrund eines einzelnen
  Feedbacks.
- Keine unbegrenzte globale Kandidatensuche.
- Keine stillschweigende Nutzung von Luftlinien als reale Wege oder Fahrten.
- Keine Spezialisierung auf die vier Testszenarien; sie dienen ausschließlich
  als Abdeckung des generischen Modells.
