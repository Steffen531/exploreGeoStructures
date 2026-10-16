# Routing-Regeln und Constraints

Kontext für Schritt 5 des `SKILL.md`-Prozesses. Alle Constraints sind
**Ausschlusskriterien** – nicht erfüllt = Route verwerfen und in
`zusammenfassung.json` mit Grund protokollieren.

## Strikte Constraints (immer aktiv)

### 1. Keine Station zweimal

Jede Station darf in einer Route nur einmal vorkommen. Keine Rundtouren,
keine Rückkehr zu bereits besuchten Haltestellen.

### 2. Kein Straßenabschnitt zweimal

Jede Kante (Verbindung zwischen Stationen) darf nur einmal verwendet
werden. Kein Zurücklaufen auf derselben Strecke.

### 3. Start ≠ Ende

Die Route darf nicht am Startpunkt enden. Ausnahme: Der Nutzer wählt
explizit denselben Start-End-Punkt (muss im Skill-Log vermerkt werden).

### 4. Keine Zwischenstopps

Nur Start, Umstiege und Ende sind erlaubt.

### 5. Alle Abfahrtszeiten >= Nutzer-Datum + Nutzer-Uhrzeit

Die Route muss innerhalb des vom Nutzer vorgegebenen Zeitfensters liegen.
Die Dauer ist ein **hartes Filter**, kein Ranking-Kriterium.

## Optimierungsziele (Ranking, priorisiert)

| Priorität | Ziel | Umsetzung |
|-----------|------|-----------|
| 1 | Kurze Umstiegszeiten | Gewicht `w1` in Score |
| 2 | Schienenverkehr bevorzugt | Straßenbahn/U-Bahn/S-Bahn/Regionalzug besser als Bus |
| 3 | Vielfalt der Verkehrsmittel | Routen mit unterschiedlichen Verkehrsmitteln bevorzugen |

Nicht Ranking-Kriterien (harte Filter): Dauer, Geschwindigkeit, Kosten.

## Kostenfunktion

```
Score = w1 * (Fußwegzeit + Wartezeit) + w2 * Σ Verkehrsmittel-Priorität
```

- `w1 = 2.0` – Umstiegszeiten stark bestrafen
- `w2 = 1.0` – Schienenverkehr bevorzugen

## Verkehrsmittel-Prioritäten (niedriger = besser)

| Verkehrsmittel | Priorität | Begründung |
|----------------|-----------|------------|
| Straßenbahn | 1 | Schienen, oft eigenes Gleisbett |
| Regionalzug | 1 | Schienen, wenige Halte |
| U-Bahn | 1 | Schienen, schnell |
| S-Bahn | 1 | Schienen, schnell |
| Fähre | 2 | Wasserweg, landschaftlich |
| Ride-Hailing | 3 | Flexibel, aber teuer/unkontrollierbar |
| Bus | 4 | Straßenverkehr, langsam |
| Fußweg | 5 | Nur für Umstiege |

Schienengebundene Verkehrsmittel erhalten die beste Priorität (1),
Buse die schlechteste (4). Straßenbahnschienen zählen als Schienenverkehr.

## Diversitäts-Regeln

- **Erst sammeln, dann rangieren:** Der Algorithmus findet ALLE Routen
  innerhalb der harten Constraints, sortiert sie nach Score und gibt die
  Top 3 zurück. Nicht die ersten 3 gefundenen Routen.
- **Kanten-Ausschluss pro Runde (bewährt):** Ein deterministischer DFS liefert
  sonst 3× dieselbe Route. Stattdessen sperrt jede Runde die Kanten der
  bereits gewählten Route – so werden die 3 Vorschläge garantiert unterschiedlich
  (Berlin 16.10.2026: 3 Routen mit 66/76/110 Min statt 3× 107 Min).
- **Schienenverkehr zuerst:** Bei Kanten mit mehreren Linien die Nachbarn nach
  Modus-Priorität sortieren, damit die bessere Linie gewählt wird.
- **Mindestens 2 neue Stationen:** Jede neue Route sollte Stationen enthalten,
  die noch nicht in den vorherigen Routen vorkamen (Ziel, nicht Garantie).

## Score-Berechnung

```
Score = 2.0 * (Fußweggesamt + Wartezeitgesamt) + 1.0 * Σ Verkehrsmittel-Priorität
```

Niedriger Score = bessere Route.
