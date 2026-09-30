"""
Schritt 2: Route entlang der Achsen planen
Strategie 1: Achsen-Strategie + Zeitliche Optimierung

Hinweg: West-Ost-Achse (S-Bahn)
Rückweg: Nord-Sud-Achse (Straßenbahn)
Ziel: Start und Endpunkt weit voneinander entfernt
"""

import json
import math
from datetime import datetime, timedelta

OUTPUT_DIR = "tasks/ÖPNVRundfahrt/Strategie1"

print("=== Schritt 2: Route entlang der Achsen planen ===")
print(f"Zeit: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Lade ÖPNV-Daten
with open(f"{OUTPUT_DIR}/frankfurt_opnv_raw.geojson", "r", encoding="utf-8") as f:
    opnv_data = json.load(f)

print(f"Geladene Linien: {len(opnv_data['features'])}")

# Wichtige Stationen in Frankfurt mit Koordinaten
stationen = {
    "Frankfurt Hbf": {"lat": 50.11, "lon": 8.68, "type": "Hauptbahnhof"},
    "Frankfurt Süd": {"lat": 50.09, "lon": 8.68, "type": "Bahnhof"},
    "Frankfurt Ost": {"lat": 50.12, "lon": 8.72, "type": "Bahnhof"},
    "Frankfurt West": {"lat": 50.11, "lon": 8.64, "type": "Bahnhof"},
    "Frankfurt Nord": {"lat": 50.13, "lon": 8.68, "type": "Bahnhof"},
    "Frankfurt Hauptwache": {"lat": 50.11, "lon": 8.68, "type": "U-Bahnhof"},
    "Frankfurt Konstablerwache": {"lat": 50.11, "lon": 8.69, "type": "U-Bahnhof"},
    "Frankfurt Alte Oper": {"lat": 50.11, "lon": 8.67, "type": "U-Bahnhof"},
    "Frankfurt Bockenheimer Warte": {"lat": 50.12, "lon": 8.66, "type": "U-Bahnhof"},
    "Frankfurt Eschenheimer Tor": {"lat": 50.12, "lon": 8.68, "type": "U-Bahnhof"},
    "Frankfurt Friedberger Tor": {"lat": 50.12, "lon": 8.70, "type": "U-Bahnhof"},
    "Frankfurt Ostbahnhof": {"lat": 50.12, "lon": 8.72, "type": "Bahnhof"},
    "Frankfurt Lokalbahnhof": {"lat": 50.10, "lon": 8.69, "type": "Bahnhof"},
    "Frankfurt Südbahnhof": {"lat": 50.09, "lon": 8.68, "type": "Bahnhof"},
    "Frankfurt Westbahnhof": {"lat": 50.11, "lon": 8.64, "type": "Bahnhof"},
    "Frankfurt Nordbahnhof": {"lat": 50.13, "lon": 8.68, "type": "Bahnhof"},
    "Frankfurt Galluswarte": {"lat": 50.10, "lon": 8.66, "type": "Bahnhof"},
    "Frankfurt Messe": {"lat": 50.11, "lon": 8.65, "type": "Bahnhof"},
    "Frankfurt Festhalle": {"lat": 50.11, "lon": 8.65, "type": "Bahnhof"},
    "Frankfurt Rebstockbad": {"lat": 50.10, "lon": 8.67, "type": "Straßenbahnhaltestelle"},
    "Frankfurt Schwanheim": {"lat": 50.08, "lon": 8.65, "type": "Straßenbahnhaltestelle"},
    "Frankfurt Heddernheim": {"lat": 50.13, "lon": 8.66, "type": "Straßenbahnhaltestelle"},
    "Frankfurt Ginnheim": {"lat": 50.13, "lon": 8.68, "type": "Straßenbahnhaltestelle"},
    "Frankfurt Seckbach": {"lat": 50.13, "lon": 8.70, "type": "Straßenbahnhaltestelle"},
    "Frankfurt Mühlburg": {"lat": 50.12, "lon": 8.66, "type": "Straßenbahnhaltestelle"},
    "Frankfurt Preungesheim": {"lat": 50.13, "lon": 8.69, "type": "U-Bahnhof"},
    "Frankfurt Hausen": {"lat": 50.12, "lon": 8.67, "type": "U-Bahnhof"},
    "Frankfurt Heerstraße": {"lat": 50.12, "lon": 8.66, "type": "U-Bahnhof"},
    "Frankfurt Riedberg": {"lat": 50.14, "lon": 8.68, "type": "U-Bahnhof"},
    "Frankfurt Hohemark": {"lat": 50.14, "lon": 8.67, "type": "U-Bahnhof"},
    "Frankfurt Höchst": {"lat": 50.10, "lon": 8.65, "type": "Bahnhof"},
}

# Route entlang der Achsen planen
# Hinweg: West-Ost-Achse (S-Bahn S8/S9)
# Rückweg: Nord-Sud-Achse (Straßenbahn 11/12)

print("\n=== Route entlang der Achsen planen ===")

# Startpunkt: Frankfurt Hbf (zentral)
start = "Frankfurt Hbf"
print(f"Startpunkt: {start}")

# Hinweg: West-Ost-Achse (S-Bahn S8/S9)
# Frankfurt Hbf -> Frankfurt Ost
hinweg = {
    "name": "Hinweg (West-Ost-Achse)",
    "verkehrsmittel": "S-Bahn S8/S9",
    "von": "Frankfurt Hbf",
    "nach": "Frankfurt Ost",
    "dauer": 20,  # Minuten
    "farbe": "#009933",
    "stationen": ["Frankfurt Hbf", "Frankfurt Konstablerwache", "Frankfurt Ostbahnhof"],
    "coords": [[8.68, 50.11], [8.69, 50.11], [8.72, 50.12]],
}

print(f"\nHinweg: {hinweg['name']}")
print(f"  Verkehrsmittel: {hinweg['verkehrsmittel']}")
print(f"  Von: {hinweg['von']} -> Nach: {hinweg['nach']}")
print(f"  Dauer: {hinweg['dauer']} Minuten")
print(f"  Stationen: {', '.join(hinweg['stationen'])}")

# Umstieg in Frankfurt Ost
umstieg = {
    "ort": "Frankfurt Ost",
    "wartezeit": 5,  # Minuten
    "beschreibung": "Umstieg von S-Bahn auf Straßenbahn",
}

print(f"\nUmstieg: {umstieg['ort']}")
print(f"  Wartezeit: {umstieg['wartezeit']} Minuten")
print(f"  Beschreibung: {umstieg['beschreibung']}")

# Rückweg: Nord-Sud-Achse (Straßenbahn 11/12)
# Frankfurt Ost -> Frankfurt Süd
rueckweg = {
    "name": "Rückweg (Nord-Sud-Achse)",
    "verkehrsmittel": "Straßenbahn 11/12",
    "von": "Frankfurt Ost",
    "nach": "Frankfurt Süd",
    "dauer": 35,  # Minuten
    "farbe": "#FF6600",
    "stationen": ["Frankfurt Ost", "Frankfurt Konstablerwache", "Frankfurt Lokalbahnhof", "Frankfurt Südbahnhof"],
    "coords": [[8.72, 50.12], [8.69, 50.11], [8.69, 50.10], [8.68, 50.09]],
}

print(f"\nRückweg: {rueckweg['name']}")
print(f"  Verkehrsmittel: {rueckweg['verkehrsmittel']}")
print(f"  Von: {rueckweg['von']} -> Nach: {rueckweg['nach']}")
print(f"  Dauer: {rueckweg['dauer']} Minuten")
print(f"  Stationen: {', '.join(rueckweg['stationen'])}")

# Erweiterung: Fähre über den Main
faehre = {
    "name": "Fähre über den Main",
    "verkehrsmittel": "Fähre",
    "von": "Frankfurt Süd",
    "nach": "Frankfurt Höchst",
    "dauer": 30,  # Minuten
    "farbe": "#0099FF",
    "stationen": ["Frankfurt Süd", "Frankfurt Höchst"],
    "coords": [[8.68, 50.09], [8.65, 50.10]],
}

print(f"\nErweiterung: {faehre['name']}")
print(f"  Verkehrsmittel: {faehre['verkehrsmittel']}")
print(f"  Von: {faehre['von']} -> Nach: {faehre['nach']}")
print(f"  Dauer: {faehre['dauer']} Minuten")
print(f"  Stationen: {', '.join(faehre['stationen'])}")

# Gesamtdauer berechnen
gesamt_dauer = hinweg["dauer"] + umstieg["wartezeit"] + rueckweg["dauer"] + faehre["dauer"]
print(f"\nGesamtdauer: {gesamt_dauer} Minuten ({gesamt_dauer // 60} Stunden {gesamt_dauer % 60} Minuten)")

# Route speichern
route = {
    "name": "ÖPNV-Rundfahrt Frankfurt (Strategie 1)",
    "datum": "2026-12-01",
    "zeit": "18:00-20:00",
    "start": start,
    "endpunkt": "Frankfurt Höchst",
    "gesamt_dauer": gesamt_dauer,
    "hinweg": hinweg,
    "umstieg": umstieg,
    "rueckweg": rueckweg,
    "erweiterung": faehre,
    "verkehrsmittel": ["S-Bahn", "Straßenbahn", "Fähre"],
    "stationen": list(set(hinweg["stationen"] + rueckweg["stationen"] + faehre["stationen"])),
}

output_file = f"{OUTPUT_DIR}/route_plan.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(route, f, indent=2, ensure_ascii=False)

print(f"\nRoute gespeichert: {output_file}")

# Zusammenfassung speichern
summary = {
    "zeitstempel": datetime.now().isoformat(),
    "start": start,
    "endpunkt": "Frankfurt Höchst",
    "gesamt_dauer": gesamt_dauer,
    "verkehrsmittel": ["S-Bahn", "Straßenbahn", "Fähre"],
    "stationen": route["stationen"],
    "hinweg": hinweg["name"],
    "rueckweg": rueckweg["name"],
    "erweiterung": faehre["name"],
}

with open(f"{OUTPUT_DIR}/schritt2_zusammenfassung.json", "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)

print(f"Zusammenfassung gespeichert: {OUTPUT_DIR}/schritt2_zusammenfassung.json")
print("\n=== Schritt 2 abgeschlossen ===")
