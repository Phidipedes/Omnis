import discord
from discord.ext import commands, tasks
from discord.utils import sleep_until

from checks import messageCheck #pylint: disable = import-error
from database import activityCollection, memberCollection #pylint: disable = import-error
from timezones import eastern #pylint: disable = import-error

import asyncio
import datetime
import itertools
import numpy
import operator
import os
import pytz
import typing

class activity(commands.Cog, name = "Activity"):

    def __init__(self, bot):

        self.bot = bot
        self.updateWhitelist.start() #pylint: disable = no-member

    @commands.group(aliases = ["inactivity", "act", "inact", "a", "ia"])
    @commands.has_any_role(738915444420903022, 716599787780177954, 730175515809546300)
    async def activity(self, ctx):

        """
        Activity commands

        Commands:
            requirements - change the weekly gexp activity requirement for all members.
                usage: o!trial requirements [amount]
                aliases: requirement, reqs, req
            check - start a manual inactivity check for all members.
                usage: o!trial check [dayOffset]
                aliases: ch, c
        """

        if ctx.invoked_subcommand == None:

            activityCommandUsageEmbed = discord.Embed(title = f"Activity Command Usage", description = f"activity [requirements|check]\nrequirements - set the weekly gexp activity requirement for the guild\ncheck - manually start an inactivity check", color = discord.Color.purple(), timestamp = datetime.datetime.utcnow())
            await ctx.channel.send(embed = activityCommandUsageEmbed)

    @activity.command(aliases = ["requirement", "reqs", "req"])
    async def requirements(self, ctx, amount: typing.Optional[int]):

        await ctx.message.delete()

        if amount == None:

            try:

                await ctx.channel.send(f"What amount fo gexp do you want to set the weekly requirement to?", delete_after = 15)
                amountResponse = await self.bot.wait_for("message", timeout = 300, check = messageCheck(ctx))
                await amount.delete()
                amount = int(amountResponse.content)
            
            except asyncio.TimeoutError:

                await ctx.channel.send(f"Timed Out", delete_after = 15)

            except ValueError:

                await ctx.channel.send(f"Amount must be an integer", delete_after = 15)

        activityCollection.update_one({"_id": "envision"}, {"$set": {"weeklyReq": amount}})
        await ctx.channel.send(f"Weekly gexp activity requirement set to {amount} by {ctx.author.name}")
    
    @activity.command(aliases = ["ch", "c"])
    async def check(self, ctx):

        activityReq = (await activityCollection.find_one({"_id": "envision"}))["weeklyReq"]
        members = (await memberCollection.find_one({"_id": "envision"}))["members"].values()

        passList = [f"+ {member['username']} --- earned {member['gexp']['total']}" for member in members if member["gexp"]["total"] >= activityReq]
        failList = [f"+ {member['username']} --- missing {activityReq - member['gexp']['total']}" for member in members if member["gexp"]["total"] < activityReq]

        passEmbed = discord.Embed(title = f"Active Members", description = f"Members who have earned at least {activityReq} gexp in the past 7 days:", color = discord.Color.green(), timestamp = datetime.datetime.utcnow())
        failEmbed = discord.Embed(title = f"Inactive Members", description = f"Members who have not earned at least {activityReq} gexp in the past 7 days:", color = discord.Color.red(), timestamp = datetime.datetime.utcnow())

        if len(passList) > 0:
        
            for chunk in numpy.array_split(passList, 5):

                passEmbed.add_field(name = f"--------------------------------------", value = "```" + "\n".join(list(chunk)) + "```", inline = False)

        else:

            passEmbed.add_field(name = f"-------------------------------------", value = "```No active members```")

        if len(failList) > 0:
        
            for chunk in numpy.array_split(failList, 5):

                failEmbed.add_field(name = f"--------------------------------------", value = "```" + "\n".join(list(chunk)) + "```", inline = False)

        else:

            failEmbed.add_field(name = f"-------------------------------------", value = "```No inactive members```")

        await ctx.channel.send(embed = passEmbed)
        await ctx.channel.send(embed = failEmbed)

    @activity.error
    async def activity_error(self, ctx, error):

        if isinstance(error, commands.MissingAnyRole):

            await ctx.channel.send(f"You are missing a required role to use this command!")

    @commands.group(aliases = ["white", "wl", "w"])
    @commands.has_any_role(738915444420903022, 716599787780177954, 730175515809546300)
    async def whitelist(self, ctx):

        if ctx.invoked_subcommand == None:

            whitelistCommandUsageEmbed = discord.Embed(title = f"Whitelist Command Usage", description = f"whitelist [add|remove|list]\nadd - add a member to the whitelist\nremove - remove a member from the whitelist\nlist - list every member that is on the whitelist")
            await ctx.channel.send(embed = whitelistCommandUsageEmbed)

    @whitelist.command(aliases = ["dura", "dur"])
    async def duration(self, ctx, duration: typing.Optional[int]):

        await ctx.message.delete()

        whitelistLogChannel = self.bot.get_channel(int(os.getenv("WHITELIST_LOG_CHANNEL_ID")))

        if duration == None:

            try:

                await ctx.channel.send(f"How long do you want to set the whitelist time to be?", delete_after = 15)
                durationResponse = await self.bot.wait_for("message", timeout = 300, check = messageCheck(ctx))
                await durationResponse.delete()
                duration = int(durationResponse.content)

            except asyncio.TimeoutError:

                await ctx.channel.send(f"Timed out", delete_after = 15)
                return
            
            except ValueError:

                await ctx.channel.send(f"The duration must be an integer.", delete_after = 15)
                return

            activityCollection.update_one({"_id": "envision"}, {"$set": {"whitelistDuration": duration}})

            await ctx.channel.send(f"Whitelist duration set to {duration} days by {ctx.author.name}")

            if ctx.channel != whitelistLogChannel:

                await whitelistLogChannel.send(f"Whitelist duration set to {duration} days by {ctx.author.name}")

    @whitelist.command(aliases = ["a"])
    async def add(self, ctx, username: typing.Optional[str]):

        await ctx.message.delete()

        activityData = await activityCollection.find_one({"_id": "envision"})
        memberData = await memberCollection.find_one({"_id": "envision"})

        if username == None:

            try:
            
                await ctx.channel.send(f"What username do you want to add to the whitelist?")
                username = (await self.bot.wait_for("message", timeout = 300, check = messageCheck(ctx))).content.casefold()

            except asyncio.TimeoutError:

                await ctx.channel.send(f"Timed out")

        username = username.casefold()

        if username not in [member["username"] for member in memberData["members"].values()]:

            await ctx.channel.send(f"That member is not in the guild. Are you sure you spelled their name correctly? I fyou are sure you spelled their name correctly and that they are in the guild, wait a few minutes and try again. The cache updates every 5 minutes.")
            return

        activityCollection.update_one({"_id": "envision"}, {"$push": {"whitelist": {"username": username, "unwhitelistDate": datetime.datetime.now().replace(hour = 0, minute = 0, second = 0, microsecond = 0).astimezone(eastern) + datetime.timedelta(days = activityData["whitelistDuration"])}}})
        await ctx.channel.send(f"Member {username} whitlisted on {datetime.datetime.now().astimezone(eastern).strftime('%A, %B %d, %Y')}. Unwhitelisted on {(datetime.datetime.now().astimezone(eastern) + datetime.timedelta(days = activityData['whitelistDuration'])).strftime('%A, %B %d, %Y')}. Added to whitelist by {ctx.author.name}")

    @whitelist.command(aliases = ["rem", "rm", "r"])
    async def remove(self, ctx, username: typing.Optional[str]):

        await ctx.message.delete()

        activityData = await activityCollection.find_one({"_id": "envision"})
        whitelistedMembers = [member["username"] for member in activityData["whitelist"]]

        if username == None:

            try:
            
                await ctx.channel.send(f"What username do you want to remove from the whitelist?")
                username = (await self.bot.wait_for("message", timeout = 300, check = messageCheck(ctx))).content.casefold()

            except asyncio.TimeoutError:

                await ctx.channel.send(f"Timed out")

        username = username.casefold()

        if username not in whitelistedMembers:

            await ctx.channel.send(f"That member is not ont he waitlist.")
            return

        activityCollection.update_one({"_id": "envision"}, {"$pull": {"whitelist": {"username": username}}})
        await ctx.channel.send(f"Unwhitelisted member {username}. Unwhitelisted by {ctx.author.name}")

    @whitelist.command(aliases = ["ext", "e"])
    async def extend(self, ctx, username: typing.Optional[str], duration: typing.Optional[int]):

        await ctx.message.delete()

        activityData = await activityCollection.find_one({"_id": "envision"})
        whitelist = activityData["whitelist"]

        whitelistLogChannel = self.bot.get_channel(int(os.getenv("WHITELIST_LOG_CHANNEL_ID")))

        if username == None:

            try:

                await ctx.channel.send(f"What member's whitelist time do you want to extend?", delete_after = 15)
                usernameResponse = await self.bot.wait_for("message", timeout = 300, check = messageCheck(ctx))
                await usernameResponse.delete()
                username = usernameResponse.content.casefold()

            except asyncio.TimeoutError:

                await ctx.channel.send(f"Timed out", delete_after = 15)
                return

        username = username.casefold()

        if username not in [member["username"] for member in whitelist]:

            await ctx.channel.send(f"That member is not on the whitelist. You can add them to the whitelist with 'o!whitelist add {username}'.", delete_after = 15)
            return

        if duration == None:

            try:

                await ctx.channel.send(f"How many days do you want to extend their whitelist by?", delete_after = 15)
                durationResponse = await self.bot.wait_for("message", timeout = 300, check = messageCheck(ctx))
                await durationResponse.delete()
                duration = int(durationResponse.content)

            except asyncio.TimeoutError:

                await ctx.channel.send(f"Timed out", delete_after = 15)
                return

            except ValueError:

                await ctx.channel.send(f"Extension duration must be an integer.", delete_after = 15)
                return

        currentUnwhitelistDate = next(member["unwhitelistDate"] for member in whitelist if member["username"] == username)

        await activityCollection.update_one({"_id": "envision", "whitelist.username": username}, {"$set": {"whitelist.$.unwhitelistDate": currentUnwhitelistDate + datetime.timedelta(days = duration)}})
        await ctx.channel.send(f"Member {username}'s whitelist time extended by {duration} days. Unwhitelisted on {(currentUnwhitelistDate + datetime.timedelta(days = duration)).strftime('%m/%d/%Y')} (mm/dd/yyyy). Extended by {ctx.author}")

        if ctx.channel != whitelistLogChannel:

            await whitelistLogChannel.send(f"Member {username}'s whitelist time extended by {duration} days. Unwhitelisted on {(currentUnwhitelistDate + datetime.timedelta(days = duration)).strftime('%m/%d/%Y')} (mm/dd/yyyy). Extended by {ctx.author}")

    @whitelist.command(aliases = ["list", "li", "l"])
    async def _list(self, ctx):

        await ctx.message.delete()

        eastern = pytz.timezone("US/Eastern")

        activityData = await activityCollection.find_one({"_id": "envision"})
        whitelist = activityData["whitelist"]

        whitelistEmbed = discord.Embed(title = f"⬜ Whitelisted Members ⬜ {datetime.datetime.now().astimezone(eastern).date().strftime('%A, %B %d, %Y')}", description = f"Whitelist duration: {activityData['whitelistDuration']}\nWhitelisted Members: {len(whitelist)}", color = discord.Color.lighter_grey(), timestamp = datetime.datetime.utcnow())

        if len(whitelist) > 0:

            for key, chunk in itertools.groupby(sorted(whitelist, key = operator.itemgetter('unwhitelistDate')), key = operator.itemgetter('unwhitelistDate')):

                whitelistEmbed.add_field(name = f"Unwhitelisted on {key.strftime('%m/%d/%Y')} (mm/dd/yyyy)", value = ("```" + "\n".join([f"+ {member['username']}" for member in chunk]) + "```"), inline = False)

        else:

            whitelist.add_field(name = f"--------------------------------------------------", value = f"```No whitelisted members```")

        await ctx.channel.send(embed = whitelistEmbed)

    @whitelist.error
    async def whitelist_error(self, ctx, error):

        if isinstance(error, commands.MissingAnyRole):

            await ctx.channel.send(f"You are missing a required role to use this command!")

    @tasks.loop(hours = 24)
    async def updateWhitelist(self):

        activityData = await activityCollection.find_one({"_id": "envision"})
        whitelist = activityData["whitelist"]

        now = datetime.datetime.now().astimezone(eastern)

        whitelistLogChannel = self.bot.get_channel(int(os.getenv("WHITELIST_LOG_CHANNEL_ID")))

        for member in whitelist:

            if member["unwhitelistDate"].date() == now.date():

                await whitelistLogChannel.send(f"Member {member['username']} unwhitelisted. Reached the end of their whitelist time.")
                activityCollection.update_one({"_id": "envision"}, {"$pull": {"whitelist": {"username": member["username"]}}})

    @updateWhitelist.before_loop
    async def beforeUpdateWhitelist(self):

        await self.bot.wait_until_ready()
        startTime = datetime.datetime.now().astimezone(eastern).replace(hour = 23, minute = 59, second = 30, microsecond = 0)
        print(f"starting whitelist update loop on {startTime.strftime('%A, %B %d, %Y')} at {startTime.strftime('%I:%M:%S')}")
        await sleep_until(startTime)

def setup(bot):

    bot.add_cog(activity(bot))