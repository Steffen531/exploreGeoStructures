"""
Schritt 4: BVG GTFS-Daten laden und auswerten
Lädt GTFS-Daten der BVG und berechnet die ÖPNV-Frequenz vormittags.
"""

import pandas as pd
import geopandas as gpd
import requests
import zipfile
import io
import os
import json
from datetime import datetime
from shapely.geometry import Point

OUTPUT_DIR = "/mnt/c/Users/Entwickler/exploreGeoStructures/tasks/belebteOrte/Strategie1"
GTFS_URL = "https://www.vbb.de/vbbgtfs"

def gtfs_laden(url):
    """Lädt GTFS-Daten von der URL und entpackt sie."""
    print(f"Lade GTFS-Daten von {url}...")
    
    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        
        # ZIP entpacken
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            z.extractall(f"{OUTPUT_DIR}/gtfs_data")
        
        print("GTFS-Daten erfolgreich geladen und entpackt")
        return True
    except Exception as e:
        print(f"Fehler beim Laden der GTFS-Daten: {e}")
        return False

def haltestellen_laden():
    """Lädt Haltestellen aus den GTFS-Daten."""
    try:
        stops = pd.read_csv(f"{OUTPUT_DIR}/gtfs_data/stops.txt")
        print(f"{len(stops)} Haltestellen geladen")
        return stops
    except Exception as e:
        print(f"Fehler beim Laden der Haltestellen: {e}")
        return None

def stop_times_laden():
    """Lädt stop_times aus den GTFS-Daten."""
    try:
        stop_times = pd.read_csv(f"{OUTPUT_DIR}/gtfs_data/stop_times.txt")
        print(f"{len(stop_times)} stop_times geladen")
        return stop_times
    except Exception as e:
        print(f"Fehler beim Laden der stop_times: {e}")
        return None

def calendar_laden():
    """Lädt calendar aus den GTFS-Daten."""
    try:
        calendar = pd.read_csv(f"{OUTPUT_DIR}/gtfs_data/calendar.txt")
        print(f"{len(calendar)} calendar-Einträge geladen")
        return calendar
    except Exception as e:
        print(f"Fehler beim Laden des calendar: {e}")
        return None

def dienstag_frequenz_berechnen(stop_times, calendar):
    """
    Berechnet die Frequenz der Abfahrten an Dienstag vormittags.
    """
    # Filtere Linien, die dienstag verkehren
    dienstag_service = calendar[calendar["tuesday"] == 1]["service_id"].unique()
    print(f"{len(dienstag_service)} Linien verkehren dienstag")
    
    # Lade trips um service_id zu bekommen
    try:
        trips = pd.read_csv(f"{OUTPUT_DIR}/gtfs_data/trips.txt")
    except Exception as e:
        print(f"Fehler beim Laden der trips: {e}")
        return None
    
    # Filtere trips auf dienstag
    trips_dienstag = trips[trips["service_id"].isin(dienstag_service)]
    print(f"{len(trips_dienstag)} trips dienstag")
    
    # Stop_times mit trips verbinden
    stop_times_dienstag = stop_times[stop_times["trip_id"].isin(trips_dienstag["trip_id"])]
    print(f"{len(stop_times_dienstag)} stop_times dienstag")
    
    # Filtere auf vormittags (9-12 Uhr)
    # GTFS-Zeiten können "HH:MM:SS" oder "H:MM:SS" sein
    stop_times_dienstag["hour"] = stop_times_dienstag["arrival_time"].str.split(":").str[0].astype(int)
    vormittags = stop_times_dienstag[
        (stop_times_dienstag["hour"] >= 9) & (stop_times_dienstag["hour"] < 12)
    ]
    print(f"{len(vormittags)} stop_times dienstag vormittags")
    
    # Frequenz pro Haltestelle berechnen
    frequenz = vormittags.groupby("stop_id").size().reset_index(name="vormittags_frequenz")
    
    return frequenz

def main():
    # GTFS-Daten laden
    if not gtfs_laden(GTFS_URL):
        print("GTFS-Daten konnten nicht geladen werden. Überspringe Schritt 4.")
        return
    
    # Daten laden
    stops = haltestellen_laden()
    stop_times = stop_times_laden()
    calendar = calendar_laden()
    
    if stops is None or stop_times is None or calendar is None:
        print("Nicht alle GTFS-Daten konnten geladen werden. Abbruch.")
        return
    
    # Frequenz berechnen
    print("Berechne Dienstag-Vormittags-Frequenz...")
    frequenz = dienstag_frequenz_berechnen(stop_times, calendar)
    
    if frequenz is None:
        print("Frequenz konnte nicht berechnet werden. Abbruch.")
        return
    
    # Mit Haltestellen verbinden
    haltestellen_freq = stops.merge(frequenz, left_on="stop_id", right_on="stop_id", how="left")
    haltestellen_freq["vormittags_frequenz"] = haltestellen_freq["vormittags_frequenz"].fillna(0)
    
    # Als GeoDataFrame speichern
    geometry = [Point(xy) for xy in zip(haltestellen_freq["stop_lon"], haltestellen_freq["stop_lat"])]
    haltestellen_gdf = gpd.GeoDataFrame(haltestellen_freq, geometry=geometry, crs="EPSG:4326")
    
    # Speichern
    output_pfad = f"{OUTPUT_DIR}/berlin_haltestellen_frequenz.geojson"
    haltestellen_gdf.to_file(output_pfad, driver="GeoJSON")
    print(f"Gespeichert: {output_pfad}")
    
    # Top 20 Haltestellen nach Frequenz
    top20 = haltestellen_gdf.nlargest(20, "vormittags_frequenz")
    
    # Zusammenfassung
    zusammenfassung = {
        "zeitstempel": datetime.now().isoformat(),
        "gesamt_haltestellen": len(haltestellen_gdf),
        "haltestellen_mit_frequenz": len(haltestellen_gdf[haltestellen_gdf["vormittags_frequenz"] > 0]),
        "top_20_haltestellen": top20[["stop_name", "vormittags_frequenz", "stop_lat", "stop_lon"]].to_dict("records"),
    }
    
    with open(f"{OUTPUT_DIR}/schritt4_zusammenfassung.json", "w", encoding="utf-8") as f:
        json.dump(zusammenfassung, f, ensure_ascii=False, indent=2)
    
    print(f"Zusammenfassung: {zusammenfassung}")

if __name__ == "__main__":
    main()
