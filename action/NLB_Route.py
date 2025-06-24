import requests
import json
import os
import logging
import asyncio  
import httpx
import operator
import traceback
import time
import GetRoute
import GeoJSON
#import GTFS

   
from requests.exceptions import HTTPError


allRouteBaseUrl = 'https://rt.data.gov.hk/v2/transport/nlb/route.php?action=list'
stopListBaseUrl = 'https://rt.data.gov.hk/v2/transport/nlb/stop.php?action=list&routeId='


nlb_route_json = 'NLB_Route'
nlb_stop_json = 'NLB_Stop'

log_dir = 'log'

nlbStops = list()


logDir = os.path.join (os.getcwd(), log_dir)

if os.path.exists(logDir) == False: 
    os.mkdir(logDir)

#if os.path.exists(os.path.join(log_dir, 'nlb.log')):
#    os.remove(os.path.join(log_dir, 'nlb.log'))

# NLB logger
nlb_logger = logging.getLogger('nlb')
nlb_handler = logging.FileHandler(os.path.join(log_dir, 'nlb.log'), encoding='utf-8', mode='w')
nlb_handler.setFormatter(logging.Formatter('%(asctime)s | %(name)s - %(levelname)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S'))
nlb_logger.addHandler(nlb_handler)
nlb_logger.setLevel(logging.INFO)


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


async def main(routes):
   
    try:
        print("Start getting NLB routes")
        nlb_logger.info("Start getting NLB routes")
        
        routeResponse = requests.get(allRouteBaseUrl, timeout=30.0)
        routeResponse.raise_for_status()

        routeObject = routeResponse.json()
        
        routeList = routeObject['routes']

        tasks = []
        nlbList = list()
        # Limit the number of concurrent tasks
        semaphore = asyncio.Semaphore(3)  # adjust the limit as needed

        async def limited_getStopList(client, nr):
            async with semaphore:
                return await getStopList(client, nr)

        async with httpx.AsyncClient() as client:
            for r in routeList:
                #time.sleep(0.05)
                nr = dict()
                nr['co'] = 'NLB'
                nr['routeId'] = r['routeId']
                nr['route'] = r['routeNo']
                nr['orig_tc'] = r['routeName_c'].split('>')[0].strip()
                nr['dest_tc'] = r['routeName_c'].split('>')[1].strip()
                nr['orig_sc'] = r['routeName_s'].split('>')[0].strip()
                nr['dest_sc'] = r['routeName_s'].split('>')[1].strip()
                nr['orig_en'] = r['routeName_e'].split('>')[0].strip()
                nr['dest_en'] = r['routeName_e'].split('>')[1].strip()

                nr['overnightRoute'] = r['overnightRoute']
                nr['specialRoute'] = r['specialRoute']
                #GTFS.findGtfsRoute(nr['co'], nr['route'], nr['orig_en'], nr['dest_en']) 
                tasks.append(limited_getStopList(client, nr))
            nlbList += await asyncio.gather(*tasks)

        nlbList = list(filter(None, nlbList))  
        nlbList.sort(key=lambda x: int(x.get('routeId')))
        
       
        print("Finish getting NLB routes")
        nlb_logger.info("Finish getting NLB routes")


        print("Start getting NLB stops")
        nlb_logger.info("Start getting NLB stops")
        nlbStopList = list({v['stop']:v for v in nlbStops}.values())
        
        global allStopList
        allStopList= sorted(nlbStopList, key=lambda x: int(operator.itemgetter("stop")(x))) 

        GetRoute.writeToJson(allStopList, nlb_stop_json)

        print("Finish getting NLB stops")
        nlb_logger.info("Finish getting NLB stops")

        for r in nlbList:
            firstStop = r['stops'][0]
            lastStop = r['stops'][-1]
            firstStopCoordinates = GetRoute.getCoordinate(firstStop, allStopList)
            lastStopCoordinates = GetRoute.getCoordinate(lastStop, allStopList)
            #print(f"{firstStopCoordinates}, {lastStopCoordinates}")

            if firstStopCoordinates is None or lastStopCoordinates is None:
                print(f"Cannot find coordinates for stops: {firstStop}, {lastStop}")
                nlb_logger.error(f"Cannot find coordinates for stops: {firstStop}, {lastStop}")
                r['gtfsRouteKey'] = []
                continue
            gtfsRouteKey = []
            gtfsRouteKey.extend(GeoJSON.matchRouteId('NLB', r['route'], firstStopCoordinates, lastStopCoordinates, routes))

            # remove empty item from gtfsRouteKey   
            gtfsRouteKey = [item for item in gtfsRouteKey if item is not None]

            if len(gtfsRouteKey) == 0:
                 nlb_logger.info(f"Cannot find GTFS route for NLB {r['route']} from {r['orig_tc'] } to {r['dest_tc']}")
            else:
                 nlb_logger.info(f"GTFS route for NLB {r['route']} from {r['orig_tc'] } to {r['dest_tc']} | "
                       f"routeCount: {len(gtfsRouteKey)}"
                       )
            for c in gtfsRouteKey:
                nlb_logger.info(f"{c} "
                            f"{routes[(c[1], c[2])][0]['properties']['stopNameC']} - "
                            f"{routes[(c[1], c[2])][-1]['properties']['stopNameC']}" )
            r['gtfsRouteKey'] = gtfsRouteKey

        GetRoute.writeToJson(nlbList, nlb_route_json)



        """         
        print("Start getting NLB route lines")
        logging.info("Start getting NLB route lines")
        nlbListWithRouteLine = list()
        
        nlbListWithRouteLine.append(GTFS.getRouteLineData('NLB', nlbList[0]))
       GetRoute.writeToJson(nlbListWithRouteLine, nlb_route_json + '_rl', None)  
        
        for r in nlbList:
            time.sleep(1)
            nlbListWithRouteLine.append(GTFS.getRouteLineData('NLB', r))
       GetRoute.writeToJson(nlbListWithRouteLine, nlb_route_json + '_rl') 
        
        print("Finish getting NLB route lines")
        logging.info("Finish getting NLB route lines")
        """
    except HTTPError as http_err:
            print(f'HTTP error occurred: {http_err}')
            nlb_logger.error(f'HTTP error occurred: {http_err}')
            print(http_err)
            nlb_logger.error(http_err, exc_info=True)
            traceback.print_exc()

    except Exception as err:
            print(f'Other error occurred: {err}')
            nlb_logger.error(f'Other error occurred: {err}')
            print(err)
            nlb_logger.error(err, exc_info=True)
            traceback.print_exc()

if __name__=="__main__":
    main()
#asyncio.run(main())