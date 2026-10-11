"""
MallsEtc – Dresden Analyse
Strategie 3: Kombinierte Filter-Logik
Sucht besondere städtische Strukturen (Malls, Bahnhöfe, Passagen) mit:
  - mehreren Ausgängen
  - Ausgängen auf unterschiedlichen Ebenen
  - Anbindung an öffentliche Verkehrsmittel

Korrigierte Fassung:
  * metrische Puffer in projiziertem CRS (UTM), nicht in lat/lon
  * Eingänge werden dem Gebäudepolygon zugeordnet (nicht dem Zentrions-Puffer)
  * räumliche Verknüpfung via Spatial Join statt Python-Schleife (O(n+m))
  * echter Ebenen-Check: distinct `level`-Tags der Eingänge
  * doppelter Import / Hilfsspalten entfernt
  * Export: KML + GPX + CSV
"""

import functools
import logging
import os
import signal
import time
import warnings

import geopandas as gpd
import numpy as np
import osmnx as ox
import osmnx._http as ox_http
import pandas as pd
from osmnx._errors import InsufficientResponseError

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------
PLACE = "Dresden, Deutschland"
OUTPUT_DIR = "tasks/MallsEtc/Dresden_Ergebnisse"

BUFFER_ENTRANCE = 10    # m Toleranz Gebäudekante -> Eingang (Polygone)
BUFFER_POINT = 60       # m Radius für Punkt-Kandidaten (z.B. railway=station)
BUFFER_TRANSIT = 200    # m Maximalabstand zur ÖPNV-Infrastruktur
MIN_ENTRANCES = 2       # min. Eingänge
MIN_TRANSIT = 1         # min. ÖPNV-Objekte im Puffer
MIN_LEVELS = 2          # min. unterschiedliche Ebenen der Eingänge

REFRESH = os.environ.get("REFRESH", "") == "1"   # REFRESH=1 -> Cache ignorieren
CACHE_DIR = os.path.join(OUTPUT_DIR, "cache")
# Basis-URLs (osmnx haengt selbst "/interpreter" an!) mit Kennzeichen
# "autoritativ": nur diese duerfen ein leeres Ergebnis als wahr durchgehen –
# regionale Mirrors decken oft nur ein Land ab (z.B. osm.ch = Schweiz).
OVERPASS_FALLBACKS = [
    ("https://overpass-api.de/api", True),
    ("http://overpass-api.de/api", True),             # TLS-Front brockelt manchmal
    ("https://maps.mail.ru/osm/tools/overpass/api", False),
    ("https://overpass.kumi.systems/api", False),
    ("https://overpass.private.coffee/api", False),
    ("https://overpass.osm.ch/api", False),
]
RETRY_DELAYS = [3, 8]           # Sekunden zwischen den Versuchen (Rate-Limits)
QUERY_TIMEOUT = 120             # harte Obergrenze pro Overpass-Abfrage

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

ox.settings.requests_timeout = 60          # nicht 180s auf einen toten Server warten
ox.settings.http_user_agent = "exploreGeoStructures/1.0 (lokale Recherche)"
# osmnx fragt vor JEDEM Request den /status-Endpunkt ab und wartet dort
# (Default 60 s, bei 504 zusätzlich 55 s) – das summiert sich zu Minuten.
# Wir begrenzen stattdessen selbst mit Backoff + QUERY_TIMEOUT.
ox.settings.overpass_rate_limit = False
ox.settings.log_level = logging.INFO       # Fortschritt sichtbar machen

# osmnx pinnat per _config_dns feste IPs (Round-Robin des Servers). Fällt genau
# diese IP aus, scheitern ALLE Abfragen mit "Connection refused", obwohl der
# Server läuft -> DNS-Pinning abschalten, urllib3 probiert alle Adressen.
ox_http._config_dns = lambda url: None

print("=" * 60)
print("MallsEtc – Dresden Analyse")
print("=" * 60)


def to_projected(gdf, label):
    """In ein metrisches CRS (UTM-Zone der Stadt) projizieren."""
    if gdf.empty:
        return gdf
    proj = ox.projection.project_gdf(gdf)
    print(f"      {label}: CRS {gdf.crs} -> {proj.crs}")
    return proj


def parse_levels(value):
    """'0;1', '0-1', 'G;1' -> Liste einzelner Ebenen."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    out = set()
    for part in str(value).replace(",", ";").split(";"):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, _, b = part.partition("-")
            try:
                lo, hi = int(float(a)), int(float(b))
            except ValueError:
                out.add(part)
                continue
            if 0 <= lo <= hi <= lo + 20:       # "0-2" sind Ebenen, "51.1-51.3" nicht
                out.update(range(lo, hi + 1))
            else:
                out.add(part)
            continue
        try:
            out.add(int(float(part)))
        except ValueError:
            out.add(part)
    return sorted(out, key=str)


def osm_ids(gdf):
    """OSM-Typ und OSM-ID aus dem von osmnx gelieferten Index ziehen."""
    idx = gdf.index
    if isinstance(idx, pd.MultiIndex):
        return (
            pd.Series(idx.get_level_values(0), index=gdf.index, name="osm_type"),
            pd.Series(idx.get_level_values(1), index=gdf.index, name="osm_id"),
        )
    return (
        pd.Series("unknown", index=gdf.index, name="osm_type"),
        pd.Series(idx, index=gdf.index, name="osm_id"),
    )


def _empty_gdf():
    """Leeres GeoDataFrame mit Geometry-Spalte und CRS."""
    return gpd.GeoDataFrame(geometry=gpd.GeoSeries([], crs="EPSG:4326"))


def log(message):
    """Mit Zeitstempel und flush ausgeben (auch bei umgeleitetem stdout sichtbar)."""
    print(f"{time.strftime('%H:%M:%S')} {message}", flush=True)


def _host_label(base_url):
    scheme, _, rest = base_url.partition("://")
    host = rest.split("/")[0]
    return f"{host} ({scheme})" if scheme == "http" else host


@functools.lru_cache(maxsize=1)
def place_bbox():
    """Rechteck (left, bottom, right, top) um den Untersuchungsraum.

    Statt features_from_place: die Stadtgrenze hat ~5880 Knoten, woraus
    osmnx einen ~2,5 MB großen Overpass-Body baut – Mirrors (nginx-Limit
    1 MB) antworten darauf mit 413. Ein Bounding-Box-Query ist ~1 KB groß.
    """
    gdf = ox.geocode_to_gdf(PLACE)
    left, bottom, right, top = (float(v) for v in gdf.total_bounds)
    log(f"      Untersuchungsraum {PLACE}: bbox({left:.4f}, {bottom:.4f}, "
        f"{right:.4f}, {top:.4f})")
    return (left, bottom, right, top)


class _QueryTimeout(Exception):
    """Hartes Zeitlimit für eine Overpass-Abfrage."""


def _with_timeout(seconds, func, *args, **kwargs):
    """func mit SIGALRM-Zeitlimit – verhindert endlose osmnx-504-Warteschleifen."""
    def handler(_signum, _frame):
        raise _QueryTimeout(f"Zeitlimit von {seconds}s überschritten")

    previous = signal.signal(signal.SIGALRM, handler)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        return func(*args, **kwargs)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def fetch_with_fallback(label, tags):
    """OSM-Abfrage: pro Mirror 2 Versuche, danach nächster Mirror.

    Wichtig: hier NICHT vorab sondieren – osmnx prüft zuerst seinen eigenen
    Antwort-Cache, eine Sondierung würde den Cache umgehen.
    """
    last_error = None
    regional_empty = False

    for endpoint, authoritative in OVERPASS_FALLBACKS:
        host = _host_label(endpoint)
        ox.settings.overpass_url = endpoint

        for attempt, delay in enumerate(RETRY_DELAYS, start=1):
            try:
                gdf = _with_timeout(
                    QUERY_TIMEOUT, ox.features_from_bbox, place_bbox(), tags=tags
                )
                log(f"      {len(gdf)} Objekte von {host}")
                return gdf
            except InsufficientResponseError:
                if authoritative:
                    return _empty_gdf()          # Server sagt: wirklich nichts da
                log(f"      {host}: 0 Treffer (wahrscheinlich nur regionale Abdeckung)")
                regional_empty = True
                break                            # nächster Mirror
            except Exception as err:             # Netzwerk-/Server-/Limit-Probleme
                last_error = err
                detail = str(err).replace("\n", " ")[:160]
                log(f"      {host}: {type(err).__name__}: {detail}")
                if attempt < len(RETRY_DELAYS):
                    log(f"      {host}: neuer Versuch in {delay}s")
                    time.sleep(delay)

    if regional_empty:
        raise RuntimeError(
            f"Für '{label}' lieferten nur regionale Mirrors 0 Treffer und die "
            f"Hauptserver waren nicht erreichbar – Ergebnis wäre falsch. "
            f"Später erneut versuchen (letzter Fehler: {last_error})"
        )
    raise RuntimeError(f"Alle Overpass-Mirrors fehlgeschlagen für '{label}'") from last_error


def load_features(label, tags):
    """Abfrage mit Datei-Cache (Pickle), damit Läufe ohne Netz möglich sind.

    Pickle statt GPKG: Spaltennamen wie 'ref:vvo', Listenwerte und der
    OSM-MultiIndex überleben GPKG nicht (bzw. nur verfälscht).
    """
    cache_path = os.path.join(CACHE_DIR, f"{label}.pkl")

    if os.path.exists(cache_path) and not REFRESH:
        gdf = pd.read_pickle(cache_path)
        log(f"      {len(gdf)} Objekte aus Cache: {cache_path}")
        return gdf

    gdf = fetch_with_fallback(label, tags)
    if len(gdf):
        try:
            gdf.to_pickle(cache_path)
            log(f"      Cache geschrieben: {cache_path}")
        except Exception as err:
            log(f"      Cache-Schreibung fehlgeschlagen: {type(err).__name__}: {err}")
    return gdf


# ---------------------------------------------------------------------------
# Schritt 1: Gebäude mit relevanten Tags extrahieren
# ---------------------------------------------------------------------------
print("\n[1/5] Lade Gebäude (mall, train_station, retail, department_store)...")

building_tags = {
    "building": ["mall", "train_station", "retail", "supermarket"],
    "shop": ["department_store", "mall"],
    "railway": ["station"],
}
buildings = load_features("gebaeude", building_tags)
print(f"      {len(buildings)} Gebäude gefunden")
if not len(buildings):
    raise SystemExit("FEHLER: Keine Gebäude erhalten – Overpass-Abfrage war leer. "
                     "Später mit REFRESH=1 erneut versuchen.")

# Geometrie reparieren, Eingangs-Puffer je nach Geometrietyp wählen
invalid = ~buildings.geometry.is_valid
if invalid.any():
    buildings.loc[invalid, "geometry"] = buildings.loc[invalid, "geometry"].make_valid()
buildings["entry_radius"] = np.where(
    buildings.geometry.geom_type.isin(["Point", "MultiPoint"]), BUFFER_POINT, BUFFER_ENTRANCE
)

# ---------------------------------------------------------------------------
# Schritt 2: ÖPNV-Haltestellen abrufen
# ---------------------------------------------------------------------------
print("\n[2/5] Lade ÖPNV-Haltestellen...")

transit_tags = {
    "public_transport": ["station", "stop_position", "platform"],
    "railway": ["station", "halt", "tram_stop"],
    "amenity": ["bus_station"],
}
transit = load_features("oepnv", transit_tags)
print(f"      {len(transit)} ÖPNV-Objekte gefunden")

# ---------------------------------------------------------------------------
# Schritt 3: Eingänge (entrance) abrufen
# ---------------------------------------------------------------------------
print("\n[3/5] Lade Eingänge (entrance)...")

entrance_tags = {
    "entrance": ["yes", "main", "exit", "secondary", "service", "staircase", "elevator"],
}
entrances = load_features("eingaenge", entrance_tags)
print(f"      {len(entrances)} Eingänge gefunden")

# ---------------------------------------------------------------------------
# Schritt 4: Spatial Join – Eingänge & ÖPNV den Gebäuden zuordnen
# ---------------------------------------------------------------------------
print("\n[4/5] Ordne Eingänge und ÖPNV den Gebäuden zu (metrische Puffer)...")

buildings_p = to_projected(buildings, "Gebäude")
transit_p = to_projected(transit, "ÖPNV")
entrances_p = to_projected(entrances, "Eingänge")

# -- Eingänge: Gebäudepolygon (+ Toleranz) enthält Eingang -------------------
# Wichtig: explizite Positions-Spalte "bidx" statt auf die Spalte
# "index_right" von sjoin zu vertrauen – die hängt von den Index-Namen ab
# (hier: benannter MultiIndex aus osm_type/osm_id).
n_buildings = len(buildings_p)
positions = np.arange(n_buildings)

entry_buffers = gpd.GeoDataFrame(
    {"bidx": positions},
    geometry=buildings_p.geometry.buffer(buildings_p["entry_radius"]).values,
    crs=buildings_p.crs,
)

ent_cols = entrances_p[["geometry"]].copy()
ent_cols["entrance_level"] = entrances_p.get("level", pd.Series(index=entrances_p.index, dtype=object))

if len(ent_cols):
    ent_join = gpd.sjoin(ent_cols, entry_buffers, how="inner", predicate="within")
else:
    ent_join = gpd.GeoDataFrame({"entrance_level": pd.Series(dtype=object),
                                 "bidx": pd.Series(dtype=int)})

entrance_count = ent_join.groupby("bidx").size()

# Distincte Ebenen je Gebäude aus den Eingangs-Level-Tags
ent_join["_lv"] = ent_join["entrance_level"].apply(parse_levels)
distinct_levels = ent_join.groupby("bidx")["_lv"].apply(
    lambda series: sorted({lv for lvs in series for lv in lvs}, key=str)
)

# -- ÖPNV: 200 m Puffer um das Gebäude --------------------------------------
transit_buffers = gpd.GeoDataFrame(
    {"bidx": positions},
    geometry=buildings_p.geometry.buffer(BUFFER_TRANSIT).values,
    crs=buildings_p.crs,
)
transit_points = transit_p[["geometry"]].copy()
transit_points["geometry"] = transit_p.geometry.centroid

transit_join = gpd.sjoin(transit_points, transit_buffers, how="inner", predicate="within")
transit_count = transit_join.groupby("bidx").size()

# ---------------------------------------------------------------------------
# Ergebnis-Tabelle zusammenbauen
# ---------------------------------------------------------------------------
osm_type, osm_id = osm_ids(buildings_p)

results = gpd.GeoDataFrame(
    {
        "osm_type": osm_type.values,
        "osm_id": osm_id.values,
        "name": buildings_p.get("name", pd.Series("", index=buildings_p.index)).fillna("").values,
        "building": buildings_p.get("building", pd.Series("", index=buildings_p.index)).fillna("").values,
        "railway": buildings_p.get("railway", pd.Series("", index=buildings_p.index)).fillna("").values,
        "building_levels": buildings_p.get("building:levels", pd.Series("", index=buildings_p.index))
        .fillna("")
        .values,
        "entrance_count": entrance_count.reindex(positions).fillna(0).astype(int).values,
        "entrance_levels": [
            ";".join(map(str, distinct_levels.get(p, []))) for p in positions
        ],
        "distinct_levels": [len(distinct_levels.get(p, [])) for p in positions],
        "transit_count": transit_count.reindex(positions).fillna(0).astype(int).values,
        "geometry": buildings_p.geometry.values,
    },
    crs=buildings_p.crs,
)
results["url"] = (
    "https://www.openstreetmap.org/" + results["osm_type"] + "/" + results["osm_id"].astype(str)
)

# ---------------------------------------------------------------------------
# Schritt 5: Filtern und exportieren
# ---------------------------------------------------------------------------
print("\n[5/5] Filtere und exportiere Ergebnisse...")

level_data_available = int(results["distinct_levels"].sum()) > 0
base = (results["entrance_count"] >= MIN_ENTRANCES) & (results["transit_count"] >= MIN_TRANSIT)

if level_data_available:
    filtered = results[base & (results["distinct_levels"] >= MIN_LEVELS)].copy()
    print(f"      Kriterien: >={MIN_ENTRANCES} Eingänge UND >={MIN_TRANSIT} ÖPNV in {BUFFER_TRANSIT} m "
          f"UND >={MIN_LEVELS} verschiedene Eingangsebenen")
else:
    filtered = results[base].copy()
    print(f"      WARNUNG: Keine `level`-Tags an Eingängen gefunden – Ebenen-Kriterium "
          f"(>={MIN_LEVELS} verschiedene Ebenen) entfaellt!")
    print(f"      Kriterien: >={MIN_ENTRANCES} Eingänge UND >={MIN_TRANSIT} ÖPNV in {BUFFER_TRANSIT} m")

filtered = filtered.sort_values(
    ["distinct_levels", "entrance_count", "transit_count"], ascending=False
)
print(f"      {len(filtered)} von {len(results)} Gebäuden erfüllen die Kriterien")

# In WGS84 zurückrechnen (KML/GPX nutzen immer lat/lon)
filtered_wgs = filtered.to_crs(4326)

# KML (Polygone)
kml_path = os.path.join(OUTPUT_DIR, "dresden_malls_kandidaten.kml")
filtered_wgs.to_file(kml_path, driver="KML")
print(f"      KML exportiert: {kml_path}")

# GPX (Waypoints für umap.openstreetmap.de)
gpx_path = os.path.join(OUTPUT_DIR, "dresden_malls_kandidaten.gpx")
points = gpd.GeoDataFrame(
    {
        "name": filtered_wgs["name"].fillna("").astype(str).values,
        "desc": (
            "Eingänge: " + filtered_wgs["entrance_count"].astype(str)
            + " | Ebenen: " + filtered_wgs["distinct_levels"].astype(str)
            + " | ÖPNV: " + filtered_wgs["transit_count"].astype(str)
        ).values,
    },
    geometry=filtered_wgs.geometry.representative_point().values,
    crs=4326,
)
points.to_file(gpx_path, driver="GPX", layer="waypoints")
print(f"      GPX exportiert: {gpx_path}")

# CSV (Kandidaten + alle getakteten Gebäude)
csv_path = os.path.join(OUTPUT_DIR, "dresden_malls_kandidaten.csv")
filtered.drop(columns=["geometry"]).to_csv(csv_path, index=False)
print(f"      CSV exportiert: {csv_path}")

all_csv = os.path.join(OUTPUT_DIR, "dresden_alle_gebaeude.csv")
results.drop(columns=["geometry"]).to_csv(all_csv, index=False)
print(f"      CSV exportiert: {all_csv}")

# ---------------------------------------------------------------------------
# Zusammenfassung
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("ZUSAMMENFASSUNG")
print("=" * 60)
print(f"Gefundene Gebäude gesamt:        {len(buildings)}")
print(f"ÖPNV-Objekte gesamt:             {len(transit)}")
print(f"Eingänge gesamt:                 {len(entrances)}")
print(f"Davon Gebäude mit Eingang:       {int((results['entrance_count'] > 0).sum())}")
print(f"Kandidaten:                      {len(filtered)}")
if not level_data_available:
    print("HINWEIS: Ebenen-Kriterium nicht anwendbar (keine level-Tags an Eingängen).")

if len(filtered):
    cols = ["name", "building", "entrance_count", "entrance_levels", "transit_count"]
    print("\nTop-Kandidaten:")
    print(filtered[cols].head(15).to_string(index=False))

print("\nVisualisierung: KML/GPX auf https://umap.openstreetmap.de importieren")
print("  -> Karte bearbeiten -> Datei hochladen (.kml bzw. .gpx) -> Layer benennen")
