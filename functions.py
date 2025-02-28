import json
from pathlib import Path
import redis
from logger import get_logger
import re
import sys

logger = get_logger()

config_path = Path('__file__').resolve().parent / 'config.json'
with config_path.open('r', encoding="utf-8-sig") as config:
    config_data = json.load(config)

botLang = config_data["settings"]["locale"]

def getLocale():
    locale_path = Path("locales") / f"{botLang}.json"
    with locale_path.open(encoding="utf-8") as f:
        return json.load(f)

def getConfig():
    return config_data

redisConnect = redis.Redis(
    host=config_data["settings"]["Redis"]["host"],
    port=config_data["settings"]["Redis"]["port"],
    password=config_data["settings"]["Redis"]["password"],
    decode_responses=True
)


def redisCheckConnection():
    try:
        redisConnect.ping()
        return True
    except redis.ConnectionError:
        return False


def convertTime(time: str):
    match = re.match(r"(\d+)([shmd]$)", time)
    if not match:
        return None
    
    value, unit = int(match.group(1)), match.group(2)
    multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400}

    return value * multipliers[unit]


