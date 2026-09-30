"""
Schritt 6: Finale Zusammenfassung und Karte
Erstellt eine Zusammenfassung aller Ergebnisse und eine HTML-Karte.
"""

import json
from datetime import datetime

OUTPUT_DIR = "tasks/Fussweg/Strategie1"

print("=== Schritt 6: Finale Zusammenfassung ===")
print(f"Zeit: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Alle Zwischenergebnisse laden
with open(f"{OUTPUT_DIR}/schritt1_zusammenfassung.json", "r", encoding="utf-8") as f:
    schritt1 = json.load(f)

with open(f"{OUTPUT_DIR}/schritt2_zusammenfassung.json", "r", encoding="utf-8") as f:
    schritt2 = json.load(f)

with open(f"{OUTPUT_DIR}/schritt3_zusammenfassung.json", "r", encoding="utf-8") as f:
    schritt3 = json.load(f)

with open(f"{OUTPUT_DIR}/schritt4_ergebnis.json", "r", encoding="utf-8") as f:
    schritt4 = json.load(f)

with open(f"{OUTPUT_DIR}/schritt5_ergebnis.json", "r", encoding="utf-8") as f:
    schritt5 = json.load(f)

# Gewinner ermitteln
gewinner = None
for kandidat in schritt5["kandidaten_ohne_abzweigungen"]:
    # Prüfe ob auch keine parallele Wege
    for k4 in schritt4["kandidaten"]:
        if k4["id"] == kandidat["id"] and k4["anzahl_parallele"] == 0:
            gewinner = kandidat
            break

print(f"\n=== GEWINNER ===")
if gewinner:
    print(f"ID: {gewinner['id']}")
    print(f"Länge: {gewinner['laenge_m']:.1f}m")
    print(f"Geradheit: {gewinner['geradheit']:.4f}")
    print(f"Abzweigungen: {gewinner['anzahl_abzweigungen']}")
else:
    print("Kein Kandidat erfüllt alle Kriterien!")

# Finale Zusammenfassung
final_summary = {
    "zeitstempel": datetime.now().isoformat(),
    "task": "Fußweg in Hamburg suchen",
    "kriterien": {
        "dauer": "~10 Minuten",
        "zugaenglichkeit": "Nur zu Fuß",
        "parallelwege": "Keine",
        "abzweigungen": "Keine",
    },
    "datenquelle": "OpenStreetMap (Overpass API)",
    "bereich": "Stadtpark Hamburg",
    "schritte": {
        "schritt1_daten_abrufen": schritt1,
        "schritt2_laenge_filtern": schritt2,
        "schritt3_geradheit_pruefen": {
            "gesamt_weise": schritt3["gesamt_weise"],
            "gerade_weise": schritt3["gerade_weise"],
        },
        "schritt4_parallelwege": {
            "kandidaten_ohne_parallele": len(schritt4["isolierte_kandidaten"]),
        },
        "schritt5_abzweigungen": {
            "kandidaten_ohne_abzweigungen": len(schritt5["kandidaten_ohne_abzweigungen"]),
        },
    },
    "gewinner": gewinner,
}

with open(f"{OUTPUT_DIR}/ergebnis_final.json", "w", encoding="utf-8") as f:
    json.dump(final_summary, f, indent=2, ensure_ascii=False)

print(f"\nFinale Zusammenfassung gespeichert: {OUTPUT_DIR}/ergebnis_final.json")

# HTML-Karte erstellen
if gewinner:
    # Kandidaten-Koordinaten laden
    with open(f"{OUTPUT_DIR}/stadtpark_fusswege_gerade.geojson", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    for f in data["features"]:
        if f["properties"]["id"] == gewinner["id"]:
            coords = f["geometry"]["coordinates"]
            break
    
    # Mittelpunkt berechnen
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    center_lon = sum(lons) / len(lons)
    center_lat = sum(lats) / len(lats)
    
    # Koordinaten für JavaScript
    coords_js = json.dumps(coords)
    
    html = f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Fußweg-Suche Hamburg - Ergebnis</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        body {{ margin: 0; padding: 0; font-family: Arial, sans-serif; }}
        #map {{ height: 80vh; width: 100%; }}
        .info {{
            padding: 20px;
            background: #f5f5f5;
        }}
        .info h1 {{ margin-top: 0; }}
        .info table {{ border-collapse: collapse; width: 100%; }}
        .info td, .info th {{
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }}
        .info th {{ background: #4CAF50; color: white; }}
    </style>
</head>
<body>
    <div class="info">
        <h1>Gefundener Fußweg in Hamburg</h1>
        <table>
            <tr><th>Eigenschaft</th><th>Wert</th></tr>
            <tr><td>OSM ID</td><td>{gewinner['id']}</td></tr>
            <tr><td>Länge</td><td>{gewinner['laenge_m']:.1f}m (~10 Minuten)</td></tr>
            <tr><td>Geradheit</td><td>{gewinner['geradheit']:.4f} (1.0 = perfekt gerade)</td></tr>
            <tr><td>Parallele Wege</td><td>Keine</td></tr>
            <tr><td>Abzweigungen</td><td>Keine</td></tr>
            <tr><td>Ort</td><td>Stadtpark Hamburg</td></tr>
        </table>
    </div>
    <div id="map"></div>
    <script>
        var map = L.map('map').setView([{center_lat}, {center_lon}], 16);
        
        L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
            subdomains: 'abcd',
            maxZoom: 20
        }}).addTo(map);
        
        var coords = {coords_js};
        var latlngs = coords.map(function(c) {{ return [c[1], c[0]]; }});
        
        L.polyline(latlngs, {{
            color: 'red',
            weight: 5,
            opacity: 0.8
        }}).addTo(map);
        
        L.marker(latlngs[0]).addTo(map)
            .bindPopup('Start');
        L.marker(latlngs[latlngs.length-1]).addTo(map)
            .bindPopup('Ende');
        
        map.fitBounds(L.latLngBounds(latlngs));
    </script>
</body>
</html>
"""
    
    with open(f"{OUTPUT_DIR}/ergebnis_karte.html", "w", encoding="utf-8") as f:
        f.write(html)
    
    print(f"Karte gespeichert: {OUTPUT_DIR}/ergebnis_karte.html")

print("\n=== Alle Schritte abgeschlossen ===")
