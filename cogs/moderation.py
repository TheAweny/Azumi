import disnake
from disnake.ext import commands
import json
from colorama import *
from pathlib import Path
from functions import getConfig, getLocale, convertTime, redisConnect
from logger import get_logger
import time
import re
from datetime import datetime



class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot  # Подключаем бота



    #    KICK    #

    @commands.command()
    @commands.has_any_role(*getConfig()["permissions"]["kick"])
    async def kick(self, ctx, member: disnake.Member, *, reason: str = getLocale()["info"]["defaultReason"]):
        if member == ctx.author:
            await ctx.reply(getLocale()["errors"]["selfAction"]["kick"].format(authorMention=ctx.author.mention))
            await ctx.message.delete(delay=15)
            return

        # Проверяем, есть ли у кикера права выше, чем у цели
        if ctx.author.top_role <= member.top_role:
            await ctx.reply(getLocale()["errors"]["highRole"]["kick"].format(authorMention=ctx.author.mention))
            await ctx.message.delete(delay=15)
            return

        await self.kick_action(ctx, member, reason)

    @commands.slash_command(name="kick", description="Кикнуть участника с сервера.")
    @commands.has_any_role(*getConfig()["permissions"]["kick"])
    async def kick_slash(self, inter: disnake.ApplicationCommandInteraction,
                         member: disnake.Member = commands.Param(description="ID или @пользователь"),
                         reason: str = commands.Param(default=getLocale()["info"]["defaultReason"], description="Причина")):
        if inter.author == member:
            await inter.send(getLocale()["errors"]["selfAction"]["kick"].format(authorMention=inter.author.mention), ephemeral=True)
            return

        # Проверяем, есть ли у кикера права выше, чем у цели
        if inter.author.top_role <= member.top_role:
            await inter.send(getLocale()["errors"]["highRole"]["kick"].format(authorMention=inter.author.mention), ephemeral=True)
            return

        await self.kick_action(inter, member, reason)

    async def kick_action(self, ctx, member: disnake.Member, reason: str):
        embed = disnake.Embed(
            title=getLocale()["moderation"]["actions"]["kick"]["title"],
            description=getLocale()["moderation"]["actions"]["kick"]["description"].format(memberMention=member.mention),
            color=disnake.Color.red()
        )
        embed.add_field(name=getLocale()["moderation"]["common"]["reason"], value=reason, inline=False)
        embed.add_field(name=getLocale()["moderation"]["common"]["moderator"], value=ctx.author.mention, inline=False)
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
            await ctx.reply(getLocale()["errors"]["noPermissions"])
            print(
                Back.RED + f" Permission Error " + Back.WHITE + f" {ctx.command.qualified_name} " + Style.RESET_ALL +
                f" User: {ctx.author} ({ctx.author.id})")
        else:
            raise

    @kick_slash.error
    async def kick_slash_error(self, inter, error):
        if isinstance(error, commands.MissingAnyRole):
            await inter.send(getLocale()["errors"]["noPermissions"], ephemeral=True)
            print(
                Back.RED + f" Permission Error " + Back.WHITE + f" {inter.application_command.name} " + Style.RESET_ALL +
                f" User: {inter.author} ({inter.author.id})")
        else:
            raise error
    
    #    BAN | In dev...  #


    @commands.command()
    @commands.has_any_role(*getConfig()["permissions"]["ban"])
    async def ban(self, ctx, member: str, *, reason: str = None):
        time = None
        convertedTime = None  

        if reason and (match := re.match(r"(\d+[smhd])\s*(.*)", reason)):  
            time, reason = match.groups()
            convertedTime = convertTime(time)
            reason = reason or getLocale()["info"]["defaultReason"]

        if convertedTime is None and time is not None:
            await ctx.reply(getLocale()["errors"]["invalidTime"])
            return

        match = re.match(r'<@!?(\d+)>', member)
        if match:
            member_id = int(match.group(1))
        elif member.isdigit():
            member_id = int(member)
        else:
            await ctx.send(getLocale()["errors"]["error"])
            return

        try:
            user_obj = await self.bot.fetch_user(member_id)
        except disnake.NotFound:
            await ctx.send(getLocale()["errors"]["unbanError"].format(memberMention=member))
            return

        await self.ban_action(ctx, member_id, reason or getLocale()["info"]["defaultReason"], convertedTime)

    @commands.slash_command(name="ban", description="Заблокировать пользователя на сервере.")
    @commands.has_any_role(*getConfig()["permissions"]["ban"])
    async def ban_slash(self, inter: disnake.ApplicationCommandInteraction,
                        member: str = commands.Param(description="ID или @пользователь"),
                        time: str = commands.Param(default=None, description="Время (1s, 1m, 1h, 1d)"),
                        reason: str = commands.Param(default="Не указана", description="Причина")):
        await self.ban_action(inter, member, reason, time)

    async def ban_action(self, ctx, user_id: int, reason: str, ban_time: int = None):
        try:
            user_obj = disnake.Object(id=user_id)  # Создаём объект пользователя для бана

            # Сохраняем бан во временном хранилище, если задано время
            if ban_time and ban_time > 0:
                expiry_time = int(time.time()) + ban_time
                redisConnect.set(f"ban:{ctx.guild.id}:{user_id}", str(expiry_time))

            # Попытка получить объект пользователя (если он существует)
            user = None
            try:
                user = await self.bot.fetch_user(user_id)
                await user.send(getLocale()["moderation"]["actions"]["ban"]["banMessage"].format(
                    reason=reason,
                    time=ban_time if ban_time else "∞",
                    guildMention=ctx.guild.name
                ))
            except disnake.Forbidden:
                print(f"Не удалось отправить сообщение пользователю {user_id} перед баном.")
            except disnake.NotFound:
                print(f"Пользователь с ID {user_id} не найден, но он всё равно будет забанен.")

            # Бан по ID
            await ctx.guild.ban(user_obj, reason=f"{reason} | Модератор: {ctx.author.name} (ID: {ctx.author.id}) | Время: {ban_time if ban_time else '∞'}")

            # Создание Embed
            embed = disnake.Embed(
                title=getLocale()["moderation"]["actions"]["ban"]["title"],
                description=getLocale()["moderation"]["actions"]["ban"]["description"].format(memberMention=f"<@{user_id}>"),
                color=disnake.Color.red()
            )
            embed.add_field(name=getLocale()["moderation"]["common"]["reason"], value=reason, inline=False)
            embed.add_field(name=getLocale()["moderation"]["common"]["moderator"], value=ctx.author.mention, inline=False)
            embed.set_thumbnail(url=user.avatar.url if user and user.avatar else ctx.guild.icon.url)

            # Отправка Embed в чат
            if isinstance(ctx, commands.Context):
                await ctx.send(embed=embed)
                await ctx.message.delete(delay=15)
            else:
                await ctx.response.send_message(embed=embed)

            # Логирование
            get_logger().debug(getLocale()["debug"]["moderation"]["ban"].format(
                member_name=user.name if user else "Unknown",
                member_id=user_id,
                guild_name=ctx.guild.name,
                guild_id=ctx.guild.id,
                reason=reason,
                moderator_name=ctx.author.name,
                moderator_id=ctx.author.id,
                time=ban_time if ban_time else "∞"
            ))

        except Exception as e:
            get_logger().error(f"Ошибка при бане пользователя {user_id}: {e}")
            await ctx.send(getLocale()["errors"]["error"])


    @commands.command()
    @commands.has_any_role(*getConfig()["permissions"]["unban"])
    async def unban(self, ctx, user: str, *, reason: str = commands.Param(default="Не указана", description="Причина бана")):
        await self.unban_action(ctx, user, reason)

    @commands.slash_command(name="unban", description="Разблокировать пользователя на сервере.")
    @commands.has_any_role(*getConfig()["permissions"]["unban"])
    async def unban_slash(self, inter: disnake.ApplicationCommandInteraction, user: str = commands.Param(description="ID или @пользователь"), reason: str = commands.Param(default="None", description="Причина бана")):
        await self.unban_action(inter, user, reason)

    async def unban_action(self, ctx, user: str, reason: str = "Не указана"):
        match = re.match(r'<@!?(\d+)>', user)
        if match:
            user_id = match.group(1)
        elif user.isdigit():
            user_id = user
        else:
            if isinstance(ctx, commands.Context):
                await ctx.send(getLocale()["errors"]["error"])
            else:
                await ctx.response.send_message(getLocale()["errors"]["error"], ephemeral=True)
            return

        try:
            user_obj = await self.bot.fetch_user(int(user_id))
        except disnake.NotFound:
            if isinstance(ctx, commands.Context):
                await ctx.send(getLocale()["errors"]["unbanError"].format(memberMention=user))
            else:
                await ctx.response.send_message(
                    getLocale()["errors"]["unbanError"].format(memberMention=user),
                    ephemeral=True
                )
            return

        if redisConnect.exists(f"ban:{ctx.guild.id}:{user_obj.id}"):
            if not redisConnect.delete(f"ban:{ctx.guild.id}:{user_obj.id}"):
                get_logger().error(getLocale()["debug"]["moderation"]["unbanError"].format(
                    error="Redis error",
                    member_id=user_obj.id,
                    guild_id=ctx.guild.id,
                    moderator_id=ctx.author.id
                ))
                if isinstance(ctx, commands.Context):
                    await ctx.send(getLocale()["errors"]["error"])
                else:
                    await ctx.response.send_message(getLocale()["errors"]["error"], ephemeral=True)
                return

            get_logger().debug(getLocale()["debug"]["moderation"]["unban"].format(
                member_name=user_obj.name,
                member_id=user_obj.id,
                guild_name=ctx.guild.name,
                guild_id=ctx.guild.id,
                reason=reason,
                moderator_name=ctx.author.name,
                moderator_id=ctx.author.id
            ))

        try:
            await ctx.guild.unban(user_obj, reason=f"{reason} | Moderator: {ctx.author.name} (ID: {ctx.author.id})")

            if isinstance(ctx, commands.Context):
                await ctx.reply(getLocale()["success"]["unban"].format(memberMention=user_obj.mention))
            else:
                await ctx.response.send_message(
                    getLocale()["success"]["unban"].format(memberMention=user_obj.mention))
            get_logger().debug(getLocale()["debug"]["moderation"]["unban"].format(
                member_name=user_obj.name,
                member_id=user_obj.id,
                guild_name=ctx.guild.name,
                guild_id=ctx.guild.id,
                reason=reason,
                moderator_name=ctx.author.name,
                moderator_id=ctx.author.id
            ))
        except disnake.NotFound:
            if isinstance(ctx, commands.Context):
                await ctx.send(getLocale()["errors"]["unbanError"].format(memberMention=user_obj.mention))
            else:
                await ctx.response.send_message(
                    getLocale()["errors"]["unbanError"].format(memberMention=user_obj.mention),
                    ephemeral=True
                )
        except disnake.Forbidden:
            if isinstance(ctx, commands.Context):
                await ctx.send(getLocale()["errors"]["noPermissions"])
            else:
                await ctx.response.send_message(getLocale()["errors"]["noPermissions"], ephemeral=True)
        except Exception as e:
            get_logger().error(getLocale()["debug"]["moderation"]["unbanError"].format(
                error=e,
                member_name=user_obj.name,
                member_id=user_obj.id,
                guild_name=ctx.guild.name,
                guild_id=ctx.guild.id,
                moderator_id=ctx.author.id
            ))
            if isinstance(ctx, commands.Context):
                await ctx.send(getLocale()["errors"]["error"])
            else:
                await ctx.response.send_message(getLocale()["errors"]["error"], ephemeral=True)

    @commands.command()
    @commands.has_any_role(*getConfig()["permissions"]["mute"])
    async def mute(self, ctx, member: disnake.Member, time: str, *, reason: str = getLocale()["info"]["defaultReason"]):
        await self.timeout_action(ctx, member, time, reason)

    @commands.slash_command(name="mute", description="Замутить участника на сервере.")
    @commands.has_any_role(*getConfig()["permissions"]["mute"])
    async def mute_slash(self, inter: disnake.ApplicationCommandInteraction,
                         member: disnake.Member = commands.Param(description="ID или @пользователь"),
                         time: str = commands.Param(description="Время (1s, 1m, 1h, 1d)"),
                         reason: str = commands.Param(default=getLocale()["info"]["defaultReason"], description="Причина")):
        await self.timeout_action(inter, member, time, reason)

    async def timeout_action(self, ctx, member: disnake.Member, time: str, reason: str):
        if member == ctx.author:
            if isinstance(ctx, commands.Context):
                await ctx.reply(getLocale()["errors"]["selfAction"]["mute"].format(authorMention=ctx.author.mention))
                await ctx.message.delete(delay=15)
            else:
                await ctx.response.send_message(getLocale()["errors"]["selfAction"]["mute"].format(authorMention=ctx.author.mention), ephemeral=True)
            return

        # Проверяем, есть ли у мутящего права выше, чем у цели
        if ctx.author.top_role <= member.top_role:
            if isinstance(ctx, commands.Context):
                await ctx.reply(getLocale()["errors"]["highRole"]["mute"].format(authorMention=ctx.author.mention))
                await ctx.message.delete(delay=15)
            else:
                await ctx.response.send_message(getLocale()["errors"]["highRole"]["mute"].format(authorMention=ctx.author.mention), ephemeral=True)
            return

        # Конвертируем время
        converted_time = convertTime(time)
        if converted_time is None:
            if isinstance(ctx, commands.Context):
                await ctx.reply(getLocale()["errors"]["invalidTime"])
                await ctx.message.delete(delay=15)
            else:
                await ctx.response.send_message(getLocale()["errors"]["invalidTime"], ephemeral=True)
            return

        try:
            
            await member.timeout(duration=converted_time, reason=f"{reason} | Модератор: {ctx.author.name} (ID: {ctx.author.id})")

            
            embed = disnake.Embed(
                title=getLocale()["moderation"]["actions"]["mute"]["title"],
                description=getLocale()["moderation"]["actions"]["mute"]["description"].format(memberMention=member.mention),
                color=disnake.Color.orange()
            )
            embed.add_field(
                name=getLocale()["moderation"]["actions"]["mute"]["duration"],
                value=time,
                inline=True
            )
            embed.add_field(
                name=getLocale()["moderation"]["common"]["reason"],
                value=reason,
                inline=True
            )
            embed.add_field(
                name=getLocale()["moderation"]["common"]["moderator"],
                value=ctx.author.mention,
                inline=False
            )
            embed.set_thumbnail(url=member.avatar.url if member.avatar else ctx.guild.icon.url)

            
            if isinstance(ctx, commands.Context):
                await ctx.send(embed=embed)
                await ctx.message.delete(delay=15)
            else:
                await ctx.response.send_message(embed=embed)

            get_logger().debug(getLocale()["debug"]["moderation"]["mute"].format(
                member_name=member.name,
                member_id=member.id,
                guild_name=ctx.guild.name,
                guild_id=ctx.guild.id,
                time=time,
                reason=reason,
                moderator_name=ctx.author.name,
                moderator_id=ctx.author.id
            ))

        except Exception as e:
            get_logger().error(getLocale()["debug"]["moderation"]["muteError"].format(
                error=e,
                member_name=member.name,
                member_id=member.id,
                guild_name=ctx.guild.name,
                guild_id=ctx.guild.id,
                moderator_id=ctx.author.id
            ))
            if isinstance(ctx, commands.Context):
                await ctx.send(getLocale()["errors"]["error"])
            else:
                await ctx.response.send_message(getLocale()["errors"]["error"], ephemeral=True)

    
    @mute.error
    async def mute_error(self, ctx, error):
        if isinstance(error, commands.MissingAnyRole):
            await ctx.reply(getLocale()["errors"]["noPermissions"])
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply(f"Пожалуйста, укажите пользователя и время мута. Пример использования команды: `{getConfig()['settings']['prefix']}mute @user <Время (1s, 1m, 1h, 1d)> <Причина>`")
        else:
            raise

    @mute_slash.error
    async def mute_slash_error(self, inter, error):
        if isinstance(error, commands.MissingAnyRole):
            await inter.send(getLocale()["errors"]["noPermissions"], ephemeral=True)
        elif isinstance(error, commands.MissingRequiredArgument):
            await inter.send(f"Не указан обязательный аргумент: {error.param.name}")
        else:
            raise

    @commands.command()
    @commands.has_any_role(*getConfig()["permissions"]["mute"])
    async def unmute(self, ctx, member: disnake.Member, *, reason: str = getLocale()["info"]["defaultReason"]):
        await self.unmute_action(ctx, member, reason)

    @commands.slash_command(name="unmute", description="Снять ограничения чата с участника сервера.")
    @commands.has_any_role(*getConfig()["permissions"]["mute"])
    async def unmute_slash(self, inter: disnake.ApplicationCommandInteraction,
                        member: disnake.Member = commands.Param(description="ID или @пользователь"),
                        reason: str = commands.Param(default=getLocale()["info"]["defaultReason"], description="Причина")):
        await self.unmute_action(inter, member, reason)

    async def unmute_action(self, ctx, member: disnake.Member, reason: str):
        if ctx.author.top_role <= member.top_role:
            if isinstance(ctx, commands.Context):
                await ctx.reply(getLocale()["errors"]["highRole"]["mute"].format(authorMention=ctx.author.mention))
                await ctx.message.delete(delay=15)
            else:
                await ctx.response.send_message(getLocale()["errors"]["highRole"]["mute"].format(authorMention=ctx.author.mention), ephemeral=True)
            return

        try:
            # Remove timeout
            await member.timeout(duration=None, reason=f"{reason} | Модератор: {ctx.author.name} (ID: {ctx.author.id})")
            
            # Create embed response
            embed = disnake.Embed(
                title="Размут",
                description=f"Ограничения чата сняты с пользователя {member.mention}",
                color=disnake.Color.green()
            )
            
            embed.add_field(
                name=getLocale()["moderation"]["common"]["reason"],
                value=reason,
                inline=True
            )
            
            embed.add_field(
                name=getLocale()["moderation"]["common"]["moderator"],
                value=ctx.author.mention,
                inline=False
            )
            
            embed.set_thumbnail(url=member.avatar.url if member.avatar else ctx.guild.icon.url)
            
            if isinstance(ctx, commands.Context):
                await ctx.send(embed=embed)
                await ctx.message.delete(delay=15)
            else:
                await ctx.response.send_message(embed=embed)

            get_logger().debug(f"Модератор {ctx.author.name} ({ctx.author.id}) снял ограничения чата с {member.name} ({member.id}) на сервере {ctx.guild.name} ({ctx.guild.id}). Причина: {reason}")

        except Exception as e:
            get_logger().error(f"Ошибка при снятии ограничений чата: {e}, пользователь: {member.name} ({member.id}), сервер: {ctx.guild.name} ({ctx.guild.id}), модератор ID: {ctx.author.id}")
            
            if isinstance(ctx, commands.Context):
                await ctx.send(getLocale()["errors"]["error"])
            else:
                await ctx.response.send_message(getLocale()["errors"]["error"], ephemeral=True)

    @unmute.error
    async def unmute_error(self, ctx, error):
        if isinstance(error, commands.MissingAnyRole):
            await ctx.reply(getLocale()["errors"]["noPermissions"])
            print(
                Back.RED + f" Permission Error " + Back.WHITE + f" {ctx.command.qualified_name} " + Style.RESET_ALL +
                f" User: {ctx.author} ({ctx.author.id})")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply(f"Пожалуйста, укажите ID или @пользователя для снятия мута. Пример использования команды: `{getConfig()['settings']['prefix']}unmute @user <Причина>`")
        else:
            raise


    @unmute_slash.error
    async def unmute_slash_error(self, inter, error):
        if isinstance(error, commands.MissingAnyRole):
            await inter.send(getLocale()["errors"]["noPermissions"], ephemeral=True)
            print(
                Back.RED + f" Permission Error " + Back.WHITE + f" {inter.application_command.name} " + Style.RESET_ALL +
                f" User: {inter.author} ({inter.author.id})")
        elif isinstance(error, commands.MissingRequiredArgument):
            await inter.send(f"Пожалуйста, укажите ID или @пользователя для снятия мута. Пример использования команды: `{getConfig()['settings']['prefix']}unmute @user <Причина>`")
        else:
            raise error
    
    
    @commands.command()
    @commands.has_any_role(*getConfig()["permissions"]["clear"])
    async def clear(self, ctx, *args, reason: str = None):
        amount = 10
        user = None

        for arg in args:
            if arg.isdigit():
                amount = int(arg)
            elif ctx.message.mentions:
                user = ctx.message.mentions[0]

        await self.clear_action(ctx, amount, user, reason)

    @commands.slash_command(name="clear", description="Очистить сообщения в канале.")
    @commands.has_any_role(*getConfig()["permissions"]["clear"])
    async def clear_slash(self, inter: disnake.ApplicationCommandInteraction,
                          amount: int = commands.Param(default=10, description="Количество сообщений (макс. 100)"),
                          user: disnake.User = commands.Param(default=None, description="ID или @пользователь"),
                          reason: str = commands.Param(default=None, description="Причина")):
        await self.clear_action(inter, amount, user, reason)

    async def clear_action(self, ctx, amount: int, user: disnake.User = None, reason: str = None):
        if amount <= 0 or amount > 100:
            if isinstance(ctx, commands.Context):
                await ctx.send(getLocale()["errors"]["clear"]["invalidAmount"])
            else:
                await ctx.response.send_message(getLocale()["errors"]["clear"]["invalidAmount"], ephemeral=True)
            return

        try:
            if isinstance(ctx, commands.Context):
                await ctx.message.delete()
            
            deleted_messages = []
            if user:
                messages = [msg async for msg in ctx.channel.history(limit=amount * 5) if msg.author == user]
                deleted_messages = messages[:amount]
                await ctx.channel.delete_messages(deleted_messages)
            else:
                deleted_messages = await ctx.channel.purge(limit=amount)

            embed = disnake.Embed(
                title=getLocale()["moderation"]["actions"]["clear"]["title"],
                color=disnake.Color.blue()
            )
            
            if user:
                embed.description = getLocale()["moderation"]["actions"]["clear"]["userDescription"].format(
                    deletedAmount=len(deleted_messages), channelMention=ctx.channel.mention, userMention=user.mention)
            else:
                embed.description = getLocale()["moderation"]["actions"]["clear"]["description"].format(
                    deletedAmount=len(deleted_messages), channelMention=ctx.channel.mention)
            
            embed.add_field(name=getLocale()["moderation"]["common"]["moderator"], value=ctx.author.mention, inline=False)
            if reason:
                embed.add_field(name=getLocale()["moderation"]["common"]["reason"], value=reason, inline=False)
            
            if isinstance(ctx, commands.Context):
                await ctx.send(embed=embed)
            else:
                await ctx.response.send_message(embed=embed)

            # Логирование
            if user:
                get_logger().debug(getLocale()["debug"]["moderation"]["clearUser"].format(
                    moderator_name=ctx.author.name,
                    moderator_id=ctx.author.id,
                    amount=len(deleted_messages),
                    user_name=user.name,
                    user_id=user.id,
                    channel_name=ctx.channel.name,
                    channel_id=ctx.channel.id,
                    guild_name=ctx.guild.name,
                    guild_id=ctx.guild.id,
                    reason=reason or getLocale()["info"]["defaultReason"]
                ))
            else:
                get_logger().debug(getLocale()["debug"]["moderation"]["clear"].format(
                    moderator_name=ctx.author.name,
                    moderator_id=ctx.author.id,
                    amount=len(deleted_messages),
                    channel_name=ctx.channel.name,
                    channel_id=ctx.channel.id,
                    guild_name=ctx.guild.name,
                    guild_id=ctx.guild.id,
                    reason=reason or getLocale()["info"]["defaultReason"]
                ))

        except disnake.Forbidden:
            error_msg = "У бота недостаточно прав для удаления сообщений"
            if isinstance(ctx, commands.Context):
                await ctx.send(error_msg)
            else:
                await ctx.response.send_message(error_msg, ephemeral=True)
            get_logger().error(getLocale()["debug"]["moderation"]["clearError"].format(
                error="Forbidden",
                channel_name=ctx.channel.name,
                channel_id=ctx.channel.id,
                guild_name=ctx.guild.name,
                guild_id=ctx.guild.id,
                moderator_id=ctx.author.id
            ))
            
        except disnake.HTTPException as e:
            error_msg = "Не удалось удалить некоторые сообщения (возможно они старше 14 дней)"
            if isinstance(ctx, commands.Context):
                await ctx.send(error_msg)
            else:
                await ctx.response.send_message(error_msg, ephemeral=True)
            get_logger().error(f"HTTP ошибка при очистке сообщений: {str(e)}")
            
        except Exception as e:
            get_logger().error(f"Неожиданная ошибка при очистке сообщений: {repr(e)}")
            if isinstance(ctx, commands.Context):
                await ctx.send(getLocale()["errors"]["error"])
            else:
                await ctx.response.send_message(getLocale()["errors"]["error"], ephemeral=True)

    @clear.error
    async def clear_error(self, ctx, error):
        if isinstance(error, commands.MissingAnyRole):
            await ctx.send(getLocale()["errors"]["noPermissions"])
        else:
            pass

    @clear_slash.error
    async def clear_slash_error(self, inter, error):
        if isinstance(error, commands.MissingAnyRole):
            await inter.send(getLocale()["errors"]["noPermissions"], ephemeral=True)
        else:
            pass

    
    # WARN | In dev... #

    @commands.command()
    @commands.has_any_role(*getConfig()["permissions"]["warn"])
    async def warn(self, ctx, member: disnake.Member, *args):
        # Объединяем все аргументы в одну строку
        args_str = ' '.join(args)
        
        # Проверяем первый аргумент на соответствие формату времени
        time_match = re.match(r'^(\d+[smhd])\s*(.*)', args_str)
        
        if time_match:
            time, reason = time_match.groups()
            reason = reason if reason else getLocale()["general"]["defaultReason"]
        else:
            time = None
            reason = args_str if args_str else getLocale()["general"]["defaultReason"]

        if member == ctx.author:
            await ctx.reply(getLocale()["errors"]["selfAction"]["warn"].format(authorMention=ctx.author.mention))
            return
        
        if ctx.author.top_role <= member.top_role:
            await ctx.reply(getLocale()["errors"]["highRole"]["warn"].format(authorMention=ctx.author.mention))
            return
        
        await self.warn_action(ctx, member, time, reason)

    @commands.slash_command(name="warn", description=getLocale()["slash"]["commands"]["warn"]["description"])
    @commands.has_any_role(*getConfig()["permissions"]["warn"])
    async def warn_slash(self, inter: disnake.ApplicationCommandInteraction,
                         member: disnake.Member = commands.Param(description="ID или @пользователь"),
                         reason: str = commands.Param(default=getLocale()["general"]["defaultReason"], description="Причина"),
                         time: str = commands.Param(default=getConfig()["commands"]["warn"]["defaultTime"], description=getLocale()["slash"]["commands"]["warn"]["options"]["time"]["description"])):
        if inter.author == member:
            await inter.send(getLocale()["errors"]["selfAction"]["warn"].format(authorMention=inter.author.mention), ephemeral=True)
            return
        
        if inter.author.top_role <= member.top_role:
            await inter.send(getLocale()["errors"]["highRole"]["warn"].format(authorMention=inter.author.mention), ephemeral=True)
            return
        
        await self.warn_action(inter, member, time, reason)

    async def warn_action(self, ctx, member: str, time: str, reason: str):
        expiry_time = None
        
        if time:
            converted_time = convertTime(time)
            if converted_time is None:
                if isinstance(ctx, commands.Context):
                    await ctx.send(getLocale()["errors"]["invalidTime"])
                else:
                    await ctx.response.send_message(getLocale()["errors"]["invalidTime"], ephemeral=True)
                return
            expiry_time = int(datetime.now().timestamp()) + converted_time

        warn_id = f"warn:{ctx.guild.id}:{member.id}:{int(datetime.now().timestamp())}"

        warn_data = {
            "user_id": member.id,
            "guild_id": ctx.guild.id,
            "reason": reason,
            "moderator_id": ctx.author.id,
            "timestamp": int(datetime.now().timestamp()),
            "expiry": expiry_time
        }

        redisConnect.set(warn_id, json.dumps(warn_data))
        if expiry_time:
            redisConnect.expireat(warn_id, expiry_time)

        user_warnsKey = f"warns:{ctx.guild.id}:{member.id}"
        redisConnect.lpush(user_warnsKey, warn_id)

        embed = disnake.Embed(
            title=getLocale()["moderation"]["actions"]["warn"]["title"],
            description=getLocale()["moderation"]["actions"]["warn"]["description"].format(memberMention=member.mention),
            color=disnake.Color.yellow()
        )

        embed.add_field(name=getLocale()["moderation"]["common"]["reason"], value=reason, inline=True)
        if expiry_time:
            time_str = time if time else getConfig()["commands"]["warn"]["defaultTime"]
            embed.add_field(
                name=getLocale()["moderation"]["actions"]["warn"]["duration"],
                value=time_str,
                inline=True
            )

        embed.add_field(name=getLocale()["moderation"]["common"]["moderator"], value=ctx.author.mention, inline=True)
        embed.set_thumbnail(url=member.avatar.url if member.avatar else ctx.guild.icon.url)

        if isinstance(ctx, commands.Context):
            await ctx.send(embed=embed)
        else:
            await ctx.response.send_message(embed=embed)


        try:
            user_embed = disnake.Embed(
                title=getLocale()["moderation"]["actions"]["warn"]["userTitle"],
                description=getLocale()["moderation"]["actions"]["warn"]["userDescription"].format(guildName=ctx.guild.name),
                color=disnake.Color.yellow()
            )

            user_embed.add_field(name=getLocale()["moderation"]["common"]["reason"], value=reason, inline=True)
            user_embed.add_field(name=getLocale()["moderation"]["common"]["moderator"], value=ctx.author.mention, inline=True)
            user_embed.set_thumbnail(url=member.avatar.url if member.avatar else ctx.guild.icon.url)

            if expiry_time:
                time_str = time if time else getConfig()["commands"]["warn"]["defaultTime"]
                user_embed.add_field(
                    name=getLocale()["moderation"]["actions"]["warn"]["duration"],
                    value=time_str,
                    inline=True
                )
        
            await member.send(embed=user_embed)

        except disnake.Forbidden:
            get_logger().warning(f"Не удалось отправить предупреждение пользователю {member.name} ({member.id}) на сервере {ctx.guild.name} ({ctx.guild.id}). Причина: Forbidden")
            pass

        except Exception as e:
            get_logger().error(f"Ошибка при отправке предупреждения: {e}")

        get_logger().debug(getLocale()["debug"]["moderation"]["warn"].format(
            member_name=member.name,
            member_id=member.id,
            guild_name=ctx.guild.name,
            guild_id=ctx.guild.id,
            reason=reason,
            moderator_name=ctx.author.name,
            moderator_id=ctx.author.id,
            time=time if time else "∞"
        ))

        await self.check_warnThresholds(ctx, member)

    async def check_warnThresholds(self, ctx, member: disnake.Member):
        user_warnsKey = f"warns:{ctx.guild.id}:{member.id}"
        warn_ids = redisConnect.lrange(user_warnsKey, 0, -1)
        
        if not warn_ids:
            return
        
        # Подсчитываем только активные предупреждения
        current_time = int(time.time())
        active_warns = 0
        
        for warn_id in warn_ids:
            warn_data_json = redisConnect.get(warn_id)
            if warn_data_json:
                try:
                    warn_data = json.loads(warn_data_json)
                    # Предупреждение активно если оно бессрочное или не истекло
                    if warn_data.get("expiry") is None or warn_data.get("expiry") > current_time:
                        active_warns += 1
                except json.JSONDecodeError:
                    continue
        
        warn_threshold = getConfig().get("warning_thresholds", {})
        
        # Сортируем пороги по убыванию, чтобы применять самое строгое наказание
        thresholds = sorted([int(t) for t in warn_threshold.keys()], reverse=True)
        
        for threshold in thresholds:
            if active_warns >= threshold:
                punishment = warn_threshold[str(threshold)]
                punishment_type = punishment.get("type")
                punishment_duration = punishment.get("duration")
                punishment_reason = punishment.get("reason", getLocale()["moderation"]["actions"]["warn"]["autoReason"])

                try:
                    if punishment_type == "timeout":
                        await self.timeout_action(ctx, member, punishment_duration, punishment_reason)
                    elif punishment_type == "kick":
                        await self.kick_action(ctx, member, punishment_reason)
                    elif punishment_type == "ban":
                        if isinstance(member, str):
                            user_id = member
                        else:
                            user_id = member.id
                        await self.ban_action(ctx, user_id, punishment_reason, convertTime(punishment_duration) if punishment_duration else None)

                    embed = disnake.Embed(
                        title=getLocale()["moderation"]["actions"]["warn"]["punishmentTitle"],
                        description=getLocale()["moderation"]["actions"]["warn"]["punishmentDescription"].format(
                            memberMention=member.mention,
                            warnCount=active_warns,
                            punishmentType=punishment_type
                        ),
                        color=disnake.Color.red()
                    )
                    
                    if isinstance(ctx, commands.Context):
                        await ctx.send(embed=embed)
                    else:
                        await ctx.response.send_message(embed=embed)
                    
                    get_logger().debug(getLocale()["debug"]["moderation"]["warnPunishment"].format(
                        member_name=member.name,
                        member_id=member.id,
                        guild_name=ctx.guild.name,
                        guild_id=ctx.guild.id,
                        warning_count=active_warns,
                        punishment_type=punishment_type,
                        punishment_duration=punishment_duration if punishment_duration else "∞"
                    ))
                    
                    break  # Применяем только одно наказание
                    
                except Exception as e:
                    get_logger().error(f"Ошибка при применении наказания {punishment_type}: {e}")

    @commands.command()
    async def warnings(self, ctx, member: disnake.Member = None):
        if member is None:
            member = ctx.author
        
        await self.show_warnings(ctx, member)

    @commands.slash_command(name="warnings", description="Показать предупреждения пользователя")
    async def warnings_slash(self, inter: disnake.ApplicationCommandInteraction,
                        member: disnake.Member = commands.Param(default=None, description="ID или @пользователь")):
        if member is None:
            member = inter.author
        
        await self.show_warnings(inter, member)

    async def show_warnings(self, ctx, member: disnake.Member):
        user_warns_key = f"warns:{ctx.guild.id}:{member.id}"
        warn_ids = redisConnect.lrange(user_warns_key, 0, -1)
        
        if not warn_ids:
            if isinstance(ctx, commands.Context):
                await ctx.send(getLocale()["moderation"]["actions"]["warn"]["noWarnings"].format(memberMention=member.mention))
            else:
                await ctx.response.send_message(getLocale()["moderation"]["actions"]["warn"]["noWarnings"].format(memberMention=member.mention))
            return
        
        embed = disnake.Embed(
            title=getLocale()["moderation"]["actions"]["warn"]["warningsTitle"],
            description=getLocale()["moderation"]["actions"]["warn"]["warningsDescription"].format(
                memberMention=member.mention,
                warnCount=len(warn_ids)
            ),
            color=disnake.Color.yellow()
        )
        
        
        current_time = int(time.time())
        active_warnings = []
        
        for warn_id in warn_ids:
            warn_data_json = redisConnect.get(warn_id)
            if warn_data_json:
                try:
                    warn_data = json.loads(warn_data_json)
                    if warn_data.get("expiry") is None or warn_data.get("expiry") > current_time:
                        active_warnings.append(warn_data)
                except json.JSONDecodeError:
                    continue
        
        active_warnings.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        
        for i, warn in enumerate(active_warnings[:10], 1):
            reason = warn.get("reason", getLocale()["general"]["defaultReason"])
            moderator_id = warn.get("moderator_id", "Unknown")
            timestamp = warn.get("timestamp", 0)
            expiry = warn.get("expiry")
            
            time_str = f"<t:{timestamp}:R>"
            expiry_str = f" (Expires <t:{expiry}:R>)" if expiry else ""
            
            embed.add_field(
                name=f"Предупреждение #{i}",
                value=f"**Причина:** {reason}\n**Модератор:** <@{moderator_id}>\n**Истекает:** {time_str}{expiry_str}",
                inline=False
            )
        
        if len(active_warnings) > 10:
            embed.set_footer(text=f"Показано 10 из {len(active_warnings)} активных предупреждений.")
        
        if isinstance(ctx, commands.Context):
            await ctx.send(embed=embed)
        else:
            await ctx.response.send_message(embed=embed)

    @commands.command()
    @commands.has_any_role(*getConfig()["permissions"]["warn"])
    async def delwarn(self, ctx, member: disnake.Member, warn_index: int):
        await self.remove_warning(ctx, member, warn_index)

    @commands.slash_command(name="delwarn", description="Удалить предупреждение пользователя")
    @commands.has_any_role(*getConfig()["permissions"]["warn"])
    async def delwarn_slash(self, inter: disnake.ApplicationCommandInteraction,
                        member: disnake.Member = commands.Param(description="ID или @пользователь"),
                        warn_index: int = commands.Param(description="Номер предупреждения (из /warnings)")):
        await self.remove_warning(inter, member, warn_index)

    async def remove_warning(self, ctx, member: disnake.Member, warn_index: int):
        if warn_index <= 0:
            if isinstance(ctx, commands.Context):
                await ctx.send(getLocale()["errors"]["invalidWarnIndex"])
            else:
                await ctx.response.send_message(getLocale()["errors"]["invalidWarnIndex"], ephemeral=True)
            return
        
        user_warns_key = f"warns:{ctx.guild.id}:{member.id}"
        warn_ids = redisConnect.lrange(user_warns_key, 0, -1)
        
        if not warn_ids:
            if isinstance(ctx, commands.Context):
                await ctx.send(getLocale()["moderation"]["actions"]["warn"]["noWarnings"].format(memberMention=member.mention))
            else:
                await ctx.response.send_message(getLocale()["moderation"]["actions"]["warn"]["noWarnings"].format(memberMention=member.mention))
            return
        
        current_time = int(time.time())
        active_warnings = []
        
        for warn_id in warn_ids:
            warn_data_json = redisConnect.get(warn_id)
            if warn_data_json:
                try:
                    warn_data = json.loads(warn_data_json)
                    if warn_data.get("expiry") is None or warn_data.get("expiry") > current_time:
                        active_warnings.append((warn_id, warn_data))
                except json.JSONDecodeError:
                    continue
        
        active_warnings.sort(key=lambda x: x[1].get("timestamp", 0), reverse=True)
        
        if warn_index > len(active_warnings):
            if isinstance(ctx, commands.Context):
                await ctx.send(getLocale()["errors"]["invalidWarnIndex"])
            else:
                await ctx.response.send_message(getLocale()["errors"]["invalidWarnIndex"], ephemeral=True)
            return
        
        warn_id, warn_data = active_warnings[warn_index - 1]
        
        redisConnect.lrem(user_warns_key, 1, warn_id)
        redisConnect.delete(warn_id)
        
        embed = disnake.Embed(
            title=getLocale()["moderation"]["actions"]["warn"]["delWarnTitle"],
            description=getLocale()["moderation"]["actions"]["warn"]["delWarnDescription"].format(
                memberMention=member.mention,
                warnIndex=warn_index
            ),
            color=disnake.Color.green()
        )
        
        reason = warn_data.get("reason", getLocale()["general"]["defaultReason"])
        moderator_id = warn_data.get("moderator_id", "Unknown")
        timestamp = warn_data.get("timestamp", 0)
        
        embed.add_field(
            name=getLocale()["moderation"]["actions"]["warn"]["delWarnInfo"],
            value=f"**Причина:** {reason}\n**Модератор:** <@{moderator_id}>\n**Когда:** <t:{timestamp}:R>",
            inline=True
        )
        
        embed.add_field(
            name=getLocale()["moderation"]["common"]["moderator"],
            value=ctx.author.mention,
            inline=True
        )
        
        if isinstance(ctx, commands.Context):
            await ctx.send(embed=embed)
        else:
            await ctx.response.send_message(embed=embed)
        
        get_logger().debug(getLocale()["debug"]["moderation"]["delWarn"].format(
            member_name=member.name,
            member_id=member.id,
            guild_name=ctx.guild.name,
            guild_id=ctx.guild.id,
            warn_index=warn_index,
            moderator_name=ctx.author.name,
            moderator_id=ctx.author.id
        ))
            
        

def setup(bot):
    bot.add_cog(Moderation(bot))
