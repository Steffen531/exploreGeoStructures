"""
Schritt 7: SVG-Karte erstellen
Erstellt eine statische SVG-Karte mit dem gefundenen Weg.
"""

import json
import math
from datetime import datetime

OUTPUT_DIR = "tasks/Fussweg/Strategie1"

print("=== Schritt 7: SVG-Karte erstellen ===")
print(f"Zeit: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Kandidaten laden
with open(f"{OUTPUT_DIR}/stadtpark_fusswege_gerade.geojson", "r", encoding="utf-8") as f:
    data = json.load(f)

# Gewinner
winner = None
for f in data["features"]:
    if f["properties"]["id"] == 41376998:
        winner = f
        break

if not winner:
    print("Gewinner nicht gefunden!")
    exit(1)

coords = winner["geometry"]["coordinates"]
print(f"Gewinner: ID {winner['properties']['id']}, {winner['properties']['length_m']:.1f}m")

# Bounding Box berechnen
lons = [c[0] for c in coords]
lats = [c[1] for c in coords]

min_lon, max_lon = min(lons), max(lons)
min_lat, max_lat = min(lats), max(lats)

# SVG Dimensionen
width = 800
height = 600
padding = 50

# Skalierung
lon_range = max_lon - min_lon
lat_range = max_lat - min_lat

# Seitenverhältnis beibehalten
scale_x = (width - 2 * padding) / lon_range
scale_y = (height - 2 * padding) / lat_range
scale = min(scale_x, scale_y)

# Zentrieren
offset_x = (width - lon_range * scale) / 2
offset_y = (height - lat_range * scale) / 2

def lon_lat_to_svg(lon, lat):
    x = offset_x + (lon - min_lon) * scale
    y = height - (offset_y + (lat - min_lat) * scale)  # Y-Achse umkehren
    return x, y

# Weg als SVG-Polyline
points = []
for c in coords:
    x, y = lon_lat_to_svg(c[0], c[1])
    points.append(f"{x:.1f},{y:.1f}")

points_str = " ".join(points)

# Start- und Endpunkte
start_x, start_y = lon_lat_to_svg(coords[0][0], coords[0][1])
end_x, end_y = lon_lat_to_svg(coords[-1][0], coords[-1][1])

# SVG erstellen
svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
    <defs>
        <style>
            .background {{ fill: #f0f0f0; }}
            .path {{ fill: none; stroke: #e74c3c; stroke-width: 4; stroke-linecap: round; stroke-linejoin: round; }}
            .start {{ fill: #27ae60; }}
            .end {{ fill: #e74c3c; }}
            .label {{ font-family: Arial, sans-serif; font-size: 14px; fill: #333; }}
            .title {{ font-family: Arial, sans-serif; font-size: 18px; font-weight: bold; fill: #333; }}
            .info {{ font-family: Arial, sans-serif; font-size: 12px; fill: #666; }}
        </style>
    </defs>
    
    <!-- Hintergrund -->
    <rect class="background" width="{width}" height="{height}"/>
    
    <!-- Titel -->
    <text class="title" x="{width//2}" y="30" text-anchor="middle">Gefundener Fußweg in Hamburg</text>
    
    <!-- Weg -->
    <polyline class="path" points="{points_str}"/>
    
    <!-- Startpunkt -->
    <circle class="start" cx="{start_x:.1f}" cy="{start_y:.1f}" r="8"/>
    <text class="label" x="{start_x + 12:.1f}" y="{start_y - 12:.1f}">Start</text>
    
    <!-- Endpunkt -->
    <circle class="end" cx="{end_x:.1f}" cy="{end_y:.1f}" r="8"/>
    <text class="label" x="{end_x + 12:.1f}" y="{end_y + 20:.1f}">Ende</text>
    
    <!-- Info-Box -->
    <rect x="10" y="{height - 80}" width="280" height="70" fill="white" stroke="#ccc" rx="5"/>
    <text class="info" x="20" y="{height - 60}">OSM ID: {winner['properties']['id']}</text>
    <text class="info" x="20" y="{height - 40}">Länge: {winner['properties']['length_m']:.1f}m (~10 Minuten)</text>
    <text class="info" x="20" y="{height - 20}">Geradheit: {winner['properties']['straightness']:.4f}</text>
</svg>
"""

output_file = f"{OUTPUT_DIR}/ergebnis_karte.svg"
with open(output_file, "w", encoding="utf-8") as f:
    f.write(svg)

print(f"SVG-Karte gespeichert: {output_file}")
print("\n=== Schritt 7 abgeschlossen ===")
