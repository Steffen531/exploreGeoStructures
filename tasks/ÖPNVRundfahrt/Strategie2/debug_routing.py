#!/usr/bin/env python3
"""Debug-Skript: Analysiert den Routing-Graph und findet blockierte Pfade."""

from routing import RoutingGraph, erstelle_test_graph, VerkehrsmittelTyp

def analysiere_graph(graph: RoutingGraph):
    """Analysiert die Graph-Struktur."""
    print("=== Graph-Analyse ===")
    print(f"Stationen: {len(graph.stationen)}")
    print(f"Linien: {len(graph.linien)}")

    print("\n--- Stationen und ihre Verbindungen ---")
    for sid, station in sorted(graph.stationen.items()):
        nachbarn = graph.get_nachbarn(sid)
        print(f"\n  {sid} ({station.name})")
        print(f"    Stadtteil: {station.stadtteil}")
        print(f"    Verkehrsmittel: {[v.value for v in station.verkehrsmittel]}")
        print(f"    Nachbarn: {len(nachbarn)}")
        for nachbar_id, linie_id in nachbarn:
            nachbar = graph.get_station(nachbar_id)
            linie = graph.linien.get(linie_id)
            print(f"      -> {nachbar_id} ({nachbar.name if nachbar else '?'}) via {linie_id} ({linie.name if linie else '?'})")

    print("\n--- Linien und ihre Stationen ---")
    for lid, linie in sorted(graph.linien.items()):
        print(f"\n  {lid} ({linie.name}) - {linie.typ.value}")
        print(f"    Stationen: {linie.stationen}")

def finde_einfache_pfade(graph: RoutingGraph, start_id: str, ziel_id: str, max_tiefe: int = 10):
    """Findet einfache Pfade ohne Constraints."""
    print(f"\n=== Einfache Pfade: {start_id} -> {ziel_id} ===")

    stack = [([start_id], {start_id})]
    gefunden = 0

    while stack and gefunden < 5:
        pfad, besucht = stack.pop()
        aktuell = pfad[-1]

        if aktuell == ziel_id:
            print(f"  Pfad: {' -> '.join(pfad)}")
            gefunden += 1
            continue

        if len(pfad) >= max_tiefe:
            continue

        for nachbar_id, linie_id in graph.get_nachbarn(aktuell):
            if nachbar_id not in besucht:
                stack.append((pfad + [nachbar_id], besucht | {nachbar_id}))

    if gefunden == 0:
        print("  Keine einfachen Pfade gefunden!")

def main():
    graph = erstelle_test_graph()
    analysiere_graph(graph)
    finde_einfache_pfade(graph, "hbf", "hoechst")

if __name__ == "__main__":
    main()
