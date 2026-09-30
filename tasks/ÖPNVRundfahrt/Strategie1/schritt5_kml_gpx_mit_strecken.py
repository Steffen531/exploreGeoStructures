"""
Schritt 5: KML- und GPX-Dateien mit tatsächlichen Strecken erstellen
Strategie 1: Achsen-Strategie + Zeitliche Optimierung

Erstellt KML- und GPX-Dateien mit den tatsächlichen Strecken der Verkehrsmittel
"""

import json
from datetime import datetime

OUTPUT_DIR = "tasks/ÖPNVRundfahrt/Strategie1"

print("=== Schritt 5: KML- und GPX mit tatsächlichen Strecken ===")
print(f"Zeit: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Lade Route
with open(f"{OUTPUT_DIR}/route_plan.json", "r", encoding="utf-8") as f:
    route = json.load(f)

# Lade OPNV-Daten mit echten Strecken
with open(f"{OUTPUT_DIR}/frankfurt_opnv_raw.geojson", "r", encoding="utf-8") as f:
    opnv_data = json.load(f)

print(f"Route: {route['name']}")
print(f"OPNV-Daten: {len(opnv_data['features'])} Strecken gefunden")

# Finde die relevanten Strecken für die Route
def finde_strecke(verkehrsmittel_typ, von, nach):
    """Finde die Strecke im GeoJSON, die am besten passt"""
    beste_strecke = None
    beste_score = 0
    
    for feature in opnv_data['features']:
        props = feature['properties']
        name = props.get('name', '')
        vehicle_type = props.get('vehicle_type', '')
        from_station = props.get('from', '')
        to_station = props.get('to', '')
        
        # Prüfe ob Verkehrsmittel-Typ passt
        if verkehrsmittel_typ.lower() not in vehicle_type.lower():
            continue
        
        # Berechne Score basierend auf Stationen
        score = 0
        
        # Prüfe ob die Stationen in der Strecke vorkommen
        if von in from_station or von in to_station:
            score += 1
        if nach in from_station or nach in to_station:
            score += 1
        
        # Prüfe ob die Stationen in der Strecke vorkommen (auch als Teilstring)
        if von in name or von in from_station or von in to_station:
            score += 0.5
        if nach in name or nach in from_station or nach in to_station:
            score += 0.5
        
        # Bonus für Strecken, die durch Frankfurt fahren
        if 'Frankfurt' in from_station or 'Frankfurt' in to_station:
            score += 0.3
        
        if score > beste_score:
            beste_score = score
            beste_strecke = feature
    
    return beste_strecke

# Finde Strecken für jedes Segment
hinweg_strecke = finde_strecke('S-Bahn', route['hinweg']['von'], route['hinweg']['nach'])
rueckweg_strecke = finde_strecke('Straßenbahn', route['rueckweg']['von'], route['rueckweg']['nach'])

# Fallback: Wenn keine Straßenbahn-Strecke gefunden wurde, nimm die erste verfügbare
if rueckweg_strecke is None:
    for feature in opnv_data['features']:
        props = feature['properties']
        if props.get('vehicle_type') == 'Straßenbahn':
            rueckweg_strecke = feature
            break

print(f"Hinweg-Strecke: {hinweg_strecke['properties']['name'] if hinweg_strecke else 'Nicht gefunden'}")
print(f"Rückweg-Strecke: {rueckweg_strecke['properties']['name'] if rueckweg_strecke else 'Nicht gefunden'}")

# Extrahiere Koordinaten aus den Strecken
def extrahiere_koordinaten(feature):
    """Extrahiere Koordinaten aus einem GeoJSON Feature"""
    if feature is None:
        return []
    return feature['geometry']['coordinates']

hinweg_coords = extrahiere_koordinaten(hinweg_strecke)
rueckweg_coords = extrahiere_koordinaten(rueckweg_strecke)

print(f"Hinweg-Koordinaten: {len(hinweg_coords)} Punkte")
print(f"Rückweg-Koordinaten: {len(rueckweg_coords)} Punkte")

# Stationen-Koordinaten
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

# KML-Datei erstellen
kml_parts = []
kml_parts.append('<?xml version="1.0" encoding="UTF-8"?>')
kml_parts.append('<kml xmlns="http://www.opengis.net/kml/2.2">')
kml_parts.append('  <Document>')
kml_parts.append(f'    <name>{route["name"]}</name>')
kml_parts.append(f'    <description>ÖPNV-Rundfahrt Frankfurt - Strategie 1: Achsen-Strategie + Zeitliche Optimierung</description>')
kml_parts.append('')
kml_parts.append('    <!-- Hinweg (S-Bahn) -->')
kml_parts.append('    <Placemark>')
kml_parts.append(f'      <name>Hinweg: {route["hinweg"]["verkehrsmittel"]}</name>')
kml_parts.append(f'      <description>Von: {route["hinweg"]["von"]} -> Nach: {route["hinweg"]["nach"]}')
kml_parts.append(f'Dauer: {route["hinweg"]["dauer"]} Minuten')
kml_parts.append(f'Stationen: {", ".join(route["hinweg"]["stationen"])}</description>')
kml_parts.append('      <Style>')
kml_parts.append('        <LineStyle>')
kml_parts.append(f'          <color>ff{route["hinweg"]["farbe"].replace("#", "")}</color>')
kml_parts.append('          <width>5</width>')
kml_parts.append('        </LineStyle>')
kml_parts.append('      </Style>')
kml_parts.append('      <LineString>')
kml_parts.append('        <coordinates>')
for coord in hinweg_coords:
    kml_parts.append(f'          {coord[0]},{coord[1]},0')
kml_parts.append('        </coordinates>')
kml_parts.append('      </LineString>')
kml_parts.append('    </Placemark>')
kml_parts.append('')
kml_parts.append('    <!-- Rückweg (Straßenbahn) -->')
kml_parts.append('    <Placemark>')
kml_parts.append(f'      <name>Rückweg: {route["rueckweg"]["verkehrsmittel"]}</name>')
kml_parts.append(f'      <description>Von: {route["rueckweg"]["von"]} -> Nach: {route["rueckweg"]["nach"]}')
kml_parts.append(f'Dauer: {route["rueckweg"]["dauer"]} Minuten')
kml_parts.append(f'Stationen: {", ".join(route["rueckweg"]["stationen"])}</description>')
kml_parts.append('      <Style>')
kml_parts.append('        <LineStyle>')
kml_parts.append(f'          <color>ff{route["rueckweg"]["farbe"].replace("#", "")}</color>')
kml_parts.append('          <width>5</width>')
kml_parts.append('        </LineStyle>')
kml_parts.append('      </Style>')
kml_parts.append('      <LineString>')
kml_parts.append('        <coordinates>')
for coord in rueckweg_coords:
    kml_parts.append(f'          {coord[0]},{coord[1]},0')
kml_parts.append('        </coordinates>')
kml_parts.append('      </LineString>')
kml_parts.append('    </Placemark>')
kml_parts.append('')
kml_parts.append('    <!-- Erweiterung (Fähre) -->')
kml_parts.append('    <Placemark>')
kml_parts.append(f'      <name>Erweiterung: {route["erweiterung"]["verkehrsmittel"]}</name>')
kml_parts.append(f'      <description>Von: {route["erweiterung"]["von"]} -> Nach: {route["erweiterung"]["nach"]}')
kml_parts.append(f'Dauer: {route["erweiterung"]["dauer"]} Minuten')
kml_parts.append(f'Stationen: {", ".join(route["erweiterung"]["stationen"])}</description>')
kml_parts.append('      <Style>')
kml_parts.append('        <LineStyle>')
kml_parts.append(f'          <color>ff{route["erweiterung"]["farbe"].replace("#", "")}</color>')
kml_parts.append('          <width>5</width>')
kml_parts.append('        </LineStyle>')
kml_parts.append('      </Style>')
kml_parts.append('      <LineString>')
kml_parts.append('        <coordinates>')
for coord in route['erweiterung']['coords']:
    kml_parts.append(f'          {coord[0]},{coord[1]},0')
kml_parts.append('        </coordinates>')
kml_parts.append('      </LineString>')
kml_parts.append('    </Placemark>')
kml_parts.append('')
kml_parts.append('    <!-- Stationen -->')

for station in route['stationen']:
    if station in station_coords:
        lat, lon = station_coords[station]
        kml_parts.append('    <Placemark>')
        kml_parts.append(f'      <name>{station}</name>')
        kml_parts.append('      <Point>')
        kml_parts.append(f'        <coordinates>{lon},{lat},0</coordinates>')
        kml_parts.append('      </Point>')
        kml_parts.append('    </Placemark>')

kml_parts.append('  </Document>')
kml_parts.append('</kml>')

kml_content = '\n'.join(kml_parts)

kml_file = f"{OUTPUT_DIR}/route_mit_strecken.kml"
with open(kml_file, "w", encoding="utf-8") as f:
    f.write(kml_content)

print(f"KML-Datei gespeichert: {kml_file}")

# GPX-Datei erstellen
gpx_parts = []
gpx_parts.append('<?xml version="1.0" encoding="UTF-8"?>')
gpx_parts.append('<gpx version="1.1" creator="exploreGeoStructures" xmlns="http://www.topografix.com/GPX/1/1">')
gpx_parts.append('  <metadata>')
gpx_parts.append(f'    <name>{route["name"]}</name>')
gpx_parts.append(f'    <desc>ÖPNV-Rundfahrt Frankfurt - Strategie 1: Achsen-Strategie + Zeitliche Optimierung</desc>')
gpx_parts.append('  </metadata>')
gpx_parts.append('')
gpx_parts.append('  <!-- Hinweg (S-Bahn) -->')
gpx_parts.append('  <trk>')
gpx_parts.append(f'    <name>Hinweg: {route["hinweg"]["verkehrsmittel"]}</name>')
gpx_parts.append(f'    <desc>Von: {route["hinweg"]["von"]} -> Nach: {route["hinweg"]["nach"]}, Dauer: {route["hinweg"]["dauer"]} Minuten</desc>')
gpx_parts.append('    <trkseg>')
for coord in hinweg_coords:
    gpx_parts.append(f'      <trkpt lat="{coord[1]}" lon="{coord[0]}"></trkpt>')
gpx_parts.append('    </trkseg>')
gpx_parts.append('  </trk>')
gpx_parts.append('')
gpx_parts.append('  <!-- Rückweg (Straßenbahn) -->')
gpx_parts.append('  <trk>')
gpx_parts.append(f'    <name>Rückweg: {route["rueckweg"]["verkehrsmittel"]}</name>')
gpx_parts.append(f'    <desc>Von: {route["rueckweg"]["von"]} -> Nach: {route["rueckweg"]["nach"]}, Dauer: {route["rueckweg"]["dauer"]} Minuten</desc>')
gpx_parts.append('    <trkseg>')
for coord in rueckweg_coords:
    gpx_parts.append(f'      <trkpt lat="{coord[1]}" lon="{coord[0]}"></trkpt>')
gpx_parts.append('    </trkseg>')
gpx_parts.append('  </trk>')
gpx_parts.append('')
gpx_parts.append('  <!-- Erweiterung (Fähre) -->')
gpx_parts.append('  <trk>')
gpx_parts.append(f'    <name>Erweiterung: {route["erweiterung"]["verkehrsmittel"]}</name>')
gpx_parts.append(f'    <desc>Von: {route["erweiterung"]["von"]} -> Nach: {route["erweiterung"]["nach"]}, Dauer: {route["erweiterung"]["dauer"]} Minuten</desc>')
gpx_parts.append('    <trkseg>')
for coord in route['erweiterung']['coords']:
    gpx_parts.append(f'      <trkpt lat="{coord[1]}" lon="{coord[0]}"></trkpt>')
gpx_parts.append('    </trkseg>')
gpx_parts.append('  </trk>')
gpx_parts.append('')
gpx_parts.append('  <!-- Stationen als Wegpunkte -->')

for station in route['stationen']:
    if station in station_coords:
        lat, lon = station_coords[station]
        gpx_parts.append(f'  <wpt lat="{lat}" lon="{lon}">')
        gpx_parts.append(f'    <name>{station}</name>')
        gpx_parts.append('  </wpt>')

gpx_parts.append('</gpx>')

gpx_content = '\n'.join(gpx_parts)

gpx_file = f"{OUTPUT_DIR}/route_mit_strecken.gpx"
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
    "strecken": {
        "hinweg": hinweg_strecke['properties']['name'] if hinweg_strecke else None,
        "rueckweg": rueckweg_strecke['properties']['name'] if rueckweg_strecke else None,
    }
}

with open(f"{OUTPUT_DIR}/schritt5_zusammenfassung.json", "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)

print(f"Zusammenfassung gespeichert: {OUTPUT_DIR}/schritt5_zusammenfassung.json")
print("\n=== Schritt 5 abgeschlossen ===")
