#!/usr/bin/env python3
"""
Besondere städtische Strukturen finden – Kombinierter Ansatz (Skill: mallsetc)
1. Gebäude, ÖPNV und Eingänge aus OSM/Overpass abrufen -> reference/datenquellen.md
2. Eingänge/ÖPNV den Gebäuden zuordnen (Spatial Join, metrisches CRS)
3. Kriterien prüfen (Eingänge, Ebenen, ÖPNV)             -> reference/kriterien.md
4. Ergebnis exportieren                                    -> SKILL.md "Output"

Ablauf: SKILL.md (Prozess, Schritte 1-8, inkl. Learnings-Loop).
"""

import argparse
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
BUFFER_ENTRANCE = 10    # m Toleranz Gebäudekande -> Eingang (Polygone)
BUFFER_POINT = 60       # m Radius für Punkt-Kandidaten (z.B. railway=station)
BUFFER_TRANSIT = 200    # m Maximalabstand zur ÖPNV-Infrastruktur
MIN_ENTRANCES = 2       # min. Eingänge
MIN_TRANSIT = 1         # min. ÖPNV-Objekte im Puffer
MIN_LEVELS = 2          # min. unterschiedliche Ebenen der Eingänge
QUERY_TIMEOUT = 120     # harte Obergrenze pro Overpass-Abfrage
RETRY_DELAYS = [3, 8]   # Sekunden zwischen den Versuchen (Rate-Limits)

# (Basis-URL, autoritativ): osmnx haengt selbst "/interpreter" an.
# "autoritativ" = ein leeres Ergebnis dort wird als wahr akzeptiert;
# regionale Mirrors (z.B. osm.ch = Schweiz) duerfen kein Leer-Ergebnis
# durchwinken (siehe reference/fehlerbehandlung.md).
OVERPASS_FALLBACKS = [
    ("https://overpass-api.de/api", True),
    ("http://overpass-api.de/api", True),
    ("https://maps.mail.ru/osm/tools/overpass/api", False),
    ("https://overpass.kumi.systems/api", False),
    ("https://overpass.private.coffee/api", False),
    ("https://overpass.osm.ch/api", False),
]

BUILDING_TAGS = {
    "building": ["mall", "train_station", "retail", "supermarket"],
    "shop": ["department_store", "mall"],
    "railway": ["station"],
}
TRANSIT_TAGS = {
    "public_transport": ["station", "stop_position", "platform"],
    "railway": ["station", "halt", "tram_stop"],
    "amenity": ["bus_station"],
}
ENTRANCE_TAGS = {
    "entrance": ["yes", "main", "exit", "secondary", "service", "staircase", "elevator"],
}


def log(message):
    """Mit Zeitstempel und flush ausgeben (auch bei umgeleitetem stdout)."""
    print(f"{time.strftime('%H:%M:%S')} {message}", flush=True)


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


# osmnx pinnat per _config_dns feste IPs (Round-Robin des Servers). Faellt
# genau diese IP aus, scheitern ALLE Abfragen mit "Connection refused",
# obwohl der Server laeuft -> Pinning abschalten (siehe learnings.md).
ox_http._config_dns = lambda url: None

ox.settings.requests_timeout = 60
ox.settings.http_user_agent = "exploreGeoStructures-mallsetc/1.0 (OpenCode skill)"
ox.settings.overpass_rate_limit = False
ox.settings.log_level = logging.INFO


# ---------------------------------------------------------------------------
# Overpass-Abfrage mit Cache, Fallback und hartem Zeitlimit
# ---------------------------------------------------------------------------
def _host_label(base_url):
    scheme, _, rest = base_url.partition("://")
    host = rest.split("/")[0]
    return f"{host} ({scheme})" if scheme == "http" else host


def fetch_with_fallback(label, tags, bbox):
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
                    QUERY_TIMEOUT, ox.features_from_bbox, bbox, tags=tags
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


def _empty_gdf():
    """Leeres GeoDataFrame mit Geometry-Spalte und CRS."""
    return gpd.GeoDataFrame(geometry=gpd.GeoSeries([], crs="EPSG:4326"))


@functools.lru_cache(maxsize=1)
def _bbox(place):
    """Rechteck (left, bottom, right, top) um die Untersuchungsregion.

    Bbox statt Stadtgrenze: die Stadtgrenze hat tausende Knoten, woraus osmnx
    einen ~2,5 MB großen Query-Body baut – Mirrors antworten mit 413.
    """
    gdf = ox.geocode_to_gdf(place)
    left, bottom, right, top = (float(v) for v in gdf.total_bounds)
    log(f"      Untersuchungsraum {place}: bbox({left:.4f}, {bottom:.4f}, "
        f"{right:.4f}, {top:.4f})")
    return (left, bottom, right, top)


def load_features(cache_dir, label, tags, refresh, bbox):
    """Abfrage mit Datei-Cache (Pickle), damit Läufe ohne Netz möglich sind."""
    cache_path = os.path.join(cache_dir, f"{label}.pkl")

    if os.path.exists(cache_path) and not refresh:
        gdf = pd.read_pickle(cache_path)
        log(f"      {len(gdf)} Objekte aus Cache: {cache_path}")
        return gdf

    gdf = fetch_with_fallback(label, tags, bbox)
    if len(gdf):
        try:
            gdf.to_pickle(cache_path)
            log(f"      Cache geschrieben: {cache_path}")
        except Exception as err:
            log(f"      Cache-Schreibung fehlgeschlagen: {type(err).__name__}: {err}")
    return gdf


# ---------------------------------------------------------------------------
# Level-Tags der Eingänge parsen
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Hauptprogramm
# ---------------------------------------------------------------------------
def to_projected(gdf, label):
    """In ein metrisches CRS (UTM-Zone der Region) projizieren."""
    if gdf.empty:
        return gdf
    proj = ox.projection.project_gdf(gdf)
    log(f"      {label}: CRS {gdf.crs} -> {proj.crs}")
    return proj


def analyze(cache_dir, place, refresh, output_dir, bbox):
    """Daten laden, Kriterien prüfen und Ergebnis-GeoDataFrame liefern."""
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(cache_dir, exist_ok=True)

    print("\n[1/5] Lade Gebäude (mall, train_station, retail, department_store)...")
    buildings = load_features(cache_dir, "gebaeude", BUILDING_TAGS, refresh, bbox)
    print(f"      {len(buildings)} Gebäude gefunden")
    if not len(buildings):
        raise SystemExit("FEHLER: Keine Gebäude erhalten – Overpass-Abfrage war leer. "
                         "Später mit --refresh erneut versuchen.")

    print("\n[2/5] Lade ÖPNV-Haltestellen...")
    transit = load_features(cache_dir, "oepnv", TRANSIT_TAGS, refresh, bbox)
    print(f"      {len(transit)} ÖPNV-Objekte gefunden")

    print("\n[3/5] Lade Eingänge (entrance)...")
    entrances = load_features(cache_dir, "eingaenge", ENTRANCE_TAGS, refresh, bbox)
    print(f"      {len(entrances)} Eingänge gefunden")

    print("\n[4/5] Ordne Eingänge und ÖPNV den Gebäuden zu (metrische Puffer)...")

    buildings_p = to_projected(buildings, "Gebäude")
    transit_p = to_projected(transit, "ÖPNV")
    entrances_p = to_projected(entrances, "Eingänge")

    n_buildings = len(buildings_p)
    positions = np.arange(n_buildings)

    # -- Eingänge: Gebäudepolygon (+ Toleranz) enthält Eingang -----------------
    # Wichtig: explizite Positions-Spalte "bidx" statt auf die Spalte
    # "index_right" von sjoin zu vertrauen (haengt von den Index-Namen ab).
    # Toleranz je nach Geometrietyp: Punkte groesser, Polygone schmaler.
    buildings_p["entry_radius"] = np.where(
        buildings_p.geometry.geom_type.isin(["Point", "MultiPoint"]),
        BUFFER_POINT, BUFFER_ENTRANCE,
    )
    entry_buffers = gpd.GeoDataFrame(
        {"bidx": positions},
        geometry=buildings_p.geometry.buffer(buildings_p["entry_radius"]).values,
        crs=buildings_p.crs,
    )

    ent_cols = entrances_p[["geometry"]].copy()
    ent_cols["entrance_level"] = entrances_p.get(
        "level", pd.Series(index=entrances_p.index, dtype=object))

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

    # -- ÖPNV: 200 m Puffer um das Gebäude ------------------------------------
    transit_buffers = gpd.GeoDataFrame(
        {"bidx": positions},
        geometry=buildings_p.geometry.buffer(BUFFER_TRANSIT).values,
        crs=buildings_p.crs,
    )
    transit_points = transit_p[["geometry"]].copy()
    transit_points["geometry"] = transit_p.geometry.centroid

    transit_join = gpd.sjoin(transit_points, transit_buffers, how="inner", predicate="within")
    transit_count = transit_join.groupby("bidx").size()

    # -- Ergebnis-Tabelle zusammenbauen ---------------------------------------
    osm_type, osm_id = osm_ids(buildings_p)

    results = gpd.GeoDataFrame(
        {
            "osm_type": osm_type.values,
            "osm_id": osm_id.values,
            "name": buildings_p.get("name", pd.Series("", index=buildings_p.index)).fillna("").values,
            "building": buildings_p.get("building", pd.Series("", index=buildings_p.index)).fillna("").values,
            "railway": buildings_p.get("railway", pd.Series("", index=buildings_p.index)).fillna("").values,
            "building_levels": buildings_p.get("building:levels", pd.Series("", index=buildings_p.index))
            .fillna("").values,
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
    return results, transit


def filter_candidates(results):
    """Kriterien anwenden; Kandidaten und verworfene Gebaeude mit Grund."""
    level_data_available = int(results["distinct_levels"].sum()) > 0
    dropped = []

    for idx, row in results.iterrows():
        reasons = []
        if row["entrance_count"] < MIN_ENTRANCES:
            reasons.append(f"nur {row['entrance_count']} Eingänge (mind. {MIN_ENTRANCES})")
        if row["transit_count"] < MIN_TRANSIT:
            reasons.append(f"kein ÖPNV in {BUFFER_TRANSIT} m")
        if level_data_available and row["distinct_levels"] < MIN_LEVELS:
            reasons.append(
                f"nur {row['distinct_levels']} Eingangsebene(n) (mind. {MIN_LEVELS})")
        if reasons:
            dropped.append({
                "name": row["name"] or "(unbenannt)",
                "osm_url": row["url"],
                "grund": "; ".join(reasons),
            })

    base = (results["entrance_count"] >= MIN_ENTRANCES) & (results["transit_count"] >= MIN_TRANSIT)
    if level_data_available:
        filtered = results[base & (results["distinct_levels"] >= MIN_LEVELS)].copy()
    else:
        filtered = results[base].copy()
    filtered = filtered.sort_values(
        ["distinct_levels", "entrance_count", "transit_count"], ascending=False
    )
    return filtered, dropped, level_data_available


def export(filtered_wgs, output_dir, stats):
    """GeoJSON, KML, GPX und Zusammenfassung schreiben."""
    os.makedirs(output_dir, exist_ok=True)

    geojson_path = os.path.join(output_dir, "kandidaten.geojson")
    filtered_wgs.to_file(geojson_path, driver="GeoJSON")
    print(f"      GeoJSON exportiert: {geojson_path}")

    kml_path = os.path.join(output_dir, "kandidaten.kml")
    filtered_wgs.to_file(kml_path, driver="KML")
    print(f"      KML exportiert: {kml_path}")

    gpx_path = os.path.join(output_dir, "kandidaten.gpx")
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

    json_path = os.path.join(output_dir, "zusammenfassung.json")
    pd.Series(stats).to_json(json_path, orient="index", indent=2, force_ascii=False)
    print(f"      Zusammenfassung exportiert: {json_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Besondere städtische Strukturen (Malls, Bahnhöfe, Passagen) finden")
    parser.add_argument("--place", type=str, help="Stadt oder Stadtteil (z.B. 'Dresden, Deutschland')")
    parser.add_argument("--bbox", type=float, nargs=4, metavar=("S", "W", "N", "E"),
                        help="Bounding Box (S, W, N, E) – ersetzt --place")
    parser.add_argument("--output", type=str, default="ergebnis", help="Ausgabeverzeichnis")
    parser.add_argument("--refresh", action="store_true", help="Cache ignorieren und neu abrufen")
    args = parser.parse_args()

    if not args.place and not args.bbox:
        parser.error("--place oder --bbox erforderlich")

    if args.bbox:
        # CLI-BBox ist (S, W, N, E); osmnx features_from_bbox erwartet
        # (left, bottom, right, top) = (W, S, E, N)
        s, w, n, e = args.bbox
        bbox = (w, s, e, n)
        place = f"BoundingBox S={s}, W={w}, N={n}, E={e}"
    else:
        place = args.place
        bbox = _bbox(place)

    output_dir = args.output
    cache_dir = os.path.join(os.path.dirname(output_dir) or ".", "cache")

    print("=" * 60)
    print("MallsEtc – Besondere städtische Strukturen")
    print("=" * 60)

    results, transit = analyze(cache_dir, place, args.refresh, output_dir, bbox)

    print("\n[5/5] Filtere und exportiere Ergebnisse...")
    filtered, dropped, level_data_available = filter_candidates(results)

    if level_data_available:
        print(f"      Kriterien: >={MIN_ENTRANCES} Eingänge UND >={MIN_TRANSIT} ÖPNV in {BUFFER_TRANSIT} m "
              f"UND >={MIN_LEVELS} verschiedene Eingangsebenen")
    else:
        print(f"      WARNUNG: Keine level-Tags an Eingängen gefunden – Ebenen-Kriterium "
              f"(>={MIN_LEVELS} verschiedene Ebenen) entfaellt!")
        print(f"      Kriterien: >={MIN_ENTRANCES} Eingänge UND >={MIN_TRANSIT} ÖPNV in {BUFFER_TRANSIT} m")

    print(f"      {len(filtered)} von {len(results)} Gebäuden erfüllen die Kriterien")

    filtered_wgs = filtered.to_crs(4326)
    stats = {
        "untersuchungsraum": place,
        "gebaeude_gesamt": len(results),
        "oepnv_objekte_gesamt": len(transit),
        "eingaenge_gesamt": int(results["entrance_count"].sum()),
        "gebaeude_mit_eingang": int((results["entrance_count"] > 0).sum()),
        "kandidaten": len(filtered),
        "verworfene_kandidaten": dropped,
        "level_daten_vorhanden": level_data_available,
    }
    export(filtered_wgs, output_dir, stats)

    print("\n" + "=" * 60)
    print("ZUSAMMENFASSUNG")
    print("=" * 60)
    print(f"Gefundene Gebäude gesamt:        {len(results)}")
    print(f"ÖPNV-Objekte gesamt:             {len(transit)}")
    print(f"Eingänge gesamt:                 {int(results['entrance_count'].sum())}")
    print(f"Davon Gebäude mit Eingang:       {int((results['entrance_count'] > 0).sum())}")
    print(f"Kandidaten:                      {len(filtered)}")
    if not level_data_available:
        print("HINWEIS: Ebenen-Kriterium nicht anwendbar (keine level-Tags an Eingängen).")

    if len(filtered):
        cols = ["name", "building", "entrance_count", "entrance_levels", "transit_count"]
        print("\nTop-Kandidaten:")
        print(filtered[cols].head(15).to_string(index=False))

    print("\nVisualisierung: GeoJSON/KML/GPX auf https://umap.openstreetmap.de importieren")
    print("  -> Karte bearbeiten -> Daten importieren -> GeoJSON wählen -> als neue Ebene")


if __name__ == "__main__":
    main()
