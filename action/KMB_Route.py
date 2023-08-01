import requests
import json
import os
import logging
import asyncio
import httpx

from requests.exceptions import HTTPError

allRouteBaseUrl = 'https://data.etabus.gov.hk/v1/transport/kmb/route'
stopListBaseUrl = 'https://data.etabus.gov.hk/v1/transport/kmb/route-stop/'
allStopBaseUrl = 'https://data.etabus.gov.hk/v1/transport/kmb/stop'

kmb_route_json = 'KMB_Route'
kmb_stop_json = 'KMB_Stop'

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


async def getStopList(client, route) :
    bound = 'outbound' if(route['bound'] == 'O')  else 'inbound'
    stopListUrl = stopListBaseUrl + route['route'] + '/' + bound + '/' + route['service_type'] 

    stopListResponse = await client.get(stopListUrl)
    stopListObject = stopListResponse.json()
    stopList = []
    for s in stopListObject['data']:
        stopList.append(s['stop'])
    r = route.copy()
    r['co'] = "KMB"
    r['stops'] = stopList
    return r


async def main():
    
    logDir = os.path.join (os.getcwd(), log_dir)
    
    if os.path.exists(logDir) == False: 
        os.mkdir(logDir)

    logFile = os.path.join(logDir, 'kmb.log')
        
    logging.basicConfig(filename=logFile, filemode='w', format='%(asctime)s | %(name)s - %(levelname)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S')

    # Creating an object
    logger = logging.getLogger()

    # Setting the threshold of logger to DEBUG
    logger.setLevel(logging.INFO)

    logging.info("Start getting KMB route")

    try:
        
        outputDir = os.path.join(os.getcwd(), output_dir)
        if os.path.exists(outputDir) == False:
            os.mkdir(outputDir)

        routeResponse = requests.get(allRouteBaseUrl)
        routeResponse.raise_for_status()
        # access Json content
        routeObject = routeResponse.json()
        
        routeList = routeObject['data']

        newRouteList = []
        async with httpx.AsyncClient() as client:
            tasks = []
            for r in routeList:
                tasks.append(getStopList(client, r))
            
            newRouteList += await asyncio.gather(*tasks)


        writeToJson(newRouteList, kmb_route_json)

        allStopResponse = requests.get(allStopBaseUrl)
        allStopResponse.raise_for_status()
        # access Json content
        allStopObject = allStopResponse.json()
        
        allStopList = allStopObject['data']
        for s in allStopList:
            s['co'] = 'KMB'

        writeToJson(allStopList, kmb_stop_json)

        logging.info("Finish getting KMB route")
        
    except HTTPError as http_err:
        print(f'HTTP error occurred: {http_err}')
        logging.error(f'HTTP error occurred: {http_err}')
    except Exception as err:
        print(f'Other error occurred: {err}')
        logging.error(f'Other error occurred: {err}')

asyncio.run(main())