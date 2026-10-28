#!/usr/bin/env bash
# exploreGeoStructures – Einmal-Setup
# Prüft die Voraussetzungen, legt .venv an und installiert alle Pakete.
# Aufruf:  ./setup.sh          (Setup)
#          ./setup.sh --tests  (zusätzlich Offline-Tests)
set -euo pipefail

cd "$(dirname "$0")"

RUN_TESTS=false
if [[ "${1:-}" == "--tests" ]]; then
  RUN_TESTS=true
fi

fail() { echo "Fehler: $1" >&2; exit 1; }

echo "==> Prüfe Voraussetzungen"
command -v python3 >/dev/null 2>&1 || fail "python3 ist nicht installiert (Debian/Ubuntu: sudo apt install python3)."
command -v git >/dev/null 2>&1 || fail "git ist nicht installiert (Debian/Ubuntu: sudo apt install git)."
python3 -c "import ensurepip" 2>/dev/null || fail "Das venv-Modul/ensurepip fehlt (Debian/Ubuntu: sudo apt install python3-venv)."
if command -v opencode >/dev/null 2>&1; then
  echo "    opencode gefunden: $(command -v opencode)"
else
  echo "    Hinweis: opencode wurde nicht im PATH gefunden – siehe https://opencode.ai"
fi

if [[ -d .venv ]]; then
  echo "==> .venv existiert bereits"
else
  echo "==> Lege virtuelle Umgebung .venv an"
  python3 -m venv .venv
fi

echo "==> Installiere Python-Pakete (requirements.txt)"
.venv/bin/pip install -r requirements.txt

echo "==> Prüfe Import der Kernpakete"
.venv/bin/python - <<'PY'
import geopandas, numpy, osmnx, pandas, pyproj, requests, shapely
print("    OK:", ", ".join(sorted(["geopandas", "numpy", "osmnx", "pandas", "pyproj", "requests", "shapely"])))
PY

if [[ "$RUN_TESTS" == true ]]; then
  echo "==> Führe Offline-Tests aus"
  .venv/bin/python -m unittest discover -s tests -v
fi

cat <<'EOF'

Setup abgeschlossen. Nächste Schritte:
  1. opencode ausführen
  2. Erste Aufgabe stellen, z. B.:  Suche Behörden in Bochum
  3. Ergebnisse liegen unter results/ – Kartenimport siehe README.md,
     Abschnitt „Ergebnisse auf einer Karte ansehen"

Hinweis: Beim ersten Paketnachschub (.venv/bin/pip install) und beim
Datenquellen-Scouting fragt opencode nach – „Allow always" speichert die
Freigabe dauerhaft (siehe README, Abschnitt „Berechtigungen").
EOF
