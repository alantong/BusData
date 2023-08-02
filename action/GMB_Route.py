import requests
import json
import os
import logging
import asyncio  
import httpx
import operator
import time
import traceback

from requests.exceptions import HTTPError

headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.84 Safari/537.36'}

allRouteBaseUrl = 'https://data.etagmb.gov.hk/route/'
stopListBaseUrl = 'https://data.etagmb.gov.hk/route-stop/'
stopLocBaseUrl = 'https://data.etagmb.gov.hk/stop/'


gmb_route_json = 'GMB_Route'
gmb_stop_json = 'GMB_Stop'

log_dir = 'log'
output_dir = 'output'

gmbRoutes = list()
gmbStops = list()

def writeToJson(content, filename) :
    outputDir = os.path.join(os.getcwd(), output_dir)
    if os.path.exists(outputDir) == False:
        os.mkdir(outputDir)

    outputJson = os.path.join (outputDir, filename + ".json")

    if os.path.exists(outputJson):
            os.remove(outputJson)

    with open(outputJson, 'w', encoding='UTF-8') as write_file:
        json.dump(content, write_file, indent=4, ensure_ascii=False)

async def getStopList(client, gr) :
    stopListUrl = f"{stopListBaseUrl}{gr['routeId']}/{gr['routeSeq']}"
    stopListResponse = await client.get(stopListUrl)
    stopListObject = stopListResponse.json()

    stopList = list()

    
    _gr = gr.copy()
    for s in stopListObject['data']['route_stops']:
        stopList.append(s['stop_id'])
        st = dict()
        st['co'] = 'GMB'
        st['stop'] = s['stop_id']
        st['name_tc'] = s['name_tc']
        st['name_sc'] = s['name_sc']
        st['name_en'] = s['name_en']
        gmbStops.append(st)

    _gr['stops'] = stopList
    return _gr
    

async def getStopLoc(client, s) :
    stopLocUrl = stopLocBaseUrl + str(s['stop'])
    stopLocResponse = await client.get(stopLocUrl)
    stopLocObj = stopLocResponse.json()
    stopLoc = stopLocObj['data']['coordinates']['wgs84']
    s['lat'] = stopLoc['latitude']
    s['long'] = stopLoc['longitude']
    return s
    
async def getRouteName(client, region, routeNo) :
    routeNameResponse = await client.get(allRouteBaseUrl+region+"/"+routeNo)
    routeNameObject =  routeNameResponse.json()
    routeIdObject = routeNameObject['data']

    for rId in routeIdObject:
        for d in rId['directions']:
            gr = dict()
            gr['co'] = 'GMB'
            gr['route'] = rId['route_code']
            gr['routeId'] = rId['route_id']
            gr['routeSeq'] = d['route_seq']
            gr['orig_tc'] = d['orig_tc']
            gr['dest_tc'] = d['dest_tc']
            gr['orig_sc'] = d['orig_sc']
            gr['dest_sc'] = d['dest_sc']
            gr['orig_en'] = d['orig_en']
            gr['dest_en'] = d['dest_en']
            gmbRoutes.append(gr)

async def main():
    logDir = os.path.join (os.getcwd(), log_dir)
    if os.path.exists(logDir) == False: 
        os.mkdir(logDir)

    logFile = os.path.join(logDir, 'gmb.log')

    logging.basicConfig(filename=logFile, filemode='w', format='%(asctime)s | %(name)s - %(levelname)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S')

    # Creating an object
    logger = logging.getLogger()

    # Setting the threshold of logger to DEBUG
    logger.setLevel(logging.DEBUG)

    logging.info("Start getting GMB route")

    try:
        for region in ('NT', 'HKI', 'KLN'): 
            routeResponse = requests.get(allRouteBaseUrl+region, headers=headers, timeout=30.0)
            routeResponse.raise_for_status()

            routeObject = routeResponse.json()
            routeList = routeObject['data']['routes']

            async with httpx.AsyncClient(timeout=30.0) as client:
                tasks = []
                for r in routeList:
                    tasks.append(getRouteName(client, region, r.strip("'")))
                await asyncio.gather(*tasks)
            
        
        gmbRouteStop = list()
        async with httpx.AsyncClient(timeout=30.0) as client:
            tasks = []
            for gr in gmbRoutes:
                 time.sleep(0.005)
                 tasks.append(getStopList(client, gr))
            gmbRouteStop += await asyncio.gather(*tasks)
    
        _gmbRouteStop = sorted(gmbRouteStop, key=operator.itemgetter('route'))
        
        writeToJson(_gmbRouteStop, gmb_route_json)
        print("GMB Route List done")


        gmbStopList = list({v['stop']:v for v in gmbStops}.values())

        _gmbStopList= sorted(gmbStopList, key=lambda x: int(operator.itemgetter("stop")(x))) 

        gmbStopLoc = list()
        async with httpx.AsyncClient(timeout=30.0) as client:
            tasks = []
            for s in _gmbStopList:
               time.sleep(0.005)
               tasks.append(getStopLoc(client, s))
            gmbStopLoc += await asyncio.gather(*tasks)

        writeToJson(gmbStopLoc, gmb_stop_json)

        print("GMB Stop List done")

        logging.info("Finish getting GMB route")

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