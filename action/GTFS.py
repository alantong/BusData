import csv
import requests
import os 
import re

gtfs_url = "https://static.data.gov.hk/td/pt-headway-tc/gtfs.zip"
output_zip = "gtfs/gtfs.zip"


frequencies = {}
trips = {}
route_groups = {}

def download_gtfs():

    # delete the existing gtfs directory if it exists
    if os.path.exists('gtfs'):  
        import shutil
        shutil.rmtree('gtfs')
    os.makedirs('gtfs')
    
    if os.path.exists(output_zip):
        os.remove(output_zip)        

    # Download the file
    print(f"Downloading GTFS zip...")
    response = requests.get(gtfs_url, stream=True)
    response.raise_for_status()
    with open(output_zip, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"Downloaded to {output_zip}")



    # Unzip the file
    import zipfile      
    with zipfile.ZipFile(output_zip, 'r') as zip_ref:
        zip_ref.extractall('gtfs')  

def extract_gtfs_frequency():
    # build a dictionary from gtfs/frequencies.txt
    print(f"Extracting GTFS frequencies...")
    with open('gtfs/frequencies.txt', encoding="utf8") as csvfile:   
        reader = csv.reader(csvfile)
        headers = next(reader, None)
        for [trip_id, _start_time, end_time, headway_secs] in reader:
            # spilt the trip_id into route_id, route_seq, service_id

            trip_id_parts = trip_id.split('-')
            if len(trip_id_parts) < 4:  # Ensure there are enough parts to unpack
                print(f"Invalid trip_id format: {trip_id}")
                continue    

            route_id = trip_id_parts[0] # e.g. 1000573
            route_seq = trip_id_parts[1]  # e.g. 2
            service_id = trip_id_parts[2]  # e.g. 480    
            key = f"{route_id}-{route_seq}"
            if key not in frequencies:
                frequencies[key] = {}
            if service_id not in frequencies[key]:
                frequencies[key][service_id] = []
            combined_data = str(_start_time) + '|' + str(end_time) + '|' + str(headway_secs)
            frequencies[key][service_id].append(combined_data)
    # Print the frequencies dictionary
    #print(f"{frequencies["1000573-1"]}")

def get_gtfs_frequencies(route_id):
    return frequencies.get(route_id, {})


def extract_gtfs_trips():
    # build a dictionary from gtfs/trips.txt
    with open('gtfs/trips.txt', encoding="utf8") as csvfile:   
        reader = csv.reader(csvfile)
        headers = next(reader, None)
        for [route_id, service_id, trip_id] in reader:
            trip_id_parts = trip_id.split('-')
            if len(trip_id_parts) < 4:  # Ensure there are enough parts to unpack
                print(f"Invalid trip_id format: {trip_id}")
                continue    

            route_id = trip_id_parts[0] # e.g. 1000573
            route_seq = trip_id_parts[1]  # e.g. 2
            service_id = trip_id_parts[2]  # e.g. 480
            time = trip_id_parts[3]
            key = f"{route_id}-{route_seq}"

            if key not in trips:
                trips[key] = {}
            if service_id not in trips[key]:
                trips[key][service_id] = []
            trips[key][service_id].append(time)
    # Print the trips dictionary
    #print(f"{trips['1723-1']}")
    return trips

def get_gtfs_trips(route_id):
    return trips.get(route_id, {})


def get_freq(gtfsRouteKey):
    freq = []
    if gtfsRouteKey is not None:
        for g in gtfsRouteKey:
            f = get_gtfs_frequencies(g[1]+ '-' + g[2])
            if f != {}:
                freq.append(f)
            else:
                freq.append(get_gtfs_trips(g[1]+ '-' + g[2]))  
    return freq


def extract_fare_attributes():
    print(f"Extracting GTFS fare attributes...")
    raw_text = open('gtfs/fare_attributes.txt', encoding="utf8").read()
    rows = list(csv.reader(raw_text.splitlines()))
    if not rows:
        return {}, {}

    header = rows[0]
    data_rows = rows[1:] if header and header[0].strip().lower() == "fare_id" else rows


    for parts in data_rows:
        if len(parts) < 3:
            continue

        fare_id = parts[0].strip()
        if not fare_id or fare_id.strip().lower() == "fare_id":
            continue

        try:
            price = float(parts[1])
        except ValueError:
            continue

        route_id = "-".join(fare_id.split("-")[:2])
        match = re.search(r"-(\d+)-(\d+)$", fare_id)
        if not match:
            continue

        orig = int(match.group(1))
        dest = int(match.group(2))
        if orig >= dest:
            continue

        #get the agency_id from the fare_id, which is the last part after the last '-'  
        agency_id = parts[5]
        
        route_groups.setdefault(agency_id + '-' + route_id, []).append((orig, dest, price))


def summarize_route_fares(pairs):
    if not pairs:
        return []

    pair_price = {(o, d): p for o, d, p in pairs}
    min_stop = min(o for o, d, _ in pairs)
    max_stop = max(d for o, d, _ in pairs)
    full_price = pair_price.get((min_stop, max_stop), max(p for _, _, p in pairs))

    full_section = {
        "range": [min_stop, max_stop],
        "price": full_price,
    }

    sections = []
    
    # Build a map of (start, price) -> [ends]
    fare_map = {}
    for (start, end), price in pair_price.items():
        key = (start, price)
        if key not in fare_map:
            fare_map[key] = []
        fare_map[key].append(end)
    
    # For each (start, price) combination, create a range [start, max_end]
    for (start, price), ends in fare_map.items():
        max_end = max(ends)
        sections.append({
            "range": [start, max_end],
            "price": price,
        })

    # Consolidate ranges with same end and price
    consolidated = {}
    for section in sections:
        end, price = section["range"][1], section["price"]
        key = (end, price)
        if key not in consolidated:
            consolidated[key] = []
        consolidated[key].append(section["range"][0])
    
    # Rebuild sections with consolidated ranges
    unique_sections = []
    for (end, price), starts in consolidated.items():
        min_start = min(starts)
        # Skip if this matches the full_section
        if min_start == full_section["range"][0] and end == full_section["range"][1] and price == full_section["price"]:
            continue
        unique_sections.append({
            "range": [min_start, end],
            "price": price,
        })

    unique_sections.sort(key=lambda x: (x["range"][0], x["range"][1]))
    return [full_section] + unique_sections

def get_route_fares(gtfsRouteKey):
    sectionfare = []
    for k in gtfsRouteKey:
        #join all elements in k with "-" to form the route key, e.g. "KMB-1223-1"
        route_key = "-".join(str(x) for x in k)
        route_fares = route_groups.get(route_key, [])
        if route_fares:
            sectionfare.append(summarize_route_fares(route_fares))
    return sectionfare

def main():
    download_gtfs()
    extract_gtfs_frequency()
    extract_fare_attributes()
    #print(summarize_route_fares(route_groups.get("KMB-1223-1", [])))
    #print(summarize_route_fares(route_groups.get("GMB-2005683-1", [])))
    #print(get_route_fares([['GMB','2005683', '1']]))
if __name__=="__main__":
    main()