"""
Schritt 4: Parallelwege prüfen
Verwendet die bereits geladenen Stadtpark-Daten, um die Umgebung der Kandidaten
zu analysieren und parallel verlaufende Verkehrswege zu finden.
"""

import json
import math
from datetime import datetime

OUTPUT_DIR = "tasks/Fussweg/Strategie1"

print("=== Schritt 4: Parallelwege prüfen ===")
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

def point_to_segment_distance(point, seg_start, seg_end):
    """Berechnet den kürzesten Abstand eines Punkts zu einem Streckenabschnitt."""
    # Vereinfachte Berechnung für kleine Distanzen
    px, py = point
    x1, y1 = seg_start
    x2, y2 = seg_end
    
    # Vom Punkt zum Startpunkt
    dx = x2 - x1
    dy = y2 - y1
    
    if dx == 0 and dy == 0:
        return haversine_distance(point, seg_start)
    
    # Projektion
    t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx*dx + dy*dy)))
    
    # Nächster Punkt auf der Strecke
    nearest_x = x1 + t * dx
    nearest_y = y1 + t * dy
    
    return haversine_distance(point, (nearest_x, nearest_y))

def min_distance_between_paths(coords1, coords2):
    """Berechnet den minimalen Abstand zwischen zwei Wegen."""
    min_dist = float('inf')
    
    # Stichproben entlang des ersten Weges
    step = max(1, len(coords1) // 50)
    for i in range(0, len(coords1), step):
        point = coords1[i]
        
        # Abstand zu jedem Segment des zweiten Weges
        for j in range(len(coords2) - 1):
            dist = point_to_segment_distance(point, coords2[j], coords2[j+1])
            if dist < min_dist:
                min_dist = dist
    
    return min_dist

# Für jeden Kandidaten die Umgebung analysieren
print("\nAnalysiere Umgebung der Kandidaten...")
print("(Suche nach parallelen Wegen im Stadtpark)")

results = []

for candidate in candidates:
    cand_id = candidate["properties"]["id"]
    cand_coords = candidate["geometry"]["coordinates"]
    cand_length = candidate["properties"]["length_m"]
    
    print(f"\n--- Kandidat {cand_id} ({cand_length:.1f}m) ---")
    
    # Finde alle Wege, die nahe am Kandidaten verlaufen
    nearby_ways = []
    
    for other in all_features:
        other_id = other["properties"]["id"]
        if other_id == cand_id:
            continue
        
        other_coords = other["geometry"]["coordinates"]
        
        # Schnelle Prüfung: Start- und Endpunkte
        dist_start = haversine_distance(cand_coords[0], other_coords[0])
        dist_end = haversine_distance(cand_coords[-1], other_coords[-1])
        
        # Wenn Start oder Ende nahebei, detaillierter prüfen
        if dist_start < 100 or dist_end < 100:
            min_dist = min_distance_between_paths(cand_coords, other_coords)
            
            if min_dist < 50:  # Weniger als 50m Abstand
                nearby_ways.append({
                    "id": other_id,
                    "highway": other["properties"]["highway"],
                    "name": other["properties"].get("name", ""),
                    "min_dist_m": round(min_dist, 1),
                })
    
    print(f"  Parallele Wege (< 50m Abstand): {len(nearby_ways)}")
    for w in nearby_ways[:5]:
        print(f"    - ID {w['id']}: {w['highway']} '{w['name']}' ({w['min_dist_m']}m)")
    
    results.append({
        "id": cand_id,
        "laenge_m": cand_length,
        "geradheit": candidate["properties"]["straightness"],
        "parallele_weise": nearby_ways,
        "anzahl_parallele": len(nearby_ways),
    })

# Kandidaten ohne parallele Wege
isolated = [r for r in results if r["anzahl_parallele"] == 0]
print(f"\n=== Ergebnis ===")
print(f"Kandidaten ohne parallele Wege: {len(isolated)}")
for r in isolated:
    print(f"  - ID {r['id']}: {r['laenge_m']:.1f}m, Geradheit {r['geradheit']:.4f}")

# Speichern
output = {
    "zeitstempel": datetime.now().isoformat(),
    "kandidaten": results,
    "isolierte_kandidaten": isolated,
}

with open(f"{OUTPUT_DIR}/schritt4_ergebnis.json", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"\nErgebnis gespeichert: {OUTPUT_DIR}/schritt4_ergebnis.json")
print("\n=== Schritt 4 abgeschlossen ===")
