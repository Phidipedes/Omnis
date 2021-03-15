import discord
from discord.ext import commands
import datetime
import typing

from checks import messageCheck #pylint: disable=import-error

class administration(commands.Cog, name = f"Administration"):

    async def __init__(self, bot):

        self.bot = bot

    @commands.group(aliases = ["c"])
    @commands.is_owner()
    async def cogs(self, ctx):

        if ctx.invoked_subcommand == None:

            cogCommandUsageEmbed = discord.Embed(title = f"Cog Command Usage", description = f"cog [load | unload | reload]", color = discord.Color.purple(), timestamp = datetime.datetime.utcnow())
            await ctx.channel.send(embed = cogCommandUsageEmbed)

    @cogs.command(aliases = ["l"])
    async def load(self, ctx, extension: typing.Optional[str] = None):

        if extension == None:

            await ctx.channel.send(f"what cog do you want to load?")
            extension = (await self.bot.wait_for(f"message", timeout = 300, check = messageCheck(ctx))).content

        self.bot.load_extension(F"extensions.{extension}")

    @cogs.command(aliases = ["ul", "u"])
    async def unload(self, ctx, extension: typing.Optional[str] = None):

        if extension == None:

            await ctx.channel.send(f"what cog do you want to unload?")
            extension = (await self.bot.wait_for(f"message", timeout = 300, check = messageCheck(ctx))).content

        self.bot.unload_extension(F"extensions.{extension}")

    @cogs.command(aliases = ["rl", "r"])
    async def reload(self, ctx, extension: typing.Optional[str] = None):

        if extension == None:

            await ctx.channel.send(f"what cog do you want to reload?")
            extension = (await self.bot.wait_for(f"message", timeout = 300, check = messageCheck(ctx))).content

        self.bot.reload_extension(F"extensions.{extension}")

    @cogs.error
    async def cogs_error(self, ctx, error):

        if isinstance(error, commands.NotOwner):

            await ctx.channel.send(f"Only the bot owner can use cog commands.")

def setup(bot):

    bot.add_cog(administration(bot))