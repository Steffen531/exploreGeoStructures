#!/usr/bin/env python3
"""
Phase 4: Kartenvisualisierung
Erstellt KML, GPX und interaktive HTML-Karten aus Routen-Daten.
"""

import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom


class KMLCreator:
    """Erstellt KML-Dateien aus Routen."""

    def __init__(self, routen: List[Dict], stationen: Dict[str, Dict], graph_linien: Dict = None):
        self.routen = routen
        self.stationen = stationen
        self.graph_linien = graph_linien or {}

    def create_kml(self, output_path: str):
        """Erstellt eine KML-Datei mit allen Routen."""
        kml = Element('kml')
        kml.set('xmlns', 'http://www.opengis.net/kml/2.2')
        document = SubElement(kml, 'Document')

        # Name
        name = SubElement(document, 'name')
        name.text = "ÖPNV-Routen"

        # Shared Styles definieren
        for i in range(1, len(self.routen) + 1):
            style = SubElement(document, 'Style')
            style.set('id', f'routeStyle{i}')
            line_style = SubElement(style, 'LineStyle')
            color = SubElement(line_style, 'color')
            color.text = self._get_route_color(i)
            width = SubElement(line_style, 'width')
            width.text = '4'

        # Routen als Placemarks
        for i, route in enumerate(self.routen, 1):
            placemark = SubElement(document, 'Placemark')
            pm_name = SubElement(placemark, 'name')
            pm_name.text = f"Route {i}"

            # Beschreibung
            desc = SubElement(placemark, 'description')
            desc.text = self._route_description(route)

            # Style-Referenz
            style_url = SubElement(placemark, 'styleUrl')
            style_url.text = f'#routeStyle{i}'

            # Linie mit Geometrie
            line_string = SubElement(placemark, 'LineString')
            coordinates = SubElement(line_string, 'coordinates')
            coordinates.text = self._get_route_coordinates(route)

        # Speichern
        xml_str = minidom.parseString(tostring(kml)).toprettyxml(indent="  ")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(xml_str)

        print(f"KML gespeichert: {output_path}")

    def _get_route_coordinates(self, route: Dict) -> str:
        """Sammelt alle Koordinaten einer Route inkl. aller Zwischenhalte und Geometrie-Punkte."""
        coords = []
        
        # Konsolidiere aufeinanderfolgende Segmente auf der gleichen Linie
        consolidated = self._consolidate_same_line_segments(route)
        
        for j, (von_id, nach_id, linie_id) in enumerate(consolidated):
            if linie_id and linie_id in self.graph_linien:
                linie = self.graph_linien[linie_id]
                
                # Hole alle Stationen auf diesem Linienabschnitt (inkl. Start, Ende, Zwischenhalte)
                segment_stations = self._get_segment_stations(linie, von_id, nach_id)
                
                # Für jedes Teilssegment: Start-Station + Geometrie-Punkte
                for k in range(len(segment_stations) - 1):
                    seg_von = segment_stations[k]
                    seg_nach = segment_stations[k + 1]
                    
                    # Start-Station des Teilssegments
                    if seg_von in self.stationen:
                        station = self.stationen[seg_von]
                        coords.append(f"{station['lon']},{station['lat']},0")
                    
                    # Geometrie-Punkte für dieses Teilssegment
                    key = (seg_von, seg_nach)
                    if hasattr(linie, 'geometrie') and key in linie.geometrie:
                        for lon, lat, _ in linie.geometrie[key]:
                            coords.append(f"{lon},{lat},0")
                
                # Letzte Station des letzten Teilssegments
                last_station = segment_stations[-1]
                if last_station in self.stationen:
                    station = self.stationen[last_station]
                    coords.append(f"{station['lon']},{station['lat']},0")
        
        return ' '.join(coords)

    def _get_segment_stations(self, linie, von_id: str, nach_id: str) -> List[str]:
        """Gibt alle Stationen auf einer Linie zwischen von und nach (inkl. Start/Ende) in Reihenfolge."""
        if not hasattr(linie, 'stationen'):
            return [von_id, nach_id]
        
        try:
            von_idx = linie.stationen.index(von_id)
            nach_idx = linie.stationen.index(nach_id)
            
            if von_idx < nach_idx:
                return linie.stationen[von_idx:nach_idx + 1]
            else:
                return linie.stationen[von_idx:nach_idx - 1:-1]  # umgekehrt
        except ValueError:
            return [von_id, nach_id]

    def _consolidate_same_line_segments(self, route: Dict) -> List[Tuple[str, str, str]]:
        """Fasst aufeinanderfolgende Segmente auf der gleichen Linie zusammen."""
        if not route.get('fahrten'):
            return []
        
        consolidated = []
        current_von = route['fahrten'][0]['von']
        current_linie = route['fahrten'][0]['linie']
        
        for fahrt in route['fahrten']:
            if fahrt['linie'] == current_linie:
                # Gleiches Linie - erweitere das Segment
                continue
            else:
                # Linienwechsel - speichere aktuelles Segment
                consolidated.append((current_von, fahrt['von'], current_linie))
                current_von = fahrt['von']
                current_linie = fahrt['linie']
        
        # Letztes Segment
        if route['fahrten']:
            consolidated.append((current_von, route['fahrten'][-1]['nach'], current_linie))
        
        return consolidated

    def _find_linie_for_segment(self, von: str, nach: str, route: Dict) -> Optional[str]:
        """Findet die Linien-ID für ein Segment."""
        for fahrt in route.get('fahrten', []):
            if fahrt['von'] == von and fahrt['nach'] == nach:
                return fahrt['linie']
        return None

    def _get_intermediate_stations(self, linie, von_id: str, nach_id: str) -> List[str]:
        """Gibt alle Zwischenhalte auf einer Linie zwischen von und nach zurück."""
        if not hasattr(linie, 'stationen'):
            return []
        
        try:
            von_idx = linie.stationen.index(von_id)
            nach_idx = linie.stationen.index(nach_id)
            
            if von_idx < nach_idx:
                return linie.stationen[von_idx + 1:nach_idx]
            else:
                return linie.stationen[nach_idx + 1:von_idx][::-1]
        except ValueError:
            return []

    def _route_description(self, route: Dict) -> str:
        """Erstellt eine HTML-Beschreibung für eine Route."""
        verkehrsmittel = ', '.join(route.get('verkehrsmittel', []))
        return f"""
        <b>Route</b><br>
        Dauer: {route.get('gesamt_dauer_min', 0)} Min<br>
        Umstiege: {len(route.get('umstiege', []))}<br>
        Verkehrsmittel: {verkehrsmittel}
        """

    def _get_route_color(self, index: int) -> str:
        """Gibt eine Farbe für die Route zurück (KML-Format: aabbggrr)."""
        colors = [
            "ff0099ff",  # Blau
            "ff00ff99",  # Grün
            "ff9900ff",  # Lila
            "ff00ffff",  # Cyan
            "ffff00ff",  # Magenta
        ]
        return colors[(index - 1) % len(colors)]


class GPXCreator:
    """Erstellt GPX-Dateien aus Routen."""

    def __init__(self, routen: List[Dict], stationen: Dict[str, Dict], graph_linien: Dict = None):
        self.routen = routen
        self.stationen = stationen
        self.graph_linien = graph_linien or {}

    def create_gpx(self, output_path: str):
        """Erstellt eine GPX-Datei mit allen Routen."""
        gpx = Element('gpx')
        gpx.set('version', '1.1')
        gpx.set('creator', 'ÖPNV-Routen-Planner')
        gpx.set('xmlns', 'http://www.topografix.com/GPX/1/1')

        # Tracks
        for i, route in enumerate(self.routen, 1):
            trk = SubElement(gpx, 'trk')
            name = SubElement(trk, 'name')
            name.text = f"Route {i}"

            # Segmente
            trkseg = SubElement(trk, 'trkseg')

            # Konsolidiere aufeinanderfolgende Segmente auf der gleichen Linie
            consolidated = self._consolidate_same_line_segments(route)
            
            # Punkte mit allen Zwischenhalten und Geometrie
            for j, (von_id, nach_id, linie_id) in enumerate(consolidated):
                if linie_id and linie_id in self.graph_linien:
                    linie = self.graph_linien[linie_id]
                    
                    # Hole alle Stationen auf diesem Linienabschnitt
                    segment_stations = self._get_segment_stations(linie, von_id, nach_id)
                    
                    # Für jedes Teilssegment: Start-Station + Geometrie-Punkte
                    for k in range(len(segment_stations) - 1):
                        seg_von = segment_stations[k]
                        seg_nach = segment_stations[k + 1]
                        
                        # Start-Station des Teilssegments
                        if seg_von in self.stationen:
                            station = self.stationen[seg_von]
                            trkpt = SubElement(trkseg, 'trkpt')
                            trkpt.set('lat', str(station['lat']))
                            trkpt.set('lon', str(station['lon']))
                            ele = SubElement(trkpt, 'ele')
                            ele.text = '0'
                        
                        # Geometrie-Punkte für dieses Teilssegment
                        key = (seg_von, seg_nach)
                        if hasattr(linie, 'geometrie') and key in linie.geometrie:
                            for lon, lat, _ in linie.geometrie[key]:
                                trkpt = SubElement(trkseg, 'trkpt')
                                trkpt.set('lat', str(lat))
                                trkpt.set('lon', str(lon))
                                ele = SubElement(trkpt, 'ele')
                                ele.text = '0'
                    
                    # Letzte Station des letzten Teilssegments
                    last_station = segment_stations[-1]
                    if last_station in self.stationen:
                        station = self.stationen[last_station]
                        trkpt = SubElement(trkseg, 'trkpt')
                        trkpt.set('lat', str(station['lat']))
                        trkpt.set('lon', str(station['lon']))
                        ele = SubElement(trkpt, 'ele')
                        ele.text = '0'

        # Speichern
        xml_str = minidom.parseString(tostring(gpx)).toprettyxml(indent="  ")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(xml_str)

        print(f"GPX gespeichert: {output_path}")

    def _consolidate_same_line_segments(self, route: Dict) -> List[Tuple[str, str, str]]:
        """Fasst aufeinanderfolgende Segmente auf der gleichen Linie zusammen."""
        if not route.get('fahrten'):
            return []
        
        consolidated = []
        current_von = route['fahrten'][0]['von']
        current_linie = route['fahrten'][0]['linie']
        
        for fahrt in route['fahrten']:
            if fahrt['linie'] == current_linie:
                continue
            else:
                consolidated.append((current_von, fahrt['von'], current_linie))
                current_von = fahrt['von']
                current_linie = fahrt['linie']
        
        if route['fahrten']:
            consolidated.append((current_von, route['fahrten'][-1]['nach'], current_linie))
        
        return consolidated

    def _get_segment_stations(self, linie, von_id: str, nach_id: str) -> List[str]:
        """Gibt alle Stationen auf einer Linie zwischen von und nach (inkl. Start/Ende) in Reihenfolge."""
        if not hasattr(linie, 'stationen'):
            return [von_id, nach_id]
        
        try:
            von_idx = linie.stationen.index(von_id)
            nach_idx = linie.stationen.index(nach_id)
            
            if von_idx < nach_idx:
                return linie.stationen[von_idx:nach_idx + 1]
            else:
                return linie.stationen[von_idx:nach_idx - 1:-1]  # umgekehrt
        except ValueError:
            return [von_id, nach_id]

    def _find_linie_for_segment(self, von: str, nach: str, route: Dict) -> Optional[str]:
        """Findet die Linien-ID für ein Segment."""
        for fahrt in route.get('fahrten', []):
            if fahrt['von'] == von and fahrt['nach'] == nach:
                return fahrt['linie']
        return None


# HTMLMapCreator entfernt - nur KML/GPX Export


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Erstellt KML/GPX Kartenvisualisierungen")
    parser.add_argument("--input", required=True, help="Eingabe-JSON mit Routen")
    parser.add_argument("--output-dir", default="output", help="Ausgabeverzeichnis")

    args = parser.parse_args()

    # Lade Routen
    with open(args.input, 'r', encoding='utf-8') as f:
        data = json.load(f)

    routen = data.get('routen', [])

    # Stationen und Linien aus dem Test-Graph laden
    from routing import erstelle_test_graph
    graph = erstelle_test_graph()
    stationen = {}
    for sid, station in graph.stationen.items():
        stationen[sid] = {
            'name': station.name,
            'lat': station.lat,
            'lon': station.lon,
        }
    # Linien für Geometrie
    graph_linien = graph.linien

    # Ausgabeverzeichnis erstellen
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    # KML
    kml_creator = KMLCreator(routen, stationen, graph_linien)
    kml_creator.create_kml(str(output_dir / "routen.kml"))

    # GPX
    gpx_creator = GPXCreator(routen, stationen, graph_linien)
    gpx_creator.create_gpx(str(output_dir / "routen.gpx"))

    print(f"\nKML und GPX in {output_dir} gespeichert!")


if __name__ == "__main__":
    main()
