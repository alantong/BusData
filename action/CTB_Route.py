import requests
import json
import os
import logging
import asyncio 
import time 
import httpx
import traceback
import GetRoute
import GeoJSON
#import GTFS

from requests.exceptions import HTTPError

allRouteBaseUrl = 'https://rt.data.gov.hk/v2/transport/citybus/route/ctb/'
stopListBaseUrl = 'https://rt.data.gov.hk/v2/transport/citybus/route-stop/CTB/'
stopInfoBaseUrl = 'https://rt.data.gov.hk/v2/transport/citybus/stop/'

ctb_route_json = 'CTB_Route'
ctb_stop_json = 'CTB_Stop'

log_dir = 'log'

logDir = os.path.join (os.getcwd(), log_dir)

if os.path.exists(logDir) == False: 
    os.mkdir(logDir)

#if os.path.exists(os.path.join(log_dir, 'ctb.log')):
#    os.remove(os.path.join(log_dir, 'ctb.log'))

# CTB logger
ctb_logger = logging.getLogger('ctb')
ctb_handler = logging.FileHandler(os.path.join(log_dir, 'ctb.log'), encoding='utf-8', mode='w')
ctb_handler.setFormatter(logging.Formatter('%(asctime)s | %(name)s - %(levelname)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S'))
ctb_logger.addHandler(ctb_handler)
ctb_logger.setLevel(logging.INFO)


async def getStopInfo(client, stopId):
    stopInfo = []
    stopInfoUrl = stopInfoBaseUrl + stopId

    stopInfoResponse = await client.get(stopInfoUrl, timeout=30.0)
    stopInfoObject = stopInfoResponse.json()

    if(len(stopInfoObject['data']) > 0):
        stopInfo = stopInfoObject['data']
        stopInfo['co'] = 'CTB'
        stopInfo.pop('data_timestamp')
    return stopInfo

async def getStopList(client, route, bound):
    stopList = []
    stopListUrl = f"{stopListBaseUrl}{route['route']}/{bound}"
    newRoute = route.copy()
    if(bound == 'inbound') :
        newRoute['orig_tc'], newRoute['dest_tc'] = newRoute['dest_tc'], newRoute['orig_tc']
        newRoute['orig_en'], newRoute['dest_en'] = newRoute['dest_en'], newRoute['orig_en']
        newRoute['orig_sc'], newRoute['dest_sc'] = newRoute['dest_sc'], newRoute['orig_sc']

    stopListResponse = await client.get(stopListUrl, timeout=30.0)
    stopListObject = stopListResponse.json()
    
    if(len(stopListObject['data']) > 0) :
        for s in stopListObject['data']:
            stopList.append(s['stop'])
        newRoute['stops'] = stopList
        newRoute['bound'] = 'I' if(bound == 'inbound') else 'O'
        newRoute.pop('data_timestamp')
        return newRoute
    else :
        return []
   
async def main(routes):
    print("Start getting CTB routes")
    ctb_logger.info("Start getting CTB routes")
        
    try:

        routeResponse = requests.get(allRouteBaseUrl, timeout=30.0)
        routeResponse.raise_for_status()
        # access Json content
        routeObject = routeResponse.json()
        
        routeList = routeObject['data']

        ctbList = []

        # Limit the number of concurrent tasks
        semaphore = asyncio.Semaphore(5)  # adjust the limit as needed

        async def limited_getStopList(client, r, b):
            async with semaphore:
                return await getStopList(client, r, b)
            
        async with httpx.AsyncClient() as client:
            tasks = []
            for r in routeList :
                #GTFS.findGtfsRoute(r['co'], r['route'], r['orig_en'], r['dest_en'])
                #print(r['route'], ' :', r['bound'], ':', r['orig_tc'], ":", r["dest_tc"])
                for b in ('outbound', 'inbound') :
                    #time.sleep(0.05)
                    tasks.append(limited_getStopList(client, r, b))
            ctbList += await asyncio.gather(*tasks)                

        ctbList = list(filter(None, ctbList))    

        #writeToJson(ctbList, ctb_route_json)
        
        print("Finish getting CTB routes")
        ctb_logger.info("Finish getting CTB routes")

        print("Start getting CTB stops")
        ctb_logger.info("Start getting CTB stops")

        ctbStops = set()

        for r in ctbList:
            for s in r['stops']:
                ctbStops.add(s)

        ctbStopList = list(ctbStops)
        ctbStopList.sort()

        global allStopList
        allStopList = []
        
        # Limit the number of concurrent tasks
        semaphore = asyncio.Semaphore(5)  # adjust the limit as needed

        async def limited_getStopInfo(client, stopId):
            async with semaphore:
                return await getStopInfo(client, stopId)

        async with httpx.AsyncClient() as client:
            tasks = []
            for c in ctbStopList:
                #time.sleep(0.05)
                tasks.append(limited_getStopInfo(client, c))
            allStopList += await asyncio.gather(*tasks)
        

        allStopList = list(filter(None, allStopList))
        GetRoute.writeToJson(allStopList, ctb_stop_json)

        print("Finish getting CTB stops")
        ctb_logger.info("Finish getting CTB stops")


        for r in ctbList:
            firstStop = r['stops'][0]
            lastStop = r['stops'][-1]
            firstStopCoordinates = GetRoute.getCoordinate(firstStop, allStopList)
            lastStopCoordinates = GetRoute.getCoordinate(lastStop, allStopList)
            #print(f"{firstStopCoordinates}, {lastStopCoordinates}")

            if firstStopCoordinates is None or lastStopCoordinates is None:
                print(f"Cannot find coordinates for stops: {firstStop}, {lastStop}")
                ctb_logger.error(f"Cannot find coordinates for stops: {firstStop}, {lastStop}")
                r['gtfsRouteKey'] = []
                continue
            gtfsRouteKey = []
            gtfsRouteKey.extend(GeoJSON.matchRouteId('CTB', r['route'], firstStopCoordinates, lastStopCoordinates, routes))

            # remove empty item from gtfsRouteKey   
            gtfsRouteKey = [item for item in gtfsRouteKey if item is not None]

            if len(gtfsRouteKey) == 0:
                 ctb_logger.info(f"Cannot find GTFS route for CTB {r['route']} from {r['orig_tc'] } to {r['dest_tc']}")
            else:
                 ctb_logger.info(f"GTFS route for CTB {r['route']} from {r['orig_tc'] } to {r['dest_tc']} | "
                       f"routeCount: {len(gtfsRouteKey)}"                                                           
                       )
            for c in gtfsRouteKey:
                ctb_logger.info(f"{c} "
                                f"{routes[(c[1], c[2])][0]['properties']['stopNameC']} - "
                                f"{routes[(c[1], c[2])][-1]['properties']['stopNameC']}" )
            r['gtfsRouteKey'] = gtfsRouteKey

        GetRoute.writeToJson(ctbList, ctb_route_json)

        
    except HTTPError as http_err:
            print(f'HTTP error occurred: {http_err}')
            ctb_logger.error(f'HTTP error occurred: {http_err}')
            print(http_err)
            ctb_logger.error(http_err, exc_info=True)
            traceback.print_exc()

    except Exception as err:
            print(f'Other error occurred: {err}')
            ctb_logger.error(f'Other error occurred: {err}')
            print(err)
            ctb_logger.error(err, exc_info=True)
            traceback.print_exc()


if __name__=="__main__":
    main()


   