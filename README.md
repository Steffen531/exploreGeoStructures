# exploreGeoStructures
Ein KI Assistent, der nach besonderen geographischen Strukturen und Bewegungsmustern sucht, die sich für Spiele wie Schnitzeljagd gut eignen.

# Projekt

* `tasks` - Hier untersuchen wir neue tasks, entwickeln und verbessern die Strategie. Wenn ein akzaptables Einstiegsniveau erreicht ist, wird ein skill erzeugt.
* `tasks/Fussweg` - Sucht nach einem Fußweg, der spezielle Anforderungen erfüllt
* `tasks/belebteOrte` - sucht nach Orten in einer Stadt, die an gewissen Tagen/Stunden besonders belebt sind
* `tasks/ÖPNVRundfahrt` - stellt eine Reise als Abfolge von öffentlichen Verkehrsmitteln zusammen, die gewisse Anforderungen erfüllt. Das Ergebnis wird in einer Karte dargestellt.
* `AGENTS.md` - zentrale Anweisungen (Nutzung python venv, Visualisierung auf Karten mittel kml-files für openstreetmap, ...)
* `.opencode/skills` - hier sind skills definiert, die einen gewissen Reifegrad haben. Mit "/skillis" kann man sie in opencode auflisten
und mit "@" einen einzelnen Skill benutzen
* `.opencode/skills/behoerdenetc` - sucht nach Behörden, Botschaften etc. in einer Stadt oder einem Stadtteil

# Design der Skills

Die skills sind die zentralen und wichtigsten Teile. Jeder Skill besteht aus einer `SKILL.md`-Datei, die den Skill, seinen Ablauf, seine Ein- und Ausgabe definiert. Daten, die hierfür benötigt werden, wie Formatvorgaben, Regeln, etc. sind in files im Verzeichnis `references` ausgelagert und werden in der SKILL.md referenziert. Siehe [Claude code Skill Architecture](https://www.mindstudio.ai/blog/claude-code-skills-architecture-skill-md-reference-files)

Die Skills sind als [self-improving skills](https://www.mindstudio.ai/blog/self-improving-ai-skills-claude-code) angelegt. Länder und Städte haben unterschiedliche Datenquellen für Geodaten. Die Zugriffe auf solche Dienste variieren ebenfalls. Solche Erkenntnisse speichert sich der skill am Ende und fragt den Nutzer nach einem feedback.

# Beispiele

## Ein einsamer Fußweg in Hamburg
![Ein einsamer Fußweg in Hamburg](docs/Fussweg2.jpg)

## Die belebtesten Orte im Bezirk Pankow dienstag vormittags
![Die belebtesten Orte im Bezirk Pankow dienstag vormittags](docs/Ergebnis.jpg)

## Behörden, Botschaften & Co. in Leiden (Niederlande)
![Behörden, Botschaften & Co. in Leiden](docs/LeidenErg.jpg)
![Behörden, Botschaften & Co. in Leiden](docs/Leiden.jpg)


# Nächste Schritte
1. Die SKILL.md soll nur den Prozess enthalten. Alles andere wird in Referenzen ausgelagert (dir references).
2. Wir brauchen ´self improving´ skills, die ihre Erfahrungen für die Zukunft speichern. Wenn also der Behörden-skill gelernt hat,
wie er in den Niederlanden an opendata kommt, dann sollte er das für zukünftige Anfragen speichern. --> https://www.mindstudio.ai/blog/self-improving-ai-skills-claude-code
