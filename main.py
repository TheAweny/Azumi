# MODULES #
from logger import get_logger
import colorama
import disnake
import os
from disnake.ext import commands
from art import *
from colorama import *
from dotenv import load_dotenv
from settings import botLang, getConfig, getLocale

config_data = getConfig()
locale_data = getLocale()

# Initialization #
colorama.init()
logger = get_logger()
load_dotenv("secret.env")

print(Fore.RED)
print(text2art("AZUMI v0.1", "roman"))
print(Style.RESET_ALL)

# CONST's #
TOKEN = os.environ["YOUR_BOT_TOKEN"]

# EVENTS #
bot = commands.Bot(
    command_prefix=config_data["settings"]["prefix"],
    help_command=None,
    intents=disnake.Intents.all(),
    activity=disnake.Activity(
        name="Lo-Fi Radio",
        type=disnake.ActivityType.listening,
        url="https://www.youtube.com/watch?v=e94hCLHEEsk"
    )
)

@bot.event
async def on_ready():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            try:
                bot.load_extension(f"cogs.{filename[:-3]}")
                logger.info(locale_data["debug"]["cogLoaded"].format(cog=filename[:-3]))
            except Exception as e:
                logger.error(locale_data["debug"]["cogLoadException"].format(cog=filename[:-3], error=e))

    logger.info(locale_data["general"]["onReady"])
    print()

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.reply(locale_data["general"]["commandNotFound"], delete_after=10)
        logger.debug(locale_data["debug"]["commandNotFound"].format(ctx=ctx))
    else:
        logger.error(locale_data["debug"]["commandError"].format(ctx=ctx, error=error))

bot.run(TOKEN)
