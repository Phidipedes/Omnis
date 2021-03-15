import discord
from discord.ext import commands

import typing

import asyncio
import datetime

from checks import messageCheck #pylint: disable=import-error

from database import trialsCollection, memberCollection #pylint: disable=import-error

class trials(commands.Cog, name = "Trial Members"):

    def __init__(self, bot):

        self.bot = bot

    @commands.group(aliases = ["trial", "t"])
    @commands.has_role(738915444420903022)
    async def trials(self, ctx):

        if ctx.invoked_subcommand == None:

            trialUsageEmbed = discord.Embed(title = f".trial usage", description = f".trial [add | remove | list | check | requirements | duration]\nadd - add a member to the trial list\nremove - remove a member from the trial list\nlist - list the current trial members\ncheck - check the staus of today's trial members\nrequirements - chnage the gexp requirement to pass trial\nduration - change the duration of the trial period", color = discord.Color.purple(), timestamp = datetime.datetime.utcnow())
            await ctx.channel.send(embed = trialUsageEmbed)

    @trials.command(aliases = ["requirement", "reqs", "req"])
    async def requirements(self, ctx, amount: typing.Optional[int] = None):

        """
        Sets the trial member gexp requirement

        Parameters:
            amount (Integer): the amount of gexp required.
        """

        try:

            if amount == None:

                await ctx.channel.send(f"What do you want to set the gexp requirement for trial members to?")
                amountQuestionMessage = await self.bot.wait_for("message", timeout = 300, check = messageCheck(ctx))

                amount = int(amountQuestionMessage.content)

            await trialsCollection.update_one({"_id": "envision"}, {"$set": {"trialReq": amount}})
            await ctx.channel.send(f"Trial gexp requirement set to {amount}")

        except asyncio.TimeoutError:

            await ctx.channel.send(f"Timed out.")

        except ValueError:

            await ctx.channel.send(f"Gexp requirement amount needs to be an integer.")

    @trials.command(aliases = ["ch", "c"])
    async def check(self, ctx):

        passList = []
        failList = []

        trialInfo = (await trialsCollection.find_one({"_id": "envision"}))
        
        trials = trialInfo["trialMembers"]

        for trial in trials:

            trialGexp = (await memberCollection.find_one({"_id": "envision"}))["members"][trial]["gexp"]["total"]

            if trialGexp >= trialInfo["trialReq"]:

                passList.append([trial, trialGexp])

            else:

                failList.append([trial, trialInfo["trialReq"] - trialGexp])

        passingMessage = ""

        for passing in passList:

            passingMessage += f"```+{passing[0]} --- earned {passing[1]} gexp```\n"

        failingMessage = ""

        for failing in failList:

            failingMessage += f"```+{failing[0]} --- missing {failing[1]} gexp```\n"

        passingEmbed = discord.Embed(title = f"✅ Passing Trial Members ✅ ~-~-~-~-~-~ {datetime.date.today()}", description = passingMessage, color = discord.Color.green(), timestamp = datetime.datetime.utcnow())
        failingEmbed = discord.Embed(title = f"❌ Failing Trial Members ❌ ~-~-~-~-~-~ {datetime.date.today()}", description = failingMessage, color = discord.Color.red(), timestamp = datetime.datetime.utcnow())

        await ctx.channel.send(embed = passingEmbed)
        await ctx.channel.send(embed = failingEmbed)

    @trials.command(aliases = ["a"])
    async def add(self, ctx, username: typing.Optional[str] = None):

        if username == None:

            await ctx.channel.send(f"What member do you want to log as trial member?")
            username = (await self.bot.wait_for("message", timeout = 300, check = messageCheck(ctx))).content

        if username.casefold() not in (await memberCollection.find_one({"_id": "envision"}))["members"].keys():

            await ctx.channel.send(f"That user is not in the guild. Make sure you spelled the name correctly! If you are sure you spelled the name correctly and that the member *is* in the guild, wait a few minutes and try again. The cache updates every minute with new members.")

        else:

            trialsCollection.update_one({"_id": ctx.guild.id}, {"$set": {f"trialMembers.{username.casefold()}": datetime.datetime.utcnow() + datetime.timedelta(7)}})

def setup(bot):

    bot.add_cog(trials(bot))