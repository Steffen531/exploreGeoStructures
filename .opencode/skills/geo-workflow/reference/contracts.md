# Verträge des Geo-Workflows

## Workflow

Ein Workflow enthält eine Region, Knoten, Constraints und Ausführungslimits.
Knoten benennen eine Capability und den produzierenden Skill. Beziehungen
zwischen Knoten stehen ausschließlich in `constraints`.

## Kandidaten

Kandidaten sind GeoJSON-Features. GeoJSON verwendet immer `[Längengrad,
Breitengrad]`. Pflichtfelder sind `candidate_id`, `producer_skill`,
`entity_type`, `temporal`, `score`, `confidence`, `sources` und `warnings`.

Linien besitzen zusätzlich `start` und `end` als `{lat, lon}`. Die Orientierung
der Liniengeometrie muss dazu passen. Zeiten sind ISO-8601-Werte mit Zeitzone.
Unbekannte Werte werden als `null` ausgegeben.

## Constraints

Räumlich: `near`, `within`, `intersects`, `starts_near`, `ends_near`,
`starts_at`, `ends_at`, `passes_through`, `avoids`, `sequence_continuity`.

Zeitlich: `starts_between`, `ends_between`, `duration_between`, `before`,
`after`, `overlaps`, `gap_between`, `active_at`, `sequence_time`.

Jeder Constraint ist hart oder weich. Eine harte Verletzung verwirft die
Kombination. Eine weiche Verletzung reduziert den Score und bleibt mit Grund
sichtbar. Entfernungen werden metrisch berechnet.

Knoten wählen standardmäßig einen Kandidaten (`selection: one`). Mengenfilter
wie „alle Behörden vermeiden“ müssen `selection: all` verwenden. Der Planner
fasst dann sämtliche Kandidatengeometrien zu einer geprüften Menge zusammen.

## Status

- `success`: verwertbare Kandidaten
- `empty`: erfolgreiche Suche ohne Kandidaten
- `degraded`: Kandidaten nur mit dokumentiertem Fallback
- `error`: Ausführung oder Quelle fehlgeschlagen

## Ride-Hailing

Nur eine Providerquelle darf einen konkreten Anbieter und Verfügbarkeit
bestätigen. Straßenrouting ohne Providerquelle erhält den Typ
`estimated_ride_hailing`; Luftlinien sind keine reale Route.
