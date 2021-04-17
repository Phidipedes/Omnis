import discord
from discord.ext import commands, tasks

import asyncio
import json
import requests
import datetime
import os

from database import memberCollection, trialsCollection, activityCollection #pylint: disable = import-error
from timezones import eastern #pylint: disable = import-error

class members(commands.Cog, name = "Member Updates"):

    def __init__(self, bot):

        self.bot = bot
        self.updateMembers.start() #pylint: disable=no-member

    @tasks.loop(minutes = 3)
    async def updateMembers(self):

        memberLogChannel = self.bot.get_channel(int(os.getenv("MEMBER_LOG_CHANNEL_ID")))
        trialDateChannel = self.bot.get_channel(int(os.getenv("TRIAL_MEMBER_DATE_CHANNEL_ID")))

        hypixelData = requests.get(f"https://api.hypixel.net/guild?key={os.getenv('HYPIXEL_API_KEY')}&name=envision").json()
        cachedData = await memberCollection.find_one({"_id": "envision"})
        trialData = await trialsCollection.find_one({"_id": "envision"})
        activityData = await activityCollection.find_one({"_id": "envision"})
        trialMembersList = [trial["username"] for trial in trialData["trialMembers"]]
        whitelistedMembersList = [wlmember["username"] for wlmember in activityData["whitelist"]]

        for member in hypixelData["guild"]["members"]:

            try:

                mojangData = requests.get(f"https://api.ashcon.app/mojang/v2/user/{member['uuid']}").json()

                currentUsername = mojangData["username"].casefold()
                currentRank = member["rank"]

                member["expHistory"]["total"] = sum(member["expHistory"].values())

                if member["uuid"] not in cachedData["members"].keys():

                    await memberCollection.update_one({"_id": "envision"}, {"$set": {f"members.{member['uuid']}": {"username": currentUsername, "rank": member["rank"], "joined": member["joined"], "gexp": member["expHistory"], }}})
                    memberJoinEmbed = discord.Embed(title = f"Member Joined", description = f"UUID: {member['uuid']}\nIGN: {currentUsername}\nJoined at:{member['joined']}", color = discord.Color.green(), timestamp = datetime.datetime.utcnow())
                    await memberLogChannel.send(embed = memberJoinEmbed)

                    memberDate = datetime.datetime.now().astimezone(eastern).replace(hour = 0, minute = 0, second = 0, microsecond = 0) + datetime.timedelta(days = trialData["trialDuration"])

                    await trialsCollection.update_one({"_id": "envision"}, {"$push": {"trialMembers": {"username": currentUsername, "memberDate": memberDate}}})
                    newTrialEmbed = discord.Embed(title = f"{currentUsername} Starting Trial", description = f"Starting trial on {datetime.datetime.now().astimezone(eastern).date().strftime('%d/%m/%Y')} (dd/mm/yyyy).\nMember on {memberDate.date().strftime('%d/%m/%Y')}\nAdded by: Omnis#7009 (auto added on member join).", color = discord.Color.green(), timestamp = datetime.datetime.utcnow())
                    trialDateChannel.send(embed = newTrialEmbed)

                else:

                    cachedUsername = cachedData["members"][member["uuid"]]["username"]
                    cachedRank = cachedData["members"][member["uuid"]]["rank"]

                    if cachedUsername!= currentUsername:

                        await memberCollection.update_one({"_id": "envision"}, {"$set": {f"members.{member['uuid']}.username": currentUsername}})
                        memberUsernameChangeEmbed = discord.Embed(title = f"Member Username Changed", description = f"UUID:{member['uuid']}\n{cachedUsername} **-->** {currentUsername}\nRank: {currentRank}", color = discord.Color.blue(), timestamp = datetime.datetime.utcnow())
                        await memberLogChannel.send(embed = memberUsernameChangeEmbed)

                        if cachedUsername in trialMembersList:

                            await trialsCollection.update_one({"_id": "envision", "trialMembers.username": cachedUsername}, {"$set": {"trialMembers.$.username": currentUsername}})

                        if cachedUsername in whitelistedMembersList:

                            await activityData.update_one({"_id": "envision", "whitelist.username": cachedUsername}, {"$set": {"whitelist.$.username": currentUsername}})

                    if cachedRank != currentRank:

                        await memberCollection.update_one({"_id": "envision"}, {"$set": {f"members.{member['uuid']}.rank": currentRank}})
                        memberRankChangeEmbed = discord.Embed(title = f"Member Rank Changed", description = f"UUID: {member['uuid']}\nUsername:{currentUsername}\n{cachedRank} **-->** {currentRank}", color = discord.Color.blue(), timestamp = datetime.datetime.utcnow())
                        await memberLogChannel.send(embed = memberRankChangeEmbed)

                await memberCollection.update_one({"_id": "envision"}, {"$set": {f"members.{member['uuid']}.gexp": member["expHistory"]}})

            except:

                me = self.bot.get_user(693132768510607400)

                me.send(f"Check log. Somethign went wrong")

                print(f"Something went wrong with the following data:\nHypixel Data:\n{member}")
                print(f"Mojang Data:\n{mojangData}")
                print(f"Cached Data:\n{cachedUsername}, {cachedRank}")

                continue

        for uuid in cachedData["members"].keys():

            if uuid not in [member["uuid"] for member in hypixelData["guild"]["members"]]:

                await memberCollection.update_one({"_id": "envision"}, {"$unset": {f"members.{uuid}": ""}})
                await trialsCollection.update_one({"_id": "envision"}, {"$pull": {"trialMembers": {"username": cachedData["members"][uuid]["username"]}}})
                await activityCollection.update_one({"_id": "envision"}, {"$pull": {"whitelist": {"username": cachedData["members"][uuid]["username"]}}})

                memberLeaveEmbed = discord.Embed(title = f"Member Left", description = f"UUID: {uuid}\nUsername: {cachedData['members'][uuid]['username']}\nRank: {cachedData['members'][uuid]['rank']}", color = discord.Color.dark_red(), timestamp = datetime.datetime.utcnow())

                await memberLogChannel.send(embed = memberLeaveEmbed)

    @updateMembers.before_loop
    async def beforeUpdateMembers(self):

        await self.bot.wait_until_ready()
        await asyncio.sleep(150)

def setup(bot):

    bot.add_cog(members(bot))