import requests
import json
import os
import logging
import asyncio
import time
import httpx
import traceback
import GetRoute
import re

from requests.exceptions import HTTPError

allRouteBaseUrl = 'https://opendata.mtr.com.hk/data/mtr_bus_routes.csv'
allStopBaseUrl = 'https://opendata.mtr.com.hk/data/mtr_bus_stops.csv'

log_dir = 'log'
output_dir = 'output'

MTRBus_route_json = 'MTR_Bus_Route'
MTRBus_stop_json = 'MTR_Bus_Stop'
 
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

def getRouteStop(routeNo, bound, stopList):
    routeStopList = []
    for s in stopList:
        if (s['route'] == routeNo and s['bound'] == bound):
            routeStopList.append(s)
    #routeStopList.sort('stopSeq')
    #print(routeStopList)
    return routeStopList

async def main():
    
    logDir = os.path.join (os.getcwd(), log_dir)
    
    if os.path.exists(logDir) == False: 
        os.mkdir(logDir)

    logFile = os.path.join(logDir, 'mtr_bus.log')
        
    logging.basicConfig(filename=logFile, filemode='w', format='%(asctime)s | %(name)s - %(levelname)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S')

    # Creating an object
    logger = logging.getLogger()

    # Setting the threshold of logger to DEBUG
    logger.setLevel(logging.INFO)

    print("Start getting MTR Bus stops")
    logging.info("Start getting MTR Bus stops")

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

                line = re.sub("(\",\"|\",|,\")", "|", line)
                #line = line.replace("\",\"", '|')
                row = [i.strip(" \"") for i in line.split('|')]
                stop = {}
                stop['co'] = 'MTR_BUS'
                stop['route'] = row[0]
                stop['bound'] = row[1]
                stop['stopSeq'] = row[2]
                stop['stopId'] = row[3]
                stop['lat'] = row[4]
                stop['long'] = row[5]
                stop['name_tc'] = row[6]
                stop['name_en'] = row[7]
                
                stopList.append(stop)
        
        writeToJson(stopList, MTRBus_stop_json)

        print("Finish getting MTR Bus stoos")
        logging.info("Finish getting MTR Bus stops")

        print("Start getting MTR Bus routes")
        logging.info("Start getting MTR Bus routes")

        routeResponse = requests.get(allRouteBaseUrl, timeout=30.0)
        routeResponse.raise_for_status()
     
        routeList = []
        if routeResponse.status_code == 200:
            routeResponse.encoding = 'utf8'
            lines = routeResponse.text.splitlines()
            for line in lines[1:]:
                row = [i.strip(" \"") for i in line.split(',')]
                route = {}
                route['co'] = 'MTR_BUS'
                routeNo = row[0]

                routeStopList = getRouteStop(routeNo, 'O', stopList)
                if(len(routeStopList) > 0 ) :
                    route['route'] = routeNo
                    route['bound'] = 'O'
                    route['orig_tc'] = row[1].split('至')[0] 
                    route['dest_tc'] = row[1].split('至')[1] 
                    route['orig_en'] = row[2].split(' to ')[0] 
                    route['dest_en'] = row[2].split(' to ')[1] 
                    stops = map(lambda x:  x['stopId'] , routeStopList)
                    route['stops'] = list(stops)
                    
                    routeList.append(route)

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
                    stops = map(lambda x:  x['stopId'] , routeStopList)
                    route['stops'] = list(stops)

                    routeList.append(route)

        writeToJson(routeList, MTRBus_route_json)


        print("Finish getting MTR Bus routes")
        logging.info("Finish getting MTR Bus rotues")

        
        
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