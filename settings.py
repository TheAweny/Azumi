import json
from pathlib import Path

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

