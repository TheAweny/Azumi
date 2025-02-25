from disnake.ext import commands
import disnake
import os

class CogManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="load", description="Загрузить указанный Cog")
    @commands.is_owner()
    async def load_cog(self, inter: disnake.ApplicationCommandInteraction, cog: str):
        try:
            self.bot.load_extension(f"cogs.{cog}")
            await inter.response.send_message(f"✅ Cog `{cog}` загружен!", ephemeral=True)
        except Exception as e:
            await inter.response.send_message(f"❌ Ошибка при загрузке `{cog}`: {e}", ephemeral=True)

    @commands.slash_command(name="unload", description="Выгрузить указанный Cog")
    @commands.is_owner()
    async def unload_cog(self, inter: disnake.ApplicationCommandInteraction, cog: str):
        try:
            self.bot.unload_extension(f"cogs.{cog}")
            await inter.response.send_message(f"✅ Cog `{cog}` выгружен!", ephemeral=True)
        except Exception as e:
            await inter.response.send_message(f"❌ Ошибка при выгрузке `{cog}`: {e}", ephemeral=True)

    @commands.slash_command(name="reload", description="Перезагрузить указанный Cog")
    @commands.is_owner()
    async def reload_cog(self, inter: disnake.ApplicationCommandInteraction, cog: str):
        try:
            self.bot.unload_extension(f"cogs.{cog}")
            self.bot.load_extension(f"cogs.{cog}")
            await inter.response.send_message(f"🔄 Cog `{cog}` перезагружен!", ephemeral=True)
        except Exception as e:
            await inter.response.send_message(f"❌ Ошибка при перезагрузке `{cog}`: {e}", ephemeral=True)


def setup(bot):
    bot.add_cog(CogManager(bot))
