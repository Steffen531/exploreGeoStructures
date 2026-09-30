"""
Schritt 3: Karte erstellen
Strategie 1: Achsen-Strategie + Zeitliche Optimierung

Erstellt eine interaktive Karte mit der geplanten Route
"""

import json
from datetime import datetime

OUTPUT_DIR = "tasks/ÖPNVRundfahrt/Strategie1"

print("=== Schritt 3: Karte erstellen ===")
print(f"Zeit: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Lade Route
with open(f"{OUTPUT_DIR}/route_plan.json", "r", encoding="utf-8") as f:
    route = json.load(f)

print(f"Route: {route['name']}")
print(f"Start: {route['start']}")
print(f"Endpunkt: {route['endpunkt']}")
print(f"Gesamtdauer: {route['gesamt_dauer']} Minuten")

# JavaScript-Code als separater String
js_code = """
        // Karte initialisieren
        var map = L.map('map').setView([50.11, 8.68], 13);
        
        // OpenStreetMap Tile Layer
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(map);
        
        // Hinweg (S-Bahn)
        var hinwegCoords = """ + json.dumps(route['hinweg']['coords']) + """;
        L.polyline(hinwegCoords, {
            color: '""" + route['hinweg']['farbe'] + """',
            weight: 5,
            opacity: 0.8
        }).addTo(map).bindPopup('<b>Hinweg</b><br>""" + route['hinweg']['verkehrsmittel'] + """<br>""" + route['hinweg']['von'] + """ -> """ + route['hinweg']['nach'] + """<br>Dauer: """ + str(route['hinweg']['dauer']) + """ Min');
        
        // Rückweg (Straßenbahn)
        var rueckwegCoords = """ + json.dumps(route['rueckweg']['coords']) + """;
        L.polyline(rueckwegCoords, {
            color: '""" + route['rueckweg']['farbe'] + """',
            weight: 5,
            opacity: 0.8
        }).addTo(map).bindPopup('<b>Rückweg</b><br>""" + route['rueckweg']['verkehrsmittel'] + """<br>""" + route['rueckweg']['von'] + """ -> """ + route['rueckweg']['nach'] + """<br>Dauer: """ + str(route['rueckweg']['dauer']) + """ Min');
        
        // Erweiterung (Fähre)
        var faehreCoords = """ + json.dumps(route['erweiterung']['coords']) + """;
        L.polyline(faehreCoords, {
            color: '""" + route['erweiterung']['farbe'] + """',
            weight: 5,
            opacity: 0.8
        }).addTo(map).bindPopup('<b>Erweiterung</b><br>""" + route['erweiterung']['verkehrsmittel'] + """<br>""" + route['erweiterung']['von'] + """ -> """ + route['erweiterung']['nach'] + """<br>Dauer: """ + str(route['erweiterung']['dauer']) + """ Min');
        
        // Stationen markieren
        var stationen = """ + json.dumps(route['stationen']) + """;
        var stationCoords = {
            "Frankfurt Hbf": [50.11, 8.68],
            "Frankfurt Süd": [50.09, 8.68],
            "Frankfurt Ost": [50.12, 8.72],
            "Frankfurt West": [50.11, 8.64],
            "Frankfurt Nord": [50.13, 8.68],
            "Frankfurt Konstablerwache": [50.11, 8.69],
            "Frankfurt Ostbahnhof": [50.12, 8.72],
            "Frankfurt Lokalbahnhof": [50.10, 8.69],
            "Frankfurt Südbahnhof": [50.09, 8.68],
            "Frankfurt Höchst": [50.10, 8.65]
        };
        
        stationen.forEach(function(station) {
            if (stationCoords[station]) {
                L.marker(stationCoords[station]).addTo(map)
                    .bindPopup('<b>' + station + '</b>');
            }
        });
        
        // Legende
        var legend = L.control({position: 'bottomright'});
        legend.onAdd = function (map) {
            var div = L.DomUtil.create('div', 'legend');
            div.innerHTML = '<h4>Legende</h4>' +
                '<div class="legend-item"><span class="legend-color" style="background: """ + route['hinweg']['farbe'] + """"></span> Hinweg (S-Bahn)</div>' +
                '<div class="legend-item"><span class="legend-color" style="background: """ + route['rueckweg']['farbe'] + """"></span> Rückweg (Straßenbahn)</div>' +
                '<div class="legend-item"><span class="legend-color" style="background: """ + route['erweiterung']['farbe'] + """"></span> Erweiterung (Fähre)</div>';
            return div;
        };
        legend.addTo(map);
"""

# Erstelle HTML-Karte mit Leaflet
html = f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ÖPNV-Rundfahrt Frankfurt - Strategie 1</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: Arial, sans-serif;
        }}
        #map {{
            height: 600px;
            width: 100%;
        }}
        .info {{
            padding: 10px;
            background: #f0f0f0;
            margin: 10px;
            border-radius: 5px;
        }}
        .legend {{
            background: white;
            padding: 10px;
            border-radius: 5px;
            box-shadow: 0 0 15px rgba(0,0,0,0.2);
        }}
        .legend-item {{
            margin: 5px 0;
        }}
        .legend-color {{
            display: inline-block;
            width: 20px;
            height: 3px;
            margin-right: 5px;
            vertical-align: middle;
        }}
    </style>
</head>
<body>
    <div class="info">
        <h1>ÖPNV-Rundfahrt Frankfurt - Strategie 1</h1>
        <p><strong>Datum:</strong> {route['datum']}</p>
        <p><strong>Zeit:</strong> {route['zeit']}</p>
        <p><strong>Start:</strong> {route['start']}</p>
        <p><strong>Endpunkt:</strong> {route['endpunkt']}</p>
        <p><strong>Gesamtdauer:</strong> {route['gesamt_dauer']} Minuten ({route['gesamt_dauer'] // 60} Stunden {route['gesamt_dauer'] % 60} Minuten)</p>
        <p><strong>Verkehrsmittel:</strong> {', '.join(route['verkehrsmittel'])}</p>
    </div>
    <div id="map"></div>
    <div class="info">
        <h2>Route</h2>
        <h3>Hinweg: {route['hinweg']['name']}</h3>
        <p><strong>Verkehrsmittel:</strong> {route['hinweg']['verkehrsmittel']}</p>
        <p><strong>Von:</strong> {route['hinweg']['von']} -> <strong>Nach:</strong> {route['hinweg']['nach']}</p>
        <p><strong>Dauer:</strong> {route['hinweg']['dauer']} Minuten</p>
        <p><strong>Stationen:</strong> {', '.join(route['hinweg']['stationen'])}</p>
        
        <h3>Umstieg: {route['umstieg']['ort']}</h3>
        <p><strong>Wartezeit:</strong> {route['umstieg']['wartezeit']} Minuten</p>
        <p><strong>Beschreibung:</strong> {route['umstieg']['beschreibung']}</p>
        
        <h3>Rückweg: {route['rueckweg']['name']}</h3>
        <p><strong>Verkehrsmittel:</strong> {route['rueckweg']['verkehrsmittel']}</p>
        <p><strong>Von:</strong> {route['rueckweg']['von']} -> <strong>Nach:</strong> {route['rueckweg']['nach']}</p>
        <p><strong>Dauer:</strong> {route['rueckweg']['dauer']} Minuten</p>
        <p><strong>Stationen:</strong> {', '.join(route['rueckweg']['stationen'])}</p>
        
        <h3>Erweiterung: {route['erweiterung']['name']}</h3>
        <p><strong>Verkehrsmittel:</strong> {route['erweiterung']['verkehrsmittel']}</p>
        <p><strong>Von:</strong> {route['erweiterung']['von']} -> <strong>Nach:</strong> {route['erweiterung']['nach']}</p>
        <p><strong>Dauer:</strong> {route['erweiterung']['dauer']} Minuten</p>
        <p><strong>Stationen:</strong> {', '.join(route['erweiterung']['stationen'])}</p>
    </div>
    <script>{js_code}
    </script>
</body>
</html>
"""

output_file = f"{OUTPUT_DIR}/route_karte.html"
with open(output_file, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\nKarte gespeichert: {output_file}")
print("\n=== Schritt 3 abgeschlossen ===")
