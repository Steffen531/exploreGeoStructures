"""
Schritt 4: KML- und GPX-Dateien erstellen
Strategie 1: Achsen-Strategie + Zeitliche Optimierung

Erstellt KML- und GPX-Dateien für die Visualisierung auf umap.openstreetmap.de
"""

import json
from datetime import datetime

OUTPUT_DIR = "tasks/ÖPNVRundfahrt/Strategie1"

print("=== Schritt 4: KML- und GPX-Dateien erstellen ===")
print(f"Zeit: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Lade Route
with open(f"{OUTPUT_DIR}/route_plan.json", "r", encoding="utf-8") as f:
    route = json.load(f)

print(f"Route: {route['name']}")

# KML-Datei erstellen
kml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>{route['name']}</name>
    <description>ÖPNV-Rundfahrt Frankfurt - Strategie 1: Achsen-Strategie + Zeitliche Optimierung</description>
    
    <!-- Hinweg (S-Bahn) -->
    <Placemark>
      <name>Hinweg: {route['hinweg']['verkehrsmittel']}</name>
      <description>Von: {route['hinweg']['von']} -> Nach: {route['hinweg']['nach']}
Dauer: {route['hinweg']['dauer']} Minuten
Stationen: {', '.join(route['hinweg']['stationen'])}</description>
      <Style>
        <LineStyle>
          <color>ff{route['hinweg']['farbe'].replace('#', '')}</color>
          <width>5</width>
        </LineStyle>
      </Style>
      <LineString>
        <coordinates>
"""
for coord in route['hinweg']['coords']:
    kml_content += f"          {coord[0]},{coord[1]},0\n"

kml_content += """        </coordinates>
      </LineString>
    </Placemark>
    
    <!-- Rückweg (Straßenbahn) -->
    <Placemark>
      <name>Rückweg: {route['rueckweg']['verkehrsmittel']}</name>
      <description>Von: {route['rueckweg']['von']} -> Nach: {route['rueckweg']['nach']}
Dauer: {route['rueckweg']['dauer']} Minuten
Stationen: {', '.join(route['rueckweg']['stationen'])}</description>
      <Style>
        <LineStyle>
          <color>ff{route['rueckweg']['farbe'].replace('#', '')}</color>
          <width>5</width>
        </LineStyle>
      </Style>
      <LineString>
        <coordinates>
"""
for coord in route['rueckweg']['coords']:
    kml_content += f"          {coord[0]},{coord[1]},0\n"

kml_content += """        </coordinates>
      </LineString>
    </Placemark>
    
    <!-- Erweiterung (Fähre) -->
    <Placemark>
      <name>Erweiterung: {route['erweiterung']['verkehrsmittel']}</name>
      <description>Von: {route['erweiterung']['von']} -> Nach: {route['erweiterung']['nach']}
Dauer: {route['erweiterung']['dauer']} Minuten
Stationen: {', '.join(route['erweiterung']['stationen'])}</description>
      <Style>
        <LineStyle>
          <color>ff{route['erweiterung']['farbe'].replace('#', '')}</color>
          <width>5</width>
        </LineStyle>
      </Style>
      <LineString>
        <coordinates>
"""
for coord in route['erweiterung']['coords']:
    kml_content += f"          {coord[0]},{coord[1]},0\n"

kml_content += """        </coordinates>
      </LineString>
    </Placemark>
    
    <!-- Stationen -->
"""
# Stationen hinzufügen
station_coords = {
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
}

for station in route['stationen']:
    if station in station_coords:
        lat, lon = station_coords[station]
        kml_content += f"""    <Placemark>
      <name>{station}</name>
      <Point>
        <coordinates>{lon},{lat},0</coordinates>
      </Point>
    </Placemark>
"""

kml_content += """  </Document>
</kml>
"""

kml_file = f"{OUTPUT_DIR}/route.kml"
with open(kml_file, "w", encoding="utf-8") as f:
    f.write(kml_content)

print(f"KML-Datei gespeichert: {kml_file}")

# GPX-Datei erstellen
gpx_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="exploreGeoStructures" xmlns="http://www.topografix.com/GPX/1/1">
  <metadata>
    <name>{route['name']}</name>
    <desc>ÖPNV-Rundfahrt Frankfurt - Strategie 1: Achsen-Strategie + Zeitliche Optimierung</desc>
  </metadata>
  
  <!-- Hinweg (S-Bahn) -->
  <trk>
    <name>Hinweg: {route['hinweg']['verkehrsmittel']}</name>
    <desc>Von: {route['hinweg']['von']} -> Nach: {route['hinweg']['nach']}, Dauer: {route['hinweg']['dauer']} Minuten</desc>
    <trkseg>
"""
for coord in route['hinweg']['coords']:
    gpx_content += f"      <trkpt lat=\"{coord[1]}\" lon=\"{coord[0]}\"></trkpt>\n"

gpx_content += """    </trkseg>
  </trk>
  
  <!-- Rückweg (Straßenbahn) -->
  <trk>
    <name>Rückweg: {route['rueckweg']['verkehrsmittel']}</name>
    <desc>Von: {route['rueckweg']['von']} -> Nach: {route['rueckweg']['nach']}, Dauer: {route['rueckweg']['dauer']} Minuten</desc>
    <trkseg>
"""
for coord in route['rueckweg']['coords']:
    gpx_content += f"      <trkpt lat=\"{coord[1]}\" lon=\"{coord[0]}\"></trkpt>\n"

gpx_content += """    </trkseg>
  </trk>
  
  <!-- Erweiterung (Fähre) -->
  <trk>
    <name>Erweiterung: {route['erweiterung']['verkehrsmittel']}</name>
    <desc>Von: {route['erweiterung']['von']} -> Nach: {route['erweiterung']['nach']}, Dauer: {route['erweiterung']['dauer']} Minuten</desc>
    <trkseg>
"""
for coord in route['erweiterung']['coords']:
    gpx_content += f"      <trkpt lat=\"{coord[1]}\" lon=\"{coord[0]}\"></trkpt>\n"

gpx_content += """    </trkseg>
  </trk>
  
  <!-- Stationen als Wegpunkte -->
"""
for station in route['stationen']:
    if station in station_coords:
        lat, lon = station_coords[station]
        gpx_content += f"""  <wpt lat="{lat}" lon="{lon}">
    <name>{station}</name>
  </wpt>
"""

gpx_content += """</gpx>
"""

gpx_file = f"{OUTPUT_DIR}/route.gpx"
with open(gpx_file, "w", encoding="utf-8") as f:
    f.write(gpx_content)

print(f"GPX-Datei gespeichert: {gpx_file}")

# Zusammenfassung speichern
summary = {
    "zeitstempel": datetime.now().isoformat(),
    "kml_datei": kml_file,
    "gpx_datei": gpx_file,
    "visualisierung": "https://umap.openstreetmap.de",
    "hinweis": "Laden Sie die KML- oder GPX-Datei auf umap.openstreetmap.de hoch, um die Route zu visualisieren.",
}

with open(f"{OUTPUT_DIR}/schritt4_zusammenfassung.json", "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)

print(f"Zusammenfassung gespeichert: {OUTPUT_DIR}/schritt4_zusammenfassung.json")
print("\n=== Schritt 4 abgeschlossen ===")
