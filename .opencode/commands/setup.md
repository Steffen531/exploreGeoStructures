---
description: Projekt-Setup prüfen und vervollständigen (venv, Pakete, Tests)
agent: build
---

Führe das Projekt-Setup für exploreGeoStructures durch und berichte kurz und einsteigerfreundlich:

1. Prüfe die Voraussetzungen: `python3`, `git` und – nur als Hinweis – `opencode` im PATH.
2. Führe `bash setup.sh --tests` aus. Das Skript legt bei Bedarf `.venv` an, installiert alle Pakete laut `requirements.txt`, prüft die Kernpakete und startet die Offline-Tests. Wiederhole seine Schritte nur einzeln, wenn es selbst fehlschlägt, und nenne dann die genaue Ursache.
3. Fasse am Ende zusammen:
   - Was ist erledigt? Welche Pakete fehlten und wurden nachinstalliert?
   - Falls `pip install` nachgefragt hat: erkläre, dass **Allow always** diese Freigabe dauerhaft für das Projekt speichert (Regeln in `opencode.jsonc`).
   - Nächste Schritte: erste Aufgabe stellen, z. B. „Suche Behörden in Bochum" – oder `@geo-workflow` für kombinierte Anfragen.
   - Ergebnisse liegen unter `results/…`; der Kartenimport ist im README unter „Ergebnisse auf einer Karte ansehen" beschrieben.

Wenn alles bereits installiert ist und die Tests grün sind, bestätige das kurz – starte keine Installationen erneut.
