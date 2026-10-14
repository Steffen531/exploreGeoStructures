# Learnings: mallsetc

Erfahrungsspeicher des Skills. **Vor dem Lauf lesen** (`SKILL.md` Schritt 1),
**nach dem Lauf ergänzen** (`SKILL.md` Schritt 8: Rating 1–5 + Hinweise des
Nutzers).

Pflegen:

- Einträge kurz halten: 1–3 Sätze je Beobachtung, mit Region und Datum.
- Nur handlungsrelevante Beobachtungen aufnehmen: funktionierende
  Server/Filter, Overpass-Spezialitäten (Fehlercodes, Limits, IP-Bans),
  Schwellen, die sich bewährt haben, Datenqualität (Level-Tags).
- Bei ~20 Einträgen aufräumen: Doppeltes verschmelzen, Veraltetes löschen,
  nach Themen sortieren.

## Was gut lief

- Dresden (11.10.2026): Overpass-Fallback (maps.mail.ru, kumi.systems) mit
  Backoff + hartem 120-s-Zeitlimit war robust – alle 3 Datensätze (Gebäude,
  ÖPNV, Eingänge) trotz ConnectionError/504/413 beantwortet.
- Dresden (11.10.2026): Bbox-Query statt Stadtgrenze (`features_from_bbox`) –
  Query-Body ~3 KB statt 2,5 MB, dadurch auch Mirrors mit kleinem
  Body-Limit erreichbar.
- Dresden (11.10.2026): Pickle-Cache für Rohdaten – Reruns komplett ohne
  Netz; GPKG-Cache scheitert an Doppelpunkt in Spaltennamen (`ref:vvo`).

## Was nicht lief

- Dresden (11.10.2026): overpass-api.de hat nach Verbindungsflut die eigene
  IP gebannt (beide A-Records, Port 443+80, auch curl → 000) – Hauptserver
  für Stunden unbrauchbar, Fallback-Mirrors zwingend.
- Dresden (11.10.2026): osmnx pinnat per `_config_dns` eine feste IP – bei
  toten A-Records scheitern alle Abfragen mit „Connection refused"; Pinning
  abschalten (`ox_http._config_dns = lambda url: None`).
- Dresden (11.10.2026): Nur 974 von 29614 Eingängen (3,3 %) tragen ein
  `level`-Tag → Ebenen-Kriterium (≥2 verschiedene Ebenen) sortiert 105 von
  133 sonstigen Kandidaten aus; bei 0 Level-Daten im Datensatz das Kriterium
  weglassen und warnen, nicht stillschweigend.
- Dresden (11.10.2026): `gpd.sjoin` benennt die rechte Index-Spalte nach den
  Index-Namen – bei benanntem MultiIndex existiert `index_right` nicht
  (KeyError); eigene Positions-Spalte `bidx` verwenden.

## Offene Fragen

- Dresden (11.10.2026): Soll das Ebenen-Kriterium bei fehlenden Level-Daten
  durch `building:levels` ≥ 2 ersetzt werden (Indiz für mehrstöckige
  Eingangssituationen)?
