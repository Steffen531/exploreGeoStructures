"""
Schritt 3: Geradheit prüfen
Prüft, wie gerade die gefilterten Wege sind.
Krümmung berechnen: Verhältnis der direkten Distanz zur tatsächlichen Weglänge.
"""

import json
import math
from datetime import datetime

OUTPUT_DIR = "tasks/Fussweg/Strategie1"

print("=== Schritt 3: Geradheit prüfen ===")
print(f"Zeit: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Gefilterte Daten laden
with open(f"{OUTPUT_DIR}/stadtpark_fusswege_laenge_600_900.geojson", "r", encoding="utf-8") as f:
    data = json.load(f)

features = data["features"]
print(f"Geladene Wege: {len(features)}")

def haversine_distance(coord1, coord2):
    """Berechnet die direkte Distanz zwischen zwei Koordinaten in Metern."""
    R = 6371000
    lon1, lat1 = coord1
    lon2, lat2 = coord2
    
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c

def calculate_straightness(coords):
    """
    Berechnet die Geradheit eines Weges.
    Verhältnis von direkter Distanz (Start-Ende) zur tatsächlichen Weglänge.
    1.0 = perfekt gerade, niedriger = krümmer.
    """
    if len(coords) < 2:
        return 0.0
    
    direct_distance = haversine_distance(coords[0], coords[-1])
    
    # Tatsächliche Weglänge
    actual_length = 0.0
    for i in range(len(coords) - 1):
        actual_length += haversine_distance(coords[i], coords[i+1])
    
    if actual_length == 0:
        return 0.0
    
    return direct_distance / actual_length

# Geradheit für jeden Weg berechnen
print("\nBerechne Geradheit...")
for f in features:
    straightness = calculate_straightness(f["geometry"]["coordinates"])
    f["properties"]["straightness"] = round(straightness, 4)

# Sortieren nach Geradheit (höchste zuerst)
features.sort(key=lambda x: x["properties"]["straightness"], reverse=True)

# Anzeigen
print(f"\nWege nach Geradheit sortiert:")
for i, f in enumerate(features):
    props = f["properties"]
    print(f"  {i+1}. ID {props['id']}: {props['length_m']:.1f}m, "
          f"Geradheit: {props['straightness']:.4f} ({props['highway']})")

# Filter: nur Wege mit Geradheit >= 0.95 (sehr gerade)
threshold = 0.95
straight_ways = [f for f in features if f["properties"]["straightness"] >= threshold]
print(f"\nWege mit Geradheit >= {threshold}: {len(straight_ways)}")

# Speichern
output = {
    "type": "FeatureCollection",
    "features": straight_ways,
}

output_file = f"{OUTPUT_DIR}/stadtpark_fusswege_gerade.geojson"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False)

print(f"Gespeichert: {output_file}")

# Zusammenfassung
summary = {
    "zeitstempel": datetime.now().isoformat(),
    "schwelle_geradheit": threshold,
    "gesamt_weise": len(features),
    "gerade_weise": len(straight_ways),
    "wege": [
        {
            "id": f["properties"]["id"],
            "laenge_m": f["properties"]["length_m"],
            "geradheit": f["properties"]["straightness"],
            "highway": f["properties"]["highway"],
        }
        for f in features
    ],
}

with open(f"{OUTPUT_DIR}/schritt3_zusammenfassung.json", "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)

print(f"Zusammenfassung gespeichert: {OUTPUT_DIR}/schritt3_zusammenfassung.json")
print("\n=== Schritt 3 abgeschlossen ===")
