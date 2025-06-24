
import folium
import json

m_ori = folium.Map(location=[22.3, 114.2], zoom_start=12)


with open('FGDB/1743-1_ori.json', encoding='utf-8') as f:
    geojson_data1 = json.load(f)

folium.GeoJson(geojson_data1).add_to(m_ori)
m_ori.save('FGDB/map/1743-1_ori.html')

simplifed = '1416-1'

m_new = folium.Map(location=[22.3, 114.2], zoom_start=12)

with open(f'FGDB/{simplifed}.json', encoding='utf-8') as f:
    geojson_data2 = json.load(f)

folium.GeoJson(geojson_data2).add_to(m_new)
m_new.save(f'FGDB/map/{simplifed}.html')

import webbrowser

webbrowser.open(f'file:///C:/Users/AlanTong/AndroidStudioProjects/BusData/FGDB/map/{simplifed}.html')
