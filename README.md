# exploreGeoStructures

OpenCode-Skills zum Suchen, Bewerten und Kombinieren räumlicher Strukturen,
Orte und Wege.

## Projektübersicht

* `AGENTS.md` - zentrale Anweisungen (Python-Venv, Kartenexporte und kombinierte Anfragen)
* `.opencode/skills` - hier sind skills definiert, die einen gewissen Reifegrad haben. Mit "/skills" kann man sie in opencode auflisten
und mit "@" einen einzelnen Skill benutzen
* `.opencode/skills/fussweg` - sucht einen möglichst geraden Fußweg ohne parallele Verkehrswege und ohne Abzweigungen von gewisser Länge bzw. Passierdauer
* `.opencode/skills/mallsetc` - sucht nach Einkaufszentren, Bahnhöfen und Passagen mit mehreren Ausgängen, Ausgängen auf unterschiedlichen Ebenen und ÖPNV-Anbindung
* `.opencode/skills/behoerdenetc` - sucht nach Behörden, Botschaften, Polizeidienststellen etc. in einer Stadt oder einem Stadtteil
* `.opencode/skills/belebteOrte` - sucht nach Orten in einer Stadt oder einem Stadtteil, die in einem Zeitfenster besonders belebt sind
* `.opencode/skills/oepnvrouten` - sucht  nach einer ÖPNV-Route mit mehreren und unterschiedlichen Verkehrsmitteln, kurzen Umsteigezeiten, ohne Rückkehr an bereits besuchte Haltetellen
* `.opencode/skills/geo-workflow` - kombiniert mehrere Skills anhand allgemeiner räumlicher und zeitlicher Constraints zu einem zusammenhängenden Workflow
* `.opencode/plan/geo-workflow-umsetzungsplan.md` - Architektur- und Umsetzungsplan des Orchestrators

## Design der Skills

Sie nutzen API-Zugänge zu Kartendiensten wie OSM/overpass, Echtzeit-Verkehrsdatenquellen via GTFS und andere opendata-Angebote. Da die skills ihre Aufgaben weltweit bewältigen sollen, müssen sie für eine bisher nicht bearbeitete Stadt oder Region zunächst die besten Datenquellen recherchieren (Datenquellen-Scouting).

Die skills sind die zentralen und wichtigsten Teile. Jeder Skill besteht aus einer `SKILL.md`-Datei, die den Skill, seinen Ablauf, seine Ein- und Ausgabe definiert. Daten, die hierfür benötigt werden, wie Formatvorgaben, Regeln, etc. sind in files im Verzeichnis `reference` ausgelagert und werden in der SKILL.md referenziert. Siehe [Claude code Skill Architecture](https://www.mindstudio.ai/blog/claude-code-skills-architecture-skill-md-reference-files)

Die Skills sind als [self-improving skills](https://www.mindstudio.ai/blog/self-improving-ai-skills-claude-code) angelegt. Länder und Städte haben unterschiedliche Datenquellen für Geodaten. Die Zugriffe auf solche Dienste variieren ebenfalls. Solche Erkenntnisse speichert sich der skill am Ende und fragt den Nutzer nach einem feedback.

## Wie nutzt man das Paket?
### Voraussetzungen
1. Linux Rechner am Internet
2. opencode V2 installiert
3. python3 installiert
4. git installiert

### Installation
1. Download mittels `git clone git@github.com:Steffen531/exploreGeoStructures.git`
2. Im obersten Verzeichnis `exploreGeoStructures` ein Python Virtual Environment unter `.venv` anlegen: `python3 -m venv .venv`

### Erste Schritte
1. `opencode` ausführen
2. Mit `/skills` skills anzeigen: es sollten die oben beschriebenen skills zu sehen sein
3. Eine erste Aufgabe stellen wie z.B. "Suche Behörden in Bochum". Dabei werden vermutlich diverse python packages ins venv installiert.

### Kombinierte Workflows

Bei Anfragen mit mehreren voneinander abhängigen Schritten wird
`geo-workflow` verwendet. Der Skill übersetzt die Anfrage in einen
Constraint-Graphen und verbindet normalisierte Kandidaten der Fach-Skills. Er
unterstützt unter anderem räumliche Nähe, Übergänge, Ausschlussbereiche,
Zeitfenster, Dauerbedingungen und geordnete Abfolgen. Die Reihenfolge der
Fach-Skills ist nicht fest codiert.

Beispiel:

```text
Verwende @geo-workflow. Finde einen 20-minütigen Fußweg, der nahe einer
Haltestelle endet. Suche von dort eine zeitlich passende ÖPNV-Verbindung zu
einem Ort, der bei der Ankunft voraussichtlich belebt ist.
```

Die Reihenfolge, Region und Zeiten sind nicht fest codiert. Ergebnisse liegen
unter `results/<workflow-id>/` als GeoJSON, KML, GPX und Zusammenfassung.

Jeder Fach-Skill beschreibt seine maschinenlesbaren Fähigkeiten in einer
`capabilities.json`. Der Orchestrator prüft harte Constraints deterministisch
und meldet unvereinbare Anforderungen, statt eine Route zu erfinden. Taxi- oder
Ride-Hailing-Abschnitte ohne Provider-API werden ausdrücklich nur als
Straßenrouting-Schätzung gekennzeichnet.

Der aktuelle Funktionsumfang und bekannte Grenzen stehen in
[`implementation-status.md`](.opencode/skills/geo-workflow/reference/implementation-status.md).

Offline-Tests ausführen:

```bash
.venv/bin/python -m unittest discover -s tests -v
```
   
## Beispiele

### Einsame Fußwege in München Giesing
![Fußwege in Giesing](docs/Giesing_Fusswege.jpg)

### Die belebtesten Orte in Potsdam Sonntag abends
![Die belebtesten Orte in Potsdam Sonntag abends](docs/Potsdam_belebtesteOrteSonntagAbends.jpg)

### Behörden, Botschaften & Co. in Leiden (Niederlande)
![Behörden, Botschaften & Co. in Leiden](docs/LeidenErg.jpg)
![Behörden, Botschaften & Co. in Leiden](docs/Leiden.jpg)

### Malls, Bahnhöfe u.ä. in Dresden
![Malls & Co. in Dresden](docs/DresdenMallsEtc.jpg)

### Eine 1-stündige ÖPNV-Rundfahrt am 1.12.26 in Frankfurt a.M. ab 18:00 Uhr
![ÖPNV-Rundfahrt in FFM](docs/ÖPNVFrankfurt.jpg)

## Nächste Schritte
1. Prüfen, ob spezialisierte OpenCode-Agents für Datenquellen-Scouting,
   Quellenprüfung und Exportvalidierung einen messbaren Vorteil bringen.
2. Den offenen Backlog in [`improvements.md`](improvements.md) anhand des
   [`Implementierungsstatus`](.opencode/skills/geo-workflow/reference/implementation-status.md)
   priorisiert weiterführen. Als Nächstes insbesondere:
   - zusammenhängende Fußwege über mehrere OSM-Ways auf einem topologischen Graphen,
   - reale Aktivitätsdaten und mehrdimensionale Belebtheitsscores,
   - offizielle Behördenregister und belastbarere Öffnungszeiten,
   - bessere GTFS-Feed-Erkennung sowie optionale Echtzeitdaten,
   - reproduzierbare Live-Tests vollständiger Workflow-Ketten.
3. Die Bedienung für Nutzer ohne IT- oder OpenCode-Erfahrung vereinfachen:
   Installation, Beispielanfragen, Berechtigungen und Kartenimport verständlicher
   und möglichst automatisiert gestalten.
