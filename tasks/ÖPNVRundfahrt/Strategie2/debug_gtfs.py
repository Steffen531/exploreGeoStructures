#!/usr/bin/env python3
"""Debug-Skript für GTFS-Problem."""

from gtfs_parser import erstelle_test_gtfs
from routing import erstelle_test_graph

def main():
    # Lade GTFS-Daten
    gtfs = erstelle_test_gtfs()
    graph = erstelle_test_graph()

    print("=== GTFS Debug ===")
    print(f"GTFS Stationen: {len(gtfs.stops)}")
    print(f"Graph Stationen: {len(graph.stationen)}")
    print(f"GTFS Linien: {len(gtfs.routes)}")
    print(f"Graph Linien: {len(graph.linien)}")

    # Prüfe Stationen
    print("\n--- Stationen ---")
    for sid in list(gtfs.stops.keys())[:5]:
        in_graph = sid in graph.stationen
        print(f"  GTFS: {sid} -> Graph: {in_graph}")

    # Prüfe Linien
    print("\n--- Linien ---")
    for lid in list(gtfs.routes.keys())[:5]:
        in_graph = lid in graph.linien
        print(f"  GTFS: {lid} -> Graph: {in_graph}")

    # Prüfe Abfahrt
    print("\n--- Abfahrt Test ---")
    result = gtfs.get_next_departure("hbf", "S8", "18:00", "2026-12-01")
    print(f"  hbf -> S8 nach 18:00: {result}")

    result = gtfs.get_next_departure("hbf", "S9", "18:00", "2026-12-01")
    print(f"  hbf -> S9 nach 18:00: {result}")

    # Prüfe StopTimes
    print("\n--- StopTimes Test ---")
    trips = gtfs.get_trips_for_route("S8")
    print(f"  S8 Fahrten: {len(trips)}")
    if trips:
        stop_times = gtfs.get_stop_times_for_trip(trips[0].trip_id)
        print(f"  Erste Fahrt StopTimes: {len(stop_times)}")
        for st in stop_times[:3]:
            print(f"    {st.stop_id}: {st.departure_time} -> {st.arrival_time}")

if __name__ == "__main__":
    main()
