# exploreGeoStructures

OpenCode-Skills zum Suchen, Bewerten und Kombinieren räumlicher Strukturen,
Orte und Wege.

## Was ist das – für Einsteiger?

### Was ist opencode?

opencode ist ein KI-Assistent, der direkt auf deinem Rechner arbeitet. Du
startest ihn im **Terminal** – dem Textfenster, in dem man sonst Befehle
eintippt – und schreibst ihm Aufgaben in normaler Sprache, z. B. „Suche
Behörden in Bochum". Der Assistent arbeitet die Aufgabe Schritt für Schritt
ab: Er liest Dateien, ruft Kartendienste im Netz auf, rechnet und legt
Ergebnisse in Ordner ab. Jeder Schritt wird im Fenster sichtbar, und bei
heiklen Aktionen (Pakete installieren, Befehle ausführen) fragt er vorher nach.

Unter der Haube „denkt" ein KI-Sprachmodell – dasselbe Prinzip wie bei einem
Sprachchat im Browser. Der Unterschied: Dieser Assistent redet nicht nur,
sondern tut etwas – Dateien lesen und schreiben, Skripte ausführen,
Kartenexporte anlegen. In diesem Projekt ist ein kostenfreies Modell
voreingestellt (siehe `opencode.jsonc`) – wie du ein anderes Modell wählst,
steht unter „Welches KI-Modell wählen?".

### Was sind Skills und was passiert hier?

**Skills** sind ausführliche Arbeitsanleitungen für Spezialaufgaben, die der
Assistent beherrscht. Dieses Paket enthält Geo-Skills: ruhige Fußwege, belebte
Orte, ÖPNV-Routen, Malls & Bahnhöfe, Behörden – sowie `geo-workflow`, das
mehrere davon zu einer Kette kombiniert. Sagst du „suche Fussweg", übernimmt
der passende Skill wie ein Fachspezialist.

| Begriff | Bild |
|---|---|
| opencode | Der Assistent mit Werkzeugkasten auf deinem Rechner |
| KI-Sprachmodell | Das Denkwerkzeug des Assistenten |
| Skill | Eine geschriebene Arbeitsanleitung für ein Fachgebiet |
| Terminal | Das Textfenster, in dem du mit dem Assistenten sprichst |
| `results/` | Der Ausgangskorb mit den fertigen Karten-Dateien |

Wie du das Paket installierst und die erste Aufgabe stellst, steht unter
„Installation" und „Erste Schritte".

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
1. Linux Rechner am Internet (unter Windows: WSL)
2. opencode V2 installiert
3. python3 installiert (inkl. venv-Modul)
4. git installiert

### Installation

```bash
git clone git@github.com:Steffen531/exploreGeoStructures.git
cd exploreGeoStructures
./setup.sh
```

`setup.sh` prüft die Voraussetzungen, legt das Virtual Environment `.venv` an
und installiert alle benötigten Pakete laut `requirements.txt`. Mit
`./setup.sh --tests` werden zusätzlich die Offline-Tests ausgeführt. Wer es
manuell bevorzugt: `python3 -m venv .venv` und danach
`.venv/bin/pip install -r requirements.txt`.

Alternativ oder nachträglich lässt sich in opencode der Befehl `/setup`
nutzen – er prüft Installation und Pakete und führt die Tests aus.

### Erste Schritte
1. `opencode` ausführen
2. Mit `/skills` skills anzeigen: es sollten die oben beschriebenen skills zu sehen sein
3. Eine erste Aufgabe stellen wie z.B. "Suche Behörden in Bochum"
4. Was dann passiert: Der passende Skill startet, lädt OSM- und Fachdaten,
   schreibt die Ergebnisse nach `results/<region>/` und fragt am Ende nach
   einem kurzen Feedback (Bewertung 1–5). Mit `@skillname …` lässt sich ein
   bestimmter Skill direkt ansprechen, z. B. `@fussweg …`.
5. Ergebnisse visualisieren: siehe „Ergebnisse auf einer Karte ansehen"

### Welches KI-Modell wählen? (kostenlos, ChatGPT, Claude …)

Der Assistent braucht ein KI-Modell als Denkwerkzeug. Drei Dinge sind zu wissen:

- **In diesem Projekt ist ein kostenfreies Modell voreingestellt**
  (`opencode/longcat-2.5-preview-free` in `opencode.jsonc`) – du kannst
  sofort loslegen.
- **opencode bringt eigene kostenlose Modelle mit.** Sie erscheinen in der
  Modellliste automatisch; tauchen sie nicht auf, verbinde einmalig einen
  OpenCode-Account über `/connect`.
- **Kostenpflichtige Anbieter** (ChatGPT/OpenAI, Claude/Anthropic, Gemini und
  viele mehr) bindest du ebenfalls über `/connect` an.

**So wählst du ein Modell:**

1. Im Terminal `/models` eingeben. Die Liste zeigt alle verfügbaren Modelle;
   die Auswahl gilt für die laufende Sitzung.
2. Für kostenpflichtige Modelle zuerst `/connect`: Anbieter auswählen und
   anmelden. Bei ChatGPT genügt „Sign in with ChatGPT" mit einem bestehenden
   Plus-/Pro-Abo – die Nutzung zählt gegen das Abo. Bei Claude verbindest du
   deinen Anthropic-Zugang; die Abrechnung erfolgt nach Tokennutzung. Danach
   erscheinen die neuen Modelle in `/models`.
3. Soll ein Modell dauerhaft gelten, trage es in `opencode.jsonc` unter
   `"model": "anbieter/modell"` ein – so wie die Voreinstellung dort. Ein
   einmal gewähltes Modell pro Sitzung ändert die Datei nicht.

Hinweis: Die Skills funktionieren mit jedem Modell; größere Modelle reagieren
bei kniffligen Regionen und kombinierten Workflows erfahrungsgemäß
zielstrebig.

### Jederzeit unterbrechen und korrigierend eingreifen

Während ein Skill arbeitet, kannst du jederzeit eingreifen: **Esc** unterbricht
den laufenden Schritt sofort. Tippe danach deine Korrektur ein – der Agent
setzt die Aufgabe mit dem bisherigen Stand fort, es muss nichts von vorn
laufen.

Beispiel: Der Skill `oepnvrouten` meldet, er entferne ICE-/RB-/RE-Verbindungen,
weil die Routenprüfung sonst nicht praktikabel ist. Du unterbrichst mit Esc
und antwortest: „Regionalverbindungen (RE u. ä.) sind ausdrücklich erwünscht –
nur ICE weglassen." Der Agent übernimmt die Vorgabe, passt die Filter an und
rechnet weiter. Solche Wünsche kann der Skill auch in seinen Erfahrungsspeicher
(`learnings.md`) aufnehmen und bei künftigen Läufen berücksichtigen.

Wichtig: Vorgaben wie „nur RE/RB, kein ICE" gehören früh in die Aufgabe oder
als sofortige Korrektur. Die Skills entschärfen Regeln bei Engpässen sonst nur
in einer fest definierten Reihenfolge und dürfen sie nicht stillschweigend
aufweichen – eine klare Ansage des Nutzers hat dabei immer Vorrang.

### Berechtigungen: welche Nachfragen erscheinen?

Die Regeln stehen in [`opencode.jsonc`](opencode.jsonc). Skill-Läufe selbst –
Lesen im Projektverzeichnis und Ausführen der Python-Suchskripte – laufen ohne
Nachfrage. Nachgefragt wird nur in diesen Fällen; **Allow always** merkt die
Freigabe dauerhaft für das Projekt, **Allow once** nur für den Einzelfall:

| Nachfrage | Wann? | Empfehlung |
|---|---|---|
| `shell: .venv/bin/pip install …` | fehlende Python-Pakete | Allow always |
| `websearch` / `webfetch` | Scouten neuer Datenquellen (v. a. GTFS in neuen Regionen) | Allow always |
| `shell: <anderer Befehl>` | ungewöhnliche Befehle wie `rm`, `git push` | kurz prüfen → Allow once |
| `execute` (Code Mode) | selten; die Skills benötigen ihn nicht | Allow once |
| `external_directory` | Dateien außerhalb des Projektverzeichnisses | kurz prüfen → Allow once |

„Reject" lehnt nur die anstehende Anfrage ab; die konfigurierten Regeln bleiben
unverändert. Paketinstallationen und ungewöhnliche Befehle bleiben bewusst
hinter einer Nachfrage.

### Ergebnisse auf einer Karte ansehen

Jeder Lauf schreibt nach `results/<region>` bzw. `results/<workflow-id>/`:

- `ergebnis.geojson` (bzw. `routen.geojson`, `kandidaten.geojson`) – empfohlene Datei für den Kartenimport
- `ergebnis.kml` / `routen.kml` – für Google Earth
- `ergebnis.gpx` – für GPS-Geräte
- `zusammenfassung.json` – Statistik und Gründe verworfener Kandidaten

Import auf [umap.openstreetmap.de](https://umap.openstreetmap.de)
(Oberfläche: uMap 3.x):

1. „Erstelle eine Karte" anklicken – der Karten-Editor öffnet sich.
2. In der Symbolleiste am rechten Rand das Symbol „Daten importieren"
   anklicken – der dunkle Pfeil nach oben: ![Import-Symbol](docs/umap-icon-import.svg)
3. Die GeoJSON-Datei in das Import-Feld ziehen oder auswählen (das Format wird
   automatisch erkannt; alternativ eine Datei-URL eintragen).
4. Importmodus „In eine neue Ebene importieren" belassen und „Importieren"
   anklicken – „Daten erfolgreich importiert!" bestätigt den Erfolg.

Alternativen: `.kml` per Drag & Drop in
[Google Earth](https://earth.google.com) ziehen, `.gpx` aufs GPS-Gerät
kopieren oder in einer GPX-App öffnen, `.geojson` direkt in QGIS öffnen.

Bleibt die Karte leer oder unvollständig, liefert `zusammenfassung.json` die
Details (z. B. verworfene Kandidaten mit Grund).

### Kombinierte Workflows

Bei Anfragen mit mehreren voneinander abhängigen Schritten wird
`geo-workflow` verwendet. Der Skill übersetzt die Anfrage in einen
Constraint-Graphen und verbindet normalisierte Kandidaten der Fach-Skills. Er
unterstützt unter anderem räumliche Nähe, Übergänge, Ausschlussbereiche,
Zeitfenster, Dauerbedingungen und geordnete Abfolgen. Die Reihenfolge der
Fach-Skills ist nicht fest codiert.

Beispiel:

```text
@geo-workflow Am 14.12.2026 bin ich ab mittags 12 Uhr in Hamburg. Ich starte meinen Weg am Bahnhof Altona und möchte von dort folgenden workflow: Eine Fahrt mit ÖPNV bis mindestens 13 Uhr. Sie soll an oder in unmittelbarer Nähe einer Mall o.ä. enden. Dort werde ich mich etwa 5 bis 10 Minuten umschauen und danach mit Uber o.ä. weiterfahren. Diese Fahrt soll mindestens 10 Minuten dauern und am Beginn eines Fusswegs enden. Dieser soll etwa 20 Minuten dauern und darf nicht an Behörden und ähnlichen Einrichtungen vorbeiführen.
```

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
3. results/workflow-20261214-hamburg-altona/: Die Kartenvisualisierungen sollen bei oepnvrouten die Linien angeben (zB U5, RE7, ..) und die Umstiegspunkte beschriften. ÖPNV-Fahrten, Fußwege, Malls sollen in unterschiedlichen Farben angezeigt werden. Fußwege sollen als "Fußweg" benannt sein.
4. results/workflow-20261214-hamburg-altona/: Die erste Fahrt führt von Altona nach Elmshorn. Danach geht es aber wieder auf der selben Zugstrecke zurück, wenngleich mit einer anderen Zuglinie. Das ist nicht erwünscht. 
