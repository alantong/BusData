import zipfile
import requests
from os import path
import csv
import json

if not path.isfile('gtfs.zip'):
    r = requests.get('https://static.data.gov.hk/td/pt-headway-tc/gtfs.zip')
    open('gtfs.zip', 'wb').write(r.content)

with zipfile.ZipFile("gtfs.zip","r") as zip_ref:
    zip_ref.extractall("gtfs")

routeList = {}

with open('gtfs/routes.txt', encoding="utf8") as csvfile:
    reader = csv.reader(csvfile)
    headers = next(reader, None)

    for [route_id, agency_id, route_short_name, route_long_name, route_type, route_url] in reader:
        routeList[route_id] = {
            'co': agency_id.replace('LWB', 'KMB').split('+'),
            'route': route_short_name,
            'orig': {
                'zh': route_long_name.split(' - ')[0]
            },
            'dest': {
                'zh': route_long_name.split(' - ')[1]
            },
            'freq': {},
    }


with open('gtfs/frequencies.txt') as csvfile:
    reader = csv.reader(csvfile)
    headers = next(reader, None)
    for [trip_id, _start_time, end_time, headway_secs] in reader:
        [route_id, bound, calendar, start_time] = trip_id.split('-')
        if bound not in routeList[route_id]['freq']:
            routeList[route_id]['freq'][bound] = {}
        if calendar not in routeList[route_id]['freq'][bound]:
            routeList[route_id]['freq'][bound][calendar] = []
        routeList[route_id]['freq'][bound][calendar].append([_start_time, end_time, headway_secs]) 


import json
with open('gtfs.json', 'w', encoding="utf8") as f:
    f.write(json.dumps({'routeList': routeList,}, ensure_ascii=False, indent=2))
