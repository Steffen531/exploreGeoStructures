# Fehlerbehandlung und Sonderfälle

Kontext für Schritt 8 des `SKILL.md`-Prozesses. Eintragsweise abarbeiten.

| Situation | Vorgehen |
|---|---|
| Kein Register / kein Open Data | OSM + Wikidata als Hauptquellen |
| Schlechte OSM-Abdeckung | Wikidata priorisieren, ggf. manuelle Recherche |
| Nur Stadtteil bekannt | Nominatim-Grenze des Stadtteils holen, dann wie üblich |
| Einzelne Kategorie gesucht | Abfrage auf einen OSM-Filter bzw. eine QID fokussieren |
| Leere Treffer | Regionsfilter (Schritt 3) und Rauschfilter der Landes-Referenz prüfen; Overpass-Server-Fallback in `reference/datenquellen.md` |
| Viele fremde Treffer | Regionsfilter ist nicht gelaufen oder fehlgeschlagen – erneut anwenden und Ausgeschlossene loggen |
| Botschaften = 0 | In vielen Städten erwartet → direkt kommunizieren, nicht als Fehler erklären |

**Immer:** OSM und Wikidata kombinieren und Duplikate bereinigen (beide haben
viele gleiche Einträge); für große Städte zusätzlich `--bbox` begrenzen.
