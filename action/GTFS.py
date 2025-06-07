import zipfile
import requests
from os import path
import csv
import json
import os

if os.path.exists('log/gtfs.log'):
    os.remove('log/gtfs.log')

gtfs_files = ['gtfs-tc', 'gtfs-en']

for file in gtfs_files:
    if not path.isfile(file + '.zip'):
        lang = file[5:7] # Extract 'tc' or 'en'
        r = requests.get(f'https://static.data.gov.hk/td/pt-headway-{lang}/gtfs.zip')
        open(file + '.zip', 'wb').write(r.content)
    # Extract the GTFS data from the zip files
    with zipfile.ZipFile(file + '.zip',"r") as zip_ref:
        zip_ref.extractall(file.replace('-', '/'))

routeList = {}

with open('gtfs/en/routes.txt', encoding="utf8") as csvfile:
    reader = csv.reader(csvfile)
    headers = next(reader, None)

    for [route_id, agency_id, route_short_name, route_long_name, route_type, route_url] in reader:
        routeList[route_id] = {
            'co': agency_id.replace('LWB', 'KMB'),  #.split('+'),
            'route': route_short_name,
            'orig': {
                'en': route_long_name.split(' - ')[0]
            },
            'dest': {
                'en': route_long_name.split(' - ')[1]
            },
            #'freq': {},
    }

with open('gtfs/tc/routes.txt', encoding="utf8") as csvfile:
    reader = csv.reader(csvfile)
    headers = next(reader, None)

    for [route_id, agency_id, route_short_name, route_long_name, route_type, route_url] in reader:
        routeList[route_id]['orig']['zh'] = route_long_name.split(' - ')[0]
        routeList[route_id]['dest']['zh'] =  route_long_name.split(' - ')[1]

    

""" with open('gtfs/frequencies.txt') as csvfile:
    reader = csv.reader(csvfile)
    headers = next(reader, None)
    for [trip_id, _start_time, end_time, headway_secs] in reader:
        [route_id, bound, calendar, start_time] = trip_id.split('-')
        if bound not in routeList[route_id]['freq']:
            routeList[route_id]['freq'][bound] = {}
        if calendar not in routeList[route_id]['freq'][bound]:
            routeList[route_id]['freq'][bound][calendar] = []
        routeList[route_id]['freq'][bound][calendar].append([_start_time, end_time, headway_secs]) 
 """


with open('output/gtfs.json', 'w', encoding="utf8") as f:
    f.write(json.dumps({'routeList': routeList,}, ensure_ascii=False, indent=2))

print("GTFS data has been written to output/gtfs.json")


#with open('output/gtfs.json', encoding='utf8') as f:
#    data = json.load(f)

# Now you can access the routeList dictionary:
#gtfsRouteList = data['routeList']
#print(f"Total GTFS routes: {len(gtfsRouteList)}")

for file in gtfs_files:
    # Remove the extracted files
    os.remove(file + '.zip')   

# Function to remove all special characters from a string except spaces
def strip(s):       
    if s is not None:
        return ''.join(e for e in s if e.isalnum()).lower()
    return s

# find GTFS route Id by co, route, orig, and dest
def findGtfsRoute(co=None, route=None, orig=None, dest=None): 
    results = []
    target_id = None
    for route_id, details in routeList.items():
        if (co is None or co in details['co']) and \
            (route is None or details['route'] == route):
            results.append([route_id, details])
    if len(results) == 0:
        target_id = None
    elif len(results) == 1:
        target_id = results[0][0]    
    else:
        for route_id, details in results:
            origMatched = strip(details['orig']['en']) == strip(orig) #or strip(orig) in strip(details['orig']['en'])
            destMatched = strip(details['dest']['en']) == strip(dest) #or strip(dest) in strip(details['dest']['en'])
            xOrigMatched = strip(details['orig']['en']) == strip(dest) #or strip(dest) in strip(details['orig']['en'])
            xDestMatched = strip(details['dest']['en']) == strip(orig) #or strip(orig) in strip(details['dest']['en']) 

            if (
                ((orig is None or origMatched ) and (dest is None or destMatched)) or \
                ((dest is None or xOrigMatched) and (orig is None or xDestMatched)) \
                ):
                target_id = route_id
         
    if target_id is None:
        with open('log/GTFS.log', 'a', encoding='utf8') as f:
            f.write(f"!!!! No GTFS route Found : co={co}, route={route}, orig={orig}, dest={dest} \n" )
    else:
        with open('log/GTFS.log', 'a', encoding='utf8') as f:
            f.write(f"GTFS route found: [{target_id}] co={co}, route={route}, orig={orig}, dest={dest}\n")
            #{details['co']} {details['route']} from {details['orig']['en']} to {details['dest']['en']}\n")
    
    return target_id  


#findGtfsRoute(co='KMB', route='102', orig='shau kei wan', dest='mei foo')
#findGtfsRoute(co='KMB', orig='LAM TIN (KWONG TIN ESTATE)')

