import csv
import requests
import os 

gtfs_url = "https://static.data.gov.hk/td/pt-headway-tc/gtfs.zip"
output_zip = "gtfs/gtfs.zip"


frequencies = {}
trips = {}

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
            frequencies[key][service_id].append([_start_time, end_time, headway_secs])
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
# def main():
#     download_gtfs()
#     extract_gtfs_frequency()

# if __name__=="__main__":
#     main()