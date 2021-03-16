import discord
from discord.ext import commands, tasks
from discord import utils

import typing
import pytz
import asyncio
import datetime
import os

import pprint

from checks import messageCheck #pylint: disable=import-error

from database import trialsCollection, memberCollection #pylint: disable=import-error

class trials(commands.Cog, name = "Trial Members"):

    def __init__(self, bot):

        self.bot = bot
        self.checkTrialMembers.start() #pylint: disable = no-member

    @commands.group(aliases = ["trial", "t"])
    @commands.has_any_role(738915444420903022, 716599787780177954, 730175515809546300)
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

    @trials.command(aliases = ["dura", "dur"])
    async def duration(self, ctx, duration: typing.Optional[int] = None):

        try:

            if duration == None:

                await ctx.channel.send(f"How many days long do you want the trial period to be?")
                duration = int((await ctx.channel.wait_for("message", timeout = 300, check = messageCheck(ctx))).content)

            await trialsCollection.update_one({"_id": "envision"}, {"$set": {"trialDuration": duration}})

            await ctx.channel.send(f"Trial period duration set to {duration} days.")

        except asyncio.TimeoutError:

            await ctx.channel.send(f"Timed out")

        except ValueError:

            await ctx.channel.send(f"You must give an integer number of days.")

    @trials.command(aliases = ["ch", "c"])
    async def check(self, ctx, dayOffset: typing.Optional[int] = 0):

        eastern = pytz.timezone("US/Eastern")

        passList = []
        failList = []

        trialData = await trialsCollection.find_one({"_id": "envision"})
        
        trialMembers = trialData["trialMembers"]

        for trial in trialMembers:

            if trial["memberDate"].date() == eastern.localize(datetime.datetime.utcnow()).date() + datetime.timedelta(days = dayOffset):

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

        passingEmbed = discord.Embed(title = f"✅ Passing Trial Members ✅ ~-~-~-~-~-~ {datetime.datetime.now().astimezone(eastern)}", description = passingMessage, color = discord.Color.green(), timestamp = datetime.datetime.utcnow())
        failingEmbed = discord.Embed(title = f"❌ Failing Trial Members ❌ ~-~-~-~-~-~ {datetime.datetime.now().astimezone(eastern)}", description = failingMessage, color = discord.Color.red(), timestamp = datetime.datetime.utcnow())

        await ctx.channel.send(embed = passingEmbed)
        await ctx.channel.send(embed = failingEmbed)

    @trials.command(aliases = ["a"])
    async def add(self, ctx, username: typing.Optional[str] = None):

        trialDateChannel = self.bot.get_channel(int(os.getenv("TRIAL_MEMBER_DATE_CHANNEL_ID")))

        await ctx.message.delete()

        try:

            eastern = pytz.timezone("US/Eastern")

            trialDuration = (await trialsCollection.find_one({"_id": "envision"}))["trialDuration"]

            if username == None:

                await ctx.channel.send(f"What member do you want to log as trial member?", delete_after = 5)
                usernameMessage = await self.bot.wait_for("message", timeout = 300, check = messageCheck(ctx))
                username = usernameMessage.content
                usernameMessage.delete()

            if username.casefold() not in [member["username"] for member in (await memberCollection.find_one({"_id": "envision"}))["members"].values()]:

                await ctx.channel.send(f"That user is not in the guild. Make sure you spelled the name correctly! If you are sure you spelled the name correctly and that the member *is* in the guild, wait a few minutes and try again. The cache updates every minute with new members.", delete_after = 8)

            elif username.casefold() in [trial["username"] for trial in (await trialsCollection.find_one({"_id": "envision"}))["trialMembers"]]:

                await ctx.channel.send(f"This member is already in their trial period.", delete_after = 5)

            else:

                trialsCollection.update_one({"_id": "envision"}, {"$push": {"trialMembers": {"username": username.casefold(), "memberDate": datetime.datetime.utcnow().astimezone(eastern) + datetime.timedelta(trialDuration)}}})

                await ctx.channel.send(f"Member {username.casefold()} starting trial on {datetime.datetime.utcnow().astimezone(eastern).date()}. (Member on {datetime.datetime.utcnow().astimezone(eastern).date() + datetime.timedelta(trialDuration)})")

                if ctx.channel != trialDateChannel:

                    await trialDateChannel.send(f"Member {username.casefold()} starting trial on {datetime.datetime.utcnow().astimezone(eastern).date()}. (Member on {datetime.datetime.utcnow().astimezone(eastern).date() + datetime.timedelta(trialDuration)})")

        except asyncio.TimeoutError:

            await ctx.channel.send(f"Timed out.")

    @trials.command(aliases = ["rem", "r"])
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

                await trialsCollection.update_one({"_id": "envision"}, {"$set": {"trialMembers": updatedTrials}})

                await ctx.channel.send(f"Removed {username.casefold()} from the trial members list.")

        except asyncio.TimeoutError:

            await ctx.channel.send(f"Timed out")

    @trials.command(aliases = ["list", "li", "l"])
    async def _list(self, ctx):

        eastern = pytz.timezone("US/Eastern")

        trialData = await trialsCollection.find_one({"_id": "envision"})

        membersMessage = f"Username ~-~-~ Member Date"

        if len(trialData["trialMembers"]) > 0:

            for trial in trialData["trialMembers"]:

                membersMessage += f"\n```+ {trial['username']} ~-~-~ {trial['memberDate'].date()}```"

        else:

            membersMessage = "```+ No Trial Members```"

        trialMemberListEmbed = discord.Embed(title = f"Trial Member List ~-~-~-~-~-~ {datetime.datetime.now().astimezone(eastern).date()}", description = membersMessage, color = discord.Color.purple(), timestamp = datetime.datetime.utcnow())
        await ctx.channel.send(embed = trialMemberListEmbed)

    @trials.error
    async def trials_error(self, ctx, error):

        if isinstance(error, commands.MissingAnyRole):

            await ctx.channel.send(f"You are missing a required role to use this command!")

    @tasks.loop(hours = 24)
    async def checkTrialMembers(self):

        eastern = pytz.timezone("US/Eastern")

        trialDateChannel = self.bot.get_channel(int(os.getenv("TRIAL_MEMBER_DATE_CHANNEL_ID")))

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

        await trialDateChannel.send(embed = passingEmbed)
        await trialDateChannel.send(embed = failingEmbed)

    @checkTrialMembers.before_loop
    async def beforeCheckLoop(self):

        eastern = pytz.timezone("US/Eastern")

        startTime = datetime.datetime.now(eastern).replace(hour = 23, minute = 59, second = 30)

        print(startTime)

        await self.bot.wait_until_ready()
        await utils.sleep_until(startTime)

def setup(bot):

    bot.add_cog(trials(bot))