"""
Schritt 3: POI-Dichte berechnen und Hotspots identifizieren
Verwendet ein Grid, um die Dichte von dienstag-vormittag-geöffneten POIs zu berechnen.
"""

import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry import box
import json
from datetime import datetime

OUTPUT_DIR = "/mnt/c/Users/Entwickler/exploreGeoStructures/tasks/belebteOrte/Strategie1"

def grid_erstellen(pois, zellengroesse=0.001):
    """
    Erstellt ein Grid über die POIs und zählt die POIs pro Zelle.
    zellengroesse: Grad (ca. 100m bei 0.001)
    """
    # Bounding Box der POIs
    minx, miny, maxx, maxy = pois.total_bounds
    
    # Grid-Zellen erstellen
    x_koordinaten = np.arange(minx, maxx, zellengroesse)
    y_koordinaten = np.arange(miny, maxy, zellengroesse)
    
    zellen = []
    for x in x_koordinaten:
        for y in y_koordinaten:
            zellen.append(box(x, y, x + zellengroesse, y + zellengroesse))
    
    grid = gpd.GeoDataFrame({"geometry": zellen}, crs=pois.crs)
    return grid

def dichte_berechnen(pois, grid):
    """Zählt POIs pro Grid-Zelle."""
    # Spatial Join: POIs zu Grid-Zellen zuordnen
    pois_in_zellen = gpd.sjoin(pois, grid, how="inner", predicate="within")
    
    # POIs pro Zelle zählen
    zaehlung = pois_in_zellen.groupby("index_right").size()
    grid["poi_anzahl"] = 0
    grid.loc[zaehlung.index, "poi_anzahl"] = zaehlung.values
    
    return grid

def hotspots_identifizieren(grid, top_n=20, min_pois=5):
    """Identifiziert die Top-N Grid-Zellen mit den meisten POIs."""
    # Filtern nach Mindestanzahl POIs
    relevante_zellen = grid[grid["poi_anzahl"] >= min_pois].copy()
    
    # Sortieren nach POI-Anzahl
    top_zellen = relevante_zellen.nlargest(top_n, "poi_anzahl")
    
    # Zentroid berechnen (als separate Spalten, nicht als Geometry)
    zentroiden = top_zellen.geometry.centroid
    top_zellen["lat"] = zentroiden.y
    top_zellen["lon"] = zentroiden.x
    
    return top_zellen

def main():
    # POIs laden
    input_pfad = f"{OUTPUT_DIR}/berlin_pois_dienstag_vormittag.geojson"
    print(f"Lade POIs von {input_pfad}...")
    
    try:
        pois = gpd.read_file(input_pfad)
    except Exception as e:
        print(f"Fehler beim Laden: {e}")
        return
    
    print(f"{len(pois)} POIs geladen")
    
    # Grid erstellen
    print("Erstelle Grid...")
    grid = grid_erstellen(pois, zellengroesse=0.001)  # ca. 100m
    print(f"{len(grid)} Grid-Zellen erstellt")
    
    # Dichte berechnen
    print("Berechne Dichte...")
    grid = dichte_berechnen(pois, grid)
    
    # Hotspots identifizieren
    print("Identifiziere Hotspots...")
    hotspots = hotspots_identifizieren(grid, top_n=20, min_pois=3)
    print(f"{len(hotspots)} Hotspots identifiziert")
    
    # Speichern
    output_grid = f"{OUTPUT_DIR}/berlin_poi_dichte_grid.geojson"
    output_hotspots = f"{OUTPUT_DIR}/berlin_poi_hotspots.geojson"
    
    grid.to_file(output_grid, driver="GeoJSON")
    hotspots.to_file(output_hotspots, driver="GeoJSON")
    
    print(f"Gespeichert: {output_grid}")
    print(f"Gespeichert: {output_hotspots}")
    
    # Zusammenfassung
    zusammenfassung = {
        "zeitstempel": datetime.now().isoformat(),
        "gesamt_pois": len(pois),
        "grid_zellen": len(grid),
        "hotspots_identifiziert": len(hotspots),
        "top_10_hotspots": hotspots.head(10)[["poi_anzahl", "lat", "lon"]].to_dict("records"),
    }
    
    with open(f"{OUTPUT_DIR}/schritt3_zusammenfassung.json", "w", encoding="utf-8") as f:
        json.dump(zusammenfassung, f, ensure_ascii=False, indent=2)
    
    print(f"Zusammenfassung: {zusammenfassung}")

if __name__ == "__main__":
    main()
