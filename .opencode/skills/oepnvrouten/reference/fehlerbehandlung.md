# Fehlerbehandlung

Kontext für Schritt 7 des `SKILL.md`-Prozesses. Edge Cases und Sonderfälle.

## Keine Routen gefunden

**Ursache:** Constraints zu strikt, Ziel nicht erreichbar, oder Dauer-Fenster
zu eng.

**Lösung (in dieser Reihenfolge):**

1. **Dauer ±10 % erweitern** (`--dauer-min` / `--dauer-max`).
2. **Umstiegs-Max +2** (z. B. von 5 auf 7).
3. **Ride-Hailing als Brücke erlauben** (fehlende ÖPNV-Verbindungen
   über Uber/Bolt/Free Now etc. ergänzen).
4. **Nur-Stationen-Constraint lockern** (Straßenabschnitt-Constraint
   aufheben, nur Stationen-Eindeutigkeit beibehalten).

**Niemals** die Keine-Wiederholungs-Constraint vollständig aufheben.

## GTFS-Feed nicht verfügbar

**Lösung:**
- Auf Overpass API zurücksetzen (kein Fahrplan, Routing mit Annäherungen).
- OTP-Instanz als Alternative prüfen.
- Lokale Verkehrsbetreiber kontaktieren.

## Startpunkt oder Endpunkt unbekannt

**Lösung:**
- Nominatim-Geocoding (`reference/datenquellen.md` §Nominatim) anwenden.
- Falls mehrere Treffer: Nutzer mit `question`-Tool nach dem korrekten
  Ort fragen.
- BBox um den gefundenen Ort legen (±0.01°).

## Überpass API nicht erreichbar

**Lösung:**
- Fallback-Server verwenden (`reference/datenquellen.md` §Overpass).
- Rate-Limit (429): Backoff mit steigender Wartezeit.
- Bei persistentem Fehler: Auf GTFS/OTP-Daten zurück Fahren.

## Ziel nicht erreichbar

**Lösung:**
- BFS-Prüfung (`_bfs_erreichbar`) durchführen.
- Falls nicht erreichbar: Nutzer informieren, Alternativen vorschlagen
  (anderer Start-/Endpunkt, Ride-Hailing).

## Unbekannte Region

**Lösung:**
- Nominatim mit `accept-language` und `polygon_geojson=1` abfragen.
- Nutzer um präzisere Region bitten (Stadtteil, Postleitzahl, Adresse).
- BBox manuell definieren (--bbox Parameter).

## Dauer zu kurz

**Ursache:** Mindestdauer kleiner als kürzeste mögliche Route.

**Lösung:**
- `--dauer-min` auf 0 oder einen kleineren Wert setzen.
- Nutzer über die minimale mögliche Dauer informieren.

## Dauer zu lang

**Ursache:** Maximaldauer größer als längste sinnvolle Route.

**Lösung:**
- `--dauer-max` auf einen realistischen Wert setzen (z. B. 180 min).
- Nutzer über die maximale sinnvolle Dauer informieren.

## Ride-Hailing nicht verfügbar

**Lösung:**
- Auf ÖPNV-Verbindungen zurückgreifen.
- Nutzer über fehlende Ride-Hailing-Optionen informieren.
- Straßenabschnitt-Constraint lockern, um Umwege zu erlauben.

## Keine Verkehrsdaten verfügbar

**Ursache:** Keine OSM-Daten, kein GTFS-Feed, keine OTP-Instanz.

**Lösung:**
- Nutzer über fehlende Daten informieren.
- Manuelle Routing-Planung vorschlagen.
- Datenquellen-Scout erneut durchführen (`reference/datenquellen.md`).
