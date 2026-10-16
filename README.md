* `AGENTS.md` - zentrale Anweisungen (Nutzung python venv, Visualisierung auf Karten mittels kml-files für openstreetmap, ...)
* `.opencode/skills` - hier sind skills definiert, die einen gewissen Reifegrad haben. Mit "/skills" kann man sie in opencode auflisten
und mit "@" einen einzelnen Skill benutzen
* `.opencode/skills/fussweg` - sucht einen möglichst geraden Fußweg ohne parallele Verkehrswege und ohne Abzweigungen von gewisser Länge bzw. Passierdauer
* `.opencode/skills/mallsetc` - sucht nach Einkaufszentren, Bahnhöfen und Passagen mit mehreren Ausgängen, Ausgängen auf unterschiedlichen Ebenen und ÖPNV-Anbindung
* `.opencode/skills/behoerdenetc` - sucht nach Behörden, Botschaften, Polizeidienststellen etc. in einer Stadt oder einem Stadtteil
* `.opencode/skills/belebteOrte` - sucht nach Orten in einer Stadt oder einem Stadtteil, die in einem Zeitfenster besonders belebt sind
* `.opencode/skills/oepnvrouten` - sucht  nach einer ÖPNV-Route mit mehreren und unterschiedlichen Verkehrsmitteln, kurzen Umsteigezeiten, ohne Rückkehr an bereits besuchte Haltetellen

# Design der Skills

Sie nutzen API-Zugänge zu Kartendiensten wie OSM/overpass, Echtzeit-Verkehrsdatenquellen via GTFS und andere opendata-Angebote. Da die skills ihre Aufgaben weltweit bewältigen sollen, müssen sie für eine bisher nicht bearbeitete Stadt oder Region zunächst die besten Datenquellen recherchieren (Datenquellen-Scouting).

Die skills sind die zentralen und wichtigsten Teile. Jeder Skill besteht aus einer `SKILL.md`-Datei, die den Skill, seinen Ablauf, seine Ein- und Ausgabe definiert. Daten, die hierfür benötigt werden, wie Formatvorgaben, Regeln, etc. sind in files im Verzeichnis `reference` ausgelagert und werden in der SKILL.md referenziert. Siehe [Claude code Skill Architecture](https://www.mindstudio.ai/blog/claude-code-skills-architecture-skill-md-reference-files)

Die Skills sind als [self-improving skills](https://www.mindstudio.ai/blog/self-improving-ai-skills-claude-code) angelegt. Länder und Städte haben unterschiedliche Datenquellen für Geodaten. Die Zugriffe auf solche Dienste variieren ebenfalls. Solche Erkenntnisse speichert sich der skill am Ende und fragt den Nutzer nach einem feedback.

# Wie nutzt man das Paket?
## Voraussetzungen
1. Linux Rechner am Internet
2. opencode V2 installiert
3. python3 installiert
4. git installiert

## Installation
1. Download mittels `git clone git@github.com:Steffen531/exploreGeoStructures.git`
2. Im obersten Verzeichnis `exploreGeoStructures` ein Python virtual environment mittel `python3 -m venv venv` anlegen

## Erste Schritte
1. `opencode` ausführen
2. Mit `/skills` skills anzeigen: es sollten die oben beschriebenen skills zu sehen sein
3. Eine erste Aufgabe stellen wie z.B. "Suche Behörden in Bochum". Dabei werden vermutlich diverse python packages ins venv installiert.
   
# Beispiele

## Einsame Fußwege in München Giesing
![Fußwege in Giesing](docs/Giesing_Fusswege.jpg)

## Die belebtesten Orte in Potsdam Sonntag abends
![Die belebtesten Orte in Potsdam Sonntag abends](docs/Potsdam_belebtesteOrteSonntagAbends.jpg)

## Behörden, Botschaften & Co. in Leiden (Niederlande)
![Behörden, Botschaften & Co. in Leiden](docs/LeidenErg.jpg)
![Behörden, Botschaften & Co. in Leiden](docs/Leiden.jpg)

## Malls, Bahnhöfe u.ä. in Dresden
![Malls & Co. in Dresden](docs/DresdenMallsEtc.jpg)

## Eine 1-stündige ÖPNV-Rundfahrt am 1.12.26 in Frankfurt a.M. ab 18:00 Uhr
![ÖPNV-Rundfahrt in FFM](docs/ÖPNVFrankfurt.jpg)

# Nächste Schritte
1. Wäre es sinnvoll, spezielle opencode agents zu definieren und zu nutzen? ZB einen agent für datenquellen-scouting, einen agent für python skripts etc.
2. Vorschläge im file `improvements` bewerten und ggf. umsetzen
