import requests
import json
import os
import logging
import asyncio 
import time 
import httpx
import traceback

from requests.exceptions import HTTPError

allRouteBaseUrl = 'https://rt.data.gov.hk/v2/transport/citybus/route/ctb/'
stopListBaseUrl = 'https://rt.data.gov.hk/v2/transport/citybus/route-stop/CTB/'
stopInfoBaseUrl = 'https://rt.data.gov.hk/v2/transport/citybus/stop/'

ctb_route_json = 'CTB_Route'
ctb_stop_json = 'CTB_Stop'

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


async def getStopInfo(client, stopId):
    stopInfo = []
    stopInfoUrl = stopInfoBaseUrl + stopId

    stopInfoResponse = await client.get(stopInfoUrl)
    stopInfoObject = stopInfoResponse.json()

    if(len(stopInfoObject['data']) > 0):
        stopInfo = stopInfoObject['data']
        stopInfo['co'] = 'CTB'
    return stopInfo

async def getStopList(client, route, bound):
    stopList = []
    stopListUrl = f"{stopListBaseUrl}{route['route']}/{bound}"
    newRoute = route.copy()
    if(bound == 'inbound') :
        newRoute['orig_tc'], newRoute['dest_tc'] = newRoute['dest_tc'], newRoute['orig_tc']
        newRoute['orig_en'], newRoute['dest_en'] = newRoute['dest_en'], newRoute['orig_en']
        newRoute['orig_sc'], newRoute['dest_sc'] = newRoute['dest_sc'], newRoute['orig_sc']

    stopListResponse = await client.get(stopListUrl)
    stopListObject = stopListResponse.json()
    
    if(len(stopListObject['data']) > 0) :
        for s in stopListObject['data']:
            stopList.append(s['stop'])
        newRoute['stops'] = stopList
        newRoute['bound'] = 'I' if(bound == 'inbound') else 'O'
        return newRoute
    else :
        return []
   
async def main():

    logDir = os.path.join (os.getcwd(), log_dir)
    
    if os.path.exists(logDir) == False: 
        os.mkdir(logDir)

    logFile = os.path.join(logDir, 'ctb.log')

    logging.basicConfig(filename=logFile, filemode='w', format='%(asctime)s | %(name)s - %(levelname)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S')

    # Creating an object
    logger = logging.getLogger()

    # Setting the threshold of logger to DEBUG
    logger.setLevel(logging.INFO)

    logging.info("Start getting CTB route")

    try:

        routeResponse = requests.get(allRouteBaseUrl, timeout=30.0)
        routeResponse.raise_for_status()
        # access Json content
        routeObject = routeResponse.json()
        
        routeList = routeObject['data']

        ctbList = []

        async with httpx.AsyncClient() as client:
            tasks = []
            for r in routeList :
                #print(r['route'], ' :', r['bound'], ':', r['orig_tc'], ":", r["dest_tc"])
                for b in ('outbound', 'inbound') :
                    time.sleep(0.005)
                    tasks.append(getStopList(client, r, b))
            ctbList += await asyncio.gather(*tasks)                

        ctbList = list(filter(None, ctbList))    

        writeToJson(ctbList, ctb_route_json)

        ctbStops = set()

        for r in ctbList:
            for s in r['stops']:
                ctbStops.add(s)

        ctbStopList = list(ctbStops)
        ctbStopList.sort()

        ctbStopInfoList = []
        async with httpx.AsyncClient() as client:
            tasks = []
            for c in ctbStopList :
                time.sleep(0.005)
                tasks.append(getStopInfo(client, c))
            ctbStopInfoList += await asyncio.gather(*tasks) 

        writeToJson(ctbStopInfoList, ctb_stop_json)

        logging.info("Finish getting CTB route")
        
    except HTTPError as http_err:
            print(f'HTTP error occurred: {http_err}')
            logging.error(f'HTTP error occurred: {http_err}')
            print(http_err)
            logging.error(http_err, exc_info=True)
            traceback.print_exc()

    except Exception as err:
            print(f'Other error occurred: {err}')
            logging.error(f'Other error occurred: {err}')
            print(err)
            logging.error(err, exc_info=True)
            traceback.print_exc()


asyncio.run(main())


   