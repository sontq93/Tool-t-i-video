import subprocess
import sys
try:
    process = subprocess.Popen([sys.executable, "app_v8.py"], cwd="/Users/chau/Downloads/tiktok_tool")
except Exception as e:
    pass
