"""
Schritt 5: Abzweigungen prüfen
Prüft, ob der Kandidaten-Weg Verbindungen zu anderen Wegen hat (Abzweigungen).
"""

import json
import math
from datetime import datetime

OUTPUT_DIR = "tasks/Fussweg/Strategie1"

print("=== Schritt 5: Abzweigungen prüfen ===")
print(f"Zeit: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Kandidaten laden
with open(f"{OUTPUT_DIR}/stadtpark_fusswege_gerade.geojson", "r", encoding="utf-8") as f:
    data = json.load(f)

candidates = data["features"]
print(f"Kandidaten: {len(candidates)}")

# Alle Stadtpark-Wege laden
with open(f"{OUTPUT_DIR}/stadtpark_fusswege_raw.geojson", "r", encoding="utf-8") as f:
    all_data = json.load(f)

all_features = all_data["features"]
print(f"Alle Stadtpark-Wege: {len(all_features)}")

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

def coords_equal(c1, c2, tolerance=0.00001):
    """Prüft, ob zwei Koordinaten (fast) gleich sind."""
    return abs(c1[0] - c2[0]) < tolerance and abs(c1[1] - c2[1]) < tolerance

def find_connections(candidate_coords, all_features, candidate_id):
    """
    Findet alle Wege, die mit dem Kandidaten verbunden sind
    (gemeinsame Start- oder Endpunkte).
    """
    connections = []
    
    cand_start = candidate_coords[0]
    cand_end = candidate_coords[-1]
    
    for other in all_features:
        other_id = other["properties"]["id"]
        if other_id == candidate_id:
            continue
        
        other_coords = other["geometry"]["coordinates"]
        other_start = other_coords[0]
        other_end = other_coords[-1]
        
        # Prüfe ob Start oder Endpunkte übereinstimsten
        start_match = coords_equal(cand_start, other_start) or coords_equal(cand_start, other_end)
        end_match = coords_equal(cand_end, other_start) or coords_equal(cand_end, other_end)
        
        if start_match or end_match:
            connections.append({
                "id": other_id,
                "highway": other["properties"]["highway"],
                "name": other["properties"].get("name", ""),
                "verbindung": "start" if start_match else "ende",
            })
    
    return connections

# Für jeden Kandidaten Abzweigungen prüfen
print("\nPrüfe Abzweigungen...")

results = []

for candidate in candidates:
    cand_id = candidate["properties"]["id"]
    cand_coords = candidate["geometry"]["coordinates"]
    cand_length = candidate["properties"]["length_m"]
    
    print(f"\n--- Kandidat {cand_id} ({cand_length:.1f}m) ---")
    
    connections = find_connections(cand_coords, all_features, cand_id)
    
    print(f"  Abzweigungen: {len(connections)}")
    for c in connections[:10]:
        print(f"    - ID {c['id']}: {c['highway']} '{c['name']}' ({c['verbindung']})")
    
    results.append({
        "id": cand_id,
        "laenge_m": cand_length,
        "geradheit": candidate["properties"]["straightness"],
        "abzweigungen": connections,
        "anzahl_abzweigungen": len(connections),
    })

# Kandidaten ohne Abzweigungen
no_branches = [r for r in results if r["anzahl_abzweigungen"] == 0]
print(f"\n=== Ergebnis ===")
print(f"Kandidaten ohne Abzweigungen: {len(no_branches)}")
for r in no_branches:
    print(f"  - ID {r['id']}: {r['laenge_m']:.1f}m, Geradheit {r['geradheit']:.4f}")

# Speichern
output = {
    "zeitstempel": datetime.now().isoformat(),
    "kandidaten": results,
    "kandidaten_ohne_abzweigungen": no_branches,
}

with open(f"{OUTPUT_DIR}/schritt5_ergebnis.json", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"\nErgebnis gespeichert: {OUTPUT_DIR}/schritt5_ergebnis.json")
print("\n=== Schritt 5 abgeschlossen ===")
