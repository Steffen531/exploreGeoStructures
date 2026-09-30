"""
Schritt 2: Nach Länge filtern
Filtert Fußwege mit einer Länge von 700-800m (ca. 10 Minuten Gehzeit).
"""

import json
import math
from datetime import datetime

OUTPUT_DIR = "tasks/Fussweg/Strategie1"

print("=== Schritt 2: Nach Länge filtern ===")
print(f"Zeit: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Rohdaten laden
with open(f"{OUTPUT_DIR}/stadtpark_fusswege_raw.geojson", "r", encoding="utf-8") as f:
    data = json.load(f)

features = data["features"]
print(f"Geladene Wege: {len(features)}")

# Länge für jedes Feature berechnen (Haversine-Formel)
def haversine_length(coords):
    """Berechnet die Länge einer Koordinatenliste in Metern."""
    total = 0.0
    R = 6371000  # Erdradius in Metern
    
    for i in range(len(coords) - 1):
        lon1, lat1 = coords[i]
        lon2, lat2 = coords[i + 1]
        
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        
        a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        total += R * c
    
    return total

# Längen berechnen
print("\nBerechne Längen...")
for f in features:
    f["properties"]["length_m"] = haversine_length(f["geometry"]["coordinates"])

# Längen-Statistiken
lengths = [f["properties"]["length_m"] for f in features]
print(f"\nLängen-Statistiken:")
print(f"  Min: {min(lengths):.1f}m")
print(f"  Max: {max(lengths):.1f}m")
print(f"  Mittel: {sum(lengths)/len(lengths):.1f}m")

# Nach Länge filtern (700-800m für ~10 Minuten)
# Etwas breiteren Bereich nehmen: 600-900m
min_len = 600
max_len = 900

filtered = [f for f in features if min_len <= f["properties"]["length_m"] <= max_len]
print(f"\nWege mit {min_len}-{max_len}m: {len(filtered)}")

# Sortieren nach Länge
filtered.sort(key=lambda x: x["properties"]["length_m"])

# Anzeigen
print(f"\nTop 20 Wege (nach Länge):")
for i, f in enumerate(filtered[:20]):
    props = f["properties"]
    print(f"  {i+1}. ID {props['id']}: {props['length_m']:.1f}m ({props['highway']}) {props.get('name', '')}")

# Speichern
output = {
    "type": "FeatureCollection",
    "features": filtered,
}

output_file = f"{OUTPUT_DIR}/stadtpark_fusswege_laenge_600_900.geojson"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False)

print(f"\nGespeichert: {output_file}")

# Zusammenfassung
summary = {
    "zeitstempel": datetime.now().isoformat(),
    "filter": f"{min_len}-{max_len}m",
    "gesamt_weise": len(features),
    "gefilterte_weise": len(filtered),
    "laenge_m": {
        "min": min(lengths),
        "max": max(lengths),
        "mean": sum(lengths) / len(lengths),
    },
}

with open(f"{OUTPUT_DIR}/schritt2_zusammenfassung.json", "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)

print(f"Zusammenfassung gespeichert: {OUTPUT_DIR}/schritt2_zusammenfassung.json")
print("\n=== Schritt 2 abgeschlossen ===")
