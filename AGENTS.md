# Projekt-Anweisungen

## Python Virtual Environment

Dieses Projekt verwendet ein Python Virtual Environment unter `.venv`.

### Python-Interpreter
- **Pfad:** `.venv/bin/python`
- **Verwendung:** `.venv/bin/python <script.py>`

### Paket-Installation
- **Befehl:** `.venv/bin/pip install <paket>`
- **Beispiel:** `.venv/bin/pip install osmnx geopandas shapely`

### Wichtige Hinweise
- Verwende immer `.venv/bin/python` statt `python3` für Skripte
- Installiere neue Pakete mit `.venv/bin/pip`
- Das venv ist im Projektverzeichnis `.venv/` enthalten

## Projekt-Struktur

```
exploreGeoStructures/
├── .venv/                  # Python Virtual Environment
├── AGENTS.md               # Diese Datei
├── opencode.jsonc          # OpenCode-Konfiguration
├── Beispiele               # Suchbeispiele
├── Strategie.md            # Strategie-Zusammenfassung
└── tasks/
    └── Fussweg/
        └── Strategie1/     # Strategie 1: Fußweg-Suche
```

## Arbeitsweise

1. **Python-Skripte** immer mit `.venv/bin/python` ausführen
2. **Neue Pakete** mit `.venv/bin/pip install` hinzufügen
3. **Ergebnisse** in den jeweiligen Task-Verzeichnissen speichern
