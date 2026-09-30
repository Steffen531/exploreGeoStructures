"""
Erstellt eine interaktive Karte von Wien mit Behörden, Polizei und Botschaften
"""

import json
from pathlib import Path
import folium
from folium.plugins import MarkerCluster

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "daten"

def load_data():
    """Alle gesammelten Daten laden"""
    # Behörden und Polizei
    with open(DATA_DIR / "einrichtungen_gesamt.json", encoding="utf-8") as f:
        behoerden_polizei = json.load(f)
    
    # Botschaften
    with open(DATA_DIR / "botschaften.json", encoding="utf-8") as f:
        botschaften = json.load(f)
    
    return behoerden_polizei, botschaften

def create_karte(behoerden_polizei, botschaften):
    """Interaktive Karte mit Folium erstellen"""
    print("=== Erstelle Karte ===")
    
    # Kartenmittelpunkt Wien
    wien_center = [48.2082, 16.3738]
    
    # Karte erstellen
    m = folium.Map(
        location=wien_center,
        zoom_start=12,
        tiles="OpenStreetMap"
    )
    
    # MarkerCluster für bessere Performance bei vielen Markern
    cluster_all = MarkerCluster(name="Alle Einrichtungen").add_to(m)
    
    # Farben für Kategorien
    farben = {
        'Behörde': 'blue',
        'Polizei': 'red',
        'Botschaft': 'green',
        'Konsulat': 'orange'
    }
    
    # Behörden und Polizei hinzufügen
    for eintrag in behoerden_polizei:
        farbe = farben.get(eintrag['kategorie'], 'gray')
        popup_text = f"""
        <b>{eintrag['name']}</b><br>
        Kategorie: {eintrag['kategorie']}<br>
        Quelle: {eintrag['quelle']}
        """
        folium.Marker(
            location=[eintrag['lat'], eintrag['lon']],
            popup=folium.Popup(popup_text, max_width=300),
            icon=folium.Icon(color=farbe, icon='info-sign'),
            tooltip=eintrag['name']
        ).add_to(cluster_all)
    
    # Botschaften hinzufügen
    for eintrag in botschaften:
        farbe = farben.get(eintrag['kategorie'], 'gray')
        popup_text = f"""
        <b>{eintrag['name']}</b><br>
        Kategorie: {eintrag['kategorie']}<br>
        Quelle: {eintrag['quelle']}
        """
        folium.Marker(
            location=[eintrag['lat'], eintrag['lon']],
            popup=folium.Popup(popup_text, max_width=300),
            icon=folium.Icon(color=farbe, icon='info-sign'),
            tooltip=eintrag['name']
        ).add_to(cluster_all)
    
    # Legende hinzufügen
    legend_html = """
    <div style="position: fixed; 
                bottom: 50px; left: 50px; width: 180px;
                border:2px solid grey; z-index:9999; font-size:14px;
                background-color:white; padding: 10px;
                border-radius: 5px;">
    <b>Legende</b><br>
    <i class="fa fa-map-marker fa-2x" style="color:blue"></i> Behörde<br>
    <i class="fa fa-map-marker fa-2x" style="color:red"></i> Polizei<br>
    <i class="fa fa-map-marker fa-2x" style="color:green"></i> Botschaft<br>
    <i class="fa fa-map-marker fa-2x" style="color:orange"></i> Konsulat<br>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Layer-Control hinzufügen
    folium.LayerControl().add_to(m)
    
    # Karte speichern
    output_path = BASE_DIR / "Wien_Behoerden_Polizei_Botschaften.html"
    m.save(str(output_path))
    
    print(f"  Karte gespeichert: {output_path}")
    
    # Statistik
    print("\n=== Statistik ===")
    kategorien = {}
    for eintrag in behoerden_polizei + botschaften:
        kategorien[eintrag['kategorie']] = kategorien.get(eintrag['kategorie'], 0) + 1
    
    print(f"Gesamt: {len(behoerden_polizei) + len(botschaften)} Einrichtungen")
    for kat, count in sorted(kategorien.items()):
        print(f"  {kat}: {count}")

def main():
    behoerden_polizei, botschaften = load_data()
    create_karte(behoerden_polizei, botschaften)

if __name__ == "__main__":
    main()
