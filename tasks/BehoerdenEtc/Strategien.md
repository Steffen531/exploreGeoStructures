# Strategien: Karte von Wien mit Behörden, Polizei & Botschaften

## Ziel
Interaktive Karte von Wien mit markierten Einrichtungen:
- Behörden & Regierungsgebäude
- Polizeidienststellen
- Ausländische Botschaften & überstaatliche Einrichtungen

---

## Strategie 1: OpenStreetMap (Overpass API)
| Aspekt | Details |
|--------|---------|
| **Datenquelle** | OpenStreetMap via Overpass API |
| **Relevante Tags** | `amenity=police`, `amenity=embassy`, `office=government`, `building=government` |
| **Vorteile** | Kostenlos, einfache Abfrage, gute Abdeckung für Polizei & Botschaften |
| **Nachteile** | Lückenhaft bei Behörden/Regierungsgebäuden, keine Garantie auf Vollständigkeit |
| **Aufwand** | Niedrig |

## Strategie 2: Offizielle Open Data (Stadt Wien)
| Aspekt | Details |
|--------|---------|
| **Datenquelle** | data.wien.gv.at |
| **Vorteile** | Offizielle, geprüfte Daten; gute Qualität |
| **Nachteile** | Nicht alle Kategorien verfügbar (z.B. Botschaften fehlen) |
| **Aufwand** | Niedrig |

## Strategie 3: Wikidata / Wikipedia
| Aspekt | Details |
|--------|---------|
| **Datenquelle** | Wikidata via SPARQL |
| **Vorteile** | Strukturierte Daten, gut für Botschaften & internationale Einrichtungen |
| **Nachteile** | Komplexere Abfrage, Vollständigkeit variiert |
| **Aufwand** | Mittel |

## Strategie 4: Kombination mehrerer Quellen
| Aspekt | Details |
|--------|---------|
| **Datenquelle** | OSM + Open Data Wien + Wikidata |
| **Vorteile** | Beste Abdeckung, hohe Vollständigkeit |
| **Nachteile** | Aufwändig, Duplikatbereinigung nötig |
| **Aufwand** | Hoch |

---

## Visualisierung
- **Folium** – interaktive Leaflet-Karten (empfohlen, einfach)
- **Plotly** – interaktive Karten mit Dashboards
- **Matplotlib + Geopandas** – statische Karten

---

## Empfehlung
**Strategie 4 (Kombination)** für beste Ergebnisse, startend mit Strategie 1 (OSM) als Basis und Ergänzung durch Strategie 2 & 3.
