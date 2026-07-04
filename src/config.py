import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent.parent
LOGS_DIR = ROOT_DIR / "logs"

LOGS_DIR.mkdir(exist_ok=True)

WEBULL_EMAIL     = os.environ["WEBULL_EMAIL"]
WEBULL_PASSWORD  = os.environ["WEBULL_PASSWORD"]
WEBULL_TRADE_PIN = os.environ["WEBULL_TRADE_PIN"]
WEBULL_DEVICE_ID = os.environ.get("WEBULL_DEVICE_ID", "")
