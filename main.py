

# MODULES #
from logger import get_logger
import colorama
import disnake
import os
from disnake.ext import commands
from art import *
from colorama import *
from dotenv import load_dotenv
from functions import botLang, getConfig, getLocale, redisConnect, redisCheckConnection
import time
import asyncio
import json

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
    )
)

@bot.event
async def on_ready():

    if not redisCheckConnection():
        logger.error(locale_data["debug"]["database"]["redisConnectionError"])
        os._exit(1)

    else:
        logger.info(locale_data["debug"]["database"]["redisConnected"])

    cogsCount, cogsLoaded = 0, 0
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            cogsCount += 1
            try:
                bot.load_extension(f"cogs.{filename[:-3]}")
                cogsLoaded += 1
                logger.info(locale_data["debug"]["cogs"]["loaded"].format(cog=filename[:-3]))
            except Exception as e:
                logger.error(locale_data["debug"]["cogs"]["loadException"].format(cog=filename[:-3], error=e))
    
    if cogsCount != cogsLoaded:
        if cogsLoaded == 0:
            print()
            logger.critical(locale_data["debug"]["cogs"]["allNotLoaded"])
            os._exit(1)

        print()
        logger.warning(locale_data["debug"]["cogs"]["someNotLoaded"].format(cogsCount=cogsCount, cogsLoaded=cogsLoaded))

    print()
    logger.info(locale_data["success"]["onReady"])
    print()
    
    
    while True:
        try:
            for key in redisConnect.keys("ban:*"):
                guild_id, user_id = key.split(":")[1], key.split(":")[2]
                ban_time = redisConnect.get(key)
                
            
                
                unbanTime = int(ban_time)
                if time.time() >= unbanTime:
                    guild = bot.get_guild(int(guild_id))
                    if guild:
                        user = await bot.get_or_fetch_user(int(user_id))
                        await guild.unban(user, reason="AUTO: Время блокировки истекло") 
                        redisConnect.delete(key)
                        get_logger().info(locale_data["moderation"]["autoUnban"].format(user_name=user.name, user_id=user.id, guild_name=guild.name, guild_id=guild.id))
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(locale_data["debug"]["moderation"]["autoUnbanError"].format(error=e) + "\n")
            if getConfig()["settings"]["locale"] == "ru":
                print(Fore.RED + Style.BRIGHT + "⚠️ ВНИМАНИЕ ⚠️:  Если данная ошибка возникает в исходном коде проекта, пожалуйста, сообщите разработчику в официальном дискорд сервере — https://discord.gg/bpaaKVsr")
            else:
                print(Fore.RED + Style.BRIGHT + "⚠️ ATTENTION ⚠️: If this error occurs in the project source code, please report it to the developer on the official Discord server — https://discord.gg/bpaaKVsr")
            break
        

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.reply(locale_data["general"]["commandNotFound"])
        logger.debug(locale_data["debug"]["commands"]["notFound"].format(ctx=ctx))
    else:
        logger.error(locale_data["debug"]["commands"]["error"].format(ctx=ctx, error=error))

bot.run(TOKEN)
