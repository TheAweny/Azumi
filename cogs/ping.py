import disnake
from disnake.ext import commands
import json
from pathlib import Path
from colorama import *
from settings import getConfig, getLocale

config_data = getConfig()
locale_data = getLocale()

#   Permissions   #
ping = config_data["permissions"]["ping"]


class Ping(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_any_role(*ping)
    async def ping(self, ctx):
        bot_latency = round(self.bot.latency * 1000, 2)

        embed = disnake.Embed(
            title=getLocale()["commands"]["ping"]["title"],
            color=disnake.Color.blurple()
        )
        embed.add_field(name="🤖 Задержка бота", value=f"{bot_latency} ms", inline=False)
        embed.set_thumbnail(url="https://cdn.discordapp.com/avatars/1342942230083538990/0776e5775f168c55f11fce7ff198a4c8?size=256&quot")

        await ctx.reply(embed=embed)

    @ping.error
    async def ping_error(self, ctx, error):
        if isinstance(error, commands.MissingAnyRole):
            await ctx.reply(config_data[f"Text"]["noPermissions"])
            print(
                Back.RED + f" Permission Error " + Back.WHITE + f" {ctx.command.qualified_name} " + Style.RESET_ALL + f" User: {ctx.author} ({ctx.author.id})")
        else:
            raise error


def setup(bot):
    bot.add_cog(Ping(bot))
