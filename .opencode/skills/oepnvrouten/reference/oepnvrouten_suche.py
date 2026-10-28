#!/usr/bin/env python3
"""
ÖPNV-Routen finden – Arbeitsversion (Skill: oepnvrouten)

1. Datenquellen scoutern und bewerten               -> reference/datenquellen.md
2. Netzwerk aufbauen (Stationen, Linien, Clustering) -> reference/datenquellen.md
3. Routing mit strikten Constraints + Diversität    -> reference/routing-regeln.md
4. Echte Fahrweg-Geometrie laden                    -> reference/datenquellen.md
5. 3 Routen-Vorschläge exportieren                  -> SKILL.md "Output"

Ablauf: SKILL.md (Prozess, Schritte 1-8, inkl. Learnings-Loop).

WICHTIG:
  * Station-Clustering ist Pflicht: In OSM sind S-Bahn/U-Bahn/Bus/Tram an einem
    Bahnhof getrennte Knoten – ohne Clustering zerfällt der Graph in hunderte
    Komponenten und es gibt keine Routen (Berlin: 1209 Komponenten ohne,
    1180 Verkehrsknoten mit 150-m-Clustering).
  * Export zeigt ECHTE Fahrwege (Strecken-Segmente der Linien), keine
    Luftlinien: relation(ID); way(r); out geom;
  * Fahrtzeiten sind Schätzwerte (kein GTFS): distance / mode speed.
"""

import argparse
import hashlib
import json
import math
import sys
import time
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path

import requests

OPENCODE_DIR = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(OPENCODE_DIR / "lib"))
from workflow_adapter import (  # noqa: E402
    candidate_feature,
    load_node_request,
    resolve_region,
    write_adapter_output,
)

CACHE_DIR = Path("results/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

OVERPASS_SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
HEADERS = {"User-Agent": "exploreGeoStructures-oepnvrouten/1.0 (OpenCode skill)"}
RETRY_DELAYS = [3, 8]

# Schätzwerte (kein GTFS): Geschwindigkeit in m/Min
GESCHWINDIGKEIT = {
    "u_bahn": 500,
    "s_bahn": 583,
    "regionalzug": 833,
    "strassenbahn": 300,
    "bus": 250,
    "faehre": 250,
    "fussweg": 80,
}
MODE_PRIO = {
    "regionalzug": 1,
    "s_bahn": 2,
    "u_bahn": 2,
    "strassenbahn": 3,
    "faehre": 4,
    "bus": 10,
    "fussweg": 5,
}
AUFENTHALT_MIN = 1  # Haltezeit pro Zwischenstation
UMSTIEG_FUSS_MIN = 2  # Gehzeit beim Umsteigen
UMSTIEG_WARTE_MIN = 4  # Wartezeit auf die nächste Bahn
CLUSTER_RADIUS_M = 150  # Stationen-Cluster (Umstiegsmodell)


def log(msg):
    print(f"{time.strftime('%H:%M:%S')} {msg}", flush=True)


# ---------------------------------------------------------------------------
# Overpass-Client mit Fallback und Cache
# ---------------------------------------------------------------------------
def overpass(query, name, refresh=False):
    cache = CACHE_DIR / f"{name}-{hashlib.sha1(query.encode()).hexdigest()[:12]}.json"
    if cache.exists() and not refresh:
        log(f"  [Cache] {name}")
        return json.loads(cache.read_text(encoding="utf-8"))
    last = None
    for server in OVERPASS_SERVERS:
        for attempt, delay in enumerate(RETRY_DELAYS):
            try:
                r = requests.post(
                    server, data={"data": query}, headers=HEADERS, timeout=150
                )
                if r.status_code == 200:
                    data = r.json()
                    cache.write_text(json.dumps(data), encoding="utf-8")
                    log(f"  [Overpass] {name} <- {server.split('/')[2]}")
                    return data
                last = f"HTTP {r.status_code}"
            except Exception as err:
                last = f"{type(err).__name__}: {str(err)[:60]}"
            if attempt < len(RETRY_DELAYS) - 1:
                time.sleep(delay)
    raise RuntimeError(f"Overpass fehlgeschlagen für '{name}': {last}")


def bbox_str(bbox):
    s, w, n, e = bbox
    return f"({s},{w},{n},{e})"


def bbox_fuer_stadt(stadt, refresh=False):
    """BBox einer Stadt über Nominatim (S, W, N, E)."""
    cache = CACHE_DIR / "stadt_bbox.json"
    if cache.exists() and not refresh:
        daten = json.loads(cache.read_text(encoding="utf-8"))
        if stadt in daten:
            return tuple(daten[stadt])
    r = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": stadt, "format": "json", "limit": 1, "accept-language": "de"},
        headers=HEADERS,
        timeout=30,
    )
    treffer = r.json()
    if not treffer:
        raise SystemExit(f"Nominatim: '{stadt}' nicht gefunden")
    b = [float(v) for v in treffer[0]["boundingbox"]]  # [S, N, W, E]
    bbox = (b[0], b[2], b[1], b[3])  # (S, W, N, E)
    daten = json.loads(cache.read_text(encoding="utf-8")) if cache.exists() else {}
    daten[stadt] = list(bbox)
    cache.write_text(json.dumps(daten, ensure_ascii=False), encoding="utf-8")
    if abs(bbox[2] - bbox[3]) < 0.02:
        log(
            f"  WARNUNG: BBox von '{stadt}' ist sehr klein – "
            f"ggf. explizit --bbox angeben"
        )
    return bbox


# ---------------------------------------------------------------------------
# Daten laden
# ---------------------------------------------------------------------------
def geocode_punkt(name, refresh=False):
    """Punkt-Koordinatensuche über Nominatim (deterministische Zielauswahl)."""
    cache = CACHE_DIR / (f"punkt-{hashlib.sha1(name.encode()).hexdigest()[:12]}.json")
    if cache.exists() and not refresh:
        return tuple(json.loads(cache.read_text(encoding="utf-8")))
    r = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": name, "format": "json", "limit": 1, "accept-language": "de"},
        headers=HEADERS,
        timeout=30,
    )
    treffer = r.json()
    if not treffer:
        cache.write_text("null", encoding="utf-8")
        return None
    punkt = (float(treffer[0]["lat"]), float(treffer[0]["lon"]))
    cache.write_text(json.dumps(list(punkt)), encoding="utf-8")
    return punkt


def lade_stationen(bbox, refresh=False):
    bb = bbox_str(bbox)
    query = f"""
    [out:json][timeout:90];
    (
      node["public_transport"="station"]{bb};
      node["public_transport"="stop_position"]{bb};
      node["railway"="station"]{bb};
      node["railway"="halt"]{bb};
      node["highway"="bus_stop"]{bb};
    );
    out body;
    """
    data = overpass(query, "stationen", refresh)
    stationen = {}
    for el in data.get("elements", []):
        if el["type"] != "node":
            continue
        t = el.get("tags", {})
        stationen[el["id"]] = {
            "id": el["id"],
            "name": t.get("name") or f"Station {el['id']}",
            "lat": el["lat"],
            "lon": el["lon"],
            "railway": t.get("railway"),
            "public_transport": t.get("public_transport"),
            "highway": t.get("highway"),
        }
    return stationen


def lade_linien(bbox, route, refresh=False):
    """Linien-Relationen eines route-Typs (mit Stationen) in der BBox.

    'out body;' liefert die Member (Stationenfolge) – 'out members;' crasht
    den Overpass-Backend (502).
    """
    bb = bbox_str(bbox)
    query = f"""
    [out:json][timeout:120];
    relation["type"="route"]["route"="{route}"]{bb};
    out body;
    """
    data = overpass(query, f"linien_{route}", refresh)
    linien = []
    for el in data.get("elements", []):
        if el["type"] != "relation":
            continue
        t = el.get("tags", {})
        refs = [m["ref"] for m in el.get("members", []) if m.get("type") == "node"]
        linien.append(
            {
                "id": str(el["id"]),
                "name": t.get("name") or t.get("ref") or f"{route} {el['id']}",
                "ref": t.get("ref") or "",
                "route": route,
                "refs": refs,
            }
        )
    return linien


def mode_fuer(route, ref):
    if route == "subway":
        return "u_bahn"
    if route == "train":
        return "s_bahn" if ref.upper().startswith("S") else "regionalzug"
    if route in ("tram", "light_rail"):
        return "strassenbahn"
    if route == "bus":
        return "bus"
    if route == "ferry":
        return "faehre"
    return "bus"


# ---------------------------------------------------------------------------
# Station-Clustering (Umstiegsmodell)
# ---------------------------------------------------------------------------
def cluster_stationen(stationen, radius_m=CLUSTER_RADIUS_M):
    try:
        import numpy as np
        from scipy.spatial import cKDTree
    except ImportError:
        return {s["id"]: [s["id"]] for s in stationen.values()}
    ids = list(stationen)
    lat0 = sum(stationen[i]["lat"] for i in ids) / len(ids)
    kx = 111320.0 * math.cos(math.radians(lat0))
    ky = 110540.0
    pts = np.array([[stationen[i]["lon"] * kx, stationen[i]["lat"] * ky] for i in ids])
    pairs = cKDTree(pts).query_pairs(radius_m)
    parent = {i: i for i in ids}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in pairs:
        ra, rb = find(ids[a]), find(ids[b])
        if ra != rb:
            parent[ra] = rb
    gruppen = {}
    for i in ids:
        gruppen.setdefault(find(i), []).append(i)
    return gruppen


def merge_gruppe(gruppe, stationen):
    def wert(s):
        w = 0 if s["name"].startswith("Station ") else 2
        if s.get("railway") in ("station", "halt"):
            w += 2
        if s.get("public_transport") == "station":
            w += 1
        return w

    beste = max(gruppe, key=lambda i: (wert(stationen[i]), i))
    s = stationen[beste]
    return {
        "id": beste,
        "name": s["name"],
        "lat": sum(stationen[i]["lat"] for i in gruppe) / len(gruppe),
        "lon": sum(stationen[i]["lon"] for i in gruppe) / len(gruppe),
    }


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------
def haversine(lat1, lon1, lat2, lon2):
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class Graph:
    def __init__(self):
        self.stationen = {}
        self.linien = {}
        self.nachbarn = {}

    def add_station(self, s):
        self.stationen[s["id"]] = s

    def add_linie(self, linie, cluster_von):
        refs = [cluster_von[r] for r in linie["refs"] if r in cluster_von]
        seq = []
        for r in refs:
            if not seq or seq[-1] != r:
                seq.append(r)
        if len(seq) < 2:
            return 0
        mode = mode_fuer(linie["route"], linie["ref"])
        self.linien[linie["id"]] = {**linie, "mode": mode, "stationen": seq}
        n = 0
        for a, b in zip(seq, seq[1:]):
            self.nachbarn.setdefault(a, []).append((b, linie["id"], mode))
            n += 1
        for a in {a for a, _ in zip(seq, seq[1:])}:
            self.nachbarn[a].sort(key=lambda e: MODE_PRIO.get(e[2], 9))
        return n


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------
def _score(route):
    vm = sum(MODE_PRIO.get(f["mode"], 5) for f in route["fahrten"])
    return 2.0 * (route["fuss"] + route["warte"]) + 1.0 * vm


def _dfs(
    graph,
    start_id,
    ziel_id,
    dauer_min,
    dauer_max,
    umstiege_min,
    umstiege_max,
    verbotene_kanten,
    max_iter=200000,
):
    stationen = graph.stationen
    routen = []
    stack = [([start_id], {start_id}, set(), 0, 0, 0, None, 0, [], [])]
    iterationen = 0
    while stack and iterationen < max_iter:
        iterationen += 1
        (pfad, bst, bkan, umst, fuss, warte, llin, zeit, fahrten, uliste) = stack.pop()
        cur = pfad[-1]
        if cur == ziel_id:
            if (
                dauer_min <= zeit <= dauer_max
                and umstiege_min <= len(uliste) <= umstiege_max
            ):
                routen.append(
                    {
                        "stationen": list(pfad),
                        "fahrten": list(fahrten),
                        "umstiege": list(uliste),
                        "dauer": zeit,
                        "fuss": fuss,
                        "warte": warte,
                    }
                )
            continue
        if zeit > dauer_max or len(uliste) > umstiege_max:
            continue
        for nb, lid, mode in reversed(graph.nachbarn.get(cur, [])):
            if nb in bst:
                continue
            kante = (cur, nb)
            if kante in bkan or (lid, cur, nb) in verbotene_kanten:
                continue
            s1, s2 = stationen[cur], stationen[nb]
            dist = haversine(s1["lat"], s1["lon"], s2["lat"], s2["lon"])
            fahrzeit = (
                max(1, round(dist / GESCHWINDIGKEIT.get(mode, 250))) + AUFENTHALT_MIN
            )
            nfuss, nwarte, numst = fuss, warte, umst
            nliste = list(uliste)
            if llin is not None and llin != lid:
                nfuss += UMSTIEG_FUSS_MIN
                nwarte += UMSTIEG_WARTE_MIN
                numst += 1
                nliste.append(
                    {
                        "station": cur,
                        "von": llin,
                        "nach": lid,
                        "fuss": UMSTIEG_FUSS_MIN,
                        "warte": UMSTIEG_WARTE_MIN,
                    }
                )
            stack.append(
                (
                    pfad + [nb],
                    bst | {nb},
                    bkan | {kante},
                    numst,
                    nfuss,
                    nwarte,
                    lid,
                    zeit + fahrzeit,
                    fahrten
                    + [
                        {
                            "von": cur,
                            "nach": nb,
                            "linie": lid,
                            "mode": mode,
                            "dauer": fahrzeit,
                            "dist_m": round(dist),
                        }
                    ],
                    nliste,
                )
            )
    return routen


def finde_routen(
    graph, start_id, ziel_id, dauer_min, dauer_max, umstiege_min, umstiege_max, anzahl=3
):
    """Bis zu `anzahl` unterschiedliche Routen (Kanten-Ausschluss pro Runde).

    Ein deterministischer DFS liefert sonst 3× dieselbe Route – das Aussperren
    der Kanten der vorherigen Route erzwingt Vielfalt.
    """
    if start_id not in graph.stationen or ziel_id not in graph.stationen:
        return []
    seen, queue = {start_id}, [start_id]
    while queue:
        cur = queue.pop(0)
        for nb, _, _ in graph.nachbarn.get(cur, []):
            if nb not in seen:
                seen.add(nb)
                queue.append(nb)
    if ziel_id not in seen:
        return []

    auswahl, verboten, signaturen = [], set(), set()
    for _runde in range(anzahl * 4):
        routen = _dfs(
            graph,
            start_id,
            ziel_id,
            dauer_min,
            dauer_max,
            umstiege_min,
            umstiege_max,
            verboten,
        )
        if not routen:
            routen = _dfs(
                graph,
                start_id,
                ziel_id,
                dauer_min,
                dauer_max,
                umstiege_min,
                umstiege_max,
                set(),
            )
            if not routen:
                break
        for r in routen:
            r["score"] = _score(r)
        routen.sort(key=lambda r: (r["score"], r["dauer"]))
        for beste in routen:
            # Nur routen mit wirklich anderen Linien aufnehmen (Node-Paare
            # innerhalb desselben Clusters erzeugen sonst Dublikate).
            signature = (
                tuple(f["linie"] for f in beste["fahrten"]),
                beste["dauer"],
            )
            if signature in signaturen:
                continue
            auswahl.append(beste)
            signaturen.add(signature)
            verboten.update((f["linie"], f["von"], f["nach"]) for f in beste["fahrten"])
            break
        else:
            break
        if len(auswahl) >= anzahl:
            break
    return auswahl


# ---------------------------------------------------------------------------
# Echte Fahrweg-Geometrie
# ---------------------------------------------------------------------------
def lade_linien_geometrie(linien_ids, refresh=False):
    """Echte Strecken der Linien: relation(ID); way(r); out geom;"""
    ergebnis = {}
    for lid in linien_ids:
        query = f"[out:json][timeout:90];relation({lid});way(r);out geom;"
        try:
            data = overpass(query, f"geometrie_{lid}", refresh)
        except Exception as err:
            log(f"  Geometrie Linie {lid} fehlgeschlagen: {err}")
            continue
        coords, adj = {}, {}
        for el in data.get("elements", []):
            if el["type"] != "way":
                continue
            nodes = el.get("nodes", [])
            geom = el.get("geometry", [])
            for i, nid in enumerate(nodes):
                if i < len(geom):
                    coords[nid] = (geom[i]["lat"], geom[i]["lon"])
            for a, b in zip(nodes, nodes[1:]):
                adj.setdefault(a, []).append(b)
                adj.setdefault(b, []).append(a)
        ergebnis[lid] = (coords, adj)
        log(f"  Geometrie Linie {lid}: {len(coords)} Knoten")
    return ergebnis


def segment_pfad(linie_id, cluster_a, cluster_b, line_geom, mitglieder):
    """Echter Fahrweg zwischen zwei Stationen auf einer Linie (BFS)."""
    if linie_id not in line_geom:
        return None
    coords, adj = line_geom[linie_id]
    starts = [m for m in mitglieder.get(cluster_a, []) if m in adj]
    goals = {m for m in mitglieder.get(cluster_b, []) if m in adj}
    if not starts or not goals:
        return None
    prev = {s: None for s in starts}
    queue = deque(starts)
    ziel = None
    while queue:
        cur = queue.popleft()
        if cur in goals:
            ziel = cur
            break
        for nb in adj.get(cur, []):
            if nb not in prev:
                prev[nb] = cur
                queue.append(nb)
    if ziel is None:
        return None
    pfad, cur = [], ziel
    while cur is not None:
        pfad.append(cur)
        cur = prev[cur]
    pfad.reverse()
    return [coords[n] for n in pfad if n in coords]


def route_punkte_real(route, line_geom, mitglieder, graph):
    """Echte Streckenpunkte (lon, lat); Luftlinie nur als Fallback."""
    punkte = []
    for f in route["fahrten"]:
        pfad = segment_pfad(f["linie"], f["von"], f["nach"], line_geom, mitglieder)
        if pfad:
            for la, lo in pfad:
                if not punkte or punkte[-1] != (lo, la):
                    punkte.append((lo, la))
        else:
            s1, s2 = graph.stationen[f["von"]], graph.stationen[f["nach"]]
            for lo, la in ((s1["lon"], s1["lat"]), (s2["lon"], s2["lat"])):
                if not punkte or punkte[-1] != (lo, la):
                    punkte.append((lo, la))
    return punkte


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
def export(routen, graph, output, punkte_pro_route):
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)

    features = []
    for i, r in enumerate(routen, 1):
        koords = punkte_pro_route[i - 1]  # (lon, lat)
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "route_id": i,
                    "dauer_min": r["dauer"],
                    "umstiege": len(r["umstiege"]),
                    "fussweg_min": r["fuss"],
                    "wartezeit_min": r["warte"],
                    "score": round(r["score"], 1),
                    "stationen": [graph.stationen[s]["name"] for s in r["stationen"]],
                    "linien": sorted({f["linie"] for f in r["fahrten"]}),
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[lo, la] for lo, la in koords],
                },
            }
        )
    (out / "routen.geojson").write_text(
        json.dumps(
            {"type": "FeatureCollection", "features": features},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    kml = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>',
        "<name>ÖPNV-Routen</name>",
    ]
    farben = ["ff0099ff", "ff00ff99", "ff9900ff"]
    for i in range(len(routen)):
        kml.append(
            f'<Style id="s{i}"><LineStyle><color>{farben[i % 3]}</color>'
            f"<width>4</width></LineStyle></Style>"
        )
    for i, r in enumerate(routen, 1):
        txt = " ".join(f"{lo},{la},0" for lo, la in punkte_pro_route[i - 1])
        kml.append(
            f"<Placemark><name>Route {i}: {r['dauer']} Min, "
            f"{len(r['umstiege'])} Umstiege</name>"
            f"<description>Score {r['score']:.1f}</description>"
            f"<styleUrl>#s{i - 1}</styleUrl><LineString><coordinates>{txt}"
            f"</coordinates></LineString></Placemark>"
        )
    kml.append("</Document></kml>")
    (out / "routen.kml").write_text("\n".join(kml), encoding="utf-8")

    gpx = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<gpx version="1.1" creator="oepnvrouten" '
        'xmlns="http://www.topografix.com/GPX/1/1">',
    ]
    for i, r in enumerate(routen, 1):
        gpx.append(f"<trk><name>Route {i} ({r['dauer']} Min)</name><trkseg>")
        for lo, la in punkte_pro_route[i - 1]:
            gpx.append(f'<trkpt lat="{la}" lon="{lo}"><ele>0</ele></trkpt>')
        gpx.append("</trkseg></trk>")
    gpx.append("</gpx>")
    (out / "routen.gpx").write_text("\n".join(gpx), encoding="utf-8")

    (out / "zusammenfassung.json").write_text(
        json.dumps(
            {"routen": routen, "anzahl": len(routen)}, ensure_ascii=False, indent=2
        ),
        encoding="utf-8",
    )
    log(f"Export nach {out}")


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# GTFS-Fahrplan-Routing (echte Abfahrts-/Ankunftszeiten)
# ---------------------------------------------------------------------------
GTFS_URL = "https://download.gtfs.de/germany/nv_free/latest.zip"
GTFS_ZIP = CACHE_DIR / "gtfs_nv.zip"


def gtfs_feed_laden(refresh=False):
    """Lädt den GTFS-Feed für Deutschland (gtfs.de, aus DELFI/NeTEx)."""
    if GTFS_ZIP.exists() and not refresh:
        log(f"  [Cache] GTFS-Feed ({GTFS_ZIP.stat().st_size / 1e6:.0f} MB)")
        return
    log("  Lade GTFS-Feed (kann >200 MB dauern)...")
    with requests.get(GTFS_URL, headers=HEADERS, stream=True, timeout=600) as r:
        r.raise_for_status()
        with open(GTFS_ZIP, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    log(f"  GTFS-Feed: {GTFS_ZIP.stat().st_size / 1e6:.0f} MB")


def gtfs_extraktion(bbox, datum, refresh=False):
    """Extrahiert Stops/Routen/Trips/Stop-Times der Region aus dem GTFS-Feed."""
    import csv
    import io
    import pickle
    import zipfile
    from datetime import date as _date

    s, w, n, e = bbox
    pkl = CACHE_DIR / f"gtfs_{datum}_{abs(hash(bbox)) % 100000}.pkl"
    if pkl.exists() and not refresh:
        log(f"  [Cache] GTFS-Extraktion {pkl.name}")
        return pickle.loads(pkl.read_bytes())

    gtfs_feed_laden(refresh)
    z = zipfile.ZipFile(GTFS_ZIP)

    def rows(name):
        with z.open(name) as f:
            yield from csv.DictReader(io.TextIOWrapper(f, encoding="utf-8"))

    stops = {}
    for r in rows("stops.txt"):
        lat, lon = float(r["stop_lat"]), float(r["stop_lon"])
        if s <= lat <= n and w <= lon <= e:
            stops[r["stop_id"]] = (r["stop_name"], lat, lon)
    log(f"  GTFS-Stops im Gebiet: {len(stops)}")

    wd = _date(int(datum[:4]), int(datum[4:6]), int(datum[6:])).weekday()
    tage = [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]
    cal, caldates = {}, {}
    for c in rows("calendar.txt"):
        cal[c["service_id"]] = c
    for c in rows("calendar_dates.txt"):
        caldates.setdefault(c["service_id"], []).append(c)

    def läuft(sid):
        c = cal.get(sid)
        if c and c["start_date"] <= datum <= c["end_date"] and c[tage[wd]] == "1":
            return True
        for cd in caldates.get(sid, []):
            if cd["date"] == datum:
                if cd["exception_type"] == "1":
                    return True
                if cd["exception_type"] == "2":
                    return False
        return False

    # Pass 1: Trip-IDs, die das Gebiet bedienen
    gebiet = set(stops)
    trip_ids = set()
    for st in rows("stop_times.txt"):
        if st["stop_id"] in gebiet:
            trip_ids.add(st["trip_id"])

    # route_id + shape_id + service am Datum
    trip_route = {}
    trip_shape = {}
    for t in rows("trips.txt"):
        if t["trip_id"] in trip_ids and läuft(t["service_id"]):
            trip_route[t["trip_id"]] = t["route_id"]
            trip_shape[t["trip_id"]] = t.get("shape_id") or ""

    route_info = {}
    for r in rows("routes.txt"):
        if r["route_id"] in set(trip_route.values()):
            route_info[r["route_id"]] = (
                r.get("route_short_name") or "",
                r.get("route_long_name") or "",
                int(r.get("route_type") or 3),
            )

    # Pass 2: Haltestellenfolgen
    trips = {tid: [trip_route[tid], []] for tid in trip_route}
    for st in rows("stop_times.txt"):
        tid = st["trip_id"]
        if tid in trips:
            hh, mm, _ = st["arrival_time"].split(":")
            arr = int(hh) * 60 + int(mm)
            hh, mm, _ = st["departure_time"].split(":")
            dep = int(hh) * 60 + int(mm)
            trips[tid][1].append((st["stop_id"], arr, dep))
    for tid in trips:
        trips[tid][1].sort(key=lambda s: s[2])

    # Streckengeometrie (shapes.txt) – nur Punkte im Gebiet
    shapes = {}
    for r in rows("shapes.txt"):
        lat, lon = float(r["shape_pt_lat"]), float(r["shape_pt_lon"])
        if s <= lat <= n and w <= lon <= e:
            shapes.setdefault(r["shape_id"], []).append(
                (int(r["shape_pt_sequence"]), lat, lon)
            )
    for sid in shapes:
        shapes[sid].sort()
    log(f"  GTFS-Shapes im Gebiet: {len(shapes)}")

    pkl.write_bytes(
        pickle.dumps(
            {
                "datum": datum,
                "stops": stops,
                "routes": route_info,
                "trips": trips,
                "trip_shape": trip_shape,
                "shapes": shapes,
            },
            protocol=4,
        )
    )
    log(f"  GTFS: {len(trips)} Trips gespeichert ({pkl.name})")
    return pickle.loads(pkl.read_bytes())


def gtfs_index(daten):
    """stop_id -> [(dep, trip_id, idx)] und Gehverbindungen zwischen nahen Stops."""
    import math as _m

    stops = daten["stops"]
    trips = daten["trips"]
    stop_trips = {}
    for tid, (_, seq) in trips.items():
        for i, (sid, _, dep) in enumerate(seq):
            stop_trips.setdefault(sid, []).append((dep, tid, i))
    for sid in stop_trips:
        stop_trips[sid].sort()

    ids = list(stops)
    walk = {i: [] for i in ids}
    try:
        import numpy as np
        from scipy.spatial import cKDTree

        lat0 = sum(s[1] for s in stops.values()) / len(stops)
        kx, ky = 111320.0 * _m.cos(_m.radians(lat0)), 110540.0
        pts = np.array([[stops[i][2] * kx, stops[i][1] * ky] for i in ids])
        for a, b in cKDTree(pts).query_pairs(400):
            ia, ib = ids[a], ids[b]
            d = haversine(stops[ia][1], stops[ia][2], stops[ib][1], stops[ib][2])
            t = max(2, round(d / 80))
            walk[ia].append((ib, t))
            walk[ib].append((ia, t))
    except ImportError:
        pass
    return stop_trips, walk


def gtfs_suche(
    daten, start_sid, ziel_sid, start_min, end_min, verbotene_trips=frozenset()
):
    """Früheste Ankunft (zeitabhängige Dijkstra-Variante)."""
    import bisect
    import heapq

    stops, trips = daten["stops"], daten["trips"]
    stop_trips, walk = gtfs_index(daten)
    best = {start_sid: start_min}
    prev = {}
    pq = [(start_min, start_sid, None)]
    ziel_zeit = None
    while pq:
        zeit, stop, quelle = heapq.heappop(pq)
        if zeit > end_min or (ziel_zeit is not None and zeit >= ziel_zeit):
            continue
        if zeit > best.get(stop, 10**9):
            continue
        prev[stop] = quelle
        if stop == ziel_sid:
            ziel_zeit = zeit
            continue
        for nb, dauer in walk.get(stop, []):
            nz = zeit + dauer
            if nz < best.get(nb, 10**9) and nz <= end_min:
                best[nb] = nz
                heapq.heappush(pq, (nz, nb, (stop, "walk", dauer, None)))
        kandidaten = stop_trips.get(stop, [])
        geprueft = 0
        for dep, tid, idx in kandidaten[
            bisect.bisect_left(kandidaten, (zeit, "", -1)) :
        ]:
            if dep > zeit + 90:
                break
            if tid in verbotene_trips:
                continue
            for j in range(idx + 1, len(trips[tid][1])):
                sid, arr, _ = trips[tid][1][j]
                if arr < best.get(sid, 10**9) and arr <= end_min:
                    best[sid] = arr
                    heapq.heappush(pq, (arr, sid, (stop, "trip", tid, j)))
            geprueft += 1
            if geprueft >= 40:
                break
    return ziel_zeit, prev, trips, stops


def gtfs_rekonstruiere(prev, ziel):
    """Baut aus den Dijkstra-Vorgängern die Bein-Liste der Verbindung."""
    legs, cur = [], ziel
    while cur is not None and prev.get(cur):
        q = prev[cur]
        if q[1] == "trip":
            legs.append(("trip", q[0], cur, q[2]))
        else:
            legs.append(("walk", q[0], cur, None))
        cur = q[0]
    legs.reverse()
    return legs


def clip_shape(daten, tid, von_xy, nach_xy):
    """Echter Streckenverlauf (aus shapes.txt) zwischen zwei Stationen.

    Die Haltestellen werden auf die Shape-Punkte projiziert und der
    Abschnitt zwischen ihnen zurückgegeben (Liste von (lon, lat)).
    """
    pts = daten.get("shapes", {}).get(daten.get("trip_shape", {}).get(tid, ""))
    if not pts:
        return None

    def naechster(xy):
        return min(
            range(len(pts)), key=lambda i: haversine(xy[1], xy[0], pts[i][1], pts[i][2])
        )

    i1, i2 = naechster(von_xy), naechster(nach_xy)
    lo, hi = sorted((i1, i2))
    return [(pts[i][2], pts[i][1]) for i in range(lo, hi + 1)]


def gtfs_verbindungen(daten, start_sid, ziel_sid, start_min, end_min, anzahl=3):
    """Bis zu `anzahl` unterschiedliche Verbindungen mit echten Zeiten."""
    ergebnisse, verboten = [], set()
    for _ in range(anzahl):
        zeit, prev, trips, stops = gtfs_suche(
            daten, start_sid, ziel_sid, start_min, end_min, frozenset(verboten)
        )
        if zeit is None:
            break
        abschnitte = []
        for leg in gtfs_rekonstruiere(prev, ziel_sid):
            if leg[0] == "walk":
                _, von, nach, _ = leg
                abschnitte.append(
                    {
                        "von": stops[von][0],
                        "nach": stops[nach][0],
                        "linie": "Fußweg",
                        "walk": True,
                        "von_xy": [stops[von][2], stops[von][1]],
                        "nach_xy": [stops[nach][2], stops[nach][1]],
                    }
                )
            else:
                _, von, nach, tid = leg
                route_id, seq = trips[tid]
                info = daten["routes"].get(route_id, ("", "", 3))
                kurz = info[0]
                lang = info[1] if len(info) > 1 else ""
                iv = next(k for k, s in enumerate(seq) if s[0] == von)
                inx = next(k for k, s in enumerate(seq) if s[0] == nach)
                von_xy = [stops[von][2], stops[von][1]]
                nach_xy = [stops[nach][2], stops[nach][1]]
                abschnitte.append(
                    {
                        "von": stops[von][0],
                        "nach": stops[nach][0],
                        "linie": kurz or lang,
                        "abfahrt": f"{seq[iv][2] // 60:02d}:{seq[iv][2] % 60:02d}",
                        "ankunft": f"{seq[inx][1] // 60:02d}:{seq[inx][1] % 60:02d}",
                        "von_xy": von_xy,
                        "nach_xy": nach_xy,
                        "punkte": clip_shape(daten, tid, von_xy, nach_xy),
                    }
                )
                verboten.add(tid)
        ergebnisse.append({"zeit": zeit, "abschnitte": abschnitte})
    return ergebnisse


def gtfs_export(ergebnisse, output, start_min, datum):
    """routen.geojson / .kml / .gpx / zusammenfassung.json mit echten Zeiten."""
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)

    features = []
    for i, e in enumerate(ergebnisse, 1):
        koords = []
        for a in e["abschnitte"]:
            segment_points = a.get("punkte") or [a.get("von_xy"), a.get("nach_xy")]
            for xy in segment_points:
                if xy and (not koords or koords[-1] != xy):
                    koords.append(xy)
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "route_id": i,
                    "dauer_min": e["zeit"] - start_min,
                    "ankunft": f"{e['zeit'] // 60:02d}:{e['zeit'] % 60:02d}",
                    "abschnitte": e["abschnitte"],
                },
                "geometry": {"type": "LineString", "coordinates": koords},
            }
        )
    (out / "routen.geojson").write_text(
        json.dumps(
            {"type": "FeatureCollection", "features": features},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    kml = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>',
        "<name>ÖPNV-Routen (GTFS)</name>",
    ]
    farben = ["ff0099ff", "ff00ff99", "ff9900ff"]
    for i in range(len(ergebnisse)):
        kml.append(
            f'<Style id="s{i}"><LineStyle><color>{farben[i % 3]}</color>'
            f"<width>4</width></LineStyle></Style>"
        )
    for i, e in enumerate(ergebnisse, 1):
        txt = " ".join(
            f"{lo},{la},0"
            for f in features[i - 1]["geometry"]["coordinates"]
            for lo, la in [f]
        )
        fahrten = [a for a in e["abschnitte"] if not a.get("walk")]
        kml.append(
            f"<Placemark><name>Route {i}: {fahrten[0]['abfahrt']} "
            f"-> {fahrten[-1]['ankunft']}</name>"
            f"<styleUrl>#s{i - 1}</styleUrl><LineString><coordinates>{txt}"
            f"</coordinates></LineString></Placemark>"
        )
    kml.append("</Document></kml>")
    (out / "routen.kml").write_text("\n".join(kml), encoding="utf-8")

    gpx = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<gpx version="1.1" creator="oepnvrouten" '
        'xmlns="http://www.topografix.com/GPX/1/1">',
    ]
    for i, e in enumerate(ergebnisse, 1):
        gpx.append(f"<trk><name>Route {i}</name><trkseg>")
        for lo, la in features[i - 1]["geometry"]["coordinates"]:
            gpx.append(f'<trkpt lat="{la}" lon="{lo}"><ele>0</ele></trkpt>')
        gpx.append("</trkseg></trk>")
    gpx.append("</gpx>")
    (out / "routen.gpx").write_text("\n".join(gpx), encoding="utf-8")

    (out / "zusammenfassung.json").write_text(
        json.dumps(
            {
                "quelle": "GTFS (gtfs.de nv_free)",
                "datum": datum,
                "verbindungen": ergebnisse,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    log(f"GTFS-Export nach {out}")


def _minutes(value):
    """HH:MM or ISO timestamp to service-day minutes."""
    if value is None:
        return None
    if "T" in value:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.hour * 60 + parsed.minute
    hour, minute = value.split(":")[:2]
    return int(hour) * 60 + int(minute)


def _point_from_value(value, endpoint="start"):
    if isinstance(value, str):
        return None
    if isinstance(value, dict) and "lat" in value and "lon" in value:
        return float(value["lat"]), float(value["lon"])
    if isinstance(value, dict) and value.get("type") == "Feature":
        declared = (value.get("properties") or {}).get(endpoint)
        if declared:
            return float(declared["lat"]), float(declared["lon"])
        geometry = value.get("geometry") or {}
        coordinates = geometry.get("coordinates")
        if geometry.get("type") == "Point":
            return float(coordinates[1]), float(coordinates[0])
        if geometry.get("type") == "LineString" and coordinates:
            point = coordinates[0 if endpoint == "start" else -1]
            return float(point[1]), float(point[0])
    return None


def _stop_candidates(value, stops, endpoint="start", limit=3):
    point = _point_from_value(value, endpoint)
    if point:
        lat, lon = point
        return [
            sid
            for _, sid in sorted(
                (haversine(lat, lon, stop[1], stop[2]), sid)
                for sid, stop in stops.items()
            )[:limit]
        ]
    if isinstance(value, str):
        return sorted(
            sid for sid, stop in stops.items() if value.lower() in stop[0].lower()
        )[:limit]
    return []


def _actual_departure(connection, fallback):
    rides = [part for part in connection["abschnitte"] if not part.get("walk")]
    return _minutes(rides[0]["abfahrt"]) if rides else fallback


def _filter_gtfs_connections(
    connections,
    duration_min,
    duration_max,
    arrival_window,
    departure_window=None,
):
    filtered = []
    arrival_start = _minutes((arrival_window or {}).get("start"))
    arrival_end = _minutes((arrival_window or {}).get("end"))
    departure_start = _minutes((departure_window or {}).get("start"))
    departure_end = _minutes((departure_window or {}).get("end"))
    for connection in connections:
        departure = _actual_departure(connection, 0)
        duration = connection["zeit"] - departure
        if departure_start is not None and departure < departure_start:
            continue
        if departure_end is not None and departure > departure_end:
            continue
        if not duration_min <= duration <= duration_max:
            continue
        if arrival_start is not None and connection["zeit"] < arrival_start:
            continue
        if arrival_end is not None and connection["zeit"] > arrival_end:
            continue
        connection["actual_departure"] = departure
        connection["duration"] = duration
        filtered.append(connection)
    return filtered


def export_normalized_gtfs(connections, output, iso_date, parameters):
    base_date = datetime.fromisoformat(iso_date).date()
    features = []
    for index, connection in enumerate(connections, 1):
        coordinates = []
        for part in connection["abschnitte"]:
            for point in part.get("punkte") or [
                part.get("von_xy"),
                part.get("nach_xy"),
            ]:
                if point and (not coordinates or coordinates[-1] != point):
                    coordinates.append(point)
        if len(coordinates) < 2:
            continue
        departure = connection.get("actual_departure", _actual_departure(connection, 0))
        start_time = datetime.combine(
            base_date, datetime.min.time()
        ).astimezone() + timedelta(minutes=departure)
        # Die lokale Systemzeitzone ist nur Fallback; der Orchestrator sollte
        # timezone explizit liefern.
        timezone_name = parameters.get("timezone")
        if timezone_name:
            from zoneinfo import ZoneInfo

            start_time = datetime.combine(
                base_date, datetime.min.time(), ZoneInfo(timezone_name)
            ) + timedelta(minutes=departure)
        end_time = start_time + timedelta(minutes=connection["zeit"] - departure)
        rides = [part for part in connection["abschnitte"] if not part.get("walk")]
        features.append(
            candidate_feature(
                candidate_id=f"gtfs-route:{index}",
                producer_skill="oepnvrouten",
                entity_type="transit_route",
                geometry={"type": "LineString", "coordinates": coordinates},
                start={"lat": coordinates[0][1], "lon": coordinates[0][0]},
                end={"lat": coordinates[-1][1], "lon": coordinates[-1][0]},
                temporal={
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat(),
                    "duration_minutes": (end_time - start_time).total_seconds() / 60,
                    "timezone": str(start_time.tzinfo),
                    "precision": "scheduled",
                },
                score=max(0.0, 1 - 0.05 * max(0, len(rides) - 1)),
                confidence=0.85,
                sources=[{"name": "GTFS", "schedule": "static"}],
                extra={
                    "segments": connection["abschnitte"],
                    "transfers": max(0, len(rides) - 1),
                },
            )
        )
    write_adapter_output(
        output,
        features,
        sources=[{"name": "GTFS", "schedule": "static"}],
        parameters=parameters,
    )


def export_normalized_osm(
    routen, points, output, iso_date, start_min, parameters, graph=None, stationen=None
):
    from zoneinfo import ZoneInfo

    timezone_name = parameters.get("timezone", "UTC")
    base = datetime.combine(
        datetime.fromisoformat(iso_date).date(),
        datetime.min.time(),
        ZoneInfo(timezone_name),
    )
    start_time = base + timedelta(minutes=start_min)
    features = []
    for index, (route, coordinates) in enumerate(zip(routen, points), 1):
        if len(coordinates) < 2:
            continue
        station_name = (
            (lambda node_id: stationen[node_id]["name"]) if stationen else None
        )
        abschnitte = []
        for fahrt in route.get("fahrten", []):
            linie = (
                graph.linien[fahrt["linie"]]["name"]
                if graph and fahrt["linie"] in graph.linien
                else fahrt.get("linie")
            )
            abschnitte.append(
                {
                    "linie": linie,
                    "dauer_min": fahrt.get("dauer"),
                    "mode": fahrt.get("mode"),
                    "von": (
                        station_name(fahrt["von"])
                        if station_name and fahrt.get("von") in stationen
                        else None
                    ),
                    "nach": (
                        station_name(fahrt["nach"])
                        if station_name and fahrt.get("nach") in stationen
                        else None
                    ),
                }
            )
        umstiege = []
        previous = None
        for abschnitt in abschnitte:
            if previous and abschnitt.get("von") and abschnitt["von"] != previous:
                umstiege.append(abschnitt["von"])
            previous = abschnitt.get("nach") or previous
        end_time = start_time + timedelta(minutes=route["dauer"])
        features.append(
            candidate_feature(
                candidate_id=f"osm-transit-route:{index}",
                producer_skill="oepnvrouten",
                entity_type="transit_route",
                geometry={
                    "type": "LineString",
                    "coordinates": [[lon, lat] for lon, lat in coordinates],
                },
                start={"lat": coordinates[0][1], "lon": coordinates[0][0]},
                end={"lat": coordinates[-1][1], "lon": coordinates[-1][0]},
                temporal={
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat(),
                    "duration_minutes": route["dauer"],
                    "timezone": timezone_name,
                    "precision": "estimated",
                },
                score=max(0.0, 1 - float(route["score"]) / 1000),
                confidence=0.35,
                sources=[{"name": "OpenStreetMap", "routing": "estimated"}],
                warnings=[
                    "Kein Fahrplan: Zeiten sind geschätzt; einzelne Geometriesegmente können Notfall-Fallbacks sein"
                ],
                extra={
                    "transfers": len(route["umstiege"]),
                    "estimated": True,
                    "segments": abschnitte,
                    "umstiegsstationen": umstiege,
                },
            )
        )
    write_adapter_output(
        output,
        features,
        status="degraded",
        warnings=["GTFS-Routing nicht verfügbar; OSM-Zeiten sind Schätzwerte"],
        sources=[{"name": "OpenStreetMap"}],
        parameters=parameters,
    )


def main():
    ap = argparse.ArgumentParser(description="ÖPNV-Routen finden")
    ap.add_argument(
        "--stadt", help="Stadt oder Stadtteil (z. B. 'Berlin, Deutschland')"
    )
    ap.add_argument("--bbox", type=float, nargs=4, metavar=("S", "W", "N", "E"))
    ap.add_argument("--datum", default="2026-10-16", help="Startdatum (ISO)")
    ap.add_argument("--uhrzeit", default="15:00", help="Startzeit (HH:MM)")
    ap.add_argument("--start", help="Startpunkt (Name)")
    ap.add_argument("--end", help="Endpunkt (Name)")
    ap.add_argument("--dauer-min", type=int, default=60)
    ap.add_argument("--dauer-max", type=int, default=120)
    ap.add_argument("--umstiege-min", type=int, default=1)
    ap.add_argument("--umstiege-max", type=int, default=5)
    ap.add_argument("--qid", help="Wikidata-QID des Ortes (nie raten)")
    ap.add_argument("--output", default="ergebnis")
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--request", help="Workflow-Knoten als JSON")
    ap.add_argument(
        "--orchestrated",
        action="store_true",
        help="Normalisierten Adaptermodus verwenden",
    )
    args = ap.parse_args()

    request = load_node_request(args.request)
    parameters = request["parameters"] if request else {}
    start_value, end_value = args.start, args.end
    arrival_window = None
    departure_window = None
    if request:
        bbox, place = resolve_region(parameters["region"])
        args.bbox, args.stadt = bbox, place
        if isinstance(parameters["region"], dict) and parameters["region"].get(
            "timezone"
        ):
            parameters.setdefault("timezone", parameters["region"]["timezone"])
        args.datum = parameters["date"]
        departure_window = parameters.get("departure_window") or {}
        args.uhrzeit = departure_window.get(
            "start", parameters.get("uhrzeit", args.uhrzeit)
        )
        if "T" in args.uhrzeit:
            args.uhrzeit = args.uhrzeit.split("T", 1)[1][:5]
        start_value, end_value = parameters["start"], parameters["end"]
        args.dauer_min = int(parameters.get("duration_min", args.dauer_min))
        args.dauer_max = int(parameters.get("duration_max", args.dauer_max))
        args.umstiege_min = int(parameters.get("transfers_min", args.umstiege_min))
        args.umstiege_max = int(parameters.get("transfers_max", args.umstiege_max))
        arrival_window = parameters.get("arrival_window")

    if not args.stadt and not args.bbox:
        ap.error("--stadt oder --bbox erforderlich")
    if start_value is None or end_value is None:
        ap.error("--start/--end oder parameters.start/parameters.end erforderlich")
    bbox = bbox_fuer_stadt(args.stadt, args.refresh) if args.stadt else tuple(args.bbox)
    log(f"BBox {bbox}")

    hh, mm = args.uhrzeit.split(":")
    start_min = int(hh) * 60 + int(mm)
    datum = args.datum.replace("-", "")

    # ---- Primär: GTFS-Fahrplan-Routing (echte Abfahrts-/Ankunftszeiten) ----
    try:
        daten = gtfs_extraktion(bbox, datum, args.refresh)
        ts = _stop_candidates(start_value, daten["stops"], "end")
        tz = _stop_candidates(end_value, daten["stops"], "start")
        if ts and tz:
            verbindungen = []
            for start_sid in ts:
                for target_sid in tz:
                    verbindungen.extend(
                        gtfs_verbindungen(
                            daten, start_sid, target_sid, start_min, start_min + 360
                        )
                    )
            verbindungen = _filter_gtfs_connections(
                verbindungen,
                args.dauer_min,
                args.dauer_max,
                arrival_window,
                departure_window,
            )
            verbindungen.sort(
                key=lambda connection: (connection["zeit"], connection["duration"])
            )
            verbindungen = verbindungen[:3]
            if verbindungen:
                gtfs_export(verbindungen, args.output, start_min, datum)
                export_normalized_gtfs(
                    verbindungen, args.output, args.datum, parameters
                )
                for i, v in enumerate(verbindungen, 1):
                    fahrten = [a for a in v["abschnitte"] if not a.get("walk")]
                    log(
                        f"  Verbindung {i}: {fahrten[0]['abfahrt']} -> "
                        f"{fahrten[-1]['ankunft']} "
                        f"({len(fahrten)} Fahrten)"
                    )
                return
            log("GTFS: keine Verbindung gefunden – Fallback auf OSM-Routing")
        else:
            log("GTFS: Start/Ziel nicht im Fahrplan – Fallback auf OSM-Routing")
    except Exception as err:
        log(f"GTFS-Routing fehlgeschlagen ({type(err).__name__}: {err})")

    # ---- Fallback: OSM-Routing (Spiel-Routen mit Schätzzeiten) ----
    stationen = lade_stationen(bbox, args.refresh)
    log(f"{len(stationen)} Stationen")
    gruppen = cluster_stationen(stationen)
    log(f"{len(gruppen)} Verkehrsknoten nach Clustering")

    graph = Graph()
    cluster_von = {}
    for root, mitglieder in gruppen.items():
        for m in mitglieder:
            cluster_von[m] = root
        repraesentant = merge_gruppe(mitglieder, stationen)
        repraesentant["id"] = root
        graph.add_station(repraesentant)

    excludes = tuple(parameters.get("exclude_route_prefixes") or [])
    for route in ["subway", "train", "tram", "light_rail", "bus"]:
        linien = lade_linien(bbox, route, args.refresh)
        if excludes:
            behalten = [
                linie
                for linie in linien
                if not str(linie.get("name", "")).upper().startswith(excludes)
            ]
            if len(behalten) != len(linien):
                log(
                    f"  {route}: {len(linien) - len(behalten)} Linien per "
                    f"exclude_route_prefixes ausgeschlossen"
                )
            linien = behalten
        n = sum(graph.add_linie(l, cluster_von) for l in linien)
        log(f"  {route}: {len(linien)} Linien, {n} Kanten")
    log(
        f"Graph: {len(graph.stationen)} Stationen, "
        f"{sum(len(v) for v in graph.nachbarn.values())} Kanten"
    )

    def finde(name):
        clusters = sorted(
            {
                cluster_von[s["id"]]
                for s in stationen.values()
                if name.lower() in s["name"].lower()
            }
        )
        # Deterministisch: größter Verbundknoten gewinnt (Bahnhofs-/Umstiegs-
        # gelände sind die größten Cluster mit dem Namen; reine Bushaltestellen
        # sind klein).
        cluster_groessen = {
            root: len(mitglieder) for root, mitglieder in gruppen.items()
        }
        clusters.sort(key=lambda tid: (-cluster_groessen.get(tid, 0), tid))
        return clusters

    if not isinstance(start_value, str) or not isinstance(end_value, str):
        error = RuntimeError(
            "GTFS lieferte keine Route; der OSM-Fallback unterstützt derzeit "
            "nur namentliche Start-/Zielpunkte"
        )
        write_adapter_output(
            args.output,
            [],
            sources=[{"name": "GTFS"}, {"name": "OpenStreetMap"}],
            parameters=parameters,
            error=error,
        )
        raise SystemExit(str(error))
    start_id = finde(start_value)
    ziel_id = finde(end_value)
    for label, treffer, name in [
        ("Start", start_id, start_value),
        ("Ziel", ziel_id, end_value),
    ]:
        log(
            f"{label} '{name}': "
            + (
                ", ".join(f"{graph.stationen[t]['name']} ({t})" for t in treffer[:3])
                or "KEIN TREFFER"
            )
        )
        if not treffer:
            raise SystemExit(f"{label} '{name}' nicht gefunden")

    routen = finde_routen(
        graph,
        start_id[0],
        ziel_id[0],
        args.dauer_min,
        args.dauer_max,
        args.umstiege_min,
        args.umstiege_max,
    )
    log(f"{len(routen)} Routen gefunden")
    for i, r in enumerate(routen, 1):
        linien = sorted({graph.linien[f["linie"]]["name"] for f in r["fahrten"]})
        log(
            f"  Route {i}: {r['dauer']} Min, {len(r['umstiege'])} Umstiege, "
            f"Score {r['score']:.1f} | {', '.join(linien)}"
        )

    if arrival_window:
        arrival_start = _minutes((arrival_window or {}).get("start"))
        arrival_end = _minutes((arrival_window or {}).get("end"))
        before = len(routen)
        routen = [
            route
            for route in routen
            if (arrival_start is None or start_min + route["dauer"] >= arrival_start)
            and (arrival_end is None or start_min + route["dauer"] <= arrival_end)
        ]
        if len(routen) != before:
            log(f"Ankunftsfenster: {before - len(routen)} Routen abgewiesen")

    if routen:
        linien_ids = sorted({f["linie"] for r in routen for f in r["fahrten"]})
        log(f"Echte Fahrwege für {len(linien_ids)} Linien laden...")
        line_geom = lade_linien_geometrie(linien_ids, args.refresh)
        punkte = [route_punkte_real(r, line_geom, gruppen, graph) for r in routen]
        real = sum(1 for p in punkte if len(p) > 50)
        log(f"Echte Strecken: {real}/{len(routen)} Routen mit Fahrweg-Geometrie")
        export(routen, graph, args.output, punkte)
        export_normalized_osm(
            routen,
            punkte,
            args.output,
            args.datum,
            start_min,
            parameters,
            graph,
            stationen,
        )
    elif request:
        write_adapter_output(
            args.output,
            [],
            status="empty",
            warnings=["Weder GTFS noch OSM-Fallback lieferte eine passende Route"],
            sources=[{"name": "GTFS"}, {"name": "OpenStreetMap"}],
            parameters=parameters,
        )


if __name__ == "__main__":
    main()
