import subprocess
import asyncio
import os
import re
import json
import time
import httpx
import GeoJSON
import KMB_Route
import CTB_Route
import NLB_Route
import GMB_Route
import MTR_BUS_Route


output_dir = 'output'

def main() :
    start_time = time.time()  # Start timer

    print("main started")
    actionDir = os.path.join(os.getcwd(), "action")
    
    global busRoutes
    busRoutes = GeoJSON.getGeoJsonRoutes("BUS")
    gmbRoutes = GeoJSON.getGeoJsonRoutes("GMB")

    KMB_Route.main(busRoutes)
    asyncio.run(CTB_Route.main(busRoutes))
    asyncio.run(NLB_Route.main(busRoutes))     
    asyncio.run(GMB_Route.main(gmbRoutes))
    MTR_BUS_Route.main(busRoutes)

    #subprocess.run(["python", os.path.join(actionDir, "FGDB_BUS.py")])
    #subprocess.run(["python", os.path.join(actionDir, "FGDB_GMB.py")])
    
    #subprocess.run(["python", os.path.join(actionDir, "GeoJSON.py")])
    #subprocess.run(["python", os.path.join(actionDir, "KMB_Route.py")])
    #subprocess.run(["python", os.path.join(actionDir, "CTB_Route.py")])
    #subprocess.run(["python", os.path.join(actionDir, "NLB_Route.py")])
    #subprocess.run(["python", os.path.join(actionDir, "GMB_Route.py")])
    #subprocess.run(["python", os.path.join(actionDir, "MTR_BUS_Route.py")])

    end_time = time.time()  # End timer
    elapsed = end_time - start_time
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)
    print(f"Script finished in {minutes} minutes {seconds} seconds")

async def async_get_with_retry(client, url, retries=5, retryTimeout=180, **kwargs):
    for attempt in range(retries):
        try:
            response = await client.get(url, **kwargs)
            response.raise_for_status()
            return response
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            print(f"Attempt {attempt+1} failed: {e}. Retrying in {retryTimeout} seconds...")
            if attempt < retries - 1:
                await asyncio.sleep(retryTimeout)
            else:
                print(f"All {retries} attempts failed for {url}")
                raise e


def writeToJson(content, filename, indent=4) :
    outputDir = os.path.join(os.getcwd(), output_dir)
    if os.path.exists(outputDir) == False:
        os.mkdir(outputDir)

    outputJson = os.path.join (outputDir, filename + ".json")

    if os.path.exists(outputJson):
        os.remove(outputJson)

    with open(outputJson, 'w', encoding='UTF-8') as write_file:
        json.dump(content, write_file, indent=indent, ensure_ascii=False, separators=(',', ':'))
        #for item in content:
        #   write_file.write(json.dumps(item, ensure_ascii=False, separators=(',', ':')) + "\n")

def getCoordinate(stop, allStopList):
    for s in allStopList:
        if s['stop'] == stop:
            #print("Found stop: " + s['stop'] + " at " + s['lat'] + ", " + s['long'])
            return [s['lat'], s['long']]

def capWords(s) :
    # Use regex to exclude words enclosed in brackets
    def transform(word):
        # Check if the word matches the regular expression
        if re.match(r'\([A-Z]{2}\d{3}\)', word) or re.match(r'\([A-Z]\d\)', word):
            return word  # Skip processing for words matching the pattern
        # Apply title case to other words
        return word.title()

    # Split the string into words and process each word
    words = re.split(r'(\s+)', s)  # Split by whitespace while keeping separators
    processed_words = [transform(word) for word in words]
    r = ''.join(processed_words)

    r = re.sub(r'\'[A-Z]', lambda p: p.group(0).lower(), r)
    r = re.sub(r'Bbi', 'BBI', r)
    r = re.sub(r'Mtr\s', 'MTR ', r)
    r = re.sub(r'Plb\s', 'PLB ', r)
    r = re.sub(r'Hku\s', 'HKU ', r)
    r = re.sub(r'Hzmb\s', 'HZMB ', r)
    r = re.sub(r'Apm\s', 'APM ', r)
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
    r = re.sub(r'\bHk\b', 'HK', r)
    r = re.sub(r'\bHkust\b', 'HKUST', r)
    r = re.sub(r'\bHkcece\b', 'HKCECE', r)
    r = re.sub(r'\bHsbc\b', 'HSBC', r)
    return r

# Using the special variable 
# __name__
if __name__=="__main__":
    main()