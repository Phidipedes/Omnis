import discord
from discord.ext import commands, tasks

import asyncio
from checks import messageCheck #pylint: disable = import-error
import datetime
from database import activityCollection, memberCollection #pylint: disable = import-error
import typing
import numpy
import pytz

class activity(commands.Cog, name = "Activity"):

    def __init__(self, bot):

        self.bot = bot

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
            whitelist - commands for the inactivity whitelist
                use 'o!help activity whitelist' for more info
        """

        if ctx.invoked_subcommand == None:

            activityCommandUsageEmbed = discord.Embed(title = f"Activity Command Usage", description = f"activity [requirements|check]\nrequirements - set the weekly gexp activity requirement for the guild\ncheck - manually start an inactivity check\nwhitelist - commands for the activity whitelist", color = discord.Color.purple(), timestamp = datetime.datetime.utcnow())
            await ctx.channel.send(embed = activityCommandUsageEmbed)

    @activity.command(aliases = ["requirement", "reqs", "req"])
    async def requirements(self, ctx, amount: typing.Optional[int] = None):

        try:

            if amount == None:

                await ctx.channel.send(f"What amount fo gexp do you want to set the weekly requirement to?")
                amount = int((await self.bot.wait_for("message", timeout = 300, check = messageCheck(ctx))).content)
                
            activityCollection.update_one({"_id": "envision"}, {"$set": {"weeklyReq": amount}})
            await ctx.channel.send(f"Weekly gexp activity requirement set to {amount}.")

        except asyncio.TimeoutError:

            await ctx.channel.send(f"Timed Out")

        except ValueError:

            await ctx.channel.send(f"Amount must be an integer")
    
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

    @commands.group(aliases = ["white", "wl", "w"])
    async def whitelist(self, ctx):

        if ctx.invoked_subcommand == None:

            whitelistCommandUsageEmbed = discord.Embed(title = f"Whitelist Command Usage", description = f"whitelist [add|remove|list]\nadd - add a member to the whitelist\nremove - remove a member from the whitelist\nlist - list every member that is on the whitelist")
            await ctx.channel.send(embed = whitelistCommandUsageEmbed)

    @whitelist.command(aliases = ["a"])
    async def add(self, ctx, username: typing.Optional[str] = None):

        eastern = pytz.timezone("US/Eastern")

        activityData = await activityCollection.find_one({"_id": "envision"})
        memberData = memberCollection.find_one({"_id": "envision"})

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

        activityCollection.update_one({"_id": "envision"}, {"$push": {"whitelist": {"username": username, "unwhitelistDate": datetime.datetime.now().astimezone(eastern) + datetime.timedelta(days = activityData["whitelistDuration"])}}})
        await ctx.channel.send(f"Member {username} whitlisted on {datetime.datetime.now().astimezone(eastern).strftime('%A, %B %d, %Y')}. Unwhitelisted on {(datetime.datetime.now().astimezone(eastern) + datetime.timedelta(days = activityData['whitelistDuration'])).strftime('%A, %B %d, %Y')}")

    @whitelist.command(aliases = ["rem", "rm", "r"])
    async def remove(self, ctx, username: typing.Optional[str] = None):

        activityData = activityCollection.find_one({"_id": "envision"})
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
        await ctx.channel.send(f"Unwhitelisted member {username}")

    @whitelist.command(aliases = ["list", "li", "l"])
    async def _list(self, ctx):

        activityData = activityCollection.find_one({"_id": "envision"})
        whitelist = activityData["whitelist"]

        whitelistEmbed = discord.Embed(title = f"⬜ Whitelisted Members ⬜", description = f"Whitelist duration: {activityData['whitelistDuration']}\nWhitelisted Members: {len(whitelist)}", color = discord.Color.lighter_grey(), timestamp = datetime.datetime.utcnow())

        if len(whitelist) > 0:
        
            for chunk in numpy.array_split(whitelist, (len(whitelist) / 22)):

                whitelistEmbed.add_field(name = f"--------------------------------------------------", value = ("```" + "\n".join([f"+ {member['username']} unwhitelisted on {member['unwhitelistedDate'].date().strftime('%m/%d/%Y')}" for member in chunk]) + "```"))

        else:

            whitelist.add_field(name = f"--------------------------------------------------", value = f"```No whitelisted members```")

def setup(bot):

    bot.add_cog(activity(bot))