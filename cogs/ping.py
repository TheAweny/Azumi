import disnake
from disnake.ext import commands
import json
from pathlib import Path
from colorama import *
from functions import getConfig, getLocale



#   Permissions   #
ping = getConfig()["permissions"]["ping"]


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
        embed.add_field(name=getLocale()["commands"]["ping"]["field"], value=f"{bot_latency} ms", inline=False)
        embed.set_thumbnail(url=getConfig()["commands"]["ping"]["thumbnail"])

        await ctx.reply(embed=embed)

    @ping.error
    async def ping_error(self, ctx, error):
        if isinstance(error, commands.MissingAnyRole):
            await ctx.reply(getLocale()["general"]["noPermissions"])
            print(
                Back.RED + f" Permission Error " + Back.WHITE + f" {ctx.command.qualified_name} " + Style.RESET_ALL + f" User: {ctx.author} ({ctx.author.id})")
        else:
            raise error


def setup(bot):
    bot.add_cog(Ping(bot))
