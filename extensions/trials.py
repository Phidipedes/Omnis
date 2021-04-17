import discord
from discord.ext import commands, tasks
from discord import utils

import asyncio
import datetime
import itertools
import operator
import os
import pytz
import typing

from checks import messageCheck #pylint: disable=import-error
from database import trialsCollection, memberCollection #pylint: disable=import-error
from timezones import eastern #pylint: disable = import-error

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
    async def requirements(self, ctx, amount: typing.Optional[int]):

        """
        Sets the trial member gexp requirement

        Parameters:
            amount (int): the amount of gexp required to pass the trial period

        Usage:
            o![trials|trial|t] [requirements|requirement|reqs|req] [amount]

        Example:
            o!trial req 200000 >> sets trial requirement to 200,000 gexp
        """

        await ctx.message.delete()

        trialDateChannel = self.bot.get_channel(int(os.getenv("TRIAL_MEMBER_DATE_CHANNEL_ID")))

        try:

            if amount == None:

                await ctx.channel.send(f"What do you want to set the gexp requirement for trial members to?", delete_after = 15)
                amountQuestionResponse = await self.bot.wait_for("message", timeout = 300, check = messageCheck(ctx))
                await amountQuestionResponse.delete()
                amount = int(amountQuestionResponse.content)

        except asyncio.TimeoutError:

            await ctx.channel.send(f"Timed out.", delete_after = 15)
            return

        except ValueError:

            await ctx.channel.send(f"Gexp requirement amount needs to be an integer.", delete_after = 15)
            return

        await trialsCollection.update_one({"_id": "envision"}, {"$set": {"trialReq": amount}})
        await ctx.channel.send(f"Trial gexp requirement set to {amount} by {ctx.message.author}")

        if ctx.channel != trialDateChannel:

            await trialDateChannel.send(f"Trial gexp requirement set to {amount} by {ctx.message.author}")

    @trials.command(aliases = ["dura", "dur"])
    async def duration(self, ctx, duration: typing.Optional[int]):

        """
        Sets the trial preiod duration

        Parameters:
            days (int): the number of days that the trial period lasts

        Usage:
            o![trials|trial|t] [duration|dura|dur=] [days]

        Example:
            o!trial dura 7 >> sets trial period to 7 days
        """

        await ctx.message.delete()

        trialDateChannel = self.bot.get_channel(int(os.getenv("TRIAL_MEMBER_DATE_CHANNEL_ID")))

        if duration == None:

            try:
            
                await ctx.channel.send(f"How many days long do you want the trial period to be?", delete_after = 15)
                durationResponse = await self.bot.wait_for("message", timeout = 300, check = messageCheck(ctx))
                await durationResponse.delete()
                duration = int(durationResponse.content)

            except asyncio.TimeoutError:

                await ctx.channel.send(f"Timed out", delete_after = 15)
                return

            except ValueError:

                await ctx.channel.send(f"You must give an integer number of days.", delete_after = 15)
                return

        await trialsCollection.update_one({"_id": "envision"}, {"$set": {"trialDuration": duration}})

        await ctx.channel.send(f"Trial period duration set to {duration} days by {ctx.author}")

        if ctx.channel != trialDateChannel:

            await trialDateChannel.send(f"Trial period duration set to {duration} days by {ctx.author}")

    @trials.command(aliases = ["a"])
    async def add(self, ctx, username: typing.Optional[str]):

        """
        Adds a member to the trial member list

        Parameters:
            username (string): the username of the new trial member

        Usage:
            o![trials|trial|t] [add|a] [username]

        Example:
            o!trial add Phidipedes >> adds the user 'Phidipedes' to the trial member list
        """

        await ctx.message.delete()

        trialDateChannel = self.bot.get_channel(int(os.getenv("TRIAL_MEMBER_DATE_CHANNEL_ID")))

        trialData = await trialsCollection.find_one({"_id": "envision"})
        trialDuration = trialData["trialDuration"]
        memberData = await memberCollection.find_one({"_id": "envision"})
        members = memberData["members"].values()

        if username == None:

            try:
            
                await ctx.channel.send(f"What member do you want to log as trial member?", delete_after = 15)
                usernameMessage = await self.bot.wait_for("message", timeout = 300, check = messageCheck(ctx))
                username = usernameMessage.content.casefold()
                await usernameMessage.delete()

            except asyncio.TimeoutError:

                await ctx.channel.send(f"Timed out.", delete_after = 15)
                return

        username = username.casefold()

        if username not in [member["username"] for member in members]:

            await ctx.channel.send(f"That user is not in the guild. Make sure you spelled the name correctly! If you are sure you spelled the name correctly and that the member *is* in the guild, wait a few minutes and try again. The cache updates every minute with new members.", delete_after = 15)
            return

        if username in [trial["username"] for trial in (await trialsCollection.find_one({"_id": "envision"}))["trialMembers"]]:

            await ctx.channel.send(f"This member is already in their trial period.", delete_after = 15)
            return

        trialsCollection.update_one({"_id": "envision"}, {"$push": {"trialMembers": {"username": username, "memberDate": (datetime.datetime.now().astimezone(eastern) + datetime.timedelta(trialDuration)).replace(hour = 0, minute = 0, second = 0, microsecond= 0)}}})
        memberDate = datetime.datetime.now().astimezone(eastern).replace(hour = 0, minute = 0, second = 0, microsecond = 0) + datetime.timedelta(days = trialData["trialDuration"])
        newTrialEmbed = discord.Embed(title = f"{username} Starting Trial", description = f"Starting trial on {datetime.datetime.now().astimezone(eastern).date().strftime('%d/%m/%Y')} (dd/mm/yyyy).\nMember on {memberDate.date().strftime('%d/%m/%Y')}\nAdded by: {ctx.author}.", color = discord.Color.green(), timestamp = datetime.datetime.utcnow())
        await ctx.channel.send(embed = newTrialEmbed)
        
        if ctx.channel != trialDateChannel:

            await trialDateChannel.send(embed = newTrialEmbed)

    @trials.command(aliases = ["rem", "r"])
    async def remove(self, ctx, username: typing.Optional[str]):

        """
        Removes a member from the trial member list

        Parameters:
            username (string): the username of the trial member

        Usage:
            o![trials|trial|t] [remove|rem|r] [username]

        Example:
            o!trial rem Phidipedes >> removes the user 'Phidipedes' from the trial member list
        """

        await ctx.message.delete()

        trialDateChannel = self.bot.get_channel(int(os.getenv("TRIAL_MEMBER_DATE_CHANNEL_ID")))

        trialData = await trialsCollection.find_one({"_id": "envision"})
        trialMembers = trialData["trialMembers"]

        if username == None:

            try:

                await ctx.channel.send(f"What member do you want to remove from the trial list?", delete_after = 15)
                usernameResponseMessage = await self.bot.wait_for("message", timeout = 300, check = messageCheck(ctx))
                username = usernameResponseMessage.content.casefold()
                await usernameResponseMessage.delete()

            except asyncio.TimeoutError:

                await ctx.channel.send(f"Timed out", delete_after = 15)
                return

        username = username.casefold()

        if username not in [trial["username"] for trial in trialMembers]:

            await ctx.channel.send(f"That user is not in the trial member list. Make sure you spelled the name correctly!", delete_after = 15)
            return

        await trialsCollection.update_one({"_id": "envision"}, {"$pull": {"trialMembers": {"username": username}}})
        removeTrialEmbed = discord.Embed(title = f"{username} Removed from Trial", description = f"Removed by {ctx.author}", color = discord.Color.dark_red())
        await ctx.channel.send(embed = removeTrialEmbed)

        if ctx.channel != trialDateChannel:

            await trialDateChannel.send(embed = removeTrialEmbed)

    @trials.command(aliases = ["ext", "e"])
    async def extend(self, ctx, username: typing.Optional[str], duration: typing.Optional[int]):

        await ctx.message.delete()

        trialData = await trialsCollection.find_one({"_id": "envision"})
        trialMembers = trialData["trialMembers"]

        trialMemberLogChannel = self.bot.get_channel(int(os.getenv("TRIAL_MEMBER_LOG_CHANNEL_ID")))

        if username == None:

            try:

                await ctx.channel.send(f"What member's trial period time do you want to extend?", delete_after = 15)
                usernameResponse = await self.bot.wait_for("message", timeout = 300, check = messageCheck(ctx))
                await usernameResponse.delete()
                username = usernameResponse.content.casefold()

            except asyncio.TimeoutError:

                await ctx.channel.send(f"Timed out", delete_after = 15)
                return

        username = username.casefold()

        if username not in [member["username"] for member in trialMembers]:

            await ctx.channel.send(f"That member is not on their trial period. You can start their trial period with 'o!trials add {username}'.", delete_after = 15)
            return

        if duration == None:

            try:

                await ctx.channel.send(f"How many days do you want to extend their trial by?", delete_after = 15)
                durationResponse = await self.bot.wait_for("message", timeout = 300, check = messageCheck(ctx))
                await durationResponse.delete()
                duration = int(durationResponse.content)

            except asyncio.TimeoutError:

                await ctx.channel.send(f"Timed out", delete_after = 15)
                return

            except ValueError:

                await ctx.channel.send(f"Extension duration must be an integer.", delete_after = 15)
                return

        memberDate = next(trial["memberDate"] for trial in trialMembers if trial["username"] == username) + datetime.timedelta(days = duration)

        await trialsCollection.update_one({"_id": "envision", "trialMembers.username": username}, {"$set": {"trialMembers.$.memberDate": memberDate}})
        extendTrialEmbed = discord.Embed(title = f"{username} Trial Extended", description = f"Extended by {duration} days.\nMember on {memberDate}.\nExtended by {ctx.author}")
        await ctx.channel.send(embed = extendTrialEmbed)

        if ctx.channel != trialMemberLogChannel:

            await trialMemberLogChannel.send(embed = extendTrialEmbed)

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
        
        await ctx.message.delete()

        trialData = await trialsCollection.find_one({"_id": "envision"})
        trialMembers = trialData["trialMembers"]

        membersMessage = f"Trial GEXP Requirement: {trialData['trialReq']}\nTrial Period Duration: {trialData['trialDuration']} days\nTrial Members: {len(trialData['trialMembers'])}"

        trialMemberListEmbed = discord.Embed(title = f"📔Trial Member List 📔 {datetime.datetime.now().astimezone(eastern).date().strftime('%A, %B %d, %Y')}", description = membersMessage, color = discord.Color.purple(), timestamp = datetime.datetime.utcnow())

        for key, chunk in itertools.groupby(sorted(trialMembers, key = operator.itemgetter('memberDate')), key = operator.itemgetter('memberDate')):

            trialMemberListEmbed.add_field(name = f"--- Member on {key.strftime('%m/%d/%Y')} (mm/dd/yyyy) ---", value = ("```" + "\n".join([f"+ {member['username']}" for member in chunk]) + "```"), inline = False)
        
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

            if trial["memberDate"].date() == (now + datetime.timedelta(days = dayOffset)).date():

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

        passingEmbed = discord.Embed(title = f"✅ Passing Trial Members ✅ {(datetime.datetime.now().astimezone(eastern).date() + datetime.timedelta(days = dayOffset)).strftime('%A, %B %d, %Y')} (as of {datetime.datetime.now().astimezone(eastern).date().strftime('%m/%d/%Y')})", description = passingMessage, color = discord.Color.green(), timestamp = datetime.datetime.utcnow())
        failingEmbed = discord.Embed(title = f"❌ Failing Trial Members ❌ {(datetime.datetime.now().astimezone(eastern).date() + datetime.timedelta(days = dayOffset)).strftime('%A, %B %d, %Y')} (as of {datetime.datetime.now().astimezone(eastern).date().strftime('%m/%d/%Y')})", description = failingMessage, color = discord.Color.red(), timestamp = datetime.datetime.utcnow())

        await ctx.channel.send(embed = passingEmbed)
        await ctx.channel.send(embed = failingEmbed)

    @trials.error
    async def trials_error(self, ctx, error):

        if isinstance(error, commands.MissingAnyRole):

            await ctx.channel.send(f"You are missing a required role to use this command!")

        else:

            await ctx.channel.send(f"{datetime.datetime.now()}\n\nAn unexepted error occured:\n{error}\n\nTake a screenshot of this and send it to Phidipedes#4636.")

    @tasks.loop(hours = 24)
    async def checkTrialMembers(self):

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

        passingEmbed = discord.Embed(title = f"✅ Passing Trial Members ✅ ~-~-~-~-~-~ {datetime.datetime.now().astimezone(eastern).date().strftime('%A, %B %d, %Y')}", description = passingMessage, color = discord.Color.green(), timestamp = datetime.datetime.utcnow())
        failingEmbed = discord.Embed(title = f"❌ Failing Trial Members ❌ ~-~-~-~-~-~ {datetime.datetime.now().astimezone(eastern).date().strftime('%A, %B %d, %Y')}", description = failingMessage, color = discord.Color.red(), timestamp = datetime.datetime.utcnow())

        await trialDateChannel.send(embed = passingEmbed)
        await trialDateChannel.send(embed = failingEmbed)

        await trialsCollection.update_one({"_id": "envision"}, {"$set": {"trialMembers": [trial for trial in trialMembers if trial["username"] not in (passList + failList)]}})

    @checkTrialMembers.before_loop
    async def beforeCheckLoop(self):

        await self.bot.wait_until_ready()
        startTime = datetime.datetime.now().astimezone(eastern).replace(hour = 23, minute = 59, second = 30)
        print(f"Starting member update loop on {startTime.strftime('%A, %B %d, %Y')} at {startTime.strftime('%I:%M:%S')}")
        await utils.sleep_until(startTime)

def setup(bot):

    bot.add_cog(trials(bot))