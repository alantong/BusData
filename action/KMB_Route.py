import requests
import json
import os
import logging
import asyncio
import time
import httpx
import traceback
import re
import string

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


def capWords(s) :
    r = s.title()
    r = re.sub(r'\'[A-Z]', lambda p: p.group(0).lower(), r)
    r = re.sub(r'\sBbi\s', ' BBI ', r)
    r = re.sub(r'Mtr\s', 'MTR ', r)
    r = re.sub(r'Plb\s', 'PLB ', r)
    r = re.sub(r'Hku\s', 'HKU ', r)
    r = re.sub(r'Near\s', 'near ', r)
    r = re.sub(r'\sAnd\s', ' and ', r)
    r = re.sub(r'Outside', 'outside', r)
    r = re.sub(r'Opposite', 'opposite', r)
    r = re.sub(r'Via', 'via', r)
    r = re.sub(r'\sOf\s', ' of ', r)
    #r = re.sub(r'By The', 'by the', r)
    #r = re.sub(r'On The', 'on the', r)
    r = re.sub(r'\bIi\b', 'II', r)
    r = re.sub(r'\bIii\b', 'III', r)
    r = re.sub(r'\(Gtc\)', '(GTC)', r)
    return r

async def getStopList(client, route) :
    bound = 'outbound' if(route['bound'] == 'O')  else 'inbound'
    stopListUrl = stopListBaseUrl + route['route'] + '/' + bound + '/' + route['service_type'] 

    stopListResponse = await client.get(stopListUrl, timeout=30.0)
    stopListObject = stopListResponse.json()
    stopList = []
    for s in stopListObject['data']:
        stopList.append(s['stop'])
    r = route.copy()
    r['co'] = "KMB"
    r['orig_en'] = capWords(r['orig_en'])
    r['dest_en'] = capWords(r['dest_en'])
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

        routeResponse = requests.get(allRouteBaseUrl, timeout=30.0)
        routeResponse.raise_for_status()
        # access Json content
        routeObject = routeResponse.json()
        
        routeList = routeObject['data']

        newRouteList = []
        async with httpx.AsyncClient() as client:
            tasks = []
            for r in routeList:
                time.sleep(0.005)
                tasks.append(getStopList(client, r))
            
            newRouteList += await asyncio.gather(*tasks)


        writeToJson(newRouteList, kmb_route_json)

        allStopResponse = requests.get(allStopBaseUrl, timeout=30.0)
        allStopResponse.raise_for_status()
        # access Json content
        allStopObject = allStopResponse.json()
        
        allStopList = allStopObject['data']
        for s in allStopList:
            s['co'] = 'KMB'
            s['name_en'] = capWords(s['name_en'])
            
        writeToJson(allStopList, kmb_stop_json)

        logging.info("Finish getting KMB route")
        
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