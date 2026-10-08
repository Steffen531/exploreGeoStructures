"""
MallsEtc – Dresden Analyse
Strategie 3: Kombinierte Filter-Logik
Sucht besondere städtische Strukturen (Malls, Bahnhöfe, Passagen) mit:
  - mehreren Ausgängen
  - Ausgängen auf unterschiedlichen Ebenen
  - Anbindung an öffentliche Verkehrsmittel
"""

import osmnx as ox
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
import warnings
warnings.filterwarnings("ignore")

PLACE = "Dresden, Deutschland"
OUTPUT_DIR = "tasks/MallsEtc/Dresden_Ergebnisse"

print("=" * 60)
print("MallsEtc – Dresden Analyse")
print("=" * 60)

# ---------------------------------------------------------------------------
# Schritt 1: Gebäude mit relevanten building-Tags extrahieren
# ---------------------------------------------------------------------------
print("\n[1/5] Lade Gebäude (mall, train_station, retail)...")

building_tags = {
    "building": ["mall", "train_station", "retail", "supermarket", "department_store"]
}
buildings = ox.features_from_place(PLACE, tags=building_tags)
print(f"      {len(buildings)} Gebäude gefunden")

# ---------------------------------------------------------------------------
# Schritt 2: ÖPNV-Haltestellen abrufen
# ---------------------------------------------------------------------------
print("\n[2/5] Lade ÖPNV-Haltestellen...")

transit_tags = {
    "public_transport": ["station", "stop_position", "platform"],
    "railway": ["station", "halt", "tram_stop"],
    "amenity": ["bus_station"]
}
transit = ox.features_from_place(PLACE, tags=transit_tags)
print(f"      {len(transit)} ÖPNV-Objekte gefunden")

# ---------------------------------------------------------------------------
# Schritt 3: Eingänge (entrance) an Gebäudepolygonen zählen
# ---------------------------------------------------------------------------
print("\n[3/5] Lade Eingänge (entrance)...")

entrance_tags = {"entrance": ["yes", "main", "exit", "service", "staircase", "elevator"]}
try:
    entrances = ox.features_from_place(PLACE, tags=entrance_tags)
    print(f"      {len(entrances)} Eingänge gefunden")
except Exception as e:
    print(f"      Keine Eingänge gefunden: {e}")
    entrances = gpd.GeoDataFrame()

# ---------------------------------------------------------------------------
# Schritt 4: Pufferanalyse – Gebäude mit ÖPNV in der Nähe + Eingänge zählen
# ---------------------------------------------------------------------------
print("\n[4/5] Analysiere ÖPNV-Nähe und Eingänge...")

# Zentroide der Gebäude verwenden für Pufferanalyse
buildings["centroid"] = buildings.geometry.centroid

# Puffer von 200m um Gebäude-Zentroide
buffer_dist = 200
buildings["buffer"] = buildings["centroid"].buffer(buffer_dist)

# Für jedes Gebäude: ÖPNV-Objekte im Puffer zählen
transit_points = transit.copy()
transit_points["centroid"] = transit_points.geometry.centroid

results = []
for idx, bldg in buildings.iterrows():
    bldg_buffer = bldg["buffer"]
    
    # ÖPNV-Objekte im Puffer finden
    nearby_transit = transit_points[transit_points["centroid"].within(bldg_buffer)]
    transit_count = len(nearby_transit)
    
    # Eingänge im Puffer zählen
    entrance_count = 0
    if len(entrances) > 0:
        entrances["centroid"] = entrances.geometry.centroid
        nearby_entrances = entrances[entrances["centroid"].within(bldg_buffer)]
        entrance_count = len(nearby_entrances)
    
    # level-Tags sammeln
    levels = bldg.get("level", "")
    if pd.isna(levels):
        levels = ""
    
    results.append({
        "osm_id": idx[1] if isinstance(idx, tuple) else idx,
        "osm_type": idx[0] if isinstance(idx, tuple) else "unknown",
        "name": bldg.get("name", ""),
        "building": bldg.get("building", ""),
        "levels": str(levels),
        "entrance_count": entrance_count,
        "transit_count": transit_count,
        "geometry": bldg.geometry
    })

import pandas as pd
results_gdf = gpd.GeoDataFrame(results, crs=buildings.crs)

# ---------------------------------------------------------------------------
# Schritt 5: Filtere nach Kriterien und exportiere als KML
# ---------------------------------------------------------------------------
print("\n[5/5] Filtere und exportiere Ergebnisse...")

# Kriterien: mind. 2 Eingänge UND mind. 1 ÖPNV-Objekt in 200m
filtered = results_gdf[
    (results_gdf["entrance_count"] >= 2) & 
    (results_gdf["transit_count"] >= 1)
].copy()

# Sortiere nach Einganzahl (absteigend)
filtered = filtered.sort_values("entrance_count", ascending=False)

print(f"      {len(filtered)} Gebäude erfüllen die Kriterien")
print(f"      (≥2 Eingänge UND ≥1 ÖPNV-Anbindung in 200m)")

# KML-Export
kml_path = f"{OUTPUT_DIR}/dresden_malls_kandidaten.kml"
filtered.to_file(kml_path, driver="KML")
print(f"      KML exportiert: {kml_path}")

# Zusammenfassung als CSV
csv_path = f"{OUTPUT_DIR}/dresden_malls_kandidaten.csv"
filtered.drop(columns=["geometry"]).to_csv(csv_path, index=False)
print(f"      CSV exportiert: {csv_path}")

# ---------------------------------------------------------------------------
# Zusammenfassung ausgeben
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("ZUSAMMENFASSUNG")
print("=" * 60)
print(f"Gefundene Gebäude gesamt:    {len(buildings)}")
print(f"ÖPNV-Objekte gesamt:         {len(transit)}")
print(f"Eingänge gesamt:             {len(entrances)}")
print(f"Kandidaten (≥2 Eingänge + ÖPNV): {len(filtered)}")
print("\nTop-Kandidaten:")
print(filtered[["name", "building", "entrance_count", "transit_count", "levels"]].head(10).to_string(index=False))
print("\nFertig! KML-Datei kann auf umap.openstreetmap.de visualisiert werden.")
