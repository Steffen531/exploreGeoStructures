"""
Schritt 5: Ergebnisse zusammenführen und rangieren
Kombiniert POI-Hotspots und ÖPNV-Frequenz zu einer rangierten Liste belebter Orte.
"""

import geopandas as gpd
import pandas as pd
import json
from datetime import datetime
from shapely.geometry import Point

OUTPUT_DIR = "/mnt/c/Users/Entwickler/exploreGeoStructures/tasks/belebteOrte/Strategie1"

def main():
    # POI-Hotspots laden
    print("Lade POI-Hotspots...")
    try:
        hotspots = gpd.read_file(f"{OUTPUT_DIR}/berlin_poi_hotspots.geojson")
        print(f"{len(hotspots)} POI-Hotspots geladen")
    except Exception as e:
        print(f"Fehler beim Laden der POI-Hotspots: {e}")
        hotspots = None
    
    # ÖPNV-Haltestellen laden
    print("Lade ÖPNV-Haltestellen...")
    try:
        haltestellen = gpd.read_file(f"{OUTPUT_DIR}/berlin_haltestellen_frequenz.geojson")
        print(f"{len(haltestellen)} Haltestellen geladen")
    except Exception as e:
        print(f"Fehler beim Laden der Haltestellen: {e}")
        haltestellen = None
    
    # Ergebnisse zusammenführen
    ergebnisse = []
    
    if hotspots is not None and len(haltestellen) > 0:
        # Für jeden POI-Hotspot die nächste Haltestelle finden
        for idx, hotspot in hotspots.iterrows():
            zentroid = hotspot.geometry.centroid
            
            # Distanz zu allen Haltestellen berechnen
            haltestellen["distanz"] = haltestellen.geometry.distance(zentroid)
            
            # Nächste Haltestelle
            naechste = haltestellen.loc[haltestellen["distanz"].idxmin()]
            
            ergebnis = {
                "rang": 0,
                "poi_anzahl": hotspot["poi_anzahl"],
                "lat": hotspot["lat"],
                "lon": hotspot["lon"],
                "naechste_haltestelle": naechste["stop_name"],
                "haltestellen_distanz_m": round(naechste["distanz"] * 111000),  # ungefähre Meter
                "oepnv_frequenz_vormittags": naechste["vormittags_frequenz"],
                "gesamt_score": hotspot["poi_anzahl"] + naechste["vormittags_frequenz"],
            }
            ergebnisse.append(ergebnis)
    
    # Nach Gesamt-Score sortieren
    ergebnisse_df = pd.DataFrame(ergebnisse)
    if len(ergebnisse_df) > 0:
        ergebnisse_df = ergebnisse_df.sort_values("gesamt_score", ascending=False)
        ergebnisse_df["rang"] = range(1, len(ergebnisse_df) + 1)
    
    # Speichern
    output_pfad = f"{OUTPUT_DIR}/berlin_belebte_orte_rangiert.json"
    with open(output_pfad, "w", encoding="utf-8") as f:
        json.dump(ergebnisse_df.to_dict("records"), f, ensure_ascii=False, indent=2)
    print(f"Gespeichert: {output_pfad}")
    
    # Zusammenfassung
    zusammenfassung = {
        "zeitstempel": datetime.now().isoformat(),
        "gesamt_orte": len(ergebnisse_df),
        "top_10_orte": ergebnisse_df.head(10).to_dict("records"),
    }
    
    with open(f"{OUTPUT_DIR}/schritt5_zusammenfassung.json", "w", encoding="utf-8") as f:
        json.dump(zusammenfassung, f, ensure_ascii=False, indent=2)
    
    print(f"Zusammenfassung: {zusammenfassung}")
    
    # Ergebnis ausgeben
    print("\n=== Top 10 belebte Orte (Dienstag Vormittag) ===")
    for _, ort in ergebnisse_df.head(10).iterrows():
        print(f"{ort['rang']}. POIs: {ort['poi_anzahl']}, ÖPNV: {ort['oepnv_frequenz_vormittags']}, "
              f"Haltestelle: {ort['naechste_haltestelle']}, Score: {ort['gesamt_score']}")

if __name__ == "__main__":
    main()
