import os
import logging  
import requests 
from requests.exceptions import HTTPError
import json
import math

log_dir = 'log'
output_dir = 'output'

GeoJSONBusUrl = 'https://static.data.gov.hk/td/routes-fares-geojson/JSON_BUS.json'
GeoJSONGMBUrl = 'https://static.data.gov.hk/td/routes-fares-geojson/JSON_GMB.json'

logDir = os.path.join (os.getcwd(), log_dir)

if os.path.exists(logDir) == False: 
    os.mkdir(logDir)

# GeoJSON logger
geojson_logger = logging.getLogger('geojson')
geojson_handler = logging.FileHandler(os.path.join(log_dir, 'geojson.log'), encoding='utf-8', mode='w')
geojson_handler.setFormatter(logging.Formatter('%(asctime)s | %(name)s - %(levelname)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S'))
geojson_logger.addHandler(geojson_handler)
geojson_logger.setLevel(logging.INFO)


outputDir = os.path.join(os.getcwd(), output_dir)
if os.path.exists(outputDir) == False:
    os.mkdir(outputDir)



def getGeoJsonRoutes(type="BUS"):  
    match type:
        case "BUS": 
            url = GeoJSONBusUrl
        case "GMB":
            url = GeoJSONGMBUrl
         
    response = requests.get(url, timeout=30.0)
    response.raise_for_status()

    # access Json content
    geojsonObject = json.loads(response.content.decode('utf-8-sig'))   

    print(f"GeoJSON {type} data fetched successfully.")
    geojson_logger.info(f"GeoJSON {type} data fetched successfully.")

    # Adjust this if your JSON structure is nested
    features =  geojsonObject.get('features', [])

 
    results = {}

    #group all features by routeId
    for feature in features:
        properties = feature.get('properties', {})
        routeId = properties.get('routeId')
        routeSeq = properties.get('routeSeq')
        
        if routeId is not None and routeSeq is not None:
            key = (routeId, routeSeq)
            if key not in results:
                results[key] = []
            results[key].append(feature)

    print(f"Total {len(results)} routes found.")
    geojson_logger.info(f"Total {len(results)} routes found.")


    # sort the result by routeNameE, then by companyCode    
    results = dict(sorted(results.items(), key=lambda item: 
        (item[1][0]['properties']['routeNameE'], item[1][0]['properties']['companyCode'])))
    
    
    #routes = results

    outputFile = os.path.join(outputDir, f"GeoJSON_{type}.txt")
    if os.path.exists(outputFile):
        os.remove(outputFile)

    # print the count of features for each routeId
    for key, features in results.items():      
        with open(outputFile, 'a', encoding='utf-8') as f:
            f.write(
                f"{key}|"
                f"{features[0]['properties']['companyCode']}|"
                f"#{features[0]['properties']['routeNameE']}|"
                f"{features[0]['properties']['locStartNameC']} - {features[0]['properties']['locEndNameC']}|"
                f"Stops: {len(features)}|"
                f"{features[0]['properties']['stopNameC']} - "
                f"{features[-1]['properties']['stopNameC']}|"
                f"{features[0]['properties']['serviceMode']}|"
                f"{features[0]['properties']['specialType']}\n"
            ) 

    """ if( features[0]['properties']['routeNameE'] == '930'):
            print(
                f"---- Route ID: {routeId} ----"
                f"{features[0]['properties']['locStartNameC']} - {features[0]['properties']['locEndNameC']} "
                )      
            for f in features:
                print(f"--->: {f['properties']['stopNameC']} ") """

    return results

# testCo = getFirstStopCoordinates(1001, 1)
# print(f"{testCo[0]} {testCo[1]}") 
# testCo = getLastStopCoordinates(1001, 1)
# print(f"{testCo[0]} {testCo[1]}") 

# testCo = getFirstStopCoordinates(1001, 2)
# print(f"{testCo[0]} {testCo[1]}") 
# testCo = getLastStopCoordinates(1001, 2)
# print(f"{testCo[0]} {testCo[1]}") 

def getFirstStopCoordinates(routeId, routeSeq, routes):
    #print(f"Getting first stop coordinates for routeId: {routeId}, routeSeq: {routeSeq}")
    for key, features in routes.items():
        #sort features by StopSeq   
        #features.sort(key=lambda x: x['properties']['stopSeq'])
        if (key[0] == routeId and key[1] == routeSeq):
            #geojson_logger.info({features[0]['properties']['stopNameC']})
            return features[0]['geometry']['coordinates'][::-1]
    return None

def getLastStopCoordinates(routeId, routeSeq, routes):
    #print(f"Getting last stop coordinates for routeId: {routeId}, routeSeq: {routeSeq}")
    for key, features in routes.items():
        #sort features by StopSeq   
        #features.sort(key=lambda x: x['properties']['stopSeq'])
        if (key[0] == routeId and key[1] == routeSeq):
            #geojson_logger.info({features[-1]['properties']['stopNameC']})
            return features[-1]['geometry']['coordinates'][::-1]
    return None

# r = getRouteKeyList('CTB', '97')
# print(f"Route Key List: {r}")
def getRouteKeyList(companyCode, routeNo, routes):
    #print(f"Getting route key list for {companyCode} {routeNo}")
    routeKeyList = []
    for (rid, routeSeq), features in routes.items():
        if (companyCode in features[0]['properties']['companyCode'] and
            features[0]['properties']['routeNameE'] == routeNo):
            gtfsCompanyCode = features[0]['properties']['companyCode']
            routeKeyList.append([gtfsCompanyCode, rid, routeSeq])
    return routeKeyList


def haversine(coord1, coord2):
    """
    Calculate the great-circle distance between two points 
    on the Earth specified in decimal degrees of latitude and longitude.
    Returns distance in meters.
    """
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    
    # Convert from string to float
    lat1 = float(lat1)
    lon1 = float(lon1)
    lat2 = float(lat2)
    lon2 = float(lon2)

    # Convert decimal degrees to radians 
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula 
    dlat = lat2 - lat1 
    dlon = lon2 - lon1 
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a)) 
    r = 6371  # Radius of Earth in kilometers
    return c * r * 1000  # Return distance in meters

# Example usage:
# coordA = [latitude1, longitude1]
# coordB = [latitude2, longitude2]
# distance_km = haversine(coordA, coordB)
# print(f"Distance: {distance_km:.2f} m")

# start = getFirstStopCoordinates(1001, 1)
# end = getLastStopCoordinates(1001, 1)
# print(f"Start Coordinates: {start}")
# print(f"End Coordinates: {end}")
# print(f"distance: {haversine(start, end):.2f} m")


def matchRouteId(companyCode, routeNo, startStop, endStop, routes):
    """
    Match the company code and route number to find the routeId.
    """
    candidateList = getRouteKeyList(companyCode, routeNo, routes)
    #if candidateList is None or len(candidateList) == 0:
    #    print(f"No route found for {companyCode} {routeNo}")
    #    return None     
    resultList = []

    #print(candidateList)

    #check if candidateList is not None and has elements
    if candidateList is None or len(candidateList) == 0:
        #print(f"No route found for {companyCode} {routeNo}")
        return []
    if len(candidateList) == 1:
        #print(f"Only 1 candidate: {routeNo} | {candidateList}")         
        return [candidateList[0]]

    for c in candidateList:    
        if c is None or len(c) < 3:
            continue    

        firstStop = None
        lastStop = None

        firstStop = getFirstStopCoordinates(c[1], c[2], routes)
        lastStop = getLastStopCoordinates(c[1], c[2], routes)

        #print(f"First Stop: {firstStop}, Last Stop: {lastStop}")

        startStopsDistance = haversine(firstStop, startStop)
        lastStopDistance = haversine(lastStop, endStop) 


        match companyCode:
            case "CTB":
                condition = startStopsDistance < 250 or lastStopDistance < 250
            case _:
                condition = startStopsDistance < 250 and lastStopDistance < 250            

        if condition:
            """
            geojson_logger.info(f"{routeNo} {c}:"
                                f"{routes[(c[1], c[2])][0]['properties']['locStartNameC']} -"
                                f"{routes[(c[1], c[2])][0]['properties']['locEndNameC']}"
                            )
            """
            resultList.append([c[0], c[1], c[2]])

    
    if len(resultList) == 0:
        return candidateList
    return resultList 



