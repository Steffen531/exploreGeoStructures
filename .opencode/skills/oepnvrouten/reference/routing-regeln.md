# Routing-Regeln und Constraints

Kontext für Schritt 5 des `SKILL.md`-Prozesses. Alle Constraints sind
**Ausschlusskriterien** – nicht erfüllt = Route verwerfen und in
`zusammenfassung.json` mit Grund protokollieren.

## Strikte Constraints (immer aktiv)

### 1. Keine Station zweimal

Jede Station darf in einer Route nur einmal vorkommen. Keine Rundtouren,
keine Rückkehr zu bereits besuchten Haltestellen.

### 2. Kein Straßenabschnitt zweimal

Jede Kante (Verbindung zwischen zwei Stationen) darf nur einmal verwendet
werden. Kein Zurücklaufen auf derselben Strecke.

### 3. Start ≠ Ende

Die Route darf nicht am Startpunkt enden. Ausnahme: Der Nutzer wählt
explizit denselben Start-End-Punkt (muss im Skill-Log vermerkt werden).

### 4. Keine Zwischenstopps

Nur Start, Umstiege und Ende sind erlaubt. Keine „Sightseeing-Pausen"
oder festgelegten Stopps auf der Strecke.

### 5. Alle Abfahrtszeiten >= aktuelles Datum+Uhrzeit

Die Route muss mit dem konfigurierten Datum und der Uhrzeit starten
und im Rahmen des Dauer-Fensters bleiben.

## Optimierungsziele (priorisiert)

| Priorität | Ziel | Umsetzung |
|-----------|------|-----------|
| 1 | Kurze Umstiegszeiten | Gewicht `w1` in Kostenfunktion |
| 2 | Strikte Keine-Wiederholungen | Harte Constraints (siehe oben) |
| 3 | Störungen/Absagen berücksichtigen | Echtzeit-Daten, Alternativen suchen |
| 4 | Einhaltung der Dauer | Harte Constraints (Dauer-Fenster) |
| 5 | Einhaltung der Umstiegsanzahl | Harte Constraints (min/max) |

## Kostenfunktion

```
Cost = w1 * (Fußwegzeit) + w2 * (Wartezeit) + w3 * (Constraint-Strafen)
```

Standard-Gewichte:
- `w1 = 2.0` (Fußgewege priorisieren)
- `w2 = 2.0` (Wartezeiten priorisieren)
- `w3 = 1.0` (Constraint-Strafen für Verkehrsmittel-Typen)

## Verkehrsmittel-Prioritäten

| Verkehrsmittel | Priorität | Begründung |
|----------------|-----------|------------|
| Regionalzug | 1 | Schnellste, wenige Halte |
| S-Bahn | 2 | Schnell, eigenes Gleis |
| U-Bahn | 2 | Schnell, unterirdisch |
| Straßenbahn | 3 | Mittel, oft eigenes Gleisbett |
| Fähre | 4 | Landschaftlich, aber langsam |
| Ride-Hailing | 5 | Dynamisch, aber teuer |
| Fußweg | 5 | Nur für Umstiege |
| Bus | 6 | Langsam, Straßenverkehr |

## Diversitäts-Regeln

- **3 Routen-Vorschläge:** Der Algorithmus sucht 3 verschiedene Routen.
- **Diversitäts-Bonus:** Stationen, die noch nicht in früheren Routen
  vorkamen, erhalten einen Bonus von +5.
- **Mindestens 2 neue Stationen:** Jede neue Route muss mindestens
  2 Stationen enthalten, die noch nicht in den vorherigen Routen waren.

## Score-Berechnung

```
Score = 2.0 * (Fußweggesamt) + 2.0 * (Wartezeitgesamt) + 1.0 * (Umstiegsanzahl)
      + Σ Verkehrsmittel-Priorität
```

Niedriger Score = bessere Route. Der Score wird in `zusammenfassung.json`
für jeden Routen-Vorschlag angegeben.
