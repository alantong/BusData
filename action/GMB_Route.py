import requests
import json
import os
import logging
import asyncio  
import httpx
import operator
import time
import traceback
import GetRoute

from requests.exceptions import HTTPError

#headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.84 Safari/537.36'}

allRouteBaseUrl = 'https://data.etagmb.gov.hk/route/'
stopListBaseUrl = 'https://data.etagmb.gov.hk/route-stop/'
stopLocBaseUrl = 'https://data.etagmb.gov.hk/stop/'


gmb_route_json = 'GMB_Route'
gmb_stop_json = 'GMB_Stop'

log_dir = 'log'

logDir = os.path.join (os.getcwd(), log_dir)
if os.path.exists(logDir) == False: 
    os.mkdir(logDir)

logFile = os.path.join(logDir, 'gmb.log')

logging.basicConfig(filename=logFile, filemode='w', format='%(asctime)s | %(name)s - %(levelname)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S')

# Creating an object
logger = logging.getLogger()

# Setting the threshold of logger to DEBUG
logger.setLevel(logging.DEBUG)

delay = 0.05

gmbRoutes = list()
gmbStops = list()

async def getStopList(client, gr) :
    stopListUrl = f"{stopListBaseUrl}{gr['routeId']}/{gr['routeSeq']}"
    stopListResponse = await GetRoute.async_get_with_retry(client, stopListUrl)
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
        st['name_en'] = GetRoute.capWords(s['name_en'])
        gmbStops.append(st)

    _gr['stops'] = stopList
    return _gr
    

async def getStopLoc(client, s) :
    stopLocUrl = stopLocBaseUrl + str(s['stop'])
    stopLocResponse = await GetRoute.async_get_with_retry(client, stopLocUrl)
    stopLocObj = stopLocResponse.json()
    stopLoc = stopLocObj['data']['coordinates']['wgs84']
    s['lat'] = stopLoc['latitude']
    s['long'] = stopLoc['longitude']
    return s
    
async def getRouteName(client, region, routeNo) :
    routeNo = routeNo.strip("'")
    routeNameResponse = await GetRoute.async_get_with_retry(client, allRouteBaseUrl+region+"/"+routeNo)
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
            gr['orig_en'] = GetRoute.capWords(d['orig_en'])
            gr['dest_en'] = GetRoute.capWords(d['dest_en'])
            gmbRoutes.append(gr)

async def main():
    try:
        logger.info("Start getting GMB route")
        print("Start getting GMB route")
        
        # Limit the number of concurrent tasks
        semaphore = asyncio.Semaphore(10)  # adjust the limit as needed

        for region in ('NT', 'HKI', 'KLN'): 
            routeResponse = requests.get(allRouteBaseUrl+region, timeout=30.0)
            routeResponse.raise_for_status()

            routeObject = routeResponse.json()
            routeList = routeObject['data']['routes']

            async def limited_getRouteName(client, region, r):
                async with semaphore:
                    return await getRouteName(client, region, r)
            
            async with httpx.AsyncClient(timeout=30.0) as client1:
                tasks = []
                for r in routeList:
                    time.sleep(delay)
                    tasks.append(limited_getRouteName(client1, region, r))
                await asyncio.gather(*tasks)
            
        gmbRouteStop = list()

        async def limited_getStopList(client, gr):
            async with semaphore:
                return await getStopList(client, gr)
        
        async with httpx.AsyncClient(timeout=30.0) as client2:
            tasks = []
            for gr in gmbRoutes:
                 time.sleep(delay)
                 tasks.append(limited_getStopList(client2, gr))
            gmbRouteStop += await asyncio.gather(*tasks)
    
        _gmbRouteStop = sorted(gmbRouteStop, key=operator.itemgetter('route'))
        
        GetRoute.writeToJson(_gmbRouteStop, gmb_route_json)
        print("GMB Route List done")

        gmbStopList = list({v['stop']:v for v in gmbStops}.values())

        _gmbStopList= sorted(gmbStopList, key=lambda x: int(operator.itemgetter("stop")(x))) 

        gmbStopLoc = list()
        print("Start getting GMB Stop List")
        async def limited_getStopLoc(client, s):
            async with semaphore:
                return await getStopLoc(client, s)
        
        async with httpx.AsyncClient(timeout=30.0) as client3:
            tasks = []
            for s in _gmbStopList:
               time.sleep(delay)
               tasks.append(limited_getStopLoc(client3, s))
            gmbStopLoc += await asyncio.gather(*tasks)

        GetRoute.writeToJson(gmbStopLoc, gmb_stop_json)

        print("GMB Stop List done")

        print("Finish getting GMB route")
        logger.info("Finish getting GMB route")

    except HTTPError as http_err:
            print(f'HTTP error occurred: {http_err}')
            logger.error(f'HTTP error occurred: {http_err}')
            print(http_err)
            logger.error(http_err, exc_info=True)
            traceback.print_exc()

    except Exception as err:
            print(f'Other error occurred: {err}')
            logger.error(f'Other error occurred: {err}')
            print(err)
            logger.error(err, exc_info=True)
            traceback.print_exc()


if __name__=="__main__":
    asyncio.run(main())