"""
Schritt 1: OSM-POIs für Berlin-Pankow abrufen
Datenquelle: Overpass API (OpenStreetMap)
"""

import osmnx as ox
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
import json
from datetime import datetime

OUTPUT_DIR = "/mnt/c/Users/Entwickler/exploreGeoStructures/tasks/belebteOrte/Strategie1"

BEZIRK = "Pankow, Berlin, Deutschland"

def pois_fuer_bezirk_abrufen():
    """POIs für Pankow abrufen."""
    tags = {
        "shop": True,
        "amenity": True,
        "office": True,
        "tourism": True,
        "leisure": True,
        "building": True,
    }
    
    try:
        pois = ox.features_from_place(BEZIRK, tags=tags)
        print(f"{len(pois)} POIs für {BEZIRK} abgerufen")
        return pois
    except Exception as e:
        print(f"Fehler beim Abrufen: {e}")
        return None

def pois_bereinigen(pois):
    """POIs bereinigen und relevante Spalten extrahieren."""
    if pois is None or len(pois) == 0:
        return None
    
    relevante_spalten = ["name", "shop", "amenity", "office", "tourism", "leisure", 
                         "building", "opening_hours", "geometry"]
    
    vorhandene_spalten = [col for col in relevante_spalten if col in pois.columns]
    pois_bereinigt = pois[vorhandene_spalten].copy()
    
    def poi_typ_zeile(row):
        for typ in ["shop", "amenity", "office", "tourism", "leisure", "building"]:
            if pd.notna(row.get(typ)):
                return typ
        return "unbekannt"
    
    pois_bereinigt["poi_typ"] = pois_bereinigt.apply(poi_typ_zeile, axis=1)
    
    return pois_bereinigt

def main():
    print(f"Rufe POIs für {BEZIRK} ab...")
    pois = pois_fuer_bezirk_abrufen()
    
    if pois is None:
        print("Keine POIs abgerufen. Abbruch.")
        return
    
    pois_bereinigt = pois_bereinigen(pois)
    
    if pois_bereinigt is None:
        print("Keine POIs nach Bereinigung übrig. Abbruch.")
        return
    
    output_pfad = f"{OUTPUT_DIR}/berlin_pois_alle.geojson"
    pois_bereinigt.to_file(output_pfad, driver="GeoJSON")
    print(f"POIs gespeichert: {output_pfad}")
    
    zusammenfassung = {
        "zeitstempel": datetime.now().isoformat(),
        "bezirk": BEZIRK,
        "gesamt_pois": int(len(pois_bereinigt)),
        "nach_typ": {str(k): int(v) for k, v in pois_bereinigt["poi_typ"].value_counts().items()},
        "mit_oeffnungszeiten": int(pois_bereinigt["opening_hours"].notna().sum()),
    }
    
    with open(f"{OUTPUT_DIR}/schritt1_zusammenfassung.json", "w", encoding="utf-8") as f:
        json.dump(zusammenfassung, f, ensure_ascii=False, indent=2)
    
    print(f"Zusammenfassung: {zusammenfassung}")

if __name__ == "__main__":
    main()
