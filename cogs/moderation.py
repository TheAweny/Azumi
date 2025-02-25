import disnake
from disnake.ext import commands
import json
from colorama import *
from pathlib import Path
from settings import getConfig, getLocale

config_data = getConfig()


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot  # Подключаем бота

    @commands.command()
    @commands.has_any_role(*config_data["permissions"]["kick"])
    async def kick(self, ctx, member: disnake.Member, *, reason: str = "Не указана"):
        if member == ctx.author:
            await ctx.reply(f"{ctx.author.mention}, ты не можешь кикнуть самого себя.", delete_after=15)
            await ctx.message.delete(delay=15)
            return

        # Проверяем, есть ли у кикера права выше, чем у цели
        if ctx.author.top_role <= member.top_role:
            await ctx.reply(
                f"{ctx.author.mention}, ты не можешь кикнуть {member}, так как его роль выше или равна твоей.",
                delete_after=15)
            await ctx.message.delete(delay=15)
            return

        await self.kick_action(ctx, member, reason)

    @commands.slash_command(name="kick", description="Кикнуть участника с сервера.")
    @commands.has_any_role(*config_data["permissions"]["kick"])
    async def kick_slash(self, inter: disnake.ApplicationCommandInteraction,
                         member: disnake.Member,
                         reason: str = "Не указана"):
        if inter.author == member:
            await inter.send(f"{inter.author.mention}, ты не можешь кикнуть самого себя.", ephemeral=True)
            return

        # Проверяем, есть ли у кикера права выше, чем у цели
        if inter.author.top_role <= member.top_role:
            await inter.send(
                f"{inter.author.mention}, ты не можешь кикнуть {member.mention}, так как его роль выше или равна твоей.",
                ephemeral=True)
            return

        await self.kick_action(inter, member, reason)

    async def kick_action(self, ctx, member: disnake.Member, reason: str):
        embed = disnake.Embed(
            title="🚨 Кик с сервера",
            description=f"**{member.mention} был кикнут**",
            color=disnake.Color.red()
        )
        embed.add_field(name="📌 Причина", value=reason, inline=False)
        embed.add_field(name="🔨 Модератор", value=ctx.author.mention, inline=False)
        embed.set_thumbnail(url=member.avatar.url if member.avatar else ctx.guild.icon.url)

        # Проверка, является ли ctx обычным сообщением или слеш-командой
        if isinstance(ctx, commands.Context):
            await ctx.send(embed=embed)
            await ctx.message.delete(delay=15)
        else:
            await ctx.response.send_message(embed=embed)

        await member.kick(reason=reason)

        print(Fore.RED + "ACTION " + Style.RESET_ALL + Style.BRIGHT +
              f"Модератор {ctx.author} кикнул {member} | Причина: {reason}" + Style.RESET_ALL)

    @kick.error
    async def kick_error(self, ctx, error):
        if isinstance(error, commands.MissingAnyRole):
            await ctx.reply(getLocale()["general"]["noPermissions"], delete_after=15)
            print(
                Back.RED + f" Permission Error " + Back.WHITE + f" {ctx.command.qualified_name} " + Style.RESET_ALL +
                f" User: {ctx.author} ({ctx.author.id})")
        else:
            raise

    @kick_slash.error
    async def kick_slash_error(self, inter, error):
        if isinstance(error, commands.MissingAnyRole):
            await inter.send(getLocale()["general"]["noPermissions"], ephemeral=True)
            print(
                Back.RED + f" Permission Error " + Back.WHITE + f" {inter.application_command.name} " + Style.RESET_ALL +
                f" User: {inter.author} ({inter.author.id})")
        else:
            raise error


def setup(bot):
    bot.add_cog(Moderation(bot))
