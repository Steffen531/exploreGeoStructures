#!/usr/bin/env python3
"""
Phase 2: Routing-Kern
A* mit strikten Constraints (Keine-Wiederholungen) und Backtracking.
Findet 3 Routen von Start nach Ende mit minimalen Umstiegszeiten.
"""

import json
import math
import heapq
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum


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

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return self.id == other.id


@dataclass
class Linie:
    id: str
    name: str
    typ: VerkehrsmittelTyp
    stationen: List[str]
    farbe: str = "#000000"
    geometrie: Dict[Tuple[str, str], List[Tuple[float, float]]] = field(default_factory=dict)  # (von, nach) -> [intermediate coords]

    def __hash__(self):
        return hash(self.id)

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


class RoutingGraph:
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


class Router:
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
        print(f"\n🔍 Suche Routen: {start_id} → {ziel_id}")
        print(f"   Dauer: {dauer_min}-{dauer_max} Minuten")
        print(f"   Umstiege: {umstiege_min}-{umstiege_max}")
        print(f"   Gewünschte Routen: {anzahl_routen}")
        print("=" * 50)

        start_zeit_min = self._zeit_zu_min(uhrzeit)

        # Stufe 1: BFS ohne Constraints
        print("\n📋 Stufe 1: BFS ohne Constraints...")
        erreichbar = self._bfs_erreichbar(start_id, ziel_id)
        if not erreichbar:
            print("   ❌ Ziel nicht erreichbar!")
            return []
        print("   ✅ Ziel erreichbar")

        # Stufe 2: DFS mit Diversitäts-Belohnung
        print("\n📋 Stufe 2: DFS mit Diversitäts-Belohnung...")
        routen = self._dfs_diversitaet(
            start_id, ziel_id, start_zeit_min,
            dauer_min, dauer_max,
            umstiege_min, umstiege_max,
            anzahl_routen
        )

        if not routen:
            print("   ⚠️  Keine Routen gefunden, versuche Standard-DFS...")
            routen = self._dfs_backtracking(
                start_id, ziel_id, start_zeit_min,
                dauer_min, dauer_max,
                umstiege_min, umstiege_max,
                anzahl_routen
            )

        for route in routen:
            route.score = self._berechne_score(route)

        routen.sort(key=lambda r: r.score)
        return routen

    def _dfs_diversitaet(
        self,
        start_id: str,
        ziel_id: str,
        start_zeit_min: int,
        dauer_min: int,
        dauer_max: int,
        umstiege_min: int,
        umstiege_max: int,
        anzahl_routen: int,
    ) -> List[Route]:
        """
        DFS mit Diversitäts-Belohnung:
        - Bereits gefundene Routen werden "blockiert" für nachfolgende Routen
        - Jede neue Route muss mindestens 2 neue Stationen enthalten
        """
        gefundene_routen: List[Route] = []

        start_station = self.graph.get_station(start_id)
        if not start_station:
            return []

        # Sammle alle Stationen aus bereits gefundenen Routen
        def get_besuchte_stationen(routen: List[Route]) -> Set[str]:
            besucht = set()
            for r in routen:
                besucht.update(r.stationen)
            return besucht

        stack = [(
            [start_id],
            {start_id},
            set(),
            {start_station.stadtteil} if start_station.stadtteil else set(),
            0, 0, 0,
            None,
            start_zeit_min,
            [], []
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
                    # Diversitäts-Prüfung: Mindestens 2 neue Stationen
                    besuchte_stationen = get_besuchte_stationen(gefundene_routen)
                    neue_stationen = set(pfad) - besuchte_stationen

                    if len(neue_stationen) >= 2 or len(gefundene_routen) == 0:
                        route = Route(
                            stationen=list(pfad),
                            fahrten=list(fahrten),
                            umstiege=list(umstiege_liste),
                            gesamt_dauer_min=dauer,
                            fussweg_gesamt_min=fussweg_gesamt,
                            wartezeit_gesamt_min=wartezeit_gesamt,
                            verkehrsmittel=list(set(f.verkehrsmittel for f in fahrten)),
                        )
                        gefundene_routen.append(route)
                        print(f"  ✅ Route {len(gefundene_routen)}: {len(pfad)} Stationen, {len(umstiege_liste)} Umstiege, {dauer} Min, {len(neue_stationen)} neue Stationen")
                continue

            if aktuelle_zeit - start_zeit_min > dauer_max:
                continue

            if len(umstiege_liste) > umstiege_max:
                continue

            # Bereits besuchte Stationen aus früheren Routen (Diversitäts-Penalty)
            besuchte_stationen = get_besuchte_stationen(gefundene_routen)

            for nachbar_id, linie_id in reversed(self.graph.get_nachbarn(aktuelle_station)):
                nachbar_station = self.graph.get_station(nachbar_id)
                if not nachbar_station:
                    continue

                # Strikte Constraints
                if nachbar_id in besuchte_st:
                    continue

                kante = (aktuelle_station, nachbar_id)
                if kante in besuchte_kanten:
                    continue

                # Diversitäts-Bonus: bevorzuge Stationen, die noch nicht in anderen Routen sind
                diversitaets_bonus = 0
                if nachbar_id not in besuchte_stationen:
                    diversitaets_bonus = 5  # Bonus für neue Stationen

                linie = self.graph.linien.get(linie_id)
                if not linie:
                    continue

                fahrzeit = 3
                wartezeit = 4
                fussweg = 0
                neue_umstiege = list(umstiege_liste)
                neue_fahrten = list(fahrten)

                if letzte_linie is not None and letzte_linie != linie_id:
                    fussweg = 2
                    neue_umstiege.append(Umstieg(
                        station=aktuelle_station,
                        von_linie=letzte_linie,
                        nach_linie=linie_id,
                        fussweg_min=fussweg,
                        wartezeit_min=wartezeit,
                    ))

                neue_zeit = aktuelle_zeit + fahrzeit + wartezeit + fussweg

                stack.append((
                    pfad + [nachbar_id],
                    besuchte_st | {nachbar_id},
                    besuchte_kanten | {kante},
                    besuchte_stadtteile | ({nachbar_station.stadtteil} if nachbar_station.stadtteil else set()),
                    len(neue_umstiege),
                    fussweg_gesamt + fussweg,
                    wartezeit_gesamt + wartezeit,
                    linie_id,
                    neue_zeit,
                    neue_fahrten + [Fahrt(
                        von=aktuelle_station,
                        nach=nachbar_id,
                        linie=linie_id,
                        verkehrsmittel=linie.typ,
                        dauer_min=fahrzeit,
                        abfahrt=self._min_zu_zeit(aktuelle_zeit),
                        ankunft=self._min_zu_zeit(neue_zeit - fussweg),
                    )],
                    neue_umstiege,
                ))

        print(f"  Debug: {iterationen} Iterationen, {len(gefundene_routen)} Routen")
        return gefundene_routen

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

    def _dfs_backtracking(
        self,
        start_id: str,
        ziel_id: str,
        start_zeit_min: int,
        dauer_min: int,
        dauer_max: int,
        umstiege_min: int,
        umstiege_max: int,
        anzahl_routen: int,
    ) -> List[Route]:
        """DFS mit strikten Constraints."""
        gefundene_routen: List[Route] = []

        start_station = self.graph.get_station(start_id)
        if not start_station:
            return []

        stack = [(
            [start_id],
            {start_id},
            set(),
            {start_station.stadtteil} if start_station.stadtteil else set(),
            0, 0, 0,
            None,
            start_zeit_min,
            [], []
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
                        stationen=list(pfad),
                        fahrten=list(fahrten),
                        umstiege=list(umstiege_liste),
                        gesamt_dauer_min=dauer,
                        fussweg_gesamt_min=fussweg_gesamt,
                        wartezeit_gesamt_min=wartezeit_gesamt,
                        verkehrsmittel=list(set(f.verkehrsmittel for f in fahrten)),
                    )
                    gefundene_routen.append(route)
                    print(f"  ✅ Route gefunden: {len(pfad)} Stationen, {len(umstiege_liste)} Umstiege, {dauer} Min")
                continue

            if aktuelle_zeit - start_zeit_min > dauer_max:
                continue

            if len(umstiege_liste) > umstiege_max:
                continue

            for nachbar_id, linie_id in reversed(self.graph.get_nachbarn(aktuelle_station)):
                nachbar_station = self.graph.get_station(nachbar_id)
                if not nachbar_station:
                    continue

                # STRIKTE CONSTRAINTS
                # 1. Keine Station zweimal
                if nachbar_id in besuchte_st:
                    continue

                # 2. Kein Straßenabschnitt zweimal
                kante = (aktuelle_station, nachbar_id)
                if kante in besuchte_kanten:
                    continue

                # 3. Stadtteile DÜRFEN wiederholt werden (gelockert)
                # if nachbar_station.stadtteil and nachbar_station.stadtteil in besuchte_stadtteile:
                #     continue

                linie = self.graph.linien.get(linie_id)
                if not linie:
                    continue

                fahrzeit = 3
                wartezeit = 4
                fussweg = 0
                neue_umstiege = list(umstiege_liste)
                neue_fahrten = list(fahrten)

                if letzte_linie is not None and letzte_linie != linie_id:
                    fussweg = 2
                    neue_umstiege.append(Umstieg(
                        station=aktuelle_station,
                        von_linie=letzte_linie,
                        nach_linie=linie_id,
                        fussweg_min=fussweg,
                        wartezeit_min=wartezeit,
                    ))

                neue_zeit = aktuelle_zeit + fahrzeit + wartezeit + fussweg

                stack.append((
                    pfad + [nachbar_id],
                    besuchte_st | {nachbar_id},
                    besuchte_kanten | {kante},
                    besuchte_stadtteile | ({nachbar_station.stadtteil} if nachbar_station.stadtteil else set()),
                    len(neue_umstiege),
                    fussweg_gesamt + fussweg,
                    wartezeit_gesamt + wartezeit,
                    linie_id,
                    neue_zeit,
                    neue_fahrten + [Fahrt(
                        von=aktuelle_station,
                        nach=nachbar_id,
                        linie=linie_id,
                        verkehrsmittel=linie.typ,
                        dauer_min=fahrzeit,
                        abfahrt=self._min_zu_zeit(aktuelle_zeit),
                        ankunft=self._min_zu_zeit(neue_zeit - fussweg),
                    )],
                    neue_umstiege,
                ))

        print(f"  Debug: {iterationen} Iterationen, {len(gefundene_routen)} Routen")
        return gefundene_routen[:anzahl_routen] if gefundene_routen else []

    def _dfs_lockere_constraints(
        self,
        start_id: str,
        ziel_id: str,
        start_zeit_min: int,
        dauer_min: int,
        dauer_max: int,
        umstiege_min: int,
        umstiege_max: int,
        anzahl_routen: int,
    ) -> List[Route]:
        """DFS mit lockeren Constraints (nur Stationen nicht wiederholen)."""
        gefundene_routen: List[Route] = []

        start_station = self.graph.get_station(start_id)
        if not start_station:
            return []

        stack = [(
            [start_id],
            {start_id},
            set(),
            set(),
            0, 0, 0,
            None,
            start_zeit_min,
            [], []
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
                        stationen=list(pfad),
                        fahrten=list(fahrten),
                        umstiege=list(umstiege_liste),
                        gesamt_dauer_min=dauer,
                        fussweg_gesamt_min=fussweg_gesamt,
                        wartezeit_gesamt_min=wartezeit_gesamt,
                        verkehrsmittel=list(set(f.verkehrsmittel for f in fahrten)),
                    )
                    gefundene_routen.append(route)
                    print(f"  ✅ Route gefunden: {len(pfad)} Stationen, {len(umstiege_liste)} Umstiege, {dauer} Min")
                continue

            if aktuelle_zeit - start_zeit_min > dauer_max:
                continue

            if len(umstiege_liste) > umstiege_max:
                continue

            for nachbar_id, linie_id in reversed(self.graph.get_nachbarn(aktuelle_station)):
                nachbar_station = self.graph.get_station(nachbar_id)
                if not nachbar_station:
                    continue

                # LOCKERE CONSTRAINTS: nur Stationen
                if nachbar_id in besuchte_st:
                    continue

                linie = self.graph.linien.get(linie_id)
                if not linie:
                    continue

                fahrzeit = 3
                wartezeit = 4
                fussweg = 0
                neue_umstiege = list(umstiege_liste)
                neue_fahrten = list(fahrten)

                if letzte_linie is not None and letzte_linie != linie_id:
                    fussweg = 2
                    neue_umstiege.append(Umstieg(
                        station=aktuelle_station,
                        von_linie=letzte_linie,
                        nach_linie=linie_id,
                        fussweg_min=fussweg,
                        wartezeit_min=wartezeit,
                    ))

                neue_zeit = aktuelle_zeit + fahrzeit + wartezeit + fussweg

                stack.append((
                    pfad + [nachbar_id],
                    besuchte_st | {nachbar_id},
                    besuchte_kanten | {(aktuelle_station, nachbar_id)},
                    besuchte_stadtteile | ({nachbar_station.stadtteil} if nachbar_station.stadtteil else set()),
                    len(neue_umstiege),
                    fussweg_gesamt + fussweg,
                    wartezeit_gesamt + wartezeit,
                    linie_id,
                    neue_zeit,
                    neue_fahrten + [Fahrt(
                        von=aktuelle_station,
                        nach=nachbar_id,
                        linie=linie_id,
                        verkehrsmittel=linie.typ,
                        dauer_min=fahrzeit,
                        abfahrt=self._min_zu_zeit(aktuelle_zeit),
                        ankunft=self._min_zu_zeit(neue_zeit - fussweg),
                    )],
                    neue_umstiege,
                ))

        print(f"  Debug: {iterationen} Iterationen, {len(gefundene_routen)} Routen")
        return gefundene_routen[:anzahl_routen] if gefundene_routen else []

    def _zeit_zu_min(self, zeit: str) -> int:
        h, m = map(int, zeit.split(":"))
        return h * 60 + m

    def _min_zu_zeit(self, minuten: int) -> str:
        h = (minuten // 60) % 24
        m = minuten % 60
        return f"{h:02d}:{m:02d}"

    def _berechne_score(self, route: Route) -> float:
        """Berechnet Score: niedriger = besser.
        Bevorzugt: schnelle Verkehrsmittel (S-Bahn, U-Bahn, Regionalzug, Straßenbahn)
        Vermeidet: langsame Verkehrsmittel (Bus)"""
        
        # Verkehrsmittel-Prioritäten (niedriger = besser)
        vm_prioritaet = {
            VerkehrsmittelTyp.REGIONALZUG: 1,  # Schnellste, wenige Halte
            VerkehrsmittelTyp.S_BAHN: 2,        # Schnell, eigenes Gleis
            VerkehrsmittelTyp.U_BAHN: 2,        # Schnell, unterirdisch
            VerkehrsmittelTyp.STRASSENBAHN: 3,  # Mittel, oft eigenes Gleisbett
            VerkehrsmittelTyp.FAEHRE: 4,        # Landschaftlich, aber langsam
            VerkehrsmittelTyp.BUS: 10,          # Langsam, Straßenverkehr
            VerkehrsmittelTyp.FUSSWEG: 5,
            VerkehrsmittelTyp.RIDE_HAILING: 6,
        }
        
        # Score aus Umstiegszeiten
        umstiegs_score = 2.0 * (route.fussweg_gesamt_min + route.wartezeit_gesamt_min) + 1.0 * len(route.umstiege)
        
        # Score aus Verkehrsmitteln (bevorzuge schnelle)
        vm_score = sum(vm_prioritaet.get(v, 5) for v in route.verkehrsmittel)
        
        return umstiegs_score + vm_score


def erstelle_test_graph() -> RoutingGraph:
    """Erstellt einen erweiterten Test-Graph für Frankfurt mit mehr Stationen und Linien."""
    graph = RoutingGraph()

    # Stationen - erweitert mit mehr Stadtteilen und Verbindungen
    stationen = [
        # Innenstadt
        Station("hbf", "Frankfurt Hbf", 50.1070, 8.6636, [VerkehrsmittelTyp.S_BAHN, VerkehrsmittelTyp.U_BAHN], "Innenstadt"),
        Station("konstablerwache", "Konstablerwache", 50.1130, 8.6895, [VerkehrsmittelTyp.U_BAHN, VerkehrsmittelTyp.STRASSENBAHN], "Innenstadt"),
        Station("hauptwache", "Hauptwache", 50.1150, 8.6770, [VerkehrsmittelTyp.U_BAHN, VerkehrsmittelTyp.STRASSENBAHN], "Innenstadt"),
        Station("willy_brandt", "Willy-Brandt-Platz", 50.1090, 8.6650, [VerkehrsmittelTyp.U_BAHN, VerkehrsmittelTyp.STRASSENBAHN], "Innenstadt"),

        # Ost
        Station("ost", "Frankfurt Ost", 50.1130, 8.7200, [VerkehrsmittelTyp.STRASSENBAHN, VerkehrsmittelTyp.BUS], "Ostend"),
        Station("bornheim", "Bornheim", 50.1200, 8.7000, [VerkehrsmittelTyp.STRASSENBAHN, VerkehrsmittelTyp.BUS], "Bornheim"),
        Station("seckbach", "Seckbach", 50.1300, 8.7000, [VerkehrsmittelTyp.STRASSENBAHN, VerkehrsmittelTyp.BUS], "Seckbach"),
        Station("nordend", "Nordend", 50.1200, 8.6800, [VerkehrsmittelTyp.STRASSENBAHN, VerkehrsmittelTyp.BUS], "Nordend"),
        Station("offenbach", "Offenbach Hbf", 50.1000, 8.7500, [VerkehrsmittelTyp.S_BAHN, VerkehrsmittelTyp.REGIONALZUG], "Offenbach"),

        # Süd
        Station("sued", "Frankfurt Süd", 50.0900, 8.6800, [VerkehrsmittelTyp.STRASSENBAHN, VerkehrsmittelTyp.BUS], "Süd"),
        Station("lokalbahnhof", "Lokalbahnhof", 50.0950, 8.6850, [VerkehrsmittelTyp.STRASSENBAHN], "Süd"),
        Station("niederrad", "Niederrad", 50.0800, 8.6500, [VerkehrsmittelTyp.S_BAHN, VerkehrsmittelTyp.STRASSENBAHN], "Niederrad"),
        Station("flughafen", "Flughafen", 50.0300, 8.6200, [VerkehrsmittelTyp.S_BAHN, VerkehrsmittelTyp.REGIONALZUG], "Flughafen"),

        # West
        Station("hoechst", "Frankfurt Höchst", 50.1000, 8.6000, [VerkehrsmittelTyp.S_BAHN, VerkehrsmittelTyp.BUS], "Höchst"),
        Station("nordweststadt", "Nordweststadt", 50.1300, 8.6500, [VerkehrsmittelTyp.U_BAHN, VerkehrsmittelTyp.STRASSENBAHN], "Nordweststadt"),
        Station("bockenheim", "Bockenheim", 50.1200, 8.6400, [VerkehrsmittelTyp.U_BAHN, VerkehrsmittelTyp.STRASSENBAHN], "Bockenheim"),
        Station("westend", "Westend", 50.1200, 8.6500, [VerkehrsmittelTyp.U_BAHN, VerkehrsmittelTyp.STRASSENBAHN], "Westend"),
        Station("gallus", "Gallus", 50.1000, 8.6400, [VerkehrsmittelTyp.STRASSENBAHN, VerkehrsmittelTyp.BUS], "Gallus"),
        Station("ginnheim", "Ginnheim", 50.1400, 8.6500, [VerkehrsmittelTyp.U_BAHN, VerkehrsmittelTyp.STRASSENBAHN], "Ginnheim"),

        # Sachsenhausen
        Station("sachsenhausen", "Sachsenhausen", 50.1000, 8.6600, [VerkehrsmittelTyp.STRASSENBAHN, VerkehrsmittelTyp.FAEHRE], "Sachsenhausen"),

        # Region
        Station("mainz_hbf", "Mainz Hbf", 50.0000, 8.6000, [VerkehrsmittelTyp.S_BAHN, VerkehrsmittelTyp.REGIONALZUG], "Mainz"),
        Station("darmstadt", "Darmstadt Hbf", 49.8700, 8.6500, [VerkehrsmittelTyp.REGIONALZUG], "Darmstadt"),
    ]

    for s in stationen:
        graph.add_station(s)

    def add_line_with_geometry(linie: Linie):
        """Hilfsfunktion: Fügt Linie mit Geometrie-Punkten hinzu."""
        station_coords = {s.id: (s.lat, s.lon) for s in stationen}
        for i in range(len(linie.stationen) - 1):
            von = linie.stationen[i]
            nach = linie.stationen[i + 1]
            if von in station_coords and nach in station_coords:
                lat1, lon1 = station_coords[von]
                lat2, lon2 = station_coords[nach]
                # Füge 20 intermediate Punkte entlang der Geraden hinzu für glatte Linien
                intermediate = []
                for frac in [j/21 for j in range(1, 21)]:  # 20 Punkte pro Segment
                    intermediate.append((lon1 + frac * (lon2 - lon1), lat1 + frac * (lat2 - lat1), 0))
                linie.add_geometrie(von, nach, intermediate)
        graph.add_linie(linie)

    # Linien - erweitert mit mehr Verbindungen
    linien = [
        # S-Bahn (schnell, eigene Gleise)
        Linie("S8", "S8", VerkehrsmittelTyp.S_BAHN, ["hbf", "konstablerwache", "ost", "offenbach"], "#009933"),
        Linie("S9", "S9", VerkehrsmittelTyp.S_BAHN, ["hbf", "hoechst", "mainz_hbf"], "#009933"),
        Linie("S1", "S1", VerkehrsmittelTyp.S_BAHN, ["hbf", "niederrad", "flughafen"], "#009933"),
        Linie("S2", "S2", VerkehrsmittelTyp.S_BAHN, ["hbf", "niederrad", "darmstadt"], "#009933"),
        Linie("S3", "S3", VerkehrsmittelTyp.S_BAHN, ["hbf", "hauptwache", "ost", "offenbach"], "#009933"),
        Linie("S4", "S4", VerkehrsmittelTyp.S_BAHN, ["hbf", "konstablerwache", "bornheim", "seckbach"], "#009933"),
        Linie("S5", "S5", VerkehrsmittelTyp.S_BAHN, ["hbf", "willy_brandt", "nordend", "bornheim"], "#009933"),
        Linie("S6", "S6", VerkehrsmittelTyp.S_BAHN, ["hbf", "hauptwache", "ost", "nordend"], "#009933"),
        Linie("S7", "S7", VerkehrsmittelTyp.S_BAHN, ["hbf", "konstablerwache", "sued", "niederrad"], "#009933"),

        # U-Bahn (schnell, unterirdisch)
        Linie("U1", "U1", VerkehrsmittelTyp.U_BAHN, ["hbf", "hauptwache", "willy_brandt", "nordweststadt"], "#0099FF"),
        Linie("U2", "U2", VerkehrsmittelTyp.U_BAHN, ["hbf", "konstablerwache", "bornheim", "seckbach"], "#0099FF"),
        Linie("U3", "U3", VerkehrsmittelTyp.U_BAHN, ["hbf", "willy_brandt", "bockenheim", "ginnheim"], "#0099FF"),
        Linie("U4", "U4", VerkehrsmittelTyp.U_BAHN, ["westend", "bockenheim", "nordweststadt", "ginnheim"], "#0099FF"),
        Linie("U5", "U5", VerkehrsmittelTyp.U_BAHN, ["hbf", "konstablerwache", "nordend", "bornheim"], "#0099FF"),
        Linie("U6", "U6", VerkehrsmittelTyp.U_BAHN, ["hbf", "gallus", "niederrad"], "#0099FF"),
        Linie("U7", "U7", VerkehrsmittelTyp.U_BAHN, ["hbf", "hauptwache", "nordend", "seckbach"], "#0099FF"),
        Linie("U8", "U8", VerkehrsmittelTyp.U_BAHN, ["hbf", "willy_brandt", "ost", "offenbach"], "#0099FF"),
        Linie("U9", "U9", VerkehrsmittelTyp.U_BAHN, ["hbf", "konstablerwache", "sued", "niederrad"], "#0099FF"),

        # Regionalzüge (sehr schnell, wenige Halte)
        Linie("R1", "RE1", VerkehrsmittelTyp.REGIONALZUG, ["hbf", "offenbach", "darmstadt"], "#FF0000"),
        Linie("R2", "RE2", VerkehrsmittelTyp.REGIONALZUG, ["hbf", "mainz_hbf", "darmstadt"], "#FF0000"),
        Linie("R3", "RE3", VerkehrsmittelTyp.REGIONALZUG, ["hbf", "hoechst", "mainz_hbf", "darmstadt"], "#FF0000"),
        Linie("R4", "RE4", VerkehrsmittelTyp.REGIONALZUG, ["hbf", "niederrad", "flughafen", "darmstadt"], "#FF0000"),
        Linie("R5", "RE5", VerkehrsmittelTyp.REGIONALZUG, ["hbf", "ost", "offenbach", "mainz_hbf"], "#FF0000"),

        # Straßenbahn (mittel, eigenes Gleisbett oft)
        Linie("T11", "11", VerkehrsmittelTyp.STRASSENBAHN, ["ost", "konstablerwache", "lokalbahnhof", "sued", "niederrad"], "#FF6600"),
        Linie("T12", "12", VerkehrsmittelTyp.STRASSENBAHN, ["ost", "konstablerwache", "sachsenhausen", "westend", "nordweststadt"], "#FF6600"),
        Linie("T14", "14", VerkehrsmittelTyp.STRASSENBAHN, ["ost", "bornheim", "seckbach", "nordend"], "#FF6600"),
        Linie("T15", "15", VerkehrsmittelTyp.STRASSENBAHN, ["hbf", "gallus", "westend", "bockenheim", "ginnheim"], "#FF6600"),
        Linie("T16", "16", VerkehrsmittelTyp.STRASSENBAHN, ["hbf", "hauptwache", "ost", "bornheim", "seckbach"], "#FF6600"),
        Linie("T17", "17", VerkehrsmittelTyp.STRASSENBAHN, ["hbf", "willy_brandt", "nordend", "nordweststadt"], "#FF6600"),
        Linie("T18", "18", VerkehrsmittelTyp.STRASSENBAHN, ["hbf", "konstablerwache", "sachsenhausen", "hoechst"], "#FF6600"),
        Linie("T19", "19", VerkehrsmittelTyp.STRASSENBAHN, ["hbf", "gallus", "sued", "niederrad", "flughafen"], "#FF6600"),
        Linie("T20", "20", VerkehrsmittelTyp.STRASSENBAHN, ["hbf", "hauptwache", "ost", "offenbach", "darmstadt"], "#FF6600"),
        Linie("T21", "21", VerkehrsmittelTyp.STRASSENBAHN, ["hbf", "willy_brandt", "bornheim", "seckbach", "nordend"], "#FF6600"),

        # Fähren (landschaftlich, langsam aber besonders)
        Linie("F1", "Fähre", VerkehrsmittelTyp.FAEHRE, ["sued", "sachsenhausen", "hoechst"], "#0000FF"),
        Linie("F2", "Fähre", VerkehrsmittelTyp.FAEHRE, ["sued", "niederrad", "mainz_hbf"], "#0000FF"),
        Linie("F3", "Fähre", VerkehrsmittelTyp.FAEHRE, ["ost", "offenbach", "mainz_hbf"], "#0000FF"),
        Linie("F4", "Fähre", VerkehrsmittelTyp.FAEHRE, ["hbf", "sachsenhausen", "hoechst", "mainz_hbf"], "#0000FF"),

        # Bus (langsam, Straßenverkehr) - NUR als Fallback, nicht primär
        Linie("B30", "30", VerkehrsmittelTyp.BUS, ["hbf", "gallus", "hoechst"], "#888888"),
        Linie("B34", "34", VerkehrsmittelTyp.BUS, ["hbf", "bornheim", "seckbach"], "#888888"),
        Linie("B36", "36", VerkehrsmittelTyp.BUS, ["konstablerwache", "ost", "offenbach"], "#888888"),
    ]

    for l in linien:
        add_line_with_geometry(l)

    return graph


def main():
    import argparse

    parser = argparse.ArgumentParser(description="ÖPNV Router")
    parser.add_argument("--start", required=True)
    parser.add_argument("--ziel", required=True)
    parser.add_argument("--datum", required=True)
    parser.add_argument("--uhrzeit", required=True)
    parser.add_argument("--dauer-min", type=int, default=60)
    parser.add_argument("--dauer-max", type=int, default=120)
    parser.add_argument("--umstiege-min", type=int, default=1)
    parser.add_argument("--umstiege-max", type=int, default=5)
    parser.add_argument("--anzahl", type=int, default=3)
    parser.add_argument("--output", default="routen.json")

    args = parser.parse_args()

    graph = erstelle_test_graph()
    router = Router(graph)

    routen = router.finde_routen(
        start_id=args.start,
        ziel_id=args.ziel,
        datum=args.datum,
        uhrzeit=args.uhrzeit,
        dauer_min=args.dauer_min,
        dauer_max=args.dauer_max,
        umstiege_min=args.umstiege_min,
        umstiege_max=args.umstiege_max,
        anzahl_routen=args.anzahl,
    )

    print(f"\n{'=' * 50}")
    print(f"ERGEBNIS: {len(routen)} Routen gefunden")
    print("=" * 50)

    for i, route in enumerate(routen, 1):
        print(f"\n📍 Route {i}:")
        print(f"   Stationen: {' → '.join(route.stationen)}")
        print(f"   Dauer: {route.gesamt_dauer_min} Minuten")
        print(f"   Umstiege: {len(route.umstiege)}")
        print(f"   Fußweg: {route.fussweg_gesamt_min} Min")
        print(f"   Wartezeit: {route.wartezeit_gesamt_min} Min")
        print(f"   Verkehrsmittel: {', '.join(v.value for v in route.verkehrsmittel)}")

    ergebnis = {
        "start": args.start,
        "ziel": args.ziel,
        "datum": args.datum,
        "uhrzeit": args.uhrzeit,
        "routen": [r.to_dict() for r in routen],
    }

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(ergebnis, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Routen gespeichert: {args.output}")


if __name__ == "__main__":
    main()
