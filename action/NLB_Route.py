import requests
import json
import os
import logging
import asyncio  
import httpx
import operator

from requests.exceptions import HTTPError


allRouteBaseUrl = 'https://rt.data.gov.hk/v2/transport/nlb/route.php?action=list'
stopListBaseUrl = 'https://rt.data.gov.hk/v2/transport/nlb/stop.php?action=list&routeId='


nlb_route_json = 'NLB_Route'
nlb_stop_json = 'NLB_Stop'

log_dir = 'log'
output_dir = 'output'

def writeToJson(content, filename) :
    outputDir = os.path.join(os.getcwd(), output_dir)
    if os.path.exists(outputDir) == False:
        os.mkdir(outputDir)

    outputJson = os.path.join (outputDir, filename + ".json")

    if os.path.exists(outputJson):
            os.remove(outputJson)

    with open(outputJson, 'w', encoding='UTF-8') as write_file:
        json.dump(content, write_file, indent=4, ensure_ascii=False)


nlbStops = list()

async def getStopList(client, route):
    stopList = []
    stopListUrl = f"{stopListBaseUrl}{route['routeId']}"
    newRoute = route.copy()

    stopListResponse = await client.get(stopListUrl)
    stopListObject = stopListResponse.json()
    
    if(len(stopListObject['stops']) > 0) :
        for s in stopListObject['stops']:
            stopList.append(s['stopId'])
            ns = dict()
            ns['co'] = 'NLB'
            ns['stop'] = s['stopId']
            ns['name_en'] = s['stopName_e'] + ", " + s['stopLocation_e']
            ns['name_tc'] = s['stopName_c'] + ", " + s['stopLocation_c']
            ns['name_sc'] = s['stopName_s'] + ", " + s['stopLocation_s']
            ns['lat'] = s['latitude']
            ns['long'] = s['longitude']
            nlbStops.append(ns)
        newRoute['stops'] = stopList
        return newRoute
    else :
        return []


async def main():

    logDir = os.path.join (os.getcwd(), log_dir)
    
    if os.path.exists(logDir) == False: 
        os.mkdir(logDir)

    logFile = os.path.join(logDir, 'nlb.log')

    logging.basicConfig(filename=logFile, filemode='w', format='%(asctime)s | %(name)s - %(levelname)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S')

    # Creating an object
    logger = logging.getLogger()

    # Setting the threshold of logger to DEBUG
    logger.setLevel(logging.INFO)

    logging.info("Start getting NLB route")

    try:

        routeResponse = requests.get(allRouteBaseUrl)
        routeResponse.raise_for_status()

        routeObject = routeResponse.json()
        
        routeList = routeObject['routes']

        async with httpx.AsyncClient() as client:
            tasks = []
            nlbList = list()
            for r in routeList:
                nr = dict()
                nr['co'] = 'NLB'
                nr['routeId'] = r['routeId']
                nr['route'] = r['routeNo']
                nr['origTc'] = r['routeName_c'].split('>')[0].strip()
                nr['destTc'] = r['routeName_c'].split('>')[1].strip()
                nr['origSc'] = r['routeName_s'].split('>')[0].strip()
                nr['destSc'] = r['routeName_s'].split('>')[1].strip()
                nr['origEn'] = r['routeName_e'].split('>')[0].strip()
                nr['destEn'] = r['routeName_e'].split('>')[1].strip()
                 
                tasks.append(getStopList(client, nr))
            nlbList += await asyncio.gather(*tasks)
        
        nlbList = list(filter(None, nlbList))  

        writeToJson(nlbList, nlb_route_json)
       

        nlbStopList = list({v['stop']:v for v in nlbStops}.values())
        nlbStopList= sorted(nlbStopList, key=lambda x: int(operator.itemgetter("stop")(x))) 

        writeToJson(nlbStopList, nlb_stop_json)

        logging.info("Finish getting NLB route")

    except HTTPError as http_err:
            print(f'HTTP error occurred: {http_err}')
            logging.error(f'HTTP error occurred: {http_err}')
    except Exception as err:
            print(f'Other error occurred: {err}')
            logging.error(f'Other error occurred: {err}')
    
asyncio.run(main())