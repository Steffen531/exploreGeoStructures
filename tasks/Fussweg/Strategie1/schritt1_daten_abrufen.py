"""
Schritt 1: OSM-Daten für den Hamburger Stadtpark abrufen
Der Stadtpark (~149 ha) hat viele Fußwege und ist überschaubar.
"""

import requests
import json
import time
from datetime import datetime

OUTPUT_DIR = "tasks/Fussweg/Strategie1"

OVERPASS_SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

print("=== Schritt 1: OSM-Daten abrufen ===")
print(f"Zeit: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Stadtpark Hamburg: ~53.585N, 10.02E
# Bounding Box: 53.575-53.595 N, 10.00-10.04 E (ca. 2km x 2km)
query = """
[out:json][timeout:60];
(
  way["highway"="footway"](53.575,10.00,53.595,10.04);
  way["highway"="path"](53.575,10.00,53.595,10.04);
);
out body;
>;
out skel qt;
"""

print("Sende Overpass API Anfrage...")
print("Bereich: Stadtpark Hamburg (53.575-53.595N, 10.00-10.04E)")

data = None
for server in OVERPASS_SERVERS:
    print(f"\nVersuche Server: {server}")
    start_time = time.time()
    
    try:
        headers = {
            "User-Agent": "exploreGeoStructures/1.0 (Fußweg-Suche Hamburg)",
        }
        response = requests.post(server, data={"data": query}, headers=headers, timeout=90)
        
        elapsed = time.time() - start_time
        print(f"Status: {response.status_code} in {elapsed:.1f}s")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Erfolg! Server: {server}")
            break
        else:
            print(f"Fehler: {response.status_code}")
            
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"Fehler nach {elapsed:.1f}s: {e}")
        continue

if data is None:
    print("\nAlle Server fehlgeschlagen!")
    exit(1)

elements = data.get("elements", [])
print(f"\nElemente empfangen: {len(elements)}")

# In GeoJSON konvertieren
nodes = {}
ways = []

for elem in elements:
    if elem["type"] == "node":
        nodes[elem["id"]] = (elem["lon"], elem["lat"])
    elif elem["type"] == "way":
        ways.append(elem)

print(f"Nodes: {len(nodes)}, Ways: {len(ways)}")

# GeoJSON Feature Collection erstellen
features = []
for way in ways:
    node_ids = way.get("nodes", [])
    coords = []
    for nid in node_ids:
        if nid in nodes:
            coords.append(nodes[nid])
    
    if len(coords) < 2:
        continue
    
    tags = way.get("tags", {})
    feature = {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": coords,
        },
        "properties": {
            "id": way["id"],
            "highway": tags.get("highway", "unknown"),
            "name": tags.get("name", ""),
            "surface": tags.get("surface", ""),
            "foot": tags.get("foot", ""),
        },
    }
    features.append(feature)

geojson = {
    "type": "FeatureCollection",
    "features": features,
}

output_file = f"{OUTPUT_DIR}/stadtpark_fusswege_raw.geojson"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(geojson, f, ensure_ascii=False)

print(f"\nGespeichert: {output_file}")
print(f"Features: {len(features)}")

# Statistiken
highway_counts = {}
for f in features:
    hw = f["properties"]["highway"]
    highway_counts[hw] = highway_counts.get(hw, 0) + 1

print(f"\nVerteilung highway-Typen: {highway_counts}")

# Zusammenfassung speichern
summary = {
    "zeitstempel": datetime.now().isoformat(),
    "gesamt_weise": len(features),
    "highway_typen": highway_counts,
    "datenquelle": "Overpass API",
    "bereich": "Stadtpark Hamburg (53.575-53.595N, 10.00-10.04E)",
}

with open(f"{OUTPUT_DIR}/schritt1_zusammenfassung.json", "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)

print(f"Zusammenfassung gespeichert: {OUTPUT_DIR}/schritt1_zusammenfassung.json")
print("\n=== Schritt 1 abgeschlossen ===")
