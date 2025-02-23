import disnake
from disnake.ext import commands
import json
from colorama import *
from pathlib import Path

config_path = Path(__file__).resolve().parent.parent / "config.json"

with config_path.open("r") as config:
    config_data = json.load(config)

kickPermission = config_data["permissions"]["kick"]


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot  # Подключаем бота

    @commands.command()
    @commands.has_any_role(*kickPermission)
    async def kick(self, ctx, member: disnake.Member, *, reason: str = "Не указана"):
        await self.kick_action(ctx, member, reason)

    @commands.slash_command(name="kick", description="Кикнуть участника с сервера.")
    @commands.has_any_role(*kickPermission)
    async def kick_slash(self, inter: disnake.ApplicationCommandInteraction,
                         member: disnake.Member,
                         reason: str = "Не указана"):
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
    @kick_slash.error
    async def kick_error(self, ctx, error):
        if isinstance(error, commands.MissingAnyRole):
            await ctx.reply("<:cross:1343199131354665043> У вас недостаточно прав для использования этой команды.")
            print(
                Back.RED + f" Permission Error " + Back.WHITE + f" {ctx.command.qualified_name} " + Style.RESET_ALL + f" User: {ctx.author} ({ctx.author.id})")
        else:
            raise error


def setup(bot):
    bot.add_cog(Moderation(bot))  # Добавляем ког в бота
