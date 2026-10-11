#!/usr/bin/env python3
"""
GTFS-Parser: Liest GTFS-Daten und stellt Fahrpläne für den Router bereit.
"""

import csv
import json
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class Stop:
    """Eine Haltestelle (GTFS stop)."""
    stop_id: str
    stop_name: str
    lat: float
    lon: float


@dataclass
class Route:
    """Eine Linie (GTFS route)."""
    route_id: str
    route_short_name: str
    route_long_name: str
    route_type: int  # 0=Tram, 1=U-Bahn, 2=S-Bahn, 3=Bus, 4=Fähre


@dataclass
class Trip:
    """Eine Fahrt (GTFS trip)."""
    trip_id: str
    route_id: str
    service_id: str


@dataclass
class StopTime:
    """Eine Haltestellen-Zeit (GTFS stop_time)."""
    trip_id: str
    stop_id: str
    arrival_time: str  # "HH:MM:SS"
    departure_time: str  # "HH:MM:SS"
    stop_sequence: int


@dataclass
class Calendar:
    """Kalender (GTFS calendar)."""
    service_id: str
    monday: bool
    tuesday: bool
    wednesday: bool
    thursday: bool
    friday: bool
    saturday: bool
    sunday: bool
    start_date: str
    end_date: str


@dataclass
class GtfsData:
    """Geparste GTFS-Daten."""
    stops: Dict[str, Stop] = field(default_factory=dict)
    routes: Dict[str, Route] = field(default_factory=dict)
    trips: Dict[str, Trip] = field(default_factory=dict)
    stop_times: Dict[str, List[StopTime]] = field(default_factory=dict)  # trip_id -> [StopTime]
    calendar: Dict[str, Calendar] = field(default_factory=dict)

    def get_trips_for_route(self, route_id: str) -> List[Trip]:
        """Gibt alle Fahrten für eine Linie zurück."""
        return [t for t in self.trips.values() if t.route_id == route_id]

    def get_stop_times_for_trip(self, trip_id: str) -> List[StopTime]:
        """Gibt alle Haltestellen-Zeiten für eine Fahrt zurück."""
        return self.stop_times.get(trip_id, [])

    def get_next_departure(
        self,
        stop_id: str,
        route_id: str,
        after_time: str,
        date: str
    ) -> Optional[Tuple[str, str]]:
        """
        Findet die nächste Abfahrt für eine Haltestelle und Linie.
        Gibt (trip_id, departure_time) zurück oder None.
        after_time: "HH:MM" Format
        """
        # Normalize after_time to HH:MM:SS for comparison
        if len(after_time) == 5:  # "HH:MM"
            after_time_cmp = after_time + ":00"
        else:
            after_time_cmp = after_time

        # Prüfe ob der Service an diesem Tag fährt
        service_ids = self._get_service_ids_for_date(date)
        if not service_ids:
            return None

        # Finde Fahrten für diese Linie und Service
        trips = self.get_trips_for_route(route_id)
        valid_trips = [t for t in trips if t.service_id in service_ids]

        best_trip = None
        best_time = None

        for trip in valid_trips:
            stop_times = self.get_stop_times_for_trip(trip.trip_id)
            for st in stop_times:
                # Normalize departure time to HH:MM:SS for comparison
                dep_time = st.departure_time
                if len(dep_time) == 5:  # "HH:MM"
                    dep_time = dep_time + ":00"
                
                if st.stop_id == stop_id and dep_time >= after_time_cmp:
                    if best_time is None or dep_time < best_time:
                        best_trip = trip.trip_id
                        best_time = dep_time

        if best_trip and best_time:
            # Return time in HH:MM format
            return (best_trip, best_time[:5])
        return None

    def _get_service_ids_for_date(self, date: str) -> Set[str]:
        """Gibt Service-IDs für ein bestimmtes Datum zurück."""
        dt = datetime.strptime(date, "%Y-%m-%d")
        weekday = dt.weekday()  # 0=Montag, 6=Sonntag

        service_ids = set()
        # Normalize date to YYYYMMDD for comparison with calendar
        date_normalized = date.replace("-", "")
        for cal in self.calendar.values():
            # Prüfe ob das Datum im Gültigkeitsbereich liegt
            if cal.start_date <= date_normalized <= cal.end_date:
                # Prüfe ob der Wochentag passt
                if weekday == 0 and cal.monday:
                    service_ids.add(cal.service_id)
                elif weekday == 1 and cal.tuesday:
                    service_ids.add(cal.service_id)
                elif weekday == 2 and cal.wednesday:
                    service_ids.add(cal.service_id)
                elif weekday == 3 and cal.thursday:
                    service_ids.add(cal.service_id)
                elif weekday == 4 and cal.friday:
                    service_ids.add(cal.service_id)
                elif weekday == 5 and cal.saturday:
                    service_ids.add(cal.service_id)
                elif weekday == 6 and cal.sunday:
                    service_ids.add(cal.service_id)

        return service_ids


class GtfsParser:
    """Parst GTFS-Daten aus einem Verzeichnis oder ZIP-Archiv."""

    def __init__(self, gtfs_path: str):
        self.gtfs_path = Path(gtfs_path)
        self.data = GtfsData()

    def parse(self) -> GtfsData:
        """Parst alle GTFS-Dateien."""
        print(f"\n📂 Lade GTFS-Daten aus: {self.gtfs_path}")

        if self.gtfs_path.is_file() and self.gtfs_path.suffix == '.zip':
            self._parse_zip()
        else:
            self._parse_directory()

        print(f"  ✅ {len(self.data.stops)} Haltestellen")
        print(f"  ✅ {len(self.data.routes)} Linien")
        print(f"  ✅ {len(self.data.trips)} Fahrten")
        print(f"  ✅ {len(self.data.calendar)} Kalender")

        return self.data

    def _parse_zip(self):
        """Parst GTFS-Daten aus einem ZIP-Archiv."""
        with zipfile.ZipFile(self.gtfs_path, 'r') as zf:
            for name in zf.namelist():
                if name.endswith('.txt'):
                    with zf.open(name) as f:
                        self._parse_csv(name, f)

    def _parse_directory(self):
        """Parst GTFS-Daten aus einem Verzeichnis."""
        for txt_file in self.gtfs_path.glob('*.txt'):
            with open(txt_file, 'r', encoding='utf-8') as f:
                self._parse_csv(txt_file.name, f)

    def _parse_csv(self, filename: str, file):
        """Parst eine einzelne GTFS-CSV-Datei."""
        reader = csv.DictReader(file)

        if filename == 'stops.txt':
            for row in reader:
                self.data.stops[row['stop_id']] = Stop(
                    stop_id=row['stop_id'],
                    stop_name=row['stop_name'],
                    lat=float(row['stop_lat']),
                    lon=float(row['stop_lon'])
                )

        elif filename == 'routes.txt':
            for row in reader:
                self.data.routes[row['route_id']] = Route(
                    route_id=row['route_id'],
                    route_short_name=row.get('route_short_name', ''),
                    route_long_name=row.get('route_long_name', ''),
                    route_type=int(row['route_type'])
                )

        elif filename == 'trips.txt':
            for row in reader:
                self.data.trips[row['trip_id']] = Trip(
                    trip_id=row['trip_id'],
                    route_id=row['route_id'],
                    service_id=row['service_id']
                )

        elif filename == 'stop_times.txt':
            for row in reader:
                stop_time = StopTime(
                    trip_id=row['trip_id'],
                    stop_id=row['stop_id'],
                    arrival_time=row['arrival_time'],
                    departure_time=row['departure_time'],
                    stop_sequence=int(row['stop_sequence'])
                )
                if row['trip_id'] not in self.data.stop_times:
                    self.data.stop_times[row['trip_id']] = []
                self.data.stop_times[row['trip_id']].append(stop_time)

        elif filename == 'calendar.txt':
            for row in reader:
                self.data.calendar[row['service_id']] = Calendar(
                    service_id=row['service_id'],
                    monday=row['monday'] == '1',
                    tuesday=row['tuesday'] == '1',
                    wednesday=row['wednesday'] == '1',
                    thursday=row['thursday'] == '1',
                    friday=row['friday'] == '1',
                    saturday=row['saturday'] == '1',
                    sunday=row['sunday'] == '1',
                    start_date=row['start_date'],
                    end_date=row['end_date']
                )


def erstelle_test_gtfs() -> GtfsData:
    """Erstellt test GTFS-Daten für Frankfurt."""
    data = GtfsData()

    # Haltestellen
    stops = [
        ("hbf", "Frankfurt Hbf", 50.1070, 8.6636),
        ("konstablerwache", "Konstablerwache", 50.1130, 8.6895),
        ("ost", "Frankfurt Ost", 50.1130, 8.7200),
        ("sued", "Frankfurt Süd", 50.0900, 8.6800),
        ("lokalbahnhof", "Lokalbahnhof", 50.0950, 8.6850),
        ("hoechst", "Frankfurt Höchst", 50.1000, 8.6000),
        ("hauptwache", "Hauptwache", 50.1150, 8.6770),
        ("willy_brandt", "Willy-Brandt-Platz", 50.1090, 8.6650),
        ("nordweststadt", "Nordweststadt", 50.1300, 8.6500),
        ("bockenheim", "Bockenheim", 50.1200, 8.6400),
        ("sachsenhausen", "Sachsenhausen", 50.1000, 8.6600),
        ("westend", "Westend", 50.1200, 8.6500),
        ("nordend", "Nordend", 50.1200, 8.6800),
        ("gallus", "Gallus", 50.1000, 8.6400),
        ("ginnheim", "Ginnheim", 50.1400, 8.6500),
        ("bornheim", "Bornheim", 50.1200, 8.7000),
        ("seckbach", "Seckbach", 50.1300, 8.7000),
        ("niederrad", "Niederrad", 50.0800, 8.6500),
        ("flughafen", "Flughafen", 50.0300, 8.6200),
        ("mainz_hbf", "Mainz Hbf", 50.0000, 8.6000),
        ("offenbach", "Offenbach Hbf", 50.1000, 8.7500),
        ("darmstadt", "Darmstadt Hbf", 49.8700, 8.6500),
    ]

    for stop_id, name, lat, lon in stops:
        data.stops[stop_id] = Stop(stop_id, name, lat, lon)

    # Linien
    routes = [
        ("S8", "S8", "S8", 2),  # S-Bahn
        ("S9", "S9", "S9", 2),
        ("S1", "S1", "S1", 2),
        ("S2", "S2", "S2", 2),
        ("S3", "S3", "S3", 2),
        ("S4", "S4", "S4", 2),
        ("S5", "S5", "S5", 2),
        ("S6", "S6", "S6", 2),
        ("S7", "S7", "S7", 2),
        ("U1", "U1", "U1", 1),  # U-Bahn
        ("U2", "U2", "U2", 1),
        ("U3", "U3", "U3", 1),
        ("U4", "U4", "U4", 1),
        ("U5", "U5", "U5", 1),
        ("U6", "U6", "U6", 1),
        ("U7", "U7", "U7", 1),
        ("U8", "U8", "U8", 1),
        ("U9", "U9", "U9", 1),
        ("T11", "11", "11", 0),  # Straßenbahn
        ("T12", "12", "12", 0),
        ("T14", "14", "14", 0),
        ("T15", "15", "15", 0),
        ("T16", "16", "16", 0),
        ("T17", "17", "17", 0),
        ("T18", "18", "18", 0),
        ("T19", "19", "19", 0),
        ("T20", "20", "20", 0),
        ("T21", "21", "21", 0),
        ("F1", "F1", "F1", 4),  # Fähre
        ("F2", "F2", "F2", 4),
        ("F3", "F3", "F3", 4),
        ("F4", "F4", "F4", 4),
        ("R1", "RE1", "RE1", 2),  # Regionalzug
        ("R2", "RE2", "RE2", 2),
        ("R3", "RE3", "RE3", 2),
        ("R4", "RE4", "RE4", 2),
        ("R5", "RE5", "RE5", 2),
    ]

    for route_id, short_name, long_name, route_type in routes:
        data.routes[route_id] = Route(route_id, short_name, long_name, route_type)

    # Fahrten (vereinfacht: jede Linie hat Fahrten alle 10 Minuten von 6:00 bis 23:59)
    trip_id = 0
    for route_id, _, _, _ in routes:
        for hour in range(6, 24):
            for minute in [0, 10, 20, 30, 40, 50]:
                if hour == 23 and minute > 50:
                    continue
                trip_id += 1
                tid = f"trip_{trip_id}"
                data.trips[tid] = Trip(tid, route_id, "service_1")

                # StopTimes für diese Fahrt
                # Vereinfacht: 2 Min pro Station
                for seq, stop_id in enumerate(get_stops_for_route(route_id), 1):
                    if seq == 1:
                        dep_time = f"{hour:02d}:{minute:02d}:00"
                        arr_time = f"{hour:02d}:{minute + 2:02d}:00"
                    else:
                        minute += 2
                        dep_time = f"{hour:02d}:{minute:02d}:00"
                        arr_time = f"{hour:02d}:{minute + 2:02d}:00"

                    stop_time = StopTime(tid, stop_id, arr_time, dep_time, seq)
                    if tid not in data.stop_times:
                        data.stop_times[tid] = []
                    data.stop_times[tid].append(stop_time)

    # Kalender (täglich)
    data.calendar["service_1"] = Calendar(
        "service_1", True, True, True, True, True, True, True,
        "20260101", "20261231"
    )

    return data


def get_stops_for_route(route_id: str) -> List[str]:
    """Gibt die Stationen für eine Linie zurück (vereinfacht)."""
    # Gleiche Struktur wie im Test-Graph
    route_stops = {
        "S8": ["hbf", "konstablerwache", "ost", "offenbach"],
        "S9": ["hbf", "hoechst", "mainz_hbf"],
        "S1": ["hbf", "niederrad", "flughafen"],
        "S2": ["hbf", "niederrad", "darmstadt"],
        "S3": ["hbf", "hauptwache", "ost", "offenbach"],
        "S4": ["hbf", "konstablerwache", "bornheim", "seckbach"],
        "S5": ["hbf", "willy_brandt", "nordend", "bornheim"],
        "S6": ["hbf", "hauptwache", "ost", "nordend"],
        "S7": ["hbf", "konstablerwache", "sued", "niederrad"],
        "U1": ["hbf", "hauptwache", "willy_brandt", "nordweststadt"],
        "U2": ["hbf", "konstablerwache", "bornheim", "seckbach"],
        "U3": ["hbf", "willy_brandt", "bockenheim", "ginnheim"],
        "U4": ["westend", "bockenheim", "nordweststadt", "ginnheim"],
        "U5": ["hbf", "konstablerwache", "nordend", "bornheim"],
        "U6": ["hbf", "gallus", "niederrad"],
        "U7": ["hbf", "hauptwache", "nordend", "seckbach"],
        "U8": ["hbf", "willy_brandt", "ost", "offenbach"],
        "U9": ["hbf", "konstablerwache", "sued", "niederrad"],
        "T11": ["ost", "konstablerwache", "lokalbahnhof", "sued", "niederrad"],
        "T12": ["ost", "konstablerwache", "sachsenhausen", "westend", "nordweststadt"],
        "T14": ["ost", "bornheim", "seckbach", "nordend"],
        "T15": ["hbf", "gallus", "westend", "bockenheim", "ginnheim"],
        "T16": ["hbf", "hauptwache", "ost", "bornheim", "seckbach"],
        "T17": ["hbf", "willy_brandt", "nordend", "nordweststadt"],
        "T18": ["hbf", "konstablerwache", "sachsenhausen", "hoechst"],
        "T19": ["hbf", "gallus", "sued", "niederrad", "flughafen"],
        "T20": ["hbf", "hauptwache", "ost", "offenbach", "darmstadt"],
        "T21": ["hbf", "willy_brandt", "bornheim", "seckbach", "nordend"],
        "F1": ["sued", "sachsenhausen", "hoechst"],
        "F2": ["sued", "niederrad", "mainz_hbf"],
        "F3": ["ost", "offenbach", "mainz_hbf"],
        "F4": ["hbf", "sachsenhausen", "hoechst", "mainz_hbf"],
        "R1": ["hbf", "offenbach", "darmstadt"],
        "R2": ["hbf", "mainz_hbf", "darmstadt"],
        "R3": ["hbf", "hoechst", "mainz_hbf", "darmstadt"],
        "R4": ["hbf", "niederrad", "flughafen", "darmstadt"],
        "R5": ["hbf", "ost", "offenbach", "mainz_hbf"],
    }
    return route_stops.get(route_id, [])


def main():
    import argparse

    parser = argparse.ArgumentParser(description="GTFS-Parser")
    parser.add_argument("--gtfs", help="Pfad zu GTFS-Daten (ZIP oder Verzeichnis)")
    parser.add_argument("--output", default="gtfs_data.json", help="Ausgabedatei (JSON)")

    args = parser.parse_args()

    if args.gtfs:
        gtfs_parser = GtfsParser(args.gtfs)
        data = gtfs_parser.parse()
    else:
        print("Keine GTFS-Daten angegeben, erstelle Test-Daten...")
        data = erstelle_test_gtfs()

    # JSON-Export
    export = {
        "stops": {k: {"stop_id": v.stop_id, "stop_name": v.stop_name, "lat": v.lat, "lon": v.lon} for k, v in data.stops.items()},
        "routes": {k: {"route_id": v.route_id, "route_short_name": v.route_short_name, "route_long_name": v.route_long_name, "route_type": v.route_type} for k, v in data.routes.items()},
        "trips": {k: {"trip_id": v.trip_id, "route_id": v.route_id, "service_id": v.service_id} for k, v in data.trips.items()},
        "calendar": {k: {"service_id": v.service_id, "monday": v.monday, "tuesday": v.tuesday, "wednesday": v.wednesday, "thursday": v.thursday, "friday": v.friday, "saturday": v.saturday, "sunday": v.sunday, "start_date": v.start_date, "end_date": v.end_date} for k, v in data.calendar.items()},
    }

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(export, f, indent=2, ensure_ascii=False)

    print(f"\n💾 GTFS-Daten gespeichert: {args.output}")


if __name__ == "__main__":
    main()
