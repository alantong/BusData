import requests
import os
import logging
import traceback
import GetRoute
import GeoJSON

from requests.exceptions import HTTPError

allRouteBaseUrl = 'https://opendata.mtr.com.hk/data/mtr_bus_routes.csv'
allStopBaseUrl = 'https://opendata.mtr.com.hk/data/mtr_bus_stops.csv'

log_dir = 'log'
output_dir = 'output'

MTRBus_route_json = 'MTR_BUS_Route'
MTRBus_stop_json = 'MTR_BUS_Stop'
 
log_dir = 'log'

logDir = os.path.join (os.getcwd(), log_dir)

if os.path.exists(logDir) == False: 
    os.mkdir(logDir)

logFile = os.path.join(logDir, 'mtr_bus.log')
    
# MTR_BUS logger
mtrbus_logger = logging.getLogger('mtr_bus')
mtrbus_handler = logging.FileHandler(os.path.join(log_dir, 'mtr_bus.log'), encoding='utf-8', mode='w')
mtrbus_handler.setFormatter(logging.Formatter('%(asctime)s | %(name)s - %(levelname)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S'))
mtrbus_logger.addHandler(mtrbus_handler)
mtrbus_logger.setLevel(logging.DEBUG)


def getRouteStop(routeNo, bound, stopList):
    routeStopList = []
    for s in stopList:
        if (s['route'] == routeNo and s['bound'] == bound):
            routeStopList.append(s)
    #routeStopList.sort('stopSeq')
    #print(routeStopList)
    return routeStopList

def main(routes):
    print("Start getting MTR Bus stops")
    mtrbus_logger.info("Start getting MTR Bus stops")

    try:
        
        outputDir = os.path.join(os.getcwd(), output_dir)
        if os.path.exists(outputDir) == False:
            os.mkdir(outputDir)


        stopResponse = requests.get(allStopBaseUrl, timeout=30.0)
        stopResponse.raise_for_status()
        
        stopList = []
        if stopResponse.status_code == 200:
            stopResponse.encoding = 'utf8'
            lines = stopResponse.text.splitlines()
            
            for line in lines[1:]:

                #line = re.sub("(\",\"|\",|,\")", "|", line)
                #line = line.replace("\",\"", '|')
                #line = re.sub("\"", "", line)
                row = [i.strip(" \"") for i in line.split(',')]
                if(len(row) > 0 ):
                    stop = {}
                    stop['co'] = 'MTR_BUS'
                    stop['route'] = row[0]
                    stop['bound'] = row[1]
                    stop['stopSeq'] = row[2]
                    stop['stop'] = row[3]
                    stop['lat'] = row[4]
                    stop['long'] = row[5]
                    stop['name_tc'] = row[6]
                    stop['name_en'] = row[7]
                    
                    stopList.append(stop)
        
        GetRoute.writeToJson(stopList, MTRBus_stop_json)

        print("Finish getting MTR Bus stops")
        mtrbus_logger.info("Finish getting MTR Bus stops")

        print("Start getting MTR Bus routes")
        mtrbus_logger.info("Start getting MTR Bus routes")

        routeResponse = requests.get(allRouteBaseUrl, timeout=30.0)
        routeResponse.raise_for_status()
     
        routeList = []
        if routeResponse.status_code == 200:
            routeResponse.encoding = 'utf8'
            lines = routeResponse.text.splitlines()
            for line in lines[1:]:
                row = [i.strip(" \"") for i in line.split(',')]


                for bound in ('O', 'I'):
                    r = {}
                    r['co'] = 'MTR_BUS'
                    routeNo = row[0]

                    routeStopList = getRouteStop(routeNo, bound, stopList)
                    if(len(routeStopList) > 0 ) :
                        r['route'] = routeNo
                        r['bound'] = 'O'
                        r['orig_tc'] = row[1].split('至')[0] 
                        r['dest_tc'] = row[1].split('至')[1] 
                        r['orig_en'] = row[2].split(' to ')[0] 
                        r['dest_en'] = row[2].split(' to ')[1] 
                        stops = map(lambda x:  x['stop'] , routeStopList)
                        r['stops'] = list(stops)

                        firstStop = r['stops'][0]
                        lastStop = r['stops'][-1]
                        firstStopCoordinates = GetRoute.getCoordinate(firstStop, stopList)
                        lastStopCoordinates = GetRoute.getCoordinate(lastStop, stopList)
                        if firstStopCoordinates is None or lastStopCoordinates is None:
                            print(f"Cannot find coordinates for stops: {firstStop}, {lastStop}")
                            mtrbus_logger.error(f"Cannot find coordinates for stops: {firstStop}, {lastStop}")
                            r['gtfsRouteKey'] = []
                            continue
                        gtfsRouteKey = []
                        gtfsRouteKey.extend(GeoJSON.matchRouteId('KMB', r, firstStopCoordinates, lastStopCoordinates, routes))
                        gtfsRouteKey.extend(GeoJSON.matchRouteId('LRTFeeder', r, firstStopCoordinates, lastStopCoordinates, routes))
                        
                        # remove empty item from gtfsRouteKey   
                        gtfsRouteKey = [item for item in gtfsRouteKey if item is not None]

                        if len(gtfsRouteKey) == 0:
                            mtrbus_logger.info(f"Cannot find GTFS route for KMB {r['route']} from {r['orig_tc'] } to {r['dest_tc']}|#stops:{len(r['stops'])}")
                        else:
                            mtrbus_logger.info(f"GTFS route for KMB {r['route']} from {r['orig_tc'] } to {r['dest_tc']}|#stops:{len(r['stops'])}|"
                                f"routeCount: {len(gtfsRouteKey)}"
                                )
                        
                        for c in gtfsRouteKey:
                            mtrbus_logger.info(f"{c} "
                                            f"{routes[(c[1], c[2])][0]['properties']['stopNameC']} - "
                                            f"{routes[(c[1], c[2])][-1]['properties']['stopNameC']}|"
                                            f"${routes[(c[1], c[2])][0]['properties']['fullFare']}|" 
                                            f"time:{routes[(c[1], c[2])][0]['properties']['journeyTime']}|" 
                                            f"#stops:{len(routes[(c[1], c[2])])}|"                                
                                            )
                            route_data = routes.get((c[1], c[2]))
                            if route_data is not None:
                                r['fullFare'] = route_data[0]['properties']['fullFare']
                                r['journeyTime'] = route_data[0]['properties']['journeyTime']    
                        r['gtfsRouteKey'] = gtfsRouteKey

                        routeList.append(r)


                """
                route = {}
                route['co'] = 'MTR_BUS'
                routeStopList = getRouteStop(routeNo, 'I', stopList)
                if(len(routeStopList) > 0 ) :
                    route['route'] = routeNo
                    route['bound'] = 'I'
                    route['orig_tc'] = row[1].split('至')[1] 
                    route['dest_tc'] = row[1].split('至')[0] 
                    route['orig_en'] = row[2].split(' to ')[1] 
                    route['dest_en'] = row[2].split(' to ')[0] 
                    stops = map(lambda x:  x['stop'] , routeStopList)
                    route['stops'] = list(stops)

                    routeList.append(route)

                """
        GetRoute.writeToJson(routeList, MTRBus_route_json)


        print("Finish getting MTR Bus routes")
        mtrbus_logger.info("Finish getting MTR Bus rotues")

        
        
    except HTTPError as http_err:
            print(f'HTTP error occurred: {http_err}')
            mtrbus_logger.error(f'HTTP error occurred: {http_err}')
            print(http_err)
            mtrbus_logger.error(http_err, exc_info=True)
            traceback.print_exc()

    except Exception as err:
            print(f'Other error occurred: {err}')
            mtrbus_logger.error(f'Other error occurred: {err}')
            print(err)
            mtrbus_logger.error(err, exc_info=True)
            traceback.print_exc()

if __name__=="__main__":
    main()