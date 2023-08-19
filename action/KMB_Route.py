import requests
import json
import os
import logging
import asyncio
import time
import httpx
import traceback
import GetRoute

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

    print("Getting stoplist of " + stopListUrl)

    stopListResponse = await client.get(stopListUrl, timeout=30.0)
    stopListObject = stopListResponse.json()
    stopList = []
    for s in stopListObject['data']:
        stopList.append(s['stop'])
    r = route.copy()
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

    print("Start getting KMB routes")
    logging.info("Start getting KMB routes")

    try:
        
        outputDir = os.path.join(os.getcwd(), output_dir)
        if os.path.exists(outputDir) == False:
            os.mkdir(outputDir)


        allStopListResponse = requests.get(stopListBaseUrl, timeout=30.0)
        allStopListResponse.raise_for_status()
        # access Json content
        allStopListObject = allStopListResponse.json()

        allStopList = allStopListObject['data']

        stopListDict = {}
        for sl in allStopList:
            sl_r = sl['route']
            sl_b = sl['bound']
            sl_st = sl['service_type']
            #.setdefault(k, []).append(v)
            stopListDict.setdefault((sl_r, sl_b, sl_st), []).append(sl['stop'])
            #stopListDict[str(sl_r)][str(sl_b)][str(sl_st)]['stops'].append(sl['stop'])

        #print(stopListDict)

        routeResponse = requests.get(allRouteBaseUrl, timeout=30.0)
        routeResponse.raise_for_status()
        # access Json content
        routeObject = routeResponse.json()
        
        routeList = routeObject['data']

        for r in routeList:
            r['co'] = "KMB"
            r['orig_en'] = GetRoute.capWords(r['orig_en'])
            r['dest_en'] = GetRoute.capWords(r['dest_en'])
            r['stops'] = stopListDict[(r['route'], r['bound'], r['service_type'])]
        
        writeToJson(routeList, kmb_route_json)

        """
        newRouteList = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            tasks = []
            for r in routeList:
                r['co'] = "KMB"
                r['orig_en'] = GetRoute.capWords(r['orig_en'])
                r['dest_en'] = GetRoute.capWords(r['dest_en'])
                time.sleep(0.005)
                tasks.append(getStopList(client, r))
            
            newRouteList += await asyncio.gather(*tasks)
        """




        print("Finish getting KMB routes")
        logging.info("Finish getting KMB rotues")

        allStopResponse = requests.get(allStopBaseUrl, timeout=30.0)
        allStopResponse.raise_for_status()
        # access Json content
        allStopObject = allStopResponse.json()
        
        allStopList = allStopObject['data']
        for s in allStopList:
            s['co'] = 'KMB'
            s['name_en'] = GetRoute.capWords(s['name_en'])
            
        writeToJson(allStopList, kmb_stop_json)

        print("Finish getting KMB stops")
        logging.info("Finish getting KMB stops")
        
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