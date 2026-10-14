# Fehlerbehandlung und Sonderfälle

Kontext für Schritt 7 des `SKILL.md`-Prozesses. Eintragsweise abarbeiten.

| Situation | Vorgehen |
|---|---|
| overpass-api.de nicht erreichbar (Connection refused, beide IPs) | Fallback-Mirrors nutzen (maps.mail.ru, kumi.systems, private.coffee); Hauptserver ist oft nur temporär gebannt |
| HTTP 413 (Request Entity Too Large) | Query-Body zu groß → Bbox statt Stadtgrenze, Filter splitten |
| HTTP 504/500 | Nicht als „leeres Ergebnis" werten – anderen Server versuchen; osmnx 504-Schleife (55 s Pause) durch hartes Zeitlimit abbrechen |
| HTTP 429 (Rate-Limit) | Backoff mit steigender Wartezeit, danach nächster Server |
| 0 Treffer bei autoritativem Server | Nur dann als „wirklich leer" werten; regionale Mirrors (z. B. osm.ch = Schweiz) liefern 0 und sind **nicht** autoritativ |
| Keine Level-Daten im Datensatz | Ebenen-Kriterium weglassen und warnen – nicht stillschweigend |
| Wenige Level-Daten (z. B. 3 %) | Kriterium anwenden, aber in `zusammenfassung.json` ausweisen, wie viele Kandidaten ohne Level-Info fielen |
| `KeyError: index_right` | Spatial Join auf Positions-Spalte `bidx` gruppieren, nicht auf `index_right` |
| GPKG-Cache schlägt fehl (Spaltenname mit Doppelpunkt) | Pickle-Cache verwenden |
| Gebäude ohne Namen | Leerer Name ist erlaubt; in KML/GPX Beschreibung aus Attributen bauen |
| Punkt-Kandidaten (railway=station ohne Polygon) | 60 m Radius statt Polygon-Toleranz |

**Immer:** Ergebnis-Cache (Pickle) nutzen, damit ein Lauf ohne Netz
reproduzierbar ist; verworfene Kandidaten mit Grund in `zusammenfassung.json`
protokollieren.
