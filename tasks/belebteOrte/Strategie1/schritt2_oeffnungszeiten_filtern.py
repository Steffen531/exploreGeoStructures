"""
Schritt 2: Öffnungszeiten parsen und filtern
Filtert POIs, die dienstag vormittags (9-12 Uhr) geöffnet sind.
"""

import geopandas as gpd
import pandas as pd
import re
import json
from datetime import datetime

OUTPUT_DIR = "/mnt/c/Users/Entwickler/exploreGeoStructures/tasks/belebteOrte/Strategie1"

def ist_dienstag_vormittag_geoeffnet(opening_hours_str):
    """
    Prüft, ob ein POI dienstag vormittags (9-12 Uhr) geöffnet ist.
    Parst OSM opening_hours-Syntax.
    """
    if pd.isna(opening_hours_str) or opening_hours_str == "":
        return False
    
    oh = str(opening_hours_str).lower()
    
    # "24/7" oder "always" → immer geöffnet
    if "24/7" in oh or "always" in oh:
        return True
    
    # Nach "di" oder "tue" suchen (Dienstag)
    # OSM-Format: "Mo-Fr 09:00-17:00" oder "Di 09:00-12:00"
    
    # Prüfe ob Dienstag erwähnt wird
    hat_dienstag = bool(re.search(r'\b(di|tue|tues)\b', oh))
    
    # Prüfe ob "mo-fr" oder "mo-su" (alle Tage) → gilt auch für Dienstag
    hat_alle_wochentage = bool(re.search(r'\b(mo[-–]fr|mo[-–]su|mo[-–]so)\b', oh))
    
    if not (hat_dienstag or hat_alle_wochentage):
        return False
    
    # Zeiten extrahieren — prüfe ob 9-12 Uhr im Öffnungszeitraum liegt
    # Suche nach Zeitbereichen wie "09:00-17:00" oder "9:00-12:00"
    zeitbereiche = re.findall(r'(\d{1,2}):(\d{2})\s*[-–]\s*(\d{1,2}):(\d{2})', oh)
    
    if not zeitbereiche:
        # Keine Zeiten gefunden, aber Dienstag erwähnt → annehmen
        return True
    
    for start_h, start_m, end_h, end_m in zeitbereiche:
        start_zeit = int(start_h) * 60 + int(start_m)
        end_zeit = int(end_h) * 60 + int(end_m)
        
        # Vormittags: 9:00 (540) bis 12:00 (720)
        vormittags_start = 9 * 60
        vormittags_end = 12 * 60
        
        # Prüfe ob sich die Zeiträume überschneiden
        if start_zeit < vormittags_end and end_zeit > vormittags_start:
            return True
    
    return False

def main():
    # POIs laden
    input_pfad = f"{OUTPUT_DIR}/berlin_pois_alle.geojson"
    print(f"Lade POIs von {input_pfad}...")
    
    try:
        pois = gpd.read_file(input_pfad)
    except Exception as e:
        print(f"Fehler beim Laden: {e}")
        return
    
    print(f"{len(pois)} POIs geladen")
    
    # Öffnungszeiten filtern
    pois["dienstag_vormittag"] = pois["opening_hours"].apply(ist_dienstag_vormittag_geoeffnet)
    
    # Nur POIs mit Öffnungszeiten
    pois_mit_oh = pois[pois["opening_hours"].notna()].copy()
    print(f"POIs mit Öffnungszeiten: {len(pois_mit_oh)}")
    
    # POIs die dienstag vormittag geöffnet sind
    pois_dienstag = pois[pois["dienstag_vormittag"] == True].copy()
    print(f"POIs dienstag vormittag geöffnet: {len(pois_dienstag)}")
    
    # Speichern
    output_alle = f"{OUTPUT_DIR}/berlin_pois_mit_oeffnungszeiten.geojson"
    output_dienstag = f"{OUTPUT_DIR}/berlin_pois_dienstag_vormittag.geojson"
    
    pois.to_file(output_alle, driver="GeoJSON")
    pois_dienstag.to_file(output_dienstag, driver="GeoJSON")
    
    print(f"Gespeichert: {output_alle}")
    print(f"Gespeichert: {output_dienstag}")
    
    # Zusammenfassung
    zusammenfassung = {
        "zeitstempel": datetime.now().isoformat(),
        "gesamt_pois": len(pois),
        "mit_oeffnungszeiten": len(pois_mit_oh),
        "dienstag_vormittag_geoeffnet": len(pois_dienstag),
        "nach_typ_dienstag": pois_dienstag["poi_typ"].value_counts().to_dict(),
    }
    
    with open(f"{OUTPUT_DIR}/schritt2_zusammenfassung.json", "w", encoding="utf-8") as f:
        json.dump(zusammenfassung, f, ensure_ascii=False, indent=2)
    
    print(f"Zusammenfassung: {zusammenfassung}")

if __name__ == "__main__":
    main()
