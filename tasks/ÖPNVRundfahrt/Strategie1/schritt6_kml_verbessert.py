"""
Schritt 6: Verbesserte KML-Datei mit Reiseverlauf, Linien und Umstiegspunkten
"""

import json
from datetime import datetime

OUTPUT_DIR = "tasks/ÖPNVRundfahrt/Strategie1"

print("=== Schritt 6: Verbesserte KML-Datei ===")
print(f"Zeit: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Lade Route
with open(f"{OUTPUT_DIR}/route_plan.json", "r", encoding="utf-8") as f:
    route = json.load(f)

# Lade OPNV-Daten
with open(f"{OUTPUT_DIR}/frankfurt_opnv_raw.geojson", "r", encoding="utf-8") as f:
    opnv_data = json.load(f)

# Finde Strecken
def finde_strecke(verkehrsmittel_typ, von, nach):
    beste_strecke = None
    beste_score = 0
    for feature in opnv_data['features']:
        props = feature['properties']
        vehicle_type = props.get('vehicle_type', '')
        from_station = props.get('from', '')
        to_station = props.get('to', '')
        if verkehrsmittel_typ.lower() not in vehicle_type.lower():
            continue
        score = 0
        if von in from_station or von in to_station:
            score += 1
        if nach in from_station or nach in to_station:
            score += 1
        if 'Frankfurt' in from_station or 'Frankfurt' in to_station:
            score += 0.3
        if score > beste_score:
            beste_score = score
            beste_strecke = feature
    return beste_strecke

hinweg_strecke = finde_strecke('S-Bahn', route['hinweg']['von'], route['hinweg']['nach'])
rueckweg_strecke = finde_strecke('Straßenbahn', route['rueckweg']['von'], route['rueckweg']['nach'])

if rueckweg_strecke is None:
    for feature in opnv_data['features']:
        if feature['properties'].get('vehicle_type') == 'Straßenbahn':
            rueckweg_strecke = feature
            break

def extrahiere_koordinaten(feature):
    if feature is None:
        return []
    return feature['geometry']['coordinates']

hinweg_coords = extrahiere_koordinaten(hinweg_strecke)
rueckweg_coords = extrahiere_koordinaten(rueckweg_strecke)

# Stationen-Koordinaten
station_coords = {
    "Frankfurt Hbf": [50.11, 8.68],
    "Frankfurt Süd": [50.09, 8.68],
    "Frankfurt Ost": [50.12, 8.72],
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
kml_parts.append(f'    <name>{route["name"]} - Reiseverlauf</name>')
kml_parts.append(f'    <description>ÖPNV-Rundfahrt Frankfurt - Strategie 1: Achsen-Strategie + Zeitliche Optimierung</description>')
kml_parts.append('')

# Stile für die verschiedenen Linien
kml_parts.append('    <!-- Stile für Linien -->')
kml_parts.append('    <Style id="hinweg">')
kml_parts.append('      <LineStyle>')
kml_parts.append('        <color>ff009933</color>')
kml_parts.append('        <width>6</width>')
kml_parts.append('      </LineStyle>')
kml_parts.append('    </Style>')
kml_parts.append('    <Style id="rueckweg">')
kml_parts.append('      <LineStyle>')
kml_parts.append('        <color>ffFF6600</color>')
kml_parts.append('        <width>6</width>')
kml_parts.append('      </LineStyle>')
kml_parts.append('    </Style>')
kml_parts.append('    <Style id="faehre">')
kml_parts.append('      <LineStyle>')
kml_parts.append('        <color>ff0099FF</color>')
kml_parts.append('        <width>6</width>')
kml_parts.append('      </LineStyle>')
kml_parts.append('    </Style>')
kml_parts.append('    <Style id="umstieg">')
kml_parts.append('      <IconStyle>')
kml_parts.append('        <color>ffFF0000</color>')
kml_parts.append('        <scale>1.5</scale>')
kml_parts.append('        <Icon>')
kml_parts.append('          <href>http://maps.google.com/mapfiles/kml/pushpin/ylw-pushpin.png</href>')
kml_parts.append('        </Icon>')
kml_parts.append('      </IconStyle>')
kml_parts.append('    </Style>')
kml_parts.append('    <Style id="start">')
kml_parts.append('      <IconStyle>')
kml_parts.append('        <color>ff00FF00</color>')
kml_parts.append('        <scale>1.5</scale>')
kml_parts.append('        <Icon>')
kml_parts.append('          <href>http://maps.google.com/mapfiles/kml/pushpin/grn-pushpin.png</href>')
kml_parts.append('        </Icon>')
kml_parts.append('      </IconStyle>')
kml_parts.append('    </Style>')
kml_parts.append('    <Style id="ziel">')
kml_parts.append('      <IconStyle>')
kml_parts.append('        <color>ffFF00FF</color>')
kml_parts.append('        <scale>1.5</scale>')
kml_parts.append('        <Icon>')
kml_parts.append('          <href>http://maps.google.com/mapfiles/kml/pushpin/pink-pushpin.png</href>')
kml_parts.append('        </Icon>')
kml_parts.append('      </IconStyle>')
kml_parts.append('    </Style>')
kml_parts.append('')

# Startpunkt
kml_parts.append('    <!-- Startpunkt -->')
kml_parts.append('    <Placemark>')
kml_parts.append('      <name>Start: Frankfurt Hbf</name>')
kml_parts.append('      <description>Startpunkt der ÖPNV-Rundfahrt</description>')
kml_parts.append('      <styleUrl>#start</styleUrl>')
kml_parts.append('      <Point>')
kml_parts.append('        <coordinates>8.68,50.11,0</coordinates>')
kml_parts.append('      </Point>')
kml_parts.append('    </Placemark>')
kml_parts.append('')

# Hinweg (S-Bahn)
kml_parts.append('    <!-- 1. Teilstrecke: S-Bahn S7/S8/S9 -->')
kml_parts.append('    <Placemark>')
kml_parts.append('      <name>1. S-Bahn S7/S8/S9</name>')
kml_parts.append(f'      <description>Von: {route["hinweg"]["von"]} -> Nach: {route["hinweg"]["nach"]}')
kml_parts.append(f'Dauer: {route["hinweg"]["dauer"]} Minuten')
kml_parts.append(f'Stationen: {", ".join(route["hinweg"]["stationen"])}</description>')
kml_parts.append('      <styleUrl>#hinweg</styleUrl>')
kml_parts.append('      <LineString>')
kml_parts.append('        <coordinates>')
for coord in hinweg_coords:
    kml_parts.append(f'          {coord[0]},{coord[1]},0')
kml_parts.append('        </coordinates>')
kml_parts.append('      </LineString>')
kml_parts.append('    </Placemark>')
kml_parts.append('')

# Umstiegspunkt 1
kml_parts.append('    <!-- Umstiegspunkt 1 -->')
kml_parts.append('    <Placemark>')
kml_parts.append('      <name>Umstieg 1: Frankfurt Ost</name>')
kml_parts.append('      <description>Umstieg von S-Bahn auf Straßenbahn</description>')
kml_parts.append('      <styleUrl>#umstieg</styleUrl>')
kml_parts.append('      <Point>')
kml_parts.append('        <coordinates>8.72,50.12,0</coordinates>')
kml_parts.append('      </Point>')
kml_parts.append('    </Placemark>')
kml_parts.append('')

# Rückweg (Straßenbahn)
kml_parts.append('    <!-- 2. Teilstrecke: Straßenbahn 11/12 -->')
kml_parts.append('    <Placemark>')
kml_parts.append('      <name>2. Straßenbahn 11/12</name>')
kml_parts.append(f'      <description>Von: {route["rueckweg"]["von"]} -> Nach: {route["rueckweg"]["nach"]}')
kml_parts.append(f'Dauer: {route["rueckweg"]["dauer"]} Minuten')
kml_parts.append(f'Stationen: {", ".join(route["rueckweg"]["stationen"])}</description>')
kml_parts.append('      <styleUrl>#rueckweg</styleUrl>')
kml_parts.append('      <LineString>')
kml_parts.append('        <coordinates>')
for coord in rueckweg_coords:
    kml_parts.append(f'          {coord[0]},{coord[1]},0')
kml_parts.append('        </coordinates>')
kml_parts.append('      </LineString>')
kml_parts.append('    </Placemark>')
kml_parts.append('')

# Umstiegspunkt 2
kml_parts.append('    <!-- Umstiegspunkt 2 -->')
kml_parts.append('    <Placemark>')
kml_parts.append('      <name>Umstieg 2: Frankfurt Süd</name>')
kml_parts.append('      <description>Umstieg von Straßenbahn auf Fähre</description>')
kml_parts.append('      <styleUrl>#umstieg</styleUrl>')
kml_parts.append('      <Point>')
kml_parts.append('        <coordinates>8.68,50.09,0</coordinates>')
kml_parts.append('      </Point>')
kml_parts.append('    </Placemark>')
kml_parts.append('')

# Erweiterung (Fähre)
kml_parts.append('    <!-- 3. Teilstrecke: Fähre -->')
kml_parts.append('    <Placemark>')
kml_parts.append('      <name>3. Fähre</name>')
kml_parts.append(f'      <description>Von: {route["erweiterung"]["von"]} -> Nach: {route["erweiterung"]["nach"]}')
kml_parts.append(f'Dauer: {route["erweiterung"]["dauer"]} Minuten')
kml_parts.append(f'Stationen: {", ".join(route["erweiterung"]["stationen"])}</description>')
kml_parts.append('      <styleUrl>#faehre</styleUrl>')
kml_parts.append('      <LineString>')
kml_parts.append('        <coordinates>')
for coord in route['erweiterung']['coords']:
    kml_parts.append(f'          {coord[0]},{coord[1]},0')
kml_parts.append('        </coordinates>')
kml_parts.append('      </LineString>')
kml_parts.append('    </Placemark>')
kml_parts.append('')

# Endpunkt
kml_parts.append('    <!-- Endpunkt -->')
kml_parts.append('    <Placemark>')
kml_parts.append('      <name>Ziel: Frankfurt Höchst</name>')
kml_parts.append('      <description>Endpunkt der ÖPNV-Rundfahrt</description>')
kml_parts.append('      <styleUrl>#ziel</styleUrl>')
kml_parts.append('      <Point>')
kml_parts.append('        <coordinates>8.65,50.1,0</coordinates>')
kml_parts.append('      </Point>')
kml_parts.append('    </Placemark>')
kml_parts.append('')

# Legende
kml_parts.append('    <!-- Legende -->')
kml_parts.append('    <Placemark>')
kml_parts.append('      <name>Legende</name>')
kml_parts.append('      <description>1. S-Bahn S7/S8/S9 (grün) - 20 Min')
kml_parts.append('2. Straßenbahn 11/12 (orange) - 35 Min')
kml_parts.append('3. Fähre (blau) - 30 Min')
kml_parts.append('Gesamtdauer: 90 Minuten</description>')
kml_parts.append('      <Point>')
kml_parts.append('        <coordinates>8.68,50.11,0</coordinates>')
kml_parts.append('      </Point>')
kml_parts.append('    </Placemark>')

kml_parts.append('  </Document>')
kml_parts.append('</kml>')

kml_content = '\n'.join(kml_parts)

kml_file = f"{OUTPUT_DIR}/route_verbessert.kml"
with open(kml_file, "w", encoding="utf-8") as f:
    f.write(kml_content)

print(f"KML-Datei gespeichert: {kml_file}")
print("\n=== Schritt 6 abgeschlossen ===")
