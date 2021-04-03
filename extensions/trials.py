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

        """
        Trial member commands

        Commands:
            requirements - change the gexp requirement for trial members to pass.
                usage: o!trial requirements [amount]
                aliases: requirement, reqs, req
            duration - change the trial period duration
                usage: o!trial duration [days]
                aliases: dura, dur
            add - add a trial member to the trial member list
                usage: o!trial add [username]
                aliases: a
            remove - remove a trial member fromt he trial member list
                usage: o!trial remove [username]
                aliases: rem, r
            list - list all the current trial members
                usage: o!trial list
                aliases: li, l
            check - check if the current trial members have passed the gexp requirement
                usage: o!trial check [dayOffset]
                aliases: ch, c
        """

        if ctx.invoked_subcommand == None:

            trialUsageEmbed = discord.Embed(title = f"trial command usage", description = f"trial [add | remove | list | check | requirements | duration]\nadd - add a member to the trial list\nremove - remove a member from the trial list\nlist - list the current trial members\ncheck - check the staus of today's trial members\nrequirements - chnage the gexp requirement to pass trial\nduration - change the duration of the trial period", color = discord.Color.purple(), timestamp = datetime.datetime.utcnow())
            await ctx.channel.send(embed = trialUsageEmbed)

    @trials.command(aliases = ["requirement", "reqs", "req"])
    async def requirements(self, ctx, amount: typing.Optional[int] = None):

        """
        Sets the trial member gexp requirement

        Parameters:
            amount (int): the amount of gexp required to pass the trial period

        Usage:
            o![trials|trial|t] [requirements|requirement|reqs|req] [amount]

        Example:
            o!trial req 200000 >> sets trial requirement to 200,000 gexp
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

        """
        Sets the trial preiod duration

        Parameters:
            days (int): the number of days that the trial period lasts

        Usage:
            o![trials|trial|t] [duration|dura|dur=] [days]

        Example:
            o!trial dura 7 >> sets trial period to 7 days
        """

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

    @trials.command(aliases = ["a"])
    async def add(self, ctx, username: typing.Optional[str] = None):

        """
        Adds a member to the trial member list

        Parameters:
            username (string): the username of the new trial member

        Usage:
            o![trials|trial|t] [add|a] [username]

        Example:
            o!trial add Phidipedes >> adds the user 'Phidipedes' to the trial member list
        """

        trialDateChannel = self.bot.get_channel(int(os.getenv("TRIAL_MEMBER_DATE_CHANNEL_ID")))

        await ctx.message.delete()

        try:

            eastern = pytz.timezone("US/Eastern")

            trialDuration = (await trialsCollection.find_one({"_id": "envision"}))["trialDuration"]

            if username == None:

                await ctx.channel.send(f"What member do you want to log as trial member?", delete_after = 5)
                usernameMessage = await self.bot.wait_for("message", timeout = 300, check = messageCheck(ctx))
                username = usernameMessage.content
                await usernameMessage.delete()

            if username.casefold() not in [member["username"] for member in (await memberCollection.find_one({"_id": "envision"}))["members"].values()]:

                await ctx.channel.send(f"That user is not in the guild. Make sure you spelled the name correctly! If you are sure you spelled the name correctly and that the member *is* in the guild, wait a few minutes and try again. The cache updates every minute with new members.", delete_after = 8)

            elif username.casefold() in [trial["username"] for trial in (await trialsCollection.find_one({"_id": "envision"}))["trialMembers"]]:

                await ctx.channel.send(f"This member is already in their trial period.", delete_after = 5)

            else:

                trialsCollection.update_one({"_id": "envision"}, {"$push": {"trialMembers": {"username": username.casefold(), "memberDate": datetime.datetime.utcnow().astimezone(eastern) + datetime.timedelta(trialDuration)}}})

                await ctx.channel.send(f"Member {username.casefold()} starting trial on {datetime.datetime.utcnow().astimezone(eastern).date()}. (Member on {datetime.datetime.utcnow().astimezone(eastern).date() + datetime.timedelta(trialDuration)})")

                if ctx.channel != trialDateChannel:

                    await trialDateChannel.send(f"Member {username.casefold()} starting trial on {datetime.datetime.utcnow().astimezone(eastern).date().strftime('%m/%d/%Y')}. (Member on {(datetime.datetime.utcnow().astimezone(eastern).date() + datetime.timedelta(trialDuration)).strftime('%m/%d/%Y')})")

        except asyncio.TimeoutError:

            await ctx.channel.send(f"Timed out.")

    @trials.command(aliases = ["rem", "r"])
    async def remove(self, ctx, username: typing.Optional[str] = None):

        """
        Removes a member from the trial member list

        Parameters:
            username (string): the username of the trial member

        Usage:
            o![trials|trial|t] [remove|rem|r] [username]

        Example:
            o!trial rem Phidipedes >> removes the user 'Phidipedes' from the trial member list
        """

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

        """
        Lists all the current trial members

        Parameters:
            None

        Usage:
            o![trials|trial|t] [list|li|l]

        Example:
            o!trial list >> lists all the trial members
        """
        
        eastern = pytz.timezone("US/Eastern")

        trialData = await trialsCollection.find_one({"_id": "envision"})
        
        activeDates = []
        for trial in trialData['trialMembers']:

            if trial['memberDate'].date() not in activeDates:

                activeDates.append(trial['memberDate'].date())

        membersMessage = f"Current Trial GEXP Requirement: {trialData['trialReq']}\nCurrent Trial Period Duration: {trialData['trialDuration']} days\nTotal Trial Members: {len(trialData['trialMembers'])}"

        trialMemberListEmbed = discord.Embed(title = f"Trial Member List ~-~-~-~-~-~ {datetime.datetime.now().astimezone(eastern).date().strftime('%m/%d/%Y')}", description = membersMessage, color = discord.Color.purple(), timestamp = datetime.datetime.utcnow())
        
        for date in activeDates:

            dateMessage = "```+ " + "\n+ ".join([trial['username'] for trial in trialData['trialMembers'] if trial['memberDate'].date() == date]) + "```"

            trialMemberListEmbed.add_field(name = f"--- Member on {date.strftime('%m/%d/%Y')} (mm/dd/yyyy) ---", value = dateMessage, inline = False)
        
        await ctx.channel.send(embed = trialMemberListEmbed)

    @trials.command(aliases = ["ch", "c"])
    async def check(self, ctx, dayOffset: typing.Optional[int] = 0):

        """
        Manually check if trial members have met the gexp requirement

        Parameters:
            dayOffset (day): the number of days intot he future or past to check for trial members

        Usage:
            o![trials|trial|t] [check|ch|c] [dayOffset]

        Example:
            o!trial check 7 >> checks if the trial members who's trial period ends in 7 day's are passing their trial.
        """

        eastern = pytz.timezone("US/Eastern")

        now = datetime.datetime.now().astimezone(eastern)

        passList = []
        failList = []

        trialData = await trialsCollection.find_one({"_id": "envision"})
        trialMembers = trialData["trialMembers"]
        memberData = await memberCollection.find_one({"_id": "envision"})
        members = memberData["members"].values()

        for trial in trialMembers:

            if trial["username"] not in [member["username"] for member in members]:

                print(f"Member {trial['username']} was listed as a trial but is not in the guild. Skipping them")
                continue

            if trial["memberDate"].date() == now.date():

                gexpEarned = next(member["gexp"]["total"] for member in members if member["username"] == trial["username"])

                if gexpEarned >= trialData["trialReq"]:

                    passList.append([trial["username"], gexpEarned])

                else:

                    failList.append([trial["username"], trialData["trialReq"] - gexpEarned])

        if len(passList) > 0:

            passingMessage = "\n".join([f"```+ {passing[0]} --- earned {passing[1]} gexp```\n" for passing in passList])

        else:
            
            passingMessage = "```No passing trials```"

        if len(failList) > 0:

            failingMessage = "\n".join([f"```+ {failing[0]} --- missing {failing[1]} gexp```\n" for failing in failList])

        else:
            
            failingMessage = "```No failing trials```"

        passingEmbed = discord.Embed(title = f"✅ Passing Trial Members ✅ {(datetime.datetime.now().astimezone(eastern).date() - datetime.timedelta(days = dayOffset)).strftime('%A, %B %d, %Y')} ({datetime.datetime.now().astimezone(eastern).date().strftime('%m/%d/%Y')})", description = passingMessage, color = discord.Color.green(), timestamp = datetime.datetime.utcnow())
        failingEmbed = discord.Embed(title = f"❌ Failing Trial Members ❌ {(datetime.datetime.now().astimezone(eastern).date() - datetime.timedelta(days = dayOffset)).strftime('%A, %B %d, %Y')} ({datetime.datetime.now().astimezone(eastern).date().strftime('%m/%d/%Y')})", description = failingMessage, color = discord.Color.red(), timestamp = datetime.datetime.utcnow())

        await ctx.channel.send(embed = passingEmbed)
        await ctx.channel.send(embed = failingEmbed)

    @trials.error
    async def trials_error(self, ctx, error):

        if isinstance(error, commands.MissingAnyRole):

            await ctx.channel.send(f"You are missing a required role to use this command!")

    @tasks.loop(hours = 24)
    async def checkTrialMembers(self):

        eastern = pytz.timezone("US/Eastern")

        trialDateChannel = self.bot.get_channel(int(os.getenv("TRIAL_MEMBER_DATE_CHANNEL_ID")))

        now = datetime.datetime.now().astimezone(eastern)

        passList = []
        failList = []

        trialData = await trialsCollection.find_one({"_id": "envision"})
        trialMembers = trialData["trialMembers"]
        memberData = await memberCollection.find_one({"_id": "envision"})
        members = memberData["members"].values()

        for trial in trialMembers:

            if trial["username"] not in [member["username"] for member in members]:

                print(f"Member {trial['username']} was listed as a trial but is not in the guild. Skipping them")
                continue

            if trial["memberDate"].date() == now.date():

                gexpEarned = next(member["gexp"]["total"] for member in members if member["username"] == trial["username"])

                if gexpEarned >= trialData["trialReq"]:

                    passList.append([trial["username"], gexpEarned])

                else:

                    failList.append([trial["username"], trialData["trialReq"] - gexpEarned])

        if len(passList) > 0:

            passingMessage = "\n".join([f"```+ {passing[0]} --- earned {passing[1]} gexp```\n" for passing in passList])

        else:
            
            passingMessage = "```No passing trials```"

        if len(failList) > 0:

            failingMessage = "\n".join([f"```+ {failing[0]} --- missing {failing[1]} gexp```\n" for failing in failList])

        else:
            
            failingMessage = "```No failing trials```"

        passingEmbed = discord.Embed(title = f"✅ Passing Trial Members ✅ ~-~-~-~-~-~ {datetime.date.now().astimezone(eastern).date().strftime('%A, %B %d, %Y')}", description = passingMessage, color = discord.Color.green(), timestamp = datetime.datetime.utcnow())
        failingEmbed = discord.Embed(title = f"❌ Failing Trial Members ❌ ~-~-~-~-~-~ {datetime.date.now().astimezone(eastern).date().strftime('%A, %B %d, %Y')}", description = failingMessage, color = discord.Color.red(), timestamp = datetime.datetime.utcnow())

        await trialDateChannel.send(embed = passingEmbed)
        await trialDateChannel.send(embed = failingEmbed)

        await trialsCollection.update_one({"_id": "envision"}, {"$set": {"trialMembers": [trial for trial in trialMembers if trial["username"] not in (passList + failList)]}})

    @checkTrialMembers.before_loop
    async def beforeCheckLoop(self):

        eastern = pytz.timezone("US/Eastern")

        startTime = datetime.datetime.now().astimezone(eastern).replace(hour = 23, minute = 59, second = 30)

        print(f"{(startTime - datetime.datetime.now().astimezone(eastern)).total_seconds()} seconds until loop starts on {startTime.strftime('%A, %B %d, %Y')}")

        print(startTime)

        await self.bot.wait_until_ready()
        await utils.sleep_until(startTime)

def setup(bot):

    bot.add_cog(trials(bot))