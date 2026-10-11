#!/usr/bin/env python3
"""
Phase 1: Daten-Scout
Findet und bewertet verfügbare Datenquellen für eine Stadt/Region.
"""

import json
import requests
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum


class QuellenTyp(Enum):
    OVERPASS = "overpass"
    GTFS = "gtfs"
    OTP = "otp"
    ECHTZEIT = "echtzeit"
    RIDE_HAILING = "ride_hailing"
    OSRM = "osrm"


@dataclass
class Datenquelle:
    typ: QuellenTyp
    name: str
    url: str
    verfuegbar: bool = False
    qualitaets_score: float = 0.0  # 0.0 bis 1.0
    beschreibung: str = ""
    bemerkungen: List[str] = field(default_factory=list)

    def to_dict(self):
        d = asdict(self)
        d['typ'] = self.typ.value
        return d


class DatenScout:
    """Findet und bewertet Datenquellen für eine Stadt."""

    def __init__(self, stadt: str):
        self.stadt = stadt
        self.quellen: List[Datenquelle] = []
        self.bbox: Optional[Tuple[float, float, float, float]] = None

    def finde_datenquellen(self) -> List[Datenquelle]:
        """Hauptfunktion: Findet alle verfügbaren Datenquellen."""
        print(f"\n🔍 Daten-Scout für: {self.stadt}")
        print("=" * 50)

        # 1. Overpass API (immer verfügbar)
        self._check_overpass()

        # 2. GTFS-Feeds suchen
        self._check_gtfs()

        # 3. OpenTripPlanner Instanzen
        self._check_otp()

        # 4. Echtzeit-APIs
        self._check_echtzeit()

        # 5. Ride-Hailing Anbieter
        self._check_ride_hailing()

        # 6. OSRM Instanzen
        self._check_osrm()

        # Sortieren nach Qualität
        self.quellen.sort(key=lambda q: q.qualitaets_score, reverse=True)

        return self.quellen

    def _check_overpass(self):
        """Prüft Overpass API für OSM-Daten."""
        print("\n📍 Prüfe Overpass API...")

        try:
            # Einfache Query: Suche nach ÖPNV-Stationen in der Stadt
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

            response = requests.post(
                "https://overpass-api.de/api/interpreter",
                data={"data": query},
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                anzahl = data.get("elements", [{}])[0].get("tags", {}).get("total", 0)

                # Bounding Box extrahieren
                if data.get("elements"):
                    bounds = data["elements"][0].get("bounds")
                    if bounds:
                        self.bbox = (
                            bounds.get("minlon", 0),
                            bounds.get("minlat", 0),
                            bounds.get("maxlon", 0),
                            bounds.get("maxlat", 0)
                        )

                verfuegbar = anzahl > 0
                score = min(anzahl / 100, 1.0)  # Normalisierung

                quelle = Datenquelle(
                    typ=QuellenTyp.OVERPASS,
                    name="OpenStreetMap (Overpass API)",
                    url="https://overpass-api.de",
                    verfuegbar=verfuegbar,
                    qualitaets_score=score,
                    beschreibung=f"{anzahl} ÖPNV-Stationen in {self.stadt}",
                    bemerkungen=["Weltweit verfügbar", "OSM-basiert", "Kein Fahrplan"]
                )
            else:
                quelle = Datenquelle(
                    typ=QuellenTyp.OVERPASS,
                    name="OpenStreetMap (Overpass API)",
                    url="https://overpass-api.de",
                    verfuegbar=False,
                    qualitaets_score=0.0,
                    beschreibung="Overpass API nicht erreichbar"
                )

        except Exception as e:
            quelle = Datenquelle(
                typ=QuellenTyp.OVERPASS,
                name="OpenStreetMap (Overpass API)",
                url="https://overpass-api.de",
                verfuegbar=False,
                qualitaets_score=0.0,
                beschreibung=f"Fehler: {str(e)}"
            )

        self.quellen.append(quelle)
        status = "✅" if quelle.verfuegbar else "❌"
        print(f"  {status} {quelle.name}: {quelle.beschreibung}")

    def _check_gtfs(self):
        """Sucht nach GTFS-Feeds für die Stadt."""
        print("\n📋 Suche GTFS-Feeds...")

        # Bekannte GTFS-Feeds für große Städte
        bekannte_feeds = {
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

        # TransitFeeds.com API
        try:
            response = requests.get(
                "https://api.transitfeeds.com/v1/getLocations",
                params={"key": "demo"},  # Demo-Key
                timeout=10
            )
            if response.status_code == 200:
                # Suche nach der Stadt in den Ergebnissen
                pass  # TransitFeeds API braucht echten Key
        except:
            pass

        feed_url = bekannte_feeds.get(self.stadt)
        if feed_url:
            quelle = Datenquelle(
                typ=QuellenTyp.GTFS,
                name=f"GTFS-Feed ({self.stadt})",
                url=feed_url,
                verfuegbar=True,
                qualitaets_score=0.9,
                beschreibung="Offizieller GTFS-Feed mit Fahrplänen",
                bemerkungen=["Fahrpläne", "Echtzeit-Daten möglich", "Standardisiert"]
            )
        else:
            quelle = Datenquelle(
                typ=QuellenTyp.GTFS,
                name=f"GTFS-Feed ({self.stadt})",
                url="",
                verfuegbar=False,
                qualitaets_score=0.0,
                beschreibung="Kein bekannter GTFS-Feed",
                bemerkungen=["TransitFeeds.com prüfen", "Verkehrsbetreiber kontaktieren"]
            )

        self.quellen.append(quelle)
        status = "✅" if quelle.verfuegbar else "❌"
        print(f"  {status} {quelle.name}: {quelle.beschreibung}")

    def _check_otp(self):
        """Prüft OpenTripPlanner Instanzen."""
        print("\n🗺️  Prüfe OpenTripPlanner...")

        bekannte_otp = {
            "Berlin": "https://otp.bbnavi.de",
            "Hamburg": "https://otp.hamburg.de",
            "München": "https://otp.mvv-muenchen.de",
            "Frankfurt": "https://otp.rmv.de",
        }

        otp_url = bekannte_otp.get(self.stadt)
        if otp_url:
            quelle = Datenquelle(
                typ=QuellenTyp.OTP,
                name=f"OTP-Instanz ({self.stadt})",
                url=otp_url,
                verfuegbar=True,
                qualitaets_score=0.95,
                beschreibung="Lokale OTP-Instanz mit Routing-Algorithmen",
                bemerkungen=["GTFS + OSM", "Erweiterte Routing-Funktionen"]
            )
        else:
            quelle = Datenquelle(
                typ=QuellenTyp.OTP,
                name=f"OTP-Instanz ({self.stadt})",
                url="",
                verfuegbar=False,
                qualitaets_score=0.0,
                beschreibung="Keine bekannte OTP-Instanz",
                bemerkungen=["OTP selbst hosten", "OTP-Dashboard prüfen"]
            )

        self.quellen.append(quelle)
        status = "✅" if quelle.verfuegbar else "❌"
        print(f"  {status} {quelle.name}: {quelle.beschreibung}")

    def _check_echtzeit(self):
        """Prüft Echtzeit-APIs."""
        print("\n⏱️  Prüfe Echtzeit-APIs...")

        bekannte_echtzeit = {
            "Berlin": "https://vbb.de/api",
            "Hamburg": "https://hvv.de/api",
            "München": "https://mvv-muenchen.de/api",
        }

        api_url = bekannte_echtzeit.get(self.stadt)
        if api_url:
            quelle = Datenquelle(
                typ=QuellenTyp.ECHTZEIT,
                name=f"Echtzeit-API ({self.stadt})",
                url=api_url,
                verfuegbar=True,
                qualitaets_score=0.85,
                beschreibung="Echtzeit-Daten für Störungen/Verspätungen",
                bemerkungen=["Fahrplan-Abweichungen", "Störungen", "Echtzeit-Abfahrten"]
            )
        else:
            quelle = Datenquelle(
                typ=QuellenTyp.ECHTZEIT,
                name=f"Echtzeit-API ({self.stadt})",
                url="",
                verfuegbar=False,
                qualitaets_score=0.0,
                beschreibung="Keine bekannte Echtzeit-API",
                bemerkungen=["GTFS-RT prüfen", "Verkehrsbetreiber kontaktieren"]
            )

        self.quellen.append(quelle)
        status = "✅" if quelle.verfuegbar else "❌"
        print(f"  {status} {quelle.name}: {quelle.beschreibung}")

    def _check_ride_hailing(self):
        """Prüft Ride-Hailing Anbieter."""
        print("\n🚗 Prüfe Ride-Hailing Anbieter...")

        # Regionale Anbieter
        anbieter = {
            "Berlin": ["Uber", "Bolt", "Free Now"],
            "Hamburg": ["Uber", "Bolt", "Free Now"],
            "München": ["Uber", "Free Now"],
            "Wien": ["Uber", "Bolt"],
            "Zürich": ["Uber"],
            "London": ["Uber", "Bolt"],
            "Paris": ["Uber", "Bolt", "Free Now"],
            "New York": ["Uber", "Lyft"],
            "Tokyo": ["Uber", "GO"],
            "Sydney": ["Uber", "DiDi"],
        }

        stadt_anbieter = anbieter.get(self.stadt, ["Uber"])  # Uber als Default

        quelle = Datenquelle(
            typ=QuellenTyp.RIDE_HAILING,
            name=f"Ride-Hailing ({self.stadt})",
            url="",
            verfuegbar=True,
            qualitaets_score=0.7,
            beschreibung=f"Verfügbar: {', '.join(stadt_anbieter)}",
            bemerkungen=["Dynamische Brücken", "API-Keys erforderlich", "Preise variabel"]
        )

        self.quellen.append(quelle)
        status = "✅" if quelle.verfuegbar else "❌"
        print(f"  {status} {quelle.name}: {quelle.beschreibung}")

    def _check_osrm(self):
        """Prüft OSRM-Instanzen für Straßenrouting."""
        print("\n🛣️  Prüfe OSRM-Instanzen...")

        try:
            response = requests.get(
                "https://router.project-osrm.org/route/v1/driving/8.68,50.11;8.69,50.12",
                params={"overview": "false"},
                timeout=10
            )
            verfuegbar = response.status_code == 200
        except:
            verfuegbar = False

        quelle = Datenquelle(
            typ=QuellenTyp.OSRM,
            name="OSRM (Open Source Routing Machine)",
            url="https://router.project-osrm.org",
            verfuegbar=verfuegbar,
            qualitaets_score=0.8 if verfuegbar else 0.0,
            beschreibung="Straßenrouting für Fußwege und Ride-Hailing",
            bemerkungen=["Weltweit verfügbar", "Schnell", "Open Source"]
        )

        self.quellen.append(quelle)
        status = "✅" if quelle.verfuegbar else "❌"
        print(f"  {status} {quelle.name}: {quelle.beschreibung}")

    def erstelle_bericht(self) -> Dict:
        """Erstellt einen zusammenfassenden Bericht."""
        verfuegbare = [q for q in self.quellen if q.verfuegbar]
        nicht_verfuegbare = [q for q in self.quellen if not q.verfuegbar]

        # Beste Quelle bestimmen
        beste_quelle = self.quellen[0] if self.quellen else None

        bericht = {
            "stadt": self.stadt,
            "bbox": self.bbox,
            "gesamt_quellen": len(self.quellen),
            "verfuegbare_quellen": len(verfuegbare),
            "beste_quelle": beste_quelle.to_dict() if beste_quelle else None,
            "quellen": [q.to_dict() for q in self.quellen],
            "empfehlung": self._generiere_empfehlung(verfuegbare)
        }

        return bericht

    def _generiere_empfehlung(self, verfuegbare: List[Datenquelle]) -> str:
        """Generiert eine Empfehlung basierend auf verfügbaren Quellen."""
        if not verfuegbare:
            return "❌ Keine Datenquellen verfügbar. Bitte manuell Daten beschaffen."

        beste = verfuegbare[0]

        if beste.typ == QuellenTyp.OTP:
            return f"✅ Nutze {beste.name}: Beste Datenqualität mit Routing-Algorithmen."
        elif beste.typ == QuellenTyp.GTFS:
            return f"✅ Nutze {beste.name}: Fahrpläne für zeitgenaues Routing."
        elif beste.typ == QuellenTyp.OVERPASS:
            return f"⚠️  Nutze {beste.name}: OSM-Daten verfügbar, aber ohne Fahrpläne. Routing mit Annäherungen."
        else:
            return f"⚠️  Nutze {beste.name}: Eingeschränkte Datenqualität."

    def print_bericht(self):
        """Druckt einen formatierten Bericht."""
        bericht = self.erstelle_bericht()

        print("\n" + "=" * 50)
        print(f"📊 DATEN-SCOUT BERICHT: {self.stadt}")
        print("=" * 50)

        if self.bbox:
            min_lon, min_lat, max_lon, max_lat = self.bbox
            print(f"\n📍 Bounding Box: ({min_lon:.4f}, {min_lat:.4f}) → ({max_lon:.4f}, {max_lat:.4f})")

        print(f"\nVerfügbare Quellen: {bericht['verfuegbare_quellen']}/{bericht['gesamt_quellen']}")

        for q in self.quellen:
            status = "✅" if q.verfuegbar else "❌"
            print(f"\n  {status} {q.name}")
            print(f"     Typ: {q.typ.value}")
            print(f"     Qualität: {q.qualitaets_score:.2f}")
            print(f"     {q.beschreibung}")
            if q.bemerkungen:
                print(f"     Hinweis: {', '.join(q.bemerkungen)}")

        print(f"\n💡 Empfehlung: {bericht['empfehlung']}")


def main():
    """CLI-Einstiegspunkt für den Daten-Scout."""
    import argparse

    parser = argparse.ArgumentParser(description="ÖPNV Daten-Scout für eine Stadt")
    parser.add_argument("--stadt", required=True, help="Name der Stadt")
    parser.add_argument("--output", default="scout_ergebnis.json", help="Ausgabedatei (JSON)")

    args = parser.parse_args()

    scout = DatenScout(args.stadt)
    scout.finde_datenquellen()
    scout.print_bericht()

    # JSON-Export
    bericht = scout.erstelle_bericht()
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(bericht, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Bericht gespeichert: {args.output}")


if __name__ == "__main__":
    main()
