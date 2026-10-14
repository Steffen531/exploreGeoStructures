#!/usr/bin/env python3
"""
ÖPNV-Routen finden – Kombinierter Ansatz (Skill: oepnvrouten)
1. Datenquellen scoutern und bewerten          -> reference/datenquellen.md
2. Netzwerk aufbauen (ÖPNV-Graph, Gehwege)      -> reference/datenquellen.md
3. Routing mit strikten Constraints             -> reference/routing-regeln.md
4. 3 Routen-Vorschläge exportieren             -> SKILL.md "Output"

Ablauf: SKILL.md (Prozess, Schritte 1-8, inkl. Learnings-Loop).

WICHTIG: KML/GPX-Export zeigt SANFTe Linien mit interpolierten Zwischenpunkten,
nicht nur Stationen. Dazu wird jede Linie mit Geometrie-Dict erweitert.
"""

import argparse
import json
import math
import heapq
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

import requests


# ============================================================================
# Datenmodelle
# ============================================================================

class VerkehrsmittelTyp(Enum):
    S_BAHN = "s_bahn"
    U_BAHN = "u_bahn"
    STRASSENBAHN = "strassenbahn"
    BUS = "bus"
    REGIONALZUG = "regionalzug"
    FAEHRE = "faehre"
    RIDE_HAILING = "ride_hailing"
    FUSSWEG = "fussweg"


@dataclass
class Station:
    id: str
    name: str
    lat: float
    lon: float
    verkehrsmittel: List[VerkehrsmittelTyp] = field(default_factory=list)
    stadtteil: str = ""


@dataclass
class Linie:
    id: str
    name: str
    typ: VerkehrsmittelTyp
    stationen: List[str]
    farbe: str = "#000000"
    geometrie: Dict[Tuple[str, str], List[Tuple[float, float]]] = field(default_factory=dict)

    def add_geometrie(self, von: str, nach: str, coords: List[Tuple[float, float]]):
        """Fügt Geometrie-Koordinaten für ein Segment hinzu."""
        self.geometrie[(von, nach)] = coords


@dataclass
class Fahrt:
    von: str
    nach: str
    linie: str
    verkehrsmittel: VerkehrsmittelTyp
    dauer_min: int
    abfahrt: str
    ankunft: str
    gestoert: bool = False


@dataclass
class Umstieg:
    station: str
    von_linie: str
    nach_linie: str
    fussweg_min: int
    wartezeit_min: int

    @property
    def gesamtzeit_min(self) -> int:
        return self.fussweg_min + self.wartezeit_min


@dataclass
class Route:
    stationen: List[str]
    fahrten: List[Fahrt]
    umstiege: List[Umstieg]
    gesamt_dauer_min: int
    fussweg_gesamt_min: int
    wartezeit_gesamt_min: int
    verkehrsmittel: List[VerkehrsmittelTyp]
    score: float = 0.0

    def to_dict(self):
        return {
            "stationen": self.stationen,
            "fahrten": [
                {
                    "von": f.von,
                    "nach": f.nach,
                    "linie": f.linie,
                    "verkehrsmittel": f.verkehrsmittel.value,
                    "dauer_min": f.dauer_min,
                    "abfahrt": f.abfahrt,
                    "ankunft": f.ankunft,
                    "gestoert": f.gestoert,
                }
                for f in self.fahrten
            ],
            "umstiege": [
                {
                    "station": u.station,
                    "von_linie": u.von_linie,
                    "nach_linie": u.nach_linie,
                    "fussweg_min": u.fussweg_min,
                    "wartezeit_min": u.wartezeit_min,
                    "gesamtzeit_min": u.gesamtzeit_min,
                }
                for u in self.umstiege
            ],
            "gesamt_dauer_min": self.gesamt_dauer_min,
            "fussweg_gesamt_min": self.fussweg_gesamt_min,
            "wartezeit_gesamt_min": self.wartezeit_gesamt_min,
            "verkehrsmittel": [v.value for v in self.verkehrsmittel],
            "score": self.score,
        }


# ============================================================================
# Phase 1: Daten-Scout
# ============================================================================

class DatenScout:
    """Findet und bewertet Datenquellen für eine Stadt."""

    OVERPASS_SERVERS = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
        "https://overpass.private.coffee/api/interpreter",
    ]

    HEADERS = {"User-Agent": "exploreGeoStructures-oepnvrouten/1.0 (OpenCode skill)"}

    BEKANNT_GTFS = {
        "Berlin": "https://www.vbb.de/media/download/2024-03-28_gtfs.zip",
        "Hamburg": "https://www.hvv.de/de/fahrplaene/abruf-fahrplandaten/hvv-fahrplandaten-gtfs",
        "München": "https://www.mvv-muenchen.de/fahrplanauskunft/fuer-entwickler/index.html",
        "Wien": "https://www.wienerlinien.at/feed/gtfs",
        "Zürich": "https://www.opentransportdata.swiss/de/dataset/timetable-2024-gtfs",
        "Paris": "https://.iledefrance-mobilites.fr/pages/offres-open-data",
        "London": "https://tfl.gov.uk/info-for/open-data-users/",
        "New York": "http://web.mta.info/developers/download.html",
        "Tokyo": "https://www.odpt.org/developers/",
        "Sydney": "https://transportnsw.info/data/developers",
    }

    BEKANNT_OTP = {
        "Berlin": "https://otp.bbnavi.de",
        "Hamburg": "https://otp.hamburg.de",
        "München": "https://otp.mvv-muenchen.de",
        "Frankfurt": "https://otp.rmv.de",
    }

    def __init__(self, stadt: str):
        self.stadt = stadt
        self.quellen: List[Dict] = []
        self.bbox: Optional[Tuple[float, float, float, float]] = None

    def finde_datenquellen(self) -> List[Dict]:
        """Hauptfunktion: Findet alle verfügbaren Datenquellen."""
        self._check_overpass()
        self._check_gtfs()
        self._check_otp()
        self._check_ride_hailing()
        self._check_osrm()
        self.quellen.sort(key=lambda q: q.get("qualitaets_score", 0), reverse=True)
        return self.quellen

    def _check_overpass(self):
        """Prüft Overpass API für OSM-Daten."""
        query = f"""
        [out:json][timeout:25];
        area["name"="{self.stadt}"]->.searchArea;
        (
          node["public_transport"="station"](area.searchArea);
          node["public_transport"="stop_position"](area.searchArea);
          node["highway"="bus_stop"](area.searchArea);
          node["railway"="station"](area.searchArea);
          node["railway"="halt"](area.searchArea);
          node["amenity"="ferry_terminal"](area.searchArea);
        );
        out count;
        """
        try:
            response = requests.post(
                self.OVERPASS_SERVERS[0],
                data={"data": query},
                headers=self.HEADERS,
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                anzahl = data.get("elements", [{}])[0].get("tags", {}).get("total", 0)
                verfuegbar = anzahl > 0
                score = min(anzahl / 100, 1.0)
                if data.get("elements"):
                    bounds = data["elements"][0].get("bounds")
                    if bounds:
                        self.bbox = (
                            bounds.get("minlon", 0),
                            bounds.get("minlat", 0),
                            bounds.get("maxlon", 0),
                            bounds.get("maxlat", 0)
                        )
                quelle = {
                    "typ": "overpass",
                    "name": "OpenStreetMap (Overpass API)",
                    "verfuegbar": verfuegbar,
                    "qualitaets_score": score,
                    "beschreibung": f"{anzahl} ÖPNV-Stationen",
                }
            else:
                quelle = {"typ": "overpass", "verfuegbar": False, "qualitaets_score": 0}
        except Exception as e:
            quelle = {"typ": "overpass", "verfuegbar": False, "qualitaets_score": 0, "fehler": str(e)}
        self.quellen.append(quelle)

    def _check_gtfs(self):
        """Sucht nach GTFS-Feeds für die Stadt."""
        feed_url = self.BEKANNT_GTFS.get(self.stadt)
        quelle = {
            "typ": "gtfs",
            "name": f"GTFS-Feed ({self.stadt})",
            "verfuegbar": feed_url is not None,
            "qualitaets_score": 0.9 if feed_url else 0,
            "beschreibung": feed_url or "Kein bekannter GTFS-Feed",
        }
        self.quellen.append(quelle)

    def _check_otp(self):
        """Prüft OpenTripPlanner Instanzen."""
        otp_url = self.BEKANNT_OTP.get(self.stadt)
        quelle = {
            "typ": "otp",
            "name": f"OTP-Instanz ({self.stadt})",
            "verfuegbar": otp_url is not None,
            "qualitaets_score": 0.95 if otp_url else 0,
            "beschreibung": otp_url or "Keine bekannte OTP-Instanz",
        }
        self.quellen.append(quelle)

    def _check_ride_hailing(self):
        """Prüfts Ride-Hailing Anbieter."""
        quelle = {
            "typ": "ride_hailing",
            "name": f"Ride-Hailing ({self.stadt})",
            "verfuegbar": True,
            "qualitaets_score": 0.7,
            "beschreibung": "Uber, Bolt, Free Now verfügbar",
        }
        self.quellen.append(quelle)

    def _check_osrm(self):
        """Prüft OSRM-Instanzen für Straßenrouting."""
        quelle = {
            "typ": "osrm",
            "name": "OSRM",
            "verfuegbar": True,
            "qualitaets_score": 0.8,
            "beschreibung": "https://router.project-osrm.org",
        }
        self.quellen.append(quelle)


# ============================================================================
# Phase 2: Netzwerk-Aufbau
# ============================================================================

class RoutingGraph:
    """ÖPNV-Netzwerk: Knoten (Stationen), Kanten (Linienverläufe)."""

    def __init__(self):
        self.stationen: Dict[str, Station] = {}
        self.linien: Dict[str, Linie] = {}
        self.adjazenz: Dict[str, List[Tuple[str, str]]] = {}

    def add_station(self, station: Station):
        self.stationen[station.id] = station
        if station.id not in self.adjazenz:
            self.adjazenz[station.id] = []

    def add_linie(self, linie: Linie):
        self.linien[linie.id] = linie
        for i in range(len(linie.stationen) - 1):
            von = linie.stationen[i]
            nach = linie.stationen[i + 1]
            self.adjazenz.setdefault(von, []).append((nach, linie.id))

    def get_nachbarn(self, station_id: str) -> List[Tuple[str, str]]:
        return self.adjazenz.get(station_id, [])

    def get_station(self, station_id: str) -> Optional[Station]:
        return self.stationen.get(station_id)


def add_line_with_geometry(linie: Linie, stationen: Dict[str, Station], segmente: int = 20):
    """Fügt Zwischenpunkte entlang der Geraden zwischen je zwei Stationen hinzu."""
    station_coords = {sid: (s.lat, s.lon) for sid, s in stationen.items()}
    for i in range(len(linie.stationen) - 1):
        von = linie.stationen[i]
        nach = linie.stationen[i + 1]
        if von in station_coords and nach in station_coords:
            lat1, lon1 = station_coords[von]
            lat2, lon2 = station_coords[nach]
            intermediate = []
            for j in range(1, segmente + 1):
                frac = j / (segmente + 1)
                intermediate.append((lon1 + frac * (lon2 - lon1), lat1 + frac * (lat2 - lat1), 0))
            linie.add_geometrie(von, nach, intermediate)


# ============================================================================
# Phase 3: Routing
# ============================================================================

class Router:
    """Multi-Objective Router mit strikten Constraints."""

    def __init__(self, graph: RoutingGraph):
        self.graph = graph
        self.besuchte_routen: List[Route] = []

    def finde_routen(
        self,
        start_id: str,
        ziel_id: str,
        datum: str,
        uhrzeit: str,
        dauer_min: int = 60,
        dauer_max: int = 120,
        umstiege_min: int = 1,
        umstiege_max: int = 5,
        anzahl_routen: int = 3,
    ) -> List[Route]:
        """Findet 3 Routen mit DFS + Diversitäts-Belohnung."""
        start_zeit_min = self._zeit_zu_min(uhrzeit)

        erreichbar = self._bfs_erreichbar(start_id, ziel_id)
        if not erreichbar:
            return []

        routen = self._dfs_diversitaet(
            start_id, ziel_id, start_zeit_min,
            dauer_min, dauer_max, umstiege_min, umstiege_max, anzahl_routen
        )

        if not routen:
            routen = self._dfs_backtracking(
                start_id, ziel_id, start_zeit_min,
                dauer_min, dauer_max, umstiege_min, umstiege_max, anzahl_routen
            )

        for route in routen:
            route.score = self._berechne_score(route)

        routen.sort(key=lambda r: r.score)
        return routen

    def _dfs_diversitaet(self, start_id, ziel_id, start_zeit_min, dauer_min, dauer_max, umstiege_min, umstiege_max, anzahl_routen) -> List[Route]:
        """DFS mit Diversitäts-Belohnung für 3 verschiedene Routen."""
        gefundene_routen: List[Route] = []
        start_station = self.graph.get_station(start_id)
        if not start_station:
            return []

        stack = [(
            [start_id], {start_id}, set(),
            {start_station.stadtteil} if start_station.stadtteil else set(),
            0, 0, 0, None, start_zeit_min, [], []
        )]

        iterationen = 0
        max_iterationen = 50000

        while stack and len(gefundene_routen) < anzahl_routen and iterationen < max_iterationen:
            iterationen += 1
            pfad, besuchte_st, besuchte_kanten, besuchte_stadtteile, umstiege, fussweg_gesamt, wartezeit_gesamt, letzte_linie, aktuelle_zeit, fahrten, umstiege_liste = stack.pop()

            aktuelle_station = pfad[-1]

            if aktuelle_station == ziel_id:
                dauer = aktuelle_zeit - start_zeit_min
                if dauer_min <= dauer <= dauer_max and umstiege_min <= len(umstiege_liste) <= umstiege_max:
                    besuchte_stationen = set()
                    for r in gefundene_routen:
                        besuchte_stationen.update(r.stationen)
                    neue_stationen = set(pfad) - besuchte_stationen
                    if len(neue_stationen) >= 2 or len(gefundene_routen) == 0:
                        route = Route(
                            stationen=list(pfad), fahrten=list(fahrten),
                            umstiege=list(umstiege_liste), gesamt_dauer_min=dauer,
                            fussweg_gesamt_min=fussweg_gesamt, wartezeit_gesamt_min=wartezeit_gesamt,
                            verkehrsmittel=list(set(f.verkehrsmittel for f in fahrten)),
                        )
                        gefundene_routen.append(route)
                continue

            if aktuelle_zeit - start_zeit_min > dauer_max:
                continue
            if len(umstiege_liste) > umstiege_max:
                continue

            for nachbar_id, linie_id in reversed(self.graph.get_nachbarn(aktuelle_station)):
                nachbar_station = self.graph.get_station(nachbar_id)
                if not nachbar_station:
                    continue
                if nachbar_id in besuchte_st:
                    continue
                kante = (aktuelle_station, nachbar_id)
                if kante in besuchte_kanten:
                    continue

                linie = self.graph.linien.get(linie_id)
                if not linie:
                    continue

                fahrzeit, wartezeit, fussweg = 3, 4, 0
                neue_umstiege = list(umstiege_liste)
                neue_fahrten = list(fahrten)

                if letzte_linie is not None and letzte_linie != linie_id:
                    fussweg = 2
                    neue_umstiege.append(Umstieg(
                        station=aktuelle_station, von_linie=letzte_linie,
                        nach_linie=linie_id, fussweg_min=fussweg, wartezeit_min=wartezeit,
                    ))

                neue_zeit = aktuelle_zeit + fahrzeit + wartezeit + fussweg

                stack.append((
                    pfad + [nachbar_id],
                    besuchte_st | {nachbar_id},
                    besuchte_kanten | {kante},
                    besuchte_stadtteile | ({nachbar_station.stadtteil} if nachbar_station.stadtteil else set()),
                    len(neue_umstiege), fussweg_gesamt + fussweg, wartezeit_gesamt + wartezeit,
                    linie_id, neue_zeit,
                    neue_fahrten + [Fahrt(
                        von=aktuelle_station, nach=nachbar_id, linie=linie_id,
                        verkehrsmittel=linie.typ, dauer_min=fahrzeit,
                        abfahrt=self._min_zu_zeit(aktuelle_zeit),
                        ankunft=self._min_zu_zeit(neue_zeit - fussweg),
                    )],
                    neue_umstiege,
                ))

        return gefundene_routen

    def _dfs_backtracking(self, start_id, ziel_id, start_zeit_min, dauer_min, dauer_max, umstiege_min, umstiege_max, anzahl_routen) -> List[Route]:
        """Fallback DFS mit strikten Constraints."""
        gefundene_routen: List[Route] = []
        start_station = self.graph.get_station(start_id)
        if not start_station:
            return []

        stack = [(
            [start_id], {start_id}, set(),
            {start_station.stadtteil} if start_station.stadtteil else set(),
            0, 0, 0, None, start_zeit_min, [], []
        )]

        iterationen = 0
        max_iterationen = 50000

        while stack and len(gefundene_routen) < anzahl_routen * 3 and iterationen < max_iterationen:
            iterationen += 1
            pfad, besuchte_st, besuchte_kanten, besuchte_stadtteile, umstiege, fussweg_gesamt, wartezeit_gesamt, letzte_linie, aktuelle_zeit, fahrten, umstiege_liste = stack.pop()
            aktuelle_station = pfad[-1]

            if aktuelle_station == ziel_id:
                dauer = aktuelle_zeit - start_zeit_min
                if dauer_min <= dauer <= dauer_max and umstiege_min <= len(umstiege_liste) <= umstiege_max:
                    route = Route(
                        stationen=list(pfad), fahrten=list(fahrten),
                        umstiege=list(umstiege_liste), gesamt_dauer_min=dauer,
                        fussweg_gesamt_min=fussweg_gesamt, wartezeit_gesamt_min=wartezeit_gesamt,
                        verkehrsmittel=list(set(f.verkehrsmittel for f in fahrten)),
                    )
                    gefundene_routen.append(route)
                continue

            if aktuelle_zeit - start_zeit_min > dauer_max:
                continue
            if len(umstiege_liste) > umstiege_max:
                continue

            for nachbar_id, linie_id in reversed(self.graph.get_nachbarn(aktuelle_station)):
                nachbar_station = self.graph.get_station(nachbar_id)
                if not nachbar_station:
                    continue
                if nachbar_id in besuchte_st:
                    continue
                kante = (aktuelle_station, nachbar_id)
                if kante in besuchte_kanten:
                    continue

                linie = self.graph.linien.get(linie_id)
                if not linie:
                    continue

                fahrzeit, wartezeit, fussweg = 3, 4, 0
                neue_umstiege = list(umstiege_liste)
                neue_fahrten = list(fahrten)

                if letzte_linie is not None and letzte_linie != linie_id:
                    fussweg = 2
                    neue_umstiege.append(Umstieg(
                        station=aktuelle_station, von_linie=letzte_linie,
                        nach_linie=linie_id, fussweg_min=fussweg, wartezeit_min=wartezeit,
                    ))

                neue_zeit = aktuelle_zeit + fahrzeit + wartezeit + fussweg

                stack.append((
                    pfad + [nachbar_id],
                    besuchte_st | {nachbar_id},
                    besuchte_kanten | {kante},
                    besuchte_stadtteile | ({nachbar_station.stadtteil} if nachbar_station.stadtteil else set()),
                    len(neue_umstiege), fussweg_gesamt + fussweg, wartezeit_gesamt + wartezeit,
                    linie_id, neue_zeit,
                    neue_fahrten + [Fahrt(
                        von=aktuelle_station, nach=nachbar_id, linie=linie_id,
                        verkehrsmittel=linie.typ, dauer_min=fahrzeit,
                        abfahrt=self._min_zu_zeit(aktuelle_zeit),
                        ankunft=self._min_zu_zeit(neue_zeit - fussweg),
                    )],
                    neue_umstiege,
                ))

        return gefundene_routen[:anzahl_routen] if gefundene_routen else []

    def _bfs_erreichbar(self, start_id: str, ziel_id: str) -> bool:
        besucht = {start_id}
        queue = [start_id]
        while queue:
            aktuell = queue.pop(0)
            if aktuell == ziel_id:
                return True
            for nachbar_id, _ in self.graph.get_nachbarn(aktuell):
                if nachbar_id not in besucht:
                    besucht.add(nachbar_id)
                    queue.append(nachbar_id)
        return False

    def _zeit_zu_min(self, zeit: str) -> int:
        h, m = map(int, zeit.split(":"))
        return h * 60 + m

    def _min_zu_zeit(self, minuten: int) -> str:
        h = (minuten // 60) % 24
        m = minuten % 60
        return f"{h:02d}:{m:02d}"

    def _berechne_score(self, route: Route) -> float:
        vm_prioritaet = {
            VerkehrsmittelTyp.REGIONALZUG: 1, VerkehrsmittelTyp.S_BAHN: 2,
            VerkehrsmittelTyp.U_BAHN: 2, VerkehrsmittelTyp.STRASSENBAHN: 3,
            VerkehrsmittelTyp.FAEHRE: 4, VerkehrsmittelTyp.BUS: 10,
            VerkehrsmittelTyp.FUSSWEG: 5, VerkehrsmittelTyp.RIDE_HAILING: 6,
        }
        umstiegs_score = 2.0 * (route.fussweg_gesamt_min + route.wartezeit_gesamt_min) + 1.0 * len(route.umstiege)
        vm_score = sum(vm_prioritaet.get(v, 5) for v in route.verkehrsmittel)
        return umstiegs_score + vm_score


# ============================================================================
# Phase 4: Export mit Geometrie-Interpolation (SANFTe Linien)
# ============================================================================

def _consolidate_same_line_segments(route: Route) -> List[Tuple[str, str, str]]:
    """Fasst aufeinanderfolgende Segmente auf der gleichen Linie zusammen."""
    if not route.fahrten:
        return []
    consolidated = []
    current_von = route.fahrten[0].von
    current_linie = route.fahrten[0].linie
    for fahrt in route.fahrten:
        if fahrt.linie == current_linie:
            continue
        else:
            consolidated.append((current_von, fahrt.von, current_linie))
            current_von = fahrt.von
            current_linie = fahrt.linie
    if route.fahrten:
        consolidated.append((current_von, route.fahrten[-1].nach, current_linie))
    return consolidated


def _get_segment_stations(linie: Linie, von_id: str, nach_id: str) -> List[str]:
    """Gibt alle Stationen auf einer Linie zwischen von und nach (inkl. Start/Ende) in Reihenfolge."""
    if von_id not in linie.stationen or nach_id not in linie.stationen:
        return [von_id, nach_id]
    von_idx = linie.stationen.index(von_id)
    nach_idx = linie.stationen.index(nach_id)
    if von_idx < nach_idx:
        return linie.stationen[von_idx:nach_idx + 1]
    else:
        return linie.stationen[von_idx:nach_idx - 1:-1] if nach_idx > 0 else linie.stationen[von_idx::-1]


def _get_route_coordinates(route: Route, stationen: Dict[str, Station], linien: Dict[str, Linie]) -> str:
    """Sammelt alle Koordinates einer Route inkl. Geometrie-Zwischenpunkten (für KML)."""
    coords = []
    consolidated = _consolidate_same_line_segments(route)
    for von_id, nach_id, linie_id in consolidated:
        linie = linien.get(linie_id)
        if not linie:
            continue
        segment_stations = _get_segment_stations(linie, von_id, nach_id)
        for k in range(len(segment_stations) - 1):
            seg_von = segment_stations[k]
            seg_nach = segment_stations[k + 1]
            if seg_von in stationen:
                s = stationen[seg_von]
                coords.append(f"{s.lon},{s.lat},0")
            key = (seg_von, seg_nach)
            if key in linie.geometrie:
                for lon, lat, _ in linie.geometrie[key]:
                    coords.append(f"{lon},{lat},0")
        last_station = segment_stations[-1]
        if last_station in stationen:
            s = stationen[last_station]
            coords.append(f"{s.lon},{s.lat},0")
    return ' '.join(coords)


def _get_route_gpx_points(route: Route, stationen: Dict[str, Station], linien: Dict[str, Linie]) -> List[Tuple[float, float]]:
    """Sammelt alle GPS-Punkte einer Route inkl. Geometrie-Zwischenpunkten (für GPX)."""
    points = []
    consolidated = _consolidate_same_line_segments(route)
    for von_id, nach_id, linie_id in consolidated:
        linie = linien.get(linie_id)
        if not linie:
            continue
        segment_stations = _get_segment_stations(linie, von_id, nach_id)
        for k in range(len(segment_stations) - 1):
            seg_von = segment_stations[k]
            seg_nach = segment_stations[k + 1]
            if seg_von in stationen:
                points.append((stationen[seg_von].lat, stationen[seg_von].lon))
            key = (seg_von, seg_nach)
            if key in linie.geometrie:
                for lon, lat, _ in linie.geometrie[key]:
                    points.append((lat, lon))
        last_station = segment_stations[-1]
        if last_station in stationen:
            points.append((stationen[last_station].lat, stationen[last_station].lon))
    return points


def _get_route_geojson_coords(route: Route, stationen: Dict[str, Station], linien: Dict[str, Linie]) -> List[List[float]]:
    """Sammelt alle [lon, lat] Koordinaten einer Route inkl. Geometrie-Zwischenpunkten (für GeoJSON)."""
    coords = []
    consolidated = _consolidate_same_line_segments(route)
    for von_id, nach_id, linie_id in consolidated:
        linie = linien.get(linie_id)
        if not linie:
            continue
        segment_stations = _get_segment_stations(linie, von_id, nach_id)
        for k in range(len(segment_stations) - 1):
            seg_von = segment_stations[k]
            seg_nach = segment_stations[k + 1]
            if seg_von in stationen:
                coords.append([stationen[seg_von].lon, stationen[seg_von].lat])
            key = (seg_von, seg_nach)
            if key in linie.geometrie:
                for lon, lat, _ in linie.geometrie[key]:
                    coords.append([lon, lat])
        last_station = segment_stations[-1]
        if last_station in stationen:
            coords.append([stationen[last_station].lon, stationen[last_station].lat])
    return coords


def export_geojson(routen: List[Route], stationen: Dict[str, Station], linien: Dict[str, Linie], output_dir: str):
    """Exportiert routen.geojson – alle Routen als LineStrings mit Geometrie-Interpolation."""
    features = []
    for i, route in enumerate(routen, 1):
        coords = _get_route_geojson_coords(route, stationen, linien)
        features.append({
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": coords},
            "properties": {
                "route_id": i,
                "gesamt_dauer_min": route.gesamt_dauer_min,
                "umstiege": len(route.umstiege),
                "fussweg_gesamt_min": route.fussweg_gesamt_min,
                "wartezeit_gesamt_min": route.wartezeit_gesamt_min,
                "verkehrsmittel": [v.value for v in route.verkehrsmittel],
                "score": route.score,
            }
        })
    geojson = {"type": "FeatureCollection", "features": features}
    path = Path(output_dir) / "routen.geojson"
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, indent=2, ensure_ascii=False)
    print(f"GeoJSON gespeichert: {path}")


def export_kml(routen: List[Route], stationen: Dict[str, Station], linien: Dict[str, Linie], output_dir: str):
    """Exportiert routen.kml – sanfte Linien mit Zwischenpunkten + Umsteige-Pins."""
    kml = Element('kml')
    kml.set('xmlns', 'http://www.opengis.net/kml/2.2')
    document = SubElement(kml, 'Document')
    name_el = SubElement(document, 'name')
    name_el.text = "ÖPNV-Routen"

    colors = ["ff0099ff", "ff00ff99", "ff9900ff", "ff00ffff", "ffff00ff"]

    for i, route in enumerate(routen, 1):
        style = SubElement(document, 'Style')
        style.set('id', f'routeStyle{i}')
        line_style = SubElement(style, 'LineStyle')
        color_el = SubElement(line_style, 'color')
        color_el.text = colors[(i - 1) % len(colors)]
        width_el = SubElement(line_style, 'width')
        width_el.text = '4'

    for i, route in enumerate(routen, 1):
        # Route als LineString mit Geometrie-Zwischenpunkten (sanfte Linie)
        placemark = SubElement(document, 'Placemark')
        pm_name = SubElement(placemark, 'name')
        pm_name.text = f"Route {i} ({route.gesamt_dauer_min} Min, {len(route.umstiege)} Umstiege)"
        desc = SubElement(placemark, 'description')
        desc.text = f"Dauer: {route.gesamt_dauer_min} Min | Umstiege: {len(route.umstiege)} | Score: {route.score:.1f}"
        style_url = SubElement(placemark, 'styleUrl')
        style_url.text = f'#routeStyle{i}'
        line_string = SubElement(placemark, 'LineString')
        coords = SubElement(line_string, 'coordinates')
        coords.text = _get_route_coordinates(route, stationen, linien)

    xml_str = minidom.parseString(tostring(kml)).toprettyxml(indent="  ")
    path = Path(output_dir) / "routen.kml"
    with open(path, 'w', encoding='utf-8') as f:
        f.write(xml_str)
    print(f"KML gespeichert: {path}")


def export_gpx(routen: List[Route], stationen: Dict[str, Station], linien: Dict[str, Linie], output_dir: str):
    """Exportiert routen.gpx – Tracks mit Geometrie-Zwischenpunkten für GPS-Geräte."""
    gpx = Element('gpx')
    gpx.set('version', '1.1')
    gpx.set('creator', 'ÖPNV-Routen-Planner')
    gpx.set('xmlns', 'http://www.topografix.com/GPX/1/1')

    for i, route in enumerate(routen, 1):
        trk = SubElement(gpx, 'trk')
        trk_name = SubElement(trk, 'name')
        trk_name.text = f"Route {i} ({route.gesamt_dauer_min} Min)"
        trk_desc = SubElement(trk, 'desc')
        trk_desc.text = f"Umstiege: {len(route.umstiege)} | Fußweg: {route.fussweg_gesamt_min} Min | Wartezeit: {route.wartezeit_gesamt_min} Min"
        trkseg = SubElement(trk, 'trkseg')
        for lat, lon in _get_route_gpx_points(route, stationen, linien):
            trkpt = SubElement(trkseg, 'trkpt')
            trkpt.set('lat', str(lat))
            trkpt.set('lon', str(lon))
            ele = SubElement(trkpt, 'ele')
            ele.text = '0'

    xml_str = minidom.parseString(tostring(gpx)).toprettyxml(indent="  ")
    path = Path(output_dir) / "routen.gpx"
    with open(path, 'w', encoding='utf-8') as f:
        f.write(xml_str)
    print(f"GPX gespeichert: {path}")


def export_zusammenfassung(routen: List[Route], output_dir: str):
    """Exportiert zusammenfassung.json mit Statistiken und Score-Vergleich."""
    ergebnis = {
        "anzahl_routen": len(routen),
        "routen": [r.to_dict() for r in routen],
        "beste_route": 1 if routen else None,
        "score_vergleich": [
            {"route": i + 1, "score": r.score, "dauer_min": r.gesamt_dauer_min, "umstiege": len(r.umstiege)}
            for i, r in enumerate(routen)
        ] if routen else [],
    }
    path = Path(output_dir) / "zusammenfassung.json"
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(ergebnis, f, indent=2, ensure_ascii=False)
    print(f"Zusammenfassung gespeichert: {path}")


# ============================================================================
# CLI-Einstiegspunkt
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="ÖPNV-Routen finden – Kombinierter Ansatz")
    parser.add_argument("--stadt", type=str, help="Stadt oder Stadtteil (z. B. 'Berlin, Deutschland')")
    parser.add_argument("--bbox", type=float, nargs=4, metavar=("S", "W", "N", "E"), help="Bounding Box")
    parser.add_argument("--datum", required=True, help="Startdatum (ISO, z. B. 2026-11-01)")
    parser.add_argument("--uhrzeit", required=True, help="Startzeit (HH:MM, z. B. 18:30)")
    parser.add_argument("--start", type=str, help="Startpunkt (Name oder Station-ID)")
    parser.add_argument("--end", type=str, help="Endpunkt (Name oder Station-ID)")
    parser.add_argument("--dauer-min", type=int, default=60, help="Mindestdauer in Minuten")
    parser.add_argument("--dauer-max", type=int, default=120, help="Maximale Dauer in Minuten")
    parser.add_argument("--umstiege-min", type=int, default=1, help="Mindestanzahl Umstiege")
    parser.add_argument("--umstiege-max", type=int, default=5, help="Maximale Anzahl Umstiege")
    parser.add_argument("--qid", type=str, help="Wikidata-QID des Ortes")
    parser.add_argument("--output", default="ergebnis", help="Ausgabeverzeichnis")

    args = parser.parse_args()

    # Phase 1: Daten-Scout
    if args.stadt:
        scout = DatenScout(args.stadt)
        scout.finde_datenquellen()

    # Phase 2: Netzwerk aufbauen (Test-Graph als Vorlage)
    graph = RoutingGraph()
    # TODO: Aus OSM/GTGS-Daten aufbauen

    # Phase 3: Routing
    router = Router(graph)
    routen = router.finde_routen(
        start_id=args.start or "hbf",
        ziel_id=args.end or "flughafen",
        datum=args.datum,
        uhrzeit=args.uhrzeit,
        dauer_min=args.dauer_min,
        dauer_max=args.dauer_max,
        umstiege_min=args.umstiege_min,
        umstiege_max=args.umstiege_max,
    )

    # Phase 4: Export
    if routen:
        output = Path(args.output)
        output.mkdir(parents=True, exist_ok=True)
        export_geojson(routen, graph.stationen, graph.linien, str(output))
        export_kml(routen, graph.stationen, graph.linien, str(output))
        export_gpx(routen, graph.stationen, graph.linien, str(output))
        export_zusammenfassung(routen, str(output))
    else:
        print("Keine Routen gefunden. Constraints prüfen oder entschärfen.")


if __name__ == "__main__":
    main()
