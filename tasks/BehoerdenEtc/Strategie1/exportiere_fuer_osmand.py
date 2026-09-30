"""
Exportiert die gesammelten Daten in GPX- und KML-Format für OSMAnd
"""

import json
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "daten"

def load_data():
    """Alle gesammelten Daten laden"""
    with open(DATA_DIR / "einrichtungen_gesamt.json", encoding="utf-8") as f:
        behoerden_polizei = json.load(f)
    
    with open(DATA_DIR / "botschaften.json", encoding="utf-8") as f:
        botschaften = json.load(f)
    
    return behoerden_polizei + botschaften

def create_gpx(eintraege, output_path):
    """GPX-Datei erstellen"""
    gpx = Element('gpx')
    gpx.set('version', '1.1')
    gpx.set('creator', 'GeoStructuresBot')
    gpx.set('xmlns', 'http://www.topografix.com/GPX/1/1')
    
    for eintrag in eintraege:
        wpt = SubElement(gpx, 'wpt')
        wpt.set('lat', str(eintrag['lat']))
        wpt.set('lon', str(eintrag['lon']))
        
        name = SubElement(wpt, 'name')
        name.text = eintrag['name']
        
        desc = SubElement(wpt, 'desc')
        desc.text = f"{eintrag['kategorie']} - {eintrag['quelle']}"
        
        # Symbol basierend auf Kategorie
        sym = SubElement(wpt, 'sym')
        if eintrag['kategorie'] == 'Polizei':
            sym.text = 'Police'
        elif eintrag['kategorie'] == 'Botschaft':
            sym.text = 'Embassy'
        elif eintrag['kategorie'] == 'Konsulat':
            sym.text = 'Embassy'
        else:
            sym.text = 'City'
    
    # XML formatieren
    xml_str = tostring(gpx, encoding='unicode')
    dom = minidom.parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent='  ')
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(pretty_xml)
    
    print(f"GPX-Datei erstellt: {output_path}")

def create_kml(eintraege, output_path):
    """KML-Datei erstellen"""
    kml = Element('kml')
    kml.set('xmlns', 'http://www.opengis.net/kml/2.2')
    
    document = SubElement(kml, 'Document')
    
    name = SubElement(document, 'name')
    name.text = 'Wien - Behörden, Polizei & Botschaften'
    
    # Stile für Kategorien
    styles = {
        'Behörde': ('ff0000ff', 'http://maps.google.com/mapfiles/kml/pushpin/blue-pushpin.png'),
        'Polizei': ('ff0000ff', 'http://maps.google.com/mapfiles/kml/pushpin/red-pushpin.png'),
        'Botschaft': ('ff00ff00', 'http://maps.google.com/mapfiles/kml/pushpin/grn-pushpin.png'),
        'Konsulat': ('ff00a5ff', 'http://maps.google.com/mapfiles/kml/pushpin/ylw-pushpin.png'),
    }
    
    for kategorie, (color, icon) in styles.items():
        style = SubElement(document, 'Style')
        style.set('id', kategorie)
        
        icon_style = SubElement(style, 'IconStyle')
        color_elem = SubElement(icon_style, 'color')
        color_elem.text = color
        
        icon_elem = SubElement(icon_style, 'Icon')
        href = SubElement(icon_elem, 'href')
        href.text = icon
    
    # Placemarks erstellen
    for eintrag in eintraege:
        placemark = SubElement(document, 'Placemark')
        
        name = SubElement(placemark, 'name')
        name.text = eintrag['name']
        
        description = SubElement(placemark, 'description')
        description.text = f"Kategorie: {eintrag['kategorie']}<br>Quelle: {eintrag['quelle']}"
        
        style_url = SubElement(placemark, 'styleUrl')
        style_url.text = f"#{eintrag['kategorie']}"
        
        point = SubElement(placemark, 'Point')
        coordinates = SubElement(point, 'coordinates')
        coordinates.text = f"{eintrag['lon']},{eintrag['lat']},0"
    
    # XML formatieren
    xml_str = tostring(kml, encoding='unicode')
    dom = minidom.parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent='  ')
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(pretty_xml)
    
    print(f"KML-Datei erstellt: {output_path}")

def main():
    eintraege = load_data()
    print(f"Gesamt: {len(eintraege)} Einrichtungen")
    
    # GPX erstellen
    create_gpx(eintraege, BASE_DIR / "Wien_Behoerden_Polizei_Botschaften.gpx")
    
    # KML erstellen
    create_kml(eintraege, BASE_DIR / "Wien_Behoerden_Polizei_Botschaften.kml")
    
    print("\n=== Export abgeschlossen ===")
    print("Dateien:")
    print(f"  - {BASE_DIR / 'Wien_Behoerden_Polizei_Botschaften.gpx'}")
    print(f"  - {BASE_DIR / 'Wien_Behoerden_Polizei_Botschaften.kml'}")
    print("\nImport in OSMAnd:")
    print("  1. Datei auf das Gerät übertragen")
    print("  2. OSMAnd öffnen")
    print("  3. Datei tippen oder über 'Karten & Ressourcen' importieren")

if __name__ == "__main__":
    main()
