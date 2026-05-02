import os
import sys
# Add parent directory to path to allow importing our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import Config

print(f"CWD: {os.getcwd()}")
print(f"RCON_PASSWORD: {Config.RCON_PASSWORD}")
