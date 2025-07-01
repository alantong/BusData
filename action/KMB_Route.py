import requests
import os
import logging
import traceback
import GetRoute
import GeoJSON
#import GTFS


from requests.exceptions import HTTPError


allRouteBaseUrl = 'https://data.etabus.gov.hk/v1/transport/kmb/route'
stopListBaseUrl = 'https://data.etabus.gov.hk/v1/transport/kmb/route-stop/'
allStopBaseUrl = 'https://data.etabus.gov.hk/v1/transport/kmb/stop'

kmb_route_json = 'KMB_Route'
kmb_stop_json = 'KMB_Stop'

log_dir = 'log'
output_dir = 'output'

logDir = os.path.join (os.getcwd(), log_dir)

if os.path.exists(logDir) == False: 
    os.mkdir(logDir)

#if os.path.exists(os.path.join(log_dir, 'kmb.log')):
#    os.remove(os.path.join(log_dir, 'kmb.log'))

# KMB logger
kmb_logger = logging.getLogger('kmb')
kmb_handler = logging.FileHandler(os.path.join(log_dir, 'kmb.log'), encoding='utf-8', mode='w')
kmb_handler.setFormatter(logging.Formatter('%(asctime)s | %(name)s - %(levelname)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S'))
kmb_logger.addHandler(kmb_handler)
kmb_logger.setLevel(logging.INFO)


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


def main(routes):
    
    try:
        # check if output/gtfs.json exists
        """if os.path.exists('output/gtfs.json'):
                
            with open('output/gtfs.json', encoding='utf8') as f:
                gtfsData = json.load(f)

            # Now you can access the routeList dictionary:
            gtfsRouteList = gtfsData['routeList']

            print(f"Total GTFS routes: {len(gtfsRouteList)}")
        """
        outputDir = os.path.join(os.getcwd(), output_dir)
        if os.path.exists(outputDir) == False:
            os.mkdir(outputDir)

        print("Start getting KMB stops")
        kmb_logger.info("Start getting KMB stops")

        allStopResponse = requests.get(allStopBaseUrl, timeout=30.0)
        allStopResponse.raise_for_status()
        # access Json content
        allStopObject = allStopResponse.json()
        
        global allStopList
        allStopList = allStopObject['data']
        for s in allStopList:
            s['co'] = 'KMB'
            s['name_en'] = GetRoute.capWords(s['name_en'])
            
        GetRoute.writeToJson(allStopList, kmb_stop_json)

        print("Finish getting KMB stops")
        kmb_logger.info("Finish getting KMB stops")


        allStopListResponse = requests.get(stopListBaseUrl, timeout=30.0)
        allStopListResponse.raise_for_status()
        # access Json content
        allStopListObject = allStopListResponse.json()

        allStopListForRoute = allStopListObject['data']

        stopListDict = {}
        for sl in allStopListForRoute:
            sl_r = sl['route']
            sl_b = sl['bound']
            sl_st = sl['service_type']
            #.setdefault(k, []).append(v)
            stopListDict.setdefault((sl_r, sl_b, sl_st), []).append(sl['stop'])
            #stopListDict[str(sl_r)][str(sl_b)][str(sl_st)]['stops'].append(sl['stop'])

        #print(stopListDict)

        print("Start getting KMB routes")
        kmb_logger.info("Start getting KMB routes")

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
            #GTFS.findGtfsRoute(r['co'], r['route'], r['orig_en'], r['dest_en'])
            #routeLineJson = GTFS.getRouteLineData('KMB', r['route'])
            #r['routeLine'] = routeLineJson

            firstStop = r['stops'][0]
            lastStop = r['stops'][-1]
            firstStopCoordinates = GetRoute.getCoordinate(firstStop, allStopList)
            lastStopCoordinates = GetRoute.getCoordinate(lastStop, allStopList)
            if firstStopCoordinates is None or lastStopCoordinates is None:
                print(f"Cannot find coordinates for stops: {firstStop}, {lastStop}")
                kmb_logger.error(f"Cannot find coordinates for stops: {firstStop}, {lastStop}")
                r['gtfsRouteKey'] = []
                continue
            gtfsRouteKey = []
            gtfsRouteKey.extend(GeoJSON.matchRouteId('KMB', r, firstStopCoordinates, lastStopCoordinates, routes))
            gtfsRouteKey.extend(GeoJSON.matchRouteId('LWB', r, firstStopCoordinates, lastStopCoordinates, routes))
            #gtfsRouteKey.extend(GeoJSON.matchRouteId('KMB+CTB', r['route'], firstStopCoordinates, lastStopCoordinates))
            #gtfsRouteKey.extend(GeoJSON.matchRouteId('LWB+CTB', r['route'], firstStopCoordinates, lastStopCoordinates))

            # remove empty item from gtfsRouteKey   
            gtfsRouteKey = [item for item in gtfsRouteKey if item is not None]

            if len(gtfsRouteKey) == 0:
                 kmb_logger.info(f"Cannot find GTFS route for KMB {r['route']} from {r['orig_tc'] } to {r['dest_tc']}|#stops:{len(r['stops'])}")
            else:
                 kmb_logger.info(f"GTFS route for KMB {r['route']} from {r['orig_tc'] } to {r['dest_tc']}|#stops:{len(r['stops'])}|"
                       f"routeCount: {len(gtfsRouteKey)}"
                       )

            fullFare = ""
            journeyTime = ""     
            for c in gtfsRouteKey:
                fullFare += str(routes[(c[1], c[2])][0]['properties']['fullFare']) + "|"
                journeyTime += str(routes[(c[1], c[2])][0]['properties']['journeyTime']) + "|"
                kmb_logger.info(f"{c} "
                                f"{routes[(c[1], c[2])][0]['properties']['stopNameC']} - "
                                f"{routes[(c[1], c[2])][-1]['properties']['stopNameC']}|"
                                f"${routes[(c[1], c[2])][0]['properties']['fullFare']}|" 
                                f"time:{routes[(c[1], c[2])][0]['properties']['journeyTime']}|" 
                                f"#stops:{len(routes[(c[1], c[2])])}|"                                
                                )
            r['fullFare'] = fullFare[:-1]
            r['journeyTime'] = journeyTime[:-1]
            r['gtfsRouteKey'] = gtfsRouteKey
            

        # write to json    
        GetRoute.writeToJson(routeList, kmb_route_json)

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
        kmb_logger.info("Finish getting KMB rotues")

        
    except HTTPError as http_err:
            print(f'HTTP error occurred: {http_err}')
            kmb_logger.error(f'HTTP error occurred: {http_err}')
            print(http_err)
            kmb_logger.error(http_err, exc_info=True)
            traceback.print_exc()

    except Exception as err:
            print(f'Other error occurred: {err}')
            kmb_logger.error(f'Other error occurred: {err}')
            print(err)
            kmb_logger.error(err, exc_info=True)
            traceback.print_exc()

#asyncio.run(main())

if __name__=="__main__":
    main()