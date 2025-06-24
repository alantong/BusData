import requests
import zipfile
import os
import geopandas as gpd
import fiona
import re
import json
import folium
import shutil

#gmb_url = "https://static.csdi.gov.hk/csdi-webpage/download/80875a417ab05918b645c9ff69a2fb74/fgdb"
bus_url = "https://static.csdi.gov.hk/csdi-webpage/download/7faa97a82780505c9673c4ba128fbfed/fgdb"
output_zip = "FGDB/BusRoute_FGDB.zip"
extract_dir = "FGDB/fgdb_extracted"

outputPath = "FGDB/BUS/Map"
if os.path.exists(outputPath) == False:
    shutil.rmtree(outputPath)
os.makedirs(outputPath, exist_ok=True)

# Download the file
print("Downloading BUS FGDB zip...")
response = requests.get(bus_url, stream=True)
response.raise_for_status()
with open(output_zip, "wb") as f:
    for chunk in response.iter_content(chunk_size=8192):
        f.write(chunk)
print(f"Downloaded to {output_zip}")

# Extract the zip file
print("Extracting...")
with zipfile.ZipFile(output_zip, 'r') as zip_ref:
    zip_ref.extractall(extract_dir)
print(f"Extracted to {extract_dir}")

gdb_path = "FGDB/fgdb_extracted/FB_ROUTE.gdb"  # path to the .gdb folder

# List all layers in the geodatabase
layers = fiona.listlayers(gdb_path)
print("Available layers:", layers)

# Read a specific layer (replace 'LayerName' with an actual layer name from the list)
gdf = gpd.read_file(gdb_path, layer=layers[0])


#print(gdf.head())

gdf.to_crs(epsg=4326, inplace=True)
gdf['geometry'] = gdf['geometry'].simplify(0.00005)
data = gdf.to_geo_dict(drop_id=True)

# gdf.to_file("FGDB/output.geojson", driver="GeoJSON")


for feature in data["features"]:
    properties = feature["properties"]
    
    with open("FGDB/BUS/" + str(properties["ROUTE_ID"]) + "-" + str(properties["ROUTE_SEQ"]) + ".json", "w", encoding='utf-8') as f:
        f.write(
            re.sub(
                r"([0-9]+\.[0-9]{5})[0-9]+",
                r"\1",
                json.dumps({
                    "features": [feature],
                    "type": "FeatureCollection"
                },
                    ensure_ascii=False,
                    separators=(",", ":")
                )
            )
        )
    
    key = str(properties["ROUTE_ID"]) + "-" + str(properties["ROUTE_SEQ"]) + "-" + \
                str(properties["COMPANY_CODE"]) + "-" + \
                str(properties["ROUTE_NAMEE"]) + "-" + \
                         str(properties["ST_STOP_NAMEC"]) + "-" + \
                         str(properties["ED_STOP_NAMEC"]) 
                      
    key = key.replace('/<br>', ' ')


    map = folium.Map(location=[22.34685599159843, 114.10950470085098], zoom_start=11)
    folium.GeoJson(feature).add_to(map)
    map.save(f'{outputPath}/{key}.html')




