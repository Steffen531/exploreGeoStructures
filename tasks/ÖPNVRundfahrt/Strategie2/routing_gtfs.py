#!/usr/bin/env python3
"""
Phase 3: GTFS/Echtzeit-Integration
Erweitert den Router um echte GTFS-Fahrpläne und Störungen.
"""

import json
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from routing import (
    RoutingGraph, Router, Route, Station, Linie, Fahrt, Umstieg,
    VerkehrsmittelTyp, erstelle_test_graph
)
from gtfs_parser import GtfsData, erstelle_test_gtfs


class GtfsRouter(Router):
    """
    Router mit GTFS-Fahrplan-Integration.
    """

    def __init__(self, graph: RoutingGraph, gtfs_data: Optional[GtfsData] = None):
        super().__init__(graph)
        self.gtfs = gtfs_data
        self.stoerungen: Dict[str, bool] = {}  # linie_id -> gestoert

    def setze_stoerung(self, linie_id: str, gestoert: bool = True):
        """Setzt eine Störung für eine Linie."""
        self.stoerungen[linie_id] = gestoert

    def finde_routen_gtfs(
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
        """
        Findet Routen mit GTFS-Fahrplänen.
        """
        print(f"\n🔍 GTFS-Router: {start_id} → {ziel_id}")
        print(f"   Datum: {datum}, Uhrzeit: {uhrzeit}")
        print(f"   Dauer: {dauer_min}-{dauer_max} Minuten")
        print(f"   Umstiege: {umstiege_min}-{umstiege_max}")
        print("=" * 50)

        start_zeit_min = self._zeit_zu_min(uhrzeit)

        if self.gtfs:
            print("\n📋 Nutze GTFS-Fahrpläne...")
            routen = self._dfs_gtfs(
                start_id, ziel_id, start_zeit_min,
                dauer_min, dauer_max,
                umstiege_min, umstiege_max,
                anzahl_routen, datum
            )
        else:
            print("\n⚠️  Keine GTFS-Daten, nutze Standard-Router...")
            routen = self._dfs_diversitaet(
                start_id, ziel_id, start_zeit_min,
                dauer_min, dauer_max,
                umstiege_min, umstiege_max,
                anzahl_routen
            )

        for route in routen:
            route.score = self._berechne_score(route)

        routen.sort(key=lambda r: r.score)
        return routen

    def _dfs_gtfs(
        self,
        start_id: str,
        ziel_id: str,
        start_zeit_min: int,
        dauer_min: int,
        dauer_max: int,
        umstiege_min: int,
        umstiege_max: int,
        anzahl_routen: int,
        datum: str,
    ) -> List[Route]:
        """
        DFS mit GTFS-Fahrplänen und Diversitäts-Belohnung.
        """
        gefundene_routen: List[Route] = []

        start_station = self.graph.get_station(start_id)
        if not start_station:
            return []

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
                        print(f"  Route {len(gefundene_routen)}: {len(pfad)} Stationen, {len(umstiege_liste)} Umstiege, {dauer} Min, {len(neue_stationen)} neue Stationen")
                continue

            if aktuelle_zeit - start_zeit_min > dauer_max:
                continue

            if len(umstiege_liste) > umstiege_max:
                continue

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

                # Störungs-Prüfung
                if self.stoerungen.get(linie_id, False):
                    continue

                # Diversitäts-Bonus
                diversitaets_bonus = 0
                if nachbar_id not in besuchte_stationen:
                    diversitaets_bonus = 5

                linie = self.graph.linien.get(linie_id)
                if not linie:
                    continue

                # GTFS-Fahrplan: Echte Abfahrtszeit finden
                if self.gtfs and linie_id in self.gtfs.routes:
                    # Finde nächste Abfahrt
                    current_time = self._min_zu_zeit(aktuelle_zeit)
                    departure = self.gtfs.get_next_departure(
                        aktuelle_station, linie_id, current_time, datum
                    )

                    if departure is None:
                        continue

                    trip_id, dep_time = departure

                    # Parse Ankunftszeit
                    arr_time = self.gtfs.get_stop_times_for_trip(trip_id)
                    ankunft = None
                    for st in arr_time:
                        if st.stop_id == nachbar_id:
                            ankunft = st.arrival_time[:5]  # Normalize to HH:MM
                            break

                    if ankunft is None:
                        continue

                    # Berechne Wartezeit
                    aktuelle_zeit_min = aktuelle_zeit
                    abfahrt_min = self._zeit_zu_min(dep_time)
                    ankunft_min = self._zeit_zu_min(ankunft)

                    wartezeit = max(0, abfahrt_min - aktuelle_zeit_min)
                    fahrzeit = ankunft_min - abfahrt_min

                    # Falls Wartezeit zu lang (über 30 Min), überspringe
                    if wartezeit > 30:
                        continue

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
                            abfahrt=dep_time,
                            ankunft=ankunft,
                            gestoert=False,
                        )],
                        neue_umstiege,
                    ))
                else:
                    # Fallback: Standard-Zeiten
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


def main():
    import argparse

    parser = argparse.ArgumentParser(description="GTFS-Router")
    parser.add_argument("--start", required=True)
    parser.add_argument("--ziel", required=True)
    parser.add_argument("--datum", required=True)
    parser.add_argument("--uhrzeit", required=True)
    parser.add_argument("--dauer-min", type=int, default=60)
    parser.add_argument("--dauer-max", type=int, default=120)
    parser.add_argument("--umstiege-min", type=int, default=1)
    parser.add_argument("--umstiege-max", type=int, default=5)
    parser.add_argument("--anzahl", type=int, default=3)
    parser.add_argument("--gtfs", help="Pfad zu GTFS-Daten")
    parser.add_argument("--output", default="routen_gtfs.json")

    args = parser.parse_args()

    # Graph erstellen
    graph = erstelle_test_graph()

    # GTFS-Daten laden
    gtfs_data = None
    if args.gtfs:
        from gtfs_parser import GtfsParser
        parser = GtfsParser(args.gtfs)
        gtfs_data = parser.parse()
    else:
        print("Keine GTFS-Daten angegeben, erstelle Test-Daten...")
        gtfs_data = erstelle_test_gtfs()

    # Router erstellen
    router = GtfsRouter(graph, gtfs_data)

    # Optional: Störungen setzen
    # router.setze_stoerung("T11", True)

    # Routen finden
    routen = router.finde_routen_gtfs(
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
        print(f"\nRoute {i}:")
        print(f"   Stationen: {' -> '.join(route.stationen)}")
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

    print(f"\nRouten gespeichert: {args.output}")


if __name__ == "__main__":
    main()
