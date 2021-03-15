import discord
from discord.ext import commands

import typing
import pytz
import asyncio
import datetime

import pprint

from checks import messageCheck #pylint: disable=import-error

from database import trialsCollection, memberCollection #pylint: disable=import-error

class trials(commands.Cog, name = "Trial Members"):

    def __init__(self, bot):

        self.bot = bot

    @commands.group(aliases = ["trial", "t"])
    @commands.has_any_role(738915444420903022, 716599787780177954)
    async def trials(self, ctx):

        if ctx.invoked_subcommand == None:

            trialUsageEmbed = discord.Embed(title = f"trial command usage", description = f"trial [add | remove | list | check | requirements | duration]\nadd - add a member to the trial list\nremove - remove a member from the trial list\nlist - list the current trial members\ncheck - check the staus of today's trial members\nrequirements - chnage the gexp requirement to pass trial\nduration - change the duration of the trial period", color = discord.Color.purple(), timestamp = datetime.datetime.utcnow())
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

        eastern = pytz.timezone("US/Eastern")

        passList = []
        failList = []

        trialData = await trialsCollection.find_one({"_id": "envision"})
        
        trialMembers = trialData["trialMembers"]

        for trial in trialMembers:

            if trial["memberDate"].date() == eastern.localize(datetime.datetime.utcnow()).date():

                for member in (await memberCollection.find_one({"_id": "envision"}))["members"].values():

                    if member["username"] == trial["username"]:

                        gexpEarned = member["gexp"]["total"]

                if gexpEarned >= trialData["trialReq"]:

                    passList.append([trial["username"], gexpEarned])

                else:

                    failList.append([trial["username"], trialData["trialReq"] - gexpEarned])

        passingMessage = ""

        if len(passList) > 0:

            for passing in passList:

                passingMessage += f"```+{passing[0]} --- earned {passing[1]} gexp```\n"

        else:
            
            passingMessage = "```No passing trials```"

        failingMessage = ""

        if len(failList) > 0:

            for failing in failList:

                failingMessage += f"```+{failing[0]} --- missing {failing[1]} gexp```\n"

        else:
            
            failingMessage = "```No failing trials```"

        passingEmbed = discord.Embed(title = f"✅ Passing Trial Members ✅ ~-~-~-~-~-~ {datetime.date.today()}", description = passingMessage, color = discord.Color.green(), timestamp = datetime.datetime.utcnow())
        failingEmbed = discord.Embed(title = f"❌ Failing Trial Members ❌ ~-~-~-~-~-~ {datetime.date.today()}", description = failingMessage, color = discord.Color.red(), timestamp = datetime.datetime.utcnow())

        await ctx.channel.send(embed = passingEmbed)
        await ctx.channel.send(embed = failingEmbed)

    @trials.command(aliases = ["a"])
    async def add(self, ctx, username: typing.Optional[str] = None):

        try:

            eastern = pytz.timezone("US/Eastern")

            trialDuration = (await trialsCollection.find_one({"_id": "envision"}))["trialDuration"]

            if username == None:

                await ctx.channel.send(f"What member do you want to log as trial member?")
                username = (await self.bot.wait_for("message", timeout = 300, check = messageCheck(ctx))).content

            if username.casefold() not in [member["username"] for member in (await memberCollection.find_one({"_id": "envision"}))["members"].values()]:

                await ctx.channel.send(f"That user is not in the guild. Make sure you spelled the name correctly! If you are sure you spelled the name correctly and that the member *is* in the guild, wait a few minutes and try again. The cache updates every minute with new members.")

            elif username.casefold() in [trial["username"] for trial in (await trialsCollection.find_one({"_id": "envision"}))["trialMembers"]]:

                await ctx.channel.send(f"This member is already in their trial period.")

            else:

                trialsCollection.update_one({"_id": "envision"}, {"$push": {"trialMembers": {"username": username.casefold(), "memberDate": eastern.localize(datetime.datetime.utcnow()) + datetime.timedelta(trialDuration)}}})

                await ctx.channel.send(f"Member {username.casefold()} starting trial on {eastern.localize(datetime.datetime.utcnow()).date()}. (Member on {eastern.localize(datetime.datetime.utcnow()).date() + datetime.timedelta(trialDuration)})")

        except asyncio.TimeoutError:

            await ctx.channel.send(f"Timed out.")

    @trials.command(aliases = ["r"])
    async def remove(self, ctx, username: typing.Optional[str] = None):

        try:
        
            if username == None:

                await ctx.channel.send(f"What member do you want to remove from the trial list?")
                username = (await self.bot.wait_for("message", timeout = 300, check = messageCheck(ctx))).content.casefold()

            if username.casefold() not in [trial["username"] for trial in (await trialsCollection.find_one({"_id": "envision"}))["trialMembers"]]:

                await ctx.channel.send(f"That user is not in the trial member list. Make sure you spelled the name correctly!")

            else:

                updatedTrials = [trial for trial in (await trialsCollection.find_one({"_id": "envision"}))["trialMembers"] if not trial["username"] == username.casefold()]

                pprint.pprint(updatedTrials)

                res = await trialsCollection.update_one({"_id": "envision"}, {"$set": {"trialMembers": updatedTrials}})

                print(res.modified_count)

                await ctx.channel.send(f"Removed {username.casefold()} from the trial members list.")

        except asyncio.TimeoutError:

            await ctx.channel.send(f"Timed out")

    @trials.error
    async def trials_error(self, ctx, error):

        if isinstance(error, commands.MissingAnyRole):

            await ctx.channel.send(f"You are missing a required role to use this command!")

def setup(bot):

    bot.add_cog(trials(bot))