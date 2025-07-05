import requests
import zipfile
import os
import geopandas as gpd
import fiona
import re
import json
import folium
import shutil

def process_fgdb(url, output_zip, extract_dir, outputPath, prefix):
    if os.path.exists(outputPath):
        shutil.rmtree(outputPath)
    os.makedirs(outputPath + "/Map", exist_ok=True)

    # Download the file
    print(f"Downloading {prefix} FGDB zip...")
    response = requests.get(url, stream=True)
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

    # Find the .gdb folder
    gdb_path = None
    for root, dirs, files in os.walk(extract_dir):
        for d in dirs:
            if d.endswith('.gdb'):
                gdb_path = os.path.join(root, d)
                break
        if gdb_path:
            break

    if not gdb_path:
        print(f"No .gdb found in {extract_dir}")
        return

    # List all layers in the geodatabase
    layers = fiona.listlayers(gdb_path)
    print(f"Available layers in {prefix}:", layers)

    # Read the first layer (adjust if needed)
    gdf = gpd.read_file(gdb_path, layer=layers[0])

    gdf.to_crs(epsg=4326, inplace=True)
    if prefix == "BUS":
        gdf['geometry'] = gdf['geometry'].simplify(0.00005)
    data = gdf.to_geo_dict(drop_id=True)

    # sort the features by ROUTE_ID in integer order if possible
    def route_id_key(x):
        try:
            return int(x["properties"]["ROUTE_ID"])
        except Exception:
            return x["properties"]["ROUTE_ID"]
    data["features"].sort(key=route_id_key)

    for feature in data["features"]:
        properties = feature["properties"]

        with open(f"{outputPath}/{properties['ROUTE_ID']}-{properties['ROUTE_SEQ']}.json", "w", encoding='utf-8') as f:
            if feature["geometry"]["type"] == "LineString":
                # Convert LineString to MultiLineString
                print(f"Converting LineString to MultiLineString for {properties['ROUTE_ID']}-{properties['ROUTE_SEQ']}")
                feature["geometry"]["type"] = "MultiLineString"
                feature["geometry"]["coordinates"] = [feature["geometry"]["coordinates"]]
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
        if prefix == "BUS":
            key = "-".join([
                properties["ROUTE_NAMEE"],
                properties["COMPANY_CODE"],
                str(properties["ROUTE_ID"]),
                str(properties["ROUTE_SEQ"]),
                properties["ST_STOP_NAMEC"],
                properties["ED_STOP_NAMEC"]
            ])
        else:  # GMB
            key = "-".join([
                properties["ROUTE_NAME"],
                str(properties["ROUTE_ID"]),
                str(properties["ROUTE_SEQ"]),
                properties["ST_STOP_NAMEC"],
                properties["ED_STOP_NAMEC"]
            ])
        key = key.replace('/<br>', ' ')
        key = key.replace('\t', ' ')
        key = key.replace('/', ' ')

        # Get all coordinates from the geometry
        coords = []
        geom = feature["geometry"]
        if geom["type"] == "MultiLineString":
            for line in geom["coordinates"]:
                coords.extend(line)
        elif geom["type"] == "LineString":
            coords = geom["coordinates"]

        # Extract lat/lon bounds
        lats = [pt[1] for pt in coords]
        lons = [pt[0] for pt in coords]
        bounds = [[min(lats), min(lons)], [max(lats), max(lons)]]

        # Center the map at the midpoint of the bounds
        center = [(bounds[0][0] + bounds[1][0]) / 2, (bounds[0][1] + bounds[1][1]) / 2]
        m = folium.Map(location=center, zoom_start=13)  # zoom_start will be overridden by fit_bounds

        folium.GeoJson(feature).add_to(m)
        m.fit_bounds(bounds)
        m.save(f'{outputPath}/Map/{key}.html')

    os.remove(output_zip)
    shutil.rmtree(extract_dir)

# --- BUS FGDB ---
bus_url = "https://static.csdi.gov.hk/csdi-webpage/download/7faa97a82780505c9673c4ba128fbfed/fgdb"
bus_output_zip = "FGDB/BusRoute_FGDB.zip"
bus_extract_dir = "FGDB/fgdb_extracted_bus"
bus_outputPath = "FGDB/BUS"
process_fgdb(bus_url, bus_output_zip, bus_extract_dir, bus_outputPath, "BUS")

# --- GMB FGDB ---
gmb_url = "https://static.csdi.gov.hk/csdi-webpage/download/80875a417ab05918b645c9ff69a2fb74/fgdb"
gmb_output_zip = "FGDB/GMBRoute_FGDB.zip"
gmb_extract_dir = "FGDB/fgdb_extracted_gmb"
gmb_outputPath = "FGDB/GMB"
process_fgdb(gmb_url, gmb_output_zip, gmb_extract_dir, gmb_outputPath, "GMB")