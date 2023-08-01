import subprocess
import os

actionDir = os.path.join(os.getcwd(), "action")

subprocess.run(["python", os.path.join(actionDir, "KMB_Route.py")])
subprocess.run(["python", os.path.join(actionDir, "CTB_Route.py")])
subprocess.run(["python", os.path.join(actionDir, "NLB_Route.py")])
subprocess.run(["python", os.path.join(actionDir, "GMB_Route.py")])