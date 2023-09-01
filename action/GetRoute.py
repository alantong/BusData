import subprocess
import os
import re

def main() :
    print("main started")
    actionDir = os.path.join(os.getcwd(), "action")

    subprocess.run(["python", os.path.join(actionDir, "KMB_Route.py")])
    subprocess.run(["python", os.path.join(actionDir, "CTB_Route.py")])
    subprocess.run(["python", os.path.join(actionDir, "NLB_Route.py")])
    subprocess.run(["python", os.path.join(actionDir, "GMB_Route.py")])
    subprocess.run(["python", os.path.join(actionDir, "MTR_BUS_Route.py")])

def capWords(s) :
    r = s.title()
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
    return r

# Using the special variable 
# __name__
if __name__=="__main__":
    main()