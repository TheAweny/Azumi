# MODULES #
from logger import get_logger
import colorama
import disnake
import os
from disnake.ext import commands
from art import *
from colorama import *
from dotenv import load_dotenv
import json
from pathlib import Path


config_path = Path(__file__).resolve().parent / "config.json"
with config_path.open("r") as config:
    config_data = json.load(config)



# Initialization #
colorama.init()
logger = get_logger()
load_dotenv("secret.env")

print(Fore.RED)
print(text2art("AZUMI","roman"))
print(Style.RESET_ALL)

# CONST's #
TOKEN = os.environ["YOUR_BOT_TOKEN"]
JOIN_ROLE = 1342976859658256405


# EVENTS #
bot = commands.Bot(command_prefix={config_data["settings"]["prefix"]}, help_command=None, intents=disnake.Intents.all(), activity=disnake.Activity(name="Lo-Fi Radio", type=disnake.ActivityType.listening, url="https://www.youtube.com/watch?v=e94hCLHEEsk"))

@bot.event
async def on_ready():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            try:
                bot.load_extension(f"cogs.{filename[:-3]}")
                logger.info(f"Загружен модуль: {filename[:-3]}")
            except Exception as e:
                logger.error(f"Не удалось загрузить модуль {filename[:-3]}: {str(e)}")

    logger.info("Азуми готова управлять серверами :3")
    print()





bot.run(TOKEN)
