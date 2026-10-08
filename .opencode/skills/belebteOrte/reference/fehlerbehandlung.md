# Fehlerbehandlung und Sonderfälle

Kontext für Schritt 8 des `SKILL.md`-Prozesses. Eintragsweise abarbeiten.

| Situation | Vorgehen |
|---|---|
| Kein GTFS-Feed / keine ÖPNV-Daten | OSM POI-Daten als Hauptquelle, ÖPNV als fehlend markieren |
| Schlechte OSM-Abdeckung | Wikidata priorisieren, ggf. manuelle Recherche |
| Nur Stadtteil bekannt | Nominatim-Grenze des Stadtteils holen, dann wie üblich |
| Einzelne Kategorie gesucht | Abfrage auf einen OSM-Filter bzw. eine QID fokussieren |
| Leere Treffer | Regionsfilter (Schritt 3) und Rauschfilter der Stadt-Referenz prüfen; Overpass-Server-Fallback in `reference/datenquellen.md` |
| Viele fremde Treffer | Regionsfilter ist nicht gelaufen oder fehlgeschlagen – erneut anwenden und Ausgeschlossene loggen |
| Google Popular Times nicht verfügbar | Als fehlend markieren, OSM + ÖPNV + Events als Hauptquellen nutzen |
| Keine Event-Daten für Zeitfenster | Als „keine Events bekannt" markieren, POI-Dichte als Proxy nutzen |
| GTFS-Zeitfenster passt nicht | Kalender Tage prüfen (calendar.txt), ggf. benachbarte Zeiten verwenden |

**Immer:** OSM und Wikidata kombinieren und Duplikate bereinigen (beide haben
viele gleiche Einträge); für große Städte zusätzlich `--bbox` begrenzen.
